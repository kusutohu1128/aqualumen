"""Independent actual-MAIN refinement comparisons; finite orders aren't truth."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import water_supported_reflector_audit as retained

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-dense-main-01'
RULE = re.compile(r'const int WST_order=\d+;\nconst vec2 WST_rule\[\d+\]=vec2\[\d+\]\(\n.*?\);\n', re.S)


def stripped(text):
    result, count = RULE.subn('<DECLARED-QUADRATURE-TABLE>\n', text)
    assert count == 1
    return result


def audit(outputs):
    records = []
    exact = 0
    baseline = retained.audit(BASE)
    for path in [BASE, *map(Path, outputs)]:
        result = retained.audit(path)
        order = int(re.search(r'const int WST_order=(\d+);', (path / 'enabled.fsh').read_text()).group(1))
        for role in ('enabled', 'ledger', 'disabled'):
            assert stripped((path / f'{role}.fsh').read_text()) == stripped((BASE / f'{role}.fsh').read_text())
            exact += 1
        for stage in range(3):
            name = f'geometry-stage{stage}.glsl'
            assert (path / name).read_bytes() == (BASE / name).read_bytes()
            exact += 1
        for tag in ('black', 'green'):
            assert (path / tag / 'actual-tilted-water-vertices.f32').read_bytes() == (BASE / tag / 'actual-tilted-water-vertices.f32').read_bytes()
            exact += 1
            for role in ('enabled', 'ledger', 'disabled'):
                for original in (BASE / tag / f'{role}-actual-inputs').iterdir():
                    if original.is_file():
                        assert (path / tag / f'{role}-actual-inputs' / original.name).read_bytes() == original.read_bytes()
                        exact += 1
                assert (path / tag / f'{role}-depth.f32').read_bytes() == (BASE / tag / f'{role}-depth.f32').read_bytes()
                exact += 1
            for slot in (1, 2, 3, 4, 5):
                assert (path / tag / f'enabled-slot{slot}.rgba32f').read_bytes() == (BASE / tag / f'enabled-slot{slot}.rgba32f').read_bytes()
                exact += 1
        value = result['reflectedGreen']
        previous = records[-1]['reflectedGreen'] if records else value
        records.append(dict(order=order, output=str(path.relative_to(ROOT)),
            reflectedGreen=value, reflectionKinds=result['reflectionKinds'],
            independentRawComparisons=result['exactRawComparisons'],
            differenceFromPrevious=value - previous,
            relativeDifferenceFromPrevious=(value - previous) / value,
            sourceSHA256=hashlib.sha256((path / 'enabled.fsh').read_bytes()).hexdigest()))
    return dict(schema='aqualumen-actual-dense-refinement-audit-v1',
        exactRawGeometryInputAndNonRuleComparisons=exact, records=records,
        baselineResponse=baseline['reflectedGreen'],
        onlyQuadratureTableChanged=True, convergenceCertified=False,
        firstObjectGeometryProven=False, IrisAccepted=False, temporalAccepted=False,
        fullGoalAchieved=False,
        scope='Actual original MAIN selected source response vs increasing finite dense rules. All observed source maps, geometry, depth, uniforms and non-rule shader bytes fixed; no certified-integral or general-scene claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('outputs', nargs='+')
    args = parser.parse_args()
    print(json.dumps(audit(args.outputs), indent=2, sort_keys=True))
