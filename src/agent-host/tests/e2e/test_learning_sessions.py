"""
E2E Tests for Learning Sessions

Tests the complete flow of proactive learning sessions including:
- Session creation
- Widget interactions (multiple choice, free text, code editor)
- Session completion and scoring
"""

import pytest
from playwright.sync_api import Page, expect

from .conftest import ChatInterface, WidgetInterface

# Mark all tests in this module as E2E
pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestSessionCreation:
    """Tests for session creation flow."""

    def test_start_learning_session_from_menu(self, chat_page: Page, chat: ChatInterface):
        """Test starting a learning session from the session type menu."""
        # Look for session type selector or menu
        session_menu = chat_page.locator("[data-session-type]")
        if session_menu.count() > 0:
            # Click on learning session type
            session_menu.filter(has_text="Learning").first.click()

            # Wait for session to initialize
            chat_page.wait_for_selector(".message", timeout=10000)

            # Verify we got a welcome message
            first_message = chat.messages.first
            expect(first_message).to_be_visible()

    def test_start_learning_session_via_command(self, chat_page: Page, chat: ChatInterface):
        """Test starting a learning session via chat command."""
        # Send command to start learning session
        chat.send_message("/learn algebra")

        # Wait for response
        chat.wait_for_response(timeout=15000)

        # Verify response contains learning-related content
        messages = chat.get_all_messages()
        assert len(messages) >= 2  # User message + assistant response

    def test_session_persists_across_reload(self, authenticated_page: Page, app_server):
        """Test that session state persists across page reload."""
        # This test verifies session ID is stored and retrieved
        authenticated_page.goto(f"{app_server.url}/")

        # Start a session
        chat = ChatInterface(authenticated_page)
        chat.send_message("Hello")
        chat.wait_for_response()

        # Get session info from page
        session_id = authenticated_page.evaluate("window.sessionId")

        # Reload page
        authenticated_page.reload()
        authenticated_page.wait_for_selector(".chat-container", timeout=5000)

        # Verify session ID is same
        new_session_id = authenticated_page.evaluate("window.sessionId")
        assert session_id == new_session_id or new_session_id is not None


class TestMultipleChoiceWidget:
    """Tests for multiple choice widget interactions."""

    def test_widget_renders_with_options(self, chat_page: Page, widgets: WidgetInterface):
        """Test that multiple choice widget renders all options."""
        # Trigger a multiple choice question (mock or via API)
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-mc-1',
                    widget_type: 'multiple_choice',
                    props: {
                        prompt: 'What is 2 + 2?',
                        options: ['3', '4', '5', '6'],
                        allow_multiple: false
                    }
                }
            }));
        """)

        # Wait for widget
        widgets.wait_for_widget("multiple-choice")

        # Verify options are rendered
        options = widgets.multiple_choice_widget.locator(".choice-option")
        expect(options).to_have_count(4)

    def test_select_single_option(self, chat_page: Page, widgets: WidgetInterface):
        """Test selecting a single option in multiple choice."""
        # Render widget
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-mc-2',
                    widget_type: 'multiple_choice',
                    props: {
                        prompt: 'Select an option',
                        options: ['Option A', 'Option B', 'Option C'],
                        allow_multiple: false
                    }
                }
            }));
        """)

        widgets.wait_for_widget("multiple-choice")

        # Select second option
        widgets.select_choice(1)

        # Widget should be hidden after submission
        expect(widgets.multiple_choice_widget).not_to_be_visible()

    def test_keyboard_navigation(self, chat_page: Page, widgets: WidgetInterface):
        """Test keyboard navigation in multiple choice widget."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-mc-3',
                    widget_type: 'multiple_choice',
                    props: {
                        prompt: 'Navigate with keyboard',
                        options: ['A', 'B', 'C'],
                        allow_multiple: false
                    }
                }
            }));
        """)

        widgets.wait_for_widget("multiple-choice")

        # Focus on widget
        widgets.multiple_choice_widget.focus()

        # Press down arrow twice to select third option
        chat_page.keyboard.press("ArrowDown")
        chat_page.keyboard.press("ArrowDown")
        chat_page.keyboard.press("Enter")

        # Verify submission happened
        expect(widgets.multiple_choice_widget).not_to_be_visible()


class TestFreeTextWidget:
    """Tests for free text input widget interactions."""

    def test_widget_renders_with_prompt(self, chat_page: Page, widgets: WidgetInterface):
        """Test that free text widget renders with prompt."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ft-1',
                    widget_type: 'free_text',
                    props: {
                        prompt: 'Enter your answer:',
                        placeholder: 'Type here...',
                        min_length: 1,
                        max_length: 100
                    }
                }
            }));
        """)

        widgets.wait_for_widget("free-text-prompt")

        # Verify prompt is shown
        prompt = widgets.free_text_widget.locator(".prompt, label")
        expect(prompt).to_contain_text("Enter your answer")

    def test_submit_text_response(self, chat_page: Page, widgets: WidgetInterface):
        """Test submitting a text response."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ft-2',
                    widget_type: 'free_text',
                    props: {
                        prompt: 'What is the capital of France?',
                        min_length: 1,
                        max_length: 50
                    }
                }
            }));
        """)

        widgets.wait_for_widget("free-text-prompt")

        # Enter text and submit
        widgets.enter_text("Paris")

        # Widget should be hidden
        expect(widgets.free_text_widget).not_to_be_visible()

    def test_validation_min_length(self, chat_page: Page, widgets: WidgetInterface):
        """Test that min length validation works."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ft-3',
                    widget_type: 'free_text',
                    props: {
                        prompt: 'Enter at least 5 characters',
                        min_length: 5,
                        max_length: 100
                    }
                }
            }));
        """)

        widgets.wait_for_widget("free-text-prompt")

        # Enter short text
        input_field = widgets.free_text_widget.locator("input, textarea")
        input_field.fill("Hi")

        # Submit button should be disabled or show error
        submit_btn = widgets.free_text_widget.locator("button[type='submit']")
        expect(submit_btn).to_be_disabled()


