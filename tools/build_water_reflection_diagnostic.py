"""Build a TEST-ONLY display of the production underwater reflection decision."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
SEAM = '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);'
REPLACEMENT = '''    vec3 diagnostic=color;
    if (underwater) {
        diagnostic=fresnel<0.999 ? vec3(0.0,1.0,0.0)
            : reflectedHit.a>0.0 ? vec3(1.0,0.0,0.0) : vec3(0.0,0.0,1.0);
    }
    gl_FragData[0]=vec4(diagnostic,1.0);'''
FINAL = '''#version 330 compatibility
uniform sampler2D colortex0;
in vec2 texcoord;
void main() {
    gl_FragColor=vec4(texture(colortex0,texcoord).rgb,1.0);
}
'''


def build(target):
    source = ROOT / 'shaders/gbuffers_water.fsh'
    text = source.read_text()
    if text.count(SEAM) != 1:
        raise ValueError('Production output seam changed')
    modifications = {'shaders/gbuffers_water.fsh': text.replace(SEAM, REPLACEMENT).encode(),
                     'shaders/final.fsh': FINAL.encode()}
    omitted = {f'shaders/composite{stage}.{extension}' for stage in (1, 2) for extension in ('vsh', 'fsh')}
    with ZipFile(target, 'x', compression=ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / 'shaders').rglob('*')):
            if not path.is_file():
                continue
            name = path.relative_to(ROOT).as_posix()
            if name in omitted:
                continue
            entry = ZipInfo(name, (2026, 10, 11, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, modifications.get(name, path.read_bytes()))
    evidence = dict(test_only=True, pack_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    production_water_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    modified_files=sorted(modifications), omitted_files=sorted(omitted),
                    legend=dict(green='underwater Fresnel below 0.999',
                                red='underwater Fresnel at least 0.999 and production SSR hit',
                                blue='underwater Fresnel at least 0.999 and production SSR miss'),
                    caveats=['Color is a decision label, not radiance',
                             'Particles and subsequent transparent draws can obscure labels',
                             'No independent second reflection trace is run'])
    with target.with_suffix('.diagnostic.json').open('x') as output:
        json.dump(evidence, output, indent=2)
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    build(parser.parse_args().target)
