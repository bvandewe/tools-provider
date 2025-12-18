# Testing Strategy

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [Test Pyramid](#2-test-pyramid)
3. [Backend Testing](#3-backend-testing)
4. [Frontend Testing](#4-frontend-testing)
5. [Integration Testing](#5-integration-testing)
6. [E2E Testing](#6-e2e-testing)
7. [Test Infrastructure](#7-test-infrastructure)
8. [Coverage Requirements](#8-coverage-requirements)

---

## 1. Overview

### Testing Philosophy

- **Protocol-First**: Validate all messages against TypeScript/Pydantic schemas
- **Behavior-Driven**: Test user scenarios, not implementation details
- **Fast Feedback**: Unit tests run in <10 seconds, full suite <5 minutes
- **Realistic Mocks**: Mock at boundaries only (WebSocket, Redis, DB)

### Test Categories

| Category | Scope | Tools | Target |
|----------|-------|-------|--------|
| Unit | Single function/class | pytest, vitest | 80% coverage |
| Integration | Component interactions | pytest-asyncio, WebSocket mock | Key flows |
| E2E | Full system | Playwright | Critical paths |
| Contract | Protocol compliance | Custom validators | All messages |

---

## 2. Test Pyramid

```
                    ┌───────────┐
                    │    E2E    │  ~10 tests
                    │ (Critical │  Playwright
                    │   Paths)  │
                    ├───────────┤
                    │Integration│  ~50 tests
                    │  (Flows)  │  WebSocket mocks
                    ├───────────┤
                    │           │
                    │   Unit    │  ~200+ tests
                    │ (Logic)   │  pytest/vitest
                    │           │
                    └───────────┘
```

---

## 3. Backend Testing

### 3.1 Directory Structure

```
src/agent-host/tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── websocket/
│   │   ├── test_manager.py
│   │   ├── test_router.py
│   │   ├── test_state_machine.py
│   │   └── handlers/
│   │       ├── test_system_handlers.py
│   │       ├── test_control_handlers.py
│   │       └── test_data_handlers.py
│   └── protocol/
│       ├── test_message_serialization.py
│       └── test_validation.py
├── integration/
│   ├── test_connection_lifecycle.py
│   ├── test_message_flow.py
│   └── test_domain_integration.py
└── fixtures/
    ├── websocket_mocks.py
    └── protocol_messages.py
```

### 3.2 Key Fixtures

```python
# tests/conftest.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_websocket():
    """Mock Starlette WebSocket."""
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws

@pytest.fixture
def mock_mediator():
    """Mock Neuroglia Mediator."""
    mediator = AsyncMock()
    mediator.execute_async = AsyncMock()
    return mediator

@pytest.fixture
def connection_manager(mock_mediator):
    """Create ConnectionManager with mocks."""
    from application.websocket.manager import ConnectionManager
    from application.websocket.router import create_router

    router = create_router()
    return ConnectionManager(router=router)

@pytest.fixture
def sample_messages():
    """Protocol message samples for testing."""
    from tests.fixtures.protocol_messages import SAMPLE_MESSAGES
    return SAMPLE_MESSAGES
```

### 3.3 Unit Test Examples

**Connection Manager Tests:**

```python
# tests/unit/websocket/test_manager.py

import pytest
from application.websocket.manager import ConnectionManager, Connection
from application.protocol import MessageTypes

@pytest.mark.asyncio
async def test_connect_creates_connection(connection_manager, mock_websocket):
    """Test that connect() creates and registers a connection."""
    connection = await connection_manager.connect(
        websocket=mock_websocket,
        user_id="user-123",
        conversation_id="conv-456",
    )

    assert connection.connection_id is not None
    assert connection.user_id == "user-123"
    assert connection.conversation_id == "conv-456"
    mock_websocket.accept.assert_called_once()

@pytest.mark.asyncio
async def test_connect_sends_established_message(connection_manager, mock_websocket):
    """Test that connection sends established message."""
    await connection_manager.connect(
        websocket=mock_websocket,
        user_id="user-123",
    )

    # Verify send_json was called with correct message type
    call_args = mock_websocket.send_json.call_args
    message = call_args[0][0]
    assert message["type"] == MessageTypes.SYSTEM_CONNECTION_ESTABLISHED

@pytest.mark.asyncio
async def test_disconnect_removes_connection(connection_manager, mock_websocket):
    """Test that disconnect() removes connection from registry."""
    connection = await connection_manager.connect(
        websocket=mock_websocket,
        user_id="user-123",
    )

    await connection_manager.disconnect(connection.connection_id)

    assert connection.connection_id not in connection_manager._connections

@pytest.mark.asyncio
async def test_broadcast_to_conversation(connection_manager, mock_websocket):
    """Test broadcasting to all connections in a conversation."""
    # Create multiple connections to same conversation
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    conn1 = await connection_manager.connect(ws1, "user-1", "conv-123")
    conn2 = await connection_manager.connect(ws2, "user-2", "conv-123")

    # Broadcast a message
    from application.protocol import create_message, ContentChunkPayload
    message = create_message(
        msg_type=MessageTypes.DATA_CONTENT_CHUNK,
        payload=ContentChunkPayload(content_id="c1", chunk="test", sequence=0),
        source="server",
    )

    await connection_manager.broadcast_to_conversation("conv-123", message)

    ws1.send_json.assert_called()
    ws2.send_json.assert_called()
```

**Message Router Tests:**

```python
# tests/unit/websocket/test_router.py

import pytest
from application.websocket.router import MessageRouter
from application.websocket.handlers.base import BaseHandler
from application.protocol import ProtocolMessage, MessageTypes

class MockHandler(BaseHandler):
    def __init__(self):
        self.called = False
        self.last_message = None

    async def process(self, connection, message, payload):
        self.called = True
        self.last_message = message

@pytest.mark.asyncio
async def test_router_routes_to_handler():
    """Test that router routes messages to correct handler."""
    router = MessageRouter()
    handler = MockHandler()

    router.register_handler(MessageTypes.SYSTEM_PONG, handler)

    message = ProtocolMessage(
        type=MessageTypes.SYSTEM_PONG,
        source="client",
        timestamp="2025-01-01T00:00:00Z",
        payload={"timestamp": "2025-01-01T00:00:00Z"},
    )

    await router.route(None, message)

    assert handler.called
    assert handler.last_message.type == MessageTypes.SYSTEM_PONG

@pytest.mark.asyncio
async def test_router_handles_unknown_type():
    """Test that router handles unknown message types gracefully."""
    router = MessageRouter()

    message = ProtocolMessage(
        type="unknown.message.type",
        source="client",
        timestamp="2025-01-01T00:00:00Z",
    )

    # Should not raise
    await router.route(None, message)
```

### 3.4 Integration Test Examples

```python
# tests/integration/test_connection_lifecycle.py

import pytest
import asyncio
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

@pytest.mark.asyncio
async def test_full_connection_lifecycle(test_app):
    """Test complete connection lifecycle: connect → messages → disconnect."""
    async with test_app.websocket_connect("/ws?token=test-token") as ws:
        # Should receive connection established
        data = await ws.receive_json()
        assert data["type"] == "system.connection.established"
        assert "connectionId" in data["payload"]

        # Send a message
        await ws.send_json({
            "type": "data.message.send",
            "source": "client",
            "timestamp": "2025-01-01T00:00:00Z",
            "payload": {
                "content": "Hello",
                "contentType": "text",
            }
        })

        # Should receive acknowledgment
        ack = await ws.receive_json()
        assert ack["type"] == "data.message.ack"

        # Disconnect
        await ws.close()

@pytest.mark.asyncio
async def test_ping_pong_heartbeat(test_app):
    """Test heartbeat mechanism."""
    async with test_app.websocket_connect("/ws?token=test-token") as ws:
        # Skip connection established
        await ws.receive_json()

        # Wait for ping (or simulate shorter interval)
        ping = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        assert ping["type"] == "system.ping"

        # Send pong
        await ws.send_json({
            "type": "system.pong",
            "source": "client",
            "timestamp": ping["payload"]["timestamp"],
            "payload": {"timestamp": ping["payload"]["timestamp"]}
        })
```

---

## 4. Frontend Testing

### 4.1 Directory Structure

```
src/agent-host/ui/tests/
├── setup.ts                       # Test setup
├── unit/
│   ├── protocol/
│   │   ├── client.test.ts
│   │   ├── message-bus.test.ts
│   │   └── reconnect.test.ts
│   └── widgets/
│       ├── widget-base.test.ts
│       ├── multiple-choice.test.ts
│       └── ... (per widget)
├── integration/
│   └── widget-lifecycle.test.ts
└── mocks/
    ├── websocket-mock.ts
    └── protocol-messages.ts
```

### 4.2 Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.d.ts', 'src/index.ts'],
    },
  },
});
```

### 4.3 Test Setup

```typescript
// tests/setup.ts

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: Error) => void) | null = null;

  send = vi.fn();
  close = vi.fn();

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

global.WebSocket = MockWebSocket as any;

// Custom element test utilities
export function createTestWidget<T extends HTMLElement>(
  tagName: string
): T {
  const element = document.createElement(tagName) as T;
  document.body.appendChild(element);
  return element;
}

export function cleanupWidgets() {
  document.body.innerHTML = '';
}
```

### 4.4 Unit Test Examples

**WebSocket Client Tests:**

```typescript
// tests/unit/protocol/client.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WebSocketClient } from '../../../src/protocol/client';
import { MessageTypes } from '../../../src/protocol/types';

describe('WebSocketClient', () => {
  let client: WebSocketClient;
  let mockWs: MockWebSocket;

  beforeEach(() => {
    client = new WebSocketClient({
      url: 'ws://localhost:8000/ws',
      token: 'test-token',
    });
  });

  afterEach(() => {
    client.disconnect();
  });

  describe('connect', () => {
    it('should establish WebSocket connection', async () => {
      const connectPromise = client.connect();

      // Get the mock WebSocket instance
      mockWs = (global.WebSocket as any).mock.instances[0];
      mockWs.simulateOpen();

      // Simulate connection established message
      mockWs.simulateMessage({
        type: MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
        source: 'server',
        timestamp: new Date().toISOString(),
        payload: {
          connectionId: 'conn-123',
          serverTime: new Date().toISOString(),
          protocolVersion: '1.0',
          heartbeatInterval: 30,
        },
      });

      await connectPromise;

      expect(client.connectionId).toBe('conn-123');
      expect(client.state).toBe('active');
    });

    it('should include token in URL', () => {
      client.connect();

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('token=test-token')
      );
    });
  });

  describe('send', () => {
    it('should serialize and send message', async () => {
      // Setup connection
      client.connect();
      mockWs = (global.WebSocket as any).mock.instances[0];
      mockWs.simulateOpen();
      mockWs.simulateMessage({
        type: MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
        source: 'server',
        timestamp: new Date().toISOString(),
        payload: { connectionId: 'conn-123' },
      });

      // Send message
      client.send(MessageTypes.DATA_MESSAGE_SEND, {
        content: 'Hello',
        contentType: 'text',
      });

      expect(mockWs.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"data.message.send"')
      );
    });
  });
});
```

**Widget Tests:**

```typescript
// tests/unit/widgets/multiple-choice.test.ts

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { MultipleChoiceWidget } from '../../../src/widgets/multiple-choice/multiple-choice';
import { createTestWidget, cleanupWidgets } from '../../setup';

