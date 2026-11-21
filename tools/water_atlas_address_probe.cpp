// TEST-only NVIDIA coordinate-expression execution. Never installs/opens Minecraft.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <openssl/sha.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <regex>
#include <vector>
#include <stdexcept>
#include <iomanip>
namespace fs=std::filesystem;
static void require(bool ok,const std::string& why){if(!ok)throw std::runtime_error(why);}
static std::string read(const fs::path& p){std::ifstream f(p);require(bool(f),"Missing source");return {std::istreambuf_iterator<char>(f),{}};}
static std::string expand(const fs::path& p,const fs::path& root,int depth=0){
    require(depth<32,"Include cycle");std::istringstream input(read(p));std::string line,out;
    std::regex pattern(R"re(^#include\s+"(/?[^"\s]+)"\s*$)re");std::smatch match;
    while(std::getline(input,line)){if(std::regex_match(line,match,pattern)){
        std::string name=match[1];if(name[0]=='/')name.erase(0,1);
        require(name.find("..") == std::string::npos,"Unsafe include");out+=expand(root/name,root,depth+1);
    }else out+=line+'\n';}return out;
}
static std::string sha(const std::string& s){unsigned char bytes[32];SHA256(reinterpret_cast<const unsigned char*>(s.data()),s.size(),bytes);std::ostringstream out;for(auto b:bytes)out<<std::hex<<std::setw(2)<<std::setfill('0')<<int(b);return out.str();}
static GLuint shader(GLenum stage,const std::string& source){
    GLuint s=glCreateShader(stage);const char* p=source.c_str();glShaderSource(s,1,&p,nullptr);glCompileShader(s);
    GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char log[4096];glGetShaderInfoLog(s,sizeof(log),nullptr,log);throw std::runtime_error(log);}return s;
}
static GLuint link(const std::string& vertex,const std::string& fragment){
    GLuint vs=shader(GL_VERTEX_SHADER,vertex),ps=shader(GL_FRAGMENT_SHADER,fragment),p=glCreateProgram();
    glAttachShader(p,vs);glAttachShader(p,ps);glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);
    require(ok,"Program link failed");glDeleteShader(vs);glDeleteShader(ps);return p;
}
struct Case{int width,height;std::size_t mismatches;std::string bodyHash;};
static Case execute(const fs::path& root,bool aligned,int width,int height){
    const auto vertex=expand(root/"final.vsh",root),full=expand(root/"final.fsh",root);
    // Compile/link the full actual FINAL, separately from the reduced address draw.
    GLuint production=link(vertex,full);glDeleteProgram(production);
    const auto main=full.rfind("void main() {\n");require(main!=std::string::npos,"Missing FINAL main");
    const auto end=full.find("    vec3 displayed;",main);require(end!=std::string::npos,"Missing record consumer");
    const auto body=full.substr(main+14,end-(main+14));
    require(body.find(aligned?"ivec2 outputPixel=ivec2(gl_FragCoord.xy);":"vec2 atlas=texcoord*vec2(4.0,2.0);")!=std::string::npos,"Wrong coordinate policy");
    std::string probe="#version 330 compatibility\nuniform float viewWidth;uniform float viewHeight;uniform sampler2D colortex9;in vec2 texcoord;\nvoid main() {\n"+body+"gl_FragColor=vec4(vec2(sourcePixel),float(tile),1.0);}\n";
    GLuint program=link(vertex,probe);glUseProgram(program);
    glUniform1f(glGetUniformLocation(program,"viewWidth"),float(width));glUniform1f(glGetUniformLocation(program,"viewHeight"),float(height));
    GLuint source,target,fbo;glGenTextures(1,&source);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,source);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,nullptr);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glUniform1i(glGetUniformLocation(program,"colortex9"),0);
    glGenTextures(1,&target);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,target);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,nullptr);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,target,0);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"Incomplete probe framebuffer");
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);glViewport(0,0,width,height);
    glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glDisable(GL_FRAMEBUFFER_SRGB);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
    std::vector<float> pixels(std::size_t(width)*height*4);glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,pixels.data());
    require(glGetError()==GL_NO_ERROR,"Native probe GL error");std::size_t mismatches=0;const int tw=width/4,th=height/2;
    for(int y=0;y<height;++y)for(int x=0;x<width;++x){auto i=(std::size_t(y)*width+x)*4;
        int sx=((2*(x%tw)+1)*width)/(2*tw),sy=((2*(y%th)+1)*height)/(2*th),tile=x/tw+4*(y/th);
        if(pixels[i]!=sx||pixels[i+1]!=sy||pixels[i+2]!=tile||pixels[i+3]!=1)mismatches++;
    }
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);glDeleteTextures(1,&target);glDeleteTextures(1,&source);glDeleteProgram(program);
    return {width,height,mismatches,sha(body)};
}
int main(int argc,char** argv){try{
    require(argc==4,"Usage: water-atlas-address-probe OLD-shaders ALIGNED-shaders NEW.json");
    fs::path output=argv[3];require(!fs::exists(output)&&!fs::is_symlink(output),"Output must be new");
    auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");require(platform,"Missing EGL platform");
    EGLDisplay display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
    if(!eglInitialize(display,nullptr,nullptr)){auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");EGLDeviceEXT devices[8];EGLint count=0;require(query&&query(8,devices,&count)&&count,"No EGL device");display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);require(eglInitialize(display,nullptr,nullptr),"EGL init failed");}
    require(eglBindAPI(EGL_OPENGL_API),"OpenGL API unavailable");EGLint attributes[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};EGLConfig config;EGLint count;
    require(eglChooseConfig(display,attributes,&config,1,&count)&&count,"Missing EGL configuration");EGLint extent[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};auto surface=eglCreatePbufferSurface(display,config,extent);
    EGLint profile[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};auto context=eglCreateContext(display,config,EGL_NO_CONTEXT,profile);
    require(context!=EGL_NO_CONTEXT&&eglMakeCurrent(display,surface,surface,context),"GL context unavailable");
    std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER)),version=reinterpret_cast<const char*>(glGetString(GL_VERSION));require(renderer.find("NVIDIA")!=std::string::npos,"NVIDIA required, no software substitution");
    std::ostringstream report;report<<"{\n  \"schema\":\"aqualumen-native-atlas-address-v1\",\n  \"renderer\":\""<<renderer<<"\",\n  \"GL\":\""<<version<<"\",\n  \"scope\":\"Native reduced coordinate-expression draw; complete FINAL also linked, NOT Iris binding/freshness or physical quality\",\n  \"IrisAccepted\":false,\n  \"physicalAccepted\":false,\n  \"cases\":[\n";
    bool first=true,qualified=true;for(bool aligned:{false,true})for(auto size:{std::pair{1600,900},std::pair{2560,1440}}){auto result=execute(argv[aligned?2:1],aligned,size.first,size.second);
        if(!first){report<<",\n";}
        first=false;report<<"    {\"aligned\":"<<(aligned?"true":"false")<<",\"width\":"<<result.width<<",\"height\":"<<result.height<<",\"pixels\":"<<result.width*result.height<<",\"mismatchedAddresses\":"<<result.mismatches<<",\"coordinateBodySHA256\":\""<<result.bodyHash<<"\"}";if(aligned&&result.mismatches)qualified=false;
    }
    report<<"\n  ],\n  \"alignedNativeCoordinateQualified\":"<<(qualified?"true":"false")<<"\n}\n";
    std::ofstream file(output);require(bool(file),"Cannot publish new result");file<<report.str();file.close();std::cout<<report.str();
    eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);return qualified?0:1;
}catch(const std::exception& failure){std::cerr<<"Rejected native atlas probe: "<<failure.what()<<'\n';return 1;}}
