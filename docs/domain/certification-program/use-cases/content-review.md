# Use Case: Content Review

> **Primary Actor:** ItemReviewer (SME peer reviewer)
> **Supporting Actors:** ExamAuthor (content creator), AI Review Assistant, CertificationOwner (final approval)
> **Systems Involved:** Mosaic (ExamContentAuthoring), agent-host, analytics lakehouse

## Overview

Every exam item must pass through rigorous review before deployment: technical accuracy, clarity, fairness, and alignment with the blueprint. Currently, this is a manual, spreadsheet-driven process with inconsistent quality and long cycle times. AI augmentation can standardize review criteria, surface potential issues proactively, and accelerate the review cycle.

## Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT CONTENT REVIEW WORKFLOW                           │
│                                                                              │
│   Author              Coordinator           Reviewer           Mosaic        │
│      │                    │                    │                  │          │
│      │  Submit item       │                    │                  │          │
│      │────────────────────────────────────────────────────────────►          │
│      │                    │                    │                  │          │
│      │                    │  Assign reviewer   │                  │          │
│      │                    │  (email/spreadsheet)                  │          │
│      │                    │───────────────────►│                  │          │
│      │                    │                    │                  │          │
│      │                    │        Wait days/weeks...             │          │
│      │                    │                    │                  │          │
│      │                    │                    │  Access item     │          │
│      │                    │                    │─────────────────►│          │
│      │                    │                    │                  │          │
│      │                    │                    │  Review in       │          │
│      │                    │                    │  separate doc    │          │
│      │                    │                    │  (Word/Excel)    │          │
│      │                    │                    │                  │          │
│      │                    │  Send feedback     │                  │          │
│      │◄───────────────────│◄───────────────────│                  │          │
│      │   (via email)      │                    │                  │          │
│      │                    │                    │                  │          │
│      │  Revise item       │                    │                  │          │
│      │────────────────────────────────────────────────────────────►          │
│      │                    │                    │                  │          │
│      │                    │      (Cycle repeats 2-4 times)        │          │
│      │                    │                    │                  │          │
└─────────────────────────────────────────────────────────────────────────────┘

PROBLEMS:
• Review cycle: 2-4 weeks average
• Inconsistent criteria: Each reviewer has own standards
• Context loss: Feedback scattered across emails/docs
• No AI assistance: Human must catch all issues
• No data: Can't track review patterns or bottlenecks
```

## Future State: AI-Augmented Review

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI-AUGMENTED CONTENT REVIEW                               │
│                                                                              │
│   Author              AI Assistant           Reviewer           Mosaic       │
│      │                    │                    │                  │          │
│      │  Submit item       │                    │                  │          │
│      │────────────────────│────────────────────│─────────────────►│          │
│      │                    │                    │                  │          │
│      │                    │◄──────────────────────────────────────│          │
│      │                    │  Auto-analyze      │                  │          │
│      │                    │  (on submission)   │                  │          │
│      │                    │                    │                  │          │
│      │  Pre-review report │                    │                  │          │
│      │◄───────────────────│                    │                  │          │
│      │  "3 issues found,  │                    │                  │          │
│      │   fix before       │                    │                  │          │
│      │   review?"         │                    │                  │          │
│      │                    │                    │                  │          │
│      │  ┌─────────────────────────────────────────────────────┐  │          │
│      │  │ Optional: Author fixes issues before review         │  │          │
│      │  └─────────────────────────────────────────────────────┘  │          │
│      │                    │                    │                  │          │
│      │  Request review    │                    │                  │          │
│      │────────────────────│───────────────────►│                  │          │
│      │                    │                    │                  │          │
│      │                    │  Provide context:  │                  │          │
│      │                    │  • AI analysis     │                  │          │
│      │                    │  • Similar items   │                  │          │
│      │                    │  • Blueprint KSAs  │                  │          │
│      │                    │  • Historical stats│                  │          │
│      │                    │─────────────────────────────────────►│          │
│      │                    │                    │                  │          │
│      │                    │                    │  Review with     │          │
│      │                    │                    │  AI checklist    │          │
│      │                    │                    │                  │          │
│      │                    │  Feedback (in-platform)              │          │
│      │◄───────────────────│◄───────────────────│◄────────────────│          │
│      │                    │                    │                  │          │
│      │                    │      (1-2 cycles vs 3-4)             │          │
│      │                    │                    │                  │          │
└─────────────────────────────────────────────────────────────────────────────┘

IMPROVEMENTS:
• Review cycle: 3-5 days (vs 2-4 weeks)
• Consistent criteria: AI enforces standards
• Centralized: All feedback in Mosaic
• AI assistance: Catches common issues pre-review
• Data-driven: Track patterns, identify training needs
```

