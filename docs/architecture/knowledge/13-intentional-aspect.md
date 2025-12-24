# Intentional Aspect: "The Compass"

## Purpose

The Intentional Aspect acts as the **Kubernetes Manifest for Learning**. It defines the "Desired State" (Spec) and tracks the "Actual Status", enabling the AI to:

- Enforce learning paths
- Detect drift from goals
- Re-optimize schedules
- Adapt intervention style based on mode

## The Reconciliation Loop

The Reconciliation Loop runs **autonomously**, exposing custom handlers for (un)Registered DomainEvent streams. Like a Kubernetes controller, it continuously works to **converge toward achieving specified Goals/Intentions**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RECONCILIATION LOOP (Autonomous)                        │
│                                                                              │
│   ┌─────────────────┐                    ┌───────────────────────────────┐   │
│   │  DomainEvent     │                    │  Per-Aggregate Reconciler       │   │
│   │  Streams         │──────────────────▶│                                 │   │
│   │                  │                    │  - State (public + private)     │   │
│   │  • Registered    │                    │  - Spec (desired state)         │   │
│   │  • Unregistered  │                    │  - Relationships                │   │
│   └─────────────────┘                    │  - Rules (BusinessRules)        │   │
│                                          │  - Behaviors (event handlers)   │   │
│                                          └───────────────┬───────────────┘   │
│                                                        │                      │
│   ┌───────────────────────────────────────────────▼──────────────────┐   │
│   │                                                                      │   │
│   │   OBSERVE  ────▶  COMPARE  ────▶  DECIDE  ────▶  ACT                │   │
│   │   (events)       (spec vs       (drift     (emit events,        │   │
│   │                  status)        detected?)  trigger actions)     │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                        │                      │
│                                          ┌───────────────▼───────────────┐   │
│                                          │  Converge toward Goal           │   │
│                                          │                                 │   │
│                                          │  • Adjust velocity               │   │
│                                          │  • Trigger interventions         │   │
│                                          │  • Re-optimize schedule          │   │
│                                          │  • Notify stakeholders           │   │
│                                          └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Per-Aggregate Reconciler

Iterations in the loop are defined **per AggregateRoot**, each managing:

| Component | Description |
|-----------|-------------|
| **State (Public)** | Observable attributes (completion %, velocity, drift status) |
| **State (Private)** | Internal tracking (velocity_history, retry counts) |
| **Spec** | Desired state (target_date, weekly_commitment, mode) |
| **Relationships** | Links to other aggregates (User, Blueprint, Cohort) |
| **Rules** | BusinessRules evaluated each iteration |
| **Behaviors** | Event handlers triggered by DomainEvent streams |

```python
# application/reconcilers/learning_intent_reconciler.py

from neuroglia.eventing import EventHandler
from domain.entities.learning_intent import LearningIntent
from domain.events import ProgressRecorded, SessionCompleted, AssessmentSubmitted

class LearningIntentReconciler:
    """Autonomous reconciler for LearningIntent aggregates."""

    def __init__(
        self,
        repository: Repository[LearningIntent],
        mediator: Mediator,
        rules: list[BusinessRule],
    ):
        self._repository = repository
        self._mediator = mediator
        self._rules = rules

    @EventHandler(ProgressRecorded)
    async def on_progress_recorded(self, event: ProgressRecorded) -> None:
        """Handle progress events and check for drift."""
        intent = await self._repository.get(event.intent_id)

        # Update internal state
        intent.record_progress(
            hours_logged=event.hours,
            concepts_completed=event.concepts,
        )

        # Evaluate business rules
        for rule in self._rules:
            await rule.evaluate(intent)

        # Persist and emit events
        await self._repository.save(intent)

    @EventHandler(SessionCompleted)
    async def on_session_completed(self, event: SessionCompleted) -> None:
        """Recalculate schedule after each learning session."""
        intent = await self._repository.get(event.intent_id)

        # Check if re-optimization needed
        if intent.state.drift_status in ["behind", "critical"]:
            await self._mediator.execute_async(
                OptimizeScheduleCommand(intent_id=intent.id())
            )

    async def reconcile_all(self) -> None:
        """Periodic reconciliation of all active intents."""
        active_intents = await self._repository.find_all(
            filter={"status": {"$ne": "completed"}}
        )

        for intent in active_intents:
            await self._reconcile_one(intent)

    async def _reconcile_one(self, intent: LearningIntent) -> None:
        """Single iteration of the reconciliation loop."""
        # OBSERVE: Get current telemetry
        telemetry = await self._get_telemetry(intent)

        # COMPARE: Spec vs Status
        drift = self._detect_drift(intent, telemetry)

        # DECIDE & ACT: Based on drift and rules
        if drift.requires_intervention:
            await self._trigger_intervention(intent, drift)
```

