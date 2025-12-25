# Certification Program - Ubiquitous Language

> **Purpose:** Establish shared terminology across all actors, services, and documentation.

---

## Program Structure

### Certification Program Hierarchy

| Term | Definition | Notes |
|------|------------|-------|
| **Certification Program** | The organizational umbrella for all certifications | e.g., "Cisco Certifications" |
| **Certification Track** | A technology-focused progression path | e.g., "Enterprise", "Security", "DevNet" |
| **Certification Level** | Proficiency tier within a track | Associate, Professional, Expert |
| **Certification Type** | Role a certification plays within a level | Core, Concentration, Specialist |
| **Certification** | A specific credential that attests competency | Issued upon passing required exam(s) |
| **Prerequisite** | Required certification before attempting another | Forms progression ladders |

### Certification Levels

| Level | Code | Description | Bloom's Focus |
|-------|------|-------------|---------------|
| **Associate** | CCA | Entry-level, foundational knowledge | Remember (20-30%), Understand (30-40%), Apply (25-35%) |
| **Professional** | CCP | Mid-level, practical implementation | Apply (30-40%), Analyze (20-30%), Evaluate (5-15%) |
| **Expert** | CCE | Senior-level, design and optimization | Analyze (25-35%), Evaluate (25-35%), Create (10-20%) |

### Certification Types

| Type | Definition | Example |
|------|------------|---------|
| **Core** | Required foundational exam for a certification | ENCOR for CCNP Enterprise |
| **Concentration** | Specialized depth exam, choose 1+ | ENARSI, SD-WAN, Wireless |
| **Specialist** | Standalone narrow-focus certification | DevNet Specialist, IoT Specialist |

### Level Invariants

| Term | Definition | Notes |
|------|------------|-------|
| **Level Invariant** | Enforceable rule that defines what a level means | e.g., "Associate prohibits 'design' verb" |
| **Bloom's Distribution** | Required percentage range per cognitive level | Enforced during blueprint validation |
| **Prohibited Verb** | Action verb not allowed at a certification level | e.g., "design" prohibited at Associate |
| **Encouraged Verb** | Preferred action verb for a certification level | e.g., "identify", "configure" for Associate |
| **Knowledge Profile** | Breadth/depth/integration characteristics | Associates: broad/shallow, Experts: focused/deep |

---

## Job Analysis (Upstream)

### Job Role Analysis (JRA)

| Term | Definition | Notes |
|------|------------|-------|
| **Job Role Analysis (JRA)** | Process of defining job roles in an industry | Answers: "What roles exist?" |
| **Job Role** | A defined position with responsibilities | e.g., "Enterprise Network Engineer" |
| **Alternative Title** | Synonymous job titles in the market | e.g., "Network Infrastructure Engineer" |
| **Experience Profile** | Typical years of experience for a role | "3-7 years" |
| **Skill Category** | High-level grouping of related competencies | e.g., "Routing & Switching", "Network Security" |
| **Industry Sector** | Market segment where role exists | e.g., "Information Technology", "Healthcare IT" |

### Job Task Analysis (JTA)

| Term | Definition | Notes |
|------|------------|-------|
| **Job Task Analysis (JTA)** | Process of identifying tasks for a job role | Answers: "What does this role do?" |
| **Job Task** | A discrete unit of work performed in a role | e.g., "Configure OSPF in multi-area networks" |
| **Task Frequency** | How often a task is performed | Daily, Weekly, Monthly, Quarterly, As-needed |
| **Task Criticality** | Impact of task failure on business | Critical, High, Medium, Low |
| **Task Difficulty** | Cognitive/skill level required | Basic, Moderate, Advanced, Expert |
| **Task Trigger** | Events that cause a task to be performed | e.g., "New site deployment", "Troubleshooting" |
| **Task Outcome** | Observable result of successful task completion | e.g., "OSPF neighbors established" |
| **SME Consensus Score** | Agreement level among SMEs on task validity | e.g., 0.92 = 92% agreed |

### JTA Data Sources

