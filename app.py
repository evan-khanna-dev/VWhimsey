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

import json
import tempfile

import streamlit as st

from orchestrator import run_pipeline
from insights import ask_about_runs

st.set_page_config(page_title="Sketch-to-VFX", layout="wide")

st.title("Sketch-to-VFX")
st.caption(
    "Upload a photo of a sketch, describe how it should move, "
    "and generate an exportable animated SVG."
)

col_input, col_output = st.columns(2)

with col_input:
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
        "Generate VFX", type="primary", disabled=uploaded_file is None
    )

with col_output:
    if generate_clicked:
        if not movement_description.strip():
            st.warning("Add a movement description first — it's what tells "
                       "the pipeline how things should move.")
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
        status = "Approved ✅" if result["approved"] else "Not approved ⚠️"
        st.subheader(status)
        st.caption(f"Passes used: {result['passes_used']}")

        if result["svg_code"]:
            st.components.v1.html(result["svg_code"], height=400)

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
        st.info("Upload a sketch and click Generate VFX to see output here.")

st.divider()
st.subheader("Insights")
st.caption(
    "Ask about past runs — this queries real history stored in "
    "ClickHouse via its MCP server."
)
insight_question = st.text_input(
    "Ask a question",
    placeholder="e.g. How many runs needed a retry before approval?",
)
if st.button("Ask"):
    if not insight_question.strip():
        st.warning("Type a question first.")
    else:
        with st.spinner("Querying run history..."):
            try:
                answer = ask_about_runs(insight_question)
                st.write(answer)
            except Exception as e:
                st.error(f"Insights query failed: {e}")