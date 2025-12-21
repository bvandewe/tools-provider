"""Jinja template rendering for conversation content.

This module provides the JinjaRenderer class which handles Jinja2-style
variable substitution in template strings using conversation context.
"""

import logging
from datetime import UTC, datetime

from application.orchestrator.context import ConversationContext

log = logging.getLogger(__name__)


class JinjaRenderer:
    """Renders Jinja2-style template strings with conversation context.

    Provides variable substitution for template content using values from
    the ConversationContext. Handles undefined variables gracefully by
    returning the original template text.

    Available template variables:
        - user_id: The user's ID
        - user_name: The user's display name (falls back to user_id)
        - conversation_id: The conversation ID
        - agent_name: The agent's display name (from definition_name)
        - current_item: Current item index (1-based for display)
        - total_items: Total number of items in template
        - timestamp: Current ISO timestamp

    Example:
        >>> renderer = JinjaRenderer()
        >>> context = ConversationContext(user_id="user123", current_item_index=2)
        >>> renderer.render("Hello {{ user_id }}!", context)
        "Hello user123!"
    """

    def render(self, template: str, context: ConversationContext) -> str:
        """Render a Jinja-style template string with context variables.

        Supports {{ variable }} syntax for variable substitution.

        Args:
            template: The template string with {{ variable }} placeholders
            context: The conversation context providing variable values

        Returns:
            The rendered string with variables substituted.
            Returns original template if any error occurs.
        """
        from jinja2 import BaseLoader, Environment, UndefinedError

        try:
            # Create a Jinja2 environment with safe defaults
            env = Environment(loader=BaseLoader(), autoescape=True)

            # Build template context from available ConversationContext fields
            template_vars = self._build_template_vars(context)

            # Render the template
            jinja_template = env.from_string(template)
            return jinja_template.render(**template_vars)

        except UndefinedError as e:
            log.warning(f"Undefined variable in template: {e}")
            return template  # Return original if variable missing
        except Exception as e:
            log.error(f"Error rendering Jinja template: {e}")
            return template  # Return original on any error

    def _build_template_vars(self, context: ConversationContext) -> dict:
        """Build the template variables dictionary from context.

        Args:
            context: The conversation context

        Returns:
            Dictionary of variable names to values for template rendering
        """
        return {
            "user_id": context.user_id or "",
            "user_name": context.user_id or "User",  # Use user_id as fallback name
            "conversation_id": context.conversation_id or "",
            "agent_name": context.definition_name or "Agent",  # Use definition_name
            "current_item": (context.current_item_index or 0) + 1,  # 1-based for display
            "total_items": context.total_items or 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