| Term | Definition | Notes |
|------|------------|-------|
| **Job Posting Analysis** | Mining job listings for task/skill signals | LinkedIn, Indeed, company career pages |
| **SME Interview** | Structured conversation with practitioners | Primary qualitative source |
| **Practitioner Survey** | Quantitative data from role incumbents | Frequency, criticality ratings |
| **Industry Report** | Third-party analysis (Gartner, IDC) | Technology trends, skill forecasts |
| **Exam Performance Data** | Historical candidate results | Reveals actual vs expected difficulty |

### Traceability Chain

| Term | Definition | Notes |
|------|------------|-------|
| **Traceability** | Linking items to their upstream justification | Item → KSA → Task → Role |
| **Validation Score** | Confidence that a KSA is job-relevant | Derived from JTA evidence |
| **Evidence Link** | Connection between KSA and supporting data | e.g., "450 practitioners rated 4.2/5" |

---

## Blueprint & Content

### ExamBlueprint Structure

| Term | Definition | Notes |
|------|------------|-------|
| **ExamBlueprint** | Hierarchical specification of what an Exam measures | Tree of Topics → Skills → KSA |
| **Topic** | Major content area within a Blueprint | e.g., "Network Security", "Routing Protocols" |
| **Skill** | Measurable capability within a Topic | e.g., "Configure BGP peering" |
| **Weight** | Percentage importance of Topic/Skill | Used for Form assembly |
| **Domain** | Grouping of related Topics | May span multiple Exams |
| **MQC Definition** | Description of Minimally Qualified Candidate | Threshold definition for passing |

### Knowledge, Skills, Abilities (KSA)

| Term | Definition | Notes |
|------|------------|-------|
| **KSA** | Knowledge, Skills, Abilities | The three dimensions of competency |
| **Knowledge** | What a Candidate knows (facts, concepts, procedures) | Measured via recall/recognition |
| **Skill** | What a Candidate can do (apply knowledge) | Measured via performance tasks |
| **Ability** | How a Candidate approaches problems (judgment, analysis) | Measured via complex scenarios |
| **KSA Statement** | Specific, measurable competency statement | e.g., "Configure BGP peering between two routers" |
| **KSA ID** | Unique identifier for a KSA Statement | e.g., "K-OSPF-001", "S-BGP-003" |
| **Bloom's Level** | Cognitive complexity of a KSA | Remember, Understand, Apply, Analyze, Evaluate, Create |
| **MQC** | Minimally Qualified Candidate | Threshold definition for passing |

### Bloom's Taxonomy

| Level | Definition | Example Verbs |
|-------|------------|---------------|
| **Remember** | Recall facts and basic concepts | Define, list, identify, name |
| **Understand** | Explain ideas or concepts | Describe, explain, summarize |
| **Apply** | Use information in new situations | Configure, implement, execute |
| **Analyze** | Draw connections among ideas | Troubleshoot, compare, differentiate |
| **Evaluate** | Justify a decision or course of action | Assess, recommend, prioritize |
| **Create** | Produce new or original work | Design, architect, develop |

### Content & Items

| Term | Definition | Notes |
|------|------------|-------|
| **Item** | A single test question or task | Atomic unit of assessment |
| **ItemTemplate** | Parameterized Item with variable placeholders | Used to generate unique Items |
| **SkillTemplate** | Complete specification for generating Items from a Skill | Includes stem templates, difficulty levels, distractor strategies |
| **Stem** | The question or prompt presented to Candidate | May contain template variables |
| **Distractor** | Incorrect answer option in MCQ | Generated via distractor strategies |
| **Key** | The correct answer in an MCQ | Also called "correct option" |
| **Fragment** | Reusable content piece | Stem, option, resource, exhibit |
| **Resource** | Supporting material for an Item | Network diagram, email, log file |
| **Exhibit** | Visual/document presented with an Item | Topology, configuration snippet |
| **Form** | A complete Exam instance with selected Items | What a Candidate actually takes |
| **FormSpec** | Specification for generating Forms | Item slots, time limits, ordering rules |
| **FormSet** | Collection of equivalent Forms | Same blueprint, different Items |
| **Item Slot** | Placeholder in FormSpec for an Item | Defines constraints (skill, difficulty) |

