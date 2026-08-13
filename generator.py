"""
Generation Agent (google-genai SDK version)
-----------------------------------------------
Takes a structured motion spec (from the Interpreter agent, or notes
from the Critique agent on a retry) and turns it into an exportable
animated SVG using native SMIL animation tags. SVG is the export
format because it's lightweight, human-editable, and viewable in any
browser without extra libraries — a good fit for a hackathon demo.

Uses the current `google-genai` SDK with a plain API key, not the
deprecated `vertexai.generative_models` module.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

from google import genai

API_KEY = os.environ["GOOGLE_API_KEY"]
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

client = genai.Client(api_key=API_KEY)

GENERATOR_PROMPT = """
You are a Generation agent in a VFX pipeline. Turn the following motion
spec into a single, valid, self-contained animated SVG file.

Rules:
- Use native SVG SMIL animation (<animate>, <animateMotion>,
  <animateTransform>) — no external JS libraries, no <script> tags.
- If an element has `trace_points`, build its path/shape geometry
  FROM THOSE LITERAL POINTS (as straight-line or minimally-smoothed
  segments), not from an idealized curve. Preserve real jaggedness —
  do not simplify sharp zigzags into smooth sine waves.
- If an element's `flows_into` references another element's name,
  animate it moving toward and terminating at that target element's
  position — e.g. treat it like fuel/energy traveling into and
  feeding that target (consider intensifying the target's glow/scale
  slightly as the source arrives, timed to sync with its arrival).
- Respect each element's position, color, motion type, path, duration,
  and easing as closely as SMIL allows (map "ease-in-out" to a keySplines
  calcMode="spline" curve, "bounce"/"elastic" to a reasonable approximation).
- If particle_trail is true for an element, simulate a trail using a
  handful of duplicated, staggered, fading copies of that element
  along its motion path.
- Output ONLY the raw SVG code. No prose, no markdown fences.

Motion spec:
{motion_spec}

{revision_notes_block}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("svg") or text.startswith("xml"):
            text = text.split("\n", 1)[1] if "\n" in text else text
    return text.strip()


def spec_to_svg(motion_spec: dict, revision_notes: str | None = None) -> str:
    """
    Turns a motion spec into exportable, self-contained SVG/SMIL
    animation code. If revision_notes is provided (from the
    Critique/Refine agent), the generator treats this as a retry pass
    and adjusts accordingly.
    """
    revision_block = ""
    if revision_notes:
        revision_block = (
            "This is a REVISION pass. The previous render was reviewed "
            f"and needs these changes:\n{revision_notes}\n"
        )

    prompt = GENERATOR_PROMPT.format(
        motion_spec=json.dumps(motion_spec, indent=2),
        revision_notes_block=revision_block,
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    return _strip_code_fence(response.text)


if __name__ == "__main__":
    sample_spec = {
        "elements": [
            {
                "name": "core_circle",
                "shape_type": "circle",
                "color": "#ff5533",
                "position": {"x_pct": 50, "y_pct": 50},
                "motion": {
                    "type": "pulse",
                    "path": "static",
                    "duration_ms": 1200,
                    "easing": "ease-in-out",
                },
                "particle_trail": False,
            },
            {
                "name": "flame_squiggle",
                "shape_type": "wavy_line",
                "color": "#ffaa00",
                "position": {"x_pct": 55, "y_pct": 50},
                "motion": {
                    "type": "whip",
                    "path": "wavy",
                    "duration_ms": 800,
                    "easing": "elastic",
                },
                "particle_trail": True,
            },
        ],
        "canvas": {"width": 512, "height": 512, "background": "transparent"},
    }
    svg_code = spec_to_svg(sample_spec)
    print(svg_code)