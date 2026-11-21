"""NEW full RGB TEST source construction; all retained modules are read-only."""
import argparse
from pathlib import Path
import water_supported_glsl_source as retained

ROOT=Path(__file__).resolve().parents[1]
def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Exactly one source seam required: '+old[:70])
    return text.replace(old,new,1)

def helper(order):
    base=retained.build(order)
    start=base.index('vec3 WST_constantAir(WST_Context p) {')
    end=base.index('\n#endif',start)
    integral=base[start:end]
    integral=replace(integral,'vec3 WST_constantAir(WST_Context p)','vec3 WRT_airIntegral(WST_Context p)')
    integral=replace(integral,'float sum=0.0,correction=0.0;int evaluations=0;','vec3 sum=vec3(0.0),correction=vec3(0.0);int evaluations=0;')
    integral=replace(integral,'float term=wu*wp*WST_kernel(p,vec3(r*cos(phi),u,r*sin(phi))).x;',
        'vec3 target=vec3(r*cos(phi),u,r*sin(phi));\n                    vec4 node=WST_kernel(p,target);\n                    if(node.x<=0.0)continue;\n                    vec3 term=wu*wp*node.x*WRT_airSource(target);')
    integral=replace(integral,'float adjusted=term-correction,total=sum+adjusted;','vec3 adjusted=term-correction,total=sum+adjusted;')
    integral=replace(integral,'return vec3(sum,float(evaluations),1.0);','return sum;')
    core=(ROOT/'shaders/lib/water_supported_rgb_test.glsl').read_text()
    return base+'\n'+core+'\n'+integral+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--order',type=int,default=96)
    p.add_argument('--validate-ray-domain',action='store_true')
    args=p.parse_args();args.out.mkdir(exist_ok=False)
    code=helper(args.order)
    canonical=ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    original=(canonical/'phase45-parent.fsh').read_text()
    mean='vec3(-0.024761740118265152,-0.9978660345077515,0.06041766330599785)'
    view='vec3(-0.21253617107868195,-0.6171247363090515,-0.7576183080673218)'
    for role,air,water,enabled in (('zero','vec3(0.0)','vec3(0.0)',True),
        ('air','vec3(0.25,0.0,0.0)','vec3(0.0)',True),
        ('water','vec3(0.0)','vec3(0.0,0.125,0.0)',True),
        ('both','vec3(0.25,0.0,0.0)','vec3(0.0,0.125,0.0)',True),
        ('disabled','vec3(0.25,0.0,0.0)','vec3(0.0,0.125,0.0)',False),
        ('unknown','vec3(0.25,0.0,0.0)','vec3(0.0,0.125,0.0)',True),
        ('invalid','vec3(0.25,0.0,0.0)','vec3(0.0,0.125,0.0)',True)):
        unknown='WRT_sourceKnown=false;' if role=='unknown' else ''
        airCheck='if(!WST_finite(ray)||ray.y<=0.0||dot(ray,ray)<1e-6)WRT_sourceKnown=false;' if args.validate_ray_domain else ''
        waterCheck='if(!WST_finite(ray)||ray.y>=0.0||dot(ray,ray)<1e-6)WRT_sourceKnown=false;' if args.validate_ray_domain else ''
        sources='\nvec3 WRT_airSource(vec3 ray){'+unknown+airCheck+'return '+air+';}\nvec3 WRT_waterSource(vec3 ray){'+waterCheck+'return '+water+';}\n'
        source=replace(original,'void main() {',code+sources+'\nvoid main() {')
        # Native TEST evaluation ROI only, NOT a production eligibility rule.
        # The original MAIN and geometry still run at all other pixels.
        anchor='color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);'
        replacement='if(ivec2(gl_FragCoord.xy)==ivec2(128,128)) {\n'
        covariance='vec3(0.0)' if role=='invalid' else 'waveResidualCovariance(max(footprint*1.25,0.035),localColumnKnown?localColumn.x:0.0)'
        replacement+=f'        color=WRT_interface(color,{mean},{view},{covariance},residualEligible && '+('true' if enabled else 'false')+');\n    }'
        source=replace(source,anchor,replacement)
        begin='// AQUALUMEN_GH_OBSERVE_BEGIN:STORE\n';end='// AQUALUMEN_GH_OBSERVE_END:STORE\n'
        left=source.index(begin);right=source.index(end,left)+len(end)
        source=source[:left]+'''// NEW TEST RGB payload; original C0 and direct TES C4 are intact.
    gl_FragData[1]=vec4(WRT_seenN,WRT_eligible);
    gl_FragData[2]=vec4(WRT_seenV,WRT_status.x);
    gl_FragData[3]=vec4(WRT_seenC,1.333);
    gl_FragData[5]=WRT_status;
    gl_FragData[6]=vec4(WRT_lastT,1.0);
    gl_FragData[7]=vec4(WRT_lastR,1.0);
'''+source[right:]
        with (args.out/f'{role}.fsh').open('x') as f:f.write(source)
    with (args.out/'helper.glsl').open('x') as f:f.write(code)
    for i in range(3):
        with (args.out/f'geometry-stage{i}.glsl').open('x') as f:f.write((canonical/f'geometry-stage{i}.glsl').read_text())
if __name__=='__main__':main()
