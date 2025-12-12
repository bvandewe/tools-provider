# Session Flow Architecture

**Version:** 1.0.0
**Status:** `ANALYSIS`
**Date:** December 11, 2025
**Purpose:** Document current implementation and identify gaps for proactive session iteration

---

## 1. Current Architecture Overview

### 1.1 Key Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Browser)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  SessionView Component                                               │    │
│  │  - Calls POST /session/ to create session                           │    │
│  │  - Opens SSE connection to GET /session/{id}/stream                 │    │
│  │  - Renders widgets based on client_action events                    │    │
│  │  - Calls POST /session/{id}/respond when user submits               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  SessionController (api/controllers/session_controller.py)          │    │
│  │                                                                      │    │
│  │  Endpoints:                                                          │    │
│  │  - POST /session/           → CreateSessionCommand                   │    │
│  │  - GET  /session/{id}       → GetSessionQuery                        │    │
│  │  - GET  /session/{id}/stream → SSE stream (creates ProactiveAgent)  │    │
│  │  - POST /session/{id}/respond → SubmitClientResponseCommand          │    │
│  │  - DELETE /session/{id}     → TerminateSessionCommand                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  ProactiveAgent (application/agents/proactive_agent.py)             │    │
│  │                                                                      │    │
│  │  - Created fresh on each /stream request                            │    │
│  │  - Contains LLM provider reference                                   │    │
│  │  - Has client tools: present_choices, request_free_text, etc.       │    │
│  │  - Runs _proactive_loop() → calls LLM → detects tool calls          │    │
│  │  - Suspends on client tool, emits CLIENT_ACTION event               │    │
│  │  - resume_with_response() to continue after user responds           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Domain Aggregates                                                   │    │
│  │                                                                      │    │
│  │  Session (domain/entities/session.py)                                │    │
│  │  ├── SessionState                                                    │    │
│  │  │   ├── id, user_id, conversation_id                               │    │
│  │  │   ├── session_type, control_mode                                 │    │
│  │  │   ├── status (PENDING→ACTIVE→AWAITING_CLIENT_ACTION→COMPLETED)   │    │
│  │  │   ├── items: list[SessionItem]  # Question-answer history        │    │
│  │  │   ├── pending_action: ClientAction | None                        │    │
│  │  │   └── config, ui_state, timestamps                               │    │
│  │  │                                                                   │    │
│  │  Conversation (domain/entities/conversation.py)                      │    │
│  │  ├── ConversationState                                               │    │
│  │  │   ├── id, user_id                                                │    │
│  │  │   ├── messages: list[Message]  # LLM message history             │    │
│  │  │   └── metadata                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LLM Provider                                      │
│  - OpenAI / Ollama / etc.                                                    │
│  - Receives system prompt + messages + tool definitions                      │
│  - Returns content and/or tool_calls                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Current Flow: Single Item Session

### 2.1 Sequence Diagram: Create → First Question → User Answer

```
┌────────┐          ┌─────────────┐         ┌─────────────┐      ┌───────────┐      ┌─────┐
│Frontend│          │  Controller │         │   Session   │      │   Agent   │      │ LLM │
└───┬────┘          └──────┬──────┘         └──────┬──────┘      └─────┬─────┘      └──┬──┘
    │                      │                       │                   │               │
    │  POST /session/      │                       │                   │               │
    │  {session_type:      │                       │                   │               │
    │   "learning"}        │                       │                   │               │
    │─────────────────────>│                       │                   │               │
    │                      │                       │                   │               │
    │                      │  CreateSessionCommand │                   │               │
    │                      │──────────────────────>│                   │               │
    │                      │                       │                   │               │
    │                      │                       │ Session.create()  │               │
    │                      │                       │ status=PENDING    │               │
    │                      │                       │ items=[]          │               │
    │                      │                       │───────────────────│               │
    │                      │                       │                   │               │
    │                      │                       │ Session.start()   │               │
    │                      │                       │ status=ACTIVE     │               │
    │                      │                       │───────────────────│               │
    │                      │                       │                   │               │
    │  {session_id,        │                       │                   │               │
    │   stream_url}        │                       │                   │               │
    │<─────────────────────│                       │                   │               │
    │                      │                       │                   │               │
    │                      │                       │                   │               │
    │  GET /session/{id}/stream (SSE)              │                   │               │
    │─────────────────────>│                       │                   │               │
    │                      │                       │                   │               │
    │                      │  GetSessionQuery      │                   │               │
    │                      │──────────────────────>│                   │               │
    │                      │<──────────────────────│                   │               │
    │                      │                       │                   │               │
    │                      │  Create ProactiveAgent│                   │               │
    │                      │──────────────────────────────────────────>│               │
    │                      │                       │                   │               │
    │                      │  agent.start_session(context)             │               │
    │                      │──────────────────────────────────────────>│               │
    │                      │                       │                   │               │
    │  SSE: connected      │                       │                   │               │
    │<─────────────────────│                       │                   │               │
    │                      │                       │                   │               │
    │                      │                       │   _proactive_loop │               │
    │                      │                       │                   │               │
    │                      │                       │                   │  chat(        │
    │                      │                       │                   │   messages=[  │
    │                      │                       │                   │    system,    │
    │                      │                       │                   │    "Start     │
    │                      │                       │                   │     learning  │
    │                      │                       │                   │     session"  │
    │                      │                       │                   │   ],          │
    │                      │                       │                   │   tools=[...] │
    │                      │                       │                   │  )            │
    │                      │                       │                   │──────────────>│
    │                      │                       │                   │               │
    │                      │                       │                   │  Response:    │
    │                      │                       │                   │  tool_calls=[ │
    │                      │                       │                   │   {name:      │
    │                      │                       │                   │    "present_  │
    │                      │                       │                   │    choices",  │
    │                      │                       │                   │    args:{...}}│
    │                      │                       │                   │  ]            │
    │                      │                       │                   │<──────────────│
    │                      │                       │                   │               │
    │                      │                       │   is_client_tool? │               │
    │                      │                       │   YES → suspend   │               │
    │                      │                       │                   │               │
    │                      │  CLIENT_ACTION event  │                   │               │
    │                      │<──────────────────────────────────────────│               │
    │                      │                       │                   │               │
    │  SSE: client_action  │                       │                   │               │
    │  {widget_type:       │                       │                   │               │
    │   "multiple_choice", │                       │                   │               │
    │   props: {...}}      │                       │                   │               │
    │<─────────────────────│                       │                   │               │
    │                      │                       │                   │               │
    │                      │  SetPendingAction     │                   │               │
    │                      │  Command              │                   │               │
    │                      │──────────────────────>│                   │               │
    │                      │                       │                   │               │
    │                      │                       │ set_pending_action│               │
    │                      │                       │ status=AWAITING   │               │
    │                      │                       │───────────────────│               │
    │                      │                       │                   │               │
    │  SSE: run_suspended  │                       │                   │               │
    │<─────────────────────│                       │                   │               │
    │                      │                       │                   │               │
    │  (SSE stream ends,   │                       │                   │               │
    │   heartbeats begin)  │                       │                   │               │
    │                      │                       │                   │               │
    │                      │                       │                   │               │
    │  [User interacts     │                       │                   │               │
    │   with widget...]    │                       │                   │               │
    │                      │                       │                   │               │
    │                      │                       │                   │               │
    │  POST /session/{id}/respond                  │                   │               │
    │  {tool_call_id,      │                       │                   │               │
    │   response: {...}}   │                       │                   │               │
    │─────────────────────>│                       │                   │               │
    │                      │                       │                   │               │
    │                      │  SubmitClientResponse │                   │               │
    │                      │  Command              │                   │               │
    │                      │──────────────────────>│                   │               │
    │                      │                       │                   │               │
    │                      │                       │ submit_response() │               │
    │                      │                       │ - clears pending  │               │
    │                      │                       │ - completes item  │               │
    │                      │                       │ - status=ACTIVE   │               │
    │                      │                       │───────────────────│               │
    │                      │                       │                   │               │
    │  {session details}   │                       │                   │               │
    │<─────────────────────│                       │                   │               │
    │                      │                       │                   │               │
    │                      │                       │                   │               │
    │  ┌────────────────────────────────────────────────────────────────────────┐     │
    │  │                         ⚠️ PROBLEM AREA                                 │     │
    │  │                                                                         │     │
    │  │  At this point, the original ProactiveAgent instance is GONE.          │     │
    │  │  Its SuspendedState (with LLM message history) is LOST.                │     │
    │  │                                                                         │     │
    │  │  The Session aggregate knows the user responded, but there's no        │     │
    │  │  mechanism to continue the agent loop with the next question.          │     │
    │  │                                                                         │     │
    │  │  If frontend reconnects to /stream:                                    │     │
    │  │  - A NEW agent is created                                              │     │
    │  │  - No conversation history (empty messages)                            │     │
    │  │  - LLM starts fresh → generates ONE question → session ends            │     │
    │  └────────────────────────────────────────────────────────────────────────┘     │
    │                      │                       │                   │               │
```

---

## 3. Detailed Component Analysis