## Persistence Strategy

The Intentional Aspect uses **State-Based Persistence** with embedded drift detection logic:

**Design Decision (Option B)**: Drift detection is embedded in the aggregate, maintaining its own `velocity_history` in state. This keeps drift logic co-located with the aggregate and avoids external analytics dependencies for real-time decisions.

```
┌───────────────────────────────────────────────────────────────────────┐
│                    LearningIntent Aggregate                           │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ State (MongoDB)                                                  │  │
│  │   - spec: target_date, commitment, mode                         │  │
│  │   - status: completion_percent, drift_status                    │  │
│  │   - velocity_history: [{week, hours, timestamp}]  ◀─── NEW      │  │
│  │   - state_version: int (optimistic concurrency)                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Behavior (Embedded)                                              │  │
│  │   - record_progress() → updates velocity_history                │  │
│  │   - calculate_drift() → queries own history                     │  │
│  │   - emit CloudEvents for external observability                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  CloudEvents    │
                    │  (Published,    │
                    │  NOT persisted) │
                    └─────────────────┘
```

## Domain Model

### LearningIntent (Aggregate Root)

```python
class LearningIntentState(AggregateState[str]):
    """The 'Spec' - What the user wants to achieve."""

    # Identity
    id: str
    user_id: str

    # The Goal
    goal_type: str  # "certification", "skill", "project", "exploration"
    target_id: str  # certification_id, skill_id, etc.
    target_name: str

    # Constraints (The Spec)
    target_date: datetime | None
    learning_style: str  # "visual", "auditory", "reading", "kinesthetic"
    weekly_commitment_hours: float
    preferred_conversation_length_minutes: int
    mode: str  # "learning", "exam_prep", "exploration"

    # Flexibility
    allow_skipping_optional: bool
    allow_deadline_extension: bool
    strictness_level: int  # 1-5 (1=flexible, 5=strict)

    # Status (The Actual)
    current_completion_percent: float
    current_velocity_hours_per_week: float
    drift_status: str  # "on_track", "behind", "ahead", "critical"
    last_activity_at: datetime

    # Velocity History (Embedded for Drift Detection)
    velocity_history: list[dict]  # [{week_start: datetime, hours: float, concepts_completed: int}]

    # Audit
    created_at: datetime
    last_modified: datetime
    state_version: int  # Optimistic concurrency


class LearningIntent(AggregateRoot[LearningIntentState, str]):
    """
    Aggregate managing user's learning goals and progress.

    Persistence: State-based (MongoDB via MotorRepository)
    Drift Detection: Embedded, queries own velocity_history
    """

    def record_progress(self, hours_logged: float, concepts_completed: list[str]) -> None:
        """Record progress and update velocity history."""
        week_start = self._get_week_start(datetime.now(timezone.utc))

        # Update or append to velocity history
        existing_week = next(
            (w for w in self.state.velocity_history if w["week_start"] == week_start),
            None
        )
        if existing_week:
            existing_week["hours"] += hours_logged
            existing_week["concepts_completed"] += len(concepts_completed)
        else:
            self.state.velocity_history.append({
                "week_start": week_start,
                "hours": hours_logged,
                "concepts_completed": len(concepts_completed)
            })
            # Keep only last 12 weeks of history
            self.state.velocity_history = self.state.velocity_history[-12:]

        # Recalculate current velocity (4-week rolling average)
        self.state.current_velocity_hours_per_week = self._calculate_rolling_velocity()
        self.state.last_activity_at = datetime.now(timezone.utc)

        # Check for drift
        new_drift_status = self._detect_drift()
        if new_drift_status != self.state.drift_status:
            old_status = self.state.drift_status
            self.state.drift_status = new_drift_status
            self.register_event(IntentDriftDetectedDomainEvent(
                aggregate_id=self.id(),
                previous_status=old_status,
                new_status=new_drift_status,
                gap_hours=self._calculate_gap_hours()
            ))

        self.register_event(IntentProgressRecordedDomainEvent(
            aggregate_id=self.id(),
            hours_logged=hours_logged,
            new_completion_percent=self.state.current_completion_percent
        ))

    def _calculate_rolling_velocity(self) -> float:
        """Calculate 4-week rolling average of hours per week."""
        recent_weeks = self.state.velocity_history[-4:]
        if not recent_weeks:
            return 0.0
        return sum(w["hours"] for w in recent_weeks) / len(recent_weeks)

    def _detect_drift(self) -> str:
        """
        Detect drift based on velocity vs commitment.

        Thresholds:
        - on_track: velocity >= 80% of commitment
        - behind: velocity 40-80% of commitment
        - critical: velocity < 40% of commitment
        - ahead: velocity > 120% of commitment
        """
        ratio = self.state.current_velocity_hours_per_week / self.state.weekly_commitment_hours

        if ratio >= 1.2:
            return "ahead"
        elif ratio >= 0.8:
            return "on_track"
        elif ratio >= 0.4:
            return "behind"
        else:
            return "critical"

    def _calculate_gap_hours(self) -> float:
        """Calculate hours behind schedule."""
        return max(0, self.state.weekly_commitment_hours - self.state.current_velocity_hours_per_week)

    @staticmethod
    def _get_week_start(dt: datetime) -> datetime:
        """Get Monday of the current week."""
        return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
```

