"""Independent white GH3 tensor moments; no rendering/physical acceptance."""
from decimal import Decimal, localcontext
from fractions import Fraction
import json
import math
import struct
import sys


def _number(value):
    if type(value) not in (int, float, str, Decimal, Fraction):
        raise ValueError('Finite exact numeric input required')
    if type(value) is float and not math.isfinite(value):
        raise ValueError('Finite input required')
    if type(value) is Decimal and not value.is_finite():
        raise ValueError('Finite input required')
    return Fraction(value)


def _decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def _wick(indices, covariance):
    """Independent Isserlis pair sum, not a quadrature transform algorithm."""
    if not indices:
        return Fraction(1)
    if len(indices) % 2:
        return Fraction(0)
    return sum((covariance[indices[0]][indices[i]] *
                _wick(indices[1:i] + indices[i + 1:], covariance)
                for i in range(1, len(indices))), Fraction(0))


def _bits_value(bits):
    return Fraction(struct.unpack('<f', struct.pack('<I', bits))[0])


def _round32(value, square_root=False):
    """Exact rational comparison to binary32 neighbors, including ties-even."""
    negative = value < 0
    if square_root and negative:
        raise ValueError('Negative rounded Schur complement; no repair')
    value = abs(value)
    limit = _bits_value(0x7f7fffff)
    if value > (limit * limit if square_root else limit):
        raise ValueError('Finite binary32 domain exceeded')
    low, high = 0, 0x7f7fffff
    while low < high:
        middle = (low + high + 1) // 2
        candidate = _bits_value(middle)
        if (candidate * candidate if square_root else candidate) <= value:
            low = middle
        else:
            high = middle - 1
    if low != 0x7f7fffff:
        midpoint = (_bits_value(low) + _bits_value(low + 1)) / 2
        boundary = midpoint * midpoint if square_root else midpoint
        if value > boundary or (value == boundary and low % 2):
            low += 1
    return -_bits_value(low) if negative else _bits_value(low)


def _record32(value):
    return dict(fraction=str(value), decimal=repr(float(value)),
                bits=struct.pack('>f', float(value)).hex())


def _binary32(covariance, phase):
    """Separate unfused IEEE arithmetic model, not observed GPU operations."""
    r = _round32
    node = r(Fraction('1.7320508075688772'))
    rotation = r(Fraction('0.7071067811865476'))
    w = (r(Fraction(1, 6)), r(Fraction(2, 3)), r(Fraction(1, 6)))
    literals = dict(nodePositive=_record32(node), rotation45=_record32(rotation),
                    weights=list(map(_record32, w)))
    rounded_covariance, remainder = None, None
    try:
        xx, xz, zz = map(r, covariance)
        rounded_covariance = list(map(str, (xx, xz, zz)))
        a = r(xx, square_root=True)
        b = r(xz / a) if a else Fraction(0)
        remainder = r(zz - r(b * b))
        if (not a and xz) or remainder < 0:
            raise ValueError('Rounded covariance rejected; no clipping')
        c = r(remainder, square_root=True)
        cosine, sine = (rotation, rotation) if phase else (Fraction(1), Fraction(0))
        nodes = []
        for i, x in enumerate((-node, Fraction(0), node)):
            for j, y in enumerate((-node, Fraction(0), node)):
                u = r(r(cosine * x) - r(sine * y))
                v = r(r(sine * x) + r(cosine * y))
                nodes.append(dict(index=[i, j], weight=str(r(w[i] * w[j])),
                    rotated_white=list(map(str, (u, v))),
                    perturbation=list(map(str, (r(a * u), r(r(b * u) + r(c * v)))))))
        def moments(field):
            return {str(p) + str(q): sum((Fraction(n['weight']) * Fraction(n[field][0]) ** p *
                Fraction(n[field][1]) ** q for n in nodes), Fraction(0))
                for p in range(5) for q in range(5 - p)}
        white, transformed = moments('rotated_white'), moments('perturbation')
        identity = ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(1)))
        targets = {k: _wick([0] * int(k[0]) + [1] * int(k[1]), identity) for k in white}
        bound = Fraction(64, 2 ** 23)
        within = all(abs(white[k] - targets[k]) <= bound * (1 + abs(targets[k])) for k in white)
        return dict(available=True, literals=literals, nodes=nodes,
            rounded_covariance=rounded_covariance, rounded_schur=str(remainder),
            product_weight_mass=str(sum((Fraction(n['weight']) for n in nodes), Fraction(0))),
            white_degree4_moments={k: str(v) for k, v in white.items()},
            transformed_degree4_moments={k: str(v) for k, v in transformed.items()},
            white_degree4_abs_plus_relative_bound=str(bound),
            white_degree4_within_predeclared_bound=within, weightsRenormalized=False,
            operation_policy='round-nearest ties-even after each primitive; no FMA',
            moment_sum_policy='exact rational sum of rounded nodes and product weights, not GPU accumulation',
            zero_policy='canonical positive zero; not signed-zero GPU equivalence',
            covarianceRepaired=False, GPUArithmeticAccepted=False)
    except ValueError as error:
        return dict(available=False, reason=str(error), literals=literals,
                    rounded_covariance=rounded_covariance,
                    rounded_schur=str(remainder) if remainder is not None else None,
                    weightsRenormalized=False, covarianceRepaired=False, GPUArithmeticAccepted=False)


