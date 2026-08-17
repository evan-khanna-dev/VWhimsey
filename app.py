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
from pathlib import Path

import streamlit as st

from orchestrator import run_pipeline
from insights import ask_about_runs
from gallery import render_gallery, invalidate_cache as invalidate_gallery_cache
from theme import (
    THEME_CSS,
    render_background,
    render_hero,
    status_badge,
    empty_state,
    render_pipeline_steps,
)

st.set_page_config(page_title="VWhimsey", layout="wide")

EXAMPLES_DIR = Path(__file__).parent / "examples"
EXAMPLES = {
    "zigzag": {
        "label": "Zigzag + particles",
        "path": EXAMPLES_DIR / "zigzag-sketch.png",
        "description": (
            "Flowing lines in this pattern throughout the pattern with "
            "red particles emitting from the pulsing, with a line "
            "flowing from the start to the finish."
        ),
    },
    "swirl": {
        "label": "Swirl + orb",
        "path": EXAMPLES_DIR / "swirl-sketch.png",
        "description": (
            "The middle of the circular orb is pulsing while the "
            "outline is swirling around the orb and down to the "
            "cone-shape."
        ),
    },
}


def _use_example(example_key: str) -> None:
    """st.button on_click callback — runs before the script body re-executes,
    so it can populate widget state (text_area's value) before that widget
    is instantiated this run. A real file upload can't be set this way (no
    Streamlit API sets a file_uploader's value), so example sketches are
    tracked as their own bytes-in-session_state source instead — see
    `sketch_source` below."""
    st.session_state["movement_description"] = EXAMPLES[example_key]["description"]
    st.session_state["sketch_source"] = f"example:{example_key}"


