# Use Case: Candidate Personalized Feedback

> **Primary Actor:** Candidate (post-exam)
> **Supporting Actors:** AI Feedback Coach
> **Systems Involved:** Score Reporting Portal, agent-host, grading-system, analytics lakehouse

## Overview

Failing a certification exam is discouraging. Many candidates who fail don't return—not because they can't pass, but because they lose confidence and don't understand _what_ to improve. This use case transforms the score report from a static document into an interactive coaching experience that builds confidence, provides actionable guidance, and improves retention rates.

## The Retention Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THE RETENTION FUNNEL                                 │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     First Attempt: 1000 Candidates                   │   │
│   │                              ▼                                       │   │
│   │   ┌─────────────────┐   ┌─────────────────────┐                     │   │
│   │   │  Pass: 650      │   │  Fail: 350           │                     │   │
│   │   │  (65%)          │   │  (35%)               │                     │   │
│   │   └─────────────────┘   └──────────┬──────────┘                     │   │
│   │                                     │                                │   │
│   │                                     ▼                                │   │
│   │   ┌────────────────────────────────────────────────────────────────┐│   │
│   │   │                  CURRENT STATE                                 ││   │
│   │   │                                                                ││   │
│   │   │  Failed candidates receive:                                    ││   │
│   │   │  • Overall score (e.g., "68% - Did Not Pass")                 ││   │
│   │   │  • Section breakdowns (e.g., "Troubleshooting: Below Passing") ││   │
│   │   │  • Generic study recommendations                               ││   │
│   │   │                                                                ││   │
│   │   │  Result:                                                       ││   │
│   │   │  • Only ~40% schedule a retake (140 of 350)                   ││   │
│   │   │  • 60% abandon the certification (210 lost)                   ││   │
│   │   │                                                                ││   │
│   │   │  Why they leave:                                               ││   │
│   │   │  • "I don't know what I did wrong"                            ││   │
│   │   │  • "The feedback doesn't help me"                             ││   │
│   │   │  • "Maybe I'm just not cut out for this"                      ││   │
│   │   │  • "The exam felt unfair/unclear"                             ││   │
│   │   │                                                                ││   │
│   │   └────────────────────────────────────────────────────────────────┘│   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ╔═══════════════════════════════════════════════════════════════════════╗ │
│   ║  OPPORTUNITY: If retention improves from 40% to 60%...               ║ │
│   ║                                                                       ║ │
│   ║  • 70 additional retakes × $400 = $28,000 revenue per cohort         ║ │
│   ║  • More certified professionals in the ecosystem                     ║ │
│   ║  • Higher candidate satisfaction and brand perception                ║ │
│   ║                                                                       ║ │
│   ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Key Constraint: No Content Disclosure

The AI coach must improve candidate understanding _without_ revealing:

- Specific questions or tasks
- Correct answers or solutions
- Exact configurations or commands
- Grading criteria details

This is both a security requirement (protect exam integrity) and a legal/contractual obligation.

## AI Feedback Coach

```yaml
agent_id: 'feedback-coach'
name: 'Certification Feedback Coach'
description: 'Post-exam coaching for personalized improvement guidance'

system_prompt: |
  You are a supportive certification feedback coach. Your role is to help
  candidates understand their exam performance and develop a personalized
  improvement plan—WITHOUT revealing any exam content.

  ## Your Mission

  Transform "I failed and don't know why" into "I understand my gaps and
  have a clear path forward."

  ## What You Can Discuss

  ✅ PERMITTED:
  - KSA categories and skill areas (from blueprint)
  - General performance patterns (time management, approach)
  - Study strategies and resources
  - Exam-taking techniques
  - Soft skills and mindset
  - Retake timing and preparation

  ❌ PROHIBITED:
  - Specific tasks or questions
  - Correct answers or solutions
  - What commands/configurations were expected
  - Which specific items were missed
  - Detailed grading criteria

  ## Coaching Approach

  1. **Acknowledge feelings**: Failing is hard. Start with empathy.
  2. **Reframe the narrative**: This is data, not judgment.
  3. **Focus on patterns**: What skill areas need attention?
  4. **Provide actionable guidance**: Specific study recommendations.
  5. **Build confidence**: Many candidates pass on second attempt.

  ## Available Data

  You have access to:
  - Performance by KSA category (aggregated, not item-level)
  - Time management patterns (rushed sections, pacing)
  - Comparison to successful candidates (anonymized patterns)
  - Exam blueprint (topics, skills, KSA statements)
  - Recommended study resources per topic

  ## Tone

  - Warm but professional
  - Encouraging without being patronizing
  - Honest about gaps without being harsh
  - Action-oriented and forward-looking

tools:
  - feedback.get_performance_summary   # Aggregated KSA performance
  - feedback.get_time_analysis        # How time was spent
  - feedback.get_pattern_comparison   # vs successful candidates
  - feedback.get_blueprint           # Exam structure and KSAs
  - feedback.get_study_resources     # Recommended materials
  - feedback.get_retake_info         # Retake policies and timing

conversation_template_id: 'feedback-session-template'
access_control:
  allowed_roles: ['candidate']
  context_restrictions:
    - exam_completed
    - feedback_period_active  # Available for 30 days post-exam
```

