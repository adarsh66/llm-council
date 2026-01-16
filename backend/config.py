"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# Azure AI Foundry endpoint (multi-model inference endpoint)
AZURE_INFERENCE_ENDPOINT = os.getenv("AZURE_INFERENCE_ENDPOINT")

# Council members - list of Azure AI Foundry model names
COUNCIL_MODELS = [
    "Phi-4",
    "gpt-5-mini",
    "gpt-4.1",
    "DeepSeek-R1",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "gpt-5"

# Model used for generating conversation titles (fast and cheap)
TITLE_MODEL = "gpt-5-mini"

# Data directory for conversation storage
#
# NOTE: On Azure App Service with `WEBSITE_RUN_FROM_PACKAGE=1`, the app content
# can be read-only. Use a writable path (e.g., `/home/data/conversations`) via
# the `DATA_DIR` App Setting.
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")
