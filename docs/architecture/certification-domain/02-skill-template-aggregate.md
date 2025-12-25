# SkillTemplate Aggregate Design

> **Bounded Context:** Exam Content (blueprint-manager service)
> **Persistence:** MongoDB via MotorRepository (state-based with CloudEvent publishing)
> **Status:** Design In Progress
> **Last Updated:** December 2025

## Overview

The `SkillTemplate` aggregate represents reusable item development guidance that can be linked to Skills across multiple blueprints and tracks. It encapsulates stem patterns, distractor strategies, and difficulty calibration to ensure consistent item quality.

## Design Rationale

### Why Separate from Blueprint?

| Concern | Blueprint-embedded | Separate Aggregate (chosen) |
|---------|-------------------|----------------------------|
| **Cross-blueprint reuse** | ❌ Copy/paste duplication | ✅ Single source, many links |
| **Cross-track sharing** | ❌ Siloed per track | ✅ Shared templates (e.g., troubleshooting) |
| **Independent versioning** | ❌ Coupled to blueprint version | ✅ Template evolves independently |
| **Specialization** | ❌ Mixed concerns | ✅ Clean separation |
| **Item writer guidance** | ❌ Scattered | ✅ Centralized expertise |

### Relationship Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SKILL TEMPLATE LINKING MODEL                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    SkillTemplate Pool                                    ││
│  │                                                                         ││
│  │   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ││
│  │   │ Routing Protocol  │  │ Security Analysis │  │ Python Scripting  │  ││
│  │   │ Troubleshooting   │  │ Template          │  │ Template          │  ││
│  │   ├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ││
│  │   │ Tracks: ENT, SP   │  │ Tracks: SEC, ENT  │  │ Tracks: DEV, ALL  │  ││
│  │   │ Levels: ALL       │  │ Levels: PROF, EXP │  │ Levels: ALL       │  ││
│  │   │ Version: 2.3      │  │ Version: 1.1      │  │ Version: 3.0      │  ││
│  │   └────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘  ││
│  │            │                      │                      │             ││
│  └────────────┼──────────────────────┼──────────────────────┼─────────────┘│
│               │                      │                      │              │
│       ┌───────┴───────┐      ┌───────┴───────┐      ┌───────┴───────┐     │
│       ▼               ▼      ▼               ▼      ▼               ▼     │
│  ┌─────────┐   ┌─────────┐  ┌─────────┐   ┌─────────┐  ┌─────────┐       │
│  │ ENCOR   │   │ SPCOR   │  │ SCOR    │   │ ENCOR   │  │ DevCOR  │       │
│  │Skill 2.3│   │Skill 1.4│  │Skill 3.1│   │Skill 4.2│  │Skill 2.1│       │
│  └─────────┘   └─────────┘  └─────────┘   └─────────┘  └─────────┘       │
│                                                                           │
│  LINK STRUCTURE:                                                          │
│  • Each link captures: (skill_id, template_id, template_version)          │
│  • Blueprint stores links; Template knows nothing about blueprints        │
│  • Versioned links prevent breaking changes from affecting existing items │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Domain Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SkillTemplate Aggregate                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      SkillTemplateState                                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │  Identity                                                              │ │
│  │  ├─ id: str (UUID)                                                    │ │
│  │  ├─ name: str (e.g., "OSPF Troubleshooting")                          │ │
│  │  ├─ slug: str (e.g., "ospf-troubleshooting")                          │ │
│  │  └─ version: str (semantic version, e.g., "2.1.0")                    │ │
│  │                                                                        │ │
│  │  Classification                                                        │ │
│  │  ├─ category: str (e.g., "troubleshooting", "configuration")          │ │
│  │  ├─ applicable_tracks: list[str] (empty = all tracks)                 │ │
│  │  ├─ applicable_levels: list[str] (empty = all levels)                 │ │
│  │  └─ tags: list[str] (e.g., ["routing", "igp", "network"])             │ │
│  │                                                                        │ │
│  │  Stem Patterns                                                         │ │
│  │  └─ stem_patterns: dict[str, StemPattern]                             │ │
│  │      ├─ id: str                                                       │ │
│  │      ├─ pattern_type: str (recall, scenario, troubleshoot, etc.)     │ │
│  │      ├─ template: str (with {{placeholders}})                        │ │
│  │      ├─ bloom_level: int (1-6)                                        │ │
│  │      ├─ example: str                                                  │ │
│  │      └─ guidelines: str                                               │ │
│  │                                                                        │ │
│  │  Difficulty Calibration                                                │ │
│  │  └─ difficulty_levels: dict[str, DifficultyLevel]                     │ │
│  │      ├─ id: str                                                       │ │
│  │      ├─ name: str (e.g., "Easy", "Medium", "Hard")                   │ │
│  │      ├─ complexity_indicators: list[str]                              │ │
│  │      ├─ time_expectation: str (e.g., "60-90 seconds")                │ │
│  │      └─ example_scenarios: list[str]                                  │ │
│  │                                                                        │ │
│  │  Distractor Strategies                                                 │ │
│  │  └─ distractor_types: dict[str, DistractorType]                       │ │
│  │      ├─ id: str                                                       │ │
│  │      ├─ name: str (e.g., "Common Misconception")                     │ │
│  │      ├─ description: str                                              │ │
│  │      ├─ examples: list[str]                                           │ │
│  │      └─ avoid_patterns: list[str]                                     │ │
│  │                                                                        │ │
│  │  Item Type Configuration                                               │ │
│  │  └─ supported_item_types: list[ItemTypeConfig]                        │ │
│  │      ├─ type: str (multiple-choice, drag-drop, simulation, etc.)     │ │
│  │      ├─ recommended: bool                                             │ │
│  │      └─ configuration_hints: dict                                     │ │
│  │                                                                        │ │
│  │  Lifecycle                                                             │ │
│  │  ├─ status: TemplateStatus (DRAFT|ACTIVE|DEPRECATED)                  │ │
│  │  └─ deprecation_reason: str | None                                    │ │
│  │                                                                        │ │
│  │  Audit                                                                 │ │
│  │  ├─ created_by: str                                                   │ │
│  │  ├─ created_at: datetime                                              │ │
│  │  ├─ updated_at: datetime                                              │ │
│  │  └─ state_version: int                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Methods (Commands)                                                          │
│  ├─ create_template()                                                        │
│  ├─ update_metadata()                                                        │
│  ├─ add_stem_pattern() / update_stem_pattern() / remove_stem_pattern()      │
│  ├─ add_difficulty_level() / update_difficulty_level()                      │
│  ├─ add_distractor_type() / update_distractor_type()                        │
│  ├─ set_item_type_config()                                                  │
│  ├─ activate()                                                               │
│  ├─ deprecate()                                                              │
│  └─ create_new_version()                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Value Objects

