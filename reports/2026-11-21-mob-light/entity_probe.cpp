// Independent GPU probe for the entity-light-21 candidate. It compiles the
// real candidate stages, captures synthetic animated "mobs" through the real
// shadow_entities.vsh/.gsh/.fsh program and queries the real
// lib/entity_occlusion.glsl and lib/local_lighting.glsl code. A double-precision
// CPU ray/triangle reference over the same triangles is the oracle.
//
// It does NOT run Minecraft or Iris: Iris preprocessing/patching, entity ids,
// the shadow-pass entity set and the per-frame image clear are emulated.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <algorithm>
#include <cstddef>
#include <cstring>
#include <set>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;

static std::string readFile(const fs::path& p) {
    std::ifstream in(p);
    if(!in) throw std::runtime_error("cannot read "+p.string());
    std::ostringstream s;s<<in.rdbuf();return s.str();
}
static std::string expand(const fs::path& file,const fs::path& root,int depth=0) {
    if(depth>32) throw std::runtime_error("include depth");
    std::istringstream in(readFile(file));
    std::ostringstream out;
    for(std::string line;std::getline(in,line);) {
        if(line.rfind("#include",0)==0) {
            auto a=line.find('"'),b=line.find('"',a+1);
            std::string name=line.substr(a+1,b-a-1);
            out<<expand(root/name.substr(name[0]=='/'?1:0),root,depth+1);
        } else out<<line<<'\n';
    }
    return out.str();
}
static std::string replaceAll(std::string s,const std::string& a,const std::string& b) {
    size_t at=0;int n=0;
    while((at=s.find(a,at))!=std::string::npos) { s.replace(at,a.size(),b);at+=b.size();n++; }
    if(n==0) throw std::runtime_error("substitution target missing: "+a);
    return s;
}
static GLuint compileStage(GLenum type,const std::string& src,const std::string& name) {
    GLuint s=glCreateShader(type);
    const char* t=src.c_str();glShaderSource(s,1,&t,nullptr);glCompileShader(s);
    GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if(!ok) { char log[16384];glGetShaderInfoLog(s,sizeof log,nullptr,log);throw std::runtime_error(name+": "+log); }
    return s;
}
static GLuint linkProgram(const std::vector<GLuint>& stages,const std::string& name,
                          const std::vector<std::pair<GLuint,const char*>>& attribs={}) {
    GLuint p=glCreateProgram();
    for(auto s:stages) glAttachShader(p,s);
    for(auto& a:attribs) glBindAttribLocation(p,a.first,a.second);
    glLinkProgram(p);
    for(auto s:stages) glDeleteShader(s);
    GLint ok=0;glGetProgramiv(p,GL_LINK_STATUS,&ok);
    if(!ok) { char log[16384];glGetProgramInfoLog(p,sizeof log,nullptr,log);throw std::runtime_error(name+": "+log); }
    return p;
}
struct Resources { int samplers=0,images=0; };
static Resources activeResources(GLuint p) {
    Resources r;GLint n=0;glGetProgramiv(p,GL_ACTIVE_UNIFORMS,&n);
    for(GLint i=0;i<n;i++) {
        char name[256];GLint size;GLenum type;glGetActiveUniform(p,i,sizeof name,nullptr,&size,&type,name);
        switch(type) {
            case GL_SAMPLER_2D: case GL_SAMPLER_2D_SHADOW: case GL_UNSIGNED_INT_SAMPLER_2D: case GL_INT_SAMPLER_2D:
            case GL_SAMPLER_3D: r.samplers+=size;break;
            case GL_IMAGE_2D: case GL_UNSIGNED_INT_IMAGE_2D: case GL_INT_IMAGE_2D: r.images+=size;break;
            default: break;
        }
    }
    return r;
}

