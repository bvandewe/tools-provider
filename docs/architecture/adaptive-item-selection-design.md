# Adaptive Item Selection Architecture Design

**Version:** 1.0.0
**Status:** `DRAFT`
**Date:** December 23, 2025
**Application:** agent-host (primary), item-selector (new service)
**Related:** [Blueprint-Driven Evaluation System](../specs/blueprint-evaluation-design.md), [Agent Aggregate Design](agent-aggregate-design.md)

---

## 1. Executive Summary

This document defines the architecture for **Adaptive Item Selection** - a flexible system that separates the "next item selection" logic from the conversation advancement process. This enables:

- **Sequential Conversations**: Current behavior - items presented in fixed order (in-process strategy)
- **Adaptive Conversations**: Items selected dynamically based on learner proficiency, statistical models, and external analytical engines
- **Hybrid Conversations**: Mix of fixed and adaptive items within the same template
- **External Engine Integration**: Dedicated microservice for CAT/IRT-based selection with CloudEvents support

### Key Design Decisions

1. **Strategy Pattern**: Selection logic abstracted behind `ItemSelectionStrategy` interface
2. **External Service for Adaptive**: New `item-selector` microservice (REST + CloudEvents), similar to `tools-provider`
3. **Template as Orchestrator**: `ConversationTemplate` references external blueprints but retains control of fixed items and adaptive slot positioning
4. **Engine Controls Termination**: In adaptive mode, the external engine signals conversation completion
5. **No Fallback**: If external engine unavailable in adaptive mode, conversation fails (assessment integrity)

---

## 2. Problem Statement

### 2.1 Current Architecture Limitations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT: Sequential-Only Flow                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ConversationTemplate                                                        │
│  ├── items: [Item0, Item1, Item2, Item3, Item4]  ← Fixed list               │
│  └── shuffle_items: bool                          ← Only randomization       │
│                                                                              │
│  FlowRunner._present_item_at_index()                                         │
│  └── next_index = context.current_item_index + 1  ← HARDCODED +1            │
│                                                                              │
│  Problems:                                                                   │
│  ✗ Cannot select items based on learner performance                         │
│  ✗ Cannot integrate external CAT/IRT engines                                │
│  ✗ Cannot mix fixed and dynamic items                                       │
│  ✗ No hook for proficiency-based termination                                │
│  ✗ Template must contain ALL items upfront                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Target Use Cases

| Use Case | Selection Mode | Termination | Item Source |
|----------|----------------|-------------|-------------|
| Widget Showcase | Sequential | Fixed count | Template.items |
| Practice Quiz | Sequential | Fixed count | Template.items |
| Adaptive Assessment | Adaptive | Engine signal | ExamBlueprint via item-selector |
| Certification Exam | Adaptive | Engine signal OR time limit | ExamBlueprint via item-selector |
| Hybrid Tutorial | Hybrid | Fixed count | Template.items + ExamBlueprint |

---

## 3. Target Architecture

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TARGET: Pluggable Item Selection                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         agent-host                                   │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐    ┌───────────────────────────────────────┐  │    │
│  │  │  FlowRunner      │───▶│  ItemSelectionStrategy (interface)    │  │    │
│  │  │                  │    │                                       │  │    │
│  │  │  - advance()     │    │  + select_next() → SelectionResult    │  │    │
│  │  │  - present()     │    │  + should_terminate() → bool          │  │    │
│  │  │  - complete()    │    │  + record_response() → void           │  │    │
│  │  └──────────────────┘    └───────────────────────────────────────┘  │    │
│  │                                       │                              │    │
│  │           ┌───────────────────────────┼───────────────────────┐     │    │
│  │           │                           │                       │     │    │
│  │           ▼                           ▼                       ▼     │    │
│  │  ┌────────────────┐        ┌────────────────┐      ┌─────────────┐ │    │
│  │  │ Sequential     │        │ Adaptive       │      │ Hybrid      │ │    │
│  │  │ Strategy       │        │ Strategy       │      │ Strategy    │ │    │
│  │  │ (in-process)   │        │ (HTTP client)  │      │ (composite) │ │    │
│  │  └────────────────┘        └───────┬────────┘      └─────────────┘ │    │
│  │                                    │                               │    │
│  └────────────────────────────────────┼───────────────────────────────┘    │
│                                       │                                     │
│                      ─────────────────┼─────────────────                   │
│                      HTTP/CloudEvents │                                     │
│                      ─────────────────┼─────────────────                   │
│                                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     item-selector (NEW SERVICE)                      │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐    ┌───────────────────┐    ┌──────────────┐  │    │
│  │  │  Selection API   │    │  CAT/IRT Engine   │    │  Event Bus   │  │    │
│  │  │  (REST)          │    │                   │    │  (CloudEvts) │  │    │
│  │  │                  │    │  - Proficiency    │    │              │  │    │
│  │  │  POST /select    │    │  - Item selection │    │  ItemGraded  │  │    │
│  │  │  POST /grade     │    │  - Termination    │    │  Terminate   │  │    │
│  │  │  GET /profile    │    │                   │    │  ProfileUpd  │  │    │
│  │  └──────────────────┘    └───────────────────┘    └──────────────┘  │    │
│  │                                    │                                │    │
│  │                                    ▼                                │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │              ExamBlueprint Store (MongoDB)                   │   │    │
│  │  │                                                              │   │    │
│  │  │  - ExamBlueprint definitions                                 │   │    │
│  │  │  - SkillTemplate references                                  │   │    │
│  │  │  - Item generation parameters                                │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Responsibilities

