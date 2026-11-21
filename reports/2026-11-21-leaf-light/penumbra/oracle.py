"""Numerical optical oracle for the penumbra of one leaf block projected on a white wall.

Run: /tmp/aqualumen-ground-metrics-venv/bin/python -I oracle.py [--quick]
Writes only oracle-* files next to this script.  No GPU, no game, no shader edits.

What is computed (all quantities per wall receiver, then averaged over the emitter disk):
  refN      neutral, binary geometry: the real 16x16 oak_leaves alpha (client jar) on both
            exposed cube quads the segment crosses (nearest texel, alpha>=0.1 like the pack's
            shadow capture).  Interior is empty, as in the vanilla cube_all model.
  refN_lamp same, but only the lamp-facing quad blocks (back-face-culled shadow pass).
  refG_phys green channel, same geometry; an opaque texel is a thin sheet of assumed green
            transmittance TAU_PHYS (NOT calibrated, a parameter).
  refG_sheet green channel, same exact geometry, but with the pack's own per-texel sheet
            constant (derived below from leaf_mask_transmission.glsl); no medium, no soft alpha.
  shaderG   numpy port of foliageSegment()/leafSurfaceCoverage() for the same segment
            (bilinear coverage, min-edge face heuristic, 0.10/m medium, chord-fade exponent).
Estimators over the 0.13 m emitter disk: tap3 (current), uni12/24/32 (area-uniform golden
spiral), mix12/24/32 (the three taps + (N-3) spiral taps, the pack's door path layout) and a
dense area-uniform reference (256 / 1024 taps, different spiral phase).
"""
import json
import sys
import time
from io import BytesIO
import multiprocessing
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ACC = HERE.parent / 'projected' / 'accepted'
JAR = (Path.home() / '.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/libraries/com/mojang/'
       'minecraft/1.21.1/minecraft-1.21.1-client.jar')
QUICK = '--quick' in sys.argv

RADIUS = 0.13            # torch emitter disk radius, local_lighting.glsl (kind not 15/16/>=18)
RECV_OFFSET = 0.025      # origin = p + normal*0.025
TAU_PHYS = 0.12          # assumed green transmittance of one opaque leaf texel (parameter)
INTERIOR = 0.10          # leaf_mask_transmission.glsl
MEAN_SURFACE = 0.5091564
ROI = (470, 225, 750, 470)   # pixel x0,y0,x1,y1 (x1,y1 exclusive) of the 1280x720 screenshots
TIP = 1.0 / 1.0

with (ACC / 'geometry.json').open() as f:
    G = json.load(f)
EYE = np.array(G['eye']); LAMP = np.array(G['source']); CELL = np.array(G['leaf'], float)
TARGET = np.array(G['target']); WALL_Z = float(G['wallZ'])

# ---------------------------------------------------------------- real atlas input
with ZipFile(JAR) as z:
    TEX = np.asarray(Image.open(BytesIO(z.read('assets/minecraft/textures/block/oak_leaves.png'))).convert('RGBA'))
assert TEX.shape == (16, 16, 4)
OPAQUE = TEX[:, :, 3] >= 26                       # alpha>=0.1 on unorm8, leaf_mask_capture.glsl
MASKF = OPAQUE.astype(float)
SPRITE_A = np.round(OPAQUE.sum() / 256.0 * 255) / 255                  # packUnorm4x8
SPRITE_RGB = np.round(TEX[OPAQUE][:, :3].mean(0)) / 255                # mean of covered texels
# Biome tint is a per-voxel chromaticity (4 bit/channel) of gl_Color; the world's biome is unknown,
# so plains foliage 0x77AB2F is ASSUMED.  It only scales the green sheet value, not any geometry.
TINT = np.round(15 * np.array([0x77, 0xAB, 0x2F]) / 0xAB) / 15
pig = np.maximum(SPRITE_RGB * TINT, 0) ** 2.2
hue = 0.5 + 0.5 * pig / max(pig.max(), 1e-5)
hue = hue / (hue @ np.array([.2126, .7152, .0722]))
MEAN_SHEET = float(np.clip((MEAN_SURFACE - (1 - SPRITE_A)) / max(SPRITE_A, 1e-5), 0, .95))
SHEET = np.clip(MEAN_SHEET * hue, .025, .95)
SHEET_G = float(SHEET[1])


def normalize(x):
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


