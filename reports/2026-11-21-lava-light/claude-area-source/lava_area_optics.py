"""CPU optics reference for exposed-lava lighting (Aqualumen 1.8.0 study, Claude).

Nothing here runs Minecraft, a GPU or a window. Three families of numbers:

  reference   brute-force area integral  E(x) = L * sum_faces  int V cos_r cos_e / r^2 dA
              with exact segment/box visibility on the same voxel boxes.
  shipped     a numpy re-statement of the 1.8.0 code paths that light a lava cave:
              vanilla block-light flood fill -> lampLighting() vanilla/attribution mix
              (release/shaders/lib/local_lighting.glsl:224-318) and, as a counterfactual,
              lava registered as ordinary point lamps through the 12-slot tile list
              (shadowcomp1.csh:67-101).
  proposed    a world-anchored tile aggregate of exposed emitter faces: analytic
              Lambert polygon irradiance for the unoccluded part and a fixed
              stratified visibility ratio (uniform or equal-contribution strata).

Usage:  python -I lava_area_optics.py [--receipt receipt.json] [--quick]
"""
import argparse, hashlib, json, math, os, platform, sys, time
import numpy as np

H_SOURCE = 8.0 / 9.0          # LiquidBlockRenderer MAX_FLUID_HEIGHT = 0.8888889f; FlowingFluid.getOwnHeight = amount/9
L_LAVA = 11.0 * (15.0 / 14.0) ** 2   # radiance chosen so one face's on-axis intensity L*A equals the shipped level-15 lamp intensity
EPS = 1e-6

# ---------------------------------------------------------------- geometry
class World:
    """Axis-aligned boxes. solid cells are unit cubes; lava cells are boxes up to their fluid top."""
    def __init__(self):
        self.lo, self.hi = [], []
    def box(self, lo, hi):
        self.lo.append(lo); self.hi.append(hi)
    def arrays(self):
        return np.array(self.lo, float), np.array(self.hi, float)

def blocked(P, Q, lo, hi, chunk=200000):
    """True where segment P->Q passes through the interior of any box (strictly between the ends)."""
    out = np.zeros(len(P), bool)
    if len(lo) == 0: return out
    for s in range(0, len(P), chunk):
        p = P[s:s + chunk]; d = Q[s:s + chunk] - p
        inv = 1.0 / np.where(np.abs(d) > 1e-12, d, 1e-12)
        t0 = (lo[None] - p[:, None]) * inv[:, None]; t1 = (hi[None] - p[:, None]) * inv[:, None]
        enter = np.minimum(t0, t1).max(-1); leave = np.maximum(t0, t1).min(-1)
        hit = (enter < leave - 1e-9) & (leave > 1e-7) & (enter < 1 - 1e-7)
        out[s:s + chunk] = hit.any(-1)
    return out

# An emitter face: horizontal upward square [x0,x1]x[z0,z1] at height y (only +Y is needed for the
# fixtures; LiquidBlockRenderer emits side faces only where a neighbour does not occlude them).
def face_samples(face, n):
    x0, x1, y, z0, z1 = face
    u = (np.arange(n) + 0.5) / n
    X, Z = np.meshgrid(x0 + (x1 - x0) * u, z0 + (z1 - z0) * u, indexing="ij")
    pts = np.stack([X.ravel(), np.full(X.size, y), Z.ravel()], -1)
    return pts, (x1 - x0) * (z1 - z0) / (n * n)

def reference_E(xr, nr, faces, world, n=32, L=L_LAVA, visibility=True, vis_fn=None):
    """Brute-force midpoint quadrature (n x n per face) with exact visibility (boxes, or vis_fn(X, P))."""
    lo, hi = world.arrays()
    E = np.zeros(len(xr))
    for f in faces:
        pts, dA = face_samples(f, n)
        R = len(xr); S = len(pts)
        P = np.repeat(pts[None], R, 0).reshape(-1, 3)
        X = np.repeat(xr[:, None], S, 1).reshape(-1, 3)
        Nn = np.repeat(nr[:, None], S, 1).reshape(-1, 3)
        d = P - X; r2 = (d * d).sum(-1); r = np.sqrt(r2)
        cr = np.maximum((d * Nn).sum(-1) / r, 0); ce = np.maximum(-d[:, 1] / r, 0)
        k = cr * ce / r2
        if visibility:
            live = k > 0
            v = np.ones(len(P))
            if vis_fn is not None: v[live] = vis_fn(X[live], P[live])
            else: v[live] = ~blocked(X[live] + Nn[live] * 1e-5, P[live] + np.array([0, 1e-5, 0]), lo, hi)
            k = k * v
        E += L * dA * k.reshape(R, S).sum(1)
    return E

