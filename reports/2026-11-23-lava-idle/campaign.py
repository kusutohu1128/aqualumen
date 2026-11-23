"""Evaluate the ordered overhead and candidate gates from validated Minecraft windows."""
import argparse
import csv
import json
import math
import subprocess
from statistics import mean
import sys

from diagnostics import R, OUT
from summarize import receipt
sys.path.insert(0,str(R.parent/'2026-11-22-gpu-profile'))
from profile_data import collect_window, read_rows, percentile

SCENES=('both-west','day-white','birch-off','birch-torch')
TARGETS=('quad/deferred','quad/composite')


def save(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def overhead(side):
    off=receipt('gp-idle-oh-off-'+side)
    on=receipt('gp-idle-p8-'+side)
    result={}
    for scene in SCENES:
        a=off['scenes'][scene]
        b=on['scenes'][scene]
        avg=100*(b['cpuMeanMs']/a['cpuMeanMs']-1)
        tail=100*(b['cpuP95Ms']/a['cpuP95Ms']-1)
        result[scene]={'offMeanMs':a['cpuMeanMs'],'onMeanMs':b['cpuMeanMs'],'meanPercent':avg,
                       'offP95Ms':a['cpuP95Ms'],'onP95Ms':b['cpuP95Ms'],'p95Percent':tail,
                       'pass':avg<=5 and tail<=8}
    return result


def gpu_deltas(side):
    a=receipt('gp-idle-p8-'+side)
    b=receipt('gp-idle-p9-'+side)
    result={}
    for scene in SCENES:
        base=a['scenes'][scene]['meanMs']
        candidate=b['scenes'][scene]['meanMs']
        deltas={k:candidate.get(k,0)-base.get(k,0) for k in sorted(base.keys()|candidate.keys())}
        result[scene]={'p8':base,'p9':candidate,'meanDeltaMs':deltas,'combinedMeanDeltaMs':sum(deltas[k] for k in TARGETS)}
    return result


def image_pair(side, scene):
    images=[]
    for pack in ('p8','p9'):
        arm=receipt(f'gp-idle-{pack}-{side}')
        path=R/'runs'/arm['label']/(scene+'-ingame.png')
        images.append(subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),
                     '-vf','scale=360:202,format=gray','-frames:v','1','-f','rawvideo','-']))
    a,b=images
    assert len(a)==len(b)==360*202
    ma,mb=mean(a),mean(b)
    correlation=sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return {'grayMeanAbsoluteCodes':mean(abs(x-y) for x,y in zip(a,b)),'correlation':correlation}


def gpu_comparison():
    pairs={i:gpu_deltas(i) for i in ('a','b')}
    saving={}
    for side,scenes in pairs.items():
        birch=scenes['birch-off']
        saving[side]=birch['combinedMeanDeltaMs']<=-2 and all(birch['meanDeltaMs'][k]<0 for k in (*TARGETS,'frame'))
    regressions={}
    for s in SCENES:
        a,b=[pairs[i][s] for i in ('a','b')]
        regressions[s]=[k for k in a['meanDeltaMs'] if all(c['meanDeltaMs'].get(k,0)>max(.1,.1*c['p8'].get(k,0)) for c in (a,b))]
    images={side:{s:image_pair(side,s) for s in SCENES} for side in pairs}
    return {'pairs':pairs,'f2ReducedGray':images,'savingGate':saving,'repeatIncreases':regressions,
            'pass':all(saving.values()) and not any(regressions.values())}


def pooled():
    result={s:{} for s in SCENES}
    for pack in ('p8','p9'):
        samples={s:[] for s in SCENES}
        for side in ('a','b'):
            arm=receipt(f'gp-idle-{pack}-{side}')
            with (R/'runs'/arm['label']/'frames.csv').open() as stream:
                all_frames=read_rows(stream)
            for s,w in arm['scenes'].items():
                samples[s].extend(collect_window(all_frames,range(w['firstFrame'],w['lastFrame']+1)))
        for s,window in samples.items():
            names={k for f in window for k in f['inclusive']}
            for k in sorted(names|{'uncovered'}):
                times=[(f['residual'] if k=='uncovered' else f['inclusive'].get(k,0))/1e6 for f in window]
                result[s].setdefault(k,{})[pack]={'medianMs':percentile(times,.5),'p95Ms':percentile(times,.95),'meanMs':mean(times)}
    return result


def interval_comparison():
    result={}
    for s in SCENES:
        result[s]={}
        for side in ('a','b'):
            a,b=[receipt(f'gp-idle-ft-{p}-{side}')['scenes'][s] for p in ('p8','p9')]
            keys=('cpuMeanMs','cpuP95Ms','cpuP99Ms','fps')
            result[s][side]={'p8':{k:a[k] for k in keys},'p9':{k:b[k] for k in keys},'delta':{k:b[k]-a[k] for k in keys}}
    return result


def write_tables(result):
    """Each CSV row contains the pooled distribution and both independent signed contrasts."""
    with (R/'range-times.csv').open('w') as stream:
        out=csv.writer(stream,lineterminator='\n')
        out.writerow(('scene','range','p8_median_ms','p8_p95_ms','p9_median_ms','p9_p95_ms',
                      'pair_a_mean_delta_ms','pair_b_mean_delta_ms','pair_a_median_delta_ms','pair_b_median_delta_ms'))
        arms={(p,i):receipt(f'gp-idle-{p}-{i}') for p in ('p8','p9') for i in ('a','b')}
        for scene in SCENES:
            for name,stat in sorted(result['pooled'][scene].items()):
                def median(pack,side):
                    g=arms[pack,side]['scenes'][scene]['gpu']
                    v=g['residual'] if name=='uncovered' else g['ranges'].get(name)
                    return v['medianMs'] if v else 0.
                out.writerow((scene,name,*[stat.get(pack,{}).get(key,0) for pack in ('p8','p9') for key in ('medianMs','p95Ms')],
                              *[result['pairs'][side][scene]['meanDeltaMs'][name] for side in ('a','b')],
                              *[median('p9',side)-median('p8',side) for side in ('a','b')]))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('mode',choices=('overhead-a','overhead-b','profile','frames'))
    args=ap.parse_args()
    if args.mode.startswith('overhead'):
        results=overhead(args.mode[-1])
        save(OUT/(args.mode+'.json'),results)
        for s,r in results.items():
            print(s,'mean %.3f%%, p95 %.3f%%'%(r['meanPercent'],r['p95Percent']),r['pass'])
        if not all(r['pass'] for r in results.values()): raise SystemExit('profiler overhead gate failed')
    elif args.mode=='profile':
        result=gpu_comparison()
        result['pooled']=pooled()
        save(OUT/'profile.json',result)
        write_tables(result)
        print('paired performance gate',result['savingGate'],result['repeatIncreases'])
        if not result['pass']: raise SystemExit('candidate GPU gate failed')
    else:
        save(OUT/'minecraft-frames.json',interval_comparison())


if __name__=='__main__':
    main()
