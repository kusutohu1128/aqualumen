// Independent GPU QA for the lava area light (candidate packs shipping lib/lava_grid.glsl).
//
// Production path under test, unmodified:
//   actual fluid quads (Sodium/vanilla geometry: corner heights - 0.001, 0.001 side insets, back-facing
//   duplicates) -> shadow_solid.vsh captureLocalCell()/captureLava() -> lampCellImage / lampIndexImage
//   -> shadowcomp1.csh (real 8x8x8 dispatch: publishLavaGroup / publishLavaNeighbors / height field)
//   -> local_lighting.glsl lampLighting() (lavaLighting + regular lamps) evaluated per receiver.
// Independent controls (none reuse the shader's estimator):
//   * CPU re-statement of the capture/publish bit contract (raw words, corner planes, group bits,
//     neighbour lists, plane records) compared bit for bit with the GPU images;
//   * a double-precision area integral of the DRAWN fluid surface (midpoint sub-triangles) with exact
//     segment-vs-box and segment-vs-fluid-prism visibility, cross-checked against the earlier
//     polygon-clipping reference in reports/2026-11-21-lava-light/area-shader/pillar-results.json;
//   * Lambert's closed-form polygon irradiance in double for the fully visible pedestal block;
//   * scene pairs differing in one cause (pillar, torch, lava, history) and the 1.8.0 baseline pack.
// Timings printed are GPU-harness timings of shadowcomp1, NOT Minecraft frame times.
#pragma once
#include <set>
#include <map>
#include <tuple>
namespace aqualumenLava {
namespace LL=aqualumenLocalLights;
using D3=LL::D3;

inline D3 add(D3 a,D3 b){return {a[0]+b[0],a[1]+b[1],a[2]+b[2]};}
inline D3 sub(D3 a,D3 b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
inline D3 mul(D3 a,double s){return {a[0]*s,a[1]*s,a[2]*s};}
inline double dot(D3 a,D3 b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline D3 cross(D3 a,D3 b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
inline double len(D3 a){return std::sqrt(dot(a,a));}
inline D3 unit(D3 a){return mul(a,1.0/len(a));}
inline void require(bool ok,const std::string& m){ if(!ok) throw std::runtime_error("lava-light QA FAIL: "+m); }
inline std::string fmt(double v){std::ostringstream s;s<<std::setprecision(6)<<v;return s.str();}

struct Report {
    int failed=0,passed=0;
    std::ostringstream json;bool first=true;
    void check(bool ok,const std::string& what) {
        if(ok) {++passed;std::cout<<"PASS lava "<<what<<"\n";}
        else {++failed;std::cout<<"FAIL lava "<<what<<"\n";}
    }
    void metric(const std::string& key,const std::string& value) {json<<(first?"":",\n")<<"    \""<<key<<"\": "<<value;first=false;}
    void metric(const std::string& key,double v) {std::ostringstream s;s<<std::setprecision(9)<<(std::isfinite(v)?v:-1.0);metric(key,s.str());}
};

// ------------------------------------------------------------------------------------------- scene model
struct Lava { int x,y,z; std::array<double,4> h; };   // fluid corner heights, corner c=[x>.5]+2[z>.5]
struct Face { std::array<int,3> cell; int face; std::array<D3,4> v; D3 n; bool back; };
struct Scene {
    std::vector<LL::Block> blocks;    // stones (full cubes) and lamps through the production block path
    std::vector<Lava> lava;
    std::set<std::tuple<int,int,int>> solid() const {
        std::set<std::tuple<int,int,int>> s;
        for(const auto& b:blocks) if(b.id==10001) s.insert({b.x,b.y,b.z});
        return s;
    }
    const Lava* lavaAt(int x,int y,int z) const { for(const auto& l:lava) if(l.x==x&&l.y==y&&l.z==z) return &l; return nullptr; }
};
inline const double kEps=0.001;   // vanilla/Sodium fluid face offsets
inline std::array<double,4> ownHeights(const Scene& s,const Lava& l) {
    if(s.lavaAt(l.x,l.y+1,l.z)) return {1,1,1,1};   // a fluid column below fluid is full height
    return l.h;
}
// Iris face normal of a (possibly non-planar) quad: (v2-v0) x (v3-v1).
inline D3 irisNormal(const std::array<D3,4>& v) { return unit(cross(sub(v[2],v[0]),sub(v[3],v[1]))); }
inline Face makeFace(const Lava& l,int face,std::array<D3,4> v,D3 outward,bool back) {
    Face f{{l.x,l.y,l.z},face,v,{0,0,0},back};
    if(dot(irisNormal(f.v),outward)<0) std::reverse(f.v.begin(),f.v.end());
    if(back) std::reverse(f.v.begin(),f.v.end());
    f.n=irisNormal(f.v);
    return f;
}
// Faces exactly as the client meshes them (absolute world coordinates).
inline std::vector<Face> fluidFaces(const Scene& s) {
    const auto solid=s.solid();
    auto isSolid=[&](int x,int y,int z){return solid.count({x,y,z})>0;};
    std::vector<Face> out;
    for(const Lava& l:s.lava) {
        std::array<double,4> h=ownHeights(s,l);
        const bool above=s.lavaAt(l.x,l.y+1,l.z)!=nullptr;
        const bool up=!above && !(isSolid(l.x,l.y+1,l.z)&&std::min({h[0],h[1],h[2],h[3]})>=1.0);
        const bool down=!s.lavaAt(l.x,l.y-1,l.z)&&!isSolid(l.x,l.y-1,l.z);
        const double y0=down?kEps:0.0;
        if(up) for(double& c:h) c-=kEps;
        auto P=[&](double x,double y,double z){return D3{l.x+x,l.y+y,l.z+z};};
        if(up) {
            std::array<D3,4> q={P(0,h[0],0),P(0,h[2],1),P(1,h[3],1),P(1,h[1],0)};
            out.push_back(makeFace(l,0,q,{0,1,0},false));
            out.push_back(makeFace(l,0,q,{0,1,0},true));   // shouldRenderBackwardUpFace: open neighbourhood
        }
        if(down) out.push_back(makeFace(l,1,{P(0,y0,1),P(0,y0,0),P(1,y0,0),P(1,y0,1)},{0,-1,0},false));
        struct Side { int dx,dz,face; };
        for(Side sd:{Side{1,0,2},Side{-1,0,3},Side{0,1,4},Side{0,-1,5}}) {
            if(s.lavaAt(l.x+sd.dx,l.y,l.z+sd.dz)||isSolid(l.x+sd.dx,l.y,l.z+sd.dz)) continue;
            std::array<D3,4> q;
            if(sd.dx) {
                const double x=sd.dx>0?1-kEps:kEps;const double ha=sd.dx>0?h[1]:h[0],hb=sd.dx>0?h[3]:h[2];
                q={P(x,ha,0),P(x,hb,1),P(x,y0,1),P(x,y0,0)};
            } else {
                const double z=sd.dz>0?1-kEps:kEps;const double ha=sd.dz>0?h[2]:h[0],hb=sd.dz>0?h[3]:h[1];
                q={P(0,ha,z),P(1,hb,z),P(1,y0,z),P(0,y0,z)};
            }
            const D3 outward={double(sd.dx),0,double(sd.dz)};
            out.push_back(makeFace(l,sd.face,q,outward,false));
            out.push_back(makeFace(l,sd.face,q,outward,true));   // lava sides are drawn double-sided
        }
    }
    return out;
}

// --------------------------------------------------------------------------- production capture + publish
struct Rig {
    LL::World w;
    double radiance[3]={0,0,0};
    D3 cam={0,0,0};
    void init(const fs::path& root) {
        w.init(root);
        const std::string src=LL::slurp(root/"lib/lava_lighting.glsl");std::smatch m;
        require(std::regex_search(src,m,std::regex("lavaRadiance\\s*=\\s*vec3\\(\\s*([0-9.]+)\\s*,\\s*([0-9.]+)\\s*,\\s*([0-9.]+)\\s*\\)")),"lava_lighting.glsl lacks const lavaRadiance");
        for(int i=0;i<3;i++) radiance[i]=std::stod(m[1+i]);
    }
    static void require(bool ok,const std::string& m){ if(!ok) throw std::runtime_error("lava-light QA FAIL: "+m); }
    void emitFace(const Face& f) {
        glNormal3d(f.n[0],f.n[1],f.n[2]);
        for(const D3& v:f.v) {
            float mid[3];
            for(int i=0;i<3;i++) mid[i]=float((f.cell[i]+0.5-v[i])*64.0);
            glVertexAttrib4f(10,10650.f,0,0,0);glVertexAttrib4f(11,mid[0],mid[1],mid[2],15.f);
            glVertex3f(float(v[0]-cam[0]),float(v[1]-cam[1]),float(v[2]-cam[2]));
        }
    }
    // Same state as LL::World::capture; fluid quads go through the solid shadow program like lava in Iris.
    void capture(const Scene& s,bool reverse=false) {
        w.lastCam=cam;
        auto faces=fluidFaces(s);
        if(reverse) std::reverse(faces.begin(),faces.end());
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        LL::resetTextureMatrices();
        glEnable(GL_RASTERIZER_DISCARD);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for(int p=0;p<3;p++) {
            glUseProgram(w.pass[p]);
            glUniformMatrix4fv(glGetUniformLocation(w.pass[p],"shadowModelViewInverse"),1,GL_FALSE,identity);
            glUniform3f(glGetUniformLocation(w.pass[p],"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
            glUniform1i(glGetUniformLocation(w.pass[p],"isEyeInWater"),0);
            LL::World::imageUnit(w.pass[p],"lampCellImage",0);LL::World::imageUnit(w.pass[p],"lampIndexImage",1);LL::World::imageUnit(w.pass[p],"shoreFaceImage",2);
            glBindImageTexture(0,w.cell,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBindImageTexture(1,w.index,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBindImageTexture(2,w.dummyShore,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBegin(GL_QUADS);
            const size_t n=s.blocks.size();
            for(size_t i=0;i<n;i++) {
                const LL::Block& b=s.blocks[reverse?n-1-i:i];
                if(b.pass!=p) continue;
                float lo[3],hi[3];LL::World::boxFor(b,lo,hi);LL::World::emitBox(b,cam,lo,hi);
            }
            if(p==0) for(const Face& f:faces) emitFace(f);
            glEnd();
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        }
        glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        require(glGetError()==GL_NO_ERROR,"GL error during lava shadow capture");
    }
    void build(const Scene& s,bool reverse=false) { w.clearRaw();capture(s,reverse);w.publish(); }
    // Direct light only: blockLevel 0 removes the vanilla residual, receivers stay inside the 19 m coverage.
    std::vector<std::array<float,3>> light(const std::vector<std::pair<D3,D3>>& rx) {
        std::vector<LL::Query> q;
        for(const auto& r:rx) q.push_back({r.first,r.second,{0,1,0},0.075f,0.f,false});
        return w.evaluate(q,cam);
    }
};

// ------------------------------------------------------------------------- CPU contract re-statement
inline int lin(int x,int y,int z,int width){return x+width*(z+width*y);}
struct Contract {
    std::map<int,unsigned> words;     // linear cell -> raw word (lava cells only)
    std::map<int,std::array<unsigned,4>> corners;
    std::map<int,unsigned> groupBits; // cluster linear -> bits
};
inline Contract lavaContract(const Scene& s,const D3& cam) {
    Contract c;
    const int ox=int(std::floor(cam[0]/8))*8-32,oy=int(std::floor(cam[1]/8))*8-32,oz=int(std::floor(cam[2]/8))*8-32;
    for(const Face& f:fluidFaces(s)) {
        const int gx=f.cell[0]-ox,gy=f.cell[1]-oy,gz=f.cell[2]-oz;
        Rig::require(gx>=0&&gy>=0&&gz>=0&&gx<64&&gy<64&&gz<64,"fixture lava outside the 64^3 grid");
        const int a=lin(gx,gy,gz,64);
        c.words[a]|=10u|(1u<<unsigned(6+f.face));
        auto& k=c.corners[a];
        for(const D3& v:f.v) {
            const double lx=v[0]-f.cell[0],ly=v[1]-f.cell[1],lz=v[2]-f.cell[2];
            const double scaled=std::clamp(ly,0.0,1.0)*62.0;
            Rig::require(std::abs(scaled-std::floor(scaled)-0.5)>0.02,"fixture height "+fmt(ly)+" sits on a 1/62 rounding tie");
            const int corner=int(lx>0.5)+2*int(lz>0.5);
            k[corner]=std::max(k[corner],1u+unsigned(std::lround(scaled)));
        }
        const int cluster=lin(gx/8,gy/8,gz/8,8),sub=lin((gx%8)/4,(gy%8)/4,(gz%8)/4,2);
        c.groupBits[cluster]|=1u<<unsigned(sub);
    }
    return c;
}
inline unsigned packed(const std::array<unsigned,4>& k){return k[0]|(k[1]<<6)|(k[2]<<12)|(k[3]<<18);}
inline std::array<int,3> axes(int face,int layer,int u,int v) {
    if(face<2) return {u,layer,v};
    if(face<4) return {layer,v,u};
    return {u,v,layer};
}

// ------------------------------------------------------------------------- independent radiometric reference
struct Tri { D3 a,b,c,n; };
struct Box { D3 lo,hi; };
struct FluidVolume { int x,y,z; std::array<double,4> h; };
struct Occluders { std::vector<Box> boxes; std::vector<FluidVolume> fluid; };
// Emitting triangles of the drawn surface (front quads only; the same diagonal v0-v2 the GPU index buffer uses).
inline std::vector<Tri> emitters(const std::vector<Face>& faces) {
    std::vector<Tri> t;
    for(const Face& f:faces) {
        if(f.back) continue;
        for(auto idx:{std::array<int,3>{0,1,2},std::array<int,3>{0,2,3}}) {
            Tri x{f.v[idx[0]],f.v[idx[1]],f.v[idx[2]],{0,0,0}};
            D3 n=cross(sub(x.b,x.a),sub(x.c,x.a));
            if(len(n)<1e-12) continue;
            n=unit(n);if(dot(n,f.n)<0){std::swap(x.b,x.c);n=mul(n,-1);}
            x.n=n;t.push_back(x);
        }
    }
    return t;
}
// The published-contract surface: quantized heights, no insets (what the GPU is allowed to integrate).
inline std::vector<Tri> contractEmitters(const Scene& s,bool emitTop=true) {
    std::vector<Tri> t;
    for(const Face& f:fluidFaces(s)) {
        if(f.back) continue;
        std::array<double,4> h;
        for(int c=0;c<4;c++) {
            double y=0;
            for(const Face& g:fluidFaces(s)) if(g.cell==f.cell) for(const D3& v:g.v)
                if(int(v[0]-g.cell[0]>0.5)+2*int(v[2]-g.cell[2]>0.5)==c) y=std::max(y,v[1]-g.cell[1]);
            h[c]=std::lround(std::clamp(y,0.0,1.0)*62.0)/62.0;
        }
        const D3 p={double(f.cell[0]),double(f.cell[1]),double(f.cell[2])};
        auto P=[&](double x,double y,double z){return add(p,D3{x,y,z});};
        std::array<D3,4> q;D3 out;
        switch(f.face) {
            case 0: if(!emitTop) continue; q={P(0,h[0],0),P(0,h[2],1),P(1,h[3],1),P(1,h[1],0)};out={0,1,0};break;
            case 1: q={P(0,0,1),P(0,0,0),P(1,0,0),P(1,0,1)};out={0,-1,0};break;
            case 2: q={P(1,h[1],0),P(1,h[3],1),P(1,0,1),P(1,0,0)};out={1,0,0};break;
            case 3: q={P(0,h[0],0),P(0,h[2],1),P(0,0,1),P(0,0,0)};out={-1,0,0};break;
            case 4: q={P(0,h[2],1),P(1,h[3],1),P(1,0,1),P(0,0,1)};out={0,0,1};break;
            default: q={P(0,h[0],0),P(1,h[1],0),P(1,0,0),P(0,0,0)};out={0,0,-1};break;
        }
        for(auto idx:{std::array<int,3>{0,1,2},std::array<int,3>{0,2,3}}) {
            Tri x{q[idx[0]],q[idx[1]],q[idx[2]],{0,0,0}};
            D3 n=cross(sub(x.b,x.a),sub(x.c,x.a));
            if(len(n)<1e-12) continue;
            n=unit(n);if(dot(n,out)<0){std::swap(x.b,x.c);n=mul(n,-1);}
            x.n=n;t.push_back(x);
        }
    }
    return t;
}
// Lambert (1760) closed form for a polygon clipped to the receiver hemisphere, double precision.
inline double lambert(const Tri& t,D3 r,D3 n) {
    std::vector<D3> poly={sub(t.a,r),sub(t.b,r),sub(t.c,r)};
    if(dot(t.n,mul(poly[0],-1))<=0) return 0;
    std::vector<D3> clipped;
    for(size_t i=0;i<poly.size();i++) {
        D3 p=poly[(i+poly.size()-1)%poly.size()],q=poly[i];double hp=dot(p,n),hq=dot(q,n);
        if((hp<0&&hq>0)||(hp>0&&hq<0)) clipped.push_back(add(p,mul(sub(q,p),hp/(hp-hq))));
        if(hq>=0) clipped.push_back(q);
    }
    if(clipped.size()<3) return 0;
    double sum=0;
    for(size_t i=0;i<clipped.size();i++) {
        D3 a=unit(clipped[i]),b=unit(clipped[(i+1)%clipped.size()]);
        D3 g=cross(a,b);double s=len(g);if(s<1e-15) continue;
        sum+=std::atan2(s,dot(a,b))*dot(n,g)/s;
    }
    return 0.5*std::abs(sum);
}
inline bool segmentHitsBox(D3 s,D3 d,const Box& b) {
    double t0=0,t1=1;
    for(int i=0;i<3;i++) {
        if(std::abs(d[i])<1e-15) { if(s[i]<=b.lo[i]||s[i]>=b.hi[i]) return false; continue; }
        double a=(b.lo[i]-s[i])/d[i],c=(b.hi[i]-s[i])/d[i];if(a>c) std::swap(a,c);
        t0=std::max(t0,a);t1=std::min(t1,c);if(t1-t0<=1e-9) return false;
    }
    return t1-t0>1e-9;
}
// Fluid body enclosed by the drawn surface: two prisms split along the x=z diagonal (local coordinates),
// shrunk by 2 mm so that it lies strictly inside the drawn faces (tops at h-1 mm, sides inset 1 mm): an
// emitter sample on a drawn face never starts inside the body that occludes other parts of the flow.
inline const double kShrink=2*kEps;
inline bool segmentHitsFluid(D3 s,D3 d,const FluidVolume& f) {
    const D3 o={double(f.x),double(f.y),double(f.z)};s=sub(s,o);
    const auto& h=f.h;const double k=kShrink;
    for(int half=0;half<2;half++) {
        // Half-spaces a.p <= b.
        std::vector<std::pair<D3,double>> hs;
        hs.push_back({{0,-1,0},-k});hs.push_back({{-1,0,0},-k});hs.push_back({{1,0,0},1-k});
        hs.push_back({{0,0,-1},-k});hs.push_back({{0,0,1},1-k});
        if(half==0) {   // x >= z: corners 0,1,3
            hs.push_back({{-1,0,1},0});
            hs.push_back({{-(h[1]-h[0]),1,-(h[3]-h[1])},h[0]-k});
        } else {        // x < z: corners 0,2,3
            hs.push_back({{1,0,-1},0});
            hs.push_back({{-(h[3]-h[2]),1,-(h[2]-h[0])},h[0]-k});
        }
        double t0=0,t1=1;bool empty=false;
        for(auto& [a,b]:hs) {
            const double num=b-dot(a,s),den=dot(a,d);
            if(std::abs(den)<1e-15) { if(num<0) {empty=true;break;} continue; }
            const double t=num/den;
            if(den>0) t1=std::min(t1,t); else t0=std::max(t0,t);
            if(t1-t0<=1e-9) {empty=true;break;}
        }
        if(!empty&&t1-t0>1e-9) return true;
    }
    return false;
}
struct Irr { double clear=0,visible=0; };
// Midpoint quadrature over N^2 congruent sub-triangles per emitting triangle.
inline Irr areaIntegral(const std::vector<Tri>& tris,D3 r,D3 n,const Occluders& occ,int N) {
    Irr e;
    const D3 origin=add(r,mul(n,1e-4));
    for(const Tri& t:tris) {
        const double area=0.5*len(cross(sub(t.b,t.a),sub(t.c,t.a)))/double(N*N);
        D3 lo=origin,hi=origin;
        for(const D3& v:{t.a,t.b,t.c}) for(int i=0;i<3;i++){lo[i]=std::min(lo[i],v[i]);hi[i]=std::max(hi[i],v[i]);}
        std::vector<const Box*> boxes;std::vector<const FluidVolume*> fluid;
        for(const Box& b:occ.boxes) { bool o=true;for(int i=0;i<3;i++) o=o&&b.lo[i]<hi[i]&&b.hi[i]>lo[i]; if(o) boxes.push_back(&b); }
        for(const FluidVolume& f:occ.fluid) { bool o=f.x<hi[0]&&f.x+1>lo[0]&&f.y<hi[1]&&f.y+1>lo[1]&&f.z<hi[2]&&f.z+1>lo[2]; if(o) fluid.push_back(&f); }
        const D3 u=sub(t.b,t.a),v=sub(t.c,t.a);
        for(int i=0;i<N;i++) for(int j=0;j+i<N;j++) for(int k=0;k<2;k++) {
            if(k==1&&i+j>=N-1) continue;
            const double a=(i+(k?2.0:1.0)/3.0)/N,b=(j+(k?2.0:1.0)/3.0)/N;
            const D3 p=add(t.a,add(mul(u,a),mul(v,b)));
            const D3 d=sub(origin,p);const double d2=dot(d,d);
            const double cs=dot(t.n,d),cr=-dot(n,d);
            if(cs<=0||cr<=0) continue;
            const double w=cs*cr/(d2*d2)*area;
            e.clear+=w;
            const D3 s=add(p,mul(t.n,1e-6)),seg=sub(origin,s);
            bool hit=false;
            for(const Box* bx:boxes) if(segmentHitsBox(s,seg,*bx)) {hit=true;break;}
            if(!hit) for(const FluidVolume* f:fluid) if(segmentHitsFluid(s,seg,*f)) {hit=true;break;}
            if(!hit) e.visible+=w;
        }
    }
    return e;
}
inline Occluders occludersOf(const Scene& s) {
    Occluders o;
    for(const auto& b:s.blocks) if(b.id==10001) o.boxes.push_back({{double(b.x),double(b.y),double(b.z)},{b.x+1.0,b.y+1.0,b.z+1.0}});
    for(const auto& l:s.lava) o.fluid.push_back({l.x,l.y,l.z,ownHeights(s,l)});
    return o;
}

// ------------------------------------------------------------------------------------------------ probe
// The 512 regular-lamp cluster rows (the full image is read; glGetTexImage always returns every row).
inline std::vector<float> lampRows(LL::World& w) {
    auto all=w.readFloat(w.list,w.pList.w,w.pList.h,4);
    all.resize(size_t(512)*w.pList.w*4);return all;
}
struct RoomSpec { int pool; bool pillar; bool torch; };
inline Scene room(int pool,bool pillar,bool torchOn,bool lavaOn=true,double height=8.0/9.0) {
    Scene s;
    std::set<std::tuple<int,int,int>> poolCells;
    if(lavaOn) {
        if(pool==1) poolCells.insert({202,172,361});
        else for(int x=201;x<=203;x++) for(int z=360;z<=362;z++) poolCells.insert({x,172,z});
    }
    for(int x=198;x<=209;x++) for(int y=172;y<=180;y++) for(int z=359;z<=367;z++) {
        const bool shell=x==198||x==209||y==172||y==180||z==359||z==367;
        if(!shell||poolCells.count({x,y,z})) continue;
        s.blocks.push_back(LL::stone(x,y,z));
    }
    for(int x=199;x<=208;x++) for(int y=173;y<=179;y++) s.blocks.push_back(LL::stone(x,y,366));   // white wall
    for(auto [x,y,z]:poolCells) {s.blocks.push_back(LL::stone(x,171,z));s.lava.push_back({x,y,z,{height,height,height,height}});}
    if(pillar) for(int y=173;y<=175;y++) s.blocks.push_back(LL::stone(202,y,364));
    if(torchOn) s.blocks.push_back(LL::torch(202,173,365,14));
    return s;
}

// Compare the actual outgoing-pass face bank and the production terrain reconstruction
// against full per-receiver transport. Reuse the same published geometry in both paths.
inline void faceBankProbe(const fs::path& root,Rig& rig,Report& rep) {
    namespace B=aqualumenBounce;
    if(!fs::exists(root/"lib/lava_face_cache.glsl")) return;
    B::Rig surfaces;
    surfaces.init(root);
    LL::World& w=rig.w;
    surfaces.w.index=w.index;
    surfaces.w.field=w.field;
    surfaces.w.list=w.list;
    rig.cam={.5,3.5,4.5};
    B::Scene patches;
    Scene scene;
    for(int x=-6;x<=5;++x) for(int z=-6;z<=5;++z) {
        scene.lava.push_back({x,0,z,{.889,.889,.889,.889}});
        scene.blocks.push_back(LL::stone(x,-1,z));
    }
    for(int x=-2;x<=2;++x) for(int y=1;y<=4;++y) {
        scene.blocks.push_back(LL::stone(x,y,7));
        patches.surf({x,y,7},4,{195,195,195});
    }
    const std::string prefix="#version 430 compatibility\n";
    const std::string sampleSource=prefix+expand(root/"lib/uniforms.glsl",root)
        +expand(root/"lib/lava_face_cache.glsl",root)
        +"uniform sampler2D probeData;out vec4 result;void main(){int i=int(gl_FragCoord.x);"
         "result=lavaFaceAtReceiver(texelFetch(probeData,ivec2(i,0),0).xyz,vec3(0,0,-1));}";
    GLuint reader=link(prefix+"void main(){gl_Position=gl_Vertex;}",sampleSource,"lava face-bank receiver");
    auto read=[&](const std::vector<D3>& points) {
        std::vector<float> data(points.size()*16),samples;
        for(size_t i=0;i<points.size();++i)
            for(int c=0;c<3;++c) data[4*i+c]=float(points[i][c]-rig.cam[c]);
        glUseProgram(reader);
        glUniform1i(glGetUniformLocation(reader,"aqualumenBounceExit"),6);
        glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,surfaces.exitTex);glActiveTexture(GL_TEXTURE0);
        w.runProgram(reader,data,int(points.size()),samples,rig.cam);
        return samples;
    };
    auto publish=[&](const Scene& current) {
        rig.build(current);
        surfaces.uploadSurfaces(patches,rig.cam);
        surfaces.dispatch(surfaces.p2,surfaces.groups2,rig.cam,false);
    };
    publish(scene);
    std::vector<D3> points;
    for(int x=-2;x<=2;++x) for(int y=1;y<=4;++y)
        for(double dx:{.25,.75}) for(double dy:{.25,.75}) points.push_back({x+dx,y+dy,7.});
    std::vector<std::pair<D3,D3>> queries;
    for(const D3& p:points) queries.push_back({p,{0,0,-1}});
    auto ref=rig.light(queries);
    auto got=read(points);
    double worst=0.,peak=0.;
    bool valid=true;
    for(size_t i=0;i<points.size();++i) {
        valid=valid && got[4*i+3]>=0.;
        for(int c=0;c<3;++c) {
            peak=std::max(peak,double(ref[i][c]));
            worst=std::max(worst,std::abs(double(got[4*i+c])-ref[i][c]));
        }
    }
    rep.check(valid && peak>.01 && worst/peak<.002,"dense lava: all 80 stored quarter faces agree with direct per-point transport (max error/peak "+fmt(worst/peak)+")");
    const auto middle=read({{0.,2.,7.},{-0.25,1.75,7.},{.25,1.75,7.},{-.25,2.25,7.},{.25,2.25,7.},{0.,2.,6.5},{3.5,2.,7.}});
    double error=0.;
    for(int c=0;c<4;++c)
        error=std::max(error,std::abs(middle[c]-.25*(middle[4+c]+middle[8+c]+middle[12+c]+middle[16+c])));
    rep.check(error<.0001 && middle[23]<0. && middle[27]<0.,"dense lava: interpolate across four coplanar faces; reject off-plane and uncaptured neighbours");
    if(LL::slurp(root/"shadowcomp2.csh").find("visibleFootprint(")!=std::string::npos) {
        D3 frontCamera=rig.cam;
        rig.cam={.5,3.5,10.5};
        publish(scene); // the light-facing face of the wall is on the far side of the stone
        auto farSide=read({{.25,2.25,7.},{.75,2.75,7.}});
        auto centre=rig.light({{{.5,2.5,7.},{0,0,-1}}});
        bool centred=centre[0][0]>.01f;
        for(int c=0;c<3;++c)
            centred=centred && std::abs(farSide[c]-centre[0][c])<.003*centre[0][0]
                      && std::abs(farSide[c]-farSide[4+c])<.00001;
        rep.check(centred,"dense lava: hidden diffuse face retains its nonzero centre radiance for reflection");
        Scene withLamp=scene;
        withLamp.blocks.push_back(LL::soulTorch(0,1,5,10));
        publish(withLamp);
        auto split=read({{.25,2.25,7.},{.75,2.75,7.}});
        auto separate=rig.light({{{.25,2.25,7.},{0,0,-1}},{{.75,2.75,7.},{0,0,-1}}});
        rep.check(std::abs(split[0]-split[4])>.001 && separate[0][2]>split[2],
                  "dense lava: adding a soul lamp restores separate samples on hidden faces and independently adds blue");
        rig.cam=frontCamera;
        publish(scene);
    }
    if(fs::exists(root/"lib/lava_reuse.glsl")) {
        publish(scene); // the new geometry has completed its first clean publication
        const auto a=B::faceAddress(B::toLocal({-2,1,7},rig.cam),4);
        const float sentinel[]={6.5f,.125f,.25f,.75f};
        glBindTexture(GL_TEXTURE_2D,surfaces.exitTex);
        glTexSubImage2D(GL_TEXTURE_2D,0,2*a[0],512+2*a[1],1,1,GL_RGBA,GL_FLOAT,sentinel);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
        publish(scene);
        const auto reused=read({points.front()});
        rep.check(std::abs(reused[0]-6.5f)<.0001f,"identical stationary geometry reuses the certified lava solution (injected sample read back)");
    }
    for(int x=-9;x<10;++x) for(int y=0;y<6;++y) scene.blocks.push_back(LL::stone(x,y,6));
    publish(scene);
    const auto hidden=read(points);
    double dark=0.;
    for(size_t i=0;i<points.size();++i) for(int c=0;c<3;++c) dark=std::max(dark,double(hidden[4*i+c]));
    rep.check(dark<.0001,"dense lava: a new opaque wall removes every cached direct-light sample on the receiver");
    scene.lava.clear();
    publish(scene);
    const auto cleared=read(points);
    bool invalid=true;
    for(size_t i=0;i<points.size();++i) invalid=invalid && cleared[4*i+3]<0.;
    rep.check(invalid,"dense lava: clearing every source invalidates the entire former receiver set on the next capture");
    glDeleteProgram(reader);
}

inline void receiverRecordProbe(const fs::path& root,LL::World& world,Report& rep) {
    if(!fs::exists(root/"lib/area_receiver.glsl")) return;
    const std::string prefix="#version 430 compatibility\n";
    const std::string shader=prefix+expand(root/"lib/area_receiver.glsl",root)+
        "uniform sampler2D probeData;out vec4 value;void main(){int i=int(gl_FragCoord.x);"
        "vec3 n=texelFetch(probeData,ivec2(i,0),0).xyz;"
        "vec2 pair=texelFetch(probeData,ivec2(i,1),0).xy;"
        "vec2 restored=areaUnpackPair(areaPackPair(pair));"
        "value=vec4(areaDecodeNormal(areaEncodeNormal(n)),length(restored-pair));}";
    const GLuint reader=link(prefix+"void main(){gl_Position=gl_Vertex;}",shader,"deferred area receiver transport");
    constexpr int count=4102;
    std::vector<float> data(16*count,0),out;
    for(int i=0;i<count;++i) {
        D3 n={0,0,0};
        if(i<6) n[i/2]=(i%2)?1:-1;
        else {
            double z=2.*(i-5.5)/(count-6)-1.;
            double r=std::sqrt(std::max(0.,1.-z*z));
            n={r*std::cos(i*2.3999632297),r*std::sin(i*2.3999632297),z};
        }
        for(int c=0;c<3;++c) data[4*i+c]=float(n[c]);
        data[4*(count+i)]=float(i)/float(count-1);
        data[4*(count+i)+1]=float((i*2377)%count)/float(count-1);
    }
    world.runProgram(reader,data,count,out,{0,0,0});
    double axes=0.,maxNormal=0.,maxPair=0.;
    for(int i=0;i<count;++i) {
        double error=0.;
        for(int c=0;c<3;++c) error+=std::pow(out[4*i+c]-data[4*i+c],2);
        maxNormal=std::max(maxNormal,std::sqrt(error));
        if(i<6) axes=std::max(axes,std::sqrt(error));
        maxPair=std::max(maxPair,double(out[4*i+3]));
    }
    rep.check(axes==0 && maxNormal<.0015 && maxPair<.00018,
              "deferred receiver: all six cube normals exact; 4096 oblique normals and pairs round-trip through the production packing (max unit-vector error "
              +fmt(maxNormal)+", paired-field error "+fmt(maxPair)+")");
    glDeleteProgram(reader);
}

inline int probe(const fs::path& root,const fs::path& baseline=fs::path(),const fs::path& jsonOut=fs::path()) {
    Report rep;
    Rig rig;rig.init(root);
    LL::World& w=rig.w;
    require(w.lavaLayout,"pack under test ships no lib/lava_grid.glsl");
    std::cout<<"LAVA QA renderer: "<<w.renderer<<" | production sources: shadow_solid.vsh (captureLava), shadowcomp1.csh, local_lighting.glsl lampLighting"
             <<" | lavaRadiance="<<rig.radiance[0]<<","<<rig.radiance[1]<<","<<rig.radiance[2]<<"\n";
    rep.metric("renderer","\""+w.renderer+"\"");
    const double R=rig.radiance[0];
    {   // Iris 1.8.8 accepts at most 16 custom images; the candidate must enlarge existing ones, not add more.
        const std::string props=LL::slurp(root/"shaders.properties");int images=0;
        std::regex re("(^|\\n)image\\.\\w+=");for(auto it=std::sregex_iterator(props.begin(),props.end(),re);it!=std::sregex_iterator();++it) ++images;
        rep.check(images<=16,"shaders.properties declares "+std::to_string(images)+" custom images (Iris limit 16)");
        rep.metric("customImages",double(images));
    }
    auto lavaE=[&](const std::array<float,3>& c){return double(c[0])/R;};

    // ===================================================== 1. capture / publish contract, bit exact
    {
        rig.cam={5.5,73.62,1.5};
        Scene s;
        for(int x=-4;x<=12;x++) for(int z=-6;z<=12;z++) s.blocks.push_back(LL::stone(x,70,z));
        // Tilted three-wide stream crossing a 4-cube group boundary (grid x 35|36).
        const double H[5]={0.8889,0.7778,0.5556,0.3334,0.1111};
        for(int x=3;x<=6;x++) for(int z=4;z<=6;z++) s.lava.push_back({x,71,z,{H[x-3],H[x-2],H[x-3],H[x-2]}});
        // Flat 2x3 sheet with a hole, an L, a floating cell (all six faces) and a two-high column.
        for(int x=-3;x<=-1;x++) for(int z=-5;z<=-4;z++) if(!(x==-2&&z==-5)) s.lava.push_back({x,71,z,{0.8889,0.8889,0.8889,0.8889}});
        s.lava.push_back({9,73,-3,{0.8889,0.8889,0.8889,0.8889}});
        s.lava.push_back({10,71,9,{0.8889,0.8889,0.8889,0.8889}});s.lava.push_back({10,72,9,{0.8889,0.8889,0.8889,0.8889}});
        // Regular lamps and their layout share the scene.
        s.blocks.push_back(LL::torch(1,71,1,14));s.blocks.push_back(LL::soulTorch(8,71,8,10));s.blocks.push_back(LL::blk(0,71,6,10114,15));
        rig.build(s);
        const auto raw=w.readUint(w.cell,w.pCell.w,w.pCell.h),idx=w.readUint(w.index,w.pIndex.w,w.pIndex.h);
        const auto field=w.readFloat(w.field,w.pField.w,w.pField.h,1);const auto list=w.readFloat(w.list,w.pList.w,w.pList.h,4);
        const Contract c=lavaContract(s,rig.cam);
        const int ox=int(std::floor(rig.cam[0]/8))*8-32,oy=int(std::floor(rig.cam[1]/8))*8-32,oz=int(std::floor(rig.cam[2]/8))*8-32;
        // Lamp words/index from the existing independent contract.
        std::map<int,unsigned> lampWords;std::vector<unsigned> wantIdx(idx.size(),0);
        for(const auto& b:s.blocks) {
            const int gx=b.x-ox,gy=b.y-oy,gz=b.z-oz;const unsigned wd=LL::expectedWord(b);
            if(wd) {int a=lin(gx,gy,gz,64);lampWords[a]=std::max(lampWords[a],wd);}
            if(LL::emits(b)) {int tile=gx/8+8*(gz/8+8*(gy/8)),bit=gx%8+8*(gz%8+8*(gy%8));wantIdx[17*tile+bit/32]|=1u<<unsigned(bit%32);wantIdx[17*tile+16]|=1u<<unsigned(bit/32);}
        }
        LL::expectedSkyColumns(wantIdx,s.blocks,rig.cam);
        for(auto& [cl,bits]:c.groupBits) wantIdx[size_t(68*128+cl)]|=bits;
        if(w.pIndex.h>=73 && !c.groupBits.empty()) wantIdx.at(72*128)=1u;
        bool tracksChanges=fs::exists(root/"lib/lava_reuse.glsl");
        if(tracksChanges) wantIdx.at(72*128+1)=1; // first floor and lava publication
        size_t badRaw=0,badCorner=0,badIdx=0,badField=0;
        for(size_t a=0;a<LL::World::kCells;a++) {
            unsigned want=lampWords.count(int(a))?lampWords.at(int(a)):0u;
            if(c.words.count(int(a))) {
                Rig::require(want==0||want==1,"fixture overlaps lava with a non-stone block");
                want=c.words.at(int(a));
            }
            badRaw+=raw[a]!=want;
            for(int k=0;k<4;k++) {
                const unsigned wk=c.corners.count(int(a))?c.corners.at(int(a))[k]:0u;
                badCorner+=raw[a+size_t(1+k)*LL::World::kCells]!=wk;
            }
            if(c.words.count(int(a))) badField+=field[a+LL::World::kCells]!=float(packed(c.corners.at(int(a))));
        }
        for(size_t i=0;i<idx.size();i++) badIdx+=idx[i]!=wantIdx[i];
        size_t badMirror=0;for(size_t a=0;a<LL::World::kCells;a++) badMirror+=field[a]!=float(raw[a]);
        rep.check(badMirror==0,"published cell field mirrors every raw word (lava face bits, lamps, stone) in the mixed scene (bad="+std::to_string(badMirror)+")");
        rep.check(badRaw==0&&badCorner==0&&badIdx==0,"capture contract: "+std::to_string(c.words.size())+" lava cells from "+std::to_string(fluidFaces(s).size())
                  +" drawn fluid quads (incl. back faces): raw words/4 corner planes/group bits + lamp words/index bit-exact (bad raw="+std::to_string(badRaw)
                  +" corner="+std::to_string(badCorner)+" index="+std::to_string(badIdx)+")");
        rep.check(badField==0,"published height field equals the packed corner planes for every lava cell (bad="+std::to_string(badField)+")");
        // Plane records of every active group, and neighbour lists of all 512 clusters.
        size_t badPlanes=0,groups=0,rects=0;std::set<int> active;
        for(auto& [cl,bits]:c.groupBits) for(int k=0;k<8;k++) if(bits&(1u<<k)) {
            const int cx=cl%8,cz=(cl/8)%8,cy=cl/64;const int gx=cx*2+(k&1),gz=cz*2+((k>>1)&1),gy=cy*2+(k>>2);
            const int id=lin(gx,gy,gz,16);active.insert(id);++groups;
            unsigned planes=0;
            for(int face=0;face<6;face++) for(int layer=0;layer<4;layer++) {
                unsigned mask=0;int lo[2]={4,4},hi[2]={-1,-1},flat=-1;
                for(int j=0;j<16;j++) {
                    auto a3=axes(face,layer,j%4,j/4);
                    const int a=lin(gx*4+a3[0],gy*4+a3[1],gz*4+a3[2],64);
                    if(!c.words.count(a)||!(c.words.at(a)&(1u<<unsigned(6+face)))) continue;
                    mask|=1u<<j;lo[0]=std::min(lo[0],j%4);lo[1]=std::min(lo[1],j/4);hi[0]=std::max(hi[0],j%4);hi[1]=std::max(hi[1],j/4);
                    int code=0;
                    if(face==0) {const auto& k4=c.corners.at(a);code=int(k4[0]);if(!(k4[0]&&k4[1]==k4[0]&&k4[2]==k4[0]&&k4[3]==k4[0])) code=-2;}
                    if(face>=2) code=-2;
                    flat=flat==-1?code:(flat!=code?-2:flat);
                }
                if(!mask) continue;
                planes|=1u<<unsigned(face*4+layer);
                const int sx=hi[0]-lo[0]+1,sy=hi[1]-lo[1]+1;const bool rect=__builtin_popcount(mask)==sx*sy&&flat>=0;rects+=rect;
                const int recIndex=id*25+face*4+layer+1;const float* r=&list[(size_t(512+recIndex/16)*w.pList.w+recIndex%16)*4];
                const float want[4]={float(mask),float(lo[0]+4*lo[1]+16*(sx-1)+64*(sy-1)),float(flat),rect?1.f:0.f};
                for(int q=0;q<4;q++) badPlanes+=r[q]!=want[q];
            }
            const int head=id*25;badPlanes+=list[(size_t(512+head/16)*w.pList.w+head%16)*4]!=float(planes);
        }
        size_t badLists=0,entries=0;
        for(int row=0;row<512;row++) {
            const int cx=row%8,cz=(row/8)%8,cy=row/64;std::multiset<int> want,got;
            for(int id:active) {
                const int gx=id%16,gz=(id/16)%16,gy=id/256;double g2=0;
                const int g[3]={gx,gy,gz},cc[3]={cx,cy,cz};
                for(int i=0;i<3;i++) {double lo=g[i]*4.0,hi=lo+4,clo=cc[i]*8.0,chi=clo+8;double d=std::max({0.0,lo-chi,clo-hi});g2+=d*d;}
                if(g2<w.range*w.range) want.insert(id);
            }
            const int n=int(field[size_t(1024+2*row)*512]);
            for(int k=1;k<=n&&k<1024;k++) got.insert(int(field[size_t(1024+2*row+k/512)*512+k%512]));
            badLists+=want!=got;entries+=got.size();
        }
        rep.check(badPlanes==0,"plane records: "+std::to_string(groups)+" active 4-cube groups, every header/mask/bounds/flat-height/rect word equals the CPU contract ("
                  +std::to_string(rects)+" analytic rectangles, bad="+std::to_string(badPlanes)+")");
        rep.check(badLists==0,"neighbour lists: all 512 clusters list exactly the active groups whose 4-cube lies within lampRange of the 8-cube ("+std::to_string(entries)+" entries, bad clusters="+std::to_string(badLists)+")");
        rig.build(s,true);
        auto expectedAgain=idx;
        if(tracksChanges) expectedAgain.at(72*128+1)=0; // identical geometry in reverse submission order
        rep.check(w.readUint(w.cell,w.pCell.w,w.pCell.h)==raw&&w.readUint(w.index,w.pIndex.w,w.pIndex.h)==expectedAgain&&w.readFloat(w.list,w.pList.w,w.pList.h,4)==list,
                  "reversed fluid/block submission reproduces raw, index and list images bit for bit");
        rep.metric("contractLavaCells",double(c.words.size()));rep.metric("contractGroups",double(groups));
    }

    // ===================================================== 2. pedestal block: fully visible, closed-form reference
    {
        rig.cam={100.5,66.62,200.5};
        Scene s;s.blocks.push_back(LL::stone(100,64,203));s.lava.push_back({100,65,203,{8.0/9,8.0/9,8.0/9,8.0/9}});
        rig.build(s);
        std::vector<std::pair<D3,D3>> rx;
        const D3 centre={100.5,65.45,203.5};
        for(int i=0;i<16;i++) {
            const double ang=i*0.3926990817,dist=1.6+0.22*i,hgt=65.25+0.18*(i%7);
            const D3 p={centre[0]+dist*std::cos(ang),hgt,centre[2]+dist*std::sin(ang)};
            rx.push_back({p,unit(sub(centre,p))});
        }
        rx.push_back({{100.5,68.2,203.5},{0,-1,0}});rx.push_back({{101.9,67.0,202.1},unit(D3{-1,-1.3,1})});
        const auto gpu=rig.light(rx);
        const auto tris=contractEmitters(s),drawn=emitters(fluidFaces(s));
        const Occluders occ=occludersOf(s);
        double maxContract=0,maxDrawn=0,maxRef=0,colour=0;
        for(size_t i=0;i<rx.size();i++) {
            double ec=0;for(const Tri& t:tris) ec+=lambert(t,rx[i].first,rx[i].second);
            double ed=0;for(const Tri& t:drawn) ed+=lambert(t,rx[i].first,rx[i].second);
            const Irr q=areaIntegral(drawn,rx[i].first,rx[i].second,occ,96);
            maxRef=std::max(maxRef,std::abs(q.visible-ed)/ed);
            maxContract=std::max(maxContract,std::abs(lavaE(gpu[i])-ec)/ec);
            maxDrawn=std::max(maxDrawn,std::abs(lavaE(gpu[i])-ed)/ed);
            colour=std::max(colour,std::abs(double(gpu[i][1])/gpu[i][0]-rig.radiance[1]/rig.radiance[0]));
        }
        rep.check(maxRef<2e-3,"reference self-check: midpoint area integral with exact visibility equals Lambert closed form for the visible block (max rel "+fmt(maxRef)+")");
        rep.check(maxContract<5e-4,"pedestal source block (top + 4 sides): GPU irradiance equals the double-precision Lambert integral of the published surface at "
                  +std::to_string(rx.size())+" receivers (max rel "+fmt(maxContract)+")");
        rep.check(maxDrawn<0.015,"pedestal: GPU vs the drawn client surface (unquantized heights, 1 mm insets) max rel "+fmt(maxDrawn)+" (<1.5%)");
        rep.check(colour<1e-5,"lava light keeps the radiance chromaticity G/R="+fmt(rig.radiance[1]/rig.radiance[0])+" (max dev "+fmt(colour)+")");
        rep.metric("pedestalMaxRelVsContract",maxContract);rep.metric("pedestalMaxRelVsDrawn",maxDrawn);
    }

    // ===================================================== 3. room: one / 3x3, pillar blocked / open, reference cross-check
    struct RoomResult { std::vector<double> gpu,ref,clear; };
    std::map<std::string,RoomResult> roomRes;
    rig.cam={205.5,174.62,362.5};
    std::vector<std::pair<D3,D3>> wall;   // receivers; order is recorded in the JSON as roomReceivers
    const double refPts[6][2]={{202.5,174.0},{201.53,175.5},{203.19,176.05},{200.5,174.2},{204.0,173.6},{203.53,177.4}};
    for(auto& p:refPts) wall.push_back({{p[0],p[1],366.0},{0,0,-1}});
    for(int x=199;x<=207;x++) for(int y=0;y<6;y++) wall.push_back({{x+0.5,173.5+y,366.0},{0,0,-1}});
    for(int x=201;x<=203;x++) for(int z=359;z<=362;z++) wall.push_back({{x+0.5,180.0,z+0.5},{0,-1,0}});
    {std::ostringstream o;o<<"[";for(size_t i=0;i<wall.size();i++) o<<(i?",":"")<<"["<<wall[i].first[0]<<","<<wall[i].first[1]<<","<<wall[i].first[2]<<","<<wall[i].second[0]<<","<<wall[i].second[1]<<","<<wall[i].second[2]<<"]";o<<"]";rep.metric("roomReceivers",o.str());}
    {
        // Reference cross-check against the earlier polygon-clipping result (pool height (214-1)/240).
        std::ifstream f(fs::path("reports/2026-11-21-lava-light/area-shader/pillar-results.json"));
        if(f) {
            std::string text((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
            std::regex re("\"poolWidth\":\\s*(\\d),\\s*\"wall\":\\s*\\[\\s*([0-9.]+),\\s*([0-9.]+)\\s*\\],\\s*\"box\":\\s*\"(pillar|past-pool)\",\\s*\"direct\":\\s*([0-9.e-]+),\\s*\"open\":\\s*([0-9.e-]+)");
            double worst=0;int n=0;
            for(auto it=std::sregex_iterator(text.begin(),text.end(),re);it!=std::sregex_iterator();++it) {
                const auto& m=*it;const int pool=std::stoi(m[1]);const bool pil=m[4]=="pillar";
                Scene s=room(pool,pil,false,true,213.0/240.0+kEps);   // drawn height = code height
                const D3 r={std::stod(m[2]),std::stod(m[3]),366.0};
                const Irr q=areaIntegral(emitters(fluidFaces(s)),r,{0,0,-1},occludersOf(s),128);
                worst=std::max(worst,std::abs(q.visible-std::stod(m[5]))/std::stod(m[6]));++n;
            }
            rep.check(n==24&&worst<0.004,"reference cross-check: this area integral reproduces all "+std::to_string(n)+" earlier polygon-clipping values (pillar/open, 1 and 3x3) to "+fmt(worst)+" of open");
            rep.metric("referenceCrossCheckWorst",worst);
        } else std::cout<<"INFO pillar-results.json not found from cwd; reference cross-check skipped\n";
    }
    for(int pool:{1,9}) for(bool pillar:{false,true}) {
        Scene s=room(pool,pillar,false);
        rig.build(s);
        const auto gpu=rig.light(wall);
        const auto tris=emitters(fluidFaces(s));const Occluders occ=occludersOf(s);
        RoomResult rr;
        for(size_t i=0;i<wall.size();i++) {
            const Irr q=areaIntegral(tris,wall[i].first,wall[i].second,occ,64);
            rr.gpu.push_back(lavaE(gpu[i]));rr.ref.push_back(q.visible);rr.clear.push_back(q.clear);
        }
        const std::string key=std::string(pool==1?"one":"nine")+(pillar?"-pillar":"-open");
        double maxErr=0,sumErr=0,blockedMax=0;int blocked=0;
        std::vector<std::pair<double,size_t>> worst;
        for(size_t i=0;i<wall.size();i++) {
            const double e=std::abs(rr.gpu[i]-rr.ref[i])/rr.clear[i];maxErr=std::max(maxErr,e);sumErr+=e;worst.push_back({e,i});
            if(rr.ref[i]==0) {++blocked;blockedMax=std::max(blockedMax,rr.gpu[i]/rr.clear[i]);}
        }
        std::sort(worst.rbegin(),worst.rend());
        for(size_t k=0;k<std::min<size_t>(6,worst.size());k++) {
            const size_t i=worst[k].second;const D3 p=wall[i].first;
            std::cout<<"INFO "<<(pool==1?"one":"nine")<<(pillar?"-pillar":"-open")<<" receiver ("<<p[0]<<","<<p[1]<<","<<p[2]<<") n=("<<wall[i].second[0]<<","<<wall[i].second[1]<<","<<wall[i].second[2]
                     <<") GPU "<<rr.gpu[i]<<" reference "<<rr.ref[i]<<" unoccluded "<<rr.clear[i]<<" err/unocc "<<worst[k].first<<"\n";
        }
        rep.check(maxErr<0.15&&sumErr/wall.size()<0.04,key+": GPU vs independent area integral at "+std::to_string(wall.size())+" wall/ceiling receivers, |err|/E_unoccluded max "+fmt(maxErr)+" mean "+fmt(sumErr/wall.size())+" (gates 0.15 / 0.04)");
        if(blocked) rep.check(blockedMax<0.02,key+": "+std::to_string(blocked)+" receivers with zero reference direct light stay dark on the GPU (max "+fmt(blockedMax)+" of unoccluded)");
        rep.metric(key+"MaxErr",maxErr);rep.metric(key+"MeanErr",sumErr/wall.size());
        auto arr=[](const std::vector<double>& v){std::ostringstream o;o<<std::setprecision(9)<<"[";for(size_t i=0;i<v.size();i++) o<<(i?",":"")<<v[i];o<<"]";return o.str();};
        rep.metric(key+"Gpu",arr(rr.gpu));rep.metric(key+"Reference",arr(rr.ref));rep.metric(key+"Unoccluded",arr(rr.clear));
        roomRes[key]=rr;
    }
    {
        // README reference: wall edge (203.19, 176.05) keeps 24% (one) / 44% (3x3) of the open direct light; centre goes dark.
        for(int pool:{1,9}) {
            const auto& o=roomRes[pool==1?"one-open":"nine-open"];const auto& p=roomRes[pool==1?"one-pillar":"nine-pillar"];
            const double gpuRatio=p.gpu[2]/o.gpu[2],refRatio=p.ref[2]/o.ref[2];
            rep.check(std::abs(gpuRatio-refRatio)<0.08,std::string(pool==1?"one":"3x3")+" pillar edge (203.19,176.05): GPU keeps "+fmt(gpuRatio)+" of open, reference "+fmt(refRatio)+" (|diff|<0.08)");
            rep.check(p.gpu[0]<0.02*o.gpu[0],std::string(pool==1?"one":"3x3")+" pillar centre (202.5,174): GPU "+fmt(p.gpu[0])+" vs open "+fmt(o.gpu[0])+" (reference "+fmt(p.ref[0])+")");
            rep.metric(std::string(pool==1?"one":"nine")+"EdgeRatioGpu",gpuRatio);rep.metric(std::string(pool==1?"one":"nine")+"EdgeRatioRef",refRatio);
            rep.metric(std::string(pool==1?"one":"nine")+"CentreOpenGpu",o.gpu[0]);rep.metric(std::string(pool==1?"one":"nine")+"CentrePillarGpu",p.gpu[0]);
        }
        const auto& one=roomRes["one-open"];const auto& nine=roomRes["nine-open"];
        double minGain=1e9;for(size_t i=0;i<wall.size();i++) minGain=std::min(minGain,nine.gpu[i]-one.gpu[i]);
        rep.check(minGain>=0,"3x3 pool never darker than the single cell at any receiver (min gain "+fmt(minGain)+")");
    }

    // ===================================================== 4. tilted flows of width 1..3
    {
        rig.cam={5.5,73.62,1.5};
        const double H[5]={0.8889,0.7778,0.5556,0.3334,0.1111};
        for(int width=1;width<=3;width++) {
            Scene s;
            for(int x=-2;x<=12;x++) for(int z=0;z<=11;z++) s.blocks.push_back(LL::stone(x,70,z));
            for(int x=3;x<=6;x++) for(int z=4;z<4+width;z++) s.lava.push_back({x,71,z,{H[x-3],H[x-2],H[x-3],H[x-2]}});
            rig.build(s);
            std::vector<std::pair<D3,D3>> rx;
            const double zc=4+width/2.0,z1=4+width;
            for(int x=3;x<=7;x++) for(double dz:{-1.0,0.0,1.0}) rx.push_back({{x+0.5,74.5,zc+dz},{0,-1,0}});
            for(int x=2;x<=7;x++) {rx.push_back({{x+0.5,71.0,2.5},{0,1,0}});rx.push_back({{x+0.5,71.0,z1+1.5},{0,1,0}});}
            for(double x:{1.5,8.5,9.5}) rx.push_back({{x,71.0,zc},{0,1,0}});
            for(int x=3;x<=6;x++) for(double y:{71.5,72.5}) rx.push_back({{x+0.5,y,z1+3.0},{0,0,-1}});
            const auto gpu=rig.light(rx);
            const auto tris=emitters(fluidFaces(s));const Occluders occ=occludersOf(s);
            double maxErr=0,sumErr=0,peak=0;
            for(size_t i=0;i<rx.size();i++) {
                const Irr q=areaIntegral(tris,rx[i].first,rx[i].second,occ,48);
                const double e=std::abs(lavaE(gpu[i])-q.visible)/std::max(q.clear,1e-9);
                maxErr=std::max(maxErr,e);sumErr+=e;peak=std::max(peak,q.visible);
            }
            const std::string key="flow-w"+std::to_string(width);
            rep.check(peak>0&&maxErr<0.15&&sumErr/rx.size()<0.04,key+": tilted four-cell flow (top 0.889->0.111, side/end faces, self-occlusion) GPU vs area integral at "
                      +std::to_string(rx.size())+" receivers, |err|/E_unoccluded max "+fmt(maxErr)+" mean "+fmt(sumErr/rx.size()));
            rep.metric(key+"MaxErr",maxErr);rep.metric(key+"MeanErr",sumErr/rx.size());
        }
    }

    // ===================================================== 5. torch in front of the pillar, removal / recapture, no ghost
    {
        rig.cam={205.5,174.62,362.5};
        std::vector<std::pair<D3,D3>> rx={{{202.5,174.0,366.0},{0,0,-1}},{{202.5,175.0,366.0},{0,0,-1}},{{203.19,176.05,366.0},{0,0,-1}},{{200.5,174.2,366.0},{0,0,-1}}};
        const Scene both=room(9,true,true),lavaOnly=room(9,true,false),torchOnly=room(9,true,true,false),empty=room(9,true,false,false);
        rig.build(torchOnly);const auto T=rig.light(rx);const auto listT=lampRows(w);
        rig.build(lavaOnly);const auto L=rig.light(rx);
        rig.build(both);const auto B=rig.light(rx);const auto listB=lampRows(w);
        double add=0;for(size_t i=0;i<rx.size();i++) for(int c=0;c<3;c++) add=std::max(add,std::abs(double(B[i][c])-T[i][c]-L[i][c])/std::max(1e-6,double(B[i][c])));
        std::vector<float> lamp0(listT.begin(),listT.begin()+size_t(512)*w.pList.w*4),lamp1(listB.begin(),listB.begin()+size_t(512)*w.pList.w*4);
        rep.check(lamp0==lamp1,"torch records in the 512 lamp cluster rows are bit-identical with and without the 3x3 pool (lava does not consume lamp slots)");
        rep.check(add<1e-5,"torch + occluded 3x3 pool = torch alone + pool alone at 4 wall receivers (max rel "+fmt(add)+")");
        rep.check(T[0][0]>0&&L[0][0]<0.02*T[0][0],"wall centre behind the pillar: torch "+fmt(T[0][0])+" dominates, occluded lava stays weak "+fmt(L[0][0]));
        rep.metric("torchCentre",double(T[0][0]));rep.metric("occludedLavaCentre",double(L[0][0]));
        // History: persistent field/list images pre-filled with junk, then recapture in sequence.
        const float junk[4]={777.f,777.f,777.f,777.f};
        glClearTexImage(w.field,0,GL_RED,GL_FLOAT,junk);glClearTexImage(w.list,0,GL_RGBA,GL_FLOAT,junk);
        rig.build(both);const auto B2=rig.light(rx);
        rig.build(lavaOnly);const auto L2=rig.light(rx);
        rig.build(both);const auto B3=rig.light(rx);
        rig.build(torchOnly);const auto T2=rig.light(rx);
        rig.build(empty);const auto E2=rig.light(rx);
        const auto fieldE=w.readFloat(w.field,w.pField.w,w.pField.h,1);
        size_t counts=0;for(int row=0;row<512;row++) counts+=fieldE[size_t(1024+2*row)*512]!=0.f;
        double dark=0;for(auto& v:E2) dark=std::max(dark,double(v[0]+v[1]+v[2]));
        rep.check(B2==B&&L2==L&&B3==B&&T2==T,"junk-filled field/list + remove torch / re-add / remove lava sequence reproduces fresh results bit for bit");
        rep.check(counts==0&&dark==0,"empty recapture: all 512 lava neighbour counts zero and receivers dark (no ghost) [nonzero counts "+std::to_string(counts)+", max "+fmt(dark)+"]");
    }

    // ===================================================== 6. a 12x12 sheet among 14 torches: lamp lists unchanged
    {
        rig.cam={5.5,73.62,1.5};
        Scene torches,sheet;
        for(int i=0;i<14;i++) torches.blocks.push_back(LL::torch(-4+(i%7)*2,71,-3+(i/7)*14,14));
        for(int x=-2;x<=9;x++) for(int z=-1;z<=10;z++) {sheet.blocks.push_back(LL::stone(x,70,z));sheet.lava.push_back({x,71,z,{0.8889,0.8889,0.8889,0.8889}});}
        Scene both=sheet;both.blocks.insert(both.blocks.end(),torches.blocks.begin(),torches.blocks.end());
        Scene floor;floor.blocks=sheet.blocks;floor.blocks.insert(floor.blocks.end(),torches.blocks.begin(),torches.blocks.end());
        rig.build(floor);const auto lt=lampRows(w);
        rig.build(both);w.publish(true);const double msLava=w.lastComputeMs;const auto lb=lampRows(w);
        rig.build(floor);w.publish(true);const double msNone=w.lastComputeMs;
        rep.check(lt==lb,"144-cell lava sheet + 14 torches: all 512 lamp cluster rows bit-identical to the torches-only scene");
        std::cout<<"INFO GPU-harness shadowcomp1 time: "<<msNone<<" ms without lava, "<<msLava<<" ms with the 144-cell sheet (not Minecraft frame time)\n";
        rep.metric("shadowcomp1MsNoLava",msNone);rep.metric("shadowcomp1MsSheet",msLava);
    }

    // ===================================================== 6b. GPU-harness cost of lampLighting per receiver (information only)
    {
        rig.cam={205.5,174.62,362.5};
        std::vector<LL::Query> q;
        for(int i=0;i<8192;i++) {
            const double u=(i%128)/128.0,v=(i/128)/64.0;
            q.push_back({{199.0+9.0*u,173.0+6.0*v,366.0},{0,0,-1},{0,1,0},0.075f,0.f,false});
        }
        auto timed=[&](const Scene& s) {
            rig.build(s);w.evaluate(q,rig.cam);   // warm-up
            double best=1e30;
            for(int k=0;k<3;k++) {
                GLuint query=0;glGenQueries(1,&query);glBeginQuery(GL_TIME_ELAPSED,query);
                w.evaluate(q,rig.cam);glEndQuery(GL_TIME_ELAPSED);
                GLuint64 ns=0;glGetQueryObjectui64v(query,GL_QUERY_RESULT,&ns);glDeleteQueries(1,&query);best=std::min(best,double(ns));
            }
            return best/8192.0;
        };
        const double torch=timed(room(9,true,true,false)),one=timed(room(1,false,false)),nine=timed(room(9,true,false)),nineTorch=timed(room(9,true,true));
        std::cout<<"INFO GPU-harness lampLighting cost per receiver (8192 wall receivers, best of 3, incl. 256 KB upload; NOT Minecraft frame time): torch only "
                 <<torch<<" ns, one lava "<<one<<" ns, 3x3+pillar "<<nine<<" ns, 3x3+pillar+torch "<<nineTorch<<" ns\n";
        rep.metric("nsPerReceiverTorchOnly",torch);rep.metric("nsPerReceiverOneLava",one);rep.metric("nsPerReceiverNinePillar",nine);rep.metric("nsPerReceiverNinePillarTorch",nineTorch);
    }

    // ===================================================== 7. lava-free path against the 1.8.0 baseline pack
    if(!baseline.empty()) {
        LL::World bw;bw.init(baseline);
        require(!bw.lavaLayout,"baseline must be the pre-lava layout");
        const D3 cam={205.5,174.62,362.5};
        Scene s=room(9,true,true,false);
        std::vector<LL::Query> q;
        for(const auto& r:wall) q.push_back({r.first,r.second,{0,1,0},0.075f,0.f,false});
        q.push_back({{202.5,174.0,366.0},{0,0,-1},{0,1,0},0.075f,0.6f,false});   // vanilla residual path too
        rig.cam=cam;rig.build(s);const auto a=w.evaluate(q,cam);
        bw.build(s.blocks,cam);const auto b=bw.evaluate(q,cam);
        double worst=0;for(size_t i=0;i<q.size();i++) for(int c=0;c<3;c++) worst=std::max(worst,std::abs(double(a[i][c])-b[i][c])/std::max(1e-6,double(std::abs(b[i][c]))));
        rep.check(worst<1e-5,"lava-free room with torch and pillar: candidate lampLighting equals the 1.8.0 baseline at "+std::to_string(q.size())+" receivers (max rel "+fmt(worst)+")");
        rep.metric("baselineLavaFreeMaxRel",worst);
    }

    faceBankProbe(root,rig,rep);
    receiverRecordProbe(root,rig.w,rep);
    std::cout<<"LAVA QA summary: passed="<<rep.passed<<" failed="<<rep.failed<<" on "<<w.renderer<<"\n";
    rep.metric("passed",double(rep.passed));rep.metric("failed",double(rep.failed));
    if(!jsonOut.empty()) {std::ofstream f(jsonOut);f<<"{\n"<<rep.json.str()<<"\n}\n";}
    return rep.failed;
}
}  // namespace aqualumenLava