### Content Lifecycle

| Term | Definition | Notes |
|------|------------|-------|
| **Draft** | Initial Item state, author working | Not visible to reviewers |
| **Submitted** | Awaiting review | CloudEvent: item.submitted.v1 |
| **In Review** | Reviewer actively evaluating | May have multiple cycles |
| **Approved** | Passed all review criteria | Ready for Form inclusion |
| **Published** | Active in production Forms | May receive candidate responses |
| **Retired** | Removed from active use | Historical data preserved |
| **Flagged** | Marked for attention | Statistical anomaly or complaint |

---

## Practical Exams

### Module Types

| Term | Definition | Notes |
|------|------------|-------|
| **Design Module** | Progressive storyline with sequential items | Proactive conversation pattern |
| **Deploy Module** | All items/resources at once, candidate-driven | Reactive workspace pattern |
| **Lablet** | Short (10-15 min) practical exercise | Multiple Lablets per Exam |
| **Long-Form Practical** | Extended (5-8h) practical exercise | Single continuous session (CCIE lab) |

### Environment

| Term | Definition | Notes |
|------|------------|-------|
| **Pod** | Virtual environment allocated to a Candidate | Contains devices, networks, configurations |
| **Device** | Virtual or physical resource in a Pod | VMs, containers, network devices |
| **Device State** | Current configuration/status of a Device | File system, services, network config |
| **Initial State** | Pod configuration before Candidate starts | May be parameterized per instance |
| **Expected State** | Correct Device State after Task completion | Compared against for grading |
| **Console** | Terminal interface to a Device | Serial console, SSH, web terminal |
| **Pod Health** | Operational status of Pod resources | Monitored during exam |

### Practical Exam Templating

| Term | Definition | Notes |
|------|------------|-------|
| **PracticalExamTemplate** | Parameterized template for generating unique exams | Enables compositional uniqueness |
| **Variable Dimension** | An aspect that can vary across instances | e.g., IP scheme, company name, protocol |
| **Variable Constraint** | Rule governing variable combinations | e.g., "If OSPF, then use area 0" |
| **Exam Instance** | A concrete generated exam from template | Unique variable values resolved |
| **Narrative Variable** | Variable affecting storyline only | Company name, character names |
| **Technical Variable** | Variable affecting device configuration | IP addresses, VLAN numbers |

### Tasks & Grading

| Term | Definition | Notes |
|------|------------|-------|
| **Task** | Specific action Candidate must perform | Mapped to KSA Statement |
| **Task Dependency** | Order requirement between Tasks | e.g., "Task 2 requires Task 1 complete" |
| **Checkpoint** | Candidate-initiated progress marker | May trigger intermediate grading |
| **Submission** | Candidate's signal that Task/Exam is complete | Triggers grading evaluation |
| **Grading Rule** | Specification for evaluating Task completion | Declarative or script-based |
| **Rubric** | Detailed scoring criteria with point values | Enables partial credit |
| **Dichotomous Scoring** | Pass/fail only, no partial credit | Current grading-system limitation |
| **Polytomous Scoring** | Multiple score levels, partial credit | Target state for enhanced grading |

---

## Exam Delivery

### Session Management

| Term | Definition | Notes |
|------|------------|-------|
| **Exam Session** | Scheduled time slot for Exam delivery | May include multiple Candidates |
| **Session Type** | Category of delivery (proctored, remote, etc.) | Determines policies |
| **Delivery Environment** | Technical infrastructure for session | On-site lab, remote proctoring |
| **Check-in** | Candidate identity verification | Required before exam access |
| **Break** | Authorized pause in exam timing | Tracked for audit |
| **Time Extension** | Authorized additional time | Accessibility accommodation |

### Attempt & Progress

