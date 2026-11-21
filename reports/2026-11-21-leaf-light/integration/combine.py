"""Build an immutable candidate from the accepted atlas-cast study and the first leaf solver."""
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/'tools'))
from land_shadow_pack import ArchiveEntry,zip_bytes
source=root/'build/Aqualumen-1.8.0-leaf-rc1.zip'
cast=root/'build/Aqualumen-leaf-cast-study-r1.zip'
assert hashlib.sha256(cast.read_bytes()).hexdigest()=='9762bb4d5e5ad6e4e577a3cc333a34a003414d375db06e8ceed1ee853196b60d'
base=root/'dist/Aqualumen-1.7.0.zip'
with ZipFile(source) as z,ZipFile(cast) as q,ZipFile(base) as old:
    files={p:z.read(p) for p in z.namelist()}
    for path in ('shaders/lib/local_capture.glsl','shaders/shaders.properties'):
        assert files[path]==old.read(path)
        files[path]=q.read(path)
    for path in ('shaders/lib/leaf_mask_capture.glsl','shaders/lib/leaf_mask_transmission.glsl'):
        assert path not in files
        files[path]=q.read(path)
p='shaders/lib/local_lighting.glsl';s=files[p].decode()
def replace_once(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)
s=replace_once(s,'#include "/lib/door_transmission.glsl"','#include "/lib/door_transmission.glsl"\n#include "/lib/leaf_mask_transmission.glsl"')
s=replace_once(s,'if(shape==2) trans*=exp(-LEAF_EXTINCTION*(end-t));','''if(shape==2) {
                // The visible leaf already supplies its own tint and coverage. Other
                // volumes cast the pattern of their recorded atlas sprite on the receiver.
                if(leafVolume && all(equal(cell,leafCell))) trans*=exp(-LEAF_EXTINCTION*(end-t));
                else {
                    vec3 origin=start-vec3(cell);
                    trans*=foliageSegment(word,origin+ray*t,origin+ray*end,end-t,t>0.0,end<dist);
                }
            }''')
files[p]=s.encode()
p='shaders/lib/leaf_light.glsl';s=files[p].decode()
a=s.index('// Leaf optics:')
b=s.index('const float LEAF_TRANSMISSION_RATIO=',a)
s=s[:a]+'''// Two-sided diffuse leaf optics. Atlas albedo includes the actual biome tint.
// The transmission ratio and canopy extinction are fitted artistic parameters.
// Habel, Kusternig & Wimmer (2007); Jacquemoud & Baret (1990).
'''+s[b:]
a=s.index('    vec3 rho=');b=s.index('\n}',a)
s=s[:a]+'''    vec3 rho=clamp(albedo,0.0,1.0);
    float peak=max(rho.r,max(rho.g,rho.b));
    // The front keeps rho. Allocate only energy it did not reflect to the back.
    return rho*min(LEAF_TRANSMISSION_RATIO,(1.0-peak)/max(peak,1e-6));'''+s[b:]
s=s.replace('// beyond the shadow distance the point is treated as lit, like shadowVisibility.','// beyond the shadow distance there is no confirmed path for direct transmission.')
a=s.index('float leafShadowTap(');b=s.index('// Near field:',a)
entry=s[a:b].replace('return 1.0;','return 0.0;').replace('coord.z-0.00015','coord.z-0.000002').replace('mix(visible*0.25,1.0,edge)','visible*0.25*(1.0-edge)')
s=s[:a]+entry+s[b:]
a=s.index('    if(max(trans.r',s.index('vec3 leafSolarNear'));b=s.index('vec3 leafSolarBeam(',a)
s=s[:a]+'''    if(max(trans.r,max(trans.g,trans.b))<=0.0 || tail) return vec3(0.0);
    return trans*leafShadowTap(start+lightDir*(top+0.035)-shift);
}
// Outside exact geometry a depth map can establish an open path immediately
// beyond this leaf. Stepping across an unidentified blocker can relight a roof.
vec3 leafSolarFar(LeafSurface leaf,vec3 start,vec3 shift,vec3 lightDir) {
    float own=leafOwnChord(start,lightDir,leaf.cell);
    float visible=leafShadowTap(start+lightDir*(own+0.035)-shift);
    return vec3(exp(-LEAF_EXTINCTION*own)*visible);
}
'''+s[b:]
files[p]=s.encode()
out=root/'build/Aqualumen-1.8.0-leaf-rc2.zip'
with out.open('xb') as stream:stream.write(zip_bytes([ArchiveEntry(k,v) for k,v in sorted(files.items())]))
sandbox=root/'build/leaf-merged-r2'
sandbox.mkdir()
with ZipFile(out) as z:z.extractall(sandbox)
with (here/'rc2.json').open('x') as f:json.dump(dict(pack=out.name,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),base=hashlib.sha256(source.read_bytes()).hexdigest(),cast=hashlib.sha256(cast.read_bytes()).hexdigest()),f,indent=2)
