"""
Gallery — browsable history of past pipeline runs
-----------------------------------------------------
Reads from the same `vfx_pipeline.runs` ClickHouse table clickhouse_log.py
writes to and insights.py's MCP agent queries. Fetches are a plain,
deterministic "most recent N rows, optionally filtered by approved" —
there's no natural-language question to resolve, so this goes straight
through clickhouse-connect (same pattern clickhouse_log.py already
uses) rather than through the MCP+Gemini round-trip insights.py uses
for open-ended questions. That round-trip exists specifically to turn
an ambiguous question into a query; a fixed list-view query doesn't
have that ambiguity, so routing it through an LLM would only add
latency, API cost, and a chance the model doesn't call the right tool
- for a change, not a benefit.

Cards are text-only (description, approval, passes, timestamp, and
the critique notes behind a retry) - no thumbnail or metadata-summary
preview.
"""

from html import escape

import streamlit as st

from clickhouse_log import fetch_runs


@st.cache_data(ttl=20, show_spinner=False)
def _cached_fetch_runs(approved: bool | None, limit: int) -> list[dict]:
    return fetch_runs(approved=approved, limit=limit)


def invalidate_cache() -> None:
    """Clears the cached run list. The 20s TTL above is just a safety
    net for repeated views / other runs landing elsewhere; it's too
    slow for the case that actually matters most - the run you just
    generated should show up in the Gallery immediately, not after a
    wait. Call this right after a run finishes (see app.py)."""
    _cached_fetch_runs.clear()


def _render_card_html(run: dict) -> str:
    description = escape(run.get("movement_description") or "(no description)")
    approved = bool(run.get("approved"))
    passes_used = run.get("passes_used") or 1
    timestamp = run.get("timestamp")
    timestamp_str = timestamp.strftime("%b %d, %Y — %H:%M") if timestamp else ""
    critique_notes = (run.get("critique_notes") or "").strip()

    badge_html = (
        '<span class="vwhim-badge vwhim-badge--ok">✓ Approved</span>'
        if approved
        else '<span class="vwhim-badge vwhim-badge--warn">⚠ Not approved</span>'
    )

    notes_html = ""
    if critique_notes:
        notes_html = (
            '<div class="vwhim-run-notes">'
            '<span class="vwhim-run-notes-label">Retry triggered by:</span> '
            f"{escape(critique_notes)}"
            "</div>"
        )

    pass_label = "pass" if passes_used == 1 else "passes"

    return f"""
<div class="vwhim-run-card">
  <div class="vwhim-run-body">
    <p class="vwhim-run-desc">{description}</p>
    <div class="vwhim-run-meta">
      {badge_html}
      <span class="vwhim-run-passes">{passes_used} {pass_label}</span>
    </div>
    <p class="vwhim-run-time">{timestamp_str}</p>
    {notes_html}
  </div>
</div>
"""


def render_gallery() -> None:
    """Mounts the full Gallery section: filter/sort controls, the card
    grid, and the empty state - the only thing app.py needs to call."""
    filter_col, sort_col = st.columns(2)
    with filter_col:
        filter_choice = st.selectbox(
            "Filter",
            ["All runs", "Approved only", "Not approved only"],
            key="gallery_filter",
        )
    with sort_col:
        sort_choice = st.selectbox(
            "Sort",
            ["Most recent first", "Oldest first"],
            key="gallery_sort",
        )

    approved_filter = {
        "All runs": None,
        "Approved only": True,
        "Not approved only": False,
    }[filter_choice]

    runs = _cached_fetch_runs(approved_filter, 60)
    if sort_choice == "Oldest first":
        runs = list(reversed(runs))

    if not runs:
        st.markdown(
            '<p class="vwhim-run-empty">No runs to show yet — generate '
            "your first animation above and it'll appear here.</p>",
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(3)
    for i, run in enumerate(runs):
        with cols[i % 3]:
            st.markdown(_render_card_html(run), unsafe_allow_html=True)
