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
        glUseProgram(0);glDeleteProgram(physics);glDeleteTextures(1,&texture);glDeleteFramebuffers(1,&framebuffer);
        std::cout<<files.size()<<" program pairs compiled and linked. This is not a Minecraft FPS benchmark.\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        return 0;
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
