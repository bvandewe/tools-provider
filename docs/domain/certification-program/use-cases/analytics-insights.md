# Use Case: Analytics & Insights

> **Primary Actor:** Analyst
> **Supporting Actors:** CertificationOwner (EPM), AI Analytics Agent
> **Systems Involved:** analytics-platform (new), CloudEvent store, Elastic, OTEL collectors, knowledge-manager, agent-host

## Overview

Analytics & Insights enables data-driven decision making for the Certification Program. This is currently a **huge gap**—Analysts have no direct access to exam data—and represents a **major AI opportunity** for automated insight extraction.

## Current State: The Data Silo Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT DATA LANDSCAPE                               │
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │   Mosaic    │   │     LDS     │   │   Grading   │   │ pod-manager │      │
│  │  (Content)  │   │  (Delivery) │   │   System    │   │  (Devices)  │      │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│         │                 │                 │                 │              │
│         ▼                 ▼                 ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         DATA SILOS                                   │    │
│  │                                                                      │    │
│  │  • Mosaic DB (items, blueprints)        ← No API for analytics      │    │
│  │  • LDS logs (candidate behavior)        ← Elastic, limited access   │    │
│  │  • CloudEvent store (system events)     ← Raw events, no dashboards │    │
│  │  • Grading results (scores)             ← Separate DB, manual export│    │
│  │  • OTEL traces (performance)            ← Just starting deployment  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│                                 ❌                                           │
│                                                                              │
│                            Analyst                                           │
│                    "I need to understand                                     │
│                     why candidates fail                                      │
│                     Task 3..."                                               │
│                                                                              │
│                    Current workflow:                                         │
│                    1. Email IT for data export                               │
│                    2. Wait days/weeks                                        │
│                    3. Receive CSV files                                      │
│                    4. Manual Excel analysis                                  │
│                    5. Limited to simple metrics                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Pain Point | Impact | Root Cause |
|------------|--------|------------|
| **No self-service access** | Analysts blocked, slow decisions | Data locked in production DBs |
| **Manual data wrangling** | Hours spent on ETL | No unified data model |
| **Lagging insights** | Reactive, not proactive | Batch exports, not real-time |
| **Limited analysis depth** | Miss root causes | Can't correlate across systems |
| **No predictive capability** | React to problems | No ML/AI on exam data |
| **Compliance risk** | Audit challenges | No clear data lineage |

## Future State: AI-Powered Analytics Platform

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI-POWERED ANALYTICS PLATFORM                           │
│                                                                              │
│  Data Sources                    Analytics Platform                          │
│  ────────────                    ──────────────────                          │
│                                                                              │
│  ┌─────────────┐                ┌──────────────────────────────────────┐    │
│  │ CloudEvents │───────────────►│                                      │    │
│  │   Store     │                │      Unified Analytics Lakehouse     │    │
│  └─────────────┘                │                                      │    │
│                                 │  ┌────────────────────────────────┐  │    │
│  ┌─────────────┐                │  │     Bronze Layer (Raw)         │  │    │
│  │   Elastic   │───────────────►│  │  • CloudEvents                 │  │    │
│  │    Logs     │                │  │  • Logs                        │  │    │
│  └─────────────┘                │  │  • Traces                      │  │    │
│                                 │  └────────────────────────────────┘  │    │
│  ┌─────────────┐                │              │                       │    │
│  │    OTEL     │───────────────►│              ▼                       │    │
│  │  Collectors │                │  ┌────────────────────────────────┐  │    │
│  └─────────────┘                │  │     Silver Layer (Curated)     │  │    │
│                                 │  │  • Exam attempts               │  │    │
│  ┌─────────────┐                │  │  • Item responses              │  │    │
│  │   Mosaic    │───────────────►│  │  • Candidate journeys          │  │    │
│  │    API      │   (CDC/batch)  │  │  • Device states               │  │    │
│  └─────────────┘                │  └────────────────────────────────┘  │    │
│                                 │              │                       │    │
│  ┌─────────────┐                │              ▼                       │    │
│  │  Grading    │───────────────►│  ┌────────────────────────────────┐  │    │
│  │   System    │                │  │     Gold Layer (Analytics)     │  │    │
│  └─────────────┘                │  │  • KSA proficiency scores      │  │    │
│                                 │  │  • Item statistics (p-value)   │  │    │
│                                 │  │  • Cohort comparisons          │  │    │
│                                 │  │  • Anomaly flags               │  │    │
│                                 │  └────────────────────────────────┘  │    │
│                                 │                                      │    │
│                                 └──────────────────────────────────────┘    │
│                                              │                               │
│                                              ▼                               │
│                                 ┌──────────────────────────────────────┐    │
│                                 │       AI Analytics Interface         │    │
│                                 │                                      │    │
│                                 │  Analyst: "Why are candidates        │    │
│                                 │           failing Task 3?"           │    │
│                                 │                                      │    │
│                                 │  AI: "Analysis of 847 attempts:      │    │
│                                 │       • 62% fail neighbor-state      │    │
│                                 │       • Root cause: AS mismatch      │    │
│                                 │       • Correlated with < 2 min      │    │
│                                 │         on requirements doc          │    │
│                                 │       • Recommend: Add explicit      │    │
│                                 │         AS mapping in exhibit"       │    │
│                                 │                                      │    │
│                                 └──────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## AI Analytics Agent

