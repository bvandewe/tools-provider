# Certification Program - Actor Roles

> **Purpose:** Define all actors, their responsibilities, and AI augmentation opportunities.

---

## Organizational Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CISCO CERTIFICATIONS ORGANIZATION                         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     CONTENT TEAMS (EPMs)                             │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────────┐ │    │
│  │  │   APS TEAM              │    │   CCIE/EXPERT TEAM              │ │    │
│  │  │   (Associate/           │    │   (CCIE + CCDE)                 │ │    │
│  │  │    Professional/        │    │                                 │ │    │
│  │  │    Specialist)          │    │                                 │ │    │
│  │  │                         │    │                                 │ │    │
│  │  │  • Enterprise Track     │    │  • CCIE Enterprise              │ │    │
│  │  │  • Security Track       │    │  • CCIE Security                │ │    │
│  │  │  • DevNet Track         │    │  • CCIE Collaboration           │ │    │
│  │  │  • Collaboration Track  │    │  • CCIE Service Provider        │ │    │
│  │  │  • Data Center Track    │    │  • CCIE Data Center             │ │    │
│  │  │  • Service Provider     │    │  • CCDE (Design Expert)         │ │    │
│  │  │                         │    │                                 │ │    │
│  │  │  Exam Types:            │    │  Exam Types:                    │ │    │
│  │  │  • Core Exams           │    │  • Written Qualifying           │ │    │
│  │  │  • Concentration Exams  │    │  • Practical Lab (8h on-site)   │ │    │
│  │  │  • Specialist Exams     │    │                                 │ │    │
│  │  │                         │    │  Delivery:                      │ │    │
│  │  │  Delivery:              │    │  • Cisco LabLocations only      │ │    │
│  │  │  • Pearson VUE          │    │  • Hardened Workstations        │ │    │
│  │  │  • Remote Proctored     │    │  • Private Network DMZ          │ │    │
│  │  │                         │    │                                 │ │    │
│  │  └─────────────────────────┘    └─────────────────────────────────┘ │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     OPERATIONAL TEAMS                                │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────────┐ │    │
│  │  │   OPERATIONS TEAM       │    │   SYSTEMS TEAM                  │ │    │
│  │  │   (Proctoring)          │    │   (Infrastructure)              │ │    │
│  │  │                         │    │                                 │ │    │
│  │  │  Session Prep:          │    │  Roles:                         │ │    │
│  │  │  • Assign POD/Form      │    │  • Operators                    │ │    │
│  │  │  • Check history        │    │  • System Administrators        │ │    │
│  │  │  • Avoid repeats        │    │                                 │ │    │
│  │  │                         │    │  Shared Services:               │ │    │
│  │  │  Day-of-Exam:           │    │  • Mosaic                       │ │    │
│  │  │  • Morning Briefing     │    │  • LDS                          │ │    │
│  │  │  • Identity Verify      │    │  • POD Automation               │ │    │
│  │  │  • Seat Assignment      │    │                                 │ │    │
│  │  │  • Issue Resolution     │    │  Responsibilities:              │ │    │
│  │  │                         │    │  • Capture requirements         │ │    │
│  │  │  Localized Rules:       │    │  • Prioritize change requests   │ │    │
│  │  │  • Per LabLocation      │    │  • Coordinate with vendors      │ │    │
│  │  │                         │    │  • Deploy to environments       │ │    │
│  │  │                         │    │  • Monitor operations           │ │    │
│  │  └─────────────────────────┘    └─────────────────────────────────┘ │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │    │
│  │  │   ANALYSTS TEAM (Security & Integrity)                          │ │    │
│  │  │                                                                 │ │    │
│  │  │  • Investigate security breaches                                │ │    │
│  │  │  • Handle compromised/exposed content                           │ │    │
│  │  │  • Research misbehaving candidates                              │ │    │
│  │  │  • Coordinate item retirement/rotation                          │ │    │
│  │  │                                                                 │ │    │
│  │  └─────────────────────────────────────────────────────────────────┘ │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Actor Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CERTIFICATION PROGRAM ACTORS                         │
│                                                                              │
│  CONTENT LIFECYCLE                     DELIVERY & SUPPORT                    │
│  ─────────────────                     ──────────────────                   │
│                                                                              │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │ Certification    │                  │     Proctor      │                 │
│  │ Owner            │                  │                  │                 │
│  │ • Blueprint mgmt │                  │ • Session monitor│                 │
│  │ • Analytics      │                  │ • Candidate help │                 │
│  └────────┬─────────┘                  └──────────────────┘                 │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │   ExamAuthor     │                  │    Candidate     │                 │
│  │   (SME)          │                  │                  │                 │
│  │ • Content draft  │                  │ • Takes exams    │                 │
│  │ • Validation     │                  │ • Seeks help     │                 │
│  └────────┬─────────┘                  └──────────────────┘                 │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │  ItemReviewer    │                  │    Analyst       │                 │
│  │                  │                  │                  │                 │
│  │ • Fairness check │                  │ • Score analysis │                 │
│  │ • Validity check │                  │ • Trend reports  │                 │
│  └────────┬─────────┘                  └──────────────────┘                 │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │     Tester       │                  │ Security Analyst │                 │
│  │                  │                  │                  │                 │
│  │ • Form testing   │                  │ • Breach invest. │                 │
│  │ • UX validation  │                  │ • Content protect│                 │
│  └──────────────────┘                  └──────────────────┘                 │
│                                                                              │
│  INFRASTRUCTURE                                                              │
│  ──────────────                                                             │
│                                                                              │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │    Operator      │                  │ System Admin     │                 │
│  │                  │                  │                  │                 │
│  │ • Monitor        │                  │ • Deploy code    │                 │
│  │ • Troubleshoot   │                  │ • Configure env  │                 │
│  └──────────────────┘                  └──────────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## APS Team: CertificationOwner (EPM)

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Blueprint Management** | Create, revise, and publish ExamBlueprints |
| **MQC Definition** | Define Minimally Qualified Candidate criteria |
| **Content Oversight** | Approve major content changes |
| **Analytics Review** | Monitor certification health metrics |
| **Stakeholder Communication** | Report to business/regulatory bodies |

