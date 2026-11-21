#!/usr/bin/env python3 -I
"""Engine-level proof that ONE storm is rain on one side and not-rain on the other (and not under a roof).

usage: rain_fire_probe.py WORLD_DIR ANALYSIS_JSON TRANSECT_JSON OUT_JSON [CPUS]
Vanilla Entity.isInRain() -> Level.isRainingAt(pos) is true only if the level is raining AND the position sees the
sky AND Biome.getPrecipitationAt(pos) == RAIN. A burning invulnerable pig standing there loses its fire in rain.
The original world is never modified: everything runs on a copy in a new /tmp directory.
(A first attempt with snow accumulation failed: forced chunks get no random ticks without a player, see NOTES.)
"""
import json, os, re, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vserver, mcnbt
world, ana_p, tr_p, out_p = sys.argv[1:5]
cpus = sys.argv[5] if len(sys.argv) > 5 else '8-11'
ana = json.load(open(ana_p)); tr = json.load(open(tr_p)); gen = ana['gen']; seed = gen['seed']; H = ana['chosen_house']
MASK = (1 << 64) - 1
regs = {}
def top(x, z):
    k = (x >> 9, z >> 9)
    if k not in regs: regs[k] = mcnbt.Region(f'{world}/world/region/r.{k[0]}.{k[1]}.mca')
    c = regs[k].chunk(x >> 4, z >> 4); i = (x & 15) + (z & 15) * 16
    return ((c['Heightmaps']['MOTION_BLOCKING'][i // 7] & MASK) >> ((i % 7) * 9) & 511) - 64
rows = tr['rows']
snow_far = rows[len(rows) // 3]
rain_far = rows[-4]            # 20 blocks past the transition, plains
ext = H['exterior_probe']['xz']
fl = H['interior_floor']['xyz']
sites = {
    'house_interior_floor': (fl[0], fl[1] + 1, fl[2]),
    'house_exterior_open_sky': (ext[0], top(*ext), ext[1]),
    'snow_side_open_sky': (snow_far['x'], top(snow_far['x'], snow_far['z']), snow_far['z']),
    'rain_side_open_sky': (rain_far['x'], top(rain_far['x'], rain_far['z']), rain_far['z']),
}
meta = {'snow_side_biome_by_transect': snow_far['biome'], 'rain_side_biome_by_transect': rain_far['biome']}
copy = tempfile.mkdtemp(prefix=f'aql-settlement-fire-{seed}-', dir='/tmp')
shutil.rmtree(copy); shutil.copytree(world, copy, ignore=shutil.ignore_patterns('session.lock', 'logs'))
s = vserver.Server(copy, seed, cpus=cpus, reuse=True)
FIRE = re.compile(r'entity data: (-?\d+)s')
def fire(tag):
    s.p.stdin.write(f'data get entity @e[tag={tag},limit=1] Fire\n'); s.p.stdin.flush()
    end = time.time() + 15
    while time.time() < end:
        try: l = s.q.get(timeout=1)
        except Exception: continue
        if l is None: return None
        m = FIRE.search(l)
        if m: return int(m[1])
        if 'No entity was found' in l: return 'dead_or_missing'
    return 'timeout'
res = {'spawn_override': 'setworldspawn + spawnChunkRadius 12 (copy only)', 'sites': {k: list(v) for k, v in sites.items()}, **meta}
try:
    for _ in range(60):
        s.p.stdin.write(f'execute if loaded {sites["rain_side_open_sky"][0]} 70 {sites["rain_side_open_sky"][2]} if loaded {sites["house_interior_floor"][0]} 70 {sites["house_interior_floor"][2]} run say QRYLOADED\n'); s.p.stdin.flush()
        try: s.wait(r'QRYLOADED', 3); break
        except TimeoutError: time.sleep(1)
    # Forced chunks get neither entity nor random ticks without a player (verified); the world-spawn ticket does.
    mid = ((sites['rain_side_open_sky'][0] + sites['house_interior_floor'][0]) // 2, (sites['rain_side_open_sky'][2] + sites['house_interior_floor'][2]) // 2)
    s.cmd(f'setworldspawn {mid[0]} 70 {mid[1]}', r'Set the world spawn point', 30)
    s.cmd('gamerule spawnChunkRadius 12', r'is now set', 30)
    time.sleep(3)
    s.cmd('gamerule doWeatherCycle false', r'is now set', 30)
    s.cmd('weather clear 100000', r'Set the weather to clear', 30)
    def summon(tag, p):
        s.p.stdin.write(f'summon minecraft:pig {p[0]+0.5} {p[1]} {p[2]+0.5} {{NoAI:1b,Invulnerable:1b,Silent:1b,Fire:30000s,Tags:["{tag}"]}}\n'); s.p.stdin.flush()
    for k, p in sites.items(): summon('dry_' + k, p)
    s.cmd('tick sprint 60', r'Sprint completed', 120)
    res['clear_weather_fire_after_60_ticks'] = {k: fire('dry_' + k) for k in sites}
    s.cmd('weather rain 100000', r'Set the weather to rain', 30)
    s.cmd('tick sprint 100', r'Sprint completed', 120)   # rainLevel rises 0.01/tick -> 1.0
    for k, p in sites.items(): summon('wet_' + k, p)
    s.cmd('tick sprint 60', r'Sprint completed', 120)
    res['rain_fire_after_60_ticks'] = {k: fire('wet_' + k) for k in sites}
finally:
    res['server_exit'] = s.stop()
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps(res, indent=1)); print('COPY', copy)
