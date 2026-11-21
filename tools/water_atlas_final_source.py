"""Bounded actual Iris FINAL main/source and view audit, not executed fetch proof."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from water_atlas_aligned_runtime import source_policy
from water_atlas_aligned_pack import gh


def main_tokens(source, patched=False):
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    body = source[source.index('void main()'):]
    if not patched:
        body = body.replace('gl_FragData[0]', 'iris_FragData0').replace('gl_FragColor', 'iris_FragData0')
    # Iris rewrites literal spelling (0.5 -> 0.5f), not integer address logic.
    body = re.sub(r'(?<![\w.])(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fF]?',
                  lambda m: format(Decimal(m[0].rstrip('fF')).normalize(), 'f'), body)
    return re.sub(r'\s+', '', body)


def audit(raw_path, pack_path):
    raw = json.loads(Path(raw_path).read_text())
    pack_path = Path(pack_path)
    encoded = pack_path.read_bytes()
    metadata = source_policy(encoded, pack_path.name)
    required = dict(available=True, readOnly=True, errorFlagConsumed=False,
                    observerVersion='0.1.3', scopeAuthorized=True,
                    programFrameViewportUnchanged=True,
                    world='AqualumenNaturalV2', worldId='b22dbccb-2970-41e6-847f-f183b1ec923d',
                    seed=308060, dimension='minecraft:overworld', packName=pack_path.name,
                    packSha256=hashlib.sha256(encoded).hexdigest())
    for key, wanted in required.items():
        if raw.get(key) != wanted:
            raise ValueError('Source observation field differs: '+key)
    if raw['viewport'] != [0, 0, 1600, 900] or 'NVIDIA' not in raw['renderer']:
        raise ValueError('Actual viewport/renderer differs')
    if raw['programBefore'] <= 0 or raw['programBefore'] != raw['programAfter'] or raw['frameBefore'] != raw['frameAfter']:
        raise ValueError('Unstable program/frame')
    for name, expected in [('viewWidth', 1600), ('viewHeight', 900)]:
        u = raw['viewUniforms'][name]
        if u['size'] != 1 or u['type'] != 5126 or u['location'] < 0 or u['value'] != expected:
            raise ValueError('Typed view uniform differs')
    stages = {s['type']: s for s in raw['stages']}
    if len(raw['stages']) != 2 or set(stages) != {35633, 35632}:
        raise ValueError('Actual stages differ')
    for stage in stages.values():
        b = stage['source'].encode()
        if len(b) != stage['sourceBytes'] or hashlib.sha256(b).hexdigest() != stage['sourceSha256']:
            raise ValueError('Actual source digest differs')
    files = gh._archive(encoded)
    if main_tokens(files['shaders/final.fsh'].decode()) != main_tokens(stages[35632]['source'], True):
        raise ValueError('Actual coordinate/fetch main differs from canonical pack')
    return dict(schema='aqualumen-atlas-actual-final-main-audit-v1',
                actualCoordinateAndFetchSourceQualified=True, actualViewUniformsQualified=True,
                renderer=raw['renderer'], GL=raw['GL'], program=raw['programBefore'], frame=raw['frameBefore'],
                phase_degrees=metadata['phase_degrees'], packSha256=required['packSha256'],
                actualFragmentSha256=stages[35632]['sourceSha256'],
                actualVertexSha256=stages[35633]['sourceSha256'],
                rawObservationSha256=hashlib.sha256(Path(raw_path).read_bytes()).hexdigest(),
                atlasTexelAddressesObserved=False, drawFreshnessProven=False,
                alignedRuntimeAccepted=False, physicalBandFixAccepted=False,
                scope='Actual linked-source cache for the current FINAL program plus scalar views. '
                      'Exact normalized main comparison only; no executed pixel-address, '
                      'same-invocation texture freshness, whole shader semantics or visual proof.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('pack', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.raw, args.pack), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