# ---------------------------------------------------------------- camera
FW = normalize(TARGET - EYE); RIGHT = normalize(np.cross(FW, [0, 1, 0])); UP = normalize(np.cross(RIGHT, FW))
W, H = 1280, 720
TAN = np.tan(np.deg2rad(G['cameraFov']) / 2)


def pixel_to_wall(px, py):
    ray = FW + RIGHT * ((px + .5 - W / 2) * 2 * TAN / H)[..., None] + UP * ((H / 2 - py - .5) * 2 * TAN / H)[..., None]
    return EYE + ray * ((WALL_Z - EYE[2]) / np.maximum(ray[..., 2], .001))[..., None]


def wall_to_pixel(x, y):
    d = np.stack([x, y, np.full_like(x, WALL_Z)], -1) - EYE
    zc = d @ FW
    return (d @ RIGHT) / zc * H / (2 * TAN) + W / 2 - .5, H / 2 - .5 - (d @ UP) / zc * H / (2 * TAN)


# ---------------------------------------------------------------- face / texel mapping
def face_uv(f, axis, high):
    """Vanilla cube_all convention (assumed, see report): returns u,v in [0,1], v from the top."""
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    u = np.where(axis == 2, np.where(high, fx, 1 - fx),
                 np.where(axis == 0, np.where(high, 1 - fz, fz), fx))
    v = np.where(axis == 1, np.where(high, fz, 1 - fz), 1 - fy)
    return u, v


def texel(u, v):
    return OPAQUE[np.clip((v * 16).astype(int), 0, 15), np.clip((u * 16).astype(int), 0, 15)]


def shader_coverage(point):
    """Port of leafSurfaceCoverage(): min-edge face choice and bilinear row bits."""
    f = np.clip(point, 0, 1)
    edge = np.minimum(f, 1 - f)
    ex, ey, ez = edge[:, 0], edge[:, 1], edge[:, 2]
    useX = (ex <= ey) & (ex <= ez)
    useY = ~useX & (ey <= ez)
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    u = np.where(useX, np.where(fx < .5, fz, 1 - fz), np.where(useY, fx, np.where(fz < .5, 1 - fx, fx)))
    v = np.where(useX, 1 - fy, np.where(useY, np.where(fy < .5, 1 - fz, fz), 1 - fy))
    u = np.clip(u * 16 - .5, 0, 15); v = np.clip(v * 16 - .5, 0, 15)
    i = u.astype(int); j = v.astype(int); i2 = np.minimum(i + 1, 15); j2 = np.minimum(j + 1, 15)
    tx = u - i; ty = v - j
    top = (1 - tx) * MASKF[j, i] + tx * MASKF[j, i2]
    bot = (1 - tx) * MASKF[j2, i] + tx * MASKF[j2, i2]
    return (1 - ty) * top + ty * bot


MODELS = ('refN', 'refN_lamp', 'refG_phys', 'refG_sheet', 'shaderG')


def trace(r, s):
    """Segment receiver r -> emitter sample s through the one leaf cube. Returns (5, M)."""
    d = s - r
    dist = np.linalg.norm(d, axis=1)
    safe = np.where(np.abs(d) < 1e-9, 1e-9, d)
    t0 = (CELL - r) / safe; t1 = (CELL + 1 - r) / safe
    lo = np.minimum(t0, t1); hi = np.maximum(t0, t1)
    tin = lo.max(1); tout = hi.min(1)
    ain = lo.argmax(1); aout = hi.argmin(1)
    tin = np.maximum(tin, 0); tout = np.minimum(tout, 1)
    hit = tout > tin
    idx = np.arange(len(r))
    f_in = np.clip(r + tin[:, None] * d - CELL, 0, 1)
    f_out = np.clip(r + tout[:, None] * d - CELL, 0, 1)
    hi_in = d[idx, ain] < 0          # moving -axis enters through the high plane
    hi_out = d[idx, aout] > 0
    o_in = texel(*face_uv(f_in, ain, hi_in))
    o_out = texel(*face_uv(f_out, aout, hi_out))
    n = o_in.astype(int) + o_out.astype(int)
    out = np.ones((5, len(r)))
    out[0] = np.where(hit, 1.0 - (o_in | o_out), 1.0)
    out[1] = np.where(hit, 1.0 - o_out, 1.0)
    out[2] = np.where(hit, TAU_PHYS ** n, 1.0)
    out[3] = np.where(hit, SHEET_G ** n, 1.0)
    L = (tout - tin) * dist
    a = shader_coverage(f_in); b = shader_coverage(f_out)
    faces = (1 - a + a * SHEET_G) * (1 - b + b * SHEET_G)
    out[4] = np.where(hit, np.exp(-INTERIOR * L) * faces ** np.minimum(1.0, 8.0 * L), 1.0)
    return out


