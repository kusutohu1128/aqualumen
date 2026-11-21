// Independent native-GPU optics oracle for the rain-film (wet dielectric) material model.
//
// What is real (production code, compiled from the pack tree given on the command line):
//   lib/dielectric_film.glsl   filmDirectBRDF(), wetSubstrate()
//   lib/rain_material.glsl     rainMaterial()
//   lib/local_lighting.glsl    lampLighting(..., bool film, out vec3 reflectedLamp), driven through the real
//                              shadow_{solid,cutout,water}.vsh capture and shadowcomp1.csh publish (World from
//                              local-lights-probe.h), i.e. from *placed lights* with real occluders.
// What is independent (this file): a double-precision CPU statement of GGX + Smith masking + Schlick Fresnel
// (F0 = 0.0204 at the half vector) and of Kubelka-Munk reduced scattering, derived from the textbook equations only;
// a half-vector quadrature of the directional albedo that is itself cross-checked against a brute-force solid-angle
// grid and a Lambertian control; physical invariants (reciprocity, rotation invariance, monotonicity, energy bound)
// that do not depend on the shader's constants; and for the lamp path an energy-constant-free ratio test
// (reflectedLamp == diffuse_lamp * filmDirectBRDF(...) for one lamp at blockLevel 0, so the unknown lamp energy cancels).
//
// Scope statement: this verifies a *direct-incidence* microfacet reflection (a thin wet film on a rough substrate)
// plus a two-flux reduced-scattering darkening of the substrate. It does NOT validate a participating-medium model:
// no film thickness, internal multiple reflection, refraction into the film, or subsurface transport is tested or
// claimed. Timings are absent on purpose: this is a correctness oracle, not a benchmark.
//
// Result handling: probe(root) returns the number of FAILed checks. Missing optional API parts are reported as
// PENDING (never silently passed). AQUALUMEN_FILM_JSON=<new file> also writes machine-readable results.
#pragma once
#include <map>
#include <random>
#include <regex>
#include <set>
#include <cstdint>
#include <cstdlib>
#include <climits>
namespace aqualumenRainFilm {
using V3=std::array<double,3>;
constexpr double kPi=3.14159265358979323846;
constexpr double kF0=0.0204;

// ---------------------------------------------------------------------------------------------------------------------
// Reporting.
struct Report {
    struct Group { std::string name; int checks=0,fails=0; std::vector<std::string> shown; };
    std::vector<Group> groups;
    std::vector<std::string> pending,info;
    std::vector<std::pair<std::string,double>> metrics;
    void begin(const std::string& n) { groups.push_back({n,0,0,{}}); }
    void check(bool ok,const std::string& what) {
        Group& g=groups.back();g.checks++;
        if(!ok) { g.fails++;if(g.shown.size()<6) g.shown.push_back(what); }
    }
    void metric(const std::string& n,double v) { metrics.emplace_back(n,v); }
    int fails() const { int n=0;for(auto& g:groups) n+=g.fails;return n; }
    int checks() const { int n=0;for(auto& g:groups) n+=g.checks;return n; }
    void print() const {
        for(auto& g:groups) {
            std::cout<<(g.fails?"FAIL ":"PASS ")<<g.name<<": "<<(g.checks-g.fails)<<"/"<<g.checks<<" checks\n";
            for(auto& s:g.shown) std::cout<<"     - "<<s<<'\n';
            if(g.fails>int(g.shown.size())) std::cout<<"     ... "<<(g.fails-int(g.shown.size()))<<" more\n";
        }
        for(auto& s:info) std::cout<<"INFO "<<s<<'\n';
        for(auto& s:pending) std::cout<<"PENDING "<<s<<'\n';
        for(auto& m:metrics) std::cout<<"METRIC "<<m.first<<" = "<<std::setprecision(8)<<m.second<<'\n';
    }
};
inline std::string fmt(double v) { std::ostringstream s;s<<std::setprecision(7)<<v;return s.str(); }
inline std::string jsonEscape(const std::string& s) {
    std::string o;for(char c:s) { if(c=='"'||c=='\\') {o+='\\';o+=c;} else if(c=='\n') o+="\\n"; else o+=c; }return o;
}
inline std::string readText(const fs::path& p) {
    std::ifstream f(p);if(!f) throw std::runtime_error("Cannot read "+p.string());
    std::ostringstream s;s<<f.rdbuf();return s.str();
}

// ---------------------------------------------------------------------------------------------------------------------
// Vector helpers and the CPU oracle (double precision).
inline double dot(const V3& a,const V3& b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline V3 add(const V3& a,const V3& b) { return {a[0]+b[0],a[1]+b[1],a[2]+b[2]}; }
inline V3 mul(const V3& a,double s) { return {a[0]*s,a[1]*s,a[2]*s}; }
inline V3 unit(const V3& a) { const double l=std::sqrt(dot(a,a));return mul(a,1.0/l); }
inline V3 cross(const V3& a,const V3& b) { return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}; }
struct Rot { double m[3][3]; V3 apply(const V3& v) const { V3 r;for(int i=0;i<3;i++) r[i]=m[i][0]*v[0]+m[i][1]*v[1]+m[i][2]*v[2];return r; } };
inline Rot randomRotation(std::mt19937_64& g) {
    std::normal_distribution<double> nd;double q[4];double n=0;
    for(double& x:q) { x=nd(g);n+=x*x; }
    n=std::sqrt(n);for(double& x:q) x/=n;
    const double w=q[0],x=q[1],y=q[2],z=q[3];
    return {{{1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)},{2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)},{2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)}}};
}
// Microfacet lobe width: alpha = perceptual^2 (Disney/Burley remap), a2 = alpha^2, plus the finite emitter's slope^2.
inline double alpha2Of(double r,double s2,double lo=0.00012) { return std::clamp(std::pow(r,4.0)+s2,lo,1.0); }
// GGX/Trowbridge-Reitz normal distribution; integrates to 1 against cos(theta_h).
inline double ggxD(double nh,double a2) { const double d=nh*nh*(a2-1.0)+1.0;return a2/(kPi*d*d); }
inline double schlick(double c) { return kF0+(1.0-kF0)*std::pow(1.0-std::clamp(c,0.0,1.0),5.0); }
// pi * f_r (the quantity filmDirectBRDF returns; the receiver cosine is NOT included).
// correlated=true: height-correlated Smith (Heitz); false: separable Smith. Both are textbook masking-shadowing terms.
inline double cpuBRDF(const V3& n,const V3& v,const V3& l,double r,double s2,bool correlated,double fresnelScale=1.0) {
    const double nl=dot(n,l),nv=dot(n,v);
    if(nl<=0.0||nv<=0.0) return 0.0;
    const V3 hs=add(v,l);const double len=std::sqrt(dot(hs,hs));if(len<1e-12) return 0.0;
    const V3 h=mul(hs,1.0/len);
    const double nh=std::clamp(dot(n,h),0.0,1.0),a2=alpha2Of(r,s2);
    double vis;
    if(correlated) vis=0.5/(nl*std::sqrt(a2+(1.0-a2)*nv*nv)+nv*std::sqrt(a2+(1.0-a2)*nl*nl));
    else {
        auto g1=[&](double x) { return 2.0*x/(x+std::sqrt(a2+(1.0-a2)*x*x)); };
        vis=g1(nl)*g1(nv)/(4.0*nl*nv);
    }
    const double f=fresnelScale==1.0?schlick(dot(v,h)):1.0;
    return kPi*ggxD(nh,a2)*vis*f;
}
// Directional albedo  (1/pi) * Int pi*f_r * cos(theta_l) dOmega_l  via stratified sampling of the half vector:
// dOmega_l = 4 (v.h) dOmega_h and the GGX normal sampler has pdf D*cos(theta_h). Local frame n=(0,0,1).
template<class Brdf> double albedoQuadrature(const V3& v,double sampleA2,int nu,int np,Brdf&& f) {
    double sum=0;
    for(int iu=0;iu<nu;iu++) {
        const double u=(iu+0.5)/nu,ct=std::sqrt((1.0-u)/(1.0+(sampleA2-1.0)*u)),st=std::sqrt(std::max(1.0-ct*ct,0.0));
        double row=0;
        for(int ip=0;ip<np;ip++) {
            const double ph=2.0*kPi*(ip+0.5)/np;
            const V3 h={st*std::cos(ph),st*std::sin(ph),ct};
            const double vh=dot(v,h);if(vh<=0.0) continue;
            const V3 l=add(mul(h,2.0*vh),mul(v,-1.0));if(l[2]<=0.0) continue;
            row+=f(l)*l[2]*4.0*vh/(ggxD(ct,sampleA2)*ct);
        }
        sum+=row;
    }
    return sum/(double(nu)*np)/kPi;
}
// Brute-force solid-angle grid (independent of the half-vector sampler).
template<class Brdf> double albedoGrid(int nt,int np,Brdf&& f) {
    double sum=0;
    for(int it=0;it<nt;it++) {
        const double th=0.5*kPi*(it+0.5)/nt;
        for(int ip=0;ip<np;ip++) {
            const double ph=2.0*kPi*(ip+0.5)/np;
            const V3 l={std::sin(th)*std::cos(ph),std::sin(th)*std::sin(ph),std::cos(th)};
            sum+=f(l)*std::cos(th)*std::sin(th);
        }
    }
    return sum*(0.5*kPi/nt)*(2.0*kPi/np)/kPi;
}
// Kubelka-Munk semi-infinite layer. dry reflectance R -> K/S = (1-R)^2/(2R); wet: S' = ratio*S, K unchanged.
inline double kmWet(double R,double ratio) {
    if(R<=0.0) return 0.0;
    if(R>=1.0) return 1.0;
    const double ks=(1.0-R)*(1.0-R)/(2.0*R)/ratio;
    return 1.0+ks-std::sqrt(ks*ks+2.0*ks);
}

