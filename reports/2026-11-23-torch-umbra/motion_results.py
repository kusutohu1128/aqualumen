"""Follow the same wall locations behind a two-block oak column and between the lanterns."""

import hashlib
import json
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from candidate import HERE, ROOT
from moving import A, B, STAGES, OAK_BASE

W, H = 1280, 720
RGB_Y = np.array([0.2126, 0.7152, 0.0722])
COW_WALL = (608, 263, 638, 281)
COW_CONTROL = (1000, 295, 1013, 309)
TAGS = ("ingame", "x11-a", "x11-b")
ARMS = {"reference": ("moving-reference", "fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"),
        "umbra": ("moving-umbra-r2", "be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2")}


def read(path):
    return json.loads(path.read_text())


def intersects(start, end, margin):
    # Test the open segment against the actual pair of unit solid log blocks.
    lo, hi = np.array(OAK_BASE) - margin, np.array(OAK_BASE) + [1, 2, 1] + margin
    delta = end - start
    moving = abs(delta) > 1e-12
    inv = np.divide(1., delta, out=np.zeros_like(delta), where=moving)
    a, b = (lo - start) * inv, (hi - start) * inv
    entry = np.where(moving, np.minimum(a, b), -np.inf).max(axis=-1)
    leave = np.where(moving, np.maximum(a, b), np.inf).min(axis=-1)
    return (np.maximum(0., entry) < np.minimum(1., leave)) & np.all(moving | ((start > lo) & (start < hi)), axis=-1)


def wall_samples(x):
    # Camera faces north. Sample world coordinates then project to the wall's
    # actual visible face, excluding silhouettes and the wall/floor seams.
    wx, wy = np.meshgrid(np.arange(404.08, 409.92, .022), np.arange(151.1, 154.9, .022))
    world = np.stack([wx, wy, np.full_like(wx, -412.)], axis=-1)
    eye = np.array([x, 152.62, -407.25])
    pitch = np.radians(4)
    forward = np.array([0., -np.sin(pitch), -np.cos(pitch)])
    up = np.array([0., np.cos(pitch), -np.sin(pitch)])
    side = np.array([1., 0., 0.])
    d = world - eye
    focal = (H / 2) / np.tan(np.radians(35))
    px = np.floor(W / 2 + focal * (d @ side) / (d @ forward)).astype(int)
    py = np.floor(H / 2 - focal * (d @ up) / (d @ forward)).astype(int)
    wall = (px > 1) & (px < W-2) & (py > 1) & (py < H-2) & ~intersects(eye, world, .045)
    source = eye + .32 * side - .30 * up + .43 * forward
    # For any radius-.13 disk orientation, its entire family of ray segments
    # is inside a .13 envelope around the centre ray. Erode/dilate the box.
    shade = wall & intersects(source, world, -.14)
    lit = wall & ~intersects(source, world, .16)
    assert shade.sum() > 100 and lit.sum() > 3000, (x, shade.sum(), lit.sum())
    return {name: (py[mask], px[mask]) for name, mask in (("shadow", shade), ("lit", lit), ("wall", wall))}


def gather(label):
    path, expected = ARMS[label]
    folder = HERE / path
    r = read(folder / "complete.json")
    pre = read(folder / "preflight.json")
    assert r["complete"] and not r["failure"] and r["size"] == [W, H] and r["originalWorldAndConfigUnchanged"]
    assert r["stages"] == STAGES and r["sourcePackShaNow"] == r["packSha256"] == expected
    assert "RTX 3080 Ti" in r["gl"]["renderer"] and pre["labAfter"] == pre["labBefore"] and not pre["foreignObservations"]
    log = (folder / "client.log").read_text(errors="replace")
    assert list(map(int, re.findall(r'\[Server\] AQ_HAND_STEP_(\d+)', log))) == list(range(1, 25))
    route = read(folder / "trajectory.json")
    assert len(route["positions"]) >= 30 and route["displacementM"] > 2
    images = {}
    for stage in STAGES:
        for tag in TAGS:
            image = folder / (stage + "-" + tag + ".png")
            assert hashlib.sha256(image.read_bytes()).hexdigest() == r["screenshots"][stage][tag]
            with Image.open(image) as frame:
                assert frame.size == (W, H)
                images[(stage, tag)] = np.asarray(frame.convert("RGB"))
    return images, dict(renderer=r["gl"]["renderer"], pack=r["packSha256"], cowDisplacementM=route["displacementM"],
                        cowSamples=len(route["positions"]), handTravelMetres=round(B-A, 2), handSteps=24)


def region(image, rect):
    x, y, r, b = rect
    return image[y:b, x:r].mean(axis=(0,1))