| Service | Responsibility | Communication |
|---------|---------------|---------------|
| **agent-host** | Conversation orchestration, widget rendering, user interaction | WebSocket to browser, HTTP to item-selector |
| **item-selector** | Adaptive selection, proficiency tracking, CAT/IRT algorithms, termination decisions | REST API + CloudEvents |
| **tools-provider** | MCP tool management (unchanged) | REST API |

---

## 4. Domain Model Changes

### 4.1 New Enums

```python
# domain/enums/item_selection.py

class ItemSelectionMode(str, Enum):
    """How items are selected for presentation."""
    
    SEQUENTIAL = "sequential"      # Fixed order from template.items
    ADAPTIVE = "adaptive"          # External engine selects items
    HYBRID = "hybrid"              # Mix of fixed and adaptive

class AdaptiveSlotType(str, Enum):
    """Types of adaptive slots in hybrid templates."""
    
    SINGLE = "single"              # One adaptive item
    BLOCK = "block"                # Multiple adaptive items until engine signals
    UNLIMITED = "unlimited"        # Continue until engine terminates
```

### 4.2 ConversationTemplate Extensions

```python
# Additions to ConversationTemplateState

class ConversationTemplateState(AggregateState[str]):
    """Extended state with selection configuration."""
    
    # Existing fields...
    
    # NEW: Item Selection Configuration
    item_selection_mode: ItemSelectionMode = ItemSelectionMode.SEQUENTIAL
    
    # NEW: Adaptive Configuration (only used when mode != SEQUENTIAL)
    adaptive_config: AdaptiveConfig | None = None


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive item selection."""
    
    # External Service
    item_selector_url: str                    # Base URL of item-selector service
    exam_blueprint_id: str                    # ExamBlueprint to use for item generation
    
    # Termination
    engine_controls_termination: bool = True  # If True, engine decides when to stop
    max_items: int | None = None              # Hard cap (optional, engine may stop earlier)
    time_limit_seconds: int | None = None     # Absolute time limit (whichever comes first)
    
    # Proficiency Thresholds
    target_proficiency: float | None = None   # Optional target (e.g., 0.8 = 80% mastery)
    min_items_before_termination: int = 3     # Minimum items before engine can terminate
    
    # Retry/Resilience
    request_timeout_seconds: int = 30
    # NOTE: No fallback - if engine unavailable, conversation fails
```

### 4.3 Hybrid Template Structure

For templates mixing fixed and adaptive items:

```python
@dataclass
class ConversationItem:
    """Extended to support adaptive slots."""
    
    # Existing fields...
    
    # NEW: Adaptive Slot Configuration
    is_adaptive_slot: bool = False                    # If True, this is a placeholder for adaptive items
    adaptive_slot_type: AdaptiveSlotType | None = None  # SINGLE, BLOCK, or UNLIMITED
    adaptive_slot_id: str | None = None               # Unique ID for tracking slot in hybrid mode
```

### 4.4 Example Template Configurations

#### Sequential (Current Behavior)
```yaml
id: "widget-showcase"
item_selection_mode: "sequential"
items:
  - id: "item-1"
    order: 1
    contents: [...]
  - id: "item-2"
    order: 2
    contents: [...]
```

#### Fully Adaptive
```yaml
id: "adaptive-assessment"
item_selection_mode: "adaptive"
adaptive_config:
  item_selector_url: "http://item-selector:8002"
  exam_blueprint_id: "math-fundamentals-l1"
  engine_controls_termination: true
  time_limit_seconds: 3600  # 1 hour max
  min_items_before_termination: 5
items: []  # Empty - all items from engine
```

#### Hybrid (Fixed + Adaptive)
```yaml
id: "hybrid-tutorial"
item_selection_mode: "hybrid"
adaptive_config:
  item_selector_url: "http://item-selector:8002"
  exam_blueprint_id: "networking-basics"
items:
  - id: "intro"
    order: 1
    contents:
      - widget_type: "text_display"
        stem: "Welcome to the networking tutorial..."
  
  - id: "adaptive-block-1"
    order: 2
    is_adaptive_slot: true
    adaptive_slot_type: "block"  # Multiple items until engine signals "next_slot"
    adaptive_slot_id: "basic-concepts"
  
  - id: "midpoint-checkpoint"
    order: 3
    contents:
      - widget_type: "text_display"
        stem: "Great progress! Let's continue..."
  
  - id: "adaptive-block-2"
    order: 4
    is_adaptive_slot: true
    adaptive_slot_type: "unlimited"  # Continue until engine terminates
    adaptive_slot_id: "advanced-topics"
```

---

## 5. ItemSelectionStrategy Interface

