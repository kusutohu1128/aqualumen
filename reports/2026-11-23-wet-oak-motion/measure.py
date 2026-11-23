"""Read the actual interpolated eye position, displayed colours and visible grass from the lossless clips."""

import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from probe import HERE, ROOT, POINTS, package

WOOD = HERE.parent / "2026-11-21-animal-light/woodland"
sys.path.insert(0, str(HERE.parent / "2026-11-23-leaf-tiles"))
from storm_results import get_frames
from display_results import WEIGHTS


def words(line, tag):
    assert np.all(line[:, 2] == tag)
    return line[:, 0].astype(np.int32) * 256 + line[:, 1]


def frames(video, components=False):
    values = []
    for frame in get_frames(video):
        # OpenGL's lower-left raster origin is the reverse of the RGB video rows.
        strip = frame[(681 if components else 686) : 702, 850:980][::-1]
        seq = np.arange(130)
        assert np.all(strip[0] == np.stack([np.full(130, 37), seq, np.full(130, 219)], axis=1))
        assert np.all(strip[15] == np.stack([np.full(130, 213), seq, np.full(130, 58)], axis=1))

        def scalar(i, tag, scale=1.0):
            row = words(strip[i], tag)
            assert row.min() == row.max()
            return row[0] / scale

        cx = 560 + scalar(1, 91, 4096.0)
        if abs(cx - 568.0) > 1.0:
            continue
        assert scalar(13, 103) == 18000
        assert np.all(strip[3, :, 2] == 93)
        vis = strip[3, :, 0] == 255
        px, py = words(strip[9], 99), words(strip[10], 100)
        overlay = (px >= 850) & (px < 980) & (py >= (681 if components else 686)) & (py < 702)
        delta = np.abs(frame[py, px].astype(int) - strip[4].astype(int)).max(axis=1)
        npixel = int((vis & ~overlay).sum())
        terms = {}
        if components:
            assert np.all(strip[20, :, 2] == 138) and np.all(strip[20, :, 1] == seq)
            vis &= strip[20, :, 0] == 255
            for k, key in enumerate(("direct", "bounce", "film", "withoutBody"), 16):
                terms[key] = np.expm1(np.log(2) * words(strip[k], 110 + k) / 2048) / 65536
            terms["bodyLoss"] = terms["withoutBody"] - (terms["direct"] + terms["bounce"] + terms["film"])
        values.append(
            dict(
                **terms,
                x=cx,
                z=415 + scalar(8, 98, 4096.0),
                eyeY=60 + scalar(14, 104, 4096.0),
                exposure=scalar(2, 92, 2048.0),
                wetness=scalar(12, 102, 32768.0),
                vis=vis,
                auto=strip[4] @ WEIGHTS,
                fixed=strip[5] @ WEIGHTS,
                scene=np.expm1(np.log(2) * words(strip[6], 96) / 2048) / 65536,
                lamp=np.expm1(np.log(2) * words(strip[7], 97) / 2048) / 65536,
                material=strip[11] @ WEIGHTS,
                screenChecks=npixel,
                screenEqual=int(np.count_nonzero((delta <= 1) & vis & ~overlay)),
            )
        )
    assert values, video
    return values


