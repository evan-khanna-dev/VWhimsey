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

from interpreter import sketch_to_spec
from generator import spec_to_svg
from critic import critique_render

MAX_PASSES = 2  # matches the "2nd pass creates agentic loop" plan


def run_pipeline(image_path: str, movement_description: str) -> dict:
    """
    Runs the full sketch -> motion spec -> SVG -> critique loop.

    Returns a dict with the final SVG code, whether it was approved,
    and a log of each pass for debugging / demo purposes.
    """
    log = []

    spec = sketch_to_spec(image_path, movement_description)
    log.append({"stage": "interpreter", "output": spec})

    revision_notes = None
    svg_code = None
    approved = False

    for pass_num in range(1, MAX_PASSES + 1):
        svg_code = spec_to_svg(spec, revision_notes=revision_notes)
        log.append({"stage": "generation", "pass": pass_num, "output": svg_code})

        critique = critique_render(svg_code, original_intent=movement_description)
        log.append({"stage": "critique", "pass": pass_num, "output": critique})

        if critique.get("approved"):
            approved = True
            break

        revision_notes = critique.get("notes", "")

    return {
        "approved": approved,
        "svg_code": svg_code,
        "passes_used": len(
            [entry for entry in log if entry["stage"] == "generation"]
        ),
        "log": log,
    }


if __name__ == "__main__":
    result = run_pipeline(
        image_path="sample_sketch.jpg",
        movement_description="gray clouds with blue lightning shooting out of them",
    )

    print(f"Approved: {result['approved']}")
    print(f"Passes used: {result['passes_used']}")

    with open("output.svg", "w") as f:
        f.write(result["svg_code"])
    print("Wrote final animation to output.svg")
