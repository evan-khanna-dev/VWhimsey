"""
Shared Gemini client
-----------------------
One place that decides whether the pipeline talks to Gemini via the
plain AI Studio API key (fast to set up, no billing) or via Vertex AI
Agent Platform (what the hackathon rules actually require for
submission: "Gemini models on Agent Platform").

Toggle with an env var — no code changes needed elsewhere once
billing is sorted:

    USE_VERTEX_AI=false   -> AI Studio API key (local dev/testing)
    USE_VERTEX_AI=true    -> Vertex AI (requires GOOGLE_CLOUD_PROJECT,
                              a billing-linked project, and
                              `gcloud auth application-default login`)

interpreter.py, generator.py, and critic.py all import get_client()
and MODEL_NAME from here instead of constructing their own client.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google import genai

# Check aistudio.google.com / Vertex AI docs for the current valid
# model name before relying on this — these change over time.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

_USE_VERTEX_AI = os.environ.get("USE_VERTEX_AI", "false").lower() == "true"


def get_client() -> genai.Client:
    """Returns a configured genai.Client for whichever backend is active."""
    if _USE_VERTEX_AI:
        project = os.environ["GOOGLE_CLOUD_PROJECT"]
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        return genai.Client(vertexai=True, project=project, location=location)

    api_key = os.environ["GOOGLE_API_KEY"]
    return genai.Client(api_key=api_key)


def using_vertex_ai() -> bool:
    """Lets calling code/log output report which backend is active."""
    return _USE_VERTEX_AI