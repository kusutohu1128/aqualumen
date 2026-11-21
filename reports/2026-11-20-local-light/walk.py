"""Check a stationary wall patch in the recorded moving camera frames, across the grid snap."""
from pathlib import Path
import csv
import json
import sys
import subprocess
import numpy as np

root = Path(__file__).resolve().parent
role = sys.argv[1] if len(sys.argv) > 1 else "walk"
assert role in ("walk", "final-walk")
folder = root / role / "capture"
scene = "lamp-night-walk"
clip = folder / ("full-frame-" + scene)
row = json.loads((folder / (scene + ".json")).read_text())
fixture = row["local_light_fixture"]
matrices = fixture["render_projection"]
projection = np.array(matrices["projection"]).reshape(4, 4).T
model = np.array(matrices["model_view"]).reshape(4, 4).T
width, height = matrices["framebuffer"]
assert [width, height] == [960, 540] and row["camera_eye_match"]
frames = np.memmap(clip / "bottom-up.rgba", mode="r", dtype=np.uint8).reshape(-1, height, width, 4)
with (clip / "ticks.csv").open() as f:
    times = np.array([int(r["elapsed_ns"]) for r in csv.DictReader(f)])
with (folder / (scene + "-walk-route.csv")).open() as f:
    pose = list(csv.DictReader(f))
assert len(frames) == len(times) and np.all(np.diff(times) > 0)
pose_time = np.array([int(v["elapsed_ns"]) for v in pose])
xs = np.array([float(v["camera_x"]) for v in pose])
at = np.interp(times, pose_time, xs)
cross = np.where((at[:-1] >= 408) & (at[1:] < 408))[0] + 1
assert len(cross) == 1
i = int(cross[0])
point = np.array(fixture["surface_samples"]["receiver-back-wall"])
reference_eye = np.array(matrices["eye"])
values = []
for n, x in enumerate(at):
    eye = reference_eye.copy()
    eye[0] = x
    v = projection @ model @ np.append(point - eye, 1)
    px, py = np.rint((v[:2] / v[3] + 1) * np.array([width, height]) / 2).astype(int)
    patch = frames[n, py-3:py+4, px-3:px+4, :3]
    values.append(patch.mean(axis=(0, 1)))
values = np.array(values)
changes = np.abs(np.diff(values, axis=0))
summary = dict(frames=len(frames), poseRows=len(pose), firstCameraX=float(at[0]), lastCameraX=float(at[-1]),
    boundaryFrame=i, boundaryTimeSeconds=times[i]*1e-9, reprojectedReceiver="receiver-back-wall",
    deltaAcrossBoundaryRGB8=changes[i-1].tolist(), largestStepRGB8=changes.max(axis=0).tolist(),
    maxFrameGapMs=np.diff(times).max()*1e-6,
    routeNoise="7x7 mean colour of a stationary wall; pose samples interpolated at recorded frame times")
(root / (role + "-measurements.json")).write_text(json.dumps(summary, indent=2) + "\n")
out = root / (role + ".mp4")
if not out.exists():
    # The guarded recorder writes at most one frame per 40 ms slot.
    # Duplicate the preceding actual frame for any missed video slot.
    proc = subprocess.Popen(["ffmpeg","-v","error","-n","-f","rawvideo","-pixel_format","rgba","-video_size",f"{width}x{height}",
        "-framerate","25","-i","-","-vf","vflip","-c:v","libx264","-threads","2","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(out)],stdin=subprocess.PIPE)
    for t in np.arange(0, times[-1]+1, 40_000_000):
        proc.stdin.write(frames[max(0, np.searchsorted(times,t,side="right")-1)].tobytes())
    proc.stdin.close()
    assert proc.wait() == 0
print(json.dumps(summary))
