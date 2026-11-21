"""CPU diagnostic partition of an observed plane's source window, not world geometry.

No production inclusion or SSR replacement. Raw normal/view/index/covariance
and shifted facet origin must be preserved. Outside-window source remains
unobserved; this interface does not call it physically black.
"""
import math
import water_source_boundary_oracle as oracle
import water_supported_rotated as rotated


def _value(coefficients, x):
    total = 0.0
    for coefficient in reversed(coefficients):
        total = total * x + coefficient
    return total


def _scale(coefficients, factor):
    return tuple(factor * value for value in coefficients)


def _add(*polynomials):
    return tuple(math.fsum(p[i] if i < len(p) else 0.0 for p in polynomials)
                 for i in range(max(map(len, polynomials))))


def _multiply(a, b):
    return tuple(math.fsum(a[j] * b[i-j] for j in range(len(a)) if 0 <= i-j < len(b))
                 for i in range(len(a) + len(b) - 1))


def _roots(coefficients, lo=-8.0, hi=8.0):
    coefficients = list(coefficients)
    while coefficients and coefficients[-1] == 0.0:
        coefficients.pop()
    if len(coefficients) < 2:
        return []
    maximum = max(map(abs, coefficients))
    coefficients = [a / maximum for a in coefficients]
    if len(coefficients) == 2:
        root = -coefficients[0] / coefficients[1]
        return [root] if lo < root < hi else []
    derivative = [i * coefficients[i] for i in range(1, len(coefficients))]
    points = [lo, *_roots(derivative, lo, hi), hi]
    roots = []
    for point in points[1:-1]:
        if abs(_value(coefficients, point)) <= 1e-13:
            roots.append(point)
    for a, b in zip(points, points[1:]):
        fa, fb = _value(coefficients, a), _value(coefficients, b)
        if fa * fb >= 0:
            continue
        for _ in range(60):
            mid = (a + b) * .5
            fm = _value(coefficients, mid)
            if fa * fm <= 0:
                b = mid
            else:
                a, fa = mid, fm
        roots.append((a + b) * .5)
    return sorted(set(roots))


def _transform(matrix, vector):
    return tuple(math.fsum(matrix[k*4+j] * vector[k] for k in range(3)) for j in range(3))


def plane_node(context, matrix, projection, origin, distance, x, z):
    q, _ = rotated.basis(context)
    node = rotated.node(context, q, x, z, 1)
    if not node['supported']:
        return node, dict(kind='unsupported')
    axis = tuple(a + b for a, b in zip(context['view'], node['target']))
    length = math.sqrt(math.fsum(a*a for a in axis))
    facet = tuple(a / length for a in axis)
    offset = _transform(matrix, facet)
    start = tuple(origin[i] + .06 * offset[i] for i in range(3))
    return node, oracle.first_plane(start, _transform(matrix, node['target']), projection, distance)


def partition(context, matrix, projection, origin, distance, x, fade_knots=False):
    """Return physical-reflection support AND safe observed-plane intervals."""
    if len(matrix) != 16 or len(projection) != 16 or len(origin) != 3:
        raise ValueError('Explicit column-major camera matrices and view origin required')
    if not all(math.isfinite(a) for a in (*matrix, *projection, *origin, distance, x)) or distance <= 0:
        raise ValueError('Finite camera/positive observed-plane distance required')
    if any(projection[i] != 0 for i in (3, 7, 15)) or projection[11] >= 0:
        raise ValueError('Declared perspective depth-plane domain required')
    q, b = rotated.basis(context)
    sx, sz = context['meanSlope'][0] + b[0][0]*x, context['meanSlope'][1] + b[1][0]*x
    s0 = (sx, -1.0, sz)
    s1 = (b[0][1], 0.0, b[1][1])
    h = (math.fsum(a*a for a in s0), 2*math.fsum(a*c for a, c in zip(s0, s1)),
         math.fsum(a*a for a in s1))
    f = tuple(math.fsum(a*v for a, v in zip(s, context['view'])) for s in (s0, s1))
    S0, S1 = _transform(matrix, s0), _transform(matrix, s1)
    V = _transform(matrix, context['view'])
    ray_polynomials = [_add(_scale(h, -V[i]), _scale(_multiply(f, (S0[i], S1[i])), 2.0)) for i in range(3)]
    bounds = [-8.0, 8.0]
    bounds += _roots(ray_polynomials[2])
    # Positive crossing changes only where plane/origin coincide or ray Z=0.
    dz = -distance-origin[2]
    bounds += _roots(_add(_scale(h, dz*dz), _scale(_multiply((S0[2], S1[2]), (S0[2], S1[2])), -.06**2)))
    planes = []
    for axis in (0, 1):
        for uv in ((.002, .08, .92, .998) if fade_knots else (.002, .998)):
            ndc = 2*uv-1
            normal = tuple(projection[k*4+axis]-ndc*projection[k*4+3] for k in range(3))
            constant = projection[12+axis]-ndc*projection[15]
            planes.append((normal, constant))
    if fade_knots:
        # u=v and u=1-v switch which viewport edge supplies min(distance).
        for sign in (-1, 1):
            planes.append((tuple(projection[k*4]+sign*projection[k*4+1] for k in range(3)),
                           projection[12]+sign*projection[13]))
    for normal, constant in planes:
        no = math.fsum(a*c for a, c in zip(normal, origin))+constant
        nv = math.fsum(a*c for a, c in zip(normal, V))
        ns = tuple(math.fsum(a*c for a, c in zip(normal, S)) for S in (S0, S1))
        nr = _add(*(_scale(ray_polynomials[i], normal[i]) for i in range(3)))
        A = _add(_scale(ray_polynomials[2], no), _scale(nr, dz))
        B = _scale(_add(_scale(ns, -V[2]), _scale((S0[2], S1[2]), nv)), .06)
        # A+B*sqrt(h)=0: squared roots are candidates only. Source/support
        # classification uses the original unsquared intersection below.
        polynomial = _add(_multiply(A, A), _scale(_multiply(_multiply(B, B), h), -1.0))
        bounds += _roots(polynomial)
    for lo, hi in rotated.intervals(context, q, b, x, 1):
        bounds += [lo, hi]
    bounds = sorted(set(bounds))
    spans = []
    for lo, hi in zip(bounds, bounds[1:]):
        if hi-lo < 1e-12:
            continue
        _, first = plane_node(context, matrix, projection, origin, distance, x, (lo+hi)*.5)
        if first['kind'] == 'observed-plane':
            if not fade_knots and spans and spans[-1][1] == lo:
                spans[-1] = (spans[-1][0], hi)
            else:
                spans.append((lo, hi))
    return spans
