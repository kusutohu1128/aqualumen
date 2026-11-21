"""New CPU source-boundary integral evidence from qualified saved native inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import water_source_boundary_audit as saved
import water_supported_conditioned as model
import water_observed_plane_integral as candidate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'
BASE = ROOT / 'reports/2026-10-06-water-source-boundary'


def run(output, fade_knots=False):
    assert not (OUT / output).exists()
    captures = {}
    for order in (8, 12):
        capture = BASE / f'fixed-observed-{order}-01'
        source = BASE / f'fixed-observer-{order}-v1'
        captures[order] = saved.audit(capture, source)
    path = BASE / 'fixed-observed-12-01'
    raw = saved.records(path / 'green/observer-nodes.bin')[0]
    state = json.loads((path / 'green/observer-actual-inputs/state.json').read_text())
    p = model.t.prepare(raw[10][:3], raw[11][:3], raw[12][:3], raw[10][3])
    matrix, projection = (state['matrices'][key] for key in ('gbufferModelView', 'gbufferProjection'))
    results = []
    for order in (4, 8, 12, 16, 24, 32, 48, 64, 96, 128):
        modes = []
        for partitioned, edge in ((False, False), (False, True), (True, False), (True, True)):
            modes.append(candidate.integrate(p, matrix, projection, raw[2][:3], state['planeViewDistance'],
                                             order, partitioned, edge, fade_knots=fade_knots))
        results.append(dict(order=order, modes=modes))
        print('FINISHED CPU first-plane order', order, flush=True)
    record = dict(schema='aqualumen-observed-plane-integral-v1',
        rawNormal=raw[10][:3], rawView=raw[11][:3], rawCovariance=raw[12][:3], eta=raw[10][3],
        edgeKnotsSplit=fade_knots,
        algorithmSHA256={name: hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest()
            for name in ('water_observed_plane_partition.py', 'water_observed_plane_integral.py', 'water_observed_plane_run.py')},
        origin=raw[2][:3], actualState=state,
        actualNodeCaptureSHA256=hashlib.sha256((path / 'green/observer-nodes.bin').read_bytes()).hexdigest(),
        results=results, capturedGPU={str(k): {name: value[name] for name in
            ('capturedGreen', 'sameNodesTruePlaneGreen', 'unitCoefficient', 'actualHits', 'actualMisses')}
            for k, value in captures.items()},
        GaussianProbabilityFitted=False, rawOpticsChanged=False,
        sourceConvergenceAccepted=False, nativeAlgorithmPortExecuted=False,
        productionIncluded=False, IrisAccepted=False, temporalAccepted=False,
        fullGoalAchieved=False,
        scope='CPU diagnostic known observed-plane window term from actual native n/v/C/eta, matrices/origin. Exact first plane and optional exact-projection edge fade are NOT the legacy SSR confidence/path functional or total unobserved-world illumination.')
    with (OUT / output).open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
    subprocess.run(['rtk', 'proxy', 'python3', '-m', 'unittest', 'discover', '-s', 'tools',
                    '-p', 'test_water_observed_plane_partition.py'], cwd=ROOT, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', choices=('integral-results-v1-replay.json', 'integral-results-v2.json'), required=True)
    parser.add_argument('--fade-knots', action='store_true')
    args = parser.parse_args()
    run(args.output, args.fade_knots)
