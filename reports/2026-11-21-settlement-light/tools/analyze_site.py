#!/usr/bin/env python3 -I
"""Offline analysis of a generated world: village pieces, house vs. Mojang template, precipitation map.

usage: analyze_site.py WORLD_DIR OUT_DIR
Reads only: WORLD_DIR/world/region/*.mca (read-only) and the vanilla client jar (templates, biome JSON).
Writes: OUT_DIR/analysis.json, OUT_DIR/precipitation-map.png (small), nothing else. No region file is copied.
"""
import gzip, hashlib, io, json, math, os, struct, sys, zipfile, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcnbt, vserver

world, out = sys.argv[1], sys.argv[2]
gen = json.load(open(f'{world}/gen.json'))
seed = gen['seed']
JAR = zipfile.ZipFile(vserver.CLIENT_JAR)
MINY = -64
MASK = (1 << 64) - 1

# ---------- load chunks ----------
chunks = {}
regs = {}
for fn in sorted(os.listdir(f'{world}/world/region')):
    p = fn.split('.')
    if len(p) != 4: continue
    r = mcnbt.Region(f'{world}/world/region/{fn}')
    for lx, lz in r.present():
        chunks[(int(p[1]) * 32 + lx, int(p[2]) * 32 + lz)] = r
def chunk(cx, cz):
    r = chunks.get((cx, cz))
    return r.chunk(cx, cz) if r else None
cache = {}
def C(cx, cz):
    if (cx, cz) not in cache: cache[(cx, cz)] = chunk(cx, cz)
    return cache[(cx, cz)]
def block(x, y, z):
    c = C(x >> 4, z >> 4)
    return mcnbt.block_at(c, x, y, z) if c else {'Name': 'unloaded'}