### TemplateStatus

```python
from enum import Enum

class TemplateStatus(str, Enum):
    """Lifecycle status of a skill template."""
    DRAFT = "draft"        # Being authored, not yet usable
    ACTIVE = "active"      # Available for linking
    DEPRECATED = "deprecated"  # Superseded, existing links remain valid
```

### StemPattern

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class StemPattern:
    """A reusable pattern for writing item stems."""

    id: str
    """Unique ID within this template."""

    pattern_type: str
    """Type: 'recall', 'scenario', 'troubleshoot', 'compare', 'design', etc."""

    name: str
    """Human-readable name (e.g., 'Troubleshooting Scenario')."""

    template: str
    """
    Stem template with placeholders.
    Example: "A network engineer is troubleshooting {{issue}} on {{device_type}}.
              The engineer observes {{symptom}}. What is the most likely cause?"
    """

    placeholders: list[dict]
    """
    Placeholder definitions: [
        {"name": "issue", "description": "The problem to solve", "examples": ["OSPF adjacency", "BGP peering"]},
        {"name": "device_type", "description": "Router/Switch type", "examples": ["Cisco ISR", "Nexus switch"]}
    ]
    """

    bloom_level: int
    """Intended Bloom's level for items using this pattern."""

    example: str
    """A complete example using this pattern."""

    guidelines: str
    """Best practices and tips for using this pattern."""

    order: int = 0
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "name": self.name,
            "template": self.template,
            "placeholders": self.placeholders,
            "bloom_level": self.bloom_level,
            "example": self.example,
            "guidelines": self.guidelines,
            "order": self.order,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StemPattern":
        return cls(
            id=data["id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            template=data["template"],
            placeholders=data.get("placeholders", []),
            bloom_level=data.get("bloom_level", 1),
            example=data.get("example", ""),
            guidelines=data.get("guidelines", ""),
            order=data.get("order", 0),
            is_active=data.get("is_active", True),
        )
```

### DifficultyLevel

```python
@dataclass
class DifficultyLevel:
    """Calibration guidance for a difficulty tier."""

    id: str
    name: str
    """Display name (e.g., 'Easy', 'Medium', 'Hard', 'Expert')."""

    description: str
    """What distinguishes this difficulty level."""

    complexity_indicators: list[str]
    """
    Factors that increase complexity:
    - "Multi-step reasoning required"
    - "Deep configuration knowledge"
    - "Cross-protocol integration"
    """

    time_expectation: str
    """Expected time to answer (e.g., "60-90 seconds")."""

    cognitive_load: str
    """Description of mental effort required."""

    example_scenarios: list[str]
    """Examples of scenarios at this difficulty."""

    item_count_guidance: str
    """How many items at this level to target."""

    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "complexity_indicators": self.complexity_indicators,
            "time_expectation": self.time_expectation,
            "cognitive_load": self.cognitive_load,
            "example_scenarios": self.example_scenarios,
            "item_count_guidance": self.item_count_guidance,
            "order": self.order,
        }
```

### DistractorType

```python
@dataclass
class DistractorType:
    """Strategy for creating plausible wrong answers."""

    id: str
    name: str
    """Type name (e.g., 'Common Misconception', 'Partial Solution')."""

    description: str
    """How this distractor type works."""

    rationale: str
    """Why this type of distractor is effective."""

    examples: list[str]
    """Concrete examples of this distractor type."""

    avoid_patterns: list[str]
    """
    Patterns to avoid:
    - "Obviously wrong answers"
    - "Trick wording"
    - "Answers that are never correct in any context"
    """

    applicability: str
    """When to use this distractor type."""

    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rationale": self.rationale,
            "examples": self.examples,
            "avoid_patterns": self.avoid_patterns,
            "applicability": self.applicability,
            "order": self.order,
        }
```

### ItemTypeConfig

```python
@dataclass
class ItemTypeConfig:
    """Configuration for a supported item type."""

    type: str
    """Item type: 'multiple-choice', 'multiple-select', 'drag-drop',
       'simulation', 'fill-blank', 'testlet'."""

    recommended: bool
    """Is this the recommended type for this template?"""

    rationale: str
    """Why this item type is (or isn't) recommended."""

    configuration_hints: dict[str, Any]
    """
    Type-specific hints:
    - For multiple-choice: {"option_count": 4, "allow_none_of_above": false}
    - For drag-drop: {"max_categories": 3, "items_per_category": 4}
    - For simulation: {"topology_type": "hub-spoke", "devices": ["router", "switch"]}
    """

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "recommended": self.recommended,
            "rationale": self.rationale,
            "configuration_hints": self.configuration_hints,
        }
```

## Aggregate State

```python
from datetime import UTC, datetime
from neuroglia.data.abstractions import AggregateState


