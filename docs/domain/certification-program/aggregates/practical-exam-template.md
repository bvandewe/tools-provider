# Practical Exam Template

> **Purpose:** Architecture for templating long-form (5-8h) practical exams with unique content per candidate.

## The Challenge

Long-form practical exams are vulnerable to content exposure:

| Risk | Impact |
|------|--------|
| **Content Sharing** | Candidates share exact tasks with future cohorts |
| **Memorization** | Static content enables "brain dump" preparation |
| **Unfair Advantage** | Candidates with prior exposure outperform equally skilled peers |
| **Shelf Life** | Content must be replaced frequently (expensive) |

## Solution: Compositional Uniqueness

Generate unique exam instances by composing templated components:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPOSITIONAL UNIQUENESS MODEL                           │
│                                                                              │
│  Static Invariants (Same for all candidates):                               │
│  ─────────────────────────────────────────────                              │
│  • Skill objectives (WHAT is being tested)                                  │
│  • Time allocation per section                                              │
│  • Grading rubric structure                                                 │
│  • Pod topology (number of devices, connections)                            │
│                                                                              │
│  Templated Variables (Unique per candidate):                                │
│  ──────────────────────────────────────────                                 │
│  • Network topology details (IPs, subnets, VLANs)                          │
│  • Device identifiers (hostnames, domain names)                             │
│  • File/directory paths                                                     │
│  • Credential sets (usernames, temporary passwords)                         │
│  • Service configurations (ports, protocols, versions)                      │
│  • Scenario narrative (company names, user personas)                        │
│  • Error injection scenarios                                                │
│  • Task ordering (where tasks are independent)                              │
│                                                                              │
│  Result: Same skills tested, different execution path                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Template Structure: Practical Exam

```
PracticalExamTemplate
├── id: str
├── skill_id: str (references Skill in Blueprint)
├── name: str
├── duration_hours: float
│
├── scenario_template: ScenarioTemplate
│   ├── narrative_template: str (Jinja2 with {placeholders})
│   ├── company_name_pool: list[str]
│   ├── user_persona_pool: list[UserPersona]
│   └── context_variables: dict[str, VariableSpec]
│
├── pod_template: PodTemplate
│   ├── topology_type: str (e.g., "hub-spoke", "full-mesh")
│   ├── device_templates: list[DeviceTemplate]
│   │   ├── role: str (router, switch, server, client)
│   │   ├── image: str
│   │   ├── hostname_template: str
│   │   ├── interfaces: list[InterfaceTemplate]
│   │   │   ├── name: str
│   │   │   ├── ip_template: str
│   │   │   └── connected_to: str (device.interface)
│   │   └── initial_config_template: str
│   ├── network_templates: list[NetworkTemplate]
│   │   ├── name: str
│   │   ├── subnet_pool: str (CIDR block to allocate from)
│   │   └── vlan_pool: list[int]
│   └── credential_policy: CredentialPolicy
│
├── task_templates: list[TaskTemplate]
│   ├── id: str
│   ├── name_template: str
│   ├── objective: str (skill being tested - invariant)
│   ├── instructions_template: str (with {placeholders})
│   ├── dependencies: list[str] (other task IDs)
│   ├── parameters: dict[str, ParameterSpec]
│   ├── expected_state_template: ExpectedStateTemplate
│   │   ├── device: str
│   │   ├── checks: list[StateCheck]
│   │   │   ├── type: str (service_running, file_exists, config_contains, etc.)
│   │   │   ├── target_template: str
│   │   │   ├── expected_template: str
│   │   │   └── partial_credit: float | None
│   │   └── timeout_seconds: int
│   ├── grading_rules: list[GradingRule]
│   │   ├── name: str
│   │   ├── condition_template: str
│   │   ├── points: float
│   │   └── is_mandatory: bool (fails entire task if not met)
│   ├── hints: list[HintTemplate]
│   └── time_estimate_minutes: int
│
├── submission_config: SubmissionConfig
│   ├── points: list[SubmissionPoint]
│   │   ├── id: str
│   │   ├── after_tasks: list[str]
│   │   ├── label: str
│   │   └── triggers_grading: bool
│   ├── allow_resubmit: bool
│   └── max_resubmits: int | None
│
└── variation_constraints: VariationConstraints
    ├── min_variation_score: float (0.0-1.0, how different each instance must be)
    ├── blacklist_combinations: list[dict] (invalid parameter combinations)
    └── dependency_graph: DependencyGraph (ensures coherent variable resolution)
```

