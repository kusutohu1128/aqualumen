#!/usr/bin/env python3 -I
"""Condense site/analysis.json + site/transect.json (+ screen logs) into the small machine-readable site-receipt.json.
usage: make_receipt.py   (run from the report directory)"""
import hashlib, json, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = json.load(open(f'{R}/site/analysis.json')); t = json.load(open(f'{R}/site/transect.json'))
H = a['chosen_house']; S = a['survey']; rows = {r['x']: r for r in t['rows']}
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def screen(p):
    out = []
    for l in open(p):
        if l.startswith('{'):
            r = json.loads(l); out.append({'seed': r['seed'], 'village_xz': r['village'][:2] if r.get('village') else None,
                                           'village_dist_from_origin': r['village'][2] if r.get('village') else None,
                                           'nearest_rain_biome_blocks': r.get('nearest_rain_biome_blocks')})
    return out
def stand(x, label, y):
    r = rows[x]
    return {'label': label, 'feet_block': [x, y, r['z']], 'biome_at_y70_and_67': r['by_y'], 'precip': r['precip']}
others = [{'piece': h['piece'], 'template': h['location'].split('/')[-1], 'match_fraction': h['match_fraction'],
           'interior_floor_cells_by_heuristic': h['interior_floor_cells']} for h in a['houses_checked']]
