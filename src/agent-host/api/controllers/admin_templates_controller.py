"""Admin controller for ConversationTemplate CRUD operations.

This controller provides administrative endpoints for managing ConversationTemplates.
All endpoints require admin role (enforced via require_roles dependency).
"""

import logging
from typing import Any

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import require_roles
from application.commands.template.create_template_command import CreateTemplateCommand
from application.commands.template.delete_template_command import DeleteTemplateCommand
from application.commands.template.update_template_command import UpdateTemplateCommand
from application.queries.template.get_templates_query import GetTemplateQuery, GetTemplatesQuery

logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ItemContentResponse(BaseModel):
    """Response model for ItemContent."""

    id: str
    order: int
    is_templated: bool = False
    source_id: str | None = None
    widget_type: str = "message"
    widget_config: dict[str, Any] = Field(default_factory=dict)
    skippable: bool = False
    required: bool = True
    show_user_response: bool = True
    max_score: float = 1.0
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None  # Excluded in client responses
    explanation: str | None = None
    initial_value: Any = None


class ConversationItemResponse(BaseModel):
    """Response model for ConversationItem."""

    id: str
    order: int
    title: str | None = None
    enable_chat_input: bool = True
    show_expiration_warning: bool = False
    expiration_warning_seconds: int = 30
    warning_message: str | None = None
    provide_feedback: bool = False
    reveal_correct_answer: bool = False
    time_limit_seconds: int | None = None
    instructions: str | None = None  # Admin-defined prompt for LLM content generation
    require_user_confirmation: bool = False
    confirmation_button_text: str = "Submit"
    contents: list[ItemContentResponse] = Field(default_factory=list)


class TemplateListResponse(BaseModel):
    """Response model for listing ConversationTemplates."""

    id: str
    name: str
    description: str | None = None
    agent_starts_first: bool = False
    is_assessment: bool = False
    item_count: int = 0
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    version: int = 1


class TemplateDetailResponse(TemplateListResponse):
    """Detailed response model for a ConversationTemplate."""

    # Flow Configuration
    allow_agent_switching: bool = True
    allow_navigation: bool = True
    allow_backward_navigation: bool = True
    enable_chat_input_initially: bool = True
    continue_after_completion: bool = False

    # Timing
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None

    # Display Options
    shuffle_items: bool = False
    display_progress_indicator: bool = True
    display_item_score: bool = False
    display_item_title: bool = True
    display_final_score_report: bool = True
    include_feedback: bool = True
    append_items_to_view: bool = True

    # Messages
    introduction_message: str | None = None
    completion_message: str | None = None

    # Items
    items: list[ConversationItemResponse] = Field(default_factory=list)

    # Scoring
    passing_score_percent: float | None = None


class ItemContentRequest(BaseModel):
    """Request model for ItemContent."""

    id: str
    order: int
    is_templated: bool = False
    source_id: str | None = None
    widget_type: str = "message"
    widget_config: dict[str, Any] = Field(default_factory=dict)
    skippable: bool = False
    required: bool = True
    show_user_response: bool = True
    max_score: float = 1.0
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    initial_value: Any = None


class ConversationItemRequest(BaseModel):
    """Request model for ConversationItem."""

    id: str
    order: int
    title: str | None = None
    enable_chat_input: bool = True
    show_expiration_warning: bool = False
    expiration_warning_seconds: int = 30
    warning_message: str | None = None
    provide_feedback: bool = False
    reveal_correct_answer: bool = False
    time_limit_seconds: int | None = None
    instructions: str | None = None  # Admin-defined prompt for LLM content generation
    require_user_confirmation: bool = False
    confirmation_button_text: str = "Submit"
    contents: list[ItemContentRequest] = Field(default_factory=list)