### IntentMilestone (Entity)

```python
@dataclass
class IntentMilestone:
    """Checkpoint within a learning intent."""
    id: str
    name: str  # "Complete Module 3"
    target_date: datetime
    completion_percent: float
    status: str  # "pending", "completed", "overdue", "skipped"
    is_required: bool
    concepts: list[str]  # Concept IDs covered
```

## AI Benefit: Strategic Alignment

The AI is not just answering questions—it is **enforcing the Spec**. It acts as the "Controller" in the K8s reconciliation loop.

### Example: Reactive Support (Coach Role)

**User Action**: User requests to skip a difficult module.

**AI Check**:

```python
intent = await get_user_intent(user_id)
module_concepts = await get_module_concepts(module_id)

# Is this module required for the goal?
is_required = await check_if_required(
    goal_id=intent.target_id,
    concepts=module_concepts
)

if is_required and intent.strictness_level >= 3:
    response = "cannot_skip"
else:
    response = "can_skip_with_warning"
```

**AI Response (Strict Mode)**:
> "I can't let you skip this. Your goal is 'Senior Architect', and this module is critical for the final exam. Let's break it down into smaller pieces instead."

**AI Response (Flexible Mode)**:
> "This module is important but not strictly required. I can let you skip it, but you may struggle with Module 7 later. Want to continue anyway?"

### Example: Proactive Support (Planner Role)

**Trigger**: Velocity drops below commitment.

**Detection Logic**:

```python
async def check_drift(intent: LearningIntent) -> DriftReport:
    if intent.current_velocity < intent.weekly_commitment_hours * 0.6:
        # Velocity is less than 60% of commitment
        return DriftReport(
            status="behind",
            gap_hours=intent.weekly_commitment_hours - intent.current_velocity,
            projected_miss_date=calculate_miss_date(intent),
            recovery_plan=generate_recovery_plan(intent)
        )
```

**AI Response**:
> "I noticed you've only logged 2 hours this week, but your plan requires 5 hours to hit your December deadline. I've re-optimized your schedule: if you do 30 mins tonight, we get back on track. Ready to start?"

## Mode-Based Behavior

The `mode` field controls AI intervention style:

| Mode | AI Behavior |
|------|-------------|
| `learning` | Can give hints, explanations, examples |
| `exam_prep` | Hints allowed, but encourages self-solving first |
| `exam` | Only encouragement, no answers, strict time limits |
| `exploration` | No enforcement, purely supportive |

```python
def get_allowed_actions(intent: LearningIntent) -> list[str]:
    if intent.mode == "exam":
        return ["encourage", "time_warning", "submit_reminder"]
    elif intent.mode == "exam_prep":
        return ["hint_after_attempt", "explain_wrong_answer", "practice_mode"]
    else:
        return ["full_explanation", "show_answer", "skip_allowed"]
```

## API Endpoints

### Get User Intent

```
GET /intent/users/{user_id}/current
Response: {
  intent: { target_name, target_date, mode, ... },
  status: { velocity, drift_status, completion_percent },
  next_milestone: { name, target_date, status }
}
```

### Create Intent

```
POST /intent/users/{user_id}
Body: {
  goal_type: "certification",
  target_id: "python-senior",
  target_date: "2025-12-01",
  weekly_commitment_hours: 5,
  mode: "learning"
}
```

### Update Progress

