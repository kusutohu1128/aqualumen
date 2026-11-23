from pathlib import Path
import zipfile, json
root=Path(__file__).resolve().parent
original=root.parents[2]/'dist/Aqualumen-1.9.0-preview.10.zip'
source=zipfile.ZipFile(original)
files={n:source.read(n) for n in source.namelist()}
def replace(file,anchor,value):
 key='shaders/'+file
 s=files[key].decode()
 assert s.count(anchor)==1,(file,anchor)
 files[key]=s.replace(anchor,value).encode()
def before(file,anchor,code):
 replace(file,anchor,code+anchor)
for f in ('grate_capture.glsl','grate_transmission.glsl'):
 files['shaders/lib/'+f]=(root/f).read_bytes()
names=['copper_grate','exposed_copper_grate','weathered_copper_grate','oxidized_copper_grate']
names+=['waxed_'+n for n in names]
files['shaders/block.properties']+=(''.join(f'\nblock.{10660+i}=minecraft:{s}' for i,s in enumerate(names))+'\n').encode()
replace('shaders.properties','false 16 104','false 16 120')
replace('lib/leaf_mask_capture.glsl','ivec2(16,104)','ivec2(16,120)')
before('lib/local_capture.glsl','#include "/lib/leaf_mask_capture.glsl"','#include "/lib/grate_capture.glsl"\n')
before('lib/local_capture.glsl','    if(id==10650)', '''    if(id>=10660 && id<10668) {
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
        captureGrate(cell,id-10660,normal,atlasUV);
#endif
        return;
    }
''')
before('lib/door_transmission.glsl','bool doorTexelBlocks', '#include "/lib/grate_transmission.glsl"\n')
before('lib/local_lighting.glsl','    if(shape==1) return false;', '    if(shape==11) return !grateFaceSolid(word,crossing-vec3(cell));\n')
before('lib/local_lighting.glsl','            if(shape>=6 && shape<=9)', '''            if(shape==11) {
                apertures|=1;
                if(grateBlocks(word,start+ray*t-vec3(cell),start+ray*end-vec3(cell))) return vec3(0.);
            }
''')
for file,anchor,ret in [('lib/leaf_light.glsl','                if(shape>=6','vec3(0.)'),('lib/trace_diffuse_face.glsl','            if(shape>=6','hit')]:
 spaces=anchor[:len(anchor)-len(anchor.lstrip())]
 before(file,anchor,spaces+f'if(shape==11 && grateBlocks(word,start+ray*t-vec3(cell),start+ray*end-vec3(cell))) return {ret};\n')
before('lib/bounce_capture.glsl','    if((id>=10500','    if(id>=10660 && id<10668) return;\n')
out=root/'Aqualumen-Copper-Grate-Preview.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in files.items():z.writestr(n,v)
with zipfile.ZipFile(out) as z: z.extractall(root/'candidate')
