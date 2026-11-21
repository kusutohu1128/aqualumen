"""TEST renderer correction: examine the last observed SSR segment, not outside.

No broader depth thickness/source/weight changes. Clip only a segment with an
independently valid previous in-frustum endpoint. Original crossing, refinement,
depth/above-water/receiver guards and source/proxy conventions remain.
"""
import argparse
from pathlib import Path
import water_source_boundary_source as passive

ROOT=Path(__file__).resolve().parents[1]


def clip_segment(source):
    signature='vec4 reflectionTrace(vec3 viewStart,vec3 viewRay,vec3 fallback,bool aboveWaterSurface,float surfaceY)'
    start=source.index(signature+' {');opening=source.index('{',start);level=1;end=opening+1
    while level:
        level+=(source[end]=='{')-(source[end]=='}');end+=1
    tracer=source[start:end]
    anchor='        vec3 q=viewStart+viewRay*travel;'
    assert tracer.count(anchor)==1
    tracer=tracer.replace(anchor,anchor+'\n        bool SWR_exitSegment=false;',1)
    anchor='        if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) break;'
    assert tracer.count(anchor)==1
    clipped='''        // A coarse endpoint outside the image can skip a visible receiver
        // BEFORE the viewport exit. Inspect only the last known inside segment.
        if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) {
            vec4 previousProjection=gbufferProjection*vec4(previous,1.0);
            if(previousProjection.w<=0.0)break;
            vec2 previousUV=previousProjection.xy/previousProjection.w*0.5+0.5;
            if(any(lessThan(previousUV,vec2(0.002)))||any(greaterThan(previousUV,vec2(0.998))))break;
            vec3 inside=previous,outside=q;
            for(int boundary=0;boundary<16;++boundary) {
                vec3 mid=(inside+outside)*0.5;
                vec4 clip=gbufferProjection*vec4(mid,1.0);
                bool observed=false;
                if(clip.w>0.0) {
                    vec2 candidate=clip.xy/clip.w*0.5+0.5;
                    observed=all(greaterThanEqual(candidate,vec2(0.002)))
                        &&all(lessThanEqual(candidate,vec2(0.998)));
                }
                if(observed)inside=mid;else outside=mid;
            }
            q=inside;projected=gbufferProjection*vec4(q,1.0);
            screen=projected.xy/projected.w*0.5+0.5;
            SWR_exitSegment=true;
        }
'''
    # The exact original viewport guard remains after boundary rounding.
    tracer=tracer.replace(anchor,clipped+anchor,1)
    anchor='        previous=q;\n        travel+=0.18+travel*0.22;'
    assert tracer.count(anchor)==1
    tracer=tracer.replace(anchor,'        if(SWR_exitSegment)break;\n'+anchor,1)
    return source[:start]+tracer+source[end:]


def build(out,order):
    assert order in (8,12)
    base=ROOT/f'reports/2026-10-06-water-fast-inverse/main-probability-{order}-v1'
    out=Path(out);out.mkdir(exist_ok=False)
    fixed=clip_segment((base/'enabled.fsh').read_text())
    for name,text in (('baseline.fsh',fixed),('observer.fsh',passive.observe(fixed))):
        with (out/name).open('x') as f:f.write(text)
    for i in range(3):
        with (out/f'geometry-stage{i}.glsl').open('x') as f:f.write((base/f'geometry-stage{i}.glsl').read_text())
    with (out/'probability-rule.json').open('x') as f:f.write((base/'probability-rule.json').read_text())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out');parser.add_argument('--order',type=int,required=True)
    args=parser.parse_args();build(args.out,args.order)
