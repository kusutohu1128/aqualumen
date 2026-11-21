"""Measure completed rain runs from their saved PNG frames (stdlib + ffmpeg only) and draw the figures.

    python3 measure.py            # every complete base-r*/rc2-r* run -> results.json, figures
Display luminance: each pixel's sRGB8 is linearised, Y = 0.2126 R + 0.7152 G + 0.0722 B, then averaged
over the 11x11 patch (exposure and tone mapping included). Hold values are per-frame medians.
"""

import json
import math
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fixture as F  # noqa: E402

LIN = [((v / 255) / 12.92) if v <= 10 else (((v / 255) + 0.055) / 1.055) ** 2.4 for v in range(256)]
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
PAIRS = ["stone-near", "stone-far", "smooth-near", "smooth-far", "frame"]
TICK = 0.05


def rgb(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"],
                          check=True, capture_output=True, timeout=20).stdout


def patch_y(raw, rect):
    x0, y0, x1, y1 = rect
    acc = 0.0
    for y in range(y0, y1):
        row = raw[(y * F.WIDTH + x0) * 3:(y * F.WIDTH + x1) * 3]
        for i in range(0, len(row), 3):
            acc += 0.2126 * LIN[row[i]] + 0.7152 * LIN[row[i + 1]] + 0.0722 * LIN[row[i + 2]]
    return acc / ((x1 - x0) * (y1 - y0))


def frame_values(path, pose):
    raw = rgb(path)
    return {s["name"]: patch_y(raw, s["patch"]) for s in F.samples(pose) if s["valid"]}


def r5(v):
    return None if v is None else round(v, 5)


def pair_ratio(vals, pair):
    names = [s["name"] for s in F.SAMPLES if s["pair"] == pair]
    sh = [n for n in names if "shelter" in n][0]
    ex = [n for n in names if "exposed" in n][0]
    return vals[ex] / vals[sh] if vals.get(sh) else None


def wetness_model(t_end, up, down, rain_on, rain_off, dt=0.05):
    """Iris-style exponential smoothing of the vanilla rain level (0.01/tick ramp). Half-lives in seconds."""
    rows, rain, wet, t = [], 0.0, 0.0, 0.0
    while t <= t_end + 1e-9:
        target = 1.0 if rain_on <= t < rain_off else 0.0
        rain = min(1.0, rain + 0.2 * dt) if target else max(0.0, rain - 0.2 * dt)
        hl = up if rain > wet else down
        wet = rain + (wet - rain) * math.exp(-math.log(2) * dt / hl)
        rows.append((round(t, 2), rain, wet))
        t += dt
    return rows


def crossing(ts, vs, level):
    for (t0, v0), (t1, v1) in zip(zip(ts, vs), zip(ts[1:], vs[1:])):
        if (v0 - level) * (v1 - level) <= 0 and v0 != v1:
            return t0 + (level - v0) * (t1 - t0) / (v1 - v0)
    return None