## Example: Network Troubleshooting Practical

```yaml
id: 'practical-tpl-net-troubleshoot-v1'
skill_id: 'NET.TROUBLESHOOT.ADVANCED'
name: 'Advanced Network Troubleshooting'
duration_hours: 6

scenario_template:
  narrative_template: |
    You are a network engineer at {company_name}, a {industry} company.

    {user_persona.name}, the {user_persona.role}, reports that users in the
    {department} department cannot access the {target_service} server.

    Your task is to diagnose and resolve the connectivity issues affecting
    the {affected_subnet} network segment.

    Pod access details:
    - Management IP: {mgmt_ip}
    - Username: {username}
    - Password: {password}

  company_name_pool:
    - 'Acme Industries'
    - 'TechCorp Solutions'
    - 'Global Systems Inc'
    - 'DataFlow Networks'

  user_persona_pool:
    - { name: 'Sarah Chen', role: 'Help Desk Manager' }
    - { name: 'Mike Rodriguez', role: 'IT Director' }
    - { name: 'Jennifer Park', role: 'Operations Lead' }

  context_variables:
    industry:
      type: enum
      values: ['manufacturing', 'healthcare', 'financial services', 'retail']
    department:
      type: enum
      values: ['Sales', 'Engineering', 'HR', 'Finance', 'Marketing']
    target_service:
      type: enum
      values: ['file', 'database', 'email', 'CRM', 'ERP']

pod_template:
  topology_type: 'hub-spoke'

  device_templates:
    - role: core_router
      image: 'cisco-ios-17'
      hostname_template: 'CORE-{site_code}'
      interfaces:
        - name: 'GigabitEthernet0/0'
          ip_template: '{core_network}.1/24'
          connected_to: 'distribution_switch.GigabitEthernet0/1'
        - name: 'GigabitEthernet0/1'
          ip_template: '{wan_network}.1/30'
          connected_to: 'wan_router.GigabitEthernet0/0'
      initial_config_template: 'config/core_router_init.j2'

    - role: distribution_switch
      image: 'cisco-ios-17'
      hostname_template: 'DIST-{site_code}'
      interfaces:
        # ... interface definitions

    - role: affected_server
      image: 'ubuntu-22.04'
      hostname_template: '{target_service}-srv-{server_id}'
      interfaces:
        - name: 'eth0'
          ip_template: '{affected_subnet}.10/24'

  network_templates:
    - name: core_network
      subnet_pool: '10.{site_octet}.0.0/16'
    - name: affected_subnet
      subnet_pool: '192.168.{vlan_id}.0/24'
      vlan_pool: [100, 110, 120, 130, 140, 150]
    - name: wan_network
      subnet_pool: '172.16.{wan_segment}.0/30'

  credential_policy:
    username_template: 'exam_{candidate_id}'
    password_policy: 'random_16_chars'  # pragma: allowlist secret
    privilege_level: 15

task_templates:
  - id: 'task-1-identify'
    name_template: 'Identify Connectivity Issue'
    objective: 'Use diagnostic tools to identify network fault'
    instructions_template: |
      Users in {department} cannot reach {target_service}-srv-{server_id}.

      1. Log into the network devices and identify the root cause
      2. Document your findings before proceeding to fix

      Affected host: {target_service}-srv-{server_id} ({affected_subnet}.10)

    dependencies: []
    parameters:
      injected_fault:
        type: enum
        values:
          - 'acl_blocking'
          - 'vlan_mismatch'
          - 'routing_missing'
          - 'interface_down'
          - 'duplex_mismatch'
    expected_state_template:
      device: 'candidate_workstation'
      checks:
        - type: file_exists
          target_template: '/home/{username}/findings.txt'
          partial_credit: 0.3
    grading_rules:
      - name: 'correct_diagnosis'
        condition_template: 'findings.txt contains "{injected_fault}"'
        points: 10
        is_mandatory: false
    time_estimate_minutes: 30

  - id: 'task-2-resolve'
    name_template: 'Resolve Connectivity Issue'
    objective: 'Apply correct fix to restore connectivity'
    instructions_template: |
      Based on your diagnosis, resolve the connectivity issue.

      Verify that {target_service}-srv-{server_id} is reachable from
      the {department} VLAN ({affected_subnet}.0/24).

    dependencies: ['task-1-identify']
    expected_state_template:
      device: 'affected_server'
      checks:
        - type: ping_reachable
          target_template: '{affected_subnet}.1'  # Default gateway
          expected_template: 'success'
        - type: tcp_port_open
          target_template: '443'
          expected_template: 'open'
    grading_rules:
      - name: 'connectivity_restored'
        condition_template: 'ping from {department}_client to {affected_subnet}.10 succeeds'
        points: 15
        is_mandatory: true
      - name: 'minimal_changes'
        condition_template: 'config_diff_lines < 10'
        points: 5
        is_mandatory: false
    time_estimate_minutes: 45

  # ... additional tasks

submission_config:
  points:
    - id: 'submit-diagnosis'
      after_tasks: ['task-1-identify']
      label: 'Submit Diagnosis'
      triggers_grading: true
    - id: 'submit-final'
      after_tasks: ['task-2-resolve', 'task-3-document']
      label: 'Final Submission'
      triggers_grading: true
  allow_resubmit: true
  max_resubmits: 2

variation_constraints:
  min_variation_score: 0.7
  blacklist_combinations:
    - { injected_fault: 'acl_blocking', target_service: 'file' }  # Too easy to diagnose
  dependency_graph:
    # Ensure coherent variable resolution
    affected_subnet.vlan_id -> distribution_switch.vlan_config
    target_service -> affected_server.services_running
```

