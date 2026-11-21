"""Freeze the chosen natural site into site.json: poses, texel-resolved patches, n.L, reserved/natural cells.

    python3 -I choose.py      (read-only on the private snapshot; refuses to overwrite site.json)
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sitesearch as S  # noqa: E402

CW, CH = 1600, 900
TORCH = dict(leaf=(208, 69, 372), n=(-1, 0, 0), S1=(210, 66, 372), S2=(210, 66, 371), blocker=[(209, 66, 372), (209, 67, 372)])
DAY = dict(leaf=(209, 71, 371), n=(1, 0, 0), time=11000,
           wall=[(206, y, z) for y in (72, 73, 74) for z in (369, 370, 371, 372)])
NIGHT = 18000


def r3(v):
    return [round(x, 4) for x in v]


def patches(sc, eye, yaw, pitch, leaf, n, light, sun=False, size=6, want=4):
    """Pixel squares (CW x CH) whose every pixel-centre ray hits an opaque texel of leaf's n face."""
    fc = S.add(tuple(v + .5 for v in leaf), n, .5)
    c = S.to_pixel(fc, eye, yaw, pitch, CW, CH)
    out = []
    span = 90
    cands = []
    for py in range(int(c[1]) - span, int(c[1]) + span, 3):
        for px in range(int(c[0]) - span, int(c[0]) + span, 3):
            cands.append((abs(px - c[0]) + abs(py - c[1]), px, py))
    cands.sort()
    taken = []
    for _, px, py in cands:
        if any(abs(px - a) < size + 10 and abs(py - b) < size + 10 for a, b in taken):
            continue
        hits = []
        ok = True
        for j in range(size):
            for i in range(size):
                d = S.pixel_ray(eye, yaw, pitch, px + i + .5, py + j + .5, CW, CH)
                h = sc.trace(eye, d, 30)
                if not (h["kind"] == "leaf" and h["cell"] == leaf and h["normal"] == n):
                    ok = False
                    break
                hits.append(h)
            if not ok:
                break
        if not ok:
            continue
        p = hits[len(hits) // 2]["point"]
        if sun:
            L = light
        else:
            L = S.norm(S.sub(light, p))
        dot = sum(a * b for a, b in zip(n, L))
        if dot >= 0:
            continue
        taken.append((px, py))
        out.append(dict(rect=[px, py, px + size, py + size], world=r3(p), texels=sorted({tuple(h["texel"]) for h in hits}),
                        nDotL=round(dot, 4), distanceToLight=None if sun else round(math.dist(p, light), 3)))
        if len(out) >= want:
            break
    return out


def pose(eye, yaw, pitch):
    return dict(feet=r3((eye[0], eye[1] - S.EYE, eye[2])), eye=r3(eye), yaw=round(yaw, 2), pitch=round(pitch, 2))


def main():
    out = HERE / "site.json"
    assert not out.exists(), "site.json exists"
    sc = S.Scene((195, 355, 225, 390))
    # ---- torch scene
    T = TORCH
    flame1 = (T["S1"][0] + .5, T["S1"][1] + .6, T["S1"][2] + .5)
    flame2 = (T["S2"][0] + .5, T["S2"][1] + .6, T["S2"][2] + .5)
    cand = S.eval_torch(sc, dict(leaf=T["leaf"], n=T["n"], flame1=flame1))[0]
    fc = S.add(tuple(v + .5 for v in T["leaf"]), T["n"], .5)
    wide = S.wide_pose(sc, dict(leaf=T["leaf"]), fc, T["n"])
    poses = {"torch-close": cand, "torch-wide": wide}
    # ---- day scene
    D = DAY
    sx, sy, _ = S.sun_direction(D["time"])
    sun = S.norm((sx, sy, 0.0))
    dc = S.eval_day(sc, dict(leaf=D["leaf"], n=D["n"], wall=D["wall"]))[0]
    dfc = S.add(tuple(v + .5 for v in D["leaf"]), D["n"], .5)
    sc.extra = {w: S.SOLID for w in D["wall"]}
    dwide = S.wide_pose(sc, dict(leaf=D["leaf"]), dfc, D["n"], extra=set(D["wall"]))
    shade = [sc.trace(p, sun, 40, skip=(D["leaf"],))["kind"] for p in S.face_points(D["leaf"], D["n"])]
    sc.extra = {}
    openv = [sc.trace(p, sun, 40, skip=(D["leaf"],))["kind"] for p in S.face_points(D["leaf"], D["n"])]
    poses.update({"day-close": dc, "day-wide": dwide})
    rec = {}
    for name, p in poses.items():
        leaf, n = (T["leaf"], T["n"]) if name.startswith("torch") else (D["leaf"], D["n"])
        light = flame1 if name.startswith("torch") else sun
        eye = tuple(p["eye"])
        pa = patches(sc, eye, p["yaw"], p["pitch"], leaf, n, light, sun=name.startswith("day"), size=6 if "close" in name else 4)
        flamepix = [S.to_pixel(f, eye, p["yaw"], p["pitch"], CW, CH) for f in (flame1, flame2)]
        fl = [sc.trace(eye, S.norm(S.sub(f, eye)), math.dist(eye, f) + .1) for f in (flame1, flame2)]
        comp, _ = S.composition(sc, eye, p["yaw"], p["pitch"], 32, 18)
        rec[name] = dict(pose(eye, p["yaw"], p["pitch"]), visibleTexels=p["visibleTexels"], patches=pa, composition=comp,
                         leafFacePixel=[round(v, 1) for v in S.to_pixel(S.add(tuple(v + .5 for v in leaf), n, .5), eye, p["yaw"], p["pitch"], CW, CH)],
                         flamePixels=[None if q is None else [round(v, 1) for v in q] for q in flamepix],
                         flameFirstHit=[dict(kind=h["kind"], cell=h["cell"], t=round(h["t"], 3)) for h in fl])
        print(name, rec[name]["pose"] if "pose" in rec[name] else rec[name]["eye"], p["yaw"], p["pitch"], len(pa), comp, file=sys.stderr)
    # ---- natural cells to verify in-game (exact name, persistent=false for leaves)
    natural = {}
    for (L, rad) in ((T["leaf"], 3), (D["leaf"], 3)):
        for x in range(L[0] - rad, L[0] + rad + 1):
            for y in range(L[1] - rad, L[1] + rad + 1):
                for z in range(L[2] - rad, L[2] + rad + 1):
                    st = sc.state((x, y, z))
                    if st and (st["Name"].endswith("_leaves") or st["Name"].endswith("_log")):
                        nm = st["Name"] + ("[persistent=false]" if st["Name"].endswith("_leaves") else "")
                        assert not st["Name"].endswith("_leaves") or st["Properties"]["persistent"] == "false", (x, y, z)
                        natural["%d %d %d" % (x, y, z)] = nm
    supports = {}
    for c in (T["S1"], T["S2"]):
        b = (c[0], c[1] - 1, c[2])
        supports["%d %d %d" % b] = sc.state(b)["Name"]
    reserved = [T["S1"], (T["S1"][0], T["S1"][1] + 1, T["S1"][2]), T["S2"], (T["S2"][0], T["S2"][1] + 1, T["S2"][2])] + T["blocker"] + D["wall"]
    for c in reserved:
        assert sc.cat(c) == S.AIR and sc.state(c)["Name"] in ("minecraft:air", "minecraft:cave_air"), c
    for name, p in rec.items():
        for dy in (0, 1):
            c = tuple(math.floor(v) for v in (p["feet"][0], p["feet"][1] + dy, p["feet"][2]))
            assert sc.cat(c) == S.AIR, (name, c)
    biome = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("anvil", S.ROOT / "reports/2026-11-21-rain-eaves/fixture/anvil.py")
        an = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(an)
        aw = an.World(S.worldread.WORLD)
        biome = {k: aw.biome(*L) for k, L in (("torchLeaf", T["leaf"]), ("dayLeaf", D["leaf"]))}
    except Exception as e:  # noqa: BLE001
        biome = repr(e)
    site = dict(schema=1, snapshot=S.SNAP, model="texel-resolved vanilla cube UV ray cast (sitesearch.py); plants/other models opaque; no shader",
                capture=[CW, CH], fovVertical=S.FOV, eyeHeight=S.EYE, biome=biome,
                torch=dict(leaf=T["leaf"], leafState=sc.state(T["leaf"]), faceNormal=T["n"], warmSlot=T["S1"], soulSlot=T["S2"],
                           flames=[r3(flame1), r3(flame2)], blocker=T["blocker"], supports=supports, time=NIGHT),
                day=dict(leaf=D["leaf"], leafState=sc.state(D["leaf"]), faceNormal=D["n"], time=D["time"], sun=r3(sun),
                         nDotSun=round(sum(a * b for a, b in zip(D["n"], sun)), 4), wall=D["wall"],
                         faceTexelSunRaysBlockedByWall=sum(k == "solid" for k in shade), faceTexelSunRaysOpen=sum(k == "sky" for k in openv),
                         faceTexelRays=len(shade)),
                reservedAir=[list(c) for c in reserved], natural=natural, poses=rec)
    out.write_text(json.dumps(site, indent=1, default=list))
    print(json.dumps({k: (v["eye"], v["yaw"], v["pitch"], len(v["patches"]), v["flameFirstHit"]) for k, v in rec.items()}, default=list))
    print("natural", len(natural), "wall shade", site["day"]["faceTexelSunRaysBlockedByWall"], "/", len(shade), "open", site["day"]["faceTexelSunRaysOpen"], "biome", biome)


if __name__ == "__main__":
    main()
