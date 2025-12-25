# Use Case: Device State Grading

> **Primary Actor:** grading-system
> **Supporting Actors:** output-collectors, pod-manager, Analyst, AI Grading Assistant
> **Systems Involved:** grading-system (new), output-collectors, pod-manager, session-manager, blueprint-manager

## Overview

Device State Grading evaluates candidate performance in the Deploy module by analyzing the final state of POD devices against expected configurations. This is where the candidate's hands-on work is objectively measured.

## Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT GRADING FLOW (Deploy Module)                    │
│                                                                              │
│  LDS                    output-collectors              grading-system        │
│   │                            │                            │                │
│   │  1. exam.completed.v1      │                            │                │
│   │───────────────────────────►│                            │                │
│   │                            │                            │                │
│   │                            │  2. For each device:       │                │
│   │                            │     Execute collection     │                │
│   │                            │     commands               │                │
│   │                            │                            │                │
│   │                            │  ┌─────────────────────┐   │                │
│   │                            │  │ show running-config │   │                │
│   │                            │  │ show ip route       │   │                │
│   │                            │  │ show ip bgp summary │   │                │
│   │                            │  │ show vlan brief     │   │                │
│   │                            │  │ ...                 │   │                │
│   │                            │  └─────────────────────┘   │                │
│   │                            │                            │                │
│   │                            │  3. Store outputs          │                │
│   │                            │────────────────────────────►               │
│   │                            │                            │                │
│   │                            │                            │  4. For each   │
│   │                            │                            │     grading    │
│   │                            │                            │     rule:      │
│   │                            │                            │     evaluate   │
│   │                            │                            │                │
│   │                            │                            │  ┌──────────┐  │
│   │                            │                            │  │ PASS/FAIL│  │
│   │                            │                            │  │ per item │  │
│   │                            │                            │  └──────────┘  │
│   │                            │                            │                │
│   │                            │                            │  5. Aggregate  │
│   │                            │                            │     scores     │
│   │                            │                            │                │
│   │◄───────────────────────────────────────────────────────│  6. Return     │
│   │                            │                            │     results    │
│   │                            │                            │                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Limitations

| Limitation | Impact | Root Cause |
|------------|--------|------------|
| **Dichotomous scoring** | Low reliability | Items are pass/fail, no partial credit |
| **Static grading rules** | Inflexible | Rules hardcoded in XML, hard to update |
| **Limited device types** | Coverage gaps | Collectors only support CLI-based devices |
| **No intermediate state** | Debugging hard | Only final state captured |
| **Manual rule authoring** | Slow iteration | No AI assistance for rule creation |
| **Vague KSA alignment** | Validity questions | Rules not traced to specific KSAs |

## The Polytomous Scoring Opportunity

