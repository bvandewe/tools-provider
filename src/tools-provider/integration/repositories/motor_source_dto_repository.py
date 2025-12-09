"""MongoDB repository implementation for SourceDto read model."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.enums import HealthStatus
from domain.repositories.source_dto_repository import SourceDtoRepository
from integration.models.source_dto import SourceDto


class MotorSourceDtoRepository(MotorRepository[SourceDto, str], SourceDtoRepository):
    """
    MongoDB-based repository for SourceDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements SourceDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.

    Note: Uses direct collection access with _find_with_options() helper instead of:
    1. Queryable lambda syntax - broken due to MotorQuery chaining bug
       (see notes/NEUROGLIA_MOTORQUERY_CHAINING_BUG.md)
    2. find_async() with sort - not supported
       (see notes/NEUROGLIA_MOTORREPOSITORY_FIND_ENHANCEMENT.md)
    """

    async def _find_with_options(
        self,
        filter_dict: dict,
        sort: list[tuple[str, int]] | None = None,
        limit: int | None = None,
        skip: int | None = None,
    ) -> list[SourceDto]:
        """Helper method to query MongoDB with sorting and pagination.

        Workaround for Neuroglia's find_async() not supporting sort/limit/skip.

        Args:
            filter_dict: MongoDB query filter
            sort: List of (field, direction) tuples. 1=ascending, -1=descending
            limit: Maximum number of documents to return
            skip: Number of documents to skip

        Returns:
            List of SourceDto entities
        """
        cursor = self.collection.find(filter_dict)

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            entities.append(entity)

        return entities

    async def get_all_async(self) -> list[SourceDto]:
        """Retrieve all sources from MongoDB.

        Delegates to MotorRepository's built-in method.
        """
        return await super().get_all_async()

    async def get_enabled_async(self) -> list[SourceDto]:
        """Retrieve all enabled sources, ordered by name."""
        return await self._find_with_options({"is_enabled": True}, sort=[("name", 1)])

    async def get_by_health_status_async(self, status: HealthStatus) -> list[SourceDto]:
        """Retrieve sources with a specific health status, ordered by updated_at."""
        return await self._find_with_options({"health_status": status.value}, sort=[("updated_at", 1)])

    async def get_by_source_type_async(self, source_type: str) -> list[SourceDto]:
        """Retrieve sources of a specific type, ordered by name.

        Args:
            source_type: Either "openapi" or "workflow"
        """
        return await self._find_with_options({"source_type": source_type}, sort=[("name", 1)])

    async def get_unhealthy_sources_async(self) -> list[SourceDto]:
        """Retrieve sources that are degraded or unhealthy, ordered by failure count."""
        return await self._find_with_options(
            {"health_status": {"$in": [HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value]}},
            sort=[("consecutive_failures", -1)],
        )
