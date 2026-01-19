from __future__ import annotations

from typing import Any, Dict, List, Tuple, AsyncGenerator

from ..settings import get_effective_settings
from .. import storage
from .common import build_agents, make_messages, run_agent


async def run_stage1_sequential(
    user_query: str, mode: str = "sequential"
) -> Tuple[List, Dict, List]:
    """Stage 1: Analysis by first agent.

    Returns (stage1_data, settings, agents).
    """
    settings = get_effective_settings(mode)
    agents = build_agents(settings)
    if not agents:
        return [], settings, []

    first = agents[0]
    analysis_prompt = (
        "Analyze the question and outline a plan to answer it step by step."
        f"\n\nQuestion:\n{user_query}"
    )
    s1_msg = make_messages(first.get("system_prompt"), analysis_prompt)
    s1_resp = await run_agent(first["name"], s1_msg)
    analysis_text = (s1_resp or {}).get("content", "")
    stage1 = [{"model": first["name"], "response": analysis_text}]

    return stage1, settings, agents


async def run_stage2_sequential(analysis_text: str, agents: List) -> List:
    """Stage 2: Execute sequentially through remaining agents.

    Returns stage2_data (list of outputs).
    """
    outputs: List[Dict[str, Any]] = []
    prev_output = analysis_text
    for idx, agent in enumerate(agents[1:], start=2):
        step_prompt = (
            f"Previous output:\n{prev_output}\n\n"
            "Improve or extend it according to the plan, ensuring correctness and clarity."
        )
        s_msg = make_messages(agent.get("system_prompt"), step_prompt)
        s_resp = await run_agent(agent["name"], s_msg)
        out_text = (s_resp or {}).get("content", "")
        outputs.append({"step": idx, "model": agent["name"], "output": out_text})
        prev_output = out_text or prev_output
    return outputs


async def run_stage3_sequential(
    prev_output: str, agents: List, settings: Dict
) -> Tuple[Dict, Dict]:
    """Stage 3: Final synthesis (optional chairman).

    Returns (stage3_data, metadata).
    """
    final_model = agents[-1]["name"]
    final_text = prev_output
    chairman_model = settings.get("chairman_model")
    if chairman_model:
        synth_prompt = (
            "As chairman, produce the final answer, improving quality and correctness if needed.\n\n"
            f"Last output:\n{prev_output}"
        )
        s_msg = make_messages(None, synth_prompt)
        s_resp = await run_agent(chairman_model, s_msg)
        final_model = chairman_model
        final_text = (s_resp or {}).get("content", prev_output)

    stage3 = {"model": final_model, "response": final_text}
    metadata = {"sequential": {"order": [a["name"] for a in agents]}}
    return stage3, metadata


async def run_sequential(
    user_query: str, mode: str = "sequential"
) -> Tuple[List, List, Dict, Dict]:
    """Run a sequential pipeline across agents."""
    s1, settings, agents = await run_stage1_sequential(user_query, mode)
    if not agents:
        return [], [], {"model": "error", "response": "No agents configured."}, {}

    analysis_text = s1[0]["response"]
    s2 = await run_stage2_sequential(analysis_text, agents)
    prev_output = s2[-1]["output"] if s2 else analysis_text
    s3, metadata = await run_stage3_sequential(prev_output, agents, settings)

    return s1, s2, s3, metadata


async def stream_sequential(
    conversation_id: str,
    user_query: str,
    mode: str = "sequential",
) -> AsyncGenerator[Dict[str, Any], None]:
    # Stage 1: Analysis
    yield {"type": "stage1_start"}
    s1, settings, agents = await run_stage1_sequential(user_query, mode)
    if not agents:
        yield {"type": "error", "message": "No agents configured."}
        return
    yield {"type": "stage1_complete", "data": s1}

    # Stage 2: Sequential execution
    yield {"type": "stage2_start"}
    analysis_text = s1[0]["response"]
    s2 = await run_stage2_sequential(analysis_text, agents)
    metadata = {"sequential": {"order": [a["name"] for a in agents]}}
    yield {"type": "stage2_complete", "data": s2, "metadata": metadata}

    # Stage 3: Final synthesis
    yield {"type": "stage3_start"}
    prev_output = s2[-1]["output"] if s2 else analysis_text
    s3, _ = await run_stage3_sequential(prev_output, agents, settings)
    yield {"type": "stage3_complete", "data": s3}

    storage.add_assistant_message(conversation_id, s1, s2, s3)
    yield {"type": "complete"}
