# Blueprint-Manager Integration Patterns

> **Purpose:** Define integration contracts between blueprint-manager and external systems
> **Status:** Design Document
> **Last Updated:** December 25, 2025

## Overview

blueprint-manager integrates with three primary systems:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            INTEGRATION LANDSCAPE                                             │
│                                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                              INBOUND INTEGRATIONS                                        ││
│  │                                                                                          ││
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                        ││
│  │  │   agent-host    │   │  tools-provider │   │   Admin API     │                        ││
│  │  │   (via MCP)     │   │   (MCP server)  │   │   (REST)        │                        ││
│  │  │                 │   │                 │   │                 │                        ││
│  │  │ AI-assisted     │   │ Tool discovery  │   │ Direct API      │                        ││
│  │  │ authoring       │   │ and execution   │   │ access          │                        ││
│  │  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘                        ││
│  │           │                     │                     │                                  ││
│  └───────────┼─────────────────────┼─────────────────────┼──────────────────────────────────┘│
│              │                     │                     │                                   │
│              └──────────────────────────────────────────►│                                   │
│                                                          │                                   │
│                                              ┌───────────▼───────────┐                       │
│                                              │   blueprint-manager   │                       │
│                                              │                       │                       │
│                                              │   ExamBlueprint       │                       │
│                                              │   SkillTemplate       │                       │
│                                              │   FormSpec            │                       │
│                                              └───────────┬───────────┘                       │
│                                                          │                                   │
│  ┌───────────────────────────────────────────────────────┼──────────────────────────────────┐│
│  │                              OUTBOUND INTEGRATIONS    │                                  ││
│  │                                                       │                                  ││
│  │           ┌───────────────────────────────────────────┼────────────────┐                ││
│  │           │                                           │                │                ││
│  │           ▼                                           ▼                ▼                ││
│  │  ┌─────────────────┐                        ┌─────────────────┐ ┌─────────────────┐     ││
│  │  │     Mosaic      │                        │ knowledge-manager│ │   EventStoreDB  │     ││
│  │  │   (REST API)    │                        │  (CloudEvents)  │ │   (Audit Log)   │     ││
│  │  │                 │                        │                 │ │                 │     ││
│  │  │ Published       │                        │ Blueprint terms │ │ Domain events   │     ││
│  │  │ blueprints      │                        │ for AI context  │ │ for audit       │     ││
│  │  └─────────────────┘                        └─────────────────┘ └─────────────────┘     ││
│  │                                                                                          ││
│  └──────────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration 1: Mosaic (Downstream)

### Purpose

Mosaic is the **system of record** for exam content (Forms, Items). blueprint-manager publishes approved blueprints to Mosaic, which uses them as the reference for Form assembly.

### Contract

| Aspect | Details |
|--------|---------|
| **Direction** | blueprint-manager → Mosaic |
| **Protocol** | REST API (HTTPS) |
| **Authentication** | OAuth2 client credentials |
| **Trigger** | `ExamBlueprint.publish()` command |
| **Idempotency** | Based on `mosaic_blueprint_id` stored in aggregate |

### API Contract (Assumed)

```yaml
# Mosaic Blueprint API (assumed contract)

POST /api/v1/blueprints:
  description: Create a new blueprint in Mosaic
  request:
    content-type: application/json
    body:
      exam_code: string      # e.g., "350-401"
      name: string           # e.g., "ENCOR"
      version: string        # e.g., "2025.1"
      level: string          # "associate" | "professional" | "expert"
      track: string          # "enterprise" | "security" | etc.
      mqc_definition:
        description: string
        cut_score: number    # 0.0-1.0
      topics:
        - id: string
          name: string
          weight: number     # 0.0-1.0
          skills:
            - id: string
              name: string
              ksa_statements:
                - id: string
                  statement: string
                  cognitive_level: string
                  item_count_target: number
      constraints:
        min_items: number
        max_items: number
        time_limit_minutes: number
  response:
    201:
      body:
        id: string           # Mosaic-assigned ID
        created_at: datetime
        status: "active"

PUT /api/v1/blueprints/{mosaic_id}:
  description: Update an existing blueprint (new version)
  request:
    # Same as POST
  response:
    200:
      body:
        id: string
        updated_at: datetime
        version: string

GET /api/v1/blueprints/{mosaic_id}:
  description: Retrieve blueprint by Mosaic ID
  response:
    200:
      body:
        # Full blueprint structure
```