## Feedback Dimensions

### 1. KSA-Based Performance (What to Study)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KSA PERFORMANCE ANALYSIS                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  YOUR PERFORMANCE BY SKILL AREA                                      │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ NETWORK INFRASTRUCTURE                                         │ │   │
│  │  │ ████████████████████░░░░░░░░░░░░░░░░░░░░ 52%                   │ │   │
│  │  │ ⚠️ Below expectations • Focus area                            │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ SECURITY IMPLEMENTATION                                        │ │   │
│  │  │ ██████████████████████████████░░░░░░░░░░ 75%                   │ │   │
│  │  │ ✓ Meets expectations                                          │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ TROUBLESHOOTING & VERIFICATION                                 │ │   │
│  │  │ ██████████████████████████████████████░░ 90%                   │ │   │
│  │  │ ✓ Exceeds expectations • Strength                             │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ AUTOMATION & PROGRAMMABILITY                                   │ │   │
│  │  │ █████████████████████████████░░░░░░░░░░░ 70%                   │ │   │
│  │  │ ~ Near threshold • Review recommended                          │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  💬 Coach says:                                                              │
│  "Your troubleshooting skills are excellent—that's a real strength to       │
│   build on. The gap in Network Infrastructure suggests focusing your        │
│   study on foundational routing and switching concepts. Would you like     │
│   me to break down what specific KSAs within that area need attention?"    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Time Management Analysis (How to Approach)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TIME MANAGEMENT ANALYSIS                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  YOUR TIME ALLOCATION VS. SUCCESSFUL CANDIDATES                      │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ DESIGN MODULE                                                  │ │   │
│  │  │                                                                │ │   │
│  │  │ You:        ████████████████████████████████░░░░ 2h 15m       │ │   │
│  │  │ Successful: ██████████████████████████░░░░░░░░░░ 1h 45m (avg) │ │   │
│  │  │                                                                │ │   │
│  │  │ ⚠️ You spent 30 min longer than average on this module        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ DEPLOY MODULE                                                  │ │   │
│  │  │                                                                │ │   │
│  │  │ You:        ████████████████████░░░░░░░░░░░░░░░░ 2h 45m       │ │   │
│  │  │ Successful: ██████████████████████████████░░░░░░ 3h 30m (avg) │ │   │
│  │  │                                                                │ │   │
│  │  │ ⚠️ You had 45 min less than average—may have felt rushed      │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Pattern detected: FRONT-LOADED                                      │   │
│  │  You spent more time on early sections, leaving less for later.      │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  💬 Coach says:                                                              │
│  "I see a pattern here that's common: spending extra time on the Design    │
│   module can leave you rushed in Deploy, where complex tasks need more     │
│   time. Consider practicing time-boxing during preparation—for example,    │
│   setting a 2-hour limit for Design in practice sessions. Would you like  │
│   some time management strategies for lab exams?"                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Soft Skills & Exam Strategy (How to Think)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOFT SKILLS ASSESSMENT                                    │
│                                                                              │
│  Based on behavioral patterns observed during your exam:                     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  📖 TASK READING                                                     │   │
│  │  ─────────────────                                                   │   │
│  │  Observation: Quick initial reads, occasional revisits               │   │
│  │  Suggestion: Consider reading each task twice before starting        │   │
│  │              Many candidates miss key details on first read          │   │
│  │                                                                      │   │
│  │  🔍 VERIFICATION HABITS                                              │   │
│  │  ────────────────────                                                │   │
│  │  Observation: Limited verification commands in console history       │   │
│  │  Suggestion: Build a habit of "configure, then verify" for every    │   │
│  │              change. Successful candidates verify 3x more often.    │   │
│  │                                                                      │   │
│  │  📋 DOCUMENTATION USE                                                │   │
│  │  ─────────────────────                                               │   │
│  │  Observation: Resources panel accessed infrequently                  │   │
│  │  Suggestion: The provided documentation often contains hints about  │   │
│  │              expected outcomes. Consider referring to it more.      │   │
│  │                                                                      │   │
│  │  🎯 TASK SEQUENCING                                                  │   │
│  │  ─────────────────                                                   │   │
│  │  Observation: Linear progression through tasks                       │   │
│  │  Suggestion: In Deploy module, consider scanning all tasks first    │   │
│  │              to identify dependencies and quick wins.               │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  💬 Coach says:                                                              │
│  "These aren't about knowledge—they're about approach. The good news:       │
│   these habits are easy to build with practice. Many candidates improve    │
│   significantly just by being more deliberate about verification.          │
│   Should we discuss specific verification techniques for the skill         │
│   areas you struggled with?"                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Conversation Flow

