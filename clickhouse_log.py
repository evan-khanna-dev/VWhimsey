"""
ClickHouse run logging + history
------------------------------------
Writes every pipeline run (Interpreter -> Generator -> Critic) into the
self-hosted ClickHouse instance, and reads it back for the Gallery
view — both by you manually and by the ClickHouse MCP server at
runtime (the actual hackathon requirement: an agent that queries this
data, not just a database quietly filling up in the background).

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

_RUNS_TABLE = "vfx_pipeline.runs"

# ADD COLUMN IF NOT EXISTS is idempotent and cheap in ClickHouse (a
# metadata-only change for MergeTree tables), but there's still no
# reason to re-run it on every single call in a process that might
# handle many runs/gallery loads - once per process lifetime is enough.
_schema_ensured = False


def _get_client():
    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def _ensure_schema(client) -> None:
    global _schema_ensured
    if _schema_ensured:
        return
    client.command(
        f"ALTER TABLE {_RUNS_TABLE} ADD COLUMN IF NOT EXISTS svg_code String DEFAULT ''"
    )
    _schema_ensured = True


def log_run(
    movement_description: str,
    approved: bool,
    passes_used: int,
    interpreter_output: dict,
    critique_notes: str,
    svg_code: str = "",
) -> None:
    """
    Inserts one row representing a completed pipeline run. Failures
    here are logged but never raised — a logging problem shouldn't
    break the actual VFX generation for the user.

    svg_code is stored alongside the metadata (added via an idempotent
    migration below) so the Gallery view can render a real thumbnail
    for runs going forward. It's plain generated SVG text - typically
    a few KB - well within what a ClickHouse String column is meant
    for, not the kind of size that needs special handling. Runs logged
    before this column existed just read back as an empty string; the
    Gallery falls back to a shape summary for those.
    """
    try:
        client = _get_client()
        _ensure_schema(client)
        client.insert(
            _RUNS_TABLE,
            [[
                movement_description,
                1 if approved else 0,
                passes_used,
                json.dumps(interpreter_output),
                critique_notes or "",
                svg_code or "",
            ]],
            column_names=[
                "movement_description",
                "approved",
                "passes_used",
                "interpreter_output",
                "critique_notes",
                "svg_code",
            ],
        )
    except Exception as e:
        print(f"[clickhouse_log] Failed to log run (non-fatal): {e}")


def fetch_runs(approved: bool | None = None, limit: int = 60) -> list[dict]:
    """
    Returns the most recent pipeline runs (newest first) for the
    Gallery view. `approved=True`/`False` filters to only approved or
    only rejected runs; leaving it as None returns both.

    Returns [] (rather than raising) if ClickHouse is unreachable,
    same non-fatal policy as log_run — the Gallery just shows an empty
    state instead of breaking the page.
    """
    try:
        client = _get_client()
        _ensure_schema(client)
        where = ""
        params = {"limit": limit}
        if approved is not None:
            where = "WHERE approved = {approved:UInt8}"
            params["approved"] = 1 if approved else 0
        result = client.query(
            f"""
            SELECT run_id, timestamp, movement_description, approved,
                   passes_used, interpreter_output, critique_notes, svg_code
            FROM {_RUNS_TABLE}
            {where}
            ORDER BY timestamp DESC
            LIMIT {{limit:UInt32}}
            """,
            parameters=params,
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]
    except Exception as e:
        print(f"[clickhouse_log] Failed to fetch run history (non-fatal): {e}")
        return []