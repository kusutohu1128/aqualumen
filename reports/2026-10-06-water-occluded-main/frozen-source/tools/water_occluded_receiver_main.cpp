// New public-MAIN occluded first-floor tracer bullet. No retained source is edited.
#define main retainedGlcheckMain
#include "glcheck.cpp"
#undef main
#include <cstdlib>

namespace occluded {
using namespace aqualumenWaterOpticalDepthDetail;
struct Context {
    EGLDisplay display=EGL_NO_DISPLAY; EGLSurface surface=EGL_NO_SURFACE; EGLContext context=EGL_NO_CONTEXT;
    Context() {
        auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        if(!platform) throw std::runtime_error("No EGL platform extension");
        display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
            EGLDeviceEXT devices[8];EGLint count=0;
            if(!query||!query(8,devices,&count)||count==0) throw std::runtime_error("No EGL device");
            display=platform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("No EGL device initialization");
        }
        eglBindAPI(EGL_OPENGL_API);
        EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count=0;eglChooseConfig(display,cfg,&config,1,&count);
        if(count!=1) throw std::runtime_error("No EGL config");
        EGLint dimensions[]={EGL_WIDTH,size,EGL_HEIGHT,size,EGL_NONE};surface=eglCreatePbufferSurface(display,config,dimensions);
        EGLint attributes[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context=eglCreateContext(display,config,EGL_NO_CONTEXT,attributes);
        if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("No GL compatibility context");
        std::string renderer=(const char*)glGetString(GL_RENDERER);
        std::cout<<"Renderer: "<<renderer<<"\nGL: "<<glGetString(GL_VERSION)<<'\n';
        if(renderer.find("RTX 3080 Ti")==std::string::npos) throw std::runtime_error("Actual RTX3080Ti required");
    }
    ~Context() {eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);}
};
void option(std::string& source,const std::string& name,const std::string& value) {
    std::string prefix="#define "+name+" ";auto at=source.find(prefix);
    if(at==std::string::npos||source.find(prefix,at+1)!=std::string::npos) throw std::runtime_error("Public option missing/ambiguous");
    source.replace(at,source.find('\n',at)-at,prefix+value);
}
void require(bool yes,const std::string& message) {if(!yes) throw std::runtime_error("INCONCLUSIVE: "+message);}
bool patch(const V3& p) {return p[0]>-2&&p[0]<2&&p[2]>-9&&p[2]<-6;}
int probe(const fs::path& root,const fs::path& out) {
    fs::create_directories(out);
    const float f=float(1/std::tan(pi/6)),np=.1f,fp=128,a=-(fp+np)/(fp-np),b=-2*fp*np/(fp-np);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverse[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    std::vector<Box> boxes={{{-8,-4,-4},{8,-1,-.05},1},{{-8,-4,-24},{8,-3,-4},2}};
    auto vertex=expand(root/"gbuffers_water.vsh",root),fragment=expand(root/"gbuffers_water.fsh",root);
    option(vertex,"WAVE_HEIGHT","0.0");option(fragment,"WAVE_HEIGHT","0.0");option(fragment,"SHORE_FOAM","0.0");
    for(const auto& file:std::array<std::pair<std::string,std::string>,2>{{{"production.vsh",vertex},{"production.fsh",fragment}}}) {
        std::ofstream stream(out/file.first);stream<<file.second;require(bool(stream),"expanded source write");
    }
    auto observed=instrumentShoreCausal(fragment,false);{std::ofstream stream(out/"observation-only.fsh");stream<<observed;}
    Fixture fixture;
    fixture.programs[0]=link(vertex,fragment,"occluded-receiver-production-main","mc_Entity");
    fixture.programs[1]=link(vertex,observed,"occluded-receiver-passive-original-invocation","mc_Entity");
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);GLenum draws[8];
    for(int i=0;i<8;i++) {
        glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,fixture.textures[i==0?6:7+i]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
        draws[i]=GL_COLOR_ATTACHMENT0+i;glFramebufferTexture2D(GL_FRAMEBUFFER,draws[i],GL_TEXTURE_2D,fixture.textures[i==0?6:7+i],0);
    }
    // Extra input objects are separate from every sampled/output attachment.
    GLuint inputs[3];glGenTextures(3,inputs);
    struct Delete {GLuint* p;~Delete(){glDeleteTextures(3,p);}} cleanup{inputs};
    glBindTexture(GL_TEXTURE_2D,fixture.textures[7]);glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,size,size,0,GL_DEPTH_COMPONENT,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,fixture.textures[7],0);
    glDrawBuffers(8,draws);require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"eight-MRT framebuffer");
    const float white[4]={1,1,1,1},shadow=1;
    std::vector<float> black(size*size*4,0),sky(skyWidth*skyHeight*4,.04f);
    for(size_t q=3;q<sky.size();q+=4) sky[q]=1;
    std::fill(sky.end()-skyWidth*4,sky.end(),0); // no Sun/cache/direct receiver source
    auto texture=[&](int unit,GLuint id,int width,int height,GLint format,GLenum channels,const float* pixels) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,id);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,format,width,height,0,channels,GL_FLOAT,pixels);
    };
    texture(0,fixture.textures[0],1,1,GL_RGBA32F,GL_RGBA,white);
    texture(1,fixture.textures[1],size,size,GL_RGBA32F,GL_RGBA,nullptr);
    texture(2,fixture.textures[2],skyWidth,skyHeight,GL_RGBA32F,GL_RGBA,sky.data());
    texture(3,fixture.textures[3],size,size,GL_R32F,GL_RED,nullptr);
    texture(4,fixture.textures[4],1,1,GL_DEPTH_COMPONENT32F,GL_DEPTH_COMPONENT,&shadow);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
    texture(5,fixture.textures[5],size,size,GL_RGBA32F,GL_RGBA,black.data());
    std::vector<float> columns(64*64*4,0),cells(16*4*24*4,0),source=cells;
    for(int z=0;z<64;z++) for(int x=0;x<64;x++) {int q=(z*64+x)*4;columns[q]=(-32+z+.5f)<-4?2.5f:.5f;columns[q+1]=-.5f;columns[q+2]=1;}
    for(int y=0;y<4;y++) for(int z=0;z<24;z++) for(int x=0;x<16;x++) {
        int q=((y*24+z)*16+x)*4;V3 center={-8+x+.5,-4+y+.5,-24+z+.5};
        bool opaque=center[1]<(center[2]<-4?-3:-1);
        cells[q]=opaque?3:2;cells[q+1]=opaque?1:0;
        for(int c=0;c<3;c++) source[q+c]=opaque?.25f:0;
        source[q+3]=opaque?1:0;
    }
    texture(6,inputs[0],64,64,GL_RGBA32F,GL_RGBA,columns.data());
    texture(7,inputs[1],16,96,GL_RGBA32F,GL_RGBA,cells.data());
    texture(8,inputs[2],16,96,GL_RGBA32F,GL_RGBA,source.data());
    save(out/"receiver-cells.rgba32f",cells);save(out/"receiver-source-neutral.rgba32f",source);
    GLint worldSampler=glGetUniformLocation(fixture.programs[0],"aqualumenReceiverSource");
    const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","aqualumenReceiverCells","aqualumenReceiverSource"};
    for(GLuint program:fixture.programs) {
        glUseProgram(program);for(int unit=0;unit<9;unit++) glUniform1i(glGetUniformLocation(program,names[unit]),unit);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverse);
        for(const char* name:{"gbufferModelView","gbufferModelViewInverse","shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform1i(glGetUniformLocation(program,"aqualumenBathymetryReady"),1);glUniform4f(glGetUniformLocation(program,"aqualumenBathymetryGrid"),-32,-32,64,-.5f);
        glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),1);glUniform3f(glGetUniformLocation(program,"aqualumenReceiverOrigin"),-8,-4,-24);
        glUniform3i(glGetUniformLocation(program,"aqualumenReceiverSize"),16,4,24);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);
        require(glGetAttribLocation(program,"mc_Entity")==10,"water material binding");
    }
    auto makeScene=[&](int tag) {
        auto result=scene(boxes,false,f,a,b);
        for(int q=0;q<size*size;q++) {
            if(result.id[q]>=0) for(int c=0;c<3;c++) result.colour[q*4+c]=.25f;
            if(result.id[q]==2&&(tag==2||(tag==1&&patch(result.receiver[q])))) result.colour[q*4+1]=.43f;
        }
        return result;
    };
    auto base=makeScene(0),hidden=makeScene(1),visible=makeScene(2);
    require(base.depth==hidden.depth&&base.colour==hidden.colour,"hidden material must have no camera-visible input change");
    save(out/"camera-depth.r32f",base.depth);save(out/"camera-source-neutral.rgba32f",base.colour);save(out/"camera-source-hidden-tag.rgba32f",hidden.colour);
    glViewport(0,0,size,size);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glDisable(GL_SCISSOR_TEST);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_FALSE);
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);glDisableVertexAttribArray(10);glVertexAttrib4f(10,10000,0,0,0);
    auto draw=[&](const Scene& input,bool observer,const std::string& label) {
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,fixture.textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,input.colour.data());
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,fixture.textures[3]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RED,GL_FLOAT,input.depth.data());
        glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,fixture.textures[7]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,input.depth.data());
        glBindTexture(GL_TEXTURE_2D,inputs[2]); // restore unit8's source after depth upload
        glUseProgram(fixture.programs[observer?1:0]);glClearColor(0,0,0,0);glClear(GL_COLOR_BUFFER_BIT);
        glBegin(GL_QUADS);glVertex3f(-8,-.5f,-24);glVertex3f(8,-.5f,-24);glVertex3f(8,-.5f,-.05f);glVertex3f(-8,-.5f,-.05f);glEnd();
        Capture result;result.colour.resize(size*size*4);glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.colour.data());
        if(observer) for(int i=1;i<8;i++) {result.state[i-1].resize(size*size*4);glReadBuffer(GL_COLOR_ATTACHMENT0+i);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.state[i-1].data());}
        require(glGetError()==GL_NO_ERROR,"actual MAIN draw/readback GL state");
        for(float value:result.colour) require(std::isfinite(value),"finite C0");
        if(observer) for(const auto& channel:result.state) for(float value:channel) require(std::isfinite(value),"finite observed original invocation");
        save(out/(label+"-C0.rgba32f"),result.colour);return result;
    };
    auto neutral=draw(base,false,"neutral"),witness=draw(base,true,"witness");
    require(difference(neutral.colour,witness.colour)<1e-6,"passive observer C0 neutrality");
    constexpr int x=64,y=53,q=(y*size+x)*4;
    require(neutral.colour[q+3]==1,"fixed water pixel coverage");
    V3 origin={witness.state[0][q],witness.state[0][q+1],witness.state[0][q+2]},ray={witness.state[3][q],witness.state[3][q+1],witness.state[3][q+2]};
    auto first=firstHit(boxes,origin,normalized(ray));
    require(first.valid&&first.id==2&&!cameraVisible(boxes,first)&&patch(first.point),"fixed actual-MAIN ray reaches first hidden tagged floor");
    for(double dx:{-.5,0.,.5}) for(double dy:{-.5,0.,.5}) {
        V3 incident=normalized({(2*(x+.5+dx)/size-1)/f,(2*(y+.5+dy)/size-1)/f,-1});
        double t=-.5/incident[1];V3 p=add({0,0,0},incident,t);constexpr double ratio=1/1.333;
        V3 r={incident[0]*ratio,-std::sqrt(1-ratio*ratio*(1-incident[1]*incident[1])),incident[2]*ratio};
        auto hit=firstHit(boxes,p,r);require(hit.valid&&hit.id==2&&patch(hit.point)&&!cameraVisible(boxes,hit),"independent full pixel footprint occlusion");
    }
    for(int yy=0;yy<4;yy++) for(int zz=0;zz<24;zz++) for(int xx=0;xx<16;xx++) {
        int p=((yy*24+zz)*16+xx)*4;V3 center={-8+xx+.5,-4+yy+.5,-24+zz+.5};
        if(cells[p]==3&&patch(center)) source[p+1]=.43f;
    }
    glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,inputs[2]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,96,GL_RGBA,GL_FLOAT,source.data());
    save(out/"receiver-source-hidden-tag.rgba32f",source);auto changed=draw(hidden,false,"hidden-tag");
    auto positive=draw(visible,false,"visible-tag");int positiveQ=(60*size+64)*4;
    double gain=changed.colour[q+1]-neutral.colour[q+1],visibleGain=positive.colour[positiveQ+1]-neutral.colour[positiveQ+1];
    require(visibleGain>.01,"camera-visible material positive control");
    std::ofstream receipt(out/"result.txt");receipt<<std::setprecision(17)<<"fixedPixel="<<x<<","<<y<<"\nfirstTravel="<<first.travel<<"\nfirstPoint="<<first.point[0]<<","<<first.point[1]<<","<<first.point[2]<<"\nworldSourceSamplerLocation="<<worldSampler<<"\nhiddenGreenGain="<<gain<<"\nvisibleGreenGain="<<visibleGain<<"\nobserverC0MaxDifference="<<difference(neutral.colour,witness.colour)<<"\n";
    std::cout<<"Qualified fixed hidden first-floor pixel64,53; source sampler location "<<worldSampler<<"; green gain="<<gain<<"; visible positive="<<visibleGain<<'\n';
    if(gain<=.001) {std::cout<<"RED: production MAIN cannot receive the qualified camera-occluded material source (not yet a rendering fix).\n";return 2;}
    std::cout<<"PASS bounded occluded material-response tracer bullet; full transport/natural acceptance still required.\n";return 0;
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=3||fs::exists(argv[2])) throw std::runtime_error("usage: water_occluded_receiver_main shaders NEW-artifact-dir");
        if(std::system("pgrep -x java >/dev/null")!=256) throw std::runtime_error("Close live Java client before native GPU validation");
        occluded::Context context;return occluded::probe(argv[1],argv[2]);
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