### 5.1 Core Interface

```python
# application/strategies/item_selection.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from domain.models.conversation_item import ConversationItem


@dataclass
class SelectionResult:
    """Result of item selection."""
    
    item: ConversationItem | None      # The selected item (None if terminating)
    should_terminate: bool             # True if conversation should end
    termination_reason: str | None     # "proficiency_reached", "max_items", "time_limit", "engine_signal"
    metadata: dict[str, Any] | None    # Engine-specific data (proficiency estimate, etc.)


@dataclass
class ResponseRecord:
    """Record of user's response to an item."""
    
    item_id: str
    widget_responses: dict[str, Any]   # widget_id -> response value
    response_time_ms: int
    is_correct: bool | None            # None if not scored yet
    score: float | None
    max_score: float | None


class ItemSelectionStrategy(ABC):
    """Abstract strategy for item selection."""
    
    @abstractmethod
    async def initialize(
        self,
        context: "ConversationContext",
        template_config: dict[str, Any],
    ) -> None:
        """Initialize the strategy for a conversation session.
        
        Called once when conversation starts.
        """
        pass
    
    @abstractmethod
    async def select_next(
        self,
        context: "ConversationContext",
    ) -> SelectionResult:
        """Select the next item to present.
        
        Returns:
            SelectionResult with the next item or termination signal
        """
        pass
    
    @abstractmethod
    async def record_response(
        self,
        context: "ConversationContext",
        response: ResponseRecord,
    ) -> None:
        """Record user's response for proficiency tracking.
        
        Called after each item is completed.
        """
        pass
    
    @abstractmethod
    async def should_terminate(
        self,
        context: "ConversationContext",
    ) -> tuple[bool, str | None]:
        """Check if conversation should terminate.
        
        Returns:
            (should_terminate, reason)
        """
        pass
    
    @abstractmethod
    async def get_progress(
        self,
        context: "ConversationContext",
    ) -> dict[str, Any]:
        """Get current progress information.
        
        Returns dict with:
            - items_completed: int
            - total_items: int | None (None if adaptive)
            - proficiency_estimate: float | None
            - time_elapsed_seconds: int
        """
        pass
```

### 5.2 Sequential Strategy (In-Process)

```python
# application/strategies/sequential_strategy.py

class SequentialSelectionStrategy(ItemSelectionStrategy):
    """In-process strategy for fixed-order item selection.
    
    This is the current behavior, refactored into strategy pattern.
    Items are presented in template.items order (or shuffled if configured).
    """
    
    def __init__(self, mediator: Mediator):
        self._mediator = mediator
        self._items: list[ConversationItem] = []
        self._current_index: int = 0
        self._shuffle_order: list[int] | None = None
    
    async def initialize(
        self,
        context: ConversationContext,
        template_config: dict[str, Any],
    ) -> None:
        """Load items from template."""
        # Query template items via mediator
        result = await self._mediator.execute_async(
            GetTemplateItemsQuery(template_id=context.template_id)
        )
        self._items = result.data or []
        
        # Handle shuffle if configured
        if template_config.get("shuffle_items", False):
            import random
            self._shuffle_order = list(range(len(self._items)))
            random.shuffle(self._shuffle_order)
    
    async def select_next(
        self,
        context: ConversationContext,
    ) -> SelectionResult:
        """Return next item in sequence."""
        if self._current_index >= len(self._items):
            return SelectionResult(
                item=None,
                should_terminate=True,
                termination_reason="all_items_completed",
                metadata={"total_items": len(self._items)},
            )
        
        # Get item (with shuffle mapping if needed)
        actual_index = self._shuffle_order[self._current_index] if self._shuffle_order else self._current_index
        item = self._items[actual_index]
        self._current_index += 1
        
        return SelectionResult(
            item=item,
            should_terminate=False,
            termination_reason=None,
            metadata={"item_index": self._current_index, "total_items": len(self._items)},
        )
    
    async def record_response(
        self,
        context: ConversationContext,
        response: ResponseRecord,
    ) -> None:
        """No-op for sequential - responses persisted via existing commands."""
        pass
    
    async def should_terminate(
        self,
        context: ConversationContext,
    ) -> tuple[bool, str | None]:
        """Terminate when all items completed."""
        if self._current_index >= len(self._items):
            return (True, "all_items_completed")
        return (False, None)
    
    async def get_progress(
        self,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Return fixed progress info."""
        return {
            "items_completed": self._current_index,
            "total_items": len(self._items),
            "proficiency_estimate": None,  # Not tracked in sequential mode
            "time_elapsed_seconds": context.elapsed_seconds,
        }
```

### 5.3 Adaptive Strategy (External Service Client)

