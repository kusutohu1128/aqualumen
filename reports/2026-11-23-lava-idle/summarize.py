"""Verify the actual compiler input and compute signed differences of paired window means."""
import argparse
import difflib
import json
from diagnostics import OUT, R, FACTORS

RUNS = R / 'runs'
CONTROLS = ('quad/final', 'dispatch/begin1')


def receipt(label):
    for tail in ('-retry2', '-retry1', ''):
        folder = RUNS / (label + tail)
        if folder.exists():
            data = json.loads((folder / 'summary.json').read_text())
            assert data['validated'] and data['label'] == folder.name
            return data
    raise FileNotFoundError(label)


def sources():
    result = {}
    for name in ('stable', 'p3', 'comp-pragma', 'comp-default', 'def-five', 'def-four'):
        s = receipt('gp-idle-src-' + name)
        assert s['pragma'] == {'composite': name not in ('stable', 'comp-default'), 'deferred': name != 'stable'}
        outputs = {p: [x.split(' format ')[1] for x in rows if x.startswith('out ')] for p, rows in s['fbo'].items()}
        assert outputs['deferred'] == [str(x)+' size 2560x1440' for x in
              ([34836,34836,34842,34842] + ([] if name in ('stable','def-four') else [33325]))]
        assert outputs['composite'] == ['34836 size 2560x1440']
        result[name] = {k: s[k] for k in ('label', 'sources', 'pragma', 'fbo')}
    def read(key, filename):
        return (OUT / 'submitted' / result[key]['label'] / filename).read_text()
    contrasts = [('stable', 'p3', None), *FACTORS.values()]
    patches=[]
    for before, after, target in contrasts:
        for program in ('deferred','composite'):
            for ext in ('.vsh','.fsh'):
                filename = program+ext
                a,b = read(before,filename),read(after,filename)
                if (target and target != program) or ext == '.vsh':
                    assert a == b, (before,after,filename)
                if before == 'comp-pragma' and program == 'composite':
                    assert a.replace('#pragma optionNV(inline 128)\n','').replace('aqualumenAreaSourceLightingIdleWater','waterIncidentIrradiance') == b
                diff = ''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),
                                                    fromfile=before+'/'+filename,tofile=after+'/'+filename))
                (OUT/'submitted'/f'{before}_{after}_{filename}.diff').write_text(diff)
                if diff: patches.append(diff)
    (R/'submitted.diff').write_text(''.join(patches))
    return result


def compare(factor):
    control,diagnostic,program = FACTORS[factor]
    result = {'control':control, 'diagnostic':diagnostic, 'program':program, 'pairs':{}}
    for side in ('a','b'):
        a,b = [receipt(f'gp-idle-{prefix}-{factor}-{side}') for prefix in ('ctl','d')]
        assert a['meanMs'].keys() == b['meanMs'].keys()
        delta = {k: b['meanMs'][k] - v for k,v in a['meanMs'].items()}
        result['pairs'][side] = {
            'controlRun':a['label'], 'diagnosticRun':b['label'], 'controlMs':a['meanMs'],
            'diagnosticMs':b['meanMs'], 'deltaMs':delta,
            'controlChecks':{k: abs(delta[k]) <= max(.1,.1*a['meanMs'][k]) for k in CONTROLS}}
    return result


