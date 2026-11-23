"""Compare stored Minecraft per-lamp visibility bytes at exactly matching receiver coordinates."""
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "2026-11-23-torch-shadow-integral"
sys.path.insert(0, str(HERE.parent / "2026-11-23-placed-penumbra"))
from score import check_record, unpack

def compare(label):
    before, scene, count = {"forest": ("birch-joint", 2, 4), "grove": ("joint-animal", 1, 1)}[label]
    rows = {}
    for path in sorted((HERE / label).glob("*-ingame.png")):
        old = PREVIOUS / before / path.name
        for entry in (old, path):
            check_record(entry.parent, entry)
        a, p, normal_a = unpack(old, scene)
        b, q, normal_b = unpack(path, scene)
        same = (p == q).all(axis=2) & (normal_a == normal_b)
        aa, bb = a[:, :, :count], b[:, :, :count]
        active_a, active_b = aa[:, :, :, 2] >= 64, bb[:, :, :, 2] >= 64
        compare = same[:, :, None] & active_a & active_b
        values = aa[:, :, :, 1] != bb[:, :, :, 1]
        flags = aa[:, :, :, 2] != bb[:, :, :, 2]
        partial = (aa[:, :, :, 1] > 0) & (aa[:, :, :, 1] < 255)
        rows[path.name] = dict(receiverSamples=int(same.size), sameReceivers=int(same.sum()),
            compared=int(compare.sum()), baselinePartial=int((compare & partial).sum()),
            changedVisibility=int((compare & values).sum()), changedFlags=int((compare & flags).sum()),
            changedActive=int((same[:, :, None] & (active_a != active_b)).sum()))
    assert set(rows) and len(rows) == (5 if label == "forest" else 10)
    data = {"stages": rows, "total": {k: sum(row[k] for row in rows.values()) for k in next(iter(rows.values()))}}
    (HERE / (label + "-comparison.json")).write_text(json.dumps(data, indent=2) + "\n")
    print(label, data["total"])

if __name__ == "__main__":
    compare(sys.argv[1])
