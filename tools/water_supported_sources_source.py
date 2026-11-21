"""New source adapter fixtures; retained RGB core and original stages read-only."""
import argparse
from pathlib import Path
import water_supported_rgb_source as rgb

ROOT = Path(__file__).resolve().parents[1]
ANCHOR = ('color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
          '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);')
N = 'vec3(-0.024761740118265152,-0.9978660345077515,0.06041766330599785)'
V = 'vec3(-0.21253617107868195,-0.6171247363090515,-0.7576183080673218)'


def build(order=96):
    canonical = ROOT / 'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    original = (canonical / 'phase45-parent.fsh').read_text()
    adapter = (ROOT / 'shaders/lib/water_supported_sources_test.glsl').read_text()
    closure = rgb.helper(order) + '\n' + adapter
    sources = {}
    for role in ('enabled', 'disabled', 'strict', 'invalid', 'ledger'):
        enabled = 'false' if role == 'disabled' else 'true'
        proxy = 'false' if role == 'strict' else 'true'
        c = ('vec3(0.0)' if role == 'invalid' else
             'waveResidualCovariance(max(footprint*1.25,0.035),localColumnKnown?localColumn.x:0.0)')
        source = rgb.replace(original, 'void main() {', closure + '\nvoid main() {')
        # The complete adapter now handles genuine receivers/reflections. The
        # old miss-only restriction cannot qualify those roles by construction.
        source = rgb.replace(source,
            '        && receiverKind!=1 && reflectedHit.a<0.0 && abs(n.y)>0.5;',
            '        && abs(n.y)>0.5;')
        # Single native TEST seam only; no production cutoff is authorized.
        replacement = ('if(ivec2(gl_FragCoord.xy)==ivec2(128,128)) {\n'
                       f'        color=WSA_interface(color,{N},{V},{c},worldPosition,viewPos,\n'
                       f'            skyAccess,caveAmbient,scatter,residualEligible && {enabled},{proxy});\n'
                       '    }')
        source = rgb.replace(source, ANCHOR, replacement)
        begin = '// AQUALUMEN_GH_OBSERVE_BEGIN:STORE\n'
        end = '// AQUALUMEN_GH_OBSERVE_END:STORE\n'
        left = source.index(begin); right = source.index(end, left) + len(end)
        if role == 'ledger':
            store = '''    gl_FragData[1]=WSA_sunLedger;
    gl_FragData[2]=vec4(WSA_airSky,WSA_airOpaque,WSA_airUnknown,float(WSA_proxyUsed));
    gl_FragData[3]=vec4(WSA_reflectionHits,WSA_reflectionMisses,WSA_moonLedger.xy);
    gl_FragData[5]=WRT_status;
    gl_FragData[6]=vec4(WSA_solar,1.0);
    gl_FragData[7]=vec4(WSA_lunar,1.0);
'''
        else:
            store = '''    gl_FragData[1]=vec4(WRT_seenN,WRT_eligible);
    gl_FragData[2]=vec4(WRT_seenV,WRT_status.x);
    gl_FragData[3]=vec4(WRT_seenC,1.333);
    gl_FragData[5]=WRT_status;
    gl_FragData[6]=vec4(WRT_lastT,1.0);
    gl_FragData[7]=vec4(WRT_lastR,1.0);
'''
        source = source[:left] + store + source[right:]
        sources[role + '.fsh'] = source
    sources['helper.glsl'] = closure
    for i in range(3):
        sources[f'geometry-stage{i}.glsl'] = (canonical / f'geometry-stage{i}.glsl').read_text()
    return sources


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('out', type=Path)
    p.add_argument('--order', type=int, default=96); args = p.parse_args()
    sources = build(args.order); args.out.mkdir(exist_ok=False)
    for name, text in sources.items():
        with (args.out / name).open('x') as f:
            f.write(text)