### 3.1 Session vs Conversation Relationship

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SESSION AGGREGATE                                   │
│                                                                              │
│  Purpose: Manages structured interactions (items, widgets, UI state)         │
│                                                                              │
│  SessionState:                                                               │
│  ├── id: "sess_abc123"                                                      │
│  ├── user_id: "user_456"                                                    │
│  ├── conversation_id: "conv_789"  ◄─── Links to Conversation                │
│  ├── session_type: LEARNING                                                 │
│  ├── control_mode: PROACTIVE                                                │
│  ├── status: AWAITING_CLIENT_ACTION                                         │
│  │                                                                           │
│  ├── items: [                        # Completed question-answer cycles     │
│  │     {                                                                     │
│  │       id: "item_1",                                                      │
│  │       sequence: 1,                                                       │
│  │       agent_prompt: "What is 2+2?",                                      │
│  │       client_action: {widget_type: "multiple_choice", ...},              │
│  │       user_response: {selection: "4", index: 1},                         │
│  │       started_at: "...",                                                 │
│  │       completed_at: "...",                                               │
│  │     }                                                                     │
│  │   ]                                                                       │
│  │                                                                           │
│  ├── pending_action: {               # Current widget waiting for response  │
│  │     tool_call_id: "call_xyz",                                            │
│  │     tool_name: "present_choices",                                        │
│  │     widget_type: "multiple_choice",                                      │
│  │     props: {prompt: "...", options: [...]}                               │
│  │   }                                                                       │
│  │                                                                           │
│  ├── ui_state: {...}                 # For frontend restoration             │
│  └── config: {max_items: 5, ...}     # Session configuration                │
│                                                                              │
│  Key Methods:                                                                │
│  - start() → status = ACTIVE                                                │
│  - set_pending_action(action) → status = AWAITING_CLIENT_ACTION             │
│  - submit_response(response) → clears pending, adds to items, status=ACTIVE │
│  - complete() → status = COMPLETED                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ conversation_id
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONVERSATION AGGREGATE                                │
│                                                                              │
│  Purpose: Raw LLM message log (for context and audit)                        │
│                                                                              │
│  ConversationState:                                                          │
│  ├── id: "conv_789"                                                         │
│  ├── user_id: "user_456"                                                    │
│  ├── messages: [                     # LLM message history                  │
│  │     {role: "system", content: "You are a learning tutor..."},            │
│  │     {role: "user", content: "Start a learning session"},                 │
│  │     {role: "assistant", content: "", tool_calls: [...]},                 │
│  │     {role: "tool", tool_call_id: "...", content: "{...}"},               │
│  │     ...                                                                   │
│  │   ]                                                                       │
│  └── metadata: {...}                                                         │
│                                                                              │
│  ⚠️ CURRENT STATUS: Conversation exists but is NOT being populated          │
│     with LLM messages during proactive sessions!                             │
│                                                                              │
│     The ProactiveAgent builds messages in-memory but doesn't persist them.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 ProactiveAgent In-Memory State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROACTIVE AGENT (Ephemeral)                          │
│                                                                              │
│  ⚠️ Created fresh on each GET /session/{id}/stream request                   │
│  ⚠️ Destroyed when SSE stream ends or disconnects                            │
│                                                                              │
│  Instance State:                                                             │
│  ├── _llm: LlmProvider                # Reference to OpenAI/Ollama          │
│  ├── _config: AgentConfig             # max_iterations, stream_responses    │
│  ├── _session_context: ProactiveSessionContext                              │
│  │     ├── session_id                                                       │
│  │     ├── session_type                                                     │
│  │     ├── config: SessionConfig                                            │
│  │     ├── conversation_id                                                  │
│  │     ├── items_completed: int                                             │
│  │     └── metadata                                                         │
│  │                                                                           │
│  └── _suspended_state: SuspendedState | None                                │
│        ├── messages: list[LlmMessage]  # ⚠️ IN-MEMORY ONLY                  │
│        │     [                                                               │
│        │       LlmMessage.system("You are a learning tutor..."),            │
│        │       LlmMessage.user("Start a learning session"),                 │
│        │       LlmMessage.assistant("", tool_calls=[...]),                  │
│        │     ]                                                               │
│        ├── pending_tool_call: LlmToolCall                                   │
│        ├── iteration: int                                                   │
│        ├── tool_calls_made: int                                             │
│        └── start_time: float                                                │
│                                                                              │
│  When agent suspends:                                                        │
│  - _suspended_state is populated                                            │
│  - Control returns to controller                                            │
│  - SSE stream emits client_action and run_suspended                         │
│                                                                              │
│  When resume_with_response() is called:                                      │
│  - Restores messages from _suspended_state                                  │
│  - Adds tool result to messages                                             │
│  - Continues _continue_loop()                                               │
│                                                                              │
│  ⚠️ PROBLEM: resume_with_response() is never called in current flow!        │
│     The agent instance is destroyed before the user responds.               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The Gap: Why Sessions End After One Item

### 4.1 Current Broken Flow

```
Timeline:
─────────────────────────────────────────────────────────────────────────────►
                                                                          time

T0: POST /session/ → Session created, status=PENDING
    │
T1: GET /stream → NEW ProactiveAgent created
    │              Agent has empty message history
    │              Agent calls LLM with system prompt
    │
T2: LLM returns tool_call (present_choices)
    │ Agent detects client tool → suspends
    │ Agent._suspended_state = {messages: [...], pending_tool_call: ...}
    │ SSE emits client_action
    │ Controller calls SetPendingActionCommand
    │ Session.status = AWAITING_CLIENT_ACTION
    │
T3: SSE stream effectively ends (only heartbeats)
    │ ⚠️ ProactiveAgent instance is still alive but idle
    │ ⚠️ In practice, connection may drop, agent gets garbage collected
    │
T4: User interacts with widget, clicks submit
    │
T5: POST /respond → SubmitClientResponseCommand
    │ Session.submit_response() called
    │ Session.pending_action = None
    │ Session.items = [{...completed item...}]
    │ Session.status = ACTIVE
    │ Response returned to frontend
    │
    │ ⚠️ NO AGENT INVOLVED IN THIS STEP
    │ ⚠️ Nobody calls agent.resume_with_response()
    │ ⚠️ LLM never sees the user's answer
    │
T6: Frontend has options:
    │
    ├─► Option A: Do nothing
    │   Session stays in ACTIVE status with no pending_action
    │   User sees nothing more happening
    │   Session effectively dead
    │
    └─► Option B: Reconnect to GET /stream
        NEW ProactiveAgent created (different instance!)
        Agent has NO _suspended_state (it's a fresh instance)
        Agent builds messages from scratch:
          - System prompt (from session_type)
          - "Start a learning session" (hardcoded)
        Agent calls LLM → LLM generates ONE question
        LLM may just respond with text (no tool call) → session completes
        OR LLM calls present_choices → cycle repeats for ONE more item
```

### 4.2 What's Missing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MISSING COMPONENTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. MESSAGE PERSISTENCE                                                      │
│     ────────────────────                                                     │
│     LLM messages are built in-memory by ProactiveAgent but never saved.     │
│     When agent is recreated, context is lost.                               │
│                                                                              │
│     Need: Save messages to Conversation aggregate after each LLM call.      │
│                                                                              │
│  2. SESSION CONTINUATION TRIGGER                                             │
│     ─────────────────────────────                                            │
│     After user responds, nothing triggers the next agent iteration.         │
│                                                                              │
│     Options:                                                                 │
│     a) POST /respond returns a streaming response (agent continues inline)  │
│     b) POST /respond triggers backend to resume agent + push via websocket  │
│     c) Frontend reconnects to /stream (current broken approach)             │
│                                                                              │
│  3. CONVERSATION RECONSTRUCTION                                              │
│     ──────────────────────────────                                           │
│     When agent is recreated, need to rebuild LLM context from stored data.  │
│                                                                              │
│     Sources:                                                                 │
│     - Conversation.messages (if persisted)                                  │
│     - Session.items (can reconstruct Q&A pairs)                             │
│                                                                              │
│  4. END CONDITION LOGIC                                                      │
│     ────────────────────                                                     │
│     LLM doesn't know when to stop asking questions.                         │
│     System prompt says "conduct a session" but no termination criteria.     │
│                                                                              │
│     Need: Either                                                             │
│     a) Backend-driven: get_next_item tool returns "no more items"           │
│     b) LLM-driven: System prompt includes "stop after N questions"          │
│     c) Config-driven: session.config.max_items checked by backend           │
│                                                                              │
│  5. ITEM CONTENT SOURCE                                                      │
│     ────────────────────                                                     │
│     Currently LLM generates questions dynamically (unpredictable).          │
│                                                                              │
│     For Phase 1 (static items):                                              │
│     Need: Predefined question bank that agent retrieves via tool.           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. System Prompts Analysis

### 5.1 Current LEARNING_SESSION_PROMPT

```python
LEARNING_SESSION_PROMPT = """You are an educational AI tutor conducting a personalized learning session.

Your role:
- Guide the student through learning material step by step
- Present concepts clearly before assessing understanding
- Use multiple choice questions to check comprehension
- Use free text prompts for explanations and deeper thinking
- Use code editors for programming exercises
- Provide encouraging, constructive feedback on responses
- Adapt difficulty based on student performance

Session Guidelines:
- Start by introducing the topic and learning objectives
- Present content in digestible chunks
- After explaining a concept, assess understanding with a question
- Celebrate correct answers and gently correct mistakes
- Summarize key takeaways at the end

Available widgets:
- present_choices: For multiple choice questions (2-6 options)
- request_free_text: For written responses and explanations
- present_code_editor: For coding exercises

Always explain WHY an answer is correct or incorrect to reinforce learning."""
```

