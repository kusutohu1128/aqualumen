"""Projection-only solar size estimate, not rendered visual acceptance."""
import argparse
import json
import math
from pathlib import Path
import re


def apparent_diameter(height, vertical_fov_degrees, angular_radius):
    values = (height, vertical_fov_degrees, angular_radius)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Projection inputs must be finite')
    if height <= 0 or not 0 < vertical_fov_degrees < 180:
        raise ValueError('Invalid viewport or vertical field of view')
    if not 0 < angular_radius < math.pi / 2:
        raise ValueError('Invalid angular radius')
    return height * math.tan(angular_radius) / math.tan(
        math.radians(vertical_fov_degrees) / 2)


def source_radius(source):
    matches = re.findall(
        r'^const\s+float\s+SUN_ANGULAR_RADIUS\s*=\s*([0-9.eE+-]+)\s*;',
        source, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError('Expected one literal production Sun angular radius')
    return float(matches[0])


def observed_projection(observation):
    projection = observation['projection']
    for container, flags in ((observation, ('available', 'stateRestored',
                                            'scopeAuthorized')),
                             (projection, ('available', 'requested',
                                           'stateUnchanged'))):
        if any(container.get(flag) is not True for flag in flags):
            raise ValueError('Projection observation is not qualified')
    if projection.get('matrixOrder') != (
            'column-major; index=column*4+row; GLSL column vectors'):
        raise ValueError('Unknown matrix storage order')
    if (projection['program'] != projection['programAfter'] or
            projection['frameBefore'] != projection['frameAfter'] or
            projection['stateBefore'] != projection['stateAfter']):
        raise ValueError('Projection observation changed context')
    uniform = projection['matrices']['gbufferProjection']
    matrix = uniform['values']
    if (uniform['type'] != 35676 or uniform['size'] != 1 or
            uniform['location'] < 0 or len(matrix) != 16 or
            not all(math.isfinite(value) for value in matrix)):
        raise ValueError('Invalid typed projection matrix')
    if (any(abs(matrix[index]) > 1e-7
            for index in (1, 2, 3, 4, 6, 7, 8, 9, 12, 13, 15)) or
            matrix[0] <= 0 or matrix[5] <= 0 or
            abs(matrix[11] + 1) > 1e-7 or
            matrix[10] >= -1 or matrix[14] >= 0):
        raise ValueError('Only centered perspective projections are supported')
    viewport = projection['viewport']
    if (len(viewport) != 4 or viewport[:2] != [0, 0] or
            any(type(value) is not int or value <= 0 for value in viewport[2:])):
        raise ValueError('Invalid actual viewport')
    width, height = viewport[2:]
    for name, expected in (('viewWidth', width), ('viewHeight', height)):
        scalar = projection['scalars'][name]
        if (scalar['type'] != 5126 or scalar['size'] != 1 or
                scalar['location'] < 0 or scalar['value'] != expected):
            raise ValueError('Viewport differs from typed shader dimensions')
    if not math.isclose(matrix[5] / matrix[0], width / height, rel_tol=1e-5):
        raise ValueError('Projection aspect differs from viewport')
    return height, math.degrees(2 * math.atan(1 / matrix[5]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height', type=int)
    parser.add_argument('--vertical-fov', type=float)
    parser.add_argument('--observation', type=Path)
    args = parser.parse_args()
    if args.observation:
        if args.height is not None or args.vertical_fov is not None:
            parser.error('Observation and supplied projection cannot be combined')
        height, vertical_fov = observed_projection(
            json.loads(args.observation.read_text()))
    else:
        if args.height is None or args.vertical_fov is None:
            parser.error('Supply an observation or both height and vertical FOV')
        height, vertical_fov = args.height, args.vertical_fov
    source = Path(__file__).resolve().parents[1] / 'shaders/lib/atmosphere.glsl'
    radius = source_radius(source.read_text())
    print(json.dumps({
        'angular_radius_radians': radius,
        'angular_diameter_degrees': math.degrees(2 * radius),
        'height': height,
        'vertical_fov_degrees': vertical_fov,
        'projection_source': str(args.observation) if args.observation else 'supplied',
        'centered_disk_diameter_pixels': apparent_diameter(
            height, vertical_fov, radius),
        'scope': 'Centered pinhole projection only; excludes clouds, glare, '
                 'tone mapping, pixel coverage and off-axis projection. '
                 'Observation describes its recorded frame, not current gameplay '
                 'or a proven same-frame screenshot. Supplied FOV is not measured.',
        'visual_accepted': False,
    }, indent=2))


if __name__ == '__main__':
    main()
