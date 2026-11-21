"""TEST MAIN: panel-wise probability quadrature, unchanged Gaussian optics.

Only diffuse quadrature changes relative to frozen fast64. The original source
adapter, solar/lunar caps, geometry, raw context and physical units stay fixed.
CPU-authored x coordinates are explicit; conditional z is evaluated on GPU.
"""
import argparse
import json
from pathlib import Path
import struct
import water_supported_probability_rule as probability
import water_conditioned_sources_source as retained

ROOT = Path(__file__).resolve().parents[1]


def binary32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def build(out, order=8):
    if order not in (8, 12, 16):
        raise ValueError('Explicit bounded quadrature order required')
    out = Path(out)
    out.mkdir(exist_ok=False)
    base = ROOT / 'reports/2026-10-06-water-fast-inverse/main-sources-64-v1'
    rule = probability.probability_rule(order)
    nodes = [(binary32(probability.c.NORMAL.inv_cdf(u)), binary32(u), binary32(w))
             for u, w in rule]
    code = f'const int WSP_order={order};\n'
    code += f'const vec3 WSP_rule[{order}]=vec3[{order}](\n'
    code += ',\n'.join(f'vec3({x:.17g},{u:.17g},{w:.17g})' for x,u,w in nodes) + ');\n'
    code += '''// Each supported panel carries its ORIGINAL Gaussian probability.
// No mixture discontinuity, survivor fitting, or physical covariance change.
bool WSP_quantile(float lo,float hi,float u,out float z) {
    float small;bool positive;
    if(lo>=0.0) {
        small=(1.0-u)*WSQ_tail(lo)+u*WSQ_tail(hi);positive=true;
    } else if(hi<=0.0) {
        small=(1.0-u)*WSQ_tail(-lo)+u*WSQ_tail(-hi);positive=false;
    } else {
        float mass=WSQ_mass(lo,hi),left=WSQ_tail(-lo)+u*mass;
        positive=left>0.5;
        small=positive?WSQ_tail(hi)+(1.0-u)*mass:left;
    }
    float absoluteZ;
    if(!WSF_inverseTail(small,absoluteZ))return false;
    z=positive?absoluteZ:-absoluteZ;
    return z>=lo&&z<=hi;
}
'''
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text()
        if path.name == 'helper.glsl' or path.suffix == '.fsh':
            anchor = 'vec3 WRT_airSource(vec3 ray);'
            assert text.count(anchor) == 1
            text = text.replace(anchor, code + '\n' + anchor, 1)
            for branch, kind in enumerate(('air', 'water')):
                signature = f'vec3 WRT_{kind}Integral(WST_Context p)'
                body = signature + ''' {
    vec3 sum=vec3(0.0),correction=vec3(0.0);vec4 q=WSQ_basis(p);
    for(int ix=0;ix<WSP_order;++ix) {
        float x=WSP_rule[ix].x;float bounds[20];int count;
        WSQ_partition(p,q,x,'''+str(branch)+''',bounds,count);
        for(int panel=0;panel<count-1;++panel) {
            float lo=bounds[panel],hi=bounds[panel+1];
            if(hi<=lo||WSQ_node(p,q,x,0.5*(lo+hi),'''+str(branch)+''').w<=0.0)continue;
            float mass=WSQ_mass(lo,hi);
            if(mass<=0.0)continue;
            for(int iz=0;iz<WSP_order;++iz) {
                float z;
                if(!WSP_quantile(lo,hi,WSP_rule[iz].y,z)){WRT_sourceKnown=false;continue;}
                vec4 node=WSQ_node(p,q,x,z,'''+str(branch)+''');
                if(node.w<=0.0){WRT_sourceKnown=false;continue;}
                vec3 term=WSP_rule[ix].z*WSP_rule[iz].z*mass*node.w*WRT_'''+kind+'''Source(node.xyz);
                vec3 adjusted=term-correction,total=sum+adjusted;
                correction=(total-sum)-adjusted;sum=total;
            }
        }
    }
    return sum;
}'''
                text = retained.replace_function(text, signature, body)
        with (out / path.name).open('x') as file:
            file.write(text)
    metadata = dict(schema='aqualumen-probability-main-rule-v1', order=order,
        CPUGeneratedX=True, binary32Nodes=nodes, panelMassFitted=False,
        supportExtent=8., physicalCovarianceChanged=False,
        physicalSourceUnitsChanged=False, IrisAccepted=False,
        scope='Per-panel conditional Gaussian quadrature; order squared is NOT total source-ray count.')
    with (out / 'probability-rule.json').open('x') as file:
        json.dump(metadata, file, indent=2, sort_keys=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('--order', type=int, default=8)
    args=parser.parse_args()
    build(args.out, args.order)
