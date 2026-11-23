"""Compare ordinary rendered colour at identical final exposure, including the first room frame."""
import sys
from room import ROOT,HERE,STUDY,GlassRoom,guarded,ArchiveEntry,zip_bytes,ZipFile
source=STUDY if sys.argv[1]=="combined" else ROOT/'dist/Aqualumen-Glass-View-Pass.zip'
label="exposure-"+sys.argv[1]
assert sys.argv[1] in ("combined","separate") and not (HERE/label).exists()
with ZipFile(source) as archive:entries={k:archive.read(k) for k in archive.namelist()}
k="shaders/final.fsh";old=b"return adapted*EXPOSURE*environment;"
assert entries[k].count(old)==1
entries[k]=entries[k].replace(old,b"return EXPOSURE;")
pack=ROOT/"build/camera-glass"/(source.stem+"-Fixed.zip")
data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(entries.items())))
if pack.exists() and pack.read_bytes()!=data:raise ValueError("Changed fixed exposure pack")
pack.write_bytes(data)
fixed=dict(backend="vgl",size="1280x720",settle="1",stages="none,one",glcache=str(guarded.BUILD/"driver-cache"),
           **{"period-ticks":"200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
guarded.launch(pack,label,"off",fixed,HERE,GlassRoom)
