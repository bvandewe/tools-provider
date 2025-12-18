"""Client response value object for widget responses.

This module contains the ClientResponse value object that represents
a user's response to a client action (widget).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    """Validation status for client responses.

    Used to track whether user responses meet schema requirements.
    """

    VALID = "valid"
    INVALID = "invalid"
    SKIPPED = "skipped"


@dataclass
class ClientResponse:
    """User's response to a client action.

    Contains the user's input from a widget along with validation status.

    Attributes:
        tool_call_id: Matches the ClientAction's tool_call_id
        response: The actual response data (schema depends on widget type)
        timestamp: When the response was submitted
        validation_status: Whether the response passed schema validation
        validation_errors: List of validation error messages if invalid
    """

    tool_call_id: str
    response: Any
    timestamp: datetime
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "tool_call_id": self.tool_call_id,
            "response": self.response,
            "timestamp": self.timestamp.isoformat(),
            "validation_status": self.validation_status,
            "validation_errors": self.validation_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientResponse":
        """Create from dictionary."""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            tool_call_id=data["tool_call_id"],
            response=data["response"],
            timestamp=timestamp,
            validation_status=data.get("validation_status", ValidationStatus.VALID),
            validation_errors=data.get("validation_errors"),
        )
