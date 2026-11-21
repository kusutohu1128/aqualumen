#!/usr/bin/env python3 -I
"""Ask the genuine vanilla 1.21.1 server (in-game BiomeManager, i.e. per-block biome) which biome each
block column of a straight transect belongs to, from the chosen house door to the nearest rain column.

usage: transect_probe.py WORLD_DIR ANALYSIS_JSON OUT_JSON [CPUS]
`execute if biome` is the same per-block lookup Level.getBiome(pos) that Biome.getPrecipitationAt uses
and the client's Iris `biome_precipitation` uniform reads for the player's block.
"""
import json, math, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vserver

world, ana_p, out_p = sys.argv[1:4]
cpus = sys.argv[4] if len(sys.argv) > 4 else '4-7'
ana = json.load(open(ana_p)); gen = ana['gen']; H = ana['chosen_house']
jar = zipfile.ZipFile(vserver.CLIENT_JAR)
def info(b): return json.loads(jar.read(f"data/minecraft/worldgen/biome/{b}.json"))
sx, sy, sz = H['door_lower']['xyz']
ex, ez = H['nearest_rain_column']['xz']; ey = H['nearest_rain_column']['y']
Y = sy  # door height; all sites are below y=80 (checked in analysis)
length = math.hypot(ex - sx, ez - sz)
n = int(math.ceil(length))
EXT = 24  # continue past the first rain column so the rain side is shown to persist
tmax = 1 + EXT / length
pts = []
for i in range(int(n * tmax) + 1):
    t = i / n
    p = (int(round(sx + (ex - sx) * t)), int(round(sz + (ez - sz) * t)))
    if not pts or pts[-1] != p: pts.append(p)
cand = sorted({b.split(':')[1] for b in ana['survey']['biome_counts']})
s = vserver.Server(world, gen['seed'], cpus=cpus, reuse=True)
try:
    # `execute if biome` is false for unloaded positions. gen_site.py force-loaded the whole rectangle
    # (persisted in the world), so the server reloads these chunks at start; wait until they are.
    import time
    for _ in range(60):
        s.p.stdin.write(f'execute if loaded {sx} {Y} {sz} if loaded {ex} {Y} {ez} run say QRYLOADED\n'); s.p.stdin.flush()
        try: s.wait(r'QRYLOADED', 3); break
        except TimeoutError: time.sleep(1)
    else: raise TimeoutError('chunks never loaded')
    for (x, z) in pts:
        for b in cand:
            for yq in (Y, ey):
                s.p.stdin.write(f'execute if biome {x} {yq} {z} minecraft:{b} run say QRY:{yq}:{b}:{x}:{z}\n')
    s.p.stdin.write('say QRYEND\n'); s.p.stdin.flush()
    got = {}
    rx = re.compile(r'QRY:(-?\d+):(\w+):(-?\d+):(-?\d+)')
    while True:
        try: line = s.q.get(timeout=120)
        except Exception: raise TimeoutError('transect queries')
        if line is None: raise RuntimeError('server died')
        if 'QRYEND' in line: break
        m = rx.search(line)
        if m: got.setdefault((int(m[3]), int(m[4])), {}).setdefault(int(m[1]), []).append(m[2])
finally:
    code = s.stop()
rows = []
for (x, z) in pts:
    per_y = got.get((x, z), {})
    ok = all(len(v) == 1 for v in per_y.values()) and len(per_y) == 2 and len({v[0] for v in per_y.values()}) == 1
    bs = [per_y[Y][0]] if ok else []
    b = bs[0] if ok else None
    cls = None
    if b:
        d = info(b)
        cls = 'none' if not d['has_precipitation'] else ('snow' if d['temperature'] < 0.15 else 'rain')
    rows.append({'x': x, 'z': z, 'biome': b, 'precip': cls, 'matches': len(bs), 'by_y': {str(k): v for k, v in per_y.items()}})
seq = [r['precip'] for r in rows]
changes = [i for i in range(1, len(seq)) if seq[i] != seq[i - 1]]
res = {'y_queried': [Y, ey], 'extension_past_nearest_rain_column_blocks': EXT, 'start': [sx, sy, sz], 'end': [ex, ey, ez], 'columns': len(rows), 'server_exit': code,
       'biomes_tested': cand, 'class_changes': len(changes), 'change_indices': changes,
       'all_columns_resolved': all(r['matches'] == 1 for r in rows),
       'transition': [rows[changes[0] - 1], rows[changes[0]]] if changes else None,
       'rows': rows}
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
