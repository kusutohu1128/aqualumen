"""Original 32 px base art for birch logs, stone and gold ore.

Everything is drawn procedurally from hand-tuned palettes and stamps; no vanilla
or third-party pixels are read.
"""
from io import BytesIO
import json, math, random, zipfile
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
S = 32


def rgb(h):
    return tuple(bytes.fromhex(h))


class Canvas:
    def __init__(self, fill):
        self.im = Image.new('RGB', (S, S), fill)

    def put(self, x, y, c):
        self.im.putpixel((x % S, y % S), c)

    def get(self, x, y):
        return self.im.getpixel((x % S, y % S))

    def stamp(self, x0, y0, rows, ink):
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in ink:
                    self.put(x0 + dx, y0 + dy, ink[ch])


# Mean linear albedo of the vanilla 1.21.1 textures these replace. Aqualumen's
# bounce capture, water-bed reflection and exposure were tuned against these
# averages, so each new texture is matched to them per channel.
VANILLA_MEAN = {
    'birch_log': (.751, .741, .714),
    'birch_log_top': (.567, .484, .279),
    'stone': (.212, .212, .212),
    'gold_ore': (.324, .261, .178),
}


def linear_mean(images):
    px = [p for im in images for p in im.convert('RGB').getdata()]
    return tuple(sum((p[c] / 255) ** 2.2 for p in px) / len(px) for c in range(3))


def calibrate(images, target):
    """Per-channel linear gain so the combined mean equals target. Returns gains."""
    gain = [t / m for t, m in zip(target, linear_mean(images))]
    luts = [[min(255, round(255 * min(1, (v / 255) ** 2.2 * g) ** (1 / 2.2))) for v in range(256)] for g in gain]
    for im in images:
        im.putdata([tuple(luts[c][p[c]] for c in range(3)) for p in im.getdata()])
    return gain


def periodic(rng, n, terms):
    """1-D noise with integer periods so it tiles over n samples."""
    waves = [(k, rng.uniform(0, 2 * math.pi), rng.uniform(.5, 1) / k) for k in terms]
    return [sum(a * math.sin(2 * math.pi * k * i / n + p) for k, p, a in waves) for i in range(n)]


# ---------------------------------------------------------------- birch bark
# Warm chalk lights, slightly cool greys, near-black lenticels with a brown cast.
BARK = dict(
    h=rgb('eeebe1'), b=rgb('e1ded3'), m=rgb('d3d1c6'), s=rgb('c2c1b8'),
    l=rgb('a8a69e'), d1=rgb('7d7870'), d2=rgb('4f4a45'), d3=rgb('2f2c2a'),
    w=rgb('d8c9b5'),
)
INK = {'h': BARK['h'], 'b': BARK['b'], 'm': BARK['m'], 's': BARK['s'], 'l': BARK['l'],
       '1': BARK['d1'], '2': BARK['d2'], '3': BARK['d3'], 'w': BARK['w'], 'f': BARK['l']}


def bark_background():
    """Shared by every side variant, so stacked logs never show a seam."""
    rng = random.Random(4412)
    c = Canvas(BARK['b'])
    rows = periodic(rng, S, (1, 2, 3, 5))
    for y in range(S):
        x = rng.randrange(S)
        covered = 0
        while covered < S:
            run = rng.randint(2, 9)
            v = .45 * rows[y] + rng.uniform(-1, 1)
            tone = 's' if v < -1.2 else 'm' if v < -.78 else 'h' if v > .74 else 'b'
            for k in range(run):
                c.put(x + covered + k, y, BARK[tone])
            covered += run
    # Paper lips: a bright lifted edge with a soft shadow underneath.
    for x, y, n in [(3, 1, 9), (19, 4, 6), (25, 9, 10), (8, 12, 5), (14, 17, 11),
                    (29, 21, 7), (1, 25, 8), (17, 28, 6), (10, 7, 4), (23, 14, 3)]:
        for k in range(n):
            c.put(x + k, y, BARK['h'])
        for k in range(1, n - 1):
            c.put(x + k, y + 1, BARK['s'] if k in (1, n - 2) else BARK['l'])
    return c


