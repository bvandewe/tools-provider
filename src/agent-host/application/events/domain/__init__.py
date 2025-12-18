"""Domain event handlers package.

With MongoDB-only architecture (no Event Sourcing), projection handlers are obsolete.
Domain events are still published via CloudEventPublisher for external consumers,
but there are no internal projection handlers to maintain separate read models.

All repositories now use the AggregateRoot directly for both reads and writes.
"""

__all__: list[str] = []
