"""Check the reproducible preview against the shader actually photographed and profiled."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from room import HERE, ROOT, STUDY_SHA, PACK

VERSION = ROOT/"dist/Aqualumen-1.9.0-preview.13.zip"
SHA = "18e666ae93ada4daf0a31fb822c23e82dd2240bf581018d11c08a54f476fe385"


def main():
    assert sha256(VERSION.read_bytes()).hexdigest()==SHA and sha256(PACK.read_bytes()).hexdigest()==STUDY_SHA
    with tempfile.TemporaryDirectory() as temp:
        for switch, name in (("--release","Aqualumen-1.8.0.zip"),("--torch-umbra-preview","Aqualumen-1.9.0-preview.12.zip"),
                            ("--visible-terrain-preview",VERSION.name)):
            out=Path(temp)/name
            subprocess.run([sys.executable,str(ROOT/"tools/build.py"),switch,"--output",str(out)],check=True)
            assert out.read_bytes()==(ROOT/"dist"/name).read_bytes()
    with ZipFile(PACK) as played, ZipFile(VERSION) as built, ZipFile(ROOT/"dist/Aqualumen-1.9.0-preview.12.zip") as previous:
        names=built.namelist()
        assert set(names)==set(previous.namelist())==set(played.namelist()) and len(names)==len(set(names))==139
        assert built.testzip() is None and all(built.read(n)==played.read(n) for n in names)
        changed=[n for n in names if built.read(n)!=previous.read(n)]
        assert set(changed)=={p.relative_to(ROOT/"release/visible-terrain").as_posix() for p in (ROOT/"release/visible-terrain/shaders").rglob("*") if p.is_file()}
    (HERE/"release.json").write_text(json.dumps(dict(pack=VERSION.name,sha256=SHA,studySHA=STUDY_SHA,
        equalDecompressedEntries=len(names),changesFromPreview12=changed,previousBuildsByteIdentical=True),indent=2)+"\n")


if __name__=="__main__":
    main()
