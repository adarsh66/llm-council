# Copilot instructions

This app is a simple local web UI that sends user prompts to multiple LLMs through OpenRouter, has each model review peers, and a Chairman model compiles the final reply. It’s intended to be deployed on Azure App Services.

## Workflow overview
- Stage 1: Send the user query to each council model independently and display tabbed responses.
- Stage 2: Share anonymized peer responses with each model for ranking and critique.
- Stage 3: A designated Chairman model synthesizes the final answer.

## Tech Stack
- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in local `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript

## Setup notes
- Create `.env` in repo root with `OPENROUTER_API_KEY=sk-or-v1-...`.
- Typical run: `uv run python -m backend.main` (backend) and `npm run dev` in `frontend`.


## Azure guidance
- Target hosting: Azure App Services.
- Persist conversation JSON under `data/conversations/` (consider Azure Files if needed).

## LLM endpoints
- Primary: OpenRouter for multi-provider access.
- If using Azure AI Foundry endpoints, mirror the same request/response shapes and routing expectations.