describe('MultipleChoiceWidget', () => {
  let widget: MultipleChoiceWidget;

  beforeEach(() => {
    widget = createTestWidget<MultipleChoiceWidget>('agent-widget-multiple-choice');
  });

  afterEach(() => {
    cleanupWidgets();
  });

  describe('configure', () => {
    it('should render options from config', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [
          { id: 'a', label: 'Option A' },
          { id: 'b', label: 'Option B' },
          { id: 'c', label: 'Option C' },
        ],
      });

      const options = widget.shadowRoot!.querySelectorAll('.mc-option');
      expect(options).toHaveLength(3);
    });

    it('should use radio buttons for single selection', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [{ id: 'a', label: 'A' }],
        maxSelections: 1,
      });

      const input = widget.shadowRoot!.querySelector('input');
      expect(input?.type).toBe('radio');
    });

    it('should use checkboxes for multiple selection', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [{ id: 'a', label: 'A' }],
        maxSelections: 3,
      });

      const input = widget.shadowRoot!.querySelector('input');
      expect(input?.type).toBe('checkbox');
    });
  });

  describe('getValue', () => {
    it('should return selected option IDs', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [
          { id: 'a', label: 'A' },
          { id: 'b', label: 'B' },
        ],
      });

      // Simulate selection
      const inputs = widget.shadowRoot!.querySelectorAll('input');
      inputs[0].click();
      inputs[1].click();

      expect(widget.getValue()).toEqual(['a', 'b']);
    });
  });

  describe('validate', () => {
    it('should fail if below minimum selections', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [{ id: 'a', label: 'A' }],
        minSelections: 2,
      });

      const result = widget.validate();
      expect(result.valid).toBe(false);
    });

    it('should pass with valid selection count', () => {
      widget.configure({
        widgetId: 'mc-1',
        options: [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }],
        minSelections: 1,
      });

      widget.shadowRoot!.querySelector('input')!.click();

      const result = widget.validate();
      expect(result.valid).toBe(true);
    });
  });
});
```

---

## 5. Integration Testing

### 5.1 Backend-Frontend Integration

Test WebSocket communication between real backend and frontend client:

```python
# tests/integration/test_full_message_flow.py