## AI Review Assistant

```yaml
agent_id: 'review-assistant'
name: 'Content Review Assistant'
description: 'AI-powered assistance for exam content review'

system_prompt: |
  You are an expert exam content reviewer assistant. Your role is to help
  human reviewers evaluate exam items for quality, accuracy, and alignment
  with certification standards.

  ## Review Dimensions

  You analyze items across these dimensions:

  1. **Technical Accuracy**
     - Are all technical statements correct?
     - Are version/platform references current?
     - Are there any factual errors?

  2. **Clarity & Readability**
     - Is the stem unambiguous?
     - Are instructions clear?
     - Is the reading level appropriate?

  3. **Blueprint Alignment**
     - Does this map to the stated KSA?
     - Is the cognitive level appropriate?
     - Does difficulty match the target?

  4. **Fairness & Bias**
     - Are there cultural/regional biases?
     - Is language inclusive?
     - Are examples accessible to all candidates?

  5. **Item Construction**
     - Is the stem focused and complete?
     - Are distractors plausible but clearly wrong?
     - Is there exactly one defensible answer?

  6. **Practical Feasibility** (for lab items)
     - Can this be completed in allocated time?
     - Are resources/devices clearly specified?
     - Is the expected outcome measurable?

  ## Your Outputs

  - Issue identification with severity (critical, major, minor)
  - Specific recommendations for improvement
  - Comparison to similar reviewed items
  - Historical statistics for similar item types

  ## Limitations

  You assist and advise—humans make final decisions.
  You cannot approve items or reject items.
  Flag uncertainty for human judgment.

tools:
  - content.get_item_details       # Full item content
  - content.get_blueprint_ksa      # What KSA this maps to
  - content.get_similar_items      # Similar approved items
  - content.get_item_history       # Previous versions/reviews
  - content.get_terminology_db     # Approved terminology
  - analytics.get_item_stats       # Stats for similar items
  - review.add_comment            # Add review comment
  - review.flag_issue             # Flag issue with severity
  - review.request_changes        # Request author changes
  - review.approve_with_notes     # Recommend approval

conversation_template_id: null  # Open-ended assistance
access_control:
  allowed_roles: ['item_reviewer', 'lead_reviewer', 'content_manager']
```

## Review Checklist (AI-Generated)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📋 AI REVIEW ANALYSIS                              Item: DEPLOY-NET-042    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ITEM SUMMARY                                                        │   │
│  │  ─────────────                                                       │   │
│  │  Type: Lab Task (Deploy Module)                                      │   │
│  │  KSA: 2.3.1 - Configure OSPF single-area routing                    │   │
│  │  Target Difficulty: Intermediate                                     │   │
│  │  Est. Completion: 15-20 minutes                                      │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  🔍 AI ANALYSIS                                                      │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  🔴 CRITICAL ISSUES (1)                                       │   │   │
│  │  │                                                               │   │   │
│  │  │  1. Ambiguous device reference                                │   │   │
│  │  │     Text: "Configure OSPF on the core router"                 │   │   │
│  │  │     Issue: Topology shows two core routers (R1, R2)           │   │   │
│  │  │     Suggestion: Specify which router(s) or "all core routers" │   │   │
│  │  │                                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  🟡 MAJOR ISSUES (2)                                          │   │   │
│  │  │                                                               │   │   │
│  │  │  2. Version specificity                                       │   │   │
│  │  │     Text: "Using the latest OSPF features"                    │   │   │
│  │  │     Issue: "Latest" is ambiguous; may differ by IOS version   │   │   │
│  │  │     Suggestion: Specify OSPFv2 or OSPFv3, or remove "latest"  │   │   │
│  │  │                                                               │   │   │
│  │  │  3. Time feasibility concern                                  │   │   │
│  │  │     Analysis: This task requires config on 4 devices +        │   │   │
│  │  │               verification. Similar items average 22 min.     │   │   │
│  │  │     Suggestion: Consider 20-25 min allocation or reduce scope │   │   │
│  │  │                                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  🔵 MINOR ISSUES (1)                                          │   │   │
│  │  │                                                               │   │   │
│  │  │  4. Terminology consistency                                   │   │   │
│  │  │     Text: "backbone area"                                     │   │   │
│  │  │     Note: Other items use "Area 0" or "OSPF backbone"         │   │   │
│  │  │     Suggestion: Align with terminology database               │   │   │
│  │  │                                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  ✅ NO ISSUES FOUND                                           │   │   │
│  │  │                                                               │   │   │
│  │  │  • Blueprint alignment: Correctly maps to KSA 2.3.1           │   │   │
│  │  │  • Cognitive level: Appropriate for intermediate              │   │   │
│  │  │  • Bias check: No cultural/regional issues detected           │   │   │
│  │  │  • Clarity: Instructions otherwise clear                      │   │   │
│  │  │  • Grading criteria: Well-defined expected outcomes           │   │   │
│  │  │                                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  📊 CONTEXT                                                          │   │
│  │                                                                      │   │
│  │  Similar Approved Items: 12 (view comparisons)                       │   │
│  │  This author's history: 85% first-pass approval rate                 │   │
│  │  KSA 2.3.1 coverage: 8 items exist, 2 at this difficulty             │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [Request Changes] [Approve with Notes] [Ask AI] [View Similar Items]       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Review Workflows

