"""CPU-only TEST light-domain integral, not a shader/physical adoption.

Observed mean n and v are never silently normalized. Fixed-peak CHORD source,
original Gaussian slope measure/legacy Fresnel, no survival renormalization.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ETA = 1.333
PEAK = (.25, .125, .0625)
ABSOLUTE = 2e-6
RELATIVE = 2e-4


def laguerre_rule(order):
    """Positive rule for integral_0^infinity exp(-u) f(u) du.

    Orthonormal Laguerre multiplication matrix: diagonal2k+1, offdiagonal k.
    Eigenvalues seed roots; polynomial Newton refinement supplies nodes and
    derivative weights. This avoids loss in tiny eigenvector-tail components.
    No dependencies or quadrature mass normalization.
    """
    if not isinstance(order, int) or not 1 <= order <= 24:
        raise ValueError('integer Laguerre order1..24 required')
    a = [[0.] * order for _ in range(order)]
    q = [[float(i == j) for j in range(order)] for i in range(order)]
    for i in range(order):
        a[i][i] = 2 * i + 1.
        if i:
            a[i - 1][i] = a[i][i - 1] = float(i)
    for _ in range(100 * order * order):
        off, p, r = max(((abs(a[i][j]), i, j) for i in range(order)
                         for j in range(i + 1, order)), default=(0., 0, 0))
        if off <= 2e-15:
            break
        app, arr, apr = a[p][p], a[r][r], a[p][r]
        angle = .5 * math.atan2(2 * apr, arr - app)
        c, s = math.cos(angle), math.sin(angle)
        for k in range(order):
            if k not in (p, r):
                x, y = a[k][p], a[k][r]
                a[k][p] = a[p][k] = c * x - s * y
                a[k][r] = a[r][k] = s * x + c * y
        a[p][p], a[r][r] = c*c*app-2*s*c*apr+s*s*arr, s*s*app+2*s*c*apr+c*c*arr
        a[p][r] = a[r][p] = 0.
        for k in range(order):
            x, y = q[k][p], q[k][r]
            q[k][p], q[k][r] = c * x - s * y, s * x + c * y
    else:
        raise ArithmeticError('Laguerre eigensystem did not converge')
    def polynomial(x):
        previous, current = 1., 1 - x
        for degree in range(2, order + 1):
            previous, current = current, ((2 * degree - 1 - x) * current - (degree - 1) * previous) / degree
        return current, order * (current - previous) / x
    rule = []
    for i in range(order):
        x = a[i][i]
        for _ in range(5):
            value, derivative = polynomial(x)
            change = value / derivative
            x -= change
            if abs(change) < 2e-15 * max(1., x):
                break
        _, derivative = polynomial(x)
        rule.append((x, 1 / (x * derivative * derivative)))
    rule.sort()
    if any(x <= 0 or w <= 0 for x, w in rule) or abs(math.fsum(w for _, w in rule) - 1) > 2e-14:
        raise ArithmeticError('positive Laguerre mass did not qualify')
    return rule


def gaussian_integral(fixture, sigma=.00465, radial_order=8, azimuth_order=16):
    """Light-space quadrature; invalid node rejects the entire returned integral.

    Laguerre weights already contain exp(-u). No extra source exponential,
    survivor normalization, or beam-to-radiance calibration is applied here.
    """
    if not math.isfinite(sigma) or sigma <= 0 or not isinstance(azimuth_order, int) or azimuth_order < 1:
        raise ValueError('positive sigma and azimuth order required')
    context = _prepare(fixture)
    terms, minimum_facing, maximum_error = [], 1., 0.
    rule = laguerre_rule(radial_order)
    for u, weight in rule:
        cosine = 1 - sigma * sigma * u
        radicand = u * (2 - sigma * sigma * u)
        if radicand <= 0 or cosine <= 0:
            return dict(domain_qualified=False, source_difference_C0=None,
                        invalid_reason='Radial node outside declared upward CHORD branch',
                        evaluated_nodes=len(terms), invalid_nodes=1)
        sine = sigma * math.sqrt(radicand)
        for j in range(azimuth_order):
            phi = 2 * math.pi * (j + .5) / azimuth_order
            target = (sine * math.cos(phi), cosine, sine * math.sin(phi))
            try:
                node = _kernel(context, target)
            except ValueError as error:
                return dict(domain_qualified=False, source_difference_C0=None,
                            invalid_reason=str(error), evaluated_nodes=len(terms), invalid_nodes=1)
            terms.append(weight * node['kernel'])
            minimum_facing = min(minimum_facing, node['facing'])
            maximum_error = max(maximum_error, node['reconstruction_error'])
    transfer = sigma * sigma * (2 * math.pi / azimuth_order) * math.fsum(terms)
    return dict(domain_qualified=True, source_transfer=transfer,
                source_difference_C0=[peak * transfer for peak in PEAK],
                sigma=sigma, radial_order=radial_order, azimuth_order=azimuth_order,
                evaluated_nodes=len(terms), invalid_nodes=0, minimum_facing=minimum_facing,
                maximum_reconstruction_error=maximum_error,
                observed_view_norm_squared=context['m2'], outgoing_norm_squared=context['k2'],
                raw_inputs_preserved=True, no_renormalization=True,
                scope='Finite positive light-domain nodes only; not full-domain/tail visibility, receivers, zero/singular covariance, energy, reciprocity, native solar disk, GLSL or adoption.')


def _dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b))


def _prepare(fixture):
    normal, view, covariance = (tuple(fixture[key]) for key in ('mean_normal', 'view_to_eye', 'covariance'))
    if any(len(value) != 3 for value in (normal, view, covariance)) or not all(
            math.isfinite(x) for x in normal + view + covariance):
        raise ValueError('finite three-component observed n/v/C required')
    xx, xz, zz = covariance
    determinant = xx * zz - xz * xz
    if xx <= 0 or zz <= 0 or determinant <= 0:
        raise ValueError('strictly positive-definite covariance required; no epsilon repair')
    if normal[1] >= -.5 or view[1] >= 0:
        raise ValueError('mean/view outside underwater interface domain')
    mean_projected = _dot(normal, view) / abs(normal[1])
    m2 = _dot(view, view)
    k2 = 1 + ETA * ETA * (m2 - 1)
    if mean_projected <= 1e-5 or not math.isfinite(k2) or k2 <= 0:
        raise ValueError('nonpositive projection/outgoing norm')
    return dict(view=view, covariance=covariance, determinant=determinant,
                mean_slope=(-normal[0] / normal[1], -normal[2] / normal[1]),
                mean_projected=mean_projected, m2=m2, k2=k2, k=math.sqrt(k2))


def _kernel(context, target):
    if len(target) != 3 or not all(math.isfinite(x) for x in target) or abs(_dot(target, target) - 1) > 1e-12 or target[1] <= 0:
        raise ValueError('finite upward unit light direction required')
    view, k = context['view'], context['k']
    axis = tuple(k * t + ETA * v for t, v in zip(target, view))
    length2 = _dot(axis, axis)
    if length2 <= 0:
        raise ValueError('singular inverse axis')
    normal = tuple(x / math.sqrt(length2) for x in axis)
    facing, transmitted_dot = _dot(normal, view), _dot(target, normal)
    if normal[1] >= 0 or facing <= 0 or transmitted_dot >= 0:
        raise ValueError('wrong inverse branch; no normal flip')
    # GLSL refract uses raw dot(n,v); waterFresnel separately clamps its cosine.
    snell = 1 - ETA * ETA * (1 - facing * facing)
    if snell <= 0:
        raise ValueError('critical/TIR inverse branch excluded')
    ray = tuple(-ETA * v + (ETA * facing - math.sqrt(snell)) * n for v, n in zip(view, normal))
    error = max(abs(r - k * t) for r, t in zip(ray, target))
    if error > 1e-11 * max(1., k) or _dot(ray, ray) < 1e-6 or ray[1] <= 0 or -view[1] + 2 * facing * normal[1] >= 0:
        raise ValueError('inverse reconstruction/legacy node domain failed')
    sx, sz = -normal[0] / normal[1], -normal[2] / normal[1]
    dx, dz = sx - context['mean_slope'][0], sz - context['mean_slope'][1]
    xx, xz, zz = context['covariance']
    density = math.exp(-.5 * (zz * dx * dx - 2 * xz * dx * dz + xx * dz * dz) / context['determinant']) / (2 * math.pi * math.sqrt(context['determinant']))
    ci = min(1., max(0., facing))
    fresnel_radicand = 1 - ETA * ETA * (1 - ci * ci)
    if fresnel_radicand <= 0:
        transmission = 0.
    else:
        ct = math.sqrt(fresnel_radicand)
        rs = (ETA * ci - ct) / max(ETA * ci + ct, 1e-5)
        rp = (ci - ETA * ct) / max(ci + ETA * ct, 1e-5)
        transmission = 1 - .5 * (rs * rs + rp * rp)
    projected = facing / (abs(normal[1]) * context['mean_projected'])
    jacobian = context['k2'] * abs(transmitted_dot) / (length2 * abs(normal[1]) ** 3)
    value = density * projected * transmission * jacobian
    if not math.isfinite(value) or value < 0 or not math.isfinite(jacobian) or jacobian <= 0:
        raise ValueError('nonfinite/nonpositive light kernel')
    return dict(kernel=value, normal=normal, slope=(sx, sz), facing=facing,
                jacobian=jacobian, reconstruction_error=error, projected_ratio=projected)


def light_kernel(fixture, transmitted_unit):
    return _kernel(_prepare(fixture), transmitted_unit)


def export_rules(output):
    if output.exists() or output.is_symlink():
        raise ValueError('NEW output required')
    rules = {}
    for order in (8, 12, 16):
        rule = laguerre_rule(order)
        errors = [abs(math.fsum(w * u ** degree for u, w in rule) - math.factorial(degree))
                  / math.factorial(degree) for degree in range(2 * order)]
        rules[str(order)] = dict(nodes=[u for u, _ in rule], weights=[w for _, w in rule],
                                checked_moment_degrees=list(range(2 * order)),
                                maximum_scaled_moment_error=max(errors))
    report = dict(schema='aqualumen-positive-laguerre-rules-v1', rules=rules,
                  measure='exp(-u) du, u in[0,infinity); weights already include exp(-u)',
                  scope='Radial quadrature moments, not source/kernel/integration or physical acceptance.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def analyze(saved, output):
    if output.exists() or output.is_symlink():
        raise ValueError('NEW output required')
    raw = saved.read_bytes()
    packet = json.loads(raw)
    selected = [entry for entry in packet['dense_references'] if entry['source'] == 'narrow']
    fixed = {(128,128), (132,131), (123,127), (132,135), (132,127), (142,134)}
    if len(selected) != 6 or {tuple(entry['pixel']) for entry in selected} != fixed:
        raise ValueError('six fixed previously selected narrow fixtures required')
    samples, maximum_error, accepted_count = [], 0., 0
    for entry in selected:
        fixture, slope = entry['actual_fixture'], entry['reference']
        comparisons = []
        for radial, azimuth in ((8,16), (12,32), (16,64)):
            try:
                result = gaussian_integral(fixture, radial_order=radial, azimuth_order=azimuth)
            except ValueError as error:
                result = dict(domain_qualified=False, source_difference_C0=None, invalid_reason=str(error))
            errors, gates = None, None
            if result['domain_qualified']:
                actual, expected = result['source_difference_C0'], slope['source_difference_C0']
                errors = [abs(x-y) for x,y in zip(actual,expected)]
                gates = [ABSOLUTE + RELATIVE * max(abs(x),abs(y)) for x,y in zip(actual,expected)]
                maximum_error = max(maximum_error, *errors)
            accepted = result['domain_qualified'] and slope['reference_qualified'] and all(e<=g for e,g in zip(errors,gates))
            accepted_count += accepted
            comparisons.append(dict(radial_order=radial, azimuth_order=azimuth, light_integral=result,
                                    C0_absolute_errors=errors, C0_gates=gates, accepted=accepted))
        refinements = []
        for a,b in zip(comparisons,comparisons[1:]):
            if a['light_integral']['domain_qualified'] and b['light_integral']['domain_qualified']:
                x,y = a['light_integral']['source_difference_C0'],b['light_integral']['source_difference_C0']
                refinements.append(dict(from_rule=[a['radial_order'],a['azimuth_order']],
                    to_rule=[b['radial_order'],b['azimuth_order']],C0_absolute_deltas=[abs(u-v) for u,v in zip(x,y)]))
        samples.append(dict(pixel=entry['pixel'], actual_fixture=fixture,
                            frozen_slope_reference_C0=slope['source_difference_C0'],
                            frozen_slope_reference_qualified=slope['reference_qualified'],
                            frozen_slope_outside_window_C0_bound=slope['outside_window_C0_absolute_bound'],
                            comparisons=comparisons, refinements=refinements))
    report = dict(schema='aqualumen-cpu-light-domain-narrow-integral-v1', input_path=str(saved.resolve()),
        input_sha256=hashlib.sha256(raw).hexdigest(), sigma=.00465, IOR=ETA, peak_radiance=PEAK,
        C0_component_absolute=ABSOLUTE,C0_relative=RELATIVE, samples=samples,
        accepted_comparisons=accepted_count,total_comparisons=18,accepted=accepted_count==18,
        maximum_C0_component_absolute_error=maximum_error,raw_inputs_preserved=True,
        no_renormalization=True,GPU_qualified=False,physical_accepted=False,shipping_accepted=False,
        scope='Six fixed source-positive saved-float fixtures only. Light-domain finite quadrature versus unchanged qualified finite-window slope reference; not all Gaussian-domain/receiver validity, singular limits, sharp Sun/beam units, GLSL, natural Iris, motion/FPS, energy or adoption.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-rules', type=Path)
    parser.add_argument('saved', type=Path, nargs='?');parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    if args.export_rules:
        if args.saved or args.output:parser.error('export and analysis modes are exclusive')
        export_rules(args.export_rules);print('CPU Laguerre rule export: ' + str(args.export_rules));return 0
    if not args.saved or not args.output:parser.error('SAVED-ORACLE.json NEW-OUTPUT.json required')
    report=analyze(args.saved,args.output)
    print(('PASS' if report['accepted'] else 'INCONCLUSIVE')+f' CPU light integral {report["accepted_comparisons"]}/18; '+str(args.output))
    return 0 if report['accepted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
