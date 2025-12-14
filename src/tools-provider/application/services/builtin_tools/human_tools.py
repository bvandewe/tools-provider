"""Human interaction tools.

Tools for human-in-the-loop interactions:
- ask_human: Request input from a human user
"""

import logging
from typing import Any

from .base import BuiltinToolResult, UserContext

logger = logging.getLogger(__name__)


async def execute_ask_human(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the ask_human tool.

    This tool returns a special response that signals the agent should
    pause and wait for human input. The actual pausing logic is handled
    by the agent host, not by this executor.
    """
    question = arguments.get("question", "")
    context = arguments.get("context")
    options = arguments.get("options", [])
    input_type = arguments.get("input_type", "text")

    if not question:
        return BuiltinToolResult(success=False, error="Question is required")

    logger.info(f"Ask human: {question[:50]}...")

    return BuiltinToolResult(
        success=True,
        result={
            "action": "request_human_input",
            "question": question,
            "context": context,
            "options": options,
            "input_type": input_type,
            "awaiting_response": True,
        },
        metadata={
            "requires_human_input": True,
            "input_type": input_type,
        },
    )
