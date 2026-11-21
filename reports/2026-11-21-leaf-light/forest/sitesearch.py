"""Read-only site search in the private V2 snapshot: natural (persistent=false) leaves whose visible FRONT face
(cutout texels resolved from the vanilla 1.21.1 leaf textures) is lit from BEHIND (n.L < 0) by
  * a torch / soul torch standing on natural ground behind the leaf plane (stone blocker cells in between), and
  * the low Sun (frozen time) with a removable opaque stone wall on the Sun side.

    python3 -I sitesearch.py [x0 z0 x1 z1]      -> site.json (+ stdout summary)

Model limits: block-face texel ray casting with vanilla cube UVs; plants/other models count as opaque occluders;
no shader, no block-light propagation. The native run re-checks every reserved and natural cell on the server.
"""
import io
import json
import math
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FT = ROOT / "reports/2026-11-20-local-light/forest-tools"
sys.path.insert(0, str(FT))
import worldread  # noqa: E402

SNAP = json.loads((HERE / "snapshot.json").read_text())
worldread.WORLD = Path(SNAP["path"])
from voxels import AIR, LEAVES, LOG, GRASS, DIRT, SOLID, WATER, PLANT, UNKNOWN, Grid, basis, project, sun_direction  # noqa: E402

CLIENT = Path.home() / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar"
FOV, W, H, EYE = 70.0, 1280, 720, 1.62
SUPPORT = (GRASS, DIRT, SOLID, LOG)
DAY_TIMES = (1000, 11000)
H4 = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]


def alpha_masks():
    out = {}
    with zipfile.ZipFile(CLIENT) as z:
        for n in z.namelist():
            if n.startswith("assets/minecraft/textures/block/") and n.endswith("_leaves.png") and "bamboo" not in n:
                raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:", "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:"],
                                     input=z.read(n), capture_output=True, check=True).stdout
                assert len(raw) == 16 * 16 * 4, n
                out["minecraft:" + n.rsplit("/", 1)[1][:-4]] = [raw[i * 4 + 3] for i in range(256)]
    return out


ALPHA = alpha_masks()


def uv(normal, f):
    fx, fy, fz = f
    if normal == (0, 0, -1):
        u, v = 1 - fx, 1 - fy
    elif normal == (0, 0, 1):
        u, v = fx, 1 - fy
    elif normal == (-1, 0, 0):
        u, v = fz, 1 - fy
    elif normal == (1, 0, 0):
        u, v = 1 - fz, 1 - fy
    elif normal == (0, 1, 0):
        u, v = fx, fz
    else:
        u, v = fx, 1 - fz
    return min(15, max(0, int(u * 16))), min(15, max(0, int(v * 16)))


