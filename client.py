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

import functools
import json
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()

import google.auth
from google import genai
from google.oauth2 import service_account
from google.genai import types

# Check aistudio.google.com / Vertex AI docs for the current valid
# model name before relying on this — these change over time.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

_USE_VERTEX_AI = os.environ.get("USE_VERTEX_AI", "false").lower() == "true"


@functools.lru_cache(maxsize=1)
def _cached_vertex_credentials():
    """
    Resolves Vertex AI credentials ONCE per process and reuses the
    result, rather than re-resolving them on every get_client() call.

    This matters now that get_client() is called fresh per call from
    insights.py (see its docstring — a fresh genai.Client is needed
    per event loop to avoid a "RuntimeError: Event loop is closed"
    bug). Credentials and the Client are two different things: a
    Credentials object manages its own token refresh internally
    (cheap, only refetches when actually near expiry), so there's no
    reason re-deriving it needs to happen more than once — building a
    service-account Credentials object from JSON, or running full ADC
    discovery (checking env vars, the gcloud SDK's cached user
    credentials file, then the GCE/Cloud Run metadata server) plus an
    actual OAuth token fetch, is real work worth doing exactly once.

    On a real GCP environment (or a local machine with
    `gcloud auth application-default login` run), Application
    Default Credentials just work.

    On a platform with no metadata server (e.g. Streamlit Community
    Cloud), ADC discovery fails. In that case, set
    GCP_SERVICE_ACCOUNT_JSON to the full contents of a service
    account key file (as a secret, never committed to the repo) and
    this builds explicit credentials from it instead.
    """
    raw_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if raw_json:
        info = json.loads(raw_json)
        return service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return credentials


def get_client() -> genai.Client:
    """Returns a configured genai.Client for whichever backend is active.

    Building a fresh genai.Client instance here is cheap and, for
    insights.py's async path, actually required (see
    _cached_vertex_credentials' docstring) — it's the credential
    resolution behind it that's worth caching, which
    _cached_vertex_credentials handles.
    """
    if _USE_VERTEX_AI:
        project = os.environ["GOOGLE_CLOUD_PROJECT"]
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            credentials=_cached_vertex_credentials(),
        )

    api_key = os.environ["GOOGLE_API_KEY"]
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2,
                http_status_codes=[429, 503],
            )
        ),
    )


def using_vertex_ai() -> bool:
    """Lets calling code/log output report which backend is active."""
    return _USE_VERTEX_AI