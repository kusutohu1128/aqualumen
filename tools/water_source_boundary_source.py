"""Passive TEST SSBO observer for actual per-node reflected source decisions.

Original integrator/tracer predicates, return expressions and all geometry stay
unchanged. Observation only; native extension is not an Iris/shipping module.
"""
import argparse
from pathlib import Path
import water_conditioned_sources_source as textutil

ROOT=Path(__file__).resolve().parents[1]
STRIDE=22
HEADER='''#extension GL_ARB_shader_storage_buffer_object : require
layout(std430) buffer WSB_Observation {
    uvec4 WSB_counts;
    vec4 WSB_records[90112];
};
bool WSB_active=false,WSB_bracketFound=false;
uint WSB_at=0u;
vec4 WSB_weight,WSB_indices,WSB_interval;
vec4 WSB_lastQ,WSB_screen,WSB_previous,WSB_terminal,WSB_refined,WSB_far,WSB_scene;
vec4 WSB_bracket,WSB_bracketPrevious;
void WSB_put(int slot,vec4 value) {
    if(WSB_at<4096u)WSB_records[WSB_at*22u+uint(slot)]=value;
}
void WSB_begin() {
    WSB_at=atomicAdd(WSB_counts.x,1u);
    if(WSB_at>=4096u)atomicAdd(WSB_counts.y,1u);
    WSB_active=true;WSB_bracketFound=false;
    WSB_lastQ=WSB_screen=WSB_previous=WSB_terminal=WSB_refined=WSB_far=WSB_scene=vec4(0.0);
    WSB_bracket=WSB_bracketPrevious=vec4(0.0);
    WSB_terminal.x=3.0;
}
void WSB_end(vec3 ray,vec3 facet,vec3 origin,vec3 position,vec3 transformed,
    vec3 start,float access,float surfaceY,vec4 hit,vec3 source,
    vec3 n,vec3 v,vec3 covariance) {
    WSB_active=false;
    WSB_put(0,vec4(ray,WSB_weight.z));WSB_put(1,vec4(facet,WSB_weight.w));
    WSB_put(2,vec4(origin,access));WSB_put(3,vec4(start,surfaceY));
    WSB_put(4,vec4(transformed,1.0));WSB_put(5,vec4(position,1.0));
    WSB_put(6,hit);WSB_put(7,vec4(source,1.0));
    WSB_put(8,vec4(WSB_weight.xy,WSB_indices.xy));WSB_put(9,WSB_interval);
    WSB_put(10,vec4(n,1.333));WSB_put(11,vec4(v,1.0));WSB_put(12,vec4(covariance,1.0));
    WSB_put(13,WSB_lastQ);WSB_put(14,WSB_screen);WSB_put(15,WSB_previous);
    WSB_put(16,WSB_terminal);WSB_put(17,WSB_refined);WSB_put(18,WSB_far);
    WSB_put(19,WSB_scene);WSB_put(20,WSB_bracket);WSB_put(21,WSB_bracketPrevious);
}
'''