def run_results(run):
    d = HERE / run
    done = json.loads((d / "complete.json").read_text())
    plan = json.loads((d / "plan.json").read_text())
    tls = plan["timelineSeconds"]
    out = dict(run=run, pack=done["pack"], sha256=done["sha256"], renderer=done["renderer"],
               declaredHalfLives=done.get("declaredHalfLives"), holds={}, series={})
    for name, h in done["holds"].items():
        per = [frame_values(d / "frames" / f["file"], h["pose"]) for f in h["frames"]]
        med = {k: st.median(v[k] for v in per) for k in per[0]}
        spread = {k: max(v[k] for v in per) - min(v[k] for v in per) for k in per[0]}
        out["holds"][name] = dict(
            weather=h["weather"], lamp=h["lamp"], pose=h["pose"], frames=[f["file"] for f in h["frames"]],
            secondsAfterBegin=[f["secondsAfterBegin"] for f in h["frames"]],
            serverRaining=h["server"].get("rain"), serverSky=h["server"].get("sky"), serverLight=h["server"].get("light"),
            medianY={k: r5(v) for k, v in med.items()}, frameSpreadY={k: r5(v) for k, v in spread.items()},
            pairRatio={p: r5(pair_ratio(med, p)) for p in PAIRS if pair_ratio(med, p) is not None})
    for step, rows in done["series"].items():
        vals = [frame_values(d / "frames" / r["file"], "a") for r in rows]
        out["series"][step] = [dict(t=r["secondsAfterBegin"], serverRaining=r["serverRaining"], file=r["file"],
                                    Y={k: r5(v[k]) for k in ("stone-exposed-near", "stone-shelter-near", "stone-mirror-a",
                                                               "smooth-exposed-near", "smooth-shelter-near", "wall-neutral-w")},
                                    pairRatio={p: r5(pair_ratio(v, p)) for p in PAIRS})
                               for r, v in zip(rows, vals)]
    H = out["holds"]

    def ratio(hold, pair):
        return H[hold]["pairRatio"].get(pair) if hold in H else None

    resp = {}
    for pose in ("a", "b"):
        for lamp in ("on", "off"):
            for pair in PAIRS:
                dry = ratio("dry-%s-%s" % (pose, lamp), pair)
                key = "%s-%s-%s" % (pose, lamp, pair)
                row = dict(dry=dry)
                for state in ("rain", "post", "final"):
                    v = ratio("%s-%s-%s" % (state, pose, lamp), pair)
                    if v is not None and dry:
                        row[state] = v
                        row[state + "OverDry"] = r5(v / dry)
                resp[key] = row
    out["exposedOverShelteredResponse"] = resp
    # Lamp-driven change at the mirror point (same frame position, same pose) dry vs wet, and the off-specular control
    spec = {}
    for pose, mirror_name, control in (("a", "stone-mirror-a", "smooth-mirror-b"), ("b", "smooth-mirror-b", "stone-mirror-a")):
        for state, on, off in (("dry", "dry-%s-on", "dry-%s-off"), ("rain", "rain-%s-on", "rain-%s-off"),
                               ("post", "post-%s-on", "post-%s-off"), ("final", "final-%s-on", "final-%s-off")):
            on, off = on % pose, off % pose
            if on in H and off in H:
                spec["%s-%s" % (pose, state)] = dict(
                    mirror=mirror_name, lampOn=H[on]["medianY"].get(mirror_name), lampOff=H[off]["medianY"].get(mirror_name),
                    lampGain=r5(H[on]["medianY"][mirror_name] - H[off]["medianY"][mirror_name]),
                    offSpecularPatch=control,
                    offSpecularGain=r5(H[on]["medianY"][control] - H[off]["medianY"][control]))
    out["mirrorLampGain"] = spec
    # Rain streak index: frame-to-frame spread of exposed vs sheltered patches in late rain and after it stopped
    streak = {}
    for hold in ("rain-a-on", "rain-a-repeat", "rain-b-on", "post-a-on", "dry-a-on", "final-a-on"):
        if hold in H:
            sp = H[hold]["frameSpreadY"]
            streak[hold] = dict(exposedMeanSpread=r5(st.mean(v for k, v in sp.items() if "exposed" in k or "mirror" in k)),
                                shelteredMeanSpread=r5(st.mean(v for k, v in sp.items() if "shelter" in k)))
    out["streakIndex"] = streak
    # Time constants: stone-near exposed/sheltered ratio in the rise and drying series vs a wetness model
    tl = {}
    rise = out["series"].get("rise", [])
    stop = out["series"].get("stop", []) + [dict(r, t=r["t"] + tls["drying"] - tls["stop"]) for r in out["series"].get("drying", [])]
    up, down, src = halflives(done.get("declaredHalfLives"))
    rain_for = tls["stop"] - tls["rise"]
    model = wetness_model(rain_for + tls["final-a-on"] - tls["stop"] + 5, up, down, 0.0, rain_for)
    at = lambda t: model[min(len(model) - 1, max(0, round(t / 0.05)))][2]  # noqa: E731
    out["wetnessModel"] = dict(halfLifeUpSeconds=up, halfLifeDownSeconds=down, source=src,
                               rainLevelRamp="vanilla 0.01 per tick (5 s)", rainSeconds=rain_for,
                               riseHalf=r5(crossing([r[0] for r in model], [r[2] for r in model], 0.5)),
                               afterStopHalf=r5(crossing([r[0] - rain_for for r in model if r[0] >= rain_for],
                                                         [r[2] for r in model if r[0] >= rain_for], 0.5)),
                               atHolds={h: r5(at(tls[h] - tls["rise"] + 8.0)) for h in tls if tls[h] >= tls["rise"]})
    for pair in ("stone-near", "smooth-near"):
        dry = ratio("dry-a-ref", pair)
        wet = st.median([r for r in (ratio("rain-a-on", pair), ratio("rain-a-repeat", pair)) if r is not None] or [float("nan")])
        row = dict(dry=dry, wet=r5(wet), delta=r5(wet - dry) if dry else None)
        if dry and abs(wet - dry) > 0.01 * abs(dry):
            norm = lambda v: (v - dry) / (wet - dry)
            ts = [r["t"] for r in rise]
            vs = [norm(r["pairRatio"][pair]) for r in rise]
            row["riseHalf"] = r5(crossing(ts, vs, 0.5))
            row["rise90"] = r5(crossing(ts, vs, 0.9))
            ts = [r["t"] for r in stop]
            vs = [norm(r["pairRatio"][pair]) for r in stop]
            row["dryHalf"] = r5(crossing(ts, vs, 0.5))
            row["dry10"] = r5(crossing(ts, vs, 0.1))
            row["normalizedRise"] = [[t, r5(v), r5(at(t))] for t, v in zip([r["t"] for r in rise], [norm(r["pairRatio"][pair]) for r in rise])]
            row["normalizedDrying"] = [[t, r5(v), r5(at(rain_for + t))] for t, v in zip(ts, vs)]
            row["columns"] = "seconds after scene begin, measured normalised response, estimated wetness (model)"
            fin = ratio("final-a-on", pair)
            row["finalNormalized"] = r5(norm(fin)) if fin else None
        tl[pair] = row
    out["timeResponse"] = tl
    return out


