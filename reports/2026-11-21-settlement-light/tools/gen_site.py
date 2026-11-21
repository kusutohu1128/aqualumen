#!/usr/bin/env python3 -I
"""Generate (genuine vanilla 1.21.1, CPU only) the chunks around a candidate site into a NEW /tmp world.

usage: gen_site.py SEED VILLAGE_X VILLAGE_Z RAIN_X RAIN_Z [CPUS]
The world stays in /tmp (never copied into the repo, never distributed). Prints the directory.
"""
import json, os, struct, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vserver, mcnbt

seed, vx, vz, rx, rz = map(int, sys.argv[1:6])
cpus = sys.argv[6] if len(sys.argv) > 6 else '4-7'
# Rectangle: the whole village footprint (jigsaw size 6, <=80 from centre) plus the rain candidate.
x0 = min(vx - 112, rx - 48) >> 4 << 4; x1 = (max(vx + 112, rx + 48) >> 4 << 4) + 15
z0 = min(vz - 112, rz - 48) >> 4 << 4; z1 = (max(vz + 112, rz + 48) >> 4 << 4) + 15
d = tempfile.mkdtemp(prefix=f'aql-settlement-world-{seed}-', dir='/tmp')
s = vserver.Server(d, seed, cpus=cpus)
t0 = time.time()
cx0, cx1, cz0, cz1 = x0 >> 4, x1 >> 4, z0 >> 4, z1 >> 4
want = {(cx, cz) for cx in range(cx0, cx1 + 1) for cz in range(cz0, cz1 + 1)}
print('chunks wanted', len(want), flush=True)
# forceload accepts at most 256 chunks per command: 16x16-chunk tiles
for tx in range(cx0, cx1 + 1, 16):
    for tz in range(cz0, cz1 + 1, 16):
        ax, bx = tx * 16, (min(tx + 15, cx1)) * 16 + 15
        az, bz = tz * 16, (min(tz + 15, cz1)) * 16 + 15
        s.cmd(f'forceload add {ax} {az} {bx} {bz}', r'force loaded|Marked|Too many|must be', 60)
def full_chunks():
    got = set()
    reg = f'{d}/world/region'
    if not os.path.isdir(reg): return got
    for fn in os.listdir(reg):
        parts = fn.split('.')
        if len(parts) != 4 or parts[0] != 'r': continue
        rxn, rzn = int(parts[1]), int(parts[2])
        r = mcnbt.Region(f'{reg}/{fn}')
        for lx, lz in r.present():
            c = (rxn * 32 + lx, rzn * 32 + lz)
            if c in want:
                try: ch = r.chunk(*c)
                except Exception: continue  # chunk being rewritten while we read: retry next poll
                if ch and ch.get('Status') == 'minecraft:full': got.add(c)
    return got
got = set()
while time.time() - t0 < 900:
    time.sleep(8)
    s.cmd('save-all flush', r'Saved the game', 120)
    got = full_chunks()
    print(f'{len(got)}/{len(want)} full after {time.time()-t0:.0f}s', flush=True)
    if len(got) == len(want): break
code = s.stop()
json.dump({'seed': seed, 'village_locate': [vx, vz], 'rain_locate': [rx, rz],
           'block_rect': [x0, z0, x1, z1], 'chunks': len(want), 'full': len(got), 'exit': code,
           'generation_seconds': round(time.time() - t0, 1), 'cpus': cpus},
          open(f'{d}/gen.json', 'w'), indent=1)
print('WORLD', d, 'exit', code)
