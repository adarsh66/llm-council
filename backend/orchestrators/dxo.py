from __future__ import annotations

from typing import Any, Dict, List, Tuple, AsyncGenerator

from ..settings import get_effective_settings
from .. import storage
from .common import build_agents, make_messages, run_agent


async def run_stage1_dxo(
    user_query: str, mode: str = "dxo"
) -> Tuple[List, Dict, Any, List]:
    """Stage 1: Draft.

    Returns (stage1_data, settings, primary_agent, critics).
    """
    settings = get_effective_settings(mode)
    agents = build_agents(settings)
    if not agents:
        return [], settings, None, []

    primary = agents[0]
    critics = agents[1:]

    draft_msg = make_messages(primary.get("system_prompt"), user_query)
    draft_resp = await run_agent(primary["name"], draft_msg)
    draft_text = (draft_resp or {}).get("content", "")
    stage1 = [{"model": primary["name"], "response": draft_text}]

    return stage1, settings, primary, critics


async def run_stage2_dxo(draft_text: str, primary: Dict, critics: List) -> List:
    """Stage 2: Critiques.

    Returns stage2_data (list of critiques).
    """
    critique_prompt = f"Please critique the following draft. Provide pros, cons, issues, and suggested fixes.\n\nDraft:\n{draft_text}"
    critiques: List[Dict[str, Any]] = []
    for critic in critics:
        c_msg = make_messages(critic.get("system_prompt"), critique_prompt)
        c_resp = await run_agent(critic["name"], c_msg)
        critiques.append(
            {"model": critic["name"], "critique": (c_resp or {}).get("content", "")}
        )
    return critiques


async def run_stage3_dxo(
    draft_text: str, critiques: List, primary: Dict, settings: Dict
) -> Tuple[Dict, Dict]:
    """Stage 3: Optimize and synthesize.

    Returns (stage3_data, metadata).
    """
    optimize_prompt = (
        "Revise the draft based on the following critiques. Improve clarity, correctness, and completeness.\n\n"
        f"Draft:\n{draft_text}\n\nCritiques:\n"
        + "\n\n".join([f"[{c['model']}]\n{c['critique']}" for c in critiques])
    )
    opt_msg = make_messages(primary.get("system_prompt"), optimize_prompt)
    opt_resp = await run_agent(primary["name"], opt_msg)
    optimized_text = (opt_resp or {}).get("content", "")

    # Optional chairman synthesis
    chairman_model = settings.get("chairman_model")
    final_model = primary["name"]
    final_text = optimized_text
    synthesis_meta: Dict[str, Any] = {}
    if chairman_model:
        synth_prompt = (
            "As chairman, produce the final answer, incorporating the optimized draft and critiques if useful.\n\n"
            f"Optimized Draft:\n{optimized_text}\n\nCritiques:\n"
            + "\n\n".join([f"[{c['model']}]\n{c['critique']}" for c in critiques])
        )
        s_msg = make_messages(None, synth_prompt)
        s_resp = await run_agent(chairman_model, s_msg)
        final_model = chairman_model
        final_text = (s_resp or {}).get("content", optimized_text)
        synthesis_meta = {"chairman": chairman_model}

    stage3 = {"model": final_model, "response": final_text}
    metadata = {
        "dxo": {
            "primary": primary["name"],
            "critics": [c["name"] for c in critics],
            **synthesis_meta,
        }
    }
    return stage3, metadata


async def run_dxo(user_query: str, mode: str = "dxo") -> Tuple[List, List, Dict, Dict]:
    """Run DxO: Draft -> Critique -> Optimize.

    Returns a tuple (stage1, stage2, stage3, metadata) compatible with non-stream API.
    """
    s1, settings, primary, critics = await run_stage1_dxo(user_query, mode)
    if not primary:
        return [], [], {"model": "error", "response": "No agents configured."}, {}

    draft_text = s1[0]["response"]
    s2 = await run_stage2_dxo(draft_text, primary, critics)
    s3, metadata = await run_stage3_dxo(draft_text, s2, primary, settings)

    return s1, s2, s3, metadata


async def stream_dxo(
    conversation_id: str, user_query: str, mode: str = "dxo"
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream DxO stages via SSE events and persist assistant message when complete."""
    # Stage 1: Draft
    yield {"type": "stage1_start"}
    s1, settings, primary, critics = await run_stage1_dxo(user_query, mode)
    if not primary:
        yield {"type": "error", "message": "No agents configured."}
        return
    yield {"type": "stage1_complete", "data": s1}

    # Stage 2: Critiques
    yield {"type": "stage2_start"}
    draft_text = s1[0]["response"]
    s2 = await run_stage2_dxo(draft_text, primary, critics)
    metadata_partial = {
        "dxo": {
            "primary": primary["name"],
            "critics": [c["name"] for c in critics],
        }
    }
    yield {"type": "stage2_complete", "data": s2, "metadata": metadata_partial}

    # Stage 3: Optimize
    yield {"type": "stage3_start"}
    s3, metadata = await run_stage3_dxo(draft_text, s2, primary, settings)
    yield {"type": "stage3_complete", "data": s3}

    # Persist
    storage.add_assistant_message(conversation_id, s1, s2, s3)
    yield {"type": "complete"}