```yaml
# Feedback Session Template
template_id: 'feedback-session-template'
name: 'Personalized Feedback Session'

phases:
  - id: 'acknowledge'
    name: 'Acknowledge & Empathize'
    goals:
      - Validate the candidate's feelings
      - Establish supportive tone
      - Gather candidate's perspective
    sample_prompts:
      - "I see you recently completed the certification exam. How are you feeling about the experience?"
      - "What's your initial reaction to the results?"
    transitions:
      - when: "candidate expresses frustration or disappointment"
        respond_with: "It's completely normal to feel that way. Failing an exam, especially one you've worked hard for, is tough. But here's what I want you to know—this is data about your current skills, not a judgment of your potential."
      - when: "candidate asks what went wrong"
        go_to: 'performance_review'

  - id: 'performance_review'
    name: 'Performance Deep-Dive'
    goals:
      - Present KSA performance clearly
      - Identify patterns without revealing content
      - Connect gaps to study areas
    tools_available:
      - feedback.get_performance_summary
      - feedback.get_blueprint
    sample_prompts:
      - "Let me walk you through your performance by skill area..."
      - "I see some clear patterns here. Your strength is in [X], while [Y] is an area for growth."
    transitions:
      - when: "candidate asks for specifics"
        respond_with: "I can't share specific questions, but I can tell you that within [skill area], the KSAs you'll want to focus on are..."
      - when: "candidate understands gaps"
        go_to: 'strategy_review'

  - id: 'strategy_review'
    name: 'Approach & Strategy'
    goals:
      - Review time management patterns
      - Discuss soft skills and habits
      - Identify exam-taking improvements
    tools_available:
      - feedback.get_time_analysis
      - feedback.get_pattern_comparison
    sample_prompts:
      - "Beyond the technical skills, there are some exam strategies that could help..."
      - "Let's look at how you managed your time compared to successful candidates."
    transitions:
      - when: "candidate asks for study resources"
        go_to: 'action_plan'
      - when: "candidate questions fairness"
        respond_with: "I understand that concern. The exam is designed to be challenging but fair. Let me show you how your experience compares to others..."

  - id: 'action_plan'
    name: 'Create Action Plan'
    goals:
      - Recommend specific study resources
      - Create timeline to retake
      - Set achievable milestones
    tools_available:
      - feedback.get_study_resources
      - feedback.get_retake_info
    sample_prompts:
      - "Based on your gaps, here's what I recommend focusing on..."
      - "Many candidates in your situation pass on their second attempt. Here's a suggested 4-week plan..."
    transitions:
      - when: "candidate commits to retake"
        go_to: 'confidence_building'
      - when: "candidate unsure about retaking"
        respond_with: "That's a valid consideration. Let's talk about what would help you feel confident about trying again..."

  - id: 'confidence_building'
    name: 'Build Confidence'
    goals:
      - Reinforce strengths
      - Share success statistics
      - End on positive note
    sample_prompts:
      - "Before we wrap up, I want to highlight your strengths again..."
      - "Candidates who follow a focused study plan like this have a [X]% pass rate on retake."
      - "You've got a clear path forward. Any final questions?"
```

## Data Model

