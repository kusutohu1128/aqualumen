"""CPU-only audit of selected actual-main saved native angular observations.

Uses frozen double arithmetic, actual observer n/C/v, and same-rule source-
minus-dark C0. No GL commands, wave recreation, camera reconstruction, source
edits, renderer adoption, or post-hoc gate changes. Same author independent
arithmetic, not a third-party audit.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from water_residual_angular_reference import finite_rule, reference

SIZE = 257
PIXELS = ((104, 140), (152, 116), (112, 104), (144, 152),
          (116, 136), (136, 108), (148, 132))
COEFFICIENT_ABSOLUTE = 2e-5
C0_ABSOLUTE = 2e-6
C0_RELATIVE = 2e-4
FROZEN_REFERENCE_SHA = '9a4862ec226c07adddc68759e375115d8588eecfe131f321b4c00cf367e19879'


def compare_observation(fixture, source, order, coefficients, C0_delta):
    double = finite_rule(fixture, source, order)
    coefficient_errors = [abs(x - y) for x, y in zip(coefficients, double['coefficients'])]
    C0_errors = [abs(x - y) for x, y in zip(C0_delta, double['source_difference_C0'])]
    gates = [C0_ABSOLUTE + C0_RELATIVE * max(abs(x), abs(y))
             for x, y in zip(C0_delta, double['source_difference_C0'])]
    finite = len(coefficients) == 4 and len(C0_delta) == 3 and all(
        math.isfinite(x) for x in tuple(coefficients) + tuple(C0_delta))
    accepted = (finite and double['sampled_domain_valid'] and
                all(x <= COEFFICIENT_ABSOLUTE for x in coefficient_errors) and
                all(x <= y for x, y in zip(C0_errors, gates)))
    return dict(accepted=accepted, finite_rule=double,
                coefficient_component_absolute_errors=coefficient_errors,
                C0_component_absolute_errors=C0_errors, C0_component_gates=gates)


def _read(path, count, manifest):
    raw = path.read_bytes()
    if sys.byteorder != 'little' or len(raw) != count * 4:
        raise ValueError('saved binary32 size/endianness mismatch: ' + str(path))
    values = array.array('f')
    values.frombytes(raw)
    if not all(math.isfinite(x) for x in values):
        raise ValueError('nonfinite saved output: ' + str(path))
    manifest[str(path)] = hashlib.sha256(raw).hexdigest()
    return values


def _pixel(values, pixel):
    x, y = pixel
    index = (y * SIZE + x) * 4
    return list(values[index:index + 4])


def _qualification(slots, pixel):
    normal, covariance, status, eye, flags, scatter = [_pixel(slots[i], pixel) for i in (1, 2, 4, 5, 6, 7)]
    expected_footprint = struct.unpack('<f', struct.pack('<f', .035))[0]
    determinant = covariance[0] * covariance[2] - covariance[1] ** 2
    qualified = (flags == [1., 1., 1., 1.] and eye[3] == 1 and scatter[3] == 1
                 and status[0] == 1 and status[1] == 1 and status[2] > 0 and status[3] == 0
                 and normal[3] == 1 and covariance[3] == expected_footprint
                 and covariance[0] >= 0 and covariance[2] >= 0 and determinant >= 0
                 and covariance[0] + covariance[2] > 1e-5)
    return dict(qualified=qualified, actual_normal_grazing=normal,
                actual_covariance_footprint=covariance, actual_status=status,
                actual_eye_eligible=eye, actual_production_flags=flags,
                actual_scatter_eligible=scatter, covariance_determinant=determinant)


def _source(name):
    if name == 'narrow':
        return dict(kind='gaussian', sigma=.00465)
    if name == 'broad':
        return dict(kind='gaussian', sigma=.08)
    if name in ('constant', 'dark'):
        return dict(kind=name)
    raise ValueError('unknown actual source')


def audit(run, pixels=PIXELS, selection_scope='Original seven retained tracer pixels'):
    source_sha = hashlib.sha256(Path(__file__).with_name('water_residual_angular_reference.py').read_bytes()).hexdigest()
    if source_sha != FROZEN_REFERENCE_SHA:
        raise ValueError('frozen reference source changed')
    recorded_raw = (run / 'result.json').read_bytes()
    recorded = json.loads(recorded_raw)
    if recorded['schema'] != 'aqualumen-native-residual-angular-v1' or recorded['size'] != SIZE:
        raise ValueError('unexpected native artifact')
    expected = {(source, order) for source in ('narrow', 'broad', 'constant', 'dark') for order in (3, 9, 17)}
    if {(c['source'], c['rule']) for c in recorded['cases']} != expected or len(recorded['cases']) != 12:
        raise ValueError('native cases missing/duplicated')
    manifest = {str(run / 'result.json'): hashlib.sha256(recorded_raw).hexdigest()}
    images = {}
    for case in recorded['cases']:
        directory = run / case['path']
        images[case['source'], case['rule']] = {
            slot: _read(directory / f'observer-slot{slot}.rgba32f', SIZE * SIZE * 4, manifest)
            for slot in range(8)}
        for name in ('observer-expanded.fsh', 'pure-expanded.fsh', 'actual-inputs.json'):
            path = directory / name
            manifest[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    entries = []
    reference_entries = []
    reference_cache = {}
    max_coefficient = max_C0 = 0.
    accepted_count = qualified_count = 0
    all_input_exact = True
    baseline = images['narrow', 3]
    for case in recorded['cases']:
        name, order = case['source'], case['rule']
        slots, dark = images[name, order], images['dark', order]
        source = _source(name)
        for pixel in pixels:
            qualification = _qualification(slots, pixel)
            qualified_count += qualification['qualified']
            normal, covariance, eye = (_pixel(slots[slot], pixel)[:3] for slot in (1, 2, 5))
            fixture = dict(name=f'{name}-gh{order}', pixel=pixel,
                           mean_normal=normal, covariance=covariance, view_to_eye=eye)
            native_C0 = _pixel(slots[0], pixel)[:3]
            dark_C0 = _pixel(dark[0], pixel)[:3]
            delta = [a - b for a, b in zip(native_C0, dark_C0)]
            coefficients = _pixel(slots[3], pixel)
            inputs_exact = all(_pixel(slots[slot], pixel) == _pixel(baseline[slot], pixel)
                               for slot in (1, 2, 5))
            dark_inputs_exact = all(_pixel(slots[slot], pixel) == _pixel(dark[slot], pixel)
                                    for slot in (1, 2, 5, 6, 7))
            all_input_exact &= inputs_exact and dark_inputs_exact
            comparison = compare_observation(fixture, source, order, coefficients, delta)
            accepted = qualification['qualified'] and dark_inputs_exact and comparison['accepted']
            accepted_count += accepted
            max_coefficient = max(max_coefficient, *comparison['coefficient_component_absolute_errors'])
            max_C0 = max(max_C0, *comparison['C0_component_absolute_errors'])
            entry = dict(source=name, rule=order, pixel=pixel, fixture=fixture,
                         actual_qualification=qualification, actual_coefficients=coefficients,
                         actual_C0=native_C0, actual_same_rule_dark_C0=dark_C0,
                         actual_source_difference_C0=delta,
                         original_inputs_exact_across_rules_sources=inputs_exact,
                         same_rule_dark_inputs_exact=dark_inputs_exact,
                         comparison=comparison, accepted=accepted)
            if name != 'dark':
                key = (tuple(normal), tuple(covariance), tuple(eye), source['kind'], source.get('sigma'))
                if key not in reference_cache:
                    dense = reference(fixture, source)
                    reference_cache[key] = len(reference_entries)
                    reference_entries.append(dict(pixel=pixel, source=name,
                                                  actual_fixture=fixture, reference=dense))
                reference_index = reference_cache[key]
                dense = reference_entries[reference_index]['reference']
                entry['reference_index'] = reference_index
                entry['native_C0_absolute_difference_from_dense_reference'] = [
                    abs(a - b) for a, b in zip(delta, dense['source_difference_C0'])]
                entry['dense_comparison_domain_qualified'] = (qualification['qualified'] and dense['reference_qualified'])
            entries.append(entry)
    dense_qualified = sum(entry['reference']['reference_qualified'] for entry in reference_entries)
    return dict(schema='aqualumen-saved-angular-selected-double-oracle-v1', run=str(run.resolve()),
                recorded_native_status=recorded['status'], recorded_native_accepted=recorded['accepted'],
                frozen_reference_sha256=source_sha, selected_pixels=pixels,
                selection_scope=selection_scope, observer_finite_raw_arrays=len(images) * 8,
                selected_cases=12, selected_samples=len(entries),
                independently_qualified_samples=qualified_count,
                finite_arithmetic_accepted_samples=accepted_count,
                finite_arithmetic_accepted=accepted_count == len(entries),
                maximum_coefficient_component_absolute_error=max_coefficient,
                maximum_source_delta_C0_component_absolute_error=max_C0,
                coefficient_absolute_tolerance=COEFFICIENT_ABSOLUTE,
                C0_absolute_tolerance=C0_ABSOLUTE, C0_relative_tolerance=C0_RELATIVE,
                actual_inputs_exact_across_selected_rules_sources=all_input_exact,
                dense_unique_cases=len(reference_entries), dense_qualified_cases=dense_qualified,
                dense_reference_all_qualified=dense_qualified == len(reference_entries),
                samples=entries, dense_references=reference_entries, raw_sha256_manifest=manifest,
                scope='Selected actual-main finite-rule arithmetic and descriptive finite-window convergence. Does not reclassify original native status or accept energy, Gaussian-tail visibility, native solar pixel filtering, whole-frame/world, same PNG, natural Iris, appearance/motion/FPS or shipping.',
                assumptions=[
                    'Original observer slot1 normal, slot2 covariance and slot5 eye ray are direct immutable binary32 readbacks; no recreated waves or camera assumptions.',
                    'Same-rule source minus dark C0; reflection contribution cancels only under matching selected inputs and separately observed no-receiver status.',
                    'Peak dyadic synthetic CHORD Gaussian, not the stock beam-calibrated solar disk.',
                    'Double Snell-discriminant TIR vs native refract-length threshold remain distinct; this is a selected noncritical comparison.',
                    'Dense differences are descriptive only; rejected/zero-convergence references remain in the packet and are never renormalized or recast as PASS.',
                    'Same author independent double arithmetic, not third-party source/provenance audit.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pixels', help='Supplemental diagnostic x,y;x,y list; original seven otherwise')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('NEW output required')
    pixels = PIXELS
    scope = 'Original seven retained tracer pixels; not changed by supplemental selection.'
    if args.pixels:
        try:
            pixels = tuple(tuple(int(value) for value in pair.split(',')) for pair in args.pixels.split(';'))
        except ValueError:
            parser.error('pixels require x,y;x,y')
        if not pixels or any(len(pixel) != 2 or not all(0 <= value < SIZE for value in pixel) for pixel in pixels):
            parser.error('pixels outside image')
        scope = 'SEPARATE source-positive diagnostic coordinates supplied after native capture; no acceptance/adoption or original-seven reclassification.'
    report = audit(args.run, pixels, scope)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(('PASS' if report['finite_arithmetic_accepted'] else 'RED') +
          f' finite-rule arithmetic {report["finite_arithmetic_accepted_samples"]}/{report["selected_samples"]}; '+
          f'dense domain/convergence {report["dense_qualified_cases"]}/{report["dense_unique_cases"]}; '+str(args.output))
    return 0 if report['finite_arithmetic_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