// ---------------------------------------------------------------------------------------------------------------------
// GPU harness: a fragment pass reads N input rows (4 x vec4 texels per row) and writes N vec4 results.
struct Rig {
    GLuint fbo=0,dataTex=0,outTex=0;
    Rig() { glGenFramebuffers(1,&fbo);glGenTextures(1,&dataTex);glGenTextures(1,&outTex); }
    static constexpr int kBatch=8192;
    using Row=std::array<float,16>;
    std::vector<std::array<float,4>> run(GLuint program,const std::vector<Row>& rows,const std::function<void(GLuint)>& setup={}) {
        std::vector<std::array<float,4>> result;result.reserve(rows.size());
        for(size_t first=0;first<rows.size();first+=kBatch) {
            const int n=int(std::min<size_t>(kBatch,rows.size()-first));
            std::vector<float> data(size_t(n)*16);
            for(int i=0;i<n;i++) for(int k=0;k<4;k++) for(int c=0;c<4;c++) data[(size_t(k)*n+i)*4+c]=rows[first+i][k*4+c];
            glBindTexture(GL_TEXTURE_2D,dataTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,n,4,0,GL_RGBA,GL_FLOAT,data.data());
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glBindTexture(GL_TEXTURE_2D,outTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,n,1,0,GL_RGBA,GL_FLOAT,nullptr);
            glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,outTex,0);
            glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
            if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("rain-film QA: framebuffer incomplete");
            glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glViewport(0,0,n,1);
            glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
            glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,dataTex);
            glUseProgram(program);glUniform1i(glGetUniformLocation(program,"probeData"),0);
            if(setup) setup(program);
            glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
            std::vector<float> out(size_t(n)*4,0);glReadPixels(0,0,n,1,GL_RGBA,GL_FLOAT,out.data());
            glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);
            if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("rain-film QA: GL error during probe draw");
            for(int i=0;i<n;i++) result.push_back({out[size_t(i)*4],out[size_t(i)*4+1],out[size_t(i)*4+2],out[size_t(i)*4+3]});
        }
        return result;
    }
};
inline Rig::Row row(const V3& a,const V3& b,const V3& c,double x,double y=0,double z=0,double w=0) {
    return {float(a[0]),float(a[1]),float(a[2]),0,float(b[0]),float(b[1]),float(b[2]),0,float(c[0]),float(c[1]),float(c[2]),0,float(x),float(y),float(z),float(w)};
}
inline V3 f3(const float* p) { return {double(p[0]),double(p[1]),double(p[2])}; }
inline V3 asDouble(const Rig::Row& r,int k) { return {double(r[k*4]),double(r[k*4+1]),double(r[k*4+2])}; }

inline const std::string kVertex="#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
inline const std::string kData="uniform sampler2D probeData;out vec4 probeOut;\nvec4 q(int i,int k){return texelFetch(probeData,ivec2(i,k),0);}\n";

// One shader prefix per attempt: some pack libs rely on the shared settings (PI), some define their own.
struct Packs {
    fs::path root;
    std::string settings,film,material;
    bool hasFilm=false,hasMaterial=false;
    GLuint build(const std::string& body,const std::string& name,bool needMaterial=false) const {
        std::string base="#version 430 compatibility\n";
        const std::string withSettings=base+settings,without=base;
        const std::string libs=film+(needMaterial?material:std::string());
        try { return link(kVertex,withSettings+libs+kData+body,name); }
        catch(const std::exception& a) {
            try { return link(kVertex,without+libs+kData+body,name); }
            catch(const std::exception& b) { throw std::runtime_error(std::string(a.what())+"\n--- retry without lib/settings.glsl ---\n"+b.what()); }
        }
    }
};

// ---------------------------------------------------------------------------------------------------------------------
inline bool nearRel(double a,double b,double rel,double abs=0) { return std::abs(a-b)<=abs+rel*std::max(std::abs(a),std::abs(b)); }
inline double rad(double deg) { return deg*kPi/180.0; }
inline std::string v3s(const V3& v) { return "("+fmt(v[0])+","+fmt(v[1])+","+fmt(v[2])+")"; }

// Direction in the local frame (n = +Z) from (theta, phi).
inline V3 dirOf(double theta,double phi) { return {std::sin(theta)*std::cos(phi),std::sin(theta)*std::sin(phi),std::cos(theta)}; }

// Samples used by several BRDF groups. Roughly half of the l directions are drawn from the GGX lobe around the mirror
// direction so the narrow peak is exercised, not only its tails.
struct Sample { V3 n,v,l;double r,s2; };
inline std::vector<Sample> makeSamples(int count,uint64_t seed) {
    std::mt19937_64 g(seed);std::uniform_real_distribution<double> U(0.0,1.0);
    const double rough[]={0.12,0.2,0.3,0.45,0.6,0.8,1.0},slopes[]={0.0,0.0,2e-4,3e-3,0.03,0.2};
    std::vector<Sample> out;
    while(int(out.size())<count) {
        const double r=rough[g()%7],s2=slopes[g()%6];
        const double a2=alpha2Of(r,s2);
        const double cv=std::pow(U(g),1.5),v_th=std::acos(std::min(cv,0.99999)),vph=2*kPi*U(g);
        V3 v=dirOf(v_th,vph),l;
        if(g()&1) {   // near-mirror: sample a half vector from GGX
            const double u=U(g),ct=std::sqrt((1.0-u)/(1.0+(a2-1.0)*u)),st=std::sqrt(std::max(1-ct*ct,0.0)),ph=2*kPi*U(g);
            const V3 h={st*std::cos(ph),st*std::sin(ph),ct};
            l=add(mul(h,2.0*dot(v,h)),mul(v,-1.0));
        } else l=dirOf(std::acos(U(g)),2*kPi*U(g));
        if(l[2]<=1e-4||v[2]<=1e-4) continue;
        out.push_back({{0,0,1},v,unit(l),r,s2});
    }
    return out;
}
inline Rot frameFor(std::mt19937_64& g) { return randomRotation(g); }

// ---------------------------------------------------------------------------------------------------------------------
// Lamp path evidence: real placed lights, real occluders, real lampLighting(film overload).
struct LampQuery { V3 p,n,v;float rough=0.2f,level=0.f,bounce=0.f;bool water=false,film=true; };
struct LampRig {
    using D3Cam=std::array<double,3>;
    aqualumenLocalLights::World& w;
    GLuint program=0;
    LampRig(aqualumenLocalLights::World& world,const Packs& packs):w(world) {
        const std::string common="#version 430 compatibility\n"+expand(w.root/"lib/settings.glsl",w.root)+expand(w.root/"lib/uniforms.glsl",w.root)
                                 +expand(w.root/"lib/local_lighting.glsl",w.root);
        const std::string body=kData+"uniform int outSel;\n"
            "void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2),d=q(i,3);vec3 refl=vec3(0.0),dif;\n"
            "  if(outSel>=2){\n"
            "    if(outSel==2) dif=lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,d.y>0.5,d.z);\n"            // legacy 7-arg overload
            "    else if(outSel==3) dif=lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,d.y>0.5);\n"            // legacy 6-arg overload
            "    else dif=lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,true,0.0);\n"                          // production water spec
            "  } else dif=lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,d.y>0.5,d.z,d.w>0.5,refl);\n"
            "  probeOut=vec4(outSel==1?refl:dif,1.0);}\n";
        program=link(kVertex,common+body,"rain-film-lamp-eval");
        (void)packs;
    }
    // sel: 0 diffuse return of the 9-arg overload, 1 reflectedLamp, 2 legacy 7-arg, 3 legacy 6-arg, 4 water=true 7-arg (production water spec)
    std::vector<V3> eval(const std::vector<LampQuery>& queries,const D3Cam& cam,int sel) {
        const size_t n=queries.size();std::vector<float> data(n*16),out;
        for(size_t i=0;i<n;i++) {
            const LampQuery& q=queries[i];
            for(int c=0;c<3;c++) { data[(0*n+i)*4+c]=float(q.p[c]-cam[c]);data[(1*n+i)*4+c]=float(q.n[c]);data[(2*n+i)*4+c]=float(q.v[c]); }
            data[(2*n+i)*4+3]=q.rough;data[(3*n+i)*4+0]=q.level;data[(3*n+i)*4+1]=q.water?1.f:0.f;data[(3*n+i)*4+2]=q.bounce;data[(3*n+i)*4+3]=q.film?1.f:0.f;
        }
        glProgramUniform1i(program,glGetUniformLocation(program,"outSel"),sel);
        w.runProgram(program,data,int(n),out,{cam[0],cam[1],cam[2]});
        std::vector<V3> r(n);
        for(size_t i=0;i<n;i++) r[i]={out[i*4],out[i*4+1],out[i*4+2]};
        return r;
    }
};

