// Independent bounded native probe of the REAL precipitation shaders (gbuffers_weather.vsh/.fsh and
// lib/weather_light.glsl) on an OpenGL compatibility context. Nothing is mocked to succeed:
//   * the light list/field are produced by the pack's own shadow_*.vsh capture + shadowcomp1.csh dispatch
//     (tools/local-lights-probe.h harness, reused read-only through tools/glcheck.cpp),
//   * the weather program is the pack's own vertex + fragment shader, a one-pixel (or 1280x720 timing) quad
//     placed at a camera-relative point through the legacy projection matrix; the projection is the ONLY thing that
//     is faked, so `position` reaches the fragment shader exactly as the vertex shader derives it,
//   * the previous formula is the unmodified rc3 gbuffers_weather.fsh, run in the same rig.
// The CPU reference below restates the physical model independently (C++ double precision).
// Photometric strengths are heuristic; nothing here is a physical measurement. Timings are GPU-harness
// timings of a synthetic quad, NOT Minecraft frame times.
// usage: weather_light_probe <staging shaders dir> <baseline rc3 shaders dir> <out.json>
#define main aqualumen_glcheck_main
#include "../../../tools/glcheck.cpp"
#undef main
#include <numeric>
#include <random>
using namespace aqualumenLocalLights;

