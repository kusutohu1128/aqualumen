"""Per-pack source isolation from completed door-light runs (stdlib + ffmpeg).

For each pack: the newest complete <before|after>-r* run (all 18 roles) and, when present, the newest
<before|after>-late-r* run, whose roles (captured >= 100 s after the first world render) replace the
same roles of the full run; replaced values are kept under `replacedEarly`. Writes results.json,
comparison.jpg, doorway.jpg, patches.jpg and timeline figures.

Values are display-referred 8-bit sRGB means of 11x11 patches from ordinary Minecraft frames. `lin`
applies only the sRGB EOTF (the pack's exposure and tone curve are NOT inverted), so the
contributions are display-linear differences, not scene radiance.
"""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import house as H  # noqa: E402  (geometry only; also loads the indirect-light fixture for projection)
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
RECEIVERS = ("warm", "warm-near", "far")


def lin(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luma(rgb):
    return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])


def latest(prefix):
    runs = [d for d in HERE.glob(prefix + "-r*") if (d / "complete.json").is_file()]
    runs.sort(key=lambda d: int(d.name.rsplit("-r", 1)[1]))
    return runs[-1] if runs else None


def load(run):
    done = json.loads((run / "complete.json").read_text())
    plan = json.loads((run / "plan.json").read_text())
    names = {r["name"]: [s["name"] for s in r.get("samples", [])] for r in plan["roles"]}
    patches, pairs = {}, {}
    for role, info in done["images"].items():
        if "patches" in info:
            patches[role] = {n: p["meanSRGB8"] for n, p in zip(names[role], info["patches"])}
            pairs[role] = {n: p["pairMeanSRGB8"] for n, p in zip(names[role], info["patches"])}
    return done, plan, patches, pairs


def ready_times(run):
    """Seconds from the first live world render (physics bridge line) to each READY that was captured."""
    import re

    text = (run / "client.log").read_text(errors="replace")
    clock = lambda s: sum(int(v) * k for v, k in zip(s.split(":"), (3600, 60, 1)))
    m = re.search(r"^\[(\d\d:\d\d:\d\d)\].*bridge initialized", text, re.M)
    t0 = clock(m.group(1))
    out = {}
    for m in re.finditer(r"^\[(\d\d:\d\d:\d\d)\].*AQD_READY_([a-z0-9-]+)_END", text, re.M):
        if clock(m.group(1)) - t0 >= 0:
            out.setdefault(m.group(2), []).append(clock(m.group(1)) - t0)
    return t0, out


def analyse(full, late):
    done, plan, P, pairs = load(full)
    source = {r: full.name for r in P}
    replaced = {}
    if late:
        ldone, _, LP, lpairs = load(late)
        assert ldone["sha256"] == done["sha256"], "late run used a different pack"
        for r in LP:
            replaced[r] = P[r]
            P[r], pairs[r], source[r] = LP[r], lpairs[r], late.name
    have = lambda *rs: all(r in P for r in rs)
    Y = lambda role, patch: luma(P[role][patch])
    out = dict(full=full.name, late=late.name if late else None, pack=done["pack"], sha256=done["sha256"],
               renderer=done["renderer"], glVersion=done.get("glVersion"), captureOrder=done["captureOrder"],
               roleSource=source, patchesSRGB8=P, replacedEarly=replaced)

    def contrib(lit, base, patch):
        return round(Y(lit, patch) - Y(base, patch), 5) if have(lit, base) else None

    c = {}
    for patch in RECEIVERS:
        c[patch] = dict(
            open=contrib("open-warm", "off-open", patch),
            closed=contrib("closed-warm", "off-closed", patch),
            noDoor=contrib("nodoor-warm", "nodoor-off", patch),
            oakClosed=contrib("oak-warm", "oak-off", patch),
            cowInDoorway=contrib("cow-warm", "cow-off", patch),
            openRepeat=contrib("open-repeat", "off-open", patch),
            returnedClosed=contrib("returned-closed", "off-closed", patch),
            bothOpenMinusSoulOpen=contrib("open-both", "open-soul", patch),
            bothClosedMinusSoulClosed=contrib("closed-both", "closed-soul", patch),
        )
        ref = c[patch]["noDoor"]
        c[patch]["ratioToNoDoor"] = {k: (round(v / ref, 4) if v is not None and ref and abs(ref) > 0.01 else None)
                                     for k, v in c[patch].items()}
    c["soul"] = dict(
        open=contrib("open-soul", "off-open", "soul"),
        closed=contrib("closed-soul", "off-closed", "soul"),
        bothOpenMinusWarmOpen=contrib("open-both", "open-warm", "soul"),
        bothClosedMinusWarmClosed=contrib("closed-both", "closed-warm", "soul"),
        warmOpenAtSoulPatch=contrib("open-warm", "off-open", "soul"),
        warmClosedAtSoulPatch=contrib("closed-warm", "off-closed", "soul"),
    )
    rep = {}
    for a, b in (("open-repeat", "open-warm"), ("returned-closed", "closed-warm"),
                 ("off-open", "nodoor-off"), ("off-closed", "off-open")):
        if have(a, b):
            rep[a + " vs " + b] = {p: round(max(abs(x - y) for x, y in zip(P[a][p], P[b][p])), 3) for p in P[a]}
    rep["framePairMax"] = round(max(abs(x - y) for r in P for p in P[r] for x, y in zip(P[r][p], pairs[r][p])), 3)
    c["repeatMaxAbsSRGB8"] = rep
    ctrl = {p: {r: round(Y(r, p), 5) for r in P} for p in ("sun", "north-wall")}
    c["controls"] = {p: dict(min=min(v.values()), max=max(v.values()), byRole=v) for p, v in ctrl.items()}
    out["contributionsDisplayLinearLuma"] = c
    t0, times = ready_times(full)
    out["fullRunSecondsAfterFirstRender"] = {r: times.get(r) for r in done["captureOrder"]}
    if late:
        out["lateRunSecondsAfterFirstRender"] = {r: ready_times(late)[1].get(r) for r in load(late)[0]["captureOrder"]}
    return out


