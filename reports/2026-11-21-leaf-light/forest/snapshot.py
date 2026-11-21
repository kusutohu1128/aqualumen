"""Copy the exact V2 TEST world (under its exclusive session lock) into a private read-only snapshot for site search."""
import fcntl, gzip, json, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "reports/2026-11-21-indirect-light"))
import capture as base
sys.path.insert(0, str(ROOT / "tools"))
import ground_shadow_lab as g
src = g.GAME.resolve() / "saves" / g.lab.WORLD
g.lab.shared.world_marker()
dst = Path(tempfile.mkdtemp(prefix="aql-leaf-forest-snapshot-")) / g.lab.WORLD
with (src / "session.lock").open("r+b") as h:
    fcntl.lockf(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = base.copy_world(src, dst)
assert base.tree(dst) == manifest
m = g.lab.pairs((dst / "aqualumen-world.properties").read_bytes())
assert m["world_id"] == g.lab.WORLD_ID and m["seed"] == "308060"
assert base.nbt(gzip.decompress((dst / "level.dat").read_bytes()))["Data"]["WorldGenSettings"]["seed"] == 308060
for p in sorted(dst.rglob("*"), reverse=True):
    p.chmod(0o555 if p.is_dir() else 0o444)
(HERE / "snapshot.json").write_text(json.dumps(dict(path=str(dst), sourceDigest=base.digest(manifest), files=len(manifest), world_id=m["world_id"], seed=m["seed"]), indent=2))
print(dst, base.digest(manifest))
