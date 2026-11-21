"""Independently verify saved display-water captures without accepting appearance."""
import csv
import argparse
import json
import math
from pathlib import Path
from zipfile import ZipFile

from display_water_runtime import OUT, PACKS, SCENES, WORLD_ID, require
from report import check_png, metrics
EXPECTED_SIZE = [1600, 900]


def audit():
    rows = []
    for role in PACKS:
        directory = OUT / (role+'-runtime')
        manifest = json.loads((directory / 'run.json').read_text())
        require(manifest['world_id'] == WORLD_ID and manifest['shader_active'] and not manifest['shader_fallback'], 'Runtime identity/activation differs')
        require(manifest['resolution'] == EXPECTED_SIZE and 'NVIDIA' in manifest['gl_renderer'], 'Unexpected runtime dimensions/renderer')
        for scene in SCENES:
            saved = json.loads((directory / (scene+'.json')).read_text())
            require(saved['pack_sha256'] == manifest['pack_sha256'], 'Scene pack identity differs')
            require(saved['window_focused'], 'Capture is unfocused')
            check_png(directory / (scene+'.png'), EXPECTED_SIZE)
            with (directory / (scene+'.csv')).open() as source:
                raw = list(csv.DictReader(source))
            require(bool(raw), 'Raw intervals missing')
            values = []
            for index, interval in enumerate(raw):
                nanoseconds = int(interval['ns'])
                milliseconds = float(interval['ms'])
                require(int(interval['frame']) == index and nanoseconds > 0 and math.isfinite(milliseconds), 'Invalid raw interval')
                require(abs(milliseconds-nanoseconds/1e6) < 1e-9, 'Raw units differ')
                values.append(milliseconds)
            recomputed = metrics(values)
            for name, value in recomputed.items():
                require(math.isclose(value, saved[name], rel_tol=1e-9, abs_tol=1e-7), 'Metric differs: '+name)
            rows.append(dict(role=role, scene=scene, **recomputed))
    with ZipFile(OUT / PACKS['control']) as archive:
        control = {name: archive.read(name) for name in archive.namelist()}
    candidate_path = Path(__file__).resolve().parents[1] / 'dist' / PACKS['candidate']
    with ZipFile(candidate_path) as archive:
        candidate = {name: archive.read(name) for name in archive.namelist()}
    require(set(candidate)-set(control) == {'shaders/composite1.vsh', 'shaders/composite1.fsh', 'shaders/composite2.vsh', 'shaders/composite2.fsh'}, 'Unexpected comparison archive difference')
    require(all(candidate[name] == blob for name, blob in control.items()), 'Common shader/optical source changed')
    result = dict(runtimeScenesVerified=12, strictPNGsVerified=12, rawIntervalsVerified=sum(row['frames'] for row in rows),
                  comparisonCommonSourcesExact=True, rows=rows, naturalAppearanceAccepted=False,
                  fullGoalAchieved=False, controlledPackOnlyTimingComparison=False,
                  limitations=[str(EXPECTED_SIZE)+' quality run, not 1440p benchmark', 'Short five-second sampling',
                               'Video encoder overlaps selected scenes', 'Cloud and wave phase not frozen',
                               'New C9 live storage not independently queried'])
    with (OUT / 'runtime-audit.json').open('x') as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', choices=['initial', 'solar-tir-v2'], default='initial')
    args = parser.parse_args()
    if args.packet == 'solar-tir-v2':
        OUT = OUT / 'solar-tir-v2'
        EXPECTED_SIZE = [1600, 800]
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-SolarTIR-v2-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-SolarTIR-v2-2026-10-11.zip'}
    audit()
