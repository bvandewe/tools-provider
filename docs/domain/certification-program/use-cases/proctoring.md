# Use Case: Proctoring

> **Primary Actor:** Proctor
> **Supporting Actors:** Candidate, AI Proctor Assistant, Session Manager
> **Systems Involved:** Mozart (scheduling portal), LDS, session-manager, agent-host, pod-manager

## Overview

Proctoring ensures exam integrity by monitoring candidate behavior, managing exam sessions, and intervening when issues arise. Proctors currently juggle multiple systems (Mozart, LDS) with limited AI assistance—a prime opportunity for augmentation.

## Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CURRENT PROCTORING WORKFLOW                           │
│                                                                              │
│  Proctor                         Mozart                      LDS             │
│     │                              │                          │              │
│     │  1. View daily schedule      │                          │              │
│     │─────────────────────────────►│                          │              │
│     │                              │                          │              │
│     │  2. Check-in candidates      │                          │              │
│     │─────────────────────────────►│                          │              │
│     │                              │                          │              │
│     │  3. Launch candidate exam    │                          │              │
│     │─────────────────────────────►│─────────────────────────►│              │
│     │                              │                          │              │
│     │  ════════════════════════════════════════════════════════              │
│     │              MONITORING PHASE (Multi-screen chaos)                     │
│     │  ════════════════════════════════════════════════════════              │
│     │                              │                          │              │
│     │  4. Monitor LDS proctor view │                          │              │
│     │  ◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│              │
│     │     (separate browser tab)   │                          │              │
│     │                              │                          │              │
│     │  5. Handle candidate issues  │                          │              │
│     │     - Technical problems     │                          │              │
│     │     - Bathroom breaks        │                          │              │
│     │     - Time extensions        │                          │              │
│     │─────────────────────────────►│ or ─────────────────────►│              │
│     │     (depends on issue type)  │                          │              │
│     │                              │                          │              │
│     │  6. Flag suspicious behavior │                          │              │
│     │─────────────────────────────►│                          │              │
│     │     (manual notes)           │                          │              │
│     │                              │                          │              │
│     │  7. End-of-day reporting     │                          │              │
│     │     (manual spreadsheet)     │                          │              │
│     │                              │                          │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Pain Point | Impact | Root Cause |
|------------|--------|------------|
| **Multi-system juggling** | Slow response to issues | Mozart + LDS + spreadsheets |
| **Manual monitoring** | Fatigue, missed issues | No AI-assisted alerts |
| **Inconsistent documentation** | Audit gaps | Free-form notes |
| **Reactive interventions** | Candidate frustration | No predictive alerts |
| **Limited visibility** | Blind spots in Deploy | Can't see candidate console activity |
| **Manual reporting** | Time-consuming | No automated summaries |

