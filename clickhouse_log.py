"""
ClickHouse run logging
-------------------------
Logs every pipeline run (Interpreter -> Generator -> Critic) into the
self-hosted ClickHouse instance, so run history can be queried later
— both by you manually and by the ClickHouse MCP server at runtime
(the actual hackathon requirement: an agent that queries this data,
not just a database quietly filling up in the background).

Requires these in .env:
    CLICKHOUSE_HOST=your-vm-external-ip
    CLICKHOUSE_PORT=8123
    CLICKHOUSE_USER=clickhouse_admin
    CLICKHOUSE_PASSWORD=whatever-you-set-earlier
"""

import json
import os

import clickhouse_connect
from dotenv import load_dotenv

load_dotenv()


def _get_client():
    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def log_run(
    movement_description: str,
    approved: bool,
    passes_used: int,
    interpreter_output: dict,
    critique_notes: str,
) -> None:
    """
    Inserts one row representing a completed pipeline run. Failures
    here are logged but never raised — a logging problem shouldn't
    break the actual VFX generation for the user.
    """
    try:
        client = _get_client()
        client.insert(
            "vfx_pipeline.runs",
            [[
                movement_description,
                1 if approved else 0,
                passes_used,
                json.dumps(interpreter_output),
                critique_notes or "",
            ]],
            column_names=[
                "movement_description",
                "approved",
                "passes_used",
                "interpreter_output",
                "critique_notes",
            ],
        )
    except Exception as e:
        print(f"[clickhouse_log] Failed to log run (non-fatal): {e}")