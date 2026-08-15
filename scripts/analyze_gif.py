"""One-off analysis of assets/clouds-enhanced.gif to inform background
CSS decisions: dimensions, frame count/duration, where the brightest
(flare) region sits per-frame, and the dominant hues to build an
accent palette from. Not part of the app; run manually and discard."""

import json
from PIL import Image, ImageSequence

path = "assets/clouds-enhanced.gif"
im = Image.open(path)

print("size:", im.size)
print("n_frames:", getattr(im, "n_frames", 1))

frames_info = []
for i, frame in enumerate(ImageSequence.Iterator(im)):
    rgb = frame.convert("RGB")
    small = rgb.resize((64, 64))
    px = list(small.getdata())
    # brightness per pixel
    brightness = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px]
    max_b = max(brightness)
    mean_b = sum(brightness) / len(brightness)
    idx = brightness.index(max_b)
    bx, by = idx % 64, idx // 64
    duration = frame.info.get("duration", 0)
    frames_info.append({
        "frame": i,
        "mean_brightness": round(mean_b, 1),
        "max_brightness": round(max_b, 1),
        "flare_xy_pct": (round(bx / 64 * 100), round(by / 64 * 100)),
        "duration_ms": duration,
    })

for f in frames_info:
    print(f)

# Brightest overall frame (peak flare) and darkest/calmest frame
brightest = max(frames_info, key=lambda f: f["max_brightness"])
calmest = min(frames_info, key=lambda f: f["mean_brightness"])
print("\nBRIGHTEST (peak flare) frame:", brightest)
print("CALMEST (lowest mean brightness) frame:", calmest)

# Sample dominant hues from a mid-brightness frame across full image
im.seek(0)
mid_frame = im.convert("RGB")
small = mid_frame.resize((80, 80))
colors = small.getcolors(80 * 80)
colors.sort(key=lambda c: -c[0])
print("\nTop colors (count, (r,g,b)) from frame 0:")
for count, rgb in colors[:12]:
    print(count, rgb, "-> hex #%02x%02x%02x" % rgb)

with open("scripts/gif_analysis.json", "w") as f:
    json.dump({"frames": frames_info}, f, indent=2)
