# Proactive Session Flow Specification

**Status:** Final Design
**Last Updated:** December 2025
**Related:** [Blueprint Evaluation Design](./blueprint-evaluation-design.md)

---

## 1. Executive Summary

This document specifies the architecture for **proactive sessions** in agent-host - sessions where the AI agent drives the interaction (presenting questions, evaluating responses) rather than responding to user queries.

### Key Design Decisions

| Aspect | Decision |
|--------|----------|
| **SSE Lifecycle** | Close on suspension, reconnect on resume |
| **Message Storage** | Persist to Conversation aggregate |
| **Item Source** | Blueprint-driven generation (LLM generates from YAML blueprints) |
| **Answer Generation** | LLM generates both content AND correct answer |
| **Answer Storage** | Backend stores answer; compares on response submission |
| **LLM Visibility** | Proactive Agent CAN see answer (for Learning feedback) |
| **Browser Visibility** | Browser NEVER sees answer during session |
| **Phase 1 Domains** | Mathematics + Networking (deterministic, verifiable answers) |

---

## 2. Session Types

### 2.1 Comparison Matrix

```
┌──────────────────┬───────────┬─────────────┬─────────────┬─────────────┐
│                  │  THOUGHT  │  LEARNING   │ EVALUATION  │   SURVEY    │
│                  │ (Reactive)│ (Proactive) │ (Proactive) │ (Proactive) │
├──────────────────┼───────────┼─────────────┼─────────────┼─────────────┤
│ Who Drives?      │ User      │ Agent       │ Agent       │ Agent       │
│ Content Source   │ None      │ Blueprints  │ Blueprints  │ Form Def    │
│ LLM Role         │ Partner   │ Tutor       │ Proctor     │ Interviewer │
│ Item Generation  │ N/A       │ LLM+Backend │ LLM+Backend │ Sequential  │
│ User Input       │ Free text │ Mixed       │ Widgets only│ Widgets only│
│ Feedback         │ Immediate │ Immediate   │ Deferred    │ None        │
│ Correct Answers  │ N/A       │ Yes (learn) │ Yes (score) │ No          │
│ Skip/Back        │ Yes       │ Configurable│ No          │ Configurable│
└──────────────────┴───────────┴─────────────┴─────────────┴─────────────┘
```

### 2.2 LLM Role Spectrum

```
GENERATIVE ◄─────────────────────────────────────────────► PRESENTATIONAL

  THOUGHT        LEARNING         SURVEY           EVALUATION
    │               │                │                  │
    ▼               ▼                ▼                  ▼
  ┌─────┐      ┌─────────┐      ┌─────────┐       ┌─────────┐
  │100% │      │  70%    │      │  10%    │       │   5%    │
  │LLM  │      │ LLM +   │      │ Script +│       │ Script  │
  │     │      │Blueprint│      │ Polish  │       │  Only   │
  └─────┘      └─────────┘      └─────────┘       └─────────┘

  LLM decides   LLM generates    LLM presents     LLM presents
  everything    from blueprints  verbatim         verbatim
```

---

## 3. Architecture Overview

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  SessionView                                                                 │
│  ├── Renders widgets (MultipleChoice, FreeText, CodeEditor)                 │
│  ├── Handles widget interactions                                            │
│  ├── Connects to SSE stream                                                 │
│  └── Submits responses via POST /respond                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/SSE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  SessionController                                                           │
│  ├── POST /session/              → CreateSessionCommand                     │
│  ├── GET  /session/{id}/stream   → ProactiveAgent.start_session()           │
│  ├── POST /session/{id}/respond  → SubmitClientResponseCommand              │
│  └── POST /session/{id}/terminate → TerminateSessionCommand                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Mediator
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ProactiveAgent                     │  ItemGeneratorService                  │
│  ├── start_session()                │  ├── generate_from_blueprint()        │
│  ├── _proactive_loop()              │  └── compute_correct_answer()         │
│  └── resume_with_response()         │                                        │
│                                     │  SessionManager                        │
│  BackendTools                       │  ├── get_next_item()                   │
│  ├── get_next_item                  │  ├── record_response()                 │
│  └── complete_session               │  └── complete_session()                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Repository
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOMAIN LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Session (Aggregate)                │  Conversation (Aggregate)              │
│  ├── id, user_id                    │  ├── id, session_id                   │
│  ├── session_type                   │  ├── messages: List[LlmMessage]       │
│  ├── status                         │  └── add_message()                    │
│  ├── items: List[SessionItem]       │                                        │
│  ├── pending_action                 │  Blueprint (Entity)                    │
│  └── submit_response()              │  ├── skill_id, constraints             │
│                                     │  └── evaluation_method                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 SSE Stream Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PENDING   │────►│   ACTIVE    │────►│  AWAITING   │────►│  COMPLETED  │
│             │     │             │     │   CLIENT    │     │             │
│ (created)   │     │ (streaming) │     │   ACTION    │     │ (finished)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   No stream          SSE active          SSE closed         SSE closed
                      (events)           (user thinking)    (session done)
