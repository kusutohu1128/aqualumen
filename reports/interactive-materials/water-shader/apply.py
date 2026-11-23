from pathlib import Path
root=Path(__file__).resolve().parent/'working/shaders'
def replace(file,a,b):
 p=root/file;s=p.read_text();assert s.count(a)==1,(file,a);p.write_text(s.replace(a,b))
replace('shaders.properties','768 258','768 606')
replace('lib/bounce_capture.glsl','#include "/lib/ground_water.glsl"','#include "/lib/ground_water.glsl"\n#include "/lib/ceiling_grid.glsl"')
replace('lib/bounce_capture.glsl','    if(bounceContains(cell))','''    vec3 grid=lampGridPosition(position,cameraPosition);
    if(imageSize(bounceSurfaceImage).y==ceilingRows && ceilingContains(cell) && normal.y>.99) {
        vec3 f=grid-vec3(cell);
        if(all(lessThan(abs(f.xz-round(f.xz)),vec2(.02))) && abs(f.y-8./9.)<.025) {
            int corner=int(f.x>.5)+2*int(f.z>.5);
            imageAtomicOr(bounceSurfaceImage,ceilingTop(cell),1u<<uint(corner));
        }
    }
    if(bounceContains(cell))''')
replace('lib/terrain.fsh.glsl','void main() {','#ifdef AQUALUMEN_BLOCK_FOLIAGE\n#include "/lib/ceiling_receiver.glsl"\n#endif\nvoid main() {')
replace('lib/terrain.fsh.glsl','    gl_FragData[0]=vec4(color,tex.a);','#ifdef AQUALUMEN_BLOCK_FOLIAGE\n    color+=ceilingSun(worldPosition,normal,albedo);\n#endif\n    gl_FragData[0]=vec4(color,tex.a);')