class SkillTemplateState(AggregateState[str]):
    """Encapsulates the persisted state for the SkillTemplate aggregate."""

    # Identity
    id: str
    name: str
    slug: str
    version: str
    description: str

    # Classification
    category: str
    applicable_tracks: list[str]  # Empty = all tracks
    applicable_levels: list[str]  # Empty = all levels
    tags: list[str]

    # Content (stored as dicts for serialization)
    stem_patterns: dict[str, dict]
    """pattern_id -> StemPattern.to_dict()"""

    difficulty_levels: dict[str, dict]
    """level_id -> DifficultyLevel.to_dict()"""

    distractor_types: dict[str, dict]
    """type_id -> DistractorType.to_dict()"""

    supported_item_types: list[dict]
    """List of ItemTypeConfig.to_dict()"""

    # Lifecycle
    status: str  # TemplateStatus.value
    deprecation_reason: str | None
    deprecated_at: datetime | None
    successor_template_id: str | None

    # Statistics (denormalized)
    stem_pattern_count: int
    difficulty_level_count: int
    distractor_type_count: int

    # Audit
    owner_user_id: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    state_version: int

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.name = ""
        self.slug = ""
        self.version = "1.0.0"
        self.description = ""
        self.category = ""
        self.applicable_tracks = []
        self.applicable_levels = []
        self.tags = []
        self.stem_patterns = {}
        self.difficulty_levels = {}
        self.distractor_types = {}
        self.supported_item_types = []
        self.status = TemplateStatus.DRAFT.value
        self.deprecation_reason = None
        self.deprecated_at = None
        self.successor_template_id = None
        self.stem_pattern_count = 0
        self.difficulty_level_count = 0
        self.distractor_type_count = 0
        self.owner_user_id = None
        self.created_by = None
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.state_version = 0

    # =========================================================================
    # Event Handlers - Apply events to state (using @dispatch)
    # =========================================================================

    @dispatch(SkillTemplateCreatedDomainEvent)
    def on(self, event: SkillTemplateCreatedDomainEvent) -> None:
        self.id = event.aggregate_id
        self.name = event.name
        self.slug = event.slug
        self.version = event.version
        self.category = event.category
        self.description = event.description
        self.applicable_tracks = event.applicable_tracks
        self.applicable_levels = event.applicable_levels
        self.tags = event.tags
        self.created_by = event.created_by
        self.owner_user_id = event.created_by
        self.created_at = event.created_at
        self.updated_at = event.created_at

    @dispatch(StemPatternAddedDomainEvent)
    def on(self, event: StemPatternAddedDomainEvent) -> None:
        self.stem_patterns[event.pattern_id] = {
            "id": event.pattern_id,
            "pattern_type": event.pattern_type,
            "name": event.name,
            "template": event.template,
            "placeholders": event.placeholders,
            "bloom_level": event.bloom_level,
            "example": event.example,
            "guidelines": event.guidelines,
            "order": len(self.stem_patterns),
            "is_active": True,
        }
        self.stem_pattern_count = len([p for p in self.stem_patterns.values() if p.get("is_active")])
        self.updated_at = event.added_at

    @dispatch(SkillTemplateActivatedDomainEvent)
    def on(self, event: SkillTemplateActivatedDomainEvent) -> None:
        self.status = TemplateStatus.ACTIVE.value
        self.updated_at = event.activated_at

    @dispatch(SkillTemplateDeprecatedDomainEvent)
    def on(self, event: SkillTemplateDeprecatedDomainEvent) -> None:
        self.status = TemplateStatus.DEPRECATED.value
        self.deprecation_reason = event.reason
        self.successor_template_id = event.successor_template_id
        self.deprecated_at = event.deprecated_at
        self.updated_at = event.deprecated_at
```

## Domain Events

```python
from dataclasses import dataclass
from datetime import datetime
from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


# === Template Lifecycle Events ===

@cloudevent("skill-template.created.v1")
@dataclass
class SkillTemplateCreatedDomainEvent(DomainEvent):
    aggregate_id: str
    name: str
    slug: str
    version: str
    category: str
    description: str
    applicable_tracks: list[str]
    applicable_levels: list[str]
    tags: list[str]
    created_by: str
    created_at: datetime


@cloudevent("skill-template.metadata.updated.v1")
@dataclass
class SkillTemplateMetadataUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    name: str | None
    description: str | None
    category: str | None
    applicable_tracks: list[str] | None
    applicable_levels: list[str] | None
    tags: list[str] | None
    updated_by: str
    updated_at: datetime


@cloudevent("skill-template.activated.v1")
@dataclass
class SkillTemplateActivatedDomainEvent(DomainEvent):
    aggregate_id: str
    activated_by: str
    activated_at: datetime


@cloudevent("skill-template.deprecated.v1")
@dataclass
class SkillTemplateDeprecatedDomainEvent(DomainEvent):
    aggregate_id: str
    reason: str
    successor_template_id: str | None
    deprecated_by: str
    deprecated_at: datetime


@cloudevent("skill-template.version.created.v1")
@dataclass
class SkillTemplateVersionCreatedDomainEvent(DomainEvent):
    """Raised when a new version is created from an existing template."""
    aggregate_id: str  # New template ID
    source_template_id: str
    source_version: str
    new_version: str
    created_by: str
    created_at: datetime


# === Stem Pattern Events ===

@cloudevent("skill-template.stem-pattern.added.v1")
@dataclass
class StemPatternAddedDomainEvent(DomainEvent):
    aggregate_id: str
    pattern_id: str
    pattern_type: str
    name: str
    template: str
    placeholders: list[dict]
    bloom_level: int
    example: str
    guidelines: str
    added_by: str
    added_at: datetime


@cloudevent("skill-template.stem-pattern.updated.v1")
@dataclass
class StemPatternUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    pattern_id: str
    pattern_type: str | None
    name: str | None
    template: str | None
    placeholders: list[dict] | None
    bloom_level: int | None
    example: str | None
    guidelines: str | None
    updated_by: str
    updated_at: datetime


@cloudevent("skill-template.stem-pattern.removed.v1")
@dataclass
class StemPatternRemovedDomainEvent(DomainEvent):
    aggregate_id: str
    pattern_id: str
    removed_by: str
    removed_at: datetime


# === Difficulty Level Events ===

@cloudevent("skill-template.difficulty-level.added.v1")
@dataclass
class DifficultyLevelAddedDomainEvent(DomainEvent):
    aggregate_id: str
    level_id: str
    name: str
    description: str
    complexity_indicators: list[str]
    time_expectation: str
    cognitive_load: str
    example_scenarios: list[str]
    added_by: str
    added_at: datetime


@cloudevent("skill-template.difficulty-level.updated.v1")
@dataclass
class DifficultyLevelUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    level_id: str
    name: str | None
    description: str | None
    complexity_indicators: list[str] | None
    time_expectation: str | None
    example_scenarios: list[str] | None
    updated_by: str
    updated_at: datetime


