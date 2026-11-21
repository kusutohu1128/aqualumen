"""Decode the signed-off Minecraft F2 field readouts in camera-independent world coordinates."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def decode(path, eye):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint32)
    h = im.shape[0]
    x, row = np.meshgrid(np.arange(16) * 8 + 4, np.arange(8) * 8 + 4)
    pixels = im[h - 1 - row, x]
    values = pixels[:, :, 0] + 256 * pixels[:, :, 1] + 65536 * pixels[:, :, 2]
    assert values[0, 15] == 54321, "raw byte marker failed"
    readout = {
        "pillarShapeWords": values[0, :3].tolist(),
        "poolShapeWords": values[0, 3:12].tolist(),
        "nearbyFluidGroups": int(values[0, 12]),
        "nearbyLamps": int(values[0, 13]),
        "sceneHasLava": int(values[0, 14]),
        "wallDirectRGB": (values[1:4, :6].T / 1e5).tolist(),
        "wallOneBounceRGB": (values[4:7, :6].T / 1e5).tolist(),
        "bounceConfidence": (values[7, :6] / 1e5).tolist(),
    }
    xx, yy = np.meshgrid((np.arange(66) + 35) * 4 + 2, (np.arange(64) + 1) * 4 + 2)
    panel = im[h - 1 - yy, xx]
    raw = panel[:, :, 0] + 256 * panel[:, :, 1] + 65536 * panel[:, :, 2]
    if np.all(raw[:, 65] == 23456):
        origin = np.floor(np.array(eye) / 8).astype(int) * 8 - 32
        def unpack(i, width):
            return np.array([i % width, i // width**2, i // width % width])
        cells = []
        count = readout["nearbyFluidGroups"]
        assert count <= 64
        for k in range(count):
            group = int(raw[k, 64]) - 1
            assert 0 <= group < 4096
            for j in range(64):
                if int(raw[k, j]) & 63 == 10:
                    cells.append((origin + unpack(group, 16) * 4 + unpack(j, 4)).tolist())
        assert len(set(map(tuple, cells))) == len(cells)
        readout["capturedLavaCellsXYZ"] = sorted(cells)
    return readout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session", type=Path)
    p.add_argument("result", type=Path)
    args = p.parse_args()
    record = json.loads((args.session / "complete.json").read_text())
    assert (
        record["complete"]
        and record["shaderpackLogged"]
        and record["originalWorldAndConfigUnchanged"]
    )
    decoded = {}
    eye = json.loads((args.session / "geometry.json").read_text())["eye"]
    for stage, shots in record["screenshots"].items():
        path = args.session / (stage + "-ingame.png")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == shots["ingame"]
        decoded[stage] = decode(path, eye)
    doc = {
        "renderer": record["gl"]["renderer"],
        "diagnosticPack": record["packSha256"],
        "scene": decoded,
        "wallPointsXYAtZ366": [
            [202.5, 174],
            [201.53, 175.5],
            [203.19, 176.05],
            [200.5, 174.2],
            [204, 173.6],
            [203.53, 177.4],
        ],
    }
    with args.result.open("x") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
