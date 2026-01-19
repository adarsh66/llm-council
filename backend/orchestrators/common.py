from __future__ import annotations

from typing import Any, Dict, List

from ..azure_inference import query_model


class FrameworkAgent:
    """Optional Microsoft Agent Framework adapter.

    Attempts to run a chat for the given model via Agent Framework.
    If the framework is unavailable or raises, callers should fall back
    to the existing `query_model()` implementation.

    This is intentionally defensive: it avoids hard coupling to a
    particular package path, and simply returns `None` on failure.
    """

    def __init__(self, model_name: str, system_prompt: str | None = None):
        self.model_name = model_name
        self.system_prompt = (system_prompt or "").strip()

    async def run(
        self,
        messages: List[Dict[str, str]],
        timeout: float | None = None,
    ) -> Dict[str, Any] | None:
        """Run messages using Agent Framework if available.

        Returns a dict resembling `{ 'content': str }` or `None` when
        Agent Framework is not available or fails.
        """
        try:
            # Try multiple potential import paths to be resilient.
            azure_ai_client = None
            try:
                # Hypothetical path for Agent Framework Azure AI client
                from agent_framework.azure_ai import AzureAIChatClient  # type: ignore

                azure_ai_client = AzureAIChatClient(model=self.model_name)
            except Exception:
                try:
                    # Alternate hypothetical import (API may differ)
                    from agents import Agent  # type: ignore

                    azure_ai_client = Agent(self.model_name)
                except Exception:
                    azure_ai_client = None

            if azure_ai_client is None:
                return None

            # Construct prompt content. Some Agent Framework clients accept
            # a list of messages; others accept a single prompt string.
            # We'll attempt a common pattern; on failure, fallback occurs.
            full_messages = list(messages)
            if self.system_prompt:
                full_messages = [
                    {"role": "system", "content": self.system_prompt}
                ] + full_messages

            # Try a `.complete()` or `.chat()` style API.
            try:
                # `.complete()` style: returns an object with `.content`
                result = await azure_ai_client.complete(
                    messages=full_messages, timeout=timeout or 120.0
                )
                content = getattr(result, "content", None)
                if isinstance(content, str):
                    return {"content": content}
            except Exception:
                try:
                    # `.chat()` style: may return dict or object with `.content`
                    result = await azure_ai_client.chat(
                        messages=full_messages, timeout=timeout or 120.0
                    )
                    if isinstance(result, dict) and "content" in result:
                        return {"content": result["content"]}
                    content = getattr(result, "content", None)
                    if isinstance(content, str):
                        return {"content": content}
                except Exception:
                    return None

            # If neither path produced content, return None so caller can fallback.
            return None
        except Exception:
            # Any unexpected framework issue -> fallback
            return None


def build_agents(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a simple agent list from mode settings.

    Each agent is a dict: { 'name': model_name, 'system_prompt': optional_str }
    """
    agents: List[Dict[str, Any]] = []
    for item in settings.get("council_models", []) or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        agents.append(
            {
                "name": name,
                "system_prompt": (item.get("system_prompt") or "").strip(),
            }
        )
    return agents


def make_messages(system_prompt: str | None, user_content: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})
    return messages


async def run_agent(
    model_name: str,
    messages: List[Dict[str, str]],
    timeout: float | None = None,
) -> Dict[str, Any] | None:
    """Run an agent using Agent Framework if available, else fallback.

    - First attempts to use `FrameworkAgent`.
    - On failure or unavailability, falls back to `query_model()`.
    """
    # Try Agent Framework
    try:
        fa = FrameworkAgent(model_name=model_name)
        result = await fa.run(messages=messages, timeout=timeout)
        if result is not None:
            return result
    except Exception:
        # Ignore and proceed to fallback
        pass

    # Fallback to existing Azure Inference path
    return await query_model(model_name, messages, timeout=timeout or 120.0)