# === Distractor Type Events ===

@cloudevent("skill-template.distractor-type.added.v1")
@dataclass
class DistractorTypeAddedDomainEvent(DomainEvent):
    aggregate_id: str
    type_id: str
    name: str
    description: str
    rationale: str
    examples: list[str]
    avoid_patterns: list[str]
    applicability: str
    added_by: str
    added_at: datetime


@cloudevent("skill-template.distractor-type.updated.v1")
@dataclass
class DistractorTypeUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    type_id: str
    name: str | None
    description: str | None
    examples: list[str] | None
    avoid_patterns: list[str] | None
    updated_by: str
    updated_at: datetime


# === Item Type Config Events ===

@cloudevent("skill-template.item-types.configured.v1")
@dataclass
class ItemTypesConfiguredDomainEvent(DomainEvent):
    aggregate_id: str
    item_types: list[dict]  # List of ItemTypeConfig.to_dict()
    configured_by: str
    configured_at: datetime
```

## Aggregate Root Implementation

```python
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
import re

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot


class SkillTemplate(AggregateRoot[SkillTemplateState, str]):
    """Aggregate root for reusable skill templates.

    Provides item development guidance including stem patterns,
    difficulty calibration, and distractor strategies.

    Persistence: MongoDB via MotorRepository (state-based).
    Domain events are published as CloudEvents but NOT persisted.
    """

    def __init__(
        self,
        template_id: str,
        name: str,
        category: str,
        created_by: str,
        version: str = "1.0.0",
        description: str = "",
        applicable_tracks: list[str] | None = None,
        applicable_levels: list[str] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a new SkillTemplate."""
        super().__init__()
        now = datetime.now(UTC)

        # Generate slug from name
        slug = self._slugify(name)

        # CORRECT PATTERN: Apply event to state, then register for publishing
        self.state.on(
            self.register_event(
                SkillTemplateCreatedDomainEvent(
                    aggregate_id=template_id,
                    name=name,
                    slug=slug,
                    version=version,
                    category=category,
                    description=description,
                    applicable_tracks=applicable_tracks or [],
                    applicable_levels=applicable_levels or [],
                    tags=tags or [],
                    created_by=created_by,
                    created_at=now,
                )
            )
        )

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug

    # =========================================================================
    # Public Command Methods
    # =========================================================================

    def update_metadata(
        self,
        updated_by: str,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        applicable_tracks: list[str] | None = None,
        applicable_levels: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Update template metadata."""
        self._assert_editable()

        self.state.on(
            self.register_event(
                SkillTemplateMetadataUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name,
                    description=description,
                    category=category,
                    applicable_tracks=applicable_tracks,
                    applicable_levels=applicable_levels,
                    tags=tags,
                    updated_by=updated_by,
                    updated_at=datetime.now(UTC),
                )
            )
        )

    def add_stem_pattern(
        self,
        pattern_id: str,
        pattern_type: str,
        name: str,
        template: str,
        bloom_level: int,
        added_by: str,
        placeholders: list[dict] | None = None,
        example: str = "",
        guidelines: str = "",
    ) -> None:
        """Add a stem pattern to the template."""
        self._assert_editable()

        if pattern_id in self.state.stem_patterns:
            raise ValueError(f"Stem pattern {pattern_id} already exists")

        self.state.on(
            self.register_event(
                StemPatternAddedDomainEvent(
                    aggregate_id=self.id(),
                    pattern_id=pattern_id,
                    pattern_type=pattern_type,
                    name=name,
                    template=template,
                    placeholders=placeholders or [],
                    bloom_level=bloom_level,
                    example=example,
                    guidelines=guidelines,
                    added_by=added_by,
                    added_at=datetime.now(UTC),
                )
            )
        )

    def update_stem_pattern(
        self,
        pattern_id: str,
        updated_by: str,
        pattern_type: str | None = None,
        name: str | None = None,
        template: str | None = None,
        placeholders: list[dict] | None = None,
        bloom_level: int | None = None,
        example: str | None = None,
        guidelines: str | None = None,
    ) -> None:
        """Update an existing stem pattern."""
        self._assert_editable()
        self._assert_pattern_exists(pattern_id)

        self.state.on(
            self.register_event(
                StemPatternUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    pattern_id=pattern_id,
                    pattern_type=pattern_type,
                    name=name,
                    template=template,
                    placeholders=placeholders,
                    bloom_level=bloom_level,
                    example=example,
                    guidelines=guidelines,
                    updated_by=updated_by,
                    updated_at=datetime.now(UTC),
                )
            )
        )

    def remove_stem_pattern(self, pattern_id: str, removed_by: str) -> None:
        """Remove a stem pattern."""
        self._assert_editable()
        self._assert_pattern_exists(pattern_id)

        self.state.on(
            self.register_event(
                StemPatternRemovedDomainEvent(
                    aggregate_id=self.id(),
                    pattern_id=pattern_id,
                    removed_by=removed_by,
                    removed_at=datetime.now(UTC),
                )
            )
        )

    def add_difficulty_level(
        self,
        level_id: str,
        name: str,
        description: str,
        complexity_indicators: list[str],
        time_expectation: str,
        cognitive_load: str,
        example_scenarios: list[str],
        added_by: str,
    ) -> None:
        """Add a difficulty level calibration."""
        self._assert_editable()

        if level_id in self.state.difficulty_levels:
            raise ValueError(f"Difficulty level {level_id} already exists")

        self.state.on(
            self.register_event(
                DifficultyLevelAddedDomainEvent(
                    aggregate_id=self.id(),
                    level_id=level_id,
                    name=name,
                    description=description,
                    complexity_indicators=complexity_indicators,
                    time_expectation=time_expectation,
                    cognitive_load=cognitive_load,
                    example_scenarios=example_scenarios,
                    added_by=added_by,
                    added_at=datetime.now(UTC),
                )
            )
        )

    def add_distractor_type(
        self,
        type_id: str,
        name: str,
        description: str,
        rationale: str,
        examples: list[str],
        avoid_patterns: list[str],
        applicability: str,
        added_by: str,
    ) -> None:
        """Add a distractor type strategy."""
        self._assert_editable()

        if type_id in self.state.distractor_types:
            raise ValueError(f"Distractor type {type_id} already exists")

        self.state.on(
            self.register_event(
                DistractorTypeAddedDomainEvent(
                    aggregate_id=self.id(),
                    type_id=type_id,
                    name=name,
                    description=description,
                    rationale=rationale,
                    examples=examples,
                    avoid_patterns=avoid_patterns,
                    applicability=applicability,
                    added_by=added_by,
                    added_at=datetime.now(UTC),
                )
            )
        )

    def configure_item_types(
        self,
        item_types: list[dict],  # List of ItemTypeConfig.to_dict()
        configured_by: str,
    ) -> None:
        """Configure supported item types for this template."""
        self._assert_editable()

        self.state.on(
            self.register_event(
                ItemTypesConfiguredDomainEvent(
                    aggregate_id=self.id(),
                    item_types=item_types,
                    configured_by=configured_by,
                    configured_at=datetime.now(UTC),
                )
            )
        )

    def activate(self, activated_by: str) -> None:
        """Activate the template, making it available for linking."""
        if self.state.status != TemplateStatus.DRAFT.value:
            raise ValueError(f"Cannot activate from status {self.state.status}")

        # Validate template has minimum content
        if not self.state.stem_patterns:
            raise ValueError("Template must have at least one stem pattern to activate")

        self.state.on(
            self.register_event(
                SkillTemplateActivatedDomainEvent(
                    aggregate_id=self.id(),
                    activated_by=activated_by,
                    activated_at=datetime.now(UTC),
                )
            )
        )

    def deprecate(
        self,
        reason: str,
        deprecated_by: str,
        successor_template_id: str | None = None,
    ) -> None:
        """Deprecate the template. Existing links remain valid."""
        if self.state.status != TemplateStatus.ACTIVE.value:
            raise ValueError(f"Cannot deprecate from status {self.state.status}")

        self.state.on(
            self.register_event(
                SkillTemplateDeprecatedDomainEvent(
                    aggregate_id=self.id(),
                    reason=reason,
                    successor_template_id=successor_template_id,
                    deprecated_by=deprecated_by,
                    deprecated_at=datetime.now(UTC),
                )
            )
        )

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _assert_editable(self) -> None:
        """Assert the template is in an editable state."""
        if self.state.status == TemplateStatus.DEPRECATED.value:
            raise ValueError("Cannot edit deprecated template. Create a new version instead.")

    def _assert_pattern_exists(self, pattern_id: str) -> None:
        if pattern_id not in self.state.stem_patterns:
            raise ValueError(f"Stem pattern {pattern_id} not found")
        if not self.state.stem_patterns[pattern_id].get("is_active", True):
            raise ValueError(f"Stem pattern {pattern_id} has been removed")
