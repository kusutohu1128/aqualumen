"""Stage the leaf-solver pack as an immutable, reproducible ZIP.

usage: python3 -I build_release.py <repo-root> <output.zip>

Entries are LICENSE plus every file under build/leaf-solver/shaders, sorted by name, serialised with
tools/land_shadow_pack.zip_bytes (fixed timestamps, mode 0644), like tools/release_pack.py.
The output is created exclusively (hard link from a private temporary) and made read-only; an
existing file is never replaced. The archive is rebuilt twice in memory and compared first.
"""
import hashlib
import os
import sys
from pathlib import Path


def main(root, output):
    root = Path(root).resolve()
    output = Path(output)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "tools"))
    from land_shadow_pack import ArchiveEntry, zip_bytes

    tree = root / "build" / "leaf-solver"

    def payload():
        entries = [ArchiveEntry("LICENSE", (root / "LICENSE").read_bytes())]
        for path in (tree / "shaders").rglob("*"):
            if path.is_file():
                entries.append(ArchiveEntry(path.relative_to(tree).as_posix(), path.read_bytes()))
        return zip_bytes(tuple(sorted(entries, key=lambda entry: entry.name)))

    data = payload()
    if payload() != data:
        raise SystemExit("archive is not reproducible")
    if output.exists() or output.is_symlink():
        existing = output.read_bytes()
        if existing == data:
            print("already present and identical:", output, hashlib.sha256(existing).hexdigest())
            return 0
        raise SystemExit(f"refusing to replace immutable {output}")
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(output, hashlib.sha256(data).hexdigest(), len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
