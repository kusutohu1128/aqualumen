// TEST ONLY. Parent/root owns native GL execution. Compilation is CPU-only.
// Reuse frozen expansion/compiler helpers, not the old executable/main path.
#define main aqualumenFrozenGlcheckMain
#include "glcheck.cpp"
#undef main
#include "water_tessellation_contract.h"
#include <cstddef>
#include <cstring>
#include <limits>
#include <regex>

namespace waterTessellationProbe {
constexpr int width=65, height=65, outputs=7;
bool artifactCreated=false;
constexpr double colourAbs=5e-4, colourRel=2e-4, fieldAbs=5e-5, fieldRel=2e-5, depthAbs=2e-6;
using M4=std::array<float,16>;
constexpr M4 identity={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
constexpr M4 view={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
constexpr M4 inverseView={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
void require(bool value,const std::string& message) {
    if(!value) throw std::runtime_error("INCONCLUSIVE water-tessellation: "+message);
}
void glOkay(const std::string& where) {
    const auto error=glGetError();
    require(error==GL_NO_ERROR,where+" GL error "+std::to_string(error));
}
std::string readText(const fs::path& path) {
    std::ifstream input(path,std::ios::binary);require(bool(input),"cannot read "+path.string());
    return {std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>()};
}
void writeText(const fs::path& path,const std::string& value) {
    std::ofstream output(path,std::ios::binary);require(bool(output),"cannot write "+path.string());
    output<<value;require(bool(output),"write failed "+path.string());
}
void writeRaw(const fs::path& path,const std::vector<float>& values) {
    std::ofstream output(path,std::ios::binary);require(bool(output),"cannot write "+path.string());
    output.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()*sizeof(float)));
    require(bool(output),"write failed "+path.string());
}
std::string quoted(const std::string& value) {
    std::ostringstream result;result<<'"';
    for(unsigned char c:value) {
        if(c=='"'||c=='\\') result<<'\\'<<c;
        else if(c<' ') result<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;
        else result<<c;
    }
    result<<'"';return result.str();
}
// These stores observe the original main's FINAL nonwater/water outputs.
// They override diagnostic slots only in a separate observer draw. No optics,
// wave/helper invocation, derivatives, normal or branch is re-evaluated.
std::string observedFS(const std::string& original,bool tessellated) {
    const std::string begin="\n// WATER_TESS_NATIVE_FIELDS_BEGIN\n",end="// WATER_TESS_NATIVE_FIELDS_END\n";
    require(original.find(begin)==std::string::npos,"observer marker already present");
    auto source=original;
    const auto add=[&](const std::string& anchor,bool water) {
        const auto at=source.find(anchor);
        require(at!=std::string::npos&&source.find(anchor,at+anchor.size())==std::string::npos,"final STORE absent/ambiguous");
        const std::string stores=
            "    gl_FragData[1]=vec4(uv,lightmap);\n"
            "    gl_FragData[2]=vertexColor;\n"
            "    gl_FragData[3]=vec4(worldNormal,waterMeanSurfaceY);\n"
            "    gl_FragData[4]=vec4(worldPosition,waterUnknownWeight);\n"
            "    gl_FragData[5]=vec4(materialId,1.0,0.0,1.0);\n"
            "    gl_FragData[6]="+std::string(tessellated&&water?"tessStageCoord":"vec4(0.0)")+";\n";
        // Generated atlas stores immediately after C0 must execute first;
        // append immediately before the existing return/end of main instead.
        auto insertion=at+anchor.size();
        if(tessellated) {
            const auto terminator=source.find(water?"\n}":"        return;",insertion);
            require(terminator!=std::string::npos,"generated final STORE terminator absent");
            insertion=terminator;
        }
        source.insert(insertion,begin+stores+end);
    };
    add("        gl_FragData[0]=vec4(lit,tex.a);\n",false);
    add("    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n",true);
    auto recovered=source;
    for(auto at=recovered.find(begin);at!=std::string::npos;at=recovered.find(begin)) {
        const auto finish=recovered.find(end,at);require(finish!=std::string::npos,"unterminated observer STORE");
        recovered.erase(at,finish+end.size()-at);
    }
    require(recovered==original,"STORE removal does not recover byte-identical expanded main");
    return source;
}

struct Context {
    EGLDisplay display=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;
    Context() {
        const auto platform=reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
        require(platform,"EGL platform display API unavailable");
        display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            const auto query=reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
            EGLDeviceEXT devices[8];EGLint count=0;
            require(query&&query(8,devices,&count)&&count>0,"no EGL device");
            display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            require(eglInitialize(display,nullptr,nullptr),"EGL device initialization failed");
        }
        require(eglBindAPI(EGL_OPENGL_API),"EGL OpenGL API bind failed");
        EGLint configAttrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,
            EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count=0;
        require(eglChooseConfig(display,configAttrs,&config,1,&count)&&count>0,"no EGL GL pbuffer config");
        EGLint surfaceAttrs[]={EGL_WIDTH,width,EGL_HEIGHT,height,EGL_NONE};
        surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,0,
            EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        require(surface!=EGL_NO_SURFACE&&context!=EGL_NO_CONTEXT&&eglMakeCurrent(display,surface,surface,context),
            "cannot create native GL 4.0 compatibility context (not an Iris context test)");
    }
    ~Context() {
        if(display!=EGL_NO_DISPLAY) {
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
            if(context!=EGL_NO_CONTEXT) eglDestroyContext(display,context);
            if(surface!=EGL_NO_SURFACE) eglDestroySurface(display,surface);
            eglTerminate(display);
        }
    }
};
struct Program {
    GLuint id=0;std::vector<GLuint> stages;std::string name;bool tessellated=false;
    Program(const std::string& label,const std::vector<std::pair<GLenum,std::string>>& sources,bool tess)
        :name(label),tessellated(tess) {
        id=glCreateProgram();
        for(const auto& source:sources) {
            const auto stage=compile(source.first,source.second,label+"-"+std::to_string(source.first));
            stages.push_back(stage);glAttachShader(id,stage);
        }
        glBindAttribLocation(id,10,"mc_Entity");glLinkProgram(id);
        GLint linked=0;glGetProgramiv(id,GL_LINK_STATUS,&linked);
        if(!linked) {char log[16384]={};glGetProgramInfoLog(id,sizeof(log),nullptr,log);throw std::runtime_error(label+": "+log);}
        require(glGetAttribLocation(id,"mc_Entity")==10,"material input location not pinned");
    }
    ~Program(){for(auto stage:stages)glDeleteShader(stage);if(id)glDeleteProgram(id);}
    Program(const Program&)=delete;Program& operator=(const Program&)=delete;
    std::string reflection() const {
        GLint linked=0,count=0;glGetProgramiv(id,GL_LINK_STATUS,&linked);glGetProgramiv(id,GL_ATTACHED_SHADERS,&count);
        std::vector<GLuint> attached(std::size_t(count),0);GLsizei actual=0;
        glGetAttachedShaders(id,count,&actual,attached.data());
        require(linked==GL_TRUE&&actual==GLsizei(tessellated?4:2),"actual attached/link stage count differs");
        std::vector<GLenum> types;std::ostringstream json;
        json<<"{\"name\":"<<quoted(name)<<",\"linked\":true,\"attached_stage_types\":[";
        for(int i=0;i<actual;++i) {GLint type=0,compiled=0;glGetShaderiv(attached[i],GL_SHADER_TYPE,&type);
            glGetShaderiv(attached[i],GL_COMPILE_STATUS,&compiled);require(compiled==GL_TRUE,"attached stage not compiled");
            types.push_back(GLenum(type));if(i)json<<',';json<<type;}
        std::sort(types.begin(),types.end());auto expected=std::vector<GLenum>{GL_VERTEX_SHADER,GL_FRAGMENT_SHADER};
        if(tessellated){expected.push_back(GL_TESS_CONTROL_SHADER);expected.push_back(GL_TESS_EVALUATION_SHADER);}
        std::sort(expected.begin(),expected.end());require(types==expected,"actual attached shader types differ");
        json<<"]";
        if(tessellated) {
            const std::array<std::pair<GLenum,GLint>,5> queries={{{GL_TESS_CONTROL_OUTPUT_VERTICES,3},
                {GL_TESS_GEN_MODE,GL_TRIANGLES},{GL_TESS_GEN_SPACING,GL_EQUAL},
                {GL_TESS_GEN_VERTEX_ORDER,GL_CCW},{GL_TESS_GEN_POINT_MODE,GL_FALSE}}};
            json<<",\"tessellation_reflection\":[";
            for(std::size_t i=0;i<queries.size();++i){GLint observed=0;glGetProgramiv(id,queries[i].first,&observed);
                require(observed==queries[i].second,"linked tessellation layout differs");
                if(i)json<<',';
                json<<"{\"pname\":"<<queries[i].first<<",\"value\":"<<observed<<'}';}
            json<<']';
        }
        json<<'}';glOkay("linked-stage reflection");return json.str();
    }
};

struct Vertex {float position[3],normal[3],color[4],uv[2],lightmap[2],material;};
struct Case {
    std::string name;float cameraY=63,planeY=3.25f,surfaceY=3.25f,depth=4,normalY=1,material=10000;
    bool reverse=false,unknown=false,mixed=false;int eyeWater=1;
};
std::vector<Vertex> vertices(const Case& input) {
    const std::array<std::array<float,2>,4> xz={{{-.9f,-.9f},{-.9f,.9f},{.9f,.9f},{.9f,-.9f}}};
    const std::array<int,6> forward={0,1,2,0,2,3},back={0,3,2,0,2,1};
    std::vector<Vertex> result;
    for(int corner:input.reverse?back:forward) {
        Vertex vertex={{xz[corner][0],input.planeY,xz[corner][1]},{0,input.normalY,0},
            {.6f+.08f*corner,.9f-.05f*corner,.7f+.03f*corner,1.0f},
            {float(corner==2||corner==3),float(corner==1||corner==2)},
            {.12f+.07f*corner,.72f+.06f*corner},input.material};
        result.push_back(vertex);
    }
    return result;
}
struct Capture {std::array<std::vector<float>,outputs> image;std::vector<float> depth;GLuint64 primitives=0;};
struct Fixture {
    std::array<GLuint,8> samplers={};std::array<GLuint,outputs> targets={};
    GLuint framebuffer=0,depthTarget=0,vertexBuffer=0,query=0;
    M4 projection={},inverseProjection={};
    Fixture() {
        glGenTextures(GLsizei(samplers.size()),samplers.data());glGenTextures(outputs,targets.data());
        glGenTextures(1,&depthTarget);glGenFramebuffers(1,&framebuffer);glGenBuffers(1,&vertexBuffer);glGenQueries(1,&query);
        const float focal=float(1/std::tan(3.14159265358979323846/6)),near=.01f,far=128;
        const float a=-(far+near)/(far-near),b=-2*far*near/(far-near);
        projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};
        inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,0,1/b,0,0,-1,a/b};
        glPixelStorei(GL_PACK_ALIGNMENT,4);glPixelStorei(GL_UNPACK_ALIGNMENT,4);
        for(GLenum p:{GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS})glPixelStorei(p,0);
        glPixelStorei(GL_PACK_SWAP_BYTES,GL_FALSE);glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
        const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadow=1;
        std::vector<float> colour(width*height*4,0),depth(width*height,1),sky(64*32*4,0);
        for(int p=0;p<width*height;++p){colour[p*4]=.03f;colour[p*4+1]=.04f;colour[p*4+2]=.05f;colour[p*4+3]=1;}
        for(int y=0;y<32;++y)for(int x=0;x<64;++x){const int p=(y*64+x)*4;sky[p+3]=1;for(int c=0;c<3;++c)sky[p+c]=y<31?.04f:0;}
        allocate(samplers[0],GL_RGBA32F,1,1,GL_RGBA,white);
        allocate(samplers[1],GL_RGBA32F,width,height,GL_RGBA,colour.data());
        allocate(samplers[2],GL_RGBA16F,64,32,GL_RGBA,sky.data());
        allocate(samplers[3],GL_DEPTH_COMPONENT32F,width,height,GL_DEPTH_COMPONENT,depth.data());
        allocate(samplers[4],GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        allocate(samplers[5],GL_RGBA16F,1,1,GL_RGBA,black);
        allocate(samplers[7],GL_RGBA16F,64,32,GL_RGBA,sky.data());
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        for(int i=0;i<outputs;++i){allocate(targets[i],GL_RGBA32F,width,height,GL_RGBA,nullptr);
            glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,targets[i],0);}
        allocate(depthTarget,GL_DEPTH_COMPONENT32F,width,height,GL_DEPTH_COMPONENT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,depthTarget,0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"seven-target depth framebuffer incomplete");
        for(GLenum cap:{GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,
            GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,
            GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE,GL_MULTISAMPLE})glDisable(cap);
        glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_TRUE);glDepthRange(0,1);
        glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
        glProvokingVertex(GL_LAST_VERTEX_CONVENTION);glPatchParameteri(GL_PATCH_VERTICES,3);
        GLint patch=0,provoking=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);glGetIntegerv(GL_PROVOKING_VERTEX,&provoking);
        require(patch==3&&provoking==GL_LAST_VERTEX_CONVENTION,"patch arity/provoking-vertex state differs");
        glViewport(0,0,width,height);glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());
        glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view.data());
        for(int unit=0;unit<2;++unit){glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glLoadIdentity();}
        glMatrixMode(GL_MODELVIEW);glOkay("fixture allocation/state");
    }
    ~Fixture() {
        glDeleteQueries(1,&query);glDeleteBuffers(1,&vertexBuffer);glDeleteFramebuffers(1,&framebuffer);
        glDeleteTextures(1,&depthTarget);glDeleteTextures(outputs,targets.data());glDeleteTextures(GLsizei(samplers.size()),samplers.data());
    }
    static void allocate(GLuint texture,GLenum format,int w,int h,GLenum channel,const float* data) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,texture);
        for(GLenum p:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,p,GL_NEAREST);
        for(GLenum p:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,p,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,GLint(format),w,h,0,channel,GL_FLOAT,data);
    }
    void inputs(const Case& input,const fs::path& directory) {
        const auto data=vertices(input);glBindBuffer(GL_ARRAY_BUFFER,vertexBuffer);
        glBufferData(GL_ARRAY_BUFFER,GLsizeiptr(data.size()*sizeof(Vertex)),data.data(),GL_STATIC_DRAW);
        // Save the one immutable upload shared by every program/draw in this case.
        std::vector<float> actual(data.size()*sizeof(Vertex)/sizeof(float),0),expected(actual.size(),0);
        std::memcpy(expected.data(),data.data(),data.size()*sizeof(Vertex));
        glGetBufferSubData(GL_ARRAY_BUFFER,0,GLsizeiptr(data.size()*sizeof(Vertex)),actual.data());
        require(actual==expected,"immutable VBO readback differs");writeRaw(directory/"uploaded-vertices.f32",actual);
        glEnableClientState(GL_VERTEX_ARRAY);glVertexPointer(3,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,position)));
        glEnableClientState(GL_NORMAL_ARRAY);glNormalPointer(GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,normal)));
        glEnableClientState(GL_COLOR_ARRAY);glColorPointer(4,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,color)));
        glClientActiveTexture(GL_TEXTURE0);glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,uv)));
        glClientActiveTexture(GL_TEXTURE1);glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,lightmap)));
        glEnableVertexAttribArray(10);glVertexAttribPointer(10,1,GL_FLOAT,GL_FALSE,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,material)));
        std::vector<float> bathymetry(64*64*4,0);
        for(int z=0;z<64;++z)for(int x=0;x<64;++x){const int p=(z*64+x)*4;
            bathymetry[p]=input.depth;bathymetry[p+1]=input.surfaceY;
            bathymetry[p+2]=input.unknown||(input.mixed&&z>=33)?0.0f:1.0f;}
        allocate(samplers[6],GL_RGBA32F,64,64,GL_RGBA,bathymetry.data());
        GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        require(format==GL_RGBA32F&&w==64&&h==64,"typed bathymetry storage differs");
        auto readback=bathymetry;std::fill(readback.begin(),readback.end(),std::numeric_limits<float>::quiet_NaN());
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,readback.data());
        require(readback==bathymetry,"typed bathymetry byte-equivalent scalar readback differs");
        writeRaw(directory/"actual-bathymetry.rgba32f",readback);glOkay("immutable vertex/map upload");
    }
    void uniforms(const Program& program,const Case& input) {
        glUseProgram(program.id);
        const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
        for(int unit=0;unit<8;++unit){const GLint location=glGetUniformLocation(program.id,names[unit]);
            require(location>=0,"required sampler inactive: "+std::string(names[unit]));glUniform1i(location,unit);
            glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,samplers[unit]);glBindSampler(unit,0);}
        for(const auto& item:std::array<std::pair<const char*,M4>,6>{{{"gbufferProjection",projection},{"gbufferProjectionInverse",inverseProjection},
            {"gbufferModelView",view},{"gbufferModelViewInverse",inverseView},{"shadowProjection",identity},{"shadowModelView",identity}}})
            glUniformMatrix4fv(glGetUniformLocation(program.id,item.first),1,GL_FALSE,item.second.data());
        glUniform3f(glGetUniformLocation(program.id,"cameraPosition"),0,input.cameraY,0);
        glUniform3f(glGetUniformLocation(program.id,"sunPosition"),0,0,-1);glUniform3f(glGetUniformLocation(program.id,"shadowLightPosition"),0,0,-1);
        glUniform1f(glGetUniformLocation(program.id,"viewWidth"),width);glUniform1f(glGetUniformLocation(program.id,"viewHeight"),height);
        glUniform1f(glGetUniformLocation(program.id,"far"),128);glUniform1f(glGetUniformLocation(program.id,"frameTimeCounter"),120);
        glUniform1i(glGetUniformLocation(program.id,"isEyeInWater"),input.eyeWater);glUniform1i(glGetUniformLocation(program.id,"aqualumenDimension"),0);
        glUniform1i(glGetUniformLocation(program.id,"aqualumenActive"),0);glUniform4f(glGetUniformLocation(program.id,"aqualumenGrid"),-32,-32,64,input.surfaceY);
        require(glGetUniformLocation(program.id,"aqualumenBathymetryReady")>=0&&glGetUniformLocation(program.id,"aqualumenBathymetryGrid")>=0,"active bathymetry contract absent");
        glUniform1i(glGetUniformLocation(program.id,"aqualumenBathymetryReady"),1);
        glUniform4f(glGetUniformLocation(program.id,"aqualumenBathymetryGrid"),-32,-32,64,input.surfaceY);
        glUniform1f(glGetUniformLocation(program.id,"rainStrength"),0);glUniform1f(glGetUniformLocation(program.id,"wetness"),0);
        glUniform1i(glGetUniformLocation(program.id,"worldTime"),6000);glUniform2i(glGetUniformLocation(program.id,"eyeBrightnessSmooth"),0,240);
        GLint unit=-1,bound=0,sampler=-1;glGetUniformiv(program.id,glGetUniformLocation(program.id,"aqualumenBathymetry"),&unit);
        glActiveTexture(GL_TEXTURE6);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);
        require(unit==6&&GLuint(bound)==samplers[6]&&sampler==0,"actual typed-map sampler binding differs");glOkay("shared sampler/uniform inputs");
    }
    Capture draw(const Program& program,const Case& input,bool observed,const fs::path& directory,const std::string& label) {
        uniforms(program,input);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        std::array<GLenum,outputs> drawBuffers={};for(int i=0;i<outputs;++i)drawBuffers[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(outputs,drawBuffers.data());const float zero[4]={};const float one=1;
        for(int i=0;i<outputs;++i)glClearBufferfv(GL_COLOR,i,zero);
        glClearBufferfv(GL_DEPTH,0,&one);
        // Original FS writes only C0. Pure tess pack writes C0,C9..C12.
        const int count=observed?outputs:(program.tessellated?5:1);glDrawBuffers(count,drawBuffers.data());
        const GLenum mode=program.tessellated?GL_PATCHES:GL_TRIANGLES;
        glBeginQuery(GL_PRIMITIVES_GENERATED,query);glDrawArrays(mode,0,6);glEndQuery(GL_PRIMITIVES_GENERATED);
        Capture capture;glGetQueryObjectui64v(query,GL_QUERY_RESULT,&capture.primitives);
        require(capture.primitives==2,"level-one generated primitive count must equal two input triangles");
        for(int i=0;i<outputs;++i){capture.image[i].assign(width*height*4,std::numeric_limits<float>::quiet_NaN());
            glReadBuffer(drawBuffers[i]);glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,capture.image[i].data());
            for(float value:capture.image[i])require(std::isfinite(value),"nonfinite actual colour/field readback");
            writeRaw(directory/(label+"-slot"+std::to_string(i)+".rgba32f"),capture.image[i]);}
        capture.depth.assign(width*height,std::numeric_limits<float>::quiet_NaN());
        glReadPixels(0,0,width,height,GL_DEPTH_COMPONENT,GL_FLOAT,capture.depth.data());
        for(float value:capture.depth)require(std::isfinite(value),"nonfinite depth readback");
        writeRaw(directory/(label+"-depth.f32"),capture.depth);glOkay("native "+label+" draw/readback");return capture;
    }
};

