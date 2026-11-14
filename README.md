# VWhimsey: Sketch to VFX Agent Pipeline

Draw a rough sketch, describe how it should move, and a multi agent
pipeline turns it into an exportable, animated SVG, with a
critique/refine loop that catches and corrects bad first passes, and
an Insights agent that can answer real questions about its own past
run history.

Built for Google Cloud's Agentic Cinema hackathon (Blockbuster
Hackathon), ClickHouse partner track.

**Live app:** https://vwhimsey-aasbmswugi87evob3w4ukb.streamlit.app/

## Who this is for

* **Beginner/emerging indie creators** who can't afford to hire a VFX
  artist and don't have time to climb the learning curve of Unity,
  Unreal Engine, or Premiere Pro's motion tooling. This replaces
  "hire someone or spend months learning software" with something
  they already know how to do: draw.
* **Experienced artists/designers who can sketch well.** For them,
  this works as a fast drafting or previsualization step, often
  quicker than opening a full timeline editor, before committing time
  to the polished version in their production tool.

## Architecture

```
sketch.jpg + "circle pulses, squiggle whips like a flame trail"
        │
        ▼
  ┌─────────────┐
  │ Interpreter │  sketch + text → structured motion spec (JSON),
  └─────────────┘  including literal traced points for jagged shapes
        │           and a flows_into relationship field
        ▼
  ┌─────────────┐
  │  Generator  │  motion spec → animated SVG (SMIL)
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │   Critic    │  renders SVG, compares to original intent
  └─────────────┘
        │
   approved? No → notes fed back to Generator (retry, up to 2 passes)
        │          malformed/unparseable SVG is retried the same way
       Yes
        │
        ▼
   final .svg file, logged to ClickHouse
```

