"""Template processing package for conversation orchestration.

This subpackage contains classes responsible for template-driven
conversation flows, including:

- JinjaRenderer: Renders Jinja2 templates with conversation context variables
- ContentGenerator: Generates dynamic content via LLM
- ItemPresenter: Presents template items (widgets, messages) to clients
- FlowRunner: Runs proactive template-driven conversation flows

Template Flow Architecture:
    FlowRunner
    ├── Runs proactive conversation flow
    ├── Tracks item progression
    └── Handles flow completion

    ItemPresenter
    ├── Presents individual items
    ├── Renders widget content
    └── Sends confirmation widgets

    ContentGenerator
    ├── Generates LLM-based content
    └── Handles templated content generation

    JinjaRenderer
    └── Variable substitution in templates
"""

from application.orchestrator.template.content_generator import ContentGenerator, GeneratedContent
from application.orchestrator.template.flow_runner import FlowRunner
from application.orchestrator.template.item_presenter import ItemPresenter
from application.orchestrator.template.jinja_renderer import JinjaRenderer

__all__ = [
    "ContentGenerator",
    "FlowRunner",
    "GeneratedContent",
    "ItemPresenter",
    "JinjaRenderer",
]
