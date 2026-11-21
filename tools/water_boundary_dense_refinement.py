"""Diagnostic-only dense refinement: change order, no optical/source predicates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import water_supported_transmission as quadrature

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-dense-sources-v1'
PATTERN = re.compile(r'const int WST_order=96;\nconst vec2 WST_rule\[96\]=vec2\[96\]\(\n.*?\);\n', re.S)


def build(out, order):
    assert order in (128, 192, 256)
    out = Path(out)
    out.mkdir(exist_ok=False)
    nodes = quadrature.legendre(order)
    assert len(nodes) == order
    assert abs(sum(w for _, w in nodes) - 2.0) < 1e-12
    assert all(-1 < x < 1 and w > 0 for x, w in nodes)
    replacement = f'const int WST_order={order};\nconst vec2 WST_rule[{order}]=vec2[{order}](\n'
    replacement += ',\n'.join(f'vec2({x:.17g},{w:.17g})' for x, w in nodes) + ');\n'
    evidence = {}
    for role in ('enabled', 'ledger', 'disabled'):
        old = (BASE / f'{role}.fsh').read_text()
        matches = list(PATTERN.finditer(old))
        assert len(matches) == 1
        match = matches[0]
        new = old[:match.start()] + replacement + old[match.end():]
        # Independent literal-prefix/suffix equality: every non-rule byte fixed.
        assert new[:match.start()] == old[:match.start()]
        assert new[match.start() + len(replacement):] == old[match.end():]
        with (out / f'{role}.fsh').open('x') as output:
            output.write(new)
        evidence[role] = dict(parentSHA256=hashlib.sha256(old.encode()).hexdigest(),
            outputSHA256=hashlib.sha256(new.encode()).hexdigest(),
            unchangedNonRuleSHA256=hashlib.sha256((old[:match.start()] + old[match.end():]).encode()).hexdigest())
    for index in range(3):
        blob = (BASE / f'geometry-stage{index}.glsl').read_bytes()
        with (out / f'geometry-stage{index}.glsl').open('xb') as output:
            output.write(blob)
    with (out / 'refinement.json').open('x') as output:
        json.dump(dict(schema='aqualumen-dense-rule-refinement-v1', order=order,
            parentOrder=96, onlyQuadratureTableChanged=True, roles=evidence,
            sourceConvergenceAccepted=False, fullGoalAchieved=False), output, indent=2, sort_keys=True)
    print('PREPARED', order, 'diagnostic dense rule; all non-rule bytes preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('--order', type=int, required=True)
    args = parser.parse_args()
    build(args.out, args.order)
