#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <vector>
#include <string>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
int main() {
 EGLDisplay d=eglGetDisplay(EGL_DEFAULT_DISPLAY);EGLint x,y;
 if(!eglInitialize(d,&x,&y)||!eglBindAPI(EGL_OPENGL_API))return 2;
 EGLConfig conf;EGLint n,attr[]={EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_NONE};
 eglChooseConfig(d,attr,&conf,1,&n);EGLContext ctx=eglCreateContext(d,conf,EGL_NO_CONTEXT,nullptr);
 if(ctx==EGL_NO_CONTEXT||!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,ctx))return 3;
 std::cout<<glGetString(GL_RENDERER)<<"\n";
 std::ifstream input("probe.comp");std::string src((std::istreambuf_iterator<char>(input)),{});
 auto csrc=src.c_str();GLuint sh=glCreateShader(GL_COMPUTE_SHADER);glShaderSource(sh,1,&csrc,nullptr);glCompileShader(sh);
 GLuint pg=glCreateProgram();glAttachShader(pg,sh);glLinkProgram(pg);GLint ok;glGetProgramiv(pg,GL_LINK_STATUS,&ok);
 if(!ok){char log[16000];glGetShaderInfoLog(sh,sizeof(log),nullptr,log);std::cerr<<log;glGetProgramInfoLog(pg,sizeof(log),nullptr,log);std::cerr<<log;return 4;}
 glUseProgram(pg);GLuint tex;glGenTextures(1,&tex);glBindTexture(GL_TEXTURE_2D,tex);
 std::vector<unsigned> mask(16*120);std::ifstream rows("mask.bin",std::ios::binary);rows.read(reinterpret_cast<char*>(mask.data()),mask.size()*4);if(!rows)return 5;
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glTexStorage2D(GL_TEXTURE_2D,1,GL_R32UI,16,120);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,120,GL_RED_INTEGER,GL_UNSIGNED_INT,mask.data());
 GLuint buf;glGenBuffers(1,&buf);glBindBuffer(GL_SHADER_STORAGE_BUFFER,buf);
 std::vector<unsigned> output(512*512*4);glBufferData(GL_SHADER_STORAGE_BUFFER,output.size()*4,nullptr,GL_DYNAMIC_READ);
 glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,buf);glDispatchCompute(64,64,4);glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,output.size()*4,output.data());
 if(glGetError()!=GL_NO_ERROR)return 6;
 std::ofstream out("projection.bin",std::ios::binary);out.write(reinterpret_cast<char*>(output.data()),output.size()*4);
}