Current dichotomous (pass/fail) scoring loses valuable information:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DICHOTOMOUS vs POLYTOMOUS SCORING                         │
│                                                                              │
│  DICHOTOMOUS (Current)                                                       │
│  ─────────────────────                                                       │
│  Task: Configure BGP peering                                                 │
│  Result: FAIL (0 points)                                                     │
│                                                                              │
│  What we DON'T know:                                                         │
│  - Was the router bgp command entered? (partial understanding)               │
│  - Was the neighbor IP correct but AS wrong? (minor error)                   │
│  - Was everything correct except authentication? (near-miss)                 │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                              │
│  POLYTOMOUS (Proposed)                                                       │
│  ─────────────────────                                                       │
│  Task: Configure BGP peering (10 points possible)                            │
│                                                                              │
│  Rubric:                                                                     │
│  ┌─────────────────────────────────────────┬────────┬───────────────────┐   │
│  │ Criterion                               │ Points │ Candidate Result  │   │
│  ├─────────────────────────────────────────┼────────┼───────────────────┤   │
│  │ BGP process configured                  │ 2      │ ✓ 2/2             │   │
│  │ Correct neighbor IP                     │ 2      │ ✓ 2/2             │   │
│  │ Correct remote-as                       │ 2      │ ✗ 0/2 (wrong AS)  │   │
│  │ Network statements present              │ 2      │ ✓ 2/2             │   │
│  │ Neighbor state = Established            │ 2      │ ✗ 0/2 (Active)    │   │
│  ├─────────────────────────────────────────┼────────┼───────────────────┤   │
│  │ TOTAL                                   │ 10     │ 6/10 (60%)        │   │
│  └─────────────────────────────────────────┴────────┴───────────────────┘   │
│                                                                              │
│  Benefits:                                                                   │
│  - Finer discrimination between candidates                                   │
│  - Diagnostic feedback for remediation                                       │
│  - Better reliability (more measurement points)                              │
│  - Clearer KSA alignment (each criterion → KSA)                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Future State: AI-Augmented Polytomous Grading

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI-AUGMENTED GRADING PIPELINE                             │
│                                                                              │
│  exam.completed.v1                                                           │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1. STATE COLLECTION (output-collectors)                              │    │
│  │                                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │    │
│  │  │   CLI      │  │   API      │  │  Web/REST  │  │   VNC      │    │    │
│  │  │ Collectors │  │ Collectors │  │ Collectors │  │ Collectors │    │    │
│  │  │            │  │            │  │            │  │ (future)   │    │    │
│  │  │ • show cmd │  │ • REST GET │  │ • HTTP req │  │ • Screenshot│   │    │
│  │  │ • config   │  │ • NETCONF  │  │ • GraphQL  │  │ • OCR      │    │    │
│  │  │ • logs     │  │ • gNMI     │  │            │  │            │    │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │    │
│  │                                                                      │    │
│  │  Output: DeviceStateSnapshot per device                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 2. STATE NORMALIZATION                                               │    │
│  │                                                                      │    │
│  │  Raw output → Structured data                                        │    │
│  │                                                                      │    │
│  │  "show ip bgp summary" output:                                       │    │
│  │  ┌────────────────────────────────────────────┐                     │    │
│  │  │ Neighbor   V  AS   MsgRcvd MsgSent  State  │                     │    │
│  │  │ 10.1.1.2   4  65002    42      45   Active │                     │    │
│  │  └────────────────────────────────────────────┘                     │    │
│  │                         ↓                                            │    │
│  │  Normalized:                                                         │    │
│  │  {                                                                   │    │
│  │    "bgp_neighbors": [                                                │    │
│  │      {                                                               │    │
│  │        "neighbor_ip": "10.1.1.2",                                    │    │
│  │        "remote_as": 65002,                                           │    │
│  │        "state": "Active"                                             │    │
│  │      }                                                               │    │
│  │    ]                                                                 │    │
│  │  }                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 3. RULE EVALUATION (grading-system)                                  │    │
│  │                                                                      │    │
│  │  GradingRuleSet (from FormSpec + SkillTemplate)                     │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │ task_id: task-bgp-peering                                    │   │    │
│  │  │ ksa_id: NET.BGP.PEER.BASIC                                   │   │    │
│  │  │                                                              │   │    │
│  │  │ criteria:                                                    │   │    │
│  │  │   - id: bgp-process                                          │   │    │
│  │  │     description: "BGP process configured"                    │   │    │
│  │  │     device: "{router_a}"                                     │   │    │
│  │  │     check: "config contains 'router bgp {as_a}'"            │   │    │
│  │  │     points: 2                                                │   │    │
│  │  │     mandatory: false                                         │   │    │
│  │  │                                                              │   │    │
│  │  │   - id: neighbor-ip                                          │   │    │
│  │  │     description: "Correct neighbor IP configured"            │   │    │
│  │  │     device: "{router_a}"                                     │   │    │
│  │  │     check: "bgp_neighbors[*].neighbor_ip contains '{ip_b}'" │   │    │
│  │  │     points: 2                                                │   │    │
│  │  │     mandatory: false                                         │   │    │
│  │  │                                                              │   │    │
│  │  │   - id: neighbor-state                                       │   │    │
│  │  │     description: "BGP neighbor state is Established"         │   │    │
│  │  │     device: "{router_a}"                                     │   │    │
│  │  │     check: "bgp_neighbors[?neighbor_ip=='{ip_b}'].state == 'Established'"│
│  │  │     points: 2                                                │   │    │
│  │  │     mandatory: true  # Required for any points               │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 4. AI-ASSISTED EVALUATION (for complex criteria)                     │    │
│  │                                                                      │    │
│  │  Some criteria require semantic understanding:                       │    │
│  │                                                                      │    │
│  │  Criterion: "Configuration follows best practices"                   │    │
│  │  AI Evaluator:                                                       │    │
│  │  - Check for hardcoded passwords (security)                          │    │
│  │  - Verify interface descriptions present (documentation)             │    │
│  │  - Assess naming conventions (maintainability)                       │    │
│  │                                                                      │    │
│  │  Output: Rubric score + justification                                │    │
│  │  {                                                                   │    │
│  │    "score": 2,                                                       │    │
│  │    "max_score": 3,                                                   │    │
│  │    "justification": "Passwords encrypted, descriptions present,     │    │
│  │                      but hostnames inconsistent with standard"       │    │
│  │  }                                                                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 5. SCORE AGGREGATION                                                 │    │
│  │                                                                      │    │
│  │  ┌────────────────────────────────────────────────────────────────┐ │    │
│  │  │ Task: Configure BGP Peering                                    │ │    │
│  │  │                                                                │ │    │
│  │  │ Criteria Results:                                              │ │    │
│  │  │   bgp-process:     2/2  ✓                                      │ │    │
│  │  │   neighbor-ip:     2/2  ✓                                      │ │    │
│  │  │   remote-as:       0/2  ✗ (configured 65001, expected 65002)  │ │    │
│  │  │   network-stmt:    2/2  ✓                                      │ │    │
│  │  │   neighbor-state:  0/2  ✗ (Active, expected Established)      │ │    │
│  │  │   best-practices:  2/3  ~ (partial)                            │ │    │
│  │  │                                                                │ │    │
│  │  │ Task Score: 8/13 (61.5%)                                       │ │    │
│  │  │ KSA Alignment: NET.BGP.PEER.BASIC → 61.5% proficiency          │ │    │
│  │  └────────────────────────────────────────────────────────────────┘ │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  grading.completed.v1 → session-manager, analytics                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Device State Snapshot Schema

