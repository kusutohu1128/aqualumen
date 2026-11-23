#define main aqualumenFullCheckMain
#include "../../tools/glcheck.cpp"
#undef main

namespace {
using aqualumenDoor::Atlas;
using aqualumenDoor::Rig;
void openContext() {
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
}
void cube(Rig &rig, int x, int y, int z, int id, int key, const float *tint) {
    const int cell[]={x,y,z}, us[]={0,1,1,0}, vs[]={0,0,1,1};
    const auto offset=rig.gridOffset();
    double mid[]={(Atlas::ox(key)+8.)/Atlas::N,(Atlas::oy(key)+8.)/Atlas::N};
    for(int axis=0;axis<3;axis++) for(int side=0;side<2;side++) {
        double normal[]={0,0,0}; normal[axis]=side?1:-1;
        Rig::V q[4]{};
        for(int k=0;k<4;k++) {
            q[k].p[axis]=side;
            q[k].p[(axis+1)%3]=us[k]; q[k].p[(axis+2)%3]=vs[k];
            q[k].uv[0]=(Atlas::ox(key)+16.*us[k])/Atlas::N;
            q[k].uv[1]=(Atlas::oy(key)+16.*vs[k])/Atlas::N;
        }
        Rig::emitQuad(cell,id,0,q,normal,mid,offset.data(),rig.cam.data(),tint);
    }
}

void capture(Rig &rig, int scene) {
    rig.clearFrame();
    aqualumenDoor::Scene layout;
    if(scene!=3) layout.lamps.push_back({{32,32,32},10100,14});
    if(scene==1 || scene==2) layout.lamps.push_back({{29,33,34},10105,10});
    if(scene==2) layout.doors.push_back({{32,33,32},8,8,false,false});
    rig.capture(layout,false,false);
    const float white[]={1,1,1}, green[]={.38f,.82f,.29f}, gold[]={.9f,.61f,.14f};
    glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D,rig.atlasTex);
    glEnable(GL_RASTERIZER_DISCARD); rig.useShadowState(rig.solid);
    glBegin(GL_QUADS);
    for(int x=29;x<35;x++) for(int z=29;z<35;z++) cube(rig,x,31,z,10001,0,white);
    for(int y=32;y<=35;y++) cube(rig,34,y,32,10001,0,white);
    if(scene==2) cube(rig,29,32,29,10650,0,white);
    glEnd(); glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
    rig.useShadowState(rig.cutout); glBegin(GL_QUADS);
    if(scene!=4) for(int x=30;x<=34;x++) for(int z=30;z<=34;z++)
        cube(rig,x,35+(z&1),z,10300,8,(x&1)?green:gold);
    glEnd(); glMemoryBarrier(GL_ALL_BARRIER_BITS); glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
    rig.publish();
}

std::vector<uint16_t> emit(Rig &rig, GLuint program, float poison) {
    const auto tex=rig.images.at("bounceExitImage");
    const float value[]={poison,poison,poison,poison};
    glClearTexImage(tex.tex,0,GL_RGBA,GL_FLOAT,value);glMemoryBarrier(GL_ALL_BARRIER_BITS);
    glUseProgram(program); glUniform3f(glGetUniformLocation(program,"cameraPosition"),rig.cam[0],rig.cam[1],rig.cam[2]);
    rig.bindSamplers(program);rig.bindImages(program);glDispatchCompute(96,32,1);
    glMemoryBarrier(GL_ALL_BARRIER_BITS);glUseProgram(0);
    std::vector<uint16_t> result(size_t(tex.w)*tex.h*4);
    glGetTextureImage(tex.tex,0,GL_RGBA,GL_HALF_FLOAT,result.size()*sizeof(uint16_t),result.data());
    Rig::checkGL("published exit field");
    return result;
}
}

int main(int argc,char **argv) try {
    if(argc!=3) throw std::runtime_error("expected reference and optimized shader directories");
    openContext(); Rig rig;rig.init(argv[1]);
    const auto reference=compute(fs::path(argv[1])/"shadowcomp2.csh",argv[1]);
    const auto tiled=compute(fs::path(argv[2])/"shadowcomp2.csh",argv[2]);
    std::cout<<"renderer "<<rig.renderer<<std::endl;
    for(int s=0;s<5;s++) {
        capture(rig,s);
        const auto ref=emit(rig,reference,-9.), trial=emit(rig,tiled,-13.);
        const auto surfaces=rig.readUint("bounceSurfaceImage");
        unsigned leaf=0,solid=0,area=0,different=0,worst=0;
        for(size_t i=0;i<ref.size();i++) if(ref[i]!=trial[i]) {
            different++; worst=std::max(worst,unsigned(std::abs(int(ref[i])-int(trial[i]))));
        }
        for(int y=0;y<256;y++) for(int x=0;x<768;x++) {
            const int index=(y*2*1536+x*2)*4;
            const uint32_t material=surfaces[y*768+x];
            const bool positive=ref[index] || ref[index+1] || ref[index+2];
            if(positive && (material>>30)==1) leaf++;
            if(positive && (material>>31)==1) solid++;
            if(ref[index+512*1536*4] && (material>>31)==1) area++;
        }
        std::cout<<"scene "<<s<<" litLeafFaces "<<leaf<<" litSolidFaces "<<solid<<" areaFaces "<<area
                 <<" components "<<ref.size()<<" different "<<different<<" maxHalfUlp "<<worst<<std::endl;
        if((s<3 && (!leaf || !solid)) || (s==3 && (leaf || solid)) || (s==4 && (leaf || !solid))
           || (s==2 && !area) || worst>1) throw std::runtime_error("field agreement or optical control failed");
    }
    if(!rig.unbound.empty() || !rig.unboundSamplers.empty()) throw std::runtime_error("unbound image or sampler");
    return 0;
} catch(const std::exception &e) {std::cerr<<e.what()<<std::endl;return 1;}
