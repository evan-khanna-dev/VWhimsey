# Sketch-to-VFX Agent Pipeline

A three-agent pipeline that turns a rough sketch + text description of
movement into an exportable animated SVG, with a critique/refine loop
that catches and corrects bad first passes.

## Architecture

```
sketch.jpg + "circle pulses, squiggle whips like a flame trail"
        │
        ▼
  ┌─────────────┐
  │ Interpreter │  sketch + text -> structured motion spec (JSON)
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │  Generator  │  motion spec -> animated SVG (SMIL)
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │   Critic    │  renders SVG, compares to original intent
  └─────────────┘
        │
   approved? ──No──> notes fed back to Generator (retry, up to 2 passes)
        │
       Yes
        │
        ▼
   final .svg file
```

## Files

- `interpreter.py` — sketch + description → motion spec (JSON)
- `generator.py` — motion spec → animated SVG code
- `critic.py` — renders SVG, judges it against original intent
- `orchestrator.py` — runs the full loop end-to-end, writes `output.svg`
- `agent_engine_wrappers.py` — optional: wraps each stage as a
  `LangchainAgent` and deploys to Vertex AI Agent Engine, matching the
  pattern from the hackathon-provided notebook
  (`intro_agent_engine.ipynb`)
- `requirements.txt` — dependencies

## Running locally

`interpreter.py`, `generator.py`, and `critic.py` currently use the
**`google-genai` SDK with a plain API key** (from aistudio.google.com),
not Vertex AI project billing. This was a deliberate switch after
hitting Vertex AI project-quota and billing setup friction — it lets
you build and test the actual agent logic without a linked
card/billing account. `agent_engine_wrappers.py` is still Vertex-AI
based and only matters once you're ready to deploy to Agent Engine
specifically (see its own docstring).

```bash
export GOOGLE_API_KEY=your-key-from-aistudio.google.com
pip install -r requirements.txt
python orchestrator.py
```

Edit the `image_path` and `movement_description` in
`orchestrator.py`'s `if __name__ == "__main__":` block to point at your
actual sketch photo.

## Open decisions / things to verify before the demo

1. **Model name** — files default to `MODEL_NAME = "gemini-2.5-flash"`
   (overridable via `export GEMINI_MODEL=...`). Confirm the current
   valid model name in aistudio.google.com before relying on it —
   these change over time.
2. **SVG vs. shader/particles** — this build goes with SVG/SMIL since
   it's dependency-light and viewable anywhere. If you want the
   shader/particle route instead, `generator.py` is the only file that
   needs to change (swap the SMIL prompt for one generating a WebGL/
   Three.js particle system).
3. **`cairosvg` rendering** — `critic.py` rasterizes SVG to a still PNG
   for Gemini to judge. SMIL animations render as a static first frame
   by default; if you want the critic judging mid-animation, you'll
   need to pick a specific timestamp to render (cairosvg doesn't
   animate, so this may need a headless-browser screenshot approach
   instead — worth testing early).
4. **Replit integration** — not yet wired in. The natural fit is
   hosting the orchestrator as a small web app on Replit where a user
   uploads a sketch and gets back the SVG live — that's your partner
   integration piece.
5. **Deployment** — `agent_engine_wrappers.py` is optional and only
   matters if the judging criteria specifically wants to see agents
   deployed to Agent Engine. For the demo video itself, running
   `orchestrator.py` locally or on Replit is probably faster to
   iterate on.