"""Audit immutable paired captures and exact restoration without launching the game."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scene(directory, pack_hash):
    m = json.loads((directory / 'manifest.json').read_text())
    require(m['available'] and m['packSha256'] == pack_hash and m['previewUniform'] == 0, 'Capture identity/availability')
    require(m['beforeReadStateRestored'] and m['afterReadStateRestored'] and m['quadInvocationReturnedObserved'], 'Pairing/state proof')
    for f in m['files'].values():
        p = directory / f['name']
        require(p.name == f['name'] and not p.is_symlink() and p.stat().st_size == f['bytes'] and sha(p) == f['sha256'], 'Capture file differs')
    width, height = m['width'], m['height']
    data = array('f')
    data.frombytes((directory / m['files']['classification']['name']).read_bytes())
    if sys.byteorder != 'little':
        data.byteswap()
    require(len(data) == width * height * 4, 'Classification byte count')
    counts = [0] * 6
    for i in range(0, len(data), 4):
        route, fresnel, travel, mask = data[i:i+4]
        require(all(math.isfinite(v) for v in (route, fresnel, travel, mask)), 'Nonfinite record')
        require(route == int(route) and 0 <= route <= 5 and 0 <= fresnel <= 1 and travel >= 0, 'Invalid record')
        require((mask == 0 and route == fresnel == travel == 0) or (mask == 1 and route > 0), 'Mask mismatch')
        counts[int(route)] += 1
    require(counts == m['routeCounts'] and sum(counts[1:]) > 0, 'Recorded route counts differ')
    beauty = (directory / m['files']['beauty']['name']).read_bytes()
    require(len(beauty) == width * height * 4, 'Beauty extent')
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(directory / m['files']['png']['name']),
                              '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], capture_output=True, timeout=30)
    expected = b''.join(beauty[y*width*4:(y+1)*width*4] for y in range(height-1, -1, -1))
    require(decoded.returncode == 0 and decoded.stdout == expected, 'PNG/raw orientation mismatch')
    points = []
    for x, display_y in ((width//2, height//2), (width-50, 50), (width-170, 200), (50, height//2)):
        y = height-1-display_y
        records = []
        for xx, yy in ((x,y), (x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            at = (max(0,min(height-1,yy))*width + max(0,min(width-1,xx))) * 4
            records.append(list(data[at:at+4]))
        at = (y*width+x)*4
        points.append(dict(displayXY=[x,display_y], beautyRGBA=list(beauty[at:at+4]),
                           sourceRecordsCenterWestEastSouthNorth=records))
    return dict(scene=m['scene'], frame=m['frame'], renderer=m['glRenderer'], routeNames=m['routeNames'],
                manifestPath=str(directory / 'manifest.json'), manifestSHA256=sha(directory / 'manifest.json'),
                routeCounts=counts, routePercent=[100*c/(width*height) for c in counts],
                allFilesAndPNGOrientationVerified=True, illustrativeSamples=points,
                attribution='Samples retain center and four neighboring source records. GL_LINEAR footprints and other translucent contributors remain qualifications. No causal or physical acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native = json.loads((args.evidence / 'native-final/receipt.json').read_text())
    require(native['passed'] and native['exit_code'] == 0 and native['final_preview0_byte_equal']
            and native['final_preview1_sensitive'], 'Native qualification missing')
    for f in native['artifacts']:
        p = args.evidence / 'native-final' / f['path']
        require(sha(p) == f['sha256'] and p.stat().st_size == f['bytes'], 'Native evidence changed')
    original = json.loads((args.evidence / 'input-sha256.json').read_text())
    current = {p.relative_to(args.root).as_posix(): sha(p) for p in (args.root / 'shaders').rglob('*') if p.is_file()}
    current['LICENSE'] = sha(args.root / 'LICENSE')
    require(original == current, 'Original shader tree changed')
    restored = json.loads((args.evidence / 'runtime/restored.json').read_text())
    require(all(restored[k] for k in ('normalConfigExact', 'normalModsExact', 'instanceExact', 'ordinarySaveExact'))
            and restored['ordinarySaveRestored'] is False, 'Restoration incomplete')
    scenes = [scene(args.evidence / 'runtime' / (name+'-paired-capture'), native['paired_zip_sha256'])
              for name in ('underwater-up-near', 'underwater-up-deep')]
    result = dict(schema='aqualumen-paired-water-audit-v1', passed=True, scenes=scenes, originalShadersExact=True,
                  nativeSSR1Tested=False, physicalAccepted=False, visualAccepted=False, performanceAcceptance=False,
                  normalRestoration=restored, openWork=['SSR1 controlled fixture',
                  'Controlled same-input optical/geometry counterfactual, not route-average brightness inference',
                  'Natural moving-wave visual acceptance; real fluid/contact simulation not validated'])
    result['evidence'] = [dict(path=str(p), sha256=sha(p)) for p in
                          (args.evidence / 'qualification.json', args.evidence / 'native-final/receipt.json',
                           args.evidence / 'control-compile.log', args.evidence / 'paired-compile.log',
                           args.evidence / 'input-sha256.json', args.evidence / 'runtime/restored.json',
                           args.evidence / 'compile-provenance.json', args.evidence / 'CLOSURE.json',
                           args.evidence / 'runtime-source-provenance.json',
                           args.evidence / 'runtime-used-source-reconstructed.py')]
    result['auditToolSHA256'] = sha(Path(__file__))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print(json.dumps(dict(passed=True, output=str(args.output), counts=[s['routeCounts'] for s in scenes])))


if __name__ == '__main__':
    main()
