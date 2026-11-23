"""Check every reported early return with 1,025 independent slab rays, including the emitter rim."""

from collections import defaultdict
import argparse
import json
import numpy as np
from candidate import WORK, HERE


def blocks(scene):
    extra = {2: [(33, 32, 32)], 4: [(33, 32, 33)], 5: [(33, 32, 33), (33, 33, 33)], 6: [(32, 33, 32)]}
    return ([] if scene == 0 else [(32, 32, 32)]) + extra.get(scene, [])


def main(carried=False):
    cases = defaultdict(list)
    for row in (WORK / "inputs.txt").read_text().splitlines():
        scene, *point = row.split()
        cases[int(scene)].append(np.array(point, float))
    seq = np.arange(768)
    angle = seq * np.pi * (3 - np.sqrt(5)) + 0.219
    rad = np.sqrt((seq + 0.5) / 768)
    rim = np.arange(256) * 2 * np.pi / 256
    disk = np.vstack(
        (
            [[0.0, 0.0]],
            np.column_stack((rad * np.cos(angle), rad * np.sin(angle))),
            np.column_stack((np.cos(rim), np.sin(rim))),
        )
    )
    tested = set()
    for tag in ("rtx", "mesa"):
        for line in (WORK / (tag + ("-carried.log" if carried else ".log"))).read_text().splitlines():
            fields = line.split()
            if len(fields) != 5 or not fields[0].isdigit() or float(fields[-1]) != 1:
                continue
            scene, i = map(int, fields[:2])
            key = (scene, i)
            if key in tested:
                continue
            tested.add(key)
            p = cases[scene][i]
            a = p[:3]
            b = p[3:6]
            l = b - a + [0, 0.025, 0]
            l /= np.linalg.norm(l)
            u = np.cross(l, [0, 1, 0] if abs(l[1]) < 0.9 else [1, 0, 0])
            u *= p[6] / np.linalg.norm(u)
            targets = b + disk[:, :1] * u + disk[:, 1:] * np.cross(l, u)
            delta = targets - a
            blocked = np.zeros(len(delta), bool)
            for cell in blocks(scene):
                c = np.array(cell, float)
                moving = np.abs(delta) > 1e-12
                inv = np.divide(1.0, delta, out=np.zeros_like(delta), where=moving)
                t0 = (c - a) * inv
                t1 = (c + 1 - a) * inv
                lo = np.max(np.where(moving, np.minimum(t0, t1), -np.inf), axis=1)
                hi = np.min(np.where(moving, np.maximum(t0, t1), np.inf), axis=1)
                keep = np.all(moving | ((a > c) & (a < c + 1)), axis=1)
                if not carried:
                    keep &= np.any(np.floor(targets) != c, axis=1)
                blocked |= keep & (np.maximum(lo, 0.0) < np.minimum(hi, 1.0))
            assert np.all(blocked), (scene, i, int((~blocked).sum()))
    assert len(tested) > 100
    report = dict(
        earlyReturns=len(tested), raysPerSource=len(disk), rays=len(disk) * len(tested), unblocked=0
    )
    (HERE / ("carried-disk.json" if carried else "opaque-disk.json")).write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--carried", action="store_true")
    main(parser.parse_args().carried)
