# Use Case: Exam Delivery

> **Primary Actor:** Candidate
> **Supporting Actors:** Proctor, AI Tutor (optional), Session Manager
> **Systems Involved:** LDS (exam-delivery-system), session-manager, pod-manager, agent-host, output-collectors

## Overview

Exam Delivery is the process of presenting exam content to Candidates and capturing their responses. The system supports two distinct delivery modes that reflect different assessment objectives:

| Mode | Description | Interaction Pattern |
|------|-------------|---------------------|
| **Design Module** | Progressive storyline with sequential items | Proactive conversation |
| **Deploy Module** | All items/resources at once, candidate-driven sequence | Reactive workspace |

## Current State (LDS-Centric)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CURRENT EXAM DELIVERY FLOW                            │
│                                                                              │
│  Candidate                        LDS                     session-manager    │
│      │                             │                            │            │
│      │  1. Launch exam             │                            │            │
│      │────────────────────────────►│                            │            │
│      │                             │  2. Validate session       │            │
│      │                             │───────────────────────────►│            │
│      │                             │                            │            │
│      │                             │  3. Session valid          │            │
│      │                             │◄───────────────────────────│            │
│      │                             │                            │            │
│      │  4. Render exam UI          │                            │            │
│      │◄────────────────────────────│                            │            │
│      │                             │                            │            │
│      │  ══════════════════════════════════════════════════════  │            │
│      │                    DESIGN MODULE                          │            │
│      │  ══════════════════════════════════════════════════════  │            │
│      │                             │                            │            │
│      │  5. View item 1             │                            │            │
│      │◄────────────────────────────│                            │            │
│      │                             │                            │            │
│      │  6. Submit response         │                            │            │
│      │────────────────────────────►│                            │            │
│      │                             │  CloudEvent:               │            │
│      │                             │  response.submitted.v1     │            │
│      │                             │────────────────────────────────────►    │
│      │                             │                            │            │
│      │  7. View item 2             │                            │            │
│      │     (with new resources)    │                            │            │
│      │◄────────────────────────────│                            │            │
│      │                             │                            │            │
│      │  ... sequential items ...   │                            │            │
│      │                             │                            │            │
│      │  ══════════════════════════════════════════════════════  │            │
│      │                    DEPLOY MODULE                          │            │
│      │  ══════════════════════════════════════════════════════  │            │
│      │                             │                            │            │
│      │  8. View all tasks +        │                            │            │
│      │     POD access credentials  │                            │            │
│      │◄────────────────────────────│                            │            │
│      │                             │                            │            │
│      │  9. Work on POD devices     │                            │            │
│      │     (candidate-driven)      │                            │            │
│      │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─►│◄─ ─ ─ pod-manager          │            │
│      │                             │                            │            │
│      │  10. Submit checkpoint      │                            │            │
│      │────────────────────────────►│                            │            │
│      │                             │  CloudEvent:               │            │
│      │                             │  checkpoint.submitted.v1   │            │
│      │                             │────────────────────────────────────►    │
│      │                             │                            │            │
│      │  11. Final submission       │                            │            │
│      │────────────────────────────►│                            │            │
│      │                             │  CloudEvent:               │            │
│      │                             │  exam.completed.v1         │            │
│      │                             │────────────────────────────────────►    │
│      │                             │                            │            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Limitations

| Limitation | Impact | Root Cause |
|------------|--------|------------|
| **Static content** | Exposure vulnerability | No parameterization in delivery |
| **No adaptive hints** | Candidate frustration | No AI assistance during exam |
| **Limited interaction** | Poor UX for complex tasks | UI designed for MCQ, not workflows |
| **Manual grading triggers** | Delayed feedback | Checkpoint submission is manual |
| **No proactive guidance** | Candidates get stuck | Design module is passive |

## Future State: Design Module (AI-Augmented Progressive)

