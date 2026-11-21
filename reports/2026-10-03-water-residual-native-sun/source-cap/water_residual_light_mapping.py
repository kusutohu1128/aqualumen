"""CPU-only inverse Snell/slope-measure diagnostic, not a rendering model."""
import argparse
import json
import math


# Fixed BEFORE observations; local double finite-difference policy, not GLSL error.
FD_STEP = 1e-5
FD_ABSOLUTE = 2e-8
FD_RELATIVE = 2e-7
UNIT_TOLERANCE = 1e-12
RECONSTRUCTION_TOLERANCE = 1e-11


def _unit(vector):
    if len(vector) != 3 or any(type(x) not in (float, int) for x in vector):
        raise ValueError("Three finite numeric coordinates required")
    values = tuple(float(x) for x in vector)
    if not all(math.isfinite(x) for x in values):
        raise ValueError("Nonfinite unit vector")
    if abs(sum(x*x for x in values)-1) > UNIT_TOLERANCE:
        raise ValueError("Strict exact-unit CPU fixture policy; no normalization")
    return values


def _index(eta):
    if type(eta) not in (float, int) or not math.isfinite(eta) or eta <= 1:
        raise ValueError("Water-to-air index must exceed one")
    return float(eta)


def forward_snell(v, n, eta=1.333):
    """Qualified water-to-air refract(-v,n,eta), without flips or clamping."""
    v, n, eta = _unit(v), _unit(n), _index(eta)
    facing = sum(a*b for a, b in zip(n, v))
    if v[1] >= 0 or n[1] >= 0 or facing <= 0:
        raise ValueError("Wrong water/facet hemisphere")
    radicand = 1-eta*eta*(1-facing*facing)
    if not math.isfinite(radicand) or radicand <= 0:
        raise ValueError("Critical/TIR branch excluded")
    cost = math.sqrt(radicand)
    ray = tuple(-eta*v[i]+(eta*facing-cost)*n[i] for i in range(3))
    if ray[1] <= 0:
        raise ValueError("Transmitted ray is not in the air hemisphere")
    return ray


def map_light(v, t, eta=1.333):
    """Inverse branch only; exact-unit double fixtures, not GPU-float intake."""
    v, t, eta = _unit(v), _unit(t), _index(eta)
    if v[1] >= 0 or t[1] <= 0:
        raise ValueError("Wrong water/air hemisphere")
    axis = tuple(t[i]+eta*v[i] for i in range(3))
    length_squared = sum(x*x for x in axis)
    if not math.isfinite(length_squared) or length_squared <= 0:
        raise ValueError("Singular inverse Snell axis")
    n = tuple(x/math.sqrt(length_squared) for x in axis)
    if n[1] >= 0 or sum(a*b for a, b in zip(t, n)) >= 0:
        raise ValueError("Wrong orientation/critical inverse branch")
    reconstructed = forward_snell(v, n, eta)
    error = max(abs(a-b) for a, b in zip(t, reconstructed))
    if error > RECONSTRUCTION_TOLERANCE:
        raise ValueError("Inverse does not reconstruct this branch")
    jacobian = abs(sum(a*b for a, b in zip(t, n)))/(length_squared*abs(n[1])**3)
    if not math.isfinite(jacobian) or jacobian <= 0:
        raise ValueError("Singular slope/solid-angle Jacobian")
    return {"normal": n, "slope": (-n[0]/n[1], -n[2]/n[1]),
            "forward_transmitted": reconstructed, "reconstruction_error": error,
            "jacobian_slope_per_solid_angle": jacobian,
            "scope": "CPU exact-unit qualified mapping only; no GLSL or integration proof",
            "GPU_qualified": False, "energy_accepted": False, "shipping_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v", type=float, nargs=3, required=True)
    parser.add_argument("--t", type=float, nargs=3, required=True)
    parser.add_argument("--eta", type=float, default=1.333)
    args = parser.parse_args()
    try:
        result = map_light(args.v, args.t, args.eta)
    except (ValueError, TypeError, OverflowError):
        parser.exit(2, "Rejected unqualified inverse-Snell input\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
