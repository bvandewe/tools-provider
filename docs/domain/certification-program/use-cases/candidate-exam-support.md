# Use Case: Candidate Self-Service AI Support

> **Primary Actor:** Candidate
> **Supporting Actors:** AI Exam Support Assistant, Proctor (escalation)
> **Systems Involved:** LDS (exam-delivery-system), agent-host

## Overview

During exam sessions, candidates encounter legitimate questions about task wording, interface usage, and resource navigation. Currently, every clarification requires proctor intervention—creating delays and inconsistent responses. An AI assistant can provide immediate, standardized support for permitted clarifications while maintaining exam integrity.

## The Clarification Challenge

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE CLARIFICATION DILEMMA                                 │
│                                                                              │
│   ╔═══════════════════════════════════════════════════════════════════════╗ │
│   ║  Candidate needs help with...           Can AI assist?                ║ │
│   ╠═══════════════════════════════════════════════════════════════════════╣ │
│   ║                                                                       ║ │
│   ║  ✅ PERMITTED                                                         ║ │
│   ║  ──────────────                                                       ║ │
│   ║  • "Where do I find the network diagram?"       → Direct answer       ║ │
│   ║  • "What does 'implement' mean in Task 3?"      → Standard definition ║ │
│   ║  • "Is there a time limit per section?"         → Policy information  ║ │
│   ║  • "The console seems frozen, what do I do?"    → Troubleshooting     ║ │
│   ║  • "Can I go back to previous tasks?"           → Navigation help     ║ │
│   ║                                                                       ║ │
│   ║  ⚠️ NEEDS ESCALATION                                                  ║ │
│   ║  ────────────────────                                                 ║ │
│   ║  • "Is my approach correct?"                    → Cannot evaluate     ║ │
│   ║  • "This task seems ambiguous..."               → Content team review ║ │
│   ║  • "The expected output format is unclear"      → May need judgment   ║ │
│   ║                                                                       ║ │
│   ║  🚫 PROHIBITED                                                        ║ │
│   ║  ─────────────                                                        ║ │
│   ║  • "What command should I use?"                 → Exam content        ║ │
│   ║  • "Is OSPF or EIGRP better here?"              → Solution hint       ║ │
│   ║  • "What's the answer to Task 2?"               → Direct answer       ║ │
│   ║                                                                       ║ │
│   ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Current vs Future State

### Current: Proctor-Mediated

```
Candidate              LDS              Proctor              Response
    │                   │                  │                    │
    │  "Click Help"     │                  │                    │
    │──────────────────►│                  │                    │
    │                   │  Alert           │                    │
    │                   │─────────────────►│                    │
    │                   │                  │                    │
    │                   │      (Proctor reading, thinking...)   │
    │                   │                  │                    │
    │                   │      Wait 2-5 minutes...              │
    │                   │                  │                    │
    │                   │  Response        │                    │
    │◄──────────────────│◄─────────────────│                    │
    │                   │                  │                    │
    │   Time lost: 3+ minutes                                   │
    │   Consistency: Variable by proctor                        │
    │   Anxiety: Elevated                                       │
    │                                                           │
```

### Future: AI-First with Escalation

```
Candidate              LDS           AI Assistant          Proctor
    │                   │                 │                   │
    │  "Click Help"     │                 │                   │
    │──────────────────►│                 │                   │
    │                   │  Question       │                   │
    │                   │────────────────►│                   │
    │                   │                 │                   │
    │                   │  [Classify]     │                   │
    │                   │                 │                   │
    │                   │  ┌──────────────────────────────┐   │
    │                   │  │ IF permitted:                │   │
    │                   │  │   → Instant response         │   │
    │                   │  │ IF escalation needed:        │   │
    │                   │  │   → "Checking with proctor"  │   │
    │                   │  │   → Route to proctor         │   │
    │                   │  │ IF prohibited:               │   │
    │                   │  │   → Polite decline + guide   │   │
    │                   │  └──────────────────────────────┘   │
    │                   │                 │                   │
    │  Response         │                 │                   │
    │◄──────────────────│◄────────────────│                   │
    │                   │                 │                   │
    │   Time: 5-10 seconds (permitted)                        │
    │   Consistency: 100% standardized                        │
    │   Anxiety: Minimized                                    │
    │                                                         │
```

## AI Exam Support Assistant

