// Independent native-GPU oracle for door-panel transmission of placed / carried local lights.
//
// What is real (production code, compiled from the pack tree given on the command line):
//   - shadow_cutout / shadow_solid vertex+fragment programs (captureLocalCell -> door capture), driven with real vertices
//     of a six-face door model, real attributes (mc_Entity, at_midBlock, mc_midTexCoord), a synthetic RGBA terrain atlas
//     bound as gtexture with the pack's own mip/filter state, and every image declared in shaders.properties
//     (clear=true images are zeroed every frame, exactly like Iris);
//   - shadowcomp1.csh (publishes the light field), and lampTransmission() / lampLighting() from lib/local_lighting.glsl.
// What is independent (this file): the atlas, the door geometry/UV model, the expected cell word / mask image, and a
// double-precision CPU ray-vs-panel oracle derived from the *geometry and atlas alpha only* (no mask, no flip bits).
//
// Conventions asserted (stated by the task, restated here so a mismatch is a finding and not a silent assumption):
//   cell word  = shape(6 low X,7 high X,8 low Z,9 high Z) | (id-10500)<<6 | flipU<<12 | flipV<<13
//   flipU = atlas U decreases along +world horizontal (Z on an X panel, X on a Z panel); flipV = atlas V (row, 0 = top)
//   increases against +world height, i.e. ordinary Minecraft texture orientation has flipV=1.
//   doorMaskImage = r32ui, width 16 (V row), height 40 (material key); bit U of texel (row,key) set <=> sprite alpha>=0.1
//   at (U,V) in canonical atlas orientation. Panel slabs: low [0,3/16], high [13/16,1] of the cell along the panel axis.
// Zero-thickness contacts (a ray lying in a slab face, touching a slab edge/corner, or touching a texel only at a
// corner/edge shared with a transparent texel) are defined to transmit; a line shared by two opaque texels blocks.
// All timings are absent on purpose: this is a correctness oracle, not a benchmark.
#pragma once
#include <map>
#include <regex>
#include <random>
#include <cstdint>
namespace aqualumenDoor {
using D3=std::array<double,3>;

struct Report {
    struct Group { std::string name; int checks=0,fails=0; std::vector<std::string> shown; };
    std::vector<Group> groups;
    void begin(const std::string& n) { groups.push_back({n,0,0,{}}); }
    void check(bool ok,const std::string& what) {
        Group& g=groups.back();g.checks++;
        if(!ok) { g.fails++;if(g.shown.size()<5) g.shown.push_back(what); }
    }
    int fails() const { int n=0;for(auto& g:groups) n+=g.fails;return n; }
    int checks() const { int n=0;for(auto& g:groups) n+=g.checks;return n; }
    void print() const {
        for(auto& g:groups) {
            std::cout<<(g.fails?"FAIL ":"PASS ")<<g.name<<": "<<(g.checks-g.fails)<<"/"<<g.checks<<" checks\n";
            for(auto& s:g.shown) std::cout<<"     - "<<s<<'\n';
            if(g.fails>int(g.shown.size())) std::cout<<"     ... "<<(g.fails-int(g.shown.size()))<<" more\n";
        }
    }
};

inline std::string fmt(double v) { std::ostringstream s;s<<std::setprecision(7)<<v;return s.str(); }
inline std::string fmt3(const D3& v) { return "("+fmt(v[0])+","+fmt(v[1])+","+fmt(v[2])+")"; }
inline std::string readText(const fs::path& p) {
    std::ifstream f(p);if(!f) throw std::runtime_error("Cannot read "+p.string());
    std::ostringstream s;s<<f.rdbuf();return s.str();
}
inline uint64_t mix64(uint64_t x) {
    x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);
}

