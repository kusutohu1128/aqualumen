"""Construct a private exposure readout by replacing only the final screen program."""
import hashlib
import io
import argparse
import sys
from pathlib import Path
from zipfile import ZipFile

here = Path(__file__).resolve().parent
root = here.parents[1]
release = root/"dist/Aqualumen-1.9.0-preview.7.zip"
release_sha = "c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"
candidate = root/"build/eye-adaptation/Aqualumen-1.9.0-preview.8.zip"


def candidate_bytes():
    sys.path.insert(0,str(root/"tools"))
    from release_pack import release_bytes
    variants=("lava-preview","canopy-preview","ground-preview","animal-preview","ceiling-preview","eye-preview")
    return release_bytes(*(root/"release"/v for v in variants))


def instrument(pack):
    data = io.BytesIO()
    snippet = (here/"meter.glsl").read_text()+"""
void main() {
    ivec2 tilePixel=ivec2(gl_FragCoord.xy)-ivec2(16,32);
    if(all(greaterThanEqual(tilePixel,ivec2(0))) && all(lessThan(tilePixel,ivec2(128,8)))) {
        gl_FragColor=vec4(meterTile(tilePixel.x/8),1.);
        return;
    }
"""
    with ZipFile(pack) as source, ZipFile(data, "w") as output:
        for item in source.infolist():
            body = source.read(item)
            if item.filename == "shaders/final.fsh":
                assert body.count(b"void main() {") == 1
                body = body.replace(b"void main() {", snippet.encode())
            output.writestr(item, body)
    return data.getvalue()


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate",action="store_true")
    args=ap.parse_args()
    assert hashlib.sha256(release.read_bytes()).hexdigest() == release_sha
    dest = root/"build/eye-adaptation"/("Aqualumen-Window-Meter-8.zip" if args.candidate else "Aqualumen-Window-Meter-7.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if args.candidate:
        candidate.write_bytes(candidate_bytes())
    dest.write_bytes(instrument(candidate if args.candidate else release))
    print(dest, hashlib.sha256(dest.read_bytes()).hexdigest())
