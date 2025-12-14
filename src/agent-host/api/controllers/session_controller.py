"""Session controller for proactive agent interactions.

This controller manages session lifecycle and client action responses.
Sessions wrap Conversations and add structured interaction management.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from classy_fastapi.decorators import delete, get, post
from fastapi import Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_access_token, get_current_user
from application.agents.agent_factory import AgentFactory
from application.agents.proactive_agent import AgentEventType, ProactiveSessionContext
from application.commands import CreateSessionCommand, SetPendingActionCommand, SubmitClientResponseCommand, TerminateSessionCommand
from application.queries import GetSessionQuery, GetSessionStateQuery, GetUserSessionsQuery, SessionStateResponse
from application.services.blueprint_store import BlueprintStore
from application.services.evaluation_session_manager import EvaluationSessionManager
from application.services.item_generator_service import ItemGeneratorService
from domain.models.session_models import SessionConfig, SessionType
from infrastructure.app_settings_service import get_settings_service
from infrastructure.llm_provider_factory import get_provider_factory

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create and start a new session."""

    session_type: str = Field(
        ...,
        description="Type of session: thought, learning, validation, survey, workflow, approval",
    )
    system_prompt: str | None = Field(
        None,
        description="Optional custom system prompt",
    )
    config: dict[str, Any] | None = Field(
        None,
        description="Optional custom configuration",
    )
    model_id: str | None = Field(
        None,
        description="Optional model override in format 'provider:model' (e.g., 'openai:gpt-4o', 'ollama:llama3')",
    )


class CreateSessionResponse(BaseModel):
    """Response after session creation."""

    session_id: str
    conversation_id: str
    status: str
    control_mode: str
    stream_url: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class SubmitResponseRequest(BaseModel):
    """Request to submit response to pending client action."""

    tool_call_id: str = Field(..., description="The tool call ID being responded to")
    response: Any = Field(..., description="The user's response data")


class SessionSummaryResponse(BaseModel):
    """Summary of a session for listing."""

    id: str
    session_type: str
    control_mode: str
    status: str
    items_completed: int
    created_at: str | None
    started_at: str | None
    completed_at: str | None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class SessionDetailResponse(BaseModel):
    """Detailed session information."""

    id: str
    user_id: str
    conversation_id: str
    session_type: str
    control_mode: str
    status: str
    system_prompt: str | None
    config: dict[str, Any]
    current_item_id: str | None
    items: list[dict[str, Any]]
    ui_state: dict[str, Any]
    pending_action: dict[str, Any] | None
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    terminated_reason: str | None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class TerminateSessionRequest(BaseModel):
    """Request to terminate a session."""

    reason: str = Field(default="User terminated", description="Reason for termination")


# =============================================================================
# Controller
# =============================================================================