class Scene:
    def __init__(self, box):
        x0, z0, x1, z1 = box
        self.world = worldread.World()
        t = time.time()
        self.grid = Grid(self.world, x0 - 24, z0 - 24, x1 + 24, z1 + 24, 50, 120)
        self.states = {}
        self.extra = {}  # hypothetical blocks (e.g. stone wall) for occlusion tests
        print("# grid %.1fs" % (time.time() - t), file=sys.stderr)

    def state(self, c):
        if c not in self.states:
            self.states[c] = self.world.state(*c)
        return self.states[c]

    def cat(self, c):
        if c in self.extra:
            return self.extra[c]
        return self.grid.cat(*c)

    def natural_leaf(self, c):
        s = self.state(c)
        return bool(s) and s["Name"].endswith("_leaves") and s.get("Properties", {}).get("persistent") == "false"

    def trace(self, o, d, maxdist, skip=(), stop_leaf=True):
        """Texel-resolved first hit. Returns dict(kind, cell, normal, texel, t, point, leaves=[cells passed])."""
        ix, iy, iz = (math.floor(v) for v in o)
        cell = [ix, iy, iz]
        step = [1 if v > 0 else -1 for v in d]
        inf = float("inf")
        tmax = [((cell[a] + (step[a] > 0)) - o[a]) / d[a] if d[a] else inf for a in range(3)]
        tdel = [abs(1 / d[a]) if d[a] else inf for a in range(3)]
        t, normal, passed = 0.0, None, []
        while t <= maxdist:
            c = tuple(cell)
            k = self.cat(c)
            if c not in skip and k != AIR and normal is not None:
                p = tuple(o[a] + d[a] * t for a in range(3))
                if k == LEAVES:
                    f = tuple(p[a] - c[a] for a in range(3))
                    tu, tv = uv(normal, f)
                    name = self.state(c)["Name"] if c not in self.extra else None
                    mask = ALPHA.get(name)
                    if mask is None or mask[tv * 16 + tu] >= 26:
                        if stop_leaf:
                            return dict(kind="leaf", cell=c, normal=normal, texel=(tu, tv), t=t, point=p, leaves=passed)
                    passed.append(c)
                else:
                    return dict(kind={LOG: "log", GRASS: "ground", DIRT: "ground", SOLID: "solid", WATER: "water",
                                      PLANT: "plant", UNKNOWN: "unknown"}.get(k, "solid"), cell=c, normal=normal, t=t, point=p, leaves=passed)
            a = min(range(3), key=lambda i: tmax[i])
            t = tmax[a]
            tmax[a] += tdel[a]
            cell[a] += step[a]
            normal = tuple(-step[a] if i == a else 0 for i in range(3))
            if not self.grid.inside(*cell) and cell[1] >= self.grid.y0 + self.grid.H:
                return dict(kind="sky", cell=None, normal=None, t=t, point=None, leaves=passed)
        return dict(kind="sky", cell=None, normal=None, t=maxdist, point=None, leaves=passed)


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b, s=1.0):
    return tuple(x + y * s for x, y in zip(a, b))


def look(eye, target):
    d = norm(sub(target, eye))
    yaw = math.degrees(math.atan2(-d[0], d[2]))
    pitch = math.degrees(-math.asin(d[1]))
    return round(yaw, 2), round(pitch, 2)


def pixel_ray(eye, yaw, pitch, px, py, w=W, h=H):
    f, r, u = basis(yaw, pitch)
    tn = math.tan(math.radians(FOV) / 2)
    nx = (px / w) * 2 - 1
    ny = 1 - (py / h) * 2
    return norm(tuple(f[i] + r[i] * nx * tn * w / h + u[i] * ny * tn for i in range(3)))


def to_pixel(point, eye, yaw, pitch, w=W, h=H):
    p = project(point, eye, yaw, pitch, FOV, w / h)
    if not p or abs(p[0]) > 1 or abs(p[1]) > 1:
        return None
    return ((p[0] + 1) / 2 * w, (1 - p[1]) / 2 * h)


def face_points(cell, n):
    """16x16 texel centres of the face of `cell` with outward normal n (horizontal or vertical)."""
    out = []
    c = tuple(v + .5 for v in cell)
    centre = add(c, n, .5)
    axes = [a for a in range(3) if n[a] == 0]
    for i in range(16):
        for j in range(16):
            p = list(centre)
            p[axes[0]] += (i + .5) / 16 - .5
            p[axes[1]] += (j + .5) / 16 - .5
            out.append(tuple(p))
    return out


def visible_texels(sc, eye, cell, n):
    vis = []
    for p in face_points(cell, n):
        d = sub(p, eye)
        dist = math.sqrt(sum(v * v for v in d))
        hit = sc.trace(eye, norm(d), dist + .02)
        if hit["kind"] == "leaf" and hit["cell"] == cell and hit["normal"] == n and abs(hit["t"] - dist) < .03:
            vis.append((p, hit["texel"]))
    return vis