def summarize(all_rows, components=False):
    names = ("auto", "fixed", "scene", "lamp", "material")
    if components:
        names += ("direct", "bounce", "film", "withoutBody", "bodyLoss")
    common = np.logical_and.reduce([r["vis"] for rows in all_rows.values() for r in rows])
    assert common.sum() > 45, common.sum()
    result = {}
    for label, rows in all_rows.items():
        samples = []
        for x in sorted({r["x"] for r in rows}):
            same = [r for r in rows if r["x"] == x]
            row = {
                k: float(np.median([r[k] for r in same])) for k in ("x", "z", "eyeY", "exposure", "wetness")
            }
            for k in names:
                row[k] = float(np.median(np.median([r[k][common] for r in same], axis=0)))
            samples.append(row)
        left = [p for p in samples if p["x"] < 568]
        right = [p for p in samples if p["x"] >= 568]
        assert len(left) >= 2 and len(right) >= 2, (label, samples)
        l, r = left[-1], right[0]
        pct = sum(s["screenEqual"] for s in rows) / sum(s["screenChecks"] for s in rows)
        assert pct > 0.95, (label, pct)
        errors = {}
        if components:
            # The red attachment is independent of the four diagnostic values.
            residual = np.concatenate(
                [
                    np.abs(r["direct"] + r["film"] + r["bounce"] - r["lamp"])[common]
                    / np.maximum(r["lamp"][common], 1e-5)
                    for r in rows
                ]
            )
            errors = dict(sumVsGbufferP99RelativeError=float(np.quantile(residual, 0.99)))
            assert errors["sumVsGbufferP99RelativeError"] < 0.02, (label, errors)
            # Compare each visible world texel to itself at the ends of the walk.
            xs = [min(samples, key=lambda p: abs(p["x"] - target))["x"] for target in (567.54, 568.76)]
            assert all(abs(x - target) < 0.11 for x, target in zip(xs, (567.54, 568.76)))
            endpoints = [[r for r in rows if r["x"] == x] for x in xs]
            changes = {}
            for term in ("lamp", "direct", "bounce", "film", "withoutBody"):
                low, high = [np.median([r[term][common] for r in end], axis=0) for end in endpoints]
                delta = high - low
                changes[term] = {
                    "mean": float(np.mean(delta)),
                    "median": float(np.median(delta)),
                    "p05": float(np.quantile(delta, 0.05)),
                    "p95": float(np.quantile(delta, 0.95)),
                }
            errors["pairedWalk"] = dict(
                xLow=xs[0], xHigh=xs[1], points=int(common.sum()), increasingX=changes,
                directSelfShadowShare=1.0 - changes["withoutBody"]["mean"] / changes["lamp"]["mean"],
            )
        result[label] = dict(
            **errors,
            framesInRange=len(rows),
            uniqueX=len(samples),
            screenMatchWithin1=pct,
            before=l,
            after=r,
            stepIncreasingX={k: r[k] - l[k] for k in (*names, "exposure", "x")},
            series=samples,
        )
    return dict(registeredIndices=np.nonzero(common)[0].tolist(), legs=result)


def main():
    import hashlib

    folder = WOOD / sys.argv[1]
    rec = json.loads((folder / "complete.json").read_text())
    components = "--components" in sys.argv[2:]
    path, data = package(components)
    assert rec["packSha256"] == hashlib.sha256(data).hexdigest() and path.read_bytes() == data
    assert all(
        rec[k]
        for k in (
            "cleanExit",
            "previousSaveUnchanged",
            "worldZipUnchanged",
            "modsUnchanged",
            "labFilesUnchanged",
        )
    )
    assert not rec["benchmarkSentinelPresent"] and not rec["logErrors"]
    assert rec["savedLevel"]["raining"] and rec["savedLevel"]["DayTime"] == 66000
    assert rec["results"]["completed"] == ["wet-oak-out-and-back"] and not rec["results"].get("failed")
    legs = rec["results"]["wetPassages"]
    assert len(legs) == 6
    result = summarize({leg["label"]: frames(folder / leg["video"], components) for leg in legs}, components)
    result.update(
        packSHA=rec["packSha256"],
        renderer=rec["renderer"],
        receipt=str(folder.relative_to(ROOT) / "complete.json"),
        fixedExposure=11.25,
    )
    (HERE / ("components.json" if components else "motion.json")).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("common", len(result["registeredIndices"]))
    for name, leg in result["legs"].items():
        print(name, leg["before"], leg["after"], "ratio", leg["screenMatchWithin1"])


if __name__ == "__main__":
    main()
