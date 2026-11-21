"""Make a viewable clip using capture timestamps and measure the wall away from the hands."""

import csv
import json
import subprocess
import sys
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parent
run = root / sys.argv[1] / "capture"
scene = "lamp-hand-" + sys.argv[2]
dest = root / (sys.argv[1] + "-" + sys.argv[2] + ".mp4")
row = json.loads((run / (scene + ".json")).read_text())
fixture = row["local_light_fixture"]
data = fixture["hand_light"]
assert row["camera_eye_match"] and data["settled_at_capture"]
clip = run / ("full-frame-" + scene)
width, height = row["framebuffer_resolution"]
frames = np.memmap(clip / "bottom-up.rgba", dtype=np.uint8, mode="r").reshape(
    -1, height, width, 4
)
with (clip / "ticks.csv").open() as f:
    times = np.array([int(r["elapsed_ns"]) for r in csv.DictReader(f)])
with (run / (scene + "-hand-trace.csv")).open() as f:
    hands = list(csv.DictReader(f))
assert len(frames) == len(times) and np.all(np.diff(times) > 0) and len(frames) > 1
hand_times = np.array([int(h["elapsed_ns"]) for h in hands])
pose = np.stack(
    [
        np.interp(times, hand_times, [float(h["camera_" + axis]) for h in hands])
        for axis in "xyz"
    ],
    axis=1,
)
mat = fixture["render_projection"]
vp = (
    np.array(mat["projection"]).reshape(4, 4).T
    @ np.array(mat["model_view"]).reshape(4, 4).T
)
point = np.array(fixture["surface_samples"]["hand-back-wall-east"])
world = np.concatenate((point - pose, np.ones((len(times), 1))), axis=1)
hom = world @ vp.T
pixels = np.rint(
    (hom[:, :2] / hom[:, 3, None] + 1) * np.array([width, height]) / 2
).astype(int)
rgb = np.array(
    [
        frames[i, y - 3 : y + 4, x - 3 : x + 4, :3].mean(axis=(0, 1))
        for i, (x, y) in enumerate(pixels)
    ]
)
assert np.isfinite(rgb).all()
with (run / (scene + "-hand-swaps.csv")).open() as f:
    swaps = list(csv.DictReader(f))
if not dest.exists():
    p = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-n",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgba",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            "25",
            "-i",
            "-",
            "-vf",
            "vflip",
            "-c:v",
            "libx264",
            "-threads",
            "3",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dest),
        ],
        stdin=subprocess.PIPE,
    )
    for t in np.arange(0, times[-1] + 1, 40_000_000):
        p.stdin.write(
            frames[max(0, np.searchsorted(times, t, side="right") - 1)].tobytes()
        )
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
summary = {
    "shaderSha256": row["pack_sha256"],
    "size": [width, height],
    "capturedFrames": len(times),
    "durationSec": round(times[-1] * 1e-9, 4),
    "maxCaptureGapMs": round(np.diff(times).max() * 1e-6, 2),
    "cameraXRange": np.ptp(pose, axis=0)[0],
    "actualClientObservedTransitions": swaps,
    "wallWorldPoint": point.tolist(),
    "receiverRedGreenBlueDisplay8MedianBySecond": [
        np.round(np.median(rgb[times // 1_000_000_000 == i], axis=0), 1).tolist()
        for i in sorted(set(times // 1_000_000_000))
    ],
    "measurement": "7x7 display pixels at the projected back-wall point. During walking the pillar can cover this point. Missing video slots repeat the preceding captured frame.",
}
dest.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
