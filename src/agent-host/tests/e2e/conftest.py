"""
E2E Test Fixtures

Provides fixtures for end-to-end testing of the agent-host application
using pytest-playwright.
"""

import os
import subprocess
import time
from collections.abc import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# =============================================================================
# Configuration
# =============================================================================

APP_HOST = os.getenv("E2E_APP_HOST", "localhost")
APP_PORT = int(os.getenv("E2E_APP_PORT", "8001"))
APP_URL = f"http://{APP_HOST}:{APP_PORT}"


# =============================================================================
# Server Management
# =============================================================================


class AppServer:
    """Manages the application server for E2E tests."""

    def __init__(self, host: str = APP_HOST, port: int = APP_PORT):
        self.host = host
        self.port = port
        self.process = None
        self._external = False

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_running(self) -> bool:
        """Check if the server is responding."""
        import urllib.error
        import urllib.request

        try:
            response = urllib.request.urlopen(f"{self.url}/api/health", timeout=2)
            return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return False

    def start(self, timeout: int = 30) -> None:
        """Start the application server."""
        # Check if server is already running externally
        if self.is_running():
            self._external = True
            return

        # Start the server
        env = os.environ.copy()
        env["PORT"] = str(self.port)

        self.process = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--host", self.host, "--port", str(self.port)],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running():
                return
            time.sleep(0.5)

        self.stop()
        raise TimeoutError(f"Server failed to start within {timeout} seconds")

    def stop(self) -> None:
        """Stop the application server."""
        if self._external:
            # Don't stop externally managed server
            return

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def app_server() -> Generator[AppServer, None, None]:
    """
    Provide an application server for the test session.

    If the server is already running (e.g., started manually for development),
    it will use that instance. Otherwise, it starts and stops the server
    automatically.
    """
    server = AppServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Generator[Browser, None, None]:
    """Provide a browser instance for the test session."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Provide a fresh browser context for each test."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext, app_server: AppServer) -> Generator[Page, None, None]:
    """Provide a fresh page for each test."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page, app_server: AppServer) -> Page:
    """
    Provide a page with authentication bypass for testing.

    In test mode, the application accepts a test token that bypasses
    the actual OAuth2 flow.
    """
    # Navigate to the app
    page.goto(app_server.url)

    # Set test authentication token
    page.evaluate("""
        localStorage.setItem('auth_bypass', 'test_user_token');
    """)

    # Reload to apply auth
    page.reload()

    return page


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def chat_page(authenticated_page: Page, app_server: AppServer) -> Page:
    """Navigate to the chat interface."""
    authenticated_page.goto(f"{app_server.url}/")
    # Wait for chat interface to load
    authenticated_page.wait_for_selector(".chat-container", timeout=5000)
    return authenticated_page


@pytest.fixture
def api_client(app_server: AppServer):
    """
    Provide a simple API client for making requests.

    Returns a function that makes authenticated API requests.
    """
    import json
    import urllib.request

    def make_request(method: str, path: str, data: dict | None = None) -> dict:
        url = f"{app_server.url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_user_token",
        }

        if data:
            body = json.dumps(data).encode("utf-8")
        else:
            body = None

        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return {
                    "status": response.status,
                    "data": json.loads(response.read().decode("utf-8")),
                }
        except urllib.error.HTTPError as e:
            return {
                "status": e.code,
                "data": json.loads(e.read().decode("utf-8")) if e.read() else None,
            }

    return make_request


# =============================================================================
# Page Object Models
# =============================================================================


class ChatInterface:
    """Page object model for the chat interface."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def message_input(self):
        """Get the message input element."""
        return self.page.locator("#messageInput")

    @property
    def send_button(self):
        """Get the send button element."""
        return self.page.locator("#sendBtn")

    @property
    def messages(self):
        """Get all message elements."""
        return self.page.locator(".message")

    @property
    def last_message(self):
        """Get the last message element."""
        return self.messages.last

    def send_message(self, text: str):
        """Send a message in the chat."""
        self.message_input.fill(text)
        self.send_button.click()

    def wait_for_response(self, timeout: int = 30000):
        """Wait for an assistant response."""
        self.page.wait_for_selector(".message.assistant", timeout=timeout)

    def get_all_messages(self) -> list[dict]:
        """Get all messages as dicts with role and content."""
        messages = []
        for msg in self.messages.all():
            classes = msg.get_attribute("class") or ""
            role = "assistant" if "assistant" in classes else "user"
            content = msg.inner_text()
            messages.append({"role": role, "content": content})
        return messages


class WidgetInterface:
    """Page object model for client action widgets."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def active_widget(self):
        """Get the active widget container."""
        return self.page.locator("#client-action-widget")

    @property
    def multiple_choice_widget(self):
        """Get the multiple choice widget."""
        return self.page.locator("ax-multiple-choice")

    @property
    def free_text_widget(self):
        """Get the free text widget."""
        return self.page.locator("ax-free-text-prompt")

    @property
    def code_editor_widget(self):
        """Get the code editor widget."""
        return self.page.locator("ax-code-editor")

    def wait_for_widget(self, widget_type: str, timeout: int = 10000):
        """Wait for a specific widget type to appear."""
        selector = f"ax-{widget_type.replace('_', '-')}"
        self.page.wait_for_selector(selector, timeout=timeout)

    def select_choice(self, index: int):
        """Select a choice in multiple choice widget."""
        options = self.multiple_choice_widget.locator(".choice-option")
        options.nth(index).click()

        # Click submit
        self.multiple_choice_widget.locator("button[type='submit']").click()

    def enter_text(self, text: str):
        """Enter text in free text widget."""
        self.free_text_widget.locator("input, textarea").fill(text)
        self.free_text_widget.locator("button[type='submit']").click()

    def enter_code(self, code: str):
        """Enter code in code editor widget."""
        editor = self.code_editor_widget.locator(".code-input")
        editor.fill(code)
        self.code_editor_widget.locator("button[type='submit']").click()


@pytest.fixture
def chat(chat_page: Page) -> ChatInterface:
    """Provide a ChatInterface for the test."""
    return ChatInterface(chat_page)


@pytest.fixture
def widgets(chat_page: Page) -> WidgetInterface:
    """Provide a WidgetInterface for the test."""
    return WidgetInterface(chat_page)