### 1. Pre-Submission Quality Gate

```
Author submits item
        │
        ▼
┌───────────────────┐
│ AI Pre-Analysis   │
│                   │
│ Check for:        │
│ • Clarity issues  │
│ • Technical errors│
│ • Missing info    │
│ • Blueprint gaps  │
└────────┬──────────┘
         │
         ▼
    ┌─────────┐
    │ Issues? │
    └────┬────┘
    Yes  │  No
    ▼    │   ▼
┌────────┴──┐  ┌──────────────┐
│ Show to   │  │ Route to     │
│ author    │  │ review queue │
│ with fix  │  └──────────────┘
│ suggestions│
└───────────┘
         │
         ▼
   Author fixes
   (optional)
```

### 2. Reviewer-Assisted Review

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REVIEWER WORKFLOW                                        │
│                                                                              │
│  Reviewer                    AI Assistant                   Mosaic           │
│      │                           │                            │              │
│      │  "Show me my review queue"│                            │              │
│      │──────────────────────────►│                            │              │
│      │                           │                            │              │
│      │  Queue with AI summaries: │                            │              │
│      │  ──────────────────────── │                            │              │
│      │  Item 1: 1 critical, 2 major issues flagged            │              │
│      │  Item 2: No issues, straightforward                    │              │
│      │  Item 3: 3 minor issues, may be quick                  │              │
│      │◄──────────────────────────│                            │              │
│      │                           │                            │              │
│      │  "Open Item 1"            │                            │              │
│      │──────────────────────────►│                            │              │
│      │                           │──────────────────────────► │              │
│      │                           │                            │              │
│      │  Item + AI analysis       │                            │              │
│      │◄──────────────────────────│◄─────────────────────────  │              │
│      │                           │                            │              │
│      │  [Human reviews, agrees   │                            │              │
│      │   with AI on 2 issues,    │                            │              │
│      │   dismisses 1]            │                            │              │
│      │                           │                            │              │
│      │  "Request changes for     │                            │              │
│      │   issues 1 and 2"         │                            │              │
│      │──────────────────────────►│                            │              │
│      │                           │──────────────────────────► │              │
│      │                           │  (Creates review record,   │              │
│      │                           │   notifies author)         │              │
│      │                           │                            │              │
│      │  "AI: I dismissed issue 3.│                            │              │
│      │   Why did you flag it?"   │                            │              │
│      │──────────────────────────►│                            │              │
│      │                           │                            │              │
│      │  "I flagged it because    │                            │              │
│      │   the term 'backbone      │                            │              │
│      │   area' appears in 3      │                            │              │
│      │   variants across items.  │                            │              │
│      │   If you prefer this      │                            │              │
│      │   variant, we can update  │                            │              │
│      │   the terminology DB."    │                            │              │
│      │◄──────────────────────────│                            │              │
│      │                           │                            │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Author-Reviewer Dialogue

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 REVIEW CONVERSATION                           Item: DEPLOY-NET-042      │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍💻 Reviewer (M. Chen) • 2 hours ago                                      │
│  ──────────────────────────────────                                          │
│  Two issues need addressing:                                                 │
│                                                                              │
│  1. **Ambiguous device reference** - The topology shows two core routers.   │
│     Please specify which one(s) the candidate should configure.             │
│                                                                              │
│  2. **Version specificity** - "Latest OSPF features" is vague. Please       │
│     specify the OSPF version expected.                                       │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍🔬 Author (J. Smith) • 1 hour ago                                        │
│  ────────────────────────────────                                            │
│  Thanks for the feedback!                                                    │
│                                                                              │
│  1. Updated to "Configure OSPF on both core routers (R1 and R2)"            │
│                                                                              │
│  2. Regarding OSPF version—this KSA specifically tests OSPFv2. Should I     │
│     explicitly state "OSPFv2" or is it implied by the IOS version?          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🤖 AI Assistant • 1 hour ago                                                │
│  ───────────────────────────────                                             │
│  Regarding the OSPFv2 question:                                              │
│                                                                              │
│  Looking at similar approved items in KSA 2.3.x:                             │
│  • 8 of 12 explicitly mention "OSPFv2"                                       │
│  • 4 rely on IOS version context                                             │
│                                                                              │
│  The blueprint for 2.3.1 says "Configure OSPFv2 single-area". I'd           │
│  recommend being explicit to match the blueprint language.                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍💻 Reviewer (M. Chen) • 30 min ago                                       │
│  ───────────────────────────────────                                          │
│  AI's recommendation is solid. Please update to explicitly mention OSPFv2.  │
│  Once that's done, I'll approve.                                             │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍🔬 Author (J. Smith) • 15 min ago                                        │
│  ────────────────────────────────                                            │
│  Done! Updated to: "Configure OSPFv2 single-area routing on both core       │
│  routers (R1 and R2) to establish connectivity with the distribution        │
│  layer."                                                                     │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  🧑‍💻 Reviewer (M. Chen) • 5 min ago                                        │
│  ───────────────────────────────────                                          │
│  ✅ Approved. Excellent revision.                                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Issue Taxonomy