### Current Workflow (Without AI)

1. Review existing Blueprint in spreadsheet/document
2. Consult with SMEs on KSA updates
3. Manually update Blueprint structure
4. Request content updates from Authors
5. Review analytics reports from separate system
6. Export reports for stakeholders

### Desired AI-Augmented Workflow

1. **Chat to query Blueprint health**
   - "What's the coverage for Network Security topic?"
   - "Which Skills have no ItemTemplates?"
   - "Show me performance trends for Topic X"

2. **AI-assisted Blueprint editing**
   - "Add a new Skill under Cloud Architecture: 'Configure multi-region failover'"
   - "Generate KSA statements for this Skill"
   - "Validate this Blueprint against MQC definition"

3. **Proactive alerts**
   - "Topic Y has 20% lower pass rate than average—investigate?"
   - "3 Items flagged for fairness review this week"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `blueprint-assistant` |
| System Prompt Focus | Blueprint structure, coverage analysis, KSA hierarchy |
| Tools | `get_blueprint`, `update_topic`, `analyze_coverage`, `generate_ksa`, `query_analytics` |
| Knowledge Namespaces | `certification-core`, `exam-analytics` |
| Access Level | Full Blueprint CRUD, read-only analytics |

---

## ExamAuthor (SME)

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Content Drafting** | Create ItemTemplates and SkillTemplates |
| **KSA Alignment** | Ensure Items measure intended KSA |
| **Difficulty Calibration** | Set appropriate difficulty levels |
| **Template Validation** | Verify generated Items are valid |

### Current Workflow (Without AI)

1. Receive assignment for Skill needing content
2. Write Item stems manually
3. Create distractors (often ad-hoc)
4. Submit for review
5. Iterate on feedback
6. For practical: write task instructions and grading scripts

### Desired AI-Augmented Workflow

1. **AI-assisted drafting**
   - "Generate 5 MCQ stems for Skill: 'Configure BGP peering'"
   - "Create distractors for this stem using common misconceptions"
   - "Suggest difficulty level based on KSA requirements"

