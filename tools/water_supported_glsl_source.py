"""Build NEW TEST-only quadrature/source artifacts; do not touch sealed CPU files."""
import argparse
import json
from pathlib import Path
import struct
import water_supported_transmission as model

ROOT=Path(__file__).resolve().parents[1]
def build(order):
    rule=model.legendre(order)
    constants=f'const int WST_order={order};\nconst vec2 WST_rule[{order}]=vec2[{order}](\n'
    constants+=',\n'.join(f'vec2({x:.17g},{w:.17g})' for x,w in rule)+');\n'
    helper=(ROOT/'shaders/lib/water_supported_transmission_test.glsl').read_text()
    return constants+helper

def main():
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    args=parser.parse_args();args.out.mkdir(exist_ok=False)
    actual=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())
    records=[p['raw']['normal'][:3]+p['raw']['view'][:3]+p['raw']['covariance'][:3]+[1.3329999446868896]
        for p in actual['points']]
    # Strict invalid C, non-unit raw view, and zero covariance: no repair.
    for c in ([.01,.04,.01],[0,0,0]):records.append(records[2][:6]+c+records[2][9:])
    records.append(records[2][:3]+[0,-2,0]+records[2][6:])
    with (args.out/'inputs.f32').open('xb') as f:
        for record in records:f.write(struct.pack('<10f',*record))
    for order in (48,64,96):
        with (args.out/f'helper-{order}.glsl').open('x') as f:f.write(build(order))
    with (args.out/'inputs.json').open('x') as f:json.dump(records,f,indent=2)
if __name__=='__main__':main()