```python
@dataclass
class DeviceStateSnapshot:
    """Complete state capture for a single device."""

    device_id: str
    device_type: str  # router, switch, server, etc.
    hostname: str
    collection_timestamp: datetime
    collection_duration_ms: int

    # Raw outputs (for audit/debugging)
    raw_outputs: dict[str, str]  # command → output

    # Normalized state (for rule evaluation)
    normalized_state: NormalizedDeviceState

    # Collection metadata
    collection_errors: list[CollectionError]
    collector_version: str


@dataclass
class NormalizedDeviceState:
    """Structured representation of device state."""

    # Configuration
    running_config: str
    startup_config: str | None
    config_diff: str | None  # vs baseline

    # Interfaces
    interfaces: list[InterfaceState]

    # Routing
    routing_table: list[RouteEntry]
    ospf_neighbors: list[OSPFNeighbor] | None
    bgp_neighbors: list[BGPNeighbor] | None
    eigrp_neighbors: list[EIGRPNeighbor] | None

    # Switching
    vlans: list[VlanState] | None
    spanning_tree: SpanningTreeState | None

    # Security
    acls: list[ACLState] | None
    nat_translations: list[NATEntry] | None

    # Services
    dhcp_bindings: list[DHCPBinding] | None
    ntp_status: NTPStatus | None

    # System
    version_info: VersionInfo
    cpu_utilization: float | None
    memory_utilization: float | None
    uptime_seconds: int | None

    # Logs (relevant excerpts)
    log_entries: list[LogEntry]

    # Files (for servers)
    file_checksums: dict[str, str] | None
    service_status: dict[str, str] | None


@dataclass
class BGPNeighbor:
    """Normalized BGP neighbor state."""
    neighbor_ip: str
    remote_as: int
    state: str  # Idle, Connect, Active, OpenSent, OpenConfirm, Established
    uptime: str | None
    prefixes_received: int | None
    prefixes_sent: int | None
```

## Grading Rule Language

A DSL for expressing grading criteria:

```yaml
# Grading rule definition
grading_rule:
  id: bgp-established
  description: "BGP neighbor reaches Established state"
  ksa_id: NET.BGP.PEER.BASIC

  # Target device (parameterized)
  device: "{router_a}"

  # Evaluation expression (JMESPath-like)
  expression: |
    normalized_state.bgp_neighbors[?neighbor_ip=='{peer_ip}'].state | [0] == 'Established'

  # Scoring
  scoring:
    type: dichotomous  # or 'polytomous'
    points_if_true: 5
    points_if_false: 0

  # Dependencies (optional)
  requires:
    - bgp-process-configured
    - bgp-neighbor-configured


# Polytomous grading rule
grading_rule:
  id: bgp-config-quality
  description: "BGP configuration quality assessment"
  ksa_id: NET.BGP.CONFIG.QUALITY

  device: "{router_a}"

  scoring:
    type: polytomous
    max_points: 6

    criteria:
      - id: has-description
        description: "Neighbor has description configured"
        expression: |
          contains(normalized_state.running_config, 'neighbor {peer_ip} description')
        points: 1

      - id: has-password
        description: "MD5 authentication configured"
        expression: |
          contains(normalized_state.running_config, 'neighbor {peer_ip} password')
        points: 2

      - id: has-timers
        description: "Custom timers configured for stability"
        expression: |
          contains(normalized_state.running_config, 'neighbor {peer_ip} timers')
        points: 1

      - id: has-soft-reconfig
        description: "Soft reconfiguration enabled"
        expression: |
          contains(normalized_state.running_config, 'neighbor {peer_ip} soft-reconfiguration')
        points: 2
```

