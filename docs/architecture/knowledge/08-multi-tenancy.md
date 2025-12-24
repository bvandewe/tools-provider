# Knowledge Manager - Multi-Tenancy

## Tenancy Model

Namespaces support flexible sharing across tenants/deployments:

| Mode | Description |
|------|-------------|
| Private | Owner tenant only |
| Shared | Explicit allow-list of tenants |
| Public | All tenants can access |

## Namespace Ownership

```python
class KnowledgeNamespaceState:
    owner_tenant_id: str | None   # None = global/system
    owner_user_id: str | None     # Creator
    is_public: bool               # Available to all
    allowed_tenant_ids: list[str] # Explicit access list
```

## Access Resolution

```python
def can_access(namespace: KnowledgeNamespace, tenant_id: str) -> bool:
    if namespace.state.is_public:
        return True
    if namespace.state.owner_tenant_id == tenant_id:
        return True
    if tenant_id in namespace.state.allowed_tenant_ids:
        return True
    return False
```

## Query Filtering

All queries include tenant context:

```python
async def get_namespaces_for_tenant(self, tenant_id: str) -> list[Namespace]:
    return await self._collection.find({
        "$or": [
            {"is_public": True},
            {"owner_tenant_id": tenant_id},
            {"allowed_tenant_ids": tenant_id},
        ]
    })
```

## Cross-Deployment Sharing

For sharing namespaces between deployments:

1. **Export** namespace as JSON/YAML package
2. **Import** into target deployment with new tenant assignment
3. Optionally maintain **sync** via event bridge

```python
# Export format
{
    "namespace": { "name": "...", "description": "..." },
    "terms": [...],
    "relationships": [...],
    "rules": [...],
    "metadata": {
        "exported_at": "...",
        "source_deployment": "...",
        "revision": 5
    }
}
```

## Tenant Isolation

- EventStoreDB: Streams prefixed with tenant ID
- MongoDB: Compound index on `tenant_id`
- Neo4j: Property-based filtering
- Qdrant: Namespace ID in payload filter

---

_Next: [09-import-export.md](09-import-export.md) - Import/Export_