# ---------------------------------------------------------------- emitter-disk sample sets
USUAL3 = np.array([(.66, 0.), (-.33, .57156), (-.33, -.57156)])
PHI = 2.39996323


def spiral(n, phase):
    k = np.arange(n)
    r = np.sqrt((k + .5) / n); a = k * PHI + phase
    return np.stack([r * np.cos(a), r * np.sin(a)], 1)


def build_sets(dense_n):
    sets = {'tap3': USUAL3}
    for n in (12, 24, 32):
        sets[f'uni{n}'] = spiral(n, .417)
        sets[f'mix{n}'] = np.concatenate([USUAL3, spiral(n - 3, .417)])
    sets['dense256'] = spiral(256, 1.2345)
    sets[f'dense{dense_n}'] = spiral(dense_n, 1.2345)
    return {k: v for k, v in sets.items()}


def disk_axes(r):
    l = normalize(LAMP - r)
    axis = np.where((np.abs(l[:, 1]) < .9)[:, None], np.array([0, 1., 0]), np.array([1., 0, 0]))
    u = normalize(np.cross(l, axis)) * RADIUS
    return u, np.cross(l, u)


_SETS = {}


def _work(r):
    u, v = disk_axes(r)
    uniq = {}
    members = {}
    for name, pts in _SETS.items():
        for p in pts:
            key = (round(float(p[0]), 9), round(float(p[1]), 9))
            uniq.setdefault(key, len(uniq))
            members.setdefault(key, []).append(name)
    acc = {name: np.zeros((len(MODELS), len(r))) for name in _SETS}
    for key, names in members.items():
        s = LAMP + u * key[0] + v * key[1]
        t = trace(r, s)
        for name in names:
            acc[name] += t
    return {name: acc[name] / len(pts) for name, pts in _SETS.items()}


def integrate(R, sets, chunk=1500, procs=22):
    global _SETS
    _SETS = sets
    parts = [R[i:i + chunk] for i in range(0, len(R), chunk)]
    with multiprocessing.get_context('fork').Pool(procs) as pool:
        res = pool.map(_work, parts)
    return {name: np.concatenate([p[name] for p in res], axis=1) for name in sets}


# ---------------------------------------------------------------- helpers: edges, predicted lines
def find_edges(s, T, rel=.2, sep=.012):
    g = np.abs(np.gradient(T, s))
    g = np.convolve(g, np.ones(3) / 3, 'same')
    gm = g.max()
    if gm <= 1e-6:
        return []
    cand = [i for i in range(1, len(g) - 1) if g[i] >= g[i - 1] and g[i] > g[i + 1] and g[i] >= rel * gm]
    kept = []
    for i in sorted(cand, key=lambda i: -g[i]):
        if all(abs(s[i] - s[j]) >= sep for j in kept):
            kept.append(i)
    return [(float(s[i]), float(g[i] / gm)) for i in sorted(kept)]


def predicted_lines(points, axis_name):
    """Silhouette lines of the cube's top (y=174) / left (x=202) edges cast by each tap, on the
    receiver plane, for the given disk taps. Front quad z=364, rear quad z=365."""
    r = np.array([[202.5, 174.2, WALL_Z - RECV_OFFSET]]) if axis_name == 'top' else \
        np.array([[201.8, LAMP[1], WALL_Z - RECV_OFFSET]])
    u, v = disk_axes(r)
    out = {}
    for tag, zp in (('front', CELL[2]), ('rear', CELL[2] + 1)):
        vals = []
        for du, dv in points:
            sp = LAMP + u[0] * du + v[0] * dv
            k = (r[0, 2] - sp[2]) / (zp - sp[2])
            if axis_name == 'top':
                vals.append(sp[1] + (CELL[1] + 1 - sp[1]) * k)
            else:
                vals.append(sp[0] + (CELL[0] - sp[0]) * k)
        out[tag] = sorted(set(round(float(x), 3) for x in vals))
    return out


def rmse(a, b, m):
    return float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))


