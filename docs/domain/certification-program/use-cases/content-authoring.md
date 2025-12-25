# Use Case: Content Authoring

> **Primary Actor:** ExamAuthor (SME - Subject Matter Expert)
> **Supporting Actors:** ItemReviewer, CertificationOwner (EPM), AI Content Assistant
> **Systems Involved:** Mosaic (primary), agent-host, knowledge-manager, tools-provider

## Overview

Content Authoring is the process of creating exam Items (questions/tasks) and Fragments (reusable content pieces) that measure the KSAs defined in a Blueprint. SMEs receive assignments from EPMs and author content within Mosaic, with AI assistance available via agent-host.

## Domain Model Mapping

| Mosaic Term | agent-host Term | Description |
|-------------|-----------------|-------------|
| Form | Conversation | A complete exam instance |
| Item | ConversationItem | A single question/task |
| Fragment | ItemContent | Reusable content piece (stem, option, resource) |
| Module | Section | Grouping of related items |
| FormSet | ConversationTemplate | Template for generating forms |

## Current State (Mosaic-Centric)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT CONTENT AUTHORING FLOW                          │
│                                                                              │
│  CertificationOwner              Mosaic                   ExamAuthor         │
│        │                           │                           │             │
│        │  1. Create assignment     │                           │             │
│        │      for Topic X          │                           │             │
│        │──────────────────────────►│                           │             │
│        │                           │                           │             │
│        │                           │  2. Notify SME            │             │
│        │                           │─────────────────────────► │             │
│        │                           │                           │             │
│        │                           │  3. View assignment       │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  4. Create Item shell     │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  5. Write stem            │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  6. Write options         │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  7. Set correct answer    │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  8. Add metadata          │             │
│        │                           │     (KSA, difficulty)     │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │  9. Submit for review     │             │
│        │                           │◄───────────────────────── │             │
│        │                           │                           │             │
│        │                           │    CloudEvent:            │             │
│        │                           │    item.submitted.v1      │             │
│        │                           │─────────────────────────► │             │
│        │                           │                           │             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Pain Point | Impact | Root Cause |
|------------|--------|------------|
| **Blank page syndrome** | Slow item creation | No starting point or templates |
| **Inconsistent quality** | High rejection rates | No real-time quality checks |
| **Distractor weakness** | Poor item discrimination | Hard to write plausible wrong answers |
| **Manual research** | Duplicated effort | SMEs research same topics repeatedly |
| **Static content** | Exposure vulnerability | No parameterization support |
| **Review cycles** | Long turnaround | Issues found late in process |

## Future State (AI-Augmented)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI-AUGMENTED CONTENT AUTHORING                          │
│                                                                              │
│  ExamAuthor                    agent-host                 AI Assistant       │
│      │                             │                           │             │
│      │  1. "Help me create items   │                           │             │
│      │     for BGP troubleshooting │                           │             │
│      │     skill"                  │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │                           │             │
│      │                             │  2. Fetch KSA details     │             │
│      │                             │     from Mosaic           │             │
│      │                             │────────────────────────── │             │
│      │                             │     tools-provider        │             │
│      │                             │                           │             │
│      │                             │  3. Get domain context    │             │
│      │                             │────────────────────────── │             │
│      │                             │     knowledge-manager     │             │
│      │                             │                           │             │
│      │  4. Suggest item structure  │                           │             │
│      │     with parameterized stem │                           │             │
│      │◄────────────────────────────│◄────────────────────────  │             │
│      │                             │                           │             │
│      │  5. "Make it about eBGP     │                           │             │
│      │     peering failure"        │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │                           │             │
│      │  6. Generate stem variants  │                           │             │
│      │     + distractor strategies │                           │             │
│      │◄────────────────────────────│◄────────────────────────  │             │
│      │                             │                           │             │
│      │  7. "Add a topology diagram │                           │             │
│      │     as exhibit"             │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │                           │             │
│      │  8. Generate parameterized  │                           │             │
│      │     topology with variables │                           │             │
│      │◄────────────────────────────│◄────────────────────────  │             │
│      │                             │                           │             │
│      │  9. Validate item quality   │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │                           │             │
│      │ 10. Quality report:         │                           │             │
│      │     - Bloom's level: ✓      │                           │             │
│      │     - Distractors: ✓        │                           │             │
│      │     - Bias check: ✓         │                           │             │
│      │     - Clarity: warning      │                           │             │
│      │◄────────────────────────────│◄────────────────────────  │             │
│      │                             │                           │             │
│      │ 11. "Fix clarity issue"     │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │                           │             │
│      │ 12. Refined stem with       │                           │             │
│      │     improved clarity        │                           │             │
│      │◄────────────────────────────│◄────────────────────────  │             │
│      │                             │                           │             │
│      │ 13. "Save to Mosaic"        │                           │             │
│      │────────────────────────────►│                           │             │
│      │                             │ 14. Create Item via       │             │
│      │                             │     Mosaic API            │             │
│      │                             │────────────────────────── │             │
│      │                             │     tools-provider        │             │
│      │                             │                           │             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## AI Agent Configuration

