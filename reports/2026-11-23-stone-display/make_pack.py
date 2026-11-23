"""Overlay only the final display curve onto the pinned Rows pack, with an optional measurement strip."""
from hashlib import sha256
from pathlib import Path
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-brick-scan"))
from niche_meter import SHIP, snippet

def build(meter):
    output = ROOT / "build/stone-display" / ("Aqualumen-Stone-Meter.zip" if meter else "Aqualumen-Stone-Display.zip")
    output.parent.mkdir(exist_ok=True, parents=True)
    with ZipFile(SHIP) as prev, ZipFile(output, "w") as result:
        for item in prev.infolist():
            payload = prev.read(item)
            if item.filename == "shaders/final.fsh":
                shader = payload.decode()
                begin, end = shader.index("vec3 tone("), shader.index("void main() {")
                shader = shader[:begin] + (HERE / "tone.glsl").read_text() + shader[end:]
                if meter:
                    shader = shader.replace("void main() {", snippet)
                payload = shader.encode()
            result.writestr(item, payload)
    print(output.relative_to(ROOT), sha256(output.read_bytes()).hexdigest())

if __name__ == "__main__":
    build(False)
    build(True)