### Mosaic Client Implementation

```python
# api/services/mosaic_client.py

from dataclasses import dataclass
from typing import Any

import httpx

from application.settings import app_settings
from domain.entities import ExamBlueprint


@dataclass
class MosaicPublishResult:
    """Result of publishing a blueprint to Mosaic."""
    success: bool
    mosaic_blueprint_id: str | None
    error_message: str | None


class MosaicClient:
    """Client for Mosaic API integration."""

    def __init__(self):
        self.base_url = app_settings.mosaic_api_url
        self.client_id = app_settings.mosaic_client_id
        self.client_secret = app_settings.mosaic_client_secret
        self._token: str | None = None

    async def _get_token(self) -> str:
        """Obtain OAuth2 access token for Mosaic API."""
        if self._token:
            return self._token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{app_settings.mosaic_token_url}",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "blueprints:write",
                },
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token

    async def publish_blueprint(
        self,
        blueprint: ExamBlueprint
    ) -> MosaicPublishResult:
        """
        Publish or update a blueprint in Mosaic.

        If mosaic_blueprint_id exists, updates existing.
        Otherwise, creates new.
        """
        token = await self._get_token()
        payload = self._transform_to_mosaic_format(blueprint)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}

            try:
                if blueprint.state.mosaic_blueprint_id:
                    # Update existing
                    response = await client.put(
                        f"{self.base_url}/api/v1/blueprints/{blueprint.state.mosaic_blueprint_id}",
                        json=payload,
                        headers=headers,
                    )
                else:
                    # Create new
                    response = await client.post(
                        f"{self.base_url}/api/v1/blueprints",
                        json=payload,
                        headers=headers,
                    )

                response.raise_for_status()
                data = response.json()

                return MosaicPublishResult(
                    success=True,
                    mosaic_blueprint_id=data["id"],
                    error_message=None,
                )

            except httpx.HTTPStatusError as e:
                return MosaicPublishResult(
                    success=False,
                    mosaic_blueprint_id=None,
                    error_message=f"Mosaic API error: {e.response.status_code} - {e.response.text}",
                )

    def _transform_to_mosaic_format(self, blueprint: ExamBlueprint) -> dict[str, Any]:
        """Transform internal blueprint format to Mosaic API format."""
        state = blueprint.state

        return {
            "exam_code": state.id,  # Or separate exam_code field
            "name": state.name,
            "version": state.version,
            "level": state.level,
            "track": state.track_id,
            "mqc_definition": state.mqc_definition,
            "topics": [
                {
                    "id": topic["id"],
                    "name": topic["name"],
                    "weight": topic["weight"],
                    "skills": [
                        {
                            "id": skill["id"],
                            "name": skill["name"],
                            "ksa_statements": skill.get("ksa_statements", []),
                        }
                        for skill in topic.get("skills", {}).values()
                    ],
                }
                for topic in state.topics.values()
            ],
            "constraints": state.constraints,
        }
```

### Publish Command Handler