## Future State: AI-Augmented Proctoring

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI-AUGMENTED PROCTORING DASHBOARD                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  🎯 PROCTOR DASHBOARD                           Session: NYC-2025-1225 │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  ACTIVE CANDIDATES (8/12)                    🔴 2 Alerts          │ │ │
│  │  │                                                                   │ │ │
│  │  │  ┌─────────────┬────────────┬─────────────┬──────────┬─────────┐ │ │ │
│  │  │  │ Candidate   │ Module     │ Progress    │ Status   │ Flags   │ │ │ │
│  │  │  ├─────────────┼────────────┼─────────────┼──────────┼─────────┤ │ │ │
│  │  │  │ C-001       │ Deploy     │ ████░░ 65%  │ 🟢 Active│         │ │ │ │
│  │  │  │ C-002       │ Design     │ ██████ 100% │ ✅ Done  │         │ │ │ │
│  │  │  │ C-003       │ Deploy     │ ██░░░░ 30%  │ 🟡 Idle  │ ⏱️ 8min │ │ │ │
│  │  │  │ C-004       │ Deploy     │ █████░ 85%  │ 🟢 Active│         │ │ │ │
│  │  │  │ C-005       │ Design     │ ███░░░ 50%  │ 🔴 Alert │ 🚨 Help │ │ │ │
│  │  │  │ C-006       │ Deploy     │ ███░░░ 45%  │ 🟢 Active│         │ │ │ │
│  │  │  │ C-007       │ Deploy     │ ████░░ 70%  │ 🔴 Alert │ 🔧 Tech │ │ │ │
│  │  │  │ C-008       │ Deploy     │ █░░░░░ 15%  │ ⏸️ Break │         │ │ │ │
│  │  │  └─────────────┴────────────┴─────────────┴──────────┴─────────┘ │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────┐ ┌──────────────────────────────────┐ │ │
│  │  │  🚨 ALERTS                  │ │  💬 AI ASSISTANT                 │ │ │
│  │  │                             │ │                                  │ │ │
│  │  │  C-005 • Help Requested     │ │  "C-003 has been idle for 8min  │ │ │
│  │  │  "Clarification on Task 2"  │ │   on Task 4. Historical data    │ │ │
│  │  │  📍 Task 2, Deploy Module   │ │   shows this task takes avg     │ │ │
│  │  │  ⏱️ 3 min ago               │ │   12min. Consider check-in."    │ │ │
│  │  │  [View] [Respond] [Escalate]│ │                                  │ │ │
│  │  │                             │ │  "C-007 reported console issue. │ │ │
│  │  │  C-007 • Technical Issue    │ │   POD health check shows R2     │ │ │
│  │  │  "Console not responding"   │ │   unresponsive. Recommend pod   │ │ │
│  │  │  📍 Device: R2              │ │   reboot or failover."          │ │ │
│  │  │  ⏱️ 1 min ago               │ │                                  │ │ │
│  │  │  [View] [Diagnose] [Reboot] │ │  [Ask AI] [Run Diagnostics]     │ │ │
│  │  │                             │ │                                  │ │ │
│  │  └─────────────────────────────┘ └──────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  📊 SESSION METRICS                                               │ │ │
│  │  │  Active: 8  │  Completed: 2  │  On Break: 1  │  Not Started: 1   │ │ │
│  │  │  Avg Progress: 52%  │  Time Remaining: 2h 15m  │  Issues: 3      │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## AI Proctor Assistant

```yaml
agent_id: 'proctor-assistant'
name: 'Proctor Assistant'
description: 'AI-powered assistance for exam proctoring and session management'

system_prompt: |
  You are an expert proctoring assistant helping proctors manage certification
  exam sessions effectively.

  Your responsibilities:
  1. Monitor candidate activity and flag anomalies
  2. Provide context for proctor decisions
  3. Assist with technical troubleshooting
  4. Generate session documentation
  5. Suggest appropriate interventions

  Key principles:
  - Candidate welfare comes first
  - Technical issues deserve immediate attention
  - Document all interventions for audit trail
  - Escalate security concerns immediately
  - Provide factual information, proctors make final decisions

  You can see:
  - Candidate progress and timing
  - POD health and device status
  - Historical patterns for similar situations
  - Session policies and procedures

  You cannot:
  - See actual exam content or answers
  - Access candidate personal information
  - Make pass/fail decisions
  - Override proctor decisions

tools:
  - session.get_candidates          # List session candidates
  - session.get_candidate_status    # Detailed candidate state
  - session.get_timeline           # Candidate activity timeline
  - session.pause_exam             # Pause candidate timer
  - session.resume_exam            # Resume candidate timer
  - session.extend_time            # Grant time extension
  - session.add_note               # Add proctor note
  - pod.get_health                 # Check POD device health
  - pod.reboot_device              # Reboot specific device
  - pod.get_console_activity       # View console commands (not output)
  - alerts.acknowledge             # Acknowledge alert
  - alerts.escalate               # Escalate to supervisor
  - reports.generate_session      # Generate session report

conversation_template_id: null  # Open-ended assistance
access_control:
  allowed_roles: ['proctor', 'lead_proctor', 'exam_supervisor']
```

