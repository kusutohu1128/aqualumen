"""Recompute the normal-play timing table from Minecraft render-tail intervals."""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
PACK=HERE.parents[1]/'dist/Aqualumen-1.0.0.zip'
capture=HERE/'final-play/capture'
run=json.loads((capture/'run.json').read_text())
complete=json.loads((capture/'complete.json').read_text())
sha=hashlib.sha256(PACK.read_bytes()).hexdigest()
assert sha==run['pack_sha256'] and run['shader_active'] and not run['shader_fallback']
assert run['framebuffer_resolution']==[2560,1440] and run['render_chunks']==12 and run['simulation_chunks']==6
assert complete['status']=='complete' and complete['scenarios']==run['scenarios']
assert complete['fixture_cleanup_complete'] and len(run['scenarios'])==17
assert 'RTX 3080 Ti' in run['gl_renderer'] and not run['native_motion_capture_active']
results=[]
for scene in run['scenarios']:
    row=json.loads((capture/(scene+'.json')).read_text())
    with (capture/(scene+'.csv')).open() as data:
        ns=[int(sample['ns']) for sample in csv.DictReader(data)]
    assert ns and min(ns)>0 and row['frames']==len(ns)
    assert row['window_focused'] and row['camera_follows_local_player'] and row['pack_sha256']==sha
    avg=1e9*len(ns)/sum(ns)
    p99=sorted(ns)[math.ceil(len(ns)*.99)-1]*1e-6
    worst=max(ns)*1e-6
    assert abs(row['mean_fps']-avg)<1e-5 and abs(row['p99_ms']-p99)<1e-6 and abs(row['max_ms']-worst)<1e-6
    if 'underwater_up' in row:
        state=row['underwater_up']
        assert state['camera_submersion_type']=='WATER' and state['camera_eye_match'] and state['actual_world_time']==6000
    results.append(dict(scene=scene,frames=len(ns),meanFPS=avg,meanMs=sum(ns)*1e-6/len(ns),p99Ms=p99,worstMs=worst,
                        over16_667ms=sum(t>16667000 for t in ns)))
with (HERE/'frame-times.json').open('x') as out:
    json.dump(dict(renderer=run['gl_renderer'],pack=sha,framebuffer=run['framebuffer_resolution'],rows=results),out,indent=2)
print('Verified',sum(r['frames'] for r in results),'render-tail intervals across',len(results),'scenes')