def lenticel(c, x, y, n, depth=2):
    """Horizontal breathing pore: dark core, softer ends, catch-light below."""
    core = {1: '1', 2: '2', 3: '3'}[depth]
    for k in range(n):
        end = k in (0, n - 1)
        c.put(x + k, y, INK['1'] if end and n > 2 else INK[core if n > 3 and k in range(n // 2 - 1, n // 2 + 1) else str(max(1, depth - 1))])
    for k in range(1, n - 1):
        c.put(x + k, y - 1, BARK['s'])
    for k in range(n):
        c.put(x + k, y + 1, BARK['h'])


# Bark marks. Rows are drawn top to bottom; '.' keeps the background.
# Bold marks are deliberately asymmetric so they never read as faces.
SCARS = {
    'slash': [
        '..s1121s....',
        's12333321s1.',
        '.h112333321s',
        '...hhh1121h.',
    ],
    'blot': [
        '.s11s.....',
        's12332ss..',
        '1233332211',
        '.hh11hhh..',
    ],
    'scar': [
        '......s11s.....',
        '...s1233221s...',
        '.s1221...s1231s',
        's11h.......h11.',
        '.h...........h.',
    ],
    'fork': [
        '....s11.',
        's11233s.',
        '.h12332s',
        '..hh1h1.',
    ],
    'curl': [
        '.hhhh..',
        'hwwwfh.',
        '.ffff..',
    ],
}


def faint(c, x, y, n):
    for k in range(n):
        c.put(x + k, y, BARK['l'] if k in (0, n - 1) else BARK['d1'])


def bark_side(variant):
    c = bark_background()
    layout = {
        0: dict(scars=[('slash', 6, 7), ('fork', 22, 21)],
                pores=[(25, 4, 5, 2), (3, 16, 4, 2), (14, 26, 3, 2)],
                faint=[(17, 13, 3), (28, 15, 2), (1, 23, 3), (9, 2, 2), (26, 29, 4), (20, 9, 2)]),
        1: dict(scars=[('blot', 18, 3), ('curl', 4, 19)],
                pores=[(4, 9, 6, 3), (24, 15, 3, 2), (12, 27, 5, 2), (27, 25, 2, 2)],
                faint=[(14, 13, 2), (1, 2, 3), (20, 21, 3), (8, 15, 2), (29, 9, 2), (3, 29, 2)]),
        2: dict(scars=[('scar', 9, 17)],
                pores=[(2, 5, 4, 2), (21, 3, 6, 3), (14, 10, 3, 2), (28, 12, 2, 2), (3, 28, 3, 2)],
                faint=[(9, 3, 2), (24, 8, 3), (1, 13, 2), (28, 24, 3), (18, 28, 2), (6, 24, 2)]),
    }[variant]
    for x, y, n in layout['faint']:
        faint(c, x, y, n)
    for x, y, n, d in layout['pores']:
        lenticel(c, x, y, n, d)
    for name, x, y in layout['scars']:
        rows = SCARS[name]
        assert 1 <= y and y + len(rows) <= S - 1, (variant, name)
        c.stamp(x, y, rows, INK)
    return c.im


WOOD = [rgb('e2d5ae'), rgb('d5c59a'), rgb('c6b184'), rgb('ad976b'), rgb('8b7752')]


def bark_top():
    rng = random.Random(77)
    c = Canvas(WOOD[0])
    cx, cy = 15.6, 16.3
    wobble = periodic(rng, 64, (2, 3, 5))
    for y in range(S):
        for x in range(S):
            dx, dy = x + .5 - cx, y + .5 - cy
            a = math.atan2(dy, dx)
            r = (abs(dx) ** 3 + abs(dy) ** 3) ** (1 / 3)  # squircle rings follow the square log
            r += .45 * wobble[int((a + math.pi) / (2 * math.pi) * 64) % 64]
            ring = (r + .2) % 3.1
            tone = 2 if ring < .9 else 1 if ring < 1.7 else 0
            if r < 1.1:
                tone = 3
            c.put(x, y, WOOD[tone])
    # Cambium line and bark rim.
    for i in range(S):
        for x, y in [(i, 2), (i, S - 3), (2, i), (S - 3, i)]:
            if 2 <= x <= S - 3 and 2 <= y <= S - 3:
                c.put(x, y, WOOD[4])
    edge = bark_side(0)
    for i in range(S):
        for d in (0, 1):
            for x, y in [(i, d), (i, S - 1 - d), (d, i), (S - 1 - d, i)]:
                c.put(x, y, edge.getpixel((i, (5 + d * 7) % S)) if d == 0 else BARK['s'])
    for x, y, n in [(6, 0, 3), (21, S - 1, 2), (0, 11, 2), (S - 1, 23, 3)]:
        for k in range(n):
            if y in (0, S - 1):
                c.put(x + k, y, BARK['d2'] if k else BARK['d1'])
            else:
                c.put(x, y + k, BARK['d2'] if k else BARK['d1'])
    return c.im


# ----------------------------------------------------------- stone and gold
STONE = [rgb(h) for h in ('5f5f60', '6c6c6d', '777878', '808181', '898a89', '939392', '9e9e9c')]


def stone_base():
    """Low-contrast cellular stone: flat clumps, light top-left lips, faint seams."""
    rng = random.Random(9031)
    pts = []
    for gy in range(6):
        for gx in range(6):
            pts.append(((gx + rng.uniform(.15, .85)) * S / 6, (gy + rng.uniform(.15, .85)) * S / 6,
                        rng.choice((2, 3, 3, 3, 4, 4, 5))))
    rows = periodic(rng, S, (1, 2, 3))
    cols = periodic(rng, S, (1, 2))
    c = Canvas(STONE[3])
    warp = {(x, y): rng.random() for x in range(S) for y in range(S)}
    for y in range(S):
        for x in range(S):
            best = []
            for px, py, tone in pts:
                dx = (x + .5 - px + S / 2) % S - S / 2
                dy = (y + .5 - py + S / 2) % S - S / 2
                best.append((math.hypot(dx, dy * 1.25) + .9 * warp[(x, y)], dx, dy, tone))
            best.sort()
            d1, dx, dy, tone = best[0]
            seam = best[1][0] - d1
            t = tone + (rows[y] + cols[x]) * .55
            if seam < .45 and (x * 7 + y * 3) % 5 < 3:
                t -= .8
            elif dx < -1.2 and dy < -.9 and seam > 1.2:
                t += .35  # faint upper lip only; the shader supplies light direction
            elif dx > 1.4 and dy > .8:
                t -= .3
            t += rng.uniform(-.3, .3)
            c.put(x, y, STONE[max(0, min(6, round(t)))])
    return c


GOLD = [rgb(h) for h in ('5a3c12', '8a5e1a', 'b47f22', 'd4a031', 'e8c04a', 'f6dc80', 'fff3c0')]
QUARTZ = [rgb('aaa69e'), rgb('bdb9b0')]

# Each nugget is a small irregular mound: (centre x, centre y, radius x, radius y, lumps).
NUGGETS = [
    (7.0, 7.0, 4.2, 2.9, 4), (24.5, 16.0, 3.8, 3.3, 4), (19.5, 4.5, 2.5, 1.9, 2),
    (13.5, 17.0, 2.7, 2.1, 3), (6.0, 24.0, 3.0, 2.3, 3), (19.0, 26.5, 2.1, 1.7, 2),
    (29.5, 27.5, 1.3, 1.0, 1), (11.0, 29.0, 1.2, 0.9, 1), (11.5, 11.5, 1.0, 0.9, 1),
]
LIGHT = (-.45, -.6, .66)


def gold_ore():
    rng = random.Random(2203)
    stone = stone_base()
    stone_gain = calibrate([stone.im], VANILLA_MEAN['stone'])
    ore = stone.im.copy()
    height = {}
    grit = {(x, y): rng.random() for x in range(S) for y in range(S)}
    for cx, cy, rx, ry, lumps in NUGGETS:
        rx, ry = rx * 1.12, ry * 1.12
        blobs = [(cx, cy, rx, ry)] + [(cx + rng.uniform(-rx, rx) * .6, cy + rng.uniform(-ry, ry) * .6,
                                       rx * rng.uniform(.45, .7), ry * rng.uniform(.45, .7)) for _ in range(lumps - 1)]
        for y in range(int(cy - ry - 2), int(cy + ry + 3)):
            for x in range(int(cx - rx - 2), int(cx + rx + 3)):
                h = 0.0
                for bx, by, brx, bry in blobs:
                    q = ((x + .5 - bx) / brx) ** 2 + ((y + .5 - by) / bry) ** 2
                    h = max(h, 1 - q)
                h -= .32 * grit[(x % S, y % S)]
                if h > .1:
                    p = (x % S, y % S)
                    height[p] = max(height.get(p, 0), h)
    # Quartz vein connecting a few grains, drawn first so gold sits on top.
    for t in range(60):
        x = 4 + t * .42
        y = 25 - t * .33 + 1.2 * math.sin(t * .35)
        p = (int(x) % S, int(y) % S)
        if p not in height and rng.random() < .8:
            ore.putpixel(p, QUARTZ[t % 3 == 0])
    norm = Image.new('RGBA', (S, S), (128, 128, 255, 255))
    spec = Image.new('RGBA', (S, S), (40, 10, 0, 255))
    H = lambda x, y: height.get((x % S, y % S), 0)
    for (x, y), h in height.items():
        gx = (H(x + 1, y) - H(x - 1, y)) * 1.6
        gy = (H(x, y + 1) - H(x, y - 1)) * 1.6
        n = (-gx, -gy, 1)
        ln = math.sqrt(sum(v * v for v in n))
        n = tuple(v / ln for v in n)
        lit = sum(a * b for a, b in zip(n, LIGHT))
        # Mostly height-driven so the grain reads under any lamp direction.
        tone = 3.0 + h * 2.2 + (lit - .66) * 1.2
        ore.putpixel((x, y), GOLD[max(1, min(5, round(tone)))])
        norm.putpixel((x, y), (round((n[0] + 1) * 127.5), round((n[1] + 1) * 127.5), 255, 255))
        spec.putpixel((x, y), (round(196 + 22 * h), 231, 0, 255))
    # One hot glint per large nugget, and contact shadows in the rock below-right.
    # Embedding seam: rock directly touching a grain is darkened on every side.
    rim = {((x + dx) % S, (y + dy) % S) for (x, y) in height for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - set(height)
    for p in rim:
        c = ore.getpixel(p)
        if c not in QUARTZ:
            ore.putpixel(p, tuple(round(v * .84) for v in c))
    return stone.im, ore, norm, spec, height, stone_gain


# --------------------------------------------------------------- packaging
def png(img):
    b = BytesIO(); img.save(b, 'PNG', optimize=True); return b.getvalue()


def write_zip(path, files):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data if isinstance(data, bytes) else json.dumps(data, indent=1).encode())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None


def main():
    out = HERE / 'textures'; out.mkdir(exist_ok=True)
    tex = 'assets/minecraft/textures/block/'
    sides = [bark_side(i) for i in range(3)]
    top = bark_top()
    gains = {'birch_log': calibrate(sides, VANILLA_MEAN['birch_log']),
             'birch_log_top': calibrate([top], VANILLA_MEAN['birch_log_top'])}
    for i, im in enumerate(sides):
        im.save(out / f'birch_side_{i}.png')
    top.save(out / 'birch_top.png')
    models, files = {}, {'pack.mcmeta': {'pack': {'pack_format': 34, 'description': 'Aqualumen | Birch bark base, original 32x'}}}
    names = ['birch_log', 'aql_birch_log_1', 'aql_birch_log_2']
    for name, im in zip(names, sides):
        files[tex + name + '.png'] = png(im)
        if name != 'birch_log':
            for kind, parent in (('', 'cube_column'), ('_horizontal', 'cube_column_horizontal')):
                files[f'assets/minecraft/models/block/{name}{kind}.json'] = {
                    'parent': f'minecraft:block/{parent}',
                    'textures': {'end': 'minecraft:block/birch_log_top', 'side': f'minecraft:block/{name}'}}
    files[tex + 'birch_log_top.png'] = png(top)
    weights = (5, 3, 3)
    variants = {}
    for axis, rot, kind in (('y', {}, ''), ('z', {'x': 90}, '_horizontal'), ('x', {'x': 90, 'y': 90}, '_horizontal')):
        variants[f'axis={axis}'] = [dict(model=f'minecraft:block/{n}{kind}', weight=w, **rot) for n, w in zip(names, weights)]
    files['assets/minecraft/blockstates/birch_log.json'] = {'variants': variants}
    write_zip(HERE / 'Aqualumen-Birch-Base-32x.zip', files)

    stone, ore, norm, spec, height, gains['stone'] = gold_ore()
    stone.save(out / 'stone.png'); ore.save(out / 'gold_ore.png'); norm.save(out / 'gold_ore_n.png'); spec.save(out / 'gold_ore_s.png')
    for variant in ('Faceted', 'Control'):
        maps = {'stone.png': stone, 'gold_ore.png': ore, 'gold_ore_n.png': norm, 'gold_ore_s.png': spec}
        if variant == 'Control':
            maps['gold_ore_n.png'] = Image.new('RGBA', (S, S), (128, 128, 255, 255))
            maps['gold_ore_s.png'] = Image.new('RGBA', (S, S), (35, 0, 0, 255))
        files = {'pack.mcmeta': {'pack': {'pack_format': 34, 'description': f'Aqualumen | {variant} gold ore + stone base, original 32x'}}}
        files.update({tex + k: png(v) for k, v in maps.items()})
        write_zip(HERE / f'Aqualumen-Gold-Base-{variant}-32x.zip', files)
    assert sum(p[1] == 231 for p in spec.getdata()) == len(height)
    report = {}
    for key, ims in (('birch_log', sides), ('birch_log_top', [top]), ('stone', [stone]), ('gold_ore', [ore])):
        m = linear_mean(ims)
        report[key] = dict(mean=[round(v, 4) for v in m], vanilla=VANILLA_MEAN[key],
                           relY=round((.2126 * m[0] + .7152 * m[1] + .0722 * m[2]) /
                                      (.2126 * VANILLA_MEAN[key][0] + .7152 * VANILLA_MEAN[key][1] + .0722 * VANILLA_MEAN[key][2]), 4),
                           gain=[round(g, 4) for g in gains[key]] if key in gains else None)
    (HERE / 'calibration.json').write_text(json.dumps(report, indent=1) + '\n')
    for k, v in report.items():
        print(k, v)
    print('birch variants', len(sides), '| gold pixels', len(height))


if __name__ == '__main__':
    main()