Every run, approved or rejected, including critique notes and passes
used, is logged to a self hosted ClickHouse instance. A separate
**Insights agent** connects Gemini to the official `mcp-clickhouse`
MCP server at runtime, so the app can answer natural language
questions about its own generation history ("how many runs needed a
retry before approval?") using live data, not canned responses.

## Why SVG, not video

Output is deliberately SVG only. There's no MP4/WebM export path,
and that's not a gap to fill in later. The generated SVG carries
structured motion data such as element positions, easing curves, and
durations via native SMIL animation tags, rather than being flattened
into pixels. That makes it more directly useful for downstream tools
with SVG/vector import support (e.g. Unity's Vector Graphics package
for shape geometry) than a flattened video clip would be, where all
of that structure is gone. A video export path was built and tested,
then deliberately removed after hitting transparency compositing and
motion smearing quality issues that would have needed an alpha
preserving codec (ProRes 4444 or QuickTime Animation) to solve
properly. It's in git history if useful as reference.

## Features

* **Sketch to VFX pipeline**: the core Interpreter → Generator →
  Critic loop described above.
* **"Try an example"**: two preloaded example sketches (with matching
  movement descriptions) so anyone can see the pipeline run
  immediately, with no drawing required.
* **Live pipeline status**: real time, step by step visibility into
  which agent is currently running, including a visibly distinct
  retry pass when the Critic rejects a first attempt and sends notes
  back to the Generator.
* **Gallery**: a browsable view of past runs pulled live from
  ClickHouse, filterable by approved or rejected, showing critique
  notes on rejected runs.
* **Insights**: ask questions about past run history in plain
  language, answered by Gemini actively querying the ClickHouse MCP
  server at runtime.

## Files

* `client.py`: shared Gemini client. Toggles between AI Studio (API
  key, no billing) and Vertex AI Agent Platform (what the hackathon
  submission requires) via one env var. Also handles auth for
  environments with no metadata server (like Streamlit Cloud) via an
  explicit service account JSON credential path.
* `interpreter.py`: sketch + description → motion spec (JSON)
* `generator.py`: motion spec → animated SVG code
* `critic.py`: renders SVG (via `cairosvg`), judges it against
  original intent
* `orchestrator.py`: runs the full loop end to end, logs each run to
  ClickHouse via `clickhouse_log.py`
* `clickhouse_log.py`: inserts one row per run into
  `vfx_pipeline.runs` (non fatal on failure; a logging problem never
  breaks actual generation)
* `insights.py`: connects Gemini to the `mcp-clickhouse` MCP server
  (spawned as a subprocess) so it can query real run history at
  runtime
* `gallery.py`: browsable view of past runs pulled live from
  ClickHouse, filterable by approved or rejected
* `theme.py`: shared visual and theming helpers used by `app.py` for
  the glass panel redesign
* `app.py`: the Streamlit UI: upload or example sketch, describe
  movement, live pipeline status, result preview and download,
  Gallery, Insights
* `DESIGN.md`: the design brief used to guide the UI and visual
  redesign
* `requirements.txt`: Python dependencies
* `packages.txt`: system level (apt) dependencies for Streamlit
  Community Cloud, currently `libcairo2`, required by `cairosvg`
* `.streamlit/config.toml`: custom theme
* `assets/clouds-enhanced.gif`: source background asset
* `static/`: processed background media (`clouds-bg.mp4`,
  `clouds-bg.webm`, `clouds-poster.jpg`, the static poster shown for
  `prefers-reduced-motion`)
* `scripts/`: one off dev scripts used to generate the background
  media (`analyze_gif.py`, `make_background.py`), not part of the
  running app
* `examples/`: the two sketches used by "Try an example"
  (`zigzag-sketch.png`, `swirl-sketch.png`)
* `LICENSE`: MIT

## Running locally

By default this runs against the **AI Studio Gemini Developer API**
(a plain API key, no billing), good for fast iteration:

```bash
cp .env.example .env
# edit .env: paste your real GOOGLE_API_KEY
pip install -r requirements.txt
streamlit run app.py
```

Note: per the hackathon rules ("Gemini models on **Agent Platform**"),
the *submitted or deployed* project runs against Vertex AI, not AI
Studio. See below.

### `cairosvg` / native `cairo` setup notes

`cairosvg` (used by the Critic to rasterize SVG for judging) depends
on the native `cairo` library, which pip does not install for you.
Setup differs by platform, and the exact commands below assume a
fairly standard setup for each; your specific system (a different
Linux distribution, an unusual shell, a locked down or managed
machine, etc.) may need slightly different syntax or an extra step
not listed here. If a command below doesn't work as written, that's
a reasonable first thing to check before assuming something else is
broken.

**Windows.** `cairo` is not on `PATH` by default. Without it, you'll
hit an error like:

```
no library called "cairo-2" was found ... cannot load library 'libcairo-2.dll'
```

Fix:
1. Install the **GTK3 runtime for Windows**, which bundles
   `libcairo-2.dll`:
   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. `client.py`/`critic.py` already explicitly registers the install
   directory via `os.add_dll_directory()` at import time (bypassing
   Windows PATH lookup, which is unreliable for this specific DLL).
   If your GTK3 runtime installed somewhere other than the default
   `C:\Program Files\GTK3-Runtime Win64\bin`, set `CAIRO_DLL_DIR` in
   your `.env` to the correct folder.
3. **Use a genuinely fresh terminal window** after installing.
   Terminals integrated into an IDE (VS Code, PyCharm, etc.) often
   cache a stale environment from before the install and won't see
   the PATH update until fully restarted, not just given a new tab.

If the GTK3 installer isn't an option (e.g. a locked down machine
with no installer permissions), an alternative that some people find
easier is installing `cairo` through a conda environment instead of
system wide, since conda packages the binary itself:
```
conda install -c conda-forge cairo
```
This sidesteps the Windows PATH/DLL issue entirely, at the cost of
needing conda as your Python environment manager instead of a plain
venv.

**macOS.** `brew install cairo` is usually enough. If you're on a
Python installed through pyenv, asdf, or something other than the
system/Homebrew Python and still hit an import error, also install
`pkg-config`, which some `cairo` bindings need to locate the library
at build time:
```
brew install cairo pkg-config
```

**Linux, outside Streamlit Cloud** (a bare VM, a Docker container you
control, WSL, etc.): install the runtime library through your
package manager rather than relying on `packages.txt`, which only
applies to Streamlit Community Cloud specifically:
```
sudo apt-get install libcairo2
```
On Fedora/RHEL based systems, the equivalent is:
```
sudo dnf install cairo
```
If you're building `cairosvg` or a related package from source rather
than installing a prebuilt wheel, you may also need the development
headers, not just the runtime library:
```
sudo apt-get install libcairo2-dev
```

**Streamlit Community Cloud.** Already handled: `libcairo2` is listed
in `packages.txt` and installed automatically on deploy. If you add or
change this file, the app needs a full reboot (not just a redeploy)
to pick up new system packages.

**Verifying the fix, on any platform**, before assuming it's resolved:
```
python -c "import cairosvg"
```
If this runs with no output at all, the library is correctly found.
Any import error here means the underlying `cairo` library still
isn't reachable, regardless of what `pip install` reported.

### Switching to Vertex AI (for submission)

