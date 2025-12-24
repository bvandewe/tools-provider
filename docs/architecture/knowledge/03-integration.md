# Knowledge Manager - Agent-Host Integration

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       agent-host                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────┐  │
│  │ User Query  │───▶│ Context Expander │───▶│ ReActAgent │  │
│  └─────────────┘    └────────┬─────────┘    └────────────┘  │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │ HTTP
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    knowledge-manager                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              POST /context/expand                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Context Expander Service (agent-host side)

```python
# application/services/context_expander.py

class ContextExpanderService:
    """Intercepts user queries and expands with domain knowledge."""

    def __init__(self, knowledge_client: KnowledgeManagerClient):
        self._client = knowledge_client

    async def expand(
        self,
        user_text: str,
        namespace_ids: list[str],
        mode: str = "auto",  # "auto", "always", "keywords_only"
    ) -> ExpandedContext:
        """Expand user query with relevant domain context."""

        result = await self._client.expand_context(
            text=user_text,
            namespace_ids=namespace_ids,
            max_terms=5,
            include_rules=True,
            include_related=True,
        )

        return ExpandedContext(
            original_text=user_text,
            context_block=result.context_block,
            matched_term_count=len(result.matched_terms),
        )
```

## Integration in Agent Runner

```python
# application/orchestrator/agent/agent_runner.py

async def run_stream(self, ...):
    # 1. Get agent definition
    agent_def = await self._get_agent_definition(...)

    # 2. Expand context if namespaces configured
    if agent_def.knowledge_namespace_ids:
        expanded = await self._context_expander.expand(
            user_text=message,
            namespace_ids=agent_def.knowledge_namespace_ids,
        )
        context_block = expanded.context_block
    else:
        context_block = None

    # 3. Build system message with context
    system_msg = self._build_system_message(
        agent_def.system_prompt,
        context_block=context_block,
    )

    # 4. Run agent
    ...
```

## AgentDefinition Schema Changes

Add to `AgentDefinitionState`:

```python
# New fields
knowledge_namespace_ids: list[str]  # Namespaces to query
context_expansion_mode: str  # "auto" | "always" | "disabled"
```

## HTTP Client

```python
# infrastructure/clients/knowledge_manager_client.py

class KnowledgeManagerClient:
    """HTTP client for knowledge-manager service."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self._base_url = base_url
        self._timeout = timeout

    async def expand_context(self, **params) -> ContextExpansionResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/v1/knowledge/context/expand",
                json=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return ContextExpansionResponse(**response.json())
```

## Configuration

```python
# application/settings.py (agent-host)

KNOWLEDGE_MANAGER_URL: str = "http://knowledge-manager:8002"
KNOWLEDGE_MANAGER_TIMEOUT: float = 5.0
CONTEXT_EXPANSION_ENABLED: bool = True
```

---

_Next: [04-context-expander.md](04-context-expander.md) - Context Expander Details_
