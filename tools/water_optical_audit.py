"""Check saved water-interface vectors against Snell/Fresnel and fixed image ROIs."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys

ROIS = {
    'near-tongue': (1350, 120, 1510, 300),
    'top-rim': (40, 0, 400, 180),
    'interior': (700, 350, 900, 550),
    'exterior': (1500, 20, 1600, 120),
    'deep-top-loop': (1380, 0, 1440, 60),
    'deep-right-loop': (1380, 600, 1460, 700),
    'deep-left-loop': (150, 600, 320, 800),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def snell(normal, view, ratio=1.333):
    ci = max(0.0, min(1.0, sum(n*v for n, v in zip(normal, view))))
    k = 1.0 - ratio*ratio*(1.0-ci*ci)
    if k <= 0:
        return k, 1.0, (0.0, 0.0, 0.0)
    ct = math.sqrt(k)
    rs = (ratio*ci-ct)/(ratio*ci+ct)
    rp = (ci-ratio*ct)/(ci+ratio*ct)
    direction = tuple(-ratio*v + (ratio*ci-ct)*n for n, v in zip(normal, view))
    return k, 0.5*(rs*rs+rp*rp), direction


def load(directory):
    m = json.loads((directory / 'manifest.json').read_text())
    require(m['available'] and m['beforeReadStateRestored'] and m['afterReadStateRestored']
            and m['quadInvocationReturnedObserved'] and m['previewUniform'] == 0, 'Pairing unavailable')
    w, h = m['width'], m['height']
    data = {}
    for key in ('classification', 'sourceC0', *('optics-colortex'+str(i) for i in (1,2,3,13,14,15))):
        entry = m['files'][key]
        require(Path(entry['name']).name == entry['name'], 'Unsafe raw path')
        path = directory / entry['name']
        raw = path.read_bytes()
        require(len(raw) == w*h*16 and len(raw) == entry['bytes']
                and hashlib.sha256(raw).hexdigest() == entry['sha256'], 'Raw identity/extent mismatch')
        values = array('f')
        values.frombytes(raw)
        if sys.byteorder != 'little':
            values.byteswap()
        data[key] = values
    return m, data


def analyze(directory):
    m, data = load(directory)
    w, h = m['width'], m['height']
    c, n, v, t = (data[k] for k in ('classification', 'optics-colortex13', 'optics-colortex14', 'optics-colortex15'))
    geometry, before, position, color = (data[k] for k in ('optics-colortex2', 'optics-colortex3', 'optics-colortex1', 'sourceC0'))
    result = dict(scene=m['scene'], frame=m['frame'], manifestSHA256=hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest(),
                  maxDiscriminantError=0.0, maxDirectionErrorAwayFromCritical=0.0,
                  maxFresnelErrorAwayFromCritical=0.0, maxNormalBlendError=0.0,
                  transmitting=0, downwardTransmitting=0, screenReceiverDownward=0, criticalUncertain=0)
    for at in range(0, w*h*4, 4):
        if c[at+3] != 1:
            continue
        require(all(math.isfinite(a[at+j]) for a in (c,n,v,t,geometry,before,position,color) for j in range(4)), 'Nonfinite input')
        normal, view = tuple(n[at:at+3]), tuple(v[at:at+3])
        require(abs(sum(x*x for x in normal)-1) < 2e-5 and abs(sum(x*x for x in view)-1) < 2e-5, 'Nonunit normal/view')
        k, f, ray = snell(normal, view)
        result['maxDiscriminantError'] = max(result['maxDiscriminantError'], abs(k-n[at+3]))
        if abs(k) <= 1e-5:
            result['criticalUncertain'] += 1
        else:
            result['maxFresnelErrorAwayFromCritical'] = max(result['maxFresnelErrorAwayFromCritical'], abs(f-c[at+1]))
            result['maxDirectionErrorAwayFromCritical'] = max(result['maxDirectionErrorAwayFromCritical'], max(abs(ray[j]-t[at+j]) for j in range(3)))
        flags = geometry[at+3]
        require(flags == int(flags) and 0 <= flags <= 3, 'Invalid interface flags')
        blend = before[at+3]
        require(0 <= blend <= 1, 'Invalid grazing blend')
        if int(flags) & 1:
            mixed = tuple(geometry[at+j]*(1-blend)+before[at+j]*blend for j in range(3))
            length = math.sqrt(sum(x*x for x in mixed))
            require(length > 0, 'Degenerate blend')
            result['maxNormalBlendError'] = max(result['maxNormalBlendError'], max(abs(mixed[j]/length-normal[j]) for j in range(3)))
        if c[at+1] < .9999:
            result['transmitting'] += 1
            if t[at+1] < 0:
                result['downwardTransmitting'] += 1
                result['screenReceiverDownward'] += int(t[at+3] == 1)
    require(result['maxDiscriminantError'] < 1e-5, 'Snell discriminant disagreement')
    require(result['maxFresnelErrorAwayFromCritical'] < .005, 'Fresnel disagreement away from critical band')
    require(result['maxDirectionErrorAwayFromCritical'] < .005, 'Refraction disagreement away from critical band')
    require(result['maxNormalBlendError'] < 2e-5, 'Actual normal differs from recorded grazing blend')
    regions = {}
    for name, box in ROIS.items():
        counts = dict(water=0, transmitting=0, downward=0, tir=0, grazingChanged=0, screenReceiver=0)
        for display_y in range(max(0, box[1]), min(h, box[3])):
            for x in range(max(0, box[0]), min(w, box[2])):
                at = ((h-1-display_y)*w+x)*4
                if c[at+3] != 1:
                    continue
                counts['water'] += 1
                counts['grazingChanged'] += int(before[at+3] < 1)
                if c[at+1] < .9999:
                    counts['transmitting'] += 1
                    counts['downward'] += int(t[at+1] < 0)
                    counts['screenReceiver'] += int(t[at+3] == 1)
                else:
                    counts['tir'] += 1
        counts['downwardFractionOfTransmitting'] = counts['downward']/max(1,counts['transmitting'])
        regions[name] = dict(displayBox=list(box), counts=counts)
    result['regions'] = regions
    result['sample1430_200'] = {}
    if w > 1430 and h > 200:
        at = ((h-1-200)*w+1430)*4
        result['sample1430_200'] = {key:list(values[at:at+4]) for key,values in data.items()}
    result['interpretationLimits'] = ['ROIs were declared before numeric inspection; boxes are not annotated fold-pixel masks.',
        'Direction agreement and a downward ray do not establish physical secondary water-surface visibility.',
        'No sufficient-cause decision from ROI percentage alone; compare images and radiometric source before a fix.',
        'C0 may include later translucent draws while optical records describe surviving water draws.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.capture)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({k:result[k] for k in ('scene','transmitting','downwardTransmitting','maxDirectionErrorAwayFromCritical')}))


if __name__ == '__main__':
    main()
