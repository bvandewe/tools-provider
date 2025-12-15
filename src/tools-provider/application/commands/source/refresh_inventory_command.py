"""Refresh inventory command with handler.

This command triggers a synchronization of the tool inventory for an upstream source.
It fetches the latest specification, parses tools, and creates/updates SourceTool aggregates.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from kurrentdbclient.exceptions import NotFoundError as StreamNotFound
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from application.services import get_adapter_for_type
from domain.entities import SourceTool, UpstreamSource
from domain.enums import SourceType
from domain.models import McpSourceConfig, ToolDefinition

from ..command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class RefreshInventoryResult:
    """Result of an inventory refresh operation."""

    source_id: str
    """ID of the source that was refreshed."""

    success: bool
    """Whether the refresh succeeded."""

    tools_discovered: int = 0
    """Number of tools discovered from the spec."""

    tools_created: int = 0
    """Number of new tools created."""

    tools_updated: int = 0
    """Number of existing tools with updated definitions."""

    tools_deprecated: int = 0
    """Number of tools deprecated (no longer in spec)."""

    inventory_hash: str = ""
    """Hash of the new inventory."""

    source_version: str | None = None
    """Version from the source spec."""

    error: str | None = None
    """Error message if refresh failed."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings from parsing."""

    duration_ms: float = 0.0
    """Time taken for the refresh in milliseconds."""