def body_clear(sc, eye):
    for dx in (-.3, .3):
        for dz in (-.3, .3):
            for dy in (-1.62, -.8, 0, .2):
                if sc.cat((math.floor(eye[0] + dx), math.floor(eye[1] + dy), math.floor(eye[2] + dz))) != AIR:
                    return False
    return True


def composition(sc, eye, yaw, pitch, nx=48, ny=27, extra_cells=()):
    cnt = {}
    near_leaf = 0
    extra = 0
    for j in range(ny):
        for i in range(nx):
            d = pixel_ray(eye, yaw, pitch, (i + .5) * W / nx, (j + .5) * H / ny)
            h = sc.trace(eye, d, 96)
            k = h["kind"]
            if k == "leaf":
                k = "leaf_near" if h["t"] < 6 else "leaf_far"
            if h["cell"] in extra_cells:
                extra += 1
            cnt[k] = cnt.get(k, 0) + 1
    tot = nx * ny
    return {k: round(v / tot, 3) for k, v in sorted(cnt.items())}, extra / tot


def ground_y(sc, x, z, top, bottom):
    for y in range(top, bottom - 1, -1):
        if sc.cat((x, y, z)) == AIR and sc.cat((x, y - 1, z)) in SUPPORT:
            return y
    return None


def segment_cells(sc, a, b):
    d = sub(b, a)
    dist = math.sqrt(sum(v * v for v in d))
    cells = []
    ix = [math.floor(v) for v in a]
    n = norm(d)
    step = [1 if v > 0 else -1 for v in n]
    inf = float("inf")
    tmax = [((ix[k] + (step[k] > 0)) - a[k]) / n[k] if n[k] else inf for k in range(3)]
    tdel = [abs(1 / n[k]) if n[k] else inf for k in range(3)]
    t = 0
    while t < dist:
        cells.append(tuple(ix))
        k = min(range(3), key=lambda q: tmax[q])
        t = tmax[k]
        tmax[k] += tdel[k]
        ix[k] += step[k]
    return cells


def torch_candidates(sc, box):
    x0, z0, x1, z1 = box
    out = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(58, 90):
                L = (x, y, z)
                if sc.grid.cat(*L) != LEAVES or not sc.natural_leaf(L):
                    continue
                for n in H4:
                    F = add(L, n)
                    F = tuple(int(v) for v in F)
                    if sc.cat(F) != AIR:
                        continue
                    t = (n[2], 0, -n[0])  # horizontal tangent
                    for k in (2, 3):
                        col = tuple(int(v) for v in add(L, n, -k))
                        ys = ground_y(sc, col[0], col[2], y, y - 3)
                        if ys is None:
                            continue
                        S1 = (col[0], ys, col[2])
                        if sc.cat((S1[0], ys + 1, S1[2])) != AIR:
                            continue
                        flame1 = (S1[0] + .5, ys + .6, S1[2] + .5)
                        back = add(tuple(v + .5 for v in L), n, -.5)
                        path = [c for c in segment_cells(sc, flame1, back) if c not in (S1, L)]
                        if any(sc.cat(c) not in (AIR, LEAVES) for c in path):
                            continue
                        # blocker = first cells from the flame toward the leaf (all AIR, placeable)
                        B = tuple(int(v) for v in add(S1, n))
                        blk = [B, (B[0], B[1] + 1, B[2])]
                        if any(sc.cat(c) != AIR for c in blk):
                            continue
                        # second (soul) slot beside S1, also behind the plane
                        S2 = None
                        for s in (1, -1):
                            c = tuple(int(v) for v in add(S1, t, s))
                            if sc.cat(c) == AIR and sc.cat((c[0], c[1] - 1, c[2])) in SUPPORT and sc.cat((c[0], c[1] + 1, c[2])) == AIR and c not in blk:
                                S2 = c
                                break
                        if S2 is None:
                            continue
                        out.append(dict(leaf=L, n=n, k=k, S1=S1, S2=S2, blocker=blk, flame1=flame1,
                                        leavesOnPath=sum(sc.cat(c) == LEAVES for c in path)))
    return out