```yaml
agent_id: 'analytics-agent'
name: 'Exam Analytics Agent'
description: 'Conversational interface for exam program analytics and insights'

system_prompt: |
  You are an expert psychometrician and data analyst helping Certification
  Program stakeholders understand exam performance.

  Your capabilities:
  1. Query exam data across all sources (attempts, responses, scores, behavior)
  2. Perform statistical analysis (item statistics, reliability, validity)
  3. Identify patterns and anomalies
  4. Generate visualizations
  5. Provide actionable recommendations

  Key metrics you can compute:
  - Item difficulty (p-value): proportion correct
  - Item discrimination: point-biserial correlation
  - Reliability: Cronbach's alpha, KR-20
  - Pass rate by cohort, location, time period
  - Time-on-task distributions
  - KSA proficiency profiles

  Always:
  - Cite sample sizes and confidence intervals
  - Note data freshness and limitations
  - Protect individual candidate privacy
  - Suggest follow-up analyses

tools:
  - analytics.query_attempts        # Query exam attempts
  - analytics.query_responses       # Query item responses
  - analytics.query_scores          # Query grading results
  - analytics.query_behavior        # Query candidate behavior events
  - analytics.compute_item_stats    # Calculate p-value, discrimination
  - analytics.compute_reliability   # Calculate exam reliability
  - analytics.compare_cohorts       # Compare groups statistically
  - analytics.detect_anomalies      # Find unusual patterns
  - analytics.generate_chart        # Create visualizations
  - analytics.export_report         # Generate PDF/Excel reports
  - knowledge.get_ksa_mapping       # Get KSA definitions

conversation_template_id: null  # Open-ended analysis
access_control:
  allowed_roles: ['analyst', 'certification_owner', 'psychometrician']
```

## Analytics Use Cases

