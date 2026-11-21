"""Exact raw-binary32 angular-support oracle. No GL and no shader adoption.

Prescribed branch: eta>1, downward incident view, upward air target,
incident-facing downward facet and forward transmitted ray. Raw view is not
normalized; generated target is a direction, so its squared norm enters the
homogeneous comparisons. Equality/singularity/invalid input stays unknown.
"""
import argparse
from fractions import Fraction
import json
import math
import struct

ETA = 1.3329999446868896


def binary32(value):
    """Round once to binary32, retaining signed zero and nonfinite payload bits."""
    try:
        raw = struct.pack('>f', float(value))
    except OverflowError:
        raw = struct.pack('>f', math.copysign(math.inf, float(value)))
    return struct.unpack('>f', raw)[0], raw.hex()


def classify(view, target, eta=ETA):
    """Return an exact rational certificate, independently of the GLSL interval.

    class0 = strict absence of this physical inverse branch only;
    class1 = strict support; class-1 = boundary/invalid/unknown.
    """
    values = [binary32(value) for value in list(view) + list(target) + [eta]]
    raw = [value for value, _ in values]
    out = dict(schema='aqualumen-exact-water-sun-support-v1',
        viewBits=[bits for _, bits in values[:3]],
        targetBits=[bits for _, bits in values[3:6]], etaBits=values[6][1],
        **{'class': -1}, reason='invalid-domain',
        nativeGLExecuted=False, shippingAccepted=False)
    if len(raw) != 7 or not all(math.isfinite(value) for value in raw):
        return out
    v = list(map(Fraction, raw[:3]))
    t = list(map(Fraction, raw[3:6]))
    e = Fraction(raw[6])
    if e <= 1 or v[1] >= 0 or t[1] <= 0:
        return out
    E = e*e
    V = sum(value*value for value in v)
    U = sum(value*value for value in t)
    B = sum(a*b for a, b in zip(v, t))
    K2 = 1+E*(V-1)
    if V <= 0 or U <= 0 or K2 <= 0:
        return out
    downward = E*v[1]*v[1]*U-K2*t[1]*t[1]
    forward = E*B*B-K2*U
    out['comparisons'] = {key: str(value) for key, value in
        dict(E=E, V=V, U=U, B=B, K2=K2,
             downwardMargin=downward, forwardMargin=forward).items()}
    if downward == 0 or forward == 0 or B == 0:
        out['reason'] = 'boundary'
    elif downward < 0 or B > 0 or forward < 0:
        out['class'] = 0
        out['reason'] = 'strict-branch-absence'
    else:
        out['class'] = 1
        out['reason'] = 'strict-branch-support'
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', nargs=7, type=float, required=True,
        metavar=('VX', 'VY', 'VZ', 'TX', 'TY', 'TZ', 'ETA'))
    args = parser.parse_args()
    print(json.dumps(classify(args.node[:3], args.node[3:6], args.node[6]),
                     sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