```python
# application/strategies/adaptive_strategy.py

class AdaptiveSelectionStrategy(ItemSelectionStrategy):
    """Strategy that delegates to external item-selector service.
    
    Communicates via REST API for synchronous operations and
    receives CloudEvents for asynchronous signals (e.g., termination).
    """
    
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        config: AdaptiveConfig,
    ):
        self._http_client = http_client
        self._config = config
        self._session_id: str | None = None
        self._terminated: bool = False
        self._termination_reason: str | None = None
    
    async def initialize(
        self,
        context: ConversationContext,
        template_config: dict[str, Any],
    ) -> None:
        """Initialize session with external engine."""
        try:
            response = await self._http_client.post(
                f"{self._config.item_selector_url}/sessions",
                json={
                    "conversation_id": context.conversation_id,
                    "user_id": context.user_id,
                    "exam_blueprint_id": self._config.exam_blueprint_id,
                    "config": {
                        "target_proficiency": self._config.target_proficiency,
                        "max_items": self._config.max_items,
                        "min_items_before_termination": self._config.min_items_before_termination,
                    },
                },
                timeout=self._config.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            self._session_id = data["session_id"]
            
        except Exception as e:
            # NO FALLBACK - fail the conversation
            raise ItemSelectorUnavailableError(
                f"Failed to initialize adaptive session: {e}"
            ) from e
    
    async def select_next(
        self,
        context: ConversationContext,
    ) -> SelectionResult:
        """Request next item from external engine."""
        if self._terminated:
            return SelectionResult(
                item=None,
                should_terminate=True,
                termination_reason=self._termination_reason,
                metadata=None,
            )
        
        try:
            response = await self._http_client.post(
                f"{self._config.item_selector_url}/sessions/{self._session_id}/select",
                json={
                    "conversation_id": context.conversation_id,
                    "items_completed": context.items_completed,
                    "elapsed_seconds": context.elapsed_seconds,
                },
                timeout=self._config.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for termination signal
            if data.get("terminate", False):
                self._terminated = True
                self._termination_reason = data.get("termination_reason", "engine_signal")
                return SelectionResult(
                    item=None,
                    should_terminate=True,
                    termination_reason=self._termination_reason,
                    metadata=data.get("metadata"),
                )
            
            # Parse item from response
            item = ConversationItem.from_dict(data["item"])
            
            return SelectionResult(
                item=item,
                should_terminate=False,
                termination_reason=None,
                metadata=data.get("metadata"),
            )
            
        except Exception as e:
            # NO FALLBACK - fail the conversation
            raise ItemSelectorUnavailableError(
                f"Failed to select next item: {e}"
            ) from e
    
    async def record_response(
        self,
        context: ConversationContext,
        response: ResponseRecord,
    ) -> None:
        """Send response to engine for proficiency update."""
        try:
            await self._http_client.post(
                f"{self._config.item_selector_url}/sessions/{self._session_id}/responses",
                json={
                    "item_id": response.item_id,
                    "widget_responses": response.widget_responses,
                    "response_time_ms": response.response_time_ms,
                    "is_correct": response.is_correct,
                    "score": response.score,
                    "max_score": response.max_score,
                },
                timeout=self._config.request_timeout_seconds,
            )
        except Exception as e:
            # Log but don't fail - response is already persisted locally
            logger.warning(f"Failed to record response with engine: {e}")
    
    async def should_terminate(
        self,
        context: ConversationContext,
    ) -> tuple[bool, str | None]:
        """Check termination conditions."""
        # Check local time limit first
        if self._config.time_limit_seconds:
            if context.elapsed_seconds >= self._config.time_limit_seconds:
                self._terminated = True
                self._termination_reason = "time_limit"
                return (True, "time_limit")
        
        # Check engine signal (set via CloudEvent or previous select call)
        if self._terminated:
            return (True, self._termination_reason)
        
        return (False, None)
    
    async def get_progress(
        self,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Query engine for progress info."""
        try:
            response = await self._http_client.get(
                f"{self._config.item_selector_url}/sessions/{self._session_id}/progress",
                timeout=self._config.request_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            # Return partial info if engine unavailable
            return {
                "items_completed": context.items_completed,
                "total_items": None,  # Unknown in adaptive mode
                "proficiency_estimate": None,
                "time_elapsed_seconds": context.elapsed_seconds,
            }
    
    # CloudEvent Handler (called by event bus subscriber)
    async def handle_termination_event(self, event_data: dict[str, Any]) -> None:
        """Handle termination signal from engine via CloudEvent."""
        if event_data.get("session_id") == self._session_id:
            self._terminated = True
            self._termination_reason = event_data.get("reason", "engine_signal")
```

---

## 6. FlowRunner Refactoring

### 6.1 Updated FlowRunner

