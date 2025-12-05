"""ExecutionProfile value object.

Defines how to execute a tool against an upstream service.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from domain.enums import ExecutionMode

from .poll_config import PollConfig


@dataclass(frozen=True)
class ExecutionProfile:
    """How to execute a tool - the "recipe" for invocation.

    Contains all information needed to make the upstream API call,
    including URL templating, headers, body, and authentication requirements.

    This is an immutable value object used within ToolDefinition.
    """

    mode: ExecutionMode
    method: str  # HTTP method: GET, POST, PUT, DELETE, PATCH
    url_template: str  # Jinja2 template with {arg} placeholders

    # Request configuration
    headers_template: Dict[str, str] = field(default_factory=dict)
    body_template: Optional[str] = None  # Jinja2 template for request body
    content_type: str = "application/json"

    # Response handling
    response_mapping: Optional[Dict[str, str]] = None  # JSONPath mappings for response

    # Security - for token exchange
    required_audience: str = ""  # Keycloak client_id for token exchange
    required_scopes: List[str] = field(default_factory=list)

    # Timeouts
    timeout_seconds: int = 30

    # Async polling configuration (only if mode == ASYNC_POLL)
    poll_config: Optional[PollConfig] = None

    def __post_init__(self) -> None:
        """Validate the execution profile configuration."""
        if self.mode == ExecutionMode.ASYNC_POLL and self.poll_config is None:
            raise ValueError("poll_config is required when mode is ASYNC_POLL")

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "mode": self.mode.value,
            "method": self.method,
            "url_template": self.url_template,
            "headers_template": dict(self.headers_template),
            "body_template": self.body_template,
            "content_type": self.content_type,
            "response_mapping": dict(self.response_mapping) if self.response_mapping else None,
            "required_audience": self.required_audience,
            "required_scopes": list(self.required_scopes),
            "timeout_seconds": self.timeout_seconds,
            "poll_config": self.poll_config.to_dict() if self.poll_config else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionProfile":
        """Deserialize from dictionary."""
        poll_config = None
        if data.get("poll_config"):
            poll_config = PollConfig.from_dict(data["poll_config"])

        return cls(
            mode=ExecutionMode(data["mode"]),
            method=data["method"],
            url_template=data["url_template"],
            headers_template=data.get("headers_template", {}),
            body_template=data.get("body_template"),
            content_type=data.get("content_type", "application/json"),
            response_mapping=data.get("response_mapping"),
            required_audience=data.get("required_audience", ""),
            required_scopes=data.get("required_scopes", []),
            timeout_seconds=data.get("timeout_seconds", 30),
            poll_config=poll_config,
        )

    @classmethod
    def sync_http(
        cls,
        method: str,
        url_template: str,
        headers_template: Optional[Dict[str, str]] = None,
        body_template: Optional[str] = None,
        content_type: str = "application/json",
        required_audience: str = "",
        timeout_seconds: int = 30,
    ) -> "ExecutionProfile":
        """Factory method for synchronous HTTP execution."""
        return cls(
            mode=ExecutionMode.SYNC_HTTP,
            method=method,
            url_template=url_template,
            headers_template=headers_template or {},
            body_template=body_template,
            content_type=content_type,
            required_audience=required_audience,
            timeout_seconds=timeout_seconds,
        )
