# Knowledge Manager - Graph Analytics

## Neo4j Schema

### Nodes

```cypher
(:Term {
  id: string,
  namespace_id: string,
  term: string,
  definition: string,
  aliases: string[],
  context_hint: string,
  created_at: datetime
})

(:Namespace {
  id: string,
  name: string,
  tenant_id: string
})

(:Community {
  id: string,
  namespace_id: string,
  name: string,
  summary: string,
  algorithm: string
})
```

### Relationships

```cypher
(:Term)-[:CONTAINS]->(:Term)
(:Term)-[:REFERENCES]->(:Term)
(:Term)-[:IS_INSTANCE_OF]->(:Term)
(:Term)-[:PARENT_OF]->(:Term)
(:Term)-[:DEPENDS_ON]->(:Term)
(:Term)-[:RELATED_TO]->(:Term)
(:Term)-[:BELONGS_TO]->(:Namespace)
(:Term)-[:MEMBER_OF]->(:Community)
```

## Community Detection

Using Louvain algorithm via Neo4j Graph Data Science:

```cypher
CALL gds.louvain.stream('knowledge-graph', {
  nodeLabels: ['Term'],
  relationshipTypes: ['REFERENCES', 'CONTAINS', 'RELATED_TO']
})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).term AS term, communityId
ORDER BY communityId
```

## Community Summarization

After detection, generate summaries using LLM:

```python
async def summarize_community(self, community_id: str) -> str:
    terms = await self._get_community_terms(community_id)

    prompt = f"""Summarize these related domain concepts in 2-3 sentences:
    {[t.term + ': ' + t.definition for t in terms]}"""

    return await self._llm.complete(prompt)
```

## Graph Queries

### Traverse Relationships

```cypher
MATCH (t:Term {id: $term_id})-[r]->(related:Term)
WHERE type(r) IN $relationship_types
RETURN related, type(r) as rel_type, r.weight as weight
```

### Find Paths

```cypher
MATCH path = shortestPath(
  (source:Term {id: $source_id})-[*..5]-(target:Term {id: $target_id})
)
RETURN path
```

### Get Term Context

```cypher
MATCH (t:Term {id: $term_id})
OPTIONAL MATCH (t)-[r]->(related:Term)
OPTIONAL MATCH (t)<-[incoming]-(referencing:Term)
RETURN t, collect(DISTINCT related) as outgoing,
       collect(DISTINCT referencing) as incoming
```

---

_Next: [06-vector-embeddings.md](06-vector-embeddings.md) - Vector Embeddings_