def blocked_by(sc, a, b, cells):
    seg = segment_cells(sc, a, b)
    return any(c in cells for c in seg)


def eval_torch(sc, cand):
    L, n = cand["leaf"], cand["n"]
    fc = add(tuple(v + .5 for v in L), n, .5)
    best = []
    t = (n[2], 0, -n[0])
    for d in (2.4, 3.0, 3.8):
        for dy in (-1.0, -.5, 0.0, .5):
            for lo in (-1.2, -.6, 0, .6, 1.2):
                eye = add(add(add(fc, n, d), (0, 1, 0), dy), t, lo)
                if not body_clear(sc, eye):
                    continue
                vis = visible_texels(sc, eye, L, n)
                if len(vis) < 90:
                    continue
                yaw, pitch = look(eye, fc)
                fl = sc.trace(eye, norm(sub(cand["flame1"], eye)), math.dist(eye, cand["flame1"]) + .1)
                hidden = fl["kind"] != "sky" and fl["t"] < math.dist(eye, cand["flame1"]) - .1
                best.append(dict(eye=eye, yaw=yaw, pitch=pitch, visibleTexels=len(vis), flameHidden=hidden,
                                 flameHitKind=fl["kind"], score=len(vis) / 256 + (0.6 if hidden else 0) - .05 * abs(dy)))
    best.sort(key=lambda r: -r["score"])
    return best[:2]


def wide_pose(sc, cand, fc, n, extra=(), min_d=5.5, max_d=10.5):
    t = (n[2], 0, -n[0])
    best = None
    for d in (5.5, 6.5, 7.5, 9.0, 10.5):
        if not min_d <= d <= max_d:
            continue
        for dy in (-1.4, -.6, 0.2):
            for lo in (-3, -1.5, 0, 1.5, 3):
                eye = add(add(add(fc, n, d), (0, 1, 0), dy), t, lo)
                if not body_clear(sc, eye):
                    continue
                vis = visible_texels(sc, eye, cand["leaf"], n)
                if len(vis) < 60:
                    continue
                yaw, pitch = look(eye, fc)
                # frame the leaf on the left/right third rather than dead centre
                yaw += 9 if lo > 0 else -9 if lo < 0 else 0
                if to_pixel(fc, eye, yaw, pitch) is None:
                    continue
                comp, ex = composition(sc, eye, yaw, pitch, 32, 18, extra)
                leaf = comp.get("leaf_near", 0) + comp.get("leaf_far", 0)
                score = (1 - abs(leaf - .45) * 2) + (1 - abs(comp.get("log", 0) - .1) * 4) * .5 + (1 - abs(comp.get("ground", 0) - .2) * 3) * .4 \
                    + min(comp.get("sky", 0), .15) * 2 - 3 * comp.get("solid", 0) - 3 * comp.get("unknown", 0) - 2 * ex + len(vis) / 512
                if best is None or score > best["score"]:
                    best = dict(eye=eye, yaw=round(yaw, 2), pitch=pitch, visibleTexels=len(vis), composition=comp, wallFraction=ex, score=score)
    return best


