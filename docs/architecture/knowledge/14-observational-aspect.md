# Observational Aspect: "The Pulse"

## Purpose

The Observational Aspect processes **high-frequency, ephemeral telemetry** to give the AI emotional intelligence. It enables:

- Detecting cognitive overload
- Sensing frustration before user quits
- Adapting pacing based on fatigue
- Psychological safety through timely intervention

## Telemetry Metrics

### Activity Metrics

| Metric | Source | Signal |
|--------|--------|--------|
| `conversation_duration` | Conversation start/end | Fatigue risk |
| `time_on_task` | Focus tracking | Engagement |
| `idle_time` | No input detected | Confusion or distraction |
| `input_rate` | Keystrokes/clicks per minute | Engagement level |

### Behavior Metrics

| Metric | Source | Signal |
|--------|--------|--------|
| `video_seek_rate` | Video player events | Confusion (high seek = rewinding) |
| `video_pause_frequency` | Video player events | Note-taking or confusion |
| `typing_error_rate` | Keystroke analysis | Fatigue |
| `click_rage_count` | Rapid repeated clicks | Frustration |
| `scroll_velocity` | Scroll events | Skimming vs reading |
| `tab_switch_count` | Focus change events | Distraction |

### Assessment Metrics

| Metric | Source | Signal |
|--------|--------|--------|
| `attempt_count` | Quiz submissions | Struggle detection |
| `time_per_question` | Quiz timing | Difficulty calibration |
| `answer_change_count` | Quiz behavior | Uncertainty |
| `hint_request_rate` | Hint button clicks | Need for support |

### Sentiment Metrics (Optional)

| Metric | Source | Signal |
|--------|--------|--------|
| `text_sentiment` | NLP on chat messages | Frustration/confusion |
| `voice_sentiment` | Audio analysis | Stress detection |
| `facial_expression` | Camera (opt-in) | Engagement/confusion |

## Storage Architecture

Telemetry is **ephemeral**, not event-sourced:

```
┌───────────────────────────────────────────────────────────┐
│                    TELEMETRY PIPELINE                      │
│                                                            │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────────┐   │
│   │ Client  │───▶│ WebSocket / │───▶│ Time-Series DB  │   │
│   │ Events  │    │ Event Hub   │    │ (InfluxDB/      │   │
│   └─────────┘    └─────────────┘    │  Prometheus)    │   │
│                                      └────────┬────────┘   │
│                                               │            │
│                         ┌─────────────────────┼────────────┤
│                         │                     │            │
│                         ▼                     ▼            │
│              ┌──────────────────┐  ┌──────────────────┐   │
│              │ Real-Time Alerts │  │  Conversation   │   │
│              │ (Frustration,    │  │    Summary      │   │
│              │  Fatigue)        │  │ (Aggregated to  │   │
│              └──────────────────┘  │  Event Store)   │   │
└───────────────────────────────────────────────────────────┘
```

- **Raw telemetry**: 24-hour retention (InfluxDB)
- **Conversation summaries**: Event-sourced (EventStoreDB)
- **Alerts**: Real-time processing (in-memory)

## AI Benefit: Emotional Intelligence

### Example: Reactive Support (Facilitator Role)

**Observation**:

```json
{
  "metric": "video_seek_rate",
  "value": 12,  // seeks in last 2 minutes
  "threshold": 5,
  "signal": "confusion"
}
```

**AI Inference**: User is rewinding repeatedly = cognitive overload.

**AI Response**:
> "This section seems dense. I've paused the video. Here's a simple diagram summarizing the last 2 minutes. Does this help?"

### Example: Proactive Support (Wellness Role)

**Observation**:

```json
{
  "conversation_duration_minutes": 95,
  "typing_error_rate": 0.15,  // 15% errors (normally 5%)
  "last_break_minutes_ago": 95
}
```

**AI Inference**: Fatigue detected.

**AI Response**:
> "You're grinding hard, but your error rate is climbing. Science says you've hit the point of diminishing returns. I'm locking the conversation for 15 minutes. Go take a walk!"

