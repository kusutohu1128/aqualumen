"""In-game check of the new base packs with the existing guarded private-client harness.

usage: python3 capture.py birch LABEL | python3 capture.py gold {Faceted,Control} LABEL
"""
import json, re, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
reports = here.parent


def install(rp, sha):
    def prepare(game, out, mods):
        target = game / 'resourcepacks' / rp.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(rp, target)
        opt = game / 'options.txt'
        line = 'resourcePacks:' + json.dumps(['vanilla', 'file/' + rp.name], separators=(',', ':'))
        data, n = re.subn(r'(?m)^resourcePacks:.*$', lambda _: line, opt.read_text())
        assert n == 1
        opt.write_text(data)
        mods['resourcePackSha256'] = sha(target)
    return prepare


def birch(label):
    sys.path.insert(0, str(reports / '2026-11-23-torch-density'))
    import measure_density as m
    g = m.guarded
    fixed = dict(backend='vgl', size='2560x1440', settle='1', stages='birch-0,birch-1', glcache=str(g.BUILD / 'driver-cache'))
    fixed.update({'period-ticks': '800', 'compiler-mod': str(m.ROOT / 'dist/aqualumen-lighting-compiler-0.3.0.jar')})
    g.launch(m.ROOT / 'dist' / g.FACE_PREVIEW[0], label, 'off', fixed, here, m.TorchCounts,
             install(here / 'Aqualumen-Birch-Base-32x.zip', g.sha))


def gold(variant, label):
    import importlib.util
    spec = importlib.util.spec_from_file_location('gold_scene_capture', reports / 'interactive-materials/gold-scene/capture.py')
    scene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene)
    guard = scene.guard
    fixed = dict(backend='vgl', size='1280x720', settle='1', stages=','.join(scene.STAGES), glcache=str(guard.BUILD / 'driver-cache'))
    fixed.update({'period-ticks': '264', 'compiler-mod': str(scene.repo / 'dist/aqualumen-lighting-compiler-0.3.0.jar')})
    guard.launch(reports / 'interactive-materials/gold/Aqualumen-1.9.0-gold-facets.zip', label, 'off', fixed, here, scene.Scene,
                 install(here / f'Aqualumen-Gold-Base-{variant}-32x.zip', guard.sha))


if __name__ == '__main__':
    if sys.argv[1] == 'birch':
        birch(sys.argv[2])
    else:
        assert sys.argv[2] in ('Faceted', 'Control')
        gold(sys.argv[2], sys.argv[3])
