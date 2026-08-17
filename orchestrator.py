"""
Orchestrator
-------------
Drives the full pipeline: Interpreter -> Generation -> Critique/Refine.
If the Critique agent rejects a pass, its notes are fed back into the
Generation agent for another attempt (bounded by MAX_PASSES). This is
the piece that turns three separate LLM calls into one agentic system
with an actual feedback loop — the part worth showing on camera in the
demo video.
"""

from collections.abc import Callable

from interpreter import sketch_to_spec
from generator import spec_to_svg
from critic import critique_render
from clickhouse_log import log_run

MAX_PASSES = 2  # matches the "2nd pass creates agentic loop" plan


def run_pipeline(
    image_path: str,
    movement_description: str,
    on_update: Callable[..., None] | None = None,
) -> dict:
    """
    Runs the full sketch -> motion spec -> SVG -> critique loop.

    Returns a dict with the final SVG code, whether it was approved,
    and a log of each pass for debugging / demo purposes. Also logs
    the run's outcome to ClickHouse for later querying.

    `on_update`, if given, is called as `on_update(event, **info)` right
    before/after each real agent call fires — for a caller (e.g. the
    Streamlit UI) that wants to reflect live progress rather than just
    showing a spinner for the whole run. Purely observational: it can't
    affect the pipeline's own control flow, and the pipeline behaves
    identically whether or not one is passed. Events, in order:
    interpreter_start, interpreter_done, generator_start(pass_num),
    generator_done(pass_num), critic_start(pass_num),
    critic_done(pass_num, approved, notes).
    """

    def notify(event: str, **info) -> None:
        if on_update is not None:
            on_update(event, **info)

    log = []

    notify("interpreter_start")
    spec = sketch_to_spec(image_path, movement_description)
    log.append({"stage": "interpreter", "output": spec})
    notify("interpreter_done")

    revision_notes = None
    svg_code = None
    approved = False

    for pass_num in range(1, MAX_PASSES + 1):
        notify("generator_start", pass_num=pass_num)
        svg_code = spec_to_svg(spec, revision_notes=revision_notes)
        log.append({"stage": "generation", "pass": pass_num, "output": svg_code})
        notify("generator_done", pass_num=pass_num)

        notify("critic_start", pass_num=pass_num)
        critique = critique_render(svg_code, original_intent=movement_description)
        log.append({"stage": "critique", "pass": pass_num, "output": critique})
        notify(
            "critic_done",
            pass_num=pass_num,
            approved=bool(critique.get("approved")),
            notes=critique.get("notes", ""),
        )

        if critique.get("approved"):
            approved = True
            break

        revision_notes = critique.get("notes", "")

    passes_used = len([entry for entry in log if entry["stage"] == "generation"])

    log_run(
        movement_description=movement_description,
        approved=approved,
        passes_used=passes_used,
        interpreter_output=spec,
        critique_notes=revision_notes or "",
        svg_code=svg_code or "",
    )

    return {
        "approved": approved,
        "svg_code": svg_code,
        "passes_used": passes_used,
        "log": log,
    }


if __name__ == "__main__":
    result = run_pipeline(
        image_path="sample_sketch.jpg",
        movement_description="circle pulses, squiggle whips like a flame trail",
    )

    print(f"Approved: {result['approved']}")
    print(f"Passes used: {result['passes_used']}")

    with open("output.svg", "w") as f:
        f.write(result["svg_code"])
    print("Wrote final animation to output.svg")