def report():
    from diagnostics import digest, ROOT
    comparisons = {factor:compare(factor) for factor in FACTORS}
    full_sources = sources()
    accepted, failures = [], []
    for path in sorted(RUNS.glob('*/complete.json')):
        data = json.loads(path.read_text())
        before_after = json.loads((path.parent/'preflight.json').read_text())
        if before_after['labBefore'] != before_after['labAfter'] or before_after['foreignObservations']:
            raise ValueError(f'preflight failed for {path.parent.name}')
        assert data['originalWorldAndConfigUnchanged']
        if data['complete']:
            window = json.loads((path.parent/'summary.json').read_text())
            arm={k:window[k] for k in ('label','mode','packSha256')}
            arm['frames']={k:v['frames'] for k,v in window['scenes'].items()} if 'scenes' in window else {window['scene']:window['frames']}
            accepted.append(arm)
        else:
            failures.append({'label':path.parent.name,'failure':data['failure']})
    dist = json.loads((OUT/'dist-before.json').read_text())
    assert dist == {p.relative_to(ROOT/'dist').as_posix():digest(p) for p in (ROOT/'dist').rglob('*') if p.is_file()}
    base = json.loads((RUNS.parent.parent/'2026-11-22-gpu-profile/runs/gp-p7-a/preflight.json').read_text())['labAfter']
    assert all(json.loads(p.read_text())['labAfter']==base for p in RUNS.glob('*/preflight.json'))
    old=RUNS.parent.parent/'2026-11-22-gpu-profile'
    calibration=json.loads((old/'summary.json').read_text())['calibration']
    assert calibration['pass'] and 3<=calibration['ratio']<=5
    proofs={}
    for path in sorted(R.glob('*.json')):
        if path.name in ('summary.json','packs.json'): continue
        d=json.loads(path.read_text())
        if 'underLock' in d:
            assert d['labAfter']==d['labBefore']==base
            proofs[path.stem]={'exit':d['exit'],'log':path.with_suffix('.log').name}
    candidate_sources={name:receipt('gp-idle-src-'+name) for name in ('p8','p9') if (RUNS/('gp-idle-src-'+name)/'summary.json').exists()}
    results={key:json.loads(path.read_text()) for key in ('overhead-a','overhead-b','profile','minecraft-frames')
             if (path:=OUT/(key+'.json')).is_file()}
    if 'profile' in results:
        results['performanceDecision'] = 'passed' if results['profile']['pass'] else 'stopped_at_gpu_gate'
        if 'minecraft-frames' in results:
            results['cpuOnlyComparison'] = 'measured'
        elif not results['profile']['pass']:
            results['cpuOnlyComparison'] = 'not run after failed GPU gate'
        interval_keys=('fps','cpuMeanMs','cpuP95Ms','cpuP99Ms','frames')
        results['minecraftIntervalsByRun'] = {}
        for suffix in ('oh-off-a','p8-a','p9-a','p9-b','p8-b','oh-off-b'):
            arm=receipt('gp-idle-'+suffix)
            results['minecraftIntervalsByRun'][arm['label']]={
                'profilerEnabled':arm['mode']=='on',
                'scenes':{s:{k:w[k] for k in interval_keys} for s,w in arm['scenes'].items()}}
    return {'experiment':'lava-free fullscreen overhead', 'candidateMeasurements':results,
            'calibrationFromPriorPinnedProfiler':calibration,
            'sourceCaptures':{k:{n:s[n] for n in ('label','sources','pragma','fbo')} for k,s in candidate_sources.items()},
            'probes':proofs, 'units':'mean elapsed GPU milliseconds per accepted frame; diagnostic minus control',
            'renderer':receipt('gp-idle-src-p3')['renderer'], 'accepted':accepted, 'rejected':failures,
            'sources':full_sources,'comparisons':comparisons,'lab':base,
            'distFilesVerified':len(dist),'reproduced':json.loads((OUT/'rebuilt/verified.json').read_text())}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('check', choices=['sources', 'report', *FACTORS])
    args=p.parse_args()
    if args.check=='report':
        (R/'summary.json').write_text(json.dumps(report(),indent=2,ensure_ascii=False)+'\n')
        raise SystemExit(0)
    result = sources() if args.check=='sources' else compare(args.check)
    path=OUT/('verified-'+args.check+'.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    if args.check!='sources':
        for side,pair in result['pairs'].items():
            print(args.check,side,{k: round(pair['deltaMs'][k],4) for k in ('quad/composite','quad/deferred','frame',*CONTROLS)}, pair['controlChecks'],flush=True)
        if not all(all(pair['controlChecks'].values()) for pair in result['pairs'].values()):
            raise SystemExit('control range outside tolerance')