## Inference Engine

### Signal Aggregation

```python
@dataclass
class UserState:
    """Real-time cognitive/emotional state."""
    engagement_level: float  # 0.0 - 1.0
    confusion_score: float   # 0.0 - 1.0
    frustration_score: float # 0.0 - 1.0
    fatigue_score: float     # 0.0 - 1.0

    inferred_at: datetime
    confidence: float
    signals_used: list[str]

async def infer_user_state(user_id: str, conversation_id: str) -> UserState:
    """Aggregate telemetry into user state."""

    metrics = await get_recent_metrics(user_id, conversation_id, window_minutes=5)

    confusion_score = calculate_confusion(
        seek_rate=metrics.video_seek_rate,
        idle_time=metrics.idle_time,
        hint_requests=metrics.hint_request_count,
    )

    fatigue_score = calculate_fatigue(
        conversation_duration=metrics.conversation_duration,
        error_rate=metrics.typing_error_rate,
        input_rate_decay=metrics.input_rate_trend,
    )

    frustration_score = calculate_frustration(
        click_rage=metrics.click_rage_count,
        attempt_failures=metrics.failed_attempts,
        sentiment=metrics.text_sentiment,
    )

    return UserState(
        engagement_level=1.0 - (confusion_score + fatigue_score) / 2,
        confusion_score=confusion_score,
        frustration_score=frustration_score,
        fatigue_score=fatigue_score,
        inferred_at=datetime.utcnow(),
        confidence=0.85,
        signals_used=list(metrics.keys()),
    )
```

### Alert Thresholds

```python
ALERT_THRESHOLDS = {
    "confusion": {
        "warning": 0.6,
        "critical": 0.8,
        "action": "offer_simplified_explanation"
    },
    "frustration": {
        "warning": 0.5,
        "critical": 0.7,
        "action": "acknowledge_and_encourage"
    },
    "fatigue": {
        "warning": 0.6,
        "critical": 0.8,
        "action": "suggest_break"
    }
}
```

## API Endpoints

### Record Telemetry (WebSocket preferred)

```
POST /telemetry/events
Body: {
  user_id: string,
  conversation_id: string,
  events: [
    { type: "video_seek", timestamp: "...", data: { position: 120 } },
    { type: "keystroke", timestamp: "...", data: { error: false } },
    ...
  ]
}
```

### Get User State

```
GET /telemetry/users/{user_id}/state
Response: {
  engagement_level: 0.7,
  confusion_score: 0.3,
  frustration_score: 0.1,
  fatigue_score: 0.5,
  suggested_action: "continue_normally",
  intervention_needed: false
}
```

### Get Conversation Summary

```
GET /telemetry/conversations/{conversation_id}/summary
Response: {
  duration_minutes: 45,
  active_time_minutes: 38,
  peak_engagement: 0.9,
  confusion_events: 2,
  break_taken: true,
  fatigue_at_end: 0.4
}
```

## Event Emission

Conversation summaries are event-sourced for analytics:

```python
@cloudevent("conversation.telemetry.summarized.v1")
class ConversationTelemetrySummarizedDomainEvent(DomainEvent):
    conversation_id: str
    user_id: str
    duration_minutes: int
    engagement_average: float
    confusion_events: int
    frustration_events: int
    fatigue_peak: float
    intervention_count: int
```

## Privacy Considerations

| Data Type | Retention | User Control |
|-----------|-----------|--------------|
| Raw telemetry | 24 hours | Auto-delete |
| Conversation summaries | 90 days | Can request deletion |
| Sentiment analysis | Never stored | Opt-in only |
| Camera/voice | Never stored | Explicit consent |

## Integration with Context Expander

```python
observational_context = {
    "current_state": "confused",  # inferred
    "fatigue_level": "moderate",
    "conversation_duration": 45,
    "suggested_pacing": "slow_down",
    "intervention_style": "supportive_not_pushing",
    "last_break": "20 minutes ago"
}
```

---

_Next: [15-conversation-loop.md](15-conversation-loop.md) - The Reconciliation Loop_