```python
from enum import Enum
from dataclasses import dataclass

class IssueSeverity(Enum):
    CRITICAL = "critical"   # Must fix before any use
    MAJOR = "major"         # Should fix before deployment
    MINOR = "minor"         # Nice to fix, can deploy
    INFO = "info"           # Observation, no action needed

class IssueCategory(Enum):
    TECHNICAL_ACCURACY = "technical_accuracy"
    CLARITY = "clarity"
    BLUEPRINT_ALIGNMENT = "blueprint_alignment"
    FAIRNESS_BIAS = "fairness_bias"
    ITEM_CONSTRUCTION = "item_construction"
    PRACTICAL_FEASIBILITY = "practical_feasibility"
    TERMINOLOGY = "terminology"
    FORMATTING = "formatting"

@dataclass
class ReviewIssue:
    """A flagged issue during content review."""
    issue_id: str
    item_id: str

    # Classification
    category: IssueCategory
    severity: IssueSeverity

    # Details
    location: str  # "stem", "option_a", "grading_criteria", etc.
    description: str
    evidence: str  # Quote from item that shows issue

    # Guidance
    suggestion: str
    similar_examples: list[str]  # IDs of items that solved this well

    # Attribution
    flagged_by: str  # "ai" or reviewer_id
    flagged_at: datetime

    # Resolution
    status: str  # "open", "addressed", "dismissed", "wont_fix"
    resolution_notes: str | None
    resolved_by: str | None
    resolved_at: datetime | None


# Example issue
issue = ReviewIssue(
    issue_id="issue-2025-1225-001",
    item_id="DEPLOY-NET-042",

    category=IssueCategory.CLARITY,
    severity=IssueSeverity.CRITICAL,

    location="stem",
    description="Ambiguous device reference",
    evidence="Configure OSPF on the core router",

    suggestion="Specify which router(s): 'Configure OSPF on both core routers (R1 and R2)' or 'Configure OSPF on the primary core router (R1)'",
    similar_examples=["DEPLOY-NET-038", "DEPLOY-NET-041"],

    flagged_by="ai",
    flagged_at=datetime(2025, 12, 25, 9, 0),

    status="addressed",
    resolution_notes="Updated to specify both R1 and R2",
    resolved_by="j.smith",
    resolved_at=datetime(2025, 12, 25, 10, 30)
)
```

