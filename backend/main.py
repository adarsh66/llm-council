"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
import json
import asyncio
from pathlib import Path

from . import storage
from .orchestrators import (
    run_dxo,
    run_sequential,
    run_ensemble,
    stream_dxo,
    stream_sequential,
    stream_ensemble,
    run_council,
    stream_council,
    generate_conversation_title,
)
from .settings import (
    get_all_settings_effective,
    save_settings,
    load_settings,
    default_settings,
)

app = FastAPI(title="LLM Council API")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str
    # Collaboration mode passed by frontend (e.g., 'council', 'dxo', 'sequential', 'ensemble')
    mode: str | None = Field(default=None)


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""

    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""

    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/api/health")
async def health():
    """Health check endpoint (safe for SPA root)."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/")
async def root():
    """Serve SPA if built assets exist; otherwise return health JSON."""
    if _INDEX_HTML.exists():
        return FileResponse(_INDEX_HTML)
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and its stored data."""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        # Idempotent: deleting a non-existent conversation returns 204 as well
        return {"status": "ok"}
    return {"status": "ok"}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Determine mode (fallback to 'council')
    mode = (request.mode or "council").strip() or "council"

    # Dispatch by mode
    if mode == "council":
        stage1_results, stage2_results, stage3_result, metadata = await run_council(
            request.content, mode=mode
        )
    elif mode == "dxo":
        stage1_results, stage2_results, stage3_result, metadata = await run_dxo(
            request.content, mode=mode
        )
    elif mode == "sequential":
        stage1_results, stage2_results, stage3_result, metadata = await run_sequential(
            request.content, mode=mode
        )
    elif mode == "ensemble":
        stage1_results, stage2_results, stage3_result, metadata = await run_ensemble(
            request.content, mode=mode
        )
    else:
        # Fallback to council
        stage1_results, stage2_results, stage3_result, metadata = await run_council(
            request.content, mode="council"
        )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id, stage1_results, stage2_results, stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Determine mode (fallback to 'council')
            mode = (request.mode or "council").strip() or "council"

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(
                    generate_conversation_title(request.content, mode=mode)
                )

            if mode == "council":
                # Use stream_council for proper streaming
                async for event in stream_council(
                    conversation_id, request.content, mode=mode
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                # Delegate to mode-specific streaming
                if mode == "dxo":
                    async for evt in stream_dxo(
                        conversation_id, request.content, mode=mode
                    ):
                        yield f"data: {json.dumps(evt)}\n\n"
                elif mode == "sequential":
                    async for evt in stream_sequential(
                        conversation_id, request.content, mode=mode
                    ):
                        yield f"data: {json.dumps(evt)}\n\n"
                elif mode == "ensemble":
                    async for evt in stream_ensemble(
                        conversation_id, request.content, mode=mode
                    ):
                        yield f"data: {json.dumps(evt)}\n\n"
                else:
                    # Fallback: council
                    async for evt in stream_ensemble(
                        conversation_id, request.content, mode="ensemble"
                    ):
                        yield f"data: {json.dumps(evt)}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Note: non-council streams persist internally in orchestrators.

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============== Settings API ===============


class CouncilModelConfig(BaseModel):
    name: str
    system_prompt: str | None = None


class SettingsModel(BaseModel):
    council_models: list[CouncilModelConfig]
    chairman_model: str
    title_model: str | None = None


@app.get("/api/settings")
def get_settings():
    # Return effective settings for all modes plus legacy top-level
    return get_all_settings_effective()


@app.put("/api/settings")
def update_settings(payload: Dict[str, Any]):
    """Update settings supporting both legacy single-mode and new per-mode payloads.

    Accepted payloads:
    - Legacy: { council_models, chairman_model, title_model, mode? }
      If 'mode' is provided, updates that mode block; else updates 'council'.
    - Per-mode: { modes: { [mode]: { council_models, chairman_model, title_model } }, default_mode? }
      Merges provided mode blocks with existing settings.
    """
    current = load_settings()
    merged = {
        "modes": current.get("modes") or default_settings().get("modes"),
        "default_mode": current.get("default_mode") or "council",
    }

    if isinstance(payload, dict) and isinstance(payload.get("modes"), dict):
        # Merge per-mode blocks
        for mode_name, block in payload["modes"].items():
            if not isinstance(block, dict):
                continue
            existing = merged["modes"].get(mode_name, {})
            merged["modes"][mode_name] = {
                **existing,
                **{
                    k: v
                    for k, v in block.items()
                    if k in ("council_models", "chairman_model", "title_model")
                },
            }
        if (
            isinstance(payload.get("default_mode"), str)
            and payload["default_mode"].strip()
        ):
            merged["default_mode"] = payload["default_mode"].strip()
    else:
        # Legacy single-mode payload
        target_mode = (payload.get("mode") or "council").strip() or "council"
        block = {
            "council_models": payload.get("council_models"),
            "chairman_model": payload.get("chairman_model"),
            "title_model": payload.get("title_model"),
        }
        existing = merged["modes"].get(target_mode, {})
        merged["modes"][target_mode] = {
            **existing,
            **{k: v for k, v in block.items() if v is not None},
        }

    save_settings(merged)
    return get_all_settings_effective()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)


# Mount static assets for single-host deployment (after API routes).
# This only takes effect when `backend/static/index.html` exists (i.e., after
# building the frontend and copying it into place).
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
