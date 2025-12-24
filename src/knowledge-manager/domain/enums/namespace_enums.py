"""Enums for Knowledge Namespace domain."""

from enum import Enum


class AccessLevel(str, Enum):
    """Access level for namespace visibility."""

    PRIVATE = "private"  # Only owner can access
    TENANT = "tenant"  # Tenant members can access
    PUBLIC = "public"  # Anyone can access (read-only for non-owners)


class RelationshipType(str, Enum):
    """Types of relationships between terms."""

    # Hierarchical
    CONTAINS = "contains"  # Parent contains child (ExamBlueprint contains ExamDomain)
    PARENT_OF = "parent_of"  # Direct parent relationship

    # Referential
    REFERENCES = "references"  # Entity references another
    IS_INSTANCE_OF = "is_instance_of"  # Concrete instance of abstract

    # Dependency
    DEPENDS_ON = "depends_on"  # Dependency relationship
    PREREQUISITE_FOR = "prerequisite_for"  # Learning prerequisite

    # Association
    RELATED_TO = "related_to"  # General association
    SYNONYM_OF = "synonym_of"  # Equivalent meaning
    ANTONYM_OF = "antonym_of"  # Opposite meaning

    # Semantic
    CORRELATES_WITH = "correlates_with"  # Statistical correlation
    PREDICTS_SUCCESS_IN = "predicts_success_in"  # Predictive relationship


class RuleType(str, Enum):
    """Types of business rules."""

    CONSTRAINT = "constraint"  # Must be satisfied (validation)
    INCENTIVE = "incentive"  # Encourages behavior (soft rule)
    PROCEDURE = "procedure"  # Defines a process
    DEFINITION = "definition"  # Definitional rule (always true by construction)
