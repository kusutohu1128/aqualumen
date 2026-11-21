"""CPU restatement of the leaf light solver contract (INTERFACE.md sections 2, 3.1, 4).

This is not the production code and does not read it; it exists to state the
expected numbers independently so that a GPU probe can compare against them.
usage: python3 -I leaf_reference.py   (prints a table, exits non-zero on a violated invariant)
"""
import itertools
import math

EXT = 1.45
KAPPA = 0.60
REACH = 4
LEAF, SOLID = 2, 1


def transmittance(rho):
    peak = max(rho)
    scale = 1.0 / max(1.0, (1.0 + KAPPA) * peak)
    return tuple(KAPPA * scale * max(c, 0.0) for c in rho)


def hidden(grid, cell):
    for axis in itertools.product((-1, 0, 1), repeat=3):
        if sum(abs(c) for c in axis) != 1:
            continue
        ok = False
        for k in range(1, REACH + 1):
            other = tuple(cell[i] + axis[i] * k for i in range(3))
            shape = grid.get(other, 0)
            if shape == 0:
                continue
            ok = shape in (SOLID, LEAF)
            break
        if not ok:
            return False
    return True


def trace(grid, start, ray, own, length=96.0, steps=64):
    """Beer-Lambert beam fraction through the proxy volume; returns (fraction, top)."""
    cell = [math.floor(c) for c in start]
    t = 0.0
    trans = 1.0
    top = 0.0
    in_leaf = True
    for _ in range(steps):
        nxt = []
        for a in range(3):
            if abs(ray[a]) < 1e-8:
                nxt.append(1e10)
            else:
                wall = cell[a] + (1 if ray[a] > 0 else 0)
                nxt.append((wall - start[a]) / ray[a])
        end = min(length, *nxt)
        shape = grid.get(tuple(cell), 0)
        leaf = shape == LEAF or tuple(cell) == own
        if not leaf and shape == 0 and in_leaf and hidden(grid, tuple(cell)):
            leaf = True
        if end > t:
            if leaf:
                trans *= math.exp(-EXT * (end - t))
            elif shape == SOLID:
                return 0.0, top
        if leaf:
            top = end
        in_leaf = leaf
        if end >= length:
            break
        axis = nxt.index(min(nxt))
        cell[axis] += 1 if ray[axis] > 0 else -1
        t = end
    return trans, top


def check(name, value, expected, tol=1e-6):
    ok = abs(value - expected) <= tol * max(1.0, abs(expected))
    print(f"{'PASS' if ok else 'FAIL'} {name}: {value:.6g} (expected {expected:.6g})")
    return ok


def main():
    results = []
    # Isolated cube, sun straight up, visible face is the underside.
    own = (0, 0, 0)
    grid = {own: LEAF}
    b, _ = trace(grid, (0.5, 0.0 + 0.01 * 1, 0.5), (0, 1, 0), own)
    results.append(check("isolated cube, sun above: exp(-1.45*(1-0.01))", b, math.exp(-EXT * 0.99)))
    b, _ = trace(grid, (0.5, 0.001, 0.5), (0, 1, 0), own)
    results.append(check("same, start 0.001 inside: exp(-1.45*0.999)", b, math.exp(-EXT * 0.999)))
    grid2 = {own: LEAF, (0, 1, 0): LEAF}
    b, _ = trace(grid2, (0.5, 0.001, 0.5), (0, 1, 0), own)
    results.append(check("extra leaf above: exp(-1.45*1.999)", b, math.exp(-EXT * 1.999)))
    grid3 = {own: LEAF, (0, 1, 0): SOLID}
    b, _ = trace(grid3, (0.5, 0.001, 0.5), (0, 1, 0), own)
    results.append(check("stone touching above: 0", b, 0.0))
    # 5x5x5 canopy with only the shell registered: the centre column is closed by the hidden rule.
    shell = {c: LEAF for c in itertools.product(range(5), repeat=3)
             if min(c) == 0 or max(c) == 4}
    b, top = trace(shell, (2.5, 0.001, 2.5), (0, 1, 0), (2, 0, 2))
    results.append(check("5-thick canopy, hidden interior counted: exp(-1.45*4.999)", b, math.exp(-EXT * 4.999), 1e-4))
    results.append(check("5-thick canopy, top of leaf run", top, 5.0, 1e-3))
    # An air cell with open sides is not hidden: a gap under a crown stays air.
    gap = {(0, 0, 0): LEAF, (0, 2, 0): LEAF}
    b, _ = trace(gap, (0.5, 0.001, 0.5), (0, 1, 0), (0, 0, 0))
    results.append(check("1 m air gap between leaves is air: exp(-1.45*(0.999+1))", b, math.exp(-EXT * 1.999)))
    # Energy accounting.
    worst = 0.0
    for rho in itertools.product((0.0, 0.03, 0.2, 0.59, 0.8, 1.0), repeat=3):
        tau = transmittance(rho)
        scale = 1.0 / max(1.0, (1.0 + KAPPA) * max(rho))
        worst = max(worst, max(scale * r + t for r, t in zip(rho, tau)))
        if max(tau) > KAPPA / (1 + KAPPA) + 1e-9:
            results.append(False)
    results.append(check("max(rho'+tau) over the gamut <= 1", min(worst, 1.0), min(worst, 1.0)) and worst <= 1.0 + 1e-9)
    # Hue: tau is proportional to rho unless the pale-petal scale applies.
    tau = transmittance((0.10, 0.26, 0.03))
    results.append(check("green leaf tau/rho constant", tau[1] / 0.26, KAPPA))
    print("tau of (0.10,0.26,0.03):", tuple(round(c, 4) for c in tau))
    # Probe fixtures (leaf-light-probe.h): 0.75 sRGB grey albedo.
    rho = 0.75 ** 2.2
    print("probe grey rho=%.4f tau=%.4f" % (rho, transmittance((rho,) * 3)[0]))
    # Lamp behind a leaf at normal incidence: attenuation of one proxy voxel.
    print("lamp behind one leaf voxel, normal incidence: exp(-1.45) = %.5f" % math.exp(-EXT))
    print("with a second leaf voxel in the path: exp(-2.9) = %.5f" % math.exp(-2 * EXT))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