def day_candidates(sc, box, tod):
    sx, sy, _ = sun_direction(tod)
    s = norm((sx, sy, 0.0))
    n = (-1 if sx > 0 else 1, 0, 0)
    x0, z0, x1, z1 = box
    out = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(60, 92):
                L = (x, y, z)
                if sc.grid.cat(*L) != LEAVES or not sc.natural_leaf(L):
                    continue
                F = (x + n[0], y, z)
                if sc.cat(F) != AIR:
                    continue
                c = (x + .5, y + .5, z + .5)
                ok = True
                for off in ((0, 0, 0), (0, .35, .35), (0, -.35, -.35), (0, .35, -.35), (0, -.35, .35)):
                    h = sc.trace(add(c, off), s, 40, skip=(L,), stop_leaf=True)
                    if h["kind"] != "sky":
                        ok = False
                        break
                if not ok:
                    continue
                # wall: 3 (y) x 4 (z) stone plane at x = leaf + 3 cells toward the Sun's x, raised along the Sun ray
                dx = 3 if sx > 0 else -3
                t = abs(dx) / abs(s[0])
                cy = math.floor(c[1] + s[1] * t)
                wall = [(x + dx, cy + j, z + k) for j in (-1, 0, 1) for k in (-2, -1, 0, 1)]
                if any(sc.cat(w) != AIR for w in wall):
                    continue
                sc.extra = {w: SOLID for w in wall}
                shaded = all(sc.trace(p, s, 40, skip=(L,))["kind"] == "solid" for p in face_points(L, n)[::17])
                sc.extra = {}
                if not shaded:
                    continue
                out.append(dict(leaf=L, n=n, sun=s, time=tod, wall=wall))
    return out


def eval_day(sc, cand):
    L, n = cand["leaf"], cand["n"]
    fc = add(tuple(v + .5 for v in L), n, .5)
    best = []
    t = (n[2], 0, -n[0])
    for d in (2.4, 3.0, 3.8):
        for dy in (-1.6, -1.0, -.5, 0.0):
            for lo in (-1.2, -.6, 0, .6, 1.2):
                eye = add(add(add(fc, n, d), (0, 1, 0), dy), t, lo)
                if not body_clear(sc, eye):
                    continue
                vis = visible_texels(sc, eye, L, n)
                if len(vis) < 90:
                    continue
                yaw, pitch = look(eye, fc)
                sc.extra = {w: SOLID for w in cand["wall"]}
                comp, ex = composition(sc, eye, yaw, pitch, 24, 14, set(cand["wall"]))
                sc.extra = {}
                best.append(dict(eye=eye, yaw=yaw, pitch=pitch, visibleTexels=len(vis), wallFraction=ex,
                                 score=len(vis) / 256 - 4 * ex + min(comp.get("sky", 0), .3)))
    best.sort(key=lambda r: -r["score"])
    return best[:1]


def main():
    box = tuple(int(v) for v in sys.argv[1:5]) if len(sys.argv) >= 5 else (150, 300, 250, 420)
    sc = Scene(box)
    t0 = time.time()
    tc = torch_candidates(sc, box)
    print("# torch candidates %d %.0fs" % (len(tc), time.time() - t0), file=sys.stderr)
    tc.sort(key=lambda c: (c["leavesOnPath"], c["k"]))
    torch = []
    for c in tc[:400]:
        ev = eval_torch(sc, c)
        if ev:
            torch.append(dict(c, close=ev[0]))
    torch.sort(key=lambda r: -r["close"]["score"])
    print("# torch evaluated %d %.0fs" % (len(torch), time.time() - t0), file=sys.stderr)
    day = []
    for tod in DAY_TIMES:
        dc = day_candidates(sc, box, tod)
        print("# day %d candidates %d %.0fs" % (tod, len(dc), time.time() - t0), file=sys.stderr)
        for c in dc[:300]:
            ev = eval_day(sc, c)
            if ev:
                day.append(dict(c, close=ev[0]))
    day.sort(key=lambda r: -r["close"]["score"])
    res = dict(box=box, snapshot=SNAP, torch=torch[:25], day=day[:25], counts=dict(torch=len(torch), day=len(day)))
    (HERE / "site-candidates.json").write_text(json.dumps(res, indent=1, default=list))
    print(json.dumps(dict(counts=res["counts"], torchTop=[(r["leaf"], r["n"], r["close"]["visibleTexels"], r["close"]["flameHidden"], round(r["close"]["score"], 2)) for r in torch[:8]],
                          dayTop=[(r["leaf"], r["time"], r["close"]["visibleTexels"], round(r["close"]["wallFraction"], 3), round(r["close"]["score"], 2)) for r in day[:8]])))


if __name__ == "__main__":
    main()