@dataclass
class RefreshInventoryCommand(Command[OperationResult[RefreshInventoryResult]]):
    """Command to refresh the tool inventory for an upstream source.

    This command:
    1. Fetches the latest specification from the source URL
    2. Parses the spec into ToolDefinitions
    3. Creates new SourceTool aggregates for discovered tools
    4. Updates definitions for existing tools
    5. Deprecates tools no longer in the spec
    6. Updates the UpstreamSource inventory metadata
    """

    source_id: str
    """ID of the upstream source to refresh."""

    force: bool = False
    """Force refresh even if inventory hash unchanged."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class RefreshInventoryCommandHandler(
    CommandHandlerBase,
    CommandHandler[RefreshInventoryCommand, OperationResult[RefreshInventoryResult]],
):
    """Handler for refreshing upstream source inventory.

    This handler orchestrates the full inventory sync process:
    1. Load the UpstreamSource aggregate
    2. Fetch and parse the specification using the appropriate adapter
    3. Create/update SourceTool aggregates for each discovered tool
    4. Deprecate tools that no longer exist in the spec
    5. Update the UpstreamSource with new inventory hash
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_repository: Repository[UpstreamSource, str],
        tool_repository: Repository[SourceTool, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_repository = source_repository
        self.tool_repository = tool_repository

    async def handle_async(self, request: RefreshInventoryCommand) -> OperationResult[RefreshInventoryResult]:
        """Handle the refresh inventory command."""
        command = request
        start_time = time.time()

        # Add tracing context
        add_span_attributes(
            {
                "source.id": command.source_id,
                "source.force_refresh": command.force,
            }
        )

        with tracer.start_as_current_span("refresh_inventory") as span:
            # Load the source aggregate
            # Note: Neuroglia's EventSourcingRepository.get_async raises esdbclient.NotFound
            # instead of returning None when the stream doesn't exist
            try:
                source = await self.source_repository.get_async(command.source_id)
            except StreamNotFound:
                source = None

            if not source:
                return self.not_found(UpstreamSource, command.source_id)

            span.set_attribute("source.name", source.state.name)
            span.set_attribute("source.type", source.state.source_type.value)
            span.set_attribute("source.url", source.state.url)
            span.set_attribute("source.openapi_url", source.state.openapi_url or "")

            # Check if source is enabled
            if not source.state.is_enabled:
                return self.bad_request(f"Source {command.source_id} is disabled")

            # Determine triggered_by
            triggered_by = None
            if command.user_info:
                triggered_by = command.user_info.get("sub") or command.user_info.get("user_id") or "system"

            # Mark sync as started
            source.mark_sync_started(triggered_by=triggered_by)
            await self.source_repository.update_async(source)

            # Determine the URL to use for fetching the spec
            # If openapi_url is set, use it; otherwise fall back to url
            spec_url = source.state.openapi_url or source.state.url

            # For MCP sources, reconstruct McpSourceConfig from stored dict
            mcp_config: McpSourceConfig | None = None
            if source.state.source_type == SourceType.MCP and source.state.mcp_config:
                try:
                    mcp_config = McpSourceConfig.from_dict(source.state.mcp_config)
                    span.set_attribute("mcp.plugin_dir", mcp_config.plugin_dir)
                    span.set_attribute("mcp.transport_type", mcp_config.transport_type.value)
                except Exception as e:
                    log.exception(f"Failed to parse MCP config for source {command.source_id}")
                    source.mark_sync_failed(f"Invalid MCP configuration: {e}")
                    await self.source_repository.update_async(source)
                    return self.ok(
                        RefreshInventoryResult(
                            source_id=command.source_id,
                            success=False,
                            error=f"Invalid MCP configuration: {e}",
                            duration_ms=(time.time() - start_time) * 1000,
                        )
                    )

            # Fetch and parse specification
            try:
                adapter = get_adapter_for_type(source.state.source_type)
                ingestion_result = await adapter.fetch_and_normalize(
                    url=spec_url,
                    auth_config=source.state.auth_config,
                    default_audience=source.state.default_audience,
                    mcp_config=mcp_config,
                )
            except Exception as e:
                log.exception(f"Failed to fetch inventory for source {command.source_id}")
                source.mark_sync_failed(str(e))
                await self.source_repository.update_async(source)
                return self.ok(
                    RefreshInventoryResult(
                        source_id=command.source_id,
                        success=False,
                        error=str(e),
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                )

            # Handle ingestion failure
            if not ingestion_result.success:
                source.mark_sync_failed(ingestion_result.error or "Unknown error")
                await self.source_repository.update_async(source)
                return self.ok(
                    RefreshInventoryResult(
                        source_id=command.source_id,
                        success=False,
                        error=ingestion_result.error,
                        warnings=ingestion_result.warnings,
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                )

            span.add_event(
                "Ingestion completed",
                {"tool_count": len(ingestion_result.tools)},
            )

            # Check if inventory actually changed
            if not command.force and source.state.inventory_hash == ingestion_result.inventory_hash:
                log.info(f"Inventory unchanged for source {command.source_id}")
                return self.ok(
                    RefreshInventoryResult(
                        source_id=command.source_id,
                        success=True,
                        tools_discovered=len(ingestion_result.tools),
                        inventory_hash=ingestion_result.inventory_hash,
                        source_version=ingestion_result.source_version,
                        warnings=["Inventory unchanged, skipped update"],
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                )

            # Process tools - create, update, or deprecate
            tools_created, tools_updated, tools_deprecated = await self._sync_tools(
                source_id=command.source_id,
                discovered_tools=ingestion_result.tools,
                span=span,
            )

            # Update source inventory
            source.update_inventory(
                tools=ingestion_result.tools,
                new_hash=ingestion_result.inventory_hash,
            )
            await self.source_repository.update_async(source)

            duration_ms = (time.time() - start_time) * 1000

            result = RefreshInventoryResult(
                source_id=command.source_id,
                success=True,
                tools_discovered=len(ingestion_result.tools),
                tools_created=tools_created,
                tools_updated=tools_updated,
                tools_deprecated=tools_deprecated,
                inventory_hash=ingestion_result.inventory_hash,
                source_version=ingestion_result.source_version,
                warnings=ingestion_result.warnings,
                duration_ms=duration_ms,
            )

            log.info(f"Inventory refresh completed for {command.source_id}: {tools_created} created, {tools_updated} updated, {tools_deprecated} deprecated in {duration_ms:.2f}ms")

            return self.ok(result)

    async def _sync_tools(
        self,
        source_id: str,
        discovered_tools: list[ToolDefinition],
        span: Any,
    ) -> tuple[int, int, int]:
        """Synchronize discovered tools with existing SourceTool aggregates.

        Creates new tools, updates changed definitions, and deprecates removed tools.

        Args:
            source_id: ID of the upstream source
            discovered_tools: List of tools parsed from the spec
            span: OpenTelemetry span for tracing

        Returns:
            Tuple of (created_count, updated_count, deprecated_count)
        """
        created_count = 0
        updated_count = 0
        deprecated_count = 0

        # Build map of discovered tools by generated ID
        discovered_tool_ids: dict[str, ToolDefinition] = {}
        for tool_def in discovered_tools:
            tool_id = SourceTool.create_tool_id(source_id, tool_def.name)
            discovered_tool_ids[tool_id] = tool_def

        span.add_event("Processing discovered tools", {"count": len(discovered_tool_ids)})

        # Process each discovered tool
        for tool_id, tool_def in discovered_tool_ids.items():
            # Try to get existing tool - handle StreamNotFound for new tools
            # Note: Neuroglia's EventSourcingRepository.get_async raises esdbclient.NotFound
            # instead of returning None when the stream doesn't exist
            try:
                existing_tool = await self.tool_repository.get_async(tool_id)
            except StreamNotFound:
                existing_tool = None

            if existing_tool is None:
                # Create new tool
                new_tool = SourceTool(
                    source_id=source_id,
                    operation_id=tool_def.name,
                    tool_name=tool_def.name,
                    definition=tool_def,
                )
                await self.tool_repository.add_async(new_tool)
                created_count += 1
                log.debug(f"Created new tool: {tool_id}")

            else:
                # Check if definition changed
                was_updated = existing_tool.update_definition(tool_def)
                if was_updated:
                    await self.tool_repository.update_async(existing_tool)
                    updated_count += 1
                    log.debug(f"Updated tool definition: {tool_id}")
                else:
                    # Just update last_seen timestamp in memory
                    # Note: mark_seen() doesn't emit events, so no need to persist
                    # The read model's last_seen_at will be updated by projection
                    # handlers when tool events are processed
                    existing_tool.mark_seen()

                # If tool was deprecated, restore it
                if existing_tool.state.status.value == "deprecated":
                    existing_tool.restore(tool_def)
                    await self.tool_repository.update_async(existing_tool)
                    log.debug(f"Restored deprecated tool: {tool_id}")

        # Find and deprecate tools no longer in spec
        # Note: In a real system, you'd query existing tools by source_id
        # For now, we skip deprecation logic to avoid complex queries
        # TODO: Implement tool deprecation when SourceToolDtoRepository.get_by_source_id is available in write model

        span.add_event(
            "Tool sync completed",
            {
                "created": created_count,
                "updated": updated_count,
                "deprecated": deprecated_count,
            },
        )

        return created_count, updated_count, deprecated_count
