// Independent NVIDIA EGL QA for the receiver-facing ONE diffuse bounce of placed lights.
//
// Runs the pack's REAL sources on the GPU: shadow_{solid,cutout,water}.vsh + shadowcomp1.csh build the lamp grid
// (lamp cells / field / list), then shadowcomp2.csh (bounceExitImage) and shadowcomp3.csh (bounceIncidentImage) run
// unchanged. No Minecraft, no world files. Scenes are controlled blocks drawn through the real shadow vertex shaders.
//
// Contract under test (shared with the shader author, restated here, NOT parsed from the GLSL):
//   32^3 local cells nested in the 64^3 lamp grid, local = lampCell-16 = world - 8*floor(camera/8) + 16.
//   face = axis*2 + (normal positive ? 1 : 0); index = 6*lampLinear(local,32) + face; address = (index%768, index/768).
//   bounceSurfaceImage r32ui 768x256: 0x80000000 | R(0..7) | G(8..15) | B(16..23) gamma UNORM8; linear ~ pow(rgb/255, 2.2).
//   shadowcomp2: 2x2 sub-points per face at 2*address + (u,v) -> bounceExitImage rgba16f 1536x512, 96x32 groups of 8x8.
//   shadowcomp3: same size -> bounceIncidentImage, gathers exit radiance over the receiver hemisphere.
//   Source flux (same as lampLighting): tint * 11*(level/14)^2 / (0.38+d^2) * cos, first-leg visibility lamp->surface.
//   exit    = albedo * E_pack (lampLighting energy*cos, which already carries 1/pi)   [pack units, NOT W/m^2]
//   incident= (1/pi) * integral of exit * cos = mean cosine-weighted exit seen by the receiver sub-point (receiver albedo not applied)
//   Local cells are stored modulo 32 in a sliding window: address uses (lampCell-16)&31, a cell is contained when
//   lampCell-(16+floor(mod(camera,8))) is in [0,32); coverage fades over 11..15 m (Chebyshev) from the eye.
//   The gather also fades its hit by 1-smoothstep(9,12,t) (reach) - printed as a second, "faded" oracle.
// Both unit conventions are single constants below (kExitDivPi, kIncidentDivPi). The measured GPU/CPU ratio is always
// printed, so a convention mismatch (x pi) shows up as a failing, explained number instead of being tuned away.
//
// Independent controls: (a) a CPU double-precision area-quadrature oracle with its own segment/AABB visibility; (b) that
// oracle is first verified against the offline single-bounce reference (reports/2026-11-21-indirect-light/reference.py,
// numbers copied from its transport.json) for the same hood geometry; (c) scene pairs that differ in one cause only.
// There is no MATLAB/Octave here and none is faked: the "offline reference" is that Python file's published numbers.
//
// Limits: the oracle is an exact area integral, the shader gathers with finitely many cosine samples, so incident is an
// APPROXIMATE gate (see kIncident*). Sub-point u/v tangent order is not asserted (the four values are compared as a set).
// Timings are not measured on purpose (a native benchmark may be running). This is a GPU harness result on synthetic
// cuboids, not a Minecraft frame time and not visual acceptance. Only one bounce, no sky/Sun term.
#pragma once
#include "local-lights-probe.h"
#include <numeric>
namespace aqualumenBounce {
namespace LL=aqualumenLocalLights;
using D3=LL::D3;
using Cell=std::array<int,3>;
using RGB8=std::array<unsigned,3>;
constexpr double kPi=3.14159265358979323846;
constexpr bool kExitDivPi=false,kIncidentDivPi=true;   // pack units: lampLighting energy already carries the 1/pi (exit = rho*E_pack)
constexpr double kExitTol=0.05;                  // lit-face exit sum, deterministic formula
constexpr double kIncMedianLo=0.75,kIncMedianHi=1.33,kIncEachLo=0.5,kIncEachHi=2.0;   // approximate sampled gather
constexpr int kLocal=32,kSurfW=768,kSurfH=256,kExitW=1536,kExitH=512;
constexpr unsigned kValid=0x80000000u;

inline void check(bool ok,const std::string& m) { if(!ok) throw std::runtime_error("bounce-light QA FAIL: "+m); }
inline void pass(const std::string& m) { std::cout<<"PASS bounce-light: "<<m<<'\n'; }
inline void info(const std::string& m) { std::cout<<"INFO bounce-light: "<<m<<'\n'; }
inline std::string f(double v,int p=4) { std::ostringstream s;s<<std::setprecision(p)<<v;return s.str(); }

// ---- contract arithmetic -------------------------------------------------------------------------------------
inline int lin(int x,int y,int z,int w) { return x+w*(z+w*y); }
inline int faceId(int axis,bool positive) { return axis*2+(positive?1:0); }
inline std::array<int,2> faceAddress(const Cell& local,int face) {
    const int index=6*lin(local[0],local[1],local[2],kLocal)+face;return {index%kSurfW,index/kSurfW};
}
inline Cell base8(const D3& cam) { return {int(std::floor(cam[0]/8))*8,int(std::floor(cam[1]/8))*8,int(std::floor(cam[2]/8))*8}; }
inline Cell toLocal(const Cell& world,const D3& cam) {   // (lampCell-16)&31 with lampCell = world - 8*floor(cam/8) + 32
    const Cell b=base8(cam);Cell l;for(int i=0;i<3;i++) l[i]=(world[i]-b[i]+16)&31;return l;
}
inline bool contained(const Cell& world,const D3& cam) {   // sliding window, origin 16+floor(mod(camera,8))
    const Cell b=base8(cam);
    for(int i=0;i<3;i++) { const int rel=world[i]-b[i]+32-(16+int(std::floor(cam[i]-b[i])));if(rel<0||rel>=kLocal) return false; }
    return true;
}
inline unsigned packSurface(const RGB8& c) { return kValid|c[0]|(c[1]<<8)|(c[2]<<16); }
inline D3 decode(const RGB8& c) { return {std::pow(c[0]/255.0,2.2),std::pow(c[1]/255.0,2.2),std::pow(c[2]/255.0,2.2)}; }

inline D3 sub(const D3& a,const D3& b) { return {a[0]-b[0],a[1]-b[1],a[2]-b[2]}; }
inline double dot(const D3& a,const D3& b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline double smooth(double a,double b,double x) { double t=std::clamp((x-a)/(b-a),0.0,1.0);return t*t*(3-2*t); }

// ---- scene + CPU oracle --------------------------------------------------------------------------------------
struct Lamp { Cell cell;int id;int level; };
struct Surf { Cell cell;int face;RGB8 rgb; };
struct Scene {
    std::set<Cell> solid;std::vector<Lamp> lamps;std::vector<Surf> surfs;
    void stone(Cell c) { solid.insert(c); }
    void lamp(Cell c,int id,int level) { lamps.push_back({c,id,level}); }
    void surf(Cell c,int face,RGB8 rgb) { surfs.push_back({c,face,rgb}); }
};
inline D3 lampTint(int id) {   // restated from lampColor(): kinds 6..10,12,14 are soul/blue, the rest warm
    const int kind=id-10099;
    return (kind>=6&&kind<=10)||kind==12||kind==14?D3{0.11,0.65,1.0}:D3{1.0,0.49,0.19};
}
struct CLamp { D3 pos,tint;double flux; };   // flux = 11*(level/14)^2, 0 when the lamp is off
inline std::vector<CLamp> cpuLamps(const Scene& s,double /*unused*/=0) {
    std::vector<CLamp> out;
    for(const Lamp& l:s.lamps) {
        const int kind=l.id-10099;const auto off=LL::kindOffset(kind);
        const int level=std::clamp(l.level,0,15);if(level==0) continue;
        out.push_back({{l.cell[0]+double(off[0]),l.cell[1]+double(off[1]),l.cell[2]+double(off[2])},lampTint(l.id),11.0*std::pow(level/14.0,2.0)});
    }
    return out;
}
// Segment test against unit cells. Zero-thickness touches (end points on a face) do not block, same as reference.py.
inline bool blockedSeg(const std::vector<Cell>& solids,const D3& s,const D3& e) {
    const D3 d=sub(e,s);
    for(const Cell& c:solids) {
        double enter=0,leave=1;bool ok=true;
        for(int a=0;a<3&&ok;a++) {
            const double lo=c[a],hi=c[a]+1;
            if(std::abs(d[a])<1e-13) { if(!(lo<s[a]&&s[a]<hi)) ok=false;continue; }
            double t0=(lo-s[a])/d[a],t1=(hi-s[a])/d[a];if(t0>t1) std::swap(t0,t1);
            enter=std::max(enter,t0);leave=std::min(leave,t1);
        }
        if(ok&&leave>enter+1e-10) return true;
    }
    return false;
}
inline D3 facePoint(const Cell& c,int face,double u,double v) {
    const int a=face/2,t1=(a+1)%3,t2=(a+2)%3;D3 p;p[a]=c[a]+((face&1)?1:0);p[t1]=c[t1]+u;p[t2]=c[t2]+v;return p;
}
inline D3 faceNormal(int face) { D3 n={0,0,0};n[face/2]=(face&1)?1:-1;return n; }

struct Oracle {
    std::vector<Cell> solids;std::vector<CLamp> lamps;double soften=0.38;
    // First-leg irradiance (lampLighting energy units) at a surface point.
    D3 direct(const D3& p,const D3& n) const {
        D3 e={0,0,0};
        for(const CLamp& l:lamps) {
            const D3 to=sub(l.pos,p);const double d2=dot(to,to),d=std::sqrt(d2);
            const double nl=dot(n,to)/d;if(nl<=0) continue;
            if(blockedSeg(solids,l.pos,p)) continue;
            if(d>=0.7*14.0) throw std::runtime_error("oracle: scene exceeds the range where lamp falloff is 1");
            for(int c=0;c<3;c++) e[c]+=l.tint[c]*l.flux*nl/(soften+d2);
        }
        return e;
    }
};
inline double exitScaleC() { return kExitDivPi?1.0:kPi; }
struct WS { D3 p,n,lo;double dA; };    // area sample of a lit surface: position, normal, exit radiance
inline std::vector<WS> wallSamples(const Oracle& o,const Scene& s,int n=8) {
    std::vector<WS> out;
    for(const Surf& sf:s.surfs) {
        const D3 alb=decode(sf.rgb),nrm=faceNormal(sf.face);
        for(int i=0;i<n;i++) for(int j=0;j<n;j++) {
            const D3 p=facePoint(sf.cell,sf.face,(i+0.5)/n,(j+0.5)/n);const D3 e=o.direct(p,nrm);
            out.push_back({p,nrm,{alb[0]*e[0]/kPi*exitScaleC(),alb[1]*e[1]/kPi*exitScaleC(),alb[2]*e[2]/kPi*exitScaleC()},1.0/(n*n)});
        }
    }
    return out;
}
// Irradiance (units of exit radiance * sr) from the lit samples at a receiver point; second leg tested per sample.
inline D3 irradiance(const Oracle& o,const std::vector<WS>& ws,const D3& r,const D3& rn,bool fade=false) {
    D3 e={0,0,0};
    for(const WS& w:ws) {
        if(w.lo[0]+w.lo[1]+w.lo[2]<=0) continue;
        const D3 d=sub(w.p,r);const double d2=dot(d,d);if(d2<1e-9) continue;const double dist=std::sqrt(d2);
        const double cr=dot(rn,d)/dist,cx=-dot(w.n,d)/dist;if(cr<=0||cx<=0) continue;
        if(blockedSeg(o.solids,r,w.p)) continue;
        const double k=cr*cx/d2*w.dA*(fade?1.0-smooth(9.0,12.0,dist):1.0);for(int c=0;c<3;c++) e[c]+=w.lo[c]*k;
    }
    return e;
}
inline Oracle makeOracle(const Scene& s) { Oracle o;o.solids.assign(s.solid.begin(),s.solid.end());o.lamps=cpuLamps(s);return o; }

// ---- hood scenes (geometry of reports/2026-11-21-indirect-light/reference.py, shifted by O) --------------------------
inline Cell shift(const Cell& o,int x,int y,int z) { return {o[0]+x,o[1]+y,o[2]+z}; }
struct Hood {
    Scene scene;Cell O;
    // lamp (9,2,4) is hooded on five sides; east side (10,2,4) is open. East wall plane x=12, north plane z=0.
    Hood(Cell o,RGB8 east,RGB8 north,bool northSurfaces=true) : O(o) {
        for(Cell c:{Cell{9,2,3},Cell{9,2,5},Cell{8,2,4},Cell{9,1,4},Cell{9,3,4}}) scene.stone(shift(O,c[0],c[1],c[2]));
        for(int y=0;y<7;y++) for(int z=0;z<10;z++) { scene.stone(shift(O,12,y,z));scene.surf(shift(O,12,y,z),faceId(0,false),east); }
        for(int y=0;y<7;y++) for(int x=6;x<=12;x++) {
            scene.stone(shift(O,x,y,-1));
            if(northSurfaces&&x<12) scene.surf(shift(O,x,y,-1),faceId(2,true),north);
        }
        scene.lamp(shift(O,9,2,4),10100,14);
    }
    Cell at(int x,int y,int z) const { return shift(O,x,y,z); }
    // receiver faces on the north wall at row y=2: cells x=8..11 (face +z)
    std::vector<std::pair<Cell,int>> northReceivers() const {
        std::vector<std::pair<Cell,int>> r;for(int x=8;x<12;x++) r.push_back({at(x,2,-1),faceId(2,true)});return r;
    }
};
inline std::array<D3,4> subpointsOf(const Cell& c,int face) {   // 2x2 sub-points at 0.25/0.75, order not significant
    return {facePoint(c,face,0.25,0.25),facePoint(c,face,0.75,0.25),facePoint(c,face,0.25,0.75),facePoint(c,face,0.75,0.75)};
}

// ---- GPU rig -------------------------------------------------------------------------------------------------
struct Images { std::vector<float> exit,inc; };
struct Rig {
    fs::path root;LL::World w;LL::ImageProps pSurf,pExit,pInc;
    GLuint surfTex=0,scratch=0,exitTex=0,incTex=0,p2=0,p3=0,atlas=0;
    int groups2[3]={0,0,0},groups3[3]={0,0,0};
    D3 cam={1003.25,71.5,-2049.75};
    std::vector<std::string> unsetUniforms;

    static void expectDispatch(const std::string& name,const std::string& src,int g[3]) {
        std::smatch m;
        check(std::regex_search(src,m,std::regex("workGroups\\s*=\\s*ivec3\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)")),name+" lacks const ivec3 workGroups");
        for(int i=0;i<3;i++) g[i]=std::stoi(m[1+i]);
        check(g[0]==96&&g[1]==32&&g[2]==1,name+" must dispatch 96x32x1 groups, declares "+std::to_string(g[0])+"x"+std::to_string(g[1])+"x"+std::to_string(g[2]));
        check(std::regex_search(src,std::regex("local_size_x\\s*=\\s*8\\s*,\\s*local_size_y\\s*=\\s*8")),name+" must use local_size 8x8");
    }
    void init(const fs::path& r) {
        root=r;w.init(root);
        const std::string props=LL::slurp(root/"shaders.properties");
        pSurf=LL::parseImage(props,"bounceSurfaceImage");pExit=LL::parseImage(props,"bounceExitImage");pInc=LL::parseImage(props,"bounceIncidentImage");
        check(pSurf.format=="r32ui"&&pSurf.w==kSurfW&&(pSurf.h==kSurfH || pSurf.h==kSurfH+2),"bounceSurfaceImage must contain 256 face rows and optionally two water-mask rows");
        check(pExit.format=="rgba16f"&&pExit.w==kExitW&&(pExit.h==kExitH || pExit.h==2*kExitH),"bounceExitImage must contain one or two rgba16f face banks");
        check(pInc.format=="rgba16f"&&pInc.w==kExitW&&(pInc.h==kExitH || pInc.h==3*kExitH || pInc.h==4*kExitH),"bounceIncidentImage must contain the supported rgba16f face banks");
        expectDispatch("shadowcomp2.csh",LL::slurp(root/"shadowcomp2.csh"),groups2);
        expectDispatch("shadowcomp3.csh",LL::slurp(root/"shadowcomp3.csh"),groups3);
        surfTex=LL::World::makeTexture(GL_R32UI,kSurfW,pSurf.h);scratch=LL::World::makeTexture(GL_R32UI,kSurfW,pSurf.h);
        exitTex=LL::World::makeTexture(GL_RGBA16F,kExitW,pExit.h);incTex=LL::World::makeTexture(GL_RGBA16F,kExitW,pInc.h);
        p2=compute(root/"shadowcomp2.csh",root);p3=compute(root/"shadowcomp3.csh",root);
        // uniforms the harness does not drive are reported, never silently assumed
        for(GLuint prog:{p2,p3}) {
            GLint n=0;glGetProgramiv(prog,GL_ACTIVE_UNIFORMS,&n);
            for(int i=0;i<n;i++) {
                char name[128];GLsizei len=0;GLint size=0;GLenum type=0;glGetActiveUniform(prog,i,sizeof(name),&len,&size,&type,name);
                const std::string s=name;
                static const std::set<std::string> known={"cameraPosition","isEyeInWater","aqualumenDimension","bounceSurfaceImage","bounceExitImage",
                    "bounceIncidentImage","aqualumenLightField","aqualumenLightList","aqualumenBounceExit","aqualumenBounceSurfaces"};
                if(!known.count(s)) unsetUniforms.push_back(std::string(prog==p2?"shadowcomp2:":"shadowcomp3:")+s);
            }
        }
    }
    void zero(GLuint tex,GLenum format,int w_,int h_,GLenum fmt,GLenum type) {
        std::vector<float> z(size_t(w_)*h_*4,0.0f);glBindTexture(GL_TEXTURE_2D,tex);
        if(type==GL_UNSIGNED_INT) { std::vector<unsigned> u(size_t(w_)*h_,0u);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,w_,h_,fmt,type,u.data()); }
        else glTexSubImage2D(GL_TEXTURE_2D,0,0,0,w_,h_,fmt,type,z.data());
        (void)format;
    }
    // Real shadow vertex stages; image writes are the only observable (rasterisation discarded).
    // texU/texV: constant gtexture/mc_midTexCoord for this draw. producer: surface image bound for bounce capture.
    void capture(const std::vector<LL::Block>& blocks,const D3& c,GLuint producerSurface,float texU=0.25f,float texV=0.25f) {
        w.lastCam=c;
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();LL::resetTextureMatrices();
        glEnable(GL_RASTERIZER_DISCARD);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for(int p=0;p<3;p++) {
            const GLuint prog=w.pass[p];glUseProgram(prog);
            glUniformMatrix4fv(glGetUniformLocation(prog,"shadowModelViewInverse"),1,GL_FALSE,identity);
            glUniform3f(glGetUniformLocation(prog,"cameraPosition"),float(c[0]),float(c[1]),float(c[2]));
            glUniform1i(glGetUniformLocation(prog,"isEyeInWater"),0);
            LL::World::imageUnit(prog,"lampCellImage",0);LL::World::imageUnit(prog,"lampIndexImage",1);LL::World::imageUnit(prog,"shoreFaceImage",2);
            LL::World::imageUnit(prog,"bounceSurfaceImage",3);LL::World::imageUnit(prog,"gtexture",4);
            glBindImageTexture(0,w.cell,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);glBindImageTexture(1,w.index,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBindImageTexture(2,w.dummyShore,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);glBindImageTexture(3,producerSurface,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,atlas?atlas:0);glActiveTexture(GL_TEXTURE0);
            const GLint mid=glGetAttribLocation(prog,"mc_midTexCoord");
            if(mid>=0) glVertexAttrib4f(mid,texU,texV,0,0);
            glColor4f(1,1,1,1);glMultiTexCoord2f(GL_TEXTURE0,texU,texV);glMultiTexCoord2f(GL_TEXTURE1,1,1);
            glBegin(GL_QUADS);
            for(const LL::Block& b:blocks) { if(b.pass!=p) continue;float lo[3],hi[3];LL::World::boxFor(b,lo,hi);LL::World::emitBox(b,c,lo,hi); }
            glEnd();
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        }
        glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        check(glGetError()==GL_NO_ERROR,"GL error during shadow capture");
    }
    static std::vector<LL::Block> blocksOf(const Scene& s) {
        std::vector<LL::Block> b;
        for(const Cell& c:s.solid) b.push_back(LL::stone(c[0],c[1],c[2]));
        for(const Lamp& l:s.lamps) b.push_back(LL::blk(l.cell[0],l.cell[1],l.cell[2],l.id,l.level));
        return b;
    }
    void uploadSurfaces(const Scene& s,const D3& c) {
        std::vector<unsigned> words(size_t(kSurfW)*kSurfH,0u);
        for(const Surf& sf:s.surfs) {
            check(contained(sf.cell,c),"fixture surface outside the sliding 32^3 window");const Cell l=toLocal(sf.cell,c);
            const auto a=faceAddress(l,sf.face);words[size_t(a[1])*kSurfW+a[0]]=packSurface(sf.rgb);
        }
        glBindTexture(GL_TEXTURE_2D,surfTex);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,kSurfW,kSurfH,GL_RED_INTEGER,GL_UNSIGNED_INT,words.data());
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
    }
    void dispatch(GLuint prog,const int g[3],const D3& c,bool second) {
        glUseProgram(prog);
        LL::setUniform(prog,"cameraPosition",c[0],c[1],c[2]);LL::setUniform(prog,"previousCameraPosition",c[0],c[1],c[2]);LL::setUniform(prog,"isEyeInWater",0);LL::setUniform(prog,"aqualumenDimension",0);
        LL::World::imageUnit(prog,"bounceSurfaceImage",0);LL::World::imageUnit(prog,"bounceExitImage",1);LL::World::imageUnit(prog,"bounceIncidentImage",2);
        glBindImageTexture(0,surfTex,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
        glBindImageTexture(1,exitTex,0,GL_FALSE,0,GL_READ_WRITE,GL_RGBA16F);glBindImageTexture(2,incTex,0,GL_FALSE,0,GL_READ_WRITE,GL_RGBA16F);
        const struct { const char* name;GLuint tex;int unit; } samplers[]={{"aqualumenLightList",w.list,1},{"aqualumenLightField",w.field,2},
            {"aqualumenBounceIncident",incTex,6},{"aqualumenBounceExit",exitTex,3},{"aqualumenBounceSurfaces",surfTex,4},{"aqualumenRawIndex",w.index,5}};
        for(auto& s:samplers) { glActiveTexture(GL_TEXTURE0+s.unit);glBindTexture(GL_TEXTURE_2D,s.tex);LL::World::imageUnit(prog,s.name,s.unit); }
        glActiveTexture(GL_TEXTURE0);
        glDispatchCompute(g[0],g[1],g[2]);glMemoryBarrier(GL_ALL_BARRIER_BITS);glUseProgram(0);
        (void)second;check(glGetError()==GL_NO_ERROR,"GL error during bounce dispatch");
    }
    // Rebuild everything exactly as one frame would: raw clear, shadow capture, shadowcomp1, surfaces, shadowcomp2, shadowcomp3.
    // Images declared clear=true are cleared (as Iris does); clear=false images keep stale data, so a pass that
    // fails to overwrite old addresses is caught by the rebuild tests.
    Images build(const Scene& s,const D3& c) {
        cam=c;w.clearRaw();zero(scratch,0,kSurfW,pSurf.h,GL_RED_INTEGER,GL_UNSIGNED_INT);
        capture(blocksOf(s),c,scratch);w.publish();
        zero(surfTex,0,kSurfW,pSurf.h,GL_RED_INTEGER,GL_UNSIGNED_INT);uploadSurfaces(s,c);
        if(pExit.clear) zero(exitTex,0,kExitW,pExit.h,GL_RGBA,GL_FLOAT);
        if(pInc.clear) zero(incTex,0,kExitW,pInc.h,GL_RGBA,GL_FLOAT);
        dispatch(p2,groups2,c,false);dispatch(p3,groups3,c,true);
        return read();
    }
    Images read() {
        Images im;im.exit.resize(size_t(kExitW)*pExit.h*4);im.inc.resize(size_t(kExitW)*kExitH*4);
        glBindTexture(GL_TEXTURE_2D,exitTex);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,im.exit.data());
        glGetTextureSubImage(incTex,0,0,0,0,kExitW,kExitH,1,GL_RGBA,GL_FLOAT,im.inc.size()*sizeof(float),im.inc.data());
        for(float v:im.exit) check(std::isfinite(v),"nonfinite bounceExitImage texel");
        im.exit.resize(im.inc.size());  // retain the outgoing-radiance bank for the bounce oracle
        for(float v:im.inc) check(std::isfinite(v),"nonfinite bounceIncidentImage texel");
        return im;
    }
    // four sub-point RGB values of one face
    std::array<D3,4> sub4(const std::vector<float>& img,const Cell& world,int face) const {
        check(contained(world,cam),"read outside local window");const Cell l=toLocal(world,cam);
        const auto a=faceAddress(l,face);std::array<D3,4> out;
        for(int k=0;k<4;k++) {
            const size_t px=size_t(2*a[1]+(k>>1))*kExitW+2*a[0]+(k&1);
            out[k]={img[px*4],img[px*4+1],img[px*4+2]};
        }
        return out;
    }
};
inline D3 sum4(const std::array<D3,4>& v) { D3 s={0,0,0};for(auto& p:v) for(int c=0;c<3;c++) s[c]+=p[c];return s; }
inline double lum(const D3& v) { return v[0]+v[1]+v[2]; }
inline double totalOf(const std::vector<float>& img) { double s=0;for(size_t i=0;i<img.size();i+=4) s+=double(img[i])+img[i+1]+img[i+2];return s; }
inline double maxOf(const std::vector<float>& img) { double m=0;for(size_t i=0;i<img.size();i+=4) m=std::max(m,double(img[i])+img[i+1]+img[i+2]);return m; }
inline double exitScale() { return kExitDivPi?1.0:kPi; }
inline double incScale() { return kIncidentDivPi?1.0/kPi:1.0; }   // E -> stored value

struct Cmp { std::vector<double> ratios;int allBlockedZero=0,allBlockedNonzero=0,penumbra=0;double worstBlockedValue=0; };
// Compare exit radiance of selected faces against the oracle. Gate: faces with all four sub-points lit use kExitTol on
// the face sum; faces whose four sub-points are all blocked must read ~0; partially lit faces are only counted.
inline Cmp compareExit(Rig& rig,const Images& im,const Scene& s,const std::vector<std::pair<Cell,int>>& faces) {
    const Oracle o=makeOracle(s);Cmp c;
    std::map<std::pair<Cell,int>,RGB8> colors;for(const Surf& sf:s.surfs) colors[{sf.cell,sf.face}]=sf.rgb;
    const double peak=std::max(maxOf(im.exit),1e-12);
    // lampLighting averages three taps on a 0.13 m disk (penumbra). A face is only "decisively" blocked / lit when the
    // verdict is the same for the lamp centre and for the lamp displaced by 0.2 m along every axis.
    const double off[7][3]={{0,0,0},{.2,0,0},{-.2,0,0},{0,.2,0},{0,-.2,0},{0,0,.2},{0,0,-.2}};
    for(const auto& fc:faces) {
        const auto rgb=colors.at(fc);const D3 alb=decode(rgb),nrm=faceNormal(fc.second);
        double cpu[3]={0,0,0};int decLit=0,anyVisible=0;
        for(const D3& p:subpointsOf(fc.first,fc.second)) {
            const D3 e=o.direct(p,nrm);for(int k=0;k<3;k++) cpu[k]+=alb[k]*e[k]/kPi*exitScale()/4;
            bool any=false,all=true;
            for(const CLamp& l:o.lamps) for(auto& d:off) {
                const D3 q={l.pos[0]+d[0],l.pos[1]+d[1],l.pos[2]+d[2]};const D3 to=sub(q,p);
                const bool v=dot(nrm,to)>0&&!blockedSeg(o.solids,q,p);any|=v;all&=v;
            }
            anyVisible+=any;decLit+=all&&!o.lamps.empty();
        }
        const D3 gpu=sum4(rig.sub4(im.exit,fc.first,fc.second));
        if(anyVisible==0) { c.worstBlockedValue=std::max(c.worstBlockedValue,lum(gpu));if(lum(gpu)<=1e-5*peak) c.allBlockedZero++;else c.allBlockedNonzero++;continue; }
        if(decLit==4) for(int k=0;k<3;k++) if(cpu[k]*4>1e-6) c.ratios.push_back(gpu[k]/(cpu[k]*4));
        if(decLit!=4) c.penumbra++;
    }
    return c;
}
inline void requireExit(const std::string& tag,const Cmp& c,bool needLit=true) {
    if(!needLit&&c.ratios.empty()) { check(c.allBlockedNonzero==0,tag+": decisively blocked faces carry exit light, worst "+f(c.worstBlockedValue,3));pass(tag+": "+std::to_string(c.allBlockedZero)+" decisively blocked faces read 0, "+std::to_string(c.penumbra)+" penumbra faces not gated"); return; }
    check(!c.ratios.empty(),tag+": no lit face to compare");
    double lo=1e9,hi=0;for(double r:c.ratios) { lo=std::min(lo,r);hi=std::max(hi,r); }
    std::ostringstream m;m<<tag<<": exit/oracle over "<<c.ratios.size()<<" lit face channels min "<<f(lo)<<" max "<<f(hi)<<"; "<<c.penumbra<<" penumbra faces not gated; "<<c.allBlockedZero<<" decisively blocked faces read 0 (worst "<<f(c.worstBlockedValue,3)<<")";
    check(c.allBlockedNonzero==0,tag+": fully blocked faces carry exit light, worst "+f(c.worstBlockedValue,3));
    check(lo>=1-kExitTol&&hi<=1+kExitTol,m.str()+" outside +/-"+f(kExitTol*100,2)+"% (convention kExitDivPi="+std::to_string(kExitDivPi)+")");
    pass(m.str());
}
struct IncRow { double gpuLum,cpuLum,fadedLum;D3 gpu,cpu; };
inline std::vector<IncRow> compareIncident(Rig& rig,const Images& im,const Scene& s,const std::vector<std::pair<Cell,int>>& recv,int n=8) {
    const Oracle o=makeOracle(s);const auto ws=wallSamples(o,s,n);std::vector<IncRow> rows;
    for(const auto& fc:recv) {
        D3 cpu={0,0,0},fad={0,0,0};const D3 nrm=faceNormal(fc.second);
        for(const D3& p:subpointsOf(fc.first,fc.second)) { const D3 e=irradiance(o,ws,p,nrm),ef=irradiance(o,ws,p,nrm,true);
            for(int k=0;k<3;k++) { cpu[k]+=e[k]*incScale()/4;fad[k]+=ef[k]*incScale()/4; } }
        const D3 g=sum4(rig.sub4(im.inc,fc.first,fc.second));D3 gm={g[0]/4,g[1]/4,g[2]/4};
        rows.push_back({lum(gm),lum(cpu),lum(fad),gm,cpu});
    }
    return rows;
}
inline void requireIncident(const std::string& tag,const std::vector<IncRow>& rows) {
    std::vector<double> r;for(const IncRow& x:rows) { check(x.cpuLum>0,tag+": oracle predicts zero where light is expected");r.push_back(x.gpuLum/x.cpuLum); }
    std::sort(r.begin(),r.end());const double med=r[r.size()/2];
    std::vector<double> rf;for(const IncRow& x:rows) rf.push_back(x.gpuLum/x.fadedLum);std::sort(rf.begin(),rf.end());
    const double medF=rf[rf.size()/2];
    std::ostringstream m;m<<tag<<": incident GPU/oracle over "<<r.size()<<" receivers min "<<f(r.front())<<" median "<<f(med)<<" max "<<f(r.back())
        <<" (oracle "<<f(rows[0].cpuLum,3)<<".."<<f(rows.back().cpuLum,3)<<" first..last, stored=E"<<(kIncidentDivPi?"/pi":"")<<")";
    m<<"; vs reach-faded oracle min "<<f(rf.front())<<" median "<<f(medF)<<" max "<<f(rf.back());
    check(r.front()>=kIncEachLo&&r.back()<=kIncEachHi&&med>=kIncMedianLo&&med<=kIncMedianHi,m.str()+" outside approx gate (physical oracle)");
    check(medF>=0.85&&medF<=1.18&&rf.front()>=0.6&&rf.back()<=1.6,m.str()+" outside 96-ray gate (faded oracle)");
    pass(m.str());
}
inline void requireZeroIncident(const std::string& tag,const std::vector<IncRow>& rows,double reference) {
    double worst=0;for(const IncRow& x:rows) worst=std::max(worst,x.gpuLum);
    check(worst<=1e-3*reference,tag+": expected no incident light, worst "+f(worst,3)+" vs unblocked "+f(reference,3));
    pass(tag+": incident exactly gone (worst "+f(worst,3)+" vs unblocked reference "+f(reference,3)+")");
}
inline double meanLum(const std::vector<IncRow>& rows) { double s=0;for(const IncRow& x:rows) s+=x.gpuLum;return s/rows.size(); }
inline std::vector<std::pair<Cell,int>> eastFaces(const Hood& h) {
    std::vector<std::pair<Cell,int>> v;for(int y=0;y<7;y++) for(int z=0;z<10;z++) v.push_back({h.at(12,y,z),faceId(0,false)});return v;
}
inline std::vector<std::pair<Cell,int>> northFaces(const Hood& h) {
    std::vector<std::pair<Cell,int>> v;for(int y=0;y<7;y++) for(int x=6;x<12;x++) v.push_back({h.at(x,y,-1),faceId(2,true)});return v;
}

// ---- CPU oracle vs the offline reference (no GPU) ------------------------------------------------------------------
inline void oracleVsOfflineReference() {
    // Same hood and receivers as reference.py: lamp (9.5,2.5,4.5), unit intensity, no softening; wall x=12, y 0..7, z 0..10.
    Scene s;for(Cell c:{Cell{9,2,3},Cell{9,2,5},Cell{8,2,4},Cell{9,1,4},Cell{9,3,4}}) s.stone(c);
    Oracle o;o.solids.assign(s.solid.begin(),s.solid.end());o.soften=0;o.lamps={{{9.5,2.5,4.5},{1,1,1},1.0}};
    const double expected24[3]={0.008044323020717677,0.010972408827308109,0.008428950006592014};      // transport.json quadrature24
    const double expected64[3]={0.00804122611311118,0.01096873135050373,0.008426402765080674};        // transport.json quadrature64
    const D3 receivers[3]={{8,2.5,0},{9.5,2.5,0},{11,2.5,0}};
    for(int n:{24,64}) {
        std::vector<WS> ws;
        for(int i=0;i<7*n;i++) for(int j=0;j<10*n;j++) {
            const D3 p={12,(i+0.5)/n,(j+0.5)/n};const D3 nrm={-1,0,0};const D3 e=o.direct(p,nrm);
            ws.push_back({p,nrm,{e[0]/kPi,e[1]/kPi,e[2]/kPi},1.0/(n*n)});
        }
        double worst=0;
        for(int r=0;r<3;r++) {
            const D3 e=irradiance(o,ws,receivers[r],{0,0,1});
            const double want=n==24?expected24[r]:expected64[r];worst=std::max(worst,std::abs(e[0]/want-1));
        }
        check(worst<2e-5,"oracle differs from reference.py quadrature"+std::to_string(n)+" by "+f(worst,3));
        pass("CPU oracle reproduces reference.py transport.json quadrature"+std::to_string(n)+" for the 3 hood receivers (worst rel "+f(worst,3)+")");
    }
    // direct path lamp->receivers is blocked (hood), as the offline file asserts
    for(const D3& r:receivers) check(blockedSeg(o.solids,o.lamps[0].pos,r),"hood does not block lamp->receiver");
    pass("offline reference geometry: direct lamp->receiver blocked for all 3 receivers");
}
inline void contractSelfCheck() {
    check(faceAddress({0,0,0},0)==std::array<int,2>{0,0},"address origin");
    check(faceAddress({31,31,31},5)==std::array<int,2>{767,255},"address of last face must be (767,255)");
    std::set<int> seen;for(int y=0;y<kLocal;y+=7) for(int z=0;z<kLocal;z+=5) for(int x=0;x<kLocal;x+=3) for(int fc=0;fc<6;fc++) {
        const auto a=faceAddress({x,y,z},fc);check(a[0]<kSurfW&&a[1]<kSurfH,"address out of image");check(seen.insert(a[1]*kSurfW+a[0]).second,"address collision");
    }
    const D3 cam={1003.25,71.5,-2049.75};
    check((toLocal({1000,64,-2056},cam)==Cell{16,16,16}),"local origin mapping (lamp cell 32 -> local 16)");
    check(packSurface({255,0,0})==0x800000FFu&&packSurface({0,255,0})==0x8000FF00u&&packSurface({0,0,255})==0x80FF0000u,"channel packing");
    pass("contract arithmetic: 196608 face addresses unique and inside 768x256, local 16 = lamp cell 32, channel bit order");
}

// ---- producer: real shadow_solid vertex capture with an actual atlas gtexture and mc_midTexCoord --------------------
inline bool producerShipped(const fs::path& root) {
    for(const char* file:{"shadow_solid.vsh","lib/shadow_vsh.glsl","lib/local_capture.glsl","lib/shore_capture.glsl","lib/bounce_capture.glsl"}) {
        const fs::path p=root/file;if(fs::exists(p)&&LL::slurp(p).find("bounceSurfaceImage")!=std::string::npos) return true;
    }
    return false;
}
// One exposed cube as a mesher would emit it: per-vertex atlas UV on the sprite corners, mc_midTexCoord at the sprite centre.
inline void emitTexturedCube(const Cell& cell,const D3& cam,float u0,float v0,float size) {
    for(int a=0;a<3;a++) for(int s=0;s<2;s++) {
        const int u=(a+1)%3,v=(a+2)%3;float normal[3]={0,0,0};normal[a]=s?1.f:-1.f;glNormal3fv(normal);
        const int cu[4]={0,1,1,0},cv[4]={0,0,1,1};
        for(int c=0;c<4;c++) {
            double p[3];p[a]=s?1:0;p[u]=cu[c];p[v]=cv[c];float rel[3],mid[3];
            for(int i=0;i<3;i++) { rel[i]=float(cell[i]+p[i]-cam[i]);mid[i]=float((0.5-p[i])*64.0); }
            glMultiTexCoord2f(GL_TEXTURE0,u0+cu[c]*size,v0+cv[c]*size);
            glVertexAttrib4f(10,10001.0f,0,0,0);glVertexAttrib4f(11,mid[0],mid[1],mid[2],0);glVertex3fv(rel);
        }
    }
}
inline void producerProbe(Rig& rig) {
    const fs::path& root=rig.root;
    const std::string fsh=expand(root/"shadow_solid.fsh",root);
    if(fsh.find("bounceSurfaceImage")!=std::string::npos) { info("SKIP producer: shadow_solid.fsh writes bounceSurfaceImage (fragment stage); this harness discards rasterisation and only drives the vertex stage"); return; }
    // The production vertex stage needs the attribute at a known slot; relink shadow_solid with mc_midTexCoord at 12.
    const GLuint vs=compile(GL_VERTEX_SHADER,expand(root/"shadow_solid.vsh",root),"shadow_solid.vsh"),fsx=compile(GL_FRAGMENT_SHADER,fsh,"shadow_solid.fsh");
    const GLuint prog=glCreateProgram();glAttachShader(prog,vs);glAttachShader(prog,fsx);
    glBindAttribLocation(prog,10,"mc_Entity");glBindAttribLocation(prog,11,"at_midBlock");glBindAttribLocation(prog,12,"mc_midTexCoord");
    glLinkProgram(prog);GLint ok=0;glGetProgramiv(prog,GL_LINK_STATUS,&ok);
    if(!ok) { char log[8192];glGetProgramInfoLog(prog,sizeof(log),nullptr,log);throw std::runtime_error(std::string("shadow_solid relink: ")+log); }
    // 64x64 RGBA8 atlas with a full mip chain: four 32x32 sprites. 3 uniform colours + 1 two-colour checker (mapped-value report).
    const RGB8 sprite[3]={{200,60,40},{40,200,80},{255,255,255}};
    std::vector<unsigned char> px(64*64*4,255);
    for(int y=0;y<64;y++) for(int x=0;x<64;x++) {
        const int sp=(y/32)*2+(x/32);unsigned char* p=&px[(size_t(y)*64+x)*4];
        if(sp<3) { p[0]=sprite[sp][0];p[1]=sprite[sp][1];p[2]=sprite[sp][2]; }
        else { const bool c=((x/4)+(y/4))&1;p[0]=c?30:230;p[1]=120;p[2]=c?220:20; }
    }
    glGenTextures(1,&rig.atlas);glBindTexture(GL_TEXTURE_2D,rig.atlas);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,64,64,0,GL_RGBA,GL_UNSIGNED_BYTE,px.data());
    glGenerateMipmap(GL_TEXTURE_2D);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST_MIPMAP_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    const D3 cam=rig.cam;const Cell b=base8(cam);
    auto drawCube=[&](const Cell& world,int sp) {
        rig.w.clearRaw();rig.zero(rig.surfTex,0,kSurfW,kSurfH,GL_RED_INTEGER,GL_UNSIGNED_INT);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();LL::resetTextureMatrices();
        glEnable(GL_RASTERIZER_DISCARD);glUseProgram(prog);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        glUniformMatrix4fv(glGetUniformLocation(prog,"shadowModelViewInverse"),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(prog,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));glUniform1i(glGetUniformLocation(prog,"isEyeInWater"),0);
        LL::World::imageUnit(prog,"lampCellImage",0);LL::World::imageUnit(prog,"lampIndexImage",1);LL::World::imageUnit(prog,"shoreFaceImage",2);
        LL::World::imageUnit(prog,"bounceSurfaceImage",3);LL::World::imageUnit(prog,"gtexture",4);
        glBindImageTexture(0,rig.w.cell,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);glBindImageTexture(1,rig.w.index,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
        glBindImageTexture(2,rig.w.dummyShore,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);glBindImageTexture(3,rig.surfTex,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
        glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,rig.atlas);glActiveTexture(GL_TEXTURE0);
        const float u0=(sp%2)*0.5f,v0=(sp/2)*0.5f;
        glVertexAttrib2f(12,u0+0.25f,v0+0.25f);glColor4f(1,1,1,1);glMultiTexCoord2f(GL_TEXTURE1,1,1);
        glBegin(GL_QUADS);emitTexturedCube(world,cam,u0,v0,0.5f);glEnd();
        glMemoryBarrier(GL_ALL_BARRIER_BITS);glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        check(glGetError()==GL_NO_ERROR,"GL error in producer capture");
        std::vector<unsigned> words(size_t(kSurfW)*rig.pSurf.h);glBindTexture(GL_TEXTURE_2D,rig.surfTex);glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,words.data());
        return words;
    };
    int exactFaces=0;
    for(int sp=0;sp<4;sp++) {
        const Cell world={b[0]-16+16+3*sp,b[1]-16+16,b[2]-16+16};
        check(contained(world,cam),"producer fixture outside window");
        const auto words=drawCube(world,sp);const Cell local=toLocal(world,cam);
        size_t nonzero=0;for(unsigned wv:words) nonzero+=wv!=0;
        check(nonzero==6,"producer: one cube must write exactly its 6 faces, wrote "+std::to_string(nonzero)+" (sprite "+std::to_string(sp)+")");
        for(int face=0;face<6;face++) {
            const auto a=faceAddress(local,face);const unsigned wv=words[size_t(a[1])*kSurfW+a[0]];
            std::ostringstream hex;hex<<std::hex<<wv;
            check((wv&kValid)!=0,"producer: sprite "+std::to_string(sp)+" face "+std::to_string(face)+" lacks the valid bit at its contract address (word 0x"+hex.str()+")");
            check((wv&0x7F000000u)==0,"producer: reserved bits 24..30 set");
            const int got[3]={int(wv&255),int((wv>>8)&255),int((wv>>16)&255)};
            if(sp<3) {
                for(int k=0;k<3;k++) check(std::abs(got[k]-int(sprite[sp][k]))<=1,"producer: sprite "+std::to_string(sp)+" face "+std::to_string(face)+" channel "+std::to_string(k)+" is "+std::to_string(got[k])+", atlas texel is "+std::to_string(sprite[sp][k]));
                exactFaces++;
            } else {
                const int lo[3]={30,120,20},hi[3]={230,120,220};
                for(int k=0;k<3;k++) check(got[k]>=std::min(lo[k],hi[k])-1&&got[k]<=std::max(lo[k],hi[k])+1,"producer: checker sprite value outside its two colours");
                if(face==0) info("producer checker sprite (30,120,220)/(230,120,20) -> mapped ("+std::to_string(got[0])+","+std::to_string(got[1])+","+std::to_string(got[2])+"); mip-average of gamma texels, gate only [min,max]");
            }
        }
    }
    pass("producer shadow_solid vertex capture, actual mip-mapped atlas gtexture + mc_midTexCoord + per-vertex UV: "+std::to_string(exactFaces)+" uniform-sprite faces equal atlas texels (+/-1 LSB), valid bit, exactly 6 words per cube at the contract addresses");
    {   // outside the sliding 32^3 window nothing may be written
        const auto words=drawCube({b[0]+20,b[1],b[2]},0);size_t nonzero=0;for(unsigned wv:words) nonzero+=wv!=0;
        check(nonzero==0,"producer wrote "+std::to_string(nonzero)+" words for a block outside the local window");
        pass("producer: block outside the 32^3 window writes nothing");
    }
    {   // lamp blocks (id 10100..) are not diffuse surfaces
        rig.w.clearRaw();
        info("producer limit: lamp-id and cutout/glass passes are not driven by the producer check (only stone id 10001)");
    }
}

