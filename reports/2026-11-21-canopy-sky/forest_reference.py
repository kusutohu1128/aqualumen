"""Independent cosine-weighted 12 m upper-sky reference from the saved forest."""
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-21-leaf-light/forest"))
from sitesearch import AIR, DIRT, GRASS, LEAVES, LOG, PLANT, SNAP, SOLID, WATER, Scene


def visibility(scene, point, direction):
    # Chord lengths through foliage use extinction 1.45/m. This reference
    # integrates a homogeneous leaf volume; the GPU additionally resolves its
    # two cutout sheets. The leafless/black-leaf brackets do not assume that fit.
    origin = [p + .0001*d for p, d in zip(point, direction)]
    cell = [math.floor(p) for p in origin]
    steps = [1 if d > 0 else -1 for d in direction]
    boundary = [(c + int(s > 0) - p)/d for c,s,p,d in zip(cell,steps,origin,direction)]
    strides = [1/abs(d) for d in direction]
    start = leaves = 0.
    while start < 12.:
        end = min(12., min(boundary))
        kind = scene.cat(tuple(cell))
        if kind in (GRASS, DIRT, SOLID, LOG):
            return (0., 0., 0.)
        if kind == LEAVES:
            leaves += end-start
        elif kind not in (AIR, WATER, PLANT):
            raise RuntimeError((tuple(cell),kind))
        for axis, b in enumerate(boundary):
            if b <= end + 1e-9:
                cell[axis] += steps[axis]
                boundary[axis] += strides[axis]
        start = end
    return (float(leaves < 1e-6), math.exp(-1.45*leaves), 1.)


def sphere(bands, angles):
    for j in range(bands):
        y = (j+.5)/bands
        r = math.sqrt(1-y*y)
        for i in range(angles):
            t = math.tau*(i+.19+(j*.61803399)%1)/angles
            yield (math.cos(t)*r, y, math.sin(t)*r)


def irradiance(scene, point, normal, bands, angles):
    energy = [0.,0.,0.]
    total = 0.
    for d in sphere(bands, angles):
        w = sum(a*b for a,b in zip(normal,d))
        if w <= 0: continue
        total += w
        for i,v in enumerate(visibility(scene,point,d)):
            energy[i] += w*v
    return [round(e/total,5) for e in energy]


def main():
    scene = Scene((207,359,210,361))
    positions = {
        "birch": ((209.5,65.5,360.), (0,0,-1)),
        "torchGrass": ((207.5,64.,359.5), (0,1,0)),
        "rootGrass": ((209.5,64.,359.5), (0,1,0)),
    }
    result = {"world": SNAP["sourceDigest"], "seed": SNAP["seed"], "reach": 12,
              "components": ["opaqueLeaves","volumeLeaves","noLeaves"],
              "scope": "Upper-hemisphere visibility for uniform sky. Saved full blocks and logs block rays, crossed plants and water are open. Geometry model, not measured game color.",
              "samples": {}}
    for label,(p,n) in positions.items():
        axes = [axis for axis,value in enumerate(n) if not value]
        corners = []
        for i in range(4):
            q = list(p)
            for bit,a in enumerate(axes):
                q[a] = math.floor(q[a])+((i>>bit)&1)
            corners.append(irradiance(scene,q,n,4,8))
        result["samples"][label] = {
            "position":p,"normal":n,
            "denseAtFaceCenter":irradiance(scene,p,n,64,128),
            "coarseAtFaceCenter":irradiance(scene,p,n,4,8),
            "meanOfFourCoarseFaceVertices":[round(sum(row[i] for row in corners)/4,5) for i in range(3)],
            "coarseVertices":corners,
        }
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
