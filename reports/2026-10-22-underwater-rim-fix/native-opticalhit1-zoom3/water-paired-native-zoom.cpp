#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
constexpr int side=65,pixels=side*side;
using Matrix=std::array<float,16>;
const Matrix identity={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
void require(bool good,const std::string& message) {if(!good)throw std::runtime_error(message);}
std::string source(const fs::path& file,const fs::path& root,int level=0) {
    require(level<32,"shader include cycle");std::ifstream stream(file);require(bool(stream),"cannot read "+file.string());
    std::ostringstream result;
    for(std::string line;std::getline(stream,line);) {
        if(line.rfind("#include",0)==0) {
            const auto a=line.find('"'),b=line.find('"',a+1);require(a!=std::string::npos&&b!=std::string::npos,"bad include");
            auto name=line.substr(a+1,b-a-1);result<<source(root/(name.front()=='/'?name.substr(1):name),root,level+1);
        }else result<<line<<'\n';
    }return result.str();
}
GLuint shader(GLenum type,const std::string& text) {
    const auto object=glCreateShader(type);const auto* pointer=text.c_str();glShaderSource(object,1,&pointer,nullptr);glCompileShader(object);
    GLint good=0;glGetShaderiv(object,GL_COMPILE_STATUS,&good);if(!good){char log[32768];glGetShaderInfoLog(object,sizeof(log),nullptr,log);throw std::runtime_error(log);}return object;
}
GLuint program(const std::string& vs,const std::string& fs) {
    GLuint vertex=shader(GL_VERTEX_SHADER,vs),fragment=shader(GL_FRAGMENT_SHADER,fs),result=glCreateProgram();
    glAttachShader(result,vertex);glAttachShader(result,fragment);glBindAttribLocation(result,10,"mc_Entity");glLinkProgram(result);
    glDeleteShader(vertex);glDeleteShader(fragment);GLint good=0;glGetProgramiv(result,GL_LINK_STATUS,&good);
    if(!good){char log[32768];glGetProgramInfoLog(result,sizeof(log),nullptr,log);throw std::runtime_error(log);}return result;
}
void raw(const fs::path& path,const std::vector<float>& values) {
    require(!fs::exists(path),"refuse existing artifact "+path.string());std::ofstream file(path,std::ios::binary);
    file.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()*sizeof(float)));require(bool(file),"artifact write failed");
}
void rawBytes(const fs::path& path,const std::vector<unsigned char>& values) {
    require(!fs::exists(path),"refuse existing artifact "+path.string());std::ofstream file(path,std::ios::binary);
    file.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()));require(bool(file),"artifact write failed");
}
struct Context {
    EGLDisplay display=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;
    Context(){
        auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");require(platform,"EGL platform extension missing");
        display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");EGLDeviceEXT devices[8];EGLint count=0;
            require(query&&query(8,devices,&count)&&count>0,"EGL device unavailable");display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            require(eglInitialize(display,nullptr,nullptr),"EGL device initialization failed");
        }
        require(eglBindAPI(EGL_OPENGL_API),"OpenGL API unavailable");
        const EGLint configAttributes[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count=0;require(eglChooseConfig(display,configAttributes,&config,1,&count)&&count==1,"no EGL config");
        const EGLint surfaceAttributes[]={EGL_WIDTH,side,EGL_HEIGHT,side,EGL_NONE};surface=eglCreatePbufferSurface(display,config,surfaceAttributes);
        const EGLint contextAttributes[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttributes);
        require(context!=EGL_NO_CONTEXT&&eglMakeCurrent(display,surface,surface,context),"compatibility context unavailable");
        const auto renderer=std::string(reinterpret_cast<const char*>(glGetString(GL_RENDERER)));
        std::cout<<"renderer="<<renderer<<"\nversion="<<glGetString(GL_VERSION)<<'\n';
        require(renderer.find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");
    }
    ~Context(){eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);}
};
struct Capture {std::vector<float> color,classification;};
struct Fixture {
    std::array<GLuint,14> textures={};GLuint framebuffer=0;Matrix projection,inverseProjection;
    const Matrix view={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const Matrix inverseView={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    Fixture(){
        const float f=3/std::tan(3.14159265358979323846f/6),n=.1f,z=128,a=-(z+n)/(z-n),b=-2*z*n/(z-n);
        projection={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};inverseProjection={1/f,0,0,0,0,1/f,0,0,0,0,1/b,0,0,-1,a/b};
        glGenTextures(textures.size(),textures.data());glGenFramebuffers(1,&framebuffer);
        std::vector<float> depth(pixels,1),color(pixels*4,.08f),sky(64*32*4,.04f),bathymetry(64*64*4,0);
        for(int p=0;p<pixels;++p)color[p*4+3]=1;
        for(int p=0;p<64*32;++p)sky[p*4+3]=1;
        for(size_t p=0;p<bathymetry.size();p+=4){bathymetry[p]=4;bathymetry[p+1]=3.25f;bathymetry[p+2]=1;}
        const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadow=0;
        upload(0,GL_RGBA32F,1,1,GL_RGBA,white);upload(1,GL_RGBA32F,side,side,GL_RGBA,color.data());
        upload(2,GL_RGBA16F,64,32,GL_RGBA,sky.data());upload(3,GL_DEPTH_COMPONENT32F,side,side,GL_DEPTH_COMPONENT,depth.data());
        upload(4,GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        upload(5,GL_RGBA16F,1,1,GL_RGBA,black);upload(6,GL_RGBA32F,64,64,GL_RGBA,bathymetry.data());upload(7,GL_RGBA16F,64,32,GL_RGBA,sky.data());
        receiver(0,true);upload(12,GL_RGBA32F,side,side,GL_RGBA,nullptr);upload(13,GL_RGBA32F,side,side,GL_RGBA,nullptr);
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[12],0);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT1,GL_TEXTURE_2D,textures[13],0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"test framebuffer incomplete");
        for(GLenum cap:{GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD})glDisable(cap);
        glDepthMask(GL_FALSE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glViewport(0,0,side,side);
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view.data());
        glDisableVertexAttribArray(10);glNormal3f(0,1,0);glColor4f(1,1,1,1);glMultiTexCoord2f(GL_TEXTURE0,.5f,.5f);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    }
    ~Fixture(){glDeleteTextures(textures.size(),textures.data());glDeleteFramebuffers(1,&framebuffer);}
    void upload(int unit,GLenum internal,int width,int height,GLenum format,const float* data){
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        for(GLenum parameter:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,parameter,GL_NEAREST);
        for(GLenum parameter:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,parameter,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,internal,width,height,0,format,GL_FLOAT,data);
    }
    void receiver(int kind,bool ready){
        std::vector<float> cells(8*8*8*4,0),radiance(cells.size(),0),sun(cells.size(),0),face(cells.size(),0);
        for(int y=0;y<8;++y)for(int z=0;z<8;++z)for(int x=0;x<8;++x){const int p=((y*8+z)*8+x)*4;
            cells[p]=kind==0?0:(y<3?3:2);cells[p+3]=1;
            radiance[p]=.2f;radiance[p+1]=.15f;radiance[p+2]=.1f;radiance[p+3]=ready?1:0;sun[p+3]=1;face[p+1]=1;face[p+3]=1;
        }
        upload(8,GL_RGBA32F,8,64,GL_RGBA,cells.data());upload(9,GL_RGBA32F,8,64,GL_RGBA,radiance.data());
        upload(10,GL_RGBA32F,8,64,GL_RGBA,sun.data());upload(11,GL_RGBA32F,8,64,GL_RGBA,face.data());
    }
    void uniforms(GLuint p,int producer,bool underwater){
        glUseProgram(p);const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7","aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces"};
        for(int i=0;i<12;++i){glUniform1i(glGetUniformLocation(p,names[i]),i);glActiveTexture(GL_TEXTURE0+i);glBindTexture(GL_TEXTURE_2D,textures[i]);}
        for(const auto& item:std::array<std::pair<const char*,Matrix>,6>{{{"gbufferProjection",projection},{"gbufferProjectionInverse",inverseProjection},{"gbufferModelView",view},{"gbufferModelViewInverse",inverseView},{"shadowProjection",identity},{"shadowModelView",identity}}})
            glUniformMatrix4fv(glGetUniformLocation(p,item.first),1,GL_FALSE,item.second.data());
        glUniform3f(glGetUniformLocation(p,"cameraPosition"),0,63,0);glUniform3f(glGetUniformLocation(p,"sunPosition"),0,0,-1);glUniform3f(glGetUniformLocation(p,"shadowLightPosition"),0,0,-1);
        glUniform1f(glGetUniformLocation(p,"viewWidth"),side);glUniform1f(glGetUniformLocation(p,"viewHeight"),side);glUniform1f(glGetUniformLocation(p,"far"),128);
        glUniform1f(glGetUniformLocation(p,"frameTimeCounter"),29);glUniform1i(glGetUniformLocation(p,"isEyeInWater"),underwater?1:0);
        glUniform1i(glGetUniformLocation(p,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(p,"aqualumenActive"),0);
        glUniform4f(glGetUniformLocation(p,"aqualumenGrid"),-32,-32,64,3.25f);glUniform1i(glGetUniformLocation(p,"aqualumenBathymetryReady"),1);
        glUniform4f(glGetUniformLocation(p,"aqualumenBathymetryGrid"),-32,-32,64,3.25f);
        glUniform1i(glGetUniformLocation(p,"aqualumenReceiverReady"),producer);glUniform1i(glGetUniformLocation(p,"aqualumenReceiverRunMode"),0);
        glUniform3f(glGetUniformLocation(p,"aqualumenReceiverOrigin"),-4,-4,-4);glUniform3i(glGetUniformLocation(p,"aqualumenReceiverSize"),8,8,8);
        glUniform1f(glGetUniformLocation(p,"rainStrength"),0);glUniform1i(glGetUniformLocation(p,"worldTime"),6000);glUniform2i(glGetUniformLocation(p,"eyeBrightnessSmooth"),0,240);
    }
    Capture draw(GLuint p,bool paired,int producer,bool underwater,float material=10000,bool clear=true,bool blend=false){
        uniforms(p,producer,underwater);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);const GLenum draws[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(paired?2:1,draws);
        if(clear){const float zero[4]={};glClearBufferfv(GL_COLOR,0,zero);glClearBufferfv(GL_COLOR,1,zero);}
        if(blend){glEnablei(GL_BLEND,0);glBlendFuncSeparatei(0,GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ZERO);}else glDisablei(GL_BLEND,0);
        glDisablei(GL_BLEND,1);glVertexAttrib4f(10,material,0,0,0);
        const float extent=material==10000?.5f:2.0f;
        const std::array<std::array<float,3>,4> vertices={{{-extent,3.25f,-extent},{-extent,3.25f,extent},{extent,3.25f,extent},{extent,3.25f,-extent}}};
        glBegin(GL_TRIANGLES);for(int i:{0,1,2,0,2,3})glVertex3fv(vertices[i].data());glEnd();
        Capture result;for(int i=0;i<(paired?2:1);++i){auto& output=i?result.classification:result.color;output.assign(pixels*4,std::numeric_limits<float>::quiet_NaN());
            glReadBuffer(draws[i]);glReadPixels(0,0,side,side,GL_RGBA,GL_FLOAT,output.data());for(float value:output)require(std::isfinite(value),"nonfinite readback");}
        require(glGetError()==GL_NO_ERROR,"native GL draw/read error");return result;
    }
};
int classify(const Capture& c,int expected,const std::string& label){
    int count=0;for(int p=0;p<pixels;++p){const auto at=p*4;const float mask=c.classification[at+3],route=c.classification[at];
        require(mask==0||mask==1,label+" mask not binary");if(mask==0){for(int component=0;component<4;++component)require(c.classification[at+component]==0,label+" nonwater not zero");continue;}
        require(route>=1&&route<=5&&route==std::floor(route),label+" invalid route");
        require(route==expected||((expected==2||expected==3)&&route==4),label+" unexpected valid route");
        require(c.classification[at+1]>=0&&c.classification[at+1]<=1,label+" invalid Fresnel");
        require(c.classification[at+2]>=0,label+" negative travel");if(route==expected)++count;
    }
    if(expected==0){require(count==0,label+" unexpected expected-route count");for(float value:c.classification)require(value==0,label+" expected no water record");}
    else {
        require(count>0,label+" expected route absent");
        const int centre=((side/2)*side+side/2)*4;
        require(c.classification[centre]==expected&&c.classification[centre+3]==1,label+" centre not expected water route");
    }
    return count;
}
bool equal(const std::vector<float>& a,const std::vector<float>& b){return a.size()==b.size()&&std::memcmp(a.data(),b.data(),a.size()*sizeof(float))==0;}
struct FinalFixture {
    std::array<GLuint,3> textures={};GLuint framebuffer=0;
    std::vector<float> color,classification;
    std::vector<unsigned char> expectedPreview;
    FinalFixture():color(pixels*4),classification(pixels*4),expectedPreview(pixels*4){
        for(int y=0;y<side;++y)for(int x=0;x<side;++x){const int p=y*side+x,at=p*4;
            color[at]=float((x*13+y*7)%97)/16.0f;color[at+1]=float((x*3+y*17)%89)/32.0f;
            color[at+2]=float((x*23+y*5)%83)/64.0f;color[at+3]=float((x+y)%11)/10.0f;
            classification[at]=p%2?9.0f:-9.0f;classification[at+1]=p%3?2.0f:-1.0f;
            classification[at+2]=p%5?96.0f:-48.0f;classification[at+3]=3.0f;
            expectedPreview[at]=p%2?255:0;expectedPreview[at+1]=p%3?255:0;
            expectedPreview[at+2]=p%5?255:0;expectedPreview[at+3]=255;
        }
        glGenTextures(textures.size(),textures.data());glGenFramebuffers(1,&framebuffer);
        for(int i=0;i<3;++i){glActiveTexture(GL_TEXTURE0+(i==1?12:0));glBindTexture(GL_TEXTURE_2D,textures[i]);
            for(GLenum parameter:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,parameter,i==0?GL_LINEAR:GL_NEAREST);
            for(GLenum parameter:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,parameter,GL_CLAMP_TO_EDGE);
            if(i<2)glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,side,side,0,GL_RGBA,GL_FLOAT,i==0?color.data():classification.data());
            else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,side,side,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
        }
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[2],0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"final framebuffer incomplete");
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);glViewport(0,0,side,side);
        glDisablei(GL_BLEND,0);glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    }
    ~FinalFixture(){glDeleteTextures(textures.size(),textures.data());glDeleteFramebuffers(1,&framebuffer);}
    GLint activeUniform(GLuint p,const char* name,GLint type){
        const GLint location=glGetUniformLocation(p,name);require(location>=0,std::string("final uniform inactive: ")+name);
        GLuint index=GL_INVALID_INDEX;glGetUniformIndices(p,1,&name,&index);require(index!=GL_INVALID_INDEX,"final uniform index absent");
        GLint actualType=0;glGetActiveUniformsiv(p,1,&index,GL_UNIFORM_TYPE,&actualType);require(actualType==type,std::string("final uniform type differs: ")+name);
        return location;
    }
    std::vector<unsigned char> draw(GLuint p,bool paired,int preview){
        glUseProgram(p);glUniform1i(activeUniform(p,"colortex0",GL_SAMPLER_2D),0);
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[0]);
        glUniform1f(glGetUniformLocation(p,"viewWidth"),side);glUniform1f(glGetUniformLocation(p,"viewHeight"),side);
        glUniform1i(glGetUniformLocation(p,"aqualumenDimension"),0);
        glUniformMatrix4fv(glGetUniformLocation(p,"gbufferModelViewInverse"),1,GL_FALSE,identity.data());
        glUniform3f(glGetUniformLocation(p,"sunPosition"),0,1,0);
        if(paired){
            const GLint previewLocation=activeUniform(p,"aqualumenPairedView",GL_INT);glUniform1i(previewLocation,preview);
            GLint actualPreview=-1;glGetUniformiv(p,previewLocation,&actualPreview);require(actualPreview==preview,"final preview uniform value differs");
            const GLint samplerLocation=activeUniform(p,"colortex12",GL_SAMPLER_2D);glUniform1i(samplerLocation,12);
            GLint actualUnit=-1;glGetUniformiv(p,samplerLocation,&actualUnit);require(actualUnit==12,"final C12 sampler unit differs");
            glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,textures[1]);
            GLint internal=0,width=0,height=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&internal);
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&width);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&height);
            require(internal==GL_RGBA32F&&width==side&&height==side,"final C12 texture shape differs");
            std::vector<float> actual(pixels*4);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());
            require(equal(actual,classification),"actual final C12 differs from invalid input pattern");
        }
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);const float clear[4]={.125f,.25f,.5f,0};glClearBufferfv(GL_COLOR,0,clear);
        glBegin(GL_TRIANGLES);for(int i:{0,1,2,0,2,3}){
            const float x=(i==1||i==2)?1.0f:0.0f,y=i>=2?1.0f:0.0f;
            glMultiTexCoord2f(GL_TEXTURE0,x,y);glVertex2f(x*2-1,y*2-1);
        }glEnd();
        std::vector<unsigned char> result(pixels*4);glReadPixels(0,0,side,side,GL_RGBA,GL_UNSIGNED_BYTE,result.data());
        for(int p=0;p<pixels;++p)require(result[p*4+3]==255,"final quad did not cover framebuffer");
        require(glGetError()==GL_NO_ERROR,"final GL draw/read error");return result;
    }
};
void finalCheck(const fs::path& control,const fs::path& paired,const fs::path& output,std::ostringstream& report){
    const auto cvs=source(control/"final.vsh",control),pvs=source(paired/"final.vsh",paired);require(cvs==pvs,"final control and paired VS differ");
    const GLuint cp=program(cvs,source(control/"final.fsh",control)),pp=program(pvs,source(paired/"final.fsh",paired));
    FinalFixture fixture;const auto a=fixture.draw(cp,false,0),b=fixture.draw(pp,true,0),preview=fixture.draw(pp,true,1);
    require(a==b,"final preview0 output not byte identical");require(a!=preview,"final preview1 did not change output");
    require(preview==fixture.expectedPreview,"final preview1 did not sample expected invalid C12 pattern");
    bool nonuniform=false;for(int p=1;p<pixels;++p)for(int c=0;c<3;++c)nonuniform|=a[p*4+c]!=a[c];
    require(nonuniform,"final synthetic beauty output unexpectedly uniform");
    raw(output/"final-input-C0.rgba32f",fixture.color);raw(output/"final-input-C12-invalid.rgba32f",fixture.classification);
    rawBytes(output/"final-control.rgba8",a);rawBytes(output/"final-paired-preview0.rgba8",b);rawBytes(output/"final-paired-preview1.rgba8",preview);
    report<<"final_preview_uniform=active-int\nfinal_preview0_uniform=0\nfinal_C12=active-sampler2D-RGBA32F-invalid-pattern\nfinal_C0=shared-nonuniform-RGBA32F-linear\nfinal_output=RGBA8-full-framebuffer\nfinal_preview0_byte_equal=1\nfinal_preview1_sensitive=1\nfinal_preview1_expected_pattern=1\n";
    glDeleteProgram(cp);glDeleteProgram(pp);
}
int main(int argc,char** argv){
    try{
        require(argc==4,"usage: water-paired-native CONTROL_SHADER_ROOT PAIRED_SHADER_ROOT NEW_OUTPUT_DIRECTORY");
        const fs::path control=argv[1],paired=argv[2],output=argv[3];require(!fs::exists(output),"output must not exist");fs::create_directories(output);
        Context context;Fixture fixture;const auto vs=source(control/"gbuffers_water.vsh",control),pvs=source(paired/"gbuffers_water.vsh",paired);
        require(vs==pvs,"control and paired VS differ");const auto cfs=source(control/"gbuffers_water.fsh",control),pfs=source(paired/"gbuffers_water.fsh",paired);
        const GLuint cp=program(vs,cfs),pp=program(pvs,pfs);
        struct Case{const char* name;int producer,geometry,route;bool sourceReady,underwater;float material;};
        const Case cases[]={{"producer-unavailable",0,0,5,true,true,10000},{"unknown",1,0,4,true,true,10000},{"known-unready",1,1,3,false,true,10000},
            {"world-source",1,1,2,true,true,10000},{"above-water",0,0,0,true,false,10000},{"nonwater",0,0,0,true,true,0}};
        std::ostringstream report;report<<"scope=native generated VS/FS fixture; not Iris binding or natural visual acceptance\nviewport=65x65\nraw_origin=bottom-left\nrgba32f_endian=native\n";
        for(const auto& item:cases){fixture.receiver(item.geometry,item.sourceReady);const auto a=fixture.draw(cp,false,item.producer,item.underwater,item.material),b=fixture.draw(pp,true,item.producer,item.underwater,item.material);
            require(equal(a.color,b.color),std::string(item.name)+" C0 not byte identical");const auto count=classify(b,item.route,item.name);
            raw(output/(std::string(item.name)+"-control-C0.rgba32f"),a.color);raw(output/(std::string(item.name)+"-paired-C0.rgba32f"),b.color);
            raw(output/(std::string(item.name)+"-paired-C12.rgba32f"),b.classification);
            report<<item.name<<" expected_route="<<item.route<<" expected_count="<<count<<" C0_byte_equal=1\n";
        }
        fixture.receiver(0,true);fixture.draw(pp,true,0,true);const float translucent[4]={1,1,1,.35f};fixture.upload(0,GL_RGBA32F,1,1,GL_RGBA,translucent);
        const auto transition=fixture.draw(pp,true,0,true,0,false,true);classify(transition,0,"nonwater translucent transition");
        report<<"nonwater_translucent_without_C12_clear=zero\n";
        const auto last=pfs.rfind("gl_FragData[1]");require(last!=std::string::npos,"paired output store missing");const auto end=pfs.find(';',last);require(end!=std::string::npos,"paired output store unterminated");
        auto mutant=pfs;mutant.replace(last,end-last,"gl_FragData[1]=vec4(9.0,0.0,0.0,1.0)");const GLuint mp=program(pvs,mutant);
        const auto unmutated=fixture.draw(pp,true,0,true),mutated=fixture.draw(mp,true,0,true);
        require(equal(unmutated.color,mutated.color),"route mutant changed C0");
        bool rejected=false;try{classify(mutated,5,"route mutant");}catch(const std::runtime_error& error){
            require(std::string(error.what())=="route mutant invalid route","mutant failed for an unpredicted reason");rejected=true;
        }
        require(rejected,"route mutant was not rejected");report<<"route_assignment_mutant=rejected\nroute_assignment_mutant_reason=route mutant invalid route\n";
        finalCheck(control,paired,output,report);
        report<<"untested_route=SSR1\nresult=PASS\n";
        std::ofstream summary(output/"SUMMARY.txt");summary<<report.str();require(bool(summary),"summary write failed");std::cout<<report.str();
        glDeleteProgram(cp);glDeleteProgram(pp);glDeleteProgram(mp);return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}

