"""Build the normal-play shader pack reproducibly from its self-contained sources."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from land_shadow_pack import ArchiveEntry, zip_bytes

ROOT = Path(__file__).resolve().parents[1]


def release_bytes(overlay=None, *additional_overlays):
    trees = [ROOT / "release"]
    for tree in (overlay, *additional_overlays):
        if tree is None:
            continue
        if not (tree / "shaders").is_dir():
            raise FileNotFoundError(tree / "shaders")
        trees.append(tree)
    sources = {"LICENSE": ROOT / "LICENSE"}
    for tree in trees:
        for path in (tree / "shaders").rglob("*"):
            if path.is_file():
                sources[path.relative_to(tree).as_posix()] = path
        # An alternate program can include an earlier overlay's exact source
        # under a second GLSL name, including on checkouts without symlinks.
        aliases = tree / "shader-aliases.json"
        if aliases.is_file():
            for name, path in json.loads(aliases.read_text()).items():
                sources[name] = tree / path
    return zip_bytes(tuple(ArchiveEntry(name, sources[name].read_bytes()) for name in sorted(sources)))


def build(output, overlay=None, *additional_overlays):
    data = release_bytes(overlay, *additional_overlays)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_bytes() == data:
        return
    with NamedTemporaryFile(dir=output.parent, delete=False) as destination:
        temporary = Path(destination.name)
        try:
            os.fchmod(destination.fileno(), 0o644)
            destination.write(data)
            destination.flush()
            os.fsync(destination.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
