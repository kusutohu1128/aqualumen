// Literal TEST GLSL integration on NVIDIA; not original-water-MAIN acceptance.
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
namespace retainedSupportedGpu {
#include "water_snell_boundary_gpu.cpp"
}
namespace gpu=retainedSupportedGpu;
using Input=std::array<float,10>;
int main(int argc,char** argv) {try {
    gpu::require(argc==4,"usage: water_supported_glsl_gpu HELPER INPUTS NEW_OUTPUT");
    const std::filesystem::path out=argv[3];
    gpu::require(!std::filesystem::exists(out),"NEW output required");
    const std::string bytes=gpu::read(argv[2]),helper=gpu::read(argv[1]);
    gpu::require(!bytes.empty()&&bytes.size()%sizeof(Input)==0&&bytes.size()<=128*sizeof(Input),"1..128 whole records required");
    std::vector<Input> inputs(bytes.size()/sizeof(Input));std::memcpy(inputs.data(),bytes.data(),bytes.size());
    for(const auto& record:inputs)for(float a:record)gpu::require(std::isfinite(a),"Finite raw inputs required");
    gpu::Context context;
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gpu::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"RTX3080Ti required");
    const std::string fragment="#version 330 compatibility\n"+helper+
        "\nuniform vec3 stNormal,stView,stCov;uniform float stEta;\n"
        "void main(){WST_Context p=WST_prepare(stNormal,stView,stCov,stEta);"
        "vec3 result=WST_constantAir(p);gl_FragData[0]=vec4(result,float(p.valid));"
        "gl_FragData[1]=vec4(stNormal,1.0);gl_FragData[2]=vec4(stView,1.0);"
        "gl_FragData[3]=vec4(stCov,stEta);"
        "gl_FragData[4]=WST_kernel(p,vec3(0.2,0.15,sqrt(1.0-0.2*0.2-0.15*0.15)));"
        "gl_FragData[5]=vec4(WST_erfcPositive(0.0),WST_erfcPositive(0.7071067811865476),"
        "WST_erfcPositive(2.0),WST_erfcPositive(4.0));}\n";
    GLuint program=glCreateProgram();
    for(auto stage:{std::pair<GLenum,std::string>{GL_VERTEX_SHADER,gpu::vertex},{GL_FRAGMENT_SHADER,fragment}}){
        GLuint shader=gpu::shader(stage.first,stage.second);glAttachShader(program,shader);glDeleteShader(shader);}
    glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    if(!linked){char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(log);}
    gpu::require(std::filesystem::create_directory(out),"Cannot create output");
    gpu::write(out/"inputs.f32",bytes);gpu::write(out/"helper.glsl",helper);
    GLuint attached[2];GLsizei count=0;glGetAttachedShaders(program,2,&count,attached);gpu::require(count==2,"Two stages required");
    for(auto stage:attached){GLint type=0,length=0;glGetShaderiv(stage,GL_SHADER_TYPE,&type);glGetShaderiv(stage,GL_SHADER_SOURCE_LENGTH,&length);
        std::string actual(std::size_t(length),'\0');GLsizei used=0;glGetShaderSource(stage,length,&used,actual.data());actual.resize(used);
        gpu::require(actual==(type==GL_VERTEX_SHADER?gpu::vertex:fragment),"Actual attached source differs");
        gpu::write(out/(type==GL_VERTEX_SHADER?"attached-vertex.glsl":"attached-fragment.glsl"),actual);}
    const char* names[]={"stNormal","stView","stCov","stEta"};GLuint indices[4];GLint types[4],sizes[4],locations[4];
    glGetUniformIndices(program,4,names,indices);glGetActiveUniformsiv(program,4,indices,GL_UNIFORM_TYPE,types);
    glGetActiveUniformsiv(program,4,indices,GL_UNIFORM_SIZE,sizes);
    for(int i=0;i<4;++i){locations[i]=glGetUniformLocation(program,names[i]);
        gpu::require(indices[i]!=GL_INVALID_INDEX&&locations[i]>=0&&sizes[i]==1&&types[i]==(i==3?GL_FLOAT:GL_FLOAT_VEC3),"Typed input uniform mismatch");}
    GLuint textures[6],fbo;glGenTextures(6,textures);glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    GLenum buffers[6];
    for(int i=0;i<6;++i){buffers[i]=GL_COLOR_ATTACHMENT0+i;glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,inputs.size(),1,0,GL_RGBA,GL_FLOAT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        gpu::require(format==GL_RGBA32F&&w==int(inputs.size())&&h==1,"Actual target storage mismatch");
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[i],GL_TEXTURE_2D,textures[i],0);}
    glDrawBuffers(6,buffers);gpu::require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"Incomplete FBO");
    for(auto cap:{GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,GL_DITHER,GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB})glDisable(cap);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glUseProgram(program);
    std::array<std::array<std::vector<float>,6>,2> captures;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-supported-glsl-gpu-v1\",\"renderer\":"<<gpu::quote(renderer)
        <<",\"GL\":"<<gpu::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"width\":"<<inputs.size()<<",\"targetInternalFormat\":34836,\"uploads\":[";
    for(int repeat=0;repeat<2;++repeat){float zero[4]={};for(int i=0;i<6;++i)glClearBufferfv(GL_COLOR,i,zero);
        for(std::size_t i=0;i<inputs.size();++i){const auto& record=inputs[i];
            for(int j=0;j<3;++j)glUniform3fv(locations[j],1,record.data()+3*j);glUniform1f(locations[3],record[9]);
            auto query=[&](){Input actual;for(int j=0;j<3;++j)glGetUniformfv(program,locations[j],actual.data()+3*j);
                glGetUniformfv(program,locations[3],actual.data()+9);
                gpu::require(std::memcmp(actual.data(),record.data(),sizeof(Input))==0,"Queried raw uniform bits mismatch");return actual;};
            auto before=query();glViewport(i,0,1,1);glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();auto after=query();
            if(repeat||i)report<<',';report<<"{\"repeat\":"<<repeat<<",\"index\":"<<i<<",\"before\":";
            gpu::numbers(report,before.data(),10);report<<",\"after\":";gpu::numbers(report,after.data(),10);report<<'}';}
        for(int slot=0;slot<6;++slot){auto& values=captures[repeat][slot];values.resize(inputs.size()*4);glReadBuffer(buffers[slot]);
            glReadPixels(0,0,inputs.size(),1,GL_RGBA,GL_FLOAT,values.data());gpu::raw(out/(std::string(repeat?"repeat-":"")+"slot"+std::to_string(slot)+".rgba32f"),values);}
        gpu::require(glGetError()==GL_NO_ERROR,"GL error");}
    bool finite=true,identical=true;
    for(int slot=0;slot<6;++slot){identical=identical&&captures[0][slot]==captures[1][slot];for(float a:captures[0][slot])finite=finite&&std::isfinite(a);}
    report<<"],\"repeatByteIdentical\":"<<(identical?"true":"false")<<",\"finiteOutputs\":"<<(finite?"true":"false")
        <<",\"waterMainExecuted\":false,\"mathAccepted\":false,\"IrisAccepted\":false,\"visualAccepted\":false,\"shippingAccepted\":false}\n";
    gpu::write(out/"result.json",report.str());
    glDeleteProgram(program);glDeleteTextures(6,textures);glDeleteFramebuffers(1,&fbo);
    std::cout<<"EXPORTED supported GLSL "<<inputs.size()<<" inputs; independent audit required\n";return finite&&identical?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
