"""Decode the pre-display float readout from Minecraft's original F2 screenshots."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from pack import HERE, package, points

SCENES = ("warm", "off", "soul", "restored")
NAMES = ("firstR", "firstG", "firstB", "secondR", "secondG", "secondB",
         "albedoR", "albedoG", "albedoB", "localY", "hdrR", "hdrG", "hdrB", "exposure")
LUMA = [.2126, .7152, .0722]
TRIALS = HERE.parent / "2026-11-21-animal-light/woodland"


def decode(path):
    with Image.open(path) as shot:
        image = np.asarray(shot.convert("RGB"))
    h, w, _ = image.shape
    values, valid = [], []
    for i in range(32):
        x = int((i + .5) * w / 32)
        cells = []
        for row in range(16):
            y = h - 1 - int((row + .5) / 16 * .21 * h)
            cell = image[y, x]
            assert (image[y-1:y+2, x-1:x+2] == cell).all(), (path, i, row)
            cells.append(bytes(cell))
        assert cells[15] == bytes((74, i, 213)) and cells[0][2] == i, (path, i)
        valid.append(cells[0][:2] == bytes((183, 255)))
        values.append([struct.unpack(">f", c + b'\0')[0] for c in cells[1:15]])
    assert np.isfinite(values).all()
    return values, valid


def read_trial(variant, run):
    folder = TRIALS / run
    receipt = json.loads((folder / "complete.json").read_text())
    _, body = package(variant, True)
    assert receipt["packSha256"] == sha256(body).hexdigest()
    assert all(receipt[k] for k in ("cleanExit", "labFilesUnchanged", "previousSaveUnchanged", "worldZipUnchanged", "modsUnchanged"))
    assert not receipt["benchmarkSentinelPresent"] and not receipt["logErrors"]
    assert "RTX 3080 Ti" in receipt["renderer"] and receipt["results"]["completed"] == ["read-forest-return"]
    assert receipt["revisit"]["sourceRun"] == "oak-night-trail"
    checkpoint = json.loads((TRIALS / "oak-night-trail/save.json").read_text())
    assert checkpoint["time"] == receipt["revisit"]["sourceSavedTime"]
    assert [checkpoint["inventory"][k][0] for k in ("1", "2")] == ["minecraft:torch","minecraft:soul_torch"]
    positions = json.loads((folder / "positions.json").read_text())
    for label, target in (("target-torch", [566,64,419]), ("placed-torch", [566,64,419]), ("empty-socket", [566,63,419])):
        assert sum(p["label"] == label and p["target"] == target for p in positions) >= 2
    views = receipt["results"]["forestViews"]
    assert [v["name"] for v in views] == list(SCENES)
    samples, hashes = {}, {}
    valid = np.ones(32, dtype=bool)
    for scene in SCENES:
        pair = []
        for suffix in ("a", "b"):
            path = folder / f"{scene}-{suffix}-ingame.png"
            sample, ok = decode(path)
            hashes[path.name] = sha256(path.read_bytes()).hexdigest()
            valid &= ok
            pair.append(sample)
        samples[scene] = pair
    meta = dict(folder=run, packSha256=receipt["packSha256"], renderer=receipt["renderer"],
                baseWorldSha256=receipt["worldZipSha256"], saveSha256=checkpoint["sha256"], sha256=hashes, views=views)
    return samples, valid, meta


def channels(samples):
    first = (samples[..., :3] * samples[..., 6:9]) @ LUMA
    second = (samples[..., 3:6] * samples[..., 6:9]) @ LUMA
    return np.stack((first, second, first+second, samples[..., 9], samples[..., 9]-first-second), axis=-1)


def displayed(rgb, exposure):
    linear = np.maximum(rgb * exposure, 0)
    return 255 * (linear / (1 + linear.max(axis=-1, keepdims=True))) ** (1 / 2.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", default="oak-return-stock")
    parser.add_argument("--leaf", default="oak-return-leaf-r2")
    args = parser.parse_args()
    data, metadata, raw = {}, {}, {}
    valid = np.ones(32, dtype=bool)
    for variant, trial in (("stock", args.stock), ("leaf", args.leaf)):
        raw[variant], ok, metadata[variant] = read_trial(variant, trial)
        data[variant] = {k: channels(np.array(v)) for k, v in raw[variant].items()}
        valid &= ok
    assert metadata["stock"]["saveSha256"] == metadata["leaf"]["saveSha256"]
    groups = {}
    for group, block in (("behindLog", np.arange(32)<16), ("besideLog", np.arange(32)>=16)):
        mask = valid & block
        assert mask.sum() >= 8
        def median(values):
            return np.median(values[mask], axis=0).tolist()
        entries = {}
        for v, reads in data.items():
            pairs = {k: p.mean(axis=0) for k, p in reads.items()}
            entries[v] = {k+"MinusOff": median(pairs[k]-pairs["off"]) for k in ("warm","soul","restored")}
            entries[v]["maxRepeatAbs"] = np.max([np.abs(p[0]-p[1])[mask].max(axis=0) for p in reads.values()], axis=0).tolist()
        for k in ("warm","soul","restored"):
            diff = {}
            irradiance = {}
            for v in data:
                diff[v] = (data[v][k] - data[v]["off"]).mean(axis=0)
                lamp = np.array(raw[v][k]).mean(axis=0)
                dark = np.array(raw[v]["off"]).mean(axis=0)
                irradiance[v] = (lamp[:,:3] + lamp[:,3:6]) - (dark[:,:3] + dark[:,3:6])
            entries[k+"DifferenceOfDifferences"] = median(diff["leaf"]-diff["stock"])
            delta = irradiance["leaf"] - irradiance["stock"]
            entries[k+"IrradianceDifferenceRGB"] = median(delta)
            # Apply only the change in return to the same reference HDR pixel at
            # the same exposure. Bloom, AA, temporal adaptation and motion are excluded.
            stock = np.array(raw["stock"][k]).mean(axis=0)
            hdr, exposure = stock[:,10:13], stock[:,13:14]
            display_change = displayed(hdr + stock[:,6:9]*delta, exposure) - displayed(hdr, exposure)
            entries[k+"EstimatedDisplayDifferenceY8"] = float(median(display_change @ LUMA))
        groups[group] = dict(points=int(mask.sum()), measurements=entries)
    out = dict(points=points(), valid=valid.tolist(), fields=NAMES, raw=raw, trials=metadata,
               measures=["firstBounceY","secondBounceY","sumBounceY","allLocalY","residualLocalY"], groups=groups)
    (HERE/"meter-results.json").write_text(json.dumps(out, separators=(",",":"), allow_nan=False)+"\n")
    print(json.dumps(groups, indent=2))


if __name__ == "__main__":
    main()
