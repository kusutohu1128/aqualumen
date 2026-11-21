"""Install the survival starter world used for the selected ordinary Minecraft run."""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(root / 'tools'))
import ground_shadow_lab as lab

def install_world(source, folder, world_sha):
    assert folder in ("Aqualumen-Woodland", "Aqualumen-Snow-Village")
    target = root / 'dist' / (folder + '.zip')
    saves = lab.GAME / 'saves'
    dest = saves / folder
    baseline = json.loads((here.parent/'normal-before.json').read_text())
    assert lab.lab.shared.prior.ordinary_tree() == baseline['ordinarySave']
    assert not lab.SENTINEL.exists() and not dest.is_symlink()
    with open('/tmp/aql-install-showcase21-'+str(os.getuid())+'.lock', 'a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not target.exists():
            lab.lab.shared.install_new(source, target, world_sha)
        assert target.is_file() and not target.is_symlink() and lab.lab.sha(target) == world_sha
        with ZipFile(target) as archive:
            assert archive.namelist() == [folder+'/level.dat']
            level = archive.read(archive.namelist()[0])
        with tempfile.TemporaryDirectory(prefix='.aql-woodland-', dir=saves.parent) as scratch:
            staged = Path(scratch) / dest.name
            staged.mkdir()
            (staged/'level.dat').write_bytes(level)
            if not dest.exists():
                # Linux RENAME_NOREPLACE: an existing user directory always wins.
                libc = ctypes.CDLL(None, use_errno=True)
                if libc.renameat2(-100, os.fsencode(staged), -100, os.fsencode(dest), 1):
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err), str(dest))
            assert not dest.is_symlink() and sorted(x.name for x in dest.iterdir()) == ['level.dat']
            assert (dest/'level.dat').read_bytes() == level
        assert lab.lab.shared.prior.ordinary_tree() == baseline['ordinarySave']
    return target, dest


def main():
    proof = json.loads(Path(sys.argv[1]).read_text())
    certificate = json.loads(Path(sys.argv[2]).read_text())
    source = root / 'build/leaf-play' / proof['worldZip']
    assert proof['worldZipUnchanged'] and proof['cleanExit'] and not proof['logErrors']
    assert proof['savedPlayer']['playerGameType'] == proof['savedLevel']['allowCommands'] == 0
    assert proof['walkMetres'] > 0 and 'water' in proof['results']
    assert proof['packSha256'] == lab.lab.sha(root/'dist/Aqualumen-1.8.0.zip')
    assert proof['worldZipSha256'] == lab.lab.sha(source)
    assert certificate['ok'] and Path(certificate['clone']).parent.parent.resolve() == Path(proof['privateGameDir']).resolve()
    assert 'NVIDIA GeForce RTX 3080 Ti' in proof['renderer']
    target, dest = install_world(source,"Aqualumen-Woodland",proof["worldZipSha256"])
    lab.receipt(here/'installation.json', dict(name=dest.name, worldZip=target.name, sha256=proof['worldZipSha256'],
                sourceWorld=proof['worldZip'], installedDirectory=str(dest), ordinarySaveExact=True, files=['level.dat'],
                naturalGenerationOnFirstOpen=True, run=proof['run']))


if __name__=="__main__":
    main()
