"""Package an isolated render candidate with the same reproducible inputs as the normal release pack."""

import argparse
import hashlib
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "tools"))
from land_shadow_pack import ArchiveEntry, zip_bytes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tree", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    sources = [ArchiveEntry("LICENSE", (root / "LICENSE").read_bytes())]
    sources.extend(
        ArchiveEntry(path.relative_to(a.tree).as_posix(), path.read_bytes())
        for path in (a.tree / "shaders").rglob("*")
        if path.is_file()
    )
    data = zip_bytes(tuple(sorted(sources, key=lambda e: e.name)))
    if a.output.exists():
        if a.output.read_bytes() != data:
            raise ValueError(f"{a.output} already identifies a different candidate")
    else:
        with NamedTemporaryFile(dir=a.output.parent) as f:
            f.write(data)
            f.flush()
            os.link(f.name, a.output)
    print(a.output, hashlib.sha256(data).hexdigest(), len(sources) - 1, "shader files")


if __name__ == "__main__":
    main()