// ---------------------------------------------------------------- geometry
struct V3 { double x=0,y=0,z=0; };
static V3 operator+(V3 a,V3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
static V3 operator-(V3 a,V3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static V3 operator*(V3 a,double s){return {a.x*s,a.y*s,a.z*s};}
static double dot(V3 a,V3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V3 cross(V3 a,V3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static double len(V3 a){return std::sqrt(dot(a,a));}
static V3 rotX(V3 p,double a){double c=std::cos(a),s=std::sin(a);return {p.x,c*p.y-s*p.z,s*p.y+c*p.z};}
static V3 rotY(V3 p,double a){double c=std::cos(a),s=std::sin(a);return {c*p.x+s*p.z,p.y,-s*p.x+c*p.z};}

struct Vertex { float p[3],uv[2],c[4],n[3]; };
struct Tri { V3 p[3]; double uv[3][2]; };
struct Mesh {
    std::vector<Vertex> v;  // GL_TRIANGLES, Minecraft quad split 0,1,2 / 2,3,0
    std::vector<Tri> t;
    void quad(const std::array<V3,4>& q,const std::array<std::array<double,2>,4>& uv,float alpha=1.0f) {
        V3 n=cross(q[1]-q[0],q[2]-q[0]);n=n*(1.0/std::max(len(n),1e-12));
        const int order[6]={0,1,2,2,3,0};
        for(int k=0;k<6;k++) {
            int i=order[k];
            v.push_back({{float(q[i].x),float(q[i].y),float(q[i].z)},{float(uv[i][0]),float(uv[i][1])},
                         {1,1,1,alpha},{float(n.x),float(n.y),float(n.z)}});
        }
        // CPU oracle uses the float-rounded positions the GPU receives.
        for(int tri=0;tri<2;tri++) {
            Tri T;
            for(int k=0;k<3;k++) {
                const Vertex& vx=v[v.size()-6+3*tri+k];
                T.p[k]={vx.p[0],vx.p[1],vx.p[2]};T.uv[k][0]=vx.uv[0];T.uv[k][1]=vx.uv[1];
            }
            t.push_back(T);
        }
    }
    void append(const Mesh& m){v.insert(v.end(),m.v.begin(),m.v.end());t.insert(t.end(),m.t.begin(),m.t.end());}
};
// Box [lo,hi] in part space -> world by fn. All faces map to one atlas rect.
static void addBox(Mesh& m,V3 lo,V3 hi,const std::function<V3(V3)>& fn,std::array<double,4> r) {
    auto P=[&](int x,int y,int z){return fn({x?hi.x:lo.x,y?hi.y:lo.y,z?hi.z:lo.z});};
    std::array<std::array<double,2>,4> uv={{{r[0],r[1]},{r[0],r[3]},{r[2],r[3]},{r[2],r[1]}}};
    m.quad({P(0,0,0),P(0,1,0),P(1,1,0),P(1,0,0)},uv);
    m.quad({P(1,0,1),P(1,1,1),P(0,1,1),P(0,0,1)},uv);
    m.quad({P(0,0,1),P(0,1,1),P(0,1,0),P(0,0,0)},uv);
    m.quad({P(1,0,0),P(1,1,0),P(1,1,1),P(1,0,1)},uv);
    m.quad({P(0,1,0),P(0,1,1),P(1,1,1),P(1,1,0)},uv);
    m.quad({P(0,0,1),P(0,0,0),P(1,0,0),P(1,0,1)},uv);
}
static const std::array<double,4> opaqueRect={0.0,0.0,0.5,1.0};
// Humanoid of six cuboids (72 triangles) with swinging limbs.
static Mesh humanoid(V3 feet,double yaw,double swing) {
    Mesh m;
    auto place=[&](V3 pivot,double pitch){return [=](V3 p){return rotY(rotX(p,pitch)+pivot,yaw)+feet;};};
    addBox(m,{-0.25,1.5,-0.25},{0.25,2.0,0.25},place({0,0,0},0),opaqueRect);
    addBox(m,{-0.25,0.75,-0.125},{0.25,1.5,0.125},place({0,0,0},0),opaqueRect);
    addBox(m,{-0.125,-0.75,-0.125},{0.125,0,0.125},place({-0.375,1.5,0},-1.4),opaqueRect);
    addBox(m,{-0.125,-0.75,-0.125},{0.125,0,0.125},place({0.375,1.5,0},-1.4),opaqueRect);
    addBox(m,{-0.125,-0.75,-0.125},{0.125,0,0.125},place({-0.125,0.75,0},swing),opaqueRect);
    addBox(m,{-0.125,-0.75,-0.125},{0.125,0,0.125},place({0.125,0.75,0},-swing),opaqueRect);
    return m;
}
// 1 m panel mapped to the 8x8-texel cutout region.
static Mesh cutoutPanel(V3 centre,double yaw) {
    Mesh m;
    auto f=[&](double x,double y){return rotY({x,y,0},yaw)+centre;};
    m.quad({f(-0.5,-0.5),f(-0.5,0.5),f(0.5,0.5),f(0.5,-0.5)},{{{0.5,0.25},{0.5,0.0},{0.75,0.0},{0.75,0.25}}});
    return m;
}

// 32x32 atlas: left half opaque, region [16,24)x[0,8) is an 8x8 entity-style
// cutout (2-texel border ring, 2x2 hole pattern inside), rest transparent.
static const int atlasSize=32;
static uint8_t atlasAlpha(int x,int y) {
    if(x<16) return 255;
    if(x<24 && y<8) {
        int lx=x-16,ly=y;
        bool ring=lx<2 || lx>=6 || ly<2 || ly>=6;
        bool pin=((lx/2)+(ly/2))%2==0;
        return (ring || pin)?255:0;
    }
    if(x>=16 && y>=8 && y<24) return ((x+y)%2==0)?255:0; // 16x16 one-texel checker
    return 0;
}
static bool texelOpaque(double u,double v) {
    int x=std::clamp(int(std::floor(u*atlasSize)),0,atlasSize-1),y=std::clamp(int(std::floor(v*atlasSize)),0,atlasSize-1);
    return atlasAlpha(x,y)>=26; // 0.1 * 255
}
// Same lattice as lib/entity_grid.glsl, in float like the GPU.
static int maskBit(float u,float v) {
    float gx=std::clamp(u,0.0f,1.0f)*8.0f,gy=std::clamp(v,0.0f,1.0f)*8.0f;
    int cx=int(std::min(std::floor(gx),7.0f)),cy=int(std::min(std::floor(gy),7.0f));
    if(cx+cy>7){int s=cx+cy-7;if(cx>=cy)cx-=s;else cy-=s;}
    float fx=gx-cx,fy=gy-cy;
    if(fx+fy<1.0f || cx+cy>=7) return cy*8-(cy*(cy-1))/2+cx;
    return 36+cy*7-(cy*(cy-1))/2+cx;
}
static void maskCentroid(int bit,double& u,double& v) {
    bool inv=bit>=36;int k=inv?bit-36:bit,w=inv?7:8,j=0;
    while(k>=w-j){k-=w-j;j++;}
    u=(k+(inv?2.0/3:1.0/3))/8;v=(j+(inv?2.0/3:1.0/3))/8;
}
struct Oracle { bool exact,lattice; };
static Oracle oracle(const std::vector<Tri>& tris,V3 s,V3 t,bool carried,const std::vector<bool>& self) {
    V3 d=t-s;double dist=len(d);
    Oracle o{false,false};
    if(dist<=0.02) return o;
    double tMin=0.01/dist,tMax=1.0-0.01/dist;
    for(size_t i=0;i<tris.size();i++) {
        if(carried && self[i]) continue;
        const Tri& T=tris[i];
        V3 e1=T.p[1]-T.p[0],e2=T.p[2]-T.p[0];
        V3 p=cross(d,e2);double det=dot(e1,p);
        if(std::abs(det)<1e-12) continue;
        V3 q0=s-T.p[0];double u=dot(q0,p)/det;if(u<0||u>1) continue;
        V3 q=cross(q0,e1);double v=dot(d,q)/det;if(v<0||u+v>1) continue;
        double tt=dot(e2,q)/det;if(tt<=tMin||tt>=tMax) continue;
        double hu=T.uv[0][0]+u*(T.uv[1][0]-T.uv[0][0])+v*(T.uv[2][0]-T.uv[0][0]);
        double hv=T.uv[0][1]+u*(T.uv[1][1]-T.uv[0][1])+v*(T.uv[2][1]-T.uv[0][1]);
        if(texelOpaque(hu,hv)) o.exact=true;
        double cu,cv;maskCentroid(maskBit(float(u),float(v)),cu,cv);
        double lu=T.uv[0][0]+cu*(T.uv[1][0]-T.uv[0][0])+cv*(T.uv[2][0]-T.uv[0][0]);
        double lv=T.uv[0][1]+cu*(T.uv[1][1]-T.uv[0][1])+cv*(T.uv[2][1]-T.uv[0][1]);
        if(texelOpaque(lu,lv)) o.lattice=true;
        if(o.exact && o.lattice) break;
    }
    return o;
}

// ---------------------------------------------------------------- GPU state
struct Gpu {
    fs::path root;
    GLuint capture=0,baseline=0,query=0,queryUnbounded=0,lighting1=0,lighting3=0;
    GLuint meta=0,heads=0,nodes=0,tris=0,shore=0,atlas=0,lightList=0,lightField=0;
    GLuint fbo=0,color0=0,color1=0,depth=0,vbo=0,rayBuffer=0,outBuffer=0;
    int fboSize=1024;
};
static GLuint makeTex(GLenum internal,int w,int h,GLenum filter=GL_NEAREST) {
    GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);
    glTexStorage2D(GL_TEXTURE_2D,1,internal,w,h);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    return t;
}
static const float shadowMV[16]={ // column-major rotation: a low oblique Sun
    0.8660254f,0.25f,-0.4330127f,0, 0,0.8660254f,0.5f,0, 0.5f,-0.4330127f,0.75f,0, 0,0,0,1};
static void setUniforms(GLuint p,const float camera[3]) {
    float inv[16];for(int c=0;c<4;c++)for(int r=0;r<4;r++)inv[c*4+r]=(r<3&&c<3)?shadowMV[r*4+c]:(r==c?1.0f:0.0f);
    GLint l;
    if((l=glGetUniformLocation(p,"shadowModelViewInverse"))>=0) glUniformMatrix4fv(l,1,GL_FALSE,inv);
    if((l=glGetUniformLocation(p,"cameraPosition"))>=0) glUniform3fv(l,1,camera);
    if((l=glGetUniformLocation(p,"isEyeInWater"))>=0) glUniform1i(l,0);
    if((l=glGetUniformLocation(p,"gtexture"))>=0) glUniform1i(l,0);
}
static void setSampler(GLuint p,const char* name,int unit,GLuint tex) {
    GLint l=glGetUniformLocation(p,name);
    glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,tex);
    if(l>=0) glUniform1i(l,unit);
}
static void bindImage(GLuint p,const char* name,int unit,GLuint tex,GLenum fmt) {
    GLint l=glGetUniformLocation(p,name);
    glBindImageTexture(unit,tex,0,GL_FALSE,0,GL_READ_WRITE,fmt);
    if(l>=0) glUniform1i(l,unit);
}
static void irisFrameClear(Gpu& g) {
    // Iris beginLevelRendering clears clear=true images only (meta, heads).
    glClearTexImage(g.meta,0,GL_RED_INTEGER,GL_UNSIGNED_INT,nullptr);
    glClearTexImage(g.heads,0,GL_RED_INTEGER,GL_UNSIGNED_INT,nullptr);
}
static double drawShadow(Gpu& g,GLuint program,const Mesh& m,int entityId,const float camera[3],bool timed=false) {
    glBindFramebuffer(GL_FRAMEBUFFER,g.fbo);
    glViewport(0,0,g.fboSize,g.fboSize);
    glUseProgram(program);setUniforms(program,camera);
    GLint l=glGetUniformLocation(program,"entityId");if(l>=0) glUniform1i(l,entityId);
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,g.atlas);
    bindImage(program,"entityMetaImage",0,g.meta,GL_R32UI);
    bindImage(program,"entityHeadImage",1,g.heads,GL_R32UI);
    bindImage(program,"entityNodeImage",2,g.nodes,GL_RGBA32UI);
    bindImage(program,"entityTriangleImage",3,g.tris,GL_RGBA32UI);
    bindImage(program,"shoreFaceImage",4,g.shore,GL_R32UI);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(-30,30,-30,30,-60,60);
    glMatrixMode(GL_MODELVIEW);glLoadMatrixf(shadowMV);
    glMatrixMode(GL_TEXTURE);glLoadIdentity();
    glMultiTexCoord2f(GL_TEXTURE1,0.03f,0.97f);
    glVertexAttrib4f(10,-1,0,0,0);glVertexAttrib4f(11,0,0,0,0);
    glBindBuffer(GL_ARRAY_BUFFER,g.vbo);
    glBufferData(GL_ARRAY_BUFFER,m.v.size()*sizeof(Vertex),m.v.data(),GL_STREAM_DRAW);
    glEnableClientState(GL_VERTEX_ARRAY);glVertexPointer(3,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,p));
    glClientActiveTexture(GL_TEXTURE0);glEnableClientState(GL_TEXTURE_COORD_ARRAY);glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,uv));
    glEnableClientState(GL_COLOR_ARRAY);glColorPointer(4,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,c));
    glEnableClientState(GL_NORMAL_ARRAY);glNormalPointer(GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,n));
    glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDisable(GL_CULL_FACE);
    GLuint q=0;if(timed){glGenQueries(1,&q);glBeginQuery(GL_TIME_ELAPSED,q);}
    glDrawArrays(GL_TRIANGLES,0,GLsizei(m.v.size()));
    double ms=0;
    if(timed){glEndQuery(GL_TIME_ELAPSED);GLuint64 ns=0;glGetQueryObjectui64v(q,GL_QUERY_RESULT,&ns);ms=ns*1e-6;glDeleteQueries(1,&q);}
    glDisableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);
    glDisableClientState(GL_COLOR_ARRAY);glDisableClientState(GL_NORMAL_ARRAY);
    glMemoryBarrier(GL_ALL_BARRIER_BITS);
    return ms;
}
static void clearTargets(Gpu& g) {
    glBindFramebuffer(GL_FRAMEBUFFER,g.fbo);
    float zero[4]={0,0,0,0},one=1.0f;
    glClearBufferfv(GL_COLOR,0,zero);glClearBufferfv(GL_COLOR,1,zero);glClearBufferfv(GL_DEPTH,0,&one);
}
static std::vector<uint32_t> readMeta(Gpu& g) {
    std::vector<uint32_t> m(512);glBindTexture(GL_TEXTURE_2D,g.meta);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,m.data());return m;
}
struct Ray { V3 s,t;bool carried; };
static std::vector<float> lastWork;
static std::vector<float> queryRays(Gpu& g,GLuint program,const std::vector<Ray>& rays,const float camera[3],double* ms=nullptr) {
    std::vector<float> in(rays.size()*8);
    for(size_t i=0;i<rays.size();i++){
        float* r=&in[i*8];r[0]=float(rays[i].s.x);r[1]=float(rays[i].s.y);r[2]=float(rays[i].s.z);r[3]=rays[i].carried?1.f:0.f;
        r[4]=float(rays[i].t.x);r[5]=float(rays[i].t.y);r[6]=float(rays[i].t.z);r[7]=0;
    }
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,g.rayBuffer);glBufferData(GL_SHADER_STORAGE_BUFFER,in.size()*4,in.data(),GL_STREAM_DRAW);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,g.outBuffer);glBufferData(GL_SHADER_STORAGE_BUFFER,rays.size()*4,nullptr,GL_STREAM_READ);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,g.rayBuffer);glBindBufferBase(GL_SHADER_STORAGE_BUFFER,1,g.outBuffer);
    glUseProgram(program);setUniforms(program,camera);
    setSampler(program,"aqualumenEntityMeta",1,g.meta);setSampler(program,"aqualumenEntityHeads",2,g.heads);
    setSampler(program,"aqualumenEntityNodes",3,g.nodes);setSampler(program,"aqualumenEntityTriangles",4,g.tris);
    glUniform1i(glGetUniformLocation(program,"rayCount"),GLint(rays.size()));
    GLuint q=0;if(ms){glGenQueries(1,&q);glBeginQuery(GL_TIME_ELAPSED,q);}
    glDispatchCompute(GLuint((rays.size()+63)/64),1,1);
    if(ms){glEndQuery(GL_TIME_ELAPSED);GLuint64 ns=0;glGetQueryObjectui64v(q,GL_QUERY_RESULT,&ns);*ms=ns*1e-6;glDeleteQueries(1,&q);}
    glMemoryBarrier(GL_ALL_BARRIER_BITS);
    std::vector<float> out(rays.size());
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,g.outBuffer);glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,out.size()*4,out.data());
    if(program==g.query || program==g.queryUnbounded) {
        lastWork.resize(out.size());
        for(size_t i=0;i<out.size();i++){float w=std::floor(out[i]/4.0f);lastWork[i]=w;out[i]-=4.0f*w;}
    }
    return out;
}
// Real lampLighting() with one lamp record in every light-list row.
static std::vector<float> lightReceivers(Gpu& g,GLuint program,const std::vector<V3>& receivers,V3 lampRelative,int record,const float camera[3]) {
    std::vector<float> list(16*512*4,0.0f);
    auto glslMod=[](float x){return x-8.0f*std::floor(x/8.0f);};
    float gx=float(lampRelative.x)+glslMod(camera[0])+32.0f,gy=float(lampRelative.y)+glslMod(camera[1])+32.0f,gz=float(lampRelative.z)+glslMod(camera[2])+32.0f;
    for(int row=0;row<512;row++){float* r=&list[row*16*4];r[0]=1;r[4]=gx;r[5]=gy;r[6]=gz;r[7]=float(record);}
    glBindTexture(GL_TEXTURE_2D,g.lightList);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,512,GL_RGBA,GL_FLOAT,list.data());
    std::vector<Ray> rays;for(auto r:receivers) rays.push_back({r,{0,1,0},false});
    glUseProgram(program);
    setSampler(program,"aqualumenLightList",5,g.lightList);setSampler(program,"aqualumenLightField",6,g.lightField);
    return queryRays(g,program,rays,camera);
}