### 1. Item Performance Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ITEM PERFORMANCE DASHBOARD                            │
│                                                                              │
│  Analyst: "Show me item statistics for the Network Certification exam       │
│            from the last 6 months"                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Item Statistics Report                                                │ │
│  │  Exam: Network Certification v2024.1                                   │ │
│  │  Period: Jun 2025 - Dec 2025                                           │ │
│  │  Sample Size: 2,847 attempts                                           │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Item ID    │ p-value │ Discrim │ Avg Time │ Flag             │  │ │
│  │  ├─────────────────────────────────────────────────────────────────┤  │ │
│  │  │ BGP-001    │ 0.72    │ 0.45    │ 45s      │ ✓ Good           │  │ │
│  │  │ BGP-002    │ 0.34    │ 0.52    │ 62s      │ ✓ Good (hard)    │  │ │
│  │  │ BGP-003    │ 0.91    │ 0.12    │ 28s      │ ⚠ Too easy       │  │ │
│  │  │ OSPF-001   │ 0.23    │ 0.08    │ 95s      │ 🚨 Review needed │  │ │
│  │  │ OSPF-002   │ 0.65    │ 0.38    │ 55s      │ ✓ Good           │  │ │
│  │  │ ...        │         │         │          │                  │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  AI Insights:                                                          │ │
│  │  • OSPF-001 has low discrimination (0.08) - high performers and       │ │
│  │    low performers answer similarly. Recommend review for ambiguity.   │ │
│  │  • BGP-003 is too easy (p=0.91) - consider for tutorial, not exam.    │ │
│  │  • Overall reliability (KR-20): 0.84 - within acceptable range.       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Failure Root Cause Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FAILURE ROOT CAUSE ANALYSIS                             │
│                                                                              │
│  Analyst: "Why are candidates failing Task 3 in the Deploy module?"         │
│                                                                              │
│  AI Analytics Agent Response:                                                │
│  ────────────────────────────                                                │
│                                                                              │
│  Analysis of Task 3: "Configure BGP Peering"                                 │
│  Sample: 847 attempts, 523 failures (62% fail rate)                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FAILURE BREAKDOWN BY GRADING CRITERION                              │    │
│  │                                                                      │    │
│  │  Criterion              │ Fail Rate │ Root Cause                     │    │
│  │  ───────────────────────┼───────────┼──────────────────────────────  │    │
│  │  bgp-process-configured │ 8%        │ Minor - forgot to save config  │    │
│  │  neighbor-ip-correct    │ 15%       │ Typos in IP address            │    │
│  │  remote-as-correct      │ 47%       │ ⚠️ Major issue - AS confusion   │    │
│  │  neighbor-established   │ 62%       │ Downstream from above          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  BEHAVIORAL CORRELATIONS                                             │    │
│  │                                                                      │    │
│  │  Candidates who failed (remote-as-correct):                          │    │
│  │  • Spent avg 1.8 min on Requirements doc (vs 4.2 min for passers)    │    │
│  │  • 72% did not open IP Scheme document                               │    │
│  │  • 45% attempted task before reading any resources                   │    │
│  │                                                                      │    │
│  │  Candidates who passed:                                               │    │
│  │  • Spent avg 4.2 min on Requirements doc                             │    │
│  │  • 89% opened both Requirements AND IP Scheme                        │    │
│  │  • 67% started with resource review before any task                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  RECOMMENDATIONS                                                     │    │
│  │                                                                      │    │
│  │  1. Content Change (High Impact):                                    │    │
│  │     Add explicit AS mapping table in IP Scheme document              │    │
│  │     Current: AS numbers buried in Requirements paragraph             │    │
│  │                                                                      │    │
│  │  2. Exhibit Enhancement (Medium Impact):                             │    │
│  │     Add AS labels to topology diagram                                │    │
│  │                                                                      │    │
│  │  3. Task Ordering (Low Impact):                                      │    │
│  │     Suggest recommended starting task in instructions                │    │
│  │                                                                      │    │
│  │  Predicted fail rate after changes: ~35% (vs current 62%)            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Cohort Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COHORT COMPARISON                                   │
│                                                                              │
│  Analyst: "Compare pass rates between training partners A and B"            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Cohort Analysis: Training Partner Comparison                          │ │
│  │  Period: Q3-Q4 2025                                                    │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │         │ Partner A │ Partner B │ Δ      │ Significance        │  │ │
│  │  ├─────────────────────────────────────────────────────────────────┤  │ │
│  │  │ N       │ 342       │ 287       │        │                     │  │ │
│  │  │ Pass %  │ 71%       │ 58%       │ +13%   │ p < 0.01 **         │  │ │
│  │  │ Avg Scr │ 74.2      │ 68.5      │ +5.7   │ p < 0.01 **         │  │ │
│  │  │ Avg Time│ 165 min   │ 178 min   │ -13min │ p < 0.05 *          │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  KSA-Level Breakdown:                                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │ KSA                    │ Partner A │ Partner B │ Gap           │  │ │
│  │  ├─────────────────────────────────────────────────────────────────┤  │ │
│  │  │ NET.BGP.PEER           │ 78%       │ 72%       │ +6%           │  │ │
│  │  │ NET.BGP.TROUBLESHOOT   │ 65%       │ 48%       │ +17% ⚠️       │  │ │
│  │  │ NET.OSPF.CONFIG        │ 82%       │ 79%       │ +3%           │  │ │
│  │  │ NET.SECURITY.ACL       │ 69%       │ 67%       │ +2%           │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  AI Insight:                                                           │ │
│  │  Partner B candidates significantly underperform on BGP Troubleshoot-  │ │
│  │  ing (17% gap). Recommend reviewing Partner B's lab curriculum for     │ │
│  │  troubleshooting methodology coverage.                                 │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Anomaly Detection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANOMALY DETECTION                                    │
│                                                                              │
│  Automated Alert: Unusual pattern detected                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  🚨 ANOMALY ALERT: Potential Content Exposure                          │ │
│  │                                                                        │ │
│  │  Pattern: Sudden improvement in Task 7 performance                      │ │
│  │                                                                        │ │
│  │  Task 7 Success Rate:                                                   │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │  100% ┤                                          ╭───────────    │  │ │
│  │  │   80% ┤                                     ╭────╯               │  │ │
│  │  │   60% ┤  ─────────────────────────────────╮╯                     │  │ │
│  │  │   40% ┤                                   │                      │  │ │
│  │  │   20% ┤                                   │                      │  │ │
│  │  │    0% ┼──────────────────────────────────────────────────────    │  │ │
│  │  │       Jun   Jul   Aug   Sep   Oct   Nov   Dec                    │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  Detection Details:                                                     │ │
│  │  • Baseline success rate (Jun-Oct): 42% ± 5%                           │ │
│  │  • Current success rate (Nov-Dec): 78%                                 │ │
│  │  • Statistical significance: p < 0.001                                 │ │
│  │  • Response pattern similarity: 89% (unusually high)                   │ │
│  │                                                                        │ │
│  │  Correlated Signals:                                                    │ │
│  │  • Average time on Task 7: decreased from 18min to 8min                │ │
│  │  • Candidates from Site X: 95% success (vs 45% elsewhere)              │ │
│  │  • No change in other task performance                                 │ │
│  │                                                                        │ │
│  │  Recommendation:                                                        │ │
│  │  HIGH PRIORITY: Investigate potential content leak for Task 7          │ │
│  │  Consider rotating Task 7 content or increasing parameterization       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Model

