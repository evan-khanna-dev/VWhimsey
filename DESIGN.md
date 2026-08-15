# Design Brief — VWhimsey

## What this is
A sketch-to-VFX tool. A user uploads a photo of a hand-drawn sketch
(shapes, squiggles, whatever they can draw), describes how it should
move, and a multi-agent pipeline (Interpreter → Generator →
Critique/Refine) turns it into an exportable animated SVG. There's
also an "Insights" panel where the tool answers questions about its
own past generation history (pulled live from ClickHouse via MCP).

## Audience
Two real, distinct users:
1. **Beginner/emerging indie creators** who can't afford a VFX artist
   and don't have time to climb the learning curve of Unity, Unreal,
   or Premiere Pro. For them, this replaces "hire someone or spend
   months learning software" with "draw what you already know how to
   draw."
2. **Experienced artists/designers who can sketch well** — for them,
   this is a fast drafting/pre-viz step, quicker than opening a full
   timeline editor, before they build the polished version in their
   real tool.

The tone should feel accessible and a little magical/whimsical — not
enterprise-SaaS, not a bare technical demo. This is a creative toy
that happens to be genuinely useful, not a dashboard.

## Background asset
There's a looping cloud/flare gif (soft pastel blue clouds with a
bright white light flare) intended as the page background — it's
meant to convey the "whimsy" of the VFX the tool produces. A single
frame is attached for reference: pale blue-cyan clouds, brightest
near center-right where a white flare sits.

### Requirements for how content sits on top of it
- Do NOT put text or UI controls directly on the raw gif with no
  treatment — contrast will fail against both the pale blue and the
  bright flare at different points in the loop.
- Use translucent "glass" panels for content areas: a soft
  `backdrop-filter: blur()` + a semi-transparent white/light fill
  (not a hard opaque card) — this keeps the dreamy tone while making
  text reliably readable regardless of what the gif is doing behind
  it at any given moment.
- Where a gradient scrim is used to improve text contrast, scope it
  to just the content area (e.g. behind the hero headline) rather
  than dimming the whole background — the goal is to preserve the
  gif's vividness everywhere it's not competing with text.
- Pull text/UI accent colors from the SAME hue family as the
  background (deep slate-blue / indigo range, not plain black or an
  unrelated accent color) so the UI and background feel like one
  cohesive world.
- If possible, crop/position the gif loop so its busiest motion (the
  flare, the cloud churn) stays away from the exact zones where body
  text sits — motion directly behind static text hurts readability
  more than color contrast alone.
- Respect `prefers-reduced-motion`: freeze on a static representative
  frame for users with that preference set.
- Prefer a looping video (webm/mp4) over a raw animated GIF for the
  actual background if feasible — smaller file size, smoother loop,
  same visual result.
- Whatever the final palette ends up being, verify text contrast
  specifically against the BRIGHTEST moment of the loop (near the
  flare), not just an average or dark frame.

## User flow (current, functional — don't break it)
1. Upload a sketch photo
2. Type a movement description
3. Click Generate — pipeline runs (Interpreter → Generator → Critic,
   with possible retry pass)
4. See the animated SVG result, approval status, passes used
5. Download the SVG
6. Expandable debug log of what each agent produced
7. Separate "Insights" section: ask a question, get an answer pulled
   from real ClickHouse run history via the MCP server

## What should visually lead
The generated SVG preview is the best asset this product has — the
actual moving output should be the visual hero, not buried below
input fields. The sketch upload / description input should feel
lightweight and secondary by comparison — the "before," with the
generated result as the "after" payoff.

## Open design questions for you to resolve
- Should Insights feel like an integrated part of the same flow, or
  a distinct secondary tool/section? Make a deliberate choice and
  justify it briefly.
- Typography: nothing decided yet — pick a display face with some
  personality (this is a creative/whimsical product, not enterprise
  software) paired with a clean, restrained body face.
- Come up with one signature visual element for this page that
  embodies "draw something rough, get real motion back" — this is
  the thing the page should be remembered by.

## Constraints
- Built in Streamlit (Python) — work within what's stylable via
  custom CSS/HTML injection in Streamlit, not a full framework
  rewrite.
- Must stay responsive down to mobile.
- Must keep visible keyboard focus states.