| Term | Definition | Notes |
|------|------------|-------|
| **Attempt** | Single instance of Candidate taking an Exam | Tracked for history/analytics |
| **Retake** | Subsequent attempt after failure | Subject to waiting period |
| **Waiting Period** | Required time between attempts | Policy-defined |
| **Progress** | Candidate's completion percentage | Per-module tracking |
| **Idle Time** | Duration without candidate activity | May trigger proctor alert |
| **Pacing** | Candidate's time distribution across items | Analytics metric |

### Proctoring

| Term | Definition | Notes |
|------|------------|-------|
| **Proctor** | Person monitoring Exam delivery | May intervene on issues |
| **Proctor Dashboard** | Unified view of all session candidates | AI-augmented in future state |
| **Proctor Alert** | System-generated notification | Idle candidate, help request, technical issue |
| **Intervention** | Proctor action on candidate issue | Documented for audit trail |
| **Incident Report** | Formal documentation of session anomaly | Required for dispute resolution |
| **Help Request** | Candidate-initiated clarification need | May route to AI or Proctor |

### Candidate Support

| Term | Definition | Notes |
|------|------------|-------|
| **Clarification** | Explanation of task wording or interface | Permitted during exam |
| **Escalation** | Routing question to human proctor | When AI cannot resolve |
| **Permitted Question** | Clarification AI can answer directly | Navigation, terminology, interface |
| **Prohibited Question** | Request for solution hints | AI must decline |

---

## Scoring & Analytics

### Scoring

| Term | Definition | Notes |
|------|------------|-------|
| **Raw Score** | Sum of points earned | Before scaling |
| **Scaled Score** | Normalized score for comparability | Across forms/cohorts |
| **Cut Score** | Minimum score for passing | Derived from MQC definition |
| **Passing Status** | Pass or Did Not Pass | Based on cut score |
| **Score Report** | Detailed breakdown of Candidate performance | Per-Topic, per-Skill granularity |
| **Section Score** | Performance within a Blueprint section | e.g., "Troubleshooting: Below Passing" |

### Psychometrics

| Term | Definition | Notes |
|------|------------|-------|
| **P-Value** | Item difficulty (proportion correct) | 0.0 = hard, 1.0 = easy |
| **Point-Biserial** | Item discrimination (correlation with total) | Negative = problematic |
| **Distractor Analysis** | Evaluation of wrong answer selection | Identifies non-functioning distractors |
| **DIF** | Differential Item Functioning | Detects bias across groups |
| **Item Statistics** | Aggregate psychometric data for an Item | Updated after each cohort |
| **Cohort** | Group of Candidates taking same Exam form | For statistical analysis |

### Analytics Platform

| Term | Definition | Notes |
|------|------------|-------|
| **Analytics Lakehouse** | Unified data platform for exam analytics | Bronze/Silver/Gold layers |
| **Bronze Layer** | Raw data ingestion (events, logs, traces) | Unprocessed |
| **Silver Layer** | Curated data (attempts, responses, journeys) | Cleaned and joined |
| **Gold Layer** | Analytics-ready aggregates | KSA proficiency, item stats |
| **Candidate Journey** | Complete timeline of candidate experience | From registration to certification |
| **Anomaly Detection** | Automated flagging of unusual patterns | Statistical outliers, security concerns |

---

## Post-Exam Experience

### Feedback & Coaching

| Term | Definition | Notes |
|------|------------|-------|
| **Performance Summary** | Aggregated KSA performance (no item details) | Permitted to share with candidate |
| **Time Analysis** | How candidate distributed time | Rushed sections, pacing patterns |
| **Pattern Comparison** | Candidate vs successful candidates | Anonymized aggregate comparison |
| **Study Resources** | Recommended learning materials | Per-topic, per-KSA |
| **Retake Guidance** | Recommendations for next attempt | Timing, focus areas |
| **Feedback Coach** | AI agent for post-exam counseling | Builds confidence, provides actionable guidance |

### Retention

