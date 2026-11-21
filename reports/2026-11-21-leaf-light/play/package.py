"""Deterministic ZIP of the generated world folder: python3 -I package.py <world-dir> <out.zip> (fixed timestamps, level 9)."""
import sys, zipfile
from pathlib import Path

world, out = Path(sys.argv[1]), Path(sys.argv[2])
if out.exists():
    raise SystemExit("refusing to overwrite " + str(out))
with zipfile.ZipFile(out, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(world.rglob("*")):
        if p.is_file():
            zi = zipfile.ZipInfo(world.name + "/" + p.relative_to(world).as_posix(), (2026, 11, 21, 0, 0, 0))
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(zi, p.read_bytes(), zipfile.ZIP_DEFLATED, 9)
print(out)
