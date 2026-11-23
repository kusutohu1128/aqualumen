"""Exercise the production wet-material and horizontal-triangle code with known planes."""
import json
import os
from zipfile import ZipFile
import numpy as np
os.environ.setdefault("PYOPENGL_PLATFORM","egl")
from OpenGL import EGL as E, GL as G
from OpenGL.GL.shaders import compileProgram,compileShader
from room import HERE
from release import VERSION


def context():
    d=E.eglGetDisplay(E.EGL_DEFAULT_DISPLAY)
    E.eglInitialize(d,None,None)
    E.eglBindAPI(E.EGL_OPENGL_API)
    cfg=(E.EGLConfig*1)()
    count=E.EGLint()
    E.eglChooseConfig(d,[E.EGL_SURFACE_TYPE,E.EGL_PBUFFER_BIT,E.EGL_RENDERABLE_TYPE,E.EGL_OPENGL_BIT,E.EGL_NONE],cfg,1,count)
    ctx=E.eglCreateContext(d,cfg[0],E.EGL_NO_CONTEXT,None)
    E.eglMakeCurrent(d,E.EGL_NO_SURFACE,E.EGL_NO_SURFACE,ctx)
    return d,ctx


def program(path,corrected):
    with ZipFile(path) as pack:
        src=lambda name:pack.read("shaders/lib/"+name+".glsl").decode()
        terrain=src("terrain.fsh")
        slope=terrain[terrain.index("    bool levelTop="):terrain.index("#endif\n    vec4 atlas=")] if corrected else ""
        material=src("rain_surface")
        surface=material[material.index("bool rainSurface("):material.index("vec3 rainSkyReflection(")]
        optics=src("rain_material")+src("dielectric_film")
    vertex="""#version 430
void main(){vec2 q=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(2.*q-1.,0.,1.);}"""
    frag="""#version 430
#define RAIN_SURFACES 1
const float TAU=6.2831853, PI=3.14159265;
uniform float wetness,access,tilt,height;
uniform int biome_precipitation,materialId;
uniform vec3 supplied;
const vec3 cameraPosition=vec3(0.);
vec3 relativeWorld(vec3 p){return p;}
bool earthAtmosphere(){return true;}
float rainExposure(vec3 p,vec3 n,float sky){return access;}
out vec4 result;
"""+optics+surface+"""
void main(){
    vec2 uv=gl_FragCoord.xy*.125;
    vec3 worldPosition=vec3(uv.x,height+tilt*uv.x,uv.y);
    vec3 n=normalize(supplied),albedo=vec3(.38),v;float film,roughness;
"""+slope+"    rainSurface(materialId,worldPosition,n,"+("levelTop," if corrected else "")+"""1.,albedo,v,film,roughness);
    result=vec4(n,film);
}"""
    return compileProgram(compileShader(vertex,G.GL_VERTEX_SHADER),compileShader(frag,G.GL_FRAGMENT_SHADER))


def main():
    display,ctx=context()
    renderer=G.glGetString(G.GL_RENDERER).decode()
    texture=G.glGenTextures(1);G.glBindTexture(G.GL_TEXTURE_2D,texture)
    G.glTexImage2D(G.GL_TEXTURE_2D,0,G.GL_RGBA32F,8,8,0,G.GL_RGBA,G.GL_FLOAT,None)
    fbo=G.glGenFramebuffers(1);G.glBindFramebuffer(G.GL_FRAMEBUFFER,fbo)
    G.glFramebufferTexture2D(G.GL_FRAMEBUFFER,G.GL_COLOR_ATTACHMENT0,G.GL_TEXTURE_2D,texture,0)
    assert G.glCheckFramebufferStatus(G.GL_FRAMEBUFFER)==G.GL_FRAMEBUFFER_COMPLETE
    G.glBindVertexArray(G.glGenVertexArrays(1));G.glViewport(0,0,8,8)
    programs=[program(VERSION,False),program(VERSION.with_name("Aqualumen-Wet-Plane-Study.zip"),True)]
    iris=(0.,126.,-1.)
    # Fixed camera and shelter are inputs. The derivatives, material, film,
    # view direction, normal decision and pixel values execute on OpenGL.
    cases=(("horizontal-wet",iris,0,1,1,1,10601,-2),("sloped-geometry",iris,.05,1,1,1,10601,-2),
           ("tilted-authored-normal",(0,1,-.02),0,1,1,1,10601,-2),("dry",iris,0,0,1,1,10601,-2),
           ("sheltered",iris,0,1,0,1,10601,-2),("unconnected-film",iris,0,.005,1,1,10601,-2),
           ("no-precipitation",iris,0,1,1,0,10601,-2),("uncoated-material",iris,0,1,1,1,0,-2),
           ("from-below",iris,0,1,1,1,10601,2),("already-up",(0,1,0),0,1,1,1,10601,-2))
    rows={}
    for name,normal,slope,wet,access,rain,material,height in cases:
        outputs=[]
        for prog in programs:
            G.glUseProgram(prog)
            loc=lambda key:G.glGetUniformLocation(prog,key)
            for key,val in (("tilt",slope),("wetness",wet),("access",access),("height",height)):
                G.glUniform1f(loc(key),val)
            G.glUniform1i(loc("biome_precipitation"),rain);G.glUniform1i(loc("materialId"),material)
            G.glUniform3f(loc("supplied"),*normal)
            G.glDrawArrays(G.GL_TRIANGLES,0,3)
            outputs.append(np.frombuffer(G.glReadPixels(0,0,8,8,G.GL_RGBA,G.GL_FLOAT),dtype=np.float32).reshape(8,8,4))
        a,b=outputs
        assert np.isfinite(a).all() and np.isfinite(b).all()
        if name=="horizontal-wet":
            assert np.all(a[:,:,2]<-.0079) and np.all(b[:,:,:3]==[0,1,0]) and np.all(b[:,:,3]>0)
        else:
            assert np.array_equal(a,b),name
        rows[name]=dict(previous=a[4,4].tolist(),candidate=b[4,4].tolist(),identical=bool(np.array_equal(a,b)))
    (HERE/"plane-controls.json").write_text(json.dumps(dict(renderer=renderer,rows=rows),indent=2)+"\n")
    print(renderer,len(rows),"controls passed")
    E.eglTerminate(display)


if __name__=="__main__":
    main()
