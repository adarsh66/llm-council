from __future__ import annotations

from typing import Any, Dict, List, Tuple, AsyncGenerator

from ..settings import get_effective_settings
from .. import storage
from .common import build_agents, make_messages, run_agent


async def run_stage1_ensemble(
    user_query: str, mode: str = "ensemble"
) -> Tuple[List, Dict, List]:
    """Stage 1: Parallel responses from all agents.

    Returns (stage1_data, settings, agents).
    """
    settings = get_effective_settings(mode)
    agents = build_agents(settings)
    if not agents:
        return [], settings, []

    stage1: List[Dict[str, Any]] = []
    for agent in agents:
        msg = make_messages(agent.get("system_prompt"), user_query)
        resp = await run_agent(agent["name"], msg)
        stage1.append(
            {"model": agent["name"], "response": (resp or {}).get("content", "")}
        )

    return stage1, settings, agents


async def run_stage2_ensemble(
    stage1: List, settings: Dict, agents: List
) -> Tuple[List, str]:
    """Stage 2: Aggregation scores by chairman.

    Returns (stage2_data, chairman_model).
    """
    chairman_model = settings.get("chairman_model") or (
        agents[0]["name"] if agents else None
    )
    scores: List[Dict[str, Any]] = []
    if chairman_model:
        score_prompt = (
            "Evaluate the following responses and assign a score (0-100) to each for quality and correctness."
            " Return a JSON-like list: [{model: name, score: number}].\n\n"
            + "\n\n".join([f"[{item['model']}]\n{item['response']}" for item in stage1])
        )
        s_msg = make_messages(None, score_prompt)
        s_resp = await run_agent(chairman_model, s_msg)
        raw = (s_resp or {}).get("content", "")
        # naive extraction of numbers; real impl should parse JSON
        import re

        for item in stage1:
            model = item["model"]
            # look for pattern 'model: <name> ... score: <num>'
            m = re.search(
                rf"{re.escape(model)}.*?(\d+)", raw, flags=re.IGNORECASE | re.DOTALL
            )
            score = int(m.group(1)) if m else 50
            scores.append({"model": model, "score": score})
    return scores, chairman_model


async def run_stage3_ensemble(
    stage1: List, chairman_model: str, agents: List
) -> Tuple[Dict, Dict]:
    """Stage 3: Synthesis by chairman.

    Returns (stage3_data, metadata).
    """
    synth_prompt = (
        "Produce a final answer that reflects the best aspects of the responses,"
        " weighting by their scores if provided.\n\n"
        + "\n\n".join([f"[{item['model']}]\n{item['response']}" for item in stage1])
    )
    s_msg = make_messages(None, synth_prompt)
    s_resp = await run_agent(chairman_model or agents[0]["name"], s_msg)
    final_text = (s_resp or {}).get("content", "")
    stage3 = {"model": chairman_model or agents[0]["name"], "response": final_text}

    metadata = {"ensemble": {"chairman": chairman_model, "count": len(agents)}}
    return stage3, metadata


async def run_ensemble(
    user_query: str, mode: str = "ensemble"
) -> Tuple[List, List, Dict, Dict]:
    """Run Ensemble: parallel responses then aggregate and synthesize."""
    s1, settings, agents = await run_stage1_ensemble(user_query, mode)
    if not agents:
        return [], [], {"model": "error", "response": "No agents configured."}, {}

    s2, chairman_model = await run_stage2_ensemble(s1, settings, agents)
    s3, metadata = await run_stage3_ensemble(s1, chairman_model, agents)

    return s1, s2, s3, metadata


async def stream_ensemble(
    conversation_id: str,
    user_query: str,
    mode: str = "ensemble",
) -> AsyncGenerator[Dict[str, Any], None]:
    # Stage 1: Parallel responses
    yield {"type": "stage1_start"}
    s1, settings, agents = await run_stage1_ensemble(user_query, mode)
    if not agents:
        yield {"type": "error", "message": "No agents configured."}
        return
    yield {"type": "stage1_complete", "data": s1}

    # Stage 2: Aggregation
    yield {"type": "stage2_start"}
    s2, chairman_model = await run_stage2_ensemble(s1, settings, agents)
    metadata = {"ensemble": {"chairman": chairman_model, "count": len(agents)}}
    yield {"type": "stage2_complete", "data": s2, "metadata": metadata}

    # Stage 3: Synthesis
    yield {"type": "stage3_start"}
    s3, _ = await run_stage3_ensemble(s1, chairman_model, agents)
    yield {"type": "stage3_complete", "data": s3}

    storage.add_assistant_message(conversation_id, s1, s2, s3)
    yield {"type": "complete"}