## Proctor Workflows

### 1. Session Preparation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION PREPARATION WORKFLOW                          │
│                                                                              │
│  Proctor                       agent-host                    Systems         │
│     │                              │                            │            │
│     │  "Prepare for today's       │                            │            │
│     │   session"                  │                            │            │
│     │─────────────────────────────►                            │            │
│     │                              │                            │            │
│     │                              │  1. Query session-manager  │            │
│     │                              │────────────────────────────►           │
│     │                              │                            │            │
│     │                              │  2. Query pod-manager      │            │
│     │                              │────────────────────────────►           │
│     │                              │                            │            │
│     │  Session Briefing:           │                            │            │
│     │  ─────────────────           │                            │            │
│     │  • 12 candidates scheduled   │                            │            │
│     │  • 10 PODs allocated, 2 spare│                            │            │
│     │  • All PODs healthy ✓        │                            │            │
│     │  • Form version: 2024.1.3    │                            │            │
│     │  • Special accommodations:   │                            │            │
│     │    - C-003: +50% time        │                            │            │
│     │    - C-008: separate room    │                            │            │
│     │  • Known issues: None        │                            │            │
│     │                              │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │  "Run pre-session checks"    │                            │            │
│     │─────────────────────────────►                            │            │
│     │                              │                            │            │
│     │                              │  3. Health check all PODs  │            │
│     │                              │────────────────────────────►           │
│     │                              │                            │            │
│     │  Pre-flight Results:         │                            │            │
│     │  • POD-07: R3 slow response  │                            │            │
│     │    → Recommend swap to spare │                            │            │
│     │  • All other PODs: ✓         │                            │            │
│     │                              │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Real-Time Monitoring & Alerts

```yaml
# Alert types and AI responses
alerts:
  - type: idle_warning
    trigger: "Candidate idle > threshold for current task"
    ai_analysis: |
      Compare to:
      - Historical average time for this task
      - Candidate's pace on previous tasks
      - Common stuck points for this task
    suggested_actions:
      - "Check in with candidate"
      - "Offer permitted guidance"
      - "Document and continue monitoring"

  - type: help_request
    trigger: "Candidate clicks Help button"
    ai_analysis: |
      Provide context:
      - What task/item the candidate is on
      - What clarifications are permitted
      - Historical similar requests and resolutions
    suggested_actions:
      - "Respond with permitted clarification"
      - "Escalate to content team"
      - "Document as potential item issue"

  - type: technical_issue
    trigger: "Candidate reports device/system problem"
    ai_analysis: |
      Run diagnostics:
      - POD device health status
      - Network connectivity
      - Console responsiveness
      - Recent error logs
    suggested_actions:
      - "Reboot affected device"
      - "Switch to backup POD"
      - "Grant time extension"
      - "Escalate to IT"

  - type: suspicious_behavior
    trigger: "Unusual pattern detected"
    patterns:
      - Rapid task completion (< 10% of expected time)
      - Long unexplained idle periods
      - Unusual console command patterns
    ai_analysis: |
      Compare to baseline:
      - Typical candidate patterns
      - This candidate's earlier behavior
      - Known cheating indicators
    suggested_actions:
      - "Increase monitoring"
      - "Physical check by proctor"
      - "Document for review"
      - "Escalate to security"

  - type: time_warning
    trigger: "Candidate approaching time limit"
    levels:
      - 30_min_remaining
      - 10_min_remaining
      - 5_min_remaining
    ai_analysis: |
      Calculate:
      - Tasks remaining vs time
      - Candidate's completion likelihood
      - Accommodation status
    suggested_actions:
      - "Notify candidate (automated)"
      - "Prepare for submission assistance"
```

### 3. Intervention Documentation