```
POST /intent/{intent_id}/progress
Body: {
  hours_logged: 1.5,
  concepts_completed: ["concept-123"],
  assessment_score: 0.85
}
```

### Get Drift Report

```
GET /intent/{intent_id}/drift
Response: {
  status: "behind",
  gap_hours: 3,
  projected_completion: "2025-12-15",
  recovery_plan: { ... }
}
```

### Request Schedule Optimization

```
POST /intent/{intent_id}/optimize
Body: {
  available_slots: [
    { day: "monday", start: "19:00", duration_minutes: 60 },
    ...
  ]
}
Response: {
  optimized_schedule: [...],
  weekly_conversations: 4,
  on_track_probability: 0.85
}
```

## Domain Events

```python
@cloudevent("intent.created.v1")
class LearningIntentCreatedDomainEvent(DomainEvent):
    user_id: str
    target_name: str
    target_date: datetime
    mode: str

@cloudevent("intent.progress.recorded.v1")
class IntentProgressRecordedDomainEvent(DomainEvent):
    intent_id: str
    hours_logged: float
    new_completion_percent: float

@cloudevent("intent.drift.detected.v1")
class IntentDriftDetectedDomainEvent(DomainEvent):
    intent_id: str
    previous_status: str
    new_status: str  # "behind", "critical"
    gap_hours: float

@cloudevent("intent.milestone.completed.v1")
class IntentMilestoneCompletedDomainEvent(DomainEvent):
    intent_id: str
    milestone_id: str
    completed_at: datetime
```

## Integration with Context Expander

```python
intentional_context = {
    "goal": "Python Senior Certification",
    "target_date": "2025-12-01",
    "mode": "learning",  # Affects allowed AI actions
    "drift_status": "behind",
    "intervention": "User needs gentle re-engagement, not pressure",
    "allowed_actions": ["hint", "explain", "encourage"]
}
```

## Intent Expression via Supportive Agent

End-users express Intent through a **supportive agent** equipped with the relevant tools and knowledge. The agent guides users through Intent specification using natural conversation, translating human goals into structured Specs.

### Agent Capabilities for Intent Expression

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 INTENT EXPRESSION AGENT                                     │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────────┐│
│  │  UNDERSTANDING     │  │  TOOLS (MCP)        │  │  KNOWLEDGE            ││
│  │                    │  │                     │  │                        ││
│  │  • Goal extraction │  │  • list_blueprints  │  │  • Blueprint catalog   ││
│  │  • Constraint ID   │  │  • analyze_schedule │  │  • Prerequisite graphs ││
│  │  • Preference elicit│  │  • estimate_effort  │  │  • Historical patterns ││
│  │  • Conflict detect │  │  • create_intent    │  │  • User's past intents││
│  └─────────────────────┘  └─────────────────────┘  └────────────────────────┘│
│                                                                              │
│  User: "I want to get certified in Python by December"                      │
│                               │                                              │
│                               ▼                                              │
│  Agent: Analyzes available blueprints, user's current mastery,              │
│         typical completion times, and proposes a structured Intent          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Intent Expression Tools (MCP)

The agent has access to specialized tools for Intent creation and management:

```python
# Agent's MCP tools for Intent expression

@mcp_tool(name="list_available_goals")
async def list_available_goals(
    category: str | None = None,
    user_id: str | None = None,
) -> list[GoalOption]:
    """
    List certification/skill goals available to the user.
    Filters by category and user's prerequisites if provided.
    """
    ...

@mcp_tool(name="analyze_goal_requirements")
async def analyze_goal_requirements(
    goal_id: str,
    user_id: str,
) -> GoalAnalysis:
    """
    Analyze what's required to achieve a goal.
    Returns:
    - Required topics/concepts
    - User's current mastery of prerequisites
    - Estimated effort (hours)
    - Suggested timeline
    - Potential blockers
    """
    ...

@mcp_tool(name="estimate_realistic_timeline")
async def estimate_realistic_timeline(
    goal_id: str,
    user_id: str,
    weekly_hours_available: float,
    preferred_style: str = "balanced",
) -> TimelineEstimate:
    """
    Given constraints, estimate realistic completion date.
    Uses historical data from similar candidates.
    """
    ...

@mcp_tool(name="create_learning_intent")
async def create_learning_intent(
    user_id: str,
    goal_type: str,
    target_id: str,
    target_date: datetime,
    weekly_commitment_hours: float,
    mode: str = "learning",
    strictness_level: int = 3,
    preferences: dict | None = None,
) -> IntentCreationResult:
    """
    Create a new LearningIntent aggregate.
    Returns the created intent and initial schedule.
    """
    ...

@mcp_tool(name="adjust_intent")
async def adjust_intent(
    intent_id: str,
    adjustments: IntentAdjustment,
) -> IntentUpdateResult:
    """
    Modify an existing intent (change deadline, commitment, mode).
    Validates against constraints and recalculates schedule.
    """
    ...
```