The Design module becomes a **Proactive Conversation** where the system guides candidates through a storyline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DESIGN MODULE - PROACTIVE CONVERSATION                    │
│                                                                              │
│  Candidate                    agent-host                    LDS              │
│      │                            │                          │               │
│      │  1. Start Design module    │                          │               │
│      │───────────────────────────►│                          │               │
│      │                            │                          │               │
│      │                            │  2. Load ConversationTemplate            │
│      │                            │     (from FormSpec)       │               │
│      │                            │                          │               │
│      │  3. Scenario introduction  │                          │               │
│      │     "You are a network     │                          │               │
│      │      engineer at {company} │                          │               │
│      │      ..."                  │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  4. Present Resource:      │                          │               │
│      │     📧 Email from manager  │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  5. Present Item 1:        │                          │               │
│      │     "Based on this email,  │                          │               │
│      │      what is your first    │                          │               │
│      │      step?"                │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  6. Submit response        │                          │               │
│      │────────────────────────────►                          │               │
│      │                            │                          │               │
│      │                            │  7. Evaluate response    │               │
│      │                            │     (immediate or queued)│               │
│      │                            │                          │               │
│      │  8. Acknowledgment +       │                          │               │
│      │     new context            │                          │               │
│      │     "Good choice. Here's   │                          │               │
│      │      what you found..."    │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  9. Present Resource:      │                          │               │
│      │     📊 Log output          │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  10. Present Item 2:       │                          │               │
│      │      "Analyze this log..." │                          │               │
│      │◄───────────────────────────│                          │               │
│      │                            │                          │               │
│      │  ... storyline continues   │                          │               │
│      │                            │                          │               │
│      │                            │  11. Sync responses       │               │
│      │                            │─────────────────────────►│               │
│      │                            │      to LDS               │               │
│      │                            │                          │               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design Module UX Widgets

The progressive storyline uses specialized widgets:

| Widget | Purpose | Example |
|--------|---------|---------|
| `ResourceCard` | Display context materials | Email, document, diagram |
| `LogViewer` | Show command/log output | Device logs, show commands |
| `TopologyViewer` | Interactive network diagram | Click devices for details |
| `MCQWidget` | Multiple choice question | Standard item presentation |
| `TextInputWidget` | Free-text response | Analysis questions |
| `NarrativeBlock` | Story progression text | "After investigating, you found..." |

### ConversationTemplate for Design Module

```yaml
id: 'design-module-network-2024'
name: 'Network Certification - Design Module'
type: 'proactive'
time_limit_minutes: 90

flow:
  - step: intro
    type: narrative
    content_template: |
      Welcome to the Design Module.

      You are a network engineer at {company_name}. Today you'll be
      investigating a series of network issues reported by various
      departments.

      Read each scenario carefully and select the best course of action.

  - step: scenario_1
    type: resource_sequence
    resources:
      - type: email
        widget: ResourceCard
        content_template: |
          From: {manager_name}
          Subject: Urgent: {department} connectivity issues

          We've had multiple reports of users unable to access {service}.
          Please investigate immediately.

    item:
      type: multiple_choice
      stem_template: |
        Based on the email, which device should you investigate first?
      options:
        - template: "{correct_device}"
          correct: true
        - template: "{distractor_1}"
        - template: "{distractor_2}"
        - template: "{distractor_3}"

    on_submit:
      - action: evaluate
      - action: show_narrative
        content_template: |
          You connected to {correct_device} and ran initial diagnostics.
          Here's what you found:

  - step: scenario_1_followup
    type: resource_sequence
    resources:
      - type: log
        widget: LogViewer
        content_template: |
          {device}# show ip interface brief
          Interface         IP-Address      Status      Protocol
          {interface_1}     {ip_1}          up          up
          {interface_2}     {ip_2}          {status}    {protocol}

    item:
      type: multiple_choice
      stem_template: |
        The log output indicates which type of issue?
      # ... options

  # ... more steps

  - step: completion
    type: narrative
    content_template: |
      You have completed the Design Module.

      Your responses have been recorded. Please proceed to the Deploy Module
      when ready.
```

## Future State: Deploy Module (Reactive Workspace)