```python
# application/orchestrator/template/flow_runner.py

class FlowRunner:
    """Runs template-driven conversation flows with pluggable selection."""
    
    def __init__(
        self,
        mediator: MediatorProtocol,
        item_presenter: ItemPresenterProtocol,
        strategy_factory: ItemSelectionStrategyFactory,  # NEW
        # ... existing callbacks
    ):
        self._mediator = mediator
        self._item_presenter = item_presenter
        self._strategy_factory = strategy_factory
        self._strategy: ItemSelectionStrategy | None = None
    
    async def run_proactive_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Run the proactive conversation flow with strategy-based selection."""
        
        # Initialize selection strategy based on template config
        self._strategy = await self._strategy_factory.create(
            mode=context.template_config.get("item_selection_mode", "sequential"),
            adaptive_config=context.template_config.get("adaptive_config"),
        )
        
        try:
            await self._strategy.initialize(context, context.template_config)
        except ItemSelectorUnavailableError as e:
            logger.error(f"Item selector unavailable: {e}")
            await self._send_error(connection, "ITEM_SELECTOR_UNAVAILABLE", str(e))
            context.state = OrchestratorState.ERROR
            return
        
        # Send introduction message
        intro_message = context.template_config.get("introduction_message")
        if intro_message:
            await self._send_and_persist_virtual_message(connection, context, intro_message)
        
        # Present first item
        await self._present_next_item(connection, context)
    
    async def _present_next_item(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Use strategy to select and present next item."""
        
        # Check termination first
        should_terminate, reason = await self._strategy.should_terminate(context)
        if should_terminate:
            await self.complete_flow(connection, context, reason)
            return
        
        # Select next item
        try:
            result = await self._strategy.select_next(context)
        except ItemSelectorUnavailableError as e:
            logger.error(f"Item selector unavailable during selection: {e}")
            await self._send_error(connection, "ITEM_SELECTOR_UNAVAILABLE", str(e))
            context.state = OrchestratorState.ERROR
            return
        
        if result.should_terminate:
            await self.complete_flow(connection, context, result.termination_reason)
            return
        
        # Update progress
        progress = await self._strategy.get_progress(context)
        if self._send_panel_header:
            await self._send_panel_header(
                connection,
                context,
                item_id=result.item.id,
                item_index=progress["items_completed"],
                item_title=result.item.title,
                total_items=progress.get("total_items"),  # May be None for adaptive
            )
        
        # Present the item
        await self._item_presenter.present_item(
            connection, context, result.item, progress["items_completed"]
        )
    
    async def advance_to_next_item(
        self,
        connection: "Connection",
        context: ConversationContext,
        response: ResponseRecord | None = None,
    ) -> None:
        """Advance to next item after recording response."""
        
        # Record response with strategy (for proficiency tracking)
        if response and self._strategy:
            await self._strategy.record_response(context, response)
        
        # Present next item (strategy handles selection)
        await self._present_next_item(connection, context)
    
    async def complete_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
        termination_reason: str | None = None,
    ) -> None:
        """Complete the flow with reason tracking."""
        
        # Get final progress from strategy
        progress = await self._strategy.get_progress(context) if self._strategy else {}
        
        # Generate score report if configured
        if context.template_config.get("display_final_score_report", False):
            await self._generate_score_report(connection, context)
        
        # Send completion message
        completion_message = context.template_config.get("completion_message")
        if completion_message:
            await self._send_and_persist_virtual_message(connection, context, completion_message)
        
        # Persist completion with reason
        await self._mediator.execute_async(
            CompleteConversationCommand(
                conversation_id=context.conversation_id,
                summary={
                    "termination_reason": termination_reason,
                    "items_completed": progress.get("items_completed"),
                    "proficiency_estimate": progress.get("proficiency_estimate"),
                },
                user_info={"sub": context.user_id},
            )
        )
        
        context.state = OrchestratorState.COMPLETED
```

### 6.2 Strategy Factory

```python
# application/strategies/strategy_factory.py

class ItemSelectionStrategyFactory:
    """Factory for creating item selection strategies."""
    
    def __init__(
        self,
        mediator: Mediator,
        http_client: httpx.AsyncClient,
    ):
        self._mediator = mediator
        self._http_client = http_client
    
    async def create(
        self,
        mode: str,
        adaptive_config: dict[str, Any] | None = None,
    ) -> ItemSelectionStrategy:
        """Create strategy based on mode."""
        
        if mode == ItemSelectionMode.SEQUENTIAL.value:
            return SequentialSelectionStrategy(self._mediator)
        
        elif mode == ItemSelectionMode.ADAPTIVE.value:
            if not adaptive_config:
                raise ValueError("adaptive_config required for ADAPTIVE mode")
            config = AdaptiveConfig(**adaptive_config)
            return AdaptiveSelectionStrategy(self._http_client, config)
        
        elif mode == ItemSelectionMode.HYBRID.value:
            if not adaptive_config:
                raise ValueError("adaptive_config required for HYBRID mode")
            config = AdaptiveConfig(**adaptive_config)
            return HybridSelectionStrategy(
                mediator=self._mediator,
                http_client=self._http_client,
                config=config,
            )
        
        else:
            raise ValueError(f"Unknown selection mode: {mode}")
```

---

## 7. item-selector Service API

### 7.1 REST Endpoints

