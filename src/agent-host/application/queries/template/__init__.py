"""ConversationTemplate queries submodule.

Contains queries for retrieving ConversationTemplates:
- GetTemplatesQuery: Get templates with optional filters
- GetTemplateQuery: Get a specific template by ID
"""

from .get_templates_query import (
    GetTemplateQuery,
    GetTemplateQueryHandler,
    GetTemplatesQuery,
    GetTemplatesQueryHandler,
)

__all__ = [
    # Get templates (list)
    "GetTemplatesQuery",
    "GetTemplatesQueryHandler",
    # Get single template
    "GetTemplateQuery",
    "GetTemplateQueryHandler",
]