The Deploy module is a **Reactive Workspace** where candidates have full autonomy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPLOY MODULE - REACTIVE WORKSPACE                        │
│                                                                              │
│  Candidate                    LDS                      pod-manager           │
│      │                         │                            │                │
│      │  1. Start Deploy module │                            │                │
│      │────────────────────────►│                            │                │
│      │                         │                            │                │
│      │                         │  2. Request POD            │                │
│      │                         │────────────────────────────►               │
│      │                         │                            │                │
│      │                         │  3. POD ready              │                │
│      │                         │     + credentials          │                │
│      │                         │◄────────────────────────────               │
│      │                         │                            │                │
│      │  4. Render workspace    │                            │                │
│      │     ┌────────────────────────────────────────┐       │                │
│      │     │  TASK LIST          │  POD ACCESS      │       │                │
│      │     │  ☐ Task 1           │  ┌──────────┐   │       │                │
│      │     │  ☐ Task 2           │  │ R1  R2   │   │       │                │
│      │     │  ☐ Task 3           │  │  ╲  ╱    │   │       │                │
│      │     │  ☐ Task 4           │  │   SW1    │   │       │                │
│      │     │                     │  │    │     │   │       │                │
│      │     │  RESOURCES          │  │  Server  │   │       │                │
│      │     │  📄 Requirements    │  └──────────┘   │       │                │
│      │     │  📊 Topology        │                 │       │                │
│      │     │  📋 IP Scheme       │  [Open Console]│       │                │
│      │     └────────────────────────────────────────┘       │                │
│      │◄────────────────────────│                            │                │
│      │                         │                            │                │
│      │  5. Candidate works     │                            │                │
│      │     on tasks in any     │                            │                │
│      │     order they choose   │                            │                │
│      │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─►│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │                │
│      │                         │     (console sessions)     │                │
│      │                         │                            │                │
│      │  6. Submit checkpoint   │                            │                │
│      │     (optional midpoint) │                            │                │
│      │────────────────────────►│                            │                │
│      │                         │  7. Trigger state          │                │
│      │                         │     collection             │                │
│      │                         │────────────────────────────►               │
│      │                         │                            │                │
│      │  8. Final submission    │                            │                │
│      │────────────────────────►│                            │                │
│      │                         │  9. Lock POD +             │                │
│      │                         │     collect final state    │                │
│      │                         │────────────────────────────►               │
│      │                         │                            │                │
│      │                         │  CloudEvent:               │                │
│      │                         │  deploy.completed.v1       │                │
│      │                         │─────────────────────────────────────►      │
│      │                         │                            │                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deploy Module Task Presentation

```yaml
deploy_module:
  id: 'deploy-network-2024-instance-{candidate_id}'
  time_limit_minutes: 240  # 4 hours

  scenario:
    narrative: |
      You are taking over network operations at {company_name}.

      The previous engineer left incomplete configurations. Your task is to
      complete the network setup according to the requirements document.

      You may complete tasks in any order, but be aware that some tasks
      depend on others.

  resources:
    - id: requirements
      type: document
      title: "Network Requirements"
      content_template: |
        ## Network Requirements for {company_name}

        ### Addressing
        - Management Network: {mgmt_subnet}
        - User VLANs: {vlan_list}
        - WAN Links: {wan_subnet}

        ### Routing
        - Internal: OSPF Area {ospf_area}
        - External: BGP AS {local_as} peering with AS {remote_as}

        ### Security
        - Management access restricted to {admin_subnet}
        - Inter-VLAN filtering per attached ACL document

    - id: topology
      type: diagram
      title: "Network Topology"
      template: "topologies/deploy-{topology_variant}.svg"

    - id: ip_scheme
      type: spreadsheet
      title: "IP Addressing Scheme"
      content_template: |
        Device,Interface,IP Address,Subnet,VLAN
        {device_1},{int_1},{ip_1},{subnet_1},{vlan_1}
        ...

  tasks:
    - id: task_1
      title: "Configure Router {router_1} Interfaces"
      description: |
        Configure all interfaces on {router_1} according to the IP scheme.
        Ensure interfaces are administratively up.
      success_criteria:
        - device: "{router_1}"
          check: "interface {int_1} has IP {ip_1}"
        - device: "{router_1}"
          check: "interface {int_1} is up/up"
      points: 10
      dependencies: []

    - id: task_2
      title: "Configure OSPF on {router_1}"
      description: |
        Configure OSPF process 1 on {router_1}.
        Advertise all connected networks in Area {ospf_area}.
      success_criteria:
        - device: "{router_1}"
          check: "OSPF neighbor with {router_2} is FULL"
      points: 15
      dependencies: [task_1]

    - id: task_3
      title: "Establish BGP Peering"
      description: |
        Configure eBGP peering between {router_edge} (AS {local_as}) and
        the ISP router at {isp_ip} (AS {remote_as}).
      success_criteria:
        - device: "{router_edge}"
          check: "BGP neighbor {isp_ip} is Established"
      points: 20
      dependencies: [task_1]

    # ... more tasks

  checkpoints:
    - id: midpoint
      after_minutes: 120
      optional: true
      message: "Optional midpoint submission - your progress will be saved"

    - id: final
      type: required
      message: "Final submission - POD will be locked for grading"
```

## AI Tutor Integration (Optional)

For training/practice exams, an AI Tutor can provide hints:

