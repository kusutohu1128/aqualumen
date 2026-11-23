"""Match measured forest error to the blockers in the GPU's receiver-cell hull."""
from collections import defaultdict
import json

from grid import HERE, captured_grid
from compare import data
from score import (FOREST_ANCHOR, FOREST_SOURCES, face_from_geometry, integral,
                   np, worldgrid)


def blockers(cell, source, shapes, world):
    # Intersect times for which the axis-aligned interpolated receiver and
    # source boxes overlap a voxel. This is independent of the GPU brick scan.
    lo = np.minimum(cell, np.floor(source - .1301).astype(int))
    hi = np.maximum(cell, np.floor(source + .1301).astype(int))
    portion = shapes[tuple(slice(a,b+1) for a,b in zip(lo,hi))]
    coords = np.argwhere(portion != 0) + lo
    solids, others = [], []
    for block in coords:
        a = np.r_[cell + 1.0001 - block, block + 1.0001 - cell]
        b = np.r_[source + .1302 - block, block + 1.1302 - source]
        if np.any((a < 0) & (b < 0)):
            continue
        enter = (a < 0) & (b >= 0)
        exit_ = (a >= 0) & (b < 0)
        first = max(a[enter] / (a[enter]-b[enter]), default=0.)
        last = min(a[exit_] / (a[exit_]-b[exit_]), default=1.)
        if first > last + 1e-5:
            continue
        kind = shapes[tuple(block)]
        xyz = block + FOREST_ANCHOR
        name = world.name(*map(int,xyz))
        entry = dict(xyz=xyz.tolist(), shape=int(kind), block=name)
        (solids if kind==1 else others).append(entry)
    if solids:
        positions = np.array([row["xyz"] for row in solids])
        box = int(np.prod(np.ptp(positions,axis=0)+1)) == len(solids)
    else:
        box = False
    if others:
        label = "foliage" if any(row["shape"] == 2 for row in others) else "otherMaterial"
        label += "AndCuboid" if box else "AndIrregularSolids" if solids else "Only"
    else:
        label = "cuboid" if box else "irregularSolids" if solids else "empty"
    return label, solids, others


def registered_frames():
    _, (base, p, _) = data("gp-density-placed-penumbra-meter")
    _, (trial, q, measured_face) = data("gp-density-placed-hull-meter")
    eye = np.array([208.5,65.62,355.5])
    face = face_from_geometry(p, eye)
    axis = np.stack([(face==2*j+2).astype(float)-(face==2*j+1) for j in range(3)],axis=2)
    cell = np.floor(p+.025*axis).astype(int)-FOREST_ANCHOR
    inside = np.floor(p-.005*axis).astype(int)-FOREST_ANCHOR
    reference_grid = worldgrid()
    safe = tuple(np.moveaxis(np.clip(inside,0,63),-1,0))
    registered = ((face>0) & (face==face_from_geometry(q,eye)) & (reference_grid[safe]==1)
                  & (np.max(abs(p-q),axis=2)<.001) & ((measured_face==0)|(measured_face==face)))
    return base, trial, p, face, axis, cell, reference_grid, registered


def census():
    words, routes = captured_grid()
    shapes = words & 63
    base, trial, p, face, axis, cell, reference_grid, registered = registered_frames()
    from worldread import World
    rows = []
    world = World()
    for lamp,source in enumerate(FOREST_SOURCES):
        a,b = base[:,:,lamp,2],trial[:,:,lamp,2]
        selected = registered & (a>=64) & (b>=64) & ((a&12)==0) & ((b&12)==0)
        ref = integral(p,face,selected,source,FOREST_ANCHOR,reference_grid)
        partial = (ref>.005) & (ref<.995) & ((b%4)==0)
        errors = abs(trial[:,:,lamp,1]/255.-ref)[partial]
        cells, labels = np.unique(cell[partial],axis=0,return_inverse=True)
        counts = np.bincount(labels)
        totals = np.bincount(labels,weights=errors)
        for i,point in enumerate(cells):
            state = int(routes[tuple(point)]>>(2*lamp)) & 3
            label, solid, other = blockers(point,source-FOREST_ANCHOR,shapes,world)
            rows.append(dict(source=lamp,cell=(point+FOREST_ANCHOR).tolist(), route=state,
                             reason=label, samples=int(counts[i]), error=float(totals[i]),
                             solid=solid, other=other))
    assert world.unchanged() and sum(r["samples"] for r in rows)==12144
    totals = defaultdict(lambda: dict(samples=0,error=0.,cellLightPairs=0))
    for row in rows:
        bucket=totals[row["reason"]]
        bucket["samples"]+=row["samples"]
        bucket["error"]+=row["error"]
        bucket["cellLightPairs"]+=1
    return dict(reasons=dict(totals),rows=rows,
                hardwareRoutes={str(k):sum(r["samples"] for r in rows if r["route"]==k) for k in range(4)})


if __name__ == "__main__":
    (HERE/"forest-census.json").write_text(json.dumps(census(),indent=2)+"\n")