def unpack(longs, bits, n=256):
    per = 64 // bits; o = []
    for i in range(n):
        w = longs[i // per] & MASK
        o.append((w >> ((i % per) * bits)) & ((1 << bits) - 1))
    return o
hm_cache = {}
def top(x, z, key='MOTION_BLOCKING'):
    """y of the first free block above the surface (heightmap + minY)."""
    k = (x >> 4, z >> 4, key)
    if k not in hm_cache:
        c = C(k[0], k[1]); hm_cache[k] = unpack(c['Heightmaps'][key], 9) if c else None
    h = hm_cache[k]
    return None if h is None else h[(x & 15) + (z & 15) * 16] + MINY
def biome_at(x, y, z):
    c = C(x >> 4, z >> 4)
    if not c: return None
    secs = {s['Y']: s for s in c['sections']}
    s = secs.get(y >> 4)
    if not s: return None
    b = s['biomes']; pal = b['palette']
    if len(pal) == 1: return pal[0]
    bits = max(1, (len(pal) - 1).bit_length())
    idx = (((y & 15) >> 2) << 4) | (((z & 15) >> 2) << 2) | ((x & 15) >> 2)
    per = 64 // bits
    return pal[(b['data'][idx // per] & MASK) >> ((idx % per) * bits) & ((1 << bits) - 1)]
BIOMES = {}
def biome_info(name):
    if name not in BIOMES:
        d = json.loads(JAR.read(f"data/minecraft/worldgen/biome/{name.split(':')[1]}.json"))
        BIOMES[name] = d
    return BIOMES[name]
def precip(name, y):
    """Vanilla 1.21.1 Biome.getPrecipitationAt: none / snow if temp<0.15 else rain.
    Below y=80 temperature == base temperature; frozen modifier and y>80 need noise -> 'unresolved'."""
    d = biome_info(name)
    if not d['has_precipitation']: return 'none'
    if d.get('temperature_modifier') == 'frozen' or y > 80: return 'unresolved'
    return 'snow' if d['temperature'] < 0.15 else 'rain'

# ---------- village structure ----------
starts = []
for (cx, cz) in sorted(chunks):
    c = C(cx, cz)
    if not c: continue
    for k, v in c.get('structures', {}).get('starts', {}).items():
        if k == 'minecraft:village_snowy' and v.get('id') != 'INVALID':
            starts.append((cx, cz, v))
assert starts, 'no village_snowy start in generated chunks'
cx, cz, st = starts[0]
pieces = st['Children']
def bb_union(bbs):
    return [min(b[0] for b in bbs), min(b[1] for b in bbs), min(b[2] for b in bbs),
            max(b[3] for b in bbs), max(b[4] for b in bbs), max(b[5] for b in bbs)]
village_bb = bb_union([p['BB'] for p in pieces])
plist = []
for i, p in enumerate(pieces):
    pe = p.get('pool_element', {})
    plist.append({'i': i, 'id': p['id'], 'location': pe.get('location'), 'element_type': pe.get('element_type'),
                  'BB': p['BB'], 'pos': [p.get('PosX'), p.get('PosY'), p.get('PosZ')],
                  'rotation': p.get('rotation'), 'ground_delta': p.get('GD'), 'keys': sorted(p.keys())})

# ---------- template machinery ----------
def template(loc):
    path = f"data/minecraft/structure/{loc.split(':')[1]}.nbt"
    return mcnbt.parse(gzip.decompress(JAR.read(path)))
ROT = {'none': lambda x, z: (x, z), 'clockwise_90': lambda x, z: (-z, x),
       'clockwise_180': lambda x, z: (-x, -z), '180': lambda x, z: (-x, -z),
       'counterclockwise_90': lambda x, z: (z, -x)}
def place(t, piece):
    rot = ROT[piece['rotation'].lower()]
    ox, oy, oz = piece['PosX'], piece['PosY'], piece['PosZ']
    pal = t['palette']; res = {}
    for b in t['blocks']:
        x, y, z = b['pos']; rx_, rz_ = rot(x, z)
        res[(ox + rx_, oy + y, oz + rz_)] = pal[b['state']]
    sx, sy, sz = t['size']
    cs = [rot(0, 0), rot(sx - 1, sz - 1)]
    bb = [ox + min(c[0] for c in cs), oy, oz + min(c[1] for c in cs),
          ox + max(c[0] for c in cs), oy + sy - 1, oz + max(c[1] for c in cs)]
    return res, bb
SOLID_FLOOR = ('planks', 'cobblestone', 'stone', 'spruce_log', 'log', 'bricks', 'terracotta', 'wool', 'carpet_base')
def is_air(n): return n.endswith('air')
def is_solid(n):
    return not (is_air(n) or 'glass' in n or 'door' in n or 'torch' in n or 'lantern' in n or n.endswith('_bed')
                or 'carpet' in n or 'pane' in n or 'trapdoor' in n or 'jigsaw' in n or 'void' in n
                or n.endswith('chest') or 'crafting' in n or 'furnace' in n or 'barrel' in n or 'bookshelf' in n
                or 'flower_pot' in n or 'ladder' in n or 'button' in n or 'plate' in n or 'sign' in n or 'snow' == n)

houses = []
for pi, p in enumerate(pieces):
    loc = p.get('pool_element', {}).get('location', '')
    if 'snowy_small_house' not in loc and 'snowy_medium_house' not in loc: continue
    t = template(loc)
    cells, bb = place(t, p)
    bb_ok = bb == list(p['BB'])
    tot = match = 0; mism = {}
    for (x, y, z), st_ in cells.items():
        n = st_['Name']
        if n in ('minecraft:jigsaw', 'minecraft:structure_void', 'minecraft:structure_block'): continue
        w = block(x, y, z)['Name']
        tot += 1
        if w == n: match += 1
        else:
            key = f'{n.split(":")[1]}->{w.split(":")[1]}'; mism[key] = mism.get(key, 0) + 1
    # door
    doors = [(pos, s_) for pos, s_ in cells.items() if s_['Name'].endswith('_door') and s_['Properties'].get('half') == 'lower']
    # interior floor cells: solid floor in template, two air above, roof above in template, walls on 4 sides
    inside = []
    for (x, y, z), s_ in cells.items():
        if not is_solid(s_['Name']) or not any(k in s_['Name'] for k in ('planks', 'cobblestone', 'stone', 'log')): continue
        a1, a2 = cells.get((x, y + 1, z)), cells.get((x, y + 2, z))
        if a1 is None or a2 is None or not is_air(a1['Name']) or not is_air(a2['Name']): continue
        roof = any(is_solid(cells.get((x, y + k, z), {'Name': 'minecraft:air'})['Name']) for k in range(3, 9))
        if not roof: continue
        walls = 0
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for k in range(1, 7):
                n2 = cells.get((x + dx * k, y + 1, z + dz * k))
                if n2 is not None and (is_solid(n2['Name']) or 'pane' in n2['Name'] or 'door' in n2['Name']):
                    walls += 1; break
        if walls == 4: inside.append((x, y, z))
    houses.append({'piece': pi, 'location': loc, 'rotation': p['rotation'], 'BB': list(p['BB']), 'bb_equals_template_transform': bb_ok,
                   'nonair_template_cells': tot, 'matching_cells': match, 'match_fraction': round(match / max(tot, 1), 4),
                   'mismatch_top': sorted(mism.items(), key=lambda kv: -kv[1])[:8],
                   'doors': [[list(pos), s_['Name'], s_['Properties']] for pos, s_ in doors], 'interior_floor_cells': len(inside),
                   '_cells': cells, '_inside': inside, '_doors': doors, '_size': t['size']})

# ---------- precipitation map (4-block cells over the generated rectangle) ----------
x0, z0, x1, z1 = gen['block_rect']
grid = {}
for x in range(x0 + 2, x1 + 1, 4):
    for z in range(z0 + 2, z1 + 1, 4):
        t_ = top(x, z)
        if t_ is None: continue
        sy = t_ - 1
        b = biome_at(x, sy, z)
        top_block = block(x, sy, z)['Name']
        grid[(x, z)] = {'y': sy, 'biome': b, 'precip': precip(b, sy), 'top': top_block, 'above': block(x, sy + 1, z)['Name']}
def count(pred):
    return sum(1 for v in grid.values() if pred(v))
def snowy(v): return v['above'] == 'minecraft:snow' or v['top'] in ('minecraft:snow_block', 'minecraft:powder_snow', 'minecraft:snow')
summary = {
    'columns': len(grid),
    'biome_counts': {},
    'precip_counts': {},
    'snow_cover_on_snow_precip_columns': count(lambda v: v['precip'] == 'snow' and snowy(v)),
    'snow_precip_columns': count(lambda v: v['precip'] == 'snow'),
    'snow_cover_on_rain_precip_columns': count(lambda v: v['precip'] == 'rain' and snowy(v)),
    'rain_precip_columns': count(lambda v: v['precip'] == 'rain'),
    'max_surface_y_snow': max([v['y'] for v in grid.values() if v['precip'] == 'snow'], default=None),
    'max_surface_y_rain': max([v['y'] for v in grid.values() if v['precip'] == 'rain'], default=None),
    'unresolved_columns': count(lambda v: v['precip'] == 'unresolved'),
}
for v in grid.values():
    summary['biome_counts'][v['biome']] = summary['biome_counts'].get(v['biome'], 0) + 1
    summary['precip_counts'][v['precip']] = summary['precip_counts'].get(v['precip'], 0) + 1

# ---------- choose the house: closest to a rain-class land column, must verify >= 0.9 ----------
rain_cols = [(x, z) for (x, z), v in grid.items() if v['precip'] == 'rain' and 'ocean' not in v['biome'] and 'river' not in v['biome']]
best = None
for h in houses:
    if h['match_fraction'] < 0.9 or not h['bb_equals_template_transform'] or not h['_doors'] or not h['_inside']: continue
    bb = h['BB']; cxh, czh = (bb[0] + bb[3]) / 2, (bb[2] + bb[5]) / 2
    dist = min((math.hypot(x - cxh, z - czh) for x, z in rain_cols), default=1e9)
    key = (round(dist, 1), h['piece'])
    if best is None or key < best[0]: best = (key, h)
assert best, 'no verified house'
dist_rain, H = best[0][0], best[1]
cells, inside, doors = H['_cells'], H['_inside'], H['_doors']
door_pos = doors[0][0]; door_state = doors[0][1]
inside.sort(key=lambda c: (c[0] - door_pos[0]) ** 2 + (c[2] - door_pos[2]) ** 2)
floor = inside[0]
# Exterior side: the door sits in a wall; the exterior is perpendicular to that wall, on the side with open sky.
outside = None
for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    pass
wall_neighbors = []
for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    wx, wz = door_pos[0] + dx, door_pos[2] + dz
    wb = block(wx, door_pos[1], wz)['Name']
    if is_solid(wb): wall_neighbors.append({'xyz': [wx, door_pos[1], wz], 'block': wb})
wall_axis = None
for wn in wall_neighbors:
    wall_axis = 'x' if wn['xyz'][0] != door_pos[0] else 'z'
# The interior floor cell lies on the interior side; the exterior is the opposite side of the wall.
if wall_axis == 'x': ext = (0, -1 if floor[2] > door_pos[2] else 1)
else: ext = (-1 if floor[0] > door_pos[0] else 1, 0)
outside = None
for k in range(1, 13):  # first open-sky ground column outside (not under eaves, leaves or a roof)
    ox_, oz_ = door_pos[0] + ext[0] * k, door_pos[2] + ext[1] * k
    t_ = top(ox_, oz_)
    if t_ is not None and t_ <= floor[1] + 2 and block(ox_, t_ - 1, oz_)['Name'] not in ('minecraft:water',):
        outside = (ox_, oz_); break
column = []
for yy in range(floor[1] + 1, floor[1] + 14):
    b = block(floor[0], yy, floor[2])['Name']
    if b != 'minecraft:air': column.append([yy, b])
roof_top = top(floor[0], floor[2]) - 1
digest_cells = sorted((x, y, z, s_['Name'], json.dumps(s_.get('Properties', {}), sort_keys=True))
                      for (x, y, z), s_ in cells.items())
world_digest = hashlib.sha256()
for (x, y, z) in sorted(cells):
    b = block(x, y, z)
    world_digest.update(f"{x},{y},{z},{b['Name']},{json.dumps(b.get('Properties', {}), sort_keys=True)}\n".encode())
glass = [list(pos) for pos, s_ in cells.items() if 'pane' in s_['Name'] or s_['Name'].endswith('glass')][:6]
house = {
    'piece_index': H['piece'], 'template': H['location'], 'rotation': H['rotation'], 'BB': H['BB'],
    'template_match_fraction': H['match_fraction'], 'bb_equals_template_transform': H['bb_equals_template_transform'],
    'mismatch_top': H['mismatch_top'],
    'door_lower': {'xyz': list(door_pos), 'block': door_state['Name'], 'props_template': door_state['Properties'],
                   'world_block': block(*door_pos)},
    'door_upper_world': block(door_pos[0], door_pos[1] + 1, door_pos[2]),
    'wall_blocks_beside_door': wall_neighbors,
    'window_cells_template': glass,
    'interior_floor': {'xyz': list(floor), 'floor_block_world': block(*floor)['Name'],
                       'air_above_world': [block(floor[0], floor[1] + 1, floor[2])['Name'], block(floor[0], floor[1] + 2, floor[2])['Name']],
                       'blocks_above_to_roof_world': column, 'motion_blocking_roof_top_y': roof_top,
                       'roof_top_block': block(floor[0], roof_top, floor[2])['Name'],
                       'block_above_roof_top': block(floor[0], roof_top + 1, floor[2])['Name']},
    'exterior_probe': None, 'exterior_direction_dxdz': list(ext),
    'distance_to_nearest_rain_column_blocks_cell_level': dist_rain,
    'world_digest_sha256_template_cells': world_digest.hexdigest(),
}
if outside:
    ty = top(*outside)
    house['exterior_probe'] = {'xz': list(outside), 'surface_block': block(outside[0], ty - 1, outside[1])['Name'],
                               'surface_y': ty - 1, 'above': block(outside[0], ty, outside[1])['Name'],
                               'biome_cell': biome_at(outside[0], ty - 1, outside[1]),
                               'precip_cell_level': precip(biome_at(outside[0], ty - 1, outside[1]), ty - 1)}
# nearest rain column to the chosen house
cxh, czh = (H['BB'][0] + H['BB'][3]) // 2, (H['BB'][2] + H['BB'][5]) // 2
nr = min(rain_cols, key=lambda c: math.hypot(c[0] - cxh, c[1] - czh))
house['nearest_rain_column'] = {'xz': list(nr), **grid[nr]}

for h in houses:
    for k in ('_cells', '_inside', '_doors', '_size'): h.pop(k, None)
res = {
    'seed': seed, 'generator': 'vanilla Minecraft 1.21.1 (world_version 3955), unmodified client.jar sha1 ' + vserver.CLIENT_JAR_SHA1,
    'gen': gen, 'village_start_chunk': [cx, cz], 'village_bb': village_bb, 'pieces_total': len(pieces),
    'piece_locations': sorted({p['location'] for p in plist if p['location']}), 'pieces': plist,
    'houses_checked': houses, 'chosen_house': house, 'survey': summary,
}
os.makedirs(out, exist_ok=True)
json.dump(res, open(f'{out}/analysis.json', 'w'), indent=1, default=str)

# ---------- small PNG (1 px = 4x4 blocks, x3) ----------
W = (x1 - x0 + 1) // 4; Hh = (z1 - z0 + 1) // 4; S = 3
COL = {'snow': (245, 245, 250), 'rain': (60, 120, 220), 'none': (130, 130, 130), 'unresolved': (220, 160, 40)}
img = [[(30, 30, 30)] * (W * S) for _ in range(Hh * S)]
for (x, z), v in grid.items():
    c = COL[v['precip']]
    if 'ocean' in v['biome'] or 'river' in v['biome']: c = tuple(int(q * 0.55) for q in c)
    px, pz = (x - x0) // 4, (z - z0) // 4
    for a in range(S):
        for b in range(S): img[pz * S + b][px * S + a] = c
def rect(bb, c):
    for x in range(bb[0], bb[3] + 1):
        for z in (bb[2], bb[5]):
            px, pz = (x - x0) // 4 * S, (z - z0) // 4 * S
            if 0 <= pz < Hh * S and 0 <= px < W * S: img[pz][px] = c
    for z in range(bb[2], bb[5] + 1):
        for x in (bb[0], bb[3]):
            px, pz = (x - x0) // 4 * S, (z - z0) // 4 * S
            if 0 <= pz < Hh * S and 0 <= px < W * S: img[pz][px] = c
for p in pieces: rect(p['BB'], (200, 40, 40))
rect(H['BB'], (255, 220, 0))
def png(path, rows):
    h, w = len(rows), len(rows[0])
    raw = b''.join(b'\x00' + bytes(v for px in r for v in px) for r in rows)
    def ch(t, d): c = struct.pack('>I', len(d)) + t + d; return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw, 9)) + ch(b'IEND', b''))
png(f'{out}/precipitation-map.png', img)
# ---------- ASCII layers of the generated house (world blocks, not the template) ----------
SYM = [('air', ' '), ('stairs', 'S'), ('slab', 's'), ('door', 'D'), ('glass_pane', 'G'), ('glass', 'g'), ('lantern', 'l'), ('torch', 't'),
       ('bed', 'B'), ('leaves', 'v'), ('stripped_spruce_log', 'L'), ('spruce_log', 'O'), ('spruce_planks', 'P'), ('cobblestone', 'C'),
       ('snow', 'n'), ('grass_block', 'r'), ('dirt', 'd'), ('chest', 'h'), ('crafting', 'k'), ('furnace', 'f'), ('barrel', 'b'),
       ('fence', '|'), ('carpet', 'c'), ('pot', 'p'), ('stone', 'o'), ('planks', 'P')]
def sym(n):
    n = n.split(':')[1]
    if n.endswith('air'): return ' '
    for k, c in SYM[1:]:
        if k in n: return c
    return '?'
bb = H['BB']; lines = []; used = {}
for yy in range(bb[1] - 1, bb[4] + 3):
    lines.append(f'y={yy}' + ('  (interior floor row below this)' if yy == floor[1] + 1 else ''))
    for zz in range(bb[2] - 1, bb[5] + 2):
        row = ''
        for xx in range(bb[0] - 1, bb[3] + 2):
            n = block(xx, yy, zz)['Name']; c = sym(n); used.setdefault(c, set()).add(n.split(':')[1]); row += c
        lines.append(row)
    lines.append('')
hdr = [f'x {bb[0]-1}..{bb[3]+1} (columns, west->east), z {bb[2]-1}..{bb[5]+1} (rows, north->south); world blocks of piece {H["piece"]} {H["location"]}']
hdr += [f'  {c!r}: {sorted(v)}' for c, v in sorted(used.items())]
open(f'{out}/house-layers.txt', 'w').write('\n'.join(hdr + [''] + lines))
print(json.dumps({k: res[k] for k in ('pieces_total', 'survey')}, indent=1))
print(json.dumps(house, indent=1, default=str))