```python
# application/commands/blueprint/publish_blueprint_command.py

from dataclasses import dataclass
from datetime import UTC, datetime

from neuroglia.mediation import Command, CommandHandler

from api.services.mosaic_client import MosaicClient, MosaicPublishResult
from domain.entities import ExamBlueprint
from domain.events import ExamBlueprintPublishedDomainEvent
from domain.repositories import ExamBlueprintRepository
from integration.models import OperationResult


@dataclass
class PublishBlueprintCommand(Command[OperationResult]):
    """Command to publish an approved blueprint to Mosaic."""
    blueprint_id: str
    published_by: str


class PublishBlueprintCommandHandler(CommandHandler[PublishBlueprintCommand, OperationResult]):
    """Handler for publishing blueprints to Mosaic."""

    def __init__(
        self,
        repository: ExamBlueprintRepository,
        mosaic_client: MosaicClient,
    ):
        self.repository = repository
        self.mosaic_client = mosaic_client

    async def handle_async(self, command: PublishBlueprintCommand) -> OperationResult:
        # Load aggregate
        blueprint = await self.repository.get_async(command.blueprint_id)
        if not blueprint:
            return OperationResult.not_found(f"Blueprint {command.blueprint_id} not found")

        # Validate state
        if blueprint.state.status != "approved":
            return OperationResult.invalid(
                f"Blueprint must be in 'approved' status to publish. Current: {blueprint.state.status}"
            )

        # Publish to Mosaic
        result: MosaicPublishResult = await self.mosaic_client.publish_blueprint(blueprint)

        if not result.success:
            return OperationResult.error(f"Failed to publish to Mosaic: {result.error_message}")

        # Update aggregate with Mosaic ID and publish event
        blueprint.publish(
            published_by=command.published_by,
            mosaic_blueprint_id=result.mosaic_blueprint_id,
        )

        # Persist (events go to EventStoreDB, state to MongoDB)
        await self.repository.save_async(blueprint)

        return OperationResult.success({
            "blueprint_id": command.blueprint_id,
            "mosaic_blueprint_id": result.mosaic_blueprint_id,
            "published_at": datetime.now(UTC).isoformat(),
        })
```

---

## Integration 2: knowledge-manager (CloudEvents)

### Purpose

knowledge-manager maintains indexed knowledge for AI agent context expansion. blueprint-manager publishes events when blueprints are created, updated, or published, so agents can reference current blueprint content.

### Contract

| Aspect | Details |
|--------|---------|
| **Direction** | blueprint-manager → knowledge-manager |
| **Protocol** | CloudEvents over HTTP |
| **Broker** | Direct POST to knowledge-manager endpoint |
| **Namespace** | `certification-blueprints` |

### Event Types

| Event Type | Trigger | knowledge-manager Action |
|------------|---------|--------------------------|
| `io.certification.blueprint.created.v1` | New draft created | Index blueprint metadata |
| `io.certification.blueprint.updated.v1` | Draft modified | Update indexed content |
| `io.certification.blueprint.published.v1` | Published to Mosaic | Full term creation with relationships |
| `io.certification.blueprint.retired.v1` | Blueprint retired | Mark terms inactive |

### CloudEvent Schema

```json
{
  "specversion": "1.0",
  "type": "io.certification.blueprint.published.v1",
  "source": "blueprint-manager",
  "id": "evt-12345-abcde",
  "time": "2025-12-25T10:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "blueprint_id": "bp-encor-2025",
    "name": "ENCOR 350-401",
    "version": "2025.1",
    "level": "professional",
    "track_id": "enterprise",
    "type": "core",
    "published_by": "user-123",
    "mosaic_blueprint_id": "mosaic-bp-456",
    "topics": [
      {
        "id": "topic-1",
        "name": "Network Infrastructure",
        "weight": 0.25,
        "skills": [
          {
            "id": "skill-1",
            "name": "Configure and verify device management",
            "ksa_statements": [
              {
                "id": "ksa-1",
                "statement": "Configure and verify device access control",
                "cognitive_level": "apply"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### knowledge-manager Event Handler

```python
# knowledge-manager/application/event_handlers/blueprint_events.py

from datetime import UTC, datetime

from cloudevents.pydantic import CloudEvent
from neuroglia.eventing.cloud_events import cloudevent_handler
from neuroglia.mediation import Mediator

from application.commands.namespace import (
    AddTermCommand,
    AddRelationshipCommand,
    UpdateTermCommand,
)