class SessionController(ControllerBase):
    """Controller for session management endpoints.

    Handles:
    - Session creation (POST /sessions)
    - Session listing (GET /sessions)
    - Session detail (GET /sessions/{id})
    - Response submission (POST /sessions/{id}/respond)
    - Session state for reconnect (GET /sessions/{id}/state)
    - Session termination (DELETE /sessions/{id})
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        super().__init__(service_provider, mapper, mediator)

    @post("/")
    async def create_session(
        self,
        body: CreateSessionRequest,
        user: dict[str, Any] = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ) -> CreateSessionResponse:
        """
        Create and start a new structured agent session.

        **Input:**
        - `session_type`: Type of session (thought, learning, validation, survey, workflow, approval)
        - `system_prompt`: Optional custom system prompt for the agent
        - `config`: Optional session configuration (varies by session type)
        - `model_id`: Optional LLM model override (e.g., 'openai:gpt-4o')

        **Side Effects:**
        - Creates a new Session entity in the database
        - Creates a linked Conversation for message storage
        - Session is automatically started and ready for streaming

        **Output:**
        - `session_id`: Unique identifier for the session
        - `conversation_id`: ID of the linked conversation
        - `status`: Current session status
        - `control_mode`: Who controls the conversation flow
        - `stream_url`: URL to connect for SSE event streaming
        """
        # Validate session type
        try:
            session_type = SessionType(body.session_type)
        except ValueError:
            valid_types = [t.value for t in SessionType]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session_type. Must be one of: {valid_types}",
            )

        # Parse config if provided
        config = None
        config_dict = body.config.copy() if body.config else {}

        # Store model_id in config dict so it persists with the session
        if body.model_id:
            config_dict["model_id"] = body.model_id
            logger.info(f"Session will use model: {body.model_id}")

        if config_dict:
            config = SessionConfig.from_dict(config_dict)

        # Create the session
        command = CreateSessionCommand(
            session_type=session_type,
            system_prompt=body.system_prompt,
            config=config,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)
        if not result.is_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error_message or "Failed to create session",
            )

        session_dto = result.data
        return CreateSessionResponse(
            session_id=session_dto.id,
            conversation_id=session_dto.conversation_id,
            status=session_dto.status,
            control_mode=session_dto.control_mode,
            stream_url=f"/api/session/{session_dto.id}/stream",
        )

    @get("/")
    async def list_sessions(
        self,
        user: dict[str, Any] = Depends(get_current_user),
        active_only: bool = False,
        session_type: str | None = None,
        limit: int = 50,
    ) -> list[SessionSummaryResponse]:
        """
        List sessions for the current user.

        **Input:**
        - `active_only`: If true, only return sessions that are not completed/terminated
        - `session_type`: Filter by session type (e.g., 'validation', 'learning')
        - `limit`: Maximum number of sessions to return (default: 50)

        **Output:**
        Returns an array of session summaries with:
        - `id`, `session_type`, `control_mode`, `status`
        - `items_completed`: Number of items/questions completed
        - `created_at`, `started_at`, `completed_at`: Timestamps

        Sessions are ordered by creation date (newest first).
        """
        query = GetUserSessionsQuery(
            user_info=user,
            active_only=active_only,
            session_type=session_type,
            limit=limit,
        )

        result = await self.mediator.execute_async(query)
        if not result.is_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error_message or "Failed to list sessions",
            )

        sessions = result.data
        return [
            SessionSummaryResponse(
                id=s.id(),
                session_type=s.state.session_type.value,
                control_mode=s.state.control_mode.value,
                status=s.state.status.value,
                items_completed=s.get_completed_items_count(),
                created_at=s.state.created_at.isoformat() if s.state.created_at else None,
                started_at=s.state.started_at.isoformat() if s.state.started_at else None,
                completed_at=s.state.completed_at.isoformat() if s.state.completed_at else None,
            )
            for s in sessions
        ]

    @get("/exams")
    async def list_exams(
        self,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> list[dict[str, Any]]:
        """List available exam blueprints for validation sessions.

        Returns a list of exam summaries with id, name, description,
        total items, and time limit.
        """
        blueprint_store = BlueprintStore()
        exams = await blueprint_store.list_exams()
        return exams

    @get("/{session_id}")
    async def get_session(
        self,
        session_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> SessionDetailResponse:
        """
        Get detailed session information including items and state.

        **Input:**
        - `session_id`: Unique identifier of the session

        **Output:**
        Returns comprehensive session details:
        - Core fields: `id`, `user_id`, `conversation_id`, `session_type`, `status`
        - Configuration: `system_prompt`, `config`, `control_mode`
        - Progress: `current_item_id`, `items` (all session items with state)
        - UI state: `ui_state`, `pending_action` (if waiting for user input)
        - Timestamps: `created_at`, `started_at`, `completed_at`

        **Authorization:** Users can only access their own sessions.
        """
        query = GetSessionQuery(
            session_id=session_id,
            user_info=user,
        )

        result = await self.mediator.execute_async(query)
        if not result.is_success:
            error_msg = result.error_message or ""
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )
            if "forbidden" in error_msg.lower() or "access" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to get session",
            )

        session = result.data
        return SessionDetailResponse(
            id=session.id(),
            user_id=session.state.user_id,
            conversation_id=session.state.conversation_id,
            session_type=session.state.session_type.value,
            control_mode=session.state.control_mode.value,
            status=session.state.status.value,
            system_prompt=session.state.system_prompt,
            config=session.state.config,
            current_item_id=session.state.current_item_id,
            items=session.state.items,
            ui_state=session.state.ui_state,
            pending_action=session.state.pending_action,
            created_at=session.state.created_at.isoformat() if session.state.created_at else None,
            started_at=session.state.started_at.isoformat() if session.state.started_at else None,
            completed_at=session.state.completed_at.isoformat() if session.state.completed_at else None,
            terminated_reason=session.state.terminated_reason,
        )

    @get("/{session_id}/state")
    async def get_session_state(
        self,
        session_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> SessionStateResponse:
        """
        Get lightweight session state for UI restoration.

        **Input:**
        - `session_id`: Unique identifier of the session

        **Output:**
        Returns only fields needed for UI state restoration:
        - `status`: Current session status
        - `pending_action`: Any pending client action requiring response
        - `current_item`: Current item being worked on
        - `ui_state`: Stored UI state for the session

        Use this endpoint after page refresh or network reconnection
        to restore the UI without fetching full session data.
        """
        query = GetSessionStateQuery(
            session_id=session_id,
            user_info=user,
        )

        result = await self.mediator.execute_async(query)
        if not result.is_success:
            error_msg = result.error_message or ""
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )
            if "forbidden" in error_msg.lower() or "access" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to get session state",
            )

        return result.data

    @post("/{session_id}/respond")
    async def submit_response(
        self,
        session_id: str,
        body: SubmitResponseRequest,
        user: dict[str, Any] = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ) -> SessionDetailResponse:
        """
        Submit a response to a pending client action.

        **Input:**
        - `session_id`: The session waiting for a response
        - `tool_call_id`: ID of the tool call being responded to
        - `response`: User's response data (format depends on action type)

        **Side Effects:**
        - Clears the pending action from the session
        - Resumes the agent loop with the user's response
        - May trigger additional tool calls or content generation
        - Events are emitted via the SSE stream

        **Output:**
        Returns the updated session details with cleared pending action.

        **Note:** This endpoint should only be called when the session has a pending_action.
        """
        command = SubmitClientResponseCommand(
            session_id=session_id,
            tool_call_id=body.tool_call_id,
            response=body.response,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)
        if not result.is_success:
            error_msg = result.error_message or ""
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )
            if "forbidden" in error_msg.lower() or "access" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to submit response",
            )

        session_dto = result.data
        return SessionDetailResponse(
            id=session_dto.id,
            user_id=session_dto.user_id,
            conversation_id=session_dto.conversation_id,
            session_type=session_dto.session_type,
            control_mode=session_dto.control_mode,
            status=session_dto.status,
            system_prompt=session_dto.system_prompt,
            config=session_dto.config,
            current_item_id=session_dto.current_item_id,
            items=session_dto.items,
            ui_state=session_dto.ui_state,
            pending_action=session_dto.pending_action,
            created_at=session_dto.created_at.isoformat() if session_dto.created_at else None,
            started_at=session_dto.started_at.isoformat() if session_dto.started_at else None,
            completed_at=session_dto.completed_at.isoformat() if session_dto.completed_at else None,
            terminated_reason=session_dto.terminated_reason,
        )

    @delete("/{session_id}")
    async def terminate_session(
        self,
        session_id: str,
        user: dict[str, Any] = Depends(get_current_user),
        body: TerminateSessionRequest | None = None,
    ) -> SessionDetailResponse:
        """
        Terminate an active session.

        **Input:**
        - `session_id`: The session to terminate
        - `reason`: Optional reason for termination (default: "User terminated")

        **Side Effects:**
        - Sets session status to 'terminated'
        - Records the termination reason and timestamp
        - Emits a SessionTerminated domain event
        - Any active SSE connections will receive a 'terminated' event

        **Output:**
        Returns the final session state with terminated status.

        **Note:** Terminated sessions cannot be resumed. Create a new session to continue.
        """
        reason = body.reason if body else "User terminated"

        command = TerminateSessionCommand(
            session_id=session_id,
            reason=reason,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)
        if not result.is_success:
            error_msg = result.error_message or ""
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )
            if "forbidden" in error_msg.lower() or "access" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to terminate session",
            )

        session_dto = result.data
        return SessionDetailResponse(
            id=session_dto.id,
            user_id=session_dto.user_id,
            conversation_id=session_dto.conversation_id,
            session_type=session_dto.session_type,
            control_mode=session_dto.control_mode,
            status=session_dto.status,
            system_prompt=session_dto.system_prompt,
            config=session_dto.config,
            current_item_id=session_dto.current_item_id,
            items=session_dto.items,
            ui_state=session_dto.ui_state,
            pending_action=session_dto.pending_action,
            created_at=session_dto.created_at.isoformat() if session_dto.created_at else None,
            started_at=session_dto.started_at.isoformat() if session_dto.started_at else None,
            completed_at=session_dto.completed_at.isoformat() if session_dto.completed_at else None,
            terminated_reason=session_dto.terminated_reason,
        )

    @get("/{session_id}/stream")
    async def stream_session(
        self,
        session_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> StreamingResponse:
        """Stream session events via Server-Sent Events (SSE).

        This endpoint provides real-time updates for:
        - Agent messages and thinking
        - Client actions (widgets to render)
        - Session state changes
        - Errors and completion events

        The stream stays open until the session completes or the client disconnects.
        """
        # Verify session exists and user has access
        query = GetSessionQuery(
            session_id=session_id,
            user_info=user,
        )

        result = await self.mediator.execute_async(query)
        if not result.is_success:
            error_msg = result.error_message or ""
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )
            if "forbidden" in error_msg.lower() or "access" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to access session",
            )

        session = result.data

        # Determine which provider/model to use
        # Priority: 1) model_id from session config, 2) app settings default, 3) factory default
        provider_factory = get_provider_factory()
        if provider_factory is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider factory not initialized",
            )

        # Check if session has a specific model_id in its config
        session_model_id = session.state.config.get("model_id") if session.state.config else None

        if session_model_id:
            # Use the model_id stored in the session (from user's selection at session creation)
            model_id = session_model_id
            logger.info(f"Using session's stored model: {model_id}")
            llm_provider = provider_factory.get_provider_for_model(model_id)
        else:
            # Fall back to app settings or default
            settings_service = get_settings_service()
            app_settings = await settings_service.get_settings_async()

            if app_settings:
                # Use the user's selected default provider from app settings
                default_provider = app_settings.llm.default_llm_provider.lower()
                if default_provider == "openai" and app_settings.llm.openai_enabled:
                    model_id = f"openai:{app_settings.llm.openai_model}"
                else:
                    model_id = f"ollama:{app_settings.llm.ollama_model}"

                logger.info(f"Using app settings default model: {model_id}")
                llm_provider = provider_factory.get_provider_for_model(model_id)
            else:
                # Fall back to factory default provider
                logger.info("No app settings found, using factory default LLM provider")
                llm_provider = provider_factory.get_default_provider()

        # Create proactive agent for this session
        # Note: session_config is for the session context, not the agent
        # AgentFactory.create_proactive builds its own AgentConfig based on session_type
        session_config = SessionConfig.from_dict(session.state.config) if session.state.config else SessionConfig()
        agent_factory = AgentFactory(llm_provider)
        agent = agent_factory.create_proactive(
            session_type=session.state.session_type,
            # Don't pass config here - let factory build AgentConfig from session_type
        )

        # Log the agent's tools for debugging
        from application.agents.client_tools import get_all_client_tools

        client_tools = get_all_client_tools()
        logger.info(f"🔧 ProactiveAgent created with {len(client_tools)} client tools: {[t.name for t in client_tools]}")

        # =============================================================================
        # Evaluation Session Manager Setup (for VALIDATION sessions)
        # =============================================================================
        tool_executor = None
        evaluation_manager = None

        if session.state.session_type == SessionType.VALIDATION:
            try:
                # Create the evaluation services
                blueprint_store = BlueprintStore()
                item_generator = ItemGeneratorService(blueprint_store, llm_provider)
                evaluation_manager = EvaluationSessionManager(
                    blueprint_store=blueprint_store,
                    item_generator=item_generator,
                )

                # Get exam_id from session config (required for evaluation sessions)
                # exam_id can be in:
                # 1. session_config.extra dict (when parsed via SessionConfig.from_dict)
                # 2. session.state.config dict directly (when stored/retrieved from DB)
                exam_id = None
                if session_config.extra and "exam_id" in session_config.extra:
                    exam_id = session_config.extra["exam_id"]
                elif session.state.config:
                    exam_id = session.state.config.get("exam_id")

                logger.debug(f"VALIDATION session config: {session.state.config}")
                logger.debug(f"SessionConfig extra: {session_config.extra}")
                logger.debug(f"Extracted exam_id: {exam_id}")

                if exam_id:
                    # Initialize the evaluation session with the exam blueprint
                    await evaluation_manager.initialize_session(
                        exam_id=exam_id,
                    )

                    # Create the tool executor for backend evaluation tools
                    tool_executor = evaluation_manager.create_tool_executor()
                    logger.info(f"📝 Evaluation session initialized with exam: {exam_id}")
                else:
                    logger.warning(f"VALIDATION session {session_id} has no exam_id configured - no backend tools available")

            except Exception as e:
                logger.error(f"Failed to initialize evaluation session manager: {e}", exc_info=True)
                # Continue without evaluation tools - agent will fall back to basic behavior

        # Get server tool definitions for VALIDATION sessions
        from application.agents.llm_provider import LlmToolDefinition

        server_tools = None
        if session.state.session_type == SessionType.VALIDATION and evaluation_manager is not None:
            tool_defs = EvaluationSessionManager.get_tool_definitions()
            server_tools = [
                LlmToolDefinition(
                    name=td["name"],
                    description=td["description"],
                    parameters=td["parameters"],
                )
                for td in tool_defs
            ]
            logger.info(f"🔧 Added {len(server_tools)} backend evaluation tools: {[t.name for t in server_tools]}")

        # Create session context for the agent
        agent_context = ProactiveSessionContext(
            session_id=session.id(),
            session_type=session.state.session_type,
            config=session_config,
            conversation_id=session.state.conversation_id,
            initial_message=None,
            items_completed=len([i for i in session.state.items if i.get("completed", False)]),
            tool_executor=tool_executor,
            server_tools=server_tools,
            metadata={"user_id": session.state.user_id},
        )

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events for the session."""
            session_completed = False  # Track if session completed (no heartbeats needed)
            try:
                # Send initial connection event with session state
                initial_state = {
                    "session_id": session.id(),
                    "status": session.state.status.value,
                    "control_mode": session.state.control_mode.value,
                    "pending_action": session.state.pending_action,
                }
                yield f"event: connected\ndata: {json.dumps(initial_state)}\n\n"

                # If there's already a pending action, send it immediately and wait
                if session.state.pending_action:
                    yield f"event: client_action\ndata: {json.dumps(session.state.pending_action)}\n\n"
                    # Don't start the agent loop - wait for response
                else:
                    # No pending action - start the proactive agent loop
                    logger.info(f"Starting proactive agent for session {session_id}")

                    async for event in agent.start_session(agent_context):
                        # Map agent events to frontend-expected SSE events
                        if event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                            # Frontend expects content_chunk with content directly
                            yield f"event: content_chunk\ndata: {json.dumps(event.data)}\n\n"

                        elif event.type == AgentEventType.TOOL_CALLS_DETECTED:
                            yield f"event: tool_calls_detected\ndata: {json.dumps(event.data)}\n\n"

                        elif event.type == AgentEventType.TOOL_EXECUTION_STARTED:
                            yield f"event: tool_executing\ndata: {json.dumps(event.data)}\n\n"

                        elif event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                            yield f"event: tool_result\ndata: {json.dumps(event.data)}\n\n"

                        elif event.type == AgentEventType.CLIENT_ACTION:
                            # ============================================================
                            # Multi-round widget handling loop
                            # Handles multiple consecutive widget interactions
                            # ============================================================
                            current_event = event

                            while True:
                                # Agent is requesting a client action (widget)
                                action_data = current_event.data.get("action", {})
                                tool_call_id = action_data.get("tool_call_id", "")

                                # Emit client action to frontend
                                yield f"event: client_action\ndata: {json.dumps(current_event.data)}\n\n"

                                # Update session state with pending action via command
                                try:
                                    command = SetPendingActionCommand(
                                        session_id=session_id,
                                        tool_call_id=tool_call_id,
                                        tool_name=action_data.get("tool_name", ""),
                                        widget_type=action_data.get("widget_type", "unknown"),
                                        props=action_data.get("props", {}),
                                        lock_input=action_data.get("lock_input", True),
                                    )
                                    result = await self.mediator.execute_async(command)
                                    if result.is_success:
                                        logger.info(f"✅ Session {session_id} pending action set: {tool_call_id}")
                                    else:
                                        logger.warning(f"Failed to set pending action: {result.error_message}")
                                except Exception as e:
                                    logger.error(f"Failed to set pending action on session {session_id}: {e}")

                                # Mark session as suspended
                                yield f"event: run_suspended\ndata: {json.dumps({'tool_call_id': tool_call_id, 'session_id': session_id})}\n\n"

                                # ============================================================
                                # Wait for client response
                                # ============================================================
                                poll_interval = 0.5  # Check every 500ms
                                max_wait_seconds = 30 * 60  # 30 minutes max wait
                                waited_seconds = 0.0
                                response_data = None

                                logger.info(f"⏳ Waiting for client response to tool_call_id: {tool_call_id}")

                                while waited_seconds < max_wait_seconds:
                                    await asyncio.sleep(poll_interval)
                                    waited_seconds += poll_interval

                                    # Send heartbeat every 30 seconds
                                    if int(waited_seconds) % 30 == 0 and waited_seconds > 0:
                                        yield f"event: heartbeat\ndata: {json.dumps({'seconds_waited': int(waited_seconds)})}\n\n"

                                    # Check if response has been submitted
                                    try:
                                        check_query = GetSessionQuery(session_id=session_id, user_info=user)
                                        check_result = await self.mediator.execute_async(check_query)
                                        if check_result.is_success:
                                            current_session = check_result.data
                                            # If pending_action is cleared, response was submitted
                                            if current_session.state.pending_action is None:
                                                if current_session.state.items:
                                                    last_item = current_session.state.items[-1]
                                                    user_response = last_item.get("user_response", {})
                                                    if user_response:
                                                        response_data = user_response.get("response", {})
                                                        logger.info(f"✅ Response detected for tool_call_id: {tool_call_id}, response: {response_data}")
                                                        break
                                                else:
                                                    response_data = {}
                                                    logger.info(f"✅ Response detected (no items) for tool_call_id: {tool_call_id}")
                                                    break
                                    except Exception as e:
                                        logger.warning(f"Error checking session state: {e}")

                                if response_data is None:
                                    # Timeout waiting for response
                                    logger.warning(f"Timeout waiting for response to {tool_call_id}")
                                    yield f"event: error\ndata: {json.dumps({'error': 'Timeout waiting for client response'})}\n\n"
                                    session_completed = True
                                    break  # Exit the multi-round loop

                                # ============================================================
                                # Resume the agent with the response
                                # ============================================================
                                from datetime import UTC, datetime

                                from domain.models.session_models import ClientResponse as DomainClientResponse

                                client_response = DomainClientResponse(
                                    tool_call_id=tool_call_id,
                                    response=response_data,
                                    timestamp=datetime.now(UTC),
                                )

                                yield f"event: run_resumed\ndata: {json.dumps({'session_id': session_id, 'tool_call_id': tool_call_id})}\n\n"

                                # Resume agent and process events
                                should_continue_loop = False
                                next_client_action_event = None

                                try:
                                    async for resume_event in agent.resume_with_response(client_response):
                                        if resume_event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                                            yield f"event: content_chunk\ndata: {json.dumps(resume_event.data)}\n\n"
                                        elif resume_event.type == AgentEventType.TOOL_CALLS_DETECTED:
                                            yield f"event: tool_calls_detected\ndata: {json.dumps(resume_event.data)}\n\n"
                                        elif resume_event.type == AgentEventType.TOOL_EXECUTION_STARTED:
                                            yield f"event: tool_executing\ndata: {json.dumps(resume_event.data)}\n\n"
                                        elif resume_event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                                            yield f"event: tool_result\ndata: {json.dumps(resume_event.data)}\n\n"
                                        elif resume_event.type == AgentEventType.CLIENT_ACTION:
                                            # Another widget - continue the loop
                                            next_client_action_event = resume_event
                                            should_continue_loop = True
                                            break
                                        elif resume_event.type == AgentEventType.RUN_COMPLETED:
                                            yield f"event: message_complete\ndata: {json.dumps({'content': resume_event.data.get('response', '')})}\n\n"
                                            yield f"event: stream_complete\ndata: {json.dumps({'session_id': session_id})}\n\n"
                                            session_completed = True
                                            break
                                        elif resume_event.type == AgentEventType.RUN_FAILED:
                                            yield f"event: error\ndata: {json.dumps({'error': resume_event.data.get('error', 'Unknown error')})}\n\n"
                                            session_completed = True
                                            break
                                        elif resume_event.type == AgentEventType.RUN_SUSPENDED:
                                            # Agent suspended - wait for next response
                                            break
                                except Exception as e:
                                    logger.error(f"Error resuming agent: {e}", exc_info=True)
                                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                                    session_completed = True
                                    break  # Exit the multi-round loop

                                if session_completed or not should_continue_loop:
                                    break  # Exit the multi-round loop

                                # Continue with the next widget
                                current_event = next_client_action_event

                            # After handling all widget interactions, exit the main event loop
                            break

                        elif event.type == AgentEventType.RUN_FAILED:
                            yield f"event: error\ndata: {json.dumps({'error': event.data.get('error', 'Unknown error')})}\n\n"
                            session_completed = True
                            break

                        elif event.type == AgentEventType.RUN_COMPLETED:
                            # Frontend expects message_complete format
                            yield f"event: message_complete\ndata: {json.dumps({'content': event.data.get('response', '')})}\n\n"
                            yield f"event: stream_complete\ndata: {json.dumps({'session_id': session_id})}\n\n"
                            session_completed = True
                            break

                        elif event.type == AgentEventType.RUN_SUSPENDED:
                            # Agent suspended waiting for client response
                            yield f"event: run_suspended\ndata: {json.dumps(event.data)}\n\n"
                            break

                # Keep connection alive with heartbeats ONLY if session is not completed
                if not session_completed:
                    heartbeat_interval = 30  # seconds
                    heartbeat_count = 0
                    max_heartbeats = 60  # ~30 minutes max wait

                    while heartbeat_count < max_heartbeats:
                        await asyncio.sleep(heartbeat_interval)
                        heartbeat_count += 1
                        yield f"event: heartbeat\ndata: {json.dumps({'count': heartbeat_count})}\n\n"

            except asyncio.CancelledError:
                logger.info(f"SSE stream cancelled for session {session_id}")
                yield f"event: disconnected\ndata: {json.dumps({'reason': 'Client disconnected'})}\n\n"
            except Exception as e:
                logger.error(f"Error in session stream {session_id}: {e}", exc_info=True)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
