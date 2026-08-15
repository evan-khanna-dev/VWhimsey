"""
Visual theme for the VWhimsey Streamlit UI.
--------------------------------------------------
Everything here is CSS/HTML injected via st.markdown(unsafe_allow_html=True)
per the "Streamlit, not a framework rewrite" constraint in DESIGN.md.

Palette derivation: sampled assets/clouds-enhanced.gif directly (see
scripts/analyze_gif.py) rather than guessing from the brief's prose
description. The gif's dominant hue sits at ~H203-204 (pale sky-blue,
e.g. #6aaedb / #87bfe2). The accent/text colors below stay in that same
analogous family, shifted toward indigo (~H206-222) and pushed dark/
saturated enough to read as ink rather than sky:

    --ink-900   #16213b   body text on glass
    --ink-700   #222f4f   headings
    --accent-600 #2966a3  buttons / links / focus rings
    --accent-800 #1c3f66  hover/active
    --sky-200   #cbe3f6   glass tint, pulled straight from the gif
    --scrim-950 #101625   hero scrim base (near-black indigo)

Background media: the source gif is 400x222, 230 frames, ~15s loop.
scripts/make_background.py re-encodes it to static/clouds-bg.mp4 /
.webm (upscaled 2.4x with Lanczos) plus static/clouds-poster.jpg, per
the brief's "prefer video over raw gif" note - 6.6MB -> ~2MB combined.

Per-frame analysis found the flare/cloud-churn ("busy" motion) roams
x=5-56%, y=22-48% of the frame and never touches the top ~20% strip.
background-position "center top" on the fixed video therefore keeps
that busiest band anchored away from the very top of the viewport,
and the hero scrim (which sits at the top) additionally neutralizes
whatever brightness is behind it - verified against the brightest
sampled frame (max_brightness ~247.7, i.e. near-white flare core).
"""

STATIC_BASE = "app/static"

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?"
    "family=Fredoka:wght@500;600;700&"
    "family=Inter:wght@400;500;600;700&display=swap"
)

_HERO_MARK_PATHS = """
<svg class="vwhim-mark" viewBox="0 0 168 56" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="A rough scribble turning into a smooth wave">
  <path class="vwhim-mark-sketch" d="M4 34 L11 22 L15 40 L21 16 L26 44 L32 20 L37 38 L43 26 L48 33 L54 29"
        stroke="#22314f" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path class="vwhim-mark-arrow" d="M66 28 H86 M79 21 L86 28 L79 35"
        stroke="#3a548a" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.65"/>
  <path class="vwhim-mark-wave" d="M96 28 C 101 6, 111 6, 116 28 C 121 50, 131 50, 136 28 C 141 6, 151 6, 156 28 C 158 34, 160 30, 162 28"
        stroke="url(#vwhim-wave-grad)" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <defs>
    <linearGradient id="vwhim-wave-grad" x1="96" y1="28" x2="162" y2="28" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#2966a3"/>
      <stop offset="1" stop-color="#8ac0e4"/>
    </linearGradient>
  </defs>
</svg>
"""


def hero_mark(size_px: int = 44) -> str:
    """Signature visual element: a rough scribble resolving into a smooth
    wave, connected by an arrow - 'draw something rough, get real motion
    back' as a single mark. Reused as the page's logo, the pipeline-running
    indicator, and the empty-state graphic so it reads as a signature, not
    a one-off decoration."""
    return (
        f'<div class="vwhim-mark-wrap" style="width:{size_px * 3}px">'
        f"{_HERO_MARK_PATHS}"
        f"</div>"
    )


def render_background() -> str:
    return f"""
<div class="vwhim-bg" aria-hidden="true">
  <video class="vwhim-bg-video" autoplay muted loop playsinline
         poster="{STATIC_BASE}/clouds-poster.jpg">
    <source src="{STATIC_BASE}/clouds-bg.webm" type="video/webm">
    <source src="{STATIC_BASE}/clouds-bg.mp4" type="video/mp4">
  </video>
  <img class="vwhim-bg-poster" src="{STATIC_BASE}/clouds-poster.jpg" alt="" />
</div>
"""