| Term | Definition | Notes |
|------|------------|-------|
| **Retention Rate** | Percentage of failed candidates who retake | Key business metric |
| **Feedback Period** | Time window for AI coaching access | Typically 30 days post-exam |
| **Content Disclosure** | Revealing specific exam content | PROHIBITED—security violation |
| **KSA-Based Feedback** | Guidance by skill category, not item | Permitted approach |

---

## Review & Quality

### Content Review

| Term | Definition | Notes |
|------|------------|-------|
| **Pre-Review Analysis** | AI evaluation before human review | Surfaces issues early |
| **Review Checklist** | Standardized criteria for evaluation | Technical accuracy, clarity, fairness |
| **Review Cycle** | Complete round of feedback and revision | Target: 1-2 cycles (vs 3-4 current) |
| **Review Assignment** | Matching reviewer to content | Based on expertise, availability |
| **Sensitivity Review** | Evaluation for bias, cultural issues | Required for all items |
| **Editorial Review** | Language, grammar, formatting check | Consistency across exam |
| **Technical Review** | Accuracy of content and solutions | SME validation |

### Quality Metrics

| Term | Definition | Notes |
|------|------------|-------|
| **First-Pass Approval Rate** | Items approved without revision | Quality indicator |
| **Review Turnaround** | Time from submission to decision | Target: 3-5 days |
| **Rejection Reason** | Categorized cause for non-approval | For trend analysis |
| **Author Quality Score** | Historical approval rate per author | Training signal |

---

## Organization Structure

### Functional Teams

| Team | Scope | Key Responsibilities |
|------|-------|---------------------|
| **APS (Associate/Professional/Specialist)** | Entry-to-mid-level certifications | Manage exam content for corresponding tracks; Core + Concentration exams |
| **CCIE/Expert** | Expert-level certifications (CCIE, CCDE) | Manage exam content for expert tracks; on-site lab delivery |
| **Operations** | Exam session delivery | Session prep, candidate check-in, proctoring, issue resolution |
| **Systems** | Infrastructure & platforms | Operate shared services, capture requirements, deploy code |
| **Analysts** | Security & integrity | Investigate breaches, handle compromised content, misbehaving candidates |

### APS Team

| Term | Definition | Notes |
|------|------------|-------|
| **APS** | Associate/Professional/Specialist team | EPMs managing non-expert certifications |
| **Core Exam** | Required foundational exam within a track | e.g., ENCOR for CCNP Enterprise |
| **Concentration Exam** | Optional specialized depth exam | Candidates choose 1+ to complete certification |
| **Track EPM** | EPM responsible for a certification track | May own multiple certifications within track |

### CCIE/Expert Team

| Term | Definition | Notes |
|------|------------|-------|
| **Expert Track** | CCIE or CCDE certification path | Requires on-site lab exam |
| **CCIE** | Cisco Certified Internetwork Expert | 2 modules; continuous daily delivery |
| **CCDE** | Cisco Certified Design Expert | 4 modules (3 Core + 1 Elective); quarterly delivery windows |
| **CCDE Core Module** | First three CCDE modules | Required for all CCDE candidates |
| **CCDE Elective** | Fourth CCDE module (Area of Expertise) | Candidate chooses based on specialization |
| **LabLocation** | Physical Cisco facility for expert exams | ~150+ globally, ~10 active at any time |
| **Static LabLocation** | Permanent facility with dedicated Proctors | Brick-and-mortar office in major cities |
| **Mobile LabLocation** | Temporary exam site with guest Proctors | Ephemeral; cannot run concurrently due to POD capacity |
| **Hardened Workstation** | Secure candidate terminal | Connected to POD via private network DMZ |
| **Private Network DMZ** | Isolated network segment | Connects workstations to POD infrastructure |
| **HostingSite** | On-premise datacenter hosting POD infrastructure | San Jose (SJ) or Brussels (BRU) |
| **LabLocation Assignment** | Mapping of LabLocation to HostingSite | Based on distance and network latency |

### Operations Team