2. **Validation assistance**
   - "Does this Item align with KSA statement X?"
   - "Check this stem for ambiguity"
   - "Validate distractor plausibility"

3. **Template creation**
   - "Convert this Item to a SkillTemplate with variable parameters"
   - "What parameters can be randomized in this practical task?"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `content-author` |
| System Prompt Focus | Item generation, KSA alignment, distractor quality |
| Tools | `generate_item`, `validate_ksa_alignment`, `check_difficulty`, `create_template`, `submit_for_review` |
| Knowledge Namespaces | `certification-core`, `item-authoring-guidelines` |
| Access Level | Create/edit own Items, read Blueprint |

---

## ItemReviewer

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Fairness Review** | Ensure Items are unbiased |
| **Validity Check** | Verify Items measure intended KSA |
| **Clarity Review** | Check for ambiguous wording |
| **Approval/Rejection** | Sign off or flag Items |

### Current Workflow (Without AI)

1. Access review queue
2. Read Item and check against guidelines
3. Cross-reference with KSA statement
4. Make approve/reject decision
5. Write feedback for rejections

### Desired AI-Augmented Workflow

1. **AI-assisted review**
   - "Summarize potential fairness issues in this Item"
   - "Does this Item measure the stated KSA?"
   - "Highlight ambiguous phrases"

2. **Batch processing**
   - "Show me all Items flagged for cultural bias"
   - "Compare this Item to similar approved Items"

3. **Decision support**
   - "Generate feedback template for rejection reason: 'ambiguous stem'"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `content-reviewer` |
| System Prompt Focus | Fairness, validity, clarity assessment |
| Tools | `get_review_queue`, `analyze_fairness`, `check_validity`, `approve_item`, `reject_item`, `flag_issue` |
| Knowledge Namespaces | `certification-core`, `review-guidelines`, `fairness-criteria` |
| Access Level | Read all Items, approve/reject, cannot edit content |

---

## Operations Team: Proctor

> **Team:** Operations
> **Focus:** Expert-level exam delivery at Cisco LabLocations

Proctors work at **Static LabLocations** (permanent facilities with dedicated staff) or as **Guest Proctors** at **Mobile LabLocations** (temporary sites, typically 1-2 weeks). Only ~10 of the 150+ global LabLocations are active at any time. Mobile sites cannot run concurrently due to POD resource capacity limits.

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Session Preparation** | Assign POD and Form to scheduled Session |
| **History Lookup** | Check candidate history to avoid repeat assignments |
| **Morning Briefing** | Deliver localized orientation per LabLocation rules |
| **Identity Verification** | Confirm candidate identity before exam |
| **Seat Assignment** | Map candidate to hardened workstation |
| **Session Monitoring** | Oversee Exam delivery throughout the day |
| **Incident Handling** | Address technical/hardware issues (may require remote intervention) |
| **Candidate Support** | Answer allowable questions, address legitimate concerns |
| **Policy Enforcement** | Ensure Exam rules followed |

### Session Preparation Workflow