### 5.2 Problems with Current Prompt

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROMPT ISSUES                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ❌ NO ITERATION INSTRUCTION                                                 │
│     The prompt doesn't tell the LLM to keep presenting questions.           │
│     It says "guide step by step" but no explicit loop/continuation.         │
│                                                                              │
│  ❌ NO TERMINATION CRITERIA                                                  │
│     When should the session end? After 5 questions? 10? User says stop?     │
│     LLM has no guidance on this.                                            │
│                                                                              │
│  ❌ NO TOOL FOR GETTING NEXT ITEM                                            │
│     LLM generates questions from its training data.                         │
│     No mechanism to fetch predefined questions.                             │
│                                                                              │
│  ❌ NO CONTEXT ABOUT PREVIOUS ITEMS                                          │
│     When agent is recreated, LLM doesn't know what was already asked.       │
│     Session info in prompt: "Items Completed: N" but no details.            │
│                                                                              │
│  ❌ NO RESPONSE EVALUATION TOOL                                              │
│     LLM is told to "celebrate correct answers" but has no way to know       │
│     what's correct for predefined questions.                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Client Tools Analysis

### 6.1 Current Client Tools

```python
# From application/agents/client_tools.py

PRESENT_CHOICES_TOOL = ClientToolDefinition(
    name="present_choices",
    description="""Present a multiple choice question to the user with 2-6 options.
The user will select exactly one option. Use this when you need the user to
choose between discrete alternatives. Each option should be clear and distinct.""",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The question or prompt"},
            "options": {"type": "array", "items": {"type": "string"}},
            "context": {"type": "string", "description": "Optional context"},
        },
        "required": ["prompt", "options"],
    },
    widget_type=WidgetType.MULTIPLE_CHOICE,
)

REQUEST_FREE_TEXT_TOOL = ClientToolDefinition(
    name="request_free_text",
    description="""Request free-form text input from the user...""",
    ...
)

PRESENT_CODE_EDITOR_TOOL = ClientToolDefinition(
    name="present_code_editor",
    description="""Present a code editor for the user to write code...""",
    ...
)
```

### 6.2 Missing Tools for Session Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TOOLS NEEDED FOR SESSION FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. get_next_item (Backend Tool - NOT Client Tool)                          │
│     ─────────────────────────────────────────────                            │
│     Purpose: Retrieve the next question/item from the session curriculum    │
│                                                                              │
│     Input:  (none - backend knows session context)                          │
│     Output: {                                                                │
│       "item_index": 2,                                                      │
│       "total_items": 5,                                                     │
│       "question": "What is the capital of France?",                         │
│       "type": "multiple_choice",                                            │
│       "options": ["London", "Paris", "Berlin", "Madrid"],                   │
│       "has_more": true                                                      │
│     }                                                                        │
│                                                                              │
│     When called: LLM then uses present_choices with this data               │
│                                                                              │
│  2. evaluate_response (Backend Tool - NOT Client Tool)                      │
│     ──────────────────────────────────────────────────                       │
│     Purpose: Check if user's answer is correct against stored solution      │
│                                                                              │
│     Input:  { "item_index": 2, "user_answer": "Paris" }                     │
│     Output: {                                                                │
│       "correct": true,                                                      │
│       "feedback": "Correct! Paris is the capital of France.",               │
│       "explanation": "Paris became the capital in..."                       │
│     }                                                                        │
│                                                                              │
│     When called: After user responds, LLM evaluates and gives feedback      │
│                                                                              │
│  3. complete_session (Backend Tool - NOT Client Tool)                       │
│     ─────────────────────────────────────────────────                        │
│     Purpose: Signal that session should end                                 │
│                                                                              │
│     Input:  { "reason": "all_items_completed" }                             │
│     Output: { "success": true, "summary": {...} }                           │
│                                                                              │
│     When called: After last item or when LLM decides to end                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Data Flow: Where Things Break

### 7.1 Message Flow (Current - Broken)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CURRENT MESSAGE FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Agent Start:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ messages = [                                                         │    │
│  │   LlmMessage.system("You are a learning tutor...")  ◄── Built fresh │    │
│  │   LlmMessage.user("Start a learning session")       ◄── Hardcoded   │    │
│  │ ]                                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  LLM Call #1:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ messages.append(                                                     │    │
│  │   LlmMessage.assistant("", tool_calls=[present_choices(...)])        │    │
│  │ )                                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  Agent Suspends:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ _suspended_state.messages = [system, user, assistant]  ◄── IN MEMORY│    │
│  │                                                          ONLY!      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  User Responds (POST /respond):                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Session.submit_response({selection: "4"})                            │    │
│  │ Session.items = [{agent_prompt, client_action, user_response}]       │    │
│  │                                                                      │    │
│  │ ⚠️ Agent NOT involved                                                │    │
│  │ ⚠️ No LlmMessage.tool_result added                                   │    │
│  │ ⚠️ No continuation of agent loop                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  Frontend Reconnects to /stream:                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ NEW Agent created                                                    │    │
│  │ messages = [                                                         │    │
│  │   LlmMessage.system("You are a learning tutor...")  ◄── Fresh       │    │
│  │   LlmMessage.user("Start a learning session")       ◄── Same msg    │    │
│  │ ]                                                                    │    │
│  │                                                                      │    │
│  │ ⚠️ Previous Q&A LOST                                                 │    │
│  │ ⚠️ LLM has no context of what was asked                              │    │
│  │ ⚠️ LLM doesn't know user answered "4" to "What is 2+2?"              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Where Conversation Aggregate Should Fit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INTENDED MESSAGE FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Agent Start:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ // Check if conversation has existing messages                       │    │
│  │ conversation = await conversation_repo.get(session.conversation_id)  │    │
│  │                                                                      │    │
│  │ if conversation.messages.length > 0:                                 │    │
│  │   messages = conversation.messages  // Resume from stored            │    │
│  │ else:                                                                │    │
│  │   messages = [system_prompt, initial_user_message]  // Fresh start  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  After Each LLM Call:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ // Persist assistant message                                         │    │
│  │ conversation.add_message(assistant_message)                          │    │
│  │ await conversation_repo.update(conversation)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  After User Response:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ // Persist tool result message                                       │    │
│  │ tool_result = LlmMessage.tool_result(tool_call_id, response)         │    │
│  │ conversation.add_message(tool_result)                                │    │
│  │ await conversation_repo.update(conversation)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  On Resume/Reconnect:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ // Reload full conversation context                                  │    │
│  │ conversation = await conversation_repo.get(session.conversation_id)  │    │
│  │ messages = conversation.messages                                     │    │
│  │                                                                      │    │
│  │ // Agent continues with full context                                 │    │
│  │ async for event in agent._continue_loop(context, messages, ...):    │    │
│  │   yield event                                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Summary: Current State vs Required State

### 8.1 Comparison Table

| Aspect | Current State | Required State |
|--------|--------------|----------------|
| **Message Persistence** | In-memory only, lost on agent destruction | Stored in Conversation aggregate |
| **Session Continuation** | Frontend must reconnect, loses context | Response triggers continuation with context |
| **Item Source** | LLM generates dynamically | Backend provides via `get_next_item` tool |
| **Response Evaluation** | LLM guesses | Backend evaluates via `evaluate_response` tool |
| **End Condition** | None (session just stops) | Backend signals "no more items" or config.max_items |
| **Context on Resume** | Empty (fresh agent) | Rebuilt from Conversation + Session |

### 8.2 Components to Build

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION ROADMAP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Backend-Driven Static Sessions                                     │
│  ────────────────────────────────────────                                    │
│                                                                              │
│  1. Session Curriculum Model                                                 │
│     - Add `curriculum: list[CurriculumItem]` to SessionConfig               │
│     - CurriculumItem: {question, type, options, correct_answer, ...}        │
│                                                                              │
│  2. Backend Tools (NOT client tools)                                         │
│     - get_next_item: Returns next curriculum item                           │
│     - evaluate_response: Checks answer against correct_answer               │
│     - complete_session: Signals end                                          │
│                                                                              │
│  3. Message Persistence                                                      │
│     - Save LLM messages to Conversation after each call                     │
│     - Include tool calls and tool results                                   │
│                                                                              │
│  4. Context Reconstruction                                                   │
│     - On /stream, load Conversation.messages                                │
│     - Detect if we're resuming mid-session                                  │
│                                                                              │
│  5. Updated System Prompt                                                    │
│     - Instruct LLM to call get_next_item for questions                      │
│     - Instruct LLM to call evaluate_response after user answers             │
│     - Instruct LLM to call complete_session when get_next_item returns none │
│                                                                              │
│  6. Continuation Flow                                                        │
│     - After user response, agent continues in same or new stream            │
│     - User response becomes tool_result in LLM context                      │
│                                                                              │
│  Phase 2: Hybrid LLM-Driven Sessions (Future)                                │
│  ────────────────────────────────────────────                                │
│                                                                              │
│  - LLM can generate questions when curriculum is exhausted                  │
│  - LLM adapts difficulty based on user performance                          │
│  - LLM decides when to end based on mastery signals                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Open Questions for Design Decision

### Q1: Continuation Mechanism

**After user submits response, how should the agent continue?**

