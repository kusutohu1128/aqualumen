"""Compare the staging tree with the pinned 1.7.0 pack and check the release constraints.

usage: python3 -I verify_tree.py <repo-root>
Reads dist/Aqualumen-1.7.0.zip (SHA-256 pinned) and build/leaf-solver; writes nothing.
"""
import hashlib
import re
import sys
import zipfile
from pathlib import Path

BASE_SHA = "eb760f429d32ea03b87d500a5f7d613a1d9a611794e3b2ddb6dd297ec80d4ec8"
ALLOWED_CHANGED = {
    "shaders/lib/local_lighting.glsl",
    "shaders/lib/lighting.glsl",
    "shaders/lib/terrain.fsh.glsl",
}
ALLOWED_ADDED = {"shaders/lib/leaf_surface.glsl", "shaders/lib/leaf_light.glsl"}
MUST_BE_IDENTICAL = (
    "shaders/shaders.properties", "shaders/block.properties", "shaders/lib/settings.glsl",
    "shaders/entity.properties", "shaders/item.properties", "LICENSE",
)


def main(root):
    root = Path(root)
    base_path = root / "dist" / "Aqualumen-1.7.0.zip"
    digest = hashlib.sha256(base_path.read_bytes()).hexdigest()
    assert digest == BASE_SHA, f"base pack SHA mismatch: {digest}"
    base = {}
    with zipfile.ZipFile(base_path) as archive:
        for name in archive.namelist():
            base[name] = archive.read(name)
    tree = root / "build" / "leaf-solver"
    current = {p.relative_to(tree).as_posix(): p.read_bytes() for p in tree.rglob("*") if p.is_file()}
    changed = {n for n in current if n in base and current[n] != base[n]}
    added = set(current) - set(base)
    removed = set(base) - set(current)
    print("changed:", sorted(changed))
    print("added:  ", sorted(added))
    print("removed:", sorted(removed))
    ok = True
    if changed - ALLOWED_CHANGED or added - ALLOWED_ADDED or removed:
        print("FAIL: unexpected file delta")
        ok = False
    for name in MUST_BE_IDENTICAL:
        if current.get(name) != base.get(name):
            print("FAIL: must be identical:", name)
            ok = False
    images = re.findall(rb"(?m)^image\.", current["shaders/shaders.properties"])
    print("image.* declarations:", len(images))
    if len(images) != 16:
        print("FAIL: image count")
        ok = False
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
