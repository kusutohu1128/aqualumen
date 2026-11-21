"""Same64 actual-source TEST MAIN, inverse-only revision and uncertainty guard."""
import argparse
import json
from pathlib import Path
import water_fast_inverse as inverse


def build(out):
    out=Path(out);out.mkdir(exist_ok=False)
    previous=inverse.ROOT/'reports/2026-10-06-water-conditioned-sampling/main-sources-64-v1'
    helper=inverse.helper(inverse.fit())
    for path in sorted(previous.iterdir()):
        if not path.is_file():continue
        text=path.read_text()
        if path.suffix=='.fsh' or path.name=='helper.glsl':
            anchor='vec3 WRT_airSource(vec3 ray);';assert text.count(anchor)==1
            text=text.replace(anchor,helper+'\n'+anchor,1)
            assert text.count('vec4 node=WSQ_sample(')==2
            text=text.replace('vec4 node=WSQ_sample(','vec4 node=WSF_sample(')
            anchor='if(status==0.0)continue;';assert text.count(anchor)==2
            text=text.replace(anchor,'if(status<0.0){WRT_sourceKnown=false;continue;}\n        '+anchor)
        with (out/path.name).open('x') as f:f.write(text)
    with (out/'inverse-coefficients.json').open('x') as f:json.dump(inverse.fit(),f,indent=2,sort_keys=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out');args=parser.parse_args();build(args.out)