class CreateTemplateRequest(BaseModel):
    """Request model for creating a ConversationTemplate."""

    id: str = Field(..., description="Unique slug identifier (immutable)")
    name: str = Field(..., description="Display name")

    # Optional fields
    description: str | None = Field(default=None, description="Template description")

    # Flow Configuration
    agent_starts_first: bool = Field(default=False, description="Agent initiates conversation")
    allow_agent_switching: bool = Field(default=True, description="User can switch agents")
    allow_navigation: bool = Field(default=True, description="User can navigate items")
    allow_backward_navigation: bool = Field(default=True, description="User can go back")
    enable_chat_input_initially: bool = Field(default=True, description="Chat input visible at start")
    continue_after_completion: bool = Field(default=False, description="Allow free chat after last item")

    # Timing
    min_duration_seconds: int | None = Field(default=None, description="Minimum duration")
    max_duration_seconds: int | None = Field(default=None, description="Maximum duration")

    # Display Options
    shuffle_items: bool = Field(default=False, description="Randomize item order")
    display_progress_indicator: bool = Field(default=True, description="Show progress bar")
    display_item_score: bool = Field(default=False, description="Show item scores")
    display_item_title: bool = Field(default=True, description="Show item titles")
    display_final_score_report: bool = Field(default=True, description="Show final score")
    include_feedback: bool = Field(default=True, description="Include feedback")
    append_items_to_view: bool = Field(default=True, description="Append items in view")

    # Messages
    introduction_message: str | None = Field(default=None, description="Welcome message")
    completion_message: str | None = Field(default=None, description="Completion message")

    # Items
    items: list[ConversationItemRequest] = Field(default_factory=list, description="Conversation items")

    # Scoring
    passing_score_percent: float | None = Field(default=None, description="Passing threshold")


class UpdateTemplateRequest(BaseModel):
    """Request model for updating a ConversationTemplate.

    All fields except version are optional. Only provided fields are updated.
    """

    version: int = Field(..., description="Current version for optimistic concurrency")

    # Optional update fields
    name: str | None = Field(default=None, description="Updated display name")
    description: str | None = Field(default=None, description="Updated description")

    # Flow Configuration
    agent_starts_first: bool | None = Field(default=None, description="Updated flow behavior")
    allow_agent_switching: bool | None = Field(default=None)
    allow_navigation: bool | None = Field(default=None)
    allow_backward_navigation: bool | None = Field(default=None)
    enable_chat_input_initially: bool | None = Field(default=None)
    continue_after_completion: bool | None = Field(default=None)

    # Timing
    min_duration_seconds: int | None = Field(default=None)
    max_duration_seconds: int | None = Field(default=None)

    # Display Options
    shuffle_items: bool | None = Field(default=None)
    display_progress_indicator: bool | None = Field(default=None)
    display_item_score: bool | None = Field(default=None)
    display_item_title: bool | None = Field(default=None)
    display_final_score_report: bool | None = Field(default=None)
    include_feedback: bool | None = Field(default=None)
    append_items_to_view: bool | None = Field(default=None)

    # Messages
    introduction_message: str | None = Field(default=None)
    completion_message: str | None = Field(default=None)

    # Items (full replacement)
    items: list[ConversationItemRequest] | None = Field(default=None, description="Updated items (full replacement)")

    # Scoring
    passing_score_percent: float | None = Field(default=None)

    # Sentinel flags to explicitly clear nullable fields
    clear_description: bool = Field(default=False, description="Set description to null")
    clear_introduction_message: bool = Field(default=False, description="Set introduction to null")
    clear_completion_message: bool = Field(default=False, description="Set completion to null")
    clear_min_duration: bool = Field(default=False, description="Set min_duration to null")
    clear_max_duration: bool = Field(default=False, description="Set max_duration to null")
    clear_passing_score: bool = Field(default=False, description="Set passing_score to null")


# =============================================================================
# ADMIN CONTROLLER
# =============================================================================