def observe(source):
    # Extension directives all precede non-preprocessor GLSL declarations.
    marker='#define WAVE_HEIGHT'
    assert marker in source
    version='#extension GL_ARB_gpu_shader_fp64 : require\n'
    assert source.count(version)==1
    source=source.replace(version,version+HEADER,1)
    signature='vec4 reflectionTrace(vec3 viewStart,vec3 viewRay,vec3 fallback,bool aboveWaterSurface,float surfaceY)'
    start=source.index(signature+' {');opening=source.index('{',start);level=1;end=opening+1
    while level:
        level+=(source[end]=='{')-(source[end]=='}');end+=1
    tracer=source[start:end]
    tracer=tracer.replace('if (projected.w<=0.0) break;',
        'if (projected.w<=0.0) {if(WSB_active){WSB_lastQ=vec4(q,travel);WSB_terminal=vec4(1.0,float(i),0.0,0.0);} break;}')
    tracer=tracer.replace('if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) break;',
        'if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) {if(WSB_active){WSB_lastQ=vec4(q,travel);WSB_screen.xy=screen;WSB_terminal=vec4(2.0,float(i),0.0,0.0);} break;}')
    anchor='        if (depth<0.999999 && q.z<scene.z && beforeSurface && abs(q.z-scene.z)<crossingWidth) {'
    assert tracer.count(anchor)==1
    observation='''        if(WSB_active) {
            WSB_lastQ=vec4(q,travel);WSB_screen=vec4(screen,depth,float(beforeSurface));
            WSB_previous=vec4(previous,crossingWidth);WSB_scene=vec4(scene,depth);
            WSB_terminal=vec4(3.0,float(i),abs(q.z-scene.z),crossingWidth);
            if(!WSB_bracketFound&&depth<0.999999&&q.z<scene.z&&beforeSurface) {
                WSB_bracketFound=true;WSB_bracket=vec4(travel,crossingWidth,q.z-scene.z,1.0);
                WSB_bracketPrevious=vec4(previous,1.0);
            }
        }
'''
    tracer=tracer.replace(anchor,observation+anchor,1)
    anchor='                return vec4(fallback,-1.0);'
    # Single refined-invalid return; only added stores, unchanged expression.
    assert tracer.count(anchor)==1
    tracer=tracer.replace('            if (refinedDepth>=0.999999 || (aboveWaterSurface && relativeWorld(scene).y<surfaceY-0.30))\n'+anchor,
        '            if (refinedDepth>=0.999999 || (aboveWaterSurface && relativeWorld(scene).y<surfaceY-0.30)) {\n'
        '                if(WSB_active){WSB_terminal.x=4.0;WSB_refined=vec4(screen,0.0,0.0);WSB_far=vec4(farHit,travel);WSB_scene=vec4(scene,refinedDepth);}\n'+anchor+'\n            }')
    anchor='            return vec4(mix(fallback,texture(colortex4,screen).rgb,edge*confidence),length(farHit-viewStart));'
    assert tracer.count(anchor)==1
    tracer=tracer.replace(anchor,
        '            if(WSB_active){WSB_terminal.x=5.0;WSB_refined=vec4(screen,confidence,edge);WSB_far=vec4(farHit,travel);WSB_scene=vec4(scene,refinedDepth);}\n'+anchor,1)
    if 'if(SWR_exitSegment)break;' in tracer:
        tracer=tracer.replace('if(SWR_exitSegment)break;',
            'if(SWR_exitSegment){if(WSB_active)WSB_terminal.x=6.0;break;}',1)
    source=source[:start]+tracer+source[end:]
    anchor='                vec3 term=WSP_rule[ix].z*WSP_rule[iz].z*mass*node.w*WRT_waterSource(node.xyz);'
    assert source.count(anchor)==1
    source=source.replace(anchor,
        '                WSB_weight=vec4(x,z,WSP_rule[ix].z*WSP_rule[iz].z*mass*node.w,mass);\n'
        '                WSB_indices=vec4(float(ix),float(iz),float(panel),1.0);WSB_interval=vec4(lo,hi,float(panel),mass);\n'+anchor,1)
    anchor='    vec4 hit=reflectionTrace(WSA_origin+mat3(gbufferModelView)*facet*0.06,\n'
    assert source.count(anchor)==1
    source=source.replace(anchor,'    WSB_begin();\n'+anchor,1)
    anchor='    if(hit.a>0.0) {'
    assert source.count(anchor)==1
    source=source.replace(anchor,
        '    WSB_active=false;\n'+anchor,1)
    call=('WSB_end(ray,facet,WSA_origin,WSA_position,mat3(gbufferModelView)*ray,\n'
          '            WSA_origin+mat3(gbufferModelView)*facet*0.06,WSA_access,WSA_position.y,hit,')
    anchor='        return WSA_checked(hit.rgb*trans+WSA_scatter*(1.0-trans));'
    assert source.count(anchor)==1
    source=source.replace(anchor,'        '+call+'hit.rgb*trans+WSA_scatter*(1.0-trans),WRT_seenN,WRT_seenV,WRT_seenC);\n'+anchor,1)
    anchor='    return WSA_checked(WSA_scatter);'
    assert source.count(anchor)==1
    source=source.replace(anchor,'    '+call+'WSA_scatter,WRT_seenN,WRT_seenV,WRT_seenC);\n'+anchor,1)
    return source


def build(out,order):
    assert order in (8,12)
    base=ROOT/f'reports/2026-10-06-water-fast-inverse/main-probability-{order}-v1'
    out=Path(out);out.mkdir(exist_ok=False)
    original=(base/'enabled.fsh').read_text()
    for name,text in (('baseline.fsh',original),('observer.fsh',observe(original))):
        with (out/name).open('x') as f:f.write(text)
    for i in range(3):
        with (out/f'geometry-stage{i}.glsl').open('x') as f:f.write((base/f'geometry-stage{i}.glsl').read_text())
    with (out/'probability-rule.json').open('x') as f:f.write((base/'probability-rule.json').read_text())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out');parser.add_argument('--order',type=int,required=True)
    args=parser.parse_args();build(args.out,args.order)
