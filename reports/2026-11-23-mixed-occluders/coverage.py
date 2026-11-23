"""Count which pair silhouettes actually overlap on the recorded finite emitter."""
import ctypes as ct
import json
import numpy as np

from grid import HERE, WORK


def classify():
    count = json.loads((HERE / "two-box-probe.json").read_text())["realPartialReceivers"]
    rows = np.fromfile(WORK / "pair-input.f32", np.float32).reshape(-1, 7, 4)[:count].copy()
    area = ct.CDLL(str(WORK / "footprint.so")).pairArea
    area.argtypes = [ct.c_int, ct.c_void_p, ct.c_void_p]
    area.restype = None

    def visible(query):
        output = np.empty(len(query), np.float64)
        area(len(query), query.ctypes.data, output.ctypes.data)
        return output

    # If both inputs are the same box, their union is that box.
    a, b = rows.copy(), rows.copy()
    a[:, 2:4] = rows[:, :2]
    b[:, :2] = rows[:, 2:4]
    first, second, both = map(visible, (a, b, rows))
    eps = 1e-6
    partial = (first > eps) & (second > eps) & (first < 1-eps) & (second < 1-eps)
    intersection = 1 + both - first - second
    disjoint = partial & (intersection <= eps)
    contained = partial & ~disjoint & (np.minimum(first,second) - both <= eps)
    return dict(forestPartialReceivers=count, threshold=eps, bothCastPartialShadow=int(partial.sum()),
                disjoint=int(disjoint.sum()), contained=int(contained.sum()),
                partlyOverlapping=int((partial & ~disjoint & ~contained).sum()),
                darkerThanEitherByOnePoint=int((np.minimum(first,second)-both > .01).sum()))


if __name__ == "__main__":
    (HERE / "coverage.json").write_text(json.dumps(classify(), indent=2) + "\n")
