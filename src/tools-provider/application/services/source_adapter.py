"""Abstract Source Adapter for fetching and normalizing tool definitions.

This module defines the abstract base class for source adapters, which are
responsible for fetching external specifications (OpenAPI, Workflow) and
converting them to normalized ToolDefinition objects.

The adapter pattern allows for polymorphic ingestion from different source types
while maintaining a consistent interface for the application layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.enums import SourceType
from domain.models import AuthConfig, ToolDefinition


@dataclass
class IngestionResult:
    """Result of a source ingestion operation.

    Contains the parsed tools along with metadata about the ingestion process.
    """

    tools: list[ToolDefinition]
    """List of parsed ToolDefinition objects."""

    inventory_hash: str
    """Hash of the entire inventory for change detection."""

    success: bool = True
    """Whether the ingestion was successful."""

    error: str | None = None
    """Error message if ingestion failed."""

    source_version: str | None = None
    """Version of the source spec (e.g., OpenAPI info.version)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings encountered during parsing."""

    ingested_at: datetime | None = None
    """Timestamp of the ingestion."""

    def __post_init__(self) -> None:
        """Set default ingestion timestamp."""
        if self.ingested_at is None:
            self.ingested_at = datetime.now(UTC)

    @classmethod
    def failure(cls, error: str) -> "IngestionResult":
        """Create a failed ingestion result.

        Args:
            error: Description of what went wrong

        Returns:
            IngestionResult with success=False
        """
        return cls(
            tools=[],
            inventory_hash="",
            success=False,
            error=error,
        )


class SourceAdapter(ABC):
    """Abstract base class for source adapters.

    Source adapters are responsible for:
    1. Fetching specifications from external URLs
    2. Parsing the specification format (OpenAPI, Workflow, etc.)
    3. Converting parsed operations to normalized ToolDefinition objects
    4. Computing inventory hashes for change detection

    Implementations:
    - OpenAPISourceAdapter: Parses OpenAPI 3.x specifications
    - WorkflowSourceAdapter: Parses workflow engine definitions (future)
    """

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Return the type of source this adapter handles."""
        ...

    @abstractmethod
    async def fetch_and_normalize(
        self,
        url: str,
        auth_config: AuthConfig | None = None,
        default_audience: str | None = None,
    ) -> IngestionResult:
        """Fetch a specification and convert it to ToolDefinitions.

        This is the main entry point for source ingestion. It:
        1. Fetches the specification from the given URL
        2. Parses the specification format
        3. Converts each operation to a ToolDefinition
        4. Computes an inventory hash for the complete set

        Args:
            url: URL to the specification (e.g., OpenAPI JSON/YAML URL)
            auth_config: Optional authentication configuration for the fetch
            default_audience: Optional default audience for token exchange (used when
                spec doesn't specify one via x-audience extension)

        Returns:
            IngestionResult containing parsed tools or error information

        Raises:
            Should not raise exceptions - errors should be captured in IngestionResult
        """
        ...

    @abstractmethod
    async def validate_url(self, url: str, auth_config: AuthConfig | None = None) -> bool:
        """Validate that a URL points to a valid specification.

        Used during source registration to verify the URL is accessible
        and contains a valid specification.

        Args:
            url: URL to validate
            auth_config: Optional authentication configuration

        Returns:
            True if URL is valid and accessible, False otherwise
        """
        ...


def get_adapter_for_type(source_type: SourceType) -> SourceAdapter:
    """Factory function to get the appropriate adapter for a source type.

    Args:
        source_type: The type of source to get an adapter for

    Returns:
        Appropriate SourceAdapter implementation

    Raises:
        ValueError: If no adapter exists for the given type
    """
    # Import here to avoid circular imports
    from .openapi_source_adapter import OpenAPISourceAdapter

    adapters = {
        SourceType.OPENAPI: OpenAPISourceAdapter(),
        # SourceType.WORKFLOW: WorkflowSourceAdapter(),  # Future implementation
    }

    adapter = adapters.get(source_type)
    if adapter is None:
        raise ValueError(f"No adapter available for source type: {source_type}")

    return adapter