| Term | Definition | Notes |
|------|------------|-------|
| **Session Preparation** | Pre-exam setup tasks | Assign POD, Form to scheduled Session |
| **POD/Form Auto-Assignment** | System-generated initial assignment | Partly automated; Proctor may override |
| **Candidate History Lookup** | Avoid repeat assignments | All-time lookback for given certification |
| **POD Initialization** | Provisioning of Pod environment | May take up to 2 hours depending on Track and hardware |
| **Morning Briefing** | Localized orientation | Rules vary by LabLocation |
| **Identity Verification** | Confirm candidate identity | Required before seat assignment |
| **Seat Assignment** | Map candidate to workstation | Physical seat in lab |
| **Issue Resolution** | Handle technical/hardware problems | May require remote intervention |
| **Guest Proctor** | Traveling Proctor at Mobile LabLocation | May be borrowed from Static site for 1-2 weeks |

### Systems Team

| Term | Definition | Notes |
|------|------------|-------|
| **Operator** | Day-to-day system operations | Monitor, troubleshoot, escalate |
| **System Administrator** | Infrastructure management | Deploy, configure, maintain |
| **Shared Services** | Centrally-operated platforms | Mosaic, LDS, POD Automation, Mozart |
| **Change Request** | Formal feature/fix specification | Prioritized and sent to vendors |
| **Software Vendor** | External development partner | Provides code; Systems team builds, tests, deploys |
| **Internal Development** | Services built by Systems team | Not all services are vendor-provided |
| **Code Build** | Deployable software artifact | Version-controlled release |
| **SystemEnvironment** | Deployment target | See Environment Types below |

### Environment Types

| Environment | Location | Description | Services |
|-------------|----------|-------------|----------|
| **SJ-LDS** | San Jose (on-premise) | PROD Lab Delivery System | LDS, POD Automation |
| **BRU-LDS** | Brussels (on-premise) | PROD Lab Delivery System | LDS, POD Automation |
| **STG** | San Jose (on-premise) | Staging for test/content development | LDS, POD Automation |
| **AWS Cloud** | AWS | Services not requiring POD access | Mosaic, Mozart/Automation platform |

### Analysts Team (Security)

| Term | Definition | Notes |
|------|------------|-------|
| **Security Analyst** | Investigates integrity issues | Content exposure, candidate misconduct |
| **Security Breach** | Compromise of exam integrity | Exposed content, cheating detected |
| **Compromised Content** | Exam material leaked externally | Requires item retirement or rotation |
| **Misbehaving Candidate** | Policy violation during exam | May result in score cancellation, ban |
| **Security Incident** | Formal record of breach investigation | Formally tracked through resolution |
| **Proctor Escalation** | Analyst involvement when candidate caught cheating | Usually no direct Proctor interaction otherwise |

### Infrastructure Concepts

| Term | Definition | Notes |
|------|------------|-------|
| **LabLocation** | Physical exam delivery site | ~150+ globally, ~10 active at any time |
| **HostingSite** | On-premise datacenter hosting POD infrastructure | San Jose (SJ) or Brussels (BRU) |
| **Region** | Geographic grouping | Americas, EMEA, APJC |
| **K8s Cluster** | Regional Kubernetes deployment | Runs LDS and related services |
| **SystemEnvironment** | Technical deployment target | SJ-LDS, BRU-LDS (PROD), STG, AWS |
| **On-Premise** | Infrastructure in Cisco data centers | HostingSites for POD-dependent workloads |
| **Cloud-Based** | Infrastructure in AWS | Services not needing POD access (Mosaic, Mozart) |

---

## Actors

