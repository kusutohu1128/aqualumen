"""Compare per-lamp visibility only on the same surface, position and source slot."""
from pathlib import Path
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "2026-11-23-torch-brick-scan"
sys.path.insert(0, str(HERE.parent / "2026-11-23-placed-penumbra"))
from score import check_record, unpack


def compare(label):
    scene, count, stages = {"forest": (2, 4, 5), "grove": (1, 1, 10)}[label]
    rows, examples = {}, []
    paths = sorted((HERE / label).glob("*-ingame.png"))
    assert len(paths) == stages
    for path in paths:
        old = BASE / label / path.name
        for entry in (old, path):
            check_record(entry.parent, entry)
        a, p, na = unpack(old, scene)
        b, q, nb = unpack(path, scene)
        same = ((p == q).all(axis=2) & (na == nb))[:, :, None]
        va, fa = a[:, :, :count, 1], a[:, :, :count, 2]
        vb, fb = b[:, :, :count, 1], b[:, :, :count, 2]
        active = same & (fa >= 64) & (fb >= 64)
        dark = active & ((fb & 16) != 0)
        opened = active & ((fb & 3) == 1) & ((fa & 3) != 1)
        changed = active & (va != vb)
        body = ((fa | fb) & 8) != 0
        obs = dict(receivers=same.size, sameReceivers=same.sum(), compared=active.sum(),
                   partial=(active & (va > 0) & (va < 255)).sum(), changed=changed.sum(),
                   changedOnBodyPaths=(changed & body).sum(), bodyPaths=(active & body).sum(),
                   changedActivity=(same & ((fa >= 64) != (fb >= 64))).sum(),
                   darkCertificates=dark.sum(), darkWasLit=(dark & (va != 0)).sum(),
                   newlyOpen=opened.sum(), newlyOpenWasShaded=(opened & (va != 255)).sum())
        rows[path.stem] = {k: int(v) for k, v in obs.items()}
        for y, x, slot in np.argwhere(changed)[:3]:
            examples.append(dict(stage=path.stem, position=p[y,x].tolist(), slot=int(slot),
                                 before=a[y,x,slot].tolist(), after=b[y,x,slot].tolist()))
    total = {k: sum(row[k] for row in rows.values()) for k in next(iter(rows.values()))}
    out = dict(stages=rows, total=total, examples=examples)
    (HERE / (label + "-comparison.json")).write_text(json.dumps(out, indent=2) + "\n")
    print(label, total)


if __name__ == "__main__":
    compare(sys.argv[1])
