# Knowledge Manager - Import/Export

## Export Formats

### JSON Package (Primary)

```json
{
  "version": "1.0",
  "exported_at": "2025-12-23T10:00:00Z",
  "namespace": {
    "id": "assessments",
    "name": "Assessment Domain",
    "description": "Core assessment terminology"
  },
  "terms": [
    {
      "id": "term-001",
      "term": "ExamBlueprint",
      "definition": "A structured definition...",
      "aliases": ["blueprint", "exam blueprint"],
      "examples": ["CCNA Blueprint"],
      "context_hint": "When discussing exam structure"
    }
  ],
  "relationships": [
    {
      "source": "term-001",
      "target": "term-002",
      "type": "contains",
      "description": "Blueprint contains domains"
    }
  ],
  "rules": [
    {
      "name": "Blueprint Completeness",
      "condition": "When creating blueprints",
      "rule_text": "Must have at least one domain",
      "applies_to": ["term-001"]
    }
  ]
}
```

### YAML Alternative

```yaml
version: "1.0"
namespace:
  id: assessments
  name: Assessment Domain

terms:
  - term: ExamBlueprint
    definition: A structured definition...
    aliases: [blueprint, exam blueprint]
```

## API Endpoints

### Export

```
GET /namespaces/{id}/export
Query: format=json|yaml, revision=N (optional)
Response: File download
```

### Import

```
POST /namespaces/import
Body: multipart/form-data with file
Query: mode=create|merge|replace
Response: { namespace_id, imported_terms: 25, imported_relationships: 10 }
```

### Validate Before Import

```
POST /namespaces/import/validate
Body: multipart/form-data with file
Response: { valid: true, warnings: [], errors: [] }
```

## Import Modes

| Mode | Behavior |
|------|----------|
| `create` | Fail if namespace exists |
| `merge` | Add new items, skip existing |
| `replace` | Delete existing, import fresh |

## Seed Data

For initial deployment, seed from files:

```python
# scripts/seed_knowledge.py

async def seed_from_directory(path: str):
    for file in Path(path).glob("*.yaml"):
        data = yaml.safe_load(file.read_text())
        await import_namespace(data, mode="merge")
```

Seed data location:

```
knowledge-manager/
  seeds/
    assessments.yaml
    networking.yaml
    security.yaml
```

## Migration Support

Export includes revision metadata for incremental sync:

```json
{
  "metadata": {
    "source_revision": 5,
    "source_deployment": "prod-us-east"
  }
}
```

---

_Next: [10-implementation-plan.md](10-implementation-plan.md) - Implementation Roadmap_
