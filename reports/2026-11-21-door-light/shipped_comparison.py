"""Compare the original and released shader in the sunset house and birch shade."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont, ImageStat

import measure


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHA = "0b1843fd4172f80a2ffa3ce885974119b6c4b04b83a43f236bee96001be80a5e"


def load(path):
    return json.loads(path.read_text())


def save(name, data):
    with (HERE / name).open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def sheet(name, columns, cells, size):
    w, h = size
    caption = 37
    canvas = Image.new("RGB", (columns * w, (h + caption) * ((len(cells) + columns - 1) // columns)), "#1b1e21")
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 18)
    for index, (path, text) in enumerate(cells):
        x, y = (index % columns) * w, (index // columns) * (h + caption)
        with Image.open(path) as im:
            canvas.paste(im.convert("RGB").resize(size, Image.Resampling.LANCZOS), (x, y))
        pen.text((x + 12, y + h + 4), text, font=font, fill="white")
    canvas.save(HERE / name, quality=93)


def house(settled=False):
    before, after = HERE / "before-r1", HERE / "shipped"
    older = measure.analyse(before, None)
    late = HERE / "shipped-settled" if settled else None
    current = measure.analyse(after, late)
    suffix = "-settled" if settled else ""

    def shot(role):
        folder = late if late and (late / (role + ".png")).is_file() else after
        return folder / (role + ".png")
    assert current["sha256"] == SHA and older["sha256"] != SHA
    assert len(current["captureOrder"]) == len(older["captureOrder"]) == 18
    a = current["contributionsDisplayLinearLuma"]
    # Check opposite sides of the partition and each light independently.
    for patch in ("warm", "warm-near"):
        v = a[patch]
        assert v["open"] > 0.035 and abs(v["closed"]) < 0.15 * v["open"], v
        assert abs(v["open"] - v["noDoor"]) < 0.2 * v["open"], v
        assert abs(v["cowInDoorway"]) < 0.20 * v["noDoor"], v
        assert abs(v["returnedClosed"]) < 0.15 * v["open"], v
    assert min(a["soul"]["closed"], a["soul"]["open"]) > .05
    assert abs(a["soul"]["closed"] - a["soul"]["open"]) < .007, a["soul"]
    save("house" + suffix + "-results.json", dict(before=older, shipped=current))
    sheet("house" + suffix + ".jpg", 2, [
        (shot("wide-closed-both"), "ダークオークを閉める　手前の魂のランタンと西日の帯"),
        (shot("wide-open-both"), "扉を開ける　奥のランタンから白い床へ届く暖色"),
        (shot("closed-warm"), "奥のランタンだけを点灯　扉を閉める"),
        (shot("open-warm"), "同じランタン、同じ床　扉を開ける"),
        (shot("nodoor-warm"), "扉を外し、光路を空ける"),
        (shot("cow-warm"), "同じ場所に牛が立つ"),
    ], (640, 360))


def birch():
    folder = HERE / "birch-native" / "capture"
    run = load(folder / "run.json")
    assert run["gl_renderer"].startswith("NVIDIA GeForce RTX 3080 Ti")
    assert run["pack_sha256"] == SHA and run["shader_active"] and not run["shader_fallback"]
    assert load(folder / "complete.json")["fixture_cleanup_complete"]
    labels = [("ground-noon", "午後の木陰　消灯"), ("ground-evening", "同じ幹　松明を置く"), ("ground-low-sun", "同じ幹　魂の松明を置く")]
    regions = load(HERE.parent / "2026-11-21-indirect-light/birch-final.json")["regions"]
    rows = {}
    for role, _ in labels:
        shot = load(folder / (role + ".json"))
        assert shot["framebuffer_resolution"] == [2560, 1440] and shot["window_focused"]
        with Image.open(folder / (role + ".png")) as im:
            rows[role] = {label: [round(v, 3) for v in ImageStat.Stat(im.convert("RGB").crop(tuple(rect))).mean]
                          for label, rect in regions.items()}
        rows[role]["meanFPS"] = shot["mean_fps"]
        rows[role]["p99Ms"] = shot["p99_ms"]
    off, warm, soul = (rows[name]["birch"] for name, _ in labels)
    assert warm[0] - off[0] > 20 and soul[2] - off[2] > 12
    save("birch.json", dict(packSHA256=SHA, regions=regions, renderer=run["gl_renderer"], roles=rows))
    sheet("birch.jpg", 3, [(folder / (name + ".png"), title) for name, title in labels], (512, 288))


if __name__ == "__main__":
    {"house": house, "settled": lambda: house(True), "birch": birch}[sys.argv[1]]()
