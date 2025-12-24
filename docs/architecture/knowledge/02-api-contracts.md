# Knowledge Manager - API Contracts

## Base URL

```
/api/v1/knowledge
```

## Authentication

All endpoints require JWT Bearer token with `knowledge:read` or `knowledge:write` scopes.

---

## Namespace Endpoints

### List Namespaces

```
GET /namespaces
```

Query params: `tenant_id`, `include_public`, `limit`, `offset`

### Get Namespace

```
GET /namespaces/{namespace_id}
```

### Create Namespace

```
POST /namespaces
Body: { name, description, icon?, is_public?, allowed_tenant_ids? }
```

### Update Namespace

```
PATCH /namespaces/{namespace_id}
Body: { name?, description?, icon?, is_public?, allowed_tenant_ids? }
```

### Delete Namespace

```
DELETE /namespaces/{namespace_id}
```

---

## Term Endpoints

### List Terms

```
GET /namespaces/{namespace_id}/terms
```

Query params: `search`, `limit`, `offset`

### Add Term

```
POST /namespaces/{namespace_id}/terms
Body: { term, definition, aliases?, examples?, context_hint? }
```

### Update Term

```
PATCH /namespaces/{namespace_id}/terms/{term_id}
```

### Remove Term

```
DELETE /namespaces/{namespace_id}/terms/{term_id}
```

---

## Relationship Endpoints

### List Relationships

```
GET /namespaces/{namespace_id}/relationships
```

### Add Relationship

```
POST /namespaces/{namespace_id}/relationships
Body: { source_term_id, target_term_id, relationship_type, description?, bidirectional?, weight? }
```

### Remove Relationship

```
DELETE /namespaces/{namespace_id}/relationships/{relationship_id}
```

---

## Rule Endpoints

### List Rules

```
GET /namespaces/{namespace_id}/rules
```

### Add Rule

```
POST /namespaces/{namespace_id}/rules
Body: { name, condition, rule_text, applies_to_term_ids, priority? }
```

### Update/Remove Rule

```
PATCH /namespaces/{namespace_id}/rules/{rule_id}
DELETE /namespaces/{namespace_id}/rules/{rule_id}
```

---

## Context Expansion Endpoint

Primary endpoint for agent-host integration:

```
POST /context/expand
Body: {
  text: string,              // User query
  namespace_ids: string[],   // Namespaces to search
  max_terms: int,            // Default: 5
  include_rules: bool,       // Default: true
  include_related: bool,     // Default: true
  related_depth: int         // Default: 1
}

Response: {
  matched_terms: TermMatch[],
  applicable_rules: Rule[],
  related_terms: TermMatch[],
  context_block: string      // Ready-to-inject text
}
```

---

## Graph Analytics Endpoints

### Traverse Graph

```
POST /graph/traverse
Body: { term_id, relationship_types?, direction?, max_depth? }
```

### Get Communities

```
GET /graph/communities?namespace_id={id}
```

### Community Summary

```
GET /graph/communities/{community_id}/summary
```

---

## Vector Search Endpoint

```
POST /search/semantic
Body: {
  query: string,
  namespace_ids: string[],
  limit: int,
  min_score: float
}
```

---

_Next: [03-integration.md](03-integration.md) - Agent-Host Integration_
