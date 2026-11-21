// Standalone same-Gaussian sampler, actual eight-MRT capture; no Iris claim.
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
namespace retainedSamplerGpu {
#include "water_snell_boundary_gpu.cpp"
}
namespace gpu=retainedSamplerGpu;
int main(int argc,char** argv){try {
    gpu::require(argc==4,"usage: water_conditioned_gpu FS INPUTS NEWOUTPUT");
    const std::filesystem::path out=argv[3];
    gpu::require(!std::filesystem::exists(out)&&!std::filesystem::is_symlink(out),"NEW output required");
    const std::string fs=gpu::read(argv[1]),input=gpu::read(argv[2]);
    gpu::require(input.size()==12*64*4*sizeof(float),"12x64 RGBA32F proposal texture required");
    gpu::Context context;
    std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gpu::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual NVIDIA RTX3080Ti required");
    GLuint program=glCreateProgram();
    for(auto stage:{std::pair<GLenum,std::string>{GL_VERTEX_SHADER,gpu::vertex},{GL_FRAGMENT_SHADER,fs}}){
        GLuint shader=gpu::shader(stage.first,stage.second);glAttachShader(program,shader);glDeleteShader(shader);}
    glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    if(!linked){char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(log);}
    gpu::require(std::filesystem::create_directory(out),"Cannot create NEW output");
    GLuint attached[2];GLsizei count=0;glGetAttachedShaders(program,2,&count,attached);
    gpu::require(count==2,"VS and FS attached");
    for(GLuint shader:attached){GLint type=0,length=0;glGetShaderiv(shader,GL_SHADER_TYPE,&type);
        glGetShaderiv(shader,GL_SHADER_SOURCE_LENGTH,&length);std::string actual(length,'\0');GLsizei used=0;
        glGetShaderSource(shader,length,&used,actual.data());actual.resize(used);
        gpu::require(actual==(type==GL_VERTEX_SHADER?gpu::vertex:fs),"Actual shader source differs");
        gpu::write(out/(type==GL_VERTEX_SHADER?"attached-vertex.glsl":"attached-fragment.glsl"),actual);}
    glUseProgram(program);const char* name="inputNodes";GLuint index;
    glGetUniformIndices(program,1,&name,&index);gpu::require(index!=GL_INVALID_INDEX,"Sampler active");
    GLint type=0,size=0,location=glGetUniformLocation(program,name);
    glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);
    glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&size);
    gpu::require(type==GL_SAMPLER_2D&&size==1&&location>=0,"Typed sampler required");
    glUniform1i(location,0);
    GLuint proposal;glGenTextures(1,&proposal);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,proposal);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,12,64,0,GL_RGBA,GL_FLOAT,input.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_BASE_LEVEL,0);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,0);
    auto queryInput=[&](const std::string& prefix){
        GLint binding=0,format=0,w=0,h=0,unit=-1;glGetUniformiv(program,location,&unit);
        glGetIntegerv(GL_TEXTURE_BINDING_2D,&binding);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        gpu::require(unit==0&&binding==int(proposal)&&format==GL_RGBA32F&&w==12&&h==64,"Actual bound input differs");
        std::vector<float> values(12*64*4);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,values.data());
        gpu::require(std::memcmp(values.data(),input.data(),input.size())==0,"Actual proposal input bits differ");
        gpu::raw(out/(prefix+"input.rgba32f"),values);
    };
    gpu::write(out/"inputs.f32",input);
    GLuint fbo,textures[8];glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glGenTextures(8,textures);
    GLenum buffers[8];
    glActiveTexture(GL_TEXTURE1);
    for(int slot=0;slot<8;++slot){buffers[slot]=GL_COLOR_ATTACHMENT0+slot;glBindTexture(GL_TEXTURE_2D,textures[slot]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,4,64,0,GL_RGBA,GL_FLOAT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        GLint format,w,h;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        gpu::require(format==GL_RGBA32F&&w==4&&h==64,"Actual output storage differs");
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[slot],GL_TEXTURE_2D,textures[slot],0);}
    glDrawBuffers(8,buffers);gpu::require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"Eight-MRT FBO complete");
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,proposal);
    for(auto cap:{GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,GL_DITHER,GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB})glDisable(cap);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glViewport(0,0,4,64);
    for(int repeat=0;repeat<2;++repeat){
        std::string prefix=repeat?"repeat-":"";queryInput(prefix+"before-");
        float zero[4]={};for(int slot=0;slot<8;++slot)glClearBufferfv(GL_COLOR,slot,zero);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        queryInput(prefix+"after-");
        for(int slot=0;slot<8;++slot){std::vector<float> values(4*64*4);glReadBuffer(buffers[slot]);
            glReadPixels(0,0,4,64,GL_RGBA,GL_FLOAT,values.data());
            gpu::raw(out/(prefix+"slot"+std::to_string(slot)+".rgba32f"),values);}
        gpu::require(glGetError()==GL_NO_ERROR,"GL capture error");}
    std::ostringstream report;report<<"{\"schema\":\"aqualumen-conditioned-sampler-gpu-v1\",\"renderer\":"<<gpu::quote(renderer)
        <<",\"GL\":"<<gpu::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"width\":4,\"height\":64,\"targetInternalFormat\":34836,\"sampler\":{\"type\":"<<type
        <<",\"size\":"<<size<<",\"location\":"<<location<<",\"unit\":0,\"width\":12,\"height\":64,\"format\":34836}"
        <<",\"waterMainExecuted\":false,\"IrisAccepted\":false,\"mathAccepted\":false,\"shippingAccepted\":false}\n";
    gpu::write(out/"result.json",report.str());
    glDeleteProgram(program);glDeleteTextures(8,textures);glDeleteTextures(1,&proposal);glDeleteFramebuffers(1,&fbo);
    std::cout<<"EXPORTED 256 proposal inputs, 2 branches, eight raw MRTs; independent audit required\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
