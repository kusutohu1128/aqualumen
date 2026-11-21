"""Audit the two native recordings against their read-only route and saved private world."""
import gzip
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageStat

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-21-indirect-light"))
import capture


def frame(video, seconds):
    data = subprocess.check_output([
        "ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(video), "-frames:v", "1",
        "-f", "image2pipe", "-c:v", "png", "pipe:1",
    ])
    return Image.open(io.BytesIO(data)).convert("RGB")


def audit(name):
    out = HERE / name
    record = json.loads((out / "complete.json").read_text())
    plan = json.loads((out / "plan.json").read_text())
    assert record["status"] == "finished" and not record["problems"] and record["world"]["sourceUnchanged"]
    video = out / "walk.mp4"
    assert capture.sha(video.read_bytes()) == record["video"]["sha256"]
    assert record["sha256"] == capture.sha((HERE.parents[1] / "dist" / record["pack"]).read_bytes())
    route = json.loads((HERE / "forest-to-bank.json").read_text())
    samples = [json.loads(line) for line in (out / "samples.jsonl").read_text().splitlines()]
    last = samples[-1]
    assert [int(value // 1) for value in last["pos"]] == route["bank"] and last["grounded"]
    assert not any(s["flying"] for s in samples)
    game = Path((out / "private-game.txt").read_text().strip())
    world = game / "saves" / record["world"]["name"]
    data = capture.nbt(gzip.decompress((world / "level.dat").read_bytes()))["Data"]
    assert data["DayTime"] == plan["time"] and bool(data["raining"]) == (plan["weather"] == "rain")
    kit = world / "datapacks/ContinuousWalk"
    manifest = capture.tree(kit)
    assert capture.digest(manifest) == plan["datapackDigest"]
    # Archive only our generated commands, including the exact steering for this run.
    archive = out / "route-commands.zip"
    if not archive.exists():
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(manifest):
                z.write(kit / path, path)
    with zipfile.ZipFile(archive) as z:
        assert {path: capture.sha(z.read(path)) for path in z.namelist()} == manifest

    positions = []
    for held, t in [(False, 1.5), (True, next(s["videoSeconds"] for s in samples if s["lightInMainhand"]) + 0.9)]:
        nearest = min(samples, key=lambda s: abs(s["videoSeconds"] - t))
        assert nearest["pos"] == [92.5, 64.0, 394.5] and nearest["lightInMainhand"] == held and nearest["stage"] == 0
        assert nearest["yaw"] == 90.0 and nearest["pitch"] == -12.0
        im = frame(video, t)
        w, h = im.size
        roi = (w // 3, h // 3, w * 5 // 12, h // 2)
        positions.append(dict(held=held, seconds=t, rectangle=roi, displayRGB=[round(v, 2) for v in ImageStat.Stat(im.crop(roi)).mean]))
    return dict(clip=name, verifiedWeather=plan["weather"], verifiedTime=data["DayTime"],
                finalFeet=last["pos"], noFlight=True, samples=len(samples), heldBark=positions,
                videoSHA=record["video"]["sha256"], commandSHA=capture.sha(archive.read_bytes()))


if __name__ == "__main__":
    data = [audit(role) for role in ("dusk-walk-final", "rain-bank")]
    print(json.dumps(data, indent=2))
