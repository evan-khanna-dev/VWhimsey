"""
Sketch-to-VFX — local UI
--------------------------
A simple Streamlit front end for the pipeline so you don't have to
hand-edit interpreter.py/orchestrator.py every time you want to test
a new sketch. Upload a photo of your sketch, describe the intended
movement, hit generate, and preview the resulting animated SVG
directly in the browser.

Run with:
    streamlit run app.py
"""

import tempfile

import streamlit as st

from orchestrator import run_pipeline
from insights import ask_about_runs
from theme import (
    THEME_CSS,
    render_background,
    render_hero,
    status_badge,
    empty_state,
)

st.set_page_config(page_title="VWhimsey", layout="wide")

st.markdown(render_background(), unsafe_allow_html=True)
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown(
    render_hero(
        "VWhimsey",
        "Draw something rough, describe how it moves, get real, "
        "exportable motion back.",
    ),
    unsafe_allow_html=True,
)

# Output gets the wider column: the generated result is the payoff and
# should visually lead, per DESIGN.md. Input stays lightweight/secondary.
col_input, col_output = st.columns([2, 3], gap="large")

with col_input, st.container(key="vwhim_input_panel"):
    st.markdown(
        '<p class="vwhim-panel-eyebrow">Step 1 — 2</p>'
        '<p class="vwhim-panel-title">Your sketch</p>',
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Sketch photo", type=["jpg", "jpeg", "png"]
    )
    movement_description = st.text_area(
        "Describe the intended movement",
        placeholder=(
            "e.g. circle pulses, squiggle whips like a flame trail"
        ),
        height=100,
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Your sketch", use_container_width=True)

    generate_clicked = st.button(
        "✨ Generate VFX", type="primary", disabled=uploaded_file is None,
        use_container_width=True,
    )

with col_output, st.container(key="vwhim_output_panel"):
    st.markdown(
        '<p class="vwhim-panel-eyebrow">Step 3 — the payoff</p>'
        '<p class="vwhim-panel-title">Your animation</p>',
        unsafe_allow_html=True,
    )

    if generate_clicked:
        if not movement_description.strip():
            st.warning(
                "Add a movement description first — it's what tells "
                "the pipeline how things should move."
            )
        else:
            with st.spinner("Running Interpreter → Generator → Critic..."):
                # Save the uploaded file to a temp path the pipeline can read
                suffix = "." + uploaded_file.name.split(".")[-1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                try:
                    result = run_pipeline(
                        image_path=tmp_path,
                        movement_description=movement_description,
                    )
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                    result = None

            if result:
                st.session_state["last_result"] = result

    result = st.session_state.get("last_result")

    if result:
        st.markdown(status_badge(result["approved"]), unsafe_allow_html=True)
        st.caption(f"Passes used: {result['passes_used']}")

        if result["svg_code"]:
            st.components.v1.html(result["svg_code"], height=420)

            st.download_button(
                "Download SVG",
                data=result["svg_code"],
                file_name="output.svg",
                mime="image/svg+xml",
            )

        with st.expander("Pipeline log (debug)"):
            for entry in result["log"]:
                st.markdown(f"**{entry['stage']}** (pass {entry.get('pass', '-')})")
                if entry["stage"] == "interpreter":
                    st.json(entry["output"])
                elif entry["stage"] == "critique":
                    st.json(entry["output"])
                else:
                    st.code(entry["output"], language="xml")
    elif not generate_clicked:
        st.markdown(
            empty_state(
                "Upload a sketch and describe its movement — your "
                "generated animation will appear here."
            ),
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# Insights is a distinct, secondary tool (real ClickHouse run history via
# MCP), not part of the creative sketch -> motion loop — kept as a quiet,
# collapsed-by-default drawer so it doesn't compete with the hero result
# above, but stays one click away for anyone who wants it. See DESIGN.md
# "Open design questions".
with st.container(key="vwhim_insights_panel"):
    with st.expander("🔍  Insights — ask about past runs", expanded=False):
        st.caption(
            "Ask about past runs — this queries real history stored in "
            "ClickHouse via its MCP server."
        )
        insight_question = st.text_input(
            "Ask a question",
            placeholder="e.g. How many runs needed a retry before approval?",
        )
        if st.button("Ask", type="secondary"):
            if not insight_question.strip():
                st.warning("Type a question first.")
            else:
                with st.spinner("Querying run history..."):
                    try:
                        answer = ask_about_runs(insight_question)
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Insights query failed: {e}")