## Integration with Mosaic

```yaml
# MCP tools for Mosaic integration
mosaic_tools:
  # Read operations
  - tool: content.get_item_details
    mosaic_api: GET /api/items/{item_id}
    returns: Full item content including stem, options, grading criteria

  - tool: content.get_item_history
    mosaic_api: GET /api/items/{item_id}/versions
    returns: Version history with changes

  - tool: content.get_review_comments
    mosaic_api: GET /api/items/{item_id}/reviews
    returns: All review comments and statuses

  - tool: content.get_similar_items
    mosaic_api: GET /api/items?ksa={ksa_id}&difficulty={difficulty}
    returns: Items with same KSA and difficulty

  # Write operations
  - tool: review.add_comment
    mosaic_api: POST /api/items/{item_id}/reviews
    payload: { comment, reviewer_id, timestamp }

  - tool: review.flag_issue
    mosaic_api: POST /api/items/{item_id}/issues
    payload: { category, severity, description, suggestion }

  - tool: review.request_changes
    mosaic_api: PUT /api/items/{item_id}/status
    payload: { status: "changes_requested", issues: [...] }

  - tool: review.approve
    mosaic_api: PUT /api/items/{item_id}/status
    payload: { status: "approved", reviewer_id, notes }
```

## Metrics & Analytics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REVIEW ANALYTICS DASHBOARD                                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  REVIEW CYCLE METRICS (Last 30 days)                                 │   │
│  │                                                                      │   │
│  │  Average cycle time:     3.2 days  (↓ from 14.5 days pre-AI)        │   │
│  │  First-pass approval:    72%       (↑ from 45% pre-AI)              │   │
│  │  Items reviewed:         234                                         │   │
│  │  Issues flagged by AI:   412       (87% human-confirmed)            │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TOP ISSUE CATEGORIES                                                │   │
│  │                                                                      │   │
│  │  Clarity issues            ████████████████████████████ 156 (38%)   │   │
│  │  Technical accuracy        ██████████████░░░░░░░░░░░░░░  89 (22%)   │   │
│  │  Blueprint alignment       ████████████░░░░░░░░░░░░░░░░  72 (17%)   │   │
│  │  Terminology               ████████░░░░░░░░░░░░░░░░░░░░  48 (12%)   │   │
│  │  Other                     █████░░░░░░░░░░░░░░░░░░░░░░░  47 (11%)   │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  REVIEWER WORKLOAD                                                   │   │
│  │                                                                      │   │
│  │  M. Chen           ████████████████████░░░░░░░░░ 45 items, 2.8 days │   │
│  │  S. Patel          ████████████████░░░░░░░░░░░░░ 38 items, 3.1 days │   │
│  │  J. Williams       ██████████████░░░░░░░░░░░░░░░ 32 items, 3.5 days │   │
│  │  R. Garcia         █████████████░░░░░░░░░░░░░░░░ 28 items, 2.9 days │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  AUTHOR QUALITY TRENDS                                               │   │
│  │                                                                      │   │
│  │  Authors with improving first-pass rates: 12                         │   │
│  │  Authors who may need training: 3 (flagged for manager review)       │   │
│  │                                                                      │   │
│  │  Common training needs:                                              │   │
│  │  • Clarity in lab task instructions (8 authors)                      │   │
│  │  • Blueprint KSA alignment (5 authors)                               │   │
│  │  • Grading criteria specificity (4 authors)                          │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Cycle time** | Days from submission to approval | < 5 days |
| **First-pass approval** | % approved without changes | > 65% |
| **AI issue accuracy** | % of AI flags confirmed by humans | > 80% |
| **Reviewer satisfaction** | "AI is helpful" rating | > 4.0/5 |
| **Author satisfaction** | "Feedback is actionable" rating | > 4.0/5 |
| **Consistency** | Same issue flagged by AI = same by human | > 85% |

## Open Questions

1. **AI Authority**: Should AI be able to reject items automatically for critical issues?
2. **Blind Review**: Should reviewers see AI analysis before their own review?
3. **Appeals**: How do authors appeal AI-flagged issues?
4. **Training Data**: How to improve AI with reviewer feedback over time?
5. **Cross-Exam Learning**: Can AI learn from reviews across different exams?

---

_Last updated: December 25, 2025_