// ---------------------------------------------------------------------------------------------------------------------
// Synthetic atlas. 256x256 RGBA8. Key k's 16x16 sprite sits at a deliberately non-grid-aligned origin with a one-texel
// opaque gutter, so a wrong mid-texcoord, wrong extent, or one-texel offset samples a decoy.
struct Atlas {
    static constexpr int N=256;
    std::vector<uint8_t> rgba;
    static int ox(int k) { return 17*(k%14)+1; }
    static int oy(int k) { return 17*(k/14)+1; }
    static int alpha(int k,int x,int y) {   // x = U column, y = V row (0 = top of sprite)
        const int s=k/2,h=k%2;
        const uint64_t hv=mix64(uint64_t(k)*1000003ULL+uint64_t(y)*16+uint64_t(x));
        switch(s) {
            case 0: return 255;                                              // plain wood
            case 1: return x==3?0:255;                                       // vertical slit, column 3
            case 2: return h==0?((x>=2&&x<=5&&y>=3&&y<=7)?0:255):((x>=9&&x<=12&&y>=8&&y<=12)?0:255);   // window, differs lower/upper
            case 3: return h==0?(y==5?0:255):(y==10?0:255);                  // horizontal slot, differs lower/upper
            case 4: return (hv&1)?255:0;                                     // 50% hash
            case 5: { const int m=(x+y)%4;return m==0?25:(m==1?26:255); }    // alpha 25/255<0.1 transparent, 26/255>=0.1 opaque
            case 6: return (x>=2&&x<=13&&y>=2&&y<=13&&x!=7&&x!=8&&y!=7&&y!=8)?0:255;   // glazed door, mullion cross
            default: return int(hv%100)<12+(s*5)%30?255:0;                   // sparse hashes (12..41% opaque)
        }
    }
    static bool opaque(int k,int x,int y) { return x>=0&&x<16&&y>=0&&y<16 && double(alpha(k,x,y))/255.0>=0.1; }
    Atlas() {
        rgba.assign(size_t(N)*N*4,0);
        for(int y=0;y<N;y++) for(int x=0;x<N;x++) {
            const uint64_t c=mix64(uint64_t(y)*N+x+77);
            uint8_t* p=&rgba[(size_t(y)*N+x)*4];
            p[0]=uint8_t(c);p[1]=uint8_t(c>>8);p[2]=uint8_t(c>>16);p[3]=255;       // decoy: opaque
        }
        for(int k=0;k<40;k++) for(int y=0;y<16;y++) for(int x=0;x<16;x++) {
            uint8_t* p=&rgba[(size_t(oy(k)+y)*N+ox(k)+x)*4];
            const uint64_t c=mix64(uint64_t(k)*7919+y*16+x);
            p[0]=uint8_t(c);p[1]=uint8_t(c>>8);p[2]=uint8_t(c>>16);p[3]=uint8_t(alpha(k,x,y));
        }
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// Scene model.
struct Door { int c[3]; int shape,key; bool uMirror,vDown; int nsign=1; };   // c = grid cell
struct Lamp { int c[3]; int id=10100,level=14; };                            // torch-like emitter (cutout pass)
struct Cube { int c[3]; };                                                   // full opaque cube (solid pass, id 10001)
struct Scene { std::vector<Door> doors; std::vector<Lamp> lamps; std::vector<Cube> cubes; };
struct Ray { D3 a,b;bool carried=false;std::string label; };

inline int axisOf(int shape) { return shape<8?0:2; }
inline D3 localPoint(const Door& d,double a,double l,double y) {
    D3 p={double(d.c[0]),double(d.c[1]),double(d.c[2])};
    const int ax=axisOf(d.shape),lat=2-ax;
    p[ax]+=a;p[lat]+=l;p[1]+=y;return p;
}
inline double slabLo(int shape) { return (shape&1)?13.0/16.0:0.0; }
inline double slabHi(int shape) { return (shape&1)?1.0:3.0/16.0; }
inline double slabMid(int shape) { return 0.5*(slabLo(shape)+slabHi(shape)); }
inline double uFrac(const Door& d,double l) { return d.uMirror?1.0-l:l; }
inline double vFrac(const Door& d,double y) { return d.vDown?1.0-y:y; }
inline unsigned expectedCellWord(const Door& d) { return unsigned(d.shape)|(unsigned(d.key)<<6)|(d.uMirror?4096u:0u)|(d.vDown?8192u:0u); }
inline int cellLinear(const int c[3]) { return c[0]+64*(c[2]+64*c[1]); }

// World-space centre of the sprite texel (col,row) of a panel: used to aim rays by *design*, not through the oracle.
inline double lateralOfCol(const Door& d,double col) { const double f=col/16.0;return d.uMirror?1.0-f:f; }
inline double heightOfRow(const Door& d,double row) { const double f=row/16.0;return d.vDown?1.0-f:f; }

// Opaque-texel probe on the panel: pixel space (pu,pv) is sprite space (texel units, V row down).
// Double-precision exact-ish oracle: returns true when the open segment, clipped to the open slab, passes through the
// interior of the union of opaque texels. Measure-zero contact never blocks.
inline bool oracleBlocks(const Door& d,const D3& a,const D3& b,bool carried) {
    if(!carried) {   // production: the placed-light goal cell is never walked
        bool goal=true;for(int i=0;i<3;i++) goal=goal&&int(std::floor(b[i]))==d.c[i];
        if(goal) return false;
    }
    const int ax=axisOf(d.shape),lat=2-ax;
    D3 o={a[0]-d.c[0],a[1]-d.c[1],a[2]-d.c[2]},dir={b[0]-a[0],b[1]-a[1],b[2]-a[2]};
    D3 lo={0,0,0},hi={1,1,1};lo[ax]=slabLo(d.shape);hi[ax]=slabHi(d.shape);
    double s0=0,s1=1;
    for(int i=0;i<3;i++) {
        if(std::abs(dir[i])<1e-15) { if(!(o[i]>lo[i]&&o[i]<hi[i])) return false; continue; }
        double t0=(lo[i]-o[i])/dir[i],t1=(hi[i]-o[i])/dir[i];if(t0>t1) std::swap(t0,t1);
        s0=std::max(s0,t0);s1=std::min(s1,t1);
    }
    if(s1-s0<=1e-9) return false;
    auto pu=[&](double s){ return 16.0*uFrac(d,o[lat]+s*dir[lat]); };
    auto pv=[&](double s){ return 16.0*vFrac(d,o[1]+s*dir[1]); };
    std::vector<double> cuts={s0,s1};
    for(int which=0;which<2;which++) {
        const double p0=which?pv(0):pu(0),p1=which?pv(1):pu(1),rate=p1-p0;
        if(std::abs(rate)<1e-12) continue;
        const double sa=(std::min(pu(s0),pu(s1))),sb=std::max(pu(s0),pu(s1)),va=std::min(pv(s0),pv(s1)),vb=std::max(pv(s0),pv(s1));
        const double lowv=which?va:sa,highv=which?vb:sb;
        for(int k=int(std::floor(lowv))-1;k<=int(std::ceil(highv))+1;k++) {
            const double s=(double(k)-p0)/rate;
            if(s>s0&&s<s1) cuts.push_back(s);
        }
    }
    std::sort(cuts.begin(),cuts.end());
    for(size_t i=0;i+1<cuts.size();i++) {
        if(cuts[i+1]-cuts[i]<=1e-12) continue;
        const double m=0.5*(cuts[i]+cuts[i+1]),u=pu(m),v=pv(m);
        std::vector<int> us,vs;
        const double ru=std::round(u),rv=std::round(v);
        if(std::abs(u-ru)<1e-9) { us={int(ru)-1,int(ru)}; } else us={int(std::floor(u))};
        if(std::abs(v-rv)<1e-9) { vs={int(rv)-1,int(rv)}; } else vs={int(std::floor(v))};
        bool all=true;
        for(int uu:us) for(int vv:vs) all=all&&Atlas::opaque(d.key,uu,vv);
        if(all) return true;
    }
    return false;
}
// Expected transmission of a segment through every door of the scene (0 or 1).
struct Oracle {
    const Scene& scene;std::map<int,std::vector<int>> byCell;
    explicit Oracle(const Scene& s):scene(s) { for(size_t i=0;i<s.doors.size();i++) byCell[cellLinear(s.doors[i].c)].push_back(int(i)); }
    double transmission(const Ray& r) const {
        int lo[3],hi[3];
        for(int i=0;i<3;i++) { lo[i]=int(std::floor(std::min(r.a[i],r.b[i])));hi[i]=int(std::floor(std::max(r.a[i],r.b[i]))); }
        for(int y=lo[1];y<=hi[1];y++) for(int z=lo[2];z<=hi[2];z++) for(int x=lo[0];x<=hi[0];x++) {
            if(x<0||y<0||z<0||x>=64||y>=64||z>=64) continue;
            const int c[3]={x,y,z};
            auto it=byCell.find(cellLinear(c));if(it==byCell.end()) continue;
            for(int i:it->second) if(oracleBlocks(scene.doors[size_t(i)],r.a,r.b,r.carried)) return 0.0;
        }
        for(const Cube& cube:scene.cubes) {   // full cubes block placed/carried rays crossing them (solid shape 1)
            D3 o={r.a[0]-cube.c[0],r.a[1]-cube.c[1],r.a[2]-cube.c[2]},dir={r.b[0]-r.a[0],r.b[1]-r.a[1],r.b[2]-r.a[2]};
            bool goal=true;for(int i=0;i<3;i++) goal=goal&&int(std::floor(r.b[i]))==cube.c[i];
            if(goal&&!r.carried) continue;
            double s0=0,s1=1;bool miss=false;
            for(int i=0;i<3;i++) {
                if(std::abs(dir[i])<1e-15) { if(!(o[i]>0&&o[i]<1)) miss=true;continue; }
                double t0=(0-o[i])/dir[i],t1=(1-o[i])/dir[i];if(t0>t1) std::swap(t0,t1);s0=std::max(s0,t0);s1=std::min(s1,t1);
            }
            if(!miss&&s1-s0>1e-9) return 0.0;
        }
        return 1.0;
    }
};

// A float32 GPU cannot resolve a ray that passes within ~1e-5 m of a texel corner/edge or slab edge. A ray is "stable"
// when the oracle gives the same answer for 16 deterministic perturbations of +-3e-5 m of both endpoints.
inline bool oracleStable(const Oracle& oracle,const Ray& r,double expected) {
    uint64_t state=0x1234567ULL;
    auto jitter=[&]{ state=mix64(state);return (double(state>>11)/9007199254740992.0*2.0-1.0)*3e-5; };
    for(int t=0;t<16;t++) {
        Ray q=r;for(int k=0;k<3;k++) { q.a[k]+=jitter();q.b[k]+=jitter(); }
        if(oracle.transmission(q)!=expected) return false;
    }
    return true;
}

// ---------------------------------------------------------------------------------------------------------------------
// GPU rig.
struct ImageDecl { std::string name,texName;GLenum internal=0,pixelFormat=0,pixelType=0;int w=0,h=0;bool clear=false;GLuint tex=0; };
inline GLenum internalFormatOf(const std::string& s) {
    if(s=="r32ui") return GL_R32UI;
    if(s=="r32f") return GL_R32F;
    if(s=="rg32f") return GL_RG32F;
    if(s=="rgba32f") return GL_RGBA32F;
    if(s=="rgba16f") return GL_RGBA16F;
    if(s=="rgba32ui") return GL_RGBA32UI;
    throw std::runtime_error("door probe: unsupported image format "+s);
}
inline GLenum pixelFormatOf(const std::string& s) {
    if(s=="red_integer") return GL_RED_INTEGER;
    if(s=="rgba_integer") return GL_RGBA_INTEGER;
    if(s=="red") return GL_RED;
    if(s=="rg") return GL_RG;
    if(s=="rgba") return GL_RGBA;
    throw std::runtime_error("door probe: unsupported pixel format "+s);
}
struct Rig {
    fs::path root;std::string renderer;
    std::map<std::string,ImageDecl> images;
    GLuint atlasTex=0,cutout=0,solid=0,comp=0,evalTrans=0,evalLight=0,dataTex=0,outTex=0,fbo=0;
    int groups[3]={8,8,8};
    D3 cam={3.25,1.5,6.75};
    std::vector<std::string> unboundSamplers;
    std::vector<std::string> unbound;   // image uniforms a program declares that shaders.properties does not
    Atlas atlas;

    D3 gridOffset() const { D3 o;for(int i=0;i<3;i++) { double m=std::fmod(cam[i],8.0);if(m<0) m+=8.0;o[i]=m+32.0; }return o; }
    bool declared(const std::string& n) const { return images.count(n)>0; }
    static void checkGL(const char* where) {
        GLenum e=glGetError();if(e!=GL_NO_ERROR) throw std::runtime_error(std::string("GL error 0x")+[&]{std::ostringstream s;s<<std::hex<<e;return s.str();}()+" in "+where);
    }
    void init(const fs::path& r) {
        root=r;renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
        while(glGetError()!=GL_NO_ERROR) {}
        const std::string props=readText(root/"shaders.properties");
        const std::regex re("(^|\\n)image\\.(\\w+)=(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+(true|false)\\s+(true|false)\\s+(\\d+)\\s+(\\d+)");
        for(auto it=std::sregex_iterator(props.begin(),props.end(),re);it!=std::sregex_iterator();++it) {
            const std::smatch& m=*it;ImageDecl d;d.name=m[2];d.texName=m[3];d.pixelFormat=pixelFormatOf(m[4]);d.internal=internalFormatOf(m[5]);
            d.pixelType=m[6]=="float"?GL_FLOAT:GL_UNSIGNED_INT;d.clear=m[7]=="true";d.w=std::stoi(m[9]);d.h=std::stoi(m[10]);
            glGenTextures(1,&d.tex);glBindTexture(GL_TEXTURE_2D,d.tex);glTexStorage2D(GL_TEXTURE_2D,1,d.internal,d.w,d.h);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glClearTexImage(d.tex,0,d.pixelFormat,d.pixelType,nullptr);
            images[d.name]=d;
        }
        // Atlas: Minecraft-like state (nearest, mip chain); the pack samples LOD 0.
        glGenTextures(1,&atlasTex);glBindTexture(GL_TEXTURE_2D,atlasTex);glTexStorage2D(GL_TEXTURE_2D,5,GL_RGBA8,Atlas::N,Atlas::N);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,Atlas::N,Atlas::N,GL_RGBA,GL_UNSIGNED_BYTE,atlas.rgba.data());glGenerateMipmap(GL_TEXTURE_2D);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        cutout=linkPackProgram(root,"shadow_cutout");solid=linkPackProgram(root,"shadow_solid");
        comp=compute(root/"shadowcomp1.csh",root);
        const std::string csh=readText(root/"shadowcomp1.csh");std::smatch m;
        if(std::regex_search(csh,m,std::regex("workGroups\\s*=\\s*ivec3\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)"))) for(int i=0;i<3;i++) groups[i]=std::stoi(m[1+i]);
        const std::string common="#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/local_lighting.glsl",root);
        const std::string vsh="#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
        const std::string data="uniform sampler2D probeData;out vec4 probeOut;\nvec4 q(int i,int k){return texelFetch(probeData,ivec2(i,k),0);}\n";
        evalTrans=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2);"
            "probeOut=vec4(lampTransmission(a.xyz,b.xyz,c.x>0.5),1.0);}","door-transmission-eval");
        evalLight=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2),d=q(i,3);"
            "probeOut=vec4(lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,d.y>0.5),1.0);}","door-lighting-eval");
        glGenTextures(1,&dataTex);glGenTextures(1,&outTex);glGenFramebuffers(1,&fbo);
        checkGL("rig init");
    }
    // Every image uniform of the program is bound by name to its shaders.properties texture on its own image unit.
    void bindImages(GLuint program) {
        GLint n=0;glGetProgramiv(program,GL_ACTIVE_UNIFORMS,&n);int unit=0;
        for(GLint i=0;i<n;i++) {
            char name[256];GLsizei len=0;GLint size=0;GLenum type=0;glGetActiveUniform(program,GLuint(i),sizeof(name),&len,&size,&type,name);
            if(!isImageType(type)) continue;
            std::string key=name;const auto br=key.find('[');if(br!=std::string::npos) key=key.substr(0,br);
            auto it=images.find(key);
            if(it==images.end()) { if(std::find(unbound.begin(),unbound.end(),key)==unbound.end()) unbound.push_back(key);continue; }
            glUniform1i(glGetUniformLocation(program,name),unit);
            glBindImageTexture(GLuint(unit),it->second.tex,0,GL_FALSE,0,GL_READ_WRITE,it->second.internal);unit++;
        }
    }
    // Every sampler uniform named like a declared image's Iris texture name (aqualumenLightList, aqualumenLightField,
    // aqualumenDoorMask, aqualumenEntity*, ...) is bound to that image's texture on its own texture unit; `probeData` is unit 0.
    void bindSamplers(GLuint program) {
        GLint n=0;glGetProgramiv(program,GL_ACTIVE_UNIFORMS,&n);int unit=1;
        for(GLint i=0;i<n;i++) {
            char name[256];GLsizei len=0;GLint size=0;GLenum type=0;glGetActiveUniform(program,GLuint(i),sizeof(name),&len,&size,&type,name);
            if(!isSamplerType(type)) continue;
            std::string key=name;const auto br=key.find('[');if(br!=std::string::npos) key=key.substr(0,br);
            const GLint loc=glGetUniformLocation(program,name);
            if(key=="probeData") { glUniform1i(loc,0);continue; }
            GLuint tex=0;for(auto& kv:images) if(kv.second.texName==key) tex=kv.second.tex;
            if(!tex) { if(std::find(unboundSamplers.begin(),unboundSamplers.end(),key)==unboundSamplers.end()) unboundSamplers.push_back(key);continue; }
            glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,tex);glUniform1i(loc,unit);unit++;
        }
        glActiveTexture(GL_TEXTURE0);
    }
    void clearFrame() {   // what Iris does to clear=true images each frame
        for(auto& kv:images) if(kv.second.clear) glClearTexImage(kv.second.tex,0,kv.second.pixelFormat,kv.second.pixelType,nullptr);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
    }
    struct V { double p[3];double uv[2]; };
    static void emitQuad(const int c[3],int id,int level,const V v[4],const double n[3],const double centre[2],const double gridOff[3],const double camera[3],const float* tint=nullptr) {
        glNormal3f(float(n[0]),float(n[1]),float(n[2]));
        for(int i=0;i<4;i++) {
            float rel[3],mid[3];
            for(int k=0;k<3;k++) { rel[k]=float(c[k]+v[i].p[k]-gridOff[k]);mid[k]=float((0.5-v[i].p[k])*64.0); }
            (void)camera;
            glVertexAttrib4f(10,float(id),0,0,0);glVertexAttrib4f(11,mid[0],mid[1],mid[2],float(level));
            glVertexAttrib2f(12,float(centre[0]),float(centre[1]));
            glTexCoord2f(float(v[i].uv[0]),float(v[i].uv[1]));glMultiTexCoord2f(GL_TEXTURE1,0,0);
            if(tint) glColor3fv(tint);else glColor4f(1,1,1,1);
            glVertex3fv(rel);
        }
    }
    static void emitBox(const int c[3],int id,int level,const double lo[3],const double hi[3],const double go[3],const double cm[3]) {
        for(int a=0;a<3;a++) for(int s=0;s<2;s++) {
            const int u=(a+1)%3,w=(a+2)%3;const int cu[4]={0,1,1,0},cw[4]={0,0,1,1};
            double n[3]={0,0,0};n[a]=s?1:-1;V q[4];
            for(int i=0;i<4;i++) { q[i].p[a]=s?hi[a]:lo[a];q[i].p[u]=cu[i]?hi[u]:lo[u];q[i].p[w]=cw[i]?hi[w]:lo[w];q[i].uv[0]=cu[i];q[i].uv[1]=cw[i]; }
            const double centre[2]={0,0};emitQuad(c,id,level,q,n,centre,go,cm);
        }
    }
    // The six faces of a vanilla-like door element, all carrying the door's block id and sprite UVs.
    void emitDoor(const Door& d,const double go[3]) {
        const int ax=axisOf(d.shape),lat=2-ax;const bool low=(d.shape&1)==0;
        const double inner=low?3.0/16.0:13.0/16.0,wall=low?0.0:1.0,s0=slabLo(d.shape),s1=slabHi(d.shape);
        const double ox=Atlas::ox(d.key),oy=Atlas::oy(d.key),N=Atlas::N;
        const double centre[2]={(ox+8)/N,(oy+8)/N};
        auto uvOf=[&](double uf,double vf,double* out){ out[0]=(ox+16.0*uf)/N;out[1]=(oy+16.0*vf)/N; };
        auto pos=[&](double a,double l,double y,double* p){ p[ax]=a;p[lat]=l;p[1]=y; };
        const int id=10500+d.key;
        const double sgn=double(d.nsign);
        // broad inset face (the face under test) and broad outer face at the cell wall
        for(int face=0;face<2;face++) {
            const double plane=face?wall:inner;V q[4];const int cl[4]={0,1,1,0},cy[4]={0,0,1,1};
            for(int i=0;i<4;i++) {
                pos(plane,cl[i],cy[i],q[i].p);
                const double uf=face?1.0-uFrac(d,cl[i]):uFrac(d,cl[i]);uvOf(uf,vFrac(d,cy[i]),q[i].uv);
            }
            double n[3]={0,0,0};n[ax]=(low?1.0:-1.0)*(face?-1.0:1.0)*sgn;emitQuad(d.c,id,0,q,n,centre,go,&cam[0]);
        }
        // lateral edge faces and top/bottom faces (thin strips; must never be mistaken for the broad face)
        for(int e=0;e<2;e++) {
            V q[4];const int ca[4]={0,1,1,0},cy[4]={0,0,1,1};
            for(int i=0;i<4;i++) { pos(ca[i]?s1:s0,e,cy[i],q[i].p);uvOf(3.0/16.0*ca[i],vFrac(d,cy[i]),q[i].uv); }
            double n[3]={0,0,0};n[lat]=e?1.0:-1.0;emitQuad(d.c,id,0,q,n,centre,go,&cam[0]);
        }
        for(int e=0;e<2;e++) {
            V q[4];const int ca[4]={0,1,1,0},cl[4]={0,0,1,1};
            for(int i=0;i<4;i++) { pos(ca[i]?s1:s0,cl[i],e,q[i].p);uvOf(uFrac(d,cl[i]),3.0/16.0*ca[i],q[i].uv); }
            double n[3]={0,0,0};n[1]=e?1.0:-1.0;emitQuad(d.c,id,0,q,n,centre,go,&cam[0]);
        }
    }
    void useShadowState(GLuint program) {
        glUseProgram(program);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelViewInverse"),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);
        const GLint g=glGetUniformLocation(program,"gtexture");if(g>=0) glUniform1i(g,0);
        bindImages(program);
    }
    void capture(const Scene& scene,bool reverse,bool doorsThroughSolid) {
        aqualumenLocalLights::resetTextureMatrices();
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,atlasTex);
        glEnable(GL_RASTERIZER_DISCARD);
        const D3 go=gridOffset();const double gv[3]={go[0],go[1],go[2]};
        for(int pass=0;pass<2;pass++) {   // 0 = cutout (doors, torches), 1 = solid (cubes)
            const GLuint program=pass==0?(doorsThroughSolid?solid:cutout):solid;
            useShadowState(program);
            glBegin(GL_QUADS);
            const size_t nd=scene.doors.size();
            if((pass==0&&!doorsThroughSolid)||(pass==1&&doorsThroughSolid)) for(size_t i=0;i<nd;i++) emitDoor(scene.doors[reverse?nd-1-i:i],gv);
            if(pass==0) for(const Lamp& l:scene.lamps) { const double lo[3]={0.4375,0,0.4375},hi[3]={0.5625,0.625,0.5625};emitBox(l.c,l.id,l.level,lo,hi,gv,&cam[0]); }
            if(pass==1) for(const Cube& c:scene.cubes) { const double lo[3]={0,0,0},hi[3]={1,1,1};emitBox(c.c,10001,0,lo,hi,gv,&cam[0]); }
            glEnd();
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        }
        glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        checkGL("shadow capture");
    }
    void publish() {
        glUseProgram(comp);
        glUniform3f(glGetUniformLocation(comp,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
        bindImages(comp);
        glDispatchCompute(GLuint(groups[0]),GLuint(groups[1]),GLuint(groups[2]));
        glMemoryBarrier(GL_ALL_BARRIER_BITS);glUseProgram(0);
        checkGL("shadowcomp1 dispatch");
    }
    void frame(const Scene& scene,bool reverse=false,bool doorsThroughSolid=false) { clearFrame();capture(scene,reverse,doorsThroughSolid);publish(); }
    std::vector<uint32_t> readUint(const std::string& name) {
        const ImageDecl& d=images.at(name);std::vector<uint32_t> v(size_t(d.w)*d.h);
        glGetTextureImage(d.tex,0,GL_RED_INTEGER,GL_UNSIGNED_INT,GLsizei(v.size()*4),v.data());return v;
    }
    std::vector<float> readFloat1(const std::string& name) {
        const ImageDecl& d=images.at(name);std::vector<float> v(size_t(d.w)*d.h);
        glGetTextureImage(d.tex,0,GL_RED,GL_FLOAT,GLsizei(v.size()*4),v.data());return v;
    }
    std::vector<float> evalRows(GLuint program,const std::vector<float>& data,int count,int rows) {
        glBindTexture(GL_TEXTURE_2D,dataTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,count,rows,0,GL_RGBA,GL_FLOAT,data.data());
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glBindTexture(GL_TEXTURE_2D,outTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,count,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,outTex,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("door probe framebuffer incomplete");
        glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glViewport(0,0,count,1);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,dataTex);
        glUseProgram(program);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
        bindSamplers(program);
        bindImages(program);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        std::vector<float> out(size_t(count)*4,0);glReadPixels(0,0,count,1,GL_RGBA,GL_FLOAT,out.data());
        glUseProgram(0);glActiveTexture(GL_TEXTURE0);glBindFramebuffer(GL_FRAMEBUFFER,0);
        checkGL("probe draw");
        for(float f:out) if(!std::isfinite(f)) throw std::runtime_error("nonfinite GPU output");
        return out;
    }
    // Real lampTransmission() on the currently published frame. Returns RGB per ray.
    std::vector<std::array<float,3>> transmission(const std::vector<Ray>& rays) {
        std::vector<std::array<float,3>> result;const D3 go=gridOffset();
        for(size_t first=0;first<rays.size();first+=8192) {
            const size_t n=std::min<size_t>(8192,rays.size()-first);std::vector<float> data(n*12,0.0f);
            for(size_t i=0;i<n;i++) {
                const Ray& r=rays[first+i];
                for(int k=0;k<3;k++) { data[(0*n+i)*4+k]=float(r.a[k]);data[(1*n+i)*4+k]=float(r.b[k]); }   // lampTransmission works in grid coordinates
                data[(2*n+i)*4]=r.carried?1.0f:0.0f;
            }
            (void)go;
            auto out=evalRows(evalTrans,data,int(n),3);
            for(size_t i=0;i<n;i++) result.push_back({out[i*4],out[i*4+1],out[i*4+2]});
        }
        return result;
    }
    struct Query { D3 p,n;float level=0; };   // p in grid coordinates
    std::vector<std::array<float,3>> lighting(const std::vector<Query>& qs) {
        const D3 go=gridOffset();const size_t n=qs.size();std::vector<float> data(n*16,0.0f);
        for(size_t i=0;i<n;i++) {
            for(int k=0;k<3;k++) { data[(0*n+i)*4+k]=float(qs[i].p[k]-go[k]);data[(1*n+i)*4+k]=float(qs[i].n[k]);data[(2*n+i)*4+k]=0.0f; }
            data[(2*n+i)*4+2]=1.0f;data[(2*n+i)*4+3]=0.5f;data[(3*n+i)*4]=qs[i].level;
        }
        auto out=evalRows(evalLight,data,int(n),4);
        std::vector<std::array<float,3>> r(n);for(size_t i=0;i<n;i++) r[i]={out[i*4],out[i*4+1],out[i*4+2]};return r;
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// Ray builders. d = door, (h,y) = panel-plane crossing point, dir in the panel frame (normal, lateral, height).
inline Ray crossing(const Door& d,double h,double y,double dn,double dl,double dy,double ta,double tb,bool carried,const std::string& label) {
    const D3 p=localPoint(d,slabMid(d.shape),h,y);D3 a,b;
    const double dv[3]={dn,dl,dy};
    for(int k=0;k<3;k++) { a[k]=p[k];b[k]=p[k]; }
    const int ax=axisOf(d.shape),lat=2-ax;const int map[3]={ax,lat,1};
    for(int j=0;j<3;j++) { a[map[j]]-=ta*dv[j];b[map[j]]+=tb*dv[j]; }
    return {a,b,carried,label};
}
inline Ray segmentLocal(const Door& d,double a0,double l0,double y0,double a1,double l1,double y1,bool carried,const std::string& label) {
    return {localPoint(d,a0,l0,y0),localPoint(d,a1,l1,y1),carried,label};
}
inline std::string doorTag(const Door& d) {
    return "shape"+std::to_string(d.shape)+" key"+std::to_string(d.key)+(d.uMirror?" mirU":"")+(d.vDown?" vDown":" vUp");
}

struct Case { Ray ray;int expect;bool policy=false; };   // expect: 1 transmits, 0 blocks (by design); policy: not derivable from the continuum oracle

// Runs a ray list on the published frame, compares with design expectations and the oracle.
inline void runCases(Report& rep,Rig& rig,const Scene& scene,const std::vector<Case>& cases,const std::string& what) {
    std::vector<Ray> rays;for(const Case& c:cases) rays.push_back(c.ray);
    const auto got=rig.transmission(rays);const Oracle oracle(scene);
    for(size_t i=0;i<cases.size();i++) {
        const double exp=oracle.transmission(rays[i]);
        const bool oracleOk=int(exp)==cases[i].expect;
        const bool gpuOk=got[i][0]==float(cases[i].expect)&&got[i][1]==float(cases[i].expect)&&got[i][2]==float(cases[i].expect);
        if(!cases[i].policy) rep.check(oracleOk,"ORACLE SELF-CHECK "+what+": "+rays[i].label+" design="+std::to_string(cases[i].expect)+" oracle="+fmt(exp));
        rep.check(gpuOk,what+": "+rays[i].label+" expected "+std::to_string(cases[i].expect)+" got "+fmt(got[i][0])+","+fmt(got[i][1])+","+fmt(got[i][2]));
    }
}
// Compares GPU against the oracle only (random sweeps).
inline void runAgainstOracle(Report& rep,Rig& rig,const Scene& scene,const std::vector<Ray>& rays,const std::string& what,int* mismatches=nullptr,int* blocked=nullptr,int* ambiguous=nullptr) {
    const auto got=rig.transmission(rays);const Oracle oracle(scene);int bad=0,zero=0,amb=0;
    for(size_t i=0;i<rays.size();i++) {
        const double exp=oracle.transmission(rays[i]);
        if(!oracleStable(oracle,rays[i],exp)) { amb++;continue; }   // float32-unresolvable geometry: reported, not judged
        if(exp==0.0) zero++;
        const bool ok=got[i][0]==float(exp)&&got[i][1]==float(exp)&&got[i][2]==float(exp);
        if(!ok) {
            bad++;
            if(std::getenv("DOOR_DEBUG")) for(const Door& d:scene.doors) if(oracleBlocks(d,rays[i].a,rays[i].b,rays[i].carried))
                std::cout<<"  [debug] oracle blocker: "<<doorTag(d)<<" cell ("<<d.c[0]<<","<<d.c[1]<<","<<d.c[2]<<")\n";
        }
        rep.check(ok,what+": "+rays[i].label+" a="+fmt3(rays[i].a)+" b="+fmt3(rays[i].b)+(rays[i].carried?" carried":" placed")+" expected "+fmt(exp)+" got "+fmt(got[i][0]));
    }
    if(mismatches) *mismatches=bad;
    if(blocked) *blocked=zero;
    if(ambiguous) *ambiguous=amb;
}
// Cell words, light field and mask image against the independent expectation.
inline void checkContract(Report& rep,Rig& rig,const Scene& scene,const std::string& what) {
    const auto cells=rig.readUint("lampCellImage");const auto field=rig.readFloat1("lampFieldImage");
    std::map<int,unsigned> expectCell;
    for(const Door& d:scene.doors) expectCell[cellLinear(d.c)]=expectedCellWord(d);
    for(const Cube& c:scene.cubes) expectCell[cellLinear(c.c)]=1u;
    for(const Lamp& l:scene.lamps) expectCell[cellLinear(l.c)]=(1u<<6)|(14u<<12);
    int wrongCell=0,wrongField=0;std::string first;
    for(size_t i=0;i<cells.size();i++) {
        auto it=expectCell.find(int(i));const unsigned want=it==expectCell.end()?0u:it->second;
        if(cells[i]!=want) { if(!wrongCell) first="cell "+std::to_string(i)+" word "+std::to_string(cells[i])+" expected "+std::to_string(want);wrongCell++; }
        if(i<field.size()&&field[i]!=float(want)) wrongField++;
    }
    rep.check(wrongCell==0,what+": lampCellImage: "+std::to_string(wrongCell)+" cells differ ("+first+")");
    rep.check(wrongField==0,what+": lampFieldImage: "+std::to_string(wrongField)+" texels differ from published cell words");
    int wrongMask=0;std::string firstMask;
    if(rig.declared("doorMaskImage")) {
        const auto mask=rig.readUint("doorMaskImage");
        rep.check(mask.size()==16*40 || mask.size()==16*104,what+": door mask contains its forty reserved sprite rows");
        std::set<int> keys;for(const Door& d:scene.doors) keys.insert(d.key);
        for(int key=0;key<40;key++) for(int row=0;row<16;row++) {
            uint32_t want=0;if(keys.count(key)) for(int u=0;u<16;u++) if(Atlas::opaque(key,u,row)) want|=1u<<u;
            const uint32_t have=size_t(key)*16+row<mask.size()?mask[size_t(key)*16+row]:0xffffffffu;
            if(have!=want) { if(!wrongMask) firstMask="key "+std::to_string(key)+" row "+std::to_string(row)+" bits 0x"+[&]{std::ostringstream s;s<<std::hex<<have<<" expected 0x"<<want;return s.str();}();wrongMask++; }
        }
        rep.check(wrongMask==0,what+": doorMaskImage: "+std::to_string(wrongMask)+" of 640 rows differ ("+firstMask+")");
    } else rep.check(false,what+": shaders.properties declares no doorMaskImage");
}

// ---------------------------------------------------------------------------------------------------------------------
inline Door door(int x,int y,int z,int shape,int key,bool uMirror=false,bool vDown=true) { return Door{{x,y,z},shape,key,uMirror,vDown,1}; }
// 640 doors, 5 cells apart (a ray never reaches the next door): i -> 10 x 8 x 8 lattice inside the 64^3 grid.
inline Door latticeDoor(int i,int shape,int key,bool uMirror,bool vDown) { return door(4+5*(i%10),4+5*((i/10)%8),4+5*(i/80),shape,key,uMirror,vDown); }

inline void groupDeclarations(Report& rep,const fs::path& root) {
    rep.begin("declarations: doorMaskImage, block ids, program set");
    const std::string props=readText(root/"shaders.properties");std::smatch m;
    const bool has=std::regex_search(props,m,std::regex("image\\.doorMaskImage=\\S+\\s+(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+(true|false)\\s+(true|false)\\s+(\\d+)\\s+(\\d+)"));
    rep.check(has,"image.doorMaskImage is not declared in shaders.properties");
    if(has) {
        rep.check(m[2]=="r32ui"&&m[3]=="unsigned_int","doorMaskImage must be r32ui/unsigned_int, got "+m[2].str()+"/"+m[3].str());
        rep.check(m[6]=="16"&&(m[7]=="40"||m[7]=="104"),"unexpected door sprite atlas reservation, got "+m[6].str()+"x"+m[7].str());
        rep.check(m[4]=="true","doorMaskImage must be cleared every frame (clear=true)");
    }
    const std::string blocks=readText(root/"block.properties");
    std::vector<std::string> species;bool structure=true;std::string bad;
    for(int id=10500;id<10540;id++) {
        std::smatch bm;const std::regex re("(^|\\n)block\\."+std::to_string(id)+"=([^\\n]*)");
        if(!std::regex_search(blocks,bm,re)) { structure=false;bad="block."+std::to_string(id)+" missing";break; }
        const std::string line=bm[2];const bool upper=(id-10500)%2==1;
        std::smatch dm;if(!std::regex_search(line,dm,std::regex("minecraft:(\\w+)_door:half=(lower|upper)"))||(dm[2]=="upper")!=upper||line.find(' ')!=std::string::npos) {
            structure=false;bad="block."+std::to_string(id)+" is not a single door half: "+line;break; }
        if(!upper) species.push_back(dm[1]);
    }
    rep.check(structure,"block.properties door ids 10500..10539: "+bad);
    if(structure) {
        rep.check(std::is_sorted(species.begin(),species.end()),"door species are not in alphabetical order");
        rep.check(std::set<std::string>(species.begin(),species.end()).size()==20,"expected 20 distinct door species");
    }
}

inline void groupContract(Report& rep,Rig& rig) {
    rep.begin("contract: cell word, light field, mask image (6-face door model, 4 shapes x mirror x vFlip x 40 keys)");
    Scene s;int n=0;
    for(int key=0;key<40;key++) for(int shape=6;shape<10;shape++) for(int mode=0;mode<4;mode++) {
        const int i=n++;s.doors.push_back(latticeDoor(i,shape,key,mode&1,(mode&2)==0));
    }
    rig.frame(s);checkContract(rep,rig,s,"all keys/orientations (cutout)");
    s.doors.resize(8);   // a sparse frame must leave every other key's row zero
    rig.frame(s);checkContract(rep,rig,s,"sparse frame, no stale rows");
    rig.frame(s,true);checkContract(rep,rig,s,"reversed draw order");
    rig.frame(s,false,true);checkContract(rep,rig,s,"doors drawn through shadow_solid");
    Scene flipped=s;for(Door& d:flipped.doors) d.nsign=-1;
    rig.frame(flipped);checkContract(rep,rig,flipped,"inset-face normal sign reversed");
    Scene empty;rig.frame(empty);checkContract(rep,rig,empty,"empty frame");
}

inline void groupClosedOpen(Report& rep,Rig& rig) {
    rep.begin("closed / open / removed");
    const int cx=20,cy=20,cz=20;
    Door closed=door(cx,cy,cz,8,0),open=door(cx,cy,cz,6,0);
    { Scene s;s.doors={closed};rig.frame(s);checkContract(rep,rig,s,"closed");
      std::vector<Case> c;
      for(bool carried:{false,true}) {
          const std::string t=carried?" carried":" placed";
          c.push_back({crossing(closed,0.5,0.5,1,0,0,1.3,1.3,carried,"closed, ray normal to panel"+t),0});
          c.push_back({crossing(closed,0.25,0.9,1,0.3,-0.2,1.3,1.3,carried,"closed, oblique, upper part"+t),0});
          c.push_back({segmentLocal(closed,0.5,0.1,0.5,0.5,0.9,0.5,carried,"closed, ray along the free side (panel not crossed)"+t),1});
      }
      runCases(rep,rig,s,c,"closed"); }
    { Scene s;s.doors={open};rig.frame(s);checkContract(rep,rig,s,"open");
      std::vector<Case> c;
      for(bool carried:{false,true}) {
          const std::string t=carried?" carried":" placed";
          // former closed-door ray runs along Z at x=0.5: the opened panel (x in [0,3/16]) no longer intersects it
          c.push_back({segmentLocal(open,0.5,-1.3,0.5,0.5,2.3,0.5,carried,"open, ray along Z at x=0.5 (former closed-door line)"+t),1});
          c.push_back({crossing(open,0.5,0.5,1,0,0,1.3,1.3,carried,"open, ray along X through the swung panel"+t),0});
      }
      runCases(rep,rig,s,c,"open"); }
    { Scene s;rig.frame(s);checkContract(rep,rig,s,"removed");
      std::vector<Case> c;
      for(bool carried:{false,true}) c.push_back({crossing(closed,0.5,0.5,1,0,0,1.3,1.3,carried,std::string("removed door, same ray")+(carried?" carried":" placed")),1});
      runCases(rep,rig,s,c,"removed"); }
}

inline void groupShapesAndSlit(Report& rep,Rig& rig) {
    rep.begin("slit vs wood, low/high X/Z, mirror");
    Scene s;std::vector<Case> cases;int n=0;
    for(int shape=6;shape<10;shape++) for(int key:{0,2}) for(int mirror=0;mirror<2;mirror++) {
        const int i=n++;Door d=door(4+5*(i%7),4+5*(i/7),20,shape,key,mirror,true);s.doors.push_back(d);
        for(bool carried:{false,true}) for(int col:{1,2,3,4,5,10,12,14}) {
            const double h=lateralOfCol(d,col+0.5),y=heightOfRow(d,7.5);
            const bool slit=key==2&&col==3;
            cases.push_back({crossing(d,h,y,1,0,0,1.3,1.3,carried,doorTag(d)+" col"+std::to_string(col)+(carried?" carried":" placed")),slit?1:0});
        }
        // light that stays on the open side of the slab: the panel is 3/16 m thick, not a full cell
        const double inner=(shape&1)?13.0/16.0:3.0/16.0,dirn=(shape&1)?-1.0:1.0;
        cases.push_back({segmentLocal(d,inner+0.1*dirn,0.5,0.5,inner+0.7*dirn,0.5,0.5,true,doorTag(d)+" carried ray beside the slab, inside the cell"),1});
    }
    rig.frame(s);checkContract(rep,rig,s,"slit/wood layout");
    runCases(rep,rig,s,cases,"slit/wood");
}

inline void groupTopBottom(Report& rep,Rig& rig) {
    rep.begin("top vs bottom halves, V orientation");
    Scene s;std::vector<Case> cases;int n=0;
    for(int shape:{6,8}) for(int vdown=0;vdown<2;vdown++) for(int mirror=0;mirror<2;mirror++) for(int half=0;half<2;half++) {
        const int i=n++;Door d=door(4+5*(i%7),4+5*(i/7),30,shape,4+half,mirror,vdown);s.doors.push_back(d);
        // window texels (lower: col3,row5; upper: col10,row10). The other half is opaque at both.
        const bool lowerWindowAt=half==0,upperWindowAt=half==1;
        const struct { double col,row;bool open; } probes[2]={{3.5,5.5,lowerWindowAt},{10.5,10.5,upperWindowAt}};
        for(auto& p:probes) cases.push_back({crossing(d,lateralOfCol(d,p.col),heightOfRow(d,p.row),1,0,0,1.3,1.3,false,
            doorTag(d)+" probe col"+fmt(p.col)+" row"+fmt(p.row)),p.open?1:0});
    }
    rig.frame(s);checkContract(rep,rig,s,"top/bottom layout");
    runCases(rep,rig,s,cases,"top/bottom");
}

inline void groupObliqueParallel(Report& rep,Rig& rig) {
    rep.begin("oblique vs parallel rays");
    Scene s;std::vector<Case> cases;int n=0;
    for(int mirror=0;mirror<2;mirror++) for(int vdown=0;vdown<2;vdown++) for(int shape:{6,7,8,9}) {
        const int i=n++;Door slit=door(4+5*(i%7),4+5*(i/7),44,shape,2,mirror,vdown),slotLow=door(4+5*(i%7),4+5*(i/7)+30,44,shape,6,mirror,vdown),
            slotHigh=door(4+5*(i%7),4+5*(i/7)+30,50,shape,7,mirror,vdown);
        s.doors.push_back(slit);s.doors.push_back(slotLow);s.doors.push_back(slotHigh);
        const double hc=lateralOfCol(slit,3.5),y=heightOfRow(slit,6.5);
        const std::string t=doorTag(slit);
        for(bool carried:{false,true}) {
            const std::string c=carried?" carried":" placed";
            // slit column is 1/16 m wide, panel 3/16 m thick: a ray with |lateral/normal| <= 1/3 can stay inside it
            cases.push_back({crossing(slit,hc,y,1,0,0,1.3,1.3,carried,t+" normal incidence"+c),1});
            cases.push_back({crossing(slit,hc,y,1,0.2,0,1.3,1.3,carried,t+" oblique lateral 0.2 (fits slit)"+c),1});
            cases.push_back({crossing(slit,hc,y,1,0.2,0.35,1.3,1.3,carried,t+" oblique lateral+vertical (fits slit)"+c),1});
            cases.push_back({crossing(slit,hc,y,1,0.5,0,1.3,1.3,carried,t+" oblique lateral 0.5 (clips mullion)"+c),0});
            cases.push_back({crossing(slit,hc,y,1,-0.5,0.1,1.3,1.3,carried,t+" oblique lateral -0.5 (clips mullion)"+c),0});
            // parallel to the panel, inside the slab
            const double depth=slabLo(shape)+0.09375;
            cases.push_back({segmentLocal(slit,depth,-0.6,y,depth,1.6,y,carried,t+" parallel along width crosses opaque columns"+c),0});
            cases.push_back({segmentLocal(slit,depth,hc,-0.6,depth,hc,1.6,carried,t+" parallel up the slit column"+c),1});
            cases.push_back({segmentLocal(slit,depth,lateralOfCol(slit,4.5),-0.6,depth,lateralOfCol(slit,4.5),1.6,carried,t+" parallel up the neighbouring column"+c),0});
            // horizontal slot rows: lower half row 5, upper half row 10 are fully transparent
            cases.push_back({segmentLocal(slotLow,depth,-0.6,heightOfRow(slotLow,5.5),depth,1.6,heightOfRow(slotLow,5.5),carried,doorTag(slotLow)+" parallel through the slot row"+c),1});
            cases.push_back({segmentLocal(slotLow,depth,-0.6,heightOfRow(slotLow,6.5),depth,1.6,heightOfRow(slotLow,6.5),carried,doorTag(slotLow)+" parallel just below the slot row"+c),0});
            cases.push_back({segmentLocal(slotHigh,depth,-0.6,heightOfRow(slotHigh,10.5),depth,1.6,heightOfRow(slotHigh,10.5),carried,doorTag(slotHigh)+" parallel through the upper slot row"+c),1});
            cases.push_back({segmentLocal(slotHigh,depth,-0.6,heightOfRow(slotHigh,5.5),depth,1.6,heightOfRow(slotHigh,5.5),carried,doorTag(slotHigh)+" parallel along the lower-half slot row (opaque here)"+c),0});
        }
    }
    rig.frame(s);checkContract(rep,rig,s,"oblique/parallel layout");
    runCases(rep,rig,s,cases,"oblique/parallel");
}

inline void groupGrazes(Report& rep,Rig& rig) {
    Scene s;std::vector<Case> cases;
    // wood panel on the low-X side: slab x in [0,3/16], lateral axis Z
    Door wood=door(10,20,10,6,0,false,true),slit=door(10,20,20,8,2,false,true);
    s.doors={wood,slit};
    for(bool carried:{false,true}) {
        const std::string c=carried?" carried":" placed";
        cases.push_back({segmentLocal(wood,3.0/16.0,-0.6,0.5,3.0/16.0,1.6,0.5,carried,"ray lying in the inset face plane [measure-zero tie]"+c),1});
        cases.push_back({segmentLocal(wood,0.0,-0.6,0.5,0.0,1.6,0.5,carried,"ray lying in the cell-wall plane [measure-zero tie]"+c),1});
        cases.push_back({segmentLocal(wood,3.0/16.0-1.0/64.0,-0.6,0.5,3.0/16.0-1.0/64.0,1.6,0.5,carried,"ray 1/64 m inside the slab, parallel"+c),0});
        cases.push_back({segmentLocal(wood,0.09,-0.6,1.0,0.09,1.6,1.0,carried,"ray along the top slab plane y=1 inside the thickness [measure-zero tie]"+c),1});
        cases.push_back({segmentLocal(wood,0.09,-0.6,0.0,0.09,1.6,0.0,carried,"ray along the bottom slab plane y=0 [measure-zero tie]"+c),1});
        cases.push_back({segmentLocal(wood,0.09,-0.6,1.0-1.0/1024.0,0.09,1.6,1.0-1.0/1024.0,carried,"ray 1/1024 m below the top plane"+c),0});
        cases.push_back({segmentLocal(wood,3.0/16.0+0.5,0.5,0.5,3.0/16.0-0.5,0.5,1.5,carried,"ray touching only the slab edge point (3/16, y=1) [measure-zero tie]"+c),1});
        cases.push_back({segmentLocal(wood,3.0/16.0+1.0/10000.0,-0.6,0.5,3.0/16.0+1.0/10000.0,1.6,0.5,carried,"ray 1e-4 m outside the inset face, parallel"+c),1});
        cases.push_back({segmentLocal(wood,3.0/16.0-1.0/10000.0,-0.6,0.5,3.0/16.0-1.0/10000.0,1.6,0.5,carried,"ray 1e-4 m inside the inset face, parallel"+c),0});
        cases.push_back({segmentLocal(wood,0.09,0.5,-0.5,0.09,0.5,1.5,carried,"vertical ray inside the slab"+c),0});
        cases.push_back({segmentLocal(wood,3.0/16.0,0.5,-0.5,3.0/16.0,0.5,1.5,carried,"vertical ray in the inset face plane [measure-zero tie]"+c),1});
        // sprite-grid ties (slit column 3 spans lateral [3/16,4/16], neighbours opaque)
        cases.push_back({crossing(slit,3.0/16.0,0.5,1,0,0,1.3,1.3,carried,"normal ray on the slit|opaque boundary (lateral 3/16) [measure-zero tie]"+c),1});
        cases.push_back({crossing(slit,4.0/16.0,0.5,1,0,0,1.3,1.3,carried,"normal ray on the slit|opaque boundary (lateral 4/16) [measure-zero tie]"+c),1});
        cases.push_back({crossing(slit,2.0/16.0,0.5,1,0,0,1.3,1.3,carried,"normal ray on an opaque|opaque boundary (lateral 2/16) [measure-zero tie]"+c),0});
        cases.push_back({crossing(slit,0.5,0.5,1,0,0,1.3,1.3,carried,"normal ray on the sprite's centre column boundary, opaque|opaque [measure-zero tie]"+c),0});
    }
    // Diagonal rays through texel corners. In sprite space the line is v=u+c (slope +1) or v=c-u (slope -1), c integer:
    // every texel interior it crosses must be transparent while some texel it only touches at a corner is opaque.
    int found=0;
    for(int key=14;key<40&&found<6;key++) for(int slope:{1,-1}) for(int c0=-2;c0<=17&&found<6;c0++) {
        int interior=0;bool clear=true,touch=false;
        for(int i=0;i<16;i++) {
            const int vin=slope>0?i+c0:c0-i-1;   // texel whose interior the line crosses at column i
            if(vin<0||vin>=16) continue;
            interior++;if(Atlas::opaque(key,i,vin)) clear=false;
            const int cu[2]={slope>0?i+1:i,slope>0?i:i+1},cv[2]={slope>0?i+c0:c0-i-2,slope>0?i+c0+1:c0-i-1};
            // corner-touched neighbours: slope +1: (i+1,i+c),(i,i+c+1); slope -1: (i,c-i-2),(i+1,c-i-1)
            for(int k=0;k<2;k++) if(Atlas::opaque(key,cu[k],slope>0?(k==0?i+c0:i+c0+1):cv[k])) touch=true;
        }
        if(!clear||!touch||interior<8) continue;
        Door dd=door(4+5*(found%6),20+5*(found/6),40,8,key,(found&1)!=0,(found&2)==0);
        const double u0=-4,u1=20,v0=slope>0?u0+c0:c0-u0,v1=slope>0?u1+c0:c0-u1;
        auto toLH=[&](double u,double v,double& l,double& y){ const double uf=u/16.0,vf=v/16.0;l=dd.uMirror?1.0-uf:uf;y=dd.vDown?1.0-vf:vf; };
        double l0,y0,l1,y1;toLH(u0,v0,l0,y0);toLH(u1,v1,l1,y1);
        s.doors.push_back(dd);
        for(bool carried:{false,true}) cases.push_back({segmentLocal(dd,0.09375,l0,y0,0.09375,l1,y1,carried,
            "diagonal through texel corners "+doorTag(dd)+" slope "+std::to_string(slope)+" c="+std::to_string(c0)+(carried?" carried":" placed")),1});
        found++;
    }
    rep.check(found>0,"harness could not construct a corner-touch diagonal on any hash sprite");
    rig.frame(s);
    std::vector<Case> finite,ties;
    for(const Case& c:cases) (c.ray.label.find("[measure-zero tie]")!=std::string::npos||c.ray.label.find("diagonal through texel corners")!=std::string::npos?ties:finite).push_back(c);
    rep.begin("grazes: finite thickness (1e-4 m and 1/64 m from a face, 1/1024 m below an edge)");
    checkContract(rep,rig,s,"graze layout");
    runCases(rep,rig,s,finite,"graze");
    rep.begin("grazes: measure-zero ties (ray in a slab/cell plane, on a texel boundary, touching an edge or a texel corner)");
    runCases(rep,rig,s,ties,"tie");

    // An isolated half has an exposed edge. Where several opaque halves
    // touch, a coplanar ray is inside the union and must not slip through.
    Scene adjoining;
    std::vector<Case> seams;
    for(int count : {1, 2, 3, 4}) {
        const int z=6+count*8;
        Door lower=door(10,20,z,6,0);
        adjoining.doors.push_back(lower);
        if(count>=2) adjoining.doors.push_back(door(10,21,z,6,1));
        if(count>=3) adjoining.doors.push_back(door(10,20,z+1,6,0));
        if(count==4) adjoining.doors.push_back(door(10,21,z+1,6,1));
        for(bool carried : {false,true}) {
            for(bool reverse : {false,true}) {
                const double from=reverse?1.4:-0.5, to=reverse?-0.5:1.4;
                seams.push_back({segmentLocal(lower,from,0.5,1,to,0.5,1,carried,"horizontal join of halves"),
                                 count>=2?0:1,true});
                seams.push_back({segmentLocal(lower,from,1,1,to,1,1,carried,"corner of four panel faces"),
                                 count==4?0:1,true});
            }
        }
    }
    rep.begin("coplanar joins: exposed edges and continuous wood between adjacent door halves");
    rig.frame(adjoining);
    runCases(rep,rig,adjoining,seams,"coplanar join");
}


// A ray that crosses two voxel faces at once (exactly through a vertical cell edge) can only continue through one of the
// two face-connected walks. Production closes the crack when EVERY walk is blocked at the crossing point (lampCornerClosed):
// a full solid, or a door whose slab contains the corner and whose texel there is opaque. This is a conservative
// policy (the continuum ray touches both slabs only at one point), so it is judged against that stated rule, not the oracle.
inline void groupCornerCrossings(Report& rep,Rig& rig) {
    rep.begin("diagonal crossing of a cell edge (two voxel faces at once): door/door, door/solid, door/open");
    Scene s;std::vector<Case> cases;int cluster=0;
    enum { None,AxisX,AxisZ,Cube,MissX,MissZ };
    struct Spec { int type;int key;bool mirror; };
    auto shapeFor=[](int type,int cx,int cz){ return type==AxisX?(cx==0?6:7):type==AxisZ?(cz==0?8:9):type==MissX?(cx==0?7:6):(cz==0?9:8); };
    auto place=[&](int cell[3],int cx,int cz,const Spec& sp,const char* tag,std::string& desc){
        if(sp.type==None) { desc+=std::string(tag)+":none ";return; }
        if(sp.type==Cube) { s.cubes.push_back({{cell[0],cell[1],cell[2]}});desc+=std::string(tag)+":stone ";return; }
        const Door d=door(cell[0],cell[1],cell[2],shapeFor(sp.type,cx,cz),sp.key,sp.mirror,true);s.doors.push_back(d);desc+=std::string(tag)+":"+doorTag(d)+" ";
    };
    // family A: ray SW<->NE, walks through SE (corner at its local (0,1)) and NW (local (1,0)); family B: SE<->NW through SW (1,1) and NE (0,0)
    auto addCase=[&](int family,const Spec& first,const Spec& second,double y,int expect,const std::string& label) {
        const int vx=10+8*(cluster%6),vz=10+8*(cluster/6),vy=30;cluster++;
        int cellA[3],cellB[3];int cxA,czA,cxB,czB;D3 from,to;
        if(family==0) { cellA[0]=vx;cellA[2]=vz-1;cxA=0;czA=1;cellB[0]=vx-1;cellB[2]=vz;cxB=1;czB=0;from={vx-0.5,vy+y,vz-0.5};to={vx+0.5,vy+y,vz+0.5}; }
        else          { cellA[0]=vx-1;cellA[2]=vz-1;cxA=1;czA=1;cellB[0]=vx;cellB[2]=vz;cxB=0;czB=0;from={vx+0.5,vy+y,vz-0.5};to={vx-0.5,vy+y,vz+0.5}; }
        cellA[1]=cellB[1]=vy;std::string desc;place(cellA,cxA,czA,first,"A",desc);place(cellB,cxB,czB,second,"B",desc);
        for(bool reverse:{false,true}) for(bool carried:{false,true}) {
            Ray r{reverse?to:from,reverse?from:to,carried,label+" family "+(family?"B":"A")+(reverse?" reversed":"")+(carried?" carried":" placed")+" | "+desc};
            cases.push_back({r,expect,true});
        }
    };
    const double yMid=0.5,ySlot=1.0-5.5/16.0;
    for(int family=0;family<2;family++) {
        addCase(family,{AxisX,0,false},{AxisZ,0,false},yMid,0,"wood X-slab + wood Z-slab both contain the corner");
        addCase(family,{AxisX,0,true},{AxisX,0,false},yMid,0,"two wood X-slabs both contain the corner, mirrored");
        addCase(family,{AxisZ,0,false},{AxisZ,0,true},yMid,0,"two wood Z-slabs both contain the corner");
        addCase(family,{AxisX,0,false},{None,0,false},yMid,1,"wood door on one walk, the other walk open air");
        addCase(family,{None,0,false},{AxisZ,0,false},yMid,1,"open air on one walk, wood door on the other");
        addCase(family,{AxisX,0,false},{Cube,0,false},yMid,0,"wood door + full stone cube");
        addCase(family,{Cube,0,false},{Cube,0,false},yMid,0,"two full stone cubes (existing rule)");
        addCase(family,{AxisX,0,false},{AxisZ,6,false},ySlot,1,"wood door + slot door transparent at the corner row");
        addCase(family,{AxisX,0,false},{AxisZ,6,false},yMid,0,"wood door + slot door, row boundary 7|8 opaque at the corner");
        addCase(family,{AxisX,2,false},{AxisZ,0,false},yMid,0,"slit door (opaque at the corner column) + wood door");
        addCase(family,{MissX,0,false},{MissZ,0,false},yMid,1,"both doors on the far side of their cells (slabs do not contain the corner)");
        addCase(family,{AxisX,0,false},{MissZ,0,false},yMid,1,"one slab contains the corner, the other cell's slab does not");
    }
    rig.frame(s);runCases(rep,rig,s,cases,"corner");
}

inline void groupRotationReplace(Report& rep,Rig& rig) {
    rep.begin("rotation, removal and replacing back");
    const int cx=24,cy=24,cz=24;
    Door closed=door(cx,cy,cz,8,4),open=door(cx,cy,cz,6,2,true,true),slitClosed=door(cx,cy,cz,8,2);
    auto ray=[&](const Door& d,bool carried,const std::string& label){ return crossing(d,lateralOfCol(d,3.5),heightOfRow(d,5.5),1,0,0,1.3,1.3,carried,label); };
    std::vector<std::vector<std::array<float,3>>> frames;
    auto runFrame=[&](const Scene& s,const std::string& name,const std::vector<Case>& c){
        rig.frame(s);checkContract(rep,rig,s,name);runCases(rep,rig,s,c,name);
        std::vector<Ray> rs;for(auto& k:c) rs.push_back(k.ray);frames.push_back(rig.transmission(rs));
    };
    Scene s1;s1.doors={closed};Scene s2;Scene s3;s3.doors={open};Scene s4=s1;Scene s5;s5.doors={slitClosed};
    // ray hits the window texel of the lower-half sprite (key 4 has window col3,row5)
    std::vector<Case> c1={{ray(closed,false,"key4 closed: window texel"),1},{crossing(closed,lateralOfCol(closed,0.5),heightOfRow(closed,0.5),1,0,0,1.3,1.3,false,"key4 closed: opaque corner texel"),0}};
    std::vector<Case> c2={{ray(closed,false,"key4 removed: window texel"),1},{crossing(closed,lateralOfCol(closed,0.5),heightOfRow(closed,0.5),1,0,0,1.3,1.3,false,"key4 removed: opaque corner texel"),1}};
    // swung: panel on the low-X side, slit sprite (key 2); the old Z-axis line misses it, an X-axis line through the slit passes
    std::vector<Case> c3={{segmentLocal(open,0.5,-1.3,0.5,0.5,2.3,0.5,false,"swung slit door: line along Z at x=.5"),1},
                          {crossing(open,lateralOfCol(open,3.5),heightOfRow(open,6.5),1,0,0,1.3,1.3,false,"swung slit door: through slit"),1},
                          {crossing(open,lateralOfCol(open,4.5),heightOfRow(open,6.5),1,0,0,1.3,1.3,false,"swung slit door: through mullion"),0}};
    std::vector<Case> c5={{crossing(slitClosed,lateralOfCol(slitClosed,3.5),heightOfRow(slitClosed,6.5),1,0,0,1.3,1.3,false,"key2 closed: slit"),1},
                          {crossing(slitClosed,lateralOfCol(slitClosed,4.5),heightOfRow(slitClosed,6.5),1,0,0,1.3,1.3,false,"key2 closed: mullion"),0}};
    runFrame(s1,"frame1 closed",c1);
    runFrame(s2,"frame2 removed",c2);
    runFrame(s3,"frame3 rotated open",c3);
    runFrame(s5,"frame4 different sprite closed",c5);
    runFrame(s4,"frame5 replaced back",c1);
    rep.check(frames[0]==frames[4],"frame5 (replaced back) differs from frame1 (closed)");
}

inline void groupIndependence(Report& rep,Rig& rig) {
    rep.begin("independence: second light, batch/draw order, keys, solid pass");
    // One receiver, three lights behind two doors in one frame. Doors: slit (key 2) and wood (key 0), panels on the low-Z side.
    Door slit=door(30,30,30,8,2,false,true),wood=door(36,30,30,8,0,false,true);
    Scene s;s.doors={slit,wood};
    auto aim=[&](const Door& d,const D3& from,double h,double y,const std::string& label){   // light beyond the panel, line through (h,y) on the mid-plane
        const D3 mid=localPoint(d,slabMid(d.shape),h,y);Ray r;r.a=from;r.label=label;
        for(int k=0;k<3;k++) r.b[k]=from[k]+1.6*(mid[k]-from[k]);
        return r;
    };
    const D3 R1={30.5,30.5,28.0},R2={36.5,30.5,28.0};
    const Ray A=aim(slit,R1,lateralOfCol(slit,3.5),heightOfRow(slit,6.5),"light A behind the slit");
    const Ray B=aim(slit,R1,lateralOfCol(slit,4.5),heightOfRow(slit,6.5),"light B behind a mullion");
    const Ray W=aim(wood,R2,0.5,0.5,"light W behind the wood door");
    rig.frame(s);
    const std::vector<Ray> together={A,B,W},reversed={W,B,A},aloneA={A},aloneB={B};
    const auto t=rig.transmission(together),r=rig.transmission(reversed),a=rig.transmission(aloneA),b=rig.transmission(aloneB);
    const Oracle oracle(s);
    rep.check(t[0][0]==1.0f&&oracle.transmission(A)==1.0,"light A (slit) must transmit, got "+fmt(t[0][0]));
    rep.check(t[1][0]==0.0f&&oracle.transmission(B)==0.0,"light B (mullion) must be blocked, got "+fmt(t[1][0]));
    rep.check(t[2][0]==0.0f&&oracle.transmission(W)==0.0,"light W (wood door) must be blocked, got "+fmt(t[2][0]));
    rep.check(t[0]==r[2]&&t[1]==r[1]&&t[2]==r[0],"ray order changes a result");
    rep.check(t[0]==a[0]&&t[1]==b[0],"batching changes a result");
    rig.frame(s,true);
    const auto t2=rig.transmission(together);rep.check(t2==t,"door draw order changes a result");
    checkContract(rep,rig,s,"two keys, reversed draw order");
    // two doors of the same key but different orientation in one frame: shared mask row is OR-idempotent
    Scene same;same.doors={door(30,30,30,8,2,false,true),door(36,30,30,6,2,true,true),door(30,36,30,9,2,false,false),door(36,36,30,7,2,true,false)};
    rig.frame(same);checkContract(rep,rig,same,"same key, four orientations in one frame");
    std::vector<Case> cs;
    for(const Door& dd:same.doors) {
        cs.push_back({crossing(dd,lateralOfCol(dd,3.5),heightOfRow(dd,6.5),1,0,0,1.3,1.3,false,doorTag(dd)+" slit"),1});
        cs.push_back({crossing(dd,lateralOfCol(dd,4.5),heightOfRow(dd,6.5),1,0,0,1.3,1.3,false,doorTag(dd)+" mullion"),0});
    }
    runCases(rep,rig,same,cs,"same key, four orientations");
    // solid pass vs cutout pass must publish the same transmission
    rig.frame(same,false,true);runCases(rep,rig,same,cs,"doors via shadow_solid");
}

inline void groupLighting(Report& rep,Rig& rig) {
    rep.begin("end-to-end lampLighting(): door vs stone vs open, with a second unaffected torch");
    // torch T1 in cell z=40, door cell z=41, receiver at z=42.5 facing T1; torch T2 on the same side as T1 but off the door line
    auto build=[&](int variant){
        Scene s;s.lamps.push_back({{40,30,40},10100,14});s.lamps.push_back({{43,30,40},10100,14});
        if(variant==1) s.doors.push_back(door(40,30,41,8,0));       // wood door, panel on the torch side
        if(variant==2) s.cubes.push_back({{40,30,41}});             // opaque stone block
        if(variant==3) s.doors.push_back(door(40,30,41,9,0));       // wood door, panel on the receiver side
        if(variant==4) s.doors.push_back(door(40,30,41,8,6));       // slot door: row 5 (y=0.625..0.6875) is a transparent strip
        if(variant==5) s.lamps.erase(s.lamps.begin());              // only T2
        return s;
    };
    const Rig::Query q{{40.5,30.64,42.5},{0,0,-1},0.0f};
    std::vector<std::array<float,3>> v(6);
    for(int i=0;i<6;i++) { Scene s=build(i);rig.frame(s);v[size_t(i)]=rig.lighting({q})[0]; }
    auto lum=[&](int i){ return double(v[size_t(i)][0])+v[size_t(i)][1]+v[size_t(i)][2]; };
    rep.check(lum(0)>lum(1)+1e-3,"open air must be brighter than a closed wood door: "+fmt(lum(0))+" vs "+fmt(lum(1)));
    rep.check(v[1]==v[2],"closed wood door (panel near torch) must equal a solid stone block for the blocked torch: "+fmt(lum(1))+" vs "+fmt(lum(2)));
    rep.check(v[3]==v[2],"closed wood door (panel near receiver) must equal a solid stone block: "+fmt(lum(3))+" vs "+fmt(lum(2)));
    rep.check(lum(4)>lum(1)+1e-6,"slot door must pass some light vs wood: "+fmt(lum(4))+" vs "+fmt(lum(1)));
    rep.check(lum(4)<lum(0),"slot door must pass less light than open air: "+fmt(lum(4))+" vs "+fmt(lum(0)));
    rep.check(std::abs(lum(1)-lum(5))<=1e-6*std::max(1.0,lum(5))&&lum(5)>0.0,"the unaffected second torch must keep its full contribution behind a closed door: door="+fmt(lum(1))+" second-only="+fmt(lum(5)));
}

inline void groupSweep(Report& rep,Rig& rig,const std::string& tag,uint64_t seed) {
    rep.begin("random sweep vs CPU oracle ("+tag+")");
    Scene s;int n=0;
    for(int key=0;key<40;key++) for(int shape=6;shape<10;shape++) for(int mode=0;mode<4;mode++) {
        const int i=n++;s.doors.push_back(latticeDoor(i,shape,key,mode&1,(mode&2)==0));
    }
    rig.frame(s);checkContract(rep,rig,s,"sweep layout "+tag);
    std::mt19937_64 rng(seed);auto U=[&](double a,double b){ return a+(b-a)*(double(rng()>>11)/9007199254740992.0); };
    std::vector<Ray> rays;
    for(const Door& d:s.doors) for(int k=0;k<48;k++) {   // k-- on resample keeps 48 rays per door
        const bool skim=k%7==0;double dn=(rng()&1?1:-1)*(skim?U(0.0,0.05):U(0.3,1.0));
        double dl=U(-1.6,1.6),dy=U(-1.6,1.6);if(skim) { dl*=2;dy*=2; }
        const double h=U(0.02,0.98),y=U(0.02,0.98),ta=U(0.7,1.6),tb=U(0.7,1.6);
        bool carried=(rng()&1)!=0;
        Ray r=crossing(d,h,y,dn,dl,dy,ta,tb,carried,doorTag(d)+" #"+std::to_string(k));
        bool inside=true;for(int i=0;i<3;i++) inside=inside&&r.a[i]>=0.5&&r.a[i]<63.5&&r.b[i]>=0.5&&r.b[i]<63.5;
        if(!inside) { k--;continue; }   // production walks only inside the 64^3 grid; resample instead of testing the grid edge
        bool goalIsDoor=true;for(int i=0;i<3;i++) goalIsDoor=goalIsDoor&&int(std::floor(r.b[i]))==d.c[i];
        if(goalIsDoor&&!carried) r.carried=true;
        rays.push_back(r);
    }
    int bad=0,zero=0,amb=0;runAgainstOracle(rep,rig,s,rays,"sweep "+tag,&bad,&zero,&amb);
    std::cout<<"  sweep "<<tag<<": "<<rays.size()<<" rays; "<<amb<<" excluded as float32-unresolvable (within 3e-5 m of a texel/slab edge); "
             <<(int(rays.size())-amb)<<" judged, "<<zero<<" of them blocked by the oracle, "<<bad<<" GPU/oracle disagreements\n";
}

inline void probe(const fs::path& root) {
    Report rep;Rig rig;
    std::cout<<"door-light probe: shader tree "<<root.string()<<" (production lampTransmission/lampLighting, shadow vertex capture, shadowcomp1)\n";
    try { groupDeclarations(rep,root); } catch(const std::exception& e) { rep.check(false,std::string("declarations: ")+e.what()); }
    try {
        rig.init(root);
        std::cout<<"  rig: "<<rig.images.size()<<" declared images, doorMaskImage "<<(rig.declared("doorMaskImage")?"declared":"ABSENT")<<'\n';
    } catch(const std::exception& e) {
        rep.begin("rig setup (compile/link production programs)");rep.check(false,e.what());rep.print();
        throw std::runtime_error("door-light QA FAIL: cannot build the GPU rig");
    }
    struct G { const char* name;std::function<void()> run; };
    const std::vector<G> gs={
        {"contract",[&]{ groupContract(rep,rig); }},
        {"closed/open",[&]{ groupClosedOpen(rep,rig); }},
        {"shapes",[&]{ groupShapesAndSlit(rep,rig); }},
        {"top/bottom",[&]{ groupTopBottom(rep,rig); }},
        {"oblique",[&]{ groupObliqueParallel(rep,rig); }},
        {"graze",[&]{ groupGrazes(rep,rig); }},
        {"corners",[&]{ groupCornerCrossings(rep,rig); }},
        {"rotation",[&]{ groupRotationReplace(rep,rig); }},
        {"independence",[&]{ groupIndependence(rep,rig); }},
        {"lighting",[&]{ groupLighting(rep,rig); }},
        {"sweep near",[&]{ rig.cam={3.25,1.5,6.75};groupSweep(rep,rig,"camera near origin",20261121); }},
        {"sweep far",[&]{ rig.cam={123457.375,71.625,-98766.125};groupSweep(rep,rig,"camera 1e5 m away",20261122);rig.cam={3.25,1.5,6.75}; }},
    };
    for(const G& g:gs) {
        try { g.run(); } catch(const std::exception& e) {
            if(rep.groups.empty()) rep.begin(g.name);
            rep.check(false,std::string(g.name)+": exception: "+e.what());
        }
    }
    if(!rig.unboundSamplers.empty()) { rep.begin("sampler uniforms without a shaders.properties texture");for(auto& u:rig.unboundSamplers) rep.check(false,"program samples '"+u+"' which no declared image provides (probe cannot bind it legitimately)"); }
    if(!rig.unbound.empty()) { rep.begin("image uniforms without a shaders.properties declaration");for(auto& u:rig.unbound) rep.check(false,"program declares image uniform '"+u+"' not present in shaders.properties"); }
    rep.print();
    std::cout<<"door-light summary: "<<(rep.checks()-rep.fails())<<"/"<<rep.checks()<<" checks passed on "<<rig.renderer<<"\n";
    std::cout<<"scope: native GL harness on the real shadow vertex, shadowcomp1 and lampTransmission/lampLighting with a synthetic atlas; "
               "a correctness oracle, not Minecraft frame timing, not a fluid simulation.\n";
    if(rep.fails()) throw std::runtime_error("door-light QA FAIL: "+std::to_string(rep.fails())+" of "+std::to_string(rep.checks())+" checks failed");
}
}
