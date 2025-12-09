"""ClaimMatcher value object.

Rules for matching JWT claims in access policies.
"""

import re
from dataclasses import dataclass
from typing import Any

from domain.enums import ClaimOperator


@dataclass(frozen=True)
class ClaimMatcher:
    """Rules for matching JWT claims in access policies.

    Uses JSONPath-like expressions to extract claim values and applies
    operators for matching. All ClaimMatchers in an AccessPolicy are
    evaluated with AND logic (all must match).

    This is an immutable value object used within AccessPolicy aggregate.
    """

    json_path: str  # Path expression (e.g., "realm_access.roles")
    operator: ClaimOperator  # How to compare
    value: str  # Expected value or pattern

    def matches(self, claims: dict[str, Any]) -> bool:
        """Check if the JWT claims match this matcher's criteria.

        Args:
            claims: The decoded JWT claims dictionary

        Returns:
            True if the claims satisfy this matcher, False otherwise
        """
        # Extract the claim value using the path
        claim_value = self._extract_claim(claims, self.json_path)

        # Handle EXISTS operator specially
        if self.operator == ClaimOperator.EXISTS:
            return claim_value is not None

        # If claim doesn't exist, most operators return False
        if claim_value is None:
            return False

        # Apply the operator
        return self._apply_operator(claim_value)

    def _extract_claim(self, claims: dict[str, Any], path: str) -> Any | None:
        """Extract a value from claims using a dot-notation path.

        Supports nested paths like "realm_access.roles" or "resource_access.client.roles".
        """
        parts = path.split(".")
        current = claims

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _apply_operator(self, claim_value: Any) -> bool:
        """Apply the operator to compare claim_value against self.value."""
        match self.operator:
            case ClaimOperator.EQUALS:
                return str(claim_value) == self.value

            case ClaimOperator.NOT_EQUALS:
                return str(claim_value) != self.value

            case ClaimOperator.CONTAINS:
                # For lists, check if value is in the list
                if isinstance(claim_value, list):
                    return self.value in claim_value
                # For strings, check substring
                return self.value in str(claim_value)

            case ClaimOperator.NOT_CONTAINS:
                if isinstance(claim_value, list):
                    return self.value not in claim_value
                return self.value not in str(claim_value)

            case ClaimOperator.MATCHES:
                # Regex match
                return bool(re.match(self.value, str(claim_value)))

            case ClaimOperator.IN:
                # Claim value must be in comma-separated list
                allowed_values = [v.strip() for v in self.value.split(",")]
                return str(claim_value) in allowed_values

            case ClaimOperator.NOT_IN:
                disallowed_values = [v.strip() for v in self.value.split(",")]
                return str(claim_value) not in disallowed_values

            case ClaimOperator.EXISTS:
                # Already handled above, but for completeness
                return True

            case _:
                return False

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "json_path": self.json_path,
            "operator": self.operator.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClaimMatcher":
        """Deserialize from dictionary."""
        return cls(
            json_path=data["json_path"],
            operator=ClaimOperator(data["operator"]),
            value=data["value"],
        )

    @classmethod
    def role_equals(cls, role: str, path: str = "realm_access.roles") -> "ClaimMatcher":
        """Factory method for matching a specific role."""
        return cls(json_path=path, operator=ClaimOperator.CONTAINS, value=role)

    @classmethod
    def claim_equals(cls, path: str, value: str) -> "ClaimMatcher":
        """Factory method for exact claim matching."""
        return cls(json_path=path, operator=ClaimOperator.EQUALS, value=value)

    @classmethod
    def claim_exists(cls, path: str) -> "ClaimMatcher":
        """Factory method for checking claim existence."""
        return cls(json_path=path, operator=ClaimOperator.EXISTS, value="")
