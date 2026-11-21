"""CPU-only raw-binary32 Snell boundary reference; never a shader fix."""
import math
import struct
import argparse
import json
from decimal import Decimal, localcontext
from fractions import Fraction


def _from_bits(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def _round(value):
    """Exact rational -> binary32, nearest/ties-even, gradual underflow."""
    q = Fraction(value)
    sign = 0x80000000 if q < 0 else 0
    a, b = abs(q.numerator), q.denominator
    if a == 0:
        return _from_bits(sign)
    e = a.bit_length()-b.bit_length()
    if (a < b << e) if e >= 0 else (a << -e < b):
        e -= 1
    shift = 149 if e < -126 else 23-e
    scaled_a, scaled_b = (a << shift, b) if shift >= 0 else (a, b << -shift)
    mantissa, remainder = divmod(scaled_a, scaled_b)
    mantissa += 2*remainder > scaled_b or 2*remainder == scaled_b and mantissa & 1
    if e < -126:
        return _from_bits(sign | mantissa)
    if mantissa == 1 << 24:
        e += 1
        mantissa >>= 1
    if e > 127:
        raise ValueError('Binary32 arithmetic overflow')
    return _from_bits(sign | ((e+127) << 23) | (mantissa-(1 << 23)))


def _sqrt32(x):
    """Round sqrt rational by exact midpoint-square comparisons."""
    if type(x) is float and x == 0:
        return x
    q = Fraction(x)
    if q < 0:
        raise ValueError('Negative binary32 square root')
    lo, hi = 0, 0x7f7fffff
    while lo < hi:
        mid = (lo+hi+1)//2
        f = Fraction(_from_bits(mid))
        if f*f <= q:
            lo = mid
        else:
            hi = mid-1
    if lo == 0x7f7fffff:
        return _from_bits(lo)
    midpoint = (Fraction(_from_bits(lo))+Fraction(_from_bits(lo+1)))/2
    upper = q > midpoint*midpoint or q == midpoint*midpoint and lo & 1
    return _from_bits(lo+int(upper))


def _op(a, b, kind):
    negative_a, negative_b = math.copysign(1,a)<0, math.copysign(1,b)<0
    x, y = Fraction(a), Fraction(b)
    if x == 0 and (y == 0 or kind in ('*','/')) or y == 0 and kind == '*':
        negative = (negative_a and (negative_b if kind=='+' else not negative_b)) if kind in ('+','-') else negative_a != negative_b
        if kind == '/' and y == 0:
            raise ZeroDivisionError
        return _from_bits(0x80000000 if negative else 0)
    return _round(x+y if kind == '+' else x-y if kind == '-' else x*y if kind == '*' else x/y)


def _fma(a, b, c):
    if (a == 0 or b == 0) and c == 0:
        negative_product = (math.copysign(1,a)<0) != (math.copysign(1,b)<0)
        return _from_bits(0x80000000 if negative_product and math.copysign(1,c)<0 else 0)
    return _round(Fraction(a)*Fraction(b)+Fraction(c))


def f32(value):
    if not math.isfinite(value):
        raise ValueError('Nonfinite input')
    if type(value) is float and value == 0:
        return value
    return _round(value)


ETA = f32(1.333)
PRECISIONS = (80, 120)
RECONSTRUCTION_ABSOLUTE = Decimal('1e-60')
INVERSE_EPS = 8*2**-23


def _replay(v, t, eta, variant):
    fused = variant != 'unfused'
    def dot(a, b):
        value = 0.0
        for x, y in zip(a, b):
            value = _fma(x, y, value) if fused else _op(value, _op(x, y, '*'), '+')
        return value
    e2 = _op(eta, eta, '*')
    k2 = _op(1, _op(e2, _op(dot(v, v), 1, '-'), '*'), '+')
    if k2 <= 0:
        return dict(accepted=False, reason='k2', k2=k2)
    k = _sqrt32(k2)
    axis = tuple(_op(_op(k, t[i], '*'), _op(eta, v[i], '*'), '+') for i in range(3))
    axis2 = dot(axis, axis)
    if axis2 <= 0:
        return dict(accepted=False, reason='axis2', k2=k2)
    n = tuple(_op(x, _sqrt32(axis2), '/') for x in axis)
    facing, td = dot(n, v), dot(n, t)
    facing2 = _op(facing, facing, '*')
    d = (_op(1, _op(e2, _op(1, facing2, '-'), '*'), '-') if not fused else
         _fma(e2, facing2, _op(1, e2, '-')) if variant == 'fma_factored' else
         _fma(-e2, _op(1, facing2, '-'), 1))
    node = n[1] < 0 and facing > 0 and td < 0 and d > 0
    result = dict(normal=list(n), k2=k2, facing=facing, transmitted_dot=td,
        discriminant=d, accepted=False, support_predicate=node)
    if not node:
        result['reason'] = 'facet_or_critical'
        return result
    factor = _op(_op(eta, facing, '*'), _sqrt32(d), '-')
    forward = tuple(_fma(factor, n[i], -_op(eta, v[i], '*')) if fused else
        _op(-_op(eta, v[i], '*'), _op(factor, n[i], '*'), '+') for i in range(3))
    error = max(abs(_op(forward[i], _op(k, t[i], '*'), '-')) for i in range(3))
    bound = _op(INVERSE_EPS, max(1, k, eta), '*')
    length2 = dot(forward, forward)
    accepted = error <= bound and forward[1] > 0 and length2 >= 1e-6
    result.update(forward=list(forward), reconstruction_error=error,
        reconstruction_bound=bound, transmitted_length_squared=length2,
        reflected_y=_op(_op(_op(2, facing, '*'), n[1], '*'), v[1], '-'),
        accepted=accepted, reason='accepted' if accepted else 'reconstruction_or_transmitted_hemisphere_or_length')
    return result


def _vector(value):
    if len(value) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError('Three finite numeric coordinates required')
    return tuple(f32(x) for x in value)


def _physical(v, t, eta, precision):
    with localcontext() as context:
        context.prec = precision
        v, raw_t, e = tuple(map(Decimal, v)), tuple(map(Decimal, t)), Decimal(eta)
        dot = lambda a, b: sum(x*y for x, y in zip(a, b))
        target_norm = dot(raw_t, raw_t).sqrt()
        if target_norm == 0:
            return dict(precision=precision, supported=False, classification='INVALID_INPUT', reason='zero_target')
        t = tuple(x/target_norm for x in raw_t)
        k2 = 1+e*e*(dot(v, v)-1)
        if v[1] >= 0 or t[1] <= 0:
            return dict(precision=precision, supported=False, classification='INVALID_DOMAIN', reason='wrong_water_air_hemisphere')
        if k2 <= 0:
            return dict(precision=precision, supported=False, classification='INVALID_RAW_VIEW_NORM', reason='nonpositive_generalized_transmitted_norm_squared')
        k = k2.sqrt()
        axis = tuple(k*t[i]+e*v[i] for i in range(3))
        axis2 = dot(axis, axis)
        if axis2 <= 0:
            return dict(precision=precision, supported=False, classification='SINGULAR_INVERSE', reason='singular_axis')
        n = tuple(x/axis2.sqrt() for x in axis)
        facing, transmitted_dot = dot(n, v), dot(n, t)
        discriminant = 1-e*e*(1-facing*facing)
        supported = n[1] < 0 and facing > 0 and transmitted_dot < 0 and discriminant > 0
        result = dict(precision=precision, supported=supported,
            classification='SUPPORTED' if supported else 'PHYSICALLY_UNSUPPORTED', normal=[str(x) for x in n],
            support_axis_y=str(axis[1]), discriminant=str(discriminant),
            raw_v_norm_squared=str(dot(v, v)), raw_t_norm_squared=str(dot(raw_t, raw_t)),
            target_unit=[str(x) for x in t], k2=str(k2), facing=str(facing),
            transmitted_dot=str(transmitted_dot))
        if supported:
            cost = discriminant.sqrt()
            forward = tuple(-e*v[i]+(e*facing-cost)*n[i] for i in range(3))
            error = max(abs(forward[i]-k*t[i]) for i in range(3))
            result.update(forward=[str(x) for x in forward], reconstruction_error=str(error),
                jacobian_slope_per_solid_angle=str(k2*abs(transmitted_dot)/(axis2*abs(n[1])**3)))
            rs = (e*facing-cost)/(e*facing+cost)
            rp = (facing-e*cost)/(facing+e*cost)
            result.update(raw_cosine_fresnel=str((rs*rs+rp*rp)/2),
                raw_cosine_transmission=str(2*e*facing*cost*((e*facing+cost)**-2+(facing+e*cost)**-2)),
                fresnel_scope='Raw-cosine algebra, not normalized-incident physical calibration.',
                critical_limit_fresnel='1')
        return result


def _agreement(references):
    """Fixed abs+rel1e-60 comparison of ALL mapped numeric fields."""
    a, b = references
    agreement = a['supported'] == b['supported'] and a['classification'] == b['classification']
    comparisons = {}
    fields = ('normal','target_unit','forward','support_axis_y','discriminant','k2','facing',
        'transmitted_dot','raw_v_norm_squared','raw_t_norm_squared','jacobian_slope_per_solid_angle',
        'raw_cosine_fresnel','raw_cosine_transmission','reconstruction_error')
    with localcontext() as context:
        context.prec = 120
        for field in fields:
            if field not in a and field not in b:
                continue
            if field not in a or field not in b:
                agreement = False
                continue
            x, y = a[field], b[field]
            xs, ys = (x, y) if type(x) is list else ([x], [y])
            pairs = [(Decimal(x), Decimal(y)) for x, y in zip(xs, ys)]
            error = max(abs(x-y) for x, y in pairs)
            passed = all(abs(x-y) <= RECONSTRUCTION_ABSOLUTE*(1+max(abs(x),abs(y))) for x,y in pairs)
            comparisons[field] = dict(maximum_absolute_difference=str(error), qualified=passed)
            agreement &= passed
    return agreement, comparisons


def diagnose(v, t, eta=ETA):
    """Interpret raw v unchanged and t as a recorded physical direction."""
    v, t = _vector(v), _vector(t)
    eta = f32(eta)
    if not math.isfinite(eta) or eta <= 1:
        raise ValueError('Finite water-to-air eta greater than one required')
    references = [_physical(v, t, eta, precision) for precision in PRECISIONS]
    agreement, comparisons = _agreement(references)
    old = {kind:_replay(v, t, eta, kind) for kind in ('unfused', 'fma_outer', 'fma_factored')}
    classification = ('POSITIVE_SUPPORTED_NUMERIC_REJECTION' if references[-1]['supported']
        and not old['unfused']['accepted'] else 'SUPPORTED_REPLAY_ACCEPTED' if references[-1]['supported']
        else references[-1]['classification'])
    if not agreement:
        classification = 'INCONCLUSIVE_REFERENCE_PRECISION'
    return dict(physical=references[-1], references=references,
        raw_v=list(v), raw_t=list(t), eta=eta,
        raw_v_bits=[struct.pack('<f', x).hex() for x in v],
        raw_t_bits=[struct.pack('<f', x).hex() for x in t],
        eta_bits=struct.pack('<f', eta).hex(),
        precision_agreement=bool(agreement), precision_comparisons=comparisons,
        precision_policy='80/120digits; per-field abs+rel1e-60; support signs must agree, no support epsilon.',
        old_binary32=old, classification=classification,
        target_policy='Normalize ONLY raw t in Decimal as physical direction; raw v is never normalized.',
        input_policy='Python numeric inputs are explicitly rounded to binary32 first; stored bits feed both replays. Already-binary32 observed inputs and signed zeros remain unchanged.',
        arithmetic_policy='Exact rational nearest/ties-even binary32 primitives, gradual underflow; fused variants hypothetical, not actual GPU compiler evidence.',
        fused_policy='fma_outer/fma_factored use sequential fused dot products and final refract multiply-add; respectively outer1-eta²*(1-facing²) and factored eta²*facing²+(1-eta²). Axis products and k² outer arithmetic remain unfused.',
        replay_scope='Inverse-node facet/discriminant/refract/reconstruction/upward/length subset ONLY. Counterfactual reflected hemisphere, density, receiver traces and whole legacy admission are not accepted here.',
        bit_encoding='Hexadecimal little-endian4-byte binary32 octets; raw signed-zero inputs retained.',
        GPUQualified=False, physicalFixAccepted=False, shippingAccepted=False)


def family():
    """Fixed BEFORE output: no search, selection, or changed thresholds."""
    cases = []
    for j in range(12, 21):
        for side in (-1, 1):
            vy = f32(-1/Fraction(ETA)+side*Fraction(1, 2**j))
            vx = _sqrt32(1-Fraction(vy)**2)
            cases.append(dict(j=j, side=side, result=diagnose((vx, vy, 0), (0, 1, 0))))
    return dict(schema='aqualumen-cpu-snell-boundary-family-v1', cases=cases,
        positive_supported_numeric_rejections=sum(c['result']['classification']=='POSITIVE_SUPPORTED_NUMERIC_REJECTION' for c in cases),
        policy='vy=f32(-1/exact_f32_eta±2^-j), vx=correctly-rounded sqrt(1-vy²), vz0, unit up target; j12..20 BOTH sides. No optical response, density, or visual gate.',
        GPUQualified=False, physicalFixAccepted=False, shippingAccepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v', type=float, nargs=3)
    parser.add_argument('--t', type=float, nargs=3)
    parser.add_argument('--eta', type=float, default=ETA)
    parser.add_argument('--family', action='store_true')
    args = parser.parse_args()
    if args.family and (args.v is not None or args.t is not None or args.eta != ETA):
        parser.error('Fixed family cannot be combined with vector/index overrides')
    if not args.family and (args.v is None or args.t is None):
        parser.error('Specify both --v and --t, or --family')
    try:
        result = family() if args.family else diagnose(args.v, args.t, args.eta)
    except (ValueError, TypeError, OverflowError, ZeroDivisionError):
        parser.exit(2, 'Rejected unqualified/nonfinite arithmetic input\n')
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if not args.family and (result['classification'].startswith('INVALID') or result['classification']=='SINGULAR_INVERSE'):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
