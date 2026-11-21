"""Mixed torch / lava / stone-pillar study: pure scene + datapack definition (no I/O, no launch).

Geometry reuses reports/2026-11-21-lava-light/basin.py (roofed chamber, white wall z=366, 3x3 lava pool
flush with the floor at y=172, stone pillar at 202,173..175,364) and adds an ordinary torch and a soul torch.
Everything is numeric/explicit so baseline (1.8.0) and candidate (1.9.0) runs are directly comparable.
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import basin  # noqa: E402  (read-only reuse of the supplied study)

NS = 'aqlava'
PLAYER = 'AqualumenLava'
PLAYER_UUID = '00000000000040008000000000000472'
EYE = (205.5, 174.62, 362.5)
AIM = (202.5, 173.64, 366.0)
TORCH = (200, 173, 363)      # ordinary torch, floor-standing, visible at the left frame edge
SOUL = (204, 173, 365)       # soul torch on the wall side of the pillar line (parent-supplied example)
TIME = 18000                 # fixed midnight; the chamber is roofed anyway
PERIOD = 200                 # ticks per stage
READY_AT = 40                # ticks after stage start: verified handshake (READY)
STILL_AT = 170               # ticks after stage start: re-verification (STILL / DRIFT)

# name: (pillar, lava cells, torch, soul)
STAGE_TABLE = {
    'dark':                 (False, 0, False, False),
    'torch':                (False, 0, True, False),
    'torch-pillar':         (True, 0, True, False),
    'lava1-open':           (False, 1, False, False),
    'lava1-pillar':         (True, 1, False, False),
    'lava9-open':           (False, 9, False, False),
    'lava9-pillar':         (True, 9, False, False),
    'torch-lava1-open':     (False, 1, True, False),
    'torch-lava1-pillar':   (True, 1, True, False),
    'torch-lava9-open':     (False, 9, True, False),
    'torch-lava9-pillar':   (True, 9, True, False),
    'soul-open':            (False, 0, False, True),
    'soul-pillar':          (True, 0, False, True),
    'soul-lava9-open':      (False, 9, False, True),
    'soul-lava9-pillar':    (True, 9, False, True),
    'restored-mixed':       (False, 1, True, False),   # == torch-lava1-open
    'restored-dark':        (False, 0, False, False),  # == dark
}
ALL = list(STAGE_TABLE)
CORE = ['dark', 'torch', 'torch-lava1-open', 'torch-lava1-pillar', 'torch-lava9-pillar', 'torch-lava9-open',
        'soul-pillar', 'soul-lava9-pillar', 'restored-mixed', 'restored-dark']
RESTORE_OF = {'restored-mixed': 'torch-lava1-open', 'restored-dark': 'dark'}
EVENT_RE = re.compile(r'\[Server\] AQLAVA_(READY|FAIL|STILL|DRIFT|BEGIN|ARM)(?:_([a-z0-9-]+))?_END')


def configure(period=200):
    """Stretch the stage timeline (slow software-GL clients need many seconds per frame)."""
    global PERIOD, READY_AT, STILL_AT
    PERIOD, READY_AT, STILL_AT = period, period // 5, period * 17 // 20


def fmt(v):
    return ('%.3f' % v).rstrip('0').rstrip('.') if '.' in '%.3f' % v else '%.3f' % v


def pose():
    dx, dy, dz = [b - a for a, b in zip(EYE, AIM)]
    return dict(yaw=-math.degrees(math.atan2(dx, dz)), pitch=-math.degrees(math.atan2(dy, math.hypot(dx, dz))))


def feet():
    return (EYE[0], EYE[1] - 1.62, EYE[2])


def wrap(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def tp_line():
    p = pose()
    return 'tp %s %s %s %s %.6f %.6f' % (PLAYER, fmt(feet()[0]), '%.2f' % feet()[1], fmt(feet()[2]), p['yaw'], p['pitch'])


def pose_selector():
    p = pose()
    f = feet()
    return ('@a[name=%s,x=%s,y=%s,z=%s,distance=..0.04,gamemode=creative,x_rotation=%.3f..%.3f,y_rotation=%.3f..%.3f]'
            % (PLAYER, fmt(f[0]), '%.2f' % f[1], fmt(f[2]), p['pitch'] - 0.05, p['pitch'] + 0.05,
               wrap(p['yaw'] - 0.05), wrap(p['yaw'] + 0.05)))


def blocks_for(name):
    """Return {(x,y,z): blockstate} for every mutable cell of the stage (pool, pillar, torch, soul)."""
    pillar, lava, torch, soul = STAGE_TABLE[name]
    assignments, _ = basin.layout(name, pillar, lava)
    cells = {}
    for line in assignments:
        _, x, y, z, block = line.split(' ', 4)
        cells[(int(x), int(y), int(z))] = block
    cells[TORCH] = 'minecraft:torch' if torch else 'minecraft:air'
    cells[SOUL] = 'minecraft:soul_torch' if soul else 'minecraft:air'
    return cells


def stage_functions(names):
    """{function name: [lines]} for the stage loop."""
    fn = {}
    cond_static = ['if block 204 180 363 minecraft:smooth_stone', 'if block 204 179 363 minecraft:air',
                   'if block 202 173 366 minecraft:white_concrete', 'if block 206 173 366 minecraft:white_concrete',
                   'if block 205 174 362 minecraft:air', 'if block 205 173 362 minecraft:air',
                   'if block 202 172 364 minecraft:smooth_stone']
    entity_free = 'unless entity @e[type=!minecraft:player,x=204,y=176,z=363,distance=..14]'
    for i, name in enumerate(names):
        cells = blocks_for(name)
        cond = ' '.join('if block %d %d %d %s' % (*k, v) for k, v in cells.items())
        nxt = names[(i + 1) % len(names)]
        fn['s%d' % i] = [
            tp_line(), *['setblock %d %d %d %s' % (*k, v) for k, v in cells.items()],
            'scoreboard players set #stage %s %d' % (NS, i),
            'say AQLAVA_BEGIN_%s_END' % name,
            'schedule function %s:v%d %dt replace' % (NS, i, READY_AT),
            'schedule function %s:e%d %dt replace' % (NS, i, STILL_AT),
            'schedule function %s:s%d %dt replace' % (NS, (i + 1) % len(names), PERIOD)]
        chk = ['scoreboard players set #ok %s 0' % NS,
               'execute store result score #t %s run time query daytime' % NS,
               'execute if score #t %s matches %d if score #stage %s matches %d %s %s %s if entity %s run scoreboard players set #ok %s 1'
               % (NS, TIME, NS, i, cond, ' '.join(cond_static), entity_free, pose_selector(), NS)]
        fn['c%d' % i] = chk
        fn['v%d' % i] = ['function %s:c%d' % (NS, i),
                         'execute if score #ok %s matches 1 run say AQLAVA_READY_%s_END' % (NS, name),
                         'execute if score #ok %s matches 0 run say AQLAVA_FAIL_%s_END' % (NS, name)]
        fn['e%d' % i] = ['function %s:c%d' % (NS, i),
                         'execute if score #ok %s matches 1 run say AQLAVA_STILL_%s_END' % (NS, name),
                         'execute if score #ok %s matches 0 run say AQLAVA_DRIFT_%s_END' % (NS, name)]
    return fn


def datapack(names):
    """{relative path: text} for the world-local datapack."""
    files = {
        'pack.mcmeta': json.dumps({'pack': {'pack_format': 48, 'description': 'Private Aqualumen lava/torch runtime study'}}),
        'data/minecraft/tags/function/tick.json': json.dumps({'values': [NS + ':tick']}),
    }
    fn = {}
    fn['tick'] = ['execute as @a[name=%s,tag=!%s_init] run function %s:setup' % (PLAYER, NS, NS),
                  'execute as @a[name=%s,tag=%s_armed,tag=!%s_run] if items entity @s weapon.offhand minecraft:paper run function %s:go'
                  % (PLAYER, NS, NS, NS)]
    fn['setup'] = ['tag @s add %s_init' % NS, 'gamerule doDaylightCycle false', 'gamerule doWeatherCycle false',
                   'gamerule doMobSpawning false', 'gamerule randomTickSpeed 0', 'gamerule doFireTick false',
                   'gamerule doTileDrops false', 'gamerule sendCommandFeedback false', 'gamerule commandBlockOutput false',
                   'gamerule announceAdvancements false', 'difficulty peaceful', 'weather clear', 'time set %d' % TIME,
                   'gamemode creative @s', 'scoreboard objectives add %s dummy' % NS, 'forceload add 198 359 209 367',
                   'tp %s 205.5 173 362.5' % PLAYER, 'schedule function %s:prepare 20t replace' % NS]
    fn['prepare'] = ['execute if loaded 202 173 364 run function %s:build' % NS,
                     'execute unless loaded 202 173 364 run schedule function %s:prepare 20t replace' % NS]
    fn['build'] = ['fill 198 172 359 209 172 367 minecraft:smooth_stone', 'fill 198 173 366 209 179 366 minecraft:white_concrete',
                   *basin.room, 'fill 199 173 360 208 179 365 minecraft:air', 'fill 199 173 366 208 179 366 minecraft:white_concrete',
                   tp_line(), 'item replace entity %s weapon.mainhand with minecraft:paper' % PLAYER,
                   'tag %s add %s_armed' % (PLAYER, NS), 'say AQLAVA_ARM_END']
    fn['go'] = ['tag @s add %s_run' % NS, 'item replace entity @s weapon.offhand with minecraft:air', 'function %s:s0' % NS]
    fn.update(stage_functions(names))
    for k, lines in fn.items():
        files['data/%s/function/%s.mcfunction' % (NS, k)] = '\n'.join(lines) + '\n'
    return files


def geometry(names):
    p = pose()
    return dict(eye=EYE, target=AIM, yaw=p['yaw'], pitch=p['pitch'], player=PLAYER, time=TIME, wallZ=366, cameraFovOption='70 (fov=0.0)',
                torch=TORCH, soul=SOUL, poolCorners=[[201, 172, 360], [203, 172, 362]], pillar=[[202, 173, 364], [202, 175, 364]],
                room=basin.room, periodTicks=PERIOD, readyAtTicks=READY_AT, stillAtTicks=STILL_AT,
                stages={n: dict(zip(('pillar', 'lavaCells', 'torch', 'soul'), STAGE_TABLE[n])) for n in names},
                restoreOf={k: v for k, v in RESTORE_OF.items() if k in names})


def self_test(names=ALL):
    files = datapack(names)
    for path, text in files.items():
        if path.endswith('.mcfunction'):
            for line in text.splitlines():
                assert line and not line.startswith('/') and '\t' not in line, (path, line)
    assert len(set(names)) == len(names) and all(re.fullmatch('[a-z0-9-]+', n) for n in names)
    # restoration stages must re-create their original exactly
    for k, v in RESTORE_OF.items():
        assert STAGE_TABLE[k] == STAGE_TABLE[v] and blocks_for(k) == blocks_for(v)
    # every mutable cell is explicitly assigned in every stage (no stale state carried over)
    keys = {frozenset(blocks_for(n)) for n in names}
    assert len(keys) == 1, 'stage cell sets differ'
    cells = next(iter(keys))
    assert TORCH in cells and SOUL in cells and len(cells) == 9 + 3 + 2
    # lava counts
    for n in names:
        lava = sum('lava' in v for v in blocks_for(n).values())
        assert lava == STAGE_TABLE[n][1], n
    return len(files)


if __name__ == '__main__':
    print('scene self-test OK, files:', self_test())
