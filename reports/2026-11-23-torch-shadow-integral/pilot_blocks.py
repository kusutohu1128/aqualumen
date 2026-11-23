"""Can the three existing terrain rays identify every cube that hides a torch?"""
import json
import sys

import numpy as np

from sweep_score import HERE, FOREST_ANCHOR, FOREST_SOURCES, check_record, face_from_geometry, integral, unpack, worldgrid


def intersections(start, rays, blocks):
    """Return entry distance along each segment, or infinity for an open ray."""
    entries = np.full((len(blocks), len(rays)), np.inf)
    parallel = abs(rays) < 1e-13
    denominator = np.where(parallel, 1., rays)
    for index, block in enumerate(blocks):
        lower = block - start
        a = lower / denominator
        b = (lower + 1.) / denominator
        near = np.maximum(0., np.where(parallel, -np.inf, np.minimum(a, b)).max(axis=1))
        far = np.minimum(1., np.where(parallel, np.inf, np.maximum(a, b)).min(axis=1))
        hit = (near < far) & ~np.any(parallel & ((lower >= 0.) | (lower + 1. <= 0.)), axis=1)
        entries[index, hit] = near[hit]
    return entries


def visible_using_pilot_hits(point, face, source, grid, taps):
    normal = np.zeros(3)
    normal[(face - 1) // 2] = 1. if face % 2 == 0 else -1.
    start = point + .025 * normal
    delta = source - start
    direction = (source - point) / np.linalg.norm(source - point)
    axis = [0., 1., 0.] if abs(direction[1]) < .9 else [1., 0., 0.]
    u = np.cross(direction, axis)
    u *= .13 / np.linalg.norm(u)
    v = np.cross(direction, u)
    lo = np.floor(np.minimum(start, source - .13)).astype(int) - FOREST_ANCHOR
    hi = np.floor(np.maximum(start, source + .13)).astype(int) - FOREST_ANCHOR
    assert (lo >= 0).all() and (hi < 64).all()
    cells = grid[tuple(slice(a, b + 1) for a, b in zip(lo, hi))]
    blocks = np.argwhere(cells == 1) + FOREST_ANCHOR + lo
    pilots = np.array([[.66, 0.], [-.33, .57156], [-.33, -.57156]])
    hits = intersections(start, delta + pilots[:, :1] * u + pilots[:, 1:] * v, blocks)
    found = np.unique(np.argmin(hits, axis=0)[np.isfinite(hits.min(axis=0))])
    # At segment fraction t the full light spans +/- t*extent on each
    # world axis. Independent axis intervals can include extra cubes.
    extent = np.hypot(u, v)
    first = np.zeros(len(blocks))
    last = np.ones(len(blocks))
    for j in range(3):
        # Both inequalities have the form speed*t >= limit.
        for speed, limit in ((delta[j]+extent[j], blocks[:,j]-start[j]),
                             (extent[j]-delta[j], start[j]-blocks[:,j]-1.)):
            if abs(speed) < 1e-13:
                last[limit > 1e-10] = -1.
            elif speed > 0:
                first = np.maximum(first, (limit-1e-10)/speed)
            else:
                last = np.minimum(last, (limit-1e-10)/speed)
    possible = blocks[first <= last]
    assert len(possible) > 0
    dense = delta + taps[:, :1] * u + taps[:, 1:] * v
    bounded = float(np.isinf(intersections(start, dense, possible)).all(axis=0).mean())
    if len(found) == 0:
        return 1., 0, possible, bounded
    clear = np.isinf(intersections(start, dense, blocks[found])).all(axis=0)
    return float(clear.mean()), len(found), possible, bounded


def main(residuals=False):
    frame = HERE / "birch-two-caps/centre-ingame.png"
    digest = check_record(frame.parent, frame)
    lamp, pos, measured = unpack(frame, 2)
    face = face_from_geometry(pos, np.array([209., 65.62, 355.5]))
    normals = np.stack([(face == 2*j+2).astype(int) - (face == 2*j+1) for j in range(3)], axis=-1)
    cell = np.floor(pos - .005*normals).astype(int) - FOREST_ANCHOR
    grid = worldgrid()
    solid = grid[tuple(np.moveaxis(np.clip(cell, 0, 63), -1, 0))] == 1
    common = solid & (face > 0) & ((measured == 0) | (measured == face))
    rng = np.random.default_rng(117)
    k = np.arange(8192) + .5
    taps = np.sqrt(k[:, None]/8192) * np.stack([np.cos(k*2.399963229728653), np.sin(k*2.399963229728653)], axis=1)
    if residuals:
        records=json.loads((HERE/"cone-sweep.json").read_text())["worstByPoseAndLamp"][:4]
        result=[]
        for record in records:
            samples=[]
            for position in ("oldPosition","position"):
                _,_,candidates,bounded=visible_using_pilot_hits(np.array(record[position]),record["face"],
                                                               FOREST_SOURCES[record["lamp"]],grid,taps)
                samples.append(dict(cubes=candidates.tolist(),visible=bounded))
            assert np.allclose([s["visible"] for s in samples],record["reference"],atol=1./8192)
            result.append(dict(screen=record["screen"],stage=record["stage"],lamp=record["lamp"],samples=samples))
        return result
    rows = []
    totals = []
    for index, source in enumerate(FOREST_SOURCES):
        flags = lamp[:, :, index, 2]
        trace = common & (flags >= 64) & ((flags & 15) == 0)
        ref = integral(pos, face, trace, source, FOREST_ANCHOR, grid)
        coords = np.argwhere((ref > .005) & (ref < .995))
        totals.append(len(coords))
        for y, x in coords[rng.choice(len(coords), size=min(128, len(coords)), replace=False)]:
            estimate, count, candidates, bounded = visible_using_pilot_hits(pos[y,x], int(face[y,x]), source, grid, taps)
            error = estimate - ref[y,x]
            assert error >= -1./8192
            assert abs(bounded - ref[y,x]) <= 1./8192
            rows.append(dict(lamp=index, screen=[int(x)*8, int(y)], pilotBlocks=count, candidateBlocks=len(candidates),
                             boundedError=abs(bounded-float(ref[y,x])),
                             pilotGeometry=estimate, reference=float(ref[y,x]), overestimate=float(error)))
    assert rows
    errors = np.array([r["overestimate"] for r in rows])
    return dict(pack=digest, input=frame.name, eligiblePartialsPerLamp=totals, seed=117,
                samples=len(rows), noPilotHit=sum(r["pilotBlocks"] == 0 for r in rows),
                overTwoPoints=int((errors > .02).sum()), overTenPoints=int((errors > .10).sum()),
                meanOverestimate=float(errors.mean()), maxOverestimate=float(errors.max()),
                candidateCounts={str(n):sum(r["candidateBlocks"]==n for r in rows)
                                 for n in sorted({r["candidateBlocks"] for r in rows})},
                maxBoundedError=max(r["boundedError"] for r in rows),
                worst=sorted(rows, key=lambda r: -r["overestimate"])[:6])


if __name__ == "__main__":
    assert sys.argv[1:] in ([],["--residuals"])
    print(json.dumps(main(bool(sys.argv[1:])), indent=2))
