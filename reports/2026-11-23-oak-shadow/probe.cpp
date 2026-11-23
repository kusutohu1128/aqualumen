// Reuse the pack's capture, publication and actual lamp samplers.
#define main aqualumenFullCheckMain
#include "../../tools/glcheck.cpp"
#undef main

GLuint diskProbe(const fs::path& root, bool candidate, bool carried) {
    std::string fragment="#version 430 compatibility\n";
    fragment += carried ? "#define PROBE_CARRIED true\n" : "#define PROBE_CARRIED false\n";
    for(const char* file: {"lib/settings.glsl","lib/uniforms.glsl","lib/local_lighting.glsl"})
        fragment+=expand(root/file,root);
    fragment+=R"(
uniform sampler2D probeData;
out vec4 result;
void main() {
    int x=int(gl_FragCoord.x);
    vec4 ar=texelFetch(probeData,ivec2(x,0),0);
    vec3 a=ar.xyz,b=texelFetch(probeData,ivec2(x,1),0).xyz;
    vec3 l=normalize(b-a+vec3(0,.025,0));
    LampOccluders o;
    o.entityTest=false;o.entities=entityBounds();o.toRelative=vec3(0);
    o.leafVolume=false;o.leafCell=ivec3(-1);o.work=entityWorkBudget;o.apertures=0;
    float visibility=lampVisibility(a,b,l,ar.w,PROBE_CARRIED,o).g;
    float exact=-2.;
)";
    if(candidate) fragment+=R"(
    vec3 axis=abs(l.y)<.9?vec3(0,1,0):vec3(1,0,0);
    vec3 u=normalize(cross(l,axis))*ar.w;
    exact=simpleSolidVisibility(a,b,l,u,cross(l,u));
)";
    fragment+="result=vec4(visibility,exact,0,1);}";
    return link("#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"solid disk study");
}

int main(int argc,char** argv) try {
    bool carried=argc==5 && std::string(argv[4])=="--carried";
    if(argc!=4 && !carried) throw std::runtime_error("expected baseline shader root, candidate shader root, input table [--carried]");
    auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    EGLDisplay display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
    if(!eglInitialize(display,nullptr,nullptr)) {
        auto devices=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
        EGLDeviceEXT found[8]; EGLint n=0;
        if(!devices || !devices(8,found,&n) || !n) throw std::runtime_error("no EGL device");
        display=platform(EGL_PLATFORM_DEVICE_EXT,found[0],nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("EGL init");
    }
    eglBindAPI(EGL_OPENGL_API);
    EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_NONE};
    EGLConfig config; EGLint count=0;
    if(!eglChooseConfig(display,attrs,&config,1,&count) || !count) throw std::runtime_error("no EGL config");
    EGLint surfaceAttrs[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};
    EGLSurface surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
    EGLint ctxAttrs[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
    EGLContext ctx=eglCreateContext(display,config,EGL_NO_CONTEXT,ctxAttrs);
    if(!eglMakeCurrent(display,surface,surface,ctx)) throw std::runtime_error("EGL context");
    aqualumenDoor::Rig rig;rig.init(argv[2]);
    std::cout<<"renderer "<<rig.renderer<<"\n"<<std::setprecision(9);
    auto stock=diskProbe(argv[1],false,carried),study=diskProbe(argv[2],true,carried);
    std::map<int,std::vector<std::array<float,7>>> scenes;
    std::ifstream input(argv[3]);int id;
    while(input>>id) {
        std::array<float,7> row;
        for(float& x:row) if(!(input>>x)) throw std::runtime_error("truncated input");
        scenes[id].push_back(row);
    }
    if(scenes.empty()) throw std::runtime_error("empty input");
    for(const auto& [sceneId,points]:scenes) {
        aqualumenDoor::Scene scene;
        if(sceneId!=0) scene.cubes.push_back({{32,32,32}});
        if(sceneId==2) scene.cubes.push_back({{33,32,32}});
        if(sceneId==4 || sceneId==5) scene.cubes.push_back({{33,32,33}});
        if(sceneId==5) scene.cubes.push_back({{33,33,33}});
        if(sceneId==6) scene.cubes.push_back({{32,33,32}});
        if(sceneId==3) scene.doors.push_back({{32,32,33},8,0,false,false});
        rig.frame(scene);
        std::vector<float> data;
        for(const auto& p:points) data.insert(data.end(),{p[0],p[1],p[2],p[6]});
        for(const auto& p:points) data.insert(data.end(),{p[3],p[4],p[5],1});
        auto base=rig.evalRows(stock,data,points.size(),2);
        auto out=rig.evalRows(study,data,points.size(),2);
        for(size_t i=0;i<points.size();++i)
            std::cout<<sceneId<<" "<<i<<" "<<base[4*i]<<" "<<out[4*i]<<" "<<out[4*i+1]<<"\n";
    }
    if(!rig.unboundSamplers.empty() || !rig.unbound.empty()) throw std::runtime_error("unbound sampler/image");
    return 0;
} catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