```

## State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SKILL TEMPLATE STATE MACHINE                             │
│                                                                              │
│                          ┌──────────────┐                                    │
│                          │    DRAFT     │                                    │
│                          └──────┬───────┘                                    │
│                                 │                                            │
│                          activate()                                          │
│                          (requires ≥1 stem pattern)                          │
│                                 │                                            │
│                                 ▼                                            │
│                          ┌──────────────┐                                    │
│               ┌─────────►│    ACTIVE    │◄────────────────┐                  │
│               │          └──────┬───────┘                 │                  │
│               │                 │                         │                  │
│               │          deprecate()              update_metadata()          │
│               │                 │                 add_stem_pattern()         │
│               │                 │                 (editing allowed           │
│               │                 │                  while active)             │
│               │                 ▼                                            │
│               │          ┌──────────────┐                                    │
│               │          │  DEPRECATED  │                                    │
│               │          └──────┬───────┘                                    │
│               │                 │                                            │
│               │          create_new_version()                                │
│               │                 │ (creates new                               │
│               └─────────────────┘  template in                               │
│                                    DRAFT state)                              │
│                                                                              │
│  NOTES:                                                                      │
│  • ACTIVE templates can still be edited (add patterns, etc.)                │
│  • DEPRECATED templates cannot be edited or linked to new skills            │
│  • Existing links to deprecated templates remain valid                       │
│  • Creating a new version copies content to a new aggregate                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Example: OSPF Troubleshooting Template

```yaml
id: "template-ospf-troubleshoot-v1"
name: "OSPF Troubleshooting"
slug: "ospf-troubleshooting"
version: "2.1.0"
category: "troubleshooting"
description: |
  Comprehensive template for developing items that assess OSPF
  troubleshooting skills across various scenarios and complexity levels.

applicable_tracks:
  - "enterprise"
  - "service-provider"

applicable_levels:
  - "professional"
  - "expert"

tags:
  - "routing"
  - "igp"
  - "ospf"
  - "troubleshooting"

stem_patterns:
  - id: "sp-1"
    pattern_type: "scenario"
    name: "Symptom-Based Troubleshooting"
    template: |
      A network engineer is troubleshooting {{issue_type}} in an OSPF network.
      The network topology consists of {{topology_description}}.
      The engineer observes the following symptom: {{symptom}}.

      {{exhibit_reference}}

      What is the most likely cause of this issue?
    placeholders:
      - name: "issue_type"
        description: "The general category of problem"
        examples: ["OSPF adjacency issues", "route redistribution problems", "suboptimal path selection"]
      - name: "topology_description"
        description: "Brief network topology"
        examples: ["three routers in a hub-and-spoke design", "a multi-area OSPF network with areas 0, 1, and 2"]
      - name: "symptom"
        description: "Observable behavior"
        examples: ["routes are missing from the routing table", "the neighbor state is stuck in EXSTART"]
      - name: "exhibit_reference"
        description: "Reference to show output"
        examples: ["Refer to the exhibit showing the output of 'show ip ospf neighbor'"]
    bloom_level: 4  # Analyze
    example: |
      A network engineer is troubleshooting OSPF adjacency issues in an OSPF network.
      The network topology consists of two routers connected via an Ethernet link.
      The engineer observes the following symptom: the neighbor state is stuck in EXSTART.

      Refer to the exhibit showing the output of 'show ip ospf neighbor'.

      What is the most likely cause of this issue?
    guidelines: |
      - Ensure the symptom is specific and observable via standard show commands
      - Include relevant exhibit data that provides clues
      - The correct answer should be determinable from the provided information
      - Avoid ambiguous scenarios with multiple equally valid causes