namespace wl {
struct Result {std::string name;bool pass;std::string detail;};
static std::vector<Result> results;
struct J {
    std::ostringstream o;bool first=true;
    J& sep() {if(!first) o<<",";first=false;return *this;}
    J& n(const char* k,double v) {sep();o<<"\""<<k<<"\":";if(std::isfinite(v)) o<<std::setprecision(6)<<v;else o<<"null";return *this;}
    J& s(const char* k,const std::string& v) {sep();o<<"\""<<k<<"\":\""<<v<<"\"";return *this;}
    J& a(const char* k,const std::vector<double>& v) {sep();o<<"\""<<k<<"\":[";for(size_t i=0;i<v.size();i++) {if(i) o<<",";o<<std::setprecision(6)<<(std::isfinite(v[i])?v[i]:0.0);}o<<"]";return *this;}
    std::string str() const {return "{"+o.str()+"}";}
};
static void record(const std::string& name,bool pass,const J& detail) {
    results.push_back({name,pass,detail.str()});
    std::cout<<(pass?"PASS ":"FAIL ")<<name<<"  "<<detail.str()<<"\n";
}
static double sstep(double a,double b,double x) {double t=std::clamp((x-a)/(b-a),0.0,1.0);return t*t*(3-2*t);}
static D3 sub(const D3& a,const D3& b) {return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static double dot3(const D3& a,const D3& b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static double len3(const D3& a) {return std::sqrt(dot3(a,a));}
static D3 unit(const D3& a) {double l=len3(a);return {a[0]/l,a[1]/l,a[2]/l};}
static double lum(const std::array<double,3>& c) {return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2];}

// ------------------------------------------------------------------ CPU restatement of the model
static double hg(double mu,double g) {double d=std::max(1+g*g-2*g*mu,1e-4);return (1-g*g)/(4*M_PI*d*std::sqrt(d));}
static double rainPhase(double mu) {return 0.10*hg(mu,0.85)+0.30*hg(mu,0.50)+0.45*hg(mu,0.0)+0.15*hg(mu,-0.35);}
static double snowPhase(double mu) {return 0.20*hg(mu,0.60)+0.50*hg(mu,0.0)+0.30*hg(mu,-0.30);}
static double phase(double mu,double liquid) {mu=std::clamp(mu,-1.0,1.0);return snowPhase(mu)*(1-liquid)+rainPhase(mu)*liquid;}
static const std::array<double,3> WARM={1.0,0.49,0.19},SOUL={0.11,0.65,1.0},SEA={0.65,1.0,0.90},REDSTONE={1.0,0.085,0.035};
// Lamp contribution before the soft luminance ceiling. `vis` is the traced RGB visibility (1 = clear).
static std::array<double,3> lampModel(const D3& particle,const D3& lamp,const D3& cam,int level,const std::array<double,3>& tint,
                                      const std::array<double,3>& vis,double liquid,double* muOut=nullptr) {
    const D3 delta=sub(lamp,particle);const double d2=dot3(delta,delta),d=std::sqrt(d2);
    const D3 rel=sub(lamp,cam);const double far_=std::max({std::abs(rel[0]),std::abs(rel[1]),std::abs(rel[2])});
    const double strength=1-sstep(19,24,far_),falloff=1-sstep(0.7*14.0,14.0,d);
    const double e=11.0*std::pow(level/14.0,2.0)*strength*falloff/(0.38+d2);
    const double mu=dot3(unit(sub(particle,cam)),unit(delta));if(muOut) *muOut=mu;
    const double k=e*M_PI*0.66*phase(mu,liquid);
    return {tint[0]*vis[0]*k,tint[1]*vis[1]*k,tint[2]*vis[2]*k};
}
static std::array<double,3> softLimit(std::array<double,3> c) {double s=1+lum(c)/16.0;for(auto& v:c) v/=s;return c;}
static double coverageCPU(const D3& particle,const D3& cam) {
    const D3 r=sub(particle,cam);return 1-sstep(19,24,std::max({std::abs(r[0]),std::abs(r[1]),std::abs(r[2])}));
}

// ------------------------------------------------------------------ rig
struct Shot {
    D3 pos={0,0,0},cam={0,0,0};
    bool snow=false;double liquidTexel=-1;   // liquidTexel: override flake colour so liquid==that value (rain: 1, snow: 0)
    float lmx=0,lmy=0;
    D3 sun={0,-1,0};bool shadowed=false,cloudShadow=false;float rain=1;
    std::array<float,3> sky={0,0,0};float alpha=-1;
};
struct Out {double r,g,b,a;std::array<double,3> rgb() const {return {r,g,b};}};
struct Rig {
    GLuint fbo=0,target=0,flake=0,skyLut=0,irr=0,shadow[2]={0,0},bigFbo=0,bigTarget=0;
    World* w=nullptr;
    static GLuint tex(GLenum internal,int ww,int hh,GLenum fmt,GLenum type,const void* data) {
        GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexImage2D(GL_TEXTURE_2D,0,internal,ww,hh,0,fmt,type,data);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return t;
    }
    void init(World& world) {
        w=&world;
        glGenFramebuffers(1,&fbo);target=tex(GL_RGBA32F,1,1,GL_RGBA,GL_FLOAT,nullptr);
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,target,0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"weather rig framebuffer incomplete");
        glGenFramebuffers(1,&bigFbo);bigTarget=tex(GL_RGBA32F,1280,720,GL_RGBA,GL_FLOAT,nullptr);
        glBindFramebuffer(GL_FRAMEBUFFER,bigFbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,bigTarget,0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"weather timing framebuffer incomplete");
        glBindFramebuffer(GL_FRAMEBUFFER,0);
        flake=tex(GL_RGBA32F,2,2,GL_RGBA,GL_FLOAT,nullptr);skyLut=tex(GL_RGBA32F,64,32,GL_RGBA,GL_FLOAT,nullptr);irr=tex(GL_RGBA32F,64,74,GL_RGBA,GL_FLOAT,nullptr);
        for(int i=0;i<2;i++) {
            float depth=i?0.0f:1.0f;shadow[i]=tex(GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,GL_FLOAT,&depth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        }
    }
    static constexpr std::array<float,3> TRANS={0.80f,0.75f,0.65f};
    void upload(const Shot& s) {
        // gtexture: rain = blue streak, snow = white flake; four identical texels
        std::array<float,4> c=s.snow?std::array<float,4>{1,1,1,0.8f}:std::array<float,4>{0.30f,0.45f,1.0f,0.6f};
        if(s.liquidTexel>=0) {   // blue-red difference giving smoothstep(0.06,0.36,x)==liquidTexel for 0, 0.5 or 1
            const float x=s.liquidTexel<=0?0.0f:s.liquidTexel>=1?0.7f:0.21f;c={0.2f,0.4f,0.2f+x,0.6f};
        }
        if(s.alpha>=0) c[3]=s.alpha;
        std::vector<float> t;for(int i=0;i<4;i++) t.insert(t.end(),c.begin(),c.end());
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,flake);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,2,2,GL_RGBA,GL_FLOAT,t.data());
        std::vector<float> sky(64*32*4,0);   // the reserved final row, first texel, is the direct solar transmission
        const size_t k=(size_t(31)*64)*4;sky[k]=TRANS[0];sky[k+1]=TRANS[1];sky[k+2]=TRANS[2];sky[k+3]=1;
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,skyLut);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,32,GL_RGBA,GL_FLOAT,sky.data());
        std::vector<float> irrad(64*74*4,0);   // rows 0..9 face diffuse, rows 10.. solar-transmission plane map
        for(int x=0;x<6;x++) for(int c2=0;c2<3;c2++) irrad[size_t(x)*4+size_t(c2)]=s.sky[size_t(c2)];
        if(!s.cloudShadow) for(int y=10;y<74;y++) for(int x=0;x<64;x++) {size_t b=(size_t(y)*64+size_t(x))*4;irrad[b]=TRANS[0];irrad[b+1]=TRANS[1];irrad[b+2]=TRANS[2];irrad[b+3]=1;}
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,irr);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,74,GL_RGBA,GL_FLOAT,irrad.data());
        glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,shadow[s.shadowed?1:0]);
        glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,w->list);
        glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,w->field);
    }
    void state(GLuint prog,const Shot& s) {
        const float I[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        const float S[16]={0.01f,0,0,0,0,0.01f,0,0,0,0,0.01f,0,0,0,0,1};
        glUseProgram(prog);
        auto mat=[&](const char* n,const float* m) {GLint l=glGetUniformLocation(prog,n);if(l>=0) glUniformMatrix4fv(l,1,GL_FALSE,m);};
        auto f1=[&](const char* n,float v) {GLint l=glGetUniformLocation(prog,n);if(l>=0) glUniform1f(l,v);};
        auto i1=[&](const char* n,int v) {GLint l=glGetUniformLocation(prog,n);if(l>=0) glUniform1i(l,v);};
        auto v3=[&](const char* n,double a,double b,double c) {GLint l=glGetUniformLocation(prog,n);if(l>=0) glUniform3f(l,float(a),float(b),float(c));};
        mat("gbufferModelView",I);mat("gbufferModelViewInverse",I);mat("gbufferProjection",I);mat("gbufferProjectionInverse",I);
        mat("shadowProjection",I);mat("shadowModelView",S);
        v3("cameraPosition",s.cam[0],s.cam[1],s.cam[2]);
        const D3 sun=unit(s.sun);v3("sunPosition",sun[0],sun[1],sun[2]);v3("shadowLightPosition",sun[0],sun[1],sun[2]);
        i1("aqualumenDimension",0);i1("isEyeInWater",0);f1("rainStrength",s.rain);f1("wetness",1.0f);
        i1("gtexture",0);i1("colortex6",1);i1("shadowtex0",2);i1("colortex11",3);i1("aqualumenLightList",4);i1("aqualumenLightField",5);
    }
    // one-pixel particle at s.pos (world coordinates; camera-relative position = pos-cam)
    Out draw(GLuint prog,const Shot& s) {
        upload(s);state(prog,s);
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glDisable(GL_ALPHA_TEST);glViewport(0,0,1,1);
        glClearColor(0,0,0,-1);glClear(GL_COLOR_BUFFER_BIT);
        const D3 p=sub(s.pos,s.cam);const double e=1e-3;
        // projection maps the quad around p to the whole viewport; modelview and every pack matrix are identity,
        // so the vertex shader's `position` is p itself.
        const double m[16]={1/e,0,0,0,0,1/e,0,0,0,0,1/e,0,-p[0]/e,-p[1]/e,-p[2]/e,1};
        float mf[16];for(int i=0;i<16;i++) mf[i]=float(m[i]);
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(mf);glMatrixMode(GL_MODELVIEW);glLoadIdentity();resetTextureMatrices();
        glColor4f(1,1,1,1);glMultiTexCoord2f(GL_TEXTURE1,s.lmx,s.lmy);
        glBegin(GL_QUADS);
        for(int c=0;c<4;c++) {const double ex=(c==0||c==3)?-1:1,ey=(c<2)?-1:1;glMultiTexCoord2f(GL_TEXTURE0,0.5f,0.5f);glVertex3f(float(p[0]+ex*e),float(p[1]+ey*e),float(p[2]));}
        glEnd();
        float px[4];glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,px);
        glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);glActiveTexture(GL_TEXTURE0);
        require(glGetError()==GL_NO_ERROR,"GL error during weather draw");
        for(float f:px) require(std::isfinite(f),"nonfinite weather output");
        // undo the shader's own 12 % flake tint so the result is the incident radiance
        std::array<float,4> c=s.snow?std::array<float,4>{1,1,1,0.8f}:std::array<float,4>{0.30f,0.45f,1.0f,0.6f};
        if(s.liquidTexel>=0) {const float x=s.liquidTexel<=0?0.0f:s.liquidTexel>=1?0.7f:0.21f;c={0.2f,0.4f,0.2f+x,0.6f};}
        double f[3];for(int i=0;i<3;i++) f[i]=1+0.12*(double(c[size_t(i)])-1);
        return {px[0]/f[0],px[1]/f[1],px[2]/f[2],px[3]};
    }
    // full-viewport timing quad; the position varies over +-4 m around s.pos
    double timeQuad(GLuint prog,const Shot& s,int repeats) {
        upload(s);state(prog,s);
        glBindFramebuffer(GL_FRAMEBUFFER,bigFbo);glDrawBuffer(GL_COLOR_ATTACHMENT0);
        glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glViewport(0,0,1280,720);
        const D3 p=sub(s.pos,s.cam);const double e=4.0;
        const double m[16]={1/e,0,0,0,0,1/e,0,0,0,0,1/e,0,-p[0]/e,-p[1]/e,-p[2]/e,1};
        float mf[16];for(int i=0;i<16;i++) mf[i]=float(m[i]);
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(mf);glMatrixMode(GL_MODELVIEW);glLoadIdentity();resetTextureMatrices();
        glColor4f(1,1,1,1);glMultiTexCoord2f(GL_TEXTURE1,s.lmx,s.lmy);
        std::vector<double> ms;
        for(int r=0;r<repeats+1;r++) {
            GLuint q;glGenQueries(1,&q);glBeginQuery(GL_TIME_ELAPSED,q);
            glBegin(GL_QUADS);
            for(int c=0;c<4;c++) {const double ex=(c==0||c==3)?-1:1,ey=(c<2)?-1:1;glMultiTexCoord2f(GL_TEXTURE0,0.5f,0.5f);glVertex3f(float(p[0]+ex*e),float(p[1]+ey*e),float(p[2]));}
            glEnd();glEndQuery(GL_TIME_ELAPSED);
            GLuint64 ns=0;glGetQueryObjectui64v(q,GL_QUERY_RESULT,&ns);glDeleteQueries(1,&q);if(r) ms.push_back(double(ns)*1e-6);
        }
        glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);
        std::sort(ms.begin(),ms.end());return ms[ms.size()/2];
    }
};
constexpr std::array<float,3> Rig::TRANS;

