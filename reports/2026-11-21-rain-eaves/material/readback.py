"""Instrument an immutable ordinary pack. Row zero keeps the ordinary displayed pixel."""
from copy import copy
import sys
from zipfile import ZipFile

def replace(code, token, value):
    assert code.count(token)==1, token
    return code.replace(token,value)

def modify(name, code):
    if name=="shaders/lib/lighting.glsl":
        code=replace(code, "#define AQUALUMEN_LIGHTING\n", "#define AQUALUMEN_LIGHTING\nvec3 measuredLampCoat, measuredSunCoat;\n")
        return replace(code,"localRadiance=albedo*block+film*lampFilm;", "localRadiance=albedo*block+film*lampFilm;\n    measuredLampCoat=film*lampFilm; measuredSunCoat=solarFilm;")
    if name=="shaders/gbuffers_terrain.fsh":
        # Only the actual terrain program writes the additional attachments.
        return replace(code,'#include "/lib/terrain.fsh.glsl"', '#include "/lib/weather_measured_terrain.glsl"')
    if name=="shaders/prepare.fsh":
        return replace(code,"const int colortex0Format", "const int colortex2Format = RGBA16F;\nconst int colortex3Format = RGBA16F;\nconst int colortex0Format")
    if name=="shaders/final.fsh":
        code=replace(code,"void main()", "void renderProduction()")
        return code+"""
uniform int biome_precipitation;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
void main(){
    renderProduction();
    ivec2 p=ivec2(gl_FragCoord.xy);
    vec4 land=texelFetch(colortex2,p,0), lobe=texelFetch(colortex3,p,0);
    int row=p.y%5;
    if(row==1) gl_FragColor=vec4(rainStrength,wetness,float(biome_precipitation==1),1);
    if(row==2) gl_FragColor=vec4(land.xyz,1);
    // Compress positive radiance without an arbitrary 1.0 clipping threshold.
    if(row==3) gl_FragColor=vec4(sqrt(lobe.rgb/(vec3(1)+lobe.rgb)),1);
    if(row==4) gl_FragColor=vec4(land.w,lobe.w,0,1);
}
"""
    return code

def terrain(code):
    code=replace(code,"RENDERTARGETS:0,5,9,14","RENDERTARGETS:0,5,9,14,2,3")
    code=replace(code,"if(film>0.0) color+=film*rainSkyReflection(worldPosition,normal,view,roughness,lightmap.y,colortex6);",
        "vec3 skyCoat=film>0.0 ? film*rainSkyReflection(worldPosition,normal,view,roughness,lightmap.y,colortex6) : vec3(0);\n    color+=skyCoat;")
    end=code.rindex("}")
    return code[:end]+"""
    vec3 lum=vec3(.2126,.7152,.0722);
    gl_FragData[4]=vec4(rainExposure(worldPosition,normal,lightmap.y),film,roughness,lightmap.y);
    gl_FragData[5]=vec4(dot(lum,measuredLampCoat),dot(lum,measuredSunCoat),dot(lum,skyCoat),
                         int(materialId)==10600 ? 1.0 : int(materialId)==10001 ? .5 : 0.0);
"""+code[end:]

if __name__=="__main__":
    with ZipFile(sys.argv[1]) as original, ZipFile(sys.argv[2],"x") as out:
        for entry in original.infolist():
            data=original.read(entry)
            if entry.filename.startswith("shaders/"):
                data=modify(entry.filename,data.decode()).encode()
            out.writestr(copy(entry),data)
        out.writestr("shaders/lib/weather_measured_terrain.glsl",terrain(original.read("shaders/lib/terrain.fsh.glsl").decode()))