```yaml
agent_id: 'exam-support-assistant'
name: 'Exam Support Assistant'
description: 'In-exam AI assistant for candidate clarifications and support'

system_prompt: |
  You are a helpful exam support assistant embedded in the certification exam
  delivery system. Your role is to help candidates with legitimate questions
  about exam navigation, interface usage, and permitted clarifications.

  ## Your Capabilities

  You CAN help with:
  - Explaining exam interface features and navigation
  - Clarifying task wording (definitions, not interpretations)
  - Locating resources (diagrams, documentation, exhibits)
  - Explaining time limits and exam policies
  - Basic technical troubleshooting (console, connectivity)
  - Confirming what tools/resources are available

  You CANNOT help with:
  - Any technical approach or methodology
  - Whether a solution is correct or complete
  - Hints about commands, configurations, or answers
  - Interpreting ambiguous requirements (escalate these)
  - Anything that would advantage one candidate over another

  ## Response Principles

  1. **Be direct**: Candidates are under time pressure
  2. **Be consistent**: Same question = same answer for all candidates
  3. **Be honest**: If you can't help, say so clearly and offer alternatives
  4. **Be calm**: Help reduce anxiety, not add to it
  5. **Be brief**: 2-3 sentences max for most responses

  ## Escalation

  When a question requires human judgment or touches exam content,
  respond with:
  "I'll check with the proctor on that. You'll see a response shortly.
  In the meantime, you can continue working on other parts."

  Then escalate to the proctor with context.

context:
  # The assistant knows about the exam structure (not content)
  exam_structure:
    modules: ['Design', 'Deploy']
    resources: ['topology_diagram', 'email_archive', 'documentation']
    tools: ['console_access', 'web_interface']

  # Standard clarifications pre-approved by content team
  permitted_clarifications:
    task_verbs:
      implement: "Configure the feature so it is operational"
      verify: "Confirm the feature works as expected"
      troubleshoot: "Identify and resolve the issue"
      document: "Record your findings in the provided location"

    interface_help:
      console: "Click the device name to open its console"
      topology: "The topology diagram is in the Resources panel on the right"
      email: "Check the Email tab in the Design module for scenario context"
      submit: "The Submit button appears when you're ready to complete a task"

tools:
  - exam.get_current_task     # What task candidate is on
  - exam.get_resources        # List available resources
  - exam.get_time_remaining   # Time status
  - exam.get_module_info      # Module structure info
  - support.log_interaction   # Log for audit trail
  - support.escalate_to_proctor  # Route to human

conversation_template_id: null  # Open-ended but bounded
access_control:
  allowed_roles: ['candidate']  # Only active candidates
  context_restrictions:
    - no_exam_content
    - no_answer_evaluation
    - time_limited_session
```

## Interaction Patterns