def _nodes(covariance, mean, precision, phase, wrong_order=False):
    xx, xz, zz = covariance
    with localcontext() as context:
        context.prec = precision
        a = _decimal(xx).sqrt()
        b = _decimal(xz) / a if xx else Decimal(0)
        c = _decimal((xx * zz - xz * xz) / xx if xx else zz).sqrt()
        z = (-Decimal(3).sqrt(), Decimal(0), Decimal(3).sqrt())
        w = (Fraction(1, 6), Fraction(2, 3), Fraction(1, 6))
        cosine = Decimal(2).sqrt() / 2 if phase else Decimal(1)
        sine = cosine if phase else Decimal(0)
        nodes = []
        for i, x in enumerate(z):
            for j, y in enumerate(z):
                u, v = cosine * x - sine * y, sine * x + cosine * y
                dx, dy = a * u, b * u + c * v
                if wrong_order:
                    lx, ly = a * x, b * x + c * y
                    dx, dy = cosine * lx - sine * ly, sine * lx + cosine * ly
                nodes.append(dict(index=[i, j], white=[str(x), str(y)],
                    rotated_white=[str(u), str(v)],
                    perturbation=[str(dx), str(dy)],
                    slope=[str(_decimal(mean[0]) + dx), str(_decimal(mean[1]) + dy)],
                    weight=str(w[i] * w[j])))
        moments = {str(p) + str(q): sum((_decimal(Fraction(n['weight'])) *
            (Decimal(n['perturbation'][0]) ** p if p else Decimal(1)) *
            (Decimal(n['perturbation'][1]) ** q if q else Decimal(1)) for n in nodes), Decimal(0))
            for p in range(5) for q in range(5 - p)}
        return nodes, moments


def evaluate(covariance, phase_degrees=0, mean=(0, 0)):
    """Nine fixed weights on mean+L R z; inputs preserved, not normalized."""
    if type(phase_degrees) not in (int, float) or phase_degrees not in (0, 45):
        raise ValueError('Only fixed phase0 or45 allowed')
    if len(covariance) != 3 or len(mean) != 2:
        raise ValueError('Covariance(xx,xz,zz) and mean(x,z) required')
    covariance, mean = tuple(map(_number, covariance)), tuple(map(_number, mean))
    xx, xz, zz = covariance
    if xx < 0 or zz < 0 or (xx == 0 and xz != 0) or xx * zz < xz * xz:
        raise ValueError('Exact PSD covariance required; no clipping or repair')
    matrix = ((xx, xz), (xz, zz))
    expected = {str(p) + str(q): _wick([0] * p + [1] * q, matrix)
                for p in range(5) for q in range(5 - p)}
    nodes, measured = _nodes(covariance, mean, 80, phase_degrees)
    _, finer = _nodes(covariance, mean, 120, phase_degrees)
    _, wrong = _nodes(covariance, mean, 80, phase_degrees, wrong_order=True)
    wrong_covariance = (((xx + zz) / 2 - xz, (xx - zz) / 2, (xx + zz) / 2 + xz)
                        if phase_degrees else covariance)
    with localcontext() as context:
        context.prec = 120
        residual = max(abs(measured[k] - _decimal(v)) for k, v in expected.items())
        agreement = all(abs(measured[k] - finer[k]) <= Decimal('1e-60') * (1 + abs(finer[k])) for k in measured)
        white6 = sum((_decimal(Fraction(n['weight'])) * Decimal(n['rotated_white'][0]) ** 6 for n in nodes), Decimal(0))
        white44 = sum((_decimal(Fraction(n['weight'])) * Decimal(n['rotated_white'][0]) ** 4 *
                       Decimal(n['rotated_white'][1]) ** 4 for n in nodes), Decimal(0))
    return dict(schema='aqualumen-white-gh-phase-reference-v1', phase_degrees=int(phase_degrees),
        exact=dict(mass='1', mean=list(map(str, mean)), covariance=list(map(str, covariance)),
                   central_moments={k: str(v) for k, v in expected.items()}),
        nodes=nodes, measured_central_moments={k: str(v) for k, v in measured.items()},
        max_degree4_residual=str(residual), degree_scope='TOTAL degree <=4 only',
        precision_agreement_80_120=agreement, reference_abs_plus_relative_tolerance='1e-60',
        wrong_order=dict(order='R L z, not L R z', covariance=list(map(str, wrong_covariance)),
                         measured_covariance=[str(wrong[k]) for k in ('20', '11', '02')],
                         matches_requested_covariance=wrong_covariance == covariance, policyAccepted=False),
        higher_degree=dict(white_X6='27/2' if phase_degrees else '9', gaussian_white_X6='15',
                           white_X4Z4='9/4' if phase_degrees else '9', gaussian_white_X4Z4='9',
                           measured_white_X6=str(white6), measured_white_X4Z4=str(white44),
                           invarianceAccepted=False, scope='Degree6/8 counterexamples outside TOTAL degree<=4 promise'),
        binary32=_binary32(covariance, phase_degrees),
        domain='Exact PSD, including zero/rank-deficient covariance; no epsilon repair',
        physicalAccepted=False, convergenceAccepted=False, shaderExecuted=False)


def main(arguments=None):
    """Fixed arity options keep negative rational literals as numeric data."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    usage = 'water_gh_phase_reference.py --covariance XX XZ ZZ [--phase 0|45] [--mean X Z]'
    if arguments == ['--help']:
        print(usage)
        return 0
    options, arity = {}, {'--covariance': 3, '--phase': 1, '--mean': 2}
    try:
        while arguments:
            key = arguments.pop(0)
            if key not in arity or key in options or len(arguments) < arity[key]:
                raise ValueError('Unknown, repeated or incomplete fixed option')
            options[key], arguments = arguments[:arity[key]], arguments[arity[key]:]
        report = evaluate(options['--covariance'], int(options.get('--phase', ['0'])[0]),
                          options.get('--mean', [0, 0]))
    except (ValueError, KeyError, TypeError):
        print('Invalid mathematical input. ' + usage, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