@cloudevent_handler("io.certification.blueprint.published.v1")
async def handle_blueprint_published(
    event: CloudEvent,
    mediator: Mediator,
) -> None:
    """
    Sync published blueprint to certification-blueprints namespace.

    Creates terms for:
    - Blueprint itself
    - Each topic
    - Each skill
    - Key KSA statements (summary)

    Creates relationships for:
    - Blueprint :HAS_TOPIC Topic
    - Topic :HAS_SKILL Skill
    - Blueprint :TARGETS Level
    - Blueprint :BELONGS_TO Track
    """
    data = event.data
    namespace_id = "certification-blueprints"

    # Create blueprint term
    blueprint_term_id = f"blueprint-{data['blueprint_id']}"
    await mediator.execute_async(
        AddTermCommand(
            namespace_id=namespace_id,
            term_id=blueprint_term_id,
            term=f"{data['name']} v{data['version']}",
            definition=_build_blueprint_definition(data),
            aliases=[data['blueprint_id'], data.get('mosaic_blueprint_id')],
            context_hint=f"Use when discussing {data['name']} exam content",
        )
    )

    # Create topic terms and relationships
    for topic in data.get('topics', []):
        topic_term_id = f"topic-{data['blueprint_id']}-{topic['id']}"

        await mediator.execute_async(
            AddTermCommand(
                namespace_id=namespace_id,
                term_id=topic_term_id,
                term=topic['name'],
                definition=f"Topic in {data['name']} covering {topic['weight']*100:.0f}% of exam",
                context_hint=f"Topic in {data['name']} blueprint",
            )
        )

        await mediator.execute_async(
            AddRelationshipCommand(
                namespace_id=namespace_id,
                source_term_id=blueprint_term_id,
                target_term_id=topic_term_id,
                relationship_type="HAS_TOPIC",
                weight=topic['weight'],
            )
        )

        # Create skill terms
        for skill in topic.get('skills', []):
            skill_term_id = f"skill-{data['blueprint_id']}-{skill['id']}"

            ksa_summary = "\n".join(
                f"- {ksa['statement']} ({ksa['cognitive_level']})"
                for ksa in skill.get('ksa_statements', [])[:5]  # Limit to 5 for summary
            )

            await mediator.execute_async(
                AddTermCommand(
                    namespace_id=namespace_id,
                    term_id=skill_term_id,
                    term=skill['name'],
                    definition=f"Skill in {topic['name']}:\n\n{ksa_summary}",
                    context_hint=f"Skill measured in {data['name']}",
                )
            )

            await mediator.execute_async(
                AddRelationshipCommand(
                    namespace_id=namespace_id,
                    source_term_id=topic_term_id,
                    target_term_id=skill_term_id,
                    relationship_type="HAS_SKILL",
                )
            )

    # Link to certification-program namespace (levels, tracks)
    await mediator.execute_async(
        AddRelationshipCommand(
            namespace_id=namespace_id,
            source_term_id=blueprint_term_id,
            target_term_id=f"level-{data['level']}",  # In certification-program namespace
            relationship_type="TARGETS_LEVEL",
            description=f"Blueprint targets {data['level']} certification level",
        )
    )


def _build_blueprint_definition(data: dict) -> str:
    """Build rich definition for blueprint term."""
    topics = data.get('topics', [])
    topic_summary = "\n".join(
        f"- {t['name']} ({t['weight']*100:.0f}%)"
        for t in topics
    )

    return f"""
{data['name']} (v{data['version']})

**Level:** {data['level'].title()}
**Track:** {data['track_id'].title()}
**Type:** {data.get('type', 'core').title()}

**Topics:**
{topic_summary}

**Total Skills:** {sum(len(t.get('skills', [])) for t in topics)}
"""
```

---

## Integration 3: Runtime Validation (Query)

### Purpose

During blueprint authoring, agents can request validation against program rules stored in knowledge-manager's `certification-program` namespace.

### Contract

| Aspect | Details |
|--------|---------|
| **Direction** | blueprint-manager → knowledge-manager |
| **Protocol** | REST API |
| **Endpoint** | `POST /api/namespaces/certification-program/validate` |
| **When** | On-demand (not blocking); during submit() is common |

### Validation Request

```python
# api/services/knowledge_client.py

from dataclasses import dataclass
from typing import Any

import httpx

from application.settings import app_settings


@dataclass
class ValidationIssue:
    """A single validation issue."""
    rule_id: str
    rule_name: str
    severity: str  # "error", "warning", "info"
    message: str
    affected_elements: list[str]  # e.g., ["topic-1", "skill-2"]


@dataclass
class ValidationReport:
    """Complete validation report."""
    is_valid: bool  # No errors (warnings allowed)
    issues: list[ValidationIssue]
    evaluated_rules: int
    passed_rules: int