def _run_pipeline_with_live_status(image_path: str, movement_description: str):
    """Runs the pipeline inside st.status(), updating a step-by-step
    display in real time via orchestrator.run_pipeline's on_update hook
    - each line only appears/changes exactly when that real agent call
    starts or finishes, no simulated delays. A retry pass (critic
    rejects -> generator revises) gets its own distinct step, appended
    only once it's actually happening, carrying the real critique notes
    that triggered it - that's the clearest on-screen proof this is a
    genuine multi-agent feedback loop rather than one model call."""
    steps = [
        {"label": "Interpreter reading your sketch...", "state": "pending"},
        {"label": "Generator creating the animation...", "state": "pending"},
        {"label": "Critic reviewing the result...", "state": "pending"},
    ]
    # keyed by pass_num so generator_done/critic_done can find the row
    # generator_start/critic_start for that same pass created
    retry_generator_steps: dict[int, dict] = {}
    retry_critic_steps: dict[int, dict] = {}
    pending_notes = {"text": ""}
    # whichever step is currently "active" - tracked so that if the
    # pipeline raises mid-call, that one row can be flipped to "failed"
    # instead of being left spinning forever (only one step is ever
    # active at a time, so the latest one set is always the right one).
    active_step_ref = {"step": None}

    with st.status("Running the pipeline...", expanded=True) as status_box:
        steps_placeholder = st.empty()

        def render() -> None:
            steps_placeholder.markdown(
                render_pipeline_steps(steps), unsafe_allow_html=True
            )

        render()

        def on_update(event: str, **info) -> None:
            pass_num = info.get("pass_num")

            if event == "interpreter_start":
                steps[0]["state"] = "active"
                active_step_ref["step"] = steps[0]
            elif event == "interpreter_done":
                steps[0]["state"] = "done"

            elif event == "generator_start":
                if pass_num == 1:
                    steps[1]["state"] = "active"
                    active_step_ref["step"] = steps[1]
                else:
                    retry_step = {
                        "label": (
                            "Critic requested changes — Generator revising "
                            f"(pass {pass_num})..."
                        ),
                        "state": "active",
                        "detail": pending_notes["text"],
                    }
                    retry_generator_steps[pass_num] = retry_step
                    steps.append(retry_step)
                    active_step_ref["step"] = retry_step
            elif event == "generator_done":
                if pass_num == 1:
                    steps[1]["state"] = "done"
                else:
                    retry_generator_steps[pass_num]["state"] = "done"

            elif event == "critic_start":
                if pass_num == 1:
                    steps[2]["state"] = "active"
                    active_step_ref["step"] = steps[2]
                else:
                    critic_step = {
                        "label": "Critic reviewing the revision...",
                        "state": "active",
                    }
                    retry_critic_steps[pass_num] = critic_step
                    steps.append(critic_step)
                    active_step_ref["step"] = critic_step
            elif event == "critic_done":
                approved = info.get("approved")
                notes = info.get("notes") or ""
                target = steps[2] if pass_num == 1 else retry_critic_steps[pass_num]
                target["state"] = "done" if approved else "rejected"
                if not approved:
                    pending_notes["text"] = notes

            render()

        try:
            result = run_pipeline(
                image_path=image_path,
                movement_description=movement_description,
                on_update=on_update,
            )
        except Exception as e:
            # Whichever step was mid-flight when this fired would
            # otherwise be left showing its spinner forever - flip it to
            # a clear failed indicator instead so the display doesn't
            # look like it's still working after the run has stopped.
            if active_step_ref["step"] is not None:
                active_step_ref["step"]["state"] = "failed"
                render()
            status_box.update(label="Pipeline failed", state="error", expanded=True)
            st.error(f"Pipeline failed: {e}")
            return None

        # The run just got logged to ClickHouse (see orchestrator.py's
        # log_run call) - clear the Gallery's cache so it shows up there
        # immediately instead of waiting out its TTL.
        invalidate_gallery_cache()

        if result["passes_used"] <= 1 and result["approved"]:
            final_label = "Approved!"
        else:
            final_label = f"Completed after {result['passes_used']} passes"
        # st.status() collapses on its own unless expanded is re-asserted
        # here - and a retry (if one happened) is the clearest on-screen
        # proof this is a real multi-agent loop, so it should stay visible
        # by default rather than requiring an extra click to re-open.
        status_box.update(label=final_label, state="complete", expanded=True)

    return result


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

    # A genuinely new upload always wins over a previously-picked example.
    # (uploaded_file stays non-None across reruns once something's been
    # picked, so this only flips sketch_source on an actual new file, not
    # on every rerun where an old upload is still sitting in the widget.)
    if uploaded_file is not None:
        upload_id = f"{uploaded_file.name}:{uploaded_file.size}"
        if st.session_state.get("_last_upload_id") != upload_id:
            st.session_state["_last_upload_id"] = upload_id
            st.session_state["sketch_source"] = "upload"

    st.markdown(
        '<p class="vwhim-example-label">or try an example</p>',
        unsafe_allow_html=True,
    )
    with st.container(key="vwhim_example_row"):
        example_cols = st.columns(len(EXAMPLES))
        for col, (example_key, example) in zip(example_cols, EXAMPLES.items()):
            with col:
                st.image(str(example["path"]), use_container_width=True)
                st.button(
                    example["label"],
                    key=f"use_example_{example_key}",
                    on_click=_use_example,
                    args=(example_key,),
                    type="secondary",
                    use_container_width=True,
                )

    movement_description = st.text_area(
        "Describe the intended movement",
        key="movement_description",
        placeholder=(
            "e.g. circle pulses, squiggle whips like a flame trail"
        ),
        height=100,
    )

    # Resolve which sketch actually feeds the pipeline: the real upload, or
    # a picked example's bytes read straight off disk (file_uploader has no
    # API to be pre-filled, so examples are threaded through separately).
    sketch_source = st.session_state.get("sketch_source")
    if sketch_source == "upload" and uploaded_file is not None:
        sketch_bytes = uploaded_file.getvalue()
        sketch_name = uploaded_file.name
        sketch_caption = "Your sketch"
    elif sketch_source and sketch_source.startswith("example:"):
        active_example = EXAMPLES[sketch_source.split(":", 1)[1]]
        sketch_bytes = active_example["path"].read_bytes()
        sketch_name = active_example["path"].name
        sketch_caption = f"Example: {active_example['label']}"
    else:
        sketch_bytes = None
        sketch_name = None
        sketch_caption = None

    if sketch_bytes is not None:
        st.image(sketch_bytes, caption=sketch_caption, use_container_width=True)

    generate_clicked = st.button(
        "✨ Generate VFX", type="primary", disabled=sketch_bytes is None,
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
            # Save the sketch (uploaded or example) to a temp path the
            # pipeline can read
            suffix = "." + sketch_name.split(".")[-1]
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            ) as tmp_file:
                tmp_file.write(sketch_bytes)
                tmp_path = tmp_file.name

            result = _run_pipeline_with_live_status(
                image_path=tmp_path,
                movement_description=movement_description,
            )

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

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# Gallery is the browsable counterpart to Insights above: same
# underlying run history, but skimmed visually rather than asked about
# in natural language. Kept as its own quiet, collapsed-by-default
# drawer for the same reason Insights is - a secondary/meta tool, not
# part of the hero creative loop.
with st.container(key="vwhim_gallery_panel"):
    with st.expander("🖼️  Gallery — browse past runs", expanded=False):
        render_gallery()
