"""Reset database command with handler.

Provides an admin command to reset all data in both WriteModel (EventStoreDB)
and ReadModel (MongoDB), then re-seed from YAML files.

This is a destructive operation that should only be used in development/testing.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from infrastructure.database_resetter import DatabaseResetter, ResetDatabaseResult

log = logging.getLogger(__name__)


@dataclass
class ResetDatabaseCommand(Command[OperationResult[ResetDatabaseResult]]):
    """Command to reset all data and re-seed from YAML files.

    This is a destructive operation that:
    1. Clears all aggregate streams from EventStoreDB (WriteModel)
    2. Drops all collections from MongoDB (ReadModel)
    3. Re-seeds AgentDefinitions and ConversationTemplates from YAML

    Only users with 'admin' role can execute this command.
    """

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""

    confirm: bool = False
    """Safety flag - must be True to proceed with reset."""


class ResetDatabaseCommandHandler(
    CommandHandlerBase,
    CommandHandler[ResetDatabaseCommand, OperationResult[ResetDatabaseResult]],
):
    """Handle database reset command.

    This handler coordinates the reset operation:
    1. Validates the confirmation flag
    2. Delegates to DatabaseResetter for actual clearing
    3. Triggers the DatabaseSeeder to re-seed data
    4. Returns a summary of the operation

    All operations are logged for audit purposes.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        database_resetter: DatabaseResetter,
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.database_resetter = database_resetter

    async def handle_async(self, request: ResetDatabaseCommand) -> OperationResult[ResetDatabaseResult]:
        """Handle the reset database command.

        Args:
            request: The reset command with confirmation flag

        Returns:
            OperationResult with reset summary
        """
        command = request

        # Extract user info for audit logging
        user_info = command.user_info or {}
        reset_by = user_info.get("preferred_username") or user_info.get("email") or user_info.get("sub", "unknown")

        log.warning(f"🗑️ Database reset requested by: {reset_by}")

        # Require explicit confirmation
        if not command.confirm:
            return self.bad_request(detail="Safety check failed: 'confirm' must be True to proceed with database reset.")

        try:
            # Execute the reset operation
            result = await self.database_resetter.reset_all_async(reset_by=reset_by)

            log.info(
                f"✅ Database reset completed by {reset_by} - "
                f"WriteModel: {'cleared' if result.cleared_write_model else 'failed'}, "
                f"ReadModel: {'cleared' if result.cleared_read_model else 'failed'}, "
                f"Seeded: {result.seeded}"
            )

            return self.ok(result)

        except Exception as e:
            log.error(f"❌ Database reset failed: {e}")
            import traceback

            log.debug(traceback.format_exc())
            # Re-raise as the framework will handle it appropriately
            raise RuntimeError(f"Database reset failed: {str(e)}") from e