# ------------------------------------------------- analytic Lambert polygon irradiance
def clip_polygon(poly, x, n):
    """Sutherland-Hodgman clip against the receiver's upper half-space (n.(p-x) >= 0)."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        da, db = np.dot(n, a - x), np.dot(n, b - x)
        if da >= 0: out.append(a)
        if (da >= 0) != (db >= 0):
            out.append(a + (b - a) * (da / (da - db)))
    return out

def lambert_polygon(x, n, poly, L=L_LAVA):
    """Lambert (1760) / Arvo (1995): E = L/2 * sum_i Theta_i (n . Gamma_i) for an emitter facing +Y.
    The polygon is listed counter-clockwise seen from above so that the sign is positive for receivers above it."""
    poly = [np.asarray(p, float) for p in poly]
    if np.mean([p[1] for p in poly]) >= x[1]: return 0.0      # receiver must be in front of an upward face
    poly = clip_polygon(poly, x, n)
    if len(poly) < 3: return 0.0
    s = 0.0
    for i in range(len(poly)):
        a = poly[i] - x; b = poly[(i + 1) % len(poly)] - x
        a /= np.linalg.norm(a); b /= np.linalg.norm(b)
        c = np.cross(a, b); cn = np.linalg.norm(c)
        if cn < 1e-14: continue
        s += math.atan2(cn, np.dot(a, b)) * np.dot(n, c / cn)
    return L * 0.5 * abs(s)

def rect_poly(x0, x1, y, z0, z1):
    return [(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)]

def howell_corner(a, b, h):
    """Configuration factor, differential element parallel to an a x b rectangle, normal through a corner
    (Howell catalog, section B). Closed form used as an independent analytic control."""
    A = a / math.hypot(a, h) if h else 1.0; B = b / math.hypot(b, h)
    return (A * math.atan(b / math.hypot(a, h)) + B * math.atan(a / math.hypot(b, h))) / (2 * math.pi)

# ----------------------------------------------------- 1.8.0 shipped behaviour (numpy)
def vanilla_flood(sources, opaque, bounds):
    """Minecraft block light: BFS, -1 per step through non-opaque cells (air), sources keep their level."""
    from collections import deque
    lvl = {}; q = deque()
    for c, L in sources.items(): lvl[c] = L; q.append(c)
    (x0, y0, z0), (x1, y1, z1) = bounds
    while q:
        c = q.popleft(); L = lvl[c] - 1
        if L <= 0: continue
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            m = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if not (x0 <= m[0] <= x1 and y0 <= m[1] <= y1 and z0 <= m[2] <= z1): continue
            if m in opaque or lvl.get(m, 0) >= L: continue
            lvl[m] = L; q.append(m)
    return lvl

def block_level(L):        # Iris lightmap texture matrix: (16 L + 8) / 256
    return (16.0 * L + 8.0) / 256.0

def shipped_vanilla(b):    # local_lighting.glsl:224, red channel of vec3(1.0,0.56,0.25)*b^3*2
    return 2.0 * b ** 3

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def shipped_point_lamp(xr, nr, lamp, level, vis=1.0):
    """Unoccluded single-ray version of local_lighting.glsl:252-303 (diffuse, red channel, tint 1)."""
    d = lamp - xr; d2 = (d * d).sum(-1); dist = np.sqrt(d2)
    nl = np.maximum((d * nr).sum(-1) / dist, 0)
    falloff = 1 - smoothstep(0.7 * 14.0, 14.0, dist)
    return 11.0 * (level / 14.0) ** 2 * falloff * vis * nl / (0.38 + d2) * (d2 < 196.0)

def shipped_tile_list(lamps, receiver_tile_centre, cap=12, rng=14.0):
    """shadowcomp1.csh:67-97: per 8^3 tile, keep the top `cap` by level/(1+|d|^2) from the tile centre."""
    w = []
    for i, (p, lvl) in enumerate(lamps):
        d = p - receiver_tile_centre
        near = np.maximum(np.abs(d) - 4.0, 0)
        if (near * near).sum() >= rng * rng: continue
        w.append((lvl / (1.0 + (d * d).sum()), i))
    w.sort(key=lambda t: -t[0])          # insertion-sort order is equivalent to a stable descending sort
    return [i for _, i in w[:cap]]

# ---------------------------------------------------------- proposed tile aggregate
class Tile:
    """World-anchored 4^3 tile; moments of its exposed +Y faces (area, centroid, in-plane variance)."""
    def __init__(self, faces):
        A = np.array([(f[1] - f[0]) * (f[4] - f[3]) for f in faces])
        cx = np.array([(f[0] + f[1]) / 2 for f in faces]); cz = np.array([(f[3] + f[4]) / 2 for f in faces])
        y = np.array([f[2] for f in faces]); wx = np.array([f[1] - f[0] for f in faces]); wz = np.array([f[4] - f[3] for f in faces])
        self.area = A.sum(); self.c = np.array([(A * cx).sum(), (A * y).sum(), (A * cz).sum()]) / self.area
        vx = (A * ((cx - self.c[0]) ** 2 + wx ** 2 / 12)).sum() / self.area
        vz = (A * ((cz - self.c[2]) ** 2 + wz ** 2 / 12)).sum() / self.area
        self.w = np.array([math.sqrt(12 * vx), math.sqrt(12 * vz)])      # equivalent rectangle sides
        self.scale = self.area / (self.w[0] * self.w[1])                  # radiance scale preserving flux
        self.faces = faces
    def rect(self):
        hx, hz = self.w / 2
        return (self.c[0] - hx, self.c[0] + hx, self.c[1], self.c[2] - hz, self.c[2] + hz)

def tiles_from_faces(faces, size=4, sunken=False):
    """sunken: the pool is let into full solid cells, so its surface (top 8/9) lies 1/9 m below a rim at
    the cell top. A tile side carries a lip only where no lava continues across that edge."""
    groups = {}
    for f in faces:
        key = (math.floor(f[0] / size), math.floor(f[2] / size), math.floor(f[3] / size))
        groups.setdefault(key, []).append(f)
    tiles = [Tile(v) for _, v in sorted(groups.items())]
    cells = {(f[0], f[3]) for f in faces}
    for t in tiles:
        t.sunken = sunken; t.rim = math.floor(t.c[1]) + 1.0
        x0, x1, _, z0, z1 = t.rect()
        own = {(f[0], f[3]) for f in t.faces}
        def continues(cands): return any(c in cells and c not in own for c in cands)
        zs = range(math.floor(z0), math.ceil(z1)); xs = range(math.floor(x0), math.ceil(x1))
        t.lips = {"x0": not continues([(math.floor(x0) - 1, z) for z in zs]),
                  "x1": not continues([(math.ceil(x1), z) for z in zs]),
                  "z0": not continues([(x, math.floor(z0) - 1) for x in xs]),
                  "z1": not continues([(x, math.ceil(z1)) for x in xs])}
    return tiles

def visible_rect(t, x, lip=True):
    """Analytic aperture clip: the rim rectangle (rect lifted to t.rim) projected centrally from the
    receiver onto the emitting plane stays axis-aligned, so the part of the sunken surface seen through
    the opening is a rectangle intersection. Exact for a rectangular sunken pool; no rays needed."""
    x0, x1, y, z0, z1 = t.rect()
    if not (lip and getattr(t, "sunken", False)): return (x0, x1, y, z0, z1)
    if x[1] <= t.rim + 1e-9: return None
    s = (x[1] - y) / (x[1] - t.rim)
    if t.lips["x0"]: x0 = max(x0, x[0] + (x0 - x[0]) * s)
    if t.lips["x1"]: x1 = min(x1, x[0] + (x1 - x[0]) * s)
    if t.lips["z0"]: z0 = max(z0, x[2] + (z0 - x[2]) * s)
    if t.lips["z1"]: z1 = min(z1, x[2] + (z1 - x[2]) * s)
    if x0 >= x1 or z0 >= z1: return None
    return (x0, x1, y, z0, z1)

def strata(rect, K, x, n, mode):
    """K visibility anchors inside the equivalent rectangle. 'uniform': kx x kz cell centres.
    'contribution': split x then z so each stratum carries an equal share of the analytic Lambert
    irradiance at this receiver (bisection on the closed form); anchor = stratum midpoint."""
    x0, x1, y, z0, z1 = rect
    k = int(round(math.sqrt(K)))
    if mode == "uniform":
        u = (np.arange(k) + 0.5) / k
        return [(x0 + (x1 - x0) * a, y, z0 + (z1 - z0) * b) for a in u for b in u]
    def F(a0, a1, b0, b1): return lambert_polygon(x, n, rect_poly(a0, a1, y, b0, b1), 1.0)
    def cuts(total_fn, lo, hi):
        T = total_fn(lo, hi); edges = [lo]
        for i in range(1, k):
            target = T * i / k; a, b = edges[-1], hi
            for _ in range(30):
                m = 0.5 * (a + b)
                if total_fn(lo, m) < target: a = m
                else: b = m
            edges.append(0.5 * (a + b))
        return edges + [hi]
    if F(x0, x1, z0, z1) <= 0: return strata(rect, K, x, n, "uniform")
    xe = cuts(lambda a, b: F(a, b, z0, z1), x0, x1); out = []
    for i in range(k):
        ze = cuts(lambda a, b: F(xe[i], xe[i + 1], a, b), z0, z1)
        for j in range(k):
            out.append((0.5 * (xe[i] + xe[i + 1]), y, 0.5 * (ze[j] + ze[j + 1])))
    return out

def proposed_E(xr, nr, tiles, world, K=4, mode="uniform", L=L_LAVA, visibility=True, lip=True):
    lo, hi = world.arrays(); E = np.zeros(len(xr))
    for t in tiles:
        for i in range(len(xr)):
            x, n = xr[i], nr[i]
            rect = visible_rect(t, x, lip)
            if rect is None: continue
            e = lambert_polygon(x, n, rect_poly(*rect), L * t.scale)
            if e <= 0: continue
            if visibility:
                a = np.array(strata(rect, K, x, n, mode))
                v = ~blocked(np.repeat(x[None] + n * 1e-5, len(a), 0), a + np.array([0, 1e-5, 0]), lo, hi)
                e *= v.mean()
            E[i] += e
    return E

def hierarchical_E(xr, nr, faces, world, K=4, visibility=True, near=(2.5, 3.5), far=(7.0, 9.0), sunken=True):
    """What one 128-bit texel per 8^3 tile can drive: a 64-bit exposure mask of the tile's dominant
    layer. From the mask the shader derives per-cell squares (near), four 4x4 quadrant rectangles (mid)
    or one 8^3 rectangle (far). Weights depend only on the receiver's distance to the tile's emitting
    bounding box and blend linearly over the bands, so the result is continuous in the receiver position."""
    parents = {}
    for f in faces: parents.setdefault((math.floor(f[0] / 8), math.floor(f[2] / 8), math.floor(f[3] / 8)), []).append(f)
    cells_all = faces
    levels = {}
    for key, fs in parents.items():
        own = set(fs)
        def sub(size):
            ts = tiles_from_faces(cells_all, size=size, sunken=sunken)
            return [t for t in ts if set(t.faces) <= own]
        lo = np.array([min(f[0] for f in fs), min(f[3] for f in fs)]); hi = np.array([max(f[1] for f in fs), max(f[4] for f in fs)])
        levels[key] = (sub(1), sub(4), sub(8), lo, hi, fs[0][2])
    E = np.zeros(len(xr))
    for key, (t1, t4, t8, lo, hi, y) in levels.items():
        for i in range(len(xr)):
            x = xr[i]
            dxz = np.maximum(np.maximum(lo - x[[0, 2]], x[[0, 2]] - hi), 0); d = math.sqrt((dxz ** 2).sum() + (x[1] - y) ** 2)
            a = min(max((d - near[0]) / (near[1] - near[0]), 0), 1); b = min(max((d - far[0]) / (far[1] - far[0]), 0), 1)
            w = {1: 1 - a, 4: a * (1 - b), 8: a * b}
            for size, ts in ((1, t1), (4, t4), (8, t8)):
                if w[size] > 0:
                    E[i] += w[size] * proposed_E(xr[i:i + 1], nr[i:i + 1], ts, world, K=K, visibility=visibility)[0]
    return E

# ------------------------------------------------------------------------- scenes
def basin_world(lava_cells, pillar):
    """Geometry of reports/2026-11-21-lava-light/basin.py (read-only mirror): smooth-stone shell
    198..209 x 172..180 x 359..367, white wall z=366, floor y=172, pillar (202,173..175,364)."""
    w = World()
    for x in range(199, 209):
        for z in range(360, 366):
            if (x, z) in lava_cells: w.box((x, 172, z), (x + 1, 172 + H_SOURCE, z + 1))
            else: w.box((x, 172, z), (x + 1, 173, z + 1))
    if pillar: w.box((202, 173, 364), (203, 176, 365))
    faces = [(x, x + 1, 172 + H_SOURCE, z, z + 1) for (x, z) in sorted(lava_cells)]
    return w, faces

def wall_receivers(step=0.25):
    xs = np.arange(199.2 + step / 2, 208.8, step); ys = np.arange(173.3 + step / 2, 177.9, step)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    xr = np.stack([X.ravel(), Y.ravel(), np.full(X.size, 366.0 - 1e-4)], -1)
    nr = np.tile([0.0, 0.0, -1.0], (len(xr), 1))
    return xr, nr, X.shape

def lightmap_basin(lava_cells, pillar, torch=None):
    opaque = set()
    for x in range(198, 210):
        for y in range(172, 181):
            for z in range(359, 368):
                shell = x in (198, 209) or y in (172, 180) or z in (359, 366, 367)
                if shell and not (y == 172 and (x, z) in lava_cells): opaque.add((x, y, z))
    if pillar: opaque |= {(202, y, 364) for y in range(173, 176)}
    src = {(x, 172, z): 15 for (x, z) in lava_cells}
    lava_only = vanilla_flood(src, opaque, ((198, 172, 359), (209, 180, 367)))
    return lava_only, opaque

def shipped_wall(lava_cells, pillar, xr, torch=None, bounce_conf=0.0):
    """Red-channel lampLighting() result for each wall receiver; torch adds one registered level-14 lamp."""
    lvl, _ = lightmap_basin(lava_cells, pillar)
    out, lava_part = [], []
    for p in xr:
        cell = (int(math.floor(p[0])), int(math.floor(p[1])), 365)      # air cell in front of the wall face
        Lb = lvl.get(cell, 0)
        if torch is not None:
            tcell = tuple(int(math.floor(v)) for v in torch)
            taxi = abs(tcell[0] - cell[0]) + abs(tcell[1] - cell[1]) + abs(tcell[2] - cell[2])
            Lb = max(Lb, 14 - taxi)                                     # vanilla max of both floods
        b = block_level(Lb); vanilla = shipped_vanilla(b)
        if torch is None:
            out.append(vanilla); lava_part.append(vanilla); continue
        taxi = abs(math.floor(torch[0]) - math.floor(p[0])) + abs(math.floor(torch[1]) - math.floor(p[1])) + abs(math.floor(torch[2]) - math.floor(p[2] - 0.03))
        tracked = min(max((14 + 1.0 - taxi) / 15.0, 0.0), 1.0)
        attribution = float(smoothstep(0, 0.15, tracked)) * min(max((tracked + 0.065) / max(b, 0.065), 0), 1)
        residual = vanilla * (1 - attribution) + attribution * (1 - bounce_conf) * 0.18 * b ** 3   # tint/weight = 1 for one lamp, red channel
        direct = float(shipped_point_lamp(p[None], np.array([[0, 0, -1.0]]), np.array(torch), 14)[0])
        out.append(direct + residual)
        lava_vanilla = shipped_vanilla(block_level(lvl.get(cell, 0)))
        lava_part.append(lava_vanilla * (1 - attribution))
    return np.array(out), np.array(lava_part)

def summarize(a):
    return {"median": float(np.median(a)), "mean": float(np.mean(a)), "min": float(np.min(a)), "max": float(np.max(a))}

# ------------------------------------------------------------------------- experiments
def analytic_controls():
    rows = []
    for h in (0.05, 0.25, 1.0, 4.0, 16.0):
        x = np.array([0.0, h, 0.0]); n = np.array([0, -1.0, 0])
        lam = lambert_polygon(x, n, rect_poly(-0.5, 0.5, 0.0, -0.5, 0.5), 1.0)
        how = math.pi * 4 * howell_corner(0.5, 0.5, h)
        ref = reference_E(x[None], n[None], [(-0.5, 0.5, 0.0, -0.5, 0.5)], World(), n=256, L=1.0, visibility=False)[0]
        rows.append({"h": h, "lambertPolygon": lam, "howellCorner": how, "midpoint256": float(ref),
                     "relLambertVsHowell": abs(lam - how) / how, "relMidpointVsHowell": abs(ref - how) / how})
    # flux: integrate unoccluded irradiance of a 3x3 upward source over a ceiling plane at height 1
    t = Tile([(x, x + 1, 0.0, z, z + 1) for x in range(3) for z in range(3)])
    radii = np.concatenate([[0], np.geomspace(1e-3, 3e3, 400)])
    flux = 0.0; prev = None
    for r0, r1 in zip(radii[:-1], radii[1:]):
        rm = 0.5 * (r0 + r1); acc = 0.0
        for k in range(16):
            ang = (k + 0.5) / 16 * 2 * math.pi
            x = np.array([t.c[0] + rm * math.cos(ang), 1.0, t.c[2] + rm * math.sin(ang)])
            acc += lambert_polygon(x, np.array([0, -1.0, 0]), rect_poly(*t.rect()), 1.0)
        flux += acc / 16 * math.pi * (r1 * r1 - r0 * r0)
    # far-field point source escaping beyond R=3000 at H=1: fraction H^2/(R^2+H^2), negligible
    return {"squareUnderReceiver": rows,
            "fluxCeilingPlane": {"integrated": flux, "piLA": math.pi * 9, "relError": abs(flux - 9 * math.pi) / (9 * math.pi)}}

def near_far():
    rows = []
    single = [(0, 1, H_SOURCE, 0, 1)]; pool = [(x, x + 1, H_SOURCE, z, z + 1) for x in range(-1, 2) for z in range(-1, 2)]
    for name, faces in (("one", single), ("nine", pool)):
        tiles = tiles_from_faces(faces); A = sum((f[1] - f[0]) * (f[4] - f[3]) for f in faces)
        c = np.array([np.mean([(f[0] + f[1]) / 2 for f in faces]), H_SOURCE, np.mean([(f[3] + f[4]) / 2 for f in faces])])
        for geom in ("above", "oblique45"):
            for d in (0.05, 0.25, 0.5, 1, 2, 4, 8, 16, 32):
                if geom == "above": x = c + [0, d, 0]; n = np.array([0, -1.0, 0])
                else: x = c + np.array([d, d, 0]) / math.sqrt(2); n = np.array([-1.0, 0, 0])
                ref = float(reference_E(x[None], n[None], faces, World(), n=64, visibility=False)[0])
                prop = float(proposed_E(x[None], n[None], tiles, World(), visibility=False)[0])
                dv = x - c; r = np.linalg.norm(dv)
                point = L_LAVA * A * max(np.dot(-dv, n) / r, 0) * max(dv[1] / r, 0) / r ** 2
                ship = sum(float(shipped_point_lamp(x[None], n[None], np.array([(f[0] + f[1]) / 2, H_SOURCE, (f[3] + f[4]) / 2]), 15)[0]) for f in faces)
                rows.append({"source": name, "geometry": geom, "distance": d, "reference": ref, "proposed": prop,
                             "pointLA": point, "hypotheticalShippedPointsLevel15": ship,
                             "relProposed": abs(prop - ref) / ref if ref else 0.0,
                             "relPoint": abs(point - ref) / ref if ref else 0.0})
    return rows

def basin(quick):
    step = 0.5 if quick else 0.25
    xr, nr, shape = wall_receivers(step)
    one = {(202, 361)}; nine = {(x, z) for x in range(201, 204) for z in range(360, 363)}
    res = {"receivers": int(len(xr)), "spacing": step, "layouts": {}}
    refs = {}
    for lname, cells in (("one", one), ("nine", nine)):
        for pillar in (False, True):
            w, faces = basin_world(cells, pillar)
            key = f"{lname}-{'pillar' if pillar else 'open'}"
            t0 = time.time(); ref = reference_E(xr, nr, faces, w, n=12 if quick else 40); tr = time.time() - t0
            refs[key] = ref
            tiles = tiles_from_faces(faces, sunken=True)
            est = {}
            variants = [("lipOnly-K0", dict(K=0, visibility=False)), ("noLip-uniform-K4", dict(K=4, lip=False))]
            variants += [(f"{m}-K{K}", dict(K=K, mode=m)) for m in ("uniform", "contribution") for K in (1, 4, 9, 16)
                         if not (m == "contribution" and K == 1)]
            for name, kw in variants:
                    p = proposed_E(xr, nr, tiles, w, **kw)
                    err = p - ref
                    mode, K = name.rsplit("-K", 1)
                    est[name] = {"relRMS": float(np.sqrt(np.mean(err ** 2)) / np.mean(ref)),
                                           "relMaxAbs": float(np.max(np.abs(err)) / np.mean(ref)),
                                           "flux": float(np.mean(p) / np.mean(ref))}
            ship, _ = shipped_wall(cells, pillar, xr)
            res["layouts"][key] = {"reference": summarize(ref), "referenceSeconds": round(tr, 2),
                                   "tiles": len(tiles), "exposedArea": sum(t.area for t in tiles),
                                   "proposedErrors": est, "shippedVanilla": summarize(ship)}
    r = res["layouts"]
    def ratio(a, b, k): return r[a][k]["median"] / r[b][k]["median"]
    res["contrasts"] = {
        "reference_nine_over_one_open": float(np.median(refs["nine-open"]) / np.median(refs["one-open"])),
        "shipped_nine_over_one_open": ratio("nine-open", "one-open", "shippedVanilla"),
        "reference_pillar_over_open_one": float(np.median(refs["one-pillar"]) / np.median(refs["one-open"])),
        "shipped_pillar_over_open_one": ratio("one-pillar", "one-open", "shippedVanilla"),
        "reference_pillar_over_open_nine": float(np.median(refs["nine-pillar"]) / np.median(refs["nine-open"])),
        "shipped_pillar_over_open_nine": ratio("nine-pillar", "nine-open", "shippedVanilla"),
        "reference_fully_shadowed_fraction_one_pillar": float(np.mean(refs["one-pillar"] < 0.02 * np.median(refs["one-open"]))),
        "reference_fully_shadowed_fraction_nine_pillar": float(np.mean(refs["nine-pillar"] < 0.02 * np.median(refs["nine-open"]))),
    }
    # The lip clip is exact geometry; residual open-case error is the midpoint reference's own 1/n step error.
    xc, nc, _ = wall_receivers(0.5); wc, fc = basin_world(one, False)
    pc = proposed_E(xc, nc, tiles_from_faces(fc, sunken=True), wc, K=0, visibility=False)
    conv = {}
    for n in ((12, 24) if quick else (12, 24, 48, 96)):
        rc = reference_E(xc, nc, fc, wc, n=n)
        conv[str(n)] = {"relRMS": float(np.sqrt(np.mean((pc - rc) ** 2)) / np.mean(rc)), "relMaxAbs": float(np.max(np.abs(pc - rc)) / np.mean(rc))}
    res["lipClipVsReferenceResolution_oneOpen"] = conv
    # A registered torch in the same room: how much of the lava-attributed vanilla light survives the attribution mix.
    torch = (207.5, 173.64, 360.5)
    full, lava_left = shipped_wall(nine, False, xr, torch=torch)
    lava_alone, _ = shipped_wall(nine, False, xr)
    res["torchAttribution"] = {"torch": torch, "lavaVanillaRetainedFraction": summarize(lava_left / lava_alone),
                               "wallTotalWithTorchOverLavaOnly": summarize(full / lava_alone)}
    return res

def lake_and_seams():
    """12x12 lava lake (cells x,z in 0..11, top at 8/9) under a ceiling at y=6; a torch at (14.5,3.64,6.5).
    Receivers on the ceiling (normal -Y) along z=6.5 from x=-6 to 26: tile boundaries at x=0,8,16,24."""
    faces = [(x, x + 1, H_SOURCE, z, z + 1) for x in range(12) for z in range(12)]
    world = World()
    for x in range(-8, 28):
        for z in range(-8, 20):
            if not (0 <= x < 12 and 0 <= z < 12): world.box((x, 0, z), (x + 1, 1, z + 1))
            else: world.box((x, 0, z), (x + 1, H_SOURCE, z + 1))
    xs = np.array(sorted(set(np.round(np.concatenate([np.arange(-6, 26.01, 0.5), [b + s for b in (8, 16) for s in (-1e-3, 1e-3)]]), 6))))
    xr = np.stack([xs, np.full(len(xs), 6.0 - 1e-4), np.full(len(xs), 6.5)], -1); nr = np.tile([0, -1.0, 0], (len(xs), 1))
    ref = reference_E(xr, nr, faces, world, n=6)
    tiles = tiles_from_faces(faces, sunken=True)
    prop = proposed_E(xr, nr, tiles, world, K=4)
    torch = np.array([14.5, 3.64, 6.5])
    lamps = [(np.array([(f[0] + f[1]) / 2, H_SOURCE, (f[3] + f[4]) / 2]), 15) for f in faces] + [(torch, 14)]
    ship = np.zeros(len(xs)); torch_kept = []; lava_selected = []
    for i, p in enumerate(xr):
        tile_centre = np.floor(p / 8) * 8 + 4          # grid tiles are world-anchored at multiples of 8
        sel = shipped_tile_list(lamps, tile_centre)
        torch_kept.append(len(lamps) - 1 in sel); lava_selected.append(sum(1 for s in sel if s < len(faces)))
        ship[i] = sum(float(shipped_point_lamp(p[None], nr[i][None], lamps[s][0], lamps[s][1])[0]) for s in sel if s < len(faces))
    torch_direct = shipped_point_lamp(xr, nr, torch, 14)
    def jump(series, b):
        a = series[np.isclose(xs, b - 1e-3)][0]; c = series[np.isclose(xs, b + 1e-3)][0]
        return float(abs(c - a) / max(abs(a), abs(c), 1e-12))
    rows = [{"x": float(xs[i]), "reference": float(ref[i]), "proposed": float(prop[i]),
             "hypotheticalPointList": float(ship[i]), "lavaLampsSelected": lava_selected[i],
             "torchSelected": bool(torch_kept[i]), "torchDirect": float(torch_direct[i])} for i in range(len(xs))]
    prop8 = proposed_E(xr, nr, tiles_from_faces(faces, size=8, sunken=True), world, K=4)
    lit = ref > 1e-3 * ref.max()
    return {"exposedCells": len(faces), "tiles": len(tiles), "rows": rows,
            "proposedVsReference": {"relRMS": float(np.sqrt(np.mean((prop[lit] - ref[lit]) ** 2)) / np.mean(ref[lit])),
                                    "relMaxAbs": float(np.max(np.abs(prop[lit] - ref[lit])) / np.mean(ref[lit]))},
            "proposedTile8VsReference": {"relRMS": float(np.sqrt(np.mean((prop8[lit] - ref[lit]) ** 2)) / np.mean(ref[lit])),
                                         "relMaxAbs": float(np.max(np.abs(prop8[lit] - ref[lit])) / np.mean(ref[lit])),
                                         "seamJump": {str(b): jump(prop8, b) for b in (8, 16)}},
            "seamJump": {str(b): {"reference": jump(ref, b), "proposed": jump(prop, b), "hypotheticalPointList": jump(ship, b)} for b in (8, 16)},
            "torchEvictedReceivers": int(sum(1 for i in range(len(xs)) if not torch_kept[i] and torch_direct[i] > 0)),
            "receiversWithTorchInRange": int(sum(1 for i in range(len(xs)) if torch_direct[i] > 0))}

def area_scaling():
    rows = []
    for k in (1, 2, 3, 4, 6, 8, 12):
        faces = [(x, x + 1, H_SOURCE, z, z + 1) for x in range(k) for z in range(k)]
        c = k / 2.0
        world = World()
        for h in (2.0, 10.0):
            x = np.array([[c, H_SOURCE + h, c]]); n = np.array([[0, -1.0, 0]])
            ref = float(reference_E(x, n, faces, world, n=8, visibility=False)[0])
            prop = float(proposed_E(x, n, tiles_from_faces(faces), world, visibility=False)[0])
            lamps = [(np.array([(f[0] + f[1]) / 2, H_SOURCE, (f[3] + f[4]) / 2]), 15) for f in faces]
            sel = shipped_tile_list(lamps, np.floor(x[0] / 8) * 8 + 4)
            pl = sum(float(shipped_point_lamp(x, n, lamps[s][0], 15)[0]) for s in sel)
            # vanilla: receiver lightmap = 15 - taxicab to the nearest lava cell (open air)
            taxi = min(abs(math.floor(x[0, 0]) - (f[0])) + abs(math.floor(x[0, 1]) - 0) + abs(math.floor(x[0, 2]) - f[3]) for f in faces)
            van = shipped_vanilla(block_level(max(15 - taxi, 0)))
            rows.append({"side": k, "area": k * k, "height": h, "reference": ref, "proposed": prop,
                         "hypotheticalPointList": pl, "pointListSlotsUsed": len(sel), "shippedVanilla": van})
    return rows

def natural_pool(repo):
    """Irregular natural shape: the 25 distinct visible lava cells listed in the other agent's
    reports/2026-11-21-lava-light/natural-pool.json (offline Anvil survey, read-only here). The cave
    around it is unknown, so receivers are VIRTUAL planes: a ceiling 5 m above the rim and a wall
    plane east of the pool. The pool is taken as sunken into a flat solid floor (rim at y=-54)."""
    path = os.path.join(repo, "reports/2026-11-21-lava-light/natural-pool.json")
    try:
        cells = json.load(open(path))["candidate"]["distinctVisibleCells"]
    except (OSError, KeyError, ValueError):
        return {"skipped": "natural-pool.json not readable"}
    y0 = cells[0][1]; pool = {(c[0], c[2]) for c in cells}
    faces = [(x, x + 1, y0 + H_SOURCE, z, z + 1) for (x, z) in sorted(pool)]
    rim = y0 + 1.0
    def vis(X, P):    # exact: the segment crosses the rim plane once; it is open only above a pool cell
        t = (rim - P[:, 1]) / (X[:, 1] - P[:, 1]); C = P + (X - P) * t[:, None]
        cx = np.floor(C[:, 0]).astype(int); cz = np.floor(C[:, 2]).astype(int)
        return np.array([(a, b) in pool for a, b in zip(cx, cz)])
    xs = np.arange(533.5, 550.5, 1.0); zs = np.arange(363.5, 382.5, 1.0)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    ceil = np.stack([X.ravel(), np.full(X.size, rim + 5 - 1e-4), Z.ravel()], -1)
    ys = np.arange(rim + 0.5, rim + 5, 0.5); zw = np.arange(364.5, 381.5, 1.0)
    Y, ZW = np.meshgrid(ys, zw, indexing="ij")
    wall = np.stack([np.full(Y.size, 550.0 - 1e-4), Y.ravel(), ZW.ravel()], -1)
    out = {"cells": len(pool), "sourceSha256": sha(path), "receivers": {}}
    for name, xr, nvec in (("ceiling", ceil, (0, -1.0, 0)), ("eastWall", wall, (-1.0, 0, 0))):
        nr = np.tile(nvec, (len(xr), 1))
        ref = reference_E(xr, nr, faces, World(), n=16, vis_fn=vis)
        row = {"count": len(xr), "reference": summarize(ref)}
        for size in (1, 4, 8):
            tl = tiles_from_faces(faces, size=size, sunken=True)
            for lip in (True, False):
                p = proposed_E(xr, nr, tl, World(), visibility=False, lip=lip)
                lit = ref > 1e-3 * ref.max()
                row[f"tile{size}{'' if lip else '-noLip'}"] = {"tiles": len(tl),
                    "relRMS": float(np.sqrt(np.mean((p[lit] - ref[lit]) ** 2)) / np.mean(ref[lit])),
                    "relMaxAbs": float(np.max(np.abs(p[lit] - ref[lit])) / np.mean(ref[lit])),
                    "flux": float(np.mean(p) / np.mean(ref))}
        out["receivers"][name] = row
    # Distance dependence of the aggregate error: ceiling planes at several heights above the rim.
    out["ceilingHeightSweep"] = {}
    for hgt in (1.5, 3, 5, 8, 12):
        xr = np.stack([X.ravel(), np.full(X.size, rim + hgt - 1e-4), Z.ravel()], -1); nr = np.tile((0, -1.0, 0), (len(xr), 1))
        ref = reference_E(xr, nr, faces, World(), n=16, vis_fn=vis); lit = ref > 1e-3 * ref.max(); row = {}
        for size in (1, 4, 8):
            p = proposed_E(xr, nr, tiles_from_faces(faces, size=size, sunken=True), World(), visibility=False)
            row[f"tile{size}"] = {"relRMS": float(np.sqrt(np.mean((p[lit] - ref[lit]) ** 2)) / np.mean(ref[lit])),
                                  "relMaxAbs": float(np.max(np.abs(p[lit] - ref[lit])) / np.mean(ref[lit]))}
        ph = hierarchical_E(xr, nr, faces, World(), visibility=False)
        row["hierarchical"] = {"relRMS": float(np.sqrt(np.mean((ph[lit] - ref[lit]) ** 2)) / np.mean(ref[lit])),
                               "relMaxAbs": float(np.max(np.abs(ph[lit] - ref[lit])) / np.mean(ref[lit]))}
        out["ceilingHeightSweep"][str(hgt)] = row
    # Continuity of the blended hierarchy: a fine line on the ceiling 5 m up, crossing every band.
    xl = np.arange(526.0, 560.0, 0.05)
    xr = np.stack([xl, np.full(len(xl), rim + 5 - 1e-4), np.full(len(xl), 372.5)], -1); nr = np.tile((0, -1.0, 0), (len(xr), 1))
    ref = reference_E(xr, nr, faces, World(), n=16, vis_fn=vis); ph = hierarchical_E(xr, nr, faces, World(), visibility=False)
    step_ref = np.abs(np.diff(ref)); step_h = np.abs(np.diff(ph))
    out["hierarchicalLine"] = {"samples": len(xl), "spacing": 0.05,
                               "maxAdjacentStepOverMean": {"reference": float(step_ref.max() / ref.mean()), "hierarchical": float(step_h.max() / ref.mean())},
                               "relRMS": float(np.sqrt(np.mean((ph - ref) ** 2)) / ref.mean())}
    return out

def sha(path):
    try:
        with open(path, "rb") as f: return hashlib.sha256(f.read()).hexdigest()
    except OSError: return None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--receipt"); ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    here = os.path.dirname(os.path.abspath(__file__)); repo = os.path.abspath(os.path.join(here, "..", "..", ".."))
    out = {"script": os.path.basename(__file__), "scriptSha256": sha(__file__), "quick": a.quick,
           "python": sys.version.split()[0], "numpy": np.__version__, "machine": platform.machine(),
           "inputs": {"dist/Aqualumen-1.8.0.zip": sha(os.path.join(repo, "dist/Aqualumen-1.8.0.zip")),
                      "release/shaders/lib/local_lighting.glsl": sha(os.path.join(repo, "release/shaders/lib/local_lighting.glsl")),
                      "release/shaders/shadowcomp1.csh": sha(os.path.join(repo, "release/shaders/shadowcomp1.csh")),
                      "release/shaders/lib/local_capture.glsl": sha(os.path.join(repo, "release/shaders/lib/local_capture.glsl")),
                      "release/shaders/block.properties": sha(os.path.join(repo, "release/shaders/block.properties")),
                      "reports/2026-11-21-lava-light/basin.py (other agent, geometry mirrored read-only)": sha(os.path.join(repo, "reports/2026-11-21-lava-light/basin.py"))},
           "constants": {"H_SOURCE": H_SOURCE, "L_LAVA": L_LAVA, "units": "red-channel shader irradiance units of local_lighting.glsl; L_LAVA*1m^2 equals the shipped level-15 lamp intensity 11*(15/14)^2"},
           "kind": "CPU numeric study. No Minecraft, GPU, window, Iris or shader compilation involved."}
    out["analyticControls"] = analytic_controls()
    out["nearFar"] = near_far()
    out["areaScaling"] = area_scaling()
    out["basinFixture"] = basin(a.quick)
    out["lakeAndSeams"] = lake_and_seams()
    out["naturalPool"] = natural_pool(repo)
    out["inputs"]["reports/2026-11-21-lava-light/natural-pool.json (other agent, read-only)"] = out["naturalPool"].get("sourceSha256")
    out["seconds"] = round(time.time() - t0, 1)
    text = json.dumps(out, indent=1, default=float)
    if a.receipt:
        with open(a.receipt, "w") as f: f.write(text + "\n")
    print(json.dumps({k: out[k] for k in ("analyticControls", "seconds")}, indent=1, default=float))
    print(json.dumps(out["basinFixture"]["contrasts"], indent=1))
    print(json.dumps(out["basinFixture"]["torchAttribution"], indent=1))
    print(json.dumps(out["lakeAndSeams"]["seamJump"], indent=1), out["lakeAndSeams"]["torchEvictedReceivers"], out["lakeAndSeams"]["receiversWithTorchInRange"])

if __name__ == "__main__":
    main()