```
Option A: Inline Streaming Response
──────────────────────────────────
POST /session/{id}/respond
  → Records response
  → Returns StreamingResponse that continues agent loop
  → Frontend receives SSE events inline

Pros: Single request, no reconnection
Cons: POST returning SSE is unconventional

Option B: Trigger + Reconnect
─────────────────────────────
POST /session/{id}/respond
  → Records response
  → Returns simple JSON
GET /session/{id}/stream
  → Loads Conversation.messages
  → Continues agent loop

Pros: RESTful, clear separation
Cons: Two requests, reconnection overhead

Option C: Hybrid - POST returns, stream continues
─────────────────────────────────────────────────
POST /session/{id}/respond
  → Records response
  → Returns JSON immediately
  → Backend triggers agent continuation
  → Existing SSE connection (kept alive with heartbeats) receives new events

Pros: Best UX, single stream
Cons: Complex state management, requires long-lived agent
```

### Q2: Message Storage Granularity

**When and what to persist to Conversation?**

```
Option A: Full Messages
───────────────────────
Store complete LlmMessage objects:
  - system prompt
  - user messages
  - assistant messages (with tool_calls)
  - tool results

Pros: Complete audit trail, easy reconstruction
Cons: Storage overhead, may include redundant system prompts

Option B: Delta Messages
────────────────────────
Store only new messages since last persist.
System prompt reconstructed on load.

Pros: Efficient storage
Cons: Complex reconstruction logic

Option C: Conversation Turns
────────────────────────────
Store semantic turns: [{agent_said, user_said, evaluation}]
Reconstruct LLM format on load.

Pros: Clean data model
Cons: Lossy (tool_call IDs lost)
```

### Q3: get_next_item Tool Behavior

**What should happen when there are no more items?**

```
Option A: Return "no_more" Signal
─────────────────────────────────
{
  "item": null,
  "has_more": false,
  "message": "All items completed"
}

LLM then calls complete_session based on this.

Option B: Throw/Error
─────────────────────
Tool returns error: "Curriculum exhausted"
System prompt tells LLM to complete session on this error.

Option C: Auto-Complete
───────────────────────
Backend automatically transitions session to COMPLETED
when get_next_item finds no more items.
LLM receives notification that session ended.
```

---

## 10. Use Case Analysis: Session Types Deep Dive

This section clarifies the distinct requirements of each session type, which drives architectural decisions.

### 10.1 Session Type Comparison Matrix

```
┌──────────────────┬───────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│                  │  THOUGHT  │  LEARNING   │ EVALUATION  │   SURVEY    │  WORKFLOW   │
│                  │ (Reactive)│ (Proactive) │ (Proactive) │ (Proactive) │ (Proactive) │
├──────────────────┼───────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Who Drives?      │ User      │ Agent       │ Agent       │ Agent       │ Agent       │
│ Content Source   │ None      │ Curriculum  │ Item Bank   │ Form Def    │ Process Def │
│ LLM Role         │ Partner   │ Tutor       │ Proctor     │ Interviewer │ Guide       │
│ Item Selection   │ N/A       │ Adaptive    │ Algorithmic │ Sequential  │ Rule-based  │
│ User Input       │ Free text │ Mixed       │ Widgets only│ Widgets only│ Mixed       │
│ Feedback         │ Immediate │ Immediate   │ Deferred    │ None        │ Contextual  │
│ Correct Answers  │ N/A       │ Yes (learn) │ Yes (score) │ No          │ Sometimes   │
│ Time Limits      │ No        │ Optional    │ Strict      │ Optional    │ Optional    │
│ Skip/Back        │ Yes       │ Configurable│ No          │ Configurable│ Configurable│
│ Validity Concern │ Low       │ Medium      │ HIGH        │ Low         │ Low         │
│ Context Needed   │ Full conv │ Summary     │ Minimal     │ Minimal     │ State only  │
└──────────────────┴───────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### 10.2 Detailed Use Case Breakdown

#### THOUGHT Session (Reactive)

**Purpose:** Open-ended exploration, brainstorming, reflection

**Characteristics:**

- User initiates and drives the conversation
- No predefined content or curriculum
- LLM acts as a Socratic partner
- Full conversation history matters for context

**LLM Usage:**

- Generates responses based on user input
- No tools needed (or optional helper tools)
- Context = full conversation history

**Content Model:**

- None - purely generative

**Example:**

```
User: "I'm thinking about changing careers..."
Agent: "What aspects of your current career feel unfulfilling?"
User: "The repetitive nature of the work..."
Agent: "When you imagine an ideal workday, what activities energize you?"
```

---

#### LEARNING Session (Proactive - Adaptive)

**Purpose:** Skill development, knowledge acquisition, practice

**Characteristics:**

- Agent guides through learning objectives
- Curriculum-based but adaptive
- Mix of explanation + assessment
- Immediate feedback on responses
- Tracks mastery/performance

**LLM Usage:**

- Personalizes content delivery
- Adapts difficulty based on performance
- Generates feedback and explanations
- May generate variations of items (for practice)

**Content Model:**

```python
@dataclass
class LearningCurriculum:
    """Defines learning objectives and content."""

    topic: str
    learning_objectives: list[str]

    # Content organized by skill/concept
    modules: list[LearningModule]

    # Adaptive parameters
    initial_difficulty: float = 0.5
    mastery_threshold: float = 0.8


@dataclass
class LearningModule:
    """A teachable concept with associated practice items."""

    concept_id: str
    concept_name: str
    explanation_template: str  # LLM can personalize

    # Practice items (templates, not exact questions)
    item_templates: list[ItemTemplate]

    # Progression rules
    prerequisite_concepts: list[str]
    mastery_items_required: int = 3


@dataclass
class ItemTemplate:
    """Template for generating practice items."""

    skill_tag: str  # e.g., "two_digit_addition"
    item_type: str  # "multiple_choice", "free_text", etc.
    difficulty: float

    # Template (LLM generates specific instance)
    template: str  # "Add two {difficulty}-digit numbers"

    # For evaluation
    evaluation_criteria: str  # "Check if sum is correct"
```

**LLM's Role in Learning:**

```
System: "You are teaching {topic}. Current concept: {concept_name}.
        Student performance: {performance_summary}.

        Based on their level, either:
        1. Explain the concept (if new or struggling)
        2. Generate a practice item using template: {item_template}
        3. Provide feedback on their last response

        Call get_learning_context() to see what to do next."

Tool: get_learning_context()
Returns: {
    "action": "present_item",
    "concept": "two_digit_addition",
    "template": "Add two 2-digit numbers",
    "difficulty": 0.5,
    "student_mastery": 0.4
}

LLM generates: "What is 34 + 27?" (using present_choices or free_text)
```

---

#### EVALUATION Session (Proactive - Algorithmic)

**Purpose:** Competency assessment, certification, testing

**Characteristics:**

- HIGH stakes: Validity, Reliability, Fairness are critical
- Strictly controlled item presentation
- NO hints, NO immediate feedback
- Time limits enforced
- Items selected algorithmically (not by LLM discretion)
- Results used for scoring/certification

**Why This Is Complex:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PSYCHOMETRIC REQUIREMENTS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  VALIDITY: Does the assessment measure what it claims to measure?            │
│  ─────────                                                                   │
│  - Content validity: Items must cover the right domain                      │
│  - Construct validity: Correct answers should correlate with actual skill   │
│  - LLM generating random questions = LOW validity                           │
│  - Pre-validated item bank = HIGH validity                                  │
│                                                                              │
│  RELIABILITY: Would the same person get the same score again?               │
│  ───────────                                                                 │
│  - Items must have known difficulty parameters                              │
│  - Scoring must be consistent and deterministic                             │
│  - LLM subjective evaluation = LOW reliability                              │
│  - Pre-calibrated items with known parameters = HIGH reliability            │
│                                                                              │
│  FAIRNESS: Do all test-takers have equal opportunity?                       │
│  ────────                                                                    │
│  - No advantage from item exposure                                          │
│  - Equivalent difficulty across forms                                       │
│  - LLM must NOT leak correct answers                                        │
│  - Item selection must be defensible                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Content Model:**

```python
@dataclass
class EvaluationBlueprint:
    """Defines the assessment structure (test specification)."""

    assessment_id: str
    title: str

    # Structure
    sections: list[EvaluationSection]
    total_items: int
    time_limit_minutes: int

    # Selection rules
    item_selection_algorithm: str  # "fixed", "random_from_pool", "adaptive"


@dataclass
class EvaluationSection:
    """A section of the assessment."""

    section_id: str
    skill_domain: str
    item_count: int

    # Constraints
    difficulty_distribution: dict[str, int]  # {"easy": 2, "medium": 3, "hard": 1}


@dataclass
class EvaluationItem:
    """A pre-validated assessment item (from item bank)."""

    item_id: str
    skill_domain: str
    difficulty: float  # IRT difficulty parameter
    discrimination: float  # IRT discrimination parameter

    # Content (FIXED - LLM cannot modify)
    stem: str  # Question text
    item_type: str
    options: list[str] | None
    correct_answer: str | int

    # Metadata
    exposure_count: int  # For item exposure control
    last_used: datetime | None
```

**LLM's LIMITED Role in Evaluation:**

```
System: "You are proctoring an assessment. Your ONLY responsibilities:
        1. Call get_next_evaluation_item() to get the next item
        2. Present it using the EXACT wording provided (no modifications)
        3. Use present_choices() or present_code_editor() as specified
        4. Call record_evaluation_response() with the raw response
        5. Do NOT provide feedback, hints, or evaluate correctness
        6. Continue until get_next_evaluation_item() returns null

        NEVER modify item content. NEVER reveal correct answers."