import pytest
import asyncio
from httpx import AsyncClient
from httpx_ws import aconnect_ws

@pytest.mark.asyncio
async def test_widget_render_flow(test_server):
    """Test: Server sends widget, client receives and renders."""
    async with aconnect_ws(f"{test_server}/ws", AsyncClient()) as ws:
        # Receive connection established
        msg = await ws.receive_json()
        assert msg["type"] == "system.connection.established"

        # Trigger widget render (via API or direct)
        # ... server sends data.widget.render

        widget_msg = await ws.receive_json()
        assert widget_msg["type"] == "data.widget.render"
        assert widget_msg["payload"]["widgetType"] == "multiple_choice"

@pytest.mark.asyncio
async def test_response_submission_flow(test_server):
    """Test: Client submits response, server acknowledges."""
    async with aconnect_ws(f"{test_server}/ws", AsyncClient()) as ws:
        await ws.receive_json()  # connection established

        # Submit response
        await ws.send_json({
            "type": "data.response.submit",
            "source": "client",
            "timestamp": "2025-01-01T00:00:00Z",
            "payload": {
                "widgetId": "widget-123",
                "responseId": "resp-456",
                "value": ["option-a"],
            }
        })

        # Verify persistence
        # (check domain or read model)
```

### 5.2 Protocol Contract Tests

Validate all messages conform to schema:

```python
# tests/integration/test_protocol_contracts.py