| Term | Definition | Key Responsibilities |
|------|------------|---------------------|
| **Certification Council** | Governance body for program structure | Define levels, types, tracks |
| **CertificationOwner (EPM)** | Exam Program Manager, owns specific certification | Blueprint authoring, analytics review |
| **ExamAuthor** | Creates Item content | Draft Items, validate against KSA |
| **SME** | Subject Matter Expert | Reviews content for accuracy, participates in JTA |
| **ItemReviewer** | Reviews Items for fairness/validity | Approve or flag Items |
| **Tester** | Tests Exam delivery | Verify Forms work correctly |
| **Proctor** | Monitors Exam sessions | Answer Candidate questions, handle incidents |
| **Candidate** | Takes Exams | Demonstrate KSA |
| **Analyst** | Reviews performance data | Generate reports, identify trends |
| **Security Analyst** | Investigates integrity breaches | Content exposure, candidate misconduct |
| **Operator** | Day-to-day system operations | Monitor systems, troubleshoot issues |
| **System Administrator** | Infrastructure management | Deploy code, configure environments |
| **Hiring Manager** | External role for JTA input | Provides real-world job requirements |

---

## AI Agents & Assistants

### Agent Definitions

| Term | Definition | Notes |
|------|------------|-------|
| **AgentDefinition** | Configuration for an AI agent | System prompt, tools, model |
| **System Prompt** | Instructions defining agent behavior | Includes permitted/prohibited actions |
| **Tool** | Function an agent can invoke | e.g., get_blueprint, validate_ksa |
| **Guardrail** | Constraint on agent behavior | e.g., "Never reveal exam content" |
| **Escalation Path** | Route to human when agent cannot resolve | Defined per agent |

### Certification Program Agents

| Agent | Role | Primary Actor Served |
|-------|------|---------------------|
| **Blueprint Assistant** | Helps create/validate blueprints | CertificationOwner |
| **Content Assistant** | Assists item authoring | ExamAuthor |
| **Review Assistant** | Pre-screens items for issues | ItemReviewer |
| **JTA Facilitator** | Structures job analysis sessions | CertificationOwner, SME |
| **Program Design Assistant** | Helps define certification structure | Certification Council |
| **Proctor Assistant** | Monitors sessions, suggests interventions | Proctor |
| **Exam Support Assistant** | Answers permitted candidate questions | Candidate (during exam) |
| **Feedback Coach** | Post-exam counseling for failed candidates | Candidate (post-exam) |
| **Analytics Agent** | Natural language querying of exam data | Analyst |
| **Template Generator** | Creates parameterized practical exam templates | CertificationOwner |

### Conversation Patterns

| Term | Definition | Notes |
|------|------------|-------|
| **ConversationTemplate** | Proactive conversation flow | Mapped to FormSpec for Exams |
| **Proactive Conversation** | System-driven progressive dialogue | Design Module pattern |
| **Reactive Conversation** | User-driven Q&A | Exam support pattern |
| **UiWidget** | Interactive UI component | MCQ selector, code editor, topology viewer |
| **Context Expansion** | Injecting domain knowledge into prompts | Via knowledge-manager |

---

## Systems & Services

### Core Systems

| System | Description | Owner |
|--------|-------------|-------|
| **Mosaic** | Exam authoring platform (Blueprint, Items, Forms) | Content Team |
| **LDS** | Exam delivery system (Candidate UI) | Delivery Team |
| **pod-manager** | Virtual environment orchestration | Infrastructure Team |
| **session-manager** | Exam session scheduling and control | Delivery Team |
| **grading-system** | Device state evaluation and scoring | Grading Team |
| **output-collectors** | Device state capture (configs, logs) | Grading Team |
| **Mozart** | Scheduling portal for proctors | Operations Team |

### Mozart Platform Services

| Service | Description | Layer |
|---------|-------------|-------|
| **agent-host** | AI agent hosting and conversation management | Application |
| **tools-provider** | MCP tool gateway to upstream services | Integration |
| **knowledge-manager** | Domain knowledge storage and retrieval | Infrastructure |
| **blueprint-manager** | Blueprint lifecycle and validation | Application |
| **analytics-platform** | Unified analytics lakehouse | Data |

---

## Events & Integration

### CloudEvents