Tool: get_next_evaluation_item()
Returns: {
    "item_id": "MATH-2D-ADD-042",
    "item_type": "multiple_choice",
    "stem": "What is 47 + 38?",
    "options": ["75", "85", "95", "105"],
    "present_using": "present_choices"
}

LLM: Calls present_choices(prompt="What is 47 + 38?", options=[...])
     # No creativity, no rephrasing - exact content only
```

**Key Insight:** For high-stakes evaluation, LLM is a **presentation layer**, not a content generator. The backend (Session Manager) controls:

- Which item comes next (algorithmic selection)
- What the correct answer is (never sent to LLM)
- Scoring (after session completes)

---

#### SURVEY Session (Proactive - Sequential)

**Purpose:** Data collection, feedback gathering, questionnaires

**Characteristics:**

- Fixed set of questions in order
- No correct answers
- All responses are valid data
- May have branching logic (skip patterns)
- LLM just presents questions politely

**Content Model:**

```python
@dataclass
class SurveyDefinition:
    """Defines a survey/questionnaire."""

    survey_id: str
    title: str
    questions: list[SurveyQuestion]

    # Branching rules
    skip_logic: dict[str, SkipRule] | None


@dataclass
class SurveyQuestion:
    """A survey question."""

    question_id: str
    text: str
    question_type: str  # "multiple_choice", "rating", "free_text", etc.
    options: list[str] | None
    required: bool = True
```

**LLM's Role:** Minimal - present questions verbatim, handle skip logic, thank user.

---

### 10.3 The LLM's Role Spectrum

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM ROLE BY SESSION TYPE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GENERATIVE ◄──────────────────────────────────────────────► PRESENTATIONAL │
│                                                                              │
│  THOUGHT        LEARNING         WORKFLOW       SURVEY      EVALUATION      │
│    │               │                │              │             │           │
│    ▼               ▼                ▼              ▼             ▼           │
│  ┌─────┐      ┌─────────┐      ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│  │100% │      │  70%    │      │  30%    │   │  10%    │   │   0%    │      │
│  │LLM  │      │ LLM +   │      │ Rules + │   │ Script +│   │ Script  │      │
│  │     │      │ Content │      │ LLM     │   │ Polish  │   │  Only   │      │
│  └─────┘      └─────────┘      └─────────┘   └─────────┘   └─────────┘      │
│                                                                              │
│  LLM decides   LLM adapts       LLM guides    LLM presents  LLM presents    │
│  everything    content          process       verbatim      verbatim        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.4 Context Requirements by Session Type

Your question about ConversationContext is excellent. Different session types need different context:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTEXT REQUIREMENTS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  THOUGHT Session:                                                            │
│  ────────────────                                                            │
│  Context needed: FULL conversation history                                   │
│  Why: LLM needs to remember everything discussed                            │
│  Challenge: Long conversations hit token limits                             │
│  Solution: Sliding window + summary of older content                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ messages = [                                                      │       │
│  │   system_prompt,                                                  │       │
│  │   summary_of_first_20_turns,  # LLM-generated summary            │       │
│  │   ...last_10_turns...         # Recent messages verbatim         │       │
│  │ ]                                                                 │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  LEARNING Session:                                                           │
│  ─────────────────                                                           │
│  Context needed: Performance summary + current state                        │
│  Why: LLM needs to know skill levels, not full dialogue                     │
│  Solution: Structured context object (not full messages)                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ context = {                                                       │       │
│  │   "current_module": "algebra_basics",                            │       │
│  │   "concept": "two_digit_addition",                               │       │
│  │   "mastery_scores": {"addition": 0.7, "subtraction": 0.4},       │       │
│  │   "items_completed": 5,                                          │       │
│  │   "recent_performance": [true, true, false, true, true],         │       │
│  │   "last_response": {"item": "34+27", "answer": "61", "correct": T}│       │
│  │ }                                                                 │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  EVALUATION Session:                                                         │
│  ───────────────────                                                         │
│  Context needed: MINIMAL (just what item to present next)                   │
│  Why: LLM should NOT know previous answers or performance                   │
│  Solution: Backend manages state, LLM is stateless per item                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ context = {                                                       │       │
│  │   "session_id": "...",                                           │       │
│  │   "items_remaining": 15,                                         │       │
│  │   "time_remaining_seconds": 1200                                 │       │
│  │   // NO performance data, NO previous responses                  │       │
│  │ }                                                                 │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  SURVEY Session:                                                             │
│  ───────────────                                                             │
│  Context needed: Current position + skip logic state                        │
│  Why: Just need to know which question is next                              │
│  Solution: Simple cursor/position tracking                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ context = {                                                       │       │
│  │   "current_question_index": 5,                                   │       │
│  │   "total_questions": 20,                                         │       │
│  │   "skipped_questions": [3]  // Due to skip logic                 │       │
│  │ }                                                                 │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.5 Proposed Architecture: SessionContext Projection

Your idea about a **ConversationContext aggregate** is on the right track. Here's a refined approach:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SESSION CONTEXT ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Event Store (Source of Truth)                                               │
│  ─────────────────────────────                                               │
│  │                                                                           │
│  │  SessionCreatedEvent                                                      │
│  │  SessionStartedEvent                                                      │
│  │  ItemPresentedEvent {item_id, content, timestamp}                        │
│  │  ResponseReceivedEvent {item_id, response, timestamp}                    │
│  │  ItemEvaluatedEvent {item_id, correct, feedback}  // Learning only       │
│  │  ...                                                                      │
│  │                                                                           │
│  ▼                                                                           │
│                                                                              │
│  Session Context Projector (Event Handler)                                   │
│  ─────────────────────────────────────────                                   │
│  │                                                                           │
│  │  Listens to session events                                               │
│  │  Builds session-type-specific context                                    │
│  │  Updates on each event                                                   │
│  │                                                                           │
│  ▼                                                                           │
│                                                                              │
│  SessionContext (Read Model - MongoDB)                                       │
│  ─────────────────────────────────────                                       │
│  │                                                                           │
│  │  {                                                                        │
│  │    session_id: "...",                                                    │
│  │    session_type: "learning",                                             │
│  │                                                                           │
│  │    // Type-specific context                                              │
│  │    learning_context: {                                                   │
│  │      current_module: "...",                                              │
│  │      mastery_scores: {...},                                              │
│  │      items_attempted: 5,                                                 │
│  │      recent_streak: 3,                                                   │
│  │      ...                                                                  │
│  │    },                                                                     │
│  │                                                                           │
│  │    // LLM-friendly summary (for sessions that need it)                   │
│  │    conversation_summary: "Student is learning algebra...",               │
│  │                                                                           │
│  │    // Last updated                                                       │
│  │    version: 42,                                                          │
│  │    updated_at: "..."                                                     │
│  │  }                                                                        │
│  │                                                                           │
│  ▼                                                                           │
│                                                                              │
│  Agent (on each iteration)                                                   │
│  ─────────────────────────                                                   │
│  │                                                                           │
│  │  1. Fetch SessionContext for session_id                                  │
│  │  2. Build system prompt with context                                     │
│  │  3. Call LLM with minimal messages                                       │
│  │                                                                           │
│  │  messages = [                                                             │
│  │    system_prompt_with_context,  // Includes SessionContext               │
│  │    user_instruction,            // "Continue the session"                │
│  │  ]                                                                        │
│  │                                                                           │
│  └───────────────────────────────────────────────────────────────────────── │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**

1. **Deterministic reconstruction** - Context rebuilt from events
2. **Session-type specific** - Different projections for different needs
3. **Bounded context size** - Summary instead of full history
4. **LLM-assisted summarization** - For Thought sessions, LLM can summarize periodically

---

### 10.6 Recommended Implementation Phases

Given the complexity, here's a phased approach:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PHASES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: Evaluation Session (Simplest Proactive)                           │
│  ────────────────────────────────────────────────                            │
│  Why start here:                                                             │
│  - LLM role is minimal (just presentation)                                  │
│  - Backend fully controls flow                                              │
│  - Establishes session infrastructure                                       │
│  - Clear success criteria                                                   │
│                                                                              │
│  Deliverables:                                                               │
│  - Static item bank (hardcoded or JSON)                                     │
│  - get_next_evaluation_item() tool                                          │
│  - record_evaluation_response() tool                                        │
│  - Session flow: create → stream → items → complete                         │
│  - Frontend widget rendering                                                │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PHASE 2: Survey Session                                                     │
│  ───────────────────────                                                     │
│  Why next:                                                                   │
│  - Similar to Evaluation but simpler (no scoring)                           │
│  - Introduces skip logic                                                    │
│  - Tests branching in session flow                                          │
│                                                                              │
│  Deliverables:                                                               │
│  - Survey definition model                                                  │
│  - Skip logic engine                                                        │
│  - get_next_survey_question() tool                                          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PHASE 3: Learning Session                                                   │
│  ─────────────────────────                                                   │
│  Why third:                                                                  │
│  - Introduces LLM adaptation                                                │
│  - Needs SessionContext projection                                          │
│  - Performance tracking                                                     │
│                                                                              │
│  Deliverables:                                                               │
│  - Curriculum model                                                         │
│  - LearningContext projection                                               │
│  - Adaptive item selection                                                  │
│  - LLM-generated item variations                                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PHASE 4: Thought Session Enhancement                                        │
│  ────────────────────────────────────                                        │
│  Why last:                                                                   │
│  - Most complex context management                                          │
│  - Needs conversation summarization                                         │
│  - Can leverage learnings from other phases                                 │
│                                                                              │
│  Deliverables:                                                               │
│  - Conversation summarization (LLM-assisted)                                │
│  - Sliding window + summary context                                         │
│  - Long conversation support                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Design Decisions (Updated)

Based on our discussion, here are the consolidated decisions:

### D1: SSE Connection Lifecycle

**Decision:** Close SSE after suspension, reconnect on resume

```
Rationale:
- Clean separation between "agent working" and "user thinking"
- No resource waste during user interaction
- Simple reconnection on POST /respond completion
- Separate channel (future) for session control messages if needed