import pytest
from pydantic import ValidationError
from application.protocol import ProtocolMessage, MessageTypes

# All valid message samples
VALID_MESSAGES = [
    {
        "type": MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
        "source": "server",
        "timestamp": "2025-01-01T00:00:00Z",
        "payload": {
            "connectionId": "conn-123",
            "serverTime": "2025-01-01T00:00:00Z",
            "protocolVersion": "1.0",
            "heartbeatInterval": 30,
        }
    },
    # ... more samples
]

@pytest.mark.parametrize("message_data", VALID_MESSAGES)
def test_valid_messages_parse(message_data):
    """All valid messages should parse without error."""
    message = ProtocolMessage.model_validate(message_data)
    assert message.type == message_data["type"]

# Invalid message samples
INVALID_MESSAGES = [
    {"type": "invalid.type"},  # Unknown type
    {"type": MessageTypes.SYSTEM_PING},  # Missing required fields
]

@pytest.mark.parametrize("message_data", INVALID_MESSAGES)
def test_invalid_messages_rejected(message_data):
    """Invalid messages should raise ValidationError."""
    with pytest.raises(ValidationError):
        ProtocolMessage.model_validate(message_data)
```

---

## 6. E2E Testing

### 6.1 Playwright Configuration

```typescript
// playwright.config.ts

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'make run',
    port: 8000,
    reuseExistingServer: !process.env.CI,
  },
});
```

### 6.2 E2E Test Scenarios

```typescript
// tests/e2e/conversation-flow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Conversation Flow', () => {
  test('complete conversation with widget interaction', async ({ page }) => {
    // Navigate to conversation
    await page.goto('/conversation/test-conv-id');

    // Wait for WebSocket connection
    await expect(page.locator('.connection-status')).toHaveText('Connected');

    // Wait for widget to render
    const widget = page.locator('agent-widget-multiple-choice');
    await expect(widget).toBeVisible();

    // Interact with widget
    await widget.locator('label:has-text("Option A")').click();

    // Submit response
    await page.click('button:has-text("Submit")');

    // Verify feedback
    await expect(page.locator('.feedback')).toBeVisible();
  });

  test('reconnection after disconnect', async ({ page }) => {
    await page.goto('/conversation/test-conv-id');
    await expect(page.locator('.connection-status')).toHaveText('Connected');

    // Simulate network disconnect
    await page.context().setOffline(true);
    await expect(page.locator('.connection-status')).toHaveText('Reconnecting');

    // Restore network
    await page.context().setOffline(false);
    await expect(page.locator('.connection-status')).toHaveText('Connected');
  });
});
```

### 6.3 Critical E2E Paths

| Scenario | Priority | Description |
|----------|----------|-------------|
| Connection Lifecycle | P0 | Connect → Use → Disconnect |
| Reconnection | P0 | Disconnect → Reconnect → Resume |
| Widget Interaction | P0 | Render → Interact → Submit |
| Content Streaming | P0 | Receive chunks → Display progressively |
| Validation Flow | P1 | Submit → Validate → Show errors |
| Canvas Pan/Zoom | P1 | Pan → Zoom → Focus |
| Multi-Widget | P1 | Multiple widgets → Navigation |

---

## 7. Test Infrastructure

### 7.1 CI/CD Pipeline

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: cd src/agent-host && pip install -e ".[test]"
      - run: cd src/agent-host && pytest --cov=application --cov-report=xml
      - uses: codecov/codecov-action@v4

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd src/agent-host/ui && npm ci
      - run: cd src/agent-host/ui && npm run test -- --coverage
      - uses: codecov/codecov-action@v4

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - uses: actions/setup-node@v4
      - run: make setup
      - run: make up  # Start Docker services
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
```