difficulty_levels:
  - id: "easy"
    name: "Easy"
    description: "Single-area OSPF, common configuration errors"
    complexity_indicators:
      - "Single OSPF area"
      - "Point-to-point or broadcast network type"
      - "Common misconfigurations (MTU, hello/dead timers)"
    time_expectation: "60-90 seconds"
    cognitive_load: "Recall and apply standard troubleshooting steps"
    example_scenarios:
      - "Mismatched hello timers preventing adjacency"
      - "Missing network statement"

  - id: "medium"
    name: "Medium"
    description: "Multi-area OSPF, virtual links, summarization"
    complexity_indicators:
      - "Multiple OSPF areas"
      - "Inter-area routing issues"
      - "Summarization impact on routing"
    time_expectation: "90-120 seconds"
    cognitive_load: "Analyze multi-area interactions"
    example_scenarios:
      - "ABR not advertising inter-area routes"
      - "Virtual link configuration issues"

  - id: "hard"
    name: "Hard"
    description: "Complex multi-vendor, redistribution, filtering"
    complexity_indicators:
      - "Route redistribution between OSPF and other protocols"
      - "Route filtering with prefix-lists or route-maps"
      - "LSA type implications"
    time_expectation: "120-180 seconds"
    cognitive_load: "Synthesize multiple protocol interactions"
    example_scenarios:
      - "Redistribution loop prevention"
      - "LSA type 5 vs type 7 behavior in NSSA"

distractor_types:
  - id: "common-misconception"
    name: "Common Misconception"
    description: "Answer based on frequently misunderstood OSPF behavior"
    rationale: "Tests whether candidate truly understands vs. has surface knowledge"
    examples:
      - "Believing all OSPF routers in an area must have same RID"
      - "Thinking DR election happens per-area rather than per-segment"
    avoid_patterns:
      - "Made-up protocol behavior"
    applicability: "Use for conceptual questions about OSPF operation"

  - id: "partial-solution"
    name: "Partial Solution"
    description: "Answer that addresses only part of the problem"
    rationale: "Tests comprehensive understanding"
    examples:
      - "Fixing hello timer but not dead timer"
      - "Adding network statement but wrong area"
    avoid_patterns:
      - "Partial solutions that are obviously incomplete"
    applicability: "Use for troubleshooting scenarios with multiple steps"

supported_item_types:
  - type: "multiple-choice"
    recommended: true
    rationale: "Standard format, works well for diagnostic reasoning"
    configuration_hints:
      option_count: 4
      allow_none_of_above: false

  - type: "simulation"
    recommended: true
    rationale: "Best for hands-on troubleshooting validation"
    configuration_hints:
      topology_type: "multi-router"
      required_commands: ["show ip ospf neighbor", "show ip ospf interface", "show ip route ospf"]
```

## Repository Configuration

Following the **agent-host pattern** with MotorRepository (state-based):

```python
# In main.py - Data Access Layer configuration
from neuroglia.data.infrastructure.mongo import MotorRepository

MotorRepository.configure(
    builder,
    entity_type=SkillTemplate,
    key_type=str,
    database_name=app_settings.database_name,
    collection_name="skill_templates",
    domain_repository_type=SkillTemplateRepository,
    implementation_type=MotorSkillTemplateRepository,
)

# Domain events are published via CloudEventPublisher (configured separately)
# They are NOT persisted to EventStoreDB
CloudEventPublisher.configure(builder)
```

## Integration with Blueprint

When a Skill in a Blueprint links to a SkillTemplate:

```python
# In ExamBlueprint.link_skill_template()
def link_skill_template(
    self,
    skill_id: str,
    template_id: str,
    template_version: str,
    linked_by: str,
) -> None:
    """Link a SkillTemplate to a skill."""
    # Validation: template must be ACTIVE
    # (checked by command handler before calling this method)

    self.state.on(
        self.register_event(
            SkillTemplateLinkedDomainEvent(
                aggregate_id=self.id(),
                skill_id=skill_id,
                template_id=template_id,
                template_version=template_version,
                linked_by=linked_by,
                linked_at=datetime.now(UTC),
            )
        )
    )