### Silver Layer: Curated Facts

```python
@dataclass
class ExamAttemptFact:
    """Curated exam attempt record."""
    attempt_id: str
    candidate_id: str  # Pseudonymized
    exam_id: str
    form_id: str
    session_id: str

    # Temporal
    started_at: datetime
    completed_at: datetime
    duration_minutes: int

    # Location
    site_id: str
    delivery_mode: str  # proctored, remote, practice

    # Outcome
    passed: bool
    total_score: float
    scaled_score: float
    percentile: float | None

    # Metadata
    form_version: str
    grading_version: str
    collected_at: datetime


@dataclass
class ItemResponseFact:
    """Individual item response record."""
    response_id: str
    attempt_id: str
    item_id: str
    slot_id: str  # Position in form

    # Timing
    presented_at: datetime
    responded_at: datetime | None
    time_spent_seconds: int

    # Response
    response_value: str | None  # Anonymized
    is_correct: bool | None  # None for practical items
    score: float
    max_score: float

    # Item metadata
    ksa_id: str
    topic_id: str
    difficulty_target: float

    # Flags
    flagged_for_review: bool
    skipped: bool


@dataclass
class CandidateBehaviorEvent:
    """Behavioral event during exam."""
    event_id: str
    attempt_id: str

    event_type: str  # resource_opened, task_started, console_command, etc.
    event_timestamp: datetime

    # Context
    resource_id: str | None
    task_id: str | None
    device_id: str | None

    # Details
    event_data: dict  # Type-specific payload
    duration_seconds: int | None
```

### Gold Layer: Analytics Aggregates

```python
@dataclass
class ItemStatistics:
    """Psychometric statistics for an item."""
    item_id: str
    calculation_date: date
    sample_size: int

    # Difficulty
    p_value: float  # Proportion correct (0-1)
    p_value_ci_lower: float
    p_value_ci_upper: float

    # Discrimination
    point_biserial: float  # Correlation with total score
    discrimination_index: float  # Upper - lower 27%

    # Timing
    avg_time_seconds: float
    median_time_seconds: float
    time_std_dev: float

    # Response distribution (for MCQ)
    option_frequencies: dict[str, float]  # option → proportion

    # Flags
    needs_review: bool
    flag_reasons: list[str]


@dataclass
class KSAProficiencyProfile:
    """Candidate proficiency across KSAs."""
    candidate_id: str  # Pseudonymized
    exam_id: str
    attempt_id: str

    ksa_scores: dict[str, KSAScore]

    # Diagnostic
    strengths: list[str]  # Top KSAs
    weaknesses: list[str]  # Bottom KSAs
    recommended_remediation: list[str]


@dataclass
class KSAScore:
    """Score for a single KSA."""
    ksa_id: str
    ksa_name: str

    score: float
    max_score: float
    percentage: float

    item_count: int
    items_correct: int

    proficiency_level: str  # Developing, Competent, Proficient
```

## MCP Tools for Analytics

