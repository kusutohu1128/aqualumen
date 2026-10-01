// Compile original pack programs with real GL, without requiring Minecraft.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <cmath>
namespace fs=std::filesystem;
std::string expand(const fs::path& file,const fs::path& root,int level=0) {
    if(level>32) throw std::runtime_error("Include cycle");
    std::ifstream input(file);
    if(!input) throw std::runtime_error("Cannot read "+file.string());
    std::ostringstream output;
    for(std::string line;std::getline(input,line);) {
        if(line.rfind("#include",0)==0) {
            auto begin=line.find('"'),end=line.find('"',begin+1);
            if(begin==std::string::npos||end==std::string::npos) throw std::runtime_error("Malformed include");
            auto name=line.substr(begin+1,end-begin-1);
            output<<expand(root/name.substr(name[0]=='/'?1:0),root,level+1);
        } else {
            output<<line<<'\n';
        }
    }
    return output.str();
}
GLuint compile(GLenum type,const std::string& source,const std::string& name) {
    GLuint shader=glCreateShader(type);
    const char* text=source.c_str();glShaderSource(shader,1,&text,nullptr);glCompileShader(shader);
    GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok) { char log[16384];glGetShaderInfoLog(shader,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log); }
    return shader;
}
GLuint link(const std::string& vs,const std::string& fragment,const std::string& name) {
    GLuint v=compile(GL_VERTEX_SHADER,vs,name+".vsh"),f=compile(GL_FRAGMENT_SHADER,fragment,name+".fsh");
    GLuint program=glCreateProgram();glAttachShader(program,v);glAttachShader(program,f);glLinkProgram(program);
    glDeleteShader(v);glDeleteShader(f);
    GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) { char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log); }
    return program;
}
GLuint compute(const fs::path& file,const fs::path& root) {
    GLuint shader=compile(GL_COMPUTE_SHADER,expand(file,root),file.filename().string());
    GLuint program=glCreateProgram();glAttachShader(program,shader);glLinkProgram(program);glDeleteShader(shader);
    GLint ok;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) {char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(file.string()+": "+log);}
    return program;
}
void rippleProbe(const fs::path& root) {
    GLuint setup=compute(root/"setup.csh",root),first=compute(root/"begin.csh",root),second=compute(root/"begin1.csh",root);
    GLuint images[2];glGenTextures(2,images);
    for(auto texture:images) {glBindTexture(GL_TEXTURE_2D,texture);glTexStorage2D(GL_TEXTURE_2D,1,GL_RG32F,512,512);}
    auto dispatch=[&](GLuint program,float force,float delta,float shiftX,float reset) {
        glUseProgram(program);
        glUniform1i(glGetUniformLocation(program,"rippleImageA"),0);glUniform1i(glGetUniformLocation(program,"rippleImageB"),1);
        glUniform1i(glGetUniformLocation(program,"aqualumenActive"),force!=0?1:0);
        glUniform1f(glGetUniformLocation(program,"aqualumenDelta"),delta);
        glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,0);
        glUniform4f(glGetUniformLocation(program,"aqualumenShift"),shiftX,0,reset,0);
        for(int i=0;i<8;i++) {auto name="aqualumenContact"+std::to_string(i);glUniform4f(glGetUniformLocation(program,name.c_str()),0,0,i==0?force:0,0.65);}
        for(int i=0;i<2;i++) glBindImageTexture(i,images[i],0,GL_FALSE,0,GL_READ_WRITE,GL_RG32F);
        glDispatchCompute(32,32,1);glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT|GL_TEXTURE_FETCH_BARRIER_BIT|GL_SHADER_STORAGE_BARRIER_BIT);
    };
    auto read=[&]() {std::vector<float> data(512*512*2);glBindTexture(GL_TEXTURE_2D,images[0]);glGetTexImage(GL_TEXTURE_2D,0,GL_RG,GL_FLOAT,data.data());return data;};
    auto energy=[&](const std::vector<float>& data) {double sum=0;for(size_t i=0;i<data.size();i+=2) {if(!std::isfinite(data[i])||!std::isfinite(data[i+1])||std::abs(data[i])>=0.5) throw std::runtime_error("Unstable wave-height GPU output");sum+=data[i]*data[i]+data[i+1]*data[i+1]/6.25;}return sum;};
    dispatch(setup,0,0,0,0);
    if(energy(read())!=0) throw std::runtime_error("Ripple setup not zero initialized");
    // Stress max supported dt and source, then prove nonzero response and dissipated energy.
    for(int frame=0;frame<20;frame++) {dispatch(first,8,0.05,0,0);dispatch(second,8,0.05,0,0);}
    auto forced=read();double initial=energy(forced);
    if(initial<0.001) throw std::runtime_error("Ripple contact produced no response");
    dispatch(first,0,0,4,0);dispatch(second,0,0,0,0);
    auto shifted=read();
    for(int y=4;y<508;y++) for(int x=4;x<504;x++) for(int c=0;c<2;c++)
        if(std::abs(shifted[(y*512+x)*2+c]-forced[(y*512+x+4)*2+c])>0.000001) throw std::runtime_error("Ripple recenter does not preserve overlap");
    for(int frame=0;frame<200;frame++) {dispatch(first,0,0.05,0,0);dispatch(second,0,0.05,0,0);}
    double final=energy(read());
    if(final>=initial*0.15) throw std::runtime_error("Ripple damping probe failed");
    dispatch(first,0,0.05,0,1);dispatch(second,0,0.05,0,0);
    if(energy(read())!=0) throw std::runtime_error("Ripple teleport reset failed");
    std::cout<<"PASS GPU wave-height: zero setup, driven response, CFL max-dt stability, integer recenter, damping "<<initial<<" -> "<<final<<", teleport reset\n";
    glDeleteProgram(setup);glDeleteProgram(first);glDeleteProgram(second);glDeleteTextures(2,images);glUseProgram(0);
}
int main(int argc,char** argv) {
    try {
        if(argc<2) throw std::runtime_error("usage: glcheck <shaders> [width height]");
        auto getPlatform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        EGLDisplay display=getPlatform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
            EGLDeviceEXT devices[8];EGLint count=0;
            if(!query || !query(8,devices,&count) || count==0) throw std::runtime_error("No EGL device");
            display=getPlatform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("Cannot initialize EGL device");
        }
        eglBindAPI(EGL_OPENGL_API);
        EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count;eglChooseConfig(display,cfg,&config,1,&count);
        if(!count) throw std::runtime_error("No EGL config");
        int width=argc>2?std::stoi(argv[2]):2560,height=argc>3?std::stoi(argv[3]):1440;
        EGLint surfaceAttrs[]={EGL_WIDTH,width,EGL_HEIGHT,height,EGL_NONE};
        EGLSurface surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("Cannot create GL compatibility context");
        std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\nGL: "<<glGetString(GL_VERSION)<<'\n';
        fs::path root=argv[1];std::vector<fs::path> files;
        for(auto& entry:fs::directory_iterator(root)) if(entry.path().extension()==".vsh") files.push_back(entry.path());
        std::sort(files.begin(),files.end());
        for(auto file:files) {
            auto fragment=file;fragment.replace_extension(".fsh");
            GLuint program=link(expand(file,root),expand(fragment,root),file.stem().string());
            glDeleteProgram(program);std::cout<<"PASS "<<file.stem().string()<<'\n';
        }
        rippleProbe(root);
        GLuint framebuffer,texture;
        glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Probe framebuffer incomplete");
        std::string probe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/water.glsl",root)+
            "void main(){gl_FragColor=vec4(waterFresnel(1.0,1.0,1.333),waterFresnel(0.0,1.0,1.333),waterFresnel(0.5,1.333,1.0),waterTransmission(10.0).r);}";
        GLuint physics=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",probe,"physics-probe");
        glUseProgram(physics);glViewport(0,0,1,1);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        float measured[4];glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        const float expected[4]={0.02037319f,1.0f,1.0f,0.04076220f};
        for(int i=0;i<4;++i) if(!std::isfinite(measured[i]) || std::abs(measured[i]-expected[i])>0.00001f) throw std::runtime_error("Water physics GPU probe failed at channel "+std::to_string(i));
        std::cout<<"PASS GPU physics: normal-incidence Fresnel, grazing reflection, total internal reflection, 10m red extinction\n";
        glDeleteProgram(physics);
        // This solar-column value has an independent high-resolution CPU
        // reference (~0.74646 blue); sixteen quadratic intervals yield ~0.74913.
        // It detects returning to coarse uniform steps that miss near-ground Mie.
        std::string atmosphereProbe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)+
            "void main(){gl_FragColor=vec4(solarTransmission(vec3(0.0,1.0,0.0),2.0),earthAtmosphere()?1.0:0.0);}";
        GLuint atmosphere=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",atmosphereProbe,"atmosphere-probe");
        glUseProgram(atmosphere);glUniform1i(glGetUniformLocation(atmosphere,"aqualumenDimension"),0);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        for(int i=0;i<3;++i) if(!std::isfinite(measured[i]) || measured[i]<=0 || measured[i]>1) throw std::runtime_error("Atmosphere solar transmission GPU output invalid");
        if(std::abs(measured[2]-0.74913f)>0.01f || measured[3]!=1.0f) throw std::runtime_error("Atmosphere near-ground solar column GPU probe failed");
        std::cout<<"PASS GPU atmosphere: near-ground Mie/Rayleigh solar column, zenith blue transmission "<<measured[2]<<" (reference 0.74646)\n";
        glUseProgram(0);glDeleteProgram(atmosphere);glDeleteTextures(1,&texture);glDeleteFramebuffers(1,&framebuffer);
        std::cout<<files.size()<<" program pairs compiled and linked. This is not a Minecraft FPS benchmark.\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        return 0;
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
