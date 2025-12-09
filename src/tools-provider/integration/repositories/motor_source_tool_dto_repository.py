"""MongoDB repository implementation for SourceToolDto read model."""

from typing import List, Optional

from domain.repositories.source_tool_dto_repository import SourceToolDtoRepository
from integration.models.source_tool_dto import SourceToolDto, SourceToolSummaryDto
from neuroglia.data.infrastructure.mongo import MotorRepository


class MotorSourceToolDtoRepository(MotorRepository[SourceToolDto, str], SourceToolDtoRepository):
    """MongoDB-based repository for SourceToolDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements SourceToolDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.

    Uses find_async() with sort/limit/skip options for querying.
    """

    async def get_by_source_id_async(
        self,
        source_id: str,
        include_disabled: bool = False,
        include_deprecated: bool = False,
    ) -> List[SourceToolDto]:
        """Get all tools for a specific source.

        Args:
            source_id: The upstream source ID
            include_disabled: Whether to include disabled tools
            include_deprecated: Whether to include deprecated tools

        Returns:
            List of tools for the source
        """
        # Build MongoDB query
        mongo_query: dict = {"source_id": source_id}

        if not include_disabled:
            mongo_query["is_enabled"] = True

        if not include_deprecated:
            mongo_query["status"] = "active"

        return await self.find_async(mongo_query, sort=[("tool_name", 1)])

    async def get_enabled_async(self) -> List[SourceToolDto]:
        """Get all enabled, active tools across all sources.

        Returns:
            List of enabled tools
        """
        return await self.find_async(
            {"is_enabled": True, "status": "active"},
            sort=[("tool_name", 1)],
        )

    async def get_by_ids_async(self, tool_ids: List[str]) -> List[SourceToolDto]:
        """Get multiple tools by their IDs.

        Args:
            tool_ids: List of tool IDs to retrieve

        Returns:
            List of tools (may be less than requested if some not found)
        """
        if not tool_ids:
            return []

        # Use MongoDB's $in operator for efficient batch lookup
        collection = self.collection
        cursor = collection.find({"id": {"$in": tool_ids}})
        results = []
        async for doc in cursor:
            results.append(self._deserialize(doc))
        return results

    async def search_async(
        self,
        query: str,
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_disabled: bool = False,
    ) -> List[SourceToolDto]:
        """Search tools by name, description, or tags.

        Args:
            query: Search query (matches name, description)
            source_id: Optional filter by source
            tags: Optional filter by tags (all must match)
            include_disabled: Whether to include disabled tools

        Returns:
            List of matching tools
        """
        # Build MongoDB query
        mongo_query: dict = {
            "$or": [
                {"tool_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
            ]
        }

        if source_id:
            mongo_query["source_id"] = source_id

        if tags:
            mongo_query["tags"] = {"$all": tags}

        if not include_disabled:
            mongo_query["is_enabled"] = True

        # Always exclude deprecated tools in search
        mongo_query["status"] = "active"

        collection = self.collection
        cursor = collection.find(mongo_query).sort("tool_name", 1)

        results = []
        async for doc in cursor:
            results.append(self._deserialize(doc))
        return results

    async def get_summaries_async(
        self,
        source_id: Optional[str] = None,
        include_disabled: bool = False,
    ) -> List[SourceToolSummaryDto]:
        """Get lightweight tool summaries for listing.

        Args:
            source_id: Optional filter by source
            include_disabled: Whether to include disabled tools

        Returns:
            List of tool summaries
        """
        # Build query
        mongo_query: dict = {"status": "active"}

        if source_id:
            mongo_query["source_id"] = source_id

        if not include_disabled:
            mongo_query["is_enabled"] = True

        # Project only fields needed for summary
        projection = {
            "_id": 1,
            "id": 1,  # The composite tool ID (source_id:operation_id)
            "source_id": 1,
            "source_name": 1,
            "tool_name": 1,
            "description": 1,
            "method": 1,
            "path": 1,
            "tags": 1,
            "label_ids": 1,
            "is_enabled": 1,
            "status": 1,
            "updated_at": 1,
            "input_schema": 1,  # Needed to compute params_count
        }

        collection = self.collection
        cursor = collection.find(mongo_query, projection).sort("tool_name", 1)

        results = []
        async for doc in cursor:
            # Compute params_count from input_schema properties
            input_schema = doc.get("input_schema", {})
            params_count = len(input_schema.get("properties", {})) if isinstance(input_schema, dict) else 0

            results.append(
                SourceToolSummaryDto(
                    id=doc.get("id", str(doc["_id"])),  # Use the 'id' field, not MongoDB's '_id'
                    source_id=doc.get("source_id", ""),
                    source_name=doc.get("source_name", ""),
                    tool_name=doc.get("tool_name", ""),
                    description=doc.get("description", ""),
                    method=doc.get("method", ""),
                    path=doc.get("path", ""),
                    tags=doc.get("tags", []),
                    label_ids=doc.get("label_ids", []),
                    params_count=params_count,
                    is_enabled=doc.get("is_enabled", True),
                    status=doc.get("status", "active"),
                    updated_at=doc.get("updated_at"),
                )
            )
        return results

    async def count_by_source_async(
        self,
        source_id: str,
        include_disabled: bool = False,
    ) -> int:
        """Count tools for a specific source.

        Args:
            source_id: The upstream source ID
            include_disabled: Whether to count disabled tools

        Returns:
            Number of tools
        """
        mongo_query: dict = {
            "source_id": source_id,
            "status": "active",
        }

        if not include_disabled:
            mongo_query["is_enabled"] = True

        collection = self.collection
        return await collection.count_documents(mongo_query)

    async def bulk_update_source_name_async(
        self,
        source_id: str,
        source_name: str,
    ) -> int:
        """Update the source_name for all tools from a source.

        Called when the source name is updated to keep denormalized data in sync.

        Args:
            source_id: The source whose tools to update
            source_name: The new source name

        Returns:
            Number of tools updated
        """
        collection = self.collection
        result = await collection.update_many(
            {"source_id": source_id},
            {"$set": {"source_name": source_name}},
        )
        return result.modified_count

    async def get_orphaned_tools_async(
        self,
        valid_source_ids: List[str],
    ) -> List[SourceToolDto]:
        """Get tools whose source_id is not in the list of valid sources.

        Used to find orphaned tools after source deletion.

        Args:
            valid_source_ids: List of existing source IDs

        Returns:
            List of orphaned tools
        """
        # Find tools where source_id is NOT in the valid list
        mongo_query = {"source_id": {"$nin": valid_source_ids}}
        return await self.find_async(mongo_query, sort=[("source_id", 1), ("tool_name", 1)])

    def _deserialize(self, doc: dict) -> SourceToolDto:
        """Deserialize MongoDB document to SourceToolDto."""
        return SourceToolDto(
            id=doc.get("id", str(doc["_id"])),  # Prefer 'id' field, fallback to _id
            source_id=doc.get("source_id", ""),
            source_name=doc.get("source_name", ""),
            tool_name=doc.get("tool_name", ""),
            operation_id=doc.get("operation_id", ""),
            description=doc.get("description", ""),
            method=doc.get("method", ""),
            path=doc.get("path", ""),
            execution_mode=doc.get("execution_mode", "sync_http"),
            input_schema=doc.get("input_schema", {}),
            tags=doc.get("tags", []),
            required_audience=doc.get("required_audience", ""),
            timeout_seconds=doc.get("timeout_seconds", 30),
            is_enabled=doc.get("is_enabled", True),
            status=doc.get("status", "active"),
            label_ids=doc.get("label_ids", []),
            discovered_at=doc.get("discovered_at"),
            last_seen_at=doc.get("last_seen_at"),
            updated_at=doc.get("updated_at"),
            enabled_by=doc.get("enabled_by"),
            disabled_by=doc.get("disabled_by"),
            disable_reason=doc.get("disable_reason"),
            definition=doc.get("definition"),
        )
