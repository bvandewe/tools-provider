"""Domain events for User authentication.

These events represent important business occurrences that have happened in the past
and may trigger side effects like notifications, logging, or updating read models.
"""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("user.loggedin.v1")
@dataclass
class UserLoggedInDomainEvent(DomainEvent):
    """Event raised when a user logs in to the Agent Host."""

    def __init__(self, aggregate_id: str, username: str, login_at: datetime):
        super().__init__(aggregate_id)
        self.username = username
        # Convert datetime to ISO8601 string for CloudEvent compatibility
        self.login_at = login_at.isoformat() if isinstance(login_at, datetime) else login_at

    aggregate_id: str
    username: str
    login_at: str  # Changed to str to ensure CloudEvent compatibility


@cloudevent("user.loggedout.v1")
@dataclass
class UserLoggedOutDomainEvent(DomainEvent):
    """Event raised when a user logs out from the Agent Host."""

    def __init__(self, aggregate_id: str, username: str, logout_at: datetime):
        super().__init__(aggregate_id)
        self.username = username
        self.logout_at = logout_at.isoformat() if isinstance(logout_at, datetime) else logout_at

    aggregate_id: str
    username: str
    logout_at: str