def timeline_summary(run):
    tl = run / "timeline/timeline.json"
    if not tl.is_file():
        return None
    rows = json.loads(tl.read_text())
    t0, _ = ready_times(run)
    text = (run / "client.log").read_text(errors="replace")
    import re

    clock = lambda s: sum(int(v) * k for v, k in zip(s.split(":"), (3600, 60, 1)))
    begins = [(clock(m.group(1)), m.group(2)) for m in re.finditer(r"^\[(\d\d:\d\d:\d\d)\].*AQD_BEGIN_([a-z0-9-]+)_END", text, re.M)]
    out = []
    for r in rows:
        t = clock(r["clock"])
        scene = [n for s, n in begins if s <= t]
        out.append(dict(file=r["file"], secondsAfterFirstRender=t - t0, scene=scene[-1] if scene else None,
                        frameMean=r["frameMean"], soul=r["patches"]["soul"] if r["patches"] else None,
                        warm=r["patches"]["warm"] if r["patches"] else None))
    return out


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, timeout=120)


def esc(t):
    return t.replace(":", r"\:").replace("'", "")


def sheet(cells, cols, target, w, h, crop=None):
    inputs, filters, labels = [], [], []
    for i, (path, label) in enumerate(cells):
        if path is None or not Path(path).is_file():
            inputs += ["-f", "lavfi", "-i", "color=c=0x171c22:s=%dx%d:d=1" % (w, h)]
            pre = ""
        else:
            inputs += ["-i", str(path)]
            pre = ("crop=%d:%d:%d:%d," % crop) if crop else ""
        filters.append("[%d:v]%sscale=%d:%d,drawbox=x=0:y=0:w=%d:h=32:color=black@0.6:t=fill,"
                       "drawtext=fontfile=%s:text='%s':x=8:y=4:fontsize=20:fontcolor=white[v%d]" % (i, pre, w, h, w, FONT, esc(label), i))
        labels.append("[v%d]" % i)
    layout = "|".join("%d_%d" % ((i % cols) * w, (i // cols) * h) for i in range(len(cells)))
    filters.append("%sxstack=inputs=%d:layout=%s[out]" % ("".join(labels), len(cells), layout))
    ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", "-q:v", "3", str(target)])


def image(runs, k, role):
    for run in (runs.get(k + "-late"), runs.get(k)):
        if run and (run / (role + ".png")).is_file():
            return run / (role + ".png")
    return None


def patch_figure(run, target):
    plan = json.loads((run / "plan.json").read_text())
    row = next(r for r in plan["roles"] if r["name"] == "open-warm")
    boxes = ",".join("drawbox=x=%d:y=%d:w=%d:h=%d:color=yellow:t=2,drawtext=fontfile=%s:text='%s':x=%d:y=%d:fontsize=18:fontcolor=yellow"
                     % (s["patch"][0] - 3, s["patch"][1] - 3, s["patch"][2] - s["patch"][0] + 6, s["patch"][3] - s["patch"][1] + 6,
                        FONT, s["name"], s["patch"][0] + 12, s["patch"][1] - 26) for s in row["samples"])
    ffmpeg(["-i", str(run / "open-warm.png"), "-vf", boxes, "-frames:v", "1", "-q:v", "3", str(target)])


# ------------------------------------------------------------------ pixel-level advisor analysis
#
# Every main-pose pixel is labelled by a camera ray through house.py geometry (every non-air cell a
# full box, the conservative cow box in cow roles), so region means need no hand-drawn masks.  The
# cow test compares, per white-runner pixel, the measured warm contribution with and without the
# cow against the fraction of lantern-body points whose straight path the vanilla cow hitbox cuts.
# The geometric fraction is a fixture expectation, not a model of the shader.

LIN8 = [lin(v) for v in range(256)]
STRIDE = 4  # region-mean sampling stride (pixels)
LANTERN_BODY = ((13 + 5 / 16, 3 + 1 / 16, 6 + 5 / 16), (13 + 11 / 16, 3 + 8 / 16, 6 + 11 / 16))  # hanging lantern
_RGB = {}


def pixels(path):
    path = Path(path)
    if path not in _RGB:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"],
                             check=True, capture_output=True, timeout=30).stdout
        _RGB[path] = raw
    return _RGB[path]


def ylin(raw, x, y):
    i = (y * H.WIDTH + x) * 3
    return 0.2126 * LIN8[raw[i]] + 0.7152 * LIN8[raw[i + 1]] + 0.0722 * LIN8[raw[i + 2]]


def camera_hit(grid, cow, eye, d, tmax=60.0):
    """Amanatides-Woo walk; first non-air cell (full box) or the cow box. Returns (t, block, cell)."""
    tc = H.seg_box(eye, tuple(eye[i] + d[i] * tmax for i in range(3)), *H.COW_BOX) if cow else None
    tc = tc * tmax if tc is not None else math.inf
    c = [math.floor(v) for v in eye]
    step = [1 if v > 0 else -1 for v in d]
    tnext = [((c[i] + (step[i] > 0)) - eye[i]) / d[i] if d[i] else math.inf for i in range(3)]
    tdelta = [abs(1 / d[i]) if d[i] else math.inf for i in range(3)]
    t = 0.0
    while t < tmax:
        if t > tc:
            return tc, "cow", None
        b = grid.get(tuple(c))
        if b is None:
            return math.inf, None, None
        if b != H.AIR:
            return (tc, "cow", None) if tc < t else (t, b, tuple(c))
        a = min(range(3), key=lambda k: tnext[k])
        t, c[a], tnext[a] = tnext[a], c[a] + step[a], tnext[a] + tdelta[a]
    return math.inf, None, None


def region(block, cell):
    if block is None:
        return "none"
    if block == "cow":
        return "cow"
    x, y, z = cell
    i = H.block_id(block)
    if i.endswith("_door"):
        return "door"
    if y >= 5:
        return "ceiling"
    if x >= 12:
        return "room-b"
    if x == 11:
        return "partition"
    if z >= 12:
        return "south-wall"
    if z == 11 and i == "minecraft:bookshelf":
        return "south-bookshelf"
    if z == 11:
        return "south-furniture"
    if x == 0:
        return "west-wall"
    if z == 0:
        return "north-wall"
    if block == H.WHITE:
        return "white-runner"
    if block == H.STONE:
        return "soul-stone"
    if y == 0:
        return "oak-floor-south" if z >= 8 else ("oak-floor-north" if z <= 3 else "oak-floor-mid")
    return "other"


_LABELS = {}


def labels(role_name, stride=STRIDE):
    r = H.role(role_name)
    key = (r["door"], r["cow"], stride)
    if key not in _LABELS:
        grid, pose, out = H.cells(r), H.POSES["main"], {}
        for py in range(stride // 2, H.HEIGHT, stride):
            for px in range(stride // 2, H.WIDTH, stride):
                t, b, c = camera_hit(grid, r["cow"], pose["eye"], H.ray(pose, px + 0.5, py + 0.5))
                out[px, py] = region(b, c)
        _LABELS[key] = out
    return _LABELS[key]


def region_means(path, role_name):
    raw, acc = pixels(path), {}
    for (px, py), name in labels(role_name).items():
        s = acc.setdefault(name, [0.0, 0])
        s[0] += ylin(raw, px, py)
        s[1] += 1
    return {k: (round(v[0] / v[1], 5), v[1]) for k, v in acc.items()}


def region_delta(a_path, a_role, b_path, b_role, min_pixels=40):
    """Region mean display-linear luma of a minus b over pixels labelled the same in both roles."""
    la, lb, ra, rb = labels(a_role), labels(b_role), pixels(a_path), pixels(b_path)
    acc = {}
    for p, name in la.items():
        if lb.get(p) != name:
            continue
        s = acc.setdefault(name, [0.0, 0.0, 0])
        s[0] += ylin(ra, *p)
        s[1] += ylin(rb, *p)
        s[2] += 1
    return {k: dict(a=round(v[0] / v[2], 5), b=round(v[1] / v[2], 5), delta=round((v[0] - v[1]) / v[2], 5), pixels=v[2])
            for k, v in sorted(acc.items()) if v[2] >= min_pixels}


def capture_time(run, role):
    """Seconds after the first live render of the READY that preceded this role's capture (PNG mtime)."""
    import time as _t

    t0, times = ready_times(run)
    info = json.loads((run / "complete.json").read_text())["images"][role]
    mt = _t.localtime((run / info["file"]).stat().st_mtime)
    shot = mt.tm_hour * 3600 + mt.tm_min * 60 + mt.tm_sec - t0
    before = [t for t in times.get(role, []) if t <= shot - info["secondsAfterReady"] + 1.5]
    return before[-1] if before else None


def early_late(full, late):
    out = {}
    if not late:
        return out
    ldone = json.loads((late / "complete.json").read_text())
    for role in ldone["captureOrder"]:
        row = dict(earlySeconds=capture_time(full, role), lateSeconds=capture_time(late, role),
                   earlyMinusLate=region_delta(full / (role + ".png"), role, late / (role + ".png"), role))
        out[role] = row
    # same-scene pairs where both captures are in the late (>=100 s) window
    for a, ra, b, rb in (("open-repeat", late, "open-warm", full), ("returned-closed", late, "closed-warm", full)):
        if (ra / (a + ".png")).is_file() and (rb / (b + ".png")).is_file():
            out["%s(late) vs %s(full)" % (a, b)] = dict(
                aSeconds=capture_time(ra, a), bSeconds=capture_time(rb, b),
                aMinusB=region_delta(ra / (a + ".png"), a, rb / (b + ".png"), b))
    return out


def runner_pixels(stride=2):
    """White-runner pixels (camera-visible in both nodoor and cow roles) with floor point."""
    pose = H.POSES["main"]
    pts = [H.project(pose, (x, 1.0, z)) for x in (4, 11) for z in (5, 8)]
    x0, x1 = max(0, int(min(p[0] for p in pts)) - 2), min(H.WIDTH, int(max(p[0] for p in pts)) + 3)
    y0, y1 = max(0, int(min(p[1] for p in pts)) - 2), min(H.HEIGHT, int(max(p[1] for p in pts)) + 3)
    g0, g1 = H.cells(H.role("nodoor-warm")), H.cells(H.role("cow-warm"))
    out = []
    for py in range(y0, y1, stride):
        for px in range(x0, x1, stride):
            d = H.ray(pose, px + 0.5, py + 0.5)
            t, b, c = camera_hit(g0, False, pose["eye"], d)
            if b != H.WHITE or c[1] != 0:
                continue
            t1, b1, _ = camera_hit(g1, True, pose["eye"], d)
            if b1 != H.WHITE:
                continue
            e = pose["eye"]
            s = (1.0 - e[1]) / d[1]  # top face of the y=0 runner
            p = tuple(e[i] + d[i] * s for i in range(3))
            if not (c[0] <= p[0] <= c[0] + 1 and c[2] <= p[2] <= c[2] + 1):
                continue  # ray entered the cell through a side face
            out.append(((px, py), p))
    return out


def cow_fraction(points, n=3):
    lo, hi = LANTERN_BODY
    lamp = [tuple(lo[k] + (hi[k] - lo[k]) * (i + 0.5) / n for k, i in enumerate(ijk))
            for ijk in ((a, b, c) for a in range(n) for b in range(n) for c in range(n))]
    box = ((3.5, 0.9, 4.5), (14.5, 3.7, 8.5))
    keep = lambda bx: all(bx[0][k] < box[1][k] and bx[1][k] > box[0][k] for k in range(3))
    walls = [b for b in H.occluders(H.role("nodoor-warm"), light=True) if keep(b)]
    cow = [(H.COW_HITBOX[0], H.COW_HITBOX[1], None, "cow")]
    out = []
    for p in points:
        q = (p[0], p[1] + 1e-4, p[2])
        vis = [s for s in lamp if H.clear(q, s, walls)]
        cut = sum(not H.clear(q, s, cow) for s in vis)
        out.append((len(vis) / len(lamp), cut / len(vis) if vis else None))
    return out


_GEO = []


def cow_pixels(src):
    """src: role -> png path for nodoor-warm, nodoor-off, cow-warm, cow-off."""
    if not _GEO:
        px = runner_pixels()
        _GEO.extend((px, cow_fraction([p for _, p in px])))
    px, geo = _GEO
    raw = {r: pixels(src[r]) for r in ("nodoor-warm", "nodoor-off", "cow-warm", "cow-off")}
    bins = {"blocked0": [], "partial": [], "blockedAll": []}
    rows = []
    for ((x, y), p), (visible, f) in zip(px, geo):
        cn = ylin(raw["nodoor-warm"], x, y) - ylin(raw["nodoor-off"], x, y)
        cc = ylin(raw["cow-warm"], x, y) - ylin(raw["cow-off"], x, y)
        rows.append((x, y, p, visible, f, cn, cc))
        if f is None or cn < 0.01:
            continue
        key = "blocked0" if f == 0 else ("blockedAll" if f == 1 else "partial")
        bins[key].append((x, y, f, cn, cc))
    summ = {}
    for k, v in bins.items():
        if not v:
            summ[k] = dict(pixels=0)
            continue
        ratio = sorted(c / n for _, _, _, n, c in v)
        summ[k] = dict(
            pixels=len(v), meanCowFraction=round(sum(f for _, _, f, _, _ in v) / len(v), 3),
            noCowContribution=round(sum(n for *_, n, _ in v) / len(v), 5),
            cowContribution=round(sum(c for *_, c in v) / len(v), 5),
            ratioMedian=round(ratio[len(ratio) // 2], 4), ratioP10=round(ratio[len(ratio) // 10], 4),
            ratioP90=round(ratio[len(ratio) * 9 // 10], 4),
            ratioBelowHalf=sum(r < 0.5 for r in ratio),
            pixelBox=[min(x for x, *_ in v), min(y for _, y, *_ in v), max(x for x, *_ in v), max(y for _, y, *_ in v)])
        pts = {(a, b) for a, b, *_ in v}
        fl = [p for (xy, p) in px if xy in pts]
        summ[k]["floorBoxLocal"] = [round(min(q[0] for q in fl), 2), round(min(q[2] for q in fl), 2),
                                    round(max(q[0] for q in fl), 2), round(max(q[2] for q in fl), 2)]
    lit = [r for r in rows if r[4] is not None and r[5] >= 0.01]
    summ["method"] = ("white_concrete top-face pixels (stride 2) visible in nodoor and cow roles; contribution = warm - off "
                      "display-linear luma; cowFraction = share of %d lantern-body points (visible past walls/frame) whose "
                      "straight path the vanilla 0.9x1.4 cow hitbox cuts; pixels with no-cow contribution < 0.01 dropped" % 27)
    summ["runnerPixels"], summ["litPixels"] = len(rows), len(lit)
    return summ, rows


def cow_figure(rows, target, base):
    """Doorway-runner crop, 2x.  Left: cow-warm frame.  Middle: measured (cow-warm - cow-off) / (nodoor-warm - nodoor-off)
    per pixel (black 0, white >= 1, red < 0, blue = no-cow contribution < 0.01).  Right: geometric unblocked share
    1 - cowFraction (white = hitbox cuts no lantern point, black = cuts all, blue = lantern hidden by walls)."""
    w, h = H.WIDTH // 2, H.HEIGHT // 2
    a, b = bytearray(b"\x10\x18\x30" * w * h), bytearray(b"\x10\x18\x30" * w * h)
    for x, y, _, _, f, cn, cc in rows:
        i = ((y // 2) * w + x // 2) * 3
        if cn >= 0.01:
            r = cc / cn
            a[i:i + 3] = bytes((160, 0, 0)) if r < 0 else bytes((max(0, min(255, int(255 * r))),) * 3)
        if f is not None:
            b[i:i + 3] = bytes((int(255 * (1 - f)),) * 3)
    tmp = Path("/tmp/aqd-cow-%d" % os.getpid())
    tmp.mkdir(exist_ok=True)
    for name, data in (("a.ppm", a), ("b.ppm", b)):
        (tmp / name).write_bytes(b"P6 %d %d 255\n" % (w, h) + bytes(data))
    cx, cy, cw, ch = 250, 125, 300, 95  # half-resolution crop around the runner
    crop = "crop=%d:%d:%d:%d,scale=%d:%d:flags=neighbor" % (cw, ch, cx, cy, cw * 2, ch * 2)
    ffmpeg(["-i", str(base), "-i", str(tmp / "a.ppm"), "-i", str(tmp / "b.ppm"), "-filter_complex",
            "[0:v]scale=%d:%d,%s[c];[1:v]%s[m];[2:v]%s[g];[c][m][g]hstack=inputs=3" % (w, h, crop, crop, crop),
            "-frames:v", "1", "-q:v", "3", str(target)])


REGIONS = ("south-bookshelf", "soul-stone", "south-wall", "oak-floor-south", "white-runner", "oak-floor-north", "north-wall")


def role_regions(run):
    """Region means for every main-pose capture of a run, in capture order (read-only on the run)."""
    done = json.loads((run / "complete.json").read_text())
    rows = []
    for r in done["captureOrder"]:
        if H.role(r)["pose"] != "main":
            rows.append(dict(role=r, seconds=capture_time(run, r), pose="wide"))
            continue
        m = region_means(run / (r + ".png"), r)
        rows.append(dict(role=r, seconds=capture_time(run, r), **{k: m[k][0] for k in REGIONS if k in m}))
    return dict(pack=done["pack"], sha256=done["sha256"], renderer=done["renderer"], rows=rows)


def settled_coefficients(run, base="nodoor-off"):
    """Patch contributions inside one run whose captures are all >= 100 s and contain no wide-pose visit."""
    done, _, P, _ = load(run)
    Y = lambda role, patch: luma(P[role][patch])
    out = {}
    for patch in ("warm", "warm-near", "far", "soul"):
        row = {}
        for lit in ("open-warm", "closed-warm", "nodoor-warm", "open-repeat", "returned-closed", "oak-warm"):
            if lit in P and base in P:
                row[lit] = round(Y(lit, patch) - Y(base, patch), 5)
        if "cow-warm" in P and "cow-off" in P:
            row["cow-warm minus cow-off"] = round(Y("cow-warm", patch) - Y("cow-off", patch), 5)
        if "oak-warm" in P and "oak-off" in P:
            row["oak-warm minus oak-off"] = round(Y("oak-warm", patch) - Y("oak-off", patch), 5)
        out[patch] = row
    return dict(run=run.name, pack=done["pack"], base=base, seconds={r: capture_time(run, r) for r in done["captureOrder"]},
                contributions=out)


def advisor(runs):
    out = dict(roleRegions={}, earlyVsLateRegions={}, cowPixels={}, settled={}, lateTimelineRegions={})
    extra = {n: HERE / n for n in ("shipped", "shipped-settled") if (HERE / n / "complete.json").is_file()}
    every = {**{r.name: r for r in runs.values() if r}, **extra}
    for name, run in sorted(every.items()):
        out["roleRegions"][name] = role_regions(run)
    for k in ("before", "after"):
        if runs.get(k) and runs.get(k + "-late"):
            out["earlyVsLateRegions"][k] = early_late(runs[k], runs[k + "-late"])
        late = runs.get(k + "-late")
        if late and timeline_summary(late):
            rows = []
            for r in timeline_summary(late):
                if r["secondsAfterFirstRender"] < 0 or not r["scene"] or r["frameMean"][0] < 10:
                    continue
                m = region_means(late / "timeline" / r["file"], r["scene"])
                rows.append(dict(file=r["file"], seconds=r["secondsAfterFirstRender"], scene=r["scene"],
                                 **{q: m[q][0] for q in REGIONS if q in m}))
            out["lateTimelineRegions"][late.name] = rows
    roles4 = ("nodoor-warm", "nodoor-off", "cow-warm", "cow-off")
    sets = {}
    if runs.get("before"):
        sets["1.5.0-before-r1"] = {r: runs["before"] for r in roles4}
    if runs.get("after"):
        late = runs.get("after-late")
        sets["rc1-mixed"] = {r: (late if late and (late / (r + ".png")).is_file() else runs["after"]) for r in roles4}
    if "shipped-settled" in extra:
        sets["1.6.0-shipped-settled"] = {r: extra["shipped-settled"] for r in roles4}
        out["settled"]["1.6.0-shipped-settled"] = settled_coefficients(extra["shipped-settled"])
    for k in ("after-late", "before-late"):
        if runs.get(k):
            base = "oak-off"
            out["settled"][runs[k].name] = settled_coefficients(runs[k], base=base)
    for key, src in sets.items():
        paths = {r: src[r] / (r + ".png") for r in roles4}
        cow, rows = cow_pixels(paths)
        cow["sources"] = {r: src[r].name for r in roles4}
        cow["seconds"] = {r: capture_time(src[r], r) for r in roles4}
        out["cowPixels"][key] = cow
        cow_figure(rows, HERE / ("cow-pixels-%s.jpg" % key), paths["cow-warm"])
    return out


def main():
    runs = {k: latest(k) for k in ("before", "after", "before-late", "after-late")}
    res = {k: analyse(runs[k], runs[k + "-late"]) for k in ("before", "after") if runs[k]}
    for k in ("before", "after", "before-late", "after-late"):
        if runs[k] and (s := timeline_summary(runs[k])):
            res.setdefault("timelines", {})[runs[k].name] = s
    if not res:
        print("no completed runs")
        return 1
    if os.environ.get("AQL_DOOR_ADVISOR", "1") == "1":
        res["advisor"] = advisor(runs)
    (HERE / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    tags = {"before": "1.5.0", "after": "1.6.0-rc1"}
    wide = [("wide-closed-both", "扉を閉・両方点灯"), ("wide-open-both", "扉を開・両方点灯")]
    main_roles = [("closed-warm", "閉・暖色のみ"), ("open-warm", "開・暖色のみ"), ("nodoor-warm", "扉なし・暖色のみ"),
                  ("oak-warm", "閉じたオーク扉・暖色のみ"), ("cow-warm", "扉口に牛・暖色のみ"), ("off-open", "開・両方消灯"),
                  ("closed-soul", "閉・魂のみ"), ("open-both", "開・両方点灯")]
    cells = [(image(runs, k, r), "%s %s" % (tags[k], lab)) for k in ("before", "after") for r, lab in wide]
    sheet(cells, 2, HERE / "wide.jpg", 640, 360)
    cells = [(image(runs, k, r), "%s %s" % (tags[k], lab)) for k in ("before", "after") for r, lab in main_roles]
    sheet(cells, 4, HERE / "comparison.jpg", 480, 270)
    door = [("closed-warm", "閉"), ("open-warm", "開"), ("nodoor-warm", "扉なし"), ("oak-warm", "オーク閉"), ("cow-warm", "牛")]
    cells = [(image(runs, k, r), "%s %s" % (tags[k], lab)) for k in ("before", "after") for r, lab in door]
    sheet(cells, 5, HERE / "doorway.jpg", 384, 336, crop=(560, 490, 400, 60))
    if runs.get("before"):
        patch_figure(runs["before"], HERE / "patches.jpg")
    for k in ("before", "after"):
        if k not in res:
            continue
        c = res[k]["contributionsDisplayLinearLuma"]
        print(k, res[k]["pack"], json.dumps({p: {q: c[p][q] for q in ("noDoor", "open", "closed", "oakClosed", "cowInDoorway")} for p in RECEIVERS}))
        print("   soul", json.dumps(c["soul"]), "| repeat", json.dumps(c["repeatMaxAbsSRGB8"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