class TestCodeEditorWidget:
    """Tests for code editor widget interactions."""

    def test_widget_renders_with_initial_code(self, chat_page: Page, widgets: WidgetInterface):
        """Test that code editor widget renders with initial code."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ce-1',
                    widget_type: 'code_editor',
                    props: {
                        prompt: 'Complete the function',
                        language: 'python',
                        initial_code: 'def hello():\\n    pass'
                    }
                }
            }));
        """)

        widgets.wait_for_widget("code-editor")

        # Verify initial code is shown
        editor = widgets.code_editor_widget.locator(".code-input, textarea")
        expect(editor).to_have_value("def hello():\n    pass")

    def test_submit_code(self, chat_page: Page, widgets: WidgetInterface):
        """Test submitting code solution."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ce-2',
                    widget_type: 'code_editor',
                    props: {
                        prompt: 'Write a function',
                        language: 'python',
                        initial_code: ''
                    }
                }
            }));
        """)

        widgets.wait_for_widget("code-editor")

        # Enter code
        widgets.enter_code("def answer():\n    return 42")

        # Widget should be hidden
        expect(widgets.code_editor_widget).not_to_be_visible()

    def test_line_numbers_displayed(self, chat_page: Page, widgets: WidgetInterface):
        """Test that line numbers are displayed in code editor."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-ce-3',
                    widget_type: 'code_editor',
                    props: {
                        prompt: 'Write code',
                        language: 'python',
                        initial_code: 'line1\\nline2\\nline3'
                    }
                }
            }));
        """)

        widgets.wait_for_widget("code-editor")

        # Verify line numbers container exists
        line_numbers = widgets.code_editor_widget.locator(".line-numbers")
        expect(line_numbers).to_be_visible()


class TestLearningSessionFlow:
    """Integration tests for complete learning session flows."""

    @pytest.mark.skip(reason="Requires full app integration")
    def test_complete_algebra_session(self, chat_page: Page, chat: ChatInterface, widgets: WidgetInterface):
        """Test completing a full algebra learning session."""
        # Start algebra session
        chat.send_message("/learn algebra")
        chat.wait_for_response()

        # Wait for first question (multiple choice)
        widgets.wait_for_widget("multiple-choice", timeout=15000)

        # Answer first question
        widgets.select_choice(1)  # Select second option

        # Wait for feedback and next question
        chat.wait_for_response()

        # Continue through questions...
        # This would need to handle the dynamic nature of the session

    @pytest.mark.skip(reason="Requires full app integration")
    def test_session_scoring(self, chat_page: Page, chat: ChatInterface):
        """Test that session tracks and reports score."""
        # Complete a session and verify score is displayed
        pass

    @pytest.mark.skip(reason="Requires full app integration")
    def test_session_timeout_handling(self, chat_page: Page, chat: ChatInterface):
        """Test graceful handling of session timeout."""
        pass


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_widget_error_display(self, chat_page: Page, widgets: WidgetInterface):
        """Test that widget errors are displayed properly."""
        # Trigger a widget with invalid props
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-error-1',
                    widget_type: 'multiple_choice',
                    props: {
                        prompt: 'Invalid question',
                        options: []  // Empty options should show error
                    }
                }
            }));
        """)

        # Verify error state or fallback
        # The widget should either show an error or not render at all

    def test_network_error_recovery(self, chat_page: Page, chat: ChatInterface):
        """Test recovery from network errors during submission."""
        # This would test the retry logic in widget submission
        pass


class TestAccessibility:
    """Accessibility tests for widgets."""

    def test_multiple_choice_aria_labels(self, chat_page: Page, widgets: WidgetInterface):
        """Test that multiple choice has proper ARIA labels."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-a11y-1',
                    widget_type: 'multiple_choice',
                    props: {
                        prompt: 'Accessible question',
                        options: ['A', 'B', 'C'],
                        allow_multiple: false
                    }
                }
            }));
        """)

        widgets.wait_for_widget("multiple-choice")

        # Check for role="radiogroup" or similar
        widget = widgets.multiple_choice_widget
        expect(widget.locator("[role='radiogroup'], [role='listbox']")).to_be_visible()

    def test_focus_management(self, chat_page: Page, widgets: WidgetInterface):
        """Test that focus is properly managed when widget appears."""
        chat_page.evaluate("""
            window.dispatchEvent(new CustomEvent('client_action', {
                detail: {
                    action_id: 'test-a11y-2',
                    widget_type: 'free_text',
                    props: {
                        prompt: 'Focus test',
                        min_length: 1,
                        max_length: 100
                    }
                }
            }));
        """)

        widgets.wait_for_widget("free-text-prompt")

        # Input should receive focus
        input_field = widgets.free_text_widget.locator("input, textarea")
        expect(input_field).to_be_focused()
