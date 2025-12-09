"""Add label to tool command and handler.

Assigns a label to a source tool for categorization.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from domain.entities.label import Label
from domain.entities.source_tool import SourceTool
from integration.models.label_dto import LabelDto
from integration.models.source_tool_dto import SourceToolDto
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)


@dataclass
class AddLabelToToolCommand(Command[OperationResult[SourceToolDto]]):
    """Command to add a label to a tool.

    Attributes:
        tool_id: ID of the tool to label
        label_id: ID of the label to add
        user_info: User performing the operation
    """

    tool_id: str
    label_id: str
    user_info: Optional[Dict[str, Any]] = None


class AddLabelToToolCommandHandler(
    CommandHandlerBase,
    CommandHandler[AddLabelToToolCommand, OperationResult[SourceToolDto]],
):
    """Handler for adding a label to a tool."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_tool_repository: Repository[SourceTool, str],
        source_tool_dto_repository: Repository[SourceToolDto, str],
        label_dto_repository: Repository[LabelDto, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_tool_repository = source_tool_repository
        self.source_tool_dto_repository = source_tool_dto_repository
        self.label_dto_repository = label_dto_repository

    async def handle_async(self, request: AddLabelToToolCommand) -> OperationResult[SourceToolDto]:
        """Handle adding a label to a tool."""
        command = request
        username = self._get_username(command.user_info)

        try:
            # Verify label exists
            label = await self.label_dto_repository.get_async(command.label_id)
            if not label:
                return self.not_found(Label, command.label_id)
            if label.is_deleted:
                return self.bad_request(f"Label '{label.name}' has been deleted")

            # Get the tool (write model)
            tool = await self.source_tool_repository.get_async(command.tool_id)
            if tool is None:
                return self.not_found(SourceTool, command.tool_id)

            # Add label
            if not tool.add_label(command.label_id, added_by=username):
                return self.bad_request(f"Tool already has label '{label.name}'")

            # Persist changes
            await self.source_tool_repository.update_async(tool)

            # Get updated DTO from read model
            tool_dto = await self.source_tool_dto_repository.get_async(command.tool_id)

            log.info(f"Added label '{label.name}' to tool '{command.tool_id}' by {username}")
            return self.ok(tool_dto)

        except Exception as e:
            log.exception(f"Error adding label to tool: {e}")
            return self.internal_server_error(f"Failed to add label: {str(e)}")