int main(int argc,char** argv) {
    try {
        if(argc<3) throw std::runtime_error("usage: entity_probe <release-shaders> <candidate-shaders> [--timing]");
        fs::path release=argv[1],cand=argv[2];
        bool timing=argc>3 && std::string(argv[3])=="--timing";
        auto getPlatform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        EGLDisplay display=getPlatform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto queryDevices=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
            EGLDeviceEXT devices[8];EGLint count=0;
            if(!queryDevices || !queryDevices(8,devices,&count) || count==0) throw std::runtime_error("no EGL device");
            display=getPlatform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("cannot initialise EGL");
        }
        eglBindAPI(EGL_OPENGL_API);
        EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint nc=0;eglChooseConfig(display,cfg,&config,1,&nc);
        if(!nc) throw std::runtime_error("no EGL config");
        EGLint sa[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};
        EGLSurface surface=eglCreatePbufferSurface(display,config,sa);
        EGLint ca[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        EGLContext ctx=eglCreateContext(display,config,EGL_NO_CONTEXT,ca);
        if(ctx==EGL_NO_CONTEXT || !eglMakeCurrent(display,surface,surface,ctx)) throw std::runtime_error("no GL 4.3 compatibility context");
        std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\nGL: "<<glGetString(GL_VERSION)<<"\n";
        GLint lim[4];glGetIntegerv(GL_MAX_IMAGE_UNITS,&lim[0]);glGetIntegerv(GL_MAX_GEOMETRY_IMAGE_UNIFORMS,&lim[1]);
        glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&lim[2]);glGetIntegerv(GL_MAX_COMBINED_IMAGE_UNIFORMS,&lim[3]);
        std::cout<<"Limits: image units "<<lim[0]<<", geometry image uniforms "<<lim[1]<<", fragment samplers "<<lim[2]<<", combined image uniforms "<<lim[3]<<"\n";
        int failures=0;
        auto check=[&](bool ok,const std::string& what){std::cout<<(ok?"PASS ":"FAIL ")<<what<<"\n";if(!ok)failures++;};

        // ------------------------------------------------ 1. compile sweep
        std::cout<<"\n== 1. Compile/link every program (raw GLSL, no Iris patching)\n";
        auto sweep=[&](const fs::path& root,const std::string& label,const std::function<std::string(std::string)>& edit) {
            int programs=0;
            std::vector<fs::path> files;
            for(auto& e:fs::directory_iterator(root)) if(e.path().extension()==".vsh"||e.path().extension()==".csh") files.push_back(e.path());
            std::sort(files.begin(),files.end());
            for(auto& f:files) {
                std::string name=f.filename().string();
                std::vector<GLuint> stages;
                if(f.extension()==".csh") stages.push_back(compileStage(GL_COMPUTE_SHADER,edit(expand(f,root)),label+name));
                else {
                    stages.push_back(compileStage(GL_VERTEX_SHADER,edit(expand(f,root)),label+name));
                    auto gsh=f;gsh.replace_extension(".gsh");
                    if(fs::exists(gsh)) stages.push_back(compileStage(GL_GEOMETRY_SHADER,edit(expand(gsh,root)),label+gsh.filename().string()));
                    auto fsh=f;fsh.replace_extension(".fsh");
                    stages.push_back(compileStage(GL_FRAGMENT_SHADER,edit(expand(fsh,root)),label+fsh.filename().string()));
                }
                GLuint p=linkProgram(stages,label+name,{{10,"mc_Entity"},{11,"at_midBlock"}});
                Resources r=activeResources(p);
                if(label=="candidate:" && (r.images>lim[0] || r.samplers>lim[2])) throw std::runtime_error(name+" exceeds unit limits");
                if(label=="candidate:") std::cout<<"  "<<std::left<<std::setw(26)<<f.stem().string()<<(stages.size()==3?" vsh+gsh+fsh":"")
                    <<" samplers "<<r.samplers<<" images "<<r.images<<"\n";
                glDeleteProgram(p);programs++;
            }
            return programs;
        };
        auto same=[](std::string s){return s;};
        int nRelease=sweep(release,"release:",same);
        int nCand=sweep(cand,"candidate:",same);
        check(nCand==nRelease+1,"release "+std::to_string(nRelease)+" programs, candidate "+std::to_string(nCand)+" (adds shadow_entities)");
        int nOff=sweep(cand,"candidate-off:",[](std::string s){
            size_t a=s.find("#define ENTITY_LIGHT_SHADOWS 1");if(a!=std::string::npos) s.replace(a,30,"#define ENTITY_LIGHT_SHADOWS 0");return s;});
        check(nOff==nCand,"ENTITY_LIGHT_SHADOWS=0 variant compiles ("+std::to_string(nOff)+" programs)");

        // ------------------------------------------------ GPU resources
        Gpu g;g.root=cand;
        auto vsh=[&](const fs::path& r,const char* n){return compileStage(GL_VERTEX_SHADER,expand(r/n,r),n);};
        auto fshS=[&](const fs::path& r,const char* n){return compileStage(GL_FRAGMENT_SHADER,expand(r/n,r),n);};
        g.capture=linkProgram({vsh(cand,"shadow_entities.vsh"),compileStage(GL_GEOMETRY_SHADER,expand(cand/"shadow_entities.gsh",cand),"gsh"),fshS(cand,"shadow_entities.fsh")},
                              "capture",{{10,"mc_Entity"},{11,"at_midBlock"}});
        g.baseline=linkProgram({vsh(release,"shadow.vsh"),fshS(release,"shadow.fsh")},"baseline",{{10,"mc_Entity"},{11,"at_midBlock"}});
        std::string rayMain=
            "layout(local_size_x=64) in;\n"
            "layout(std430,binding=0) readonly buffer Rays { vec4 rays[]; };\n"
            "layout(std430,binding=1) writeonly buffer Results { float results[]; };\n"
            "uniform int rayCount;\n";
        std::string occlusion=expand(cand/"lib/entity_occlusion.glsl",cand);
        std::string querySrc="#version 430 compatibility\n"+expand(cand/"lib/settings.glsl",cand)+occlusion+rayMain+
            "void main(){uint i=gl_GlobalInvocationID.x;if(i>=uint(rayCount))return;\n"
            " EntityBounds b=entityBounds();vec4 s=rays[2u*i],t=rays[2u*i+1u];int work=entityWorkBudget;\n"
            " float v=entityTransmission(b,s.xyz,t.xyz,s.w>0.5,work);results[i]=v+4.0*float(entityWorkBudget-work);}\n";
        g.query=linkProgram({compileStage(GL_COMPUTE_SHADER,querySrc,"query")},"query");
        g.queryUnbounded=linkProgram({compileStage(GL_COMPUTE_SHADER,replaceAll(replaceAll(querySrc,"const int entityMaxTests=160;","const int entityMaxTests=1000000;"),
            "const int entityWorkBudget=512;","const int entityWorkBudget=1000000;"),"query-unbounded")},"query-unbounded");
        auto lightingSrc=[&](int samples){
            std::string s="#version 430 compatibility\n"+expand(cand/"lib/settings.glsl",cand)+expand(cand/"lib/uniforms.glsl",cand)+
                expand(cand/"lib/local_lighting.glsl",cand)+rayMain+
                "void main(){uint i=gl_GlobalInvocationID.x;if(i>=uint(rayCount))return;\n"
                " results[i]=lampLighting(rays[2u*i].xyz,vec3(0,1,0),vec3(0),0.0,0.0,false).r;}\n";
            if(samples==1) s=replaceAll(s,"#define LOCAL_LIGHT_SAMPLES 3","#define LOCAL_LIGHT_SAMPLES 1");
            return s;
        };
        GLuint noSphere=linkProgram({compileStage(GL_COMPUTE_SHADER,replaceAll(querySrc,"if(dot(off,off)>radius*radius) continue;","")," query-nosphere")},"query-nosphere");
        g.lighting3=linkProgram({compileStage(GL_COMPUTE_SHADER,lightingSrc(3),"lighting3")},"lighting3");
        g.lighting1=linkProgram({compileStage(GL_COMPUTE_SHADER,lightingSrc(1),"lighting1")},"lighting1");

        g.meta=makeTex(GL_R32UI,512,1);g.heads=makeTex(GL_R32UI,1024,864);
        g.nodes=makeTex(GL_RGBA32UI,1024,256);g.tris=makeTex(GL_RGBA32UI,1024,96);g.shore=makeTex(GL_R32UI,2336,768);
        // Stale garbage in the never-cleared record images must be harmless.
        {std::vector<uint32_t> junk(1024*256*4,0xA5A5A5A5u);glBindTexture(GL_TEXTURE_2D,g.nodes);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1024,256,GL_RGBA_INTEGER,GL_UNSIGNED_INT,junk.data());}
        g.lightList=makeTex(GL_RGBA32F,16,512);g.lightField=makeTex(GL_R32F,512,512);
        {std::vector<float> z(512*512,0.0f);glBindTexture(GL_TEXTURE_2D,g.lightField);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,512,GL_RED,GL_FLOAT,z.data());}
        {
            std::vector<uint8_t> px(atlasSize*atlasSize*4);
            for(int y=0;y<atlasSize;y++)for(int x=0;x<atlasSize;x++){uint8_t* p=&px[(y*atlasSize+x)*4];p[0]=uint8_t(60+5*x);p[1]=uint8_t(90+3*y);p[2]=70;p[3]=atlasAlpha(x,y);}
            g.atlas=makeTex(GL_RGBA8,atlasSize,atlasSize);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,atlasSize,atlasSize,GL_RGBA,GL_UNSIGNED_BYTE,px.data());
        }
        g.color0=makeTex(GL_RGBA32F,g.fboSize,g.fboSize);g.color1=makeTex(GL_RGBA32F,g.fboSize,g.fboSize);g.depth=makeTex(GL_DEPTH_COMPONENT32F,g.fboSize,g.fboSize);
        glGenFramebuffers(1,&g.fbo);glBindFramebuffer(GL_FRAMEBUFFER,g.fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,g.color0,0);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT1,GL_TEXTURE_2D,g.color1,0);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,g.depth,0);
        GLenum bufs[2]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,bufs);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("fbo incomplete");
        glGenBuffers(1,&g.vbo);glGenBuffers(1,&g.rayBuffer);glGenBuffers(1,&g.outBuffer);
        float camera[3]={1203.37f,71.62f,-388.91f};

        // ------------------------------------------------ 2. shadow targets unchanged
        std::cout<<"\n== 2. Solar shadow pass / shadowcolor attachments: release fallback 'shadow' vs candidate 'shadow_entities'\n";
        Mesh crowd;
        for(int i=0;i<6;i++) crowd.append(humanoid({-6.0+2.3*i,0,1.5*std::sin(i)},0.4*i,0.5*std::sin(1.3*i)));
        crowd.append(cutoutPanel({0,1.2,-3},0.3));
        auto readTargets=[&](){
            std::vector<float> all(size_t(g.fboSize)*g.fboSize*9);
            glBindTexture(GL_TEXTURE_2D,g.color0);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,all.data());
            glBindTexture(GL_TEXTURE_2D,g.color1);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,all.data()+size_t(g.fboSize)*g.fboSize*4);
            glBindTexture(GL_TEXTURE_2D,g.depth);glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT,all.data()+size_t(g.fboSize)*g.fboSize*8);
            return all;
        };
        clearTargets(g);irisFrameClear(g);drawShadow(g,g.baseline,crowd,21000,camera);auto base=readTargets();
        clearTargets(g);irisFrameClear(g);drawShadow(g,g.capture,crowd,21000,camera);auto cand2=readTargets();
        size_t diff=0,covered=0;
        for(size_t i=0;i<base.size();i++) if(std::memcmp(&base[i],&cand2[i],4)!=0) diff++;
        for(size_t i=0;i<size_t(g.fboSize)*g.fboSize;i++) if(base[size_t(g.fboSize)*g.fboSize*8+i]<1.0f) covered++;
        check(diff==0 && covered>1000,"depth + shadowcolor0 + shadowcolor1 bit-identical over "+std::to_string(covered)+" covered texels ("+std::to_string(diff)+" differing words)");
        clearTargets(g);irisFrameClear(g);drawShadow(g,g.capture,crowd,-1,camera);auto unlisted=readTargets();
        diff=0;for(size_t i=0;i<base.size();i++) if(std::memcmp(&base[i],&unlisted[i],4)!=0) diff++;
        check(diff==0,"filtered (unlisted) entities still rasterise identically into the solar shadow targets");

        // ------------------------------------------------ 3. filtering
        std::cout<<"\n== 3. Material/entity filtering (Iris ids from entity.properties)\n";
        Mesh one=humanoid({0,0,0},0,0);
        for(int id:{-1,0,21002}) {
            irisFrameClear(g);drawShadow(g,g.capture,one,id,camera);auto m=readMeta(g);
            check(m[0]==0 && m[10]==one.t.size(),"entityId "+std::to_string(id)+" (unlisted / non-entity draw / name tag, projectile, beacon...) stores 0 triangles, rejects "+std::to_string(m[10]));
        }
        {
            Mesh ghost=one;for(auto& v:ghost.v) v.c[3]=0.05f;
            irisFrameClear(g);drawShadow(g,g.capture,ghost,21000,camera);auto m=readMeta(g);
            check(m[0]==0,"vertex alpha 0.05 (invisible rendering) stores 0 triangles");
        }
        irisFrameClear(g);drawShadow(g,g.capture,one,21000,camera);
        {auto m=readMeta(g);check(m[0]==one.t.size() && m[2]==0,"caster id stores all "+std::to_string(m[0])+" triangles, "+std::to_string(m[1])+" cell nodes, overflow "+std::to_string(m[2]));}

        // ------------------------------------------------ 4. exactness vs CPU
        std::cout<<"\n== 4. GPU any-hit vs double-precision CPU oracle on the same triangles\n";
        std::mt19937 rng(21);
        std::uniform_real_distribution<double> U(0,1);
        auto randomRays=[&](int n,V3 lo,V3 hi,double maxLen,bool axisAligned){
            std::vector<Ray> r;
            for(int i=0;i<n;i++){
                V3 s={lo.x+(hi.x-lo.x)*U(rng),lo.y+(hi.y-lo.y)*U(rng),lo.z+(hi.z-lo.z)*U(rng)};
                V3 d;
                if(axisAligned){int a=i%3;double l=(U(rng)*2-1)*maxLen;d={a==0?l:0,a==1?l:0,a==2?l:0};}
                else{do d={U(rng)*2-1,U(rng)*2-1,U(rng)*2-1};while(len(d)>1||len(d)<0.05);d=d*(maxLen/len(d)*U(rng));}
                r.push_back({s,s+d,(i&7)==0});
            }
            return r;
        };
        struct Score { size_t n=0,gpuHits=0,latticeMismatch=0,exactMismatch=0,budget=0; };
        auto score=[&](const Mesh& m,const std::vector<bool>& self,const std::vector<Ray>& rays){
            Score s;s.n=rays.size();
            auto gpu=queryRays(g,g.query,rays,camera);
            auto unb=queryRays(g,g.queryUnbounded,rays,camera);
            for(size_t i=0;i<rays.size();i++){
                Oracle o=oracle(m.t,rays[i].s,rays[i].t,rays[i].carried,self);
                bool hit=unb[i]<0.5f;
                if(gpu[i]<0.5f) s.gpuHits++;
                if(hit!=o.lattice) s.latticeMismatch++;
                if(hit!=o.exact) s.exactMismatch++;
                if((gpu[i]<0.5f)!=hit) s.budget++;
            }
            return s;
        };
        Mesh scene;
        for(int i=0;i<10;i++) scene.append(humanoid({-7.0+1.6*i,-1.0+0.3*i,2.0*std::cos(0.7*i)},0.9*i,0.6*std::sin(2.1*i)));
        for(int i=0;i<4;i++) scene.append(cutoutPanel({-3.0+2.0*i,0.5,-2.5},0.7*i));
        std::vector<bool> noSelf(scene.t.size(),false);
        irisFrameClear(g);drawShadow(g,g.capture,scene,21000,camera);
        {
            auto m=readMeta(g);
            std::cout<<"  scene: "<<scene.t.size()<<" triangles submitted, "<<m[0]<<" stored, "<<m[1]<<" cell nodes, overflow "<<m[2]<<"\n";
            auto r1=randomRays(30000,{-9,-1.5,-4},{9,3.5,4},14,false);
            auto r2=randomRays(6000,{-9,-1.5,-4},{9,3.5,4},10,true);
            auto r3=randomRays(4000,{-22,-20,-22},{22,20,22},14,false);
            r1.insert(r1.end(),r2.begin(),r2.end());r1.insert(r1.end(),r3.begin(),r3.end());
            Score s=score(scene,noSelf,r1);
            std::cout<<"  "<<s.n<<" segments (incl. 6000 axis-aligned, 4000 grid-wide), GPU blocked "<<s.gpuHits<<"\n";
            check(s.latticeMismatch<=s.n/5000,"GPU (unbounded budget) vs CPU with the same 8x8 alpha lattice: "+std::to_string(s.latticeMismatch)+" mismatches");
            std::cout<<"  INFO vs exact per-texel alpha: "<<s.exactMismatch<<" mismatches ("<<std::fixed<<std::setprecision(3)<<100.0*s.exactMismatch/s.n<<"%), lattice approximation of cut-outs\n";
            check(s.budget==0,"160-test budget changed "+std::to_string(s.budget)+" results in this scene");
        }

        {
            // Large animated geometry (ghast/dragon scale) and a long oblique sheet.
            Mesh big;
            addBox(big,{-2,-2,-2},{2,2,2},[](V3 p){return rotY(rotX(p,0.5),0.7)+V3{4,6,-5};},opaqueRect);
            big.quad({V3{-10,-3,-8},V3{-10,9,4},V3{9,7,6},V3{9,-5,-6}},{{{0,0},{0,1},{0.5,1},{0.5,0}}});
            std::vector<bool> none(big.t.size(),false);
            irisFrameClear(g);drawShadow(g,g.capture,big,21000,camera);
            auto m=readMeta(g);
            auto rays=randomRays(20000,{-14,-8,-14},{14,14,14},14,false);
            Score s=score(big,none,rays);
            check(m[2]==0 && s.latticeMismatch<=4 && s.budget==0,"4 m cube + 22 m oblique sheet: "+std::to_string(m[1])+" nodes, overflow "+std::to_string(m[2])
                  +", "+std::to_string(s.latticeMismatch)+" oracle mismatches over "+std::to_string(s.n)+" segments ("+std::to_string(s.gpuHits)+" blocked)");
        }

        // ------------------------------------------------ 5. targeted cases
        std::cout<<"\n== 5. Between / beside / behind receiver / beyond lamp / cutout / self\n";
        {
            Mesh mob=humanoid({0,0,0},0,0);
            irisFrameClear(g);drawShadow(g,g.capture,mob,21000,camera);
            std::vector<Ray> r={
                {{-3,1.1,0},{3,1.1,0},false},   // through the torso
                {{-3,1.1,1.2},{3,1.1,1.2},false}, // beside
                {{0.4,1.1,0},{3,1.1,0},false},  // receiver just right of torso, lamp further right: caster behind receiver
                {{-3,1.1,0},{-0.4,1.1,0},false},// lamp in front of the mob: caster beyond lamp
                {{-3,1.1,0},{3,1.1,0},true},    // held light, not the holder: still blocked
                {{-3,1.1,0},{-0.37,1.1,0},false},// lamp 0.12 m before the surface: still lit
            };
            auto o=queryRays(g,g.query,r,camera);
            check(o[0]==0,"caster between receiver and lamp blocks");
            check(o[1]==1,"segment beside the caster is lit");
            check(o[2]==1,"caster behind the receiver is ignored");
            check(o[3]==1,"caster beyond the lamp is ignored");
            check(o[4]==0,"another entity blocks a held light");
            check(o[5]==1,"segment ending 0.12 m before the caster is lit");
        }
        {
            Mesh panel=cutoutPanel({0,1,0},0);
            irisFrameClear(g);drawShadow(g,g.capture,panel,21000,camera);
            // Panel x in [-0.5,0.5] maps to texels 16..24; hole texel lx=2..5 at
            // pins where (lx/2+ly/2) odd: lx=2,3 ly=4,5 -> x=-0.25..0, uv v=0..0.25 top->bottom.
            std::vector<Ray> r={{{-0.125,0.875,-2},{-0.125,0.875,2},false},
                                {{-0.45,1.0,-2},{-0.45,1.0,2},false}};
            // Compute through CPU so the expectation is texel-exact.
            Oracle a=oracle(panel.t,r[0].s,r[0].t,false,std::vector<bool>(panel.t.size(),false));
            Oracle b=oracle(panel.t,r[1].s,r[1].t,false,std::vector<bool>(panel.t.size(),false));
            auto o=queryRays(g,g.query,r,camera);
            check(!a.exact && o[0]==1,"ray through a transparent cut-out texel is lit");
            check(b.exact && o[1]==0,"ray through the opaque border is blocked");
            // Dense scan of the 8x8-texel cut-out: lattice error vs per-texel truth.
            std::vector<Ray> scan;std::vector<bool> none(panel.t.size(),false);
            for(int y=0;y<128;y++)for(int x=0;x<128;x++){double px=-0.5+(x+0.5)/128,py=0.5+(y+0.5)/128;scan.push_back({{px,py,-2},{px+0.3,py-0.2,2},false});}
            auto so=queryRays(g,g.query,scan,camera);
            size_t wrongExact=0,wrongLattice=0,open=0;
            for(size_t i=0;i<scan.size();i++){Oracle q=oracle(panel.t,scan[i].s,scan[i].t,false,none);bool hit=so[i]<0.5f;
                if(!q.exact)open++;if(hit!=q.exact)wrongExact++;if(hit!=q.lattice)wrongLattice++;}
            check(wrongLattice==0,"dense 128x128 cut-out scan matches the lattice oracle exactly");
            std::cout<<"  INFO cut-out scan: "<<open<<" of "<<scan.size()<<" rays pass transparent texels; GPU differs from per-texel truth on "
                     <<wrongExact<<" ("<<std::setprecision(2)<<std::fixed<<100.0*wrongExact/scan.size()<<"%)\n";
            // Worst case: 1-texel checker, 16 texels per triangle leg (2 texels per lattice step).
            Mesh fine;
            {auto f=[&](double x,double y){return V3{x,y+1.0,0};};
             fine.quad({f(-0.5,-0.5),f(-0.5,0.5),f(0.5,0.5),f(0.5,-0.5)},{{{0.5,0.75},{0.5,0.25},{1.0,0.25},{1.0,0.75}}});}
            irisFrameClear(g);drawShadow(g,g.capture,fine,21000,camera);
            auto fo=queryRays(g,g.query,scan,camera);
            size_t fineExact=0,fineLattice=0;std::vector<bool> none2(fine.t.size(),false);
            for(size_t i=0;i<scan.size();i++){Oracle q=oracle(fine.t,scan[i].s,scan[i].t,false,none2);bool hit=fo[i]<0.5f;
                if(hit!=q.exact)fineExact++;if(hit!=q.lattice)fineLattice++;}
            check(fineLattice==0,"1-texel checker panel matches the lattice oracle");
            std::cout<<"  INFO worst case (1-texel checker, 16 texels per triangle leg): GPU differs from per-texel truth on "<<fineExact
                     <<" of "<<scan.size()<<" ("<<100.0*fineExact/scan.size()<<"%); finer alpha detail than 8 lattice steps per edge is not resolved\n";
        }
        {
            Mesh self=humanoid({0,-1.62,0},0.2,0.3),other=humanoid({3,-1.62,0},0,0);
            irisFrameClear(g);
            drawShadow(g,g.capture,self,21001,camera);drawShadow(g,g.capture,other,21000,camera);
            auto m=readMeta(g);
            std::vector<Ray> r={{{0,-0.5,-2},{0,-0.5,2},true},{{0,-0.5,-2},{0,-0.5,2},false},{{3,-0.5,-2},{3,-0.5,2},true}};
            auto o=queryRays(g,g.query,r,camera);
            check(m[9]==self.t.size(),"current_player triangles flagged self ("+std::to_string(m[9])+")");
            check(o[0]==1,"holder's own body never shadows its held light");
            check(o[1]==0,"holder's body does shadow placed lamps");
            check(o[2]==0,"other players/mobs shadow the held light");
        }

        // ------------------------------------------------ 6. temporal: move, despawn, recentre
        std::cout<<"\n== 6. Crossing a lamp ray over frames; despawn; camera recentre (no ghosts)\n";
        {
            V3 receiver={0,0.02,0},lamp={0,2.6,6};
            int frames=24,transitions=0,errors=0;float prev=-1;
            std::string trace;
            for(int f=0;f<frames;f++){
                double x=-2.0+4.0*f/(frames-1);
                Mesh mob=humanoid({x,0,3},1.5708,0.8*std::sin(f*0.9));
                irisFrameClear(g);drawShadow(g,g.capture,mob,21000,camera);
                auto o=queryRays(g,g.query,{{receiver,lamp,false}},camera);
                Oracle orc=oracle(mob.t,receiver,lamp,false,std::vector<bool>(mob.t.size(),false));
                if(orc.lattice!=(o[0]<0.5f)) errors++;
                if(prev>=0 && prev!=o[0]) transitions++;
                prev=o[0];trace+=o[0]<0.5f?'#':'.';
            }
            std::cout<<"  frame trace (# shadowed): "<<trace<<"\n";
            check(errors==0 && transitions>=2,"walking mob enters and leaves the lamp ray, every frame matches the oracle");
            irisFrameClear(g);
            auto o=queryRays(g,g.query,{{receiver,lamp,false}},camera);
            auto m=readMeta(g);
            check(o[0]==1 && m[0]==0,"despawn: next frame without the draw has no caster (record images not cleared, heads are)");
            // Recentre: world-fixed mob, camera moves 5.3 m; relative coords shift.
            V3 worldMob={1205.0,71.0,-386.0};
            float cam2[3]={camera[0]+5.3f,camera[1],camera[2]-2.1f};
            auto rel=[&](V3 w,const float* c){return V3{w.x-c[0],w.y-c[1],w.z-c[2]};};
            Mesh a=humanoid(rel(worldMob,camera),0,0);
            irisFrameClear(g);drawShadow(g,g.capture,a,21000,camera);
            Ray before={rel({1205.0,72.1,-390.0},camera),rel({1205.0,72.1,-382.0},camera),false};
            auto ob=queryRays(g,g.query,{before},camera);
            Mesh b=humanoid(rel(worldMob,cam2),0,0);
            irisFrameClear(g);drawShadow(g,g.capture,b,21000,cam2);
            Ray after={rel({1205.0,72.1,-390.0},cam2),rel({1205.0,72.1,-382.0},cam2),false};
            Ray oldPlace=before; // same relative coords as last frame, now empty space
            auto oa=queryRays(g,g.query,{after,oldPlace},cam2);
            check(ob[0]==0 && oa[0]==0,"after a 5.7 m camera move the world-fixed mob still blocks the world-fixed ray");
            check(oa[1]==1,"previous frame's camera-relative location is empty (no recentre ghost)");
        }

        // ------------------------------------------------ 7. soft shadow via lampLighting
        std::cout<<"\n== 7. Real lampLighting(): glowstone (radius 0.42) above a mob, floor receivers\n";
        {
            Mesh mob=humanoid({0,0,0},0,0);
            V3 lamp={0,3.4,0};
            std::vector<V3> recv;for(int i=0;i<=24;i++) recv.push_back({-1.2+0.1*i,-0.97,0.0});
            // receivers just above a floor at y=-1 relative to the mob's feet plane shifted:
            Mesh lifted=humanoid({0,-0.6,0},0,0);
            for(int pass=0;pass<2;pass++){
                irisFrameClear(g);if(pass==1) drawShadow(g,g.capture,lifted,21000,camera);
                auto l3=lightReceivers(g,g.lighting3,recv,lamp,15*64+15,camera);
                auto l1=lightReceivers(g,g.lighting1,recv,lamp,15*64+15,camera);
                if(pass==0){std::cout<<"  x:      ";for(auto& r:recv) std::cout<<std::setw(5)<<std::setprecision(1)<<std::fixed<<r.x;std::cout<<"\n";}
                std::cout<<(pass==0?"  no mob 3:":"  mob   3:");
                for(auto v:l3) std::cout<<std::setw(5)<<std::setprecision(2)<<v;std::cout<<"\n";
                std::cout<<(pass==0?"  no mob 1:":"  mob   1:");
                for(auto v:l1) std::cout<<std::setw(5)<<std::setprecision(2)<<v;std::cout<<"\n";
                static std::vector<float> empty3;
                if(pass==0) empty3=l3;
                else {
                    std::set<int> levels;bool bounded=true;
                    for(size_t i=0;i<l3.size();i++){float ratio=l3[i]/std::max(empty3[i],1e-6f);
                        levels.insert(int(std::lround(ratio*3)));if(std::abs(ratio*3-std::lround(ratio*3))>0.02) bounded=false;}
                    check(bounded && levels.count(0) && levels.count(3) && (levels.count(1)||levels.count(2)),
                          "3-sample emitter disk gives umbra, penumbra steps of 1/3 and lit floor");
                }
            }
            irisFrameClear(g);drawShadow(g,g.capture,lifted,21001,camera);
            auto held=lightReceivers(g,g.lighting3,recv,lamp,1024+15*64+15,camera);
            auto placed=lightReceivers(g,g.lighting3,recv,lamp,15*64+15,camera);
            check(held[12]>0.0f && placed[12]==0.0f,"self caster: held record lit under the body, placed record shadowed");
        }

        // ------------------------------------------------ 8. timing (opt-in, short)
        if(timing) {
            std::cout<<"\n== 8. GPU harness timing (not Minecraft frame time; other GPU work may be running)\n";
            Mesh herd;
            for(int i=0;i<64;i++) herd.append(humanoid({-12.0+3.0*(i%8),0,-12.0+3.0*(i/8)},0.37*i,0.5*std::sin(i)));
            double bestBase=1e9,bestCap=1e9;
            for(int k=0;k<3;k++){
                clearTargets(g);irisFrameClear(g);bestBase=std::min(bestBase,drawShadow(g,g.baseline,herd,21000,camera,true));
                clearTargets(g);irisFrameClear(g);bestCap=std::min(bestCap,drawShadow(g,g.capture,herd,21000,camera,true));
            }
            auto m=readMeta(g);
            std::cout<<"  64 humanoids, "<<herd.t.size()<<" tris: shadow draw baseline "<<std::setprecision(3)<<bestBase
                     <<" ms, with GS capture "<<bestCap<<" ms; stored "<<m[0]<<" tris, "<<m[1]<<" nodes, overflow "<<m[2]<<"\n";
            std::vector<Ray> rays;rays.reserve(1<<20);
            std::uniform_real_distribution<double> X(-14,14),Z(-14,14);
            for(int i=0;i<(1<<20);i++){V3 s={X(rng),0.02,Z(rng)};V3 t={X(rng)*0.5,3.0,Z(rng)*0.5};
                if(len(t-s)>13.5) t=s+(t-s)*(13.5/len(t-s));rays.push_back({s,t,false});}
            double full=1e9,empty=1e9;
            double fullNoSphere=1e9;
            for(int k=0;k<5;k++){double ms;
                queryRays(g,noSphere,rays,camera,&ms);fullNoSphere=std::min(fullNoSphere,ms);
                queryRays(g,g.query,rays,camera,&ms);full=std::min(full,ms);}
            std::cout<<"  interleaved A/B (min of 5): without sphere reject "<<fullNoSphere<<" ms, candidate "<<full<<" ms\n";
            {double sum=0,mx=0;size_t capped=0;for(float w:lastWork){sum+=w;mx=std::max(mx,double(w));if(w>=511)capped++;}
             std::cout<<"  herd work units per segment: mean "<<std::setprecision(1)<<sum/lastWork.size()<<", max "<<mx<<", budget-capped "<<capped<<"\n";
             std::cout<<std::setprecision(3);}
            irisFrameClear(g);
            for(int k=0;k<3;k++){double ms;queryRays(g,g.query,rays,camera,&ms);empty=std::min(empty,ms);}
            std::cout<<"  1,048,576 floor->lamp segments through the herd: "<<full<<" ms; same segments, empty frame: "<<empty<<" ms\n";
            // Typical: two mobs at opposite grid corners make the global bounds
            // span the grid, while the shaded segments cross only empty bricks.
            Mesh sparse=humanoid({-20,-1,-20},0,0);sparse.append(humanoid({20,1,20},1,0.3));
            irisFrameClear(g);drawShadow(g,g.capture,sparse,21000,camera);
            double sp=1e9;for(int k=0;k<3;k++){double ms;queryRays(g,g.query,rays,camera,&ms);sp=std::min(sp,ms);}
            double sum=0;for(float w:lastWork)sum+=w;
            std::cout<<"  same segments, two distant mobs (bounds span the grid): "<<sp<<" ms, mean "<<std::setprecision(1)<<sum/lastWork.size()<<" work units\n"<<std::setprecision(3);
        }

        std::cout<<"\n"<<(failures==0?"ALL PASS":"FAILURES: "+std::to_string(failures))<<"\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,ctx);eglDestroySurface(display,surface);eglTerminate(display);
        return failures==0?0:1;
    } catch(const std::exception& e) {
        std::cerr<<"ERROR: "<<e.what()<<"\n";return 2;
    }
}