| Tool | Operation | Description |
|------|-----------|-------------|
| `analytics.query_attempts` | Query | Filter/aggregate exam attempts |
| `analytics.query_responses` | Query | Query item-level responses |
| `analytics.query_behavior` | Query | Query behavioral events |
| `analytics.compute_item_stats` | Query | Calculate item psychometrics |
| `analytics.compute_reliability` | Query | Calculate exam reliability |
| `analytics.compare_cohorts` | Query | Statistical comparison |
| `analytics.detect_anomalies` | Query | Pattern anomaly detection |
| `analytics.generate_chart` | Command | Create visualization |
| `analytics.export_report` | Command | Generate downloadable report |
| `analytics.schedule_report` | Command | Set up recurring report |

### Example Tool Usage

```python
# Query exam attempts with filters
query = {
    "exam_id": "network-cert-2024",
    "date_range": {"start": "2025-06-01", "end": "2025-12-31"},
    "filters": {
        "delivery_mode": "proctored",
        "site_id": ["site-nyc", "site-sfo"]
    },
    "group_by": ["month", "site_id"],
    "metrics": ["count", "pass_rate", "avg_score"]
}

result = await analytics.query_attempts(query)

# Returns:
{
    "data": [
        {"month": "2025-06", "site_id": "site-nyc", "count": 142, "pass_rate": 0.68, "avg_score": 72.4},
        {"month": "2025-06", "site_id": "site-sfo", "count": 98, "pass_rate": 0.71, "avg_score": 74.1},
        ...
    ],
    "total_count": 2847,
    "query_time_ms": 234
}
```

## Event-Driven Analytics Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EVENT-DRIVEN ANALYTICS PIPELINE                           │
│                                                                              │
│  Source Systems          Event Broker           Analytics Platform           │
│                                                                              │
│  ┌─────────────┐                                                             │
│  │    LDS      │─── exam.started.v1 ────────►┌─────────────────────────┐    │
│  │             │─── response.submitted.v1 ──►│                         │    │
│  │             │─── exam.completed.v1 ──────►│   Stream Processor      │    │
│  └─────────────┘                             │   (Kafka/Flink/Spark)   │    │
│                                              │                         │    │
│  ┌─────────────┐                             │   • Enrich events       │    │
│  │   Grading   │─── grading.completed.v1 ───►│   • Compute metrics     │    │
│  │   System    │                             │   • Detect anomalies    │    │
│  └─────────────┘                             │   • Update aggregates   │    │
│                                              │                         │    │
│  ┌─────────────┐                             └───────────┬─────────────┘    │
│  │   Mosaic    │─── item.published.v1 ──────►            │                  │
│  │             │─── blueprint.updated.v1 ───►            │                  │
│  └─────────────┘                                         │                  │
│                                                          ▼                  │
│                                              ┌─────────────────────────┐    │
│                                              │   Analytics Lakehouse   │    │
│                                              │                         │    │
│                                              │   Bronze │ Silver │ Gold│    │
│                                              │   (raw)  │(curated)│(agg)│   │
│                                              └─────────────────────────┘    │
│                                                          │                  │
│                                                          ▼                  │
│                                              ┌─────────────────────────┐    │
│                                              │   AI Analytics Agent    │    │
│                                              │   (agent-host)          │    │
│                                              └─────────────────────────┘    │
│                                                          │                  │
│                                                          ▼                  │
│                                                      Analyst               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Privacy & Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Data Minimization** | Pseudonymize candidate IDs in analytics layer |
| **Access Control** | Role-based access to different data levels |
| **Audit Trail** | Log all analyst queries and exports |
| **Retention** | Configurable retention per data category |
| **Right to Erasure** | Pseudonymization key deletion capability |
| **Data Lineage** | Track data from source to insight |

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Self-service access** | % queries via AI agent vs manual | > 80% |
| **Query latency** | Time from question to insight | < 30 sec |
| **Data freshness** | Lag from event to queryable | < 5 min |
| **Analyst satisfaction** | Survey score | > 4.5/5 |
| **Anomaly detection** | Content exposure detected within | < 7 days |
| **Report automation** | % recurring reports automated | > 90% |

## Open Questions

1. **Data Warehouse Technology**: Snowflake, Databricks, BigQuery, or self-hosted?
2. **Real-time vs Batch**: Which analyses need real-time? Which can be daily batch?
3. **PII Handling**: Pseudonymization strategy for candidate data?
4. **Historical Data**: How far back to migrate existing data?
5. **Cost Model**: Who pays for analytics compute/storage?

---

_Last updated: December 25, 2025_
