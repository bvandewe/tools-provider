# The Integrated Conversation Loop

## Overview

A **Conversation** is not just a chat window—it is a **Reconciliation Loop** where the AI agent continuously observes, references, and steers. The three aspects work together to form the **Context Vector** that guides every AI action.

## The Loop in Action

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                                   │
│                                                                              │
│   User types: "I'm stuck on this exercise"                                  │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STEP 1: OBSERVATIONAL                                 │
│                           (The Pulse)                                        │
│                                                                              │
│   Telemetry Check:                                                          │
│   ┌─────────────────────────────────────────┐                               │
│   │ • idle_time: 45 seconds                 │                               │
│   │ • typing_error_rate: 0.08 (normal)      │                               │
│   │ • conversation_duration: 25 mins        │                               │
│   │ • focus_status: active                  │                               │
│   └─────────────────────────────────────────┘                               │
│                                                                              │
│   Inference: User is cognitively available, not fatigued or frustrated.     │
│   Signal: PROCEED_NORMALLY                                                  │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 2: SEMANTIC                                     │
│                           (The Map)                                          │
│                                                                              │
│   Graph Queries:                                                            │
│   ┌─────────────────────────────────────────┐                               │
│   │ Q: What is this exercise testing?       │                               │
│   │ A: Concept = "ListComprehensions"       │                               │
│   │                                         │                               │
│   │ Q: Does user know prerequisites?        │                               │
│   │ A: (User)-[:MASTERED]->(Loops) ✓        │                               │
│   │    (User)-[:MASTERED]->(Lists) ✓        │                               │
│   │    (User)-[:STRUGGLING_WITH]->(None)    │                               │
│   └─────────────────────────────────────────┘                               │
│                                                                              │
│   Inference: User has the prerequisite knowledge.                           │
│   Signal: NOT_A_KNOWLEDGE_GAP → likely syntax/logic block                   │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STEP 3: INTENTIONAL                                   │
│                          (The Compass)                                       │
│                                                                              │
│   Spec Check:                                                               │
│   ┌─────────────────────────────────────────┐                               │
│   │ • goal: "Python Intermediate Cert"      │                               │
│   │ • mode: "learning" (not "exam")         │                               │
│   │ • strictness: 2 (flexible)              │                               │
│   │ • drift_status: "on_track"              │                               │
│   └─────────────────────────────────────────┘                               │
│                                                                              │
│   Inference: User is in learning mode → hints are allowed.                  │
│   Signal: FULL_SUPPORT_ALLOWED                                              │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STEP 4: CONTEXT ASSEMBLY                              │
│                                                                              │
│   Context Vector:                                                           │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │ {                                                           │           │
│   │   "observational": {                                        │           │
│   │     "state": "focused",                                     │           │
│   │     "fatigue": "low",                                       │           │
│   │     "pacing": "normal"                                      │           │
│   │   },                                                        │           │
│   │   "semantic": {                                             │           │
│   │     "current_concept": "ListComprehensions",                │           │
│   │     "prerequisites_met": true,                              │           │
│   │     "likely_issue": "syntax_or_logic"                       │           │
│   │   },                                                        │           │
│   │   "intentional": {                                          │           │
│   │     "mode": "learning",                                     │           │
│   │     "allowed_actions": ["hint", "explain", "show_example"], │           │
│   │     "goal_context": "Python Intermediate"                   │           │
│   │   }                                                         │           │
│   │ }                                                           │           │
│   └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 5: AI DECISION                                  │
│                                                                              │
│   Agent receives: User query + Context Vector                               │
│                                                                              │
│   Decision Logic:                                                           │
│   • Prerequisites are met → not a knowledge gap                             │
│   • Mode is "learning" → can give direct help                               │
│   • User is focused → no need for wellness check                            │
│                                                                              │
│   Action: Provide syntax hint specific to List Comprehensions               │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 6: RESPONSE                                     │
│                                                                              │
│   AI Says:                                                                  │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │ "You've been quiet for a minute. Remember, a List          │           │
│   │  Comprehension always starts with the expression, not      │           │
│   │  the loop.                                                  │           │
│   │                                                             │           │
│   │  Template: [expression for item in iterable]                │           │
│   │                                                             │           │
│   │  Want to see an example with your current code?"            │           │
│   └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Context Expander Implementation