// ---------------------------------------------------------------------------------------------------------------------
inline int probe(const fs::path& root,bool strictPending=false) {
    Report rep;
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    const std::string glVersion=reinterpret_cast<const char*>(glGetString(GL_VERSION));
    std::cout<<"RAIN-FILM QA renderer: "<<renderer<<" | GL "<<glVersion<<'\n';
    const bool software=renderer.find("llvmpipe")!=std::string::npos||renderer.find("softpipe")!=std::string::npos||renderer.find("SWR")!=std::string::npos||renderer.find("Software")!=std::string::npos;
    if(software) std::cout<<"WARNING software renderer: results are NOT NVIDIA results\n";
    rep.metric("software_renderer",software?1:0);

    // ------------------------------------------------------------------ 0. API presence (never a silent pass)
    Packs packs;packs.root=root;
    const fs::path filmFile=root/"lib/dielectric_film.glsl",materialFile=root/"lib/rain_material.glsl",lampFile=root/"lib/local_lighting.glsl";
    packs.hasFilm=fs::exists(filmFile);packs.hasMaterial=fs::exists(materialFile);
    if(!packs.hasFilm) { rep.pending.push_back("lib/dielectric_film.glsl absent: film BRDF/substrate/lamp checks not run");rep.print();return 0; }
    const std::string filmSrc=readText(filmFile);
    rep.begin("api: announced signatures present");
    {
        auto has=[&](const std::string& src,const std::string& rx) { return std::regex_search(src,std::regex(rx)); };
        rep.check(has(filmSrc,"float\\s+filmDirectBRDF\\s*\\(\\s*vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*\\)"),"float filmDirectBRDF(vec3,vec3,vec3,float,float)");
        rep.check(has(filmSrc,"vec3\\s+wetSubstrate\\s*\\(\\s*vec3\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*\\)"),"vec3 wetSubstrate(vec3,float)");
        if(packs.hasMaterial) rep.check(has(readText(materialFile),"vec3\\s+rainMaterial\\s*\\(\\s*int\\s+\\w+\\s*\\)"),"vec3 rainMaterial(int)");
        const std::string lampSrc=readText(lampFile);
        const bool nine=has(lampSrc,"vec3\\s+lampLighting\\s*\\([^)]*bool\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*bool\\s+\\w+\\s*,\\s*out\\s+vec3\\s+\\w+\\s*\\)");
        const bool seven=has(lampSrc,"vec3\\s+lampLighting\\s*\\(vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*bool\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*\\)");
        const bool six=has(lampSrc,"vec3\\s+lampLighting\\s*\\(vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*vec3\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*float\\s+\\w+\\s*,\\s*bool\\s+\\w+\\s*\\)");
        rep.check(seven&&six,"legacy 7-arg and 6-arg lampLighting overloads stay public");
        if(!nine) rep.pending.push_back("lampLighting(...,bool film,out vec3 reflectedLamp) absent: lamp path checks not run");
        rep.metric("lamp_film_overload_present",nine?1:0);
        if(!packs.hasMaterial) rep.pending.push_back("lib/rain_material.glsl absent: material checks not run");
    }
    packs.film=expand(filmFile,root);
    packs.settings=expand(root/"lib/settings.glsl",root);
    if(packs.hasMaterial) packs.material=expand(materialFile,root);
    Rig rig;
    uint64_t sampleSeed=0xA17E5EEDULL;

    // ------------------------------------------------------------------ GPU kernels
    const std::string brdfBody=
        "void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2),d=q(i,3);\n"
        "  probeOut=vec4(filmDirectBRDF(a.xyz,b.xyz,c.xyz,d.x,d.y),0.0,0.0,1.0);}\n";
    const GLuint brdfProgram=packs.build(brdfBody,"rain-film-brdf");
    auto gpuBRDF=[&](const std::vector<Rig::Row>& rows) {
        auto out=rig.run(brdfProgram,rows);std::vector<double> v(out.size());
        for(size_t i=0;i<out.size();i++) v[i]=out[i][0];
        return v;
    };
    const std::string wetBody=
        "void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),d=q(i,3);probeOut=vec4(wetSubstrate(a.xyz,d.x),1.0);}\n";
    const GLuint wetProgram=packs.build(wetBody,"rain-film-wet");
    const std::string albedoBody=
        "uniform int NU;uniform int NP;\n"
        "void main(){int i=int(gl_FragCoord.x);vec4 b=q(i,1),c=q(i,3);\n"
        "  vec3 n=vec3(0.0,0.0,1.0),v=normalize(b.xyz);float r=c.x,s2=c.y,a2=clamp(pow(r,4.0)+s2,0.00012,1.0);\n"
        "  float sum=0.0;\n"
        "  for(int iu=0;iu<NU;iu++){\n"
        "    float u=(float(iu)+0.5)/float(NU),ct=sqrt((1.0-u)/(1.0+(a2-1.0)*u)),st=sqrt(max(1.0-ct*ct,0.0));\n"
        "    float d=ct*ct*(a2-1.0)+1.0,D=a2/(3.14159265*d*d);float row=0.0;\n"
        "    for(int ip=0;ip<NP;ip++){\n"
        "      float ph=6.28318531*(float(ip)+0.5)/float(NP);vec3 h=vec3(st*cos(ph),st*sin(ph),ct);\n"
        "      float vh=dot(v,h);if(vh<=0.0) continue;vec3 l=2.0*vh*h-v;if(l.z<=0.0) continue;\n"
        "      row+=filmDirectBRDF(n,v,l,r,s2)*l.z*4.0*vh/(D*ct);}\n"
        "    sum+=row;}\n"
        "  probeOut=vec4(sum/float(NU*NP)/3.14159265,0.0,0.0,1.0);}\n";
    const GLuint albedoProgram=packs.build(albedoBody,"rain-film-albedo");
    const int NU=2048,NP=64;
    auto gpuAlbedo=[&](const std::vector<Rig::Row>& rows) {
        auto out=rig.run(albedoProgram,rows,[&](GLuint p) { glUniform1i(glGetUniformLocation(p,"NU"),NU);glUniform1i(glGetUniformLocation(p,"NP"),NP); });
        std::vector<double> v(out.size());for(size_t i=0;i<out.size();i++) v[i]=out[i][0];return v;
    };

    // ------------------------------------------------------------------ 1. BRDF against the textbook oracle (+ positivity)
    const auto samples=makeSamples(24000,sampleSeed);
    std::mt19937_64 rg(0x5EED);
    std::vector<Rig::Row> rows;std::vector<Sample> rotated;
    for(const Sample& s:samples) {
        const Rot R=frameFor(rg);Sample t={R.apply(s.n),R.apply(s.v),R.apply(s.l),s.r,s.s2};
        // round-trip through float so CPU and GPU see exactly the same inputs
        auto rf=[](V3 a) { for(double& x:a) x=double(float(x));return a; };
        t.n=rf(t.n);t.v=rf(t.v);t.l=rf(t.l);rotated.push_back(t);
        rows.push_back(row(t.n,t.v,t.l,t.r,t.s2));
    }
    const auto gpuF=gpuBRDF(rows);
    {
        rep.begin("brdf: positivity and finiteness over 24000 random (n,v,l,roughness,extent) in arbitrary frames");
        size_t negative=0,nonfinite=0;double maxValue=0;
        for(double f:gpuF) { if(!std::isfinite(f)) nonfinite++; else { if(f<0) negative++;maxValue=std::max(maxValue,f); } }
        rep.check(nonfinite==0,std::to_string(nonfinite)+" non-finite results");
        rep.check(negative==0,std::to_string(negative)+" negative results");
        rep.metric("brdf_random_max_value",maxValue);
    }
    {
        rep.begin("brdf: GGX + Smith masking + Schlick(F0=0.0204 at half vector) vs double-precision CPU oracle");
        double worstC=0,worstS=0;size_t badC=0,badS=0;
        std::string firstBad;
        for(size_t i=0;i<rotated.size();i++) {
            const Sample& s=rotated[i];const double a2=alpha2Of(s.r,s.s2);
            const double tol=2.5e-3+6e-7/a2,abs=1e-6;
            const double c=cpuBRDF(s.n,s.v,s.l,s.r,s.s2,true),p=cpuBRDF(s.n,s.v,s.l,s.r,s.s2,false);
            auto rel=[&](double ref) { return std::abs(gpuF[i]-ref)/std::max(std::abs(ref),1e-3); };
            worstC=std::max(worstC,rel(c));worstS=std::max(worstS,rel(p));
            if(std::abs(gpuF[i]-c)>abs+tol*std::max(std::abs(c),std::abs(gpuF[i]))) { badC++;if(firstBad.empty()) firstBad="n="+v3s(s.n)+" v="+v3s(s.v)+" l="+v3s(s.l)+" r="+fmt(s.r)+" s2="+fmt(s.s2)+" GPU "+fmt(gpuF[i])+" oracle "+fmt(c); }
            if(std::abs(gpuF[i]-p)>abs+tol*std::max(std::abs(p),std::abs(gpuF[i]))) badS++;
        }
        rep.check(badC==0,std::to_string(badC)+"/"+std::to_string(rotated.size())+" samples differ from the height-correlated Smith oracle; first: "+firstBad);
        rep.metric("brdf_oracle_worst_rel_correlated",worstC);
        rep.metric("brdf_oracle_worst_rel_separable",worstS);
        rep.metric("brdf_oracle_bad_correlated",double(badC));
        rep.metric("brdf_oracle_bad_separable",double(badS));
        rep.info.push_back("masking model identified: "+std::string(badC==0?"height-correlated Smith":(badS==0?"separable Smith":"neither"))+" (separable oracle disagrees with "+std::to_string(badS)+" samples: the check discriminates the two)");
    }
    {
        rep.begin("brdf: hemisphere rule - below-hemisphere view or light returns exactly 0");
        std::vector<Rig::Row> r;
        std::mt19937_64 g(77);std::uniform_real_distribution<double> U(0,1);
        for(int i=0;i<400;i++) {
            V3 below=dirOf(std::acos(-0.02-0.98*U(g)),2*kPi*U(g)),above=dirOf(std::acos(0.05+0.95*U(g)),2*kPi*U(g));
            r.push_back(row({0,0,1},above,below,0.2+0.5*U(g),0.01*U(g)));    // light below
            r.push_back(row({0,0,1},below,above,0.2+0.5*U(g),0.01*U(g)));    // view below
            r.push_back(row({0,0,1},below,below,0.2+0.5*U(g),0.01*U(g)));    // both below (incl. mirror)
        }
        const auto f=gpuBRDF(r);size_t nonzero=0;
        for(double x:f) if(x!=0.0) nonzero++;
        rep.check(nonzero==0,std::to_string(nonzero)+" of "+std::to_string(f.size())+" below-hemisphere results are non-zero");
        // And continuity: just above the horizon is finite and non-negative.
        std::vector<Rig::Row> e;
        for(double c:{1e-1,1e-2,1e-3,1e-4,1e-5,1e-6}) { const V3 g1={std::sqrt(1-c*c),0,c};e.push_back(row({0,0,1},{0,0,1},g1,0.3,0.0));e.push_back(row({0,0,1},g1,{0,0,1},0.3,0.0));e.push_back(row({0,0,1},g1,{-g1[0],0,g1[2]},0.3,0.0)); }
        for(double x:gpuBRDF(e)) rep.check(std::isfinite(x)&&x>=0,"near-grazing value not finite/non-negative: "+fmt(x));
    }

    // ------------------------------------------------------------------ 2. reciprocity and frame invariance
    {
        rep.begin("brdf: reciprocity f(v,l) = f(l,v) and invariance under rotation of the frame");
        std::vector<Rig::Row> a,b,c;std::vector<size_t> idx;
        for(size_t i=0;i<4000;i++) {
            const Sample& s=rotated[i];
            a.push_back(row(s.n,s.v,s.l,s.r,s.s2));b.push_back(row(s.n,s.l,s.v,s.r,s.s2));
            const Rot R=frameFor(rg);auto rf=[&](V3 x) { x=R.apply(x);for(double& y:x) y=double(float(y));return x; };
            c.push_back(row(rf(s.n),rf(s.v),rf(s.l),s.r,s.s2));
        }
        const auto fa=gpuBRDF(a),fb=gpuBRDF(b),fc=gpuBRDF(c);
        double worstRec=0,worstRot=0;size_t badRec=0,badRot=0;
        for(size_t i=0;i<fa.size();i++) {
            const double a2=alpha2Of(rotated[i].r,rotated[i].s2),tol=2.5e-3+6e-7/a2;
            const double dr=std::abs(fa[i]-fb[i])/std::max({std::abs(fa[i]),std::abs(fb[i]),1e-3}),dt=std::abs(fa[i]-fc[i])/std::max({std::abs(fa[i]),std::abs(fc[i]),1e-3});
            worstRec=std::max(worstRec,dr);worstRot=std::max(worstRot,dt);
            if(dr>tol&&std::abs(fa[i]-fb[i])>1e-6) badRec++;
            if(dt>tol&&std::abs(fa[i]-fc[i])>1e-6) badRot++;
        }
        rep.check(badRec==0,std::to_string(badRec)+" reciprocity violations, worst rel "+fmt(worstRec));
        rep.check(badRot==0,std::to_string(badRot)+" frame-rotation violations, worst rel "+fmt(worstRot));
        rep.metric("reciprocity_worst_rel",worstRec);rep.metric("rotation_worst_rel",worstRot);
    }

    // ------------------------------------------------------------------ 3. closed forms at normal incidence: F0 and the lobe width
    {
        rep.begin("brdf: normal-incidence closed form f = F0/(4 a2) reproduces F0 and a2 = roughness^4 + emitterSlope2");
        std::vector<Rig::Row> r;std::vector<std::pair<double,double>> cases;
        for(double ro:{0.2,0.3,0.45,0.6,0.8,1.0}) for(double s2:{0.0,0.002,0.02,0.1}) { cases.push_back({ro,s2});r.push_back(row({0,0,1},{0,0,1},{0,0,1},ro,s2)); }
        const auto f=gpuBRDF(r);double worst=0;
        for(size_t i=0;i<cases.size();i++) {
            const double a2=alpha2Of(cases[i].first,cases[i].second),expect=kF0/(4.0*a2);
            const double rel=std::abs(f[i]-expect)/expect;worst=std::max(worst,rel);
            rep.check(rel<3e-3,"r="+fmt(cases[i].first)+" s2="+fmt(cases[i].second)+": GPU "+fmt(f[i])+" vs F0/(4 a2) "+fmt(expect));
            // the inferred width must equal r^4 + s2 (the lamp extent term), not just be monotonic
            const double inferred=kF0/(4.0*f[i]);
            rep.check(nearRel(inferred,a2,4e-3),"inferred a2 "+fmt(inferred)+" vs r^4+s2 "+fmt(a2));
        }
        rep.metric("normal_incidence_worst_rel",worst);
    }

    // ------------------------------------------------------------------ 4. normalization: directional albedo, energy bound, F0
    {
        rep.begin("brdf: quadrature controls (CPU) - sampler reproduces Lambertian albedo 1 and a brute-force solid-angle grid");
        const V3 v=unit({0.4,0.1,0.9});
        const double lam=albedoQuadrature(v,alpha2Of(0.3,0),2048,64,[](const V3&) { return 1.0; });   // f = pi*(1/pi) -> albedo = 1
        rep.check(std::abs(lam-1.0)<2e-3,"half-vector sampler on a Lambertian: "+fmt(lam));
        for(double ro:{0.25,0.6}) {
            const V3 vv=unit({std::sin(rad(50)),0,std::cos(rad(50))});
            auto f=[&](const V3& l) { return cpuBRDF({0,0,1},vv,l,ro,0.0,true); };
            const double a=albedoQuadrature(vv,alpha2Of(ro,0),2048,64,f),b=albedoGrid(6000,720,f);
            rep.check(std::abs(a-b)<0.004*std::max(a,b)+1e-6,"r="+fmt(ro)+": half-vector "+fmt(a)+" vs grid "+fmt(b));
        }
    }
    {
        rep.begin("brdf: normalized directional albedo (energy) vs CPU oracle, bound <= 1, F0 reproduction");
        std::vector<Rig::Row> r;std::vector<std::array<double,3>> cases;   // theta_v deg, r, s2
        for(double th:{0.0,20.0,45.0,65.0,80.0,87.0}) for(double ro:{0.15,0.3,0.6,1.0}) for(double s2:{0.0,0.01}) {
            cases.push_back({th,ro,s2});r.push_back(row({0,0,1},dirOf(rad(th),0.7),{0,0,1},ro,s2));
        }
        const auto g=gpuAlbedo(r);double worstAbs=0,worstRel=0,maxAlbedo=0;
        std::map<std::string,double> table;
        for(size_t i=0;i<cases.size();i++) {
            const V3 vv=asDouble(r[i],1);
            auto fC=[&](const V3& l) { return cpuBRDF({0,0,1},vv,l,cases[i][1],cases[i][2],true); };
            auto fS=[&](const V3& l) { return cpuBRDF({0,0,1},vv,l,cases[i][1],cases[i][2],false); };
            const double a2=alpha2Of(cases[i][1],cases[i][2]);
            const double cc=albedoQuadrature(vv,a2,NU,NP,fC),cs=albedoQuadrature(vv,a2,NU,NP,fS);
            const double best=std::abs(g[i]-cc)<=std::abs(g[i]-cs)?cc:cs;
            const double err=std::abs(g[i]-best);worstAbs=std::max(worstAbs,err);worstRel=std::max(worstRel,err/std::max(best,1e-4));
            maxAlbedo=std::max(maxAlbedo,g[i]);
            rep.check(std::isfinite(g[i])&&g[i]>=0.0,"theta_v "+fmt(cases[i][0])+" r "+fmt(cases[i][1])+": albedo "+fmt(g[i]));
            rep.check(g[i]<=1.0+2e-3,"energy: albedo "+fmt(g[i])+" > 1 at theta_v "+fmt(cases[i][0])+" r "+fmt(cases[i][1])+" s2 "+fmt(cases[i][2]));
            rep.check(err<=0.01*best+2e-4,"theta_v "+fmt(cases[i][0])+" r "+fmt(cases[i][1])+" s2 "+fmt(cases[i][2])+": GPU albedo "+fmt(g[i])+" vs oracle "+fmt(best));
            std::ostringstream key;key<<"albedo_thv"<<int(cases[i][0])<<"_r"<<cases[i][1]<<"_s"<<cases[i][2];table[key.str()]=g[i];
        }
        for(auto& kv:table) rep.metric(kv.first,kv.second);
        rep.metric("albedo_worst_abs_vs_oracle",worstAbs);rep.metric("albedo_max",maxAlbedo);
        // F0: for a (nearly) smooth lobe the albedo at normal view is the normal-incidence reflectance
        std::vector<Rig::Row> n0;for(double ro:{0.1,0.15,0.2,0.3}) n0.push_back(row({0,0,1},{0,0,1},{0,0,1},ro,0.0));
        const auto f0=gpuAlbedo(n0);
        const double f0r[]={0.1,0.15,0.2,0.3};
        for(size_t i=0;i<f0.size();i++) rep.check(f0[i]>0.0185&&f0[i]<kF0*1.03,"normal-view albedo "+fmt(f0[i])+" must reproduce F0 "+fmt(kF0)+" at r="+fmt(f0r[i]));
        // grazing views reflect more (Fresnel) but never more than 1
        std::vector<Rig::Row> gz;for(double th:{0.0,45.0,70.0,85.0,89.0}) gz.push_back(row({0,0,1},dirOf(rad(th),0.3),{0,0,1},0.25,0.0));
        const auto fg=gpuAlbedo(gz);
        for(size_t i=1;i<fg.size();i++) rep.check(fg[i]>fg[i-1]*0.999,"albedo must rise toward grazing: "+fmt(fg[i-1])+" -> "+fmt(fg[i]));
        rep.check(fg.back()>0.2&&fg.back()<=1.002,"grazing albedo "+fmt(fg.back())+" must be large but <= 1");
        rep.metric("albedo_normal_r0.2",f0[2]);rep.metric("albedo_grazing_89deg_r0.25",fg.back());
    }

    // ------------------------------------------------------------------ 5. roughness / extent response and angular response
    {
        rep.begin("brdf: roughness and emitter-extent monotonicity, angular response (in-plane sweeps)");
        const double th=rad(50);const V3 v={std::sin(th),0,std::cos(th)};
        auto mirror=[&](double dTheta) { return V3{-std::sin(th+dTheta),0,std::cos(th+dTheta)}; };   // dTheta along the incidence plane
        // peak at the mirror direction decreases with roughness, and with emitter extent
        std::vector<Rig::Row> pk;const double rs[]={0.12,0.2,0.3,0.4,0.6,0.8,1.0};
        for(double ro:rs) pk.push_back(row({0,0,1},v,mirror(0),ro,0));
        auto fp=gpuBRDF(pk);
        for(size_t i=1;i<fp.size();i++) rep.check(fp[i]<fp[i-1],"mirror peak must fall with roughness: r="+fmt(rs[i-1])+" "+fmt(fp[i-1])+" -> r="+fmt(rs[i])+" "+fmt(fp[i]));
        std::vector<Rig::Row> pe;const double ss[]={0.0,1e-4,1e-3,1e-2,0.05,0.2};
        for(double s2:ss) pe.push_back(row({0,0,1},v,mirror(0),0.3,s2));
        fp=gpuBRDF(pe);
        for(size_t i=1;i<fp.size();i++) rep.check(fp[i]<fp[i-1],"mirror peak must fall with emitter slope^2: "+fmt(ss[i-1])+" -> "+fmt(ss[i]));
        // off-specular (theta_h ~ 15 deg) response rises with roughness while the lobe is still narrower than that
        std::vector<Rig::Row> off;const double ro2[]={0.1,0.2,0.3,0.4,0.5};
        for(double ro:ro2) off.push_back(row({0,0,1},v,mirror(rad(-30)),ro,0));   // light moved 30 deg => half vector ~15 deg off the normal
        fp=gpuBRDF(off);
        for(size_t i=1;i<fp.size();i++) rep.check(fp[i]>fp[i-1],"off-specular response must grow with roughness: "+fmt(ro2[i-1])+" -> "+fmt(ro2[i]));
        // fine in-plane sweep: peak location and half-width
        struct Curve { double r,s2,peakDeg,fwhmDeg,fwhmOracle,peakOracle; };
        std::vector<Curve> curves;
        for(double ro:{0.15,0.3,0.6}) for(double s2:{0.0,0.01}) {
            std::vector<Rig::Row> sw;std::vector<double> ang;
            for(double a=-89.5;a<=89.5;a+=0.05) { ang.push_back(a);sw.push_back(row({0,0,1},v,{std::sin(rad(a)),0,std::cos(rad(a))},ro,s2)); }
            const auto f=gpuBRDF(sw);
            std::vector<double> c(f.size());
            for(size_t i=0;i<f.size();i++) c[i]=cpuBRDF({0,0,1},v,{std::sin(rad(ang[i])),0,std::cos(rad(ang[i]))},ro,s2,true);
            auto stats=[&](const std::vector<double>& y,double& peakAng,double& fwhm) {
                size_t k=size_t(std::max_element(y.begin(),y.end())-y.begin());peakAng=ang[k];
                const double half=0.5*y[k];size_t lo=k,hi=k;
                while(lo>0&&y[lo]>half) lo--;
                while(hi+1<y.size()&&y[hi]>half) hi++;
                fwhm=ang[hi]-ang[lo];
            };
            Curve cv{ro,s2,0,0,0,0};
            stats(f,cv.peakDeg,cv.fwhmDeg);stats(c,cv.peakOracle,cv.fwhmOracle);
            curves.push_back(cv);
            rep.check(std::abs(cv.peakDeg-cv.peakOracle)<=0.15,"r="+fmt(ro)+" s2="+fmt(s2)+": peak "+fmt(cv.peakDeg)+" deg vs oracle "+fmt(cv.peakOracle));
            rep.check(std::abs(cv.fwhmDeg-cv.fwhmOracle)<=0.03*cv.fwhmOracle+0.15,"r="+fmt(ro)+" s2="+fmt(s2)+": FWHM "+fmt(cv.fwhmDeg)+" vs oracle "+fmt(cv.fwhmOracle));
            // Physical, oracle-free: the lobe peak sits at the mirror direction (-50 deg) or slightly toward grazing
            // (the well-known off-specular shift from Fresnel and masking), never toward the normal.
            if(ro<=0.3) rep.check(cv.peakDeg<=-49.7&&cv.peakDeg>=-54.0,"r="+fmt(ro)+" s2="+fmt(s2)+": peak "+fmt(cv.peakDeg)+" deg must lie in [-54,-49.7] (mirror = -50)");
            if(ro<=0.3) {   // outward decline on both sides of the peak until the lobe has fallen to 1 % or |theta_l| reaches 70 deg
                size_t k=size_t(std::max_element(f.begin(),f.end())-f.begin());size_t viol=0,steps=0;
                for(size_t i=k+1;i<f.size()&&f[i-1]>0.01*f[k]&&ang[i]<=70.0;i++) { steps++;if(f[i]>f[i-1]*1.0005+1e-6) viol++; }
                for(size_t i=k;i>0&&f[i]>0.01*f[k]&&ang[i-1]>=-70.0;i--) { steps++;if(f[i-1]>f[i]*1.0005+1e-6) viol++; }
                rep.check(viol==0&&steps>40,"r="+fmt(ro)+" s2="+fmt(s2)+": "+std::to_string(viol)+" non-monotone steps away from the peak ("+std::to_string(steps)+" checked)");
            }
            std::ostringstream key;key<<"fwhm_deg_r"<<ro<<"_s"<<s2;rep.metric(key.str(),cv.fwhmDeg);
        }
        // Width trends are asserted where the lobe is still a lobe (r <= 0.3); at r = 0.6 the response is an off-specular
        // shoulder whose half-maximum width is not a roughness measure.
        for(size_t i=0;i<2;i++) rep.check(curves[i+2].fwhmDeg>curves[i].fwhmDeg,"FWHM must grow with roughness: r="+fmt(curves[i].r)+"->"+fmt(curves[i+2].r)+" s2="+fmt(curves[i].s2));
        for(size_t i=0;i<4;i+=2) rep.check(curves[i+1].fwhmDeg>curves[i].fwhmDeg,"FWHM must grow with emitter extent at r="+fmt(curves[i].r));
    }

    // ------------------------------------------------------------------ 6. numeric edge cases
    {
        rep.begin("brdf: numeric edge cases are finite and non-negative");
        std::vector<Rig::Row> e;
        const V3 up={0,0,1},side={1,0,0},d45=unit({1,0,1}),m45=unit({-1,0,1});
        const double rr[]={0.0,1e-4,0.02,0.5,1.0,2.0},sl[]={0.0,1e-6,0.5,1.0,10.0,1e6};
        for(double r0:rr) for(double s0:sl) {
            e.push_back(row(up,up,up,r0,s0));                       // normal incidence
            e.push_back(row(up,d45,m45,r0,s0));                     // mirror at 45 deg
            e.push_back(row(up,side,side,r0,s0));                   // both exactly on the horizon
            e.push_back(row(up,side,up,r0,s0));                     // view on horizon
            e.push_back(row(up,up,side,r0,s0));                     // light on horizon
            e.push_back(row(up,d45,{-d45[0],0,-d45[2]},r0,s0));     // antiparallel: zero-length half vector
            e.push_back(row(up,d45,d45,r0,s0));                     // light == view at 45 deg (retro)
        }
        const auto f=gpuBRDF(e);size_t bad=0;std::string first;
        for(size_t i=0;i<f.size();i++) if(!std::isfinite(f[i])||f[i]<0) { bad++;if(first.empty()) first="case "+std::to_string(i)+" -> "+fmt(f[i]); }
        rep.check(bad==0,std::to_string(bad)+" non-finite/negative; first "+first);
        // zero roughness must still produce a bounded peak (the lobe width is clamped, not divided by zero)
        std::vector<Rig::Row> z;z.push_back(row(up,up,up,0.0,0.0));
        const auto fz=gpuBRDF(z);rep.check(fz[0]>0&&fz[0]<1e7,"zero roughness peak must be bounded: "+fmt(fz[0]));
        rep.metric("zero_roughness_peak",fz[0]);
        // Horizon response must not be larger than the peak by an absurd factor (no spurious spike where cos -> 0)
        std::vector<Rig::Row> h;for(double c:{1e-3,1e-5,1e-7}) { const V3 l={std::sqrt(1-c*c),0,c};h.push_back(row(up,up,l,0.3,0.0)); }
        for(double x:gpuBRDF(h)) rep.check(x<50.0,"horizon response must not spike: "+fmt(x));
    }

    // ------------------------------------------------------------------ 7. wetSubstrate: Kubelka-Munk reduced scattering
    {
        rep.begin("wetSubstrate: Kubelka-Munk oracle, identity at ratio 1, black/white endpoints, monotone, bounded");
        std::vector<Rig::Row> r;std::vector<std::array<double,2>> cases;
        const double dries[]={0.0,1e-4,0.02,0.05,0.1,0.2,0.35,0.5,0.7,0.9,0.98,1.0};
        const double ratios[]={1.0,0.95,0.8,0.6,0.45,0.3,0.15,0.05,0.01};
        for(double d:dries) for(double q:ratios) { cases.push_back({d,q});r.push_back(row({d,d,d},{0,0,0},{0,0,0},q)); }
        const auto g=rig.run(wetProgram,r);double worst=0,worstId=0;
        for(size_t i=0;i<cases.size();i++) {
            const double dry=cases[i][0],ratio=cases[i][1],want=kmWet(dry,ratio);
            for(int c=0;c<3;c++) {
                rep.check(std::isfinite(g[i][c])&&g[i][c]>=-1e-7&&g[i][c]<=1.0+1e-6,"out of [0,1]: dry "+fmt(dry)+" ratio "+fmt(ratio)+" -> "+fmt(g[i][c]));
                worst=std::max(worst,std::abs(g[i][c]-want));
                rep.check(std::abs(g[i][c]-want)<=2.5e-4+2e-3*want,"dry "+fmt(dry)+" ratio "+fmt(ratio)+": GPU "+fmt(g[i][c])+" vs KM oracle "+fmt(want));
                rep.check(g[i][c]<=dry+2e-5,"wet substrate brighter than dry: dry "+fmt(dry)+" ratio "+fmt(ratio)+" -> "+fmt(g[i][c]));
            }
            if(ratio==1.0) { worstId=std::max(worstId,std::abs(g[i][0]-dry));rep.check(std::abs(g[i][0]-dry)<=1e-4,"ratio 1 must be the identity: dry "+fmt(dry)+" -> "+fmt(g[i][0])); }
            if(dry==0.0) rep.check(g[i][0]==0.0f||g[i][0]<1e-6,"black stays black: "+fmt(g[i][0]));
            if(dry==1.0) rep.check(g[i][0]>=1.0-1e-4,"white (K=0) stays white for every ratio: ratio "+fmt(ratio)+" -> "+fmt(g[i][0]));
        }
        rep.metric("wet_worst_abs_vs_km",worst);rep.metric("wet_identity_worst_abs",worstId);
        // monotone in ratio (wetter = lower ratio = darker) and in the dry reflectance; strict where defined
        for(double d:{0.02,0.1,0.2,0.5,0.8}) {
            std::vector<Rig::Row> m;std::vector<double> rs;
            for(double q=0.02;q<=1.0001;q+=0.02) { rs.push_back(q);m.push_back(row({d,d,d},{0,0,0},{0,0,0},q)); }
            const auto f=rig.run(wetProgram,m);
            for(size_t i=1;i<f.size();i++) rep.check(f[i][0]>=f[i-1][0]-1e-6,"non-monotone in ratio at dry "+fmt(d)+": ratio "+fmt(rs[i-1])+"->"+fmt(rs[i]));
            rep.check(f.front()[0]<f.back()[0]*0.999,"dry "+fmt(d)+": ratio 0.02 must be darker than ratio 1");
        }
        for(double q:{0.3,0.55,0.9}) {
            std::vector<Rig::Row> m;for(double d=0.0;d<=1.0001;d+=0.01) m.push_back(row({d,d,d},{0,0,0},{0,0,0},q));
            const auto f=rig.run(wetProgram,m);
            for(size_t i=1;i<f.size();i++) rep.check(f[i][0]>=f[i-1][0]-1e-6,"non-monotone in dry reflectance at ratio "+fmt(q)+" step "+std::to_string(i));
        }
        // channels are independent and the function is applied per channel
        std::vector<Rig::Row> ch;ch.push_back(row({0.15,0.45,0.8},{0,0,0},{0,0,0},0.5));
        const auto fc=rig.run(wetProgram,ch);
        for(int c=0;c<3;c++) rep.check(std::abs(fc[0][c]-kmWet(std::array<double,3>{0.15,0.45,0.8}[c],0.5))<2.5e-4,"channel "+std::to_string(c)+" mixes with another channel");
        // edge inputs: finite
        std::vector<Rig::Row> ed;
        for(double d:{-0.5,0.0,1.0,1.5,100.0}) for(double q:{-1.0,0.0,1e-7,1.0,2.0,100.0}) ed.push_back(row({d,d,d},{0,0,0},{0,0,0},q));
        for(const auto& o:rig.run(wetProgram,ed)) rep.check(std::isfinite(o[0])&&std::isfinite(o[1])&&std::isfinite(o[2])&&o[0]>=-1e-6&&o[0]<=1.0+1e-5,"edge input produced "+fmt(o[0]));
    }

    // ------------------------------------------------------------------ 8. rainMaterial table
    if(packs.hasMaterial) {
        rep.begin("rainMaterial: table sanity, zero coverage when ineligible, every eligible entry is physically usable");
        const std::string matBody=
            "void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0);probeOut=vec4(rainMaterial(int(a.x)),1.0);}\n";
        const GLuint matProgram=packs.build(matBody,"rain-film-material",true);
        std::vector<Rig::Row> r;std::vector<int> ids;
        for(int id=0;id<=12000;id++) { ids.push_back(id);r.push_back(row({double(id),0,0},{0,0,0},{0,0,0},0)); }
        const auto m=rig.run(matProgram,r);
        std::map<std::array<float,3>,int> distinct;std::vector<int> eligible;
        size_t ineligibleNonZero=0;
        for(size_t i=0;i<ids.size();i++) {
            const auto& o=m[i];
            const bool finite=std::isfinite(o[0])&&std::isfinite(o[1])&&std::isfinite(o[2]);
            rep.check(finite,"id "+std::to_string(ids[i])+" returns a non-finite value");
            rep.check(o[0]>0.0f&&o[0]<=1.0f,"id "+std::to_string(ids[i])+": scatteringRatio "+fmt(o[0])+" outside (0,1]");
            rep.check(o[1]>=0.0f&&o[1]<=1.0f,"id "+std::to_string(ids[i])+": roughness "+fmt(o[1])+" outside [0,1]");
            rep.check(o[2]>=0.0f&&o[2]<=1.0f,"id "+std::to_string(ids[i])+": coverage "+fmt(o[2])+" outside [0,1]");
            if(o[2]>0.0f) {
                eligible.push_back(ids[i]);distinct[{o[0],o[1],o[2]}]++;
                rep.check(o[0]<1.0f,"eligible id "+std::to_string(ids[i])+" must darken when wet (ratio<1), has "+fmt(o[0]));
                rep.check(o[1]>=0.05f,"eligible id "+std::to_string(ids[i])+" roughness "+fmt(o[1])+" is not a rough-substrate value");
            } else if(o[0]!=1.0f) ineligibleNonZero++;
        }
        // ineligible ids must be neutral: no coverage AND ratio 1 so that no darkening can leak through
        rep.check(ineligibleNonZero==0,std::to_string(ineligibleNonZero)+" ineligible ids carry a ratio != 1");
        // Out-of-range ids behave as ineligible.
        std::vector<Rig::Row> oob;for(double id:{-1.0,-1000.0,12001.0,65535.0,1e6,2147483520.0}) oob.push_back(row({id,0,0},{0,0,0},{0,0,0},0));
        for(const auto& o:rig.run(matProgram,oob)) rep.check(o[2]==0.0f,"out-of-range id must have zero coverage, got "+fmt(o[2]));
        std::ostringstream ids2;for(int id:eligible) ids2<<id<<' ';
        rep.info.push_back("eligible ids ("+std::to_string(eligible.size())+", "+std::to_string(distinct.size())+" distinct triples): "+ids2.str());
        rep.metric("rain_material_eligible_ids",double(eligible.size()));
        rep.metric("rain_material_distinct_triples",double(distinct.size()));
        rep.check(!eligible.empty(),"no eligible material at all");
        // Cross-check: every eligible id must be registered by block.properties (a bound id nobody emits is dead weight).
        const fs::path props=root/"block.properties";
        if(fs::exists(props)) {
            const std::string text=readText(props);
            std::set<int> bound;std::smatch bm;std::regex re("(^|\\n)block\\.(\\d+)\\s*=");
            for(auto it=std::sregex_iterator(text.begin(),text.end(),re);it!=std::sregex_iterator();++it) bound.insert(std::stoi((*it)[2]));
            std::string unbound;
            for(int id:eligible) if(!bound.count(id)) unbound+=std::to_string(id)+" ";
            rep.info.push_back(unbound.empty()?"every eligible rain material id is registered in block.properties":"eligible ids NOT registered in block.properties (unreachable in game): "+unbound);
            rep.metric("rain_material_unregistered_ids",double(std::count_if(eligible.begin(),eligible.end(),[&](int id) { return !bound.count(id); })));
        }
    }

    // ------------------------------------------------------------------ 9. lamp path: placed lights -> real lampLighting(film overload)
    bool lampPath=false;
    for(const std::string& p:rep.pending) if(p.rfind("lampLighting",0)==0) lampPath=true;
    if(!lampPath) {
        using namespace aqualumenLocalLights;
        World w;w.init(root);
        LampRig lamps(w,packs);
        const D3 C0={1003.25,71.5,-2049.75};
        const V3 LP={1005.5,71.64,-2049.5};              // standing torch in cell (1005,71,-2050): mount 0, y offset .64
        const double radius=0.13;
        const V3 up={0,1,0};
        auto mirrorView=[&](const V3& P,double azDeg=0,double elevDeg=0) {   // view direction that mirrors the torch for an upward normal
            V3 l=unit({LP[0]-P[0],LP[1]-P[1],LP[2]-P[2]});V3 vv={-l[0],l[1],-l[2]};
            if(azDeg!=0||elevDeg!=0) {   // rotate about the vertical axis by azDeg, then raise by elevDeg
                const double a=rad(azDeg),c=std::cos(a),s=std::sin(a);vv={vv[0]*c-vv[2]*s,vv[1],vv[0]*s+vv[2]*c};
                const double h=std::sqrt(vv[0]*vv[0]+vv[2]*vv[2]),e=std::atan2(vv[1],h)+rad(elevDeg);const double sc=std::cos(e)/std::max(h,1e-9);
                vv={vv[0]*sc,std::sin(e),vv[2]*sc};
            }
            return unit(vv);
        };
        std::vector<Block> scene;
        for(int x=1000;x<=1016;x++) for(int z=-2056;z<=-2042;z++) scene.push_back(stone(x,70,z));   // floor, top face at y=71
        scene.push_back(torch(1005,71,-2050));
        w.build(scene,C0);
        auto evalBRDF=[&](const std::vector<LampQuery>& q,double slope2Scale=1.0) {      // production filmDirectBRDF at the geometry
            std::vector<Rig::Row> rr;
            for(const auto& lq:q) {
                const V3 l=unit({LP[0]-lq.p[0],LP[1]-lq.p[1],LP[2]-lq.p[2]});
                const double d2=(LP[0]-lq.p[0])*(LP[0]-lq.p[0])+(LP[1]-lq.p[1])*(LP[1]-lq.p[1])+(LP[2]-lq.p[2])*(LP[2]-lq.p[2]);
                rr.push_back(row(lq.n,lq.v,l,lq.rough,slope2Scale*radius*radius/(4.0*std::max(d2,0.1))));
            }
            return gpuBRDF(rr);
        };
        // ---- 9a. receivers around the torch at several ranges, azimuths, roughness values and view directions
        std::vector<LampQuery> qs;std::mt19937_64 g(4242);std::uniform_real_distribution<double> U(0,1);
        while(qs.size()<96) {
            const double d=0.8+3.2*U(g),az=2*kPi*U(g);
            LampQuery q;q.p={LP[0]+d*std::cos(az),71.0,LP[2]+d*std::sin(az)};q.n=up;q.rough=float(0.15+0.45*U(g));
            q.v=mirrorView(q.p,-25+50*U(g),-6+12*U(g));
            if(q.v[1]<0.15) continue;
            qs.push_back(q);
        }
        auto dif=lamps.eval(qs,C0,0),refl=lamps.eval(qs,C0,1),leg7=lamps.eval(qs,C0,2),leg6=lamps.eval(qs,C0,3);
        {
            rep.begin("lamp path: overload compatibility (diffuse return unchanged, film=false adds nothing)");
            double worst=0;
            for(size_t i=0;i<qs.size();i++) for(int c=0;c<3;c++) { worst=std::max(worst,std::abs(dif[i][c]-leg7[i][c]));rep.check(dif[i][c]==leg7[i][c],"9-arg diffuse differs from the 7-arg overload at query "+std::to_string(i)); }
            rep.metric("lamp_overload_max_abs_diff",worst);
            auto noFilm=qs;for(auto& q:noFilm) q.film=false;
            const auto d2=lamps.eval(noFilm,C0,0),r2=lamps.eval(noFilm,C0,1);
            for(size_t i=0;i<qs.size();i++) for(int c=0;c<3;c++) {
                rep.check(r2[i][c]==0.0,"film=false must write zero reflectedLamp, got "+fmt(r2[i][c]));
                rep.check(d2[i][c]==dif[i][c],"film flag must not change the diffuse return");
                rep.check(leg6[i][c]==leg7[i][c],"6-arg and 7-arg overloads disagree");
            }
        }
        {
            rep.begin("lamp path: reflectedLamp == diffuse x filmDirectBRDF(n,v,l,roughness,r^2/(4 max(d^2,.1))) per channel (lamp energy cancels)");
            const auto brdf=evalBRDF(qs);double worst=0;size_t compared=0,lit=0;
            for(size_t i=0;i<qs.size();i++) {
                for(int c=0;c<3;c++) {
                    if(dif[i][c]<=1e-7) continue;
                    compared++;
                    const double want=dif[i][c]*brdf[i],got=refl[i][c];
                    const double rel=std::abs(got-want)/std::max(want,1e-6);worst=std::max(worst,rel);
                    rep.check(std::abs(got-want)<=4e-3*std::max(want,got)+2e-6,"query "+std::to_string(i)+" ch"+std::to_string(c)+": reflectedLamp "+fmt(got)+" vs diffuse*brdf "+fmt(want)+" (brdf "+fmt(brdf[i])+", r="+fmt(qs[i].rough)+")");
                }
                if(refl[i][0]>0) lit++;
            }
            rep.check(compared>200,"too few lit receivers compared: "+std::to_string(compared));
            rep.metric("lamp_ratio_worst_rel",worst);rep.metric("lamp_receivers_compared",double(compared));
            // discrimination: the control with the extent term removed must differ clearly for near receivers
            const auto brdf0=evalBRDF(qs,0.0);size_t differ=0;
            for(size_t i=0;i<qs.size();i++) if(dif[i][0]>1e-7&&std::abs(brdf0[i]-brdf[i])>0.05*brdf[i]) differ++;
            rep.check(differ>5,"fixture cannot distinguish the extent term (only "+std::to_string(differ)+" receivers are sensitive)");
            rep.metric("lamp_extent_sensitive_receivers",double(differ));
        }
        {   // chromaticity: one lamp, one wet BRDF => reflected has the lamp's own colour, i.e. same channel ratios as diffuse
            rep.begin("lamp path: reflected colour equals the lamp colour (warm torch vs soul torch)");
            std::vector<LampQuery> one(1);one[0].p={LP[0]+2.0,71.0,LP[2]};one[0].n=up;one[0].v=mirrorView(one[0].p);one[0].rough=0.2f;
            const auto dw=lamps.eval(one,C0,0)[0],rw=lamps.eval(one,C0,1)[0];
            std::vector<Block> soul=scene;soul.back()=soulTorch(1005,71,-2050);w.build(soul,C0);
            const auto ds=lamps.eval(one,C0,0)[0],rs=lamps.eval(one,C0,1)[0];
            w.build(scene,C0);
            auto ratioRG=[](const V3& a) { return a[0]/std::max(a[2],1e-9); };
            rep.check(rw[0]>0&&rs[0]+rs[1]+rs[2]>0,"mirror receiver must light up for both lamps");
            rep.check(nearRel(ratioRG(rw),ratioRG(dw),5e-3),"warm torch: reflected R/B "+fmt(ratioRG(rw))+" vs diffuse R/B "+fmt(ratioRG(dw)));
            rep.check(nearRel(ratioRG(rs),ratioRG(ds),5e-3),"soul torch: reflected R/B "+fmt(ratioRG(rs))+" vs diffuse R/B "+fmt(ratioRG(ds)));
            rep.check(std::abs(ratioRG(rw)-ratioRG(rs))>0.5*ratioRG(rw),"warm and soul torches must have clearly different colours");
        }
        {   // angular: peak of reflectedLamp over view azimuth sits at the geometric mirror
            rep.begin("lamp path: angular response - reflectedLamp peaks at the geometric mirror view, falls off both sides");
            for(double ro:{0.15,0.25}) {
                LampQuery base;base.p={LP[0]+2.5,71.0,LP[2]+0.7};base.n=up;base.rough=float(ro);
                std::vector<LampQuery> sweep;std::vector<double> ang;
                for(double a=-20.0;a<=20.0001;a+=0.25) { ang.push_back(a);LampQuery q=base;q.v=mirrorView(base.p,a,0);sweep.push_back(q); }
                const auto rf=lamps.eval(sweep,C0,1);
                size_t k=0;for(size_t i=0;i<rf.size();i++) if(rf[i][0]>rf[k][0]) k=i;
                rep.check(std::abs(ang[k])<=0.75,"r="+fmt(ro)+": peak at azimuth offset "+fmt(ang[k])+" deg from the mirror");
                rep.check(rf[k][0]>20.0*rf.front()[0]&&rf[k][0]>20.0*rf.back()[0],"r="+fmt(ro)+": peak/edge contrast too low ("+fmt(rf[k][0])+" vs "+fmt(rf.front()[0])+","+fmt(rf.back()[0])+")");
                size_t viol=0;
                for(size_t i=k+1;i<rf.size();i++) if(rf[i][0]>rf[i-1][0]*1.002+1e-7) viol++;
                for(size_t i=k;i>0;i--) if(rf[i-1][0]>rf[i][0]*1.002+1e-7) viol++;
                rep.check(viol==0,"r="+fmt(ro)+": "+std::to_string(viol)+" non-monotone azimuth steps");
                std::ostringstream key;key<<"lamp_peak_offset_deg_r"<<ro;rep.metric(key.str(),ang[k]);
            }
            // the wet reflection responds to the viewer: same receiver, mirror vs 40 deg away, ratio huge; diffuse does not
            LampQuery a;a.p={LP[0]+2.5,71.0,LP[2]+0.7};a.n=up;a.rough=0.2f;a.v=mirrorView(a.p);LampQuery b=a;b.v=mirrorView(a.p,40,0);
            const auto ra=lamps.eval({a,b},C0,1),da=lamps.eval({a,b},C0,0);
            rep.check(ra[0][0]>50.0*std::max(ra[1][0],1e-9),"mirror vs 40 deg-off view: "+fmt(ra[0][0])+" vs "+fmt(ra[1][0]));
            rep.check(da[0][0]==da[1][0],"the ordinary diffuse term must not depend on the view");
            rep.metric("lamp_mirror_to_offaxis_ratio",ra[0][0]/std::max(ra[1][0],1e-12));
        }
        {   // occluder: same visibility for diffuse and wet reflection
            rep.begin("lamp path: occluder - a wall removes diffuse and wet reflection together; penumbra keeps the BRDF ratio");
            std::vector<LampQuery> q;
            for(double dz=-4.0;dz<=4.0001;dz+=0.25) { LampQuery a;a.p={1011.5,71.0,LP[2]+dz};a.n=up;a.rough=0.2f;a.v=mirrorView(a.p);q.push_back(a); }
            const auto freeD=lamps.eval(q,C0,0),freeR=lamps.eval(q,C0,1);
            std::vector<Block> walled=scene;
            for(int y=71;y<=73;y++) for(int z=-2050;z<=-2049;z++) walled.push_back(stone(1008,y,z));    // two-cell wall at x=1008: shadows the middle receivers only
            w.build(walled,C0);
            const auto wallD=lamps.eval(q,C0,0),wallR=lamps.eval(q,C0,1);
            w.build(scene,C0);
            size_t blocked=0,partial=0,untouched=0;const auto brdf=evalBRDF(q);
            for(size_t i=0;i<q.size();i++) {
                const double fd=freeD[i][0],wd=wallD[i][0],fr=freeR[i][0],wr=wallR[i][0];
                rep.check(fd>0&&fr>0,"unoccluded receiver "+std::to_string(i)+" must be lit");
                if(wd==0.0) { blocked++;rep.check(wr==0.0,"diffuse is blocked but wet reflection leaks: "+fmt(wr)+" at receiver "+std::to_string(i)); }
                else if(wd<fd*0.999) { partial++;rep.check(std::abs(wr-wd*brdf[i])<=4e-3*std::max(wr,wd*brdf[i])+2e-6,"penumbra: reflected "+fmt(wr)+" vs diffuse*brdf "+fmt(wd*brdf[i])); }
                else { untouched++;rep.check(wr==fr,"unoccluded receiver changed by the wall: "+fmt(fr)+" -> "+fmt(wr)); }
                rep.check(wr<=fr*1.0001+1e-9,"wall must not brighten the wet reflection");
            }
            rep.check(blocked>=8&&untouched>=8,"fixture must contain both shadowed ("+std::to_string(blocked)+") and open ("+std::to_string(untouched)+") receivers");
            rep.metric("lamp_occluder_blocked",double(blocked));rep.metric("lamp_occluder_partial",double(partial));rep.metric("lamp_occluder_open",double(untouched));
        }
        {   // angle: grazing / back-facing receivers and lamp off
            rep.begin("lamp path: receivers facing away, lamp switched off, and no lamp produce no wet reflection");
            std::vector<LampQuery> q;
            LampQuery a;a.p={LP[0]+2.0,71.0,LP[2]};a.n={0,-1,0};a.rough=0.2f;a.v={0,-1,0};q.push_back(a);      // facing away from the lamp
            a.n={-1,0,0};a.v=unit({-1,0.3,0});q.push_back(a);                                                   // vertical wall plane through the lamp side (grazing from the lamp side is lit)
            a.n={1,0,0};a.v=unit({1,0.3,0});q.push_back(a);                                                     // back face
            const auto r1=lamps.eval(q,C0,1),d1=lamps.eval(q,C0,0);
            rep.check(r1[0][0]==0&&d1[0][0]==0,"downward-facing receiver must not reflect the lamp");
            rep.check(r1[2][0]==0&&d1[2][0]==0,"receiver facing away must not reflect the lamp");
            std::vector<Block> off=scene;off.back()=torch(1005,71,-2050,0);w.build(off,C0);
            std::vector<LampQuery> m(1);m[0].p={LP[0]+2.0,71.0,LP[2]};m[0].n=up;m[0].v=mirrorView(m[0].p);m[0].rough=0.2f;
            const auto ro=lamps.eval(m,C0,1)[0],doff=lamps.eval(m,C0,0)[0];
            rep.check(ro[0]==0&&ro[1]==0&&ro[2]==0,"lamp at level 0 must not reflect");
            rep.check(doff[0]==0,"lamp at level 0 must not light the receiver");
            w.build({stone(1000,70,-2056)},C0);   // lamp removed completely
            m[0].level=0.8f;
            const auto rn=lamps.eval(m,C0,1)[0],dn=lamps.eval(m,C0,0)[0];
            rep.check(rn[0]==0&&rn[1]==0&&rn[2]==0,"vanilla block-light residual must not create a wet reflection");
            rep.check(dn[0]>0,"vanilla residual diffuse must remain (blockLevel 0.8)");
            w.build(scene,C0);
        }
        {   // superposition: two lamps add linearly in diffuse and reflection
            rep.begin("lamp path: superposition of two placed lights (one warm, one soul) is additive");
            std::vector<Block> A=scene,B=scene,AB=scene;
            A.back()=torch(1005,71,-2050);B.back()=soulTorch(1008,71,-2047);
            AB.back()=torch(1005,71,-2050);AB.push_back(soulTorch(1008,71,-2047));
            std::vector<LampQuery> q;std::mt19937_64 h(99);
            while(q.size()<40) {
                LampQuery a;a.p={1004.0+7.0*U(h),71.0,-2053.0+7.0*U(h)};a.n=up;a.rough=float(0.15+0.4*U(h));
                a.v=unit({U(h)-0.5,0.2+0.8*U(h),U(h)-0.5});q.push_back(a);
            }
            w.build(A,C0);auto dA=lamps.eval(q,C0,0),rA=lamps.eval(q,C0,1);
            w.build(B,C0);auto dB=lamps.eval(q,C0,0),rB=lamps.eval(q,C0,1);
            w.build(AB,C0);auto dAB=lamps.eval(q,C0,0),rAB=lamps.eval(q,C0,1);
            w.build(scene,C0);
            size_t nonzero=0;
            for(size_t i=0;i<q.size();i++) for(int c=0;c<3;c++) {
                const double sd=dA[i][c]+dB[i][c],sr=rA[i][c]+rB[i][c];
                rep.check(std::abs(dAB[i][c]-sd)<=2e-4*std::max(sd,1e-3)+1e-6,"diffuse superposition at "+std::to_string(i));
                rep.check(std::abs(rAB[i][c]-sr)<=2e-4*std::max(sr,1e-3)+1e-6,"reflection superposition at "+std::to_string(i)+" ch"+std::to_string(c)+": "+fmt(rAB[i][c])+" vs "+fmt(sr));
                if(rA[i][c]>0&&rB[i][c]>0) nonzero++;
            }
            rep.check(nonzero>10,"fixture has too few receivers lit by both lamps: "+std::to_string(nonzero));
        }
        {   // coverage fade at the grid edge, consistent for diffuse and reflection; nothing beyond the grid
            rep.begin("lamp path: grid-edge coverage fade is shared by diffuse and wet reflection; zero beyond 24 m");
            std::vector<Block> far=scene;
            for(int x=1017;x<=1034;x++) for(int z=-2056;z<=-2042;z++) far.push_back(stone(x,70,z));
            far.push_back(torch(1023,71,-2050));far.push_back(torch(1030,71,-2050));
            w.build(far,C0);
            const V3 L1={1023.5,71.64,-2049.5};
            std::vector<LampQuery> q;
            for(double dx:{1.5,2.0}) { LampQuery a;a.p={L1[0]+dx,71.0,L1[2]};a.n=up;a.rough=0.2f;
                V3 l=unit({L1[0]-a.p[0],L1[1]-a.p[1],L1[2]-a.p[2]});a.v={-l[0],l[1],-l[2]};q.push_back(a); }
            // 1025.0..1026.0 is 22 m from the camera: inside the fade band 19..24
            const auto dfar=lamps.eval(q,C0,0),rfar=lamps.eval(q,C0,1);
            const double eye=std::max(std::abs(q[0].p[0]-C0[0]),std::abs(q[0].p[2]-C0[2]));
            const double t=std::clamp((eye-19.0)/5.0,0.0,1.0),cov=1.0-t*t*(3.0-2.0*t);
            rep.check(dfar[0][0]>0&&rfar[0][0]>0,"receiver in the fade band must still see a reflection (cov "+fmt(cov)+")");
            std::vector<Rig::Row> rr;
            for(const auto& lq:q) { V3 l=unit({L1[0]-lq.p[0],L1[1]-lq.p[1],L1[2]-lq.p[2]});const double d2=(L1[0]-lq.p[0])*(L1[0]-lq.p[0])+(L1[1]-lq.p[1])*(L1[1]-lq.p[1])+(L1[2]-lq.p[2])*(L1[2]-lq.p[2]);
                rr.push_back(row(lq.n,lq.v,l,lq.rough,radius*radius/(4.0*std::max(d2,0.1)))); }
            const auto bf=gpuBRDF(rr);
            for(size_t i=0;i<q.size();i++) rep.check(std::abs(rfar[i][0]-dfar[i][0]*bf[i])<=4e-3*rfar[i][0]+2e-6,"faded reflection "+fmt(rfar[i][0])+" vs faded diffuse*brdf "+fmt(dfar[i][0]*bf[i]));
            rep.metric("lamp_edge_coverage",cov);
            LampQuery beyond;beyond.p={1029.0,71.0,L1[2]};beyond.n=up;beyond.rough=0.2f;beyond.v=up;
            const V3 L2={1030.5,71.64,-2049.5};V3 l2=unit({L2[0]-beyond.p[0],L2[1]-beyond.p[1],L2[2]-beyond.p[2]});beyond.v={-l2[0],l2[1],-l2[2]};
            const auto rb=lamps.eval({beyond},C0,1)[0];
            rep.check(rb[0]==0&&rb[1]==0&&rb[2]==0,"receiver beyond the 24 m grid must have zero wet reflection, got "+fmt(rb[0]));
            w.build(scene,C0);
        }
        {   // the production water spec is the reference the film shares; report how close
            rep.begin("lamp path: film reflection vs production water-surface specular at the same inputs (shared 1x spec)");
            const auto water=lamps.eval(qs,C0,4);double worst=0;size_t n=0;
            for(size_t i=0;i<qs.size();i++) {
                if(water[i][0]<=1e-7) continue;
                const double rel=std::abs(refl[i][0]-water[i][0])/water[i][0];worst=std::max(worst,rel);n++;
                rep.check(rel<4e-3,"receiver "+std::to_string(i)+": film "+fmt(refl[i][0])+" vs water spec "+fmt(water[i][0]));
            }
            rep.check(n>40,"too few comparable receivers: "+std::to_string(n));
            rep.metric("lamp_film_vs_water_worst_rel",worst);
        }
        rep.info.push_back("lamp fixture: stone floor top y=71, torch kind 1 level 14 at (1005.5,71.64,-2049.5), camera (1003.25,71.5,-2049.75); visibility from production lampVisibility");
    }

    // ------------------------------------------------------------------ summary
    rep.print();
    std::cout<<"RAIN-FILM QA summary: "<<rep.checks()<<" checks, "<<rep.fails()<<" failed, "<<rep.pending.size()<<" pending, renderer "<<renderer<<(software?" (SOFTWARE)":"")<<'\n';
    if(const char* path=std::getenv("AQUALUMEN_FILM_JSON")) {
        const fs::path out=path;
        if(fs::exists(out)) throw std::runtime_error("AQUALUMEN_FILM_JSON target exists; refusing to overwrite earlier evidence: "+out.string());
        std::ofstream f(out);
        f<<"{\n \"renderer\": \""<<jsonEscape(renderer)<<"\",\n \"gl_version\": \""<<jsonEscape(glVersion)<<"\",\n \"software_renderer\": "<<(software?"true":"false")
         <<",\n \"checks\": "<<rep.checks()<<",\n \"fails\": "<<rep.fails()<<",\n \"pending\": [";
        for(size_t i=0;i<rep.pending.size();i++) f<<(i?",":"")<<"\""<<jsonEscape(rep.pending[i])<<"\"";
        f<<"],\n \"groups\": [\n";
        for(size_t i=0;i<rep.groups.size();i++) {
            const auto& g=rep.groups[i];
            f<<"  {\"name\": \""<<jsonEscape(g.name)<<"\", \"checks\": "<<g.checks<<", \"fails\": "<<g.fails<<", \"shown\": [";
            for(size_t k=0;k<g.shown.size();k++) f<<(k?",":"")<<"\""<<jsonEscape(g.shown[k])<<"\"";
            f<<"]}"<<(i+1<rep.groups.size()?",":"")<<"\n";
        }
        f<<" ],\n \"info\": [";
        for(size_t i=0;i<rep.info.size();i++) f<<(i?",":"")<<"\""<<jsonEscape(rep.info[i])<<"\"";
        f<<"],\n \"metrics\": {";
        for(size_t i=0;i<rep.metrics.size();i++) f<<(i?",":"")<<"\n  \""<<jsonEscape(rep.metrics[i].first)<<"\": "<<std::setprecision(10)<<rep.metrics[i].second;
        f<<"\n }\n}\n";
    }
    return rep.fails()+(strictPending?int(rep.pending.size()):0);
}
} // namespace aqualumenRainFilm
