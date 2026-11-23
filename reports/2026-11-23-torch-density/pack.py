from pathlib import Path
import hashlib
import subprocess
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]

BASE=ROOT/"dist/Aqualumen-1.9.0-preview.8.zip"
OUT=ROOT/"build/torch-density"
PACK=OUT/"Aqualumen-Face-Tiles.zip"

if __name__=="__main__":
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()=="2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72"
    subprocess.run([sys.executable, ROOT/"tools/build.py", "--face-preview", "--output", PACK], check=True)
    with ZipFile(BASE) as old, ZipFile(PACK) as new:
        assert set(new.namelist())-set(old.namelist())=={"shaders/lib/bounce_dispatch.glsl"}
        assert not set(old.namelist())-set(new.namelist())
        assert [p for p in old.namelist() if old.read(p)!=new.read(p)]==["shaders/shadowcomp3.csh","shaders/shadowcomp4.csh"]
        old.extractall(OUT/"base")
        new.extractall(OUT/"candidate")
    print(hashlib.sha256(PACK.read_bytes()).hexdigest(),PACK)
