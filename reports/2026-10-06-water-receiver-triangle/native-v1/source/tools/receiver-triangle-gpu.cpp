// Standalone saved actual Iris VS / owned pass-through fragment interpolation.
// Not original terrain fragment shading, actual live index binding or game timing.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <stdexcept>
#include <cstring>
#include <cmath>
#include <cstdint>

template<class T> T read(std::ifstream& in) {
    T value;in.read(reinterpret_cast<char*>(&value),sizeof(value));
    if(!in) throw std::runtime_error("Truncated fixture");return value;
}
GLuint shader(GLenum type,const std::string& source) {
    GLuint id=glCreateShader(type);const char* p=source.c_str();glShaderSource(id,1,&p,nullptr);glCompileShader(id);
    GLint ok;glGetShaderiv(id,GL_COMPILE_STATUS,&ok);
    if(!ok) {char log[16384];glGetShaderInfoLog(id,sizeof(log),nullptr,log);throw std::runtime_error(log);}return id;
}
struct Face {uint32_t axis;std::array<float,3> origin;std::array<uint32_t,20> words;};
struct Point {uint32_t face;float s,t;};
int main(int argc,char** argv) {
    try {
        if(argc!=4 || std::filesystem::exists(argv[3])) throw std::runtime_error("New output required: source input output");
        const uint32_t native=1;if(*reinterpret_cast<const uint8_t*>(&native)!=1) throw std::runtime_error("Little endian required");
        std::ifstream vs(argv[1]);std::string source((std::istreambuf_iterator<char>(vs)),{});
        std::ifstream in(argv[2],std::ios::binary);
        if(source.empty() || read<uint32_t>(in)!=0x41515431 || read<uint32_t>(in)!=14) throw std::runtime_error("Actual fixture scope rejected");
        uint32_t points=read<uint32_t>(in);if(points!=58) throw std::runtime_error("Exact 58-point fixture required");
        std::array<float,16> light;std::array<float,2> shrink;
        for(auto& f:light) f=read<float>(in);for(auto& f:shrink) f=read<float>(in);
        std::array<Face,14> faces;
        std::vector<uint32_t> vertices(56*7,0),indices(84),wrong(84);
        for(size_t f=0;f<14;f++) {
            auto& face=faces[f];face.axis=read<uint32_t>(in);if(face.axis>2) throw std::runtime_error("Invalid face axis");
            for(auto& x:face.origin) x=read<float>(in);for(auto& w:face.words) w=read<uint32_t>(in);
            for(size_t v=0;v<4;v++) for(size_t w=0;w<5;w++) vertices[(f*4+v)*7+w]=face.words[v*5+w];
        }
        const uint32_t pattern[6]={0,1,2,2,3,0},alternative[6]={1,2,3,3,0,1};
        for(size_t i=0;i<84;i++) {
            indices[i]=read<uint32_t>(in);
            if(indices[i]!=4*(i/6)+pattern[i%6]) throw std::runtime_error("Actual installed index generator differs");
            wrong[i]=4*(i/6)+alternative[i%6];
        }
        std::vector<Point> queries(points);
        for(auto& p:queries) {
            p.face=read<uint32_t>(in);p.s=read<float>(in);p.t=read<float>(in);
            if(p.face>=14 || !std::isfinite(p.s) || !std::isfinite(p.t) || p.s<0 || p.s>1 || p.t<0 || p.t>1) throw std::runtime_error("Point scope rejected");
        }
        if(in.peek()!=EOF) throw std::runtime_error("Fixture extent changed");
        auto getPlatform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        if(!getPlatform) throw std::runtime_error("EGL platform extension missing");
        EGLDisplay display=getPlatform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
            EGLDeviceEXT devices[8];EGLint count=0;
            if(!query || !query(8,devices,&count) || !count) throw std::runtime_error("No EGL device");
            display=getPlatform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("EGL device unavailable");
        }
        if(!eglBindAPI(EGL_OPENGL_API)) throw std::runtime_error("GL API unavailable");
        EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count;eglChooseConfig(display,cfg,&config,1,&count);
        if(count!=1) throw std::runtime_error("No EGL config");
        EGLint size[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};auto surface=eglCreatePbufferSurface(display,config,size);
        EGLint attrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        auto context=eglCreateContext(display,config,EGL_NO_CONTEXT,attrs);
        if(context==EGL_NO_CONTEXT || !eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("No GL context");
        std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
        if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Actual NVIDIA required");
        std::cout<<"Renderer: "<<renderer<<"\nGL: "<<glGetString(GL_VERSION)<<"\nSubpixel bits: ";
        GLint subpixels;glGetIntegerv(GL_SUBPIXEL_BITS,&subpixels);std::cout<<subpixels<<"\n";
        const std::string fragment="#version 150\nin vec2 uv;in vec2 lightmap;in vec4 vertexColor;out vec4 attributes0;out vec4 attributes1;void main(){attributes0=vec4(uv,lightmap);attributes1=vertexColor;}\n";
        GLuint v=shader(GL_VERTEX_SHADER,source),f=shader(GL_FRAGMENT_SHADER,fragment),program=glCreateProgram();
        glAttachShader(program,v);glAttachShader(program,f);
        glBindAttribLocation(program,0,"a_Position");glBindAttribLocation(program,1,"a_Color");
        glBindAttribLocation(program,2,"a_TexCoord");glBindAttribLocation(program,3,"a_LightAndData");
        glBindFragDataLocation(program,0,"attributes0");glBindFragDataLocation(program,1,"attributes1");glLinkProgram(program);
        GLint linked;glGetProgramiv(program,GL_LINK_STATUS,&linked);
        if(!linked) {char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(log);}
        glDeleteShader(v);glDeleteShader(f);glUseProgram(program);
        auto uniform=[&](const char* name){GLint loc=glGetUniformLocation(program,name);if(loc<0) throw std::runtime_error(std::string("Required actual VS uniform absent: ")+name);return loc;};
        glUniformMatrix4fv(uniform("iris_LightmapTextureMatrix"),1,GL_FALSE,light.data());
        glUniform2fv(uniform("u_TexCoordShrink"),1,shrink.data());
        GLuint vao,vbo,ebo;glGenVertexArrays(1,&vao);glBindVertexArray(vao);
        glGenBuffers(1,&vbo);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,vertices.size()*4,vertices.data(),GL_STATIC_DRAW);
        for(int i=0;i<4;i++) glEnableVertexAttribArray(i);
        glVertexAttribIPointer(0,2,GL_UNSIGNED_INT,28,(void*)0);glVertexAttribPointer(1,4,GL_UNSIGNED_BYTE,GL_TRUE,28,(void*)8);
        glVertexAttribIPointer(2,2,GL_UNSIGNED_SHORT,28,(void*)12);glVertexAttribIPointer(3,4,GL_UNSIGNED_BYTE,28,(void*)16);
        glGenBuffers(1,&ebo);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ebo);
        GLuint framebuffer,textures[2];glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glGenTextures(2,textures);
        constexpr int extent=1024,pixel=512;
        for(int i=0;i<2;i++) {
            glBindTexture(GL_TEXTURE_2D,textures[i]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,extent,extent,0,GL_RGBA,GL_FLOAT,nullptr);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,textures[i],0);
        }
        GLenum buffers[2]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,buffers);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Incomplete owned FBO");
        glViewport(0,0,extent,extent);glEnable(GL_SCISSOR_TEST);glScissor(pixel,pixel,1,1);
        glDisable(GL_CULL_FACE);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_DITHER);glDisable(GL_FRAMEBUFFER_SRGB);
        std::vector<float> output;output.reserve(points*4*8);
        constexpr float ndc=2.0f*(pixel+.5f)/extent-1.0f;
        for(int diagonal=0;diagonal<2;diagonal++) {
            auto& selected=diagonal?wrong:indices;glBufferData(GL_ELEMENT_ARRAY_BUFFER,selected.size()*4,selected.data(),GL_STATIC_DRAW);
            for(int projection=0;projection<2;projection++) for(auto& p:queries) {
                const auto& face=faces[p.face];auto axis=face.axis,saxis=(axis+1)%3,taxis=(axis+2)%3;
                uint32_t section=face.words[4]>>24;
                float translation[3]={float(((section>>5)&7)*16),float((section&3)*16),float(((section>>2)&7)*16)};
                glUniform3f(uniform("u_RegionOffset"),-face.origin[0]-translation[0],-face.origin[1]-translation[1],-face.origin[2]-translation[2]);
                std::array<float,16> model{};model[saxis*4]=1;model[taxis*4+1]=1;model[15]=1;
                glUniformMatrix4fv(uniform("iris_ModelViewMatrix"),1,GL_FALSE,model.data());
                float ks=projection?.4f:0,kt=projection?.25f:0;
                std::array<float,16> project{};project[0]=2+ndc*ks;project[4]=ndc*kt;project[12]=-2*p.s+ndc;
                project[1]=ndc*ks;project[5]=2+ndc*kt;project[13]=-2*p.t+ndc;project[3]=ks;project[7]=kt;project[15]=1;
                glUniformMatrix4fv(uniform("iris_ProjectionMatrix"),1,GL_FALSE,project.data());
                const float unset[4]={-17,-17,-17,-17};glClearBufferfv(GL_COLOR,0,unset);glClearBufferfv(GL_COLOR,1,unset);
                glDrawElements(GL_TRIANGLES,6,GL_UNSIGNED_INT,(void*)(uintptr_t(p.face*6*4)));
                for(int attachment=0;attachment<2;attachment++) {
                    float values[4];glReadBuffer(buffers[attachment]);glReadPixels(pixel,pixel,1,1,GL_RGBA,GL_FLOAT,values);
                    for(float x:values) {if(!std::isfinite(x) || x==-17) throw std::runtime_error("Missing/nonfinite owned fragment");output.push_back(x);}
                }
                if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Actual interpolation GL error");
            }
        }
        std::ofstream out(argv[3],std::ios::binary);out.write(reinterpret_cast<const char*>(output.data()),output.size()*sizeof(float));
        if(!out) throw std::runtime_error("Output write failed");
        std::cout<<"Captured "<<output.size()<<" floats: original and deliberate opposite diagonal, orthographic and projective\n";
        glDeleteFramebuffers(1,&framebuffer);glDeleteTextures(2,textures);glDeleteBuffers(1,&vbo);glDeleteBuffers(1,&ebo);
        glDeleteVertexArrays(1,&vao);glDeleteProgram(program);
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
    }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
