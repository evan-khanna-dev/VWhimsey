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

- `client.py` — shared Gemini client. Toggles between AI Studio (API
  key, no billing) and Vertex AI Agent Platform (what the hackathon
  submission requires) via one env var — nothing else needs to change.
- `interpreter.py` — sketch + description → motion spec (JSON)
- `generator.py` — motion spec → animated SVG code
- `critic.py` — renders SVG, judges it against original intent
- `orchestrator.py` — runs the full loop end-to-end, writes `output.svg`
- `app.py` — local Streamlit UI: upload a sketch, describe movement,
  see the result, no hand-editing files needed
- `requirements.txt` — dependencies

## Running locally

By default this runs against the **AI Studio Gemini Developer API**
(a plain API key, no billing) — good for fast iteration. Note: per
the hackathon rules ("Gemini models on **Agent Platform**"), the
*submitted* project needs to actually run against Vertex AI, not just
AI Studio — switch that over before you submit (see below).

```bash
cp .env.example .env
# edit .env and paste your real GOOGLE_API_KEY
pip install -r requirements.txt
streamlit run app.py
```

### Switching to Vertex AI (for submission)

Once your GCP project has billing linked:

```
# in .env
USE_VERTEX_AI=true
GOOGLE_CLOUD_PROJECT=your-hackathon-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

Also run once per machine: `gcloud auth application-default login`.
No code changes needed — `client.py` reads this and every other file
picks it up automatically.

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
5. **Vertex AI switch for submission** — see the "Switching to Vertex
   AI" section above. This is the piece needed to satisfy the
   hackathon's actual rule ("Gemini models on Agent Platform") —
   the AI Studio path is great for dev speed but likely doesn't
   count toward the submission requirement on its own.