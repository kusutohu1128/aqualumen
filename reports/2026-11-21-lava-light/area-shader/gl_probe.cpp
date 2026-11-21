// The test reads receiver-relative vertices and writes one measured value per case.
#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
GLuint makeShader(GLenum stage,const std::string& source) {
    GLuint shader=glCreateShader(stage);
    const char* data=source.data();
    glShaderSource(shader,1,&data,nullptr);
    glCompileShader(shader);
    GLint ok=0;
    glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok) {
        char message[4096]{};
        glGetShaderInfoLog(shader,sizeof(message),nullptr,message);
        throw std::runtime_error(message);
    }
    return shader;
}
int main(int argc,char** argv) {
    if(argc!=2 && argc!=3) return 2;
    EGLDisplay display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if(!eglInitialize(display,nullptr,nullptr) || !eglBindAPI(EGL_OPENGL_API)) return 3;
    const EGLint cfgAttrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
    EGLConfig cfg; EGLint count=0;
    if(!eglChooseConfig(display,cfgAttrs,&cfg,1,&count)||!count) return 4;
    const EGLint ctxAttrs[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_NONE};
    EGLContext ctx=eglCreateContext(display,cfg,EGL_NO_CONTEXT,ctxAttrs);
    const EGLint surfaceAttrs[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
    EGLSurface surface=eglCreatePbufferSurface(display,cfg,surfaceAttrs);
    if(!eglMakeCurrent(display,surface,surface,ctx)) return 5;
    std::cerr<<glGetString(GL_RENDERER)<<" | "<<glGetString(GL_VERSION)<<"\n";
    std::ifstream file(argv[1]);
    if(!file) return 6;
    std::string lib((std::istreambuf_iterator<char>(file)), {});
    bool testPillar = argc == 3;
    if (testPillar) {
        std::ifstream pillar(argv[2]);
        if (!pillar) return 6;
        lib += "\n" + std::string(std::istreambuf_iterator<char>(pillar), {});
    }
    std::string source="#version 430 core\n"+lib+R"(
layout(local_size_x=1) in;
layout(std430,binding=0) readonly buffer Inputs { vec4 vertices[]; };
layout(std430,binding=1) writeonly buffer Results { float measured[]; };
)" + (testPillar ? R"(
void main() {
    uint id = gl_GlobalInvocationID.x, i = id * 6u;
    measured[id] = lavaIrradianceBehindBox(vertices[i].xyz, vertices[i+1u].xyz, vertices[i+2u].xyz,
        vertices[i+3u].xyz, vertices[i+4u].xyz, vertices[i+5u].xyz);
}
)" : R"(
void main() {
    uint id=gl_GlobalInvocationID.x, i=id*4u;
    measured[id]=lavaTriangleIrradiance(vertices[i].xyz,vertices[i+1u].xyz,vertices[i+2u].xyz,vertices[i+3u].xyz);
}
)");
    GLuint program=glCreateProgram();
    glAttachShader(program,makeShader(GL_COMPUTE_SHADER,source));
    glLinkProgram(program);GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) return 7;
    glUseProgram(program);
    std::vector<std::array<float,4>> vertices;
    std::array<float,4> v{};
    while(std::cin>>v[0]){
        if(!(std::cin>>v[1]>>v[2])) return 8;
        vertices.push_back(v);
    }
    const size_t stride = testPillar ? 6 : 4;
    if(vertices.empty() || vertices.size()%stride) return 9;
    std::vector<float> values(vertices.size()/stride);
    GLuint buffers[2];glGenBuffers(2,buffers);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[0]);
    glBufferData(GL_SHADER_STORAGE_BUFFER,vertices.size()*sizeof(v),vertices.data(),GL_STATIC_DRAW);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,buffers[0]);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[1]);
    glBufferData(GL_SHADER_STORAGE_BUFFER,values.size()*sizeof(float),nullptr,GL_DYNAMIC_READ);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,1,buffers[1]);
    glDispatchCompute(values.size(),1,1);
    glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);glFinish();
    glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,values.size()*sizeof(float),values.data());
    std::cout.precision(10);
    for(float value:values) std::cout<<value<<"\n";
    return glGetError()==GL_NO_ERROR ? 0 : 9;
}