# ---------------------------------------------------------------- plotting without matplotlib
COL = {'dense': (0, 0, 0), 'tap3': (220, 30, 30), 'uni12': (30, 100, 220), 'uni24': (20, 160, 90),
       'uni32': (150, 60, 200), 'mix32': (230, 140, 20), 'mix12': (120, 120, 120), 'mix24': (0, 170, 170),
       'obsStone': (150, 150, 150), 'obsDark': (190, 120, 120)}


def plot_panels(path, panels, size=(560, 300)):
    cols = 2
    rows = (len(panels) + 1) // 2
    img = Image.new('RGB', (cols * size[0], rows * size[1] + 30), 'white')
    dr = ImageDraw.Draw(img)
    x = 8; y = 6
    for name, c in COL.items():
        dr.line([(x, y + 5), (x + 18, y + 5)], fill=c, width=3); dr.text((x + 22, y), name, fill='black'); x += 80
    for k, (title, s, curves, marks, xlim) in enumerate(panels):
        ox = (k % cols) * size[0]; oy = (k // cols) * size[1] + 30
        l, t, r, b = ox + 44, oy + 22, ox + size[0] - 10, oy + size[1] - 26
        dr.rectangle([l, t, r, b], outline=(160, 160, 160)); dr.text((ox + 6, oy + 4), title, fill='black')
        lo, hi = xlim
        sel = (s >= lo) & (s <= hi); s = s[sel]; curves = {n: c[sel] for n, c in curves.items()}
        ymax = max(1.0, max(float(np.max(c)) for c in curves.values()))
        px = lambda v: l + (v - lo) / (hi - lo) * (r - l)
        py = lambda v: b - v / ymax * (b - t)
        for m, label in marks:
            if lo <= m <= hi:
                dr.line([(px(m), t), (px(m), b)], fill=(235, 200, 200) if label == 'front' else (200, 215, 240))
        for name, c in curves.items():
            dr.line([(px(a), py(v)) for a, v in zip(s, c)], fill=COL[name], width=2 if name == 'dense' else 1)
        for v in (0, .5, 1):
            dr.text((ox + 6, py(v) - 5), f'{v:.1f}', fill='gray')
        dr.text((l, b + 4), f'{lo:.2f}', fill='gray'); dr.text((r - 40, b + 4), f'{hi:.2f}', fill='gray')
    img.save(path)


def main():
    t_start = time.time()
    dense_n = 256 if QUICK else 1024
    sets = build_sets(dense_n)
    report = dict(
        pack='Aqualumen-1.8.0.zip (sha256 f3a53aa4..., the shader files match release/ byte for byte)',
        radius=RADIUS, denseTaps=dense_n, roiPixels=dict(x0=ROI[0], y0=ROI[1], x1=ROI[2], y1=ROI[3], note='x1,y1 exclusive'),
        constants=dict(spriteCoverage=float(SPRITE_A), spriteRGB=SPRITE_RGB.tolist(), assumedTint=TINT.tolist(),
                       shaderSheetRGB=SHEET.tolist(), shaderSheetGreen=SHEET_G, tauPhysGreenAssumed=TAU_PHYS,
                       opaqueTexels=int(OPAQUE.sum())))
    # ---- ROI image
    xx, yy = np.meshgrid(np.arange(ROI[0], ROI[2]), np.arange(ROI[1], ROI[3]))
    wall = pixel_to_wall(xx.astype(float), yy.astype(float))
    # camera ray must not cross the leaf cube, wall above floor (y>=173)
    d = wall - EYE
    safe = np.where(np.abs(d) < 1e-9, 1e-9, d)
    t0 = (CELL - EYE) / safe; t1 = (CELL + 1 - EYE) / safe
    cam_free = ~(np.minimum(np.maximum(t0, t1), 1).min(-1) > np.maximum(np.minimum(t0, t1), 0).max(-1))
    valid = cam_free & (wall[..., 1] >= 173.0)
    report['roiWorld'] = dict(xRange=[float(wall[..., 0].min()), float(wall[..., 0].max())],
                              yRange=[float(wall[..., 1].min()), float(wall[..., 1].max())], validPixels=int(valid.sum()),
                              totalPixels=int(valid.size))
    R = (wall - np.array([0, 0, RECV_OFFSET])).reshape(-1, 3)
    roi_sets = {k: v for k, v in sets.items() if k != 'dense256' or True}
    print('ROI', R.shape, 'taps', {k: len(v) for k, v in roi_sets.items()}, flush=True)
    est = integrate(R, roi_sets)
    est = {k: v.reshape(len(MODELS), *xx.shape) for k, v in est.items()}
    dense = f'dense{dense_n}'
    print('ROI done', time.time() - t_start, flush=True)
    np.savez_compressed(HERE / 'oracle-roi.npz', models=np.array(MODELS), roi=np.array(ROI), valid=valid,
                        **{f'{k}': v.astype(np.float32) for k, v in est.items()})
    stats = {}
    for mi, mname in enumerate(MODELS):
        stats[mname] = {}
        for name in est:
            if name == dense:
                continue
            e = est[name][mi] - est[dense][mi]
            stats[mname][name] = dict(rmse=rmse(est[name][mi], est[dense][mi], valid),
                                      maxAbs=float(np.abs(e[valid]).max()),
                                      p99Abs=float(np.quantile(np.abs(e[valid]), .99)))
        stats[mname]['dense_vs_dense256_rmse'] = rmse(est['dense256'][mi], est[dense][mi], valid)
    report['roiSamplingError'] = stats
    report['roiModelGap'] = {
        'shaderG_dense_vs_refG_sheet_dense_rmse': rmse(est[dense][4], est[dense][3], valid),
        'shaderG_dense_vs_refG_phys_dense_rmse': rmse(est[dense][4], est[dense][2], valid),
        'refG_sheet_dense_vs_refN_dense_rmse': rmse(est[dense][3], est[dense][0], valid)}
    # ---- profiles (strip averaged), top and left, over the whole wall beyond the shadow
    prof = {}
    panels = []
    for pname, axis in (('top', 'y'), ('left', 'x')):
        if pname == 'top':
            s = np.arange(173.60, 176.00 + 1e-9, .004); trans = np.linspace(-.30, .30, 13)
            pts = np.array([[202.5 + a, v, WALL_Z - RECV_OFFSET] for v in s for a in trans])
        else:
            s = np.arange(200.40, 202.50 + 1e-9, .004); trans = np.linspace(-.20, .20, 11)
            pts = np.array([[v, LAMP[1] + a, WALL_Z - RECV_OFFSET] for v in s for a in trans])
        pe = integrate(pts, sets, chunk=1000)
        P = {name: v.reshape(len(MODELS), len(s), len(trans)).mean(2) for name, v in pe.items()}
        prof[pname] = dict(s=s, P=P, strip=trans.tolist())
        pr = {}
        for mi, mname in enumerate(MODELS):
            pr[mname] = {}
            for name in P:
                pr[mname][name] = [dict(pos=round(p, 4), rel=round(h, 3)) for p, h in find_edges(s, P[name][mi])]
        lines = {name: predicted_lines(sets[name], pname) for name in ('tap3', 'uni12', 'mix32', dense)}
        report[f'profile_{pname}'] = dict(sWorld=[float(s[0]), float(s[-1])], stripOffsets=[float(trans[0]), float(trans[-1])],
                                          edges=pr, predictedSilhouetteLines=lines)
        # pixel position of the profile line, for the parent's real-image comparison
        if pname == 'top':
            px, py = wall_to_pixel(np.full_like(s, 202.5), s)
        else:
            px, py = wall_to_pixel(s, np.full_like(s, LAMP[1]))
        report[f'profile_{pname}']['pixelEnds'] = dict(start=[float(px[0]), float(py[0])], end=[float(px[-1]), float(py[-1])])
        marks = [(m, 'front') for m in lines['tap3']['front']] + [(m, 'rear') for m in lines['tap3']['rear']]
        for mname in ('refN', 'refG_sheet', 'shaderG'):
            mi = MODELS.index(mname)
            curves = {'dense': P[dense][mi], 'tap3': P['tap3'][mi], 'uni12': P['uni12'][mi], 'uni32': P['uni32'][mi],
                      'mix32': P['mix32'][mi]}
            panels.append((pname, mname, s, curves, marks))
    # ---- the plateau between the rear and front silhouette in the dense references
    plateau = {}
    for pname, (front, rear, outside, inside) in {'top': (174.29, 174.10, 174.50, 173.95), 'left': (201.60, 201.857, 201.35, 202.05)}.items():
        s = prof[pname]['s']; P = prof[pname]['P'][dense]
        def at(v, mi):
            return float(P[mi][np.argmin(np.abs(s - v))])
        plateau[pname] = {m: dict(outside=at(outside, i), betweenEdges=at((front + rear) / 2, i), inside=at(inside, i))
                          for i, m in enumerate(MODELS)}
    report['plateauBetweenEdgesDense'] = plateau
    # ---- ramp metrics: staircase (total variation excess) and step heights across silhouettes
    win = {'top': (174.00, 174.45), 'left': (201.45, 201.95)}
    ramp = {}
    for pname in ('top', 'left'):
        s = prof[pname]['s']; sel = (s >= win[pname][0]) & (s <= win[pname][1])
        ramp[pname] = {}
        for mi, mname in enumerate(MODELS):
            rows = {}
            dn = prof[pname]['P'][dense][mi][sel]
            tv_dense = np.abs(np.diff(dn)).sum()
            for name, P in prof[pname]['P'].items():
                c = P[mi][sel]
                rows[name] = dict(totalVariationOverDense=float(np.abs(np.diff(c)).sum() / max(tv_dense, 1e-9)),
                                  rmseVsDense=float(np.sqrt(np.mean((c - dn) ** 2))), maxAbsVsDense=float(np.abs(c - dn).max()))
            ramp[pname][mname] = rows
    report['rampMetrics'] = dict(windows=win, note='profiles are strip averaged; total variation over dense is 1 for the same monotone ramp',
                                 values=ramp)
    # step across each silhouette in the dense reference and in tap3: (outer level, inner level, jump)
    def lev(pname, mi, name, v):
        s = prof[pname]['s']; return float(prof[pname]['P'][name][mi][np.argmin(np.abs(s - v))])
    steps = {}
    # front ramp = [wall coordinate where the front quad begins, ends]; rear ramp analogous (dense disk extents)
    edges_ranges = {'top': {'front': (174.387, 174.182), 'rear': (174.136, 174.064)},
                    'left': {'front': (201.501, 201.708), 'rear': (201.897, 201.824)}}
    for pname in ('top', 'left'):
        steps[pname] = {}
        for mi, mname in enumerate(MODELS):
            steps[pname][mname] = {}
            for edge, (a, b) in edges_ranges[pname].items():
                for name in ('tap3', dense):
                    steps[pname][mname][f'{edge}.{name}'] = dict(outsideLevel=lev(pname, mi, name, a), insideLevel=lev(pname, mi, name, b),
                                                              jump=lev(pname, mi, name, a) - lev(pname, mi, name, b))
    report['silhouetteSteps'] = dict(note='level just outside / inside the dense-disk penumbra extent of each silhouette; '
                                          'front = z=364 quad edge, rear = z=365 quad edge', values=steps)
    # ---- observed screenshots and normalization limits
    pics = {n: np.asarray(Image.open(ACC / f'{n}.png').convert('RGB')).astype(float) for n in ('open', 'foliage', 'stone', 'dark', 'again')}
    sl = (slice(ROI[1], ROI[3]), slice(ROI[0], ROI[2]))
    o, f, st, dk, ag = (pics[n][sl] for n in ('open', 'foliage', 'stone', 'dark', 'again'))
    norm = {}
    for tag, base in (('stone', st), ('dark', dk)):
        den = o - base
        ok = valid & (den[..., 1] > 12)
        norm[tag] = dict(usablePixels=int(ok.sum()), medianContrastGreen=float(np.median(den[..., 1][ok])),
                         p10ContrastGreen=float(np.quantile(den[..., 1][ok], .1)),
                         quantizationHalfStepOverMedianContrast=float(.5 / np.median(den[..., 1][ok])),
                         repeatFrameMedianAbsDiffGreen=float(np.median(np.abs(ag - f)[..., 1][ok])))
    both = valid & ((o - dk)[..., 1] > 12)
    norm['stoneMinusDarkGreenOnLampLitWall'] = dict(median=float(np.median((st - dk)[..., 1][both])),
                                                    p10=float(np.quantile((st - dk)[..., 1][both], .1)),
                                                    p90=float(np.quantile((st - dk)[..., 1][both], .9)),
                                                    openMinusDarkMedian=float(np.median((o - dk)[..., 1][both])))
    umbra = valid & (est[dense][0] < .35) & ((o - dk)[..., 1] > 12)
    norm['umbraOnly'] = dict(pixels=int(umbra.sum()),
                             stoneMinusDarkMedianRGB=np.median((st - dk)[umbra], axis=0).tolist(),
                             stoneMinusDarkP10P90Green=[float(np.quantile((st - dk)[..., 1][umbra], .1)), float(np.quantile((st - dk)[..., 1][umbra], .9))],
                             foliageMinusDarkMedianGreen=float(np.median((f - dk)[..., 1][umbra])),
                             openMinusDarkMedianGreen=float(np.median((o - dk)[..., 1][umbra])),
                             openMinusStoneMedianGreen=float(np.median((o - st)[..., 1][umbra])),
                             note='umbra = dense refN < 0.35. Where the lamp is blocked, stone should equal dark if the baseline were purely ambient')
    obsA = np.clip((f[..., 1] - st[..., 1]) / np.maximum(o[..., 1] - st[..., 1], 1), -.5, 1.5)
    obsB = np.clip((f[..., 1] - dk[..., 1]) / np.maximum(o[..., 1] - dk[..., 1], 1), -.5, 1.5)
    use = valid & ((o - st)[..., 1] > 12) & ((o - dk)[..., 1] > 12)
    corr = {}
    for obs_name, obs in (('obs_stone_norm', obsA), ('obs_dark_norm', obsB)):
        for mi, mname in enumerate(MODELS):
            for tag, tf in (('T', lambda x: x), ('T^(1/2.2)', lambda x: np.power(x, 1 / 2.2))):
                corr[f'{obs_name}~{mname}.{dense}.{tag}'] = float(np.corrcoef(obs[use], tf(est[dense][mi][use]))[0, 1])
        corr[f'{obs_name}~shaderG.tap3.T'] = float(np.corrcoef(obs[use], est['tap3'][4][use])[0, 1])
    norm['pixelsUsedForCorrelation'] = int(use.sum())
    norm['correlationObservedVsOracle'] = corr
    report['normalization'] = norm
    # ---- does the real screenshot carry the 3-tap comb? residual correlation inside the edge bands
    wx, wy = wall[..., 0], wall[..., 1]
    bands = {'top': valid & (wy >= 174.05) & (wy <= 174.45) & (wx >= 201.9) & (wx <= 203.0),
             'left': valid & (wx >= 201.45) & (wx <= 201.95) & (wy >= 173.1) & (wy <= 174.1)}
    comb = {}
    for bname, bm in bands.items():
        bm = bm & ((o - dk)[..., 1] > 12)
        comb[bname] = dict(pixels=int(bm.sum()))
        for mname in ('shaderG', 'refG_sheet', 'refN'):
            mi = MODELS.index(mname)
            dn = est[dense][mi][bm]
            slope = np.polyfit(dn, obsB[bm], 1)
            resid = obsB[bm] - np.polyval(slope, dn)
            comb[bname][mname] = {k: float(np.corrcoef(resid, est[k][mi][bm] - dn)[0, 1])
                                  for k in ('tap3', 'uni12', 'uni32', 'mix32')}
            comb[bname][mname]['fitSlope'] = float(slope[0])
            comb[bname][mname]['residualStdDisplayRatio'] = float(resid.std())
    report['observedCombResidualCorrelation'] = dict(
        note='obs=(foliage-dark)/(open-dark) green; residual after linear fit to the dense oracle inside each edge band, '
             'correlated with (estimator - dense). A positive tap3 value with ~0 control (uni32) means the screenshot '
             'carries the 3-tap pattern. Display space; not radiance.', bands={k: dict(zip(('xMin', 'xMax', 'yMin', 'yMax'), v)) for k, v in
             {'top': (201.9, 203.0, 174.05, 174.45), 'left': (201.45, 201.95, 173.1, 174.1)}.items()}, values=comb)
    # observed profiles on the same strips
    for pname in ('top', 'left'):
        s = prof[pname]['s']; tr = np.array(prof[pname]['strip'])
        if pname == 'top':
            X = (202.5 + tr)[None, :].repeat(len(s), 0); Y = s[:, None].repeat(len(tr), 1)
        else:
            X = s[:, None].repeat(len(tr), 1); Y = (LAMP[1] + tr)[None, :].repeat(len(s), 0)
        px, py = wall_to_pixel(X.ravel(), Y.ravel())
        def sample(img):
            x0 = np.clip(np.floor(px).astype(int), 0, W - 2); y0 = np.clip(np.floor(py).astype(int), 0, H - 2)
            tx = px - x0; ty = py - y0
            v = (1 - ty) * ((1 - tx) * img[y0, x0] + tx * img[y0, x0 + 1]) + ty * ((1 - tx) * img[y0 + 1, x0] + tx * img[y0 + 1, x0 + 1])
            return v.reshape(len(s), len(tr)).mean(1)
        full = {n: pics[n][..., 1] for n in ('open', 'foliage', 'stone', 'dark')}
        sm = {n: sample(v) for n, v in full.items()}
        A = (sm['foliage'] - sm['stone']) / np.maximum(sm['open'] - sm['stone'], 1)
        B = (sm['foliage'] - sm['dark']) / np.maximum(sm['open'] - sm['dark'], 1)
        report[f'profile_{pname}']['observed'] = dict(
            stoneNormEdges=[dict(pos=round(p, 4), rel=round(h, 3)) for p, h in find_edges(s, np.convolve(A, np.ones(5) / 5, 'same'))],
            darkNormEdges=[dict(pos=round(p, 4), rel=round(h, 3)) for p, h in find_edges(s, np.convolve(B, np.ones(5) / 5, 'same'))],
            note='green display channel, strip-averaged, 5-sample smoothing; display-space ratio, not radiance')
        prof[pname]['obsA'] = A; prof[pname]['obsB'] = B
    # ---- profile plots (zoomed to the silhouettes; observed display ratios overlaid on the shaderG panels)
    zoom = {'top': (173.95, 174.50), 'left': (201.40, 202.00)}
    plist = {}
    for pname, mname, s, curves, marks in panels:
        curves = dict(curves)
        if mname == 'shaderG':
            curves['obsStone'] = prof[pname]['obsA']; curves['obsDark'] = prof[pname]['obsB']
        plist[(pname, mname)] = (f'{pname} edge, {mname}: wall {"y" if pname == "top" else "x"} [m]', s, curves, marks, zoom[pname])
    plot_panels(HERE / 'oracle-profiles.png', [plist[(a, b)] for b in ('refN', 'refG_sheet', 'shaderG') for a in ('top', 'left')])
    # ---- image panels
    def tile(a, scale=2, gamma=1.0):
        im = Image.fromarray((np.clip(a, 0, 1) ** gamma * 255 + .5).astype(np.uint8))
        return im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    names = [('refN dense', est[dense][0]), ('refG_sheet dense', est[dense][3]), ('shaderG dense', est[dense][4]),
             ('shaderG tap3 (current)', est['tap3'][4]), ('shaderG uni12', est['uni12'][4]), ('shaderG uni32', est['uni32'][4]),
             ('shaderG mix32', est['mix32'][4]), ('refN tap3', est['tap3'][0])]
    tiles = [(n, tile(a)) for n, a in names]
    tiles.append(('error shaderG tap3-dense x4', tile(np.abs(est['tap3'][4] - est[dense][4]) * 4)))
    tiles.append(('error shaderG uni32-dense x4', tile(np.abs(est['uni32'][4] - est[dense][4]) * 4)))
    tiles.append(('error shaderG mix32-dense x4', tile(np.abs(est['mix32'][4] - est[dense][4]) * 4)))
    obs_img = Image.fromarray(np.clip(pics['foliage'][sl], 0, 255).astype(np.uint8)).resize((xx.shape[1] * 2, xx.shape[0] * 2), Image.NEAREST)
    tiles.append(('real foliage.png ROI', obs_img))
    tiles.append(('real (foliage-stone)/(open-stone) G', tile(np.clip(obsA, 0, 1))))
    tiles.append(('real (foliage-dark)/(open-dark) G', tile(np.clip(obsB, 0, 1))))
    tw, th = tiles[0][1].size
    cols = 3; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 16)), 'white'); dr = ImageDraw.Draw(sheet)
    for k, (n, im) in enumerate(tiles):
        x = (k % cols) * tw; y = (k // cols) * (th + 16)
        sheet.paste(im.convert('RGB'), (x, y + 16)); dr.text((x + 4, y + 2), n, fill='black')
    sheet.save(HERE / 'oracle-roi.png')
    report['runtimeSeconds'] = time.time() - t_start
    (HERE / 'oracle-result.json').write_text(json.dumps(report, indent=1))
    print('done', report['runtimeSeconds'])


if __name__ == '__main__':
    main()
