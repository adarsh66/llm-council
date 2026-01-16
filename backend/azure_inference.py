"""Azure AI Inference client for making LLM requests."""

import asyncio
from typing import List, Dict, Any, Optional

from azure.ai.inference.aio import ChatCompletionsClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError

from .config import AZURE_INFERENCE_ENDPOINT


# Shared credential instance (will be initialized on first use)
_credential: Optional[DefaultAzureCredential] = None
_client: Optional[ChatCompletionsClient] = None


async def get_client() -> ChatCompletionsClient:
    """
    Get or create the shared ChatCompletionsClient.

    Uses DefaultAzureCredential for authentication (supports az login,
    managed identity, environment variables, etc.)
    """
    global _credential, _client

    if _client is None:
        if not AZURE_INFERENCE_ENDPOINT:
            raise ValueError(
                "AZURE_INFERENCE_ENDPOINT environment variable is not set. "
                "Please set it to your Azure AI Foundry endpoint URL."
            )

        _credential = DefaultAzureCredential()
        _client = ChatCompletionsClient(
            endpoint=AZURE_INFERENCE_ENDPOINT,
            credential=_credential,
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

    return _client


async def query_model(
    model: str, messages: List[Dict[str, str]], timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Azure AI Inference API.

    Args:
        model: Azure model name (e.g., "gpt-5", "phi-4", "deepseek-r1")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds (used as a general guideline)

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    try:
        client = await get_client()

        response = await client.complete(
            model=model,
            messages=messages,
        )

        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message

            result = {
                "content": message.content,
            }

            # Check for reasoning/thinking content (for models like deepseek-r1)
            # Azure AI Inference may return this in different ways depending on model
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                result["reasoning_details"] = message.reasoning_content

            return result

        return None

    except HttpResponseError as e:
        print(f"Error querying model {model}: {e.status_code} - {e.message}")
        return None
    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str], messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of Azure model names
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model name to response dict (or None if failed)
    """
    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}


async def close_client():
    """Close the shared client and credential (call on shutdown)."""
    global _credential, _client

    if _client is not None:
        await _client.close()
        _client = None

    if _credential is not None:
        await _credential.close()
        _credential = None
