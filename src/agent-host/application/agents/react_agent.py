"""ReAct Agent implementation for Agent Host.

This module implements the ReAct (Reasoning and Acting) agent pattern,
which interleaves reasoning steps with tool execution in a loop until
the task is complete.

Pattern:
1. Observe: Receive user input and context
2. Think: LLM generates reasoning and potential tool calls
3. Act: Execute tool calls if requested
4. Repeat: Continue until LLM produces final response (no tool calls)

References:
- ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from uuid import uuid4

from application.agents.agent_config import AgentConfig
from application.agents.base_agent import Agent, AgentError, AgentEvent, AgentEventType, AgentRunContext, AgentRunResult, ToolExecutionRequest
from application.agents.llm_provider import LlmMessage, LlmProvider

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

logger = logging.getLogger(__name__)


class ReActAgent(Agent):
    """ReAct-style agent that interleaves reasoning with tool execution.

    The ReAct agent follows this loop:
    1. Send conversation + user message to LLM
    2. If LLM returns tool calls:
       a. Execute each tool
       b. Add tool results to conversation
       c. Go back to step 1
    3. If LLM returns text response (no tool calls):
       a. Return the response to user
       b. End loop

    Safety Features:
    - Max iterations to prevent infinite loops
    - Max tool calls per iteration
    - Configurable error handling
    - Timeout enforcement

    Usage:
        agent = ReActAgent(llm_provider, config)
        context = AgentRunContext(
            user_message="What's the weather?",
            tools=[weather_tool],
            tool_executor=execute_tool,
        )
        result = await agent.run(context)
    """

    async def run(self, context: AgentRunContext) -> AgentRunResult:
        """Run the agent on a user request (non-streaming).

        Args:
            context: The run context

        Returns:
            The result of the agent run
        """
        start_time = time.time()
        messages: list[LlmMessage] = []
        tool_calls_made = 0

        try:
            # Build initial messages
            messages = self._build_messages(context)

            for iteration in range(self._config.max_iterations):
                logger.debug(f"ReAct iteration {iteration + 1}/{self._config.max_iterations}")

                # Call LLM
                response = await self._llm.chat(
                    messages=messages,
                    tools=context.tools if context.tools else None,
                )

                # Add assistant message to history
                assistant_message = LlmMessage.assistant(
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
                messages.append(assistant_message)

                # If no tool calls, we're done
                if not response.has_tool_calls:
                    return AgentRunResult(
                        success=True,
                        response=response.content,
                        messages=messages,
                        tool_calls_made=tool_calls_made,
                        iterations=iteration + 1,
                        total_time_ms=(time.time() - start_time) * 1000,
                    )

                # Execute tool calls
                if context.tool_executor and response.tool_calls:
                    for tool_call in response.tool_calls[: self._config.max_tool_calls_per_iteration]:
                        request = ToolExecutionRequest(
                            call_id=tool_call.id,
                            tool_name=tool_call.name,
                            arguments=tool_call.arguments,
                        )

                        # Execute tool (collect single result from async iterator)
                        async for result in context.tool_executor(request):
                            tool_calls_made += 1
                            messages.append(result.to_llm_message())
                            break  # Only expect one result per request

            # Max iterations reached
            logger.warning(f"ReAct agent reached max iterations ({self._config.max_iterations})")
            return AgentRunResult(
                success=True,
                response=messages[-1].content if messages else "Max iterations reached.",
                messages=messages,
                tool_calls_made=tool_calls_made,
                iterations=self._config.max_iterations,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"ReAct agent error: {e}")
            return AgentRunResult(
                success=False,
                response="",
                messages=messages,
                tool_calls_made=tool_calls_made,
                iterations=0,
                total_time_ms=(time.time() - start_time) * 1000,
                error=AgentError(str(e), "execution_error", is_retryable=True),
            )

    async def run_stream(self, context: AgentRunContext) -> AsyncIterator[AgentEvent]:
        """Run the agent with streaming events.

        This is the primary method for interactive use, emitting events
        as the agent reasons and acts.

        Args:
            context: The run context

        Yields:
            Events as the agent executes
        """
        start_time = time.time()
        tool_calls_made = 0
        current_iteration = 0

        # Emit run started event
        yield AgentEvent(
            type=AgentEventType.RUN_STARTED,
            data={"user_message": context.user_message, "tools_count": len(context.tools)},
        )

        try:
            # Build initial messages
            messages = self._build_messages(context)

            # Add user message event
            user_msg_id = str(uuid4())
            yield AgentEvent(
                type=AgentEventType.MESSAGE_ADDED,
                data={
                    "message_id": user_msg_id,
                    "role": "user",
                    "content": context.user_message,
                },
                message_id=user_msg_id,
            )

            for iteration in range(self._config.max_iterations):
                current_iteration = iteration + 1

                # Emit iteration started
                yield AgentEvent(
                    type=AgentEventType.ITERATION_STARTED,
                    data={"iteration": current_iteration, "max_iterations": self._config.max_iterations},
                    iteration=current_iteration,
                )

                # Emit LLM request started
                yield AgentEvent(
                    type=AgentEventType.LLM_REQUEST_STARTED,
                    data={"model": self._llm.model, "messages_count": len(messages)},
                    iteration=current_iteration,
                )

                # Stream LLM response
                assistant_content = ""
                tool_calls = []
                assistant_msg_id = str(uuid4())

                if self._config.stream_responses:
                    async for chunk in self._llm.chat_stream(
                        messages=messages,
                        tools=context.tools if context.tools else None,
                    ):
                        if chunk.content:
                            assistant_content += chunk.content
                            yield AgentEvent(
                                type=AgentEventType.LLM_RESPONSE_CHUNK,
                                data={"content": chunk.content},
                                iteration=current_iteration,
                                message_id=assistant_msg_id,
                            )

                        if chunk.done:
                            if chunk.tool_calls:
                                tool_calls = chunk.tool_calls
                            break
                else:
                    # Non-streaming
                    response = await self._llm.chat(
                        messages=messages,
                        tools=context.tools if context.tools else None,
                    )
                    assistant_content = response.content
                    tool_calls = response.tool_calls or []

                    if assistant_content:
                        yield AgentEvent(
                            type=AgentEventType.LLM_RESPONSE_CHUNK,
                            data={"content": assistant_content},
                            iteration=current_iteration,
                            message_id=assistant_msg_id,
                        )

                # Add assistant message to history
                assistant_message = LlmMessage.assistant(
                    content=assistant_content,
                    tool_calls=tool_calls if tool_calls else None,
                )
                messages.append(assistant_message)

                # Emit LLM response completed
                yield AgentEvent(
                    type=AgentEventType.LLM_RESPONSE_COMPLETED,
                    data={
                        "content": assistant_content,
                        "has_tool_calls": bool(tool_calls),
                        "tool_calls_count": len(tool_calls) if tool_calls else 0,
                    },
                    iteration=current_iteration,
                    message_id=assistant_msg_id,
                )

                # If no tool calls, we're done
                if not tool_calls:
                    yield AgentEvent(
                        type=AgentEventType.MESSAGE_ADDED,
                        data={
                            "message_id": assistant_msg_id,
                            "role": "assistant",
                            "content": assistant_content,
                        },
                        message_id=assistant_msg_id,
                    )

                    yield AgentEvent(
                        type=AgentEventType.ITERATION_COMPLETED,
                        data={"iteration": current_iteration, "finished": True},
                        iteration=current_iteration,
                    )

                    yield AgentEvent(
                        type=AgentEventType.RUN_COMPLETED,
                        data={
                            "success": True,
                            "response": assistant_content,
                            "tool_calls_made": tool_calls_made,
                            "iterations": current_iteration,
                            "total_time_ms": (time.time() - start_time) * 1000,
                        },
                    )
                    return

                # Tool calls detected
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALLS_DETECTED,
                    data={"tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in tool_calls]},
                    iteration=current_iteration,
                )

                # Execute tool calls
                if context.tool_executor:
                    for tool_call in tool_calls[: self._config.max_tool_calls_per_iteration]:
                        request = ToolExecutionRequest(
                            call_id=tool_call.id,
                            tool_name=tool_call.name,
                            arguments=tool_call.arguments,
                        )

                        # Emit tool execution started
                        yield AgentEvent(
                            type=AgentEventType.TOOL_EXECUTION_STARTED,
                            data={
                                "call_id": tool_call.id,
                                "tool_name": tool_call.name,
                                "arguments": tool_call.arguments,
                            },
                            iteration=current_iteration,
                        )

                        # Execute tool
                        try:
                            async for result in context.tool_executor(request):
                                tool_calls_made += 1
                                messages.append(result.to_llm_message())

                                if result.success:
                                    yield AgentEvent(
                                        type=AgentEventType.TOOL_EXECUTION_COMPLETED,
                                        data={
                                            "call_id": result.call_id,
                                            "tool_name": result.tool_name,
                                            "result": result.result,
                                            "execution_time_ms": result.execution_time_ms,
                                        },
                                        iteration=current_iteration,
                                    )
                                else:
                                    yield AgentEvent(
                                        type=AgentEventType.TOOL_EXECUTION_FAILED,
                                        data={
                                            "call_id": result.call_id,
                                            "tool_name": result.tool_name,
                                            "error": result.error,
                                            "execution_time_ms": result.execution_time_ms,
                                        },
                                        iteration=current_iteration,
                                    )

                                    if self._config.stop_on_error:
                                        raise AgentError(
                                            f"Tool execution failed: {result.error}",
                                            "tool_execution_error",
                                        )
                                break  # Only expect one result per request

                        except AgentError:
                            raise
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            yield AgentEvent(
                                type=AgentEventType.TOOL_EXECUTION_FAILED,
                                data={
                                    "call_id": tool_call.id,
                                    "tool_name": tool_call.name,
                                    "error": str(e),
                                },
                                iteration=current_iteration,
                            )

                            if self._config.stop_on_error:
                                raise AgentError(str(e), "tool_execution_error")

                # Emit iteration completed
                yield AgentEvent(
                    type=AgentEventType.ITERATION_COMPLETED,
                    data={"iteration": current_iteration, "finished": False},
                    iteration=current_iteration,
                )

            # Max iterations reached
            logger.warning(f"ReAct agent reached max iterations ({self._config.max_iterations})")
            yield AgentEvent(
                type=AgentEventType.RUN_COMPLETED,
                data={
                    "success": True,
                    "response": messages[-1].content if messages else "",
                    "tool_calls_made": tool_calls_made,
                    "iterations": current_iteration,
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "max_iterations_reached": True,
                },
            )

        except AgentError as e:
            yield AgentEvent(
                type=AgentEventType.RUN_FAILED,
                data={
                    "error": e.to_dict(),
                    "tool_calls_made": tool_calls_made,
                    "iterations": current_iteration,
                    "total_time_ms": (time.time() - start_time) * 1000,
                },
            )

        except Exception as e:
            logger.error(f"ReAct agent error: {e}")
            yield AgentEvent(
                type=AgentEventType.RUN_FAILED,
                data={
                    "error": {"message": str(e), "error_code": "unexpected_error"},
                    "tool_calls_made": tool_calls_made,
                    "iterations": current_iteration,
                    "total_time_ms": (time.time() - start_time) * 1000,
                },
            )

    @staticmethod
    def configure(builder: "ApplicationBuilderBase") -> None:
        """Configure ReActAgent in the service collection.

        Note: Requires LlmProvider to be registered first.

        Args:
            builder: The application builder
        """
        from application.settings import Settings

        # Get settings
        settings: Settings | None = None
        for desc in builder.services:
            if desc.service_type is Settings and desc.singleton:
                settings = desc.singleton
                break

        if settings is None:
            from application.settings import app_settings

            settings = app_settings

        # Get LLM provider
        llm_provider: LlmProvider | None = None
        for desc in builder.services:
            if desc.service_type is LlmProvider and desc.singleton:
                llm_provider = desc.singleton
                break

        if llm_provider is None:
            logger.error("LlmProvider not found in services. Register it before ReActAgent.")
            raise RuntimeError("LlmProvider must be registered before ReActAgent")

        # Create agent config from settings
        config = AgentConfig(
            name=settings.agent_name,
            system_prompt=settings.system_prompt,
            max_iterations=settings.agent_max_iterations,
            max_tool_calls_per_iteration=settings.agent_max_tool_calls_per_iteration,
            stream_responses=settings.ollama_stream,
            stop_on_error=settings.agent_stop_on_error,
            retry_on_error=settings.agent_retry_on_error,
            max_retries=settings.agent_max_retries,
            timeout_seconds=settings.agent_timeout_seconds,
        )

        agent = ReActAgent(llm_provider, config)

        # Register as both concrete type and abstract interface
        builder.services.add_singleton(ReActAgent, singleton=agent)
        builder.services.add_singleton(Agent, singleton=agent)

        logger.info(f"Configured ReActAgent: name={config.name}, max_iterations={config.max_iterations}")
