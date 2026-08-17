"""
Critique/Refine Agent (google-genai SDK version)
----------------------------------------------------
Renders the generated SVG to a still image, then asks Gemini to
compare that rendered result against the user's original intent
(sketch description + movement description). Returns either an
approval, or specific notes to send back to the Generation agent for
another pass. This loop is what makes the pipeline agentic rather
than a single one-shot generation call.

Uses the current `google-genai` SDK with a plain API key, not the
deprecated `vertexai.generative_models` module.
"""

import json
import os
import xml.etree.ElementTree as ET

from google.genai import types

from client import get_client, MODEL_NAME

client = get_client()

CRITIC_PROMPT = """
You are the Critique/Refine agent in a VFX generation pipeline.

Original user intent: "{original_intent}"

Look at the attached still frame of the generated animation and decide:
1. Does it plausibly match the described shapes and movement intent?
2. Are there obvious problems (wrong element missing, colors way off,
   motion direction backwards, elements overlapping incorrectly)?

Return ONLY valid JSON, no prose, no markdown fences:
{{
  "approved": true,
  "notes": "string — empty if approved, otherwise specific, actionable
             instructions the Generation agent can act on directly"
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
    only — see README for the mid-animation-frame caveat.
    """
    import cairosvg

    return cairosvg.svg2png(bytestring=svg_code.encode("utf-8"))


def critique_render(svg_code: str, original_intent: str) -> dict:
    """
    Compares a rendered SVG result to the original intent. Returns a
    dict: {"approved": bool, "notes": str}. On approval, notes is empty.

    A Generator output that isn't even valid XML (a mismatched/unclosed
    tag, usually from truncation) can't be rasterized to judge at all -
    rather than letting that crash the whole pipeline, it's treated as
    an automatic rejection with notes explaining what's wrong, so it
    flows through the same Generator-revises retry loop as an ordinary
    quality rejection instead of being a dead end.
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

    prompt = CRITIC_PROMPT.format(original_intent=original_intent)

    image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[image_part, prompt],
    )

    cleaned = _strip_code_fence(response.text)
    return json.loads(cleaned)


if __name__ == "__main__":
    # Quick manual smoke test — swap in real SVG output to try it.
    fake_svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>" \
               "<circle cx='50' cy='50' r='20' fill='red'/></svg>"
    result = critique_render(
        svg_code=fake_svg,
        original_intent="circle pulses, squiggle whips like a flame trail",
    )
    print(json.dumps(result, indent=2))