Flow:
1. GET /stream → Agent runs → CLIENT_ACTION → SSE closes
2. User interacts with widget (no SSE)
3. POST /respond → Records response → Returns JSON
4. GET /stream → Agent continues → Repeat
```

### D2: Context Management

**Decision:** Session-type-specific context projections

```
Rationale:
- Different session types need different context
- Evaluation needs minimal context (security)
- Learning needs performance summaries
- Thought needs conversation summaries
- One-size-fits-all doesn't work

Implementation:
- SessionContext read model (projected from events)
- Type-specific context schemas
- LLM-assisted summarization for Thought sessions
```

### D3: LLM Role

**Decision:** Backend-driven item selection for proactive sessions

```
Rationale:
- Evaluation: LLM is presentation only (validity/reliability)
- Learning: Backend selects item template, LLM generates instance
- Survey: LLM is presentation only
- Thought: LLM drives (existing behavior)

This means:
- get_next_item() returns backend's selection
- LLM cannot skip or modify items in Evaluation
- LLM can personalize presentation in Learning
```

### D4: Curriculum/Content Source

**Decision:** Flexible - inline config OR reference to content service

```python
# Option A: Inline for simple cases
POST /session/
{
  "session_type": "evaluation",
  "config": {
    "items": [
      {"stem": "What is 2+2?", "options": [...], "correct": 1},
      ...
    ]
  }
}

# Option B: Reference for complex cases
POST /session/
{
  "session_type": "evaluation",
  "config": {
    "blueprint_id": "MATH-101-MIDTERM",
    "item_bank_id": "math-elementary"
  }
}
```

---

## 12. Next Steps

1. **Review use case analysis** - Confirm understanding of session types
2. **Prioritize Phase 1** - Start with Evaluation Session
3. **Design backend tools** - `get_next_evaluation_item()`, `record_evaluation_response()`
4. **Implement session flow** - Create → Stream → Items → Complete
5. **Build frontend widgets** - Start with `present_choices`

---

## 13. Blueprint-Driven Item Generation (Game Changer)

### 13.1 The Problem with Traditional Item Banks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRADITIONAL ITEM BANK PAIN POINTS                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COST OF CREATION                                                            │
│  ─────────────────                                                           │
│  - Subject Matter Experts (SMEs) write each item manually                   │
│  - Review cycles: content, bias, psychometric                               │
│  - Typical cost: $50-500 per validated item                                 │
│  - Time: weeks to months for a meaningful bank                              │
│                                                                              │
│  EXPOSURE RISK                                                               │
│  ─────────────                                                               │
│  - Once an item is seen, it can be shared                                   │
│  - "Item harvesting" degrades assessment validity                           │
│  - Must constantly refresh pool (more cost)                                 │
│  - High-stakes exams spend millions on item security                        │
│                                                                              │
│  SCALING CHALLENGE                                                           │
│  ─────────────────                                                           │
│  - New topic = new items to create                                          │
│  - Difficulty calibration requires pilot testing                            │
│  - Adaptive testing needs 5-10x more items than fixed-form                  │
│                                                                              │
│  LIMITED PERSONALIZATION                                                     │
│  ────────────────────────                                                    │
│  - Same items for everyone                                                  │
│  - Can't adapt to learner's context                                         │
│  - "One size fits all" questions                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 The Blueprint-Driven Generation Paradigm

**Core Insight:** For **procedural/deterministic domains**, we can separate:

- **WHAT to assess** (Blueprint) - human-authored, validated
- **HOW to present it** (Item Instance) - LLM-generated, infinite variations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BLUEPRINT → LLM → ITEM INSTANCE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BLUEPRINT (Human-Authored, Validated)                                       │
│  ─────────────────────────────────────                                       │
│  │                                                                           │
│  │  skill_id: "MATH.ARITH.ADD.2DIGIT"                                       │
│  │  skill_description: "Add two 2-digit integers"                           │
│  │  cognitive_level: "Apply"  (Bloom's taxonomy)                            │
│  │  domain: "Mathematics > Arithmetic > Addition"                           │
│  │                                                                           │
│  │  constraints:                                                             │
│  │    operand_1: {min: 10, max: 99, type: "integer"}                        │
│  │    operand_2: {min: 10, max: 99, type: "integer"}                        │
│  │    operation: "addition"                                                  │
│  │    difficulty_factors:                                                    │
│  │      - "no_carry": 0.3                                                   │
│  │      - "single_carry": 0.5                                               │
│  │      - "double_carry": 0.7                                               │
│  │                                                                           │
│  │  presentation:                                                            │
│  │    item_type: "multiple_choice"                                          │
│  │    distractor_strategy: "off_by_10", "off_by_1", "wrong_operation"       │
│  │    time_limit_seconds: 30                                                │
│  │                                                                           │
│  │  evaluation:                                                              │
│  │    method: "exact_match"  # Answer is computable!                        │
│  │    partial_credit: false                                                 │
│  │                                                                           │
│  ▼                                                                           │
│                                                                              │
│  LLM GENERATION (Controlled by Backend)                                      │
│  ──────────────────────────────────────                                      │
│  │                                                                           │
│  │  System: "Generate a math problem following these constraints..."        │
│  │                                                                           │
│  │  LLM Output:                                                              │
│  │  {                                                                        │
│  │    "operand_1": 47,                                                      │
│  │    "operand_2": 38,                                                      │
│  │    "stem": "What is 47 + 38?",                                           │
│  │    "distractors": [75, 95, 76],  // Generated per strategy               │
│  │    "correct_answer": 85          // Computed, not guessed!               │
│  │  }                                                                        │
│  │                                                                           │
│  ▼                                                                           │
│                                                                              │
│  ITEM INSTANCE (Presented to User)                                           │
│  ─────────────────────────────────                                           │
│  │                                                                           │
│  │  {                                                                        │
│  │    "stem": "What is 47 + 38?",                                           │
│  │    "options": ["75", "76", "85", "95"],  // Shuffled                     │
│  │    "correct_index": 2,  // Backend knows, never sent to LLM context      │
│  │    "time_limit": 30,                                                     │
│  │    "blueprint_id": "MATH.ARITH.ADD.2DIGIT",                              │
│  │    "difficulty_actual": 0.52  // Computed from carry analysis            │
│  │  }                                                                        │
│  │                                                                           │
│  └───────────────────────────────────────────────────────────────────────── │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.3 Why This Works for Certain Domains

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOMAIN SUITABILITY ANALYSIS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ✅ EXCELLENT FIT: Procedural/Deterministic Domains                          │
│  ──────────────────────────────────────────────────                          │
│                                                                              │
│  MATHEMATICS                                                                 │
│  • Arithmetic: Addition, subtraction, multiplication, division              │
│  • Algebra: Equation solving, expression simplification                     │
│  • Geometry: Area/perimeter calculations, angle relationships               │
│  • Why: Answer is COMPUTABLE from inputs                                    │
│                                                                              │
│  PROGRAMMING                                                                 │
│  • Syntax: "Write a function that..." → EXECUTABLE                          │
│  • Algorithms: "Sort this array..." → VERIFIABLE OUTPUT                     │
│  • Debugging: "Find the bug in..." → TESTABLE                               │
│  • Why: Code can be RUN and OUTPUT VERIFIED                                 │
│                                                                              │
│  NETWORKING / SYSTEMS                                                        │
│  • IP Addressing: "What's the subnet for..." → COMPUTABLE                   │
│  • Routing: "Which path will packet take..." → DETERMINISTIC                │
│  • Troubleshooting: "Given these symptoms..." → RULE-BASED                  │
│  • Why: Network behavior follows DEFINED RULES                              │
│                                                                              │
│  LANGUAGE / GRAMMAR                                                          │
│  • Conjugation: "Conjugate 'être' in passé composé" → LOOKUP                │
│  • Syntax: "Identify the subject in..." → PARSEABLE                         │
│  • Why: Grammar rules are FORMAL                                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ⚠️ PARTIAL FIT: Semi-Structured Domains                                     │
│  ──────────────────────────────────────                                      │
│                                                                              │
│  READING COMPREHENSION                                                       │
│  • Can generate passages + questions                                        │
│  • But: Answer validity requires human review OR                            │
│         Constrained to factual recall (not inference)                       │
│                                                                              │
│  SCIENCE CONCEPTS                                                            │
│  • Factual: "What is the chemical symbol for..." → LOOKUP                   │
│  • Conceptual: "Explain why..." → NEEDS RUBRIC                              │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ❌ POOR FIT: Subjective/Creative Domains                                    │
│  ──────────────────────────────────────                                      │
│                                                                              │
│  • Essay writing → No single correct answer                                 │
│  • Art critique → Subjective evaluation                                     │
│  • Ethical reasoning → Multiple valid perspectives                          │
│                                                                              │
│  For these: Human-authored items OR LLM-as-judge (different architecture)   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.4 Architecture: Evaluation Engine with Blueprint-Driven Generation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EVALUATION ENGINE ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     ASSESSMENT BLUEPRINT                             │    │
│  │                                                                      │    │
│  │  assessment_id: "MATH-FUNDAMENTALS-L1"                              │    │
│  │  title: "Mathematics Fundamentals - Level 1"                        │    │
│  │  total_items: 20                                                    │    │
│  │  time_limit_minutes: 30                                             │    │
│  │                                                                      │    │
│  │  sections:                                                          │    │
│  │    - domain: "Addition"                                             │    │
│  │      item_count: 5                                                  │    │
│  │      skill_blueprints: ["ADD.1DIGIT", "ADD.2DIGIT", "ADD.3DIGIT"]  │    │
│  │      difficulty_distribution: {easy: 2, medium: 2, hard: 1}        │    │
│  │                                                                      │    │
│  │    - domain: "Subtraction"                                          │    │
│  │      item_count: 5                                                  │    │
│  │      skill_blueprints: ["SUB.1DIGIT", "SUB.2DIGIT", "SUB.BORROW"]  │    │
│  │      difficulty_distribution: {easy: 2, medium: 2, hard: 1}        │    │
│  │                                                                      │    │
│  │    - domain: "Multiplication"                                       │    │
│  │      item_count: 5                                                  │    │
│  │      ...                                                            │    │
│  │                                                                      │    │
│  │    - domain: "Division"                                             │    │
│  │      item_count: 5                                                  │    │
│  │      ...                                                            │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     SESSION ORCHESTRATOR                             │    │
│  │                                                                      │    │
│  │  1. Load Assessment Blueprint                                        │    │
│  │  2. Initialize Session State:                                        │    │
│  │     - items_plan: [blueprint_id, difficulty, domain] × 20           │    │
│  │     - items_presented: []                                           │    │
│  │     - items_responses: []                                           │    │
│  │     - current_index: 0                                              │    │
│  │                                                                      │    │
│  │  3. On get_next_item():                                              │    │
│  │     a. Get next blueprint from items_plan                           │    │
│  │     b. Call Item Generator with blueprint + difficulty              │    │
│  │     c. Store generated item (for scoring later)                     │    │
│  │     d. Return item to LLM (without correct answer!)                 │    │
│  │                                                                      │    │
│  │  4. On record_response():                                            │    │
│  │     a. Store user's answer                                          │    │
│  │     b. Compute correctness (backend, not LLM!)                      │    │
│  │     c. Update metrics (for adaptive selection if enabled)           │    │
│  │     d. Return "next" or "complete" signal                           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     ITEM GENERATOR SERVICE                           │    │
│  │                                                                      │    │
│  │  Input:                                                              │    │
│  │    blueprint_id: "MATH.ARITH.ADD.2DIGIT"                            │    │
│  │    target_difficulty: 0.5                                           │    │
│  │    presentation: "multiple_choice"                                  │    │
│  │                                                                      │    │
│  │  Process:                                                            │    │
│  │    1. Load Skill Blueprint (constraints, rules)                     │    │
│  │    2. Select parameters to achieve target difficulty                │    │
│  │       - difficulty 0.5 → "single_carry" scenario                   │    │
│  │    3. Generate operands within constraints                          │    │
│  │       - operand_1: random(10, 99) with carry constraint            │    │
│  │       - operand_2: computed to ensure single carry                 │    │
│  │    4. Compute correct answer (DETERMINISTIC)                        │    │
│  │       - answer = operand_1 + operand_2                             │    │
│  │    5. Generate distractors per strategy                             │    │
│  │       - off_by_10: answer ± 10                                     │    │
│  │       - off_by_1: answer ± 1                                       │    │
│  │       - wrong_op: operand_1 - operand_2 (if positive)              │    │
│  │    6. Format stem using LLM (optional personalization)              │    │
│  │                                                                      │    │
│  │  Output:                                                             │    │
│  │    {                                                                 │    │
│  │      item_id: "gen_abc123",                                         │    │
│  │      blueprint_id: "MATH.ARITH.ADD.2DIGIT",                         │    │
│  │      stem: "Calculate: 47 + 38 = ?",                                │    │
│  │      options: ["75", "85", "86", "95"],                             │    │
│  │      correct_index: 1,  // STORED, NOT SENT TO LLM                  │    │
│  │      correct_answer: 85,                                            │    │
│  │      difficulty_computed: 0.52,                                     │    │
│  │      generation_params: {op1: 47, op2: 38, carry: "single"}        │    │
│  │    }                                                                 │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     LLM (Presentation Layer)                         │    │
│  │                                                                      │    │
│  │  Receives:                                                           │    │
│  │    {                                                                 │    │
│  │      "action": "present_item",                                      │    │
│  │      "item_type": "multiple_choice",                                │    │
│  │      "stem": "Calculate: 47 + 38 = ?",                              │    │
│  │      "options": ["75", "85", "86", "95"],                           │    │
│  │      "item_number": 5,                                              │    │
│  │      "total_items": 20,                                             │    │
│  │      "time_remaining_seconds": 1500                                 │    │
│  │      // NO correct_index!                                           │    │
│  │    }                                                                 │    │
│  │                                                                      │    │
│  │  LLM's Job:                                                          │    │
│  │    - Call present_choices(prompt=stem, options=options)             │    │
│  │    - Optionally add encouraging context                             │    │
│  │    - Handle UI concerns (time warnings, etc.)                       │    │
│  │                                                                      │    │
│  │  LLM CANNOT:                                                         │    │
│  │    - Know the correct answer                                        │    │
│  │    - Skip or reorder items                                          │    │
│  │    - Generate different questions                                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.5 Skill Blueprint Examples

```python
# Example Skill Blueprints for Different Domains

