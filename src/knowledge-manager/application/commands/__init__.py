"""Command handlers for Knowledge Manager."""

from application.commands.command_handler_base import CommandHandlerBase
from application.commands.namespace.add_term_command import AddTermCommand, AddTermCommandHandler
from application.commands.namespace.create_namespace_command import CreateNamespaceCommand, CreateNamespaceCommandHandler
from application.commands.namespace.delete_namespace_command import DeleteNamespaceCommand, DeleteNamespaceCommandHandler
from application.commands.namespace.remove_term_command import RemoveTermCommand, RemoveTermCommandHandler
from application.commands.namespace.update_namespace_command import UpdateNamespaceCommand, UpdateNamespaceCommandHandler
from application.commands.namespace.update_term_command import UpdateTermCommand, UpdateTermCommandHandler

__all__ = [
    "CommandHandlerBase",
    # Namespace commands
    "CreateNamespaceCommand",
    "CreateNamespaceCommandHandler",
    "UpdateNamespaceCommand",
    "UpdateNamespaceCommandHandler",
    "DeleteNamespaceCommand",
    "DeleteNamespaceCommandHandler",
    # Term commands
    "AddTermCommand",
    "AddTermCommandHandler",
    "UpdateTermCommand",
    "UpdateTermCommandHandler",
    "RemoveTermCommand",
    "RemoveTermCommandHandler",
]
