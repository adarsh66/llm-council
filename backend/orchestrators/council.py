"""LLM Council orchestration: 3-stage peer evaluation and synthesis."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, AsyncGenerator
import asyncio
import re
from collections import defaultdict

from ..settings import get_effective_settings
from ..config import CHAIRMAN_MODEL, TITLE_MODEL
from .. import storage
from .common import build_agents, make_messages, run_agent


async def run_stage1_council(
    user_query: str, mode: str = "council"
) -> Tuple[List, List]:
    """Stage 1: Collect individual responses from all council models.

    Returns (stage1_data, agents).
    """
    settings = get_effective_settings(mode)
    agents = build_agents(settings)
    if not agents:
        return [], []

    async def _call(agent_cfg: Dict[str, Any]):
        name = agent_cfg.get("name", "")
        if not name:
            return None, None
        sys_prompt = (agent_cfg.get("system_prompt") or "").strip()
        messages = make_messages(sys_prompt, user_query)
        resp = await run_agent(name, messages)
        return name, resp

    responses = await asyncio.gather(*[_call(a) for a in agents])

    # Format results
    stage1_results = []
    for model, response in responses:
        if response is not None:
            stage1_results.append(
                {"model": model, "response": response.get("content", "")}
            )

    return stage1_results, agents


async def run_stage2_council(
    user_query: str, stage1_results: List[Dict[str, Any]], agents: List
) -> Tuple[List, Dict[str, str]]:
    """Stage 2: Each model ranks the anonymized responses.

    Returns (stage2_data, label_to_model_mapping).
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result["model"]
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join(
        [
            f"Response {label}:\n{result['response']}"
            for label, result in zip(labels, stage1_results)
        ]
    )

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    async def _call(agent_cfg: Dict[str, Any]):
        name = agent_cfg.get("name", "")
        if not name:
            return None, None
        sys_prompt = (agent_cfg.get("system_prompt") or "").strip()
        messages = make_messages(sys_prompt, ranking_prompt)
        resp = await run_agent(name, messages)
        return name, resp

    responses = await asyncio.gather(*[_call(a) for a in agents])
    responses = [(n, r) for n, r in responses if n is not None]

    # Format results
    stage2_results = []
    for model, response in responses:
        if response is not None:
            full_text = response.get("content", "")
            parsed = _parse_ranking_from_text(full_text)
            stage2_results.append(
                {"model": model, "ranking": full_text, "parsed_ranking": parsed}
            )

    return stage2_results, label_to_model


async def run_stage3_council(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    settings: Dict,
) -> Tuple[Dict, Dict]:
    """Stage 3: Chairman synthesizes final response.

    Returns (stage3_data, metadata).
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join(
        [
            f"Model: {result['model']}\nResponse: {result['response']}"
            for result in stage1_results
        ]
    )

    stage2_text = "\n\n".join(
        [
            f"Model: {result['model']}\nRanking: {result['ranking']}"
            for result in stage2_results
        ]
    )

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's
question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive,
accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = make_messages(None, chairman_prompt)

    # Query the chairman model
    chairman_model = settings.get("chairman_model") or CHAIRMAN_MODEL
    response = await run_agent(chairman_model, messages)

    if response is None:
        stage3 = {
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis.",
        }
    else:
        stage3 = {"model": chairman_model, "response": response.get("content", "")}

    metadata = {}
    return stage3, metadata


def _parse_ranking_from_text(ranking_text: str) -> List[str]:
    """Parse the FINAL RANKING section from model response."""
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r"\d+\.\s*Response [A-Z]", ranking_section)
            if numbered_matches:
                result = []
                for m in numbered_matches:
                    match = re.search(r"Response [A-Z]", m)
                    if match:
                        result.append(match.group())
                return result
            matches = re.findall(r"Response [A-Z]", ranking_section)
            return matches

    matches = re.findall(r"Response [A-Z]", ranking_text)
    return matches


def _calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]], label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Calculate aggregate rankings across all models."""
    model_positions: Dict[str, List[int]] = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking["ranking"]
        parsed_ranking = _parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append(
                {
                    "model": model,
                    "average_rank": round(avg_rank, 2),
                    "rankings_count": len(positions),
                }
            )

    aggregate.sort(key=lambda x: x["average_rank"])
    return aggregate


async def generate_conversation_title(user_query: str, mode: str = "council") -> str:
    """Generate a short title for a conversation based on the first user message."""
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = make_messages(None, title_prompt)

    settings = get_effective_settings(mode)
    title_model = settings.get("title_model") or TITLE_MODEL
    response = await run_agent(title_model, messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = response.get("content", "New Conversation").strip()
    title = title.strip("\"'")

    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_council(
    user_query: str, mode: str = "council"
) -> Tuple[List, List, Dict, Dict]:
    """Run the complete 3-stage council process.

    Returns a tuple (stage1, stage2, stage3, metadata) compatible with non-stream API.
    """
    s1, agents = await run_stage1_council(user_query, mode)
    if not agents:
        return (
            [],
            [],
            {
                "model": "error",
                "response": "All models failed to respond. Please try again.",
            },
            {},
        )

    s2, label_to_model = await run_stage2_council(user_query, s1, agents)

    settings = get_effective_settings(mode)
    s3, _ = await run_stage3_council(user_query, s1, s2, settings)

    aggregate_rankings = _calculate_aggregate_rankings(s2, label_to_model)
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
    }

    return s1, s2, s3, metadata


async def stream_council(
    conversation_id: str, user_query: str, mode: str = "council"
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream council stages via SSE events and persist assistant message when complete."""
    # Stage 1: Collect responses
    yield {"type": "stage1_start"}
    s1, agents = await run_stage1_council(user_query, mode)
    if not agents:
        yield {"type": "error", "message": "All models failed to respond."}
        return
    yield {"type": "stage1_complete", "data": s1}

    # Stage 2: Rankings
    yield {"type": "stage2_start"}
    s2, label_to_model = await run_stage2_council(user_query, s1, agents)
    aggregate_rankings = _calculate_aggregate_rankings(s2, label_to_model)
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
    }
    yield {"type": "stage2_complete", "data": s2, "metadata": metadata}

    # Stage 3: Synthesis
    yield {"type": "stage3_start"}
    settings = get_effective_settings(mode)
    s3, _ = await run_stage3_council(user_query, s1, s2, settings)
    yield {"type": "stage3_complete", "data": s3}

    storage.add_assistant_message(conversation_id, s1, s2, s3)
    yield {"type": "complete"}
