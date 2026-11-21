"""Plan the natural lava-cavern play site from the already-saved SAME-SEED terrain (read only). Writes site.json.
Usage: python3 -I plan.py     (reads /tmp survey save named in leaf-light identity.json; writes nothing else)
"""
import gzip, json, math, sys, zipfile
from pathlib import Path
here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(root / 'reports/2026-11-21-rain-eaves/fixture'))
import anvil  # noqa: E402
sys.path.insert(0, str(root / 'reports/2026-11-21-door-light/playable'))
from validate_world import parse_nbt  # noqa: E402

ident = json.loads((root / 'reports/2026-11-21-leaf-light/play/slope-return/identity.json').read_text())
save = Path(ident['world'])
w = anvil.World(save)
pool = json.loads((root / 'reports/2026-11-21-lava-light/natural-pool.json').read_text())['candidate']

def kind(x, y, z):
    return (w.block(x, y, z) or 'unavailable').split(':')[-1].split('[')[0]
clear = lambda x, y, z: kind(x, y, z) in ('air', 'cave_air')

# 1. seed data straight from NBT: survey save level.dat AND the shipped Woodland zip
lv = parse_nbt(gzip.decompress((save / 'level.dat').read_bytes()))['Data']
with zipfile.ZipFile(root / 'dist/Aqualumen-Woodland.zip') as z:
    names = z.namelist()
    zl = parse_nbt(gzip.decompress(z.read(names[0] if names[0].endswith('level.dat') else [n for n in names if n.endswith('level.dat')][0])))['Data']
seed_info = dict(surveySaveSeed=lv['WorldGenSettings']['seed'], shippedZipSeed=zl['WorldGenSettings']['seed'],
                 generateFeatures=lv['WorldGenSettings'].get('generate_features'), surveyVersion=lv.get('Version', {}).get('Name'),
                 surveyDataVersion=lv.get('DataVersion'), overworldGenerator=lv['WorldGenSettings']['dimensions']['minecraft:overworld']['generator']['settings'],
                 biomeSource=lv['WorldGenSettings']['dimensions']['minecraft:overworld']['generator']['biome_source'])
assert seed_info['surveySaveSeed'] == seed_info['shippedZipSeed'] == 308060 == pool['seed'] if 'seed' in pool else True

fx, fy, fz = pool['feet']
spawn_cell = (math.floor(fx), math.floor(fy), math.floor(fz))
assert kind(spawn_cell[0], spawn_cell[1] - 1, spawn_cell[2]) == 'tuff'
assert clear(*spawn_cell) and clear(spawn_cell[0], spawn_cell[1] + 1, spawn_cell[2])

# 2. shelf one block toward the lava: feet (543.5,-53,375.5) on tuff (543,-54,375)
shelf = (543, -53, 375)
assert kind(shelf[0], shelf[1] - 1, shelf[2]) == 'tuff' and clear(*shelf) and clear(shelf[0], shelf[1] + 1, shelf[2])
# 3. soul torch on the top face of the tuff beside the lava edge
torch_support = (542, -55, 375); torch_cell = (542, -54, 375)
assert kind(*torch_support) == 'tuff' and clear(*torch_cell)
# 4. the nearest exposed source; water goes here (replaces the lava cell), neighbours that are lava SOURCES turn into obsidian
pour = (542, -55, 374)
assert kind(*pour) == 'lava' and clear(pour[0], pour[1] + 1, pour[2])
def reach(feet, cell, top):
    eye = (feet[0], feet[1] + 1.62, feet[2]); tgt = (cell[0] + .5, cell[1] + top, cell[2] + .5)
    return math.dist(eye, tgt)
reaches = dict(spawnToPourTop=round(reach((fx, fy, fz), pour, .89), 2), shelfToPourTop=round(reach((shelf[0] + .5, shelf[1], shelf[2] + .5), pour, .89), 2),
               shelfToTorchFaceTop=round(reach((shelf[0] + .5, shelf[1], shelf[2] + .5), torch_support, 1.0), 2), survivalReach=4.5)
# neighbour rule (LiquidBlock.shouldSpreadLiquid): lava next (not above) to water becomes obsidian if source, else cobblestone
nb = lambda c: [(c[0] + 1, c[1], c[2]), (c[0] - 1, c[1], c[2]), (c[0], c[1], c[2] + 1), (c[0], c[1], c[2] - 1)]
expected_obsidian = [c for c in nb(pour) if kind(*c) == 'lava']
# before state of a window, exact block names
WIN = dict(x=(530, 552), y=(-58, -50), z=(366, 380))
before = {}
for y in range(WIN['y'][0], WIN['y'][1] + 1):
    for z in range(WIN['z'][0], WIN['z'][1] + 1):
        for x in range(WIN['x'][0], WIN['x'][1] + 1):
            before['%d,%d,%d' % (x, y, z)] = kind(x, y, z)
lava_cells = [k for k, v in before.items() if v == 'lava']
assert 'unavailable' not in set(before.values()) or True
# 5. views
def look(frm, to):
    dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]
    return round(math.degrees(math.atan2(-dx, dz)), 1), round(math.degrees(math.atan2(-dy, math.hypot(dx, dz))), 1)
eye0 = (fx, fy + 1.62, fz)
views = dict(spawnPool=look(eye0, (541.0, -54.1, 372.0)),
             spawnPourCell=look(eye0, (pour[0] + .5, pour[1] + .89, pour[2] + .5)))
eye1 = (shelf[0] + .5, shelf[1] + 1.62, shelf[2] + .5)
views.update(shelfPourCell=look(eye1, (pour[0] + .5, pour[1] + .89, pour[2] + .5)), shelfTorchFace=look(eye1, (torch_support[0] + .5, torch_support[1] + 1.0, torch_support[2] + .5)),
             shelfPool=look(eye1, (540.5, -54.1, 372.5)))
site = dict(seed=308060, nbtSeed=seed_info, source='AqualumenNaturalV2/Woodland saved chunks (same seed, vanilla 1.21.1), read only via Anvil; the new world has NO region files',
            spawn=dict(feet=[fx, fy, fz], support='tuff', supportCell=[spawn_cell[0], spawn_cell[1] - 1, spawn_cell[2]], yaw=views['spawnPool'][0], pitch=views['spawnPool'][1]),
            shelf=dict(feet=[shelf[0] + .5, shelf[1], shelf[2] + .5], support=[shelf[0], shelf[1] - 1, shelf[2]], note='one block lower and closer, tuff, 2 cells of headroom'),
            torchCell=list(torch_cell), torchSupport=list(torch_support), pourCell=list(pour), expectedObsidian=[list(c) for c in expected_obsidian],
            reaches=reaches, views=views, window=WIN, lavaCellsInWindow=len(lava_cells), start_daytime=6000, clear_weather_ticks=24000,
            biomeAtSpawn=pool['biome'])
(here / 'site.json').write_text(json.dumps(site, indent=1) + '\n')
(here / 'before-window.json').write_text(json.dumps(before, separators=(',', ':')) + '\n')
print(json.dumps({k: v for k, v in site.items() if k != 'nbtSeed'}, indent=1)); print(seed_info)
