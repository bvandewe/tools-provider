"""Domain exceptions for agent-host.

This module contains domain-specific exceptions that can be raised
by aggregate roots and domain services when invariants are violated.
"""


class DomainError(Exception):
    """Base exception for domain rule violations.

    Raised when a domain invariant is violated or a business rule
    cannot be satisfied. This is distinct from application-level
    errors or infrastructure failures.

    Attributes:
        message: Human-readable description of the violation.
        code: Optional error code for programmatic handling.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class AgentNotFoundError(DomainError):
    """Raised when an agent cannot be found."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent not found: {agent_id}", code="AGENT_NOT_FOUND")
        self.agent_id = agent_id


class AgentArchivedError(DomainError):
    """Raised when attempting to modify an archived agent."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent is archived and cannot be modified: {agent_id}", code="AGENT_ARCHIVED")
        self.agent_id = agent_id


class SessionAlreadyActiveError(DomainError):
    """Raised when attempting to start a session while one is already active."""

    def __init__(self, agent_id: str, session_id: str) -> None:
        super().__init__(f"Agent {agent_id} already has an active session: {session_id}", code="SESSION_ALREADY_ACTIVE")
        self.agent_id = agent_id
        self.session_id = session_id


class NoActiveSessionError(DomainError):
    """Raised when an operation requires an active session but none exists."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent {agent_id} has no active session", code="NO_ACTIVE_SESSION")
        self.agent_id = agent_id


class InvalidToolCallIdError(DomainError):
    """Raised when a client response has a mismatched tool_call_id."""

    def __init__(self, expected: str, received: str) -> None:
        super().__init__(f"Tool call ID mismatch: expected '{expected}', received '{received}'", code="INVALID_TOOL_CALL_ID")
        self.expected = expected
        self.received = received


class NotSuspendedError(DomainError):
    """Raised when attempting to resume an agent that is not suspended."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent {agent_id} is not suspended", code="NOT_SUSPENDED")
        self.agent_id = agent_id


class UserAlreadyAssignedError(DomainError):
    """Raised when attempting to assign a user who is already assigned."""

    def __init__(self, agent_id: str, user_id: str) -> None:
        super().__init__(f"User {user_id} is already assigned to agent {agent_id}", code="USER_ALREADY_ASSIGNED")
        self.agent_id = agent_id
        self.user_id = user_id


class InvalidAssignmentRoleError(DomainError):
    """Raised when an invalid assignment role is provided."""

    def __init__(self, role: str) -> None:
        super().__init__(f"Invalid assignment role: {role}", code="INVALID_ASSIGNMENT_ROLE")
        self.role = role