> **Note:** POD/Form assignment is partly automated. System suggests assignments based on availability and candidate history (all-time lookback for given certification). Proctors may override before exam starts. POD initialization may take **up to 2 hours** depending on Track and hardware devices involved.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SESSION PREPARATION (Day Before)                       │
│                                                                              │
│  Proctor                       Mozart                    pod-manager         │
│     │                            │                           │               │
│     │  1. View tomorrow's        │                           │               │
│     │     scheduled sessions     │                           │               │
│     │───────────────────────────►│                           │               │
│     │                            │                           │               │
│     │     Auto-assigned POD/Form │                           │               │
│     │     suggestions displayed  │                           │               │
│     │◄───────────────────────────│                           │               │
│     │                            │                           │               │
│     │  2. Review candidate       │                           │               │
│     │     attempt history        │                           │               │
│     │     (all-time lookback)    │                           │               │
│     │───────────────────────────►│                           │               │
│     │                            │                           │               │
│     │  3. Override POD/Form if   │                           │               │
│     │     needed (optional)      │                           │               │
│     │───────────────────────────►│                           │               │
│     │                            │                           │               │
│     │  4. Trigger POD init       │                           │               │
│     │     (up to 2h lead time)   │                           │               │
│     │───────────────────────────────────────────────────────►│               │
│     │                            │                           │               │
│     │  5. Verify POD health      │                           │               │
│     │───────────────────────────────────────────────────────►│               │
│     │                            │                           │               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Day-of-Exam Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DAY-OF-EXAM WORKFLOW                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  MORNING BRIEFING                                                    │    │
│  │                                                                      │    │
│  │  • Localized rules (vary by LabLocation)                            │    │
│  │  • Facility orientation                                              │    │
│  │  • Policy reminders                                                  │    │
│  │  • Q&A session                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  IDENTITY VERIFICATION                                               │    │
│  │                                                                      │    │
│  │  • Check government ID                                               │    │
│  │  • Match to registration                                             │    │
│  │  • Photograph (if required)                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  SEAT ASSIGNMENT                                                     │    │
│  │                                                                      │    │
│  │  • Assign candidate to hardened workstation                          │    │
│  │  • Verify workstation connected via private network DMZ              │    │
│  │  • Confirm POD accessibility                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  MONITORING & SUPPORT                                                │    │
│  │                                                                      │    │
│  │  • Monitor candidate progress                                        │    │
│  │  • Address technical/hardware issues                                 │    │
│  │  • Answer permitted questions                                        │    │
│  │  • Request remote intervention if needed                             │    │
│  │  • Log all incidents                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Workflow (Without AI)

1. Manually check multiple systems for session setup
2. When Candidate raises hand, check context in multiple systems
3. Determine if question is allowable
4. Provide assistance or escalate
5. Log incidents in separate system

### Desired AI-Augmented Workflow

1. **Session preparation assistance**
   - "Show me tomorrow's candidates with their attempt history"
   - "Which PODs are available and healthy for CCIE Enterprise?"
   - "Suggest POD/Form assignments avoiding repeats"

2. **Instant context lookup**
   - "What Item is Candidate 123 currently on?"
   - "Show me this Candidate's attempt history"
   - "Explain what this Item is testing"

3. **Allowability check**
   - "Can I clarify the term 'subnet' for the Candidate?"
   - "Is this a content question or policy question?"

4. **Incident assistance**
   - "Candidate reports device not responding—check Pod status"
   - "Request remote intervention for workstation 5"
   - "Draft incident report for: 'Candidate requested bathroom break at 45min mark'"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `proctor-support` |
| System Prompt Focus | Quick context, allowability judgment, incident handling, session prep |
| Tools | `get_candidate_context`, `get_item_info`, `check_pod_status`, `lookup_attempt_history`, `create_incident_report`, `get_available_pods`, `suggest_assignments`, `request_remote_intervention` |
| Knowledge Namespaces | `certification-core`, `proctor-guidelines`, `active-sessions`, `lab-location-rules` |
| Access Level | Read-only on all session data, create incidents, assign POD/Form |

---

## Candidate

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Demonstrate KSA** | Complete Exam Items successfully |
| **Follow Rules** | Adhere to Exam policies |
| **Seek Appropriate Help** | Ask allowable questions |

### Current Workflow (Without AI)

1. Start Exam session
2. Answer Items sequentially
3. If confused, raise hand for Proctor
4. For practical: interact with Pod devices
5. Submit and await results

### Desired AI-Augmented Workflow

1. **Concept clarification** (without answer disclosure)
   - "Explain what subnetting means in general"
   - "What's the difference between TCP and UDP?"
   - (AI must NOT reveal Item-specific answers)

2. **Navigation assistance**
   - "How much time remaining?"
   - "Which sections have I completed?"

3. **Post-exam**
   - "Explain why I got this question wrong" (after results released)
   - "What resources can help me improve on Topic X?"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `candidate-tutor` |
| System Prompt Focus | Concept explanation WITHOUT answer disclosure, Socratic method |
| Tools | `explain_concept`, `get_resources`, `check_time_remaining`, `get_completed_sections` |
| Knowledge Namespaces | `certification-concepts` (NO access to answers/grading) |
| Access Level | Own session only, no Item answers |

**Critical Constraint:** Candidate-facing agent must NEVER have access to:

- Correct answers
- Grading rules
- Item-specific hints