class AdminTemplatesController(ControllerBase):
    """Controller for administrative ConversationTemplate operations.

    All endpoints require the 'admin' role.

    Provides CRUD operations:
    - GET /admin/templates - List all templates
    - GET /admin/templates/{id} - Get a specific template
    - POST /admin/templates - Create a new template
    - PUT /admin/templates/{id} - Update a template
    - DELETE /admin/templates/{id} - Delete a template
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        from neuroglia.serialization.json import JsonSerializer

        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = self.service_provider.get_required_service(JsonSerializer)

        # Initialize ControllerBase
        self.name = "AdminTemplates"

        # Import here to avoid circular imports
        from classy_fastapi.routable import Routable
        from neuroglia.mvc.controller_base import generate_unique_id_function

        # Override prefix to /admin/templates
        Routable.__init__(
            self,
            prefix="/admin/templates",
            tags=["Admin - Templates"],
            generate_unique_id_function=generate_unique_id_function,
        )

    def _template_to_list_response(self, template: Any) -> TemplateListResponse:
        """Convert a template to list response."""
        return TemplateListResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            agent_starts_first=template.agent_starts_first,
            is_assessment=template.is_assessment,
            item_count=template.item_count,
            created_by=template.created_by,
            created_at=template.created_at.isoformat() if template.created_at else None,
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            version=template.version,
        )

    def _template_to_detail_response(self, template: Any) -> TemplateDetailResponse:
        """Convert a template to detail response."""
        items_response = []
        for item in template.items:
            contents_response = []
            for content in item.contents:
                contents_response.append(
                    ItemContentResponse(
                        id=content.id,
                        order=content.order,
                        is_templated=content.is_templated,
                        source_id=content.source_id,
                        widget_type=content.widget_type,
                        widget_config=content.widget_config or {},
                        skippable=content.skippable,
                        required=content.required,
                        max_score=content.max_score,
                        stem=content.stem,
                        options=content.options,
                        correct_answer=content.correct_answer,
                        explanation=content.explanation,
                        initial_value=content.initial_value,
                    )
                )
            items_response.append(
                ConversationItemResponse(
                    id=item.id,
                    order=item.order,
                    title=item.title,
                    enable_chat_input=item.enable_chat_input,
                    show_expiration_warning=item.show_expiration_warning,
                    expiration_warning_seconds=item.expiration_warning_seconds if item.expiration_warning_seconds is not None else 30,
                    warning_message=item.warning_message,
                    provide_feedback=item.provide_feedback,
                    reveal_correct_answer=item.reveal_correct_answer,
                    time_limit_seconds=item.time_limit_seconds,
                    instructions=item.instructions,
                    require_user_confirmation=getattr(item, "require_user_confirmation", False),
                    confirmation_button_text=getattr(item, "confirmation_button_text", "Submit"),
                    contents=contents_response,
                )
            )

        return TemplateDetailResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            agent_starts_first=template.agent_starts_first,
            is_assessment=template.is_assessment,
            item_count=template.item_count,
            created_by=template.created_by,
            created_at=template.created_at.isoformat() if template.created_at else None,
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            version=template.version,
            allow_agent_switching=template.allow_agent_switching,
            allow_navigation=template.allow_navigation,
            allow_backward_navigation=template.allow_backward_navigation,
            enable_chat_input_initially=template.enable_chat_input_initially,
            continue_after_completion=template.continue_after_completion,
            min_duration_seconds=template.min_duration_seconds,
            max_duration_seconds=template.max_duration_seconds,
            shuffle_items=template.shuffle_items,
            display_progress_indicator=template.display_progress_indicator,
            display_item_score=template.display_item_score,
            display_item_title=template.display_item_title,
            display_final_score_report=template.display_final_score_report,
            include_feedback=template.include_feedback,
            append_items_to_view=template.append_items_to_view,
            introduction_message=template.introduction_message,
            completion_message=template.completion_message,
            items=items_response,
            passing_score_percent=template.passing_score_percent,
        )

    @get(
        "/",
        response_model=list[TemplateListResponse],
        summary="List all ConversationTemplates",
        description="Returns all ConversationTemplates in the system (admin access only).",
    )
    async def list_templates(
        self,
        proactive_only: bool = False,
        assessments_only: bool = False,
        created_by: str | None = None,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """List all ConversationTemplates.

        **Parameters:**
        - `proactive_only`: Only templates with agent_starts_first=True
        - `assessments_only`: Only templates with scoring enabled
        - `created_by`: Filter by specific creator

        **Returns:**
        Array of all templates in the system.
        """
        query = GetTemplatesQuery(
            user_info=user,
            proactive_only=proactive_only,
            assessments_only=assessments_only,
            created_by=created_by,
        )
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            return [self._template_to_list_response(t) for t in result.data]

        return self.process(result)

    @get(
        "/{template_id}",
        response_model=TemplateDetailResponse,
        summary="Get a ConversationTemplate",
        description="Returns a specific ConversationTemplate by ID (admin access only).",
    )
    async def get_template(
        self,
        template_id: str,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Get a specific ConversationTemplate by ID.

        **Parameters:**
        - `template_id`: The unique identifier of the template

        **Returns:**
        The full template details including items and contents.
        """
        query = GetTemplateQuery(template_id=template_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            return self._template_to_detail_response(result.data)

        return self.process(result)

    @post(
        "/",
        response_model=TemplateDetailResponse,
        summary="Create a ConversationTemplate",
        description="Creates a new ConversationTemplate (admin access only).",
        status_code=201,
    )
    async def create_template(
        self,
        request: CreateTemplateRequest,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Create a new ConversationTemplate.

        **Request Body:**
        - `id`: Unique slug identifier (immutable after creation)
        - `name`: Display name
        - Other fields are optional

        **Returns:**
        The created template.
        """
        # Convert Pydantic items to dicts for command
        items_data = [item.model_dump() for item in request.items] if request.items else []

        command = CreateTemplateCommand(
            id=request.id,
            name=request.name,
            description=request.description,
            agent_starts_first=request.agent_starts_first,
            allow_agent_switching=request.allow_agent_switching,
            allow_navigation=request.allow_navigation,
            allow_backward_navigation=request.allow_backward_navigation,
            enable_chat_input_initially=request.enable_chat_input_initially,
            continue_after_completion=request.continue_after_completion,
            min_duration_seconds=request.min_duration_seconds,
            max_duration_seconds=request.max_duration_seconds,
            shuffle_items=request.shuffle_items,
            display_progress_indicator=request.display_progress_indicator,
            display_item_score=request.display_item_score,
            display_item_title=request.display_item_title,
            display_final_score_report=request.display_final_score_report,
            include_feedback=request.include_feedback,
            append_items_to_view=request.append_items_to_view,
            introduction_message=request.introduction_message,
            completion_message=request.completion_message,
            items=items_data,
            passing_score_percent=request.passing_score_percent,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            return self._dto_to_detail_response(result.data)

        return self.process(result)

    @put(
        "/{template_id}",
        response_model=TemplateDetailResponse,
        summary="Update a ConversationTemplate",
        description="Updates an existing ConversationTemplate (admin access only).",
    )
    async def update_template(
        self,
        template_id: str,
        request: UpdateTemplateRequest,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Update an existing ConversationTemplate.

        Uses optimistic concurrency - provide the current version
        to ensure no concurrent modifications.

        **Parameters:**
        - `template_id`: The ID of the template to update

        **Request Body:**
        - `version`: Current version (required for concurrency check)
        - Other fields are optional - only provided fields are updated

        **Returns:**
        The updated template.
        """
        # Convert Pydantic items to dicts for command (if provided)
        items_data = [item.model_dump() for item in request.items] if request.items else None

        command = UpdateTemplateCommand(
            id=template_id,
            version=request.version,
            name=request.name,
            description=request.description,
            agent_starts_first=request.agent_starts_first,
            allow_agent_switching=request.allow_agent_switching,
            allow_navigation=request.allow_navigation,
            allow_backward_navigation=request.allow_backward_navigation,
            enable_chat_input_initially=request.enable_chat_input_initially,
            continue_after_completion=request.continue_after_completion,
            min_duration_seconds=request.min_duration_seconds,
            max_duration_seconds=request.max_duration_seconds,
            shuffle_items=request.shuffle_items,
            display_progress_indicator=request.display_progress_indicator,
            display_item_score=request.display_item_score,
            display_item_title=request.display_item_title,
            display_final_score_report=request.display_final_score_report,
            include_feedback=request.include_feedback,
            append_items_to_view=request.append_items_to_view,
            introduction_message=request.introduction_message,
            completion_message=request.completion_message,
            items=items_data,
            passing_score_percent=request.passing_score_percent,
            clear_description=request.clear_description,
            clear_introduction_message=request.clear_introduction_message,
            clear_completion_message=request.clear_completion_message,
            clear_min_duration=request.clear_min_duration,
            clear_max_duration=request.clear_max_duration,
            clear_passing_score=request.clear_passing_score,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            return self._dto_to_detail_response(result.data)

        return self.process(result)

    @delete(
        "/{template_id}",
        summary="Delete a ConversationTemplate",
        description="Deletes a ConversationTemplate (admin access only).",
        status_code=204,
    )
    async def delete_template(
        self,
        template_id: str,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Delete a ConversationTemplate.

        Note: If the template is referenced by AgentDefinitions,
        those definitions will have dangling template_id references.
        Consider updating or deleting related definitions first.

        **Parameters:**
        - `template_id`: The ID of the template to delete

        **Returns:**
        No content on success.
        """
        command = DeleteTemplateCommand(
            id=template_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return None  # 204 No Content

        return self.process(result)

    def _dto_to_detail_response(self, dto: Any) -> TemplateDetailResponse:
        """Convert a DTO to detail response."""
        items_response = []
        for item in dto.items or []:
            contents_response = []
            for content in item.contents or []:
                contents_response.append(
                    ItemContentResponse(
                        id=content.id,
                        order=content.order,
                        is_templated=content.is_templated,
                        source_id=content.source_id,
                        widget_type=content.widget_type,
                        widget_config=content.widget_config or {},
                        skippable=content.skippable,
                        required=content.required,
                        max_score=content.max_score,
                        stem=content.stem,
                        options=content.options,
                        correct_answer=content.correct_answer,
                        explanation=content.explanation,
                        initial_value=content.initial_value,
                    )
                )
            items_response.append(
                ConversationItemResponse(
                    id=item.id,
                    order=item.order,
                    title=item.title,
                    enable_chat_input=item.enable_chat_input,
                    show_expiration_warning=item.show_expiration_warning,
                    expiration_warning_seconds=item.expiration_warning_seconds if item.expiration_warning_seconds is not None else 30,
                    warning_message=item.warning_message,
                    provide_feedback=item.provide_feedback,
                    reveal_correct_answer=item.reveal_correct_answer,
                    time_limit_seconds=item.time_limit_seconds,
                    instructions=item.instructions,
                    require_user_confirmation=getattr(item, "require_user_confirmation", False),
                    confirmation_button_text=getattr(item, "confirmation_button_text", "Submit"),
                    contents=contents_response,
                )
            )

        return TemplateDetailResponse(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            agent_starts_first=dto.agent_starts_first,
            is_assessment=dto.passing_score_percent is not None,
            item_count=len(dto.items or []),
            created_by=dto.created_by,
            created_at=dto.created_at.isoformat() if dto.created_at else None,
            updated_at=dto.updated_at.isoformat() if dto.updated_at else None,
            version=dto.version,
            allow_agent_switching=dto.allow_agent_switching,
            allow_navigation=dto.allow_navigation,
            allow_backward_navigation=dto.allow_backward_navigation,
            enable_chat_input_initially=dto.enable_chat_input_initially,
            continue_after_completion=dto.continue_after_completion,
            min_duration_seconds=dto.min_duration_seconds,
            max_duration_seconds=dto.max_duration_seconds,
            shuffle_items=dto.shuffle_items,
            display_progress_indicator=dto.display_progress_indicator,
            display_item_score=dto.display_item_score,
            display_item_title=dto.display_item_title,
            display_final_score_report=dto.display_final_score_report,
            include_feedback=dto.include_feedback,
            append_items_to_view=dto.append_items_to_view,
            introduction_message=dto.introduction_message,
            completion_message=dto.completion_message,
            items=items_response,
            passing_score_percent=dto.passing_score_percent,
        )
