"""Read and preserve completed actual1440p run with the retained strict reader."""
import json
from pathlib import Path
import shutil
import report
from water_path_precision_prepare import OUT, GAME
from water_path_precision_iris_setup import PACK, sha

RUN = 'pathprecision-refine12-1440-20261006-v1'


def collect():
    original = GAME / 'aqualumen-benchmark/runs' / RUN
    run, rows = report.load_run(original)
    setup = json.loads((OUT / 'iris-setup.json').read_text())
    assert run['run_id'] == RUN and run['pack_name'] == PACK
    assert run['pack_sha256'] == setup['packSHA256']
    assert run['world_id'] == setup['testWorldUUID'] and run['seed'] == 308060
    assert run['expected_resolution'] == [2560, 1440] and run['render_chunks'] == 12 and run['simulation_chunks'] == 6
    assert 'RTX 3080 Ti' in run['gl_renderer'] and 'NVIDIA' in run['gl_version']
    assert run['mods']['iris'] == '1.8.8+mc1.21.1'
    assert run['mods']['aqualumen_physics'] == '0.3.0'
    assert run['mods']['aqualumen_benchmark'] == '0.3.9'
    assert all(row['window_focused'] is True for row in rows)
    target = OUT / 'iris1440-run-v1'
    assert not target.exists()
    shutil.copytree(original, target)
    assert {str(p.relative_to(original)): sha(p) for p in original.rglob('*') if p.is_file()} == {
        str(p.relative_to(target)): sha(p) for p in target.rglob('*') if p.is_file()}
    record = dict(schema='aqualumen-path-precision-iris1440-audit-v1', pack=PACK, packSHA256=setup['packSHA256'],
                  strictOriginalReportReaderPassed=True, actualNvidiaIrisActiveWithoutFallback=True,
                  worldUUID=run['world_id'], seed=run['seed'], allPNGsComplete2560x1440=True,
                  allRawFrameIntervalsRecomputed=True, allCaptureWindowsFocused=True,
                  sceneCount=len(rows), intervalCount=sum(r['frames'] for r in rows),
                  scenes=[{k:r[k] for k in ('scenario','workload','frames','mean_fps','p99_ms','max_ms','window_focused')} for r in rows],
                  scriptedBoatContactInputObserved=True, vanillaRowingAccepted=False,
                  nativeSSRPrecisionGateTransferredToIrisPixels=False, causalPackABCompared=False,
                  motionAccepted=False, naturalAppearanceAccepted=False, physicalEnergyAccepted=False,
                  FPSFloorIsReleaseGate=False, fullGoalAchieved=False)
    with (OUT / 'iris1440-audit.json').open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == '__main__':
    collect()
