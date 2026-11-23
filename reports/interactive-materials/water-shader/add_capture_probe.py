from pathlib import Path
p=Path('probe.cpp')
s=p.read_text().replace('auto c=eglCreateContext(d,cfg,EGL_NO_CONTEXT,ctx);eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,c);','auto c=eglCreateContext(d,cfg,EGL_NO_CONTEXT,ctx);EGLint plane[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};auto screen=eglCreatePbufferSurface(d,cfg,plane);eglMakeCurrent(d,screen,screen,c);')
a=' auto run=[&](int mode){'
s=s.replace(a,''' // Exercise the actual shadow_water vertex stage with Sodium-style flat top quads.
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
''' + a)
s=s.replace('    if(mode!=2 && x>=28 && x<35 && z>=28 && z<36)\n      data[258*768+lamp(x-24,6,z-24,16)]=15;','')
s=s.replace('  glActiveTexture(GL_TEXTURE1);glTexSubImage2D', '''  if(mode!=2) {
   captureWater(capture);
   std::vector<unsigned> captured(data.size());glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,captured.data());
   int n=std::count(captured.begin()+258*768,captured.begin()+264*768,15u);
   if(n!=56)throw std::runtime_error("GPU top capture count "+std::to_string(n));
  }
  glActiveTexture(GL_TEXTURE1);glTexSubImage2D''')
s=s.replace('#include <cmath>','#include <cmath>\n#include <algorithm>')
p.write_text(s)
