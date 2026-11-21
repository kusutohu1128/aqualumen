"""TEST-only double-precision angular integration; CPU, no renderer commands.

The synthetic source uses CHORD distance and peak radiance, not the native
pixel-integrated solar disk or its perpendicular-beam calibration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

IOR = 1.333
PEAK_TAG = (.25, .125, .0625)
REFERENCE_ABSOLUTE = 2e-7
REFERENCE_RELATIVE = 2e-4
REFERENCE_EXTENT = 6.0


def _dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b))


def _normal(v):
    length = math.sqrt(_dot(v, v))
    if length <= 0 or not math.isfinite(length):
        raise ValueError('nonfinite/zero direction')
    return tuple(x / length for x in v)


def _prepare(fixture):
    normal = tuple(fixture['mean_normal'])
    view = tuple(fixture['view_to_eye'])
    covariance = tuple(fixture['covariance'])
    if len(normal) != 3 or len(view) != 3 or len(covariance) != 3:
        raise ValueError('expected three-component normal/view/covariance')
    if not all(math.isfinite(v) for v in normal + view + covariance):
        raise ValueError('nonfinite fixture')
    # Preserve observed inputs; do not repair/re-normalize them silently.
    if abs(_dot(normal, normal) - 1) > 2e-6 or abs(_dot(view, view) - 1) > 2e-6:
        raise ValueError('observed direction outside unit-vector input scope')
    xx, xz, zz = covariance
    determinant = xx * zz - xz * xz
    if xx < 0 or zz < 0 or determinant < 0 or (xx == 0 and xz != 0):
        raise ValueError('indefinite covariance')
    root_x = math.sqrt(xx)
    cross = xz / root_x if root_x else 0.
    root_z = math.sqrt(determinant / xx if xx else zz)
    side = -1. if normal[1] < 0 else 1.
    projected = _dot(normal, view) / abs(normal[1])
    if abs(normal[1]) <= .5 or projected <= 1e-5:
        raise ValueError('mean outside declared interface domain')
    slopes = (-normal[0] / normal[1], -normal[2] / normal[1])
    # The plane-projected ratio is affine in standard-normal coordinates.
    a = -side * (root_x * view[0] + cross * view[2]) / projected
    b = -side * root_z * view[2] / projected
    return dict(normal=normal, view=view, covariance=covariance, root_x=root_x,
                cross=cross, root_z=root_z, side=side, mean_slope=slopes,
                projected=projected, affine=(a, b))


def _validate_source(source):
    if source.get('kind') not in ('constant', 'dark', 'gaussian'):
        raise ValueError('source kind must be constant, dark, or gaussian')
    if source['kind'] == 'gaussian':
        sigma = source.get('sigma', float('nan'))
        if not math.isfinite(sigma) or sigma <= 0:
            raise ValueError('positive finite CHORD sigma required')


def _node(prepared, x, z, source):
    sx = prepared['mean_slope'][0] + prepared['root_x'] * x
    sz = prepared['mean_slope'][1] + prepared['cross'] * x + prepared['root_z'] * z
    inverse_length = 1 / math.sqrt(1 + sx * sx + sz * sz)
    side = prepared['side']
    normal = (-side * sx * inverse_length, side * inverse_length, -side * sz * inverse_length)
    view = prepared['view']
    facing = _dot(normal, view)
    ratio = facing / abs(normal[1]) / prepared['projected']
    ci = min(1., max(0., facing))
    snell = 1 - IOR * IOR * (1 - ci * ci)
    tir = snell < 0
    reflected_y = -view[1] + 2 * facing * normal[1]
    transmitted_y = None
    if tir:
        reflectance, illumination = 1., 0.
    else:
        ct = math.sqrt(snell)
        perpendicular = (IOR * ci - ct) / (IOR * ci + ct)
        parallel = (ci - IOR * ct) / (ci + IOR * ct)
        reflectance = .5 * (perpendicular ** 2 + parallel ** 2)
        transmitted = tuple(-IOR * v + (IOR * facing - ct) * n for v, n in zip(view, normal))
        transmitted_y = transmitted[1]
        kind = source['kind']
        if kind == 'constant':
            illumination = 1.
        elif kind == 'dark':
            illumination = 0.
        elif kind == 'gaussian':
            sigma = source['sigma']
            if not math.isfinite(sigma) or sigma <= 0:
                raise ValueError('positive finite CHORD sigma required')
            direction = _normal(transmitted)
            chord2 = direction[0] ** 2 + (direction[1] - 1) ** 2 + direction[2] ** 2
            illumination = math.exp(-chord2 / (2 * sigma * sigma))
        else:
            raise ValueError('source kind must be constant, dark, or gaussian')
    valid = facing > 0 and reflected_y < 0 and (tir or transmitted_y > 0)
    return (ratio, ratio * reflectance, ratio * (1 - reflectance), ratio * tir,
            ratio * (1 - reflectance) * illumination), dict(valid=valid,
            facing=facing, reflected_y=reflected_y, transmitted_y=transmitted_y,
            snell=snell)


def _integrate(prepared, source, xnodes, znodes):
    terms = [[] for _ in range(5)]
    invalid = 0
    minimum_facing = 1.
    minimum_reflected_margin = float('inf')
    minimum_transmitted_y = float('inf')
    for x, wx in xnodes:
        for z, wz in znodes:
            node, domain = _node(prepared, x, z, source)
            probability = wx * wz
            for i in range(5):
                terms[i].append(probability * node[i])
            invalid += not domain['valid']
            minimum_facing = min(minimum_facing, domain['facing'])
            minimum_reflected_margin = min(minimum_reflected_margin, -domain['reflected_y'])
            if domain['transmitted_y'] is not None:
                minimum_transmitted_y = min(minimum_transmitted_y, domain['transmitted_y'])
    totals = [math.fsum(values) for values in terms]
    return dict(coefficients=totals[:4], source_transfer=totals[4],
                source_difference_C0=[totals[4] * peak for peak in PEAK_TAG],
                sampled_domain_valid=invalid == 0, invalid_sample_count=invalid,
                evaluated_nodes=len(xnodes) * len(znodes),
                minimum_facing=minimum_facing,
                minimum_reflected_down_margin=minimum_reflected_margin,
                minimum_transmitted_up_margin=None if minimum_transmitted_y == float('inf') else minimum_transmitted_y)


def finite_rule(fixture, source, order=3):
    """Finite-rule arithmetic; no opaque receiver lookup is simulated.

    Input sourceDifference means same-rule source minus dark; constant water
    reflection cancels. A caller must separately qualify actual receiver flags.
    """
    _validate_source(source)
    prepared = _prepare(fixture)
    rule = standard_normal_rule(order)
    result = _integrate(prepared, source, rule, rule)
    result.update(rule_order=order, source=source,
                  scope='Finite-node open-domain arithmetic; no actual receiver policy proof.')
    return result


def _legendre_rule(order):
    rule = []
    for i in range(1, order + 1):
        x = math.cos(math.pi * (i - .25) / (order + .5))
        for _ in range(30):
            previous, current = 1., x
            for degree in range(2, order + 1):
                previous, current = current, ((2 * degree - 1) * x * current - (degree - 1) * previous) / degree
            derivative = order * (x * current - previous) / (x * x - 1)
            change = current / derivative
            x -= change
            if abs(change) < 2e-15:
                break
        rule.append((x, 2 / ((1 - x * x) * derivative * derivative)))
    return sorted(rule)


def _inverse_zenith_seed(prepared, sigma):
    """Source-centered breakpoints, not a copied forward-optics integrand.

    From vector Snell geometry, a transmitting normal is parallel to t-eta*I.
    Choose the declared side; invert its slopes through the same covariance
    coordinates. Seed widths come from two neighboring target directions.
    This prevents accepting zero integrals simply because a grid missed a
    narrow bright lobe. No source mass is dropped around these seeds.
    """
    if prepared['root_x'] <= 0 or prepared['root_z'] <= 0:
        return None
    def inverse(target):
        candidate = _normal(tuple(t + IOR * v for t, v in zip(target, prepared['view'])))
        if candidate[1] * prepared['side'] < 0:
            candidate = tuple(-x for x in candidate)
        if abs(candidate[1]) < 1e-12:
            return None
        sx, sz = -candidate[0] / candidate[1], -candidate[2] / candidate[1]
        x = (sx - prepared['mean_slope'][0]) / prepared['root_x']
        z = (sz - prepared['mean_slope'][1] - prepared['cross'] * x) / prepared['root_z']
        return (x, z)
    center = inverse((0., 1., 0.))
    if center is None:
        return None
    perturbed = [inverse((math.sin(sigma), math.cos(sigma), 0.)),
                 inverse((-math.sin(sigma), math.cos(sigma), 0.)),
                 inverse((0., math.cos(sigma), math.sin(sigma))),
                 inverse((0., math.cos(sigma), -math.sin(sigma)))]
    widths = [max((abs(point[i] - center[i]) for point in perturbed if point is not None), default=0.)
              for i in (0, 1)]
    return dict(center=center, widths=widths)


def _window_axes(prepared, source, extent):
    base = [-extent + 2 * extent * i / 8 for i in range(9)]
    axes = [set(base), set(base)]
    seed = _inverse_zenith_seed(prepared, source['sigma']) if source['kind'] == 'gaussian' else None
    if seed is not None:
        for i in (0, 1):
            center, width = seed['center'][i], seed['widths'][i]
            for multiple in (-2., -1., 0., 1., 2.):
                point = center + multiple * width
                if -extent < point < extent:
                    axes[i].add(point)
    return [sorted(axis) for axis in axes], seed


def _composite_nodes(bounds, subdivisions, order):
    rule = _legendre_rule(order)
    nodes = []
    for left, right in zip(bounds, bounds[1:]):
        for piece in range(subdivisions):
            a = left + (right - left) * piece / subdivisions
            b = left + (right - left) * (piece + 1) / subdivisions
            midpoint, scale = (a + b) / 2, (b - a) / 2
            for node, weight in rule:
                x = midpoint + scale * node
                nodes.append((x, scale * weight * math.exp(-x * x / 2) / math.sqrt(2 * math.pi)))
    return nodes


def _window_domain(prepared, extent):
    """Sufficient finite-square geometric enclosure, not a Gaussian-tail test.

    Facing numerator is affine; the reflected-Y numerator is convex when the
    view is underwater, so their worst values occur at square corners. For a
    unit incident ray, refraction bends it by <=pi/2-asin(1/eta). Therefore a
    view zenith angle below asin(1/eta) keeps every non-TIR ray upward. A fixed
    1e-4-radian margin excludes float-direction/critical-boundary ambiguity.
    """
    view = prepared['view']
    corners = []
    for x in (-extent, extent):
        for z in (-extent, extent):
            sx = prepared['mean_slope'][0] + prepared['root_x'] * x
            sz = prepared['mean_slope'][1] + prepared['cross'] * x + prepared['root_z'] * z
            numerator = prepared['side'] * (-sx * view[0] + view[1] - sz * view[2])
            reflected_numerator = view[1] * (1 - sx * sx - sz * sz) - 2 * (sx * view[0] + sz * view[2])
            corners.append((numerator, reflected_numerator))
    angle = math.acos(max(-1., min(1., -view[1] / math.sqrt(_dot(view, view)))))
    transmission_margin = math.asin(1 / IOR) - angle
    facing_lower = min(x[0] for x in corners)
    reflected_upper = max(x[1] for x in corners)
    qualified = (prepared['side'] == -1 and view[1] < 0 and facing_lower > 1e-4
                 and reflected_upper < -1e-4 and transmission_margin > 1e-4)
    return dict(qualified=qualified, facing_numerator_lower=facing_lower,
                reflected_y_numerator_upper=reflected_upper,
                ideal_unit_view_transmission_angle_margin=transmission_margin,
                direction_input_roundoff_margin=1e-4,
                scope='Sufficient fixed-square near-vertical enclosure; not unbounded Gaussian visibility, receivers, or a universal floating-point bound.')


def _tail_bound(prepared, extent):
    one_tail = math.erfc(extent / math.sqrt(2))
    probability = one_tail * (2 - one_tail)
    absolute_first_moment = math.sqrt(2 / math.pi) * (
        math.exp(-extent * extent / 2) + (1 - math.exp(-extent * extent / 2)) * one_tail)
    projected_bound = probability + sum(abs(a) for a in prepared['affine']) * absolute_first_moment
    return dict(probability=probability, absolute_projected_mass_bound=projected_bound,
                C0_absolute_bound=PEAK_TAG[0] * projected_bound,
                scope='Bound on omitted source-minus-dark radiance only, since |T*source|<=1; does not guarantee outside-window validity or all-or-nothing acceptance.')


def _agreement(left, right):
    # Compare observable C0 components. The peak tag's largest component gives
    # the strongest absolute gate; coefficient convergence is also recorded.
    errors = [abs(a - b) for a, b in zip(left['source_difference_C0'], right['source_difference_C0'])]
    gates = [REFERENCE_ABSOLUTE + REFERENCE_RELATIVE * max(abs(a), abs(b))
             for a, b in zip(left['source_difference_C0'], right['source_difference_C0'])]
    coefficient_errors = [abs(a - b) for a, b in zip(left['coefficients'], right['coefficients'])]
    coefficient_gates = [REFERENCE_ABSOLUTE + REFERENCE_RELATIVE * max(abs(a), abs(b))
                         for a, b in zip(left['coefficients'], right['coefficients'])]
    return dict(accepted=all(e <= g for e, g in zip(errors + coefficient_errors, gates + coefficient_gates)),
                C0_absolute_errors=errors, C0_gates=gates,
                coefficient_absolute_errors=coefficient_errors)


def reference(fixture, source):
    """Empirically converged fixed-window Gaussian integral, no renormalization.

    GL6 on every seeded cell with 1/2/4 subdivisions plus a separate GL8
    order check at subdivision4. Two successive grid checks AND order check
    must pass the predeclared C0/coeff gates. This is not rigorous cubature
    error certification, and never reclassifies a finite native helper run.
    """
    _validate_source(source)
    prepared = _prepare(fixture)
    extent = REFERENCE_EXTENT
    axes, seed = _window_axes(prepared, source, extent)
    history = []
    for subdivisions, order in ((1, 6), (2, 6), (4, 6), (4, 8)):
        xnodes = _composite_nodes(axes[0], subdivisions, order)
        znodes = _composite_nodes(axes[1], subdivisions, order)
        result = _integrate(prepared, source, xnodes, znodes)
        result.update(cell_subdivisions=subdivisions, legendre_order=order)
        history.append(result)
    comparisons = [_agreement(a, b) for a, b in zip(history, history[1:])]
    enclosure = _window_domain(prepared, extent)
    tail = _tail_bound(prepared, extent)
    final = dict(history[-1])
    converged = all(check['accepted'] for check in comparisons)
    # A Gaussian cannot qualify via repeated underflow-to-zero. Such a case
    # remains explicitly inconclusive until another integration plan is declared.
    nonzero = source['kind'] != 'gaussian' or final['source_transfer'] > 1e-12
    qualified = enclosure['qualified'] and all(h['sampled_domain_valid'] for h in history)
    final.update(converged=converged and nonzero,
                 finite_window_domain_qualified=qualified,
                 reference_qualified=converged and nonzero and qualified,
                 extent=extent, source_seed=seed, source=source,
                 convergence_history=history, convergence_comparisons=comparisons,
                 finite_window_domain=enclosure, outside_window=tail,
                 outside_window_C0_absolute_bound=tail['C0_absolute_bound'],
                 absolute_tolerance=REFERENCE_ABSOLUTE, relative_tolerance=REFERENCE_RELATIVE,
                 no_renormalization=True,
                 scope='Fixed-window open-source radiance diagnostic, not the same unbounded all-or-nothing operator, receiver acceptance, physical energy, native solar pixel coverage, or adoption.')
    return final


def standard_normal_rule(order):
    """Gaussian quadrature for E[f(Z)], Z~N(0,1), via Jacobi eigensystem.

    The orthonormal probabilists' Hermite multiplication matrix has off-
    diagonals sqrt(k). Its eigenvalues are nodes; first-row eigenvector squares
    are probabilities. No package dependency or dropped-node normalization.
    """
    if not isinstance(order, int) or not 1 <= order <= 33:
        raise ValueError('supported standard-normal order is an integer 1..33')
    matrix = [[0.0] * order for _ in range(order)]
    vectors = [[float(i == j) for j in range(order)] for i in range(order)]
    for i in range(1, order):
        matrix[i - 1][i] = matrix[i][i - 1] = math.sqrt(i)
    for _ in range(100 * order * order):
        off, p, q = max(((abs(matrix[i][j]), i, j)
                         for i in range(order) for j in range(i + 1, order)),
                        default=(0.0, 0, 0))
        if off <= 2e-15:
            break
        app, aqq, apq = matrix[p][p], matrix[q][q], matrix[p][q]
        angle = .5 * math.atan2(2 * apq, aqq - app)
        cosine, sine = math.cos(angle), math.sin(angle)
        for k in range(order):
            if k not in (p, q):
                akp, akq = matrix[k][p], matrix[k][q]
                matrix[k][p] = matrix[p][k] = cosine * akp - sine * akq
                matrix[k][q] = matrix[q][k] = sine * akp + cosine * akq
        matrix[p][p] = cosine * cosine * app - 2 * sine * cosine * apq + sine * sine * aqq
        matrix[q][q] = sine * sine * app + 2 * sine * cosine * apq + cosine * cosine * aqq
        matrix[p][q] = matrix[q][p] = 0.0
        for k in range(order):
            vp, vq = vectors[k][p], vectors[k][q]
            vectors[k][p], vectors[k][q] = cosine * vp - sine * vq, sine * vp + cosine * vq
    else:
        raise ArithmeticError('Jacobi eigensystem did not converge')
    rule = sorted((matrix[i][i], vectors[0][i] ** 2) for i in range(order))
    # Odd Hermite rules are exactly symmetric; restore only that known identity
    # to remove eigensolver's ulp-scale antisymmetry, not a model mass repair.
    for i in range(order // 2):
        j = order - 1 - i
        node = (abs(rule[i][0]) + abs(rule[j][0])) * .5
        weight = (rule[i][1] + rule[j][1]) * .5
        rule[i], rule[j] = (-node, weight), (node, weight)
    if order % 2:
        rule[order // 2] = (0.0, rule[order // 2][1])
    if abs(math.fsum(w for _, w in rule) - 1) > 2e-14:
        raise ArithmeticError('Gaussian rule mass did not qualify')
    return rule


def export_rules(output):
    if output.exists() or output.is_symlink():
        raise ValueError('NEW output required')
    rules = {}
    for order in (3, 9, 17):
        rule = standard_normal_rule(order)
        errors = []
        for degree in range(2 * order):
            expected = 0.0 if degree % 2 else math.prod(range(1, degree, 2))
            actual = math.fsum(w * x ** degree for x, w in rule)
            errors.append(abs(actual - expected) / max(1.0, abs(expected)))
        rules[str(order)] = dict(nodes=[x for x, _ in rule], weights=[w for _, w in rule],
                                maximum_scaled_moment_error=max(errors),
                                checked_moment_degrees=list(range(2 * order)))
    report = dict(schema='aqualumen-standard-normal-rules-v1', rules=rules,
                  method='Double Jacobi eigensystem of probabilists Hermite multiplication matrix.',
                  scope='Probability moments, not angular-source or renderer acceptance.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def compare_fixture(fixture):
    """Reported errors are observations, never a new shipping/adoption gate."""
    sources = ({'kind': 'gaussian', 'sigma': .00465},
               {'kind': 'gaussian', 'sigma': .08}, {'kind': 'constant'})
    cases = []
    for source in sources:
        dense = reference(fixture, source)
        rules = []
        for order in (3, 9, 17):
            rule = finite_rule(fixture, source, order)
            rule['C0_absolute_difference_from_reference'] = [
                abs(a - b) for a, b in zip(rule['source_difference_C0'], dense['source_difference_C0'])]
            rule['common_domain_qualified'] = rule['sampled_domain_valid'] and dense['reference_qualified']
            rules.append(rule)
        cases.append(dict(source=source, reference=dense, finite_rules=rules))
    return dict(name=fixture.get('name'), pixel=fixture.get('pixel'),
                observed_input=fixture, cases=cases)


def analyze(input_path, output_path):
    if output_path.exists() or output_path.is_symlink():
        raise ValueError('NEW output required')
    raw = input_path.read_bytes()
    inputs = json.loads(raw)
    if not isinstance(inputs.get('fixtures'), list) or not inputs['fixtures']:
        raise ValueError('input requires a nonempty fixtures list')
    report = dict(schema='aqualumen-residual-angular-double-reference-v1',
                  input_path=str(input_path.resolve()),
                  input_sha256=hashlib.sha256(raw).hexdigest(),
                  input_provenance=inputs.get('provenance'),
                  peak_radiance_tag=PEAK_TAG, IOR=IOR,
                  source='exp(-||normalize(transmitted)-zenith||^2/(2*sigma^2)); constant=1, dark=0',
                  reference_C0_component_absolute=REFERENCE_ABSOLUTE,
                  reference_C0_relative=REFERENCE_RELATIVE,
                  native_arithmetic_C0_component_absolute=2e-6,
                  native_arithmetic_C0_relative=2e-4,
                  native_arithmetic_coefficient_absolute=2e-5,
                  assumptions=[
                      'Observed n,v,C are immutable inputs. Receiver qualification belongs to actual native snapshots, not this CPU model.',
                      'Dark baseline uses the same rule and source function, so constant reflected-water scatter cancels.',
                      'Peak dyadic tag retained, no perpendicular-beam/radiance recalibration or eta-squared changes.',
                      'Double exact Snell discriminant sign; native refract-vector-length TIR threshold is different and must be qualified separately away from critical.',
                      'GL6 grid refinement plus GL8 order check is empirical convergence, not a universal certified integration error.',
                      'Fixed-window source seeds avoid coarse-zero-only convergence; no dropped-invalid-point or missing-tail renormalization.',
                      'Finite-window diagnostic differs from the unbounded all-or-nothing domain acceptance rule; tail radiance bounds are not tail visibility guarantees.',
                      'No actual solar disk pixel derivative/filter comparison, Smith masking, multiple scatter, calibrated energy, reciprocity, actual Iris or adoption claim.'],
                  fixtures=[compare_fixture(fixture) for fixture in inputs['fixtures']])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-rules', type=Path)
    parser.add_argument('input', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    if args.export_rules is not None:
        if args.input is not None or args.output is not None:
            parser.error('export and analysis modes are exclusive')
        export_rules(args.export_rules)
        print('PASS standard-normal moments; ' + str(args.export_rules))
    else:
        if args.input is None or args.output is None:
            parser.error('INPUT.json NEW-OUTPUT.json or --export-rules NEW.json required')
        report = analyze(args.input, args.output)
        qualified = sum(case['reference']['reference_qualified']
                        for fixture in report['fixtures'] for case in fixture['cases'])
        print(f'CPU angular reference: {qualified}/{3 * len(report["fixtures"])} finite-window cases qualified; {args.output}')
        # Inconclusive reference-domain cases are retained, never a fake PASS.
        return 0 if qualified == 3 * len(report['fixtures']) else 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
