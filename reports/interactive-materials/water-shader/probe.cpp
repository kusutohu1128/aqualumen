#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <cmath>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
std::string expand(const fs::path& p) {
 std::ifstream f(p); if(!f) throw std::runtime_error(p.string());
 std::string s,line;
 while(std::getline(f,line)){
  if(line.starts_with("#include \"/")) {auto end=line.rfind('"'); s+=expand(fs::path("working/shaders")/line.substr(11,end-11));}
  else s+=line+"\n";
 }
 return s;
}
GLuint compile(){
 auto source=expand("working/shaders/shadowcomp5.csh");
 const char* code=source.c_str(); GLuint s=glCreateShader(GL_COMPUTE_SHADER);glShaderSource(s,1,&code,nullptr);glCompileShader(s);GLuint p=glCreateProgram();glAttachShader(p,s);glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);
 if(!ok){char log[4096];glGetShaderInfoLog(s,sizeof(log),nullptr,log);std::cerr<<log;throw std::runtime_error("link");}
 glUseProgram(p);return p;
}
int lamp(int x,int y,int z,int w){return x+w*(z+w*y);}
int main(){
 EGLDisplay d=eglGetDisplay(EGL_DEFAULT_DISPLAY);EGLint a,b,num;
 if(!eglInitialize(d,&a,&b)) throw std::runtime_error("egl");eglBindAPI(EGL_OPENGL_API);
 EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
 EGLConfig cfg;eglChooseConfig(d,attrs,&cfg,1,&num);
 EGLint ctx[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
 auto c=eglCreateContext(d,cfg,EGL_NO_CONTEXT,ctx);EGLint plane[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};auto screen=eglCreatePbufferSurface(d,cfg,plane);eglMakeCurrent(d,screen,screen,c);auto shader=compile();
 std::cout<<glGetString(GL_RENDERER)<<"\n";
 auto loc=[&](const char*n){return glGetUniformLocation(shader,n);};
 auto make=[](int unit,int w,int h,int fmt){GLuint t;glGenTextures(1,&t);glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,t);glTexStorage2D(GL_TEXTURE_2D,1,fmt,w,h);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);return t;};
 std::vector<float> field(512*2048),rp(512*512),depth(16*16,1);
 GLuint target=make(0,768,606,GL_R32UI);glBindImageTexture(0,target,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
 make(1,512,2048,GL_R32F);glUniform1i(loc("aqualumenLightField"),1);
 make(2,16,16,GL_DEPTH_COMPONENT32F);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,16,GL_DEPTH_COMPONENT,GL_FLOAT,depth.data());glUniform1i(loc("shadowtex0"),2);
 make(3,512,512,GL_R32F);glUniform1i(loc("aqualumenRippleA"),3);
 make(4,16,104,GL_R32UI);glUniform1i(loc("aqualumenDoorMask"),4);
 std::vector<float> identity(16,0);for(int i=0;i<4;i++)identity[i*5]=1;
 glUniformMatrix4fv(loc("gbufferModelViewInverse"),1,0,identity.data());glUniformMatrix4fv(loc("shadowModelView"),1,0,identity.data());identity[0]=identity[5]=identity[10]=.03;glUniformMatrix4fv(loc("shadowProjection"),1,0,identity.data());
 glUniform3f(loc("shadowLightPosition"),.5,.866,0);glUniform1f(loc("frameTimeCounter"),3);
 glUniform4f(loc("aqualumenGrid"),-32,-32,64,-1.1111);
 // Exercise the actual shadow_water vertex stage with Sodium-style flat top quads.
 auto vs=expand("working/shaders/shadow_water.vsh");auto ptr=vs.c_str();
 GLuint vertex=glCreateShader(GL_VERTEX_SHADER);glShaderSource(vertex,1,&ptr,nullptr);glCompileShader(vertex);
 GLuint capture=glCreateProgram();glAttachShader(capture,vertex);
 glBindAttribLocation(capture,6,"mc_Entity");glBindAttribLocation(capture,7,"at_midBlock");glLinkProgram(capture);
 GLint ok=0;glGetProgramiv(capture,GL_LINK_STATUS,&ok);if(!ok)throw std::runtime_error("capture program");
 auto captureWater=[&](GLuint program){
  glUseProgram(program);auto u=[&](const char* n){return glGetUniformLocation(program,n);};
  glUniform1i(u("bounceSurfaceImage"),0);
  std::vector<float> id(16);for(int i=0;i<4;i++)id[i*5]=1;
  glUniformMatrix4fv(u("shadowModelViewInverse"),1,0,id.data());
  glEnable(GL_RASTERIZER_DISCARD);glNormal3f(0,1,0);
  glVertexAttrib4f(6,10000,0,0,0);
  glBegin(GL_POINTS);
  for(int x=28;x<35;x++)for(int z=28;z<36;z++)for(int dx=0;dx<2;dx++)for(int dz=0;dz<2;dz++){
   glVertexAttrib4f(7,64.f*(.5f-dx),-25,64.f*(.5f-dz),0);
   glVertex3f(x-32+dx,-2+8.f/9.f,z-32+dz);
  }
  glEnd();glDisable(GL_RASTERIZER_DISCARD);glMemoryBarrier(GL_ALL_BARRIER_BITS);glUseProgram(shader);
 };
 auto run=[&](int mode){
  std::vector<unsigned> data(768*606,0);std::fill(field.begin(),field.end(),0);
  for(int x=24;x<=39;x++)for(int z=24;z<=39;z++){
    if(mode==1 || !(x>=31 && x<35 && z>=29 && z<36)){
     field[lamp(x,34,z,64)]=1;
     data[6*lamp(x-16,18,z-16,32)+2]=0x80000000u;
    }

  }
  for(int z=0;z<512;z++)for(int x=0;x<512;x++){
   float r=std::hypot((x-256)*.125f,(z-256)*.125f);
   rp[x+512*z]=mode==4?.045f*std::cos(9*r)*std::exp(-std::pow((r-2)/1.f,2)):0;
  }
  glActiveTexture(GL_TEXTURE0);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,768,606,GL_RED_INTEGER,GL_UNSIGNED_INT,data.data());
  if(mode!=2) {
   captureWater(capture);
   std::vector<unsigned> captured(data.size());glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,captured.data());
   int n=std::count(captured.begin()+258*768,captured.begin()+264*768,15u);
   if(n!=56)throw std::runtime_error("GPU top capture count "+std::to_string(n));
  }
  glActiveTexture(GL_TEXTURE1);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,2048,GL_RED,GL_FLOAT,field.data());
  glActiveTexture(GL_TEXTURE3);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,512,GL_RED,GL_FLOAT,rp.data());
  glUniform3f(loc("sunPosition"),.5,mode==3?-.866:.866,0);glUniform1i(loc("aqualumenActive"),1);
  glDispatchCompute(32,32,16);glMemoryBarrier(GL_ALL_BARRIER_BITS);glFinish();
  auto err=glGetError();if(err)throw std::runtime_error("dispatch error "+std::to_string(err));
  glActiveTexture(GL_TEXTURE0);glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,data.data());data.erase(data.begin(),data.begin()+264*768);
  std::cout<<"mode "<<mode<<" fixed-point flux "<<std::accumulate(data.begin(),data.end(),0ull)<<"\n";return data;
 };
 auto a0=run(0),a1=run(1),a2=run(2),a3=run(3),a4=run(4);
 auto sum=[](const auto& v){return std::accumulate(v.begin(),v.end(),0ull);};size_t delta=0;for(size_t i=0;i<a0.size();i++) delta+=a0[i]!=a4[i];
 std::cout<<"contact changed bins "<<delta<<"\n";
 return !(sum(a0)>0 && !sum(a1) && !sum(a2) && !sum(a3) && sum(a4)>0 && delta>20);
}