## Instance Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRACTICAL EXAM INSTANCE GENERATION                        │
│                                                                              │
│  Input: PracticalExamTemplate + CandidateID + RandomSeed                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. VARIABLE RESOLUTION                                                │   │
│  │                                                                       │   │
│  │    Topological sort of dependency graph                               │   │
│  │    ↓                                                                  │   │
│  │    Resolve variables in order (respecting constraints)                │   │
│  │    ↓                                                                  │   │
│  │    Validate: no blacklist combinations, min_variation_score met       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 2. POD CONFIGURATION GENERATION                                       │   │
│  │                                                                       │   │
│  │    Render device configs from templates                               │   │
│  │    ↓                                                                  │   │
│  │    Inject fault condition into appropriate device                     │   │
│  │    ↓                                                                  │   │
│  │    Generate candidate credentials                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 3. TASK INSTANTIATION                                                 │   │
│  │                                                                       │   │
│  │    Render instructions from templates                                 │   │
│  │    ↓                                                                  │   │
│  │    Compute expected states from templates                             │   │
│  │    ↓                                                                  │   │
│  │    Parameterize grading rules                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 4. NARRATIVE GENERATION (LLM-Assisted)                                │   │
│  │                                                                       │   │
│  │    Generate coherent scenario narrative                               │   │
│  │    ↓                                                                  │   │
│  │    Ensure consistency across all task instructions                    │   │
│  │    ↓                                                                  │   │
│  │    Create immersive context (emails, tickets, etc.)                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  Output: PracticalExamInstance                                              │
│  ├── pod_config: PodConfiguration                                           │
│  ├── tasks: list[TaskInstance]                                              │
│  ├── scenario_narrative: str                                                │
│  ├── grading_package: GradingPackage                                        │
│  └── candidate_materials: CandidateMaterials                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Grading Rule Adaptation

Grading rules must be parameterized to match the instance:

```python
# Example: Grading rule template
class GradingRuleTemplate:
    name: str
    condition_template: str  # "{target_service}-srv-{server_id} responds on port 443"
    points: float

# Instance with resolved variables
class GradingRuleInstance:
    name: str
    condition: str  # "database-srv-42 responds on port 443"
    points: float

    def evaluate(self, device_state: DeviceState) -> GradingResult:
        # Evaluate condition against actual device state
        ...
```

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Template Exposure** | Templates stored encrypted; access logged |
| **Seed Prediction** | Cryptographically secure random seed per candidate |
| **Instance Caching** | Instances generated on-demand, not pre-cached |
| **Grading Leakage** | Grading rules never exposed to candidate |
| **Narrative Consistency** | LLM prompts reviewed for unintended hints |

## AI Agent Opportunities

| Task | Agent Role |
|------|------------|
| **Narrative Generation** | Create immersive, coherent scenario text |
| **Coherence Validation** | Check all task instructions are consistent |
| **Difficulty Calibration** | Estimate instance difficulty from parameters |
| **Hint Generation** | Create progressive hints without revealing answers |
| **Post-Exam Explanation** | Explain what candidate did wrong (after grading) |

---

_Last updated: December 24, 2025_
