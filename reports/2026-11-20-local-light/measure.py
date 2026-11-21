"""Measure projected world receivers on actual Minecraft PNGs (9 x 9 output pixels)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def read_scene(folder, scene):
    row = json.loads((folder / (scene + ".json")).read_text())
    assert row["shader_active"] and not row["shader_fallback"] and row["camera_eye_match"]
    fixture = row["local_light_fixture"]
    assert fixture["pre_sample_block_validation"]["passed"]
    return row, fixture, np.asarray(Image.open(folder / (scene + ".png")).convert("RGB"))


def sample_rgb(image, x, y, radius=4):
    x, y = round(x), round(y)
    h, w = image.shape[:2]
    if not (radius <= x < w - radius and radius <= y < h - radius):
        raise ValueError("Receiver falls outside image")
    region = image[y-radius:y+radius+1, x-radius:x+radius+1]
    return region.mean(axis=(0, 1)).round(2).tolist()


def actual_receiver_pixels(role, row, fixture):
    observation = fixture.get("render_projection")
    origin = "Iris camera matrices captured for this frame"
    if not observation:
        # The first timing run saved the setting FOV. Spectator flight changes
        # the actual projection. Reuse only a separately observed matching pose.
        for source in ("emitter-display", "optics"):
            for key in ("lamp-day-canopy", "lamp-night-off"):
                path = ROOT / source / "capture" / (key + ".json")
                if not path.is_file():
                    continue
                reference = json.loads(path.read_text())
                if reference["actual_camera_rotation"] != row["actual_camera_rotation"]:
                    continue
                if not np.allclose(reference["actual_camera_position"], row["actual_camera_position"], atol=0.00001):
                    continue
                observation = reference["local_light_fixture"].get("render_projection")
                if observation:
                    origin = f"Matching Iris camera matrices from {source}/{key}"
                    break
            if observation:
                break
    if not observation:
        return {}, "No matching rendered projection"
    w, h = row["framebuffer_resolution"]
    rw, rh = observation["framebuffer"]
    assert w * rh == h * rw
    proj = np.array(observation["projection"]).reshape(4, 4).T
    view = np.array(observation["model_view"]).reshape(4, 4).T
    eye = np.array(row["actual_camera_position"])
    targets = dict(fixture["surface_samples"])
    if "lantern-reflection" in observation["pixels"]:
        x, y = observation["pixels"]["lantern-reflection"]
        result = {"lantern-reflection": [x*w/rw, y*h/rh]}
    else:
        result = {}
    for key, xyz in targets.items():
        clip = proj @ view @ np.append(np.array(xyz)-eye, 1)
        if clip[3] > 0:
            x, y = clip[:2] / clip[3]
            result[key] = [(1+x)*w/2, (1-y)*h/2]
    return result, origin


def measure(role):
    folder = ROOT / role / "capture"
    run = json.loads((folder / "run.json").read_text())
    assert "NVIDIA GeForce RTX 3080 Ti" in run["gl_renderer"]
    assert json.loads((folder / "complete.json").read_text())["status"] == "complete"
    out = {}
    for scene in run["scenarios"]:
        row, fixture, image = read_scene(folder, scene)
        points, origin = actual_receiver_pixels(role, row, fixture)
        out[scene] = {
            "eye": row["actual_camera_position"],
            "rotation": row["actual_camera_rotation"],
            "meanFPS": row["mean_fps"],
            "p99ms": row["p99_ms"],
            "frames": row["frames"],
            "sampleSeconds": row["sample_seconds_actual"],
            "projectionSource": origin,
            "pixels": points,
            "RGB8": {name: sample_rgb(image, *point) for name, point in points.items()},
        }
    return {"sha256": run["pack_sha256"], "renderer": run["gl_renderer"],
            "size": run["resolution"], "scenes": out}


if __name__ == "__main__":
    roles = ["old-baseline", "photon-default", "delivery", "optics", "adaptive", "final"]
    result = {role: measure(role) for role in roles}
    (ROOT / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
