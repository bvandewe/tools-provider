"""MongoDB repository implementation for LabelDto read model."""

from typing import List, Optional

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.repositories.label_dto_repository import LabelDtoRepository
from integration.models.label_dto import LabelDto


class MotorLabelDtoRepository(MotorRepository[LabelDto, str], LabelDtoRepository):
    """
    MongoDB-based repository for LabelDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements LabelDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.
    """

    async def get_all_async(self, include_deleted: bool = False) -> List[LabelDto]:
        """Retrieve all labels from the read model.

        Args:
            include_deleted: Whether to include soft-deleted labels
        """
        filter_dict = {}
        if not include_deleted:
            filter_dict["is_deleted"] = False

        cursor = self.collection.find(filter_dict).sort("name", 1)

        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                entities.append(entity)

        return entities

    async def get_by_name_async(self, name: str) -> Optional[LabelDto]:
        """Retrieve a label by its name (case-insensitive).

        Args:
            name: Label name to search for

        Returns:
            LabelDto if found, None otherwise
        """
        # Case-insensitive search
        filter_dict = {"name": {"$regex": f"^{name}$", "$options": "i"}, "is_deleted": False}

        doc = await self.collection.find_one(filter_dict)
        if doc:
            return self._deserialize_entity(doc)

        return None

    async def get_active_async(self) -> List[LabelDto]:
        """Retrieve all non-deleted labels from the read model."""
        return await self.get_all_async(include_deleted=False)

    async def search_by_name_async(self, name_filter: str) -> List[LabelDto]:
        """Search labels by name (case-insensitive partial match).

        Args:
            name_filter: Partial name to search for

        Returns:
            List of matching LabelDto objects
        """
        filter_dict = {"name": {"$regex": name_filter, "$options": "i"}}

        cursor = self.collection.find(filter_dict).sort("name", 1)

        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                entities.append(entity)

        return entities