```

The link is stored in the Blueprint, not the Template. This means:

- Templates don't know which blueprints use them
- Blueprints capture the exact version at link time
- Template deprecation doesn't break existing links
- New links to deprecated templates are blocked by business logic in the command handler

---

## UI Widget Specification for Exam Delivery

The `UIWidgetSpec` embedded in SkillTemplate defines how the item is rendered in agent-host Conversations during exam delivery. This bridges blueprint-manager (content definition) with agent-host (delivery experience).

### UIWidgetSpec Model

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class UIWidgetSpec:
    """Specification for rendering skill-based items in Conversations.

    This spec is consumed by agent-host's widget renderer registry
    to dynamically generate appropriate UI components.
    """

    widget_type: WidgetType
    """Primary widget type for response collection."""

    layout: WidgetLayout
    """Spatial arrangement and sizing configuration."""

    input_schema: dict[str, Any]
    """JSON Schema defining the structure of candidate responses."""

    resources: list[ResourceSpec] = field(default_factory=list)
    """Attached resources (diagrams, logs, configs) shown with the item."""

    validation_rules: list[ValidationRule] = field(default_factory=list)
    """Client-side validation before submission."""

    progressive_disclosure: ProgressiveDisclosure | None = None
    """Configuration for revealing content incrementally (Design module)."""

    scoring_hints: dict[str, Any] = field(default_factory=dict)
    """Hints for automated or assisted scoring."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "widget_type": self.widget_type.value,
            "layout": self.layout.to_dict(),
            "input_schema": self.input_schema,
            "resources": [r.to_dict() for r in self.resources],
            "validation_rules": [v.to_dict() for v in self.validation_rules],
            "progressive_disclosure": self.progressive_disclosure.to_dict() if self.progressive_disclosure else None,
            "scoring_hints": self.scoring_hints,
        }


class WidgetType(str, Enum):
    """Available widget types for exam delivery.
    
    This enum must support ALL existing agent-host widgets plus new ones.
    New widget types (TBD) will be added as UI requirements evolve.
    """

    # Selection-based
    MCQ = "mcq"                    # Multiple choice question
    MCQ_MULTI = "mcq_multi"        # Multiple select
    DRAG_DROP = "drag_drop"        # Drag and drop ordering/matching
    HOTSPOT = "hotspot"            # Click on image region

    # Input-based
    TEXT_INPUT = "text_input"      # Free-text response
    CODE_INPUT = "code_input"      # Code editor with syntax highlighting
    CONFIG_INPUT = "config_input"  # Network/system configuration
    DATETIME_RANGE = "datetime_range"  # Date/time range picker (TBD)

    # Analysis-based
    LOG_VIEWER = "log_viewer"      # Scrollable log output with highlighting
    TOPOLOGY_VIEWER = "topology"   # Interactive network diagram
    PACKET_CAPTURE = "packet_cap"  # Wireshark-like packet analysis
    DOCUMENT_VIEWER = "doc_viewer" # Document viewer with TOC navigation (TBD)
    TABLE_OF_CONTENT = "toc"       # Navigable table of contents (TBD)

    # Interactive
    INTERACTIVE_TERMINAL = "terminal"  # Live terminal session (TBD)

    # Composite
    SCENARIO = "scenario"          # Progressive storyline with multiple sub-items
    SIMULATION = "simulation"      # Full device simulation (POD integration)


@dataclass
class WidgetLayout:
    """Spatial configuration for widget rendering."""

    width: str = "full"       # "full", "half", "third", "auto"
    height: str = "auto"      # "auto", "fixed:400px", "fill"
    position: str = "inline"  # "inline", "modal", "split-left", "split-right"
    scroll: bool = True       # Enable scrolling for long content
    collapsible: bool = False # Allow minimizing

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "position": self.position,
            "scroll": self.scroll,
            "collapsible": self.collapsible,
        }


@dataclass
class ResourceSpec:
    """Attached resource displayed with the item."""

    id: str
    """Unique resource identifier."""

    resource_type: ResourceType
    """Type of resource (affects rendering)."""

    title: str
    """Display title (e.g., 'Email from Network Manager')."""

    content: str | None = None
    """Inline content (text, markdown, mermaid)."""

    url: str | None = None
    """URL for external resources (images, documents)."""

    parameters: dict[str, Any] = field(default_factory=dict)
    """Parameterization for unique instance generation."""

    display_order: int = 0
    """Order in which resources are presented."""

    reveal_condition: str | None = None
    """Condition for progressive disclosure (e.g., "after_item_1")."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "parameters": self.parameters,
            "display_order": self.display_order,
            "reveal_condition": self.reveal_condition,
        }


class ResourceType(str, Enum):
    """Types of resources attachable to items."""

    EMAIL = "email"           # Formatted email message
    DOCUMENT = "document"     # Text/markdown document
    LOG_OUTPUT = "log"        # Command output or log file
    CONFIG_SNIPPET = "config" # Device/system configuration
    DIAGRAM = "diagram"       # Network/architecture diagram (SVG, Mermaid)
    TABLE = "table"           # Data table
    IMAGE = "image"           # Static image
    VIDEO = "video"           # Video clip


@dataclass
class ValidationRule:
    """Client-side validation for response input."""

    field: str
    """Field in input_schema to validate."""

    rule_type: str
    """Type: 'required', 'min_length', 'max_length', 'pattern', 'custom'."""

    value: Any
    """Rule parameter (e.g., min length value, regex pattern)."""

    message: str
    """Error message to display on validation failure."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "rule_type": self.rule_type,
            "value": self.value,
            "message": self.message,
        }


@dataclass
class ProgressiveDisclosure:
    """Configuration for revealing content incrementally (Design module)."""

    mode: str
    """'sequential', 'gated', 'time_based'."""

    sequence: list[str]
    """Ordered list of resource IDs or item IDs to reveal."""

    gates: dict[str, str] = field(default_factory=dict)
    """Conditions for gated disclosure: {"resource_id": "condition_expression"}."""

    timing: dict[str, int] = field(default_factory=dict)
    """Time-based delays in seconds: {"resource_id": delay_seconds}."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "sequence": self.sequence,
            "gates": self.gates,
            "timing": self.timing,
        }
```

### Widget Type Examples

#### MCQ Widget (Multiple Choice)

```yaml
ui_widget_spec:
  widget_type: mcq
  layout:
    width: full
    position: inline
  input_schema:
    type: object
    properties:
      selected_option:
        type: string
        enum: ["A", "B", "C", "D"]
    required: ["selected_option"]
  validation_rules:
    - field: selected_option
      rule_type: required
      value: true
      message: "Please select an answer"
  resources:
    - id: show-output
      resource_type: log
      title: "Router Output"
      content: |
        R1# show ip ospf neighbor
        Neighbor ID     Pri   State           Dead Time   Address         Interface
        10.0.0.2        1     FULL/DR         00:00:32    192.168.1.2     GigabitEthernet0/0
```

#### Scenario Widget (Progressive Storyline)

```yaml
ui_widget_spec:
  widget_type: scenario
  layout:
    width: full
    position: inline
  progressive_disclosure:
    mode: sequential
    sequence:
      - intro_narrative
      - email_resource
      - question_1
      - result_narrative
      - log_resource
      - question_2
  resources:
    - id: intro_narrative
      resource_type: document
      title: "Scenario"
      content: |
        You are a network engineer at {{company_name}}. Your manager has
        escalated a critical issue affecting the {{department}} department.
      display_order: 1

    - id: email_resource
      resource_type: email
      title: "Email from {{manager_name}}"
      content: |
        **From:** {{manager_name}}, IT Director
        **Subject:** URGENT: Network connectivity issues

        We're experiencing intermittent connectivity problems on the
        {{affected_network}} segment. Users are reporting...
      display_order: 2
      parameters:
        company_name:
          type: string
          pool: ["Acme Corp", "TechStart Inc", "GlobalNet"]
        manager_name:
          type: string
          pool: ["Sarah Chen", "Marcus Johnson", "Priya Patel"]

    - id: log_resource
      resource_type: log
      title: "Router {{router_name}} Output"
      reveal_condition: "after:question_1"
      content: |
        {{router_name}}# show ip route
        ...
      display_order: 4
```

