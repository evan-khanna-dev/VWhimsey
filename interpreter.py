"""
Interpreter Agent (google-genai SDK version)
-----------------------------------------------
Reads a hand-drawn sketch (image) plus a text description of intended
movement, and turns it into a structured "motion spec" — the contract
that the Generation agent consumes.

Uses the current `google-genai` SDK with a plain API key (from
aistudio.google.com), NOT the deprecated `vertexai.generative_models`
module and NOT Vertex AI project billing. Good for local dev/testing
before you're ready to deal with Vertex AI project setup.
"""

import json
import os

from google.genai import types

from client import get_client, MODEL_NAME

client = get_client()

INTERPRETER_PROMPT = """
You are analyzing a hand-drawn sketch for a VFX motion design tool.

The user described the intended movement as: "{movement_description}"

Look at the sketch and identify:
1. The distinct shapes/elements drawn (name, approximate type: circle,
   line, blob, etc., and rough position as x/y percent of canvas)
2. For each shape, infer a motion type from the description
   (e.g. pulse, orbit, whip, trail, fade) and estimate:
   - path (straight, circular, wavy, custom points)
   - duration_ms
   - easing (linear, ease-in-out, bounce, elastic)
3. Any implied particle or trail behavior (e.g. "squiggle whips like
   a flame trail" implies a trailing particle emitter)
4. CRITICAL — do not smooth or idealize jagged/chaotic lines into
   generic curves. If the drawn line is sharp, erratic, or spiky,
   preserve that literally: trace 10-20 actual points along the
   drawn path (as x/y percent of canvas) that follow its real peaks
   and valleys, in `trace_points`. A jagged line should produce a
   jagged `trace_points` list, not a smoothed sine wave.
5. If one element's motion is described as moving toward, feeding
   into, or triggering another element (e.g. "the wave moves like
   fire into the flare"), record that relationship in `flows_into`
   using the other element's `name`. Leave it null if there's no
   such relationship.

Return ONLY valid JSON in this exact shape, no prose, no markdown fences:
{{
  "elements": [
    {{
      "name": "string",
      "shape_type": "string",
      "color": "string (hex, best guess or default #ffffff)",
      "position": {{"x_pct": 0, "y_pct": 0}},
      "trace_points": [{{"x_pct": 0, "y_pct": 0}}],
      "flows_into": "string or null",
      "motion": {{
        "type": "string",
        "path": "string",
        "duration_ms": 0,
        "easing": "string"
      }},
      "particle_trail": true
    }}
  ],
  "canvas": {{"width": 512, "height": 512, "background": "transparent"}}
}}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


def sketch_to_spec(image_path: str, movement_description: str) -> dict:
    """
    Turns a hand-drawn sketch (shape + squiggle etc.) plus a text
    description of intended movement into a structured motion spec
    that the Generation agent can consume.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = INTERPRETER_PROMPT.format(movement_description=movement_description)

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[image_part, prompt],
    )

    cleaned = _strip_code_fence(response.text)
    return json.loads(cleaned)


if __name__ == "__main__":
    # Quick manual smoke test — swap in a real sketch path to try it.
    spec = sketch_to_spec(
        image_path="sample_sketch.jpg",
        movement_description="circle pulses, squiggle whips like a flame trail",
    )
    print(json.dumps(spec, indent=2))