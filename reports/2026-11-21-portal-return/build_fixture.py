"""One-time isolated VANILLA 1.21.1 dedicated server (loopback, CPU only) builds the portal-return fixture world.

  python3 -I build_fixture.py

Server driver reused from reports/2026-11-21-settlement-light/tools/vserver.py (explicit path, unmodified; PROPS overridden in-process).
Output: build/aql-portal-return/Aqualumen-Portal-Return.zip (+ fixture.json). Nothing outside build/aql-portal-return/ and /tmp/aql-portal-return-* is written.
Layout (flat overworld, x east, z south, feet y=-60): lit portal (axis x, interior x0..1,y-60..-58,z-3), two white-concrete panels on z=10,
warm torch (-4,-59,9) and soul torch (6,-59,9) on their north faces, spawn (1,-60,3).
"""
import hashlib, json, os, shutil, sys, tempfile, zipfile
from pathlib import Path
here = Path(__file__).resolve().parent
root = here.parents[1]
sys.path.insert(0, str(root / 'reports/2026-11-21-settlement-light/tools'))
import vserver  # noqa: E402

vserver.PROPS = (vserver.PROPS.replace('level-type=minecraft\\:normal', 'level-type=minecraft\\:flat')
                 .replace('generate-structures=true', 'generate-structures=false'))
assert 'minecraft\\:flat' in vserver.PROPS
outdir = root / 'build/aql-portal-return'
work = Path(tempfile.mkdtemp(prefix='aql-portal-return-srv-', dir='/tmp'))
srv = vserver.Server(str(work), seed=308061, cpus='0-3', heap='1G')
log = []
def c(text, pat=r'.'):
    m = srv.cmd(text, pat, 60)
    log.append({'cmd': text, 'reply': m.string.split(']: ', 1)[-1]})
    return m.string
try:
    c('forceload add -12 -12 12 16', r'Marked|forceload')
    import time; time.sleep(8)
    c('execute if block 1 -61 3 minecraft:grass_block', r'Test passed|Test failed')
    c('execute if block 1 -60 3 minecraft:air', r'Test passed|Test failed')
    # portal frame (obsidian), then ignite with fire as vanilla does
    c('fill 0 -61 -3 1 -61 -3 minecraft:obsidian', r'filled|No blocks')
    c('fill 0 -57 -3 1 -57 -3 minecraft:obsidian', r'filled|No blocks')
    c('fill -1 -60 -3 -1 -58 -3 minecraft:obsidian', r'filled|No blocks')
    c('fill 2 -60 -3 2 -58 -3 minecraft:obsidian', r'filled|No blocks')
    c('setblock 0 -60 -3 minecraft:fire', r'Changed|Could not')
    time.sleep(2)
    for y in (-60, -59, -58):
        for x in (0, 1):
            c('execute if block %d %d -3 minecraft:nether_portal[axis=x]' % (x, y), r'Test passed|Test failed')
    c('fill -5 -60 10 -3 -58 10 minecraft:white_concrete', r'filled')
    c('fill 5 -60 10 7 -58 10 minecraft:white_concrete', r'filled')
    c('setblock -4 -59 9 minecraft:wall_torch[facing=north]', r'Changed|Could not')
    c('setblock 6 -59 9 minecraft:soul_wall_torch[facing=north]', r'Changed|Could not')
    c('setworldspawn 1 -60 3 0', r'Set the world spawn')
    for g in ('spawnRadius 0', 'doDaylightCycle false', 'doWeatherCycle false', 'doMobSpawning false'):
        c('gamerule ' + g, r'Gamerule')
    c('time set 18000', r'Set the time')
    c('weather clear', r'Set the weather')
    c('save-all flush', r'Saved the game')
finally:
    rc = srv.stop()
log.append({'serverExit': rc})
w = work / 'world'
for p in w.rglob('session.lock'):
    p.unlink()
NAME = 'Aqualumen-Portal-Return'
zp = outdir / (NAME + '.zip')
with zipfile.ZipFile(zp, 'x', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(w.rglob('*')):
        if p.is_file():
            z.write(p, NAME + '/' + str(p.relative_to(w)))
sha = hashlib.sha256(zp.read_bytes()).hexdigest()
(outdir / 'fixture.json').write_text(json.dumps({'zip': zp.name, 'sha256': sha, 'serverWork': str(work), 'console': log}, indent=2) + '\n')
print(sha, rc)
for l in log: print(l)