## AI Grading Assistant

For complex or subjective criteria:

```yaml
agent_id: 'grading-assistant'
name: 'Grading Assistant'
description: 'Evaluates complex configuration criteria using semantic analysis'

system_prompt: |
  You are an expert network engineer evaluating candidate configurations
  for certification exams.

  Your task:
  1. Analyze the provided device configuration
  2. Evaluate against the specified rubric criteria
  3. Provide objective scores with clear justification
  4. Identify partial credit opportunities

  Evaluation principles:
  - Be consistent across candidates
  - Focus on functionality over style
  - Recognize equivalent solutions
  - Document reasoning for audit trail

tools:
  - grading.get_expected_state
  - grading.get_rubric
  - grading.submit_evaluation
  - knowledge.get_best_practices
  - knowledge.get_equivalent_commands

access_control:
  allowed_roles: ['grading_system']  # Not human-accessible
```

### AI Evaluation Example

```python
# Complex criterion: "Troubleshooting approach was methodical"
ai_evaluation_request = {
    "criterion": {
        "id": "troubleshooting-method",
        "description": "Candidate demonstrated methodical troubleshooting",
        "max_points": 5
    },
    "evidence": {
        "console_history": [
            "show ip interface brief",
            "show ip route",
            "show ip bgp summary",
            "show ip bgp neighbors 10.1.1.2",
            "debug ip bgp",
            "no debug all",
            "show running-config | section router bgp"
        ],
        "timestamps": ["10:01", "10:02", "10:03", "10:05", "10:06", "10:08", "10:10"],
        "config_changes": [
            {"time": "10:12", "change": "neighbor 10.1.1.2 remote-as 65002"}
        ]
    },
    "rubric": {
        "5": "Systematic top-down approach, efficient diagnosis, minimal unnecessary commands",
        "4": "Generally methodical with minor inefficiencies",
        "3": "Some structure but with significant detours",
        "2": "Trial-and-error approach with eventual success",
        "1": "Random commands, no clear methodology",
        "0": "Did not attempt troubleshooting"
    }
}

ai_evaluation_response = {
    "score": 4,
    "justification": """
    Candidate demonstrated a methodical approach:
    1. Started with interface status verification (show ip interface brief)
    2. Checked routing table (show ip route)
    3. Examined BGP summary, then specific neighbor
    4. Used debug briefly and disabled appropriately
    5. Verified configuration before making changes

    Minor inefficiency: Could have checked 'show ip bgp neighbors' earlier
    to see the specific error state.

    Score: 4/5 - Generally methodical with minor inefficiencies.
    """,
    "evidence_references": [
        "Console command sequence shows logical progression",
        "Debug was used appropriately and disabled after use",
        "Config change was targeted and correct"
    ]
}
```

## Collector Types

| Collector | Device Types | Method | Challenges |
|-----------|--------------|--------|------------|
| **CLI Collector** | Routers, Switches | SSH/Telnet + expect | Parsing variations |
| **API Collector** | Modern devices | NETCONF, gNMI, REST | Schema differences |
| **Web Collector** | Web services | HTTP requests | Authentication, dynamic content |
| **File Collector** | Servers | SSH + file read | Permissions, paths |
| **DB Collector** | Databases | SQL queries | Connection, sanitization |
| **VNC Collector** | GUI-only | Screenshot + OCR | Accuracy, positioning |

### Collector Interface