class KnowledgeClient:
    """Client for knowledge-manager API."""

    def __init__(self):
        self.base_url = app_settings.knowledge_manager_url

    async def validate_blueprint(
        self,
        blueprint_data: dict[str, Any],
    ) -> ValidationReport:
        """
        Validate blueprint against certification-program rules.

        Args:
            blueprint_data: Blueprint state as dict

        Returns:
            ValidationReport with any issues found
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/namespaces/certification-program/validate",
                json={
                    "entity_type": "blueprint",
                    "entity_data": blueprint_data,
                },
            )
            response.raise_for_status()
            data = response.json()

            return ValidationReport(
                is_valid=data["is_valid"],
                issues=[
                    ValidationIssue(**issue)
                    for issue in data.get("issues", [])
                ],
                evaluated_rules=data["evaluated_rules"],
                passed_rules=data["passed_rules"],
            )
```

### Validation Logic (in knowledge-manager)

```python
# knowledge-manager/application/queries/validate_entity_query.py

from dataclasses import dataclass
from typing import Any

from neuroglia.mediation import Query, QueryHandler

from domain.repositories import KnowledgeNamespaceRepository


@dataclass
class ValidateEntityQuery(Query[dict]):
    """Query to validate an entity against namespace rules."""
    namespace_id: str
    entity_type: str
    entity_data: dict[str, Any]


class ValidateEntityQueryHandler(QueryHandler[ValidateEntityQuery, dict]):
    """Handler for entity validation against rules."""

    def __init__(self, repository: KnowledgeNamespaceRepository):
        self.repository = repository

    async def handle_async(self, query: ValidateEntityQuery) -> dict:
        namespace = await self.repository.get_async(query.namespace_id)
        if not namespace:
            return {"error": f"Namespace {query.namespace_id} not found"}

        issues = []
        evaluated = 0
        passed = 0

        # Get active rules
        rules = [
            r for r in namespace.state.rules.values()
            if r.get("is_active", True)
        ]

        for rule in rules:
            evaluated += 1

            # Evaluate rule condition
            if not self._matches_condition(rule, query.entity_data):
                passed += 1
                continue  # Rule doesn't apply to this entity

            # Check rule
            violation = self._check_rule(rule, query.entity_data)
            if violation:
                issues.append(violation)
            else:
                passed += 1

        return {
            "is_valid": not any(i["severity"] == "error" for i in issues),
            "issues": issues,
            "evaluated_rules": evaluated,
            "passed_rules": passed,
        }

    def _matches_condition(self, rule: dict, entity: dict) -> bool:
        """Check if rule condition matches entity."""
        condition = rule.get("condition", "")

        # Simple condition parsing (real impl would use expression evaluator)
        if "blueprint.level ==" in condition:
            expected_level = condition.split("==")[1].strip().strip('"\'')
            return entity.get("level") == expected_level

        if condition == "always":
            return True

        return False

    def _check_rule(self, rule: dict, entity: dict) -> dict | None:
        """Check a specific rule against entity. Returns issue if violated."""
        rule_id = rule["id"]
        rule_text = rule.get("rule_text", "")

        # Example: Check Bloom distribution
        if "bloom" in rule_id.lower():
            violation = self._check_bloom_rule(rule, entity)
            if violation:
                return {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name"),
                    "severity": "error" if rule.get("priority", 1) == 1 else "warning",
                    "message": violation,
                    "affected_elements": [],
                }

        # Example: Check prohibited verbs
        if "verb" in rule_id.lower():
            violations = self._check_verb_rule(rule, entity)
            if violations:
                return {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name"),
                    "severity": "warning",
                    "message": f"Found prohibited verbs in KSAs: {', '.join(violations)}",
                    "affected_elements": violations,
                }

        return None

    def _check_bloom_rule(self, rule: dict, entity: dict) -> str | None:
        """Check Bloom's taxonomy distribution rule."""
        # Extract KSA cognitive levels from all skills
        cognitive_levels = []
        for topic in entity.get("topics", {}).values():
            for skill in topic.get("skills", {}).values():
                for ksa in skill.get("ksa_statements", []):
                    level = ksa.get("cognitive_level", "").lower()
                    cognitive_levels.append(level)

        if not cognitive_levels:
            return None

        total = len(cognitive_levels)
        lower_levels = ["remember", "understand", "apply"]
        higher_levels = ["analyze", "evaluate", "create"]

        lower_count = sum(1 for l in cognitive_levels if l in lower_levels)
        higher_count = sum(1 for l in cognitive_levels if l in higher_levels)

        level = entity.get("level", "")

        if level == "associate":
            if lower_count / total < 0.5:
                return f"Associate blueprint has {lower_count/total*100:.0f}% lower cognitive items, need ≥50%"

        if level == "expert":
            if higher_count / total < 0.4:
                return f"Expert blueprint has {higher_count/total*100:.0f}% higher cognitive items, need ≥40%"

        return None

    def _check_verb_rule(self, rule: dict, entity: dict) -> list[str]:
        """Check for prohibited verbs in KSA statements."""
        level = entity.get("level", "")

        prohibited = {
            "associate": ["design", "architect", "optimize", "evaluate"],
            "expert": [],  # Expert discourages but doesn't prohibit
        }

        if level not in prohibited:
            return []

        violations = []
        for topic in entity.get("topics", {}).values():
            for skill in topic.get("skills", {}).values():
                for ksa in skill.get("ksa_statements", []):
                    statement = ksa.get("statement", "").lower()
                    for verb in prohibited[level]:
                        if statement.startswith(verb) or f" {verb} " in statement:
                            violations.append(f"{verb} in '{ksa['statement'][:50]}...'")

        return violations