bool compare(std::ostringstream& report,const std::string& name,const std::vector<float>& a,
    const std::vector<float>& b,double abs,double rel,bool& first) {
    const auto result=aqualumenWaterTessellation::compareSamples(a,b,abs,rel);
    if(!first)report<<',';
    first=false;
    report<<"{\"name\":"<<quoted(name)<<",\"accepted\":"<<(result.accepted()?"true":"false")
        <<",\"finite_and_same_shape\":"<<(result.valid?"true":"false")<<",\"scalar_samples\":"<<result.samples
        <<",\"outside_bound\":"<<result.outside<<",\"maximum_absolute_delta\":"<<result.maximumAbsolute
        <<",\"absolute_tolerance\":"<<abs<<",\"relative_tolerance\":"<<rel<<'}';
    return result.accepted();
}
std::vector<float> channels(const Capture& capture,int slot,std::initializer_list<int> components,
    const std::vector<int>& covered) {
    std::vector<float> result;for(int p:covered)for(int c:components)result.push_back(capture.image[slot][p*4+c]);return result;
}

int run(const fs::path& generated,const fs::path& original,const fs::path& artifacts) {
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required, preserve previous evidence");
    require(fs::is_directory(generated)&&fs::is_directory(original),"shader roots required");
    const auto metadata=readText(generated.parent_path()/"WATER-TESSELLATION-PROBE.json");
    require(metadata.find("aqualumen-water-tessellation-probe-v1")!=std::string::npos,"generated pack schema differs");
    require(std::regex_search(metadata,std::regex("\"level\"\\s*:\\s*1\\s*[,}]")),"only level-one integration is approved");
    require(std::regex_search(metadata,std::regex("\"fixed_phase_seconds\"\\s*:\\s*120\\.0\\s*[,}]")),"fixture pins analytic phase120");
    const auto ovs=expand(original/"gbuffers_water.vsh",generated),ofs=expand(original/"gbuffers_water.fsh",generated);
    const auto tvs=expand(generated/"gbuffers_water.vsh",generated),tcs=expand(generated/"gbuffers_water.tcs",generated);
    const auto tes=expand(generated/"gbuffers_water.tes",generated),tfs=expand(generated/"gbuffers_water.fsh",generated);
    for(const auto* source:{&ovs,&ofs,&tvs,&tfs})require(source->find("#define frameTimeCounter 120.0\n")!=std::string::npos,
        "same generated fixed-phase include root not present in every paired VS/FS");
    require(tcs.find("flat in float tessVertex_materialId[];")!=std::string::npos&&
        tcs.find("flat out float tessControl_materialId[];")!=std::string::npos&&
        tes.find("flat in float tessControl_materialId[];")!=std::string::npos,"qualifier-corrected v2 material chain required");
    const auto oobserved=observedFS(ofs,false),tobserved=observedFS(tfs,true);
    require(fs::create_directories(artifacts),"artifact directory creation failed; preserve previous evidence");
    artifactCreated=true;
    writeText(artifacts/"pack-metadata.json",metadata);
    for(const auto& source:std::array<std::pair<const char*,const std::string*>,8>{{{"baseline-shared-includes.vsh",&ovs},
        {"baseline-shared-includes.fsh",&ofs},{"generated.vsh",&tvs},{"generated.tcs",&tcs},{"generated.tes",&tes},
        {"generated.fsh",&tfs},{"baseline-fields.fsh",&oobserved},{"generated-fields.fsh",&tobserved}}})writeText(artifacts/source.first,*source.second);
    Context context;
    const auto renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));const auto version=reinterpret_cast<const char*>(glGetString(GL_VERSION));
    require(renderer&&version&&std::string(renderer).find("NVIDIA")!=std::string::npos,"actual NVIDIA native renderer required");
    GLint drawBuffers=0,attachments=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&drawBuffers);glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);
    require(drawBuffers>=outputs&&attachments>=outputs,"seven MRT outputs required");
    Program baseline("baseline-pure",{{GL_VERTEX_SHADER,ovs},{GL_FRAGMENT_SHADER,ofs}},false);
    Program baselineFields("baseline-fields",{{GL_VERTEX_SHADER,ovs},{GL_FRAGMENT_SHADER,oobserved}},false);
    Program tess("tessellation-pure",{{GL_VERTEX_SHADER,tvs},{GL_TESS_CONTROL_SHADER,tcs},{GL_TESS_EVALUATION_SHADER,tes},{GL_FRAGMENT_SHADER,tfs}},true);
    Program tessFields("tessellation-fields",{{GL_VERTEX_SHADER,tvs},{GL_TESS_CONTROL_SHADER,tcs},{GL_TESS_EVALUATION_SHADER,tes},{GL_FRAGMENT_SHADER,tobserved}},true);
    std::ostringstream report;report<<std::setprecision(12);
    report<<"{\"schema\":\"aqualumen-native-water-tessellation-v1\",\"renderer\":"<<quoted(renderer)<<",\"GL\":"<<quoted(version)
        <<",\"width\":"<<width<<",\"height\":"<<height<<",\"phase_seconds\":120,\"baseline_include_root\":"<<quoted(generated.string())
        <<",\"native_context_request\":\"4.0 compatibility; not the actual Iris context\",\"triangle_draw_mode\":"<<GL_TRIANGLES
        <<",\"patch_draw_mode\":"<<GL_PATCHES<<",\"patch_vertices\":3,\"last_vertex_convention\":true,\"seven_mrt_field_observer\":true"
        <<",\"programs\":["<<baseline.reflection()<<','<<baselineFields.reflection()<<','<<tess.reflection()<<','<<tessFields.reflection()<<"],\"cases\":[";
    Fixture fixture;
    std::vector<Case> cases;cases.push_back({"known-positive-top"});
    Case negative;negative.name="known-reversed-top";negative.normalY=-1;negative.reverse=true;cases.push_back(negative);
    Case unknown=negative;unknown.name="unknown-reversed-top";unknown.unknown=true;cases.push_back(unknown);
    Case mixed;mixed.name="mixed-unknown-positive-top";mixed.mixed=true;cases.push_back(mixed);
    Case bottom=negative;bottom.name="thin-bottom-air-eye";bottom.cameraY=64.0f-1.05f;
    bottom.planeY=64.001f-bottom.cameraY;bottom.surfaceY=(64.0f+1.0f/9.0f)-bottom.cameraY;bottom.depth=1.0f/9.0f;bottom.eyeWater=0;cases.push_back(bottom);
    Case nonwater;nonwater.name="nonwater-flat-material";nonwater.material=12345;nonwater.eyeWater=0;cases.push_back(nonwater);
    bool accepted=true;
    for(std::size_t caseIndex=0;caseIndex<cases.size();++caseIndex) {
        const auto& input=cases[caseIndex];const auto directory=artifacts/input.name;fs::create_directory(directory);
        fixture.inputs(input,directory);
        const auto bp=fixture.draw(baseline,input,false,directory,"baseline-pure"),br=fixture.draw(baseline,input,false,directory,"baseline-repeat");
        const auto bf=fixture.draw(baselineFields,input,true,directory,"baseline-fields");
        const auto tp=fixture.draw(tess,input,false,directory,"tess-pure"),tr=fixture.draw(tess,input,false,directory,"tess-repeat");
        const auto tf=fixture.draw(tessFields,input,true,directory,"tess-fields");
        std::vector<int> covered;std::vector<float> baselineCoverage,tessCoverage;
        for(int p=0;p<width*height;++p){const bool b=bf.image[5][p*4+1]==1,t=tf.image[5][p*4+1]==1;
            baselineCoverage.push_back(float(b));tessCoverage.push_back(float(t));if(b)covered.push_back(p);}
        require(covered.size()>=32,"case lacks nonvacuous rendered coverage");
        if(caseIndex)report<<',';
        report<<"{\"name\":"<<quoted(input.name)<<",\"covered_pixels\":"<<covered.size()<<",\"camera_y\":"<<input.cameraY
            <<",\"plane_relative_y\":"<<input.planeY<<",\"surface_relative_y\":"<<input.surfaceY<<",\"column_depth\":"<<input.depth
            <<",\"eye_in_water\":"<<input.eyeWater<<",\"material_constant_per_input_primitive\":"<<input.material<<",\"normal_y\":"<<input.normalY
            <<",\"comparisons\":[";bool first=true;
        const auto check=[&](const std::string& name,const std::vector<float>& a,const std::vector<float>& b,double abs,double rel=0.0){
            const bool pass=compare(report,name,a,b,abs,rel,first);accepted=accepted&&pass;};
        check("exact-coverage",baselineCoverage,tessCoverage,0);
        check("baseline-C0-repeat",bp.image[0],br.image[0],0);
        check("tess-C0-repeat",tp.image[0],tr.image[0],0);
        check("baseline-C0-observer-neutrality",bp.image[0],bf.image[0],colourAbs,colourRel);
        check("tess-C0-observer-neutrality",tp.image[0],tf.image[0],colourAbs,colourRel);
        check("level-one-C0",bp.image[0],tp.image[0],colourAbs,colourRel);
        check("baseline-depth-repeat",bp.depth,br.depth,0);check("tess-depth-repeat",tp.depth,tr.depth,0);
        check("baseline-depth-observer-neutrality",bp.depth,bf.depth,depthAbs);
        check("tess-depth-observer-neutrality",tp.depth,tf.depth,depthAbs);
        check("level-one-depth",bp.depth,tp.depth,depthAbs);
        const auto field=[&](const std::string& name,int slot,std::initializer_list<int> components){
            check(name,channels(bf,slot,components,covered),channels(tf,slot,components,covered),fieldAbs,fieldRel);};
        field("uv",1,{0,1});field("lightmap",1,{2,3});field("vertexColor",2,{0,1,2,3});
        field("worldNormal",3,{0,1,2});field("worldPosition",4,{0,1,2});field("waterMeanSurfaceY",3,{3});field("waterUnknownWeight",4,{3});
        check("flat-materialId-exact",channels(bf,5,{0},covered),channels(tf,5,{0},covered),0);
        std::size_t stageQualified=0,waterQualified=0,underwaterQualified=0,knownQualified=0,mixedWeights=0;
        double minimumWeight=1,maximumWeight=0,minimumBary=1,maximumBary=0,maximumBarySumError=0;
        std::vector<float> pureStage,observerStage;
        for(int p:covered) {
            const int i=p*4;require(bf.image[5][i]==input.material&&tf.image[5][i]==input.material,"flat material differs from actual immutable primitive input");
            const float weight=bf.image[4][i+3];minimumWeight=std::min(minimumWeight,double(weight));maximumWeight=std::max(maximumWeight,double(weight));
            if(weight>1e-4f&&weight<.9999f)++mixedWeights;
            if(tp.image[2][i+2]>.5f)++waterQualified;
            if(tp.image[2][i+1]>.5f)++underwaterQualified;
            if(tp.image[1][i+3]>.5f)++knownQualified;
            for(int c=0;c<4;++c){pureStage.push_back(tp.image[4][i+c]);observerStage.push_back(tf.image[6][i+c]);}
            if(input.material==10000) {
                const auto* bary=&tp.image[4][i];require(std::abs(bary[3]-1.0f)<=fieldAbs,"TES stage alpha missing on covered water");++stageQualified;
                double sum=0;for(int c=0;c<3;++c){minimumBary=std::min(minimumBary,double(bary[c]));maximumBary=std::max(maximumBary,double(bary[c]));sum+=bary[c];
                    require(bary[c]>=-fieldAbs&&bary[c]<=1+fieldAbs,"interpolated TES coordinates out of simplex");}
                maximumBarySumError=std::max(maximumBarySumError,std::abs(sum-1));
                require(std::abs(sum-1)<=3*fieldAbs,"interpolated TES coordinate sum differs");
            } else for(int c=0;c<4;++c)require(tp.image[4][i+c]==0,"nonwater C12 is not exact zero");
        }
        check("unchanged-C12-vs-field-observer-TES-varying",pureStage,observerStage,fieldAbs,fieldRel);
        if(input.material==10000)require(waterQualified==covered.size()&&stageQualified==covered.size(),"water/stage qualification incomplete");
        else require(waterQualified==0&&stageQualified==0,"nonwater mask qualification differs");
        if(input.eyeWater==1&&input.material==10000)require(underwaterQualified==covered.size(),"underwater qualification absent");
        if(input.unknown||input.name=="thin-bottom-air-eye")require(minimumWeight>.9999,"unknown/bottom did not retain contributing-vertex rejection");
        if(input.mixed)require(mixedWeights>=16,"mixed-unknown input did not produce nonconstant interpolated unknown weight");
        if(!input.unknown&&!input.mixed&&input.material==10000&&input.name!="thin-bottom-air-eye")
            require(maximumWeight==0&&knownQualified==covered.size(),"known-top field/actual C9 qualification absent");
        report<<"],\"qualification\":{\"water_pixels\":"<<waterQualified<<",\"underwater_pixels\":"<<underwaterQualified
            <<",\"C9_known_pixels\":"<<knownQualified<<",\"C12_TES_stage_pixels\":"<<stageQualified<<",\"mixed_unknown_weight_pixels\":"<<mixedWeights
            <<",\"unknown_weight_min\":"<<minimumWeight<<",\"unknown_weight_max\":"<<maximumWeight
            <<",\"interpolated_TES_barycentric_min\":"<<minimumBary<<",\"interpolated_TES_barycentric_max\":"<<maximumBary
            <<",\"interpolated_TES_barycentric_sum_max_error\":"<<maximumBarySumError<<",\"primitives_per_draw\":2}}";
    }
    report<<"],\"accepted\":"<<(accepted?"true":"false")
        <<",\"scope\":\"Empirical native level-one link/patch draw, same uploaded inputs, covered fragment fields and full-frame C0/depth. Constant material per input primitive. C12 is interpolated TES output, not a fragment built-in or invocation counter. No actual Iris, Sodium encoding, natural screenshot, physical fluid, density2/4, tessellated new wave evaluation, FPS or shipping acceptance.\"}\n";
    writeText(artifacts/"result.json",report.str());
    std::cout<<(accepted?"PASS":"RED")<<" native level-one water tessellation integration; six cases; evidence "<<artifacts<<'\n';
    return accepted?0:1;
}
} // namespace waterTessellationProbe

int main(int argc,char** argv) {
    if(argc!=4){std::cerr<<"usage: water_tessellation_probe <generated-shaders> <original-shaders> <NEW-artifact-directory>\n";return 2;}
    try{return waterTessellationProbe::run(fs::absolute(argv[1]),fs::absolute(argv[2]),fs::absolute(argv[3]));}
    catch(const std::exception& error){std::cerr<<error.what()<<'\n';
        const fs::path artifacts=fs::absolute(argv[3]);
        if(waterTessellationProbe::artifactCreated&&fs::is_directory(artifacts)&&!fs::exists(artifacts/"failure.txt")) {
            try{waterTessellationProbe::writeText(artifacts/"failure.txt",std::string(error.what())+"\n");}catch(...){}
        }
        return 2;
    }
}