### Conversational Intent Elicitation

The agent uses a structured conversation flow to elicit Intent:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                INTENT ELICITATION CONVERSATION                              │
│                                                                              │
│  ① GOAL IDENTIFICATION                                                      │
│     User: "I want to learn Python"                                          │
│     Agent: Calls list_available_goals(category="python")                    │
│     Agent: "I see several Python paths. Are you aiming for:                 │
│             - Python Fundamentals (beginner)                                │
│             - Python Professional (intermediate)                            │
│             - Python Senior Architect (advanced)?"                          │
│                                                                              │
│  ② CONSTRAINT DISCOVERY                                                     │
│     User: "Professional level, I need it for a job by March"                │
│     Agent: Calls analyze_goal_requirements(goal="python-pro", user=...)     │
│     Agent: "March is 12 weeks away. The Python Professional path            │
│             typically takes 8-10 weeks at 5 hours/week. You already         │
│             know loops and functions. How many hours per week               │
│             can you commit?"                                                │
│                                                                              │
│  ③ PREFERENCE ELICITATION                                                   │
│     User: "Maybe 4-5 hours, mostly evenings"                                │
│     Agent: Calls estimate_realistic_timeline(weekly_hours=4.5)              │
│     Agent: "At 4.5 hours/week, you'll finish by Feb 28 with buffer.         │
│             Do you prefer:                                                  │
│             - Strict mode (I'll hold you accountable)                       │
│             - Flexible mode (I'll adapt to your pace)                       │
│             - Exam prep mode (practice tests emphasis)?"                    │
│                                                                              │
│  ④ CONFLICT RESOLUTION                                                      │
│     Agent: "I noticed you have an existing intent for 'Data Science'        │
│             that overlaps. Should I:                                        │
│             - Pause Data Science until Python is done                       │
│             - Run both in parallel (reduce hours each)                      │
│             - Cancel Data Science?"                                         │
│                                                                              │
│  ⑤ CONFIRMATION & CREATION                                                  │
│     Agent: Calls create_learning_intent(...)                                │
│     Agent: "Done! Your Python Professional path starts Monday.              │
│             First session: 45 min on 'Advanced Functions'.                  │
│             I'll check in weekly and adjust if needed."                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Intent Adjustment Patterns

The agent also helps users **modify intents** when circumstances change:

```python
# Example: User requests to change their intent

class IntentAdjustment:
    """Structured adjustment request."""
    new_target_date: datetime | None = None
    new_weekly_hours: float | None = None
    new_mode: str | None = None
    new_strictness: int | None = None
    pause_until: datetime | None = None
    cancel_reason: str | None = None

# Conversation example:
# User: "I'm going on vacation next week, can we pause?"
# Agent: Calls adjust_intent(intent_id, IntentAdjustment(pause_until=...))
# Agent: "Paused until Jan 5. I've recalculated: you'll need 5.5 hours/week
#         after vacation to hit your March deadline. Does that work?"
```

### Agent Knowledge for Intent Support

The agent has access to contextual knowledge for better Intent guidance:

```python
@dataclass
class IntentSupportKnowledge:
    """Knowledge the agent uses for Intent elicitation."""

    # Blueprint catalog
    available_blueprints: list[BlueprintSummary]

    # User's current state
    user_mastery: dict[str, float]  # skill_id -> confidence
    user_history: list[PastIntent]  # Previous goals
    user_schedule_patterns: SchedulePatterns  # When they typically study

    # Historical patterns (anonymized)
    avg_completion_times: dict[str, timedelta]  # blueprint_id -> typical time
    success_predictors: dict[str, list[str]]    # blueprint_id -> key skills
    common_blockers: dict[str, list[str]]       # blueprint_id -> typical struggles

    # Constraint validation
    min_weekly_hours: float = 1.0
    max_concurrent_intents: int = 3
    min_notice_days: int = 7  # For deadline changes
```

```

---

*Next: [14-observational-aspect.md](14-observational-aspect.md) - Telemetry & Empathy*