| Event | Description | Trigger |
|-------|-------------|---------|
| **blueprint.published.v1** | Blueprint ready for item authoring | EPM publishes blueprint |
| **item.submitted.v1** | Item ready for review | Author submits |
| **item.approved.v1** | Item passed review | Reviewer approves |
| **form.generated.v1** | Exam form assembled | FormSpec execution |
| **exam.launched.v1** | Candidate started exam | Session start |
| **response.submitted.v1** | Candidate answered item | Design Module |
| **checkpoint.submitted.v1** | Candidate marked progress | Deploy Module |
| **exam.completed.v1** | Candidate finished exam | Final submission |
| **grading.completed.v1** | Scoring finished | Grading system |
| **score.released.v1** | Results available to candidate | Score reporting |

---

## Accreditation & Compliance

| Term | Definition | Notes |
|------|------------|-------|
| **ANSI/ISO 17024** | Accreditation standard for certification bodies | Requires documented JTA |
| **Audit Trail** | Complete history of actions and decisions | Required for accreditation |
| **JTA Evidence** | Documentation supporting blueprint design | Task lists, SME consensus, surveys |
| **Audit** | Formal review by accreditation body | Periodic, requires evidence |
| **Cut Score Study** | Formal process to establish passing score | Required methodology |
| **Standard Setting** | Process to define performance standards | Links MQC to cut score |

---

## Relationships

```
Certification Program
└── Certification Track (1..n)
    └── Certification (1..n)
        ├── Certification Level
        ├── Certification Type
        ├── Prerequisites (0..n)
        └── Required Exams (1..n)

Job Role Analysis
└── Job Role (1..n)
    └── Job Task (1..n)
        └── KSA Requirement (1..n)
            └── Validation Evidence (1..n)

ExamBlueprint
├── Certification (1)
├── Level Invariants (1)
├── Topic (1..n)
│   ├── Skill (1..n)
│   │   ├── KSA Statement (1..n)
│   │   │   └── JTA Traceability (1)
│   │   └── SkillTemplate (0..n)
│   └── Weight (%)
└── MQC Definition

FormSpec
├── Item Slot (1..n)
│   ├── SkillTemplate reference
│   ├── Difficulty constraint
│   └── Time allocation
├── Ordering rules
└── Time limit

SkillTemplate
├── stem_templates[]
├── difficulty_levels{}
├── distractor_strategies[]
├── parameter_ranges{}
└── evaluation_method

PracticalExamTemplate
├── Design Module
│   └── Narrative Variables
├── Deploy Module
│   ├── Technical Variables
│   └── Device Templates
├── Variable Constraints
├── Grading Rules (parameterized)
└── Instance Generator

Exam Session
├── Candidates (1..n)
│   └── Attempt (1)
│       ├── Responses (1..n)
│       └── Device States (0..n)
├── Proctor (1)
├── POD Allocations (0..n)
└── Incidents (0..n)
```

---

## Abbreviations

| Abbrev | Expansion |
|--------|-----------|
| ANSI | American National Standards Institute |
| APJC | Asia Pacific, Japan, China |
| APS | Associate/Professional/Specialist (team) |
| CCA | Cisco Certified Associate (example level code) |
| CCDE | Cisco Certified Design Expert |
| CCP | Cisco Certified Professional (example level code) |
| CCE | Cisco Certified Expert (example level code) |
| CDC | Change Data Capture |
| DIF | Differential Item Functioning |
| DMZ | Demilitarized Zone (network security) |
| EMEA | Europe, Middle East, Africa |
| EPM | Exam Program Manager |
| ETL | Extract, Transform, Load |
| ISO | International Organization for Standardization |
| JRA | Job Role Analysis |
| JTA | Job Task Analysis |
| KSA | Knowledge, Skills, Abilities |
| LDS | Lab Delivery System (exam-delivery-system) |
| BRU | Brussels (HostingSite) |
| SJ | San Jose (HostingSite) |
| K8s | Kubernetes |
| LLM | Large Language Model |
| MCP | Model Context Protocol |
| MCQ | Multiple Choice Question |
| MQC | Minimally Qualified Candidate |
| OTEL | OpenTelemetry |
| POD | Practical On-Demand (virtual lab environment) |
| SME | Subject Matter Expert |
| STG | Staging (environment) |

---

_Last updated: December 25, 2025_