---

## Analyst

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Performance Analysis** | Analyze score distributions |
| **Trend Detection** | Identify patterns over time |
| **Item Analysis** | Evaluate Item difficulty/discrimination |
| **Reporting** | Generate reports for stakeholders |

### Current Workflow (Without AI)

1. Export data from analytics platform
2. Load into analysis tools (Excel, R, Python)
3. Run standard psychometric analyses
4. Generate visualizations
5. Write report narrative

### Desired AI-Augmented Workflow

1. **Natural language queries**
   - "What's the pass rate trend for Q4?"
   - "Which Items have discrimination index below 0.2?"
   - "Compare Cohort A vs Cohort B on Topic X"

2. **Report generation**
   - "Generate executive summary for November exams"
   - "Create Item analysis report for Form 2024-A"

3. **Anomaly detection**
   - "Flag any unusual score patterns this week"
   - "Are there any Items with suspected key leakage?"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `analytics-assistant` |
| System Prompt Focus | Psychometric analysis, trend interpretation, report generation |
| Tools | `query_scores`, `analyze_items`, `compare_cohorts`, `generate_report`, `detect_anomalies` |
| Knowledge Namespaces | `exam-analytics`, `psychometric-methods` |
| Access Level | Read-only aggregated data, no PII |

---

## Tester

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Form Testing** | Verify Forms render correctly |
| **UX Validation** | Ensure Candidate experience is smooth |
| **Edge Case Testing** | Test unusual scenarios |
| **Bug Reporting** | Document issues found |

### Current Workflow (Without AI)

1. Receive test Form assignment
2. Walk through Exam as mock Candidate
3. Note any issues (display, timing, grading)
4. Submit bug reports
5. Re-test after fixes

### Desired AI-Augmented Workflow

1. **Test case generation**
   - "What edge cases should I test for this FormSpec?"
   - "Generate test data for parameter combinations"

2. **Issue documentation**
   - "Draft bug report for: 'Timer displays wrong when paused'"
   - "Compare current behavior to expected from FormSpec"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `test-assistant` |
| System Prompt Focus | Test case generation, bug documentation |
| Tools | `get_form_spec`, `generate_test_cases`, `create_bug_report`, `lookup_expected_behavior` |
| Knowledge Namespaces | `certification-core`, `testing-guidelines` |
| Access Level | Read FormSpecs, create test reports |

---

## Analysts Team: Security Analyst

> **Team:** Analysts
> **Focus:** Exam integrity and security investigations

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Breach Investigation** | Research suspected content exposure |
| **Candidate Misconduct** | Investigate misbehaving candidates |
| **Content Protection** | Coordinate item retirement/rotation |
| **Trend Analysis** | Identify patterns suggesting compromise |
| **Incident Resolution** | Close security incidents with evidence |

### Current Workflow (Without AI)

1. Receive alert about potential breach (exposed content, suspicious scores)
2. Manually gather evidence from multiple systems
3. Cross-reference candidate behavior with known patterns
4. Determine scope of compromise
5. Recommend remediation (retire items, ban candidates, etc.)
6. Document findings

### Desired AI-Augmented Workflow

1. **Evidence gathering**
   - "Show all candidates who saw Item 12345 in the past 6 months"
   - "Compare score patterns for this Item before and after suspected leak"
   - "Find forum posts mentioning this exam topic"

2. **Pattern recognition**
   - "Are there unusual completion time patterns for this Form?"
   - "Identify candidates with suspiciously similar answer sequences"
   - "Flag Items with sudden P-value changes"

3. **Remediation support**
   - "Generate list of Items to retire based on exposure analysis"
   - "Draft candidate ban recommendation with evidence summary"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `security-analyst` |
| System Prompt Focus | Breach investigation, pattern detection, evidence documentation |
| Tools | `query_item_exposure`, `analyze_score_patterns`, `compare_answer_sequences`, `search_external_sources`, `generate_remediation_report`, `flag_candidates` |
| Knowledge Namespaces | `exam-analytics`, `security-patterns`, `breach-procedures` |
| Access Level | Full read on exam data, flag candidates, recommend actions |

---

## Systems Team: Operator

