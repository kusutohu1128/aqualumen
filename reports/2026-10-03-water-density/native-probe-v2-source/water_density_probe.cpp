// TEST ONLY. CPU compilation does not execute GL; root owns all native runs.
#define main aqualumenFrozenGlcheckMain
#include "glcheck.cpp"
#undef main
#include "water_density_contract.h"
#include "water_tessellation_contract.h"
#include <cstddef>
#include <cstring>
#include <regex>
#include <map>

namespace waterDensityProbe {
constexpr int size=65;
constexpr float plane=3.25f;
using M4=std::array<float,16>;
constexpr M4 identity={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
constexpr M4 view={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
constexpr M4 inverseView={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
bool ownedArtifact=false;
void require(bool value,const std::string& message){if(!value)throw std::runtime_error("INCONCLUSIVE density: "+message);}
void okay(const std::string& label){const auto e=glGetError();require(e==GL_NO_ERROR,label+" GL error "+std::to_string(e));}
std::string readText(const fs::path& path){std::ifstream input(path,std::ios::binary);require(bool(input),"cannot read "+path.string());return {std::istreambuf_iterator<char>(input),{}};}
void textFile(const fs::path& path,const std::string& value){std::ofstream out(path,std::ios::binary);out<<value;require(bool(out),"cannot save "+path.string());}
void rawFile(const fs::path& path,const std::vector<float>& value){std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<const char*>(value.data()),std::streamsize(value.size()*sizeof(float)));require(bool(out),"cannot save "+path.string());}
std::string quote(const std::string& value){std::ostringstream out;out<<'"';for(unsigned char c:value){if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<' ')out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else out<<c;}out<<'"';return out.str();}
struct Context {
    EGLDisplay display=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;
    Context(){
        auto platform=reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));require(platform,"no EGL platform API");
        display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)){auto query=reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
            EGLDeviceEXT devices[8];EGLint count=0;require(query&&query(8,devices,&count)&&count,"no EGL device");
            display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);require(eglInitialize(display,nullptr,nullptr),"EGL init failed");}
        require(eglBindAPI(EGL_OPENGL_API),"EGL GL API bind failed");
        const EGLint configAttrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count=0;require(eglChooseConfig(display,configAttrs,&config,1,&count)&&count,"no EGL config");
        const EGLint surfaceAttrs[]={EGL_WIDTH,size,EGL_HEIGHT,size,EGL_NONE};surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        const EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,0,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        require(context!=EGL_NO_CONTEXT&&surface!=EGL_NO_SURFACE&&eglMakeCurrent(display,surface,surface,context),"native 4.0 compatibility context failed");
    }
    ~Context(){if(display!=EGL_NO_DISPLAY){eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);if(context!=EGL_NO_CONTEXT)eglDestroyContext(display,context);if(surface!=EGL_NO_SURFACE)eglDestroySurface(display,surface);eglTerminate(display);}}
};
std::string observeFS(const std::string& original){
    auto result=original;const std::string begin="\n// DENSITY_NATIVE_OBSERVER_BEGIN\n",end="// DENSITY_NATIVE_OBSERVER_END\n";
    for(const auto& seam:std::array<std::pair<const char*,const char*>,2>{{{"        gl_FragData[0]=vec4(lit,tex.a);\n","        return;"},{"    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n","\n}"}}}){
        const auto at=result.find(seam.first);require(at!=std::string::npos&&result.find(seam.first,at+std::strlen(seam.first))==std::string::npos,"STORE seam changed");
        const auto finish=result.find(seam.second,at+std::strlen(seam.first));require(finish!=std::string::npos,"STORE terminator missing");
        result.insert(finish,begin+"    gl_FragData[5]=vec4(1.0);\n"+end);
    }
    auto recovered=result;for(auto at=recovered.find(begin);at!=std::string::npos;at=recovered.find(begin)){const auto finish=recovered.find(end,at);require(finish!=std::string::npos,"observer block malformed");recovered.erase(at,finish+end.size()-at);}
    require(recovered==original,"observer removal must recover byte-identical expanded FS");return result;
}
GLuint program(const std::array<std::string,4>& sources,const std::string& label,std::ostringstream& report){
    const std::array<GLenum,4> types={GL_VERTEX_SHADER,GL_TESS_CONTROL_SHADER,GL_TESS_EVALUATION_SHADER,GL_FRAGMENT_SHADER};
    const GLuint id=glCreateProgram();std::array<GLuint,4> shaders={};
    for(int i=0;i<4;++i){shaders[i]=compile(types[i],sources[i],label+"-"+std::to_string(types[i]));glAttachShader(id,shaders[i]);}
    glBindAttribLocation(id,10,"mc_Entity");
    const char* fields[]={"gl_Position","worldPosition","waterMeanSurfaceY","waterUnknownWeight","materialId","tessStageCoord"};
    glTransformFeedbackVaryings(id,6,fields,GL_INTERLEAVED_ATTRIBS);glLinkProgram(id);
    GLint linked=0;glGetProgramiv(id,GL_LINK_STATUS,&linked);if(!linked){char log[16384]={};glGetProgramInfoLog(id,sizeof(log),nullptr,log);throw std::runtime_error(label+": "+log);}
    GLint attachedCount=0;glGetProgramiv(id,GL_ATTACHED_SHADERS,&attachedCount);require(attachedCount==4,"actual four attached stages required");
    std::array<GLuint,4> attached={};GLsizei actual=0;glGetAttachedShaders(id,4,&actual,attached.data());require(actual==4,"attached-stage reflection changed");
    std::vector<GLint> actualTypes;for(GLuint stage:attached){GLint type=0;glGetShaderiv(stage,GL_SHADER_TYPE,&type);actualTypes.push_back(type);}
    std::sort(actualTypes.begin(),actualTypes.end());std::vector<GLint> expectedTypes(types.begin(),types.end());std::sort(expectedTypes.begin(),expectedTypes.end());require(actualTypes==expectedTypes,"attached-stage types differ");
    report<<"{\"program\":"<<quote(label)<<",\"linked\":true,\"actual_stage_types\":[";for(std::size_t i=0;i<actualTypes.size();++i){if(i)report<<',';report<<actualTypes[i];}report<<"],\"tess_layout\":[";
    const std::array<std::pair<GLenum,GLint>,5> layout={{{GL_TESS_CONTROL_OUTPUT_VERTICES,3},{GL_TESS_GEN_MODE,GL_TRIANGLES},{GL_TESS_GEN_SPACING,GL_EQUAL},{GL_TESS_GEN_VERTEX_ORDER,GL_CCW},{GL_TESS_GEN_POINT_MODE,GL_FALSE}}};
    for(std::size_t i=0;i<layout.size();++i){GLint value=0;glGetProgramiv(id,layout[i].first,&value);require(value==layout[i].second,"actual linked tess layout differs");if(i)report<<',';report<<value;}report<<"],\"TF_fields\":[";
    const std::array<GLenum,6> fieldTypes={GL_FLOAT_VEC4,GL_FLOAT_VEC3,GL_FLOAT,GL_FLOAT,GL_FLOAT,GL_FLOAT_VEC4};
    GLint fieldCount=0,mode=0;glGetProgramiv(id,GL_TRANSFORM_FEEDBACK_VARYINGS,&fieldCount);glGetProgramiv(id,GL_TRANSFORM_FEEDBACK_BUFFER_MODE,&mode);require(fieldCount==6&&mode==GL_INTERLEAVED_ATTRIBS,"TF reflection count/mode differs");
    for(int i=0;i<6;++i){char name[256]={};GLsizei length=0;GLint arraySize=0;GLenum type=0;glGetTransformFeedbackVarying(id,GLuint(i),sizeof(name),&length,&arraySize,&type,name);
        require(std::string(name)==fields[i]&&arraySize==1&&type==fieldTypes[i],"actual TF field reflection differs");if(i)report<<',';report<<quote(name);}
    report<<"]}";for(auto shader:shaders)glDeleteShader(shader);okay("actual link/TF reflection");return id;
}
struct Vertex {float position[3],normal[3],colour[4],uv[2],lightmap[2],material;};
struct Raster {std::vector<float> colour,depth,coverage;};
struct Capture {std::vector<float> values;GLuint64 primitives=0;Raster pure,observer;};
struct Fixture {
    aqualumenWaterOpticalDepthDetail::Fixture resources;
    GLuint vbo=0,tf=0;std::array<GLuint,3> queries={};M4 projection={},inverseProjection={};
    float currentSurface=plane;int currentEyeWater=1;
    Fixture(const fs::path& artifacts){
        require(epoxy_gl_version()>=46||epoxy_has_gl_extension("GL_ARB_transform_feedback_overflow_query"),"bounded capture requires actual TF overflow query support");
        GLint maxBuffers=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&maxBuffers);require(maxBuffers>=6,"six MRT draw buffers required");
        glGenBuffers(1,&vbo);glGenBuffers(1,&tf);glGenQueries(3,queries.data());
        const float focal=float(1/std::tan(3.14159265358979323846/6)),near=.01f,far=128,a=-(far+near)/(far-near),b=-2*far*near/(far-near);
        projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,0,1/b,0,0,-1,a/b};
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view.data());
        for(GLenum cap:{GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE,GL_MULTISAMPLE})glDisable(cap);
        glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_TRUE);glDepthRange(0,1);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glViewport(0,0,size,size);
        glProvokingVertex(GL_LAST_VERTEX_CONVENTION);glPatchParameteri(GL_PATCH_VERTICES,3);GLint patch=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);require(patch==3,"actual patch arity differs");
        std::vector<float> colour(size*size*4,0),depth(size*size,1),sky(64*32*4,0),map(64*64*4,0);
        for(int p=0;p<size*size;++p){colour[p*4]=.03f;colour[p*4+1]=.04f;colour[p*4+2]=.05f;colour[p*4+3]=1;}
        for(int y=0;y<32;++y)for(int x=0;x<64;++x){int p=(y*64+x)*4;sky[p+3]=1;for(int c=0;c<3;++c)sky[p+c]=y<31?.04f:0;}
        for(std::size_t p=0;p<map.size();p+=4){map[p]=4;map[p+1]=plane;map[p+2]=1;}
        const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadow=1;
        allocate(0,GL_RGBA32F,1,1,GL_RGBA,white);allocate(1,GL_RGBA32F,size,size,GL_RGBA,colour.data());allocate(2,GL_RGBA16F,64,32,GL_RGBA,sky.data());allocate(3,GL_DEPTH_COMPONENT32F,size,size,GL_DEPTH_COMPONENT,depth.data());
        allocate(4,GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        allocate(5,GL_RGBA16F,1,1,GL_RGBA,black);allocate(7,GL_RGBA16F,64,32,GL_RGBA,sky.data());allocate(15,GL_RGBA32F,64,64,GL_RGBA,map.data());
        GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        require(format==GL_RGBA32F&&w==64&&h==64,"typed map storage differs");auto actual=map;std::fill(actual.begin(),actual.end(),NAN);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());require(actual==map,"actual map readback differs");rawFile(artifacts/"actual-bathymetry.rgba32f",actual);
        glBindFramebuffer(GL_FRAMEBUFFER,resources.framebuffer);for(int i=0;i<6;++i){allocate(8+i,GL_RGBA32F,size,size,GL_RGBA,nullptr);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,resources.textures[8+i],0);}
        allocate(14,GL_DEPTH_COMPONENT32F,size,size,GL_DEPTH_COMPONENT,nullptr);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,resources.textures[14],0);require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"depth/MRT framebuffer incomplete");
        const std::array<Vertex,3> vertices={{{{-.9f,plane,-.9f},{0,1,0},{.6f,.9f,.7f,1},{0,0},{.12f,.72f},10000},{{-.9f,plane,.9f},{0,1,0},{.68f,.85f,.73f,1},{0,1},{.19f,.78f},10000},{{.9f,plane,.9f},{0,1,0},{.76f,.80f,.76f,1},{1,1},{.26f,.84f},10000}}};
        static_assert(sizeof(Vertex)==15*sizeof(float),"raw input packing");glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),vertices.data(),GL_STATIC_DRAW);
        std::vector<float> expected(sizeof(vertices)/sizeof(float)),uploaded(expected.size(),NAN);std::memcpy(expected.data(),vertices.data(),sizeof(vertices));glGetBufferSubData(GL_ARRAY_BUFFER,0,sizeof(vertices),uploaded.data());require(uploaded==expected,"immutable vertex upload differs");rawFile(artifacts/"uploaded-vertices.f32",uploaded);
        glEnableClientState(GL_VERTEX_ARRAY);glVertexPointer(3,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,position)));glEnableClientState(GL_NORMAL_ARRAY);glNormalPointer(GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,normal)));glEnableClientState(GL_COLOR_ARRAY);glColorPointer(4,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,colour)));
        glClientActiveTexture(GL_TEXTURE0);glEnableClientState(GL_TEXTURE_COORD_ARRAY);glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,uv)));glClientActiveTexture(GL_TEXTURE1);glEnableClientState(GL_TEXTURE_COORD_ARRAY);glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,lightmap)));
        glEnableVertexAttribArray(10);glVertexAttribPointer(10,1,GL_FLOAT,GL_FALSE,sizeof(Vertex),reinterpret_cast<void*>(offsetof(Vertex,material)));okay("fixture uploads");
    }
    ~Fixture(){glDeleteQueries(3,queries.data());glDeleteBuffers(1,&tf);glDeleteBuffers(1,&vbo);}
    void allocate(int slot,GLenum format,int w,int h,GLenum channel,const float* data){glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,resources.textures[slot]);for(GLenum p:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,p,GL_NEAREST);for(GLenum p:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,p,GL_CLAMP_TO_EDGE);glTexImage2D(GL_TEXTURE_2D,0,GLint(format),w,h,0,channel,GL_FLOAT,data);}
    void uniforms(GLuint id){glUseProgram(id);const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
        for(int unit=0;unit<8;++unit){auto location=glGetUniformLocation(id,names[unit]);require(location>=0,"required sampler inactive");glUniform1i(location,unit);glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,resources.textures[unit==6?15:unit]);glBindSampler(unit,0);}
        for(const auto& item:std::array<std::pair<const char*,M4>,6>{{{"gbufferProjection",projection},{"gbufferProjectionInverse",inverseProjection},{"gbufferModelView",view},{"gbufferModelViewInverse",inverseView},{"shadowProjection",identity},{"shadowModelView",identity}}})glUniformMatrix4fv(glGetUniformLocation(id,item.first),1,GL_FALSE,item.second.data());
        glUniform3f(glGetUniformLocation(id,"cameraPosition"),0,63,0);glUniform3f(glGetUniformLocation(id,"sunPosition"),0,0,-1);glUniform3f(glGetUniformLocation(id,"shadowLightPosition"),0,0,-1);glUniform1f(glGetUniformLocation(id,"viewWidth"),size);glUniform1f(glGetUniformLocation(id,"viewHeight"),size);glUniform1f(glGetUniformLocation(id,"far"),128);glUniform1f(glGetUniformLocation(id,"frameTimeCounter"),120);
        glUniform1i(glGetUniformLocation(id,"isEyeInWater"),currentEyeWater);glUniform1i(glGetUniformLocation(id,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(id,"aqualumenActive"),0);glUniform4f(glGetUniformLocation(id,"aqualumenGrid"),-32,-32,64,currentSurface);glUniform1i(glGetUniformLocation(id,"aqualumenBathymetryReady"),1);glUniform4f(glGetUniformLocation(id,"aqualumenBathymetryGrid"),-32,-32,64,currentSurface);glUniform1f(glGetUniformLocation(id,"rainStrength"),0);glUniform1f(glGetUniformLocation(id,"wetness"),0);glUniform1i(glGetUniformLocation(id,"worldTime"),6000);glUniform2i(glGetUniformLocation(id,"eyeBrightnessSmooth"),0,240);
        GLint unit=-1,bound=0,sampler=-1;glGetUniformiv(id,glGetUniformLocation(id,"aqualumenBathymetry"),&unit);glActiveTexture(GL_TEXTURE6);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);require(unit==6&&GLuint(bound)==resources.textures[15]&&sampler==0,"actual map binding differs");okay("uniform/binding inputs");}
    void upload(const std::array<Vertex,3>& vertices,float depth,float surface,bool allUnknown,bool thirdUnknown,const fs::path& directory){
        currentSurface=surface;glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),vertices.data(),GL_STATIC_DRAW);
        std::vector<float> expected(sizeof(vertices)/sizeof(float)),actual(expected.size(),NAN);std::memcpy(expected.data(),vertices.data(),sizeof(vertices));glGetBufferSubData(GL_ARRAY_BUFFER,0,sizeof(vertices),actual.data());require(actual==expected,"control immutable VBO readback differs");rawFile(directory/"uploaded-vertices.f32",actual);
        std::vector<float> map(64*64*4,0);for(int z=0;z<64;++z)for(int x=0;x<64;++x){int p=(z*64+x)*4;map[p]=depth;map[p+1]=surface;map[p+2]=allUnknown||(thirdUnknown&&x==30&&z==33)?0.0f:1.0f;}
        allocate(15,GL_RGBA32F,64,64,GL_RGBA,map.data());GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);require(format==GL_RGBA32F&&w==64&&h==64,"control typed map storage differs");actual=map;std::fill(actual.begin(),actual.end(),NAN);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());require(actual==map,"control typed map readback differs");rawFile(directory/"actual-bathymetry.rgba32f",actual);okay("control upload");
    }
    std::vector<float> feedback(GLuint id,GLuint64& primitiveCount,const fs::path& output){
        uniforms(id);glEnable(GL_RASTERIZER_DISCARD);glBeginQuery(GL_PRIMITIVES_GENERATED,queries[0]);glDrawArrays(GL_PATCHES,0,3);glEndQuery(GL_PRIMITIVES_GENERATED);glGetQueryObjectui64v(queries[0],GL_QUERY_RESULT,&primitiveCount);
        const auto budget=aqualumenWaterDensity::checkedCapacity(primitiveCount);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,GLsizeiptr(budget.capacityBytes),nullptr,GL_STREAM_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,tf);
        glBeginQuery(GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN,queries[1]);glBeginQuery(GL_TRANSFORM_FEEDBACK_OVERFLOW_ARB,queries[2]);glBeginTransformFeedback(GL_TRIANGLES);glDrawArrays(GL_PATCHES,0,3);glEndTransformFeedback();glEndQuery(GL_TRANSFORM_FEEDBACK_OVERFLOW_ARB);glEndQuery(GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN);
        GLuint64 written=0,overflow=1;glGetQueryObjectui64v(queries[1],GL_QUERY_RESULT,&written);glGetQueryObjectui64v(queries[2],GL_QUERY_RESULT,&overflow);glDisable(GL_RASTERIZER_DISCARD);
        require(overflow==0&&written==primitiveCount,"bounded TF overflow/count instability; do not read an unqualified capture");
        std::vector<float> result(budget.observedVertices*aqualumenWaterDensity::stride,NAN);glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,GLsizeiptr(result.size()*sizeof(float)),result.data());for(float value:result)require(std::isfinite(value),"nonfinite actual TES output");rawFile(output,result);okay("original TES main feedback capture");return result;
    }
    Raster raster(GLuint id,bool observe,const fs::path& directory,const std::string& label){
        uniforms(id);glBindFramebuffer(GL_FRAMEBUFFER,resources.framebuffer);const std::array<GLenum,6> buffers={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2,GL_COLOR_ATTACHMENT3,GL_COLOR_ATTACHMENT4,GL_COLOR_ATTACHMENT5};glDrawBuffers(6,buffers.data());const float zero[4]={},one=1;for(int i=0;i<6;++i)glClearBufferfv(GL_COLOR,i,zero);glClearBufferfv(GL_DEPTH,0,&one);glDrawBuffers(observe?6:5,buffers.data());glDrawArrays(GL_PATCHES,0,3);
        Raster result;result.colour.resize(size*size*4);result.depth.resize(size*size);result.coverage.resize(size*size*4);glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.colour.data());glReadPixels(0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,result.depth.data());glReadBuffer(GL_COLOR_ATTACHMENT5);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.coverage.data());
        for(const auto* values:{&result.colour,&result.depth,&result.coverage})for(float value:*values)require(std::isfinite(value),"nonfinite raster readback");
        rawFile(directory/(label+"-C0.rgba32f"),result.colour);rawFile(directory/(label+"-depth.f32"),result.depth);rawFile(directory/(label+"-coverage.rgba32f"),result.coverage);okay("within-level native raster draw");return result;
    }
};
std::array<std::array<float,10>,3> corners(const std::vector<float>& values){
    std::array<std::array<float,10>,3> result={};std::array<bool,3> found={};
    for(std::size_t p=0;p<values.size();p+=14)for(int i=0;i<3;++i)if(values[p+10+i]==1){
        bool oneHot=true;for(int j=0;j<3;++j)if(j!=i&&values[p+10+j]!=0)oneHot=false;
        if(oneHot){for(int c=0;c<10;++c){if(found[i])require(result[i][c]==values[p+c],"duplicate original corner outputs disagree");result[i][c]=values[p+c];}found[i]=true;}}
    require(found[0]&&found[1]&&found[2],"all three original corners must be observed nonvacuously");return result;
}
Vertex vertex(float x,float z,float y=plane,float normalY=1,float material=10000){
    return {{x,y,z},{0,normalY,0},{.7f,.8f,.75f,1},{.5f,.5f},{.2f,.8f},material};
}
using Edge=std::map<std::pair<float,float>,std::vector<float>>;
Edge sharedEdge(const std::vector<float>& values){
    Edge edge;
    for(std::size_t p=0;p<values.size();p+=14)if(values[p+12]==0){
        require(values[p+13]==1&&std::abs(values[p+4]-values[p+6])<=5e-6,"shared edge TF selection is not qualified diagonal/TES output");
        std::vector<float> fields(values.begin()+std::ptrdiff_t(p),values.begin()+std::ptrdiff_t(p+10));
        const auto key=std::make_pair(values[p+4],values[p+6]);const auto found=edge.find(key);
        if(found!=edge.end())require(aqualumenWaterTessellation::compareSamples(found->second,fields,0,0).accepted(),"duplicate canonical edge outputs disagree");
        else edge.emplace(key,fields);
    }
    require(edge.size()>=3,"shared edge lacks an actual generated noncorner sample");return edge;
}
struct EdgeComparison {bool qualified=false,accepted=false;std::size_t points=0;double maximumAbsolute=0;};
EdgeComparison compareEdge(const Edge& a,const Edge& b){
    EdgeComparison result;if(a.empty()||a.size()!=b.size())return result;
    std::vector<float> av,bv;for(const auto& point:a){auto match=b.find(point.first);if(match==b.end())return result;av.insert(av.end(),point.second.begin(),point.second.end());bv.insert(bv.end(),match->second.begin(),match->second.end());}
    const auto comparison=aqualumenWaterTessellation::compareSamples(av,bv,0,0);result.qualified=true;result.accepted=comparison.accepted();result.points=a.size();result.maximumAbsolute=comparison.maximumAbsolute;return result;
}
bool controls(Fixture& fixture,const std::array<std::array<std::string,4>,3>& sources,const fs::path& artifacts,std::ostringstream& report){
    bool accepted=true;const std::array<int,3> levels={1,2,4};report<<",\"controls\":[";bool first=true;
    for(int index=0;index<3;++index){const auto level=levels[index];const auto directory=artifacts/("controls-level"+std::to_string(level));fs::create_directory(directory);
        std::ostringstream reflected;const auto id=program(sources[index],"control-TES-main",reflected);fixture.resources.programs[0]=id;
        if(!first){report<<',';}first=false;report<<"{\"level\":"<<level<<",\"program\":"<<reflected.str()<<",\"shared_edge_cases\":[";
        Edge reference;bool firstEdge=true;
        if(level>1)for(int variation=0;variation<3;++variation){
            const char* labels[]={"known-opposite-endpoint-order-and-normal","off-edge-third-unknown","off-edge-third-unadmitted-normal-stress"};
            const auto caseDir=directory/labels[variation];fs::create_directory(caseDir);
            std::array<Vertex,3> a={vertex(-.9f,-.9f),vertex(.9f,.9f),vertex(-.9f,.9f)};
            std::array<Vertex,3> b={vertex(.9f,.9f,plane,-1),vertex(-.9f,-.9f,plane,-1),vertex(.9f,-.9f,plane,-1)};
            // Only the third A normal changes: this mixed-normal input is an
            // uploaded classifier stress, not a claim about natural Sodium meshes.
            if(variation==2){a[2].normal[0]=1;a[2].normal[1]=0;}
            const auto aDir=caseDir/"A",bDir=caseDir/"B";fs::create_directory(aDir);fs::create_directory(bDir);fixture.currentEyeWater=1;
            fixture.upload(a,4,plane,false,variation==1,aDir);GLuint64 acount=0;const auto av=fixture.feedback(id,acount,aDir/"actual-TES.f32");
            fixture.upload(b,4,plane,false,variation==1,bDir);GLuint64 bcount=0;const auto bv=fixture.feedback(id,bcount,bDir/"actual-TES.f32");
            const auto ae=sharedEdge(av),be=sharedEdge(bv);if(variation==0)reference=ae;
            const auto pair=compareEdge(ae,be),referenceA=compareEdge(reference,ae),referenceB=compareEdge(reference,be);
            const auto ac=corners(av),bc=corners(bv);bool flags=ac[0][8]==0&&ac[1][8]==0&&ac[2][8]==float(variation!=0)&&bc[0][8]==0&&bc[1][8]==0&&bc[2][8]==0;
            std::size_t knownEdge=0,unknownInterior=0;
            for(const auto& point:ae)if(point.second[8]==0&&point.second[9]==10000&&std::abs(point.second[7]-plane)<=5e-6)++knownEdge;
            for(std::size_t p=0;p<av.size();p+=14)if(av[p+10]>0&&av[p+11]>0&&av[p+12]>0&&av[p+8]==1)++unknownInterior;
            const bool pass=pair.qualified&&pair.accepted&&referenceA.accepted&&referenceB.accepted&&flags&&knownEdge==ae.size()&&acount>1&&bcount>1&&(variation==0||unknownInterior>0);accepted=accepted&&pass;
            if(!firstEdge){report<<',';}firstEdge=false;report<<"{\"name\":"<<quote(labels[variation])<<",\"actual_A_primitives\":"<<acount<<",\"actual_B_primitives\":"<<bcount<<",\"unique_shared_edge_points\":"<<ae.size()<<",\"generated_noncorner_points\":"<<ae.size()-2<<",\"known_edge_points\":"<<knownEdge<<",\"unknown_interior_vertices_A\":"<<unknownInterior<<",\"original_corner_flags_qualified\":"<<(flags?"true":"false")<<",\"matching_coordinate_sets\":"<<(pair.qualified?"true":"false")<<",\"canonical_edge_exact_A_vs_B\":"<<(pair.accepted?"true":"false")<<",\"canonical_edge_max_delta\":"<<pair.maximumAbsolute<<",\"edge_exact_vs_known_reference\":"<<(referenceA.accepted&&referenceB.accepted?"true":"false")<<",\"fields\":\"clip4/worldPosition3/mean/unknown/material; excludes bary-index permutation and normal\",\"accepted\":"<<(pass?"true":"false")<<'}';
        }
        report<<"],\"exclusion_and_fallback_cases\":[";
        for(int kind=0;kind<3;++kind){const char* labels[]={"thin-bottom-negative","nonwater-factor-one","allunknown-positive-fallback"};const auto caseDir=directory/labels[kind];fs::create_directory(caseDir);
            const float mean=kind==0?64.001f-63.0f:plane,surface=kind==0?(64.0f+1.0f/9.0f)-63.0f:plane,depth=kind==0?1.0f/9.0f:4.0f,material=kind==1?12345.0f:10000.0f;
            const std::array<Vertex,3> input={vertex(-.9f,-.9f,mean,kind==0?-1.0f:1.0f,material),vertex(-.9f,.9f,mean,kind==0?-1.0f:1.0f,material),vertex(.9f,.9f,mean,kind==0?-1.0f:1.0f,material)};
            fixture.currentEyeWater=kind==2?1:0;fixture.upload(input,depth,surface,kind==2,false,caseDir);GLuint64 count=0;const auto values=fixture.feedback(id,count,caseDir/"actual-TES.f32");const auto actualCorners=corners(values);
            std::size_t qualified=0;double maxY=0,maxClipPlaneError=0;bool fields=true;
            for(std::size_t p=0;p<values.size();p+=14){const auto* v=&values[p];fields=fields&&v[8]==1&&v[9]==material&&v[13]==1&&std::abs(v[7]-mean)<=5e-6;++qualified;
                maxY=std::max(maxY,std::abs(double(v[5])-mean));if(kind<2)for(int c=0;c<4;++c){double linear=0;for(int corner=0;corner<3;++corner)linear+=double(v[10+corner])*actualCorners[corner][c];maxClipPlaneError=std::max(maxClipPlaneError,std::abs(double(v[c])-linear));}}
            const bool pass=fields&&qualified>=3&&(kind==1?count==1:(level==1?count==1:count>1))&&(kind==2||(maxY<=5e-6&&maxClipPlaneError<=5e-6));accepted=accepted&&pass;
            if(kind){report<<',';}report<<"{\"name\":"<<quote(labels[kind])<<",\"actual_primitives\":"<<count<<",\"finite_qualified_vertices\":"<<qualified<<",\"unknown_mean_material_stage_fields_qualified\":"<<(fields?"true":"false")<<",\"maximum_y_delta_from_undisplaced_mean\":"<<maxY<<",\"maximum_clip_error_from_original_corner_plane\":"<<maxClipPlaneError<<",\"source_domain\":\"uploaded interface classifier; not natural-world visual evidence\",\"accepted\":"<<(pass?"true":"false")<<'}';
        }
        report<<"]}";glDeleteProgram(id);fixture.resources.programs[0]=0;
    }
    report<<']';return accepted;
}
int run(const std::array<fs::path,3>& roots,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required");
    const std::array<int,3> levels={1,2,4};std::array<std::array<std::string,4>,3> sources={};std::array<std::string,3> observed={};
    for(int i=0;i<3;++i){const auto metadata=readText(roots[i].parent_path()/"WATER-TESSELLATION-PROBE.json");require(std::regex_search(metadata,std::regex("\"level\"\\s*:\\s*"+std::to_string(levels[i])+"\\s*[,}]")),"pack level does not match pinned CLI order1/2/4");require(std::regex_search(metadata,std::regex("\"fixed_phase_seconds\"\\s*:\\s*120\\.0\\s*[,}]")),"analytic phase120 required");
        const char* names[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes","gbuffers_water.fsh"};for(int j=0;j<4;++j)sources[i][j]=expand(roots[i]/names[j],roots[i]);require(sources[i][0].find("#define frameTimeCounter 120.0\n")!=std::string::npos&&sources[i][3].find("#define frameTimeCounter 120.0\n")!=std::string::npos,"compiled fixed phase missing");observed[i]=observeFS(sources[i][3]);}
    require(fs::create_directories(artifacts),"cannot create new artifacts");ownedArtifact=true;
    Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");
    Fixture fixture(artifacts);std::array<Capture,3> captures={};std::ostringstream report;report<<std::setprecision(12);report<<"{\"schema\":\"aqualumen-native-water-density-v2\",\"scope\":\"known vertical tracer plus canonical shared edges, synthetic off-edge third-corner flag stresses, thin-bottom/nonwater/allunknown uploaded TF controls; no actual Iris/physical/visual/FPS acceptance\",\"renderer\":"<<quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"patch_vertices\":3,\"draw_mode\":"<<GL_PATCHES<<",\"culling_enabled\":false,\"phase_seconds\":120,\"TF_stride_floats\":14,\"TF_capacity_triangle_budget\":4096,\"levels\":[";
    bool accepted=true;std::array<std::array<float,10>,3> baselineCorners={};
    for(int i=0;i<3;++i){const auto directory=artifacts/("level"+std::to_string(levels[i]));fs::create_directory(directory);if(i)report<<',';report<<"{\"level\":"<<levels[i]<<",\"programs\":[";
        const char* names[]={"water.vsh","water.tcs","water.tes","water.fsh"};for(int j=0;j<4;++j)textFile(directory/names[j],sources[i][j]);textFile(directory/"observed.fsh",observed[i]);
        auto observerSources=sources[i];observerSources[3]=observed[i];fixture.resources.programs[0]=program(sources[i],"pure",report);report<<',';fixture.resources.programs[1]=program(observerSources,"observer",report);report<<']';
        auto& capture=captures[i];capture.values=fixture.feedback(fixture.resources.programs[0],capture.primitives,directory/"actual-TES-triangles.f32");GLuint64 observerCount=0;const auto observerFeedback=fixture.feedback(fixture.resources.programs[1],observerCount,directory/"observer-TES-triangles.f32");
        capture.pure=fixture.raster(fixture.resources.programs[0],false,directory,"pure");capture.observer=fixture.raster(fixture.resources.programs[1],true,directory,"observer");
        const auto tfNeutral=aqualumenWaterTessellation::compareSamples(capture.values,observerFeedback,0,0),colourNeutral=aqualumenWaterTessellation::compareSamples(capture.pure.colour,capture.observer.colour,5e-4,2e-4),depthNeutral=aqualumenWaterTessellation::compareSamples(capture.pure.depth,capture.observer.depth,2e-6,0);
        const auto actualCorners=corners(capture.values);if(i==0)baselineCorners=actualCorners;const bool exactCorners=actualCorners==baselineCorners;
        std::size_t covered=0,interior=0,knownVertices=0;double maximumHeightDelta=0,maximumClipDelta=0;
        for(std::size_t p=0;p<capture.observer.coverage.size();p+=4)if(capture.observer.coverage[p]==1)++covered;
        require(covered>=32,"rendered observer coverage must be nonvacuous");
        for(std::size_t p=0;p<capture.values.size();p+=14){const auto* vertex=&capture.values[p];require(std::abs(vertex[7]-plane)<=5e-6f&&vertex[8]==0&&vertex[9]==10000&&vertex[13]==1,"known mean/unknown/material/TES stage qualification differs");++knownVertices;
            const double sum=double(vertex[10])+vertex[11]+vertex[12];require(std::abs(sum-1)<1e-5,"TES barycentrics must form simplex");
            if(vertex[10]>1e-5&&vertex[11]>1e-5&&vertex[12]>1e-5){++interior;double linearHeight=0;std::array<double,4> linearClip={};for(int corner=0;corner<3;++corner){linearHeight+=double(vertex[10+corner])*baselineCorners[corner][5];for(int c=0;c<4;++c)linearClip[c]+=double(vertex[10+corner])*baselineCorners[corner][c];}
                maximumHeightDelta=std::max(maximumHeightDelta,std::abs(double(vertex[5])-linearHeight));for(int c=0;c<4;++c)maximumClipDelta=std::max(maximumClipDelta,std::abs(double(vertex[c])-linearClip[c]));}}
        const bool pass=tfNeutral.accepted()&&observerCount==capture.primitives&&colourNeutral.accepted()&&depthNeutral.accepted()&&exactCorners;accepted=accepted&&pass;
        report<<",\"actual_output_primitives\":"<<capture.primitives<<",\"actual_TF_vertices\":"<<capture.values.size()/14<<",\"known_stage_vertices\":"<<knownVertices<<",\"covered_pixels\":"<<covered<<",\"interior_vertices\":"<<interior<<",\"interior_height_max_delta_from_level1_plane\":"<<maximumHeightDelta<<",\"interior_clip_max_delta_from_level1_plane\":"<<maximumClipDelta<<",\"exact_original_corners\":"<<(exactCorners?"true":"false")<<",\"TF_observer_exact\":"<<(tfNeutral.accepted()?"true":"false")<<",\"within_level_C0_observer_neutral\":"<<(colourNeutral.accepted()?"true":"false")<<",\"within_level_C0_max_delta\":"<<colourNeutral.maximumAbsolute<<",\"within_level_depth_observer_neutral\":"<<(depthNeutral.accepted()?"true":"false")<<",\"within_level_depth_max_delta\":"<<depthNeutral.maximumAbsolute<<",\"TF_overflow\":false,\"accepted\":"<<(pass?"true":"false")<<'}';
        if(i==2)accepted=accepted&&interior>0&&maximumHeightDelta>1e-5&&maximumClipDelta>1e-5;
        for(auto& id:fixture.resources.programs){glDeleteProgram(id);id=0;}
    }
    const bool moreGeometry=captures[1].primitives>captures[0].primitives&&captures[2].primitives>captures[1].primitives&&captures[2].primitives>2;accepted=accepted&&moreGeometry;
    report<<']';const bool controlPass=controls(fixture,sources,artifacts,report);accepted=accepted&&controlPass;
    report<<",\"actual_output_count_increases\":"<<(moreGeometry?"true":"false")<<",\"count_formula_assumed\":false,\"cross_density_C0_neutrality_claimed\":false,\"controls_accepted\":"<<(controlPass?"true":"false")<<",\"accepted\":"<<(accepted?"true":"false")<<"}\n";textFile(artifacts/"result.json",report.str());std::cout<<(accepted?"PASS":"RED")<<" density tracer and controls "<<artifacts<<'\n';return accepted?0:1;
}
} // namespace waterDensityProbe
int main(int argc,char** argv){if(argc!=5){std::cerr<<"usage: water_density_probe <level1-shaders> <level2-shaders> <level4-shaders> <NEW-artifacts>\n";return 2;}
    try{return waterDensityProbe::run({fs::absolute(argv[1]),fs::absolute(argv[2]),fs::absolute(argv[3])},fs::absolute(argv[4]));}
    catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(waterDensityProbe::ownedArtifact)try{waterDensityProbe::textFile(fs::absolute(argv[4])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}}