```

**Key Insight:** SSE stream closes when agent suspends (AWAITING_CLIENT_ACTION). Frontend reconnects after submitting response.

---

## 4. Session Flow Sequence

### 4.1 Complete Flow Diagram

```
Frontend                 Controller              Agent              Backend Tools         Domain
   │                         │                     │                      │                 │
   │ POST /session/          │                     │                      │                 │
   │────────────────────────►│                     │                      │                 │
   │                         │ CreateSessionCmd    │                      │                 │
   │                         │─────────────────────┼──────────────────────┼────────────────►│
   │                         │                     │                      │    Session      │
   │                         │                     │                      │    created      │
   │◄────────────────────────│                     │                      │                 │
   │ {session_id}            │                     │                      │                 │
   │                         │                     │                      │                 │
   │ GET /stream             │                     │                      │                 │
   │────────────────────────►│                     │                      │                 │
   │                         │ start_session()     │                      │                 │
   │                         │────────────────────►│                      │                 │
   │                         │                     │ get_next_item()      │                 │
   │                         │                     │─────────────────────►│                 │
   │                         │                     │                      │ Load blueprint  │
   │                         │                     │                      │ Generate item   │
   │                         │                     │                      │ Compute answer  │
   │                         │                     │◄─────────────────────│                 │
   │                         │                     │ {stem, options}      │                 │
   │                         │                     │ (NO correct_answer)  │                 │
   │                         │                     │                      │                 │
   │                         │                     │ LLM: present_choices │                 │
   │ SSE: client_action      │◄────────────────────│                      │                 │
   │◄────────────────────────│                     │                      │                 │
   │                         │ Agent suspends      │                      │                 │
   │ SSE: connection closes  │◄────────────────────│                      │                 │
   │◄────────────────────────│                     │                      │                 │
   │                         │                     │                      │                 │
   │ [User interacts with widget]                  │                      │                 │
   │                         │                     │                      │                 │
   │ POST /respond           │                     │                      │                 │
   │────────────────────────►│                     │                      │                 │
   │                         │ SubmitResponseCmd   │                      │                 │
   │                         │─────────────────────┼──────────────────────┼────────────────►│
   │                         │                     │                      │   Session.      │
   │                         │                     │                      │   submit_       │
   │                         │                     │                      │   response()    │
   │◄────────────────────────│                     │                      │                 │
   │ {ok}                    │                     │                      │                 │
   │                         │                     │                      │                 │
   │ GET /stream (reconnect) │                     │                      │                 │
   │────────────────────────►│                     │                      │                 │
   │                         │ resume_session()    │                      │                 │
   │                         │────────────────────►│                      │                 │
   │                         │                     │ Load Conversation    │                 │
   │                         │                     │ (rebuild context)    │                 │
   │                         │                     │                      │                 │
   │                         │                     │ record_response()    │                 │
   │                         │                     │─────────────────────►│                 │
   │                         │                     │                      │ Evaluate answer │
   │                         │                     │◄─────────────────────│                 │
   │                         │                     │ {correct, feedback}  │                 │
   │                         │                     │                      │                 │
   │                         │                     │ get_next_item()      │                 │
   │                         │                     │─────────────────────►│                 │
   │                         │                     │  ... cycle repeats   │                 │
   │                         │                     │                      │                 │
   │                         │                     │ (no more items)      │                 │
   │                         │                     │◄─────────────────────│                 │
   │                         │                     │                      │                 │
   │                         │                     │ complete_session()   │                 │
   │                         │                     │─────────────────────►│                 │
   │ SSE: session_completed  │◄────────────────────│                      │                 │
   │◄────────────────────────│                     │                      │                 │
   │                         │                     │                      │                 │
