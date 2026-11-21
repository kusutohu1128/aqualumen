"""Audit the local 1.21.1 models against the door geometry used by the shader."""
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
runtime = json.loads((HERE.parent / "2026-11-20-underwater-refinement/local-launch.json").read_text())
jar = Path(next(lib for lib in runtime["cp"] if lib.endswith("/minecraft-1.21.1-client.jar")))
pack = (ROOT / "release/shaders/block.properties").read_text()
keys = {int(key): (name, half) for key, name, half in
        re.findall(r"^block\.(105\d\d)=minecraft:(\w+_door):half=(upper|lower)$", pack, re.M)}
assert sorted(keys) == list(range(10500, 10540))
states = Counter()
by_shape = Counter()
holes = {}
with zipfile.ZipFile(jar) as z:
    def read(path):
        return json.loads(z.read("assets/minecraft/" + path + ".json"))

    blocks = sorted(Path(k).stem for k in z.namelist() if k.startswith("assets/minecraft/blockstates/") and k.endswith("_door.json"))
    assert set(keys.values()) == {(name, half) for name in blocks for half in ("upper", "lower")}
    for name in blocks:
        variants = read("blockstates/" + name)["variants"]
        assert len(variants) == 32
        for variant, value in variants.items():
            state = dict(pair.split("=") for pair in variant.split(","))
            assert (name, state["half"]) in keys.values()
            model = read("models/" + value["model"].split(":")[1])
            parent = read("models/" + model["parent"].split(":")[1])
            [element] = parent["elements"]
            assert element["from"] == [0, 0, 0] and element["to"] == [3, 16, 16]
            rot = value.get("y", 0)
            assert rot in (0, 90, 180, 270) and not value.get("x") and not value.get("uvlock")
            by_shape[{0:"low X", 90:"low Z", 180:"high X", 270:"high Z"}[rot]] += 1
            inner, outer = [element["faces"][side] for side in ("east", "west")]
            assert "cullface" not in inner and outer.get("cullface") == "west"
            assert not inner.get("rotation") and not outer.get("rotation")
            assert abs(inner["uv"][2] - inner["uv"][0]) == 16 and inner["uv"][1::2] == [0, 16]
            assert [inner["uv"][2], 0, inner["uv"][0], 16] == outer["uv"]
            assert inner["texture"] == outer["texture"]
            texture = model["textures"][inner["texture"].lstrip("#")].split(":")[-1]
            image = Image.open(io.BytesIO(z.read("assets/minecraft/textures/" + texture + ".png"))).convert("RGBA")
            assert image.size == (16, 16)
            holes[(name, state["half"])] = sum(a < 26 for a in image.getchannel("A").tobytes())
            states[name] += 1
print(json.dumps(dict(clientSHA256=hashlib.sha256(jar.read_bytes()).hexdigest(), species=len(blocks),
                      checkedVariants=sum(states.values()), shapeCounts=by_shape,
                      transparentTexels={name: {half: holes[(name, half)] for half in ("lower", "upper")} for name in blocks},
                      scope="installed default 1.21.1 resources; model and alpha audit, no artwork included"), indent=2))