```

---

## Integration 4: tools-provider (MCP Tools)

### Purpose

tools-provider exposes blueprint-manager operations as MCP tools for AI agents in agent-host.

### Tool Registration

```yaml
# tools-provider configuration

upstream_sources:
  - id: 'blueprint-manager'
    name: 'Blueprint Manager'
    base_url: '${BLUEPRINT_MANAGER_URL}'
    openapi_url: '${BLUEPRINT_MANAGER_URL}/api/openapi.json'
    auth:
      type: 'oauth2_token_passthrough'  # Pass user's token
    tool_prefix: 'blueprint'
```

### Available Tools

| Tool Name | HTTP Method | Endpoint | Description |
|-----------|-------------|----------|-------------|
| `blueprint.create` | POST | `/api/blueprints` | Create new blueprint |
| `blueprint.get` | GET | `/api/blueprints/{id}` | Get blueprint by ID |
| `blueprint.list` | GET | `/api/blueprints` | List blueprints with filters |
| `blueprint.update` | PUT | `/api/blueprints/{id}` | Update blueprint metadata |
| `blueprint.add_topic` | POST | `/api/blueprints/{id}/topics` | Add topic |
| `blueprint.add_skill` | POST | `/api/blueprints/{id}/topics/{tid}/skills` | Add skill to topic |
| `blueprint.add_ksa` | POST | `/api/blueprints/{id}/skills/{sid}/ksa` | Add KSA statement |
| `blueprint.validate` | POST | `/api/blueprints/{id}/validate` | Validate against rules |
| `blueprint.submit` | POST | `/api/blueprints/{id}/submit` | Submit for review |
| `blueprint.approve` | POST | `/api/blueprints/{id}/approve` | Approve (reviewer) |
| `blueprint.reject` | POST | `/api/blueprints/{id}/reject` | Reject with feedback |
| `blueprint.publish` | POST | `/api/blueprints/{id}/publish` | Publish to Mosaic |
| `skill_template.create` | POST | `/api/skill-templates` | Create template |
| `skill_template.get` | GET | `/api/skill-templates/{id}` | Get template |
| `skill_template.list` | GET | `/api/skill-templates` | List templates |
| `skill_template.link` | POST | `/api/skill-templates/{id}/link` | Link to blueprint skill |
| `skill_template.preview` | POST | `/api/skill-templates/{id}/preview` | Generate preview item |

---

## Error Handling

### Error Codes

| Code | Meaning | Retry? |
|------|---------|--------|
| `BLUEPRINT_NOT_FOUND` | Blueprint ID doesn't exist | No |
| `INVALID_STATE_TRANSITION` | e.g., publish before approve | No |
| `VALIDATION_FAILED` | Failed program rules | No |
| `MOSAIC_UNAVAILABLE` | Cannot reach Mosaic API | Yes (with backoff) |
| `MOSAIC_REJECTED` | Mosaic rejected blueprint | No (check payload) |
| `KNOWLEDGE_UNAVAILABLE` | Cannot reach knowledge-manager | Yes |

### Retry Policy

```python
# For Mosaic integration
MOSAIC_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay_seconds": 1,
    "max_delay_seconds": 30,
    "exponential_base": 2,
    "retry_on": [
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        # 5xx errors
    ],
}
```

---

## Configuration

### Environment Variables

```bash
# blueprint-manager/.env

