"""
Insights Agent
----------------
Connects Gemini to the mcp-clickhouse MCP server (spawned as a
subprocess) so the model can query real pipeline run history stored
in ClickHouse — approvals, rejections, passes used, revision notes —
and answer questions about it in natural language.

This is the piece that satisfies the hackathon's actual Grafana...
er, ClickHouse requirement: an agent that ACTIVELY CALLS the MCP
server at runtime, not just a database quietly sitting there.

Requires the same CLICKHOUSE_* vars already in .env, plus:
    pip install mcp-clickhouse mcp
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client import get_client, MODEL_NAME

client = get_client()

# IMPORTANT: env here must include the full parent environment (PATH,
# etc.) — passing only the CLICKHOUSE_* vars replaces the subprocess's
# entire environment and causes it to fail to even launch on some
# systems (observed on Windows as an immediate "Connection closed").
_MCP_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "mcp_clickhouse.main"],
    env={
        **os.environ,
        "CLICKHOUSE_HOST": os.environ["CLICKHOUSE_HOST"],
        "CLICKHOUSE_PORT": os.environ.get("CLICKHOUSE_PORT", "8123"),
        "CLICKHOUSE_USER": os.environ["CLICKHOUSE_USER"],
        "CLICKHOUSE_PASSWORD": os.environ["CLICKHOUSE_PASSWORD"],
        # Our self-hosted VM serves plain HTTP on 8123, no TLS — the
        # package defaults CLICKHOUSE_SECURE to true (HTTPS), which
        # causes an immediate silent crash ("Connection closed") if
        # left unset.
        "CLICKHOUSE_SECURE": "false",
        "CLICKHOUSE_VERIFY": "false",
        # CRITICAL: FastMCP prints an ASCII-art startup banner to
        # stdout by default, which corrupts the stdio JSON-RPC stream
        # and causes an immediate "Connection closed" error on the
        # client side. This must be disabled.
        "FASTMCP_SHOW_SERVER_BANNER": "false",
        "FASTMCP_SHOW_CLI_BANNER": "false",
        "FASTMCP_QUIET": "1",
    },
)

_SYSTEM_CONTEXT = """
You are the Insights agent for a sketch-to-VFX pipeline. You have
access to a ClickHouse database with a table `vfx_pipeline.runs`
containing columns: run_id, timestamp, movement_description,
approved (1/0), passes_used, interpreter_output (JSON string),
critique_notes.

Use the available ClickHouse tools to query this table and answer
the user's question about past pipeline runs. Be specific and cite
real numbers from the data, not guesses.
"""


async def _ask_about_runs(question: str) -> str:
    async with stdio_client(_MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=f"{_SYSTEM_CONTEXT}\n\nQuestion: {question}",
                config={"tools": [session]},
            )
            return response.text


def ask_about_runs(question: str) -> str:
    """Synchronous wrapper — call this from app.py or elsewhere."""
    return asyncio.run(_ask_about_runs(question))


if __name__ == "__main__":
    print(ask_about_runs("How many runs have been approved on the first pass, and how many needed a retry?"))