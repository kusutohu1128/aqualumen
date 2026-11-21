"""Fixed raw node inputs for independent CPU/GPU comparison, not scene search."""
from decimal import Decimal, localcontext
import math
import hashlib
from pathlib import Path
import struct
import argparse
import json

from water_snell_boundary_reference import ETA, diagnose, f32, family
from water_residual_sun_integral import sharp_cap_rule

SAVED = Path(__file__).resolve().parents[1] / 'reports/2026-10-03-water-residual-native-sun/native-cap-v1/fov2-rain0-cachepositive-enabled1'
PINS = {
    'observer-slot1.rgba32f': 'ef48981c9324fe56db7a2c1234b9aa6a451004624e598397c78a1a3281a8fb94',
    'observer-slot5.rgba32f': 'bf28a0320c92728461f7ff690551b7ba2707458003ded02643fe86097feca124',
    'observer-slot2.rgba32f': 'a92518e350ad0b42a168af36d78fe594d74785e5fdb339e2f986f9a6ec4d32e2',
}
PIXELS = ((128, 128), (132, 131), (123, 127), (132, 135), (132, 127), (142, 134))


def fixtures(include_saved=True):
    values = [0., -1., 0., 0., 1., 0., ETA]
    cases = [dict(name='normal', input=values,
                  reference=diagnose(values[:3], values[3:6], values[6]))]
    for entry in family()['cases']:
        reference = entry['result']
        cases.append(dict(name=f"up-{entry['j']}-{entry['side']}", family='up',
            j=entry['j'], side=entry['side'],
            input=reference['raw_v']+reference['raw_t']+[ETA], reference=reference))
    view = (f32(math.sqrt(1-.95**2)), f32(-.95), 0.)
    with localcontext() as context:
        context.prec = 120
        vx, vy, _ = map(Decimal, view)
        eta = Decimal(ETA)
        m2 = vx*vx+vy*vy
        magnitude = m2.sqrt()
        k = (1+eta*eta*(m2-1)).sqrt()
        ex, ey = vx/magnitude, vy/magnitude
        px, py = -vy/magnitude, vx/magnitude
        for j in range(12, 21):
            for side in (-1, 1):
                cosine = (-k/eta+side*Decimal(2)**(-j))/magnitude
                sine = (1-cosine*cosine).sqrt()
                target = (f32(cosine*ex-sine*px), f32(cosine*ey-sine*py), 0.)
                reference = diagnose(view, target)
                cases.append(dict(name=f'tilted-{j}-{side}', family='tilted', j=j, side=side,
                    input=list(view)+list(target)+[ETA], reference=reference))
    if include_saved:
        maps = {}
        for name, expected in PINS.items():
            raw = (SAVED/name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected or len(raw) != 257*257*16:
                raise ValueError('Pinned saved raw n/v/C map differs: '+name)
            maps[name] = raw
        nodes = sharp_cap_rule((0., 1., 0.), radial_order=4, azimuth_order=12)
        for x, y in PIXELS:
            offset = 16*(y*257+x)
            take = lambda name: list(struct.unpack_from('<4f', maps[name], offset)[:3])
            saved_fixture = dict(mean_normal=take('observer-slot1.rgba32f'),
                                 view_to_eye=take('observer-slot5.rgba32f'),
                                 covariance=take('observer-slot2.rgba32f'))
            for index, (direction, weight) in enumerate(nodes):
                target = [f32(value) for value in direction]
                view = saved_fixture['view_to_eye']
                cases.append(dict(name=f'saved-{x}-{y}-{index}', family='saved',
                    pixel=[x, y], node=index, weight=weight, saved_fixture=saved_fixture,
                    input=view+target+[ETA], reference=diagnose(view, target),
                    targetProvenance='NEW rounded CPU-generated cap direction; not an actual GPU target export'))
    return cases


def export(output):
    """NEW generated binary/reference packet; no external state mutation."""
    if output.exists() or output.is_symlink():
        raise ValueError('NEW output directory required')
    cases = fixtures()
    raw = b''.join(struct.pack('<7f', *case['input']) for case in cases)
    root = Path(__file__).resolve().parent
    sources = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
               ('water_snell_boundary_cases.py', 'water_snell_boundary_reference.py',
                'water_residual_sun_integral.py', 'water_residual_light_integral.py')}
    metadata = dict(schema='aqualumen-fixed-snell-node-inputs-v1', count=len(cases),
        inputSHA256=hashlib.sha256(raw).hexdigest(), sourceSHA256=sources, savedMapSHA256=PINS,
        fields=['view.x', 'view.y', 'view.z', 'generatedTarget.x', 'generatedTarget.y',
                'generatedTarget.z', 'eta'], cases=cases,
        gates=dict(vectorAbsolute=1e-7, scalarRelative=2e-4,
                   C0Absolute=2e-6, C0Relative=2e-4),
        scope='37 fixed synthetic boundary/normal nodes plus288 fixed saved-view/controlled-target nodes. Not actual Iris n/v/Sun targets or original whole-wrapper acceptance.',
        GPUAccepted=False, IrisAccepted=False, shippingAccepted=False)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs.f32').write_bytes(raw)
    (output/'cases.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export(args.export)
    except (ValueError, OSError):
        parser.exit(2, 'Refused invalid/existing export or changed input pins\n')
    print(f"CPU fixed node export: {result['count']} inputs; no GL")


if __name__ == '__main__':
    main()
