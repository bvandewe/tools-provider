# Orchestrator Refactoring Recommendation

## Implementation Progress ✅

| Phase | Description | Status | Tests |
|-------|-------------|--------|-------|
| Phase 1 | Extract Data Classes | ✅ Complete | Passing |
| Phase 2 | Extract Protocol Senders | ✅ Complete | Passing |
| Phase 3 | Extract Handlers | ✅ Complete | Passing |
| Phase 4 | Extract Template Processing | ✅ Complete | Passing |
| Phase 5 | Extract Agent Execution | ✅ Complete | Passing |

**Total Tests: 305** (as of 2024-12-21)

### Created Package Structure

```
application/orchestrator/
├── __init__.py              # Package exports
├── context.py               # ConversationContext, ItemExecutionState, OrchestratorState
├── handlers/
│   ├── message_handler.py   # User text message handling
│   ├── widget_handler.py    # Widget response handling
│   ├── flow_handler.py      # Flow control (start/pause/cancel)
│   └── model_handler.py     # LLM model selection
├── template/
│   ├── jinja_renderer.py    # Jinja2 variable substitution
│   ├── content_generator.py # LLM-based content generation
│   ├── item_presenter.py    # Item presentation to clients
│   └── flow_runner.py       # Proactive flow execution
├── agent/
│   ├── agent_runner.py      # Agent invocation and event handling
│   ├── tool_executor.py     # Tool execution via ToolProviderClient
│   └── stream_handler.py    # Content streaming to clients
└── protocol/
    ├── config_sender.py     # Configuration and flow control
    ├── widget_sender.py     # Widget rendering
    └── content_sender.py    # Content streaming
```

---

## Current State Analysis

The `ConversationOrchestrator` class (~1900 lines) has grown into a **God Object** that handles too many responsibilities:

1. **Conversation Lifecycle Management** - Initialize, cleanup, state machine
2. **Agent Execution** - Building context, running agent streams, handling events
3. **Template Processing** - Loading items, rendering content, tracking progress
4. **LLM Integration** - Jinja templating, content generation
5. **Protocol Message Sending** - Config, chat input, errors, widgets
6. **Domain Command Dispatch** - Recording responses, advancing templates
7. **Tool Management** - Loading tools, executing tools
8. **Flow Control** - Start, pause, cancel, resume

## Proposed Architecture

### Option A: Modular Package (Recommended)

Promote the orchestrator to its own top-level package with focused modules:

```
application/
├── orchestrator/                    # New top-level package
│   ├── __init__.py                  # Export main Orchestrator class
│   ├── orchestrator.py              # Main coordinator (~200 lines)
│   ├── context.py                   # ConversationContext, ItemExecutionState
│   ├── state_machine.py             # OrchestratorState enum, transitions
│   │
│   ├── handlers/                    # Event/Message handlers
│   │   ├── __init__.py
│   │   ├── message_handler.py       # handle_user_message()
│   │   ├── widget_handler.py        # handle_widget_response()
│   │   ├── flow_handler.py          # handle_flow_start/pause/cancel()
│   │   └── model_handler.py         # handle_model_change()
│   │
│   ├── template/                    # Template processing
│   │   ├── __init__.py
│   │   ├── item_presenter.py        # _present_item(), _render_item_content()
│   │   ├── content_generator.py     # _get_content_stem(), _generate_with_llm()
│   │   ├── jinja_renderer.py        # _render_jinja_template()
│   │   └── template_persistence.py  # _persist_item_response()
│   │
│   ├── agent/                       # Agent execution
│   │   ├── __init__.py
│   │   ├── agent_runner.py          # _run_agent_stream(), _build_agent_context()
│   │   ├── tool_executor.py         # Tool execution, MCP client integration
│   │   └── stream_handler.py        # Event streaming, message completion
│   │
│   └── protocol/                    # Protocol message senders
│       ├── __init__.py
│       ├── config_sender.py         # _send_conversation_config()
│       ├── widget_sender.py         # _send_widget_render(), _send_confirmation_widget()
│       ├── chat_sender.py           # _send_chat_input_enabled(), _stream_agent_response()
│       └── error_sender.py          # _send_error()
│
├── websocket/                       # Stays focused on WebSocket transport
│   ├── manager.py                   # Connection lifecycle only
│   ├── connection.py                # Connection dataclass
│   └── handler.py                   # WebSocket message routing
```

### Class Responsibilities After Refactoring

#### 1. `Orchestrator` (Main Coordinator) - ~200 lines

```python
class Orchestrator:
    """Thin coordinator that delegates to specialized handlers."""

    def __init__(
        self,
        mediator: Mediator,
        connection_manager: ConnectionManager,
        message_handler: MessageHandler,
        widget_handler: WidgetHandler,
        flow_handler: FlowHandler,
        agent_runner: AgentRunner,
        item_presenter: ItemPresenter,
    ):
        ...

    async def initialize(self, connection, conversation_id) -> None:
        # Delegates to context builder

    async def handle_user_message(self, connection, content) -> None:
        # Delegates to message_handler

    async def handle_widget_response(self, connection, ...) -> None:
        # Delegates to widget_handler
```

#### 2. `WidgetHandler` - ~150 lines

```python
class WidgetHandler:
    """Handles widget responses and confirmation flows."""

    def __init__(self, mediator, widget_sender, template_persistence):
        ...

    async def handle_response(self, context, widget_id, item_id, value):
        # Track response
        # Check completion
        # Persist if complete
```

#### 3. `ItemPresenter` - ~200 lines

