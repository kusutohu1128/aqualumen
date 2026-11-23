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
 std::ifstream input("capture-test.comp");std::string src((std::istreambuf_iterator<char>(input)),{});
 auto csrc=src.c_str();GLuint sh=glCreateShader(GL_COMPUTE_SHADER);glShaderSource(sh,1,&csrc,nullptr);glCompileShader(sh);
 GLuint pg=glCreateProgram();glAttachShader(pg,sh);glLinkProgram(pg);GLint ok;glGetProgramiv(pg,GL_LINK_STATUS,&ok);
 if(!ok){char log[16000];glGetShaderInfoLog(sh,sizeof(log),nullptr,log);std::cerr<<log;glGetProgramInfoLog(pg,sizeof(log),nullptr,log);std::cerr<<log;return 4;}
 glUseProgram(pg);GLuint tex;glGenTextures(1,&tex);glBindTexture(GL_TEXTURE_2D,tex);
 std::vector<unsigned> mask(16*120);std::ifstream rows("mask.bin",std::ios::binary);rows.read(reinterpret_cast<char*>(mask.data()),mask.size()*4);if(!rows)return 5;
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glTexStorage2D(GL_TEXTURE_2D,1,GL_R32UI,16,120);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,120,GL_RED_INTEGER,GL_UNSIGNED_INT,mask.data());

 // Use the independently generated default-alpha table as an RGBA atlas,
 // then check that shader-side capture reconstructs every one of its rows.
 std::vector<unsigned> atlas(256);
 for(int y=0;y<16;y++)for(int x=0;x<16;x++)atlas[y*16+x]=(mask[105*16+y]&(1u<<x))?0xffffffffu:0xffffffu;
 std::vector<unsigned> zero(16*120);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,120,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 glBindImageTexture(0,tex,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
 GLuint cells;glGenTextures(1,&cells);glBindTexture(GL_TEXTURE_2D,cells);glTexStorage2D(GL_TEXTURE_2D,1,GL_R32UI,1,1);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 glBindImageTexture(1,cells,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
 GLuint srcTex;glGenTextures(1,&srcTex);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,srcTex);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,16,16);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,16,GL_RGBA,GL_UNSIGNED_BYTE,atlas.data());
 glDispatchCompute(6,1,1);glMemoryBarrier(GL_TEXTURE_UPDATE_BARRIER_BIT);
 glBindTexture(GL_TEXTURE_2D,cells);GLuint word;glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,&word);
 glBindTexture(GL_TEXTURE_2D,tex);glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 bool pass=glGetError()==GL_NO_ERROR && zero==mask && word==(11u|(63u<<9u));
 std::cout<<(pass?"PASS":"FAIL")<<" atlas capture, orientation face bits, untouched door and leaf slots; word="<<word<<"\n";return pass?0:1;
}