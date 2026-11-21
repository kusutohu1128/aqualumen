"""Decode the final-pass TEST strip and compare it with the saved Anvil terrain."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
parser.add_argument('observer_zip', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
reference = Path(__file__).resolve().parents[1] / '2026-10-06-water-coast-world'
raw = json.loads((reference/'selected-raw-v1.json').read_text())
oracle = json.loads((reference/'geometry-audit.json').read_text())
row = json.loads((args.run/'coast-day.json').read_text())
run = json.loads((args.run/'run.json').read_text())
end = json.loads((args.run/'complete.json').read_text())
assert run['world_id'] == raw['worldId'] == row['world_id']
assert run['pack_sha256'] == row['pack_sha256'] == hashlib.sha256(args.observer_zip.read_bytes()).hexdigest()
assert run['shader_active'] and not run['shader_fallback'] and 'RTX 3080 Ti' in run['gl_renderer']
assert row['window_focused'] and row['framebuffer_resolution'] == [2560, 1440] and end['status'] == 'complete'
assert math.dist(row['actual_camera_position'], raw['unshiftedCameraPosition']) < 0.001
image = Image.open(args.run/'coast-day.png').convert('RGB')
assert image.size == (2560, 1440)


def value(x, row_from_bottom):
    y = image.height-1-row_from_bottom
    low = image.getpixel((x,y))
    high = image.getpixel((16+x,y))
    return struct.unpack('<f', bytes((*low[:2], *high[:2])))[0]


points = []
for index, point in enumerate(oracle['points']):
    expected = point['firstIntersection']
    assert value(index,6) == 123.5 and value(index,7) > .999
    travel = value(index,1)
    normal = [value(index,axis) for axis in range(2,5)]
    error = abs(travel-expected['travelMetres'])
    points.append(dict(prior=point['priorRole'], found=value(index,0)==1, metres=travel,
                       expectedMetres=expected['travelMetres'], errorMetres=error, normal=normal,
                       expectedNormal=expected['normal'], sampleRed=value(index,5)))
assert len(points)==16 and sum(p['prior']=='miss' for p in points)==8
passed = all(p['found'] and p['normal']==p['expectedNormal'] and p['errorMetres'] < .001 and p['sampleRed'] > 0 for p in points)
result = dict(world=run['world_id'], observer=run['pack_sha256'], passed=passed, points=points,
              maxErrorMetres=max(p['errorMetres'] for p in points))
with args.output.open('x') as out:
    json.dump(result, out, indent=2)
if not passed:
    raise SystemExit('Ray replay differs from independent first-cube distances or normals')
print('16 ray distances and normals agree. Maximum absolute error in metres', result['maxErrorMetres'])