### 7.2 Test Data Management

```python
# tests/fixtures/protocol_messages.py

from application.protocol import MessageTypes

SAMPLE_MESSAGES = {
    "connection_established": {
        "type": MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
        "source": "server",
        "timestamp": "2025-01-01T00:00:00Z",
        "payload": {
            "connectionId": "conn-test-123",
            "serverTime": "2025-01-01T00:00:00Z",
            "protocolVersion": "1.0",
            "heartbeatInterval": 30,
            "features": ["streaming", "widgets"],
        }
    },
    "widget_render_multiple_choice": {
        "type": MessageTypes.DATA_WIDGET_RENDER,
        "source": "server",
        "timestamp": "2025-01-01T00:00:00Z",
        "payload": {
            "widgetId": "widget-mc-1",
            "widgetType": "multiple_choice",
            "config": {
                "options": [
                    {"id": "a", "label": "Option A"},
                    {"id": "b", "label": "Option B"},
                ],
                "minSelections": 1,
                "maxSelections": 1,
            }
        }
    },
    # ... more samples
}
```

---

## 8. Coverage Requirements

### 8.1 Minimum Coverage Targets

| Component | Line Coverage | Branch Coverage |
|-----------|---------------|-----------------|
| Protocol Models | 100% | 100% |
| Connection Manager | 90% | 85% |
| Message Router | 90% | 85% |
| Handlers | 80% | 75% |
| Frontend Client | 90% | 85% |
| Widgets (each) | 80% | 75% |
| Canvas Engine | 75% | 70% |

### 8.2 Coverage Exceptions

Exclude from coverage:

- `__init__.py` files
- Type definitions (`*.d.ts`)
- Development utilities
- Error logging branches (acceptable to not test)

### 8.3 Quality Gates

CI fails if:

- Coverage drops below thresholds
- Any P0 E2E test fails
- Type checking fails (mypy/tsc)
- Lint errors exist

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Backend Implementation Guide](./backend-implementation-guide.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)
- [Protocol Specification](../specs/websocket-protocol-v1.md)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