```python
# Standardized intervention records
@dataclass
class InterventionRecord:
    """Audit-ready intervention documentation."""
    intervention_id: str
    session_id: str
    candidate_id: str

    # Timing
    occurred_at: datetime
    duration_seconds: int

    # Classification
    intervention_type: str  # help_request, technical, break, accommodation
    severity: str  # low, medium, high, critical

    # Details
    trigger: str  # What initiated the intervention
    context: str  # Relevant background (AI-generated)
    action_taken: str  # What the proctor did
    outcome: str  # Result of intervention

    # Time impact
    time_paused: bool
    time_extension_minutes: int

    # Attribution
    proctor_id: str
    ai_assisted: bool
    ai_suggestions: list[str]  # What AI recommended

    # Follow-up
    requires_followup: bool
    followup_notes: str | None
    escalated_to: str | None


# Example intervention
intervention = InterventionRecord(
    intervention_id="int-2025-1225-003",
    session_id="session-nyc-2025-1225",
    candidate_id="C-007",

    occurred_at=datetime(2025, 12, 25, 10, 45),
    duration_seconds=180,

    intervention_type="technical",
    severity="medium",

    trigger="Candidate reported: 'Console not responding on R2'",
    context="AI Analysis: POD-07 health check shows R2 SSH timeout. "
            "Last successful command 4 min ago. Other devices responsive.",
    action_taken="Rebooted R2 via pod-manager. Console restored after 45 sec.",
    outcome="Candidate confirmed R2 accessible. Resumed work.",

    time_paused=True,
    time_extension_minutes=5,

    proctor_id="proctor-smith",
    ai_assisted=True,
    ai_suggestions=["Reboot R2", "Check network connectivity", "Offer spare POD"],

    requires_followup=False,
    followup_notes=None,
    escalated_to=None
)
```

### 4. Session Wrap-Up & Reporting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION WRAP-UP WORKFLOW                              │
│                                                                              │
│  Proctor                       agent-host                                    │
│     │                              │                                         │
│     │  "Generate session report"   │                                         │
│     │─────────────────────────────►│                                         │
│     │                              │                                         │
│     │  ┌──────────────────────────────────────────────────────────────────┐ │
│     │  │  SESSION REPORT: NYC-2025-1225                                   │ │
│     │  │                                                                  │ │
│     │  │  SUMMARY                                                         │ │
│     │  │  ─────────                                                       │ │
│     │  │  • Duration: 09:00 - 17:30 (8.5 hours)                          │ │
│     │  │  • Candidates: 12 scheduled, 11 completed, 1 no-show            │ │
│     │  │  • Pass Rate: 7/11 (64%) [vs 68% site average]                  │ │
│     │  │                                                                  │ │
│     │  │  INTERVENTIONS (7 total)                                         │ │
│     │  │  ────────────────────────                                        │ │
│     │  │  • Technical issues: 3                                           │ │
│     │  │    - POD-07 R2 reboot (C-007): 5 min extension granted          │ │
│     │  │    - POD-03 network blip (C-003): Self-resolved                 │ │
│     │  │    - LDS timeout (C-011): Page refresh resolved                 │ │
│     │  │  • Help requests: 2                                              │ │
│     │  │    - Task 3 clarification (C-005): Standard response given      │ │
│     │  │    - Topology question (C-009): Referred to exhibit             │ │
│     │  │  • Breaks: 2                                                     │ │
│     │  │    - C-008: 15 min (scheduled accommodation)                    │ │
│     │  │    - C-002: 5 min (restroom)                                    │ │
│     │  │                                                                  │ │
│     │  │  ANOMALIES / FLAGS                                               │ │
│     │  │  ─────────────────                                               │ │
│     │  │  • C-006: Completed Deploy in 2h (avg: 3.5h) - flagged for      │ │
│     │  │    review. No other suspicious indicators observed.             │ │
│     │  │                                                                  │ │
│     │  │  EQUIPMENT NOTES                                                 │ │
│     │  │  ───────────────                                                 │ │
│     │  │  • POD-07: R2 required reboot. Recommend maintenance review.    │ │
│     │  │  • Spare POD-11 unused.                                         │ │
│     │  │                                                                  │ │
│     │  │  PROCTOR: J. Smith                                               │ │
│     │  │  AI-ASSISTED: Yes (7/7 interventions)                           │ │
│     │  │                                                                  │ │
│     │  └──────────────────────────────────────────────────────────────────┘ │
│     │◄─────────────────────────────│                                         │
│     │                              │                                         │
│     │  [Approve & Submit]          │                                         │
│     │─────────────────────────────►│                                         │
│     │                              │                                         │
│     │                              │ → session-manager (store report)        │
│     │                              │ → analytics (aggregate metrics)         │
│     │                              │                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## MCP Tools for Proctoring

