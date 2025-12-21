"""LLM-based content generation for template items.

This module provides the ContentGenerator class which generates dynamic
content using LLM providers. Used for templated content that needs to
be generated at runtime rather than serving static text.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from application.orchestrator.context import ConversationContext
from application.orchestrator.template.jinja_renderer import JinjaRenderer

if TYPE_CHECKING:
    from application.agents.llm_provider import LlmMessage

log = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """Result of LLM content generation.

    For simple widgets (message), only stem is populated.
    For structured widgets (multiple_choice), all fields may be populated.
    """

    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    @classmethod
    def from_text(cls, text: str) -> "GeneratedContent":
        """Create GeneratedContent from plain text (stem only)."""
        return cls(stem=text)

    @classmethod
    def from_json(cls, json_str: str) -> "GeneratedContent":
        """Parse JSON response into GeneratedContent.

        Expected JSON format:
        {
            "stem": "What is 25 + 17?",
            "options": ["42", "43", "32", "52"],
            "correct_answer": "42",
            "explanation": "25 + 17 = 42..."
        }
        """
        try:
            # Try to extract JSON from the response (handle markdown code blocks)
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_str)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON object
                json_match = re.search(r"\{[\s\S]*\}", json_str)
                if json_match:
                    json_str = json_match.group(0)

            data = json.loads(json_str)
            return cls(
                stem=data.get("stem"),
                options=data.get("options"),
                correct_answer=data.get("correct_answer"),
                explanation=data.get("explanation"),
            )
        except (json.JSONDecodeError, AttributeError) as e:
            log.warning(f"Failed to parse JSON content, treating as plain text: {e}")
            # Fallback: treat as plain text
            return cls(stem=json_str.strip())


class LlmProviderProtocol(Protocol):
    """Protocol for LLM provider interface."""

    async def chat(self, messages: list["LlmMessage"]) -> Any:
        """Send messages to the LLM and get a response."""
        ...


class LlmProviderFactoryProtocol(Protocol):
    """Protocol for LLM provider factory interface."""

    def get_provider_for_model(self, model_id: str) -> LlmProviderProtocol:
        """Get the appropriate provider for a given model ID."""
        ...


class ContentGenerator:
    """Generates templated content using LLM providers.

    This class handles dynamic content generation for template items,
    using the LlmProviderFactory to route requests to the appropriate
    LLM backend (OpenAI, Ollama, etc.).

    Content generation is a simple one-shot request without tool calling
    or conversation context - just prompt in, content out.

    For structured widgets (multiple_choice, etc.), returns GeneratedContent
    with all fields populated. For simple widgets, only stem is populated.

    Example:
        >>> generator = ContentGenerator(llm_factory, jinja_renderer)
        >>> result = await generator.generate(context, item_content, item)
        >>> # Returns GeneratedContent with stem, options, etc.
    """

    def __init__(
        self,
        llm_provider_factory: LlmProviderFactoryProtocol,
        jinja_renderer: JinjaRenderer | None = None,
    ) -> None:
        """Initialize the ContentGenerator.

        Args:
            llm_provider_factory: Factory for creating LLM providers
            jinja_renderer: Optional renderer for Jinja templates in instructions.
                           Creates a default one if not provided.
        """
        self._llm_provider_factory = llm_provider_factory
        self._jinja_renderer = jinja_renderer or JinjaRenderer()

    async def generate(
        self,
        context: ConversationContext,
        content: Any,  # ItemContentDto
        item: Any | None = None,  # ConversationItemDto
    ) -> GeneratedContent | None:
        """Generate templated content using LLM.

        Uses item.instructions (if available) to guide content generation.
        Falls back to source_id lookup if no instructions provided.

        For structured widgets (multiple_choice), returns GeneratedContent
        with stem, options, correct_answer, and explanation populated.

        Note: LLM generation uses the LlmProviderFactory directly rather than
        going through the Agent, as templated content generation is a simple
        one-shot request without tool calling or conversation context.

        Args:
            context: The conversation context
            content: The ItemContentDto with is_templated=True
            item: The parent ConversationItemDto (optional)

        Returns:
            GeneratedContent with fields populated, or None if generation failed
        """
        # Build the generation prompt
        instructions = getattr(item, "instructions", None) if item else None
        source_id = getattr(content, "source_id", None)

        if not instructions and not source_id:
            content_id = getattr(content, "id", "unknown")
            log.debug(f"Templated content {content_id} has no instructions or source_id, skipping generation")
            return None

        try:
            # Build prompt for LLM
            full_prompt = self._build_prompt(context, content, instructions, source_id)

            if not full_prompt:
                return None

            content_id = getattr(content, "id", "unknown")
            log.debug(f"Generating templated content with prompt: {full_prompt[:200]}...")

            # Use LlmProviderFactory directly for simple content generation
            generated = await self._generate_with_llm(context, full_prompt)
            return generated

        except Exception as e:
            content_id = getattr(content, "id", "unknown")
            log.exception(f"Error generating templated content {content_id}: {e}")
            return None

    def _build_prompt(
        self,
        context: ConversationContext,
        content: Any,
        instructions: str | None,
        source_id: str | None,
    ) -> str | None:
        """Build the LLM prompt from instructions and content metadata.

        Args:
            context: The conversation context
            content: The ItemContentDto
            instructions: Template instructions (may contain Jinja variables)
            source_id: Optional source template ID

        Returns:
            The complete prompt string, or None if no prompt could be built
        """
        prompt_parts = []

        if instructions:
            # Render instructions with Jinja variables
            rendered_instructions = self._jinja_renderer.render(instructions, context)
            prompt_parts.append(rendered_instructions)

        if source_id:
            # TODO: Fetch SkillTemplate by source_id and incorporate its prompt
            prompt_parts.append(f"Content type: {source_id}")

        # Note: We don't add widget type hint here anymore since instructions should
        # be explicit about output format (JSON for structured widgets)

        if not prompt_parts:
            return None

        return "\n\n".join(prompt_parts)

    async def _generate_with_llm(
        self,
        context: ConversationContext,
        prompt: str,
    ) -> GeneratedContent | None:
        """Generate content using the LLM provider.

        Uses the model configured in the conversation context for a simple
        one-shot text generation. Parses response as JSON for structured
        content (when JSON is detected), otherwise returns as plain text stem.

        Args:
            context: The conversation context with model configuration
            prompt: The generation prompt

        Returns:
            GeneratedContent with parsed fields, or None if generation failed
        """
        try:
            from application.agents.llm_provider import LlmMessage, LlmMessageRole

            # Get the model from context (uses definition's model or default)
            model_id = context.model or "openai:gpt-4o-mini"

            # Get the appropriate LLM provider
            llm_provider = self._llm_provider_factory.get_provider_for_model(model_id)

            # Build a simple message list for generation
            messages = [
                LlmMessage(
                    role=LlmMessageRole.SYSTEM,
                    content="You are a helpful assistant generating educational content. When asked to return JSON, return ONLY the JSON object with no additional text or formatting.",
                ),
                LlmMessage(role=LlmMessageRole.USER, content=prompt),
            ]

            # Generate response (non-streaming for simplicity)
            response = await llm_provider.chat(messages)

            if not response or not response.content:
                return None

            raw_content = response.content.strip()

            # Check if this looks like JSON (for structured widgets)
            if raw_content.startswith("{") or "```json" in raw_content or '{"stem"' in raw_content:
                return GeneratedContent.from_json(raw_content)
            else:
                return GeneratedContent.from_text(raw_content)

        except Exception as e:
            log.exception(f"Error in LLM content generation: {e}")
            return None
