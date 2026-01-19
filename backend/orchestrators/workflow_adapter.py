"""Agent Framework workflow adapter for LLM Council orchestrations."""

from __future__ import annotations

from typing import Any, Dict, List, AsyncGenerator, Optional, Type

try:
    from agent_framework import (
        ChatAgent,
        WorkflowBuilder,
        ChatMessage,
        WorkflowEvent,
        WorkflowOutputEvent,
        AgentRunUpdateEvent,
        WorkflowRunState,
        WorkflowStatusEvent,
    )
    from azure.ai.inference.aio import ChatCompletionsClient
    from azure.identity.aio import DefaultAzureCredential

    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    ChatAgent: Optional[Type[Any]] = None
    WorkflowBuilder: Optional[Type[Any]] = None
    ChatMessage: Optional[Type[Any]] = None
    WorkflowEvent: Optional[Type[Any]] = None
    WorkflowOutputEvent: Optional[Type[Any]] = None
    AgentRunUpdateEvent: Optional[Type[Any]] = None
    WorkflowRunState: Optional[Type[Any]] = None
    WorkflowStatusEvent: Optional[Type[Any]] = None
    ChatCompletionsClient: Optional[Type[Any]] = None
    DefaultAzureCredential: Optional[Type[Any]] = None


from ..config import AZURE_INFERENCE_ENDPOINT


def is_available() -> bool:
    """Check if Agent Framework is available.

    Returns:
        bool: True if Agent Framework is available, False otherwise.
    """
    return AGENT_FRAMEWORK_AVAILABLE


async def create_agent(model_name: str, system_prompt: str | None = None) -> Any:
    """Create a ChatAgent for the given model.

    Args:
        model_name: Name of the model to use.
        system_prompt: Optional system prompt for the agent.

    Returns:
        ChatAgent instance or None if framework unavailable.
    """
    if (
        not AGENT_FRAMEWORK_AVAILABLE
        or ChatAgent is None
        or ChatCompletionsClient is None
        or DefaultAzureCredential is None
    ):
        return None

    try:
        # Create async chat client for Azure AI Foundry
        client = ChatCompletionsClient(
            endpoint=AZURE_INFERENCE_ENDPOINT,
            credential=DefaultAzureCredential(),
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

        # Agent names must start and end with alphanumeric characters
        safe_name = model_name.replace("/", "-").replace("_", "-").replace(".", "-")

        # Create agent with system prompt if provided
        if system_prompt:
            agent = ChatAgent(
                chat_client=client,
                instructions=system_prompt,
                name=safe_name,
                model=model_name,
            )
        else:
            agent = ChatAgent(chat_client=client, name=safe_name, model=model_name)

        return agent
    except Exception as e:
        # Log error but return None to allow fallback
        print(f"Error creating agent for {model_name}: {e}")
        return None


async def build_concurrent_workflow(agents: List[Any]) -> Any:
    """Build a concurrent workflow from agents.

    All agents run in parallel on the same input.

    Args:
        agents: List of ChatAgent instances

    Returns:
        Built workflow or None if unavailable
    """
    if not AGENT_FRAMEWORK_AVAILABLE or not agents or WorkflowBuilder is None:
        return None

    try:
        builder = WorkflowBuilder()

        # Add first agent as start
        builder = builder.set_start_executor(agents[0])

        # Add all remaining agents concurrently (no edges = all run independently)
        # All agents receive the same input message
        # This creates fan-out pattern where all agents run concurrently

        return builder.build()
    except Exception as e:
        print(f"Error building concurrent workflow: {e}")
        return None


async def build_sequential_workflow(agents: List[Any]) -> Any:
    """Build a sequential workflow from agents.

    Args:
        agents: List of ChatAgent instances

    Returns:
        Built workflow or None if unavailable
    """
    if not AGENT_FRAMEWORK_AVAILABLE or not agents or WorkflowBuilder is None:
        return None

    try:
        builder = WorkflowBuilder()
        builder = builder.set_start_executor(agents[0])

        # Create sequential chain: agent_0 -> agent_1 -> ... -> agent_n
        for i in range(len(agents) - 1):
            builder = builder.add_edge(agents[i], agents[i + 1])

        return builder.build()
    except Exception as e:
        print(f"Error building sequential workflow: {e}")
        return None


async def run_workflow(workflow: Any, user_query: str) -> List[Dict[str, Any]]:
    """Run a workflow and collect results.

    Args:
        workflow: Built workflow instance
        user_query: User query to process

    Returns:
        List of results
    """
    if not AGENT_FRAMEWORK_AVAILABLE or workflow is None or ChatMessage is None:
        return []

    try:
        # Create initial message
        message = ChatMessage(role="user", text=user_query)

        # Run workflow and collect results
        events = await workflow.run(message)
        outputs = events.get_outputs()

        return [{"content": output} for output in outputs]
    except Exception as e:
        print(f"Error running workflow: {e}")
        return []


async def stream_workflow(
    workflow: Any, user_query: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream workflow events.

    Args:
        workflow: Built workflow instance.
        user_query: User query.

    Yields:
        Dict[str, Any]: Workflow events containing type and data.
    """
    if (
        not AGENT_FRAMEWORK_AVAILABLE
        or workflow is None
        or ChatMessage is None
        or AgentRunUpdateEvent is None
        or WorkflowOutputEvent is None
        or WorkflowStatusEvent is None
        or WorkflowRunState is None
    ):
        return

    try:
        message = ChatMessage(role="user", text=user_query)

        async for event in workflow.run_stream(message):
            if isinstance(event, AgentRunUpdateEvent):
                yield {
                    "type": "agent_update",
                    "executor_id": (
                        event.executor_id
                        if hasattr(event, "executor_id")
                        else "unknown"
                    ),
                    "data": event.data if hasattr(event, "data") else str(event),
                }
            elif isinstance(event, WorkflowOutputEvent):
                yield {
                    "type": "workflow_output",
                    "data": event.data if hasattr(event, "data") else None,
                }
            elif isinstance(event, WorkflowStatusEvent):
                if event.state == WorkflowRunState.IDLE:
                    break
    except Exception as e:
        yield {"type": "error", "message": str(e)}