#### Topology Viewer Widget

```yaml
ui_widget_spec:
  widget_type: topology
  layout:
    width: half
    height: fixed:400px
    position: split-right
  resources:
    - id: network_diagram
      resource_type: diagram
      title: "Network Topology"
      content: |
        ```mermaid
        graph LR
            R1[Router R1<br>{{r1_ip}}] --- SW1[Switch SW1]
            R2[Router R2<br>{{r2_ip}}] --- SW1
            SW1 --- Server[Web Server<br>{{server_ip}}]
        ```
      parameters:
        r1_ip:
          type: ip
          template: "10.{{x}}.1.1"
        r2_ip:
          type: ip
          template: "10.{{x}}.2.1"
        server_ip:
          type: ip
          template: "10.{{x}}.10.100"
```

### Integration with agent-host Conversation

When exam delivery renders a SkillTemplate:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                 SKILLTEMPLATE → CONVERSATION WIDGET FLOW                             │
│                                                                                      │
│  1. FormSpec references SkillTemplate ID + version                                  │
│     ├── FormSpec.items[0].skill_template_id = "st-ospf-troubleshoot"               │
│     └── FormSpec.items[0].skill_template_version = "2.1.0"                         │
│                                                                                      │
│  2. Delivery Agent fetches SkillTemplate from blueprint-manager                     │
│     └── GET /api/skill-templates/st-ospf-troubleshoot?version=2.1.0                │
│                                                                                      │
│  3. Agent extracts UIWidgetSpec                                                     │
│     ├── widget_type: scenario                                                       │
│     ├── resources: [intro, email, question_1, log, question_2]                     │
│     └── progressive_disclosure: sequential                                          │
│                                                                                      │
│  4. Agent instantiates parameters (if any)                                          │
│     ├── company_name → "Acme Corp" (random from pool)                              │
│     ├── manager_name → "Sarah Chen" (random from pool)                             │
│     └── r1_ip → "10.42.1.1" (generated from template)                              │
│                                                                                      │
│  5. Agent sends Conversation messages with widget payloads                          │
│     ├── Message 1: { type: "narrative", content: intro_narrative }                 │
│     ├── Message 2: { type: "resource", widget: "email", data: email_resource }     │
│     ├── Message 3: { type: "widget", widget: "mcq", input_schema: {...} }          │
│     │                                                                               │
│  6. Candidate responds via widget                                                   │
│     └── { selected_option: "B" }                                                    │
│                                                                                      │
│  7. Agent advances progressive disclosure                                           │
│     ├── Message 4: { type: "narrative", content: result_narrative }                │
│     ├── Message 5: { type: "resource", widget: "log", data: log_resource }         │
│     └── Message 6: { type: "widget", widget: "mcq", input_schema: {...} }          │
│                                                                                      │
│  8. Responses collected in Conversation.items                                       │
│     └── items: [{ template_id, question_id, response, timestamp }, ...]            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Conversation Message Schema for Widgets

```python
@dataclass
class WidgetMessage:
    """Conversation message that renders a UI widget."""

    message_type: str = "widget"
    """Always 'widget' for these messages."""

    widget_spec: dict[str, Any]
    """The UIWidgetSpec.to_dict() payload."""

    item_id: str
    """Unique identifier for this item instance."""

    parameters_resolved: dict[str, Any]
    """Resolved parameter values for this instance."""

    scoring_key: str | None = None
    """Reference to correct answer (for immediate scoring if enabled)."""


# Example message in Conversation
{
    "role": "assistant",
    "content": "Based on the information provided, what is your first troubleshooting step?",
    "message_type": "widget",
    "widget_spec": {
        "widget_type": "mcq",
        "layout": {"width": "full", "position": "inline"},
        "input_schema": {
            "type": "object",
            "properties": {
                "selected_option": {"type": "string", "enum": ["A", "B", "C", "D"]}
            },
            "required": ["selected_option"]
        },
        "options": [
            {"id": "A", "text": "Check the interface status on R1"},
            {"id": "B", "text": "Verify OSPF neighbor adjacency"},
            {"id": "C", "text": "Restart the routing process"},
            {"id": "D", "text": "Review the access control lists"}
        ]
    },
    "item_id": "item-001-instance-abc123",
    "parameters_resolved": {
        "router_name": "R1",
        "interface": "GigabitEthernet0/0"
    }
}
```

### Widget Renderer Registry (agent-host Frontend)

The agent-host UI maintains a registry of widget renderers:

```typescript
// ui/src/widgets/registry.ts

interface WidgetRenderer {
  type: WidgetType;
  component: React.ComponentType<WidgetProps>;
  validateResponse: (response: any, schema: JSONSchema) => ValidationResult;
}

const widgetRegistry: Map<WidgetType, WidgetRenderer> = new Map([
  ['mcq', { component: MCQWidget, validateResponse: validateMCQ }],
  ['mcq_multi', { component: MCQMultiWidget, validateResponse: validateMCQMulti }],
  ['text_input', { component: TextInputWidget, validateResponse: validateText }],
  ['log_viewer', { component: LogViewerWidget, validateResponse: () => ({ valid: true }) }],
  ['topology', { component: TopologyWidget, validateResponse: () => ({ valid: true }) }],
  ['scenario', { component: ScenarioWidget, validateResponse: validateScenario }],
  // ... more widgets
]);

function renderWidget(message: WidgetMessage): React.ReactNode {
  const renderer = widgetRegistry.get(message.widget_spec.widget_type);
  if (!renderer) {
    return <UnsupportedWidget type={message.widget_spec.widget_type} />;
  }
  return <renderer.component spec={message.widget_spec} itemId={message.item_id} />;
}
```

---

_Last updated: December 2025_