```yaml
agent_id: 'exam-tutor'
name: 'Exam Tutor'
description: 'Provides progressive hints during practice exams'

system_prompt: |
  You are a supportive exam tutor helping candidates during practice exams.

  Guidelines:
  - Provide hints only when requested
  - Start with subtle hints, progress to more direct guidance
  - Never give away the exact answer
  - Encourage the candidate to think through the problem
  - Reference relevant concepts without solving for them

hint_levels:
  - level: 1
    type: conceptual
    example: "Think about which protocol handles neighbor discovery."

  - level: 2
    type: directional
    example: "The issue is related to the BGP state machine. What happens before Established?"

  - level: 3
    type: procedural
    example: "Check the neighbor configuration on both routers. Compare the IP addresses and AS numbers."

# Only enabled for practice exams
enabled_for:
  - session_type: practice
  - session_type: training
disabled_for:
  - session_type: certification
  - session_type: proctored
```

## Event Flow

```
Candidate Action           LDS                    Event Broker              Subscribers
      │                     │                          │                         │
      │  Start exam         │                          │                         │
      │────────────────────►│                          │                         │
      │                     │  exam.started.v1         │                         │
      │                     │─────────────────────────►│                         │
      │                     │                          │───────────────────────► │
      │                     │                          │   session-manager       │
      │                     │                          │   (track attempt)       │
      │                     │                          │                         │
      │  Submit response    │                          │                         │
      │────────────────────►│                          │                         │
      │                     │  response.submitted.v1   │                         │
      │                     │─────────────────────────►│                         │
      │                     │                          │───────────────────────► │
      │                     │                          │   analytics             │
      │                     │                          │   (candidate behavior)  │
      │                     │                          │                         │
      │  Move to next item  │                          │                         │
      │────────────────────►│                          │                         │
      │                     │  item.navigated.v1       │                         │
      │                     │─────────────────────────►│                         │
      │                     │                          │                         │
      │  Submit checkpoint  │                          │                         │
      │────────────────────►│                          │                         │
      │                     │  checkpoint.submitted.v1 │                         │
      │                     │─────────────────────────►│                         │
      │                     │                          │───────────────────────► │
      │                     │                          │   output-collectors     │
      │                     │                          │   (collect device state)│
      │                     │                          │                         │
      │  Final submit       │                          │                         │
      │────────────────────►│                          │                         │
      │                     │  exam.completed.v1       │                         │
      │                     │─────────────────────────►│                         │
      │                     │                          │───────────────────────► │
      │                     │                          │   grading-system        │
      │                     │                          │   (queue for grading)   │
      │                     │                          │                         │
```

## Parameterized Content at Delivery

When delivering parameterized content, LDS requests instance generation:

```python
# LDS requests unique instance for candidate
instance_request = {
    "form_spec_id": "form-spec-2024-a",
    "candidate_id": "candidate-12345",
    "session_id": "session-67890",
    "seed": generate_crypto_seed()  # Deterministic but unpredictable
}

# agent-host generates unique instance
instance = await generate_form_instance(instance_request)

# Instance contains resolved parameters
{
    "items": [
        {
            "slot_id": "slot-1",
            "stem": "What is 7 × 8?",  # Resolved from "What is {a} × {b}?"
            "options": ["56", "49", "63", "15"],  # Resolved + shuffled
            "correct_index": 0,
            "parameters": {"a": 7, "b": 8}  # Stored for grading
        },
        # ... more items
    ],
    "resources": [
        {
            "id": "topology",
            "content": "<svg>...</svg>",  # Rendered with instance params
            "parameters": {"site_code": "NYC", "subnet": "10.1.0.0/16"}
        }
    ]
}
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Content uniqueness** | % candidates with identical forms | 0% |
| **Delivery reliability** | % sessions without technical issues | > 99.5% |
| **Candidate satisfaction** | Post-exam UX survey score | > 4.2/5 |
| **Response capture** | % responses successfully recorded | 100% |
| **POD availability** | Time from request to ready | < 2 min |

## Open Questions

1. **agent-host vs LDS**: For Design module, should agent-host BE the delivery UI, or provide widgets embedded in LDS?
2. **Offline Resilience**: How to handle network interruptions during Deploy module?
3. **Hint Fairness**: If AI tutor is enabled, how to ensure fair scoring across candidates?
4. **Instance Caching**: Should generated instances be cached or generated on-demand?

---

_Last updated: December 25, 2025_