### Pattern 1: Navigation Help (Immediate Response)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 EXAM SUPPORT                                                            │
│                                                                              │
│  Candidate: Where can I find the network topology?                          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Assistant: The network topology diagram is in the Resources panel on       │
│  the right side of your screen. Click the "Topology" tab to view it.        │
│  You can also expand it to full screen using the button in the corner.      │
│                                                                              │
│  [Close] [Still Need Help]                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Definition Clarification (Immediate Response)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 EXAM SUPPORT                                                            │
│                                                                              │
│  Candidate: Task 4 says to "verify" connectivity. Does that mean            │
│  I need to fix it if it's broken, or just confirm current state?            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Assistant: "Verify" means confirm the feature works as expected.           │
│  If you find it's not working, that's useful information for the task.      │
│  Focus on confirming the current state rather than modifying it.            │
│                                                                              │
│  [Close] [Still Need Help]                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 3: Technical Issue (Troubleshoot + Escalate)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 EXAM SUPPORT                                                            │
│                                                                              │
│  Candidate: The console for R2 isn't responding. I've been waiting          │
│  for 2 minutes and nothing happens when I type.                             │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Assistant: I understand that's frustrating. Let me help:                   │
│                                                                              │
│  1. First, try pressing Enter a few times to wake the console               │
│  2. If that doesn't work, try closing and reopening the console tab         │
│                                                                              │
│  If it's still not responding, I'll alert the proctor who can               │
│  investigate further. Your exam timer can be paused if there's              │
│  a technical issue.                                                         │
│                                                                              │
│  [It's Working Now] [Still Not Working - Get Proctor]                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 4: Boundary Question (Polite Decline)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 EXAM SUPPORT                                                            │
│                                                                              │
│  Candidate: Is OSPF the right protocol to use for Task 3?                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Assistant: I can't provide guidance on technical approaches or             │
│  solution methods—that's part of what the exam is assessing.                │
│                                                                              │
│  What I can help with:                                                      │
│  • Clarifying what the task is asking you to do                             │
│  • Finding resources like topology diagrams or documentation                │
│  • Explaining interface features                                            │
│                                                                              │
│  Is there something else I can help you with?                               │
│                                                                              │
│  [No, Thanks] [Different Question]                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 5: Ambiguous Content (Escalate to Proctor)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 EXAM SUPPORT                                                            │
│                                                                              │
│  Candidate: Task 5 mentions "the remote site" but the topology shows        │
│  three remote sites. Which one is it referring to?                          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Assistant: That's a good question that needs human review. I'm             │
│  checking with the proctor now—you'll see a response in the next            │
│  few minutes.                                                               │
│                                                                              │
│  In the meantime, you can continue working on other tasks. This             │
│  won't count against your time unfairly.                                    │
│                                                                              │
│  ⏳ Waiting for proctor response...                                         │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍💼 Proctor (2 min later):                                                │
│  "The remote site" in Task 5 refers to the Branch-West site shown in        │
│  the lower-left of the topology. Thank you for flagging—we'll clarify       │
│  this in future versions.                                                   │
│                                                                              │
│  [Got It, Thanks]                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Classification Logic

```python
from enum import Enum
from dataclasses import dataclass

class QuestionCategory(Enum):
    NAVIGATION = "navigation"       # UI, where to find things
    DEFINITION = "definition"       # What words mean
    POLICY = "policy"               # Exam rules, time, etc.
    TECHNICAL = "technical"         # Console, connectivity issues
    CONTENT = "content"             # About exam content (escalate/decline)
    APPROACH = "approach"           # Solution methodology (decline)

class ResponseType(Enum):
    IMMEDIATE = "immediate"         # AI responds directly
    TROUBLESHOOT = "troubleshoot"   # AI guides, may escalate
    ESCALATE = "escalate"           # Route to proctor
    DECLINE = "decline"             # Politely refuse + redirect

@dataclass
class ClassificationResult:
    category: QuestionCategory
    response_type: ResponseType
    confidence: float
    reasoning: str

# Classification rules
CLASSIFICATION_RULES = {
    QuestionCategory.NAVIGATION: ResponseType.IMMEDIATE,
    QuestionCategory.DEFINITION: ResponseType.IMMEDIATE,
    QuestionCategory.POLICY: ResponseType.IMMEDIATE,
    QuestionCategory.TECHNICAL: ResponseType.TROUBLESHOOT,
    QuestionCategory.CONTENT: ResponseType.ESCALATE,
    QuestionCategory.APPROACH: ResponseType.DECLINE,
}

# Example classifier prompt
CLASSIFIER_PROMPT = """
Classify the candidate's question into one of these categories:

- NAVIGATION: Questions about the exam interface, where to find things
  Examples: "Where is the topology?", "How do I submit?", "Can I go back?"

- DEFINITION: Questions about what task words mean (not interpretation)
  Examples: "What does 'verify' mean?", "What is 'implement'?"

- POLICY: Questions about exam rules and procedures
  Examples: "How much time do I have?", "Can I use a calculator?"

- TECHNICAL: Issues with exam system or devices
  Examples: "Console not responding", "Page won't load"

- CONTENT: Questions about exam content requiring judgment
  Examples: "Is this task asking for X or Y?", "The diagram seems wrong"

- APPROACH: Questions about how to solve tasks
  Examples: "Should I use OSPF?", "Is my config correct?"

Question: {question}
Current task: {current_task}
Module: {module}

Classification:
"""
```

## Integration with LDS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LDS + AI SUPPORT INTEGRATION                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          LDS EXAM UI                                    ││
│  │                                                                         ││
│  │  ┌───────────────────────────────────────────────┐  ┌────────────────┐ ││
│  │  │                                               │  │   RESOURCES    │ ││
│  │  │                 TASK CONTENT                  │  │                │ ││
│  │  │                                               │  │ • Topology     │ ││
│  │  │  Task 5: Configure OSPF on the core routers  │  │ • Email        │ ││
│  │  │  to establish connectivity between...         │  │ • Docs         │ ││
│  │  │                                               │  │                │ ││
│  │  │                                               │  └────────────────┘ ││
│  │  │                                               │                     ││
│  │  │                                               │  ┌────────────────┐ ││
│  │  │                                               │  │   CONSOLES     │ ││
│  │  │                                               │  │                │ ││
│  │  │                                               │  │ R1  R2  R3     │ ││
│  │  │                                               │  │ S1  S2         │ ││
│  │  │                                               │  │                │ ││
│  │  └───────────────────────────────────────────────┘  └────────────────┘ ││
│  │                                                                         ││
│  │  ┌──────────────────────────────────────────────────────────────────┐  ││
│  │  │  ⏱️ 2:45:30 remaining    │    [◄ Prev]  [Next ►]  │  [❓ Help]   │  ││
│  │  └──────────────────────────────────────────────────────────────────┘  ││
│  │                                                    ▲                    ││
│  └─────────────────────────────────────────────────────│────────────────────┘│
│                                                        │                     │
│                                                        │ Click               │
│                                                        ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  💬 EXAM SUPPORT CHAT (embedded iframe → agent-host)                    ││
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │ How can I help you with the exam?                                  │ ││
│  │  │                                                                    │ ││
│  │  │ I can help with:                                                   │ ││
│  │  │ • Finding resources (topology, docs, emails)                       │ ││
│  │  │ • Understanding task wording                                       │ ││
│  │  │ • Exam interface navigation                                        │ ││
│  │  │ • Technical issues with consoles                                   │ ││
│  │  │                                                                    │ ││
│  │  │ [Type your question...]                                  [Send]   │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Audit Trail

Every interaction is logged for quality assurance and continuous improvement:

```python
@dataclass
class SupportInteraction:
    """Audit record for support interactions."""
    interaction_id: str
    session_id: str
    candidate_id: str  # Anonymized for analysis

    # Timing
    timestamp: datetime
    response_time_ms: int

    # Question
    question_text: str
    current_task: str
    current_module: str
    time_remaining_seconds: int

    # Classification
    category: QuestionCategory
    response_type: ResponseType
    classification_confidence: float

    # Response
    ai_response: str | None
    escalated_to_proctor: bool
    proctor_response: str | None

    # Outcome
    candidate_feedback: str | None  # "helpful" | "not_helpful" | None
    followup_question: bool

    # Analysis (populated post-hoc)
    was_appropriate: bool | None  # QA review
    should_have_escalated: bool | None
    improvement_notes: str | None
```

## Metrics & Continuous Improvement

| Metric | Description | Target |
|--------|-------------|--------|
| **Response time** | Seconds to first response | < 10 sec |
| **Resolution rate** | % resolved without escalation | > 80% |
| **Escalation accuracy** | % escalations that needed human | > 95% |
| **Decline accuracy** | % declines that were correct | > 99% |
| **Candidate satisfaction** | Post-interaction rating | > 4.0/5 |
| **Consistency score** | Same question = same answer | 100% |

### Feedback Loop

```
Interactions            Weekly Analysis           Content Updates
     │                        │                        │
     │  Logged data           │                        │
     │───────────────────────►│                        │
     │                        │                        │
     │                        │  Identify patterns:    │
     │                        │  • Common questions    │
     │                        │  • Escalation themes   │
     │                        │  • Decline edge cases  │
     │                        │                        │
     │                        │───────────────────────►│
     │                        │                        │
     │                        │                        │  Update:
     │                        │                        │  • Permitted clarifications
     │                        │                        │  • Classifier rules
     │                        │                        │  • Standard responses
     │                        │                        │
     │◄──────────────────────────────────────────────────
     │  Improved assistant
     │
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Availability** | Support accessible on every task | 100% |
| **Response time** | First response latency | < 10 sec |
| **No content leakage** | Questions that reveal answers | 0 |
| **Escalation coverage** | Ambiguous cases routed to proctor | 100% |
| **Consistency** | Same question = same answer | 100% |
| **Candidate satisfaction** | Would use again | > 90% |

## Open Questions

1. **Conversation History**: Should AI see candidate's previous questions in session?
2. **Proactive Hints**: Should AI offer navigation tips before candidate asks?
3. **Language Support**: Multi-language exams need multi-language support?
4. **Accessibility**: How to make support accessible for candidates with disabilities?
5. **Offline Mode**: What happens if agent-host connection drops?

---

_Last updated: December 25, 2025_
