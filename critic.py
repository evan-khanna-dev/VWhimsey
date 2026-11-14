"""
Critique/Refine Agent (google-genai SDK version)
------------------------------------------------
Renders the generated SVG to a still image, then asks Gemini to
compare that render against the user's original sketch and movement
description. Approval is decided in code from per-item scores, so the
model can't simply say "looks fine". Returns either an approval or
specific notes to send back to the Generation agent for another pass.

Uses the current `google-genai` SDK with a plain API key.
"""

import json
import xml.etree.ElementTree as ET
from typing import Optional

from google.genai import types

from client import get_client, MODEL_NAME

client = get_client()

CRITIC_PROMPT = """
You are a strict critic in a sketch-to-animation pipeline.
Default to REJECT unless the result clearly matches the sketch.

You get two images:
IMAGE 1: the user's original sketch.
IMAGE 2: a still frame of the generated SVG.

User's movement description: "{original_intent}"

First list the distinct shapes you see in the sketch. Then score each
item from 1 to 5 (5 = clearly matches the sketch, 1 = clearly wrong):
- shapes: every shape in the sketch appears in the result
- layout: shapes sit in the same positions and proportions as the sketch
- smoothness: curves in the sketch are smooth curves, not jagged polygons
- framing: nothing important is cut off or runs outside the canvas
- intent: the frame is consistent with the movement description

Return ONLY JSON, no prose, no markdown fences:
{{
  "sketch_shapes": ["..."],
  "scores": {{"shapes": 1, "layout": 1, "smoothness": 1, "framing": 1, "intent": 1}},
  "problems": ["specific problem", "..."],
  "fixes": "specific instructions the generator can act on directly"
}}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


def _render_svg_to_png_bytes(svg_code: str) -> bytes:
    """
    Rasterizes SVG (a static/first frame) to PNG bytes so Gemini can
    view it. Requires `cairosvg` (pip install cairosvg + system cairo
    library). Note: SMIL animations rasterize to their initial frame
    only, so motion itself is not judged here.
    """
    import cairosvg

    return cairosvg.svg2png(bytestring=svg_code.encode("utf-8"))


def critique_render(
    svg_code: str,
    original_intent: str,
    sketch_bytes: Optional[bytes] = None,
    sketch_mime: str = "image/png",
) -> dict:
    """
    Compares a rendered SVG result to the user's sketch and intent.
    Returns {"approved": bool, "notes": str}. On approval, notes is empty.

    An SVG that isn't valid XML (usually truncation) can't be rendered,
    so it is treated as an automatic rejection with notes, and flows
    through the same Generator-revises retry loop as any other rejection.
    """
    try:
        png_bytes = _render_svg_to_png_bytes(svg_code)
    except ET.ParseError as e:
        return {
            "approved": False,
            "notes": (
                f"The generated SVG is not valid XML ({e}) and couldn't "
                "be rendered at all. Make sure every tag you open is "
                "properly closed and the file is complete, well-formed SVG."
            ),
        }

    parts = []
    if sketch_bytes:
        parts.append(
            types.Part.from_bytes(data=sketch_bytes, mime_type=sketch_mime)
        )
    parts.append(types.Part.from_bytes(data=png_bytes, mime_type="image/png"))
    parts.append(CRITIC_PROMPT.format(original_intent=original_intent))

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )

    result = json.loads(_strip_code_fence(response.text))
    scores = result.get("scores", {})
    approved = bool(scores) and min(scores.values()) >= 4

    notes = ""
    if not approved:
        notes = (
            "Problems: " + "; ".join(result.get("problems", []))
            + ". Fixes: " + result.get("fixes", "")
        )
    return {"approved": approved, "notes": notes}


if __name__ == "__main__":
    # Quick manual smoke test - swap in real SVG output to try it.
    fake_svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>" \
               "<circle cx='50' cy='50' r='20' fill='red'/></svg>"
    result = critique_render(
        svg_code=fake_svg,
        original_intent="circle pulses, squiggle whips like a flame trail",
    )
    print(json.dumps(result, indent=2))