```

### 4.2 Message Persistence Strategy

When agent runs, messages are persisted to the Conversation aggregate:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION MESSAGES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  messages: [                                                                 │
│    {role: "system", content: "You are an assessment proctor..."},           │
│    {role: "user", content: "Begin the session"},                            │
│    {role: "assistant", content: "", tool_calls: [                           │
│      {id: "call_1", name: "get_next_item", arguments: "{}"}                 │
│    ]},                                                                       │
│    {role: "tool", tool_call_id: "call_1", content: "{item_data}"},          │
│    {role: "assistant", content: "", tool_calls: [                           │
│      {id: "call_2", name: "present_choices", arguments: "{...}"}            │
│    ]},                                                                       │
│    {role: "tool", tool_call_id: "call_2", content: "{user_response}"},      │
│    {role: "assistant", content: "", tool_calls: [                           │
│      {id: "call_3", name: "record_response", arguments: "{...}"}            │
│    ]},                                                                       │
│    ...                                                                       │
│  ]                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

On reconnect, agent loads messages from Conversation and continues.

---

## 5. Backend Tools

### 5.1 Tool Definitions

```python
# Tools executed by BACKEND (not client widgets)

GET_NEXT_ITEM_TOOL = BackendToolDefinition(
    name="get_next_item",
    description="""Get the next assessment item to present to the user.
Returns the item stem, options (for multiple choice), and presentation type.
Returns null when no more items remain (session should complete).""",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

RECORD_RESPONSE_TOOL = BackendToolDefinition(
    name="record_response",
    description="""Record the user's response to the current item.
Returns correctness (for learning sessions) or acknowledgment (for evaluation).
Must be called after receiving user input via client tool.""",
    parameters={
        "type": "object",
        "properties": {
            "user_response": {
                "type": "string",
                "description": "The user's response (selection index or text)"
            }
        },
        "required": ["user_response"],
    },
)

COMPLETE_SESSION_TOOL = BackendToolDefinition(
    name="complete_session",
    description="""Signal that the session should end.
Call when get_next_item returns null or when terminating early.""",
    parameters={
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": ["all_items_completed", "time_expired", "user_terminated"]
            }
        },
        "required": ["reason"],
    },
)
```

### 5.2 Client Tools (Existing)

```python
# Tools that trigger UI widgets (suspend agent)

PRESENT_CHOICES_TOOL      # Multiple choice widget
REQUEST_FREE_TEXT_TOOL    # Text input widget
PRESENT_CODE_EDITOR_TOOL  # Code editor widget
```

---

## 6. Context by Session Type

Different session types require different context for the LLM:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTEXT REQUIREMENTS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EVALUATION Session:                                                         │
│  ───────────────────                                                         │
│  Context needed: MINIMAL (just what item to present next)                   │
│  Why: LLM should NOT know previous answers or performance                   │
│                                                                              │
│  context = {                                                                 │
│    "session_id": "...",                                                     │
│    "item_number": 5,                                                        │
│    "total_items": 20,                                                       │
│    "time_remaining_seconds": 1200                                           │
│    // NO performance data, NO previous responses                            │
│  }                                                                           │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  LEARNING Session:                                                           │
│  ─────────────────                                                           │
│  Context needed: Performance summary + current state                        │
│  Why: LLM adapts difficulty, provides feedback                              │
│                                                                              │
│  context = {                                                                 │
│    "current_skill": "two_digit_addition",                                   │
│    "mastery_scores": {"addition": 0.7, "subtraction": 0.4},                 │
│    "items_completed": 5,                                                    │
│    "recent_performance": [true, true, false, true, true],                   │
│    "last_item_feedback": "Correct! The answer is 85."                       │
│  }                                                                           │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  THOUGHT Session (Reactive):                                                 │
│  ────────────────────────────                                                │
│  Context needed: FULL conversation history                                  │
│  Why: Open-ended dialogue requires memory                                   │
│                                                                              │
│  context = conversation.messages (with summarization for long sessions)     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. System Prompt Templates

### 7.1 Evaluation Session Prompt

```
You are an assessment proctor conducting a timed evaluation.

