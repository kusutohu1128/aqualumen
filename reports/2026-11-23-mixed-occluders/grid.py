"""Read the classifier's actual voxel/material field in the existing four-torch scene."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = HERE.parent / "2026-11-23-placed-penumbra"
sys.path.insert(0, str(PRIOR))
from score import DENSITY, FOREST_ANCHOR, check_record
from PIL import Image
import numpy as np

WORK = ROOT / "build/mixed-occluders"
BASE = ROOT / "dist/Aqualumen-Placed-Penumbra-Animal-Study.zip"
GRID_RUN = DENSITY / "gp-density-mixed-grid"


def build():
    assert sha256(BASE.read_bytes()).hexdigest() == "231e3b92831701eea5d7129c65904a63302467b2dc3534a3ffc863c9d6c368ef"
    output = WORK / "Aqualumen-Forest-Grid-Readback.zip"
    WORK.mkdir(parents=True, exist_ok=True)
    with ZipFile(BASE) as src, ZipFile(output, "w") as dst:
        for entry in src.infolist():
            data = src.read(entry)
            if entry.filename == "shaders/final.fsh":
                header, sep, _ = data.partition(b"void main() {")
                assert sep
                data = header + (HERE / "grid.frag").read_bytes()
            dst.writestr(entry, data)
    return sha256(output.read_bytes()).hexdigest()


def captured_grid():
    path = GRID_RUN / "birch-4-ingame.png"
    captured_sha = check_record(GRID_RUN, path)
    assert captured_sha == sha256((WORK / "Aqualumen-Forest-Grid-Readback.zip").read_bytes()).hexdigest()
    with Image.open(path) as im:
        rgb = np.asarray(im.convert("RGB"))[::-1]
    assert np.array_equal(rgb[513,:256], np.repeat(np.arange(256)[:,None],3,axis=1))
    words = rgb.astype(np.int32) @ np.array([1,256,65536])
    assert np.array_equal(words[514,:3] - 32768, FOREST_ANCHOR)
    def plane(start):
        # Driver stores cells in x,z,y order; expose world[x,y,z].
        return words[:512,start:start+512].reshape(64,64,64).transpose(2,0,1)
    return plane(0), plane(512)


if __name__ == "__main__":
    print(build())
