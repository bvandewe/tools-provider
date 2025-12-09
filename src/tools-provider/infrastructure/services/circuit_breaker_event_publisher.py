"""Circuit Breaker Event Publisher Service.

This service handles publishing CloudEvents for circuit breaker state transitions.
It's designed to be used as a callback from CircuitBreaker instances to emit
events when the circuit changes state (opened, closed, half-opened).
"""

import datetime
import logging
import uuid
from typing import TYPE_CHECKING, Any

from neuroglia.eventing.cloud_events.cloud_event import CloudEvent, CloudEventSpecVersion
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions

from domain.events.circuit_breaker import CircuitBreakerClosedDomainEvent, CircuitBreakerHalfOpenedDomainEvent, CircuitBreakerOpenedDomainEvent

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


class CircuitBreakerEventPublisher:
    """Service for publishing circuit breaker state change events.

    This service provides a callback function that can be passed to CircuitBreaker
    instances. When the circuit breaker transitions state, it will call the callback
    which publishes the event as a CloudEvent.

    Example:
        publisher = CircuitBreakerEventPublisher(cloud_event_bus, options)
        circuit = CircuitBreaker(
            circuit_id="keycloak",
            circuit_type="token_exchange",
            on_state_change=publisher.publish_event,
        )
    """

    def __init__(
        self,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        """Initialize the circuit breaker event publisher.

        Args:
            cloud_event_bus: The CloudEventBus for publishing events
            cloud_event_publishing_options: Options for CloudEvent publishing
        """
        self._cloud_event_bus = cloud_event_bus
        self._publishing_options = cloud_event_publishing_options

    async def publish_event(self, event: Any) -> None:
        """Publish a circuit breaker state change event.

        This method is designed to be used as the on_state_change callback
        for CircuitBreaker instances.

        Args:
            event: A CircuitBreaker domain event (Opened, Closed, or HalfOpened)
        """
        try:
            # Determine event type from the event class
            event_type: str | None = None
            if isinstance(event, CircuitBreakerOpenedDomainEvent):
                event_type = "circuit_breaker.opened.v1"
            elif isinstance(event, CircuitBreakerClosedDomainEvent):
                event_type = "circuit_breaker.closed.v1"
            elif isinstance(event, CircuitBreakerHalfOpenedDomainEvent):
                event_type = "circuit_breaker.half_opened.v1"
            else:
                logger.warning(f"Unknown circuit breaker event type: {type(event)}")
                return

            # Build CloudEvent
            cloud_event = CloudEvent(
                id=str(uuid.uuid4()).replace("-", ""),
                source=self._publishing_options.source,
                type=f"{self._publishing_options.type_prefix}.{event_type}",
                specversion=CloudEventSpecVersion.v1_0,
                time=datetime.datetime.now(datetime.UTC),
                subject=event.circuit_id,
                data=self._event_to_dict(event),
            )

            # Publish to the event bus (synchronous reactive stream)
            self._cloud_event_bus.output_stream.on_next(cloud_event)

            # Log with optional manual reset info (only for closed events)
            log_msg = f"Published circuit breaker event: {event_type} for circuit '{event.circuit_id}'"
            if isinstance(event, CircuitBreakerClosedDomainEvent) and event.closed_by:
                log_msg += f" (manual reset by {event.closed_by})"
            logger.info(log_msg)

        except Exception as e:
            # Don't let event publishing failures break the circuit breaker
            logger.error(f"Failed to publish circuit breaker event: {e}")

    def _event_to_dict(self, event: Any) -> dict:
        """Convert a circuit breaker event to a dictionary.

        Args:
            event: The domain event to convert

        Returns:
            Dictionary representation of the event
        """
        if isinstance(event, CircuitBreakerOpenedDomainEvent):
            return {
                "circuit_id": event.circuit_id,
                "circuit_type": event.circuit_type,
                "source_id": event.source_id,
                "failure_count": event.failure_count,
                "failure_threshold": event.failure_threshold,
                "last_failure_time": event.last_failure_time.isoformat() if event.last_failure_time else None,
                "reason": event.reason.value if event.reason else None,
            }
        elif isinstance(event, CircuitBreakerClosedDomainEvent):
            return {
                "circuit_id": event.circuit_id,
                "circuit_type": event.circuit_type,
                "source_id": event.source_id,
                "reason": event.reason.value if event.reason else None,
                "closed_at": event.closed_at.isoformat() if event.closed_at else None,
                "was_manual": event.was_manual,
                "closed_by": event.closed_by,
            }
        elif isinstance(event, CircuitBreakerHalfOpenedDomainEvent):
            return {
                "circuit_id": event.circuit_id,
                "circuit_type": event.circuit_type,
                "source_id": event.source_id,
                "recovery_timeout": event.recovery_timeout,
                "opened_at": event.opened_at.isoformat() if event.opened_at else None,
            }
        else:
            # Fallback: try to use __dict__
            return dict(event.__dict__) if hasattr(event, "__dict__") else {}

    # =========================================================================
    # Service Configuration (Neuroglia Pattern)
    # =========================================================================

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure and register the circuit breaker event publisher.

        This method follows the Neuroglia pattern for service configuration,
        creating a singleton instance and registering it in the DI container.

        Resolves CloudEventBus and CloudEventPublishingOptions from the DI container.
        Must be called after CloudEventPublisher.configure(builder).

        Args:
            builder: WebApplicationBuilder instance for service registration

        Returns:
            The builder instance for fluent chaining
        """
        log = logging.getLogger(__name__)
        log.info("🔧 Configuring CircuitBreakerEventPublisher...")

        # Resolve CloudEventBus from registered singletons
        cloud_event_bus: CloudEventBus | None = None
        for desc in builder.services:
            if desc.service_type == CloudEventBus and desc.singleton is not None:
                cloud_event_bus = desc.singleton
                break

        # Resolve CloudEventPublishingOptions from registered singletons
        publishing_options: CloudEventPublishingOptions | None = None
        for desc in builder.services:
            if desc.service_type == CloudEventPublishingOptions and desc.singleton is not None:
                publishing_options = desc.singleton
                break

        if not cloud_event_bus or not publishing_options:
            log.warning("CloudEventBus or CloudEventPublishingOptions not found in DI container. " "Circuit breaker events will not be published.")
            return builder

        publisher = CircuitBreakerEventPublisher(
            cloud_event_bus=cloud_event_bus,
            cloud_event_publishing_options=publishing_options,
        )
        builder.services.add_singleton(CircuitBreakerEventPublisher, singleton=publisher)
        log.info("✅ CircuitBreakerEventPublisher configured")

        return builder