def halflives(declared):
    """Seconds. Iris 1.8.8 SmoothedFloat reads the pack values as tenths of a second (defaults 600 / 200)."""
    up = down = None
    for k, v in (declared or {}).items():
        if k.lower().startswith("wetnesshalflife"):
            up = float(v) / 10
        if k.lower().startswith("drynesshalflife"):
            down = float(v) / 10
    src = "declared" if up is not None or down is not None else "Iris defaults"
    return (60.0 if up is None else up), (20.0 if down is None else down), src


def figure(runs, results):
    """Eave comparison: rows = packs, columns = dry / late rain / just after rain / dry again (wide pose)."""
    cols = [("dry-wide-on", "乾いた夕暮れ"), ("rain-wide-on", "雨の終盤"), ("post-wide-on", "雨上がり直後"), ("final-wide-on", "乾いた後")]
    inputs, cells = [], []
    for r in runs:
        d = HERE / r
        for hold, label in cols:
            frame = results[r]["holds"][hold]["frames"][0]
            inputs += ["-i", str(d / "frames" / frame)]
            t = results[r]["holds"][hold]["secondsAfterBegin"][0]
            cells.append((label, results[r]["pack"].replace(".zip", "")))
    n = len(inputs) // 2
    w, h = 640, 360
    chains = []
    for i, (label, pack) in enumerate(cells):
        chains.append("[%d:v]scale=%d:%d,drawtext=fontfile=%s:text='%s':x=12:y=10:fontsize=24:fontcolor=white:"
                      "box=1:boxcolor=black@0.55:boxborderw=6,drawtext=fontfile=%s:text='%s':x=12:y=h-34:fontsize=18:"
                      "fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5[c%d]" % (i, w, h, FONT, label, FONT, pack, i))
    layout = "|".join("%d_%d" % ((i % len(cols)) * w, (i // len(cols)) * h) for i in range(n))
    chains.append("".join("[c%d]" % i for i in range(n)) + "xstack=inputs=%d:layout=%s[o]" % (n, layout))
    target = HERE / "eaves-comparison.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(chains), "-map", "[o]",
                    "-frames:v", "1", "-q:v", "3", str(target)], check=True)
    return target.name


def figure_pose(runs, results, pose, name):
    """Measurement pose with patch boxes: dry / late rain / post-rain for each pack."""
    cols = [("dry-%s-on" % pose, "乾燥"), ("rain-%s-on" % pose, "雨（終盤）"), ("post-%s-on" % pose, "雨上がり")]
    cols = [c for c in cols if all(c[0] in results[r]["holds"] for r in runs)]
    inputs, chains = [], []
    w, h = 640, 360
    boxes = []
    for s in F.samples(pose):
        if s["valid"]:
            x0, y0, x1, y1 = s["patch"]
            color = "cyan" if "shelter" in s["name"] else "orange" if ("exposed" in s["name"] or "mirror" in s["name"]) else "white"
            boxes.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=%s@0.9:t=2" % (x0 - 3, y0 - 3, x1 - x0 + 6, y1 - y0 + 6, color))
    i = 0
    for r in runs:
        for hold, label in cols:
            inputs += ["-i", str(HERE / r / "frames" / results[r]["holds"][hold]["frames"][0])]
            chains.append("[%d:v]%s,scale=%d:%d,drawtext=fontfile=%s:text='%s  %s':x=10:y=8:fontsize=20:fontcolor=white:"
                          "box=1:boxcolor=black@0.55:boxborderw=5[c%d]" % (i, ",".join(boxes), w, h, FONT, label,
                                                                            results[r]["pack"].replace(".zip", ""), i))
            i += 1
    layout = "|".join("%d_%d" % ((k % len(cols)) * w, (k // len(cols)) * h) for k in range(i))
    chains.append("".join("[c%d]" % k for k in range(i)) + "xstack=inputs=%d:layout=%s[o]" % (i, layout))
    target = HERE / name
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(chains), "-map", "[o]",
                    "-frames:v", "1", "-q:v", "3", str(target)], check=True)
    return target.name


def main():
    runs = []
    for prefix in ("base", "rc3"):
        done = [d.name for d in sorted(HERE.glob(prefix + "-r*")) if (d / "complete.json").is_file()]
        if done:
            runs.append(done[-1])
    results = {}
    for r in runs:
        results[r] = run_results(r)
        (HERE / r / "results.json").write_text(json.dumps(results[r], indent=1, ensure_ascii=False))
    summary = dict(runs=runs, method=__doc__.strip(), figures=[])
    for r in runs:
        res = results[r]
        summary[r] = dict(pack=res["pack"], renderer=res["renderer"], declaredHalfLives=res.get("declaredHalfLives"),
                          wetnessModel={k: v for k, v in res["wetnessModel"].items() if k != "atHolds"},
                          exposedOverSheltered={k: v for k, v in res["exposedOverShelteredResponse"].items() if k.startswith("a-on") or k.startswith("b-on")},
                          mirrorLampGain=res["mirrorLampGain"], streakIndex=res["streakIndex"],
                          timeResponse={p: {k: v for k, v in row.items() if not k.startswith("normalized")} for p, row in res["timeResponse"].items()})
    if runs:
        summary["figures"].append(figure(runs, results))
        summary["figures"].append(figure_pose(runs, results, "a", "pose-a-patches.jpg"))
        summary["figures"].append(figure_pose(runs, results, "b", "pose-b-patches.jpg"))
    (HERE / "results.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({r: summary[r]["timeResponse"] for r in runs}, indent=1))


if __name__ == "__main__":
    main()