```python
@dataclass
class CandidateFeedbackProfile:
    """Aggregated performance data for feedback (no item-level detail)."""
    candidate_id: str  # Anonymized for AI
    exam_id: str
    attempt_number: int
    exam_date: datetime

    # Overall
    passed: bool
    overall_score_bucket: str  # "significantly_below", "near_threshold", "meets", "exceeds"

    # KSA Performance (aggregated)
    ksa_performance: dict[str, KsaPerformance]

    # Time patterns
    time_allocation: TimeAnalysis

    # Behavioral patterns (derived from telemetry)
    soft_skills: SoftSkillsAssessment

    # Comparison data (anonymized)
    comparison_to_passers: PatternComparison


@dataclass
class KsaPerformance:
    """Performance for a KSA category."""
    ksa_category: str
    ksa_description: str

    # Bucket-based (not percentage to avoid reverse engineering)
    performance_level: str  # "significantly_below", "below", "meets", "exceeds"
    is_focus_area: bool

    # Related study resources
    recommended_resources: list[StudyResource]


@dataclass
class TimeAnalysis:
    """Time management patterns."""
    total_time_used: timedelta
    total_time_allowed: timedelta

    # By module
    design_time: timedelta
    design_time_vs_average: str  # "under", "typical", "over"
    deploy_time: timedelta
    deploy_time_vs_average: str

    # Pattern
    pacing_pattern: str  # "front_loaded", "even", "back_loaded", "rushed_throughout"
    time_pressure_indicators: list[str]


@dataclass
class SoftSkillsAssessment:
    """Behavioral observations (derived, not item-specific)."""
    task_reading_pattern: str
    verification_frequency: str  # "low", "moderate", "high"
    documentation_usage: str  # "low", "moderate", "high"
    task_sequencing: str  # "linear", "strategic", "scattered"
    help_request_pattern: str

    # Recommendations
    improvement_areas: list[str]
    recommended_practices: list[str]


@dataclass
class StudyResource:
    """Study recommendation."""
    resource_type: str  # "course", "lab", "documentation", "practice_exam"
    title: str
    url: str
    relevance_score: float
    estimated_duration: str
```

## Privacy & Security

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA FLOW & PRIVACY                                       │
│                                                                              │
│   Grading System          Analytics Lakehouse          AI Feedback Coach    │
│        │                        │                            │              │
│        │  Item-level results    │                            │              │
│        │───────────────────────►│                            │              │
│        │  (Task 1: Pass,        │                            │              │
│        │   Task 2: Partial,     │  ┌─────────────────────┐   │              │
│        │   Task 3: Fail...)     │  │ AGGREGATION LAYER   │   │              │
│        │                        │  │                     │   │              │
│        │                        │  │ • Roll up to KSA    │   │              │
│        │                        │  │ • Remove item refs  │   │              │
│        │                        │  │ • Compute patterns  │   │              │
│        │                        │  │ • Anonymize IDs     │   │              │
│        │                        │  │                     │   │              │
│        │                        │  └──────────┬──────────┘   │              │
│        │                        │             │              │              │
│        │                        │             │              │              │
│        │                        │             │  Aggregated  │              │
│        │                        │             │  profile     │              │
│        │                        │             │─────────────►│              │
│        │                        │             │              │              │
│        │                        │             │              │  Candidate   │
│        │                        │             │              │  sees only   │
│        │                        │             │              │  aggregated  │
│        │                        │             │              │  feedback    │
│        │                        │             │              │              │
│   ❌ AI never sees item-level data ❌                        │              │
│   ❌ Candidate never sees item IDs ❌                         │              │
│                                                               │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Engagement** | % of failed candidates who use coach | > 60% |
| **Session completion** | % who finish feedback session | > 80% |
| **Satisfaction** | Post-session rating | > 4.2/5 |
| **Retake intent** | % who schedule retake within 60 days | > 50% (vs 40% baseline) |
| **Retake pass rate** | % of coached candidates who pass | > 75% |
| **Content security** | Item-level leakage incidents | 0 |

## Open Questions

1. **Timing**: When is feedback available? Immediately after, or 24-48h delay?
2. **Duration**: How long should feedback access remain open?
3. **Multiple Attempts**: How does feedback differ for 2nd, 3rd attempts?
4. **Passed Candidates**: Should passing candidates also get coaching?
5. **Human Escalation**: Can candidates request to speak to a human coach?
6. **Employer Access**: Should sponsors/employers see aggregated feedback?

---

_Last updated: December 25, 2025_
