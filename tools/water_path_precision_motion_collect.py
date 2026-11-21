"""Separate900p recording evidence; never bypass the original1440p reader."""
import csv
import json
import math
from pathlib import Path
import shutil
import report
from water_path_precision_prepare import OUT, GAME
from water_path_precision_iris_setup import PACK, sha


def collect():
    name = 'pathprecision-refine12-motion900-20261006-v1'
    original = GAME/'aqualumen-benchmark/runs'/name
    run = json.loads((original/'run.json').read_text())
    done = json.loads((original/'complete.json').read_text())
    row = json.loads((original/'moving-view.json').read_text())
    setup = json.loads((OUT/'iris-setup.json').read_text())
    assert done['run_id'] == run['run_id'] == name and done['status'] == 'complete'
    assert run['scenarios'] == ['moving-view'] and run['expected_resolution'] == [1600,900]
    assert run['pack_name'] == PACK and run['pack_sha256'] == setup['packSHA256']
    assert run['world_id'] == setup['testWorldUUID'] and run['seed'] == 308060
    assert run['shader_active'] and not run['shader_fallback'] and 'RTX 3080 Ti' in run['gl_renderer']
    assert row['shader_active'] and not row['shader_fallback'] and row['pack_sha256'] == run['pack_sha256']
    assert row['world_id'] == run['world_id'] and row['resolution'] == row['framebuffer_resolution'] == [1600,900]
    assert row['window_focused'] and row['camera_lock'] and row['camera_follows_local_player']
    assert row['player_dimension'] == 'minecraft:overworld' and row['sample_seconds_actual'] >= 14.9
    assert abs(row['actual_camera_rotation'][1] - row['expected_camera_rotation'][1]) <= .05
    report.check_png(original/'moving-view.png', [1600,900])
    with (original/'moving-view.csv').open() as f:
        values = [float(r['ms']) for r in csv.DictReader(f)]
    assert len(values) >= 10 and all(math.isfinite(v) and v>0 for v in values)
    for key,value in report.metrics(values).items():
        assert abs(row[key]-value) <= max(.001, abs(value)*.00001)
    video = json.loads((OUT/'moving-view-video-metadata.json').read_text())
    assert len(video['streams']) == 1
    stream = video['streams'][0]
    assert (stream['width'],stream['height'],stream['r_frame_rate'],stream['nb_read_frames']) == (1600,900,'24/1','480')
    assert float(video['format']['duration']) == 20
    for t in (0,8,16):
        report.check_png(OUT/f'moving-view-frame-{t:02d}.png', [1600,900])
    target = OUT/'iris900-motion-run-v1'
    assert not target.exists()
    shutil.copytree(original,target)
    assert {str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()} == {
        str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}
    receipt = dict(schema='aqualumen-path-precision-motion-capture-v1', packSHA256=run['pack_sha256'],
        worldUUID=run['world_id'], sourceFullWindowSize=[1600,900], videoFrames=480, videoSeconds=20,
        sourceWindow=62914567, display=':1.0', sourceWindowPosition=[96,164], rootDisplaySize=[1920,1080],
        sourceWindowFullyWithinDisplay=True, decodedSampleFramesRootInspected=[0,8,16],
        completeQualifiedBenchmarkCameraRun=True, recordedCSVRecomputed=True,
        videoRecordingOverheadExcludedFrom1440pRun=True, actual1440pBenchmark=False,
        wholeClipTemporalNaturalnessAccepted=False, contactPropagationAccepted=False,
        sameFrameNativePNGVideoPixelEqualityProven=False, physicalEnergyAccepted=False, fullGoalAchieved=False)
    with (OUT/'motion900-audit.json').open('x') as f:
        json.dump(receipt,f,indent=2,sort_keys=True)
    print(json.dumps(receipt,indent=2,sort_keys=True))


if __name__ == '__main__':
    collect()