```yaml
openapi: "3.0.3"
info:
  title: Item Selector Service API
  version: "1.0.0"
  description: Adaptive item selection and proficiency tracking service

paths:
  /sessions:
    post:
      summary: Initialize a new selection session
      requestBody:
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateSessionRequest"
      responses:
        "201":
          description: Session created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/CreateSessionResponse"
        "503":
          description: Engine unavailable

  /sessions/{session_id}/select:
    post:
      summary: Select next item for presentation
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/SelectNextRequest"
      responses:
        "200":
          description: Next item or termination signal
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SelectNextResponse"

  /sessions/{session_id}/responses:
    post:
      summary: Record user response for proficiency update
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/RecordResponseRequest"
      responses:
        "200":
          description: Response recorded

  /sessions/{session_id}/progress:
    get:
      summary: Get current session progress
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Progress information
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProgressResponse"

components:
  schemas:
    CreateSessionRequest:
      type: object
      required:
        - conversation_id
        - user_id
        - exam_blueprint_id
      properties:
        conversation_id:
          type: string
        user_id:
          type: string
        exam_blueprint_id:
          type: string
        config:
          type: object
          properties:
            target_proficiency:
              type: number
            max_items:
              type: integer
            min_items_before_termination:
              type: integer

    CreateSessionResponse:
      type: object
      properties:
        session_id:
          type: string
        exam_blueprint_name:
          type: string
        estimated_items:
          type: integer

    SelectNextRequest:
      type: object
      properties:
        conversation_id:
          type: string
        items_completed:
          type: integer
        elapsed_seconds:
          type: integer

    SelectNextResponse:
      type: object
      properties:
        terminate:
          type: boolean
        termination_reason:
          type: string
          enum: [proficiency_reached, max_items, min_items_threshold, engine_decision]
        item:
          $ref: "#/components/schemas/ConversationItem"
        metadata:
          type: object
          properties:
            proficiency_estimate:
              type: number
            confidence_interval:
              type: array
              items:
                type: number
            items_remaining_estimate:
              type: integer

    ConversationItem:
      type: object
      description: Full ConversationItem with ItemContent widgets
      properties:
        id:
          type: string
        order:
          type: integer
        title:
          type: string
        contents:
          type: array
          items:
            $ref: "#/components/schemas/ItemContent"

    ItemContent:
      type: object
      properties:
        id:
          type: string
        widget_type:
          type: string
        stem:
          type: string
        options:
          type: array
          items:
            type: string
        correct_answer:
          type: string
          description: Included for server-side scoring

    RecordResponseRequest:
      type: object
      properties:
        item_id:
          type: string
        widget_responses:
          type: object
        response_time_ms:
          type: integer
        is_correct:
          type: boolean
        score:
          type: number
        max_score:
          type: number

    ProgressResponse:
      type: object
      properties:
        items_completed:
          type: integer
        total_items:
          type: integer
          nullable: true
        proficiency_estimate:
          type: number
        confidence_interval:
          type: array
          items:
            type: number
        time_elapsed_seconds:
          type: integer
```

### 7.2 CloudEvents

```yaml
# Events emitted by item-selector

- type: "io.mozart.itemselector.session.terminated.v1"
  source: "/item-selector"
  subject: "{session_id}"
  data:
    session_id: string
    conversation_id: string
    reason: string  # proficiency_reached, max_items, manual_stop
    final_proficiency: number
    items_completed: integer

- type: "io.mozart.itemselector.proficiency.updated.v1"
  source: "/item-selector"
  subject: "{session_id}"
  data:
    session_id: string
    user_id: string
    skill_id: string
    old_proficiency: number
    new_proficiency: number
    confidence: number

# Events consumed by item-selector

- type: "io.mozart.agenthost.item.scored.v1"
  source: "/agent-host"
  subject: "{conversation_id}"
  data:
    conversation_id: string
    item_id: string
    is_correct: boolean
    score: number
    response_time_ms: integer
```

---

## 8. ConversationContext Extensions

```python
# Additions to ConversationContext

@dataclass
class ConversationContext:
    """Extended context with adaptive tracking."""
    
    # Existing fields...
    
    # NEW: Adaptive Session Tracking
    adaptive_session_id: str | None = None
    
    # NEW: Item History (for hybrid mode slot tracking)
    visited_item_ids: set[str] = field(default_factory=set)
    current_adaptive_slot_id: str | None = None
    
    # NEW: Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    @property
    def elapsed_seconds(self) -> int:
        """Get seconds elapsed since conversation started."""
        return int((datetime.now(UTC) - self.started_at).total_seconds())
    
    @property
    def items_completed(self) -> int:
        """Get count of completed items."""
        return len(self.visited_item_ids)
```

---

## 9. Error Handling

### 9.1 Custom Exceptions

```python
# application/exceptions.py

class ItemSelectorError(Exception):
    """Base exception for item selector errors."""
    pass

class ItemSelectorUnavailableError(ItemSelectorError):
    """Raised when item selector service is unreachable."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class ItemSelectorSessionError(ItemSelectorError):
    """Raised when session operations fail."""
    pass
```

### 9.2 Failure Behavior

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| Engine unavailable at init | Conversation fails immediately | Error message, cannot start |
| Engine unavailable during select | Conversation fails | Error message, session ends |
| Engine unavailable during record_response | Log warning, continue | No impact (response persisted locally) |
| Engine timeout | Treated as unavailable | Error message, session ends |
| Invalid response from engine | Conversation fails | Error message, session ends |

---

## 10. Implementation Plan

### Phase 1: Foundation (1 week)

