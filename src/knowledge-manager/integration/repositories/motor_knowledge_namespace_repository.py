"""MongoDB repository implementation for KnowledgeNamespace aggregate."""

import logging

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.entities import KnowledgeNamespace
from domain.repositories import KnowledgeNamespaceRepository

log = logging.getLogger(__name__)


class MotorKnowledgeNamespaceRepository(MotorRepository[KnowledgeNamespace, str], KnowledgeNamespaceRepository):
    """MongoDB-based repository for KnowledgeNamespace aggregate.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements KnowledgeNamespaceRepository for domain-specific query methods.

    Configured via MotorRepository.configure() in main.py.
    AggregateState fields are stored at the document root level.

    Note: Standard CRUD operations (get_async, add_async, update_async, remove_async)
    are inherited from MotorRepository. Only domain-specific query methods are
    implemented here.
    """

    async def get_by_tenant_async(self, tenant_id: str) -> list[KnowledgeNamespace]:
        """Retrieve namespaces for a specific tenant.

        Uses native MongoDB filter. The Neuroglia MotorRepository flattens
        the AggregateState fields to the document root, so we query owner_tenant_id
        directly (not state.owner_tenant_id).

        Args:
            tenant_id: The tenant to filter by

        Returns:
            List of namespaces belonging to the tenant
        """
        cursor = self.collection.find({"owner_tenant_id": tenant_id}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_public_async(self) -> list[KnowledgeNamespace]:
        """Retrieve all public namespaces.

        Returns:
            List of public namespaces
        """
        cursor = self.collection.find({"access_level": "public", "is_deleted": False}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