THEME_CSS = f"""
<style>
@import url('{FONT_IMPORT}');

:root {{
  --ink-900: #16213b;
  --ink-700: #222f4f;
  --ink-500: #46567c;
  --accent-600: #2966a3;
  --accent-700: #204f80;
  --accent-800: #1c3f66;
  --sky-200: #cbe3f6;
  --sky-100: #eaf4fb;
  --scrim-950: #101625;
  --glass-border: rgba(255,255,255,0.65);
  --font-display: 'Fredoka', 'Segoe UI', sans-serif;
  --font-body: 'Inter', 'Segoe UI', sans-serif;
}}

html, body, [class*="css"] {{
  font-family: var(--font-body);
  color: var(--ink-900);
}}

/* ---------- fixed background video ---------- */
.vwhim-bg {{
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  z-index: -1;
  overflow: hidden;
  background: #bcdcf0;
}}
.vwhim-bg-video, .vwhim-bg-poster {{
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top; /* keeps the flare's busiest roam zone off the very top strip */
}}
.vwhim-bg-poster {{ display: none; }}

@media (prefers-reduced-motion: reduce) {{
  .vwhim-bg-video {{ display: none; }}
  .vwhim-bg-poster {{ display: block; }}
}}

/* ---------- Streamlit chrome: let the video show through ---------- */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background: transparent !important;
}}
[data-testid="stHeader"] {{
  background: transparent !important;
}}
[data-testid="stAppViewContainer"] .block-container {{
  max-width: 1180px;
  padding-top: 1.5rem;
  padding-bottom: 3rem;
}}

/* ---------- hero ---------- */
.vwhim-hero {{
  display: flex;
  justify-content: center;
  margin-bottom: 1.75rem;
}}
.vwhim-hero-scrim {{
  max-width: 720px;
  width: 100%;
  text-align: center;
  padding: 2.1rem 2rem 1.9rem;
  border-radius: 26px;
  background: radial-gradient(120% 160% at 50% 0%, rgba(10,14,26,0.82), rgba(10,14,26,0.70) 60%, rgba(10,14,26,0.52) 100%);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow: 0 12px 40px rgba(10,16,32,0.32);
}}
.vwhim-mark-wrap {{ margin: 0 auto 0.6rem; opacity: 0.95; }}
.vwhim-mark {{ width: 100%; height: auto; display: block; }}
.vwhim-mark-wave {{
  stroke-dasharray: 5 6;
  animation: vwhim-flow 2.6s linear infinite;
}}
@media (prefers-reduced-motion: reduce) {{
  .vwhim-mark-wave {{ animation: none; }}
}}
@keyframes vwhim-flow {{
  to {{ stroke-dashoffset: -33; }}
}}
.vwhim-hero-scrim .vwhim-hero-title {{
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
  font-size: clamp(2rem, 5vw, 2.9rem);
  color: #ffffff !important;
  margin: 0 0 0.4rem;
  letter-spacing: -0.01em;
  text-shadow: 0 2px 14px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.4);
}}
.vwhim-hero-scrim .vwhim-hero-sub {{
  font-family: var(--font-body) !important;
  font-size: clamp(0.95rem, 2vw, 1.08rem);
  color: #eaf2fc !important;
  margin: 0;
  font-weight: 400;
  text-shadow: 0 1px 8px rgba(0,0,0,0.35);
}}

/* ---------- glass panels ---------- */
.st-key-vwhim_input_panel > div,
.st-key-vwhim_output_panel > div,
.st-key-vwhim_insights_panel > div {{
  border-radius: 22px;
  border: 1px solid var(--glass-border);
}}
.st-key-vwhim_input_panel > div {{
  background: linear-gradient(180deg, rgba(255,255,255,0.52), rgba(255,255,255,0.38));
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  padding: 1.3rem 1.4rem 1.5rem;
  box-shadow: 0 6px 24px rgba(22,33,59,0.10);
}}
.st-key-vwhim_output_panel > div {{
  background: linear-gradient(180deg, rgba(255,255,255,0.66), rgba(255,255,255,0.50));
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  padding: 1.5rem 1.6rem 1.7rem;
  box-shadow: 0 14px 44px rgba(22,33,59,0.16), 0 0 0 1px rgba(255,255,255,0.4) inset;
}}
.st-key-vwhim_insights_panel > div {{
  background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0.30));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 0.9rem 1.3rem 1.1rem;
  box-shadow: 0 4px 18px rgba(22,33,59,0.08);
}}

.vwhim-panel-eyebrow {{
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.78rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--accent-700);
  margin: 0 0 0.5rem;
}}
.vwhim-panel-title {{
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.4rem;
  color: var(--ink-700);
  margin: 0 0 0.3rem;
}}

/* ---------- empty state / signature mark reuse ---------- */
.vwhim-empty {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2.2rem 1rem 1.6rem;
  gap: 0.9rem;
}}
.vwhim-empty .vwhim-mark-wrap {{ width: 190px; }}
.vwhim-empty .vwhim-mark-sketch {{ stroke: var(--ink-500); }}
.vwhim-empty p {{
  color: var(--ink-500);
  font-size: 0.95rem;
  max-width: 32ch;
  margin: 0;
}}

/* ---------- status badge ---------- */
.vwhim-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.95rem;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  margin-bottom: 0.6rem;
}}
.vwhim-badge--ok {{
  background: rgba(41,102,163,0.14);
  color: var(--accent-800);
  border: 1px solid rgba(41,102,163,0.28);
}}
.vwhim-badge--warn {{
  background: rgba(160,110,30,0.12);
  color: #7a5414;
  border: 1px solid rgba(160,110,30,0.25);
}}

/* ---------- typography on glass ---------- */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {{
  font-family: var(--font-display);
  color: var(--ink-700);
}}
p, label, [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] {{
  color: var(--ink-900);
}}
[data-testid="stCaptionContainer"] {{
  color: var(--ink-500) !important;
}}

/* ---------- widgets: blend into glass, keep strong focus rings ---------- */
[data-testid="stFileUploaderDropzone"],
.stTextArea textarea,
.stTextInput input {{
  background: rgba(255,255,255,0.6) !important;
  border: 1px solid rgba(22,33,59,0.14) !important;
  border-radius: 12px !important;
  color: var(--ink-900) !important;
}}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {{
  color: var(--ink-500) !important;
  opacity: 0.85;
}}

button:focus-visible,
[data-testid="stFileUploaderDropzone"]:focus-visible,
.stTextArea textarea:focus-visible,
.stTextInput input:focus-visible,
a:focus-visible {{
  outline: 3px solid var(--accent-600) !important;
  outline-offset: 2px !important;
}}

div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {{
  font-family: var(--font-display);
  font-weight: 600;
  border-radius: 999px !important;
  border: none !important;
  padding: 0.55rem 1.3rem !important;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}}
div[data-testid="stButton"] button[kind="primary"] {{
  background: linear-gradient(135deg, #3a86cf, #163a63) !important;
  color: #ffffff !important;
  border: 1.5px solid rgba(255,255,255,0.55) !important;
  box-shadow: 0 8px 24px rgba(15,40,74,0.5), inset 0 1px 0 rgba(255,255,255,0.3);
  letter-spacing: 0.01em;
}}
div[data-testid="stButton"] button[kind="primary"]:not(:disabled):hover {{
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(15,40,74,0.58), inset 0 1px 0 rgba(255,255,255,0.35);
}}
div[data-testid="stButton"] button[kind="secondary"] {{
  background: rgba(255,255,255,0.75) !important;
  color: var(--accent-800) !important;
  border: 1px solid rgba(41,102,163,0.35) !important;
}}
/* Streamlit wraps button labels in their own markdown container ("p" /
   [data-testid=stMarkdownContainer]), which the global text-color rule
   above also matches directly - a direct rule on that descendant beats
   inheritance from the button, so without this the label text ignores
   whatever color the button itself sets. Force it back to match. */
div[data-testid="stButton"] button[kind="primary"] p,
div[data-testid="stButton"] button[kind="primary"] [data-testid="stMarkdownContainer"] {{
  color: #ffffff !important;
}}
div[data-testid="stButton"] button[kind="secondary"] p,
div[data-testid="stButton"] button[kind="secondary"] [data-testid="stMarkdownContainer"] {{
  color: var(--accent-800) !important;
}}
div[data-testid="stButton"] button[kind="primary"]:disabled {{
  background: linear-gradient(135deg, rgba(58,134,207,0.55), rgba(22,58,99,0.55)) !important;
  color: rgba(255,255,255,0.85) !important;
  border: 1.5px dashed rgba(255,255,255,0.5) !important;
  box-shadow: none;
  opacity: 1 !important;
}}

[data-testid="stExpander"] {{
  background: rgba(255,255,255,0.4);
  border-radius: 14px !important;
  border: 1px solid rgba(22,33,59,0.10) !important;
}}

hr {{
  border-color: rgba(22,33,59,0.14) !important;
}}

/* ---------- mobile ---------- */
@media (max-width: 640px) {{
  [data-testid="stAppViewContainer"] .block-container {{
    padding-left: 0.8rem;
    padding-right: 0.8rem;
  }}
  .vwhim-hero-scrim {{ padding: 1.5rem 1.2rem 1.4rem; border-radius: 20px; }}
  .st-key-vwhim_input_panel > div,
  .st-key-vwhim_output_panel > div {{ padding: 1rem 1.1rem 1.2rem; }}
}}
</style>
"""


def render_hero(title: str, subtitle: str) -> str:
    return f"""
<div class="vwhim-hero">
  <div class="vwhim-hero-scrim">
    {hero_mark(44)}
    <h1 class="vwhim-hero-title">{title}</h1>
    <p class="vwhim-hero-sub">{subtitle}</p>
  </div>
</div>
"""


def status_badge(approved: bool) -> str:
    if approved:
        return '<div class="vwhim-badge vwhim-badge--ok">✓ Approved</div>'
    return '<div class="vwhim-badge vwhim-badge--warn">⚠ Not approved</div>'


def empty_state(message: str) -> str:
    return f"""
<div class="vwhim-empty">
  {hero_mark(38)}
  <p>{message}</p>
</div>
"""