```python
class DeviceCollector(ABC):
    """Base interface for device state collectors."""

    @abstractmethod
    async def connect(self, device: DeviceInstance) -> None:
        """Establish connection to device."""
        ...

    @abstractmethod
    async def collect(
        self,
        commands: list[CollectionCommand]
    ) -> dict[str, CollectionResult]:
        """Execute collection commands and return results."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection."""
        ...


@dataclass
class CollectionCommand:
    """Command to execute for state collection."""
    id: str
    command: str  # "show ip bgp summary" or "GET /api/status"
    timeout_seconds: int = 30
    parse_format: str = "text"  # text, json, xml
    normalizer: str | None = None  # Normalizer function name
```

## Event Flow

```
LDS                    Event Broker              Services
 │                          │                        │
 │  exam.completed.v1       │                        │
 │─────────────────────────►│                        │
 │                          │───────────────────────►│ session-manager
 │                          │                        │ (mark attempt complete)
 │                          │                        │
 │                          │───────────────────────►│ output-collectors
 │                          │                        │ (begin collection)
 │                          │                        │
 │                          │                        │
output-collectors           │                        │
 │                          │                        │
 │  collection.completed.v1 │                        │
 │─────────────────────────►│                        │
 │  (includes state blob)   │───────────────────────►│ grading-system
 │                          │                        │ (begin evaluation)
 │                          │                        │
 │                          │                        │
grading-system              │                        │
 │                          │                        │
 │  grading.completed.v1    │                        │
 │─────────────────────────►│                        │
 │  (includes scores)       │───────────────────────►│ session-manager
 │                          │                        │ (update result)
 │                          │                        │
 │                          │───────────────────────►│ analytics
 │                          │                        │ (store for analysis)
 │                          │                        │
```

## KSA Traceability

Each grading criterion maps to a specific KSA, enabling:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KSA TRACEABILITY MATRIX                            │
│                                                                              │
│  KSA Statement                          Grading Criteria        Candidate    │
│  ────────────────────────────────────   ──────────────────      Result       │
│                                                                              │
│  NET.BGP.PEER.BASIC                                                          │
│  "Configure BGP peering"                                                     │
│    ├── bgp-process-configured          → 2/2 ✓                              │
│    ├── neighbor-ip-correct             → 2/2 ✓                              │
│    ├── remote-as-correct               → 0/2 ✗                              │
│    └── neighbor-established            → 0/2 ✗                              │
│                                        ─────────                             │
│                                        4/8 = 50%                             │
│                                                                              │
│  NET.BGP.ADVERTISE.NETWORKS                                                  │
│  "Advertise networks via BGP"                                                │
│    ├── network-statement-present       → 2/2 ✓                              │
│    ├── correct-networks-advertised     → 2/2 ✓                              │
│    └── no-extraneous-networks          → 1/1 ✓                              │
│                                        ─────────                             │
│                                        5/5 = 100%                            │
│                                                                              │
│  Overall KSA Profile:                                                        │
│  ┌────────────────────────────┬─────────┬────────────────────────────────┐  │
│  │ KSA                        │ Score   │ Proficiency                    │  │
│  ├────────────────────────────┼─────────┼────────────────────────────────┤  │
│  │ NET.BGP.PEER.BASIC         │ 50%     │ ▓▓▓▓░░░░░░ Developing          │  │
│  │ NET.BGP.ADVERTISE.NETWORKS │ 100%    │ ▓▓▓▓▓▓▓▓▓▓ Proficient          │  │
│  │ NET.BGP.TROUBLESHOOT       │ 75%     │ ▓▓▓▓▓▓▓░░░ Competent           │  │
│  └────────────────────────────┴─────────┴────────────────────────────────┘  │
│                                                                              │
│  Diagnostic Value: Candidate can advertise networks but struggles with      │
│                    initial peering establishment (likely AS config issues)  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Polytomous adoption** | % tasks with multi-point rubrics | > 80% |
| **KSA traceability** | % criteria linked to KSAs | 100% |
| **Collection success** | % devices successfully collected | > 99% |
| **Grading latency** | Time from submit to score | < 5 min |
| **Inter-rater reliability** | AI vs human agreement | > 0.90 |
| **Candidate feedback** | % with diagnostic report | 100% |

## Open Questions

1. **Rubric Authoring**: Who defines polytomous rubrics - SMEs, psychometricians, or AI-assisted?
2. **Partial Credit Thresholds**: How to determine point allocations per criterion?
3. **AI Grading Approval**: Should AI scores for subjective criteria require human review?
4. **Baseline Configs**: How to handle candidates who "break" devices vs never configured?
5. **Time-Based Criteria**: Should methodology scores consider command timing?

---

_Last updated: December 25, 2025_