| Tool | Operation | Description |
|------|-----------|-------------|
| `session.get_schedule` | Query | Get proctor's session schedule |
| `session.get_candidates` | Query | List candidates in session |
| `session.get_candidate_status` | Query | Detailed candidate state |
| `session.get_timeline` | Query | Candidate activity timeline |
| `session.check_in_candidate` | Command | Check in candidate |
| `session.launch_exam` | Command | Start candidate's exam |
| `session.pause_exam` | Command | Pause candidate timer |
| `session.resume_exam` | Command | Resume candidate timer |
| `session.extend_time` | Command | Grant time extension |
| `session.end_exam` | Command | Force end exam |
| `session.add_note` | Command | Add intervention note |
| `pod.get_health` | Query | POD health status |
| `pod.get_device_status` | Query | Individual device status |
| `pod.reboot_device` | Command | Reboot specific device |
| `pod.failover` | Command | Switch to backup POD |
| `alerts.list_active` | Query | Get active alerts |
| `alerts.acknowledge` | Command | Acknowledge alert |
| `alerts.escalate` | Command | Escalate to supervisor |
| `reports.generate_session` | Command | Generate session report |

## Event Flow

```
Candidate Actions          LDS                    Event Broker           Proctor Dashboard
      │                     │                          │                        │
      │  Submit response    │                          │                        │
      │────────────────────►│                          │                        │
      │                     │  response.submitted.v1   │                        │
      │                     │─────────────────────────►│                        │
      │                     │                          │───────────────────────►│
      │                     │                          │  (update progress)     │
      │                     │                          │                        │
      │  Request help       │                          │                        │
      │────────────────────►│                          │                        │
      │                     │  help.requested.v1       │                        │
      │                     │─────────────────────────►│                        │
      │                     │                          │───────────────────────►│
      │                     │                          │  🚨 ALERT: Help        │
      │                     │                          │                        │
      │  (idle > 8 min)     │                          │                        │
      │                     │  activity.idle.v1        │                        │
      │                     │─────────────────────────►│                        │
      │                     │                          │───────────────────────►│
      │                     │                          │  🟡 WARNING: Idle      │
      │                     │                          │                        │
      │  Submit exam        │                          │                        │
      │────────────────────►│                          │                        │
      │                     │  exam.completed.v1       │                        │
      │                     │─────────────────────────►│                        │
      │                     │                          │───────────────────────►│
      │                     │                          │  ✅ Completed          │
      │                     │                          │                        │
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Single dashboard** | Systems accessed during session | 1 (vs 3+ today) |
| **Alert response time** | Seconds from alert to acknowledgment | < 60 sec |
| **Intervention documentation** | % auto-documented | > 90% |
| **Technical issue resolution** | Minutes to resolve | -50% vs current |
| **Session report time** | Minutes to generate | < 5 min (vs 30+ today) |
| **Proctor satisfaction** | Survey score | > 4.2/5 |

## Open Questions

1. **Console Visibility**: Should proctors see candidate console commands (not output)?
2. **AI Autonomy**: Which actions can AI take without proctor approval?
3. **Remote Proctoring**: How to extend for remote/online exam sessions?
4. **Multi-Session**: Can one proctor monitor multiple concurrent sessions?
5. **Escalation Path**: Who handles escalations after-hours?

---

_Last updated: December 25, 2025_