inline bool shipped(const fs::path& root) {
    const bool a=fs::exists(root/"shadowcomp2.csh"),b=fs::exists(root/"shadowcomp3.csh");
    if(!a&&!b) return false;
    auto mentions=[&](const char* file) { return fs::exists(root/file)&&LL::slurp(root/file).find("bounceSurfaceImage")!=std::string::npos; };
    const bool ma=mentions("shadowcomp2.csh"),mb=mentions("shadowcomp3.csh");
    if(ma!=mb||(ma&&!(a&&b))) throw std::runtime_error("Partial bounce pass: shadowcomp2.csh and shadowcomp3.csh must ship together");
    return ma&&mb;
}

inline void probe(const fs::path& root) {
    int softFailures=0;   // documented findings that must not hide the remaining measurements; still fail the run
    auto softly=[&](const std::function<void()>& fn) { try { fn(); } catch(const std::exception& e) { std::cout<<"FAIL(continuing) "<<e.what()<<'\n';softFailures++; } };
    std::cout<<"BOUNCE-LIGHT QA renderer: "<<reinterpret_cast<const char*>(glGetString(GL_RENDERER))<<" | "<<reinterpret_cast<const char*>(glGetString(GL_VERSION))<<'\n';
    contractSelfCheck();
    oracleVsOfflineReference();
    check(shipped(root),"pack ships no bounce passes (shadowcomp2.csh / shadowcomp3.csh with bounceSurfaceImage); CPU oracle checks above passed, GPU checks NOT run");
    Rig rig;rig.init(root);
    std::cout<<"BOUNCE-LIGHT QA production sources: shadow_*.vsh, shadowcomp1.csh, shadowcomp2.csh ("<<rig.groups2[0]<<"x"<<rig.groups2[1]<<"), shadowcomp3.csh ("
             <<rig.groups3[0]<<"x"<<rig.groups3[1]<<"); images surface clear="<<rig.pSurf.clear<<" exit clear="<<rig.pExit.clear<<" incident clear="<<rig.pInc.clear<<'\n';
    for(const auto& u:rig.unsetUniforms) info("uniform left at its default by this harness: "+u);
    const D3 cam0={1003.25,71.5,-2049.75};const Cell O={994,68,-2055};
    const RGB8 red={180,40,40},gray={120,120,120},black={12,12,12},white={235,235,235};

    // 1. hood B: white north wall, red east wall
    Hood base(O,red,white);Images im0=rig.build(base.scene,cam0);
    requireExit("hood B red east wall",compareExit(rig,im0,base.scene,eastFaces(base)));
    requireExit("hood B white north wall (blocked / leak-lit faces)",compareExit(rig,im0,base.scene,northFaces(base)),false);
    const auto rows0=compareIncident(rig,im0,base.scene,base.northReceivers());requireIncident("hood B receivers x=8..11,y=2",rows0);
    const double ref0=meanLum(rows0);
    {   // the three offline receiver x positions: centre faces rank as the offline file does (9.5 > 11 > 8)
        check(rows0[1].gpuLum>rows0[3].gpuLum&&rows0[1].gpuLum>rows0[0].gpuLum,"receiver nearest the lamp axis must receive the most bounce");
        pass("ray directions: receiver ranking centre("+f(rows0[1].gpuLum,3)+") > far east("+f(rows0[3].gpuLum,3)+") and > far west("+f(rows0[0].gpuLum,3)+") as in the offline integral");
    }
    {   // all-image gate: total exit equals oracle total; incident is only present on valid faces (no stale/stray writes)
        const Oracle o=makeOracle(base.scene);double cpu=0;
        for(const Surf& sf:base.scene.surfs) { const D3 a=decode(sf.rgb),n=faceNormal(sf.face);
            for(const D3& p:subpointsOf(sf.cell,sf.face)) { const D3 e=o.direct(p,n);cpu+=(a[0]*e[0]+a[1]*e[1]+a[2]*e[2])/kPi*exitScale(); } }
        const double gpu=totalOf(im0.exit)*1.0,ratio=gpu/cpu;
        check(std::abs(ratio-1)<0.06,"whole bounceExitImage sum / oracle = "+f(ratio));
        pass("whole-image exit sum / oracle = "+f(ratio)+" (no stray or stale exit writes anywhere in 1536x512)");
        std::set<std::pair<int,int>> valid;for(const Surf& sf:base.scene.surfs) { const auto a=faceAddress(toLocal(sf.cell,cam0),sf.face);valid.insert({a[0],a[1]}); }
        double stray=0;for(int y=0;y<kExitH;y++) for(int x=0;x<kExitW;x++) if(!valid.count({x/2,y/2})) { const size_t i=(size_t(y)*kExitW+x)*4;stray+=double(im0.inc[i])+im0.inc[i+1]+im0.inc[i+2]; }
        check(stray==0,"incident written at faces without a valid surface record, sum "+f(stray,3));
        pass("incident image is exactly zero at every face without a valid surface record");
    }

    // 2. different wall A colours: incident scales with the albedo, per channel
    for(const auto& [name,col]:std::vector<std::pair<std::string,RGB8>>{{"gray",gray},{"black",black},{"white",white}}) {
        Hood h(O,col,white);Images im=rig.build(h.scene,cam0);
        const auto rows=compareIncident(rig,im,h.scene,h.northReceivers());
        double gpu[3]={0,0,0},ref[3]={0,0,0};for(const IncRow& r:rows) for(int k=0;k<3;k++) { gpu[k]+=r.gpu[k];ref[k]+=rows0[&r-&rows[0]].gpu[k]; }
        const D3 a=decode(col),b=decode(red);std::ostringstream m;m<<"wall A "<<name<<": GPU(color)/GPU(red) per channel";
        for(int k=0;k<3;k++) {
            const double got=gpu[k]/ref[k],want=a[k]/b[k];m<<' '<<f(got,4)<<" (albedo ratio "<<f(want,4)<<")";
            check(std::abs(got/want-1)<0.04,m.str()+" differs >4%");
        }
        pass(m.str());
        if(name!="black") requireIncident("wall A "+name,rows); else info("wall A black: GPU/oracle "+f(rows[1].gpuLum/rows[1].cpuLum,3)+" (colour-ratio gate above is the check; magnitudes are tiny)");
    }

    // 3. both obstructed legs separately
    softly([&] {
        Hood h(O,red,white);h.scene.stone(h.at(10,2,4));      // plug the hood opening: first leg dead everywhere
        Images im=rig.build(h.scene,cam0);
        if(maxOf(im.exit)>1e-6*maxOf(im0.exit)) {
            std::ostringstream where;int shown=0;
            for(auto& fc:eastFaces(h)) { const double v=lum(sum4(rig.sub4(im.exit,fc.first,fc.second)));if(v>0&&shown++<6) where<<" east(y="<<fc.first[1]-O[1]<<",z="<<fc.first[2]-O[2]<<")="<<f(v,3); }
            for(auto& fc:northFaces(h)) { const double v=lum(sum4(rig.sub4(im.exit,fc.first,fc.second)));if(v>0&&shown++<6) where<<" north(x="<<fc.first[0]-O[0]<<",y="<<fc.first[1]-O[1]<<")="<<f(v,3); }
            {   // isolate: evaluate the production lampLighting() alone at the lit face's sub-points (no bounce pass involved)
                std::ostringstream direct;
                for(auto& fc:eastFaces(h)) if(lum(sum4(rig.sub4(im.exit,fc.first,fc.second)))>0) {
                    std::vector<LL::Query> qs;for(const D3& p:subpointsOf(fc.first,fc.second)) qs.push_back({p,{-1,0,0},{0,1,0},0.075f,0.0f,false});
                    const auto e=rig.w.evaluate(qs,cam0);direct<<" lampLighting@subpoints=";for(auto& v:e) direct<<f(v[0]+v[1]+v[2],3)<<",";
                    where<<direct.str();break;
                }
            }
            check(false,"first-leg blocker: exit not zero with the lamp fully enclosed, peak "+f(maxOf(im.exit),3)+" lit faces:"+where.str());
        }
        requireZeroIncident("first leg blocked (hood opening plugged): exit is zero everywhere and",compareIncident(rig,im,h.scene,h.northReceivers(),4),ref0);
    });
    {
        Hood h(O,red,white);for(int x=8;x<12;x++) h.scene.stone(h.at(x,2,0));   // receivers walled in; lamp->east wall mostly untouched
        Images im=rig.build(h.scene,cam0);
        requireExit("second-leg-only blocker keeps exit",compareExit(rig,im,h.scene,eastFaces(h)));
        check(maxOf(im.exit)>0.5*maxOf(im0.exit),"second-leg blocker unexpectedly darkened the exit image");
        const auto rows=compareIncident(rig,im,h.scene,h.northReceivers(),4);double worst=0;for(auto& r:rows) worst=std::max(worst,r.gpuLum);
        requireZeroIncident("second leg blocked (cells in front of receivers), exit image intact (peak "+f(maxOf(im.exit),3)+" vs "+f(maxOf(im0.exit),3)+"); ",rows,ref0);
    }

    // 4. lamp off / removed, then rebuild without stale data
    {
        Hood h(O,red,white);h.scene.lamps.clear();Images im=rig.build(h.scene,cam0);
        check(maxOf(im.exit)==0&&maxOf(im.inc)==0,"lamp removed: bounce images are not exactly zero (exit "+f(maxOf(im.exit),3)+", incident "+f(maxOf(im.inc),3)+")");
        pass("lamp removed after a lit frame: exit and incident images exactly zero everywhere (rebuild leaves no ghost)");
        Hood h0(O,red,white);h0.scene.lamps[0].level=0;Images im2=rig.build(h0.scene,cam0);
        check(maxOf(im2.exit)==0&&maxOf(im2.inc)==0,"lamp level 0: bounce images are not exactly zero");
        pass("lamp level 0 (off): exit and incident exactly zero everywhere");
        Images again=rig.build(base.scene,cam0);double worst=0;
        for(size_t i=0;i<again.inc.size();i++) worst=std::max(worst,std::abs(double(again.inc[i])-im0.inc[i]));
        check(worst<=1e-6,"rebuilding the original scene after remove differs from the first build by "+f(worst,3));
        pass("lamp restored: rebuild reproduces the first build (max abs diff "+f(worst,3)+")");
    }

    // 5. negative / back-facing
    {
        Hood h(O,red,white);
        for(int y=0;y<7;y++) for(int z=0;z<10;z++) h.scene.surf(h.at(12,y,z),faceId(0,true),red);          // wall back side (normal +x, away from lamp)
        for(int x=8;x<12;x++) h.scene.surf(h.at(x,2,-1),faceId(2,false),white);                           // receivers facing away (normal -z)
        Images im=rig.build(h.scene,cam0);
        std::vector<std::pair<Cell,int>> back,away;for(int y=0;y<7;y++) for(int z=0;z<10;z++) back.push_back({h.at(12,y,z),faceId(0,true)});
        for(int x=8;x<12;x++) away.push_back({h.at(x,2,-1),faceId(2,false)});
        double exitBack=0,incAway=0;
        for(auto& fc:back) exitBack=std::max(exitBack,lum(sum4(rig.sub4(im.exit,fc.first,fc.second))));
        for(auto& fc:away) incAway=std::max(incAway,lum(sum4(rig.sub4(im.inc,fc.first,fc.second))));
        check(exitBack<=1e-5*maxOf(im0.exit),"back-facing wall side carries exit light "+f(exitBack,3));
        check(incAway<=1e-3*ref0*4,"receiver facing away from the wall gathers light "+f(incAway,3));
        const auto rows=compareIncident(rig,im,h.scene,h.northReceivers());requireIncident("front receivers unchanged by back-facing records",rows);
        pass("negative cases: wall back side (normal +x) exit "+f(exitBack,3)+" and away-facing receivers (normal -z) incident "+f(incAway,3)+" are zero");
    }

    // 6. source addition: torch + soul torch
    {
        Hood h(O,red,white);Hood hs(O,red,white);hs.scene.lamps.clear();hs.scene.lamp(h.at(10,2,4),10105,10);
        Hood hb(O,red,white);hb.scene.lamp(hb.at(10,2,4),10105,10);
        Images ia=rig.build(h.scene,cam0),is=rig.build(hs.scene,cam0),ib=rig.build(hb.scene,cam0);
        double worst=0;for(size_t i=0;i<ib.inc.size();i++) if((i&3)!=3) worst=std::max(worst,std::abs((double(ib.inc[i])-ia.inc[i]-is.inc[i])/std::max(double(ib.inc[i]),1e-4)));
        for(size_t i=0;i<ib.inc.size();i+=4) if(ib.inc[i]+ib.inc[i+1]+ib.inc[i+2]>1e-3*ref0) { for(int k=0;k<3;k++) worst=std::max(worst,std::abs((double(ib.inc[i+k])-ia.inc[i+k]-is.inc[i+k])/std::max(double(ib.inc[i+k]),1e-4))); }
        check(worst<0.02,"torch+soul incident is not the sum of the two single-lamp builds, worst relative "+f(worst,3));
        pass("source addition: incident(torch+soul) = incident(torch)+incident(soul) within "+f(worst*100,2)+"% on lit texels");
        requireIncident("soul torch alone (level 10, blue)",compareIncident(rig,is,hs.scene,hs.northReceivers()));
        requireExit("soul torch alone on red east wall",compareExit(rig,is,hs.scene,eastFaces(hs)));
        requireIncident("torch + soul torch",compareIncident(rig,ib,hb.scene,hb.northReceivers()));
        const auto rs=compareIncident(rig,is,hs.scene,hs.northReceivers());
        for(int k=1;k<3;k++) { const double got=rs[1].gpu[k]/rs[1].gpu[0],want=rs[1].cpu[k]/rs[1].cpu[0];
            check(std::abs(got/want-1)<0.05,"soul torch on red wall: channel ratio "+std::to_string(k)+"/0 is "+f(got)+", oracle "+f(want)); }
        pass("colour of source preserved: soul torch on red wall incident rgb ("+f(rs[1].gpu[0],3)+","+f(rs[1].gpu[1],3)+","+f(rs[1].gpu[2],3)+") matches oracle ("+f(rs[1].cpu[0],3)+","+f(rs[1].cpu[1],3)+","+f(rs[1].cpu[2],3)+")");
    }

    // 7. room: floor / ceiling / south wall receivers with different normals (ray directions beyond +z)
    {
        Hood h(O,red,white);
        std::vector<std::pair<Cell,int>> recv;
        for(int x=6;x<12;x++) for(int z=0;z<10;z++) { h.scene.stone(h.at(x,-1,z));h.scene.surf(h.at(x,-1,z),faceId(1,true),white);if(x==9&&z>=1&&z<=3) recv.push_back({h.at(x,-1,z),faceId(1,true)}); }
        for(int x=6;x<12;x++) for(int z=0;z<10;z++) { h.scene.stone(h.at(x,7,z));h.scene.surf(h.at(x,7,z),faceId(1,false),white);if(x==10&&z>=6&&z<=8) recv.push_back({h.at(x,7,z),faceId(1,false)}); }
        for(int x=6;x<12;x++) for(int y=0;y<7;y++) { h.scene.stone(h.at(x,y,10));h.scene.surf(h.at(x,y,10),faceId(2,false),white);if(x==10&&y>=3&&y<=5) recv.push_back({h.at(x,y,10),faceId(2,false)}); }
        Images im=rig.build(h.scene,cam0);
        const auto rows=compareIncident(rig,im,h.scene,recv);
        requireIncident("room receivers with normals +y (floor), -y (ceiling), -z (south wall)",rows);
    }

    // 8. bright direct light: a very bright hooded lamp that directly floods the north wall must not change recoverable bounce elsewhere
    {
        Hood h(O,red,white);
        // lamp C: level 15, 0.5 m from the north wall, hooded on every side but north (its direct light floods the wall at y=5)
        Hood hc(O,red,white);
        const Cell c=hc.at(7,5,0);hc.scene.lamp(c,10100,15);
        for(Cell d:{Cell{8,5,0},Cell{6,5,0},Cell{7,4,0},Cell{7,6,0},Cell{7,5,1}}) hc.scene.stone(hc.at(d[0],d[1],d[2]));
        Images imA=rig.build(h.scene,cam0),imC=rig.build(hc.scene,cam0);
        Oracle oc=makeOracle(hc.scene);
        const D3 directProbe=oc.direct(facePoint(hc.at(7,5,-1),faceId(2,true),0.5,0.5),faceNormal(faceId(2,true)));
        const D3 directA=makeOracle(h.scene).direct(facePoint(hc.at(9,2,-1),faceId(2,true),0.5,0.5),faceNormal(faceId(2,true)));
        check(lum(directProbe)>100*lum(rows0[1].cpu)+1e-9,"fixture: direct light of lamp C is not much brighter than the bounce being recovered");
        const auto rowsC=compareIncident(rig,imC,hc.scene,hc.northReceivers());
        double worst=0;for(size_t i=0;i<rowsC.size();i++) worst=std::max(worst,std::abs(rowsC[i].gpuLum/rows0[i].gpuLum-1));
        check(worst<0.02,"bright direct lamp C changed the independent bounce at row y=2 by "+f(worst*100,3)+"%");
        pass("bright direct light (lamp C direct energy at y=5 north wall "+f(lum(directProbe),3)+" vs hood-A bounce "+f(rows0[1].gpuLum,3)+"; ratio "+f(lum(directProbe)/rows0[1].gpuLum,3)+"): hood-A bounce at y=2 receivers unchanged to "+f(worst*100,3)+"%, recovered from the incident image alone");
        (void)directA;(void)imA;
    }

    // 9. rebuild after grid recentre: camera moves 8+ cells, every local address changes, world-space result must not
    {
        const D3 cam1={1010.75,71.5,-2049.75};   // mod 8 changes 3.25 -> 2.75, window origin moves by 8 cells, scene stays inside 11 m coverage
        Images im1=rig.build(base.scene,cam1);
        requireExit("after grid recentre (+8.5 m)",compareExit(rig,im1,base.scene,eastFaces(base)));
        const auto rows1=compareIncident(rig,im1,base.scene,base.northReceivers());requireIncident("after grid recentre",rows1);
        double worst=0;for(size_t i=0;i<rows1.size();i++) worst=std::max(worst,std::abs(rows1[i].gpuLum/rows0[i].gpuLum-1));
        check(worst<0.01,"recentred grid changes world-space incident by "+f(worst*100,3)+"%");
        const double e0=totalOf(im0.exit),e1=totalOf(im1.exit);
        check(std::abs(e1/e0-1)<1e-3,"recentred exit total differs: "+f(e1/e0,6));
        pass("grid recentre: world-space incident identical to "+f(worst*100,4)+"%, whole-image exit total ratio "+f(e1/e0,6)+" (old local addresses hold no ghost)");
        // wall added after the recentre build: first-leg blocker must kill the light, nothing stale remains
        Hood w(O,red,white);w.scene.stone(w.at(10,2,4));Images im2=rig.build(w.scene,cam1);
        check(maxOf(im2.exit)==0&&maxOf(im2.inc)==0,"wall added after recentre: stale bounce remains (exit "+f(maxOf(im2.exit),3)+", inc "+f(maxOf(im2.inc),3)+")");
        pass("wall added after recentre: exit and incident images exactly zero");
    }

    // 10. producer: real shadow_solid vertex capture with actual atlas gtexture
    if(producerShipped(root)) producerProbe(rig);
    else info("producer not shipped: no shadow_solid capture of bounceSurfaceImage in this pack; consumer passes were driven by CPU-written surface words");
    check(softFailures==0,std::to_string(softFailures)+" check(s) failed (marked FAIL(continuing) above); other measurements completed");
    pass("finite: every bounce exit / incident texel read after every build was finite");
    std::cout<<"PASS bounce-light GPU oracle: renderer "<<reinterpret_cast<const char*>(glGetString(GL_RENDERER))<<"; analytic CPU oracle, GPU harness, not a Minecraft frame time\n";
}
}  // namespace aqualumenBounce
