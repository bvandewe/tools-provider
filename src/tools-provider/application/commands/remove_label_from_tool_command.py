"""Remove label from tool command and handler.

Removes a label from a source tool.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from domain.entities.source_tool import SourceTool
from integration.models.source_tool_dto import SourceToolDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)


@dataclass
class RemoveLabelFromToolCommand(Command[OperationResult[SourceToolDto]]):
    """Command to remove a label from a tool.

    Attributes:
        tool_id: ID of the tool
        label_id: ID of the label to remove
        user_info: User performing the operation
    """

    tool_id: str
    label_id: str
    user_info: dict[str, Any] | None = None


class RemoveLabelFromToolCommandHandler(
    CommandHandlerBase,
    CommandHandler[RemoveLabelFromToolCommand, OperationResult[SourceToolDto]],
):
    """Handler for removing a label from a tool."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_tool_repository: Repository[SourceTool, str],
        source_tool_dto_repository: Repository[SourceToolDto, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_tool_repository = source_tool_repository
        self.source_tool_dto_repository = source_tool_dto_repository

    async def handle_async(self, request: RemoveLabelFromToolCommand) -> OperationResult[SourceToolDto]:
        """Handle removing a label from a tool."""
        command = request
        username = self._get_username(command.user_info)

        try:
            # Get the tool (write model)
            tool = await self.source_tool_repository.get_async(command.tool_id)
            if tool is None:
                return self.not_found(SourceTool, command.tool_id)

            # Remove label
            if not tool.remove_label(command.label_id, removed_by=username):
                return self.bad_request(f"Tool does not have label '{command.label_id}'")

            # Persist changes
            await self.source_tool_repository.update_async(tool)

            # Get updated DTO from read model
            tool_dto = await self.source_tool_dto_repository.get_async(command.tool_id)

            log.info(f"Removed label '{command.label_id}' from tool '{command.tool_id}' by {username}")
            return self.ok(tool_dto)

        except Exception as e:
            log.exception(f"Error removing label from tool: {e}")
            return self.internal_server_error(f"Failed to remove label: {str(e)}")