### Content Author Assistant

```yaml
agent_id: 'content-author-assistant'
name: 'Content Author Assistant'
description: 'Assists SMEs in creating high-quality, parameterized exam items'

system_prompt: |
  You are an expert item writer assisting Subject Matter Experts in creating
  certification exam content.

  Your responsibilities:
  1. Generate item stems based on KSA statements and skill templates
  2. Create plausible distractors using proven strategies
  3. Suggest parameterization opportunities for unique item generation
  4. Validate items against psychometric quality criteria
  5. Ensure content is free of bias, ambiguity, and cueing

  Item writing best practices:
  - Stem should be self-contained (answerable without options)
  - Options should be parallel in structure and length
  - Avoid "all of the above" and "none of the above"
  - Use scenario-based stems for higher cognitive levels
  - Include exhibits (diagrams, logs, configs) for realism

  For practical exam items:
  - Define clear success criteria (observable device state)
  - Specify which devices/interfaces are in scope
  - Include grading checkpoints for partial credit

tools:
  - mosaic.get_assignment
  - mosaic.get_ksa_details
  - mosaic.create_item
  - mosaic.update_item
  - mosaic.add_fragment
  - mosaic.submit_for_review
  - knowledge.get_domain_context
  - knowledge.get_similar_items  # Avoid duplication
  - validation.check_item_quality
  - validation.check_bias
  - validation.check_bloom_level
  - generation.create_distractors
  - generation.parameterize_stem

conversation_template_id: null  # Open-ended
access_control:
  allowed_roles: ['exam_author', 'item_writer', 'sme']
```

## Item Creation Workflow

### Step 1: Assignment Context

```python
# SME receives assignment with context
assignment = {
    "id": "assign-001",
    "blueprint_id": "bp-network-2024",
    "topic": "Routing Protocols",
    "skill": "BGP Troubleshooting",
    "ksa_statements": [
        "Diagnose BGP neighbor establishment failures",
        "Interpret BGP state machine transitions",
        "Resolve common BGP configuration errors"
    ],
    "target_item_count": 5,
    "difficulty_distribution": {
        "easy": 1,
        "medium": 3,
        "hard": 1
    },
    "item_types": ["multiple_choice", "practical_task"],
    "deadline": "2025-02-15"
}
```

### Step 2: AI-Assisted Stem Generation

```python
# AI generates stem options based on KSA
stem_suggestions = [
    {
        "stem": """
        A network engineer is troubleshooting a BGP peering issue between
        router {router_a} (AS {as_a}) and router {router_b} (AS {as_b}).

        The following output is observed on {router_a}:

        {router_a}# show ip bgp summary
        Neighbor        AS    State
        {peer_ip}       {as_b} {bgp_state}

        Which action would resolve this issue?
        """,
        "parameters": {
            "router_a": {"type": "hostname", "pool": ["R1", "R2", "R3"]},
            "router_b": {"type": "hostname", "pool": ["R1", "R2", "R3"]},
            "as_a": {"type": "int", "range": [64512, 65534]},
            "as_b": {"type": "int", "range": [64512, 65534]},
            "peer_ip": {"type": "ip", "template": "10.{x}.{y}.{z}"},
            "bgp_state": {"type": "enum", "values": ["Idle", "Active", "OpenSent"]}
        },
        "cognitive_level": "Apply",
        "ksa_alignment": "Diagnose BGP neighbor establishment failures"
    }
]
```

### Step 3: Distractor Generation

```python
# AI generates distractors using proven strategies
distractor_set = {
    "correct_answer": "Verify the neighbor IP address configuration",
    "distractors": [
        {
            "text": "Restart the BGP process on both routers",
            "strategy": "common_misconception",
            "why_wrong": "Restarting doesn't fix config issues"
        },
        {
            "text": "Increase the BGP hold timer",
            "strategy": "partially_correct",
            "why_wrong": "Timer adjustment doesn't fix establishment"
        },
        {
            "text": "Configure route redistribution",
            "strategy": "related_concept",
            "why_wrong": "Redistribution is unrelated to peering"
        }
    ]
}
```

### Step 4: Quality Validation

