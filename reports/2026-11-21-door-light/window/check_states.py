"""Decode the diagnostic screenshot and check it against the installed vanilla atlas/model."""
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
receipt = json.loads((HERE / "state/complete.json").read_text())
runtime = json.loads((HERE.parents[1] / "2026-11-20-underwater-refinement/local-launch.json").read_text())
blocks = (ROOT / "release/shaders/block.properties").read_text()
keys = {(name, half): int(i)-10500 for i, name, half in
        re.findall(r"^block\.(105\d\d)=minecraft:(\w+_door):half=(lower|upper)$", blocks, re.M)}
audit = {}
with zipfile.ZipFile(next(n for n in runtime["cp"] if n.endswith("/minecraft-1.21.1-client.jar"))) as jar:
    for name, state in [("dark", "dark_oak"), ("oak", "oak"), ("open", "oak"), ("empty", None), ("acacia", "acacia")]:
        photo = HERE / "state" / (name + ".png")
        assert hashlib.sha256(photo.read_bytes()).hexdigest() == receipt["images"][name]["sha256"]
        im = Image.open(photo).convert("RGB")
        def bit(x, y):
            rgb = im.getpixel((int((x+.5)*im.width/32), int((y+.5)*im.height/17)))
            assert rgb in ((255,255,255),(0,0,0)), rgb
            return int(rgb[0] != 0)
        halves = {}
        for h, half in enumerate(("lower", "upper")):
            start = 16*h
            word = sum(bit(start+u, 0) << u for u in range(16))
            if state is None:
                assert word == 0
                halves[half] = {"removedCellWord": word}
                continue
            variants = json.loads(jar.read(f"assets/minecraft/blockstates/{state}_door.json"))["variants"]
            is_open = str(name == "open").lower()
            key = f"facing=south,half={half},hinge=left,open={is_open}"
            variant = variants[key]
            shape = {0:6, 90:8, 180:7, 270:9}[variant.get("y",0)]
            assert word & 63 == shape and (word>>6)&63 == keys[(state+"_door",half)]
            model = json.loads(jar.read("assets/minecraft/models/"+variant["model"].split(":")[1]+".json"))
            element = json.loads(jar.read("assets/minecraft/models/"+model["parent"].split(":")[1]+".json"))["elements"][0]
            front = element["faces"]["east"]
            # On the +X face unrotated Minecraft UV increases to the north.
            # Rotating 90/180 degrees reverses world-horizontal depth/width.
            uv_reverse = front["uv"][0] > front["uv"][2]
            expected_flip_u = True ^ uv_reverse ^ (variant.get("y", 0) in (90,180))
            assert (word >> 12)&1 == expected_flip_u and (word>>13)&1 == 1
            texture = model["textures"][front["texture"][1:]].split(":")[-1]
            rgba = Image.open(io.BytesIO(jar.read("assets/minecraft/textures/"+texture+".png"))).convert("RGBA")
            mismatches = sum(bit(start+u, v+1) != (rgba.getpixel((u,v))[3]>=26) for v in range(16) for u in range(16))
            assert mismatches == 0, (name, half, mismatches)
            halves[half] = dict(cellWord=word, orientedPanel=shape, material=keys[(state+"_door",half)], checkedAlphaBits=256, mismatches=mismatches)
        audit[name] = halves
print(json.dumps(dict(renderer=receipt["renderer"], roles=audit), indent=2))
