#!/usr/bin/env python3 -I
"""One storm, two precipitation types: run the genuine vanilla server on a COPY of the generated world,
start rain with deep snow accumulation allowed, sprint N ticks, and count new snow layers per precipitation class.

usage: weather_probe.py WORLD_DIR OUT_JSON [TICKS] [CPUS]
Vanilla ServerLevel only places snow where Biome.getPrecipitationAt(pos) == SNOW (checked at the block's
own biome), so new snow in 'snow' columns and none in 'rain' columns is the engine's own answer.
The original world dir is never modified; the copy lives in a new /tmp dir.
"""
import json, os, shutil, sys, tempfile, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcnbt, vserver

world, out_p = sys.argv[1:3]
ticks = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
cpus = sys.argv[4] if len(sys.argv) > 4 else '8-11'
gen = json.load(open(f'{world}/gen.json')); seed = gen['seed']
x0, z0, x1, z1 = gen['block_rect']
jar = zipfile.ZipFile(vserver.CLIENT_JAR)
BI = {}
def binfo(n):
    if n not in BI: BI[n] = json.loads(jar.read(f"data/minecraft/worldgen/biome/{n.split(':')[1]}.json"))
    return BI[n]
MASK = (1 << 64) - 1

class W:
    def __init__(self, d):
        self.reg = {}; self.d = d; self.c = {}
        for fn in os.listdir(f'{d}/world/region'):
            p = fn.split('.')
            if len(p) == 4: self.reg[(int(p[1]), int(p[2]))] = mcnbt.Region(f'{d}/world/region/{fn}')
    def chunk(self, cx, cz):
        if (cx, cz) not in self.c:
            r = self.reg.get((cx >> 5, cz >> 5)); self.c[(cx, cz)] = r.chunk(cx, cz) if r else None
        return self.c[(cx, cz)]
    def top(self, x, z):
        c = self.chunk(x >> 4, z >> 4)
        longs = c['Heightmaps']['MOTION_BLOCKING']; i = (x & 15) + (z & 15) * 16
        return ((longs[i // 7] & MASK) >> ((i % 7) * 9) & 511) - 64
    def block(self, x, y, z):
        return mcnbt.block_at(self.chunk(x >> 4, z >> 4), x, y, z)
    def biome(self, x, y, z):
        c = self.chunk(x >> 4, z >> 4); s = {q['Y']: q for q in c['sections']}[y >> 4]['biomes']; pal = s['palette']
        if len(pal) == 1: return pal[0]
        bits = max(1, (len(pal) - 1).bit_length()); idx = (((y & 15) >> 2) << 4) | (((z & 15) >> 2) << 2) | ((x & 15) >> 2)
        per = 64 // bits
        return pal[(s['data'][idx // per] & MASK) >> ((idx % per) * bits) & ((1 << bits) - 1)]

def snapshot(d):
    w = W(d); res = {}
    for x in range(x0 + 2, x1 + 1, 4):
        for z in range(z0 + 2, z1 + 1, 4):
            t = w.top(x, z); sy = t - 1
            b = w.biome(x, sy, z); info = binfo(b)
            cls = 'none' if not info['has_precipitation'] else ('unresolved' if sy > 80 or info.get('temperature_modifier') == 'frozen'
                                                                else ('snow' if info['temperature'] < 0.15 else 'rain'))
            a = w.block(x, t, z)
            layers = int(a['Properties']['layers']) if a['Name'] == 'minecraft:snow' else 0
            res[(x, z)] = (cls, layers, w.block(x, sy, z)['Name'])
    return res

before = snapshot(world)
copy = tempfile.mkdtemp(prefix=f'aql-settlement-weather-{seed}-', dir='/tmp')
shutil.rmtree(copy); shutil.copytree(world, copy, ignore=shutil.ignore_patterns('session.lock', 'logs'))
s = vserver.Server(copy, seed, cpus=cpus, reuse=True)
try:
    for _ in range(60):
        s.p.stdin.write(f'execute if loaded {x0 + 8} 70 {z0 + 8} if loaded {x1 - 8} 70 {z1 - 8} run say QRYLOADED\n'); s.p.stdin.flush()
        try: s.wait(r'QRYLOADED', 3); break
        except TimeoutError: time.sleep(1)
    s.cmd('gamerule snowAccumulationHeight 8', r'Gamerule .* is now set', 30)
    s.cmd('gamerule doWeatherCycle false', r'Gamerule .* is now set', 30)
    s.cmd('weather rain 100000', r'Set the weather to rain', 30)
    t0 = time.time()
    s.cmd(f'tick sprint {ticks}', r'[Ss]print completed', 900)
    sprint_seconds = round(time.time() - t0, 1)
    s.cmd('save-all flush', r'Saved the game', 300)
finally:
    code = s.stop()
after = snapshot(copy)
lv = mcnbt.load_gz(f'{copy}/world/level.dat')['Data']
# columns >= 8 blocks (2 grid cells) away from a class change, to ignore cell-level vs per-block biome fuzz
def interior(k, cls):
    x, z = k
    return all(before.get((x + dx * 4, z + dz * 4), (cls,))[0] == cls for dx in (-2, -1, 0, 1, 2) for dz in (-2, -1, 0, 1, 2))
stats = {}
for k, (cls, l0, name) in before.items():
    if cls not in ('snow', 'rain') or not interior(k, cls): continue
    l1 = after[k][1]
    st = stats.setdefault(cls, {'columns': 0, 'columns_with_new_snow': 0, 'new_layers': 0, 'columns_snow_before': 0})
    st['columns'] += 1; st['columns_snow_before'] += l0 > 0
    if l1 > l0: st['columns_with_new_snow'] += 1; st['new_layers'] += l1 - l0
res = {'ticks': ticks, 'sprint_wall_seconds': sprint_seconds, 'server_exit': code,
       'level_dat_after': {'raining': lv.get('raining'), 'rainTime': lv.get('rainTime'), 'thundering': lv.get('thundering')},
       'gamerules': {'snowAccumulationHeight': 8, 'doWeatherCycle': False},
       'columns_interior_by_class': stats, 'cpus': cpus}
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps(res, indent=1)); print('COPY', copy)