| Task | Component | Description |
|------|-----------|-------------|
| 1.1 | Domain | Add `ItemSelectionMode` and `AdaptiveSlotType` enums |
| 1.2 | Domain | Add `AdaptiveConfig` dataclass |
| 1.3 | Domain | Extend `ConversationTemplateState` with new fields |
| 1.4 | Domain | Add domain events for adaptive config changes |
| 1.5 | Infrastructure | Add custom exceptions |

### Phase 2: Strategy Interface (1 week)

| Task | Component | Description |
|------|-----------|-------------|
| 2.1 | Application | Create `ItemSelectionStrategy` interface |
| 2.2 | Application | Create `SelectionResult` and `ResponseRecord` DTOs |
| 2.3 | Application | Implement `SequentialSelectionStrategy` (refactor existing logic) |
| 2.4 | Application | Create `ItemSelectionStrategyFactory` |
| 2.5 | Tests | Unit tests for sequential strategy |

### Phase 3: FlowRunner Refactoring (1 week)

| Task | Component | Description |
|------|-----------|-------------|
| 3.1 | Orchestrator | Inject `ItemSelectionStrategyFactory` into `FlowRunner` |
| 3.2 | Orchestrator | Refactor `advance_to_next_item()` to use strategy |
| 3.3 | Orchestrator | Refactor `_present_item_at_index()` to use strategy |
| 3.4 | Orchestrator | Add termination reason tracking |
| 3.5 | Tests | Integration tests for sequential flow |

### Phase 4: item-selector Service Scaffold (2 weeks)

| Task | Component | Description |
|------|-----------|-------------|
| 4.1 | New Service | Create `item-selector` project structure (FastAPI) |
| 4.2 | New Service | Define OpenAPI spec and models |
| 4.3 | New Service | Implement session management |
| 4.4 | New Service | Implement placeholder selection algorithm |
| 4.5 | New Service | Add CloudEvents publishing |
| 4.6 | Docker | Add to docker-compose.yml |

### Phase 5: Adaptive Strategy (1 week)

| Task | Component | Description |
|------|-----------|-------------|
| 5.1 | Application | Implement `AdaptiveSelectionStrategy` HTTP client |
| 5.2 | Application | Add CloudEvents subscription handler |
| 5.3 | Infrastructure | Add `httpx` async client configuration |
| 5.4 | Tests | Integration tests with mocked item-selector |

### Phase 6: Hybrid Strategy (1 week)

| Task | Component | Description |
|------|-----------|-------------|
| 6.1 | Domain | Extend `ConversationItem` with adaptive slot fields |
| 6.2 | Application | Implement `HybridSelectionStrategy` |
| 6.3 | Application | Add slot transition logic |
| 6.4 | Tests | Tests for hybrid flow with fixed + adaptive items |

### Phase 7: CAT/IRT Integration (Future)

| Task | Component | Description |
|------|-----------|-------------|
| 7.1 | item-selector | Integrate actual IRT library (e.g., `catsim`) |
| 7.2 | item-selector | Implement proficiency estimation |
| 7.3 | item-selector | Implement adaptive termination criteria |
| 7.4 | item-selector | Add ExamBlueprint management |

---

## 11. Migration Strategy

### 11.1 Backward Compatibility

- **Default Mode**: `item_selection_mode` defaults to `SEQUENTIAL`
- **Existing Templates**: Continue to work unchanged
- **No Data Migration**: New fields are optional with sensible defaults

### 11.2 Feature Flag Approach

```python
# settings.py

class Settings:
    # Feature flags
    ENABLE_ADAPTIVE_SELECTION: bool = False  # Phase 5+
    ENABLE_HYBRID_TEMPLATES: bool = False    # Phase 6+
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| SequentialSelectionStrategy | Item ordering, shuffle, termination |
| AdaptiveSelectionStrategy | HTTP client mocking, error handling |
| HybridSelectionStrategy | Slot transitions, delegation |
| ItemSelectionStrategyFactory | Mode routing |

### 12.2 Integration Tests

| Scenario | Description |
|----------|-------------|
| Sequential Flow | Full conversation with fixed items |
| Adaptive Flow (Mock) | Conversation with mocked item-selector |
| Engine Unavailable | Verify proper failure behavior |
| Termination Signals | Time limit, engine signal, proficiency |

### 12.3 Contract Tests

| Consumer | Provider | Contract |
|----------|----------|----------|
| agent-host | item-selector | OpenAPI spec validation |
| item-selector | agent-host | CloudEvent schema validation |

---

## 13. Observability

### 13.1 Metrics

```python
# Prometheus metrics

selection_strategy_requests_total = Counter(
    "selection_strategy_requests_total",
    "Total selection requests",
    ["strategy", "result"]  # result: success, error, terminate
)

selection_latency_seconds = Histogram(
    "selection_latency_seconds",
    "Item selection latency",
    ["strategy"]
)