def crossing(folder):
    # Decode at quarter-second intervals. The compressed video uses 4:2:0;
    # use an even crop origin and compare it only to its own pre-crossing levels.
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(folder/"crossing.mp4"), "-vf", "fps=4,crop=30:18:608:264",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ])
    values = np.frombuffer(raw, np.uint8).reshape(-1,18,30,3).mean(axis=(1,2))
    assert len(values) == 80
    chroma = values[:,0] - values[:,2]
    start, end = np.median(chroma[8:28]), np.median(chroma[-8:])
    return dict(secondsPerSample=.25, wallRectangle=[608,264,638,282], redMinusBlue=chroma.round(2).tolist(),
                settledStart=float(start), min=float(chroma.min()), max=float(chroma.max()), settledEnd=float(end))


def comparison_image(pictures):
    items = [
        ("both-restored", "二灯のみ・順応後"), ("both-west", "牛が暖色の光を遮る"), ("both-east", "牛が青い光を遮る"),
        ("hand-left-clear", "手持ちの松明・柱を外す"), ("hand-left-oak", "同じ位置にオークの柱"), ("hand-right-oak", "松明を持って右へ1.4 m"),
    ]
    canvas = Image.new("RGB", (1170, 636), "#19201f")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 17)
    for i,(stage,title) in enumerate(items):
        frame = Image.fromarray(pictures[stage,"ingame"])
        if i < 3:
            frame = frame.crop((190,190,1060,720))
        frame.thumbnail((386,278), Image.Resampling.LANCZOS)
        x, y = (i%3)*390, (i//3)*318
        canvas.paste(frame,(x+(390-frame.width)//2,y+(278-frame.height)//2))
        draw.text((x+13,y+279), title, fill="white", font=font)
    canvas.save(HERE/"moving-comparison.jpg", quality=94)


def analyze(images):
    stages = ("both-empty", "both-west", "both-east", "both-restored", "walk-cleared")
    cow = {}
    hand = {}
    for tag in TAGS:
        cow[tag] = {s: {k: region(images[s,tag], box).round(3).tolist()
                        for k,box in (("wallRGB", COW_WALL), ("controlRGB", COW_CONTROL))}
                    for s in stages}
        hand[tag] = {}
        for name, x, dark in (("left", A, "hand-dark"), ("right", B, "hand-right-dark")):
            samples = wall_samples(x)
            side = {}
            for group, pts in samples.items():
                oak = images["hand-"+name+"-oak", tag][pts].astype(float) @ RGB_Y
                clear = images["hand-"+name+"-clear", tag][pts].astype(float) @ RGB_Y
                off = images[dark, tag][pts].astype(float) @ RGB_Y
                side[group] = dict(points=len(oak), clearMinusOakMedian=float(np.median(clear-oak)),
                                   clearMinusDarkMedian=float(np.median(clear-off)),
                                   clearMedian=float(np.median(clear)), oakMedian=float(np.median(oak)))
            hand[tag][name] = side
    return dict(cow=cow, hand=hand)


def main():
    arms, pictures, differences = {}, {}, {}
    for label in ARMS:
        pictures[label], run = gather(label)
        arms[label] = {**run, "folder": ARMS[label][0], **analyze(pictures[label]), "crossing": crossing(HERE/ARMS[label][0])}
    for stage in STAGES:
        per_tag = {}
        for tag in TAGS:
            a, b = [pictures[k][stage, tag] for k in ARMS]
            if stage.startswith("hand-"):
                pts = wall_samples(B if "right" in stage else A)["wall"]
                a, b = a[pts], b[pts]
            else:
                x, y, r, bot = COW_WALL
                a, b = a[y:bot,x:r], b[y:bot,x:r]
            diff = np.abs(a.astype(int) - b).max(axis=-1)
            per_tag[tag] = dict(points=diff.size, median=float(np.median(diff)),
                                p95=float(np.quantile(diff,.95)), max=int(diff.max()))
        differences[stage] = per_tag
    report = dict(cameraFovY=70, sampleGridMetres=.022, oakBase=OAK_BASE, cowPatch=COW_WALL,
                  controlPatch=COW_CONTROL, runs=arms, maxChannelDifferences=differences)
    for manifest in ("geometry.json", "observer.json"):
        assert read(HERE/ARMS["reference"][0]/manifest) == read(HERE/ARMS["umbra"][0]/manifest)
    checks = {}
    for label, run in arms.items():
        samples = run["crossing"]
        checks[label+"MovingShadowChangesColour"] = (
            samples["min"] < samples["settledStart"]-20 and samples["max"] > samples["settledStart"]+20
        )
        checks[label+"MovingShadowClears"] = abs(samples["settledStart"] - samples["settledEnd"]) < 1.0
        checks[label+"ColumnShadesThePredictedWall"] = all(
            side["shadow"]["clearMinusOakMedian"] > 3 * abs(side["lit"]["clearMinusOakMedian"])
            and side["shadow"]["clearMinusOakMedian"] > 10
            for sides in run["hand"].values() for side in sides.values()
        )
    checks["settledF2MatchesWithinOneLevel"] = all(
        tags["ingame"]["max"] <= 1 for s,tags in differences.items() if s != "both-empty"
    )
    report["checks"] = checks
    (HERE / "moving.json").write_text(json.dumps(report, indent=2)+"\n")
    comparison_image(pictures["umbra"])
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()