Once your GCP project has billing linked and the AI Platform API is
enabled:

```
# in .env
USE_VERTEX_AI=true
GOOGLE_CLOUD_PROJECT=your-hackathon-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.6-flash
```

Also run once per local machine:
`gcloud auth application-default login`

No code changes needed. `client.py` reads this and everything else
picks it up automatically.

### ClickHouse setup (partner track integration)

This project self hosts ClickHouse (Apache 2.0, open source) on a
small GCP Compute Engine VM running the official Docker image, rather
than using ClickHouse Cloud's trial (whose 30 day window would expire
before the hackathon's judging period even starts).

```bash
gcloud compute instances create-with-container clickhouse-vm \
  --zone=us-central1-a --machine-type=e2-small \
  --container-image=clickhouse/clickhouse-server \
  --tags=clickhouse-server
```

Set a real password on a new user (the default `default` user's
config is read only inside the image):

```sql
CREATE USER clickhouse_admin IDENTIFIED WITH plaintext_password BY '...';
GRANT SELECT, INSERT, ALTER, CREATE, DROP, SHOW ON *.* TO clickhouse_admin WITH GRANT OPTION;
```

Then in `.env`:
```
CLICKHOUSE_HOST=your_vm_external_ip
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=clickhouse_admin
CLICKHOUSE_PASSWORD=your_real_password
```

The `mcp-clickhouse` server (used by `insights.py`) needs two
additional env vars set explicitly, since this VM serves plain HTTP
(no TLS) on port 8123, and the package otherwise defaults to
expecting HTTPS:
```
CLICKHOUSE_SECURE=false
CLICKHOUSE_VERIFY=false
```
It also prints a startup banner to stdout by default, which corrupts
the stdio JSON-RPC protocol the MCP client depends on and causes an
opaque "Connection closed" error. `insights.py` explicitly disables
this via `FASTMCP_SHOW_SERVER_BANNER=false` and related env vars. If
you're debugging MCP connection issues, run
`python -m mcp_clickhouse.main` standalone first to see real errors
directly, since the wrapped client swallows subprocess stderr.

## Deploying (Streamlit Community Cloud)

1. Push to a public GitHub repo (MIT licensed, required by the
   hackathon rules).
2. Connect the repo at https://share.streamlit.io, main file `app.py`.
3. Add secrets in the app's dashboard (Settings → Secrets), mirroring
   your `.env`. **One addition is needed here that isn't needed
   locally:** Application Default Credentials don't work on
   Streamlit Cloud (no GCP metadata server available), so add a
   service account key instead:

   ```bash
   gcloud iam service-accounts create vfx-hackathon-sa
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member="serviceAccount:vfx-hackathon-sa@YOUR_PROJECT.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   gcloud iam service-accounts keys create vfx-sa-key.json \
     --iam-account=vfx-hackathon-sa@YOUR_PROJECT.iam.gserviceaccount.com
   ```

   Paste the full contents of `vfx-sa-key.json` into a
   `GCP_SERVICE_ACCOUNT_JSON` secret (`client.py` reads this
   automatically when present, falling back to normal ADC discovery
   otherwise). **Do not commit this key file to the repo.** Delete it
   locally once it's saved in Streamlit's secrets.

4. The ClickHouse VM's firewall must allow inbound traffic from
   wherever the app is deployed. Since Streamlit Cloud's egress IPs
   aren't fixed or known in advance, the firewall rule for this
   project is scoped open (`0.0.0.0/0`) rather than to a specific IP,
   relying on ClickHouse's own password authentication for security
   instead.

## Findings / things worth knowing

* **Ambiguous or chaotic sketches get smoothed by default.** Early
  testing showed the Interpreter tends to abstract a jagged, erratic
  hand drawn line into a generic "wavy" motion category, losing the
  actual sharpness of the drawing. Fixed by having the Interpreter
  trace literal coordinate points along the drawn path
  (`trace_points`) instead of just categorizing motion type, and
  having the Generator build geometry from those literal points
  rather than inventing an idealized curve.
* **Cross element relationships needed an explicit field.** Getting
  one element to visibly "flow into" or "feed" another (e.g. an
  energy trail feeding a flare) required adding a `flows_into` field
  to the motion spec. Without it, elements animated independently
  with no visible relationship between them.
* **LLM authored SVG occasionally comes back malformed** (truncated
  or mismatched tags). This is a known, recoverable failure mode, not
  a one time thing. It's now treated the same way as a critic
  rejection: the parser error is fed back to the Generator as
  feedback for a retry, rather than crashing the run outright.