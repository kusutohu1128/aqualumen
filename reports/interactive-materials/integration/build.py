"""Combine independently tested Aqualumen preview features against their common base."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import subprocess, sys, re
here=Path(__file__).resolve().parent
study=here.parent
repo=study.parents[1]
def contents(path):
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        return {n:archive.read(n) for n in archive.namelist() if not n.endswith('/')}
base=contents(repo/'dist/Aqualumen-1.9.0-preview.10.zip')
result=base.copy()
packs=[study/'gold/Aqualumen-1.9.0-gold-facets.zip',study/'copper/Aqualumen-Copper-Grate-Preview.zip']
packs += [Path(p) for p in sys.argv[1:]]
for path in packs:
    variant=contents(path)
    for name,other in variant.items():
        original=base.get(name,b'')
        if other==original: continue
        if path==packs[0] and name in ('shaders/block.properties','shaders/lib/terrain.fsh.glsl'):
            assert other.count(b'10660')==1
            assert b'10901' not in original
            other=other.replace(b'10660',b'10901')
        current=result.get(name,b'')
        if current==original or current==other:
            result[name]=other; continue
        if name=='shaders/block.properties' and all(x.startswith(original) for x in (current,other)):
            result[name]=current+other[len(original):];continue
        if name=='shaders/lib/terrain.fsh.glsl' and b'ceilingSun(worldPosition' in other:
            # Both add linear radiance at the same output. Apply the independent water insertion
            # exactly once, then merge the remaining includes against the original program.
            write=b'    gl_FragData[0]=vec4(color,tex.a);'
            add=b'#ifdef AQUALUMEN_BLOCK_FOLIAGE\n    color+=ceilingSun(worldPosition,normal,albedo);\n#endif\n'
            assert other.count(add+write)==1 and current.count(write)==1
            current=current.replace(write,add+write)
            other=other.replace(add+write,write)
        with TemporaryDirectory() as d:
            paths=[Path(d)/n for n in ('current','original','variant')]
            for f,data in zip(paths,(current,original,other)): f.write_bytes(data)
            proc=subprocess.run(['git','merge-file','-p',*paths],capture_output=True)
            if proc.returncode:raise RuntimeError(f'{path.name}: overlapping edits to {name}')
            result[name]=proc.stdout
ids=re.findall(rb'^block\.(\d+)=',result['shaders/block.properties'],re.M)
assert len(ids)==len(set(ids))
assert b'block.10901=minecraft:gold_ore' in result['shaders/block.properties']
assert b'block.10660=minecraft:copper_grate' in result['shaders/block.properties']
dest=here/'Aqualumen-Interactive-Materials.zip'
with ZipFile(dest,'w',ZIP_DEFLATED) as z:
    for n in sorted(result):z.writestr(n,result[n])
with ZipFile(dest) as z: z.extractall(here/'candidate')
print(dest.name,len(result))
