"""Compare the player's measured shadow at matching camera X on the outward and return walks."""

import json
from pathlib import Path
import numpy as np

here = Path(__file__).resolve().parent
src = json.loads((here.parent/"2026-11-23-wet-oak-motion/components.json").read_text())
assert len(src["registeredIndices"]) == 130
result = {}
for name in ("empty", "slow-empty"):
    a, b = (src["legs"][name+"-"+direction]["series"] for direction in ("east","west"))
    grid = np.linspace(567.54, 568.76, 101)
    curves, max_steps = [], []
    for series in (a,b):
        xs = np.array([p["x"] for p in series])
        assert np.all(np.diff(xs)>0) and xs[0] <= grid[0] < grid[-1] <= xs[-1]
        segment = (xs[1:] > grid[0]) & (xs[:-1] < grid[-1])
        max_steps.append(float(np.diff(xs)[segment].max()))
        curves.append(np.interp(grid, xs, [p["bodyLoss"] for p in series]))
    diff = abs(curves[0] - curves[1])
    span = abs(float(np.mean(curves,axis=0)[0] - np.mean(curves,axis=0)[-1]))
    result[name] = dict(rangeX=[grid[0], grid[-1]], maxInterpolationStep=max_steps,
                        commonSpatialChange=span, directionDifferenceMedian=float(np.median(diff)),
                        directionDifferenceP95=float(np.quantile(diff,.95)), maxDifference=float(diff.max()),
                        medianAsFractionOfSpatialChange=float(np.median(diff)/span))
(here/"walk-direction.json").write_text(json.dumps(result, indent=2)+"\n")
print(result)