# ═══════════════════════════════════════════════════════════════════════════
# MATHEMATICS
# ═══════════════════════════════════════════════════════════════════════════

MATH_ADD_2DIGIT = SkillBlueprint(
    skill_id="MATH.ARITH.ADD.2DIGIT",
    domain="Mathematics > Arithmetic > Addition",
    skill_statement="Accurately add two 2-digit positive integers",
    cognitive_level="Apply",

    # Generation constraints
    generation_rules={
        "operand_count": 2,
        "operand_range": {"min": 10, "max": 99},
        "operation": "addition",
        "answer_type": "integer",
    },

    # Difficulty factors (used to compute actual difficulty)
    difficulty_factors={
        "no_carry": {"weight": 0.3, "constraint": "sum of ones < 10 AND sum of tens < 10"},
        "single_carry": {"weight": 0.5, "constraint": "exactly one carry"},
        "double_carry": {"weight": 0.7, "constraint": "carry in ones AND tens"},
    },

    # Presentation
    presentation={
        "item_type": "multiple_choice",
        "option_count": 4,
        "distractor_strategies": [
            {"type": "off_by_10", "description": "Common place value error"},
            {"type": "off_by_1", "description": "Careless error"},
            {"type": "wrong_operation", "description": "Subtraction instead"},
        ],
        "stem_templates": [
            "What is {op1} + {op2}?",
            "Calculate: {op1} + {op2} = ?",
            "Find the sum: {op1} + {op2}",
        ],
    },

    # Evaluation
    evaluation={
        "method": "exact_match",
        "compute_answer": "op1 + op2",  # Deterministic!
        "partial_credit": False,
    },

    # Performance expectations
    performance_benchmarks={
        "novice": {"accuracy": 0.6, "time_seconds": 30},
        "competent": {"accuracy": 0.85, "time_seconds": 15},
        "expert": {"accuracy": 0.98, "time_seconds": 5},
    },
)


# ═══════════════════════════════════════════════════════════════════════════
# PROGRAMMING
# ═══════════════════════════════════════════════════════════════════════════