```python
# application/services/conversation_context_service.py

@dataclass
class ConversationContext:
    """The unified context vector for a conversation."""

    # From Observational
    user_state: UserState
    pacing_recommendation: str

    # From Semantic
    user_mastery: list[str]
    user_struggles: list[str]
    current_concept: str | None
    prerequisites_status: dict[str, str]

    # From Intentional
    learning_mode: str
    allowed_actions: list[str]
    goal_name: str
    drift_status: str

    # Assembled
    context_block: str  # Ready-to-inject text for LLM


class ConversationContextService:
    """Assembles the full context vector for a conversation."""

    def __init__(
        self,
        observational_client: ObservationalClient,
        semantic_client: SemanticClient,
        intentional_client: IntentionalClient,
    ):
        self._obs = observational_client
        self._sem = semantic_client
        self._int = intentional_client

    async def get_context(
        self,
        user_id: str,
        conversation_id: str,
        current_activity_id: str | None = None,
    ) -> ConversationContext:
        """Gather context from all three aspects."""

        # Parallel fetch from all aspects
        obs_task = self._obs.get_user_state(user_id, conversation_id)
        sem_task = self._sem.get_user_knowledge(user_id, current_activity_id)
        int_task = self._int.get_user_intent(user_id)

        obs_result, sem_result, int_result = await asyncio.gather(
            obs_task, sem_task, int_task
        )

        # Assemble context block for LLM injection
        context_block = self._format_context_block(
            obs_result, sem_result, int_result
        )

        return ConversationContext(
            user_state=obs_result,
            pacing_recommendation=self._infer_pacing(obs_result),
            user_mastery=sem_result.mastered_skills,
            user_struggles=sem_result.struggling_concepts,
            current_concept=sem_result.current_concept,
            prerequisites_status=sem_result.prereq_status,
            learning_mode=int_result.mode,
            allowed_actions=self._get_allowed_actions(int_result.mode),
            goal_name=int_result.target_name,
            drift_status=int_result.drift_status,
            context_block=context_block,
        )

    def _format_context_block(self, obs, sem, intent) -> str:
        """Format the context vector as injectable text."""
        return f"""
---
## Conversation Context

**User State**: {obs.engagement_level:.0%} engaged, {obs.fatigue_score:.0%} fatigued
**Learning Mode**: {intent.mode} (actions allowed: {', '.join(self._get_allowed_actions(intent.mode))})
**Goal**: {intent.target_name} (status: {intent.drift_status})

**Knowledge Context**:
- Mastered: {', '.join(sem.mastered_skills[:5])}
- Struggling: {', '.join(sem.struggling_concepts) or 'None detected'}
- Current topic: {sem.current_concept}

**Guidance**: Adjust response pacing to {self._infer_pacing(obs)}.
---
"""
```

## Proactive Intervention Flow

The loop also runs **proactively** when triggers fire:

```python
class ProactiveInterventionService:
    """Monitors for intervention triggers across all aspects."""

    TRIGGERS = [
        # Observational triggers
        ("fatigue_critical", lambda obs: obs.fatigue_score > 0.8),
        ("frustration_high", lambda obs: obs.frustration_score > 0.7),
        ("confusion_detected", lambda obs: obs.confusion_score > 0.6),

        # Intentional triggers
        ("drift_critical", lambda intent: intent.drift_status == "critical"),
        ("milestone_overdue", lambda intent: intent.has_overdue_milestone),

        # Semantic triggers
        ("mentoring_opportunity", lambda sem: sem.can_mentor_peers),
        ("peer_struggling", lambda sem: sem.peers_need_help),
    ]

    async def check_triggers(self, user_id: str, conversation_id: str) -> list[Intervention]:
        """Check all triggers and return needed interventions."""
        context = await self._context_service.get_context(user_id, conversation_id)

        interventions = []
        for name, condition, in self.TRIGGERS:
            if self._evaluate_trigger(condition, context):
                intervention = await self._create_intervention(name, context)
                interventions.append(intervention)

        return interventions
```

## AI Role Mapping

Based on the context, the AI adopts different roles:

| Aspect | Role | Trigger | Behavior |
|--------|------|---------|----------|
| Semantic | **Tutor** | User asks question | Explain based on prior knowledge |
| Semantic | **Connector** | User masters skill | Suggest mentoring peers |
| Intentional | **Coach** | User tries to skip | Enforce or negotiate based on strictness |
| Intentional | **Planner** | Drift detected | Re-optimize schedule |
| Observational | **Facilitator** | Confusion detected | Simplify, pause, offer alternative |
| Observational | **Wellness** | Fatigue detected | Enforce break |

## Benefits Summary

| Benefit | How Achieved |
|---------|--------------|
| **Reduced Cognitive Load** | AI manages schedule (Intent) and finds resources (Semantic) |
| **Psychological Safety** | Observational ensures supportive intervention before frustration |
| **Personalization** | Graph knows what user mastered/struggles with |
| **Goal Alignment** | Intent ensures user stays on track |
| **Adaptive Pacing** | Telemetry adjusts AI tone and speed |

## Confidence Assessment

| Metric | Score | Rationale |
|--------|-------|-----------|
| **Feasibility** | 0.9 | Observational layer is standard EdTech (xAPI, Caliper). Intentional is goal management. |
| **Relevancy** | 0.98 | This is personalized learning's "Holy Grail". Context vector dramatically reduces hallucinations. |

---

_End of Runtime Aspects documentation._