Your responsibilities:
1. Call get_next_item() to retrieve the next question
2. Present it using the EXACT wording provided (do not modify)
3. Use present_choices() for multiple choice items
4. After user responds, call record_response() with their answer
5. Continue until get_next_item() returns null
6. Then call complete_session(reason="all_items_completed")

CRITICAL RULES:
- NEVER reveal correct answers
- NEVER provide hints or feedback during the test
- NEVER skip or reorder items
- NEVER modify question wording

Session Info:
- Total Items: {total_items}
- Time Limit: {time_limit_minutes} minutes
```

### 7.2 Learning Session Prompt

```
You are an educational tutor helping a student learn {topic}.

Your responsibilities:
1. Call get_next_item() to get the next practice problem
2. Present it engagingly using appropriate widget
3. After user responds, call record_response() to check their answer
4. Provide encouraging feedback based on the response
5. Explain WHY the answer is correct or incorrect
6. Continue until get_next_item() returns null

Current Performance:
{performance_summary}

Adapt your approach:
- If struggling: Provide more explanation, easier items
- If excelling: Offer challenge, move faster
```

---

## 8. Implementation Notes

### 8.1 Agent Reconstruction on Reconnect

When frontend reconnects to `/stream`:

1. Load Session aggregate (status, items, pending_action)
2. Load Conversation aggregate (messages)
3. Create new ProactiveAgent instance
4. Inject conversation messages as context
5. Continue `_proactive_loop()` from current state

### 8.2 Answer Security Model

The security boundary is **browser ↔ server**, NOT **LLM ↔ backend**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ANSWER VISIBILITY MODEL                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ITEM GENERATION (by Item Generator LLM):                                    │
│  ─────────────────────────────────────────                                   │
│  LLM generates:                                                              │
│  {                                                                           │
│    "stem": "What is 47 + 38?",                                              │
│    "options": ["75", "85", "86", "95"],                                     │
│    "correct_answer": "85",           ◄── LLM GENERATES THIS                 │
│    "correct_index": 1,                                                      │
│    "explanation": "47+38=85..."      ◄── For feedback                       │
│  }                                                                           │
│                                                                              │
│  Backend STORES complete item (including answer) for:                        │
│  - Audit trail                                                              │
│  - Response verification                                                    │
│  - Analytics                                                                │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ITEM PRESENTATION (by Proactive Agent):                                     │
│  ──────────────────────────────────────────                                  │
│                                                                              │
│  EVALUATION MODE - Agent receives:                                           │
│  {                                                                           │
│    "stem": "What is 47 + 38?",                                              │
│    "options": ["75", "85", "86", "95"]                                      │
│    // No answer - proctor should not reveal                                 │
│  }                                                                           │
│                                                                              │
│  LEARNING MODE - Agent receives:                                             │
│  {                                                                           │
│    "stem": "What is 47 + 38?",                                              │
│    "options": ["75", "85", "86", "95"],                                     │
│    "correct_answer": "85",           ◄── Tutor CAN see this                 │
│    "explanation": "47+38=85..."      ◄── For providing feedback             │
│  }                                                                           │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  BROWSER (in ALL modes):                                                     │
│  ──────────────────────────                                                  │
│  {                                                                           │
│    "widget": "multiple_choice",                                             │
│    "prompt": "What is 47 + 38?",                                            │
│    "options": ["75", "85", "86", "95"]                                      │
│    // NEVER receives correct_answer, correct_index, or explanation          │
│  }                                                                           │
│                                                                              │
│  ✓ LLM is server-side - cannot be inspected by user                         │
│  ✓ System prompt instructs not to reveal (Evaluation)                       │
│  ✓ Client tools strip answer before sending to browser                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Generated Item Storage

All generated items are stored for:

- Audit trail (what was presented)
- Analytics (difficulty calibration)
- Reproducibility (debugging)

---

## 9. Related Documents

- [Blueprint Evaluation Design](./blueprint-evaluation-design.md) - Complete blueprint-driven generation architecture
- [Session Flow Archive](./session-flow-archive.md) - Historical analysis and design evolution
- Phase 1 Implementation: Math + Networking domains with YAML blueprints

---

_This document supersedes earlier exploratory analysis. For implementation details, see the Blueprint Evaluation Design document._
