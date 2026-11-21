// TEST-only native replay of after-quad read routing and per-FBO read-buffer state.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <array>
#include <vector>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cstring>
#include <cmath>
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static GLuint shader(GLenum type,const char* src){GLuint s=glCreateShader(type);glShaderSource(s,1,&src,nullptr);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);need(ok,"fixture shader compile");return s;}
static GLuint program(){const char* vs="#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
 const char* fs="#version 330 compatibility\nvoid main(){gl_FragColor=vec4(gl_FragCoord.x/48.0,gl_FragCoord.y/32.0,0.375,1.0);}";
 auto v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs),p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);need(ok,"fixture link");glDeleteShader(v);glDeleteShader(f);return p;}
static GLint value(GLenum n){GLint v;glGetIntegerv(n,&v);return v;}
static constexpr std::array<GLenum,11> keys={GL_READ_FRAMEBUFFER_BINDING,GL_READ_BUFFER,GL_PIXEL_PACK_BUFFER_BINDING,GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_IMAGE_HEIGHT,GL_PACK_SKIP_PIXELS,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_IMAGES,GL_PACK_SWAP_BYTES,GL_PACK_LSB_FIRST};
static std::array<GLint,11> state(){std::array<GLint,11> r;for(size_t i=0;i<keys.size();i++)r[i]=value(keys[i]);return r;}
static void cleanPack(){glBindBuffer(GL_PIXEL_PACK_BUFFER,0);for(size_t i=4;i<keys.size();i++)glPixelStorei(keys[i],0);glPixelStorei(GL_PACK_ALIGNMENT,4);}
static void restore(const std::array<GLint,11>& s){glBindFramebuffer(GL_READ_FRAMEBUFFER,s[0]);glReadBuffer(s[1]);glBindBuffer(GL_PIXEL_PACK_BUFFER,s[2]);for(size_t i=3;i<keys.size();i++)glPixelStorei(keys[i],s[i]);}
static std::array<float,4> observe(GLuint fbo,bool fix){auto saved=state();glBindFramebuffer(GL_READ_FRAMEBUFFER,fbo);int target=value(GL_READ_BUFFER);glReadBuffer(GL_COLOR_ATTACHMENT0);cleanPack();std::array<float,4> out;glReadPixels(21,9,1,1,GL_RGBA,GL_FLOAT,out.data());if(fix)glReadBuffer(target);restore(saved);return out;}
static GLuint texture(){GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,48,32,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);return t;}
static GLuint framebuffer(){GLuint f;glGenFramebuffers(1,&f);glBindFramebuffer(GL_FRAMEBUFFER,f);auto a=texture(),b=texture();glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,a,0);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT1,GL_TEXTURE_2D,b,0);glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT1);need(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"fixture framebuffer");return f;}
static std::vector<unsigned char> bytes(GLuint output){auto saved=state();glBindFramebuffer(GL_READ_FRAMEBUFFER,output);int target=value(GL_READ_BUFFER);glReadBuffer(GL_COLOR_ATTACHMENT0);cleanPack();std::vector<unsigned char> b(48*32*4);glReadPixels(0,0,48,32,GL_RGBA,GL_UNSIGNED_BYTE,b.data());glReadBuffer(target);restore(saved);return b;}
static void draw(){glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();}
int main(int argc,char** argv){try {
 need(argc==2,"new output JSON required");need(!std::filesystem::exists(argv[1]),"refuse output overwrite");
 auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");need(platform,"EGL platform");EGLDisplay d=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
 if(!eglInitialize(d,nullptr,nullptr)){auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");EGLDeviceEXT devices[8];EGLint n;need(query&&query(8,devices,&n)&&n,"EGL device");d=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);need(eglInitialize(d,nullptr,nullptr),"EGL initialize");}
 need(eglBindAPI(EGL_OPENGL_API),"GL API");EGLint attributes[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};EGLConfig c;EGLint n;need(eglChooseConfig(d,attributes,&c,1,&n)&&n,"EGL config");EGLint dims[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};auto surface=eglCreatePbufferSurface(d,c,dims);EGLint profile[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};auto context=eglCreateContext(d,c,EGL_NO_CONTEXT,profile);need(context!=EGL_NO_CONTEXT&&eglMakeCurrent(d,surface,surface,context),"GL context");
 std::string renderer=(const char*)glGetString(GL_RENDERER),version=(const char*)glGetString(GL_VERSION);need(renderer.find("NVIDIA")!=std::string::npos,"NVIDIA only");
 GLuint p=program(),output=framebuffer(),reader=framebuffer(),pack;glGenBuffers(1,&pack);glBindBuffer(GL_PIXEL_PACK_BUFFER,pack);glBufferData(GL_PIXEL_PACK_BUFFER,65536,nullptr,GL_STATIC_READ);
 glBindFramebuffer(GL_DRAW_FRAMEBUFFER,output);glBindFramebuffer(GL_READ_FRAMEBUFFER,reader);glUseProgram(p);glViewport(0,0,48,32);glDisable(GL_FRAMEBUFFER_SRGB);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_DITHER);draw();
 glPixelStorei(GL_PACK_ALIGNMENT,8);glPixelStorei(GL_PACK_ROW_LENGTH,7);glPixelStorei(GL_PACK_IMAGE_HEIGHT,6);glPixelStorei(GL_PACK_SKIP_PIXELS,5);glPixelStorei(GL_PACK_SKIP_ROWS,4);glPixelStorei(GL_PACK_SKIP_IMAGES,3);glPixelStorei(GL_PACK_SWAP_BYTES,1);glPixelStorei(GL_PACK_LSB_FIRST,1);
 auto original=state();auto before=bytes(output);observe(output,false);need(state()==original,"negative caller restore");glBindFramebuffer(GL_READ_FRAMEBUFFER,output);bool leaked=value(GL_READ_BUFFER)!=GL_COLOR_ATTACHMENT1;glReadBuffer(GL_COLOR_ATTACHMENT1);restore(original);need(leaked,"negative failed to reproduce target read-buffer leak");
 for(int i=0;i<2;i++){auto pixel=observe(output,true);need(state()==original,"caller state differs");need(value(GL_DRAW_FRAMEBUFFER_BINDING)==(int)output&&value(GL_CURRENT_PROGRAM)==(int)p,"draw/program differs");glBindFramebuffer(GL_READ_FRAMEBUFFER,output);need(value(GL_READ_BUFFER)==GL_COLOR_ATTACHMENT1,"target read-buffer differs");restore(original);std::array<float,4> expected={std::round((21.5f/48)*255)/255,std::round((9.5f/32)*255)/255,std::round(.375f*255)/255,1};for(int k=0;k<4;k++)need(std::abs(pixel[k]-expected[k])<1e-6,"output route/color differs");need(bytes(output)==before,"output bytes changed by observe");draw();need(bytes(output)==before,"subsequent draw changed");}
 need(glGetError()==GL_NO_ERROR,"native fixture GL error (observer itself never consumes it)");
 std::ofstream f(argv[1]);need(bool(f),"new report");f<<"{\"schema\":\"aqualumen-atlas-native-output-state-v1\",\"renderer\":\""<<renderer<<"\",\"GL\":\""<<version<<"\",\"negativeTargetReadBufferLeakReproduced\":true,\"caller11StateFieldsEqual\":true,\"targetReadBufferRestored\":true,\"outputRoutingAndColorMatch\":true,\"wholeOutputBytesPassive\":true,\"subsequentDrawBytesEqual\":true,\"repeats\":2,\"IrisAccepted\":false,\"physicalAccepted\":false}\n";f.close();std::cout<<"PASS native after-quad routing/state RED->GREEN, repeated output passivity; "<<renderer<<"; "<<version<<"\n";
 eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(d,context);eglDestroySurface(d,surface);eglTerminate(d);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
