"""Install the tested optional pack alongside the existing Lab packs and record both states."""
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path

from pack import PACK, ROOT

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-22-gpu-profile"))
import run as guarded


def metadata(game):
    result = {}
    for path in game.rglob("*"):
        s = path.lstat()
        result[path.relative_to(game).as_posix()] = (s.st_mode, s.st_size, s.st_mtime_ns)
    return result


def install_zip(src, dst, expected):
    if dst.exists():
        assert guarded.sha(dst) == expected
        return
    with tempfile.NamedTemporaryFile(dir=dst.parent, prefix=".aqualumen-") as temp:
        temp.write(src.read_bytes())
        temp.flush()
        os.fsync(temp.fileno())
        assert guarded.sha(Path(temp.name)) == expected
        os.chmod(temp.name, 0o644)
        os.link(temp.name, dst)


def install():
    name, sha = guarded.FACE_PREVIEW
    assert guarded.sha(PACK) == sha
    dist = ROOT / "dist" / name
    lab = guarded.GAME / "shaderpacks" / name
    output = HERE / "lab.json"
    before = guarded.lab_check()
    if output.exists():
        result = json.loads(output.read_text())
        assert before == result["labAfter"] and guarded.sha(dist) == guarded.sha(lab) == sha
        return
    accepted = json.loads((guarded.RUNS / "gp-p7-a/preflight.json").read_text())["labAfter"]
    assert before == accepted and not lab.exists()
    prior = metadata(guarded.GAME)
    install_zip(PACK, dist, sha)
    install_zip(PACK, lab, sha)
    after = guarded.lab_check()
    current = metadata(guarded.GAME)
    expected_added = lab.relative_to(guarded.GAME).as_posix()
    assert current.keys() - prior.keys() == {expected_added} and prior.keys() <= current.keys()
    assert all(current[key] == value for key, value in prior.items() if key != "shaderpacks")
    assert before["selected"] == after["selected"] == "Aqualumen-1.8.0.zip"
    assert before["activeMods"] == after["activeMods"]
    assert before["fileHashes"] == {key: val for key, val in after["fileHashes"].items() if key != expected_added}
    guarded.save(output, dict(sha256=sha, dist=str(dist), lab=str(lab), labBefore=before, labAfter=after,
                              preexistingEntries=len(prior), newFiles=[expected_added]))
    print(dist, lab)


if __name__ == "__main__":
    with open("/tmp/aql-render21-1000.lock","a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        install()