> **Team:** Systems
> **Focus:** Day-to-day operations of shared services

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Monitoring** | Watch dashboards for system health |
| **Troubleshooting** | Diagnose and resolve issues |
| **Escalation** | Route complex issues to SysAdmins or vendors |
| **User Support** | Help internal users with system questions |
| **Incident Response** | First responder for production issues |

### Current Workflow (Without AI)

1. Monitor multiple dashboards (Mosaic, LDS, POD status)
2. When alert fires, check logs across systems
3. Attempt standard remediation steps
4. Escalate to SysAdmin if beyond scope
5. Log incident details

### Desired AI-Augmented Workflow

1. **Unified monitoring**
   - "Show health status across all systems"
   - "What errors have occurred in the last hour?"
   - "Which PODs are showing degraded performance?"

2. **Guided troubleshooting**
   - "LDS is slow—check common causes"
   - "Candidate can't connect to POD—run diagnostics"
   - "Compare current metrics to yesterday's baseline"

3. **Incident documentation**
   - "Create incident ticket for LDS timeout issue"
   - "Summarize today's issues for handoff"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `ops-assistant` |
| System Prompt Focus | System monitoring, troubleshooting, incident triage |
| Tools | `get_system_health`, `query_logs`, `check_pod_status`, `run_diagnostics`, `create_incident`, `get_runbook` |
| Knowledge Namespaces | `system-operations`, `runbooks`, `infrastructure` |
| Access Level | Read all system data, create incidents, execute safe diagnostics |

---

## Systems Team: System Administrator

> **Team:** Systems
> **Focus:** Infrastructure management and code deployment

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Code Deployment** | Deploy builds to SystemEnvironments |
| **Environment Config** | Configure DEV/STG/PROD settings |
| **Change Management** | Execute change requests from vendors |
| **Capacity Planning** | Monitor and scale infrastructure |
| **Vendor Coordination** | Receive builds, validate, deploy |

### Current Workflow (Without AI)

1. Receive code build artifact from vendor
2. Validate build in DEV environment
3. Promote to STG for testing
4. Schedule production deployment
5. Execute deployment across regions (Americas, EMEA, APJC)
6. Monitor for issues post-deployment

### Desired AI-Augmented Workflow

1. **Deployment assistance**
   - "What's the status of build 2.3.1 across all environments?"
   - "Show differences between STG and PROD configs"
   - "Generate deployment checklist for this release"

2. **Impact analysis**
   - "What exams are running during the proposed maintenance window?"
   - "Which regions have the most active sessions right now?"

3. **Change tracking**
   - "Summarize all changes deployed this week"
   - "What vendor change requests are pending?"

### AI Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent Name | `sysadmin-assistant` |
| System Prompt Focus | Deployment, configuration, change management |
| Tools | `get_deployment_status`, `compare_configs`, `get_active_sessions`, `create_deployment_plan`, `query_change_requests`, `check_maintenance_impact` |
| Knowledge Namespaces | `infrastructure`, `deployment-procedures`, `system-configs` |
| Access Level | Read all infrastructure data, execute approved deployments |

---

## Summary: Agent-to-Actor Mapping

| Team | Actor | Agent Name | Primary Capability |
|------|-------|------------|-------------------|
| APS / Expert | CertificationOwner (EPM) | `blueprint-assistant` | Blueprint CRUD, coverage analysis |
| APS / Expert | ExamAuthor (SME) | `content-author` | Item generation, template creation |
| APS / Expert | ItemReviewer | `content-reviewer` | Fairness/validity analysis, approval |
| Operations | Proctor | `proctor-support` | Session prep, context, incident handling |
| — | Candidate | `candidate-tutor` | Concept help (no answers) |
| Analysts | Analyst | `analytics-assistant` | Query, report, anomaly detection |
| Analysts | Security Analyst | `security-analyst` | Breach investigation, pattern detection |
| — | Tester | `test-assistant` | Test case generation, bug docs |
| Systems | Operator | `ops-assistant` | Monitoring, troubleshooting, triage |
| Systems | System Administrator | `sysadmin-assistant` | Deployment, config, change management |

---

_Last updated: December 25, 2025_