# Service Configuration
APP_PORT=8003
APP_NAME="Blueprint Manager"

# Database (Dual-Persistence)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=blueprint_manager
EVENTSTORE_URL=esdb://localhost:2113?tls=false

# Mosaic Integration
MOSAIC_API_URL=https://mosaic.example.com
MOSAIC_TOKEN_URL=https://auth.example.com/oauth/token
MOSAIC_CLIENT_ID=blueprint-manager
MOSAIC_CLIENT_SECRET=<secret>

# Knowledge Manager Integration
KNOWLEDGE_MANAGER_URL=http://localhost:8002

# CloudEvents
CLOUDEVENT_SINK=http://localhost:8002/api/events

# Auth
KEYCLOAK_URL=http://localhost:8041
KEYCLOAK_REALM=certifications
```

---

## Sequence Diagrams

### Blueprint Authoring Flow

```
EPM                    agent-host          tools-provider      blueprint-manager     knowledge-manager
 │                         │                    │                     │                     │
 │  "Create CCNP Core"     │                    │                     │                     │
 │────────────────────────►│                    │                     │                     │
 │                         │                    │                     │                     │
 │                         │  blueprint.create  │                     │                     │
 │                         │───────────────────►│                     │                     │
 │                         │                    │                     │                     │
 │                         │                    │  POST /blueprints   │                     │
 │                         │                    │────────────────────►│                     │
 │                         │                    │                     │                     │
 │                         │                    │                     │──── CloudEvent ────►│
 │                         │                    │                     │  blueprint.created  │
 │                         │                    │                     │                     │
 │                         │                    │  { id: "bp-123" }   │                     │
 │                         │                    │◄────────────────────│                     │
 │                         │                    │                     │                     │
 │                         │  Blueprint created │                     │                     │
 │                         │◄───────────────────│                     │                     │
 │                         │                    │                     │                     │
 │  "Add topic: Routing"   │                    │                     │                     │
 │────────────────────────►│                    │                     │                     │
 │                         │                    │                     │                     │
 │                         │ blueprint.add_topic│                     │                     │
 │                         │───────────────────►│                     │                     │
 │                         │                    │                     │                     │
 │                         │                    │POST /bp/123/topics  │                     │
 │                         │                    │────────────────────►│                     │
 │                         │                    │                     │                     │
 │                         │                    │                     │ (optional validate) │
 │                         │                    │                     │────────────────────►│
 │                         │                    │                     │                     │
 │                         │                    │                     │  { is_valid: true } │
 │                         │                    │                     │◄────────────────────│
 │                         │                    │                     │                     │
 │                         │                    │  Topic added        │                     │
 │                         │                    │◄────────────────────│                     │
 │                         │                    │                     │                     │
 │  Topic added            │                    │                     │                     │
 │◄────────────────────────│                    │                     │                     │
```

### Blueprint Publication Flow

```
EPM              blueprint-manager           Mosaic          knowledge-manager
 │                      │                      │                     │
 │  publish(bp-123)     │                      │                     │
 │─────────────────────►│                      │                     │
 │                      │                      │                     │
 │                      │  POST /blueprints    │                     │
 │                      │─────────────────────►│                     │
 │                      │                      │                     │
 │                      │  { mosaic_id: "m456"}│                     │
 │                      │◄─────────────────────│                     │
 │                      │                      │                     │
 │                      │  Store mosaic_id     │                     │
 │                      │  Emit published event│                     │
 │                      │                      │                     │
 │                      │────────── CloudEvent: blueprint.published ─────────────►│
 │                      │                      │                     │
 │                      │                      │                     │  Index terms
 │                      │                      │                     │  Create relations
 │                      │                      │                     │
 │  Published to m456   │                      │                     │
 │◄─────────────────────│                      │                     │
```
