"""One-off: convert assets/clouds-enhanced.gif into a looping mp4/webm
(smaller, smoother than raw GIF per DESIGN.md) plus a static poster
frame for prefers-reduced-motion. Upscales slightly with Lanczos since
the source is only 400x222. Not part of the app; run manually."""

import subprocess
import tempfile
import os

from PIL import Image, ImageSequence
import imageio_ffmpeg

SRC = "assets/clouds-enhanced.gif"
OUT_DIR = "static"  # Streamlit serves this dir at app/static/ when enableStaticServing is on
TARGET_W, TARGET_H = 960, 534  # upscaled ~2.4x, keeps the 400x222 aspect (1.802); even dims for h264

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
print("ffmpeg:", ffmpeg)

im = Image.open(SRC)

with tempfile.TemporaryDirectory() as tmp:
    durations = []
    i = 0
    for frame in ImageSequence.Iterator(im):
        rgb = frame.convert("RGB").resize((TARGET_W, TARGET_H), Image.LANCZOS)
        rgb.save(os.path.join(tmp, f"f{i:04d}.png"))
        durations.append(frame.info.get("duration", 70))
        i += 1
    n = i
    avg_ms = sum(durations) / len(durations)
    fps = 1000 / avg_ms
    print(f"{n} frames, avg {avg_ms:.1f}ms/frame -> {fps:.2f} fps")

    # Poster frame = frame 0 (matches the reference frame described in the brief)
    Image.open(os.path.join(tmp, "f0000.png")).save(
        os.path.join(OUT_DIR, "clouds-poster.jpg"), quality=90
    )

    in_pattern = os.path.join(tmp, "f%04d.png")

    # H.264 mp4 (broad support)
    subprocess.run([
        ffmpeg, "-y", "-framerate", f"{fps:.4f}", "-i", in_pattern,
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        os.path.join(OUT_DIR, "clouds-bg.mp4"),
    ], check=True)

    # VP9 webm (smaller, modern browsers)
    subprocess.run([
        ffmpeg, "-y", "-framerate", f"{fps:.4f}", "-i", in_pattern,
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1",
        os.path.join(OUT_DIR, "clouds-bg.webm"),
    ], check=True)

print("done")
for f in ["clouds-bg.mp4", "clouds-bg.webm", "clouds-poster.jpg"]:
    p = os.path.join(OUT_DIR, f)
    print(f, os.path.getsize(p) if os.path.exists(p) else "MISSING")