```python
class ItemPresenter:
    """Presents template items to the client."""

    def __init__(self, mediator, content_generator, widget_sender):
        ...

    async def present_item(self, connection, context, item_index):
        # Load item via query
        # Render each content
        # Send widgets
```

#### 4. `ContentGenerator` - ~150 lines

```python
class ContentGenerator:
    """Generates templated content via LLM."""

    def __init__(self, llm_provider_factory, jinja_renderer):
        ...

    async def get_content_stem(self, context, content, item):
        # Static: apply Jinja
        # Templated: generate via LLM
```

#### 5. `AgentRunner` - ~250 lines

```python
class AgentRunner:
    """Runs agent execution and streams responses."""

    def __init__(self, agent, llm_provider_factory, tool_executor):
        ...

    async def run_stream(self, connection, context, message):
        # Build agent context
        # Execute agent
        # Handle events
```

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Lines per file | ~1900 | 150-250 |
| Testability | Hard (many mocks) | Easy (isolated units) |
| Cognitive Load | High | Low (single responsibility) |
| Reusability | None | Components can be reused |
| Onboarding | Difficult | Clear entry points |
| Debugging | Hard to trace | Clear call hierarchy |

## Migration Strategy

### Phase 1: Extract Data Classes (Low Risk)

1. Move `ConversationContext` to `orchestrator/context.py`
2. Move `ItemExecutionState` to `orchestrator/context.py`
3. Move `OrchestratorState` to `orchestrator/state_machine.py`
4. Update imports in orchestrator.py

### Phase 2: Extract Protocol Senders (Medium Risk)

1. Create `orchestrator/protocol/` package
2. Extract `_send_*` methods to specialized sender classes
3. Inject senders into orchestrator
4. Run tests after each extraction

### Phase 3: Extract Handlers (Medium Risk)

1. Create `orchestrator/handlers/` package
2. Extract `handle_*` methods one by one
3. Keep original methods as thin wrappers initially
4. Remove wrappers after validation

### Phase 4: Extract Template Processing (Higher Risk)

1. Create `orchestrator/template/` package
2. Extract item presentation logic
3. Extract content generation
4. Extract Jinja rendering

### Phase 5: Extract Agent Execution (Higher Risk)

1. Create `orchestrator/agent/` package
2. Extract agent running logic
3. Extract tool execution
4. Extract stream handling

## Dependency Injection

After refactoring, the orchestrator should be assembled via DI:

```python
# In main.py or a factory
def create_orchestrator(
    mediator: Mediator,
    connection_manager: ConnectionManager,
    llm_provider_factory: LlmProviderFactory,
    agent: Agent,
    tool_provider_client: ToolProviderClient,
) -> Orchestrator:

    # Build leaf dependencies first
    jinja_renderer = JinjaRenderer()

    # Build protocol senders
    widget_sender = WidgetSender(connection_manager)
    config_sender = ConfigSender(connection_manager)
    error_sender = ErrorSender(connection_manager)

    # Build content generator
    content_generator = ContentGenerator(llm_provider_factory, jinja_renderer)

    # Build template services
    template_persistence = TemplatePersistence(mediator)
    item_presenter = ItemPresenter(mediator, content_generator, widget_sender)

    # Build handlers
    widget_handler = WidgetHandler(mediator, widget_sender, template_persistence, item_presenter)
    message_handler = MessageHandler(mediator, agent_runner)
    flow_handler = FlowHandler(item_presenter)

    # Assemble orchestrator
    return Orchestrator(
        mediator=mediator,
        connection_manager=connection_manager,
        message_handler=message_handler,
        widget_handler=widget_handler,
        flow_handler=flow_handler,
        item_presenter=item_presenter,
    )
```

## Location Recommendation

**Promote to `application/orchestrator/`** rather than keeping in `websocket/`:

### Reasons

1. **Single Responsibility**: `websocket/` should only handle WebSocket transport concerns
2. **Domain Alignment**: Orchestration is application logic, not transport logic
3. **Testability**: Easier to test orchestrator without WebSocket dependencies
4. **Reusability**: Orchestrator could potentially support other transports (HTTP SSE, etc.)

### The WebSocket Package Should

- Handle WebSocket connection lifecycle
- Parse/serialize WebSocket messages
- Route messages to the orchestrator
- **NOT** contain business logic

## Recommended File Structure

```
src/agent-host/
├── application/
│   ├── orchestrator/           # NEW: All orchestration logic
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main coordinator
│   │   ├── context.py          # Context + State dataclasses
│   │   ├── handlers/
│   │   ├── template/
│   │   ├── agent/
│   │   └── protocol/
│   │
│   ├── websocket/              # SLIM: Transport only
│   │   ├── __init__.py
│   │   ├── manager.py          # Connection lifecycle
│   │   ├── connection.py       # Connection dataclass
│   │   └── router.py           # Message routing to orchestrator
│   │
│   ├── agents/                 # Existing: Agent implementations
│   ├── commands/               # Existing: CQRS commands
│   ├── queries/                # Existing: CQRS queries
│   └── protocol/               # Existing: Message types
```

## Conclusion

The refactoring will:

1. **Reduce file sizes** from ~1900 to 150-250 lines each
2. **Improve testability** with isolated, mockable components
3. **Clarify architecture** with clear separation of concerns
4. **Enable parallel development** on different components
5. **Simplify debugging** with traceable call hierarchies

The migration can be done incrementally, starting with low-risk extractions (data classes) and progressing to higher-risk ones (agent execution).
