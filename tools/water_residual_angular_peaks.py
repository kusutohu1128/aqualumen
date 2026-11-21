"""Descriptive saved-map components only; no shader/quality acceptance."""
import argparse
from array import array
import json
import math
from pathlib import Path
import sys

SIZE = 257
ROI = {(x, y) for y in range(88, 169) for x in range(88, 169)
       if (x - 128) ** 2 + (y - 128) ** 2 <= 40 ** 2}
LUMINANCE = (.2126, .7152, .0722)


def components(luminance):
    peak = max(luminance.values(), default=0.)
    if peak <= 0:
        return []
    remaining = {point for point, value in luminance.items() if value > .2 * peak}
    result = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        frontier, region = [seed], []
        while frontier:
            point = frontier.pop()
            region.append(point)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor = (point[0] + dx, point[1] + dy)
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        frontier.append(neighbor)
        maximum = min(region, key=lambda point: (-luminance[point], point))
        result.append(dict(pixels=len(region), peak_pixel=list(maximum),
                           peak_luminance=luminance[maximum]))
    return sorted(result, key=lambda item: (-item['peak_luminance'], item['peak_pixel']))


def _raw(path):
    data = Path(path).read_bytes()
    if len(data) != SIZE * SIZE * 4 * 4:
        raise ValueError('Expected exact 257x257 little-endian RGBA32F')
    values = array('f')
    values.frombytes(data)
    if sys.byteorder != 'little':
        values.byteswap()
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Nonfinite readback')
    return values


def describe(directory):
    directory = Path(directory)
    common, domain = set(ROI), []
    for source in ('narrow', 'broad', 'constant', 'dark'):
        for order in (3, 9, 17):
            path = directory / f'{source}-gh{order}'
            status, eye, flags, scatter = [_raw(path / f'observer-slot{slot}.rgba32f')
                                         for slot in (4, 5, 6, 7)]
            valid = set()
            for x, y in ROI:
                p = (y * SIZE + x) * 4
                if (all(flags[p + c] == 1 for c in range(4))
                        and eye[p + 3] == 1 and scatter[p + 3] == 1
                        and status[p] == 1 and status[p + 1] == 1
                        and status[p + 2] > 0 and status[p + 3] == 0):
                    valid.add((x, y))
            common &= valid
            domain.append(dict(source=source, order=order, valid=len(valid),
                               excluded=len(ROI - valid)))
    report = dict(schema='aqualumen-angular-descriptive-peaks-v1',
                  ROI_points=len(ROI), common_domain_points=len(common), domain=domain,
                  fixed_policy=dict(center=[128, 128], radius=40, peak_fraction=.2,
                                    neighbors=8, luminance=LUMINANCE),
                  status='PASS' if common == ROI else 'INCONCLUSIVE',
                  quality_accepted=False, solar_source_class_accepted=False,
                  actual_node_count_proven=False, results=[])
    if common != ROI:
        return report
    for source in ('narrow', 'broad'):
        for order in (3, 9, 17):
            light = _raw(directory / f'{source}-gh{order}' / 'observer-slot0.rgba32f')
            dark = _raw(directory / f'dark-gh{order}' / 'observer-slot0.rgba32f')
            values = {}
            for x, y in ROI:
                p = (y * SIZE + x) * 4
                values[(x, y)] = max(0., math.fsum(w * (light[p + c] - dark[p + c])
                                                   for c, w in enumerate(LUMINANCE)))
            regions = components(values)
            report['results'].append(dict(source=source, order=order,
                                          peak_luminance=max(values.values()),
                                          component_count=len(regions), components=regions))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(describe(args.directory), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
