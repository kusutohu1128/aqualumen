"""Clone only preview 7's idempotent fourth incident-bank update."""
from copy import copy
from hashlib import sha256
from pathlib import Path
import sys
from zipfile import ZipFile

P7 = "c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"


def generate(source, output):
    assert sha256(source.read_bytes()).hexdigest() == P7
    assert output.resolve() == Path(__file__).resolve().parents[2]/"build/gpu-profiler/Aqualumen-profile-4x.zip"
    temp = output.with_suffix(".tmp")
    program = "shaders/shadowcomp4.csh"
    with ZipFile(source) as original, ZipFile(temp, "w") as clone:
        body = original.read(program)
        assert b"ivec2(0,1536)+patchAddress" in body
        for entry in original.infolist():
            clone.writestr(copy(entry), original.read(entry))
        for n in (5, 6, 7):
            entry = copy(original.getinfo(program))
            entry.filename = program.replace("4", str(n))
            assert entry.filename not in original.namelist()
            clone.writestr(entry, body)
    with ZipFile(source) as original, ZipFile(temp) as clone:
        assert len(clone.namelist()) == len(set(original.namelist())) + 3
        assert all(original.read(k) == clone.read(k) for k in original.namelist())
        assert all(clone.read(program.replace("4", str(n))) == body for n in (5, 6, 7))
    temp.replace(output)
    print(sha256(output.read_bytes()).hexdigest(), output)


if __name__ == "__main__":
    generate(*map(Path, sys.argv[1:]))
