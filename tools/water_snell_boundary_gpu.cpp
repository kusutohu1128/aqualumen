#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <array>
#include <cstring>
#include <cmath>
#include <iomanip>
#include <limits>
#include <cstdint>
#include <epoxy/gl.h>
#include <epoxy/egl.h>
static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559);
using Record=std::array<float,7>;
static_assert(sizeof(Record)==28);
std::vector<Record> records(const std::string& bytes) {
    if (bytes.empty() || bytes.size()%sizeof(Record)!=0 || bytes.size()>512*sizeof(Record))
        throw std::runtime_error("Need 1..512 whole seven-float records");
    std::vector<Record> result(bytes.size()/sizeof(Record));
    std::memcpy(result.data(),bytes.data(),bytes.size());
    for (const auto& record:result) for (float value:record)
        if (!std::isfinite(value)) throw std::runtime_error("Need finite input values");
    return result;
}
namespace fs=std::filesystem;
std::string read(const fs::path& path) {
    std::ifstream stream(path,std::ios::binary);
    if (!stream) throw std::runtime_error("Cannot read "+path.string());
    return {std::istreambuf_iterator<char>(stream),std::istreambuf_iterator<char>()};
}
std::string quote(const std::string& text) {
    std::ostringstream out;out<<'"';
    for (unsigned char c:text) {
        if (c=='"' || c=='\\') out<<'\\'<<char(c);
        else if (c=='\n') out<<"\\n";
        else if (c=='\r') out<<"\\r";
        else if (c=='\t') out<<"\\t";
        else if (c<32) throw std::runtime_error("Unsupported control character");
        else out<<char(c);
    }
    return out.str()+'"';
}
const std::string vertex="#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
std::string fragment(const std::string& helper) {
    return "#version 330 compatibility\n"+helper+"\n"
        "uniform vec3 wsView; uniform vec3 wsTarget; uniform float wsEta;\n"
        "void main(){WaterSnellNode node=waterSnellNode(wsView,wsTarget,wsEta);\n"
        "gl_FragData[0]=vec4(node.facet,float(node.status));\n"
        "gl_FragData[1]=vec4(node.ray,node.facing);\n"
        "gl_FragData[2]=vec4(node.transmittedCosine,node.transmission,node.jacobian,1.0);}\n";
}
void require(bool value,const std::string& message) { if (!value) throw std::runtime_error(message); }
void write(const fs::path& path,const std::string& bytes) {
    std::ofstream stream(path,std::ios::binary);stream.write(bytes.data(),std::streamsize(bytes.size()));
    require(bool(stream),"Cannot write "+path.string());
}
void raw(const fs::path& path,const std::vector<float>& values) {
    write(path,std::string(reinterpret_cast<const char*>(values.data()),values.size()*sizeof(float)));
}
void numbers(std::ostream& out,const float* values,std::size_t count) {
    out<<'[';for (std::size_t i=0;i<count;++i) { if (i) out<<',';
        if (std::isfinite(values[i])) out<<values[i];else out<<"null"; }out<<']';
}
struct Context {
    EGLDisplay display=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;
    Context() {
        // Same surfaceless/device fallback and compatibility request as glcheck.cpp.
        auto platform=reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
        require(platform!=nullptr,"No EGL platform entry point");
        display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if (!eglInitialize(display,nullptr,nullptr)) {
            auto query=reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
            EGLDeviceEXT devices[8];EGLint count=0;
            require(query && query(8,devices,&count) && count>0,"No EGL device");
            display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            require(eglInitialize(display,nullptr,nullptr),"Cannot initialize EGL device");
        }
        require(eglBindAPI(EGL_OPENGL_API),"Cannot bind OpenGL API");
        const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
        EGLConfig config;EGLint count=0;require(eglChooseConfig(display,attrs,&config,1,&count)&&count>0,"No EGL config");
        const EGLint size[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};surface=eglCreatePbufferSurface(display,config,size);
        const EGLint profile[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,
            EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context=eglCreateContext(display,config,EGL_NO_CONTEXT,profile);
        require(surface!=EGL_NO_SURFACE && context!=EGL_NO_CONTEXT
            && eglMakeCurrent(display,surface,surface,context),"Cannot create GL compatibility context");
    }
    ~Context() { eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
        eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display); }
};
GLuint shader(GLenum type,const std::string& source) {
    GLuint result=glCreateShader(type);const char* text=source.data();const GLint length=GLint(source.size());
    glShaderSource(result,1,&text,&length);glCompileShader(result);GLint okay=0;glGetShaderiv(result,GL_COMPILE_STATUS,&okay);
    if (!okay) { char log[16384];glGetShaderInfoLog(result,sizeof(log),nullptr,log);throw std::runtime_error(log); }
    return result;
}
int render(const std::string& helper,const std::string& inputBytes,const std::vector<Record>& inputs,const fs::path& output) {
    require(!fs::exists(output) && !fs::is_symlink(output),"NEW output directory required");
    Context context;const auto renderer=std::string(reinterpret_cast<const char*>(glGetString(GL_RENDERER)));
    require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual RTX 3080 Ti renderer required");
    const bool fp64=epoxy_has_gl_extension("GL_ARB_gpu_shader_fp64");require(fp64,"Actual shader fp64 extension required");
    const auto source=fragment(helper);GLuint program=glCreateProgram();
    for (auto pair:{std::pair<GLenum,std::string>{GL_VERTEX_SHADER,vertex},{GL_FRAGMENT_SHADER,source}}) {
        GLuint stage=shader(pair.first,pair.second);glAttachShader(program,stage);glDeleteShader(stage);
    }
    glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    if (!linked) { char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(log); }
    require(fs::create_directory(output),"Cannot create NEW output directory");
    write(output/"inputs.f32",inputBytes);write(output/"helper.glsl",helper);
    GLuint attached[2];GLsizei attachedCount=0;glGetAttachedShaders(program,2,&attachedCount,attached);
    require(attachedCount==2,"Exactly VS/FS must be attached");
    for (GLuint stage:attached) { GLint type=0,length=0;glGetShaderiv(stage,GL_SHADER_TYPE,&type);glGetShaderiv(stage,GL_SHADER_SOURCE_LENGTH,&length);
        std::string actual(std::size_t(length),'\0');GLsizei used=0;glGetShaderSource(stage,length,&used,actual.data());actual.resize(std::size_t(used));
        require(actual==(type==GL_VERTEX_SHADER?vertex:source),"Attached source differs from literal constructed stage");
        write(output/(type==GL_VERTEX_SHADER?"attached-vertex.glsl":"attached-fragment.glsl"),actual);
    }
    const char* names[]={"wsView","wsTarget","wsEta"};GLuint indices[3];glGetUniformIndices(program,3,names,indices);
    GLint types[3],sizes[3],locations[3];glGetActiveUniformsiv(program,3,indices,GL_UNIFORM_TYPE,types);
    glGetActiveUniformsiv(program,3,indices,GL_UNIFORM_SIZE,sizes);
    for (int i=0;i<3;++i) { locations[i]=glGetUniformLocation(program,names[i]);
        require(indices[i]!=GL_INVALID_INDEX && locations[i]>=0 && sizes[i]==1
            && types[i]==(i<2?GL_FLOAT_VEC3:GL_FLOAT),"Actual active uniform type/size differs"); }
    GLuint textures[3],fbo;glGenTextures(3,textures);glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    const GLenum buffers[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2};
    for (int i=0;i<3;++i) { glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,GLsizei(inputs.size()),1,0,GL_RGBA,GL_FLOAT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        GLint actualFormat=0,width=0,height=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&actualFormat);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&width);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&height);
        require(actualFormat==GL_RGBA32F && width==GLint(inputs.size()) && height==1,"Actual three-target storage differs");
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[i],GL_TEXTURE_2D,textures[i],0); }
    glDrawBuffers(3,buffers);require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"Incomplete three-output framebuffer");
    for (auto capability:{GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,GL_DITHER,GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB}) glDisable(capability);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glUseProgram(program);
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-snell-node-native-v1\",\"renderer\":"<<quote(renderer)
        <<",\"GL\":"<<quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"fp64Extension\":true,\"program\":"<<program
        <<",\"width\":"<<inputs.size()<<",\"height\":1,\"targetInternalFormat\":34836,\"format\":\"little-endian binary32\",\"uniforms\":[";
    for (int i=0;i<3;++i) { if (i) report<<',';report<<"{\"name\":"<<quote(names[i])<<",\"type\":"<<types[i]
        <<",\"size\":"<<sizes[i]<<",\"location\":"<<locations[i]<<'}'; }report<<"],\"uploads\":[";
    std::array<std::array<std::vector<float>,3>,2> captures;
    for (int repeat=0;repeat<2;++repeat) {
        const float zero[4]={};for (int i=0;i<3;++i) glClearBufferfv(GL_COLOR,i,zero);
        for (std::size_t i=0;i<inputs.size();++i) { const auto& values=inputs[i];
            glUniform3fv(locations[0],1,values.data());glUniform3fv(locations[1],1,values.data()+3);glUniform1f(locations[2],values[6]);
            auto query=[&]() { Record actual={};glGetUniformfv(program,locations[0],actual.data());glGetUniformfv(program,locations[1],actual.data()+3);
                glGetUniformfv(program,locations[2],actual.data()+6);require(std::memcmp(actual.data(),values.data(),sizeof(Record))==0,"Queried uniform bits differ");return actual; };
            const auto before=query();glViewport(GLint(i),0,1,1);glBegin(GL_QUADS);
            glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();const auto after=query();
            if (repeat || i) report<<',';
            report<<"{\"repeat\":"<<repeat<<",\"index\":"<<i<<",\"before\":";
            numbers(report,before.data(),7);report<<",\"after\":";numbers(report,after.data(),7);report<<'}';
        }
        for (int slot=0;slot<3;++slot) { auto& values=captures[repeat][slot];values.resize(inputs.size()*4);
            glReadBuffer(buffers[slot]);glReadPixels(0,0,GLsizei(inputs.size()),1,GL_RGBA,GL_FLOAT,values.data());
            raw(output/(std::string(repeat?"repeat-":"")+"slot"+std::to_string(slot)+".rgba32f"),values); }
        require(glGetError()==GL_NO_ERROR,"GL error during node capture");
    }
    bool finite=true,identical=true;report<<"],\"results\":[";
    for (int slot=0;slot<3;++slot) { identical=identical && std::memcmp(captures[0][slot].data(),captures[1][slot].data(),inputs.size()*16)==0;
        for (float value:captures[0][slot]) finite=finite && std::isfinite(value); }
    for (std::size_t i=0;i<inputs.size();++i) { if (i) report<<',';report<<"{\"index\":"<<i<<",\"slots\":[";
        for (int slot=0;slot<3;++slot) { if (slot) report<<',';numbers(report,captures[0][slot].data()+i*4,4); }report<<"]}"; }
    report<<"],\"repeatByteIdentical\":"<<(identical?"true":"false")<<",\"finiteOutputs\":"<<(finite?"true":"false")
        <<",\"mathAccepted\":false,\"waterMainExecuted\":false,\"physicalAccepted\":false,\"shippingAccepted\":false,"
        "\"scope\":\"Standalone literal math node, typed inputs and actual source capture only; independent numeric oracle is external. No cap/water-main/visibility/performance acceptance.\"}\n";
    write(output/"result.json",report.str());glDeleteProgram(program);glDeleteTextures(3,textures);glDeleteFramebuffers(1,&fbo);
    std::cout<<"EXPORTED standalone node "<<inputs.size()<<" inputs; independent oracle required\n";return finite&&identical?0:1;
}
int main(int argc,char** argv) {
    try {
        if (argc==3 && std::string(argv[1])=="--cpu-construction") {
            const auto source=fragment(read(argv[2]));
            std::cout<<"{\"schema\":\"aqualumen-snell-node-cpu-construction-v1\",\"glExecuted\":false,\"vertexSource\":"
                <<quote(vertex)<<",\"fragmentSource\":"<<quote(source)<<"}\n";
            return 0;
        }
        if (argc==4) {
            const std::uint32_t one=1;require(*reinterpret_cast<const unsigned char*>(&one)==1,"Little-endian host required");
            const auto bytes=read(argv[2]);const auto inputs=records(bytes);
            return render(read(argv[1]),bytes,inputs,argv[3]);
        }
        throw std::runtime_error("usage: --cpu-construction HELPER | HELPER SEVEN-FLOATS.f32 NEWOUTPUT");
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