static std::string fileHash(const fs::path& p) {
    std::string cmd="sha256sum '"+p.string()+"'";FILE* f=popen(cmd.c_str(),"r");char b[256]={0};if(f) {if(!fgets(b,sizeof b,f)) b[0]=0;pclose(f);}
    return std::string(b).substr(0,64);
}
}  // namespace wl

using namespace wl;

int main(int argc,char** argv) {
    int exitCode=0;
    try {
        if(argc>=3&&std::string(argv[1])=="--glcheck") return aqualumen_glcheck_main(argc-1,argv+1);   // original harness, same binary
        if(argc<4) throw std::runtime_error("usage: weather_light_probe <staging shaders> <baseline rc3 shaders> <out.json>");
        const fs::path root=argv[1],baseRoot=argv[2],outPath=argv[3];
        // ---- EGL: prefer the NVIDIA device; never silently fall back to software
        auto getPlatform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
        EGLDeviceEXT devices[8];EGLint ndev=0;
        if(!query||!query(8,devices,&ndev)||ndev==0) throw std::runtime_error("No EGL device");
        EGLDisplay display=EGL_NO_DISPLAY;EGLContext context=EGL_NO_CONTEXT;EGLSurface surface=EGL_NO_SURFACE;std::string rendererSeen;
        for(int i=0;i<ndev&&context==EGL_NO_CONTEXT;i++) {
            EGLDisplay d=getPlatform(EGL_PLATFORM_DEVICE_EXT,devices[i],nullptr);
            if(!eglInitialize(d,nullptr,nullptr)) continue;
            eglBindAPI(EGL_OPENGL_API);
            EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
            EGLConfig config;EGLint count=0;eglChooseConfig(d,cfg,&config,1,&count);if(!count) continue;
            EGLint sa[]={EGL_WIDTH,64,EGL_HEIGHT,64,EGL_NONE};EGLSurface sf=eglCreatePbufferSurface(d,config,sa);
            EGLint ca[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
            EGLContext c=eglCreateContext(d,config,EGL_NO_CONTEXT,ca);
            if(c==EGL_NO_CONTEXT||!eglMakeCurrent(d,sf,sf,c)) continue;
            rendererSeen=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
            if(rendererSeen.find("NVIDIA")==std::string::npos) {eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(d,c);continue;}
            display=d;context=c;surface=sf;
        }
        if(context==EGL_NO_CONTEXT) throw std::runtime_error("No NVIDIA EGL device available (last renderer: "+rendererSeen+"); refusing to report software results as NVIDIA");
        const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER)),version=reinterpret_cast<const char*>(glGetString(GL_VERSION));
        std::cout<<"Renderer: "<<renderer<<"\nGL: "<<version<<"\n";

        // ---- programs: REAL new weather pass, real helper, and the unmodified rc3 weather pass (previous formula)
        GLuint progNew=linkPackProgram(root,"gbuffers_weather"),progOld=linkPackProgram(baseRoot,"gbuffers_weather");
        auto samplerCount=[&](GLuint p) {GLint n=0,cnt=0;glGetProgramiv(p,GL_ACTIVE_UNIFORMS,&n);
            for(GLint i=0;i<n;i++) {GLenum t=0;GLint sz=0;char nm[128];GLsizei l=0;glGetActiveUniform(p,GLuint(i),128,&l,&sz,&t,nm);cnt+=isSamplerType(t)?sz:0;}return cnt;};
        {J d;d.n("samplers_new",samplerCount(progNew)).n("samplers_old",samplerCount(progOld)).n("max_texture_units",glInteger(GL_MAX_TEXTURE_IMAGE_UNITS));
         record("compile.real_weather_program_links_and_fits_limits",samplerCount(progNew)<=glInteger(GL_MAX_TEXTURE_IMAGE_UNITS)-0&&samplerCount(progNew)<=16,d);}
        const std::string helperSrc=fs::exists(root/"lib/weather_light.glsl")?slurp(root/"lib/weather_light.glsl"):"";
        std::smatch sm;int configuredSources=4;
        if(std::regex_search(helperSrc,sm,std::regex("#define\\s+WEATHER_LIGHT_SOURCES\\s+(\\d+)"))) configuredSources=std::stoi(sm[1]);

        World world;world.init(root);
        Rig rig;rig.init(world);
        const std::string common="#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/weather_light.glsl",root);
        const std::string data="uniform sampler2D probeData;out vec4 probeOut;\nvec4 q(int i,int k){return texelFetch(probeData,ivec2(i,k),0);}\n";
        const std::string vsh="#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
        GLuint helperProg=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2);int traced;"
            "vec3 r=weatherLampLight(a.xyz,normalize(b.xyz),c.x,b.w,traced);probeOut=vec4(r,float(traced));}","weather-helper");
        GLuint phaseProg=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);float mu=q(i,0).x;"
            "probeOut=vec4(weatherRainPhase(mu),weatherSnowPhase(mu),weatherPhase(mu,q(i,0).y),weatherHG(mu,0.5));}","weather-phase");

        const D3 C0={1003.25,71.5,-2049.75},LP={1005.5,71.64,-2049.5};
        auto shot=[&](D3 pos) {Shot s;s.pos=pos;s.cam=C0;return s;};
        auto build=[&](const std::vector<Block>& scene) {world.build(scene,C0);};
        auto run=[&](GLuint prog,const Shot& s) {return rig.draw(prog,s);};
        const std::vector<Block> oneTorch={torch(1005,71,-2050)};
        auto near=[](double a,double b,double rel,double abs=0) {return std::abs(a-b)<=abs+rel*std::max(std::abs(a),std::abs(b));};
        auto chroma=[](std::array<double,3> c) {double s=c[0]+c[1]+c[2];return std::array<double,3>{c[0]/s,c[1]/s,c[2]/s};};
        auto vec=[](std::array<double,3> c) {return std::vector<double>{c[0],c[1],c[2]};};

        // ================================================================ 1. normalized phase functions (GPU helper)
        {
            const int N=4001;std::vector<float> in(size_t(N)*16,0),out;
            for(int i=0;i<N;i++) {in[size_t(i)*4]=float(-1+2.0*i/(N-1));in[size_t(i)*4+1]=0.5f;}
            world.runProgram(phaseProg,in,N,out,C0);
            double ir=0,is=0,im=0,ih=0,minv=1e9,maxErr=0;
            for(int i=0;i+1<N;i++) {
                const double dm=2.0/(N-1);
                ir+=0.5*(out[size_t(i)*4]+out[size_t(i+1)*4])*dm;is+=0.5*(out[size_t(i)*4+1]+out[size_t(i+1)*4+1])*dm;
                im+=0.5*(out[size_t(i)*4+2]+out[size_t(i+1)*4+2])*dm;ih+=0.5*(out[size_t(i)*4+3]+out[size_t(i+1)*4+3])*dm;
            }
            for(int i=0;i<N;i++) {
                const double mu=-1+2.0*i/(N-1);minv=std::min({minv,double(out[size_t(i)*4]),double(out[size_t(i)*4+1])});
                maxErr=std::max(maxErr,std::abs(out[size_t(i)*4]-rainPhase(mu))/rainPhase(mu));maxErr=std::max(maxErr,std::abs(out[size_t(i)*4+1]-snowPhase(mu))/snowPhase(mu));
            }
            ir*=2*M_PI;is*=2*M_PI;im*=2*M_PI;ih*=2*M_PI;
            const double rf=out[size_t(N-1)*4]/out[0],sf=out[size_t(N-1)*4+1]/out[1],mf=out[size_t(N-1)*4+2]/out[2];   // mix at liquid=0.5
            J d;d.n("sphere_integral_rain",ir).n("sphere_integral_snow",is).n("sphere_integral_mix",im).n("sphere_integral_hg",ih).n("min_value",minv).n("max_rel_err_vs_cpu",maxErr).n("rain_forward_over_back",rf).n("snow_forward_over_back",sf).n("mixture_half_forward_over_back",mf);
            record("phase.normalized_and_matches_independent_cpu",std::abs(ir-1)<2e-3&&std::abs(is-1)<2e-3&&std::abs(im-1)<2e-3&&std::abs(ih-1)<2e-3&&minv>0&&maxErr<2e-4,d);
            record("phase.rain_forward_lobe_vs_snow_diffuse",rf>=8&&sf>=1.4&&sf<=3&&sf<rf/3&&mf>sf*1.05&&mf<rf*0.95,d);
        }

        // ================================================================ 2. rig validity: rc3 shader reproduces its own hard-wired formula
        {
            build({});Shot s=shot({1008,71.64,-2049.5});s.lmx=0.8f;
            Out o=run(progOld,s);const double k=2.0*std::pow(0.8,3);
            J d;d.a("old_gpu",{o.r,o.g,o.b}).a("old_formula",{k,0.56*k,0.25*k});
            record("rig.old_shader_equals_hardwired_formula",near(o.r,k,1e-3,1e-4)&&near(o.g,0.56*k,1e-3,1e-4)&&near(o.b,0.25*k,1e-3,1e-4),d);
        }
        // ================================================================ 3. coverage / discard unchanged
        {
            build({});double maxDiff=0;int checked=0;bool discardParity=true;
            for(bool snow:{false,true}) for(float a:{0.0f,0.003f,0.0105f,0.0108f,0.02f,0.2f,0.7f,1.0f}) {
                Shot s=shot({1008,71.64,-2049.5});s.snow=snow;s.alpha=a;s.lmx=0.6f;s.lmy=1;s.sun={0.3,0.8,0.2};
                Out o=run(progOld,s),n=run(progNew,s);maxDiff=std::max(maxDiff,std::abs(o.a-n.a));checked++;
                discardParity&=((o.a<0)==(n.a<0));
            }
            J d;d.n("cases",checked).n("max_alpha_difference",maxDiff);
            record("coverage.alpha_and_discard_identical_to_rc3",maxDiff==0&&discardParity,d);
        }

        // ================================================================ 4. lamp type: off / warm / soul / palette
        {
            // off lamp: written nowhere, so the particle with no stale column light is black; with stale column light it is neutral
            build({torch(1005,71,-2050,0)});
            Shot s=shot({1008.5,71.64,-2049.5});
            Out off0=run(progNew,s);s.lmx=0.7f;Out off7=run(progNew,s),oldOff7=run(progOld,s);
            J d;d.a("new_lmx0",vec(off0.rgb())).a("new_lmx0.7",vec(off7.rgb())).a("old_lmx0.7",vec(oldOff7.rgb()));
            record("lamp.off_torch_is_dark_and_never_orange",lum(off0.rgb())<1e-6&&off7.r<=off7.b*1.05&&lum(off7.rgb())<0.05&&lum(off7.rgb())<0.06*lum(oldOff7.rgb()),d);
        }
        {
            struct K {const char* name;int id,level;std::array<double,3> tint;};
            const std::vector<K> kinds={{"torch",10100,14,WARM},{"soul_torch",10105,10,SOUL},{"lantern",10110,15,WARM},{"soul_lantern",10111,10,SOUL},
                {"sea_lantern",10115,15,SEA},{"redstone_torch",10116,7,REDSTONE},{"campfire",10112,15,WARM}};
            double worstChroma=0;std::ostringstream names;bool ok=true;J d;
            for(auto& k:kinds) {
                const int kind=k.id-10099;
                Block b=blk(1005,71,-2050,k.id,k.level);build({b});
                const D3 lamp={1005+kindOffset(kind)[0],71+kindOffset(kind)[1],-2050+kindOffset(kind)[2]};
                Shot s=shot({lamp[0]+3.0,lamp[1],lamp[2]});s.lmx=0;
                Out o=run(progNew,s);
                const auto ref=softLimit(lampModel(s.pos,lamp,C0,k.level,k.tint,{1,1,1},1.0));
                const auto cg=chroma(o.rgb()),cr=chroma(ref);
                double err=0;for(int i=0;i<3;i++) err=std::max(err,std::abs(cg[i]-cr[i]));worstChroma=std::max(worstChroma,err);
                const bool mag=near(lum(o.rgb()),lum(ref),0.04);
                ok&=err<0.01&&mag;
                d.a(k.name,{o.r,o.g,o.b,ref[0],ref[1],ref[2]});
                if(k.tint==SOUL) ok&=o.b>o.r*3&&o.r<o.g;
                if(k.tint==WARM) ok&=o.r>o.b*3;
            }
            d.n("worst_chromaticity_error",worstChroma);
            record("lamp.palette_kind_colour_and_strength_vs_cpu_model",ok,d);
        }
        // ================================================================ 5. unoccluded torch quantitative + stone, stained glass, glowstone self
        {
            build(oneTorch);Shot s=shot({1008.5,71.64,-2049.5});s.lmx=0;Out clear=run(progNew,s);
            const auto ref=softLimit(lampModel(s.pos,LP,C0,14,WARM,{1,1,1},1.0));
            J d;d.a("gpu",vec(clear.rgb())).a("cpu_reference",vec(ref));
            record("lamp.torch_clear_sight_matches_cpu_reference",near(clear.r,ref[0],0.03)&&near(clear.g,ref[1],0.03)&&near(clear.b,ref[2],0.03),d);
            // stone between receiver and lamp
            build({torch(1005,71,-2050),stone(1007,71,-2050)});
            Out hidden0=run(progNew,s);s.lmx=0.5f;Out hidden5=run(progNew,s);
            build(oneTorch);Out open5=run(progNew,s),old5=run(progOld,s);
            // sideways control: the same stone elsewhere must not occlude
            build({torch(1005,71,-2050),stone(1007,71,-2048)});Out side=run(progNew,s);
            J d2;d2.a("blocked_lmx0",vec(hidden0.rgb())).a("blocked_lmx0.5",vec(hidden5.rgb())).a("open_lmx0.5",vec(open5.rgb())).a("old_lmx0.5",vec(old5.rgb())).a("stone_off_axis",vec(side.rgb()));
            record("lamp.stone_between_receiver_and_lamp_blocks_it",lum(hidden0.rgb())<1e-6&&lum(hidden5.rgb())<0.08*lum(open5.rgb())&&hidden5.r<=hidden5.b*1.05&&near(side.r,open5.r,1e-4,1e-6),d2);
        }
        {
            // stained glass: one block of dyed glass transmits RGB per channel (pack table, independent restatement)
            const double glass[3][3]={{.85,.20,.16},{.19,.36,.86},{.25,.60,.19}};   // red(14), blue(11), green(13)
            const int dye[3]={14,11,13};bool ok=true;J d;
            build(oneTorch);Shot s=shot({1008.5,71.64,-2049.5});s.lmx=0;Out clear=run(progNew,s);
            for(int g=0;g<3;g++) {
                build({torch(1005,71,-2050),blk(1007,71,-2050,10400+dye[g])});Out o=run(progNew,s);
                double dev=0;std::vector<double> ratios;
                for(int c=0;c<3;c++) {const double r=o.rgb()[size_t(c)]/clear.rgb()[size_t(c)];ratios.push_back(r);dev=std::max(dev,std::abs(r/glass[g][c]-1));}
                ok&=dev<0.12;d.a(g==0?"red_glass_ratio":g==1?"blue_glass_ratio":"green_glass_ratio",ratios).n(g==0?"red_dev":g==1?"blue_dev":"green_dev",dev);
            }
            record("lamp.stained_glass_tints_per_channel",ok,d);
        }
        {
            // a solid light-emitting cube must not shadow itself (goal-cell exclusion)
            build({blk(1005,71,-2050,10114,15)});
            const D3 lamp={1005.5,71.5,-2049.5};Shot s=shot({1008.5,71.5,-2049.5});s.lmx=0;
            Out o=run(progNew,s);const auto ref=softLimit(lampModel(s.pos,lamp,C0,15,WARM,{1,1,1},1.0));
            J d;d.a("gpu",vec(o.rgb())).a("cpu",vec(ref));
            record("lamp.solid_emitter_cell_does_not_self_shadow",near(o.r,ref[0],0.05),d);
        }
        // ================================================================ 6. carried lamp
        {
            const auto items=parseItemIds(root);auto it=items.find("torch");require(it!=items.end(),"item.properties lacks minecraft:torch");
            Carried c;c.item=it->second;c.level=14;c.firstPerson=true;c.rightHanded=true;
            world.buildCarried({},C0,c);Snap snap=carriedSnapshot(world,C0);
            require(snap.held.size()==1,"expected exactly one held record");
            const D3 hand=snap.held[0].world;
            Shot s=shot({hand[0]+0.8,hand[1]+0.1,hand[2]-0.3});s.lmx=0;
            Out near_=run(progNew,s);s.pos={hand[0]-0.2,hand[1]+3.0,hand[2]-6.0};Out far_=run(progNew,s);
            // wall between hand and a particle behind it
            const D3 behind={hand[0],hand[1],hand[2]-4.0};
            std::vector<Block> wall;for(int x=1002;x<=1004;x++) for(int y=70;y<=72;y++) wall.push_back(stone(x,y,int(std::floor(hand[2]-2.0))));
            world.buildCarried(wall,C0,c);Shot sb=shot(behind);sb.lmx=0;Out blocked=run(progNew,sb);
            world.buildCarried({},C0,c);Out open=run(progNew,sb);
            world.build({},C0);Out none=run(progNew,sb);Shot sn=shot({hand[0]+0.8,hand[1]+0.1,hand[2]-0.3});Out noneNear=run(progNew,sn);
            const auto ref=softLimit(lampModel({hand[0]+0.8,hand[1]+0.1,hand[2]-0.3},hand,C0,14,WARM,{1,1,1},1.0));
            J d;d.a("hand_world",{hand[0],hand[1],hand[2]}).a("near_gpu",vec(near_.rgb())).a("near_cpu",vec(ref)).a("far",vec(far_.rgb())).a("behind_open",vec(open.rgb())).a("behind_wall",vec(blocked.rgb())).a("no_carried_near",vec(noneNear.rgb())).a("no_carried_behind",vec(none.rgb()));
            record("carried.hand_torch_lights_nearby_particle_like_cpu_model",near(near_.r,ref[0],0.05)&&near_.r>near_.b*3&&lum(noneNear.rgb())<1e-6,d);
            // hand pressed against a wall: the published anchor stays clear of it and an open-side particle is still lit
            std::vector<Block> pressed;for(int x=1002;x<=1004;x++) for(int y=70;y<=72;y++) pressed.push_back(stone(x,y,int(std::floor(hand[2]-0.25))));
            world.buildCarried(pressed,C0,c);Snap snap2=carriedSnapshot(world,C0);require(snap2.held.size()==1,"pressed hand: expected one held record");
            const D3 anchor=snap2.held[0].world;Shot sp=shot({anchor[0]+0.4,anchor[1]+0.05,anchor[2]+0.3});sp.lmx=0;Out pr=run(progNew,sp);
            const auto refP=softLimit(lampModel(sp.pos,anchor,C0,14,WARM,{1,1,1},1.0));
            Shot sw=shot({anchor[0],anchor[1],anchor[2]-1.5});sw.lmx=0;Out beyond=run(progNew,sw);
            J dp;dp.a("anchor",{anchor[0],anchor[1],anchor[2]}).a("open_side_gpu",vec(pr.rgb())).a("open_side_cpu",vec(refP)).a("beyond_wall",vec(beyond.rgb()));
            // the finite emitter disk (radius 0.13) touches the wall, so a wall penumbra of one to two of three taps is expected, never full or zero
            dp.n("open_side_fraction_of_unoccluded",pr.r/refP[0]);
            record("carried.anchor_against_wall_keeps_light_with_wall_penumbra",pr.r>=0.25*refP[0]&&pr.r<=1.0001*refP[0]&&lum(beyond.rgb())<1e-6&&anchor[2]>std::floor(hand[2]-0.25)+1.0-0.05,dp);
            record("carried.distance_wall_and_removal",lum(far_.rgb())<0.2*lum(near_.rgb())&&lum(blocked.rgb())<1e-6&&lum(open.rgb())>1e-3&&lum(none.rgb())<1e-6,d);
        }
        // ================================================================ 7. angle: forward / side / back, rain and snow, mixture
        {
            // camera on the lamp's row so eye, particle and lamp are exactly collinear for the forward and back spots
            const D3 C1={1002.25,71.64,-2049.5};world.build(oneTorch,C1);
            struct A {const char* name;D3 pos;} spots[3]={{"forward_lamp_beyond_particle",{1004.4,71.64,-2049.5}},{"side",{1005.5,71.64,-2047.3}},{"back_lamp_on_viewer_side",{1006.6,71.64,-2049.5}}};
            double rainVal[3],snowVal[3],midVal[3];bool ok=true;J d;
            for(int i=0;i<3;i++) {
                Shot s=shot(spots[i].pos);s.cam=C1;s.lmx=0;
                Out r=run(progNew,s);s.snow=true;Out sn=run(progNew,s);s.snow=false;s.liquidTexel=0.5;Out mid=run(progNew,s);
                double mu=0;const auto rr=softLimit(lampModel(spots[i].pos,LP,C1,14,WARM,{1,1,1},1.0,&mu));
                const auto sr=softLimit(lampModel(spots[i].pos,LP,C1,14,WARM,{1,1,1},0.0));
                const auto mr=softLimit(lampModel(spots[i].pos,LP,C1,14,WARM,{1,1,1},0.5));
                rainVal[i]=r.g;snowVal[i]=sn.g;midVal[i]=mid.g;
                ok&=near(r.g,rr[1],0.03)&&near(sn.g,sr[1],0.03)&&near(mid.g,mr[1],0.03);
                d.a(spots[i].name,{mu,r.g,rr[1],sn.g,sr[1],mid.g,mr[1]});
            }
            const double rainRatio=rainVal[0]/rainVal[2],snowRatio=snowVal[0]/snowVal[2];
            d.n("rain_forward_over_back",rainRatio).n("snow_forward_over_back",snowRatio);
            record("angle.rain_snow_mixture_matches_cpu_and_forward_exceeds_back",ok&&rainRatio>=6&&snowRatio>=1.4&&snowRatio<rainRatio/3&&midVal[0]>snowVal[0]&&midVal[0]<rainVal[0]&&rainVal[1]<rainVal[0],d);
            // the same geometry with the previous formula: direction-blind
            Shot o=shot(spots[0].pos);o.cam=C1;o.lmx=0.9f;Out o1=run(progOld,o);o.pos=spots[2].pos;Out o2=run(progOld,o);
            J d2;d2.n("old_forward_over_back",o1.g/o2.g);record("angle.previous_formula_is_direction_blind",near(o1.g,o2.g,1e-4),d2);
        }
        // ================================================================ 8. distance
        {
            build(oneTorch);std::vector<double> ds={0.5,1,2,4,8,12,13.9,14.5,16},gpu,cpu;bool ok=true,mono=true;double prev=1e9;
            for(double dd:ds) {
                Shot s=shot({LP[0],LP[1],LP[2]+dd});s.lmx=0;Out o=run(progNew,s);
                const auto ref=softLimit(lampModel(s.pos,LP,C0,14,WARM,{1,1,1},1.0));
                gpu.push_back(o.g);cpu.push_back(ref[1]);ok&=near(o.g,ref[1],0.04,2e-5);
                if(dd>=1&&dd<=13.9) {mono&=o.g<prev;prev=o.g;}
                if(dd>=14.5) ok&=lum(o.rgb())<1e-6;
            }
            J d;d.a("distance_m",ds).a("gpu_green",gpu).a("cpu_green",cpu);
            record("distance.regularized_falloff_range_cutoff_and_monotone",ok&&mono,d);
            // very close pass: finite and soft-limited, never a singularity
            double worst=0;for(double dd:{0.0,0.02,0.05,0.1,0.2}) {Shot s=shot({LP[0]+dd,LP[1],LP[2]});s.lmx=0;worst=std::max(worst,lum(run(progNew,s).rgb()));}
            J d2;d2.n("worst_luminance_at_lamp",worst);record("distance.lamp_graze_is_soft_limited",worst<=16.0+1e-3&&std::isfinite(worst),d2);
        }
        // ================================================================ 9. daylight: Sun with terrain shadow, no cosine, no double count, local additivity
        {
            const D3 P={1006.0,74.0,-2046.0};
            struct SunCase {const char* name;D3 dir;};
            const std::vector<SunCase> suns={{"sun_high",{0.35,0.85,-0.40}},{"sun_low",{0.80,0.30,0.52}}};
            build({});bool ok=true;J d;
            Shot base=shot(P);base.lmy=1;base.lmx=0;base.sky={0.10f,0.14f,0.22f};
            Shot night=base;night.sun={0,-1,0};Out skyOnly=run(progNew,night);
            for(auto& sc:suns) {
                Shot s=base;s.sun=sc.dir;Out lit=run(progNew,s);s.shadowed=true;Out sh=run(progNew,s);s.shadowed=false;s.cloudShadow=true;Out cl=run(progNew,s);
                Shot o=base;o.sun=sc.dir;Out oldLit=run(progOld,o);
                const D3 ray=unit(sub(P,C0));const double mu=dot3(ray,unit(sc.dir));
                const double T[3]={0.80,0.75,0.65},SOLAR_[3]={18,17.6,17};
                std::array<double,3> ref{};for(int c=0;c<3;c++) ref[size_t(c)]=double(base.sky[size_t(c)])+SOLAR_[c]*T[c]*(1-0.85)*0.66*phase(mu,1.0);
                const double dev=std::abs(lit.g/ref[1]-1);
                ok&=dev<0.03&&lum(sh.rgb())>0&&near(sh.g,skyOnly.g,1e-5,1e-6)&&near(cl.g,skyOnly.g,1e-5,1e-6)&&lit.g>skyOnly.g*1.01;
                d.a(sc.name,{mu,lit.g,ref[1],oldLit.g,sh.g,cl.g,skyOnly.g}).n(sc.name[4]=='h'?"dev_high":"dev_low",dev);
            }
            record("daylight.sun_matches_cpu_obeys_terrain_and_cloud_shadow_and_sky_term_unchanged",ok,d);
            // the removed Lambert cosine: the old shader scales the Sun by sun.y, the new one does not
            Shot a=base,b=base;a.sun=unit(D3{0.35,0.85,-0.40});b.sun=unit(D3{0.35,0.85,-0.40});   // equal direction, equal phase
            Out hi=run(progNew,a);Out hiOld=run(progOld,a);
            Shot lowRay=base;lowRay.sun=unit(D3{0.8,0.3,0.52});
            J d2;d2.n("new_sun_term_high",hi.g-skyOnly.g).n("old_sun_term_high",hiOld.g-skyOnly.g);
            record("daylight.sky_term_identical_to_rc3_when_sun_is_down",[&]{Shot x=night;Out o=run(progOld,x),n=run(progNew,x);return near(o.g,n.g,1e-5,1e-6)&&near(o.r,n.r,1e-5,1e-6)&&near(o.b,n.b,1e-5,1e-6);}(),d2);
            // sky access gate: lightmap.y=0 removes sky and Sun but never a lamp
            build(oneTorch);Shot lamp=shot({1008.5,71.64,-2049.5});lamp.sky=base.sky;lamp.sun={0.35,0.85,-0.40};lamp.lmx=0;
            lamp.lmy=1;Out withSun=run(progNew,lamp);lamp.shadowed=true;Out shadowedLamp=run(progNew,lamp);lamp.lmy=0;Out noAccess=run(progNew,lamp);
            lamp.shadowed=false;lamp.sun={0,-1,0};lamp.sky={0,0,0};Out lampNight=run(progNew,lamp);
            build({});Shot noLamp=lamp;noLamp.lmy=1;noLamp.sky=base.sky;noLamp.sun={0.35,0.85,-0.40};Out sunNoLamp=run(progNew,noLamp);noLamp.shadowed=true;Out shNoLamp=run(progNew,noLamp);
            const double A=withSun.g-sunNoLamp.g,B=shadowedLamp.g-shNoLamp.g,Cn=lampNight.g;
            J d3;d3.a("lamp_term_sunlit_shadowed_night_noaccess",{A,B,Cn,noAccess.g});
            record("daylight.local_energy_not_multiplied_by_sun_visibility_or_sky_access",near(A,Cn,2e-4,1e-6)&&near(B,Cn,2e-4,1e-6)&&near(noAccess.g,Cn,2e-4,1e-6)&&Cn>0.01,d3);
            // horizon: Sun below the horizon contributes nothing even with a lit sky
            build({});Shot hz=base;hz.sun={0.9,-0.08,0.2};Out below=run(progNew,hz);
            J d4;d4.a("below_horizon",vec(below.rgb())).a("sky_only",vec(skyOnly.rgb()));
            record("daylight.sun_below_horizon_adds_nothing",near(below.g,skyOnly.g,1e-5,1e-6),d4);
        }
        // ================================================================ 10. unsupported source / grid edge / tile boundary
        {
            build({});Shot s=shot({1008.5,71.64,-2049.5});s.lmx=1.0f;Out unsup=run(progNew,s),old=run(progOld,s);
            J d;d.a("new",vec(unsup.rgb())).a("old",vec(old.rgb())).n("old_over_new_luminance",lum(old.rgb())/std::max(lum(unsup.rgb()),1e-9));
            record("fallback.unsupported_light_is_weak_and_not_orange",unsup.r<=unsup.b*1.05&&lum(unsup.rgb())<0.06&&lum(old.rgb())>25*lum(unsup.rgb()),d);
            // outside the 24 m grid the pack knows no sources: same neutral fallback, finite
            build(oneTorch);Shot f=shot({C0[0]+30,71.64,-2049.5});f.lmx=0.6f;Out out=run(progNew,f);
            const double want=0.66*0.08*std::pow(0.6,3);
            J d2;d2.a("gpu",vec(out.rgb())).n("expected_green",want*0.96);
            record("fallback.outside_grid_is_neutral_fallback",near(out.g,want*0.96,1e-3,1e-6)&&out.r<=out.b*1.05,d2);
        }
        auto sweep=[&](const char* name,std::vector<Block> scene,D3 lamp,D3 from,D3 to,int steps,double tol,int level=14) {
            build(scene);double worst=0,peak=0;std::vector<double> sampleGpu,sampleCpu;
            for(int i=0;i<=steps;i++) {
                const double t=double(i)/steps;D3 p={from[0]+(to[0]-from[0])*t,from[1]+(to[1]-from[1])*t,from[2]+(to[2]-from[2])*t};
                Shot s=shot(p);s.lmx=0;Out o=run(progNew,s);
                const auto ref=softLimit(lampModel(p,lamp,C0,level,WARM,{1,1,1},1.0));
                const double cov=coverageCPU(p,C0);peak=std::max(peak,cov*ref[1]);
                worst=std::max(worst,std::abs(o.g-cov*ref[1]));
                if(i%(steps/8)==0) {sampleGpu.push_back(o.g);sampleCpu.push_back(cov*ref[1]);}
            }
            J d;d.n("max_abs_error",worst).n("peak_reference",peak).a("gpu_samples",sampleGpu).a("cpu_samples",sampleCpu);
            record(name,worst<=tol*peak,d);
        };
        // feather at the grid edge: the lamp sits beyond 19 m so its strength fades together with the grid coverage
        sweep("feather.grid_edge_follows_cpu_smoothstep",{torch(1023,71,-2050)},{1023.5,71.64,-2049.5},{1020.25,71.64,-2046.5},{1029.25,71.64,-2046.5},180,0.05);
        sweep("feather.tile_boundary_has_no_step",oneTorch,LP,{1006.5,71.64,-2046.5},{1010.5,71.64,-2046.5},160,0.03);
        // ================================================================ 11. bounded work
        {
            std::vector<Block> many;int n=0;for(int x=1000;x<1008&&n<30;x++) for(int z=-2056;z<-2052&&n<30;z++,n++) many.push_back(torch(x,71,z,14));
            build(many);std::mt19937 rng(7);std::uniform_real_distribution<double> u(-1,1);
            const int N=512;std::vector<float> in(size_t(N)*16,0),out;
            for(int i=0;i<N;i++) {
                D3 p={C0[0]+u(rng)*6,C0[1]+u(rng)*3,C0[2]-3+u(rng)*5};D3 r=unit(sub(p,C0));
                in[size_t(i)*4]=float(p[0]-C0[0]);in[size_t(i)*4+1]=float(p[1]-C0[1]);in[size_t(i)*4+2]=float(p[2]-C0[2]);
                in[(size_t(N)+size_t(i))*4]=float(r[0]);in[(size_t(N)+size_t(i))*4+1]=float(r[1]);in[(size_t(N)+size_t(i))*4+2]=float(r[2]);in[(size_t(N)+size_t(i))*4+3]=1;
                in[(size_t(2)*size_t(N)+size_t(i))*4]=0.5f;
            }
            world.runProgram(helperProg,in,N,out,C0);
            int maxTraced=0;double maxLum=0;for(int i=0;i<N;i++) {maxTraced=std::max(maxTraced,int(out[size_t(i)*4+3]));maxLum=std::max(maxLum,lum({out[size_t(i)*4],out[size_t(i)*4+1],out[size_t(i)*4+2]}));}
            J d;d.n("configured_sources",configuredSources).n("max_traced_sources_with_30_lamps",maxTraced).n("max_luminance",maxLum).n("list_capacity",world.capacity).n("particles",N);
            const int designBudget=4;   // independent of the shader: more than four traced sources per particle is a regression
            d.n("design_budget",designBudget);
            record("work.traced_sources_bounded_and_output_soft_limited",maxTraced==configuredSources&&configuredSources<=designBudget&&maxLum<16.0+0.1,d);
            build({});world.runProgram(helperProg,in,N,out,C0);int t0=0;for(int i=0;i<N;i++) t0=std::max(t0,int(out[size_t(i)*4+3]));
            J d2;d2.n("max_traced_without_lamps",t0);record("work.no_lamps_no_tracing",t0==0,d2);
        }
        // ================================================================ 12. previous formula vs new, quantitative table
        {
            J d;std::vector<double> dist={1,2,4,8,12,16,22};std::vector<double> oldL,newL,ratio;
            build(oneTorch);
            for(double dd:dist) {
                Shot s=shot({LP[0],LP[1]+0.0,LP[2]+dd});s.lmx=0.9f;   // stale column light of a lit floor under the streak
                Out o=run(progOld,s),n=run(progNew,s);oldL.push_back(lum(o.rgb()));newL.push_back(lum(n.rgb()));ratio.push_back(lum(n.rgb())/lum(o.rgb()));
            }
            d.a("distance_from_torch_m",dist).a("old_luminance",oldL).a("new_luminance",newL).a("new_over_old",ratio);
            // soul lamp: old always orange, new blue
            build({blk(1005,71,-2050,10105,10)});Shot s=shot({1008.5,71.64,-2049.5});s.lmx=0.7f;Out o=run(progOld,s),n=run(progNew,s);
            d.a("soul_old_rgb",vec(o.rgb())).a("soul_new_rgb",vec(n.rgb()));
            record("compare.far_streaks_dim_and_soul_not_orange",newL.back()<0.1*oldL.back()&&n.b>n.r&&o.r>o.b*3,d);
        }
        // ================================================================ 13. GPU harness timing (not Minecraft frame time)
        {
            std::vector<Block> twelve;for(int i=0;i<12;i++) twelve.push_back(torch(1000+i%6,71,-2056+i/6*2,14));
            struct T {const char* name;std::vector<Block> scene;} cases[3]={{"no_lamps",{}},{"one_torch",oneTorch},{"twelve_torches_capacity",twelve}};
            J d;for(auto& c:cases) {
                build(c.scene);Shot s=shot({1003.0,71.64,-2053.0});s.lmx=0.7f;s.lmy=1;s.sky={0.1f,0.14f,0.22f};s.sun={0.35,0.85,-0.4};
                const double oldMs=rig.timeQuad(progOld,s,7),newMs=rig.timeQuad(progNew,s,7);
                d.a(c.name,{oldMs,newMs});
            }
            d.s("unit","ms per 1280x720 full-coverage synthetic quad, [rc3, staging]; GPU harness, not Minecraft frame time");
            record("timing.gpu_harness_worst_case_quad",true,d);
        }
        // ---- finish
        int failed=0;for(auto& r:results) failed+=!r.pass;
        std::ofstream out(outPath);
        out<<"{\"renderer\":\""<<renderer<<"\",\"gl_version\":\""<<version<<"\",\"nvidia\":true,\"minecraft_started\":false,\"probe\":\"weather_light_probe\","
           <<"\"staging_shaders\":\""<<root.string()<<"\",\"baseline_shaders\":\""<<baseRoot.string()<<"\","
           <<"\"weather_fsh_sha256\":\""<<fileHash(root/"gbuffers_weather.fsh")<<"\",\"weather_light_glsl_sha256\":\""<<fileHash(root/"lib/weather_light.glsl")<<"\","
           <<"\"old_weather_fsh_sha256\":\""<<fileHash(baseRoot/"gbuffers_weather.fsh")<<"\",\"checks\":"<<results.size()<<",\"failed\":"<<failed<<",\"results\":[";
        for(size_t i=0;i<results.size();i++) out<<(i?",\n":"\n")<<"{\"name\":\""<<results[i].name<<"\",\"pass\":"<<(results[i].pass?"true":"false")<<",\"detail\":"<<results[i].detail<<"}";
        out<<"\n]}\n";
        std::cout<<"\n"<<results.size()<<" checks, "<<failed<<" failed on "<<renderer<<"\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        exitCode=failed?1:0;
    } catch(const std::exception& e) {
        std::cerr<<"weather-light probe ERROR: "<<e.what()<<"\n";exitCode=2;
    }
    return exitCode;
}