```python
# Real-time quality checks
quality_report = {
    "overall_score": 0.85,
    "checks": {
        "bloom_level": {
            "status": "pass",
            "detected": "Apply",
            "target": "Apply",
            "message": "Cognitive level matches KSA requirement"
        },
        "distractor_plausibility": {
            "status": "pass",
            "scores": [0.8, 0.75, 0.7],
            "message": "All distractors are plausible"
        },
        "option_homogeneity": {
            "status": "pass",
            "message": "Options are similar in length and structure"
        },
        "stem_clarity": {
            "status": "warning",
            "message": "Consider specifying the IOS version for show command"
        },
        "bias_check": {
            "status": "pass",
            "message": "No cultural, gender, or regional bias detected"
        },
        "cueing_check": {
            "status": "pass",
            "message": "Correct answer is not grammatically cued"
        }
    },
    "suggestions": [
        "Add 'on a Cisco IOS router' to clarify platform"
    ]
}
```

## MCP Tools Required

### Mosaic Integration

| Tool | Operation | Description |
|------|-----------|-------------|
| `mosaic.get_assignments` | Query | Get SME's pending assignments |
| `mosaic.get_assignment` | Query | Get specific assignment details |
| `mosaic.get_ksa_details` | Query | Get KSA context for item writing |
| `mosaic.create_item` | Command | Create new item in Mosaic |
| `mosaic.update_item` | Command | Update item content |
| `mosaic.add_fragment` | Command | Add reusable fragment |
| `mosaic.attach_exhibit` | Command | Attach diagram/resource to item |
| `mosaic.submit_for_review` | Command | Submit item for review |
| `mosaic.get_similar_items` | Query | Find similar existing items |

### Content Generation

| Tool | Operation | Description |
|------|-----------|-------------|
| `generate.stem_variants` | Command | Create stem variations |
| `generate.distractors` | Command | Generate plausible wrong options |
| `generate.exhibit` | Command | Generate diagram/topology |
| `generate.parameterize` | Command | Add parameters to static content |

### Validation

| Tool | Operation | Description |
|------|-----------|-------------|
| `validate.item_quality` | Query | Comprehensive quality check |
| `validate.bloom_level` | Query | Detect cognitive level |
| `validate.bias` | Query | Check for bias issues |
| `validate.duplication` | Query | Check for similar existing items |

## Design Module Content (Progressive Storyline)

For the Design module's progressive storyline, content includes Resources that build context:

```yaml
design_module_content:
  scenario:
    company: "{company_name}"
    industry: "{industry}"
    situation: "Network upgrade project"

  resources:
    - type: email
      from: "{manager_name}, IT Director"
      subject: "Urgent: Network Issues in {department}"
      body_template: |
        Hi,

        We've been experiencing intermittent connectivity issues in the
        {department} department since the {event_trigger}.

        Please investigate and provide recommendations by {deadline}.

        Regards,
        {manager_name}

    - type: topology_diagram
      template: "topology/hub-spoke-{site_count}.svg"
      parameters:
        site_count: [3, 4, 5]

    - type: log_excerpt
      device: "{affected_device}"
      log_template: |
        %BGP-5-ADJCHANGE: neighbor {peer_ip} {state_change}
        %LINEPROTO-5-UPDOWN: Interface {interface}, changed state to {state}

  items:
    - sequence: 1
      type: analysis
      context_resources: [email, topology_diagram]
      question: "Based on the email and topology, which device should you investigate first?"

    - sequence: 2
      type: investigation
      context_resources: [email, topology_diagram, log_excerpt]
      question: "The logs indicate which type of failure?"
```

## Event Flow

```
ExamAuthor Action          Mosaic                    Event Broker
      │                      │                            │
      │  Create item         │                            │
      │─────────────────────►│                            │
      │                      │  item.created.v1           │
      │                      │───────────────────────────►│
      │                      │                            │
      │  Submit for review   │                            │  → knowledge-manager
      │─────────────────────►│                            │    (index new content)
      │                      │  item.submitted.v1         │
      │                      │───────────────────────────►│
      │                      │                            │  → notification-service
      │                      │                            │    (alert reviewer)
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **First-pass approval** | % items approved without revision | > 80% |
| **Time to create** | Minutes per item (avg) | -40% vs current |
| **Quality score** | Automated quality check score | > 0.85 |
| **Distractor effectiveness** | Post-exam discrimination index | > 0.3 |
| **Parameterization rate** | % items with parameters | > 60% (new items) |

## Open Questions

1. **SkillTemplate Ownership**: Should SkillTemplates live in Mosaic or blueprint-manager?
2. **Fragment Reuse**: How to surface reusable fragments across assignments?
3. **AI Attribution**: Should AI-generated content be flagged in Mosaic?
4. **Version Control**: How to track AI suggestions vs SME refinements?

---

_Last updated: December 25, 2025_
