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
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FutureTimeoutError

from dotenv import load_dotenv

load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client import get_client, MODEL_NAME

# NOTE: deliberately NOT a module-level `client = get_client()` shared
# across calls here (unlike interpreter.py/generator.py/critic.py,
# where that's fine for their synchronous calls). See _ask_about_runs
# below for why the async path specifically needs a fresh client per
# call.

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
    # A fresh client per call, not a shared module-level one: the
    # genai Client's async path (.aio) lazily binds its underlying
    # httpx connection pool to whichever event loop is running the
    # first time it's actually used. asyncio.run() (below) creates a
    # new loop per call and closes it when the call finishes; a client
    # reused across multiple such calls ends up holding a pooled
    # connection tied to a now-closed loop, and cleaning that up raises
    # `RuntimeError: Event loop is closed` deep inside httpx - which is
    # exactly what surfaced (wrapped in nested TaskGroup
    # ExceptionGroups from anyio/mcp) as "unhandled errors in a
    # TaskGroup" in the UI. Confirmed via the actual traceback, not
    # guessed. A fresh client has no stale pooled connection to clean
    # up, so this can't happen. This is also exactly why `python
    # insights.py` standalone always worked: it calls this once per
    # process, so there's only ever one loop, period.
    # Granular per-phase timing to server logs (not shown to users) -
    # kept permanently, not just for this investigation: the "MCP tool
    # calls finish but the final response never arrives" hang is still
    # unexplained (see InsightsTimeout below), and this is what
    # actually pinpointed that the credential/get_client() step is NOT
    # the bottleneck (consistently <1s, before and after caching it -
    # see client.py) while generate_content varies wildly call to call
    # (3s-44s+ even on calls that eventually succeed).
    t_start = time.monotonic()
    client = get_client()
    t_client = time.monotonic()
    print(f"[insights timing] get_client(): {t_client - t_start:.2f}s", flush=True)

    async with stdio_client(_MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            t_mcp_init = time.monotonic()
            print(f"[insights timing] MCP connect+initialize: {t_mcp_init - t_client:.2f}s", flush=True)

            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=f"{_SYSTEM_CONTEXT}\n\nQuestion: {question}",
                config={"tools": [session]},
            )
            t_done = time.monotonic()
            print(f"[insights timing] generate_content (incl. tool calls): {t_done - t_mcp_init:.2f}s", flush=True)
            print(f"[insights timing] TOTAL: {t_done - t_start:.2f}s", flush=True)
            return response.text


_QUERY_TIMEOUT_S = 45  # was 30: real timing showed a legitimate, successful
# call taking 44.23s (several tool-calling rounds) - 30s would have
# aborted that as a false-positive "timeout" before it ever got a
# chance to finish. 45s covers that with a little margin while still
# bounding the genuine hang to a reasonable, visible wait.


class InsightsTimeout(Exception):
    """Raised when a query doesn't come back within _QUERY_TIMEOUT_S
    seconds. There's a separate, still-undiagnosed intermittent hang
    where the MCP tool calls complete cleanly but the final Gemini
    response never arrives - no exception, just silence. Rather than
    that freezing the UI indefinitely, callers should catch this and
    show a clear "try again" message instead."""


def _run_bounded(question: str) -> str:
    async def _with_asyncio_timeout():
        return await asyncio.wait_for(
            _ask_about_runs(question), timeout=_QUERY_TIMEOUT_S
        )

    return asyncio.run(_with_asyncio_timeout())


def ask_about_runs(question: str) -> str:
    """Synchronous wrapper — call this from app.py or elsewhere.

    Runs the call inside a dedicated worker thread (its own thread, its
    own event loop via asyncio.run()) rather than directly on the
    caller's thread - cheap extra isolation from whatever event loop
    Streamlit's own server is running elsewhere in the process, on top
    of the fresh-client fix in _ask_about_runs.

    Bounded by _QUERY_TIMEOUT_S two different ways, because a hang can
    fail to respond to cancellation depending on where it's actually
    stuck:
      1. `asyncio.wait_for` inside the worker thread - handles a call
         that's merely slow but still yielding control back to the
         event loop normally; this cancels it cleanly.
      2. `Future.result(timeout=...)` on this thread, as a hard
         backstop - if the hang is a true block that never yields
         (which asyncio-level cancellation can't touch, by definition -
         confirmed this class of hang exists for this exact call via
         testing), this stops the CALLER from waiting rather than
         relying on the stuck code to cooperate. The worker thread
         itself is abandoned (Python threads can't be force-killed) and
         the pool is shut down without waiting for it, so a stuck call
         can't block the rest of the app - it just leaks one thread
         until it eventually resolves or the process exits.
    Either path raises InsightsTimeout.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_run_bounded, question)
    try:
        return future.result(timeout=_QUERY_TIMEOUT_S + 5)
    except (asyncio.TimeoutError, _FutureTimeoutError):
        raise InsightsTimeout(
            f"Query took longer than {_QUERY_TIMEOUT_S}s to answer."
        ) from None
    finally:
        pool.shutdown(wait=False)


if __name__ == "__main__":
    print(ask_about_runs("How many runs have been approved on the first pass, and how many needed a retry?"))