adaptive_session_items_total = Counter(
    "adaptive_session_items_total",
    "Total items presented in adaptive sessions",
    ["blueprint_id"]
)
```

### 13.2 Tracing

- Span: `item_selection.select_next`
- Attributes: `strategy`, `session_id`, `item_id`, `terminate`

### 13.3 Logging

```python
logger.info(
    "Item selected",
    extra={
        "conversation_id": context.conversation_id,
        "strategy": "adaptive",
        "item_id": result.item.id,
        "proficiency_estimate": result.metadata.get("proficiency_estimate"),
    }
)
```

---

## 14. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | Which IRT/CAT library for item-selector? (catsim, custom?) | TBD | Open |
| 2 | Should ExamBlueprint be a separate aggregate or part of item-selector? | TBD | Open |
| 3 | How to handle partial session recovery after engine restart? | TBD | Open |
| 4 | Should proficiency estimates persist across conversations? | TBD | Open |

---

## 15. Glossary

| Term | Definition |
|------|------------|
| **CAT** | Computerized Adaptive Testing - algorithm that selects items based on learner ability |
| **IRT** | Item Response Theory - statistical framework for modeling item difficulty and learner ability |
| **ExamBlueprint** | Configuration defining skills and constraints for an assessment |
| **SkillTemplate** | Template for generating items for a specific skill |
| **Proficiency** | Estimated learner ability level (typically 0.0 to 1.0 or θ scale) |
| **Termination Criterion** | Rule for when to stop adaptive testing (e.g., SE threshold, max items) |

---

## 16. Appendix: Sequence Diagrams

### A.1 Sequential Flow (Current Behavior Refactored)

```
┌─────────┐     ┌───────────┐     ┌────────────────┐     ┌─────────────┐
│ Browser │     │ FlowRunner│     │ Sequential     │     │ Template    │
│         │     │           │     │ Strategy       │     │ Store       │
└────┬────┘     └─────┬─────┘     └───────┬────────┘     └──────┬──────┘
     │                │                   │                     │
     │ WS Connect     │                   │                     │
     │───────────────▶│                   │                     │
     │                │                   │                     │
     │                │ create(SEQUENTIAL)│                     │
     │                │──────────────────▶│                     │
     │                │                   │                     │
     │                │  initialize()     │                     │
     │                │──────────────────▶│                     │
     │                │                   │  GetTemplateItems   │
     │                │                   │────────────────────▶│
     │                │                   │◀────────────────────│
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │                │  select_next()    │                     │
     │                │──────────────────▶│                     │
     │                │    Item 0         │                     │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │   Widget       │                   │                     │
     │◀───────────────│                   │                     │
     │                │                   │                     │
     │   Response     │                   │                     │
     │───────────────▶│                   │                     │
     │                │ record_response() │                     │
     │                │──────────────────▶│                     │
     │                │                   │                     │
     │                │  select_next()    │                     │
     │                │──────────────────▶│                     │
     │                │    Item 1         │                     │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │      ...       │       ...         │                     │
     │                │                   │                     │
     │                │  select_next()    │                     │
     │                │──────────────────▶│                     │
     │                │  terminate=true   │                     │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │   Complete     │                   │                     │
     │◀───────────────│                   │                     │
     │                │                   │                     │
```

### A.2 Adaptive Flow

```
┌─────────┐     ┌───────────┐     ┌────────────────┐     ┌──────────────┐
│ Browser │     │ FlowRunner│     │ Adaptive       │     │ item-selector│
│         │     │           │     │ Strategy       │     │ (External)   │
└────┬────┘     └─────┬─────┘     └───────┬────────┘     └──────┬───────┘
     │                │                   │                     │
     │ WS Connect     │                   │                     │
     │───────────────▶│                   │                     │
     │                │                   │                     │
     │                │ create(ADAPTIVE)  │                     │
     │                │──────────────────▶│                     │
     │                │                   │                     │
     │                │  initialize()     │                     │
     │                │──────────────────▶│                     │
     │                │                   │  POST /sessions     │
     │                │                   │────────────────────▶│
     │                │                   │   {session_id}      │
     │                │                   │◀────────────────────│
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │                │  select_next()    │                     │
     │                │──────────────────▶│                     │
     │                │                   │POST /sessions/x/sel │
     │                │                   │────────────────────▶│
     │                │                   │   {item: {...}}     │
     │                │                   │◀────────────────────│
     │                │    Item           │                     │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │   Widget       │                   │                     │
     │◀───────────────│                   │                     │
     │                │                   │                     │
     │   Response     │                   │                     │
     │───────────────▶│                   │                     │
     │                │ record_response() │                     │
     │                │──────────────────▶│                     │
     │                │                   │POST /sessions/x/resp│
     │                │                   │────────────────────▶│
     │                │                   │      (async)        │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │      ...       │       ...         │                     │
     │                │                   │                     │
     │                │  select_next()    │                     │
     │                │──────────────────▶│                     │
     │                │                   │POST /sessions/x/sel │
     │                │                   │────────────────────▶│
     │                │                   │  {terminate: true,  │
     │                │                   │   reason: "prof"}   │
     │                │                   │◀────────────────────│
     │                │  terminate=true   │                     │
     │                │◀──────────────────│                     │
     │                │                   │                     │
     │   Complete     │                   │                     │
     │◀───────────────│                   │                     │
     │                │                   │                     │
```

---

**Document End**
