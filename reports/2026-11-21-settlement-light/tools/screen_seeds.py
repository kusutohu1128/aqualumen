#!/usr/bin/env python3 -I
"""Pre-registered seed screen using genuine vanilla 1.21.1 /locate (CPU only, loopback, fresh /tmp dirs).

Procedure (fixed before running): seeds START, START+1, ... ; for each, fresh server, then
  1. /locate structure minecraft:village_snowy  (must be found, <= MAXDIST blocks from 0,0)
  2. from that village: /execute positioned X 70 Z run /locate biome <b> for rain biomes
     (has_precipitation=true, base temperature >= 0.15, i.e. rain not snow at sea level)
Accept the first seed whose nearest rain biome is <= RAINDIST blocks from the village centre.
"""
import json, os, re, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vserver

START, N, MAXDIST, RAINDIST = int(sys.argv[1]), int(sys.argv[2]), 1500, 260
RAIN = ['taiga', 'forest', 'plains', 'birch_forest', 'flower_forest', 'old_growth_pine_taiga',
        'old_growth_spruce_taiga', 'meadow', 'sunflower_plains', 'dark_forest']
OK = re.compile(r'The nearest \S+ is at \[(-?\d+), [^,\]]+, (-?\d+)\] \((\d+) blocks away\)')
ANY = r'The nearest \S+ is at .*blocks away\)|Could not find|Unable to|not find'

def locate(s, c):
    s.cmd(c, ANY, 240)
    # the matched line is in s.log tail
    for line in reversed(s.log[-8:]):
        m = OK.search(line)
        if m: return int(m[1]), int(m[2]), int(m[3])
        if 'Could not find' in line or 'not find' in line: return None
    return None

results = []
for seed in range(START, START + N):
    d = tempfile.mkdtemp(prefix=f'aql-settlement-screen-{seed}-', dir='/tmp')
    t0 = time.time(); rec = {'seed': seed}
    s = vserver.Server(d, seed)
    try:
        v = locate(s, 'locate structure minecraft:village_snowy')
        rec['village'] = v
        if v and v[2] <= MAXDIST:
            rec['rain'] = {}
            for b in RAIN:
                r = locate(s, f'execute positioned {v[0]} 70 {v[1]} run locate biome minecraft:{b}')
                rec['rain'][b] = r
            best = min((x[2] for x in rec['rain'].values() if x), default=None)
            rec['nearest_rain_biome_blocks'] = best
            rec['accepted'] = best is not None and best <= RAINDIST
    finally:
        rec['exit'] = s.stop(); rec['seconds'] = round(time.time() - t0, 1)
    print(json.dumps(rec), flush=True); results.append(rec)
    if rec.get('accepted'):
        print('ACCEPT', seed, d, flush=True); break
    shutil.rmtree(d)
