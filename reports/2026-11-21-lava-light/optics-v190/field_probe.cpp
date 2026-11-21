// Run the production horizontal-source classifier on a supplied lamp field.
#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdlib>

std::vector<char> readFile(const char* path) {
    std::ifstream f(path,std::ios::binary);
    if (!f) throw std::runtime_error(path);
    return {std::istreambuf_iterator<char>(f),{}};
}
int main(int argc,char** argv) {
    if(argc!=5) return 2;
    EGLDisplay display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if(!eglInitialize(display,nullptr,nullptr)||!eglBindAPI(EGL_OPENGL_API)) return 3;
    const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
    EGLConfig cfg;EGLint count;
    if(!eglChooseConfig(display,attrs,&cfg,1,&count)||count!=1) return 4;
    const EGLint ver[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_NONE};
    EGLContext ctx=eglCreateContext(display,cfg,EGL_NO_CONTEXT,ver);
    const EGLint one[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
    EGLSurface surf=eglCreatePbufferSurface(display,cfg,one);
    if(!eglMakeCurrent(display,surf,surf,ctx)) return 5;
    std::cerr<<glGetString(GL_RENDERER)<<" | "<<glGetString(GL_VERSION)<<"\n";
    auto shader=readFile(argv[1]),field=readFile(argv[2]),points=readFile(argv[3]);
    if(field.size()!=512*1024*sizeof(float)||points.empty()||points.size()%(12*sizeof(float))) return 6;
    size_t rays=points.size()/(12*sizeof(float));
    std::vector<float> data(rays*2);
    GLuint sh=glCreateShader(GL_COMPUTE_SHADER);
    GLint len=shader.size(); const char* code=shader.data();
    glShaderSource(sh,1,&code,&len); glCompileShader(sh);
    GLuint prog=glCreateProgram();glAttachShader(prog,sh);glLinkProgram(prog);
    GLint ok=0;glGetProgramiv(prog,GL_LINK_STATUS,&ok);
    if(!ok) {char log[4096]{};glGetShaderInfoLog(sh,sizeof(log),nullptr,log);std::cerr<<log;glGetProgramInfoLog(prog,sizeof(log),nullptr,log);std::cerr<<log;return 7;}
    glUseProgram(prog);
    GLuint texture;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_R32F,512,1024);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,1024,GL_RED,GL_FLOAT,field.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glUniform1i(glGetUniformLocation(prog,"aqualumenLightField"),0);
    GLuint buffers[2];glGenBuffers(2,buffers);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[0]);glBufferData(GL_SHADER_STORAGE_BUFFER,points.size(),points.data(),GL_STATIC_DRAW);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,buffers[0]);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[1]);glBufferData(GL_SHADER_STORAGE_BUFFER,data.size()*sizeof(float),nullptr,GL_DYNAMIC_READ);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,1,buffers[1]);
    glDispatchCompute((rays+63)/64,1,1);glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
    glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,data.size()*sizeof(float),data.data());
    std::ofstream out(argv[4],std::ios::binary);
    out.write(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    return glGetError()==GL_NO_ERROR&&out.good()?0:8;
}
