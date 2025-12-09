"""PollConfig value object.

Configuration for async polling execution mode.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PollConfig:
    """Configuration for async polling execution mode.

    When a tool uses ASYNC_POLL execution mode, this configuration
    defines how to poll for the operation's completion status.

    This is an immutable value object used within ExecutionProfile.
    """

    status_url_template: str  # URL template with {job_id} placeholder
    status_field_path: str  # JSONPath to status field in response
    completed_values: list[str]  # Values indicating job completed successfully
    failed_values: list[str]  # Values indicating job failed
    result_field_path: str  # JSONPath to result data in response

    # Polling behavior
    max_poll_attempts: int = 60
    poll_interval_seconds: float = 1.0
    backoff_multiplier: float = 1.5
    max_interval_seconds: float = 30.0

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "status_url_template": self.status_url_template,
            "status_field_path": self.status_field_path,
            "completed_values": list(self.completed_values),
            "failed_values": list(self.failed_values),
            "result_field_path": self.result_field_path,
            "max_poll_attempts": self.max_poll_attempts,
            "poll_interval_seconds": self.poll_interval_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "max_interval_seconds": self.max_interval_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PollConfig":
        """Deserialize from dictionary."""
        return cls(
            status_url_template=data["status_url_template"],
            status_field_path=data["status_field_path"],
            completed_values=data["completed_values"],
            failed_values=data["failed_values"],
            result_field_path=data["result_field_path"],
            max_poll_attempts=data.get("max_poll_attempts", 60),
            poll_interval_seconds=data.get("poll_interval_seconds", 1.0),
            backoff_multiplier=data.get("backoff_multiplier", 1.5),
            max_interval_seconds=data.get("max_interval_seconds", 30.0),
        )
