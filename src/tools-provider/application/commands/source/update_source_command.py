"""Update Source Command.

Command and handler for updating editable fields of an existing upstream source.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from opentelemetry import trace

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities import UpstreamSource
from integration.models.source_dto import SourceDto

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class UpdateSourceCommand(Command[OperationResult[SourceDto]]):
    """Command to update an existing upstream source.

    Editable fields:
    - name: Human-readable name
    - description: Human-readable description
    - url: Service base URL (not the OpenAPI spec URL)
    - required_scopes: Scopes required for all tools from this source

    Note: openapi_url is immutable and cannot be changed after registration.
    """

    source_id: str
    """ID of the source to update."""

    name: str | None = None
    """New name for the source. None to keep current."""

    description: str | None = None
    """New description. None to keep current."""

    url: str | None = None
    """New service base URL. None to keep current."""

    required_scopes: list[str] | None = None
    """New scopes required for all tools from this source. None to keep current."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class UpdateSourceCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateSourceCommand, OperationResult[SourceDto]],
):
    """Handler for updating existing upstream sources.

    This handler:
    1. Loads the existing source from EventStoreDB
    2. Validates the update request
    3. Updates the aggregate
    4. Persists the changes
    5. Returns the updated source DTO
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_repository: Repository[UpstreamSource, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_repository = source_repository

    async def handle_async(self, request: UpdateSourceCommand) -> OperationResult[SourceDto]:
        """Handle the update source command."""
        command = request
        start_time = time.time()

        with tracer.start_as_current_span("UpdateSourceCommand") as span:
            span.set_attribute("source.id", command.source_id)

            # Load existing source
            source = await self.source_repository.get_async(command.source_id)
            if not source:
                return self.not_found(UpstreamSource, command.source_id)

            # Determine updated_by from user context
            updated_by = None
            if command.user_info:
                updated_by = command.user_info.get("sub") or command.user_info.get("user_id") or command.user_info.get("preferred_username")

            # Update the aggregate
            changed = source.update(
                name=command.name,
                description=command.description,
                url=command.url,
                required_scopes=command.required_scopes,
                updated_by=updated_by,
            )

            if not changed:
                log.info(f"No changes to apply for source {command.source_id}")
                # Return current state without saving
                dto = SourceDto(
                    id=source.id(),
                    name=source.state.name,
                    url=source.state.url,
                    source_type=source.state.source_type,
                    health_status=source.state.health_status,
                    is_enabled=source.state.is_enabled,
                    inventory_count=source.state.inventory_count,
                    inventory_hash=source.state.inventory_hash,
                    last_sync_at=source.state.last_sync_at,
                    last_sync_error=source.state.last_sync_error,
                    consecutive_failures=source.state.consecutive_failures,
                    created_at=source.state.created_at,
                    updated_at=source.state.updated_at,
                    created_by=source.state.created_by,
                    default_audience=source.state.default_audience,
                    openapi_url=source.state.openapi_url,
                    description=source.state.description,
                    auth_mode=source.state.auth_mode,
                    required_scopes=source.state.required_scopes,
                )
                return self.ok(dto)

            span.set_attribute("source.updated_by", updated_by or "unknown")

            # Persist changes to EventStoreDB
            saved_source = await self.source_repository.update_async(source)

            # Build DTO response
            dto = SourceDto(
                id=saved_source.id(),
                name=saved_source.state.name,
                url=saved_source.state.url,
                source_type=saved_source.state.source_type,
                health_status=saved_source.state.health_status,
                is_enabled=saved_source.state.is_enabled,
                inventory_count=saved_source.state.inventory_count,
                inventory_hash=saved_source.state.inventory_hash,
                last_sync_at=saved_source.state.last_sync_at,
                last_sync_error=saved_source.state.last_sync_error,
                consecutive_failures=saved_source.state.consecutive_failures,
                created_at=saved_source.state.created_at,
                updated_at=saved_source.state.updated_at,
                created_by=saved_source.state.created_by,
                default_audience=saved_source.state.default_audience,
                openapi_url=saved_source.state.openapi_url,
                description=saved_source.state.description,
                auth_mode=saved_source.state.auth_mode,
                required_scopes=saved_source.state.required_scopes,
            )

            processing_time = (time.time() - start_time) * 1000
            log.info(f"Source updated: {dto.id} ({dto.name}) in {processing_time:.2f}ms")

            return self.ok(dto)