PYTHON_STRING_LENGTH = SkillBlueprint(
    skill_id="PROG.PYTHON.STRING.LENGTH",
    domain="Programming > Python > Strings",
    skill_statement="Write Python code to count characters in a string",
    cognitive_level="Apply",

    generation_rules={
        "language": "python",
        "task_type": "function_implementation",
        "input_type": "string",
        "output_type": "integer",
        "test_cases_count": 3,
    },

    difficulty_factors={
        "basic": {"weight": 0.3, "constraint": "Simple ASCII string"},
        "with_spaces": {"weight": 0.5, "constraint": "String with spaces"},
        "unicode": {"weight": 0.7, "constraint": "String with unicode chars"},
        "empty_edge": {"weight": 0.4, "constraint": "Include empty string test"},
    },

    presentation={
        "item_type": "code_editor",
        "language": "python",
        "starter_code": "def count_chars(s: str) -> int:\n    # Your code here\n    pass",
        "stem_templates": [
            "Write a function that returns the number of characters in a string.",
            "Implement count_chars() to return the length of the input string.",
        ],
    },

    evaluation={
        "method": "test_execution",  # Run code against test cases!
        "test_generator": "generate_string_test_cases",
        "timeout_seconds": 5,
        "partial_credit": True,  # Based on % of test cases passed
    },

    # Example generated test cases
    # (Backend generates, runs user code, checks output)
    example_tests=[
        {"input": "hello", "expected": 5},
        {"input": "hello world", "expected": 11},
        {"input": "", "expected": 0},
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# NETWORKING
# ═══════════════════════════════════════════════════════════════════════════

NETWORK_SUBNET_CALC = SkillBlueprint(
    skill_id="NET.IP.SUBNET.CALC",
    domain="Networking > IP Addressing > Subnetting",
    skill_statement="Calculate network address from IP and subnet mask",
    cognitive_level="Apply",

    generation_rules={
        "ip_version": "IPv4",
        "address_class": ["A", "B", "C"],  # Random selection
        "cidr_range": {"min": 8, "max": 30},
    },

    difficulty_factors={
        "classful": {"weight": 0.3, "constraint": "CIDR matches class boundary"},
        "simple_cidr": {"weight": 0.5, "constraint": "CIDR on byte boundary (8,16,24)"},
        "complex_cidr": {"weight": 0.7, "constraint": "CIDR not on byte boundary"},
    },

    presentation={
        "item_type": "multiple_choice",
        "option_count": 4,
        "distractor_strategies": [
            {"type": "broadcast_address", "description": "Broadcast instead of network"},
            {"type": "host_address", "description": "First host instead of network"},
            {"type": "wrong_mask_application", "description": "Common masking error"},
        ],
        "stem_templates": [
            "Given IP address {ip}/{cidr}, what is the network address?",
            "Calculate the network address for {ip} with subnet mask {mask}",
        ],
    },

    evaluation={
        "method": "exact_match",
        "compute_answer": "ip_and_mask(ip, cidr)",  # Deterministic!
    },
)
```

### 13.6 Performance Analytics & IRT Integration

Your mention of IRT is spot-on. Here's how it fits:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IRT-LITE INTEGRATION                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRADITIONAL IRT                                                             │
│  ───────────────                                                             │
│  - Requires pre-calibrated items (thousands of responses)                   │
│  - Item parameters: difficulty (b), discrimination (a), guessing (c)        │
│  - Expensive to develop, maintain                                           │
│                                                                              │
│  BLUEPRINT-DRIVEN IRT-LITE                                                   │
│  ─────────────────────────                                                   │
│  - Difficulty is COMPUTED from generation parameters, not calibrated        │
│  - Discrimination assumed from blueprint design                             │
│  - Continuously refined from response data                                  │
│                                                                              │
│  Example:                                                                    │
│  ─────────                                                                   │
│  Blueprint: MATH.ADD.2DIGIT                                                 │
│  Generated: 47 + 38 (single carry)                                          │
│                                                                              │
│  Computed Difficulty:                                                        │
│    base_difficulty = 0.4 (2-digit addition)                                 │
│    + carry_factor = 0.15 (single carry)                                     │
│    + large_numbers = 0.05 (both > 30)                                       │
│    ─────────────────────────────────                                        │
│    estimated_difficulty = 0.60                                              │
│                                                                              │
│  After Response:                                                             │
│    user_answer: "85" (correct)                                              │
│    response_time: 8 seconds                                                 │
│    benchmark: competent = 15 seconds                                        │
│                                                                              │
│  Inference:                                                                  │
│    - Correct AND fast → ability > difficulty                                │
│    - Ability estimate increases                                             │
│    - Next item: select higher difficulty blueprint                          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  SESSION CONTEXT (Updated After Each Item)                                   │
│  ─────────────────────────────────────────                                   │
│                                                                              │
│  {                                                                           │
│    "session_id": "...",                                                     │
│    "items_completed": 5,                                                    │
│                                                                              │
│    "performance_by_domain": {                                               │
│      "addition": {                                                          │
│        "items_attempted": 2,                                                │
│        "items_correct": 2,                                                  │
│        "accuracy": 1.0,                                                     │
│        "avg_time_seconds": 7.5,                                             │
│        "estimated_ability": 0.72  // Updated via IRT-lite                  │
│      },                                                                      │
│      "subtraction": {                                                       │
│        "items_attempted": 2,                                                │
│        "items_correct": 1,                                                  │
│        "accuracy": 0.5,                                                     │
│        "avg_time_seconds": 22.0,                                            │
│        "estimated_ability": 0.38                                            │
│      }                                                                       │
│    },                                                                        │
│                                                                              │
│    "overall_ability_estimate": 0.55,                                        │
│                                                                              │
│    // For adaptive item selection                                           │
│    "next_item_recommendation": {                                            │
│      "domain": "subtraction",  // Weakest area                             │
│      "target_difficulty": 0.40,  // Slightly below ability                 │
│      "rationale": "Reinforce struggling domain"                            │
│    }                                                                         │
│  }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.7 Why This Changes Everything

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALUE PROPOSITION                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BEFORE (Traditional Item Bank)                                              │
│  ──────────────────────────────                                              │
│                                                                              │
│  Cost: $50-500 per validated item                                           │
│  Time: Weeks per topic                                                      │
│  Scale: Fixed pool (exposure risk)                                          │
│  Personalization: None                                                      │
│  Maintenance: Constant refresh needed                                       │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  AFTER (Blueprint-Driven Generation)                                         │
│  ────────────────────────────────────                                        │
│                                                                              │
│  Cost: ~$5-20 per validated BLUEPRINT (covers infinite items)               │
│  Time: Hours per topic (skill definition, not items)                        │
│  Scale: Infinite variations (zero exposure risk!)                           │
│  Personalization: Context-aware presentation                                │
│  Maintenance: Blueprint refinement only                                     │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  EXAMPLE ROI                                                                 │
│  ───────────                                                                 │
│                                                                              │
│  Goal: Assess elementary math (K-5)                                         │
│                                                                              │
│  Traditional:                                                                │
│    - 50 items per skill × 100 skills = 5,000 items                         │
│    - At $100/item = $500,000                                                │
│    - Time: 6-12 months                                                      │
│    - Exposure: Items leak, need 20% refresh/year = $100k/year              │
│                                                                              │
│  Blueprint-Driven:                                                           │
│    - 100 blueprints × $15/blueprint = $1,500                                │
│    - Time: 2-4 weeks                                                        │
│    - Exposure: Zero risk (every item is unique)                             │
│    - Maintenance: Blueprint tuning only                                     │
│                                                                              │
│  SAVINGS: ~99% cost reduction, infinite scale                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.8 Validity & Reliability Considerations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PSYCHOMETRIC VALIDITY IN BLUEPRINT MODEL                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CONTENT VALIDITY                                                            │
│  ────────────────                                                            │
│  Question: Does the item measure what we claim?                             │
│                                                                              │
│  Traditional: SME reviews each item                                         │
│  Blueprint: SME validates the BLUEPRINT (skill definition + constraints)    │
│             All generated items are, by construction, valid instances       │
│                                                                              │
│  ✅ Validity is INHERITED from blueprint, not per-item                       │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  CONSTRUCT VALIDITY                                                          │
│  ──────────────────                                                          │
│  Question: Do correct answers correlate with actual skill?                  │
│                                                                              │
│  Traditional: Pilot testing, statistical analysis                           │
│  Blueprint: Skill hierarchy ensures construct alignment                     │
│             Performance data validates/refines difficulty factors           │
│                                                                              │
│  ⚠️ Requires monitoring and blueprint refinement over time                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  RELIABILITY                                                                 │
│  ───────────                                                                 │
│  Question: Would same person get same score on equivalent form?             │
│                                                                              │
│  Traditional: Carefully balanced parallel forms                             │
│  Blueprint: Generated items from same blueprint = parallel by construction  │
│             Difficulty is COMPUTED, so forms are comparable                │
│                                                                              │
│  ✅ Parallel forms are FREE (generate N versions)                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  FAIRNESS                                                                    │
│  ────────                                                                    │
│  Question: Equal opportunity for all test-takers?                           │
│                                                                              │
│  Traditional: Item bias review, DIF analysis                                │
│  Blueprint: Constraints prevent biased content                              │
│             Stem templates reviewed for inclusive language                  │
│             Numbers/contexts can be randomized to avoid cultural bias       │
│                                                                              │
│  ⚠️ Blueprint design must be intentionally inclusive                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Updated Phase 1 Recommendation

Given this insight, I recommend:

### Phase 1A: Blueprint-Driven Math Evaluation (Proof of Concept)

**Scope:**

- Single domain: 2-digit arithmetic (add, subtract)
- 3-5 skill blueprints
- Multiple choice only
- Backend-computed difficulty
- Simple session flow

**Deliverables:**

1. SkillBlueprint data model
2. ItemGenerator service (deterministic math)
3. Session orchestrator with get_next_item() tool
4. Response recording with correctness computation
5. Basic SessionContext tracking

**Success Criteria:**

- Can run a 10-item math quiz
- Every item is unique (generated on-the-fly)
- Correct answers are never exposed to LLM
- Scoring is 100% accurate

### Phase 1B: Programming Evaluation Extension

**Scope:**

- Python code challenges
- Executable test cases
- Partial credit based on tests passed

This proves the model works for **code execution** domains.

---

_Document updated: December 12, 2025_
_Status: Blueprint-driven generation concept validated, ready for Phase 1A implementation spec_
