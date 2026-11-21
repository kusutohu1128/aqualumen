"""Build a TEST-only matrix of lava material IDs, emitting face heights, render paths and a solid floor control."""
from pathlib import Path
from zipfile import ZipFile
import sys
here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(root/'tools'))
from land_shadow_pack import ArchiveEntry,zip_bytes
from tempfile import TemporaryDirectory
import json, hashlib
tag='Aqualumen-lava-face-test-r3'
target=root/'build'/(tag+'.zip')
with TemporaryDirectory() as tmp:
    td=Path(tmp)
    with ZipFile(root/'dist/Aqualumen-1.8.0.zip') as z:z.extractall(td)
    s=td/'shaders'
    def append(name,text):
        with (s/name).open('a') as f:f.write('\n'+text+'\n')
    append('block.properties','block.10650=minecraft:lava')
    p=s/'lib/shadow_vsh.glsl';st=p.read_text()
    decl="""
// The existing shore atlas is cleared every frame and its normal writer only runs from underwater.
void sampleLavaStudy(vec3 position,vec3 normal) {
    if(isEyeInWater!=0) return;
    vec3 world=position+cameraPosition;
    ivec3 cell=ivec3(floor(world+at_midBlock.xyz/64.0));
    ivec2 column=cell.xz-ivec2(201,360);
    if(cell.y!=172 || any(lessThan(column,ivec2(0))) || any(greaterThan(column,ivec2(2)))) return;
    uint stage=8u;
#ifdef LOCAL_SOLID
    stage=1u;
#elif defined LOCAL_CUTOUT
    stage=2u;
#elif defined LOCAL_GLASS
    stage=4u;
#endif
    if(int(mc_Entity.x)!=10650) {
        if(normal.y>.5) imageAtomicOr(shoreFaceImage,column+ivec2(4,0),stage);
        return;
    }
    imageAtomicOr(shoreFaceImage,column,stage);
    if(normal.y<.5) return;
    int corner=int(world.x>float(cell.x)+.5)+2*int(world.z>float(cell.z)+.5);
    int height=1+int(round(240.0*clamp(world.y-float(cell.y),0.0,1.0)));
    imageAtomicMax(shoreFaceImage,column+ivec2(4*corner,4),uint(height));
}
"""
    st=st.replace('void main() {',decl+'\nvoid main() {').replace('    captureLocalCell(receiverPosition,n,uv);','    sampleLavaStudy(receiverPosition,n);\n    captureLocalCell(receiverPosition,n,uv);')
    p.write_text(st)
    p=s/'final.fsh';st=p.read_text()
    st=st.replace('void main() {', '''uniform usampler2D aqualumenShoreFaces;
void main() {
    ivec2 studyPixel=ivec2(gl_FragCoord.xy);
    if(all(lessThan(studyPixel,ivec2(256,128)))) {
        uint w=texelFetch(aqualumenShoreFaces,studyPixel/16,0).r;
        gl_FragColor=vec4(float(w&255u)/255.0,0.0,1.0,1.0);
        return;
    }''')
    p.write_text(st)
    files=[ArchiveEntry(p.relative_to(td).as_posix(),p.read_bytes()) for p in sorted(td.rglob('*')) if p.is_file()]
    data=zip_bytes(tuple(files))
    if target.exists():assert target.read_bytes()==data
    else:target.write_bytes(data)
print(target,hashlib.sha256(target.read_bytes()).hexdigest())