rec = {
 'schema': 'aqualumen-site-receipt/1', 'created': '2026-11-21',
 'seed': {'value': 20261139, 'is_second_seed': True, 'first_seed_in_lab_world_AqualumenNaturalV2': 308060,
          'seed_origin': 'pre-registered sequential scan 20261121.. (see selection); not hand-picked'},
 'game': {'version': '1.21.1', 'world_version': 3955, 'level_type': 'minecraft:normal', 'generate_structures': True,
          'generator': 'unmodified Mojang client.jar net.minecraft.server.Main (headless dedicated server, 127.0.0.1, offline, CPU only)',
          'client_jar_sha1': a['generator'].split('sha1 ')[1], 'client_jar_sha1_matches_mojang_meta': True,
          'java': 'Microsoft OpenJDK 21.0.7 (Prism java-runtime-delta)', 'mods': 'none', 'shaders': 'none', 'gpu': 'not used'},
 'selection': {'rule': 'first seed with /locate structure village_snowy <=1500 blocks from 0,0 AND nearest rain-class biome (taiga/forest/plains/birch/flower/old-growth/meadow/sunflower/dark forest) <=260 blocks from the village centre by /locate biome (32-block step)',
               'batch1_seeds_20261121_20261132': 'no seed accepted (best 273)', 'batch2_seeds_20261133_20261139': 'accepted at the 19th seed tried',
               'screen_logs': ['screen-batch1.log', 'screen-batch2.log']},
 'village': {'structure': 'minecraft:village_snowy', 'locate_xz': a['gen']['village_locate'], 'start_chunk': a['village_start_chunk'],
             'bb': a['village_bb'], 'pieces': a['pieces_total'], 'town_center': 'snowy_meeting_point_3 at -912,67,576',
             'verified_from_saved_chunks': True},
 'house': {'piece_index': H['piece_index'], 'template': H['template'], 'rotation': H['rotation'], 'bb': H['BB'],
           'template_cells_match_fraction': H['template_match_fraction'], 'bb_equals_template_transform': H['bb_equals_template_transform'],
           'mismatch_only': H['mismatch_top'], 'mismatch_meaning': 'template air -> snow layer / spruce leaves (post-structure vanilla features)',
           'world_digest_sha256_of_template_cells': H['world_digest_sha256_template_cells'],
           'door_lower': H['door_lower']['xyz'], 'door_block': H['door_lower']['block'],
           'wall_beside_door': H['wall_blocks_beside_door'], 'window_pane': H['window_cells_template'],
           'interior_floor_block_xyz': H['interior_floor']['xyz'], 'interior_floor_block': H['interior_floor']['floor_block_world'],
           'interior_stand_feet_block': [H['interior_floor']['xyz'][0], H['interior_floor']['xyz'][1] + 1, H['interior_floor']['xyz'][2]],
           'roof_column_above_floor': H['interior_floor']['blocks_above_to_roof_world'], 'roof_top_y': H['interior_floor']['motion_blocking_roof_top_y'],
           'roof_top_block': H['interior_floor']['roof_top_block'], 'exterior_open_sky': H['exterior_probe'],
           'roof_materials_in_pack_block_properties': {'spruce_slab:type=bottom': 10301, 'spruce_planks': 10602, 'stripped_spruce_log': 'unmapped', 'snow': 'unmapped'},
           'other_houses_checked': others},
 'precipitation': {'rule': 'Biome.has_precipitation && temperature<0.15 -> snow else rain, evaluated at the block position (y<=80 so no height term)',
                   'snowy_plains': {'temperature': 0.0, 'has_precipitation': True, 'class': 'snow'},
                   'plains': {'temperature': 0.8, 'has_precipitation': True, 'class': 'rain'},
                   'natural_snow_in_generated_chunks': {'snow_class_columns': S['snow_precip_columns'], 'snow_class_with_snow_cover': S['snow_cover_on_snow_precip_columns'],
                                                        'rain_class_columns': S['rain_precip_columns'], 'rain_class_with_snow_cover': S['snow_cover_on_rain_precip_columns'],
                                                        'grid': '4x4-block cells over the 289 generated chunks'}},
 'boundary': {'method': 'genuine in-game per-block biome lookup (execute if biome) on a 131-column straight line, queried at two heights',
              'line_from': t['start'], 'line_to_nearest_rain_column': t['end'], 'columns': t['columns'],
              'class_changes_among_resolved_columns': sum(1 for u, v in zip([r['precip'] for r in t['rows'] if r['precip']], [r['precip'] for r in t['rows'] if r['precip']][1:]) if u != v), 'unresolved_height_dependent_columns': sum(1 for r in t['rows'] if not r['precip']), 'transition_snow_to_rain_toward_west': [rows[-1003]['x'], rows[-1007]['x']],
              'height_dependent_columns_x': [-1004, -1005], 'height_dependent_note': 'x=-1004,-1005: plains at y=67 but snowy_plains at y=70; unusable as stand points',
              'distance_house_door_to_transition_blocks': abs(t['start'][0] - rows[-1003]['x']),
              'stand_points': [stand(-996, 'snow side, far', 67), stand(-1003, 'snow side, next to boundary', 68),
                               stand(-1007, 'rain side, next to boundary', 68), stand(-1014, 'rain side, far', 69)]},
 'reproducibility': {'village_pieces_identical_across_two_independent_generations': True, 'pieces_sha256': hashlib.sha256(json.dumps(
                         [(p['location'], p['BB'], p['rotation'], p['pos']) for p in a['pieces']]).encode()).hexdigest(),
                     'house_cell_digest_identical': True,
                     'surface_decoration_columns_differing_between_runs': {'differing': 86, 'of': 73984, 'inside_village_bb': 0, 'min_distance_to_house_blocks': 73,
                                                                         'kind': 'short_grass vs snow layer'}},
 'unverified': ['no Minecraft client, Iris or GPU was run: biome_precipitation values at the stand points are derived (Iris 1.8.8 bytecode + biome JSON), not read from a client',
                'Level.isRainingAt / random-tick snow accumulation could not be exercised: a player-less server gives no entity or random ticks (tools/negative)',
                'cell-level survey (4 blocks) vs per-block lookup differ near the boundary; only the 131-column line is per-block',
                'columns with surface y>80 (ice spikes, 560 of 4624 cells) are unresolved for temperature'],
 'tool_sha256': {f: sha(f'{R}/tools/{f}') for f in ['vserver.py', 'screen_seeds.py', 'gen_site.py', 'analyze_site.py', 'transect_probe.py', 'mcnbt.py']},
 'world_files': 'generated in /tmp only; not copied into the repository and not for distribution',
}
json.dump(rec, open(f'{R}/site-receipt.json', 'w'), indent=1, ensure_ascii=False)
print(os.path.getsize(f'{R}/site-receipt.json'), 'bytes')
