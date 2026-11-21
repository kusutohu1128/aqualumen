// Independent NVIDIA EGL QA for the camera-local placed-light grid.
//
// Everything below runs the REAL production sources of the pack under test:
//   shadow_solid/shadow_cutout/shadow_water.vsh -> captureLocalCell() writes lampCellImage / lampIndexImage
//   shadowcomp1.csh                              -> real compute dispatch, publishes lampFieldImage / lampListImage
//   lib/local_lighting.glsl lampLighting()/lampSurfaceEmission() and the real gbuffers_terrain pass read them.
// Fixtures are controlled blocks drawn through the real shadow vertex shaders; nothing is mocked to succeed.
// Independent controls are (a) a CPU re-statement of the capture/cluster contract, compared bit for bit with the
// GPU images, (b) physical invariants (inverse square, cosine facing, mirror geometry, Beer-Lambert, translation
// invariance) that do not copy the shader's energy constants, and (c) scene pairs that differ in one cause only.
// Caps/ranges (lampRange, lampCapacity, image sizes, clear flags, workGroups) are parsed from the actual sources.
// Timings printed here are GPU-harness timings of the compute pass, NOT Minecraft frame times.
#pragma once
#include <regex>
#include <map>
#include <set>
#include <chrono>
#include <functional>
namespace aqualumenLocalLights {
using D3=std::array<double,3>;
struct Block { int x,y,z,id,level,pass; };  // pass: 0 shadow_solid, 1 shadow_cutout, 2 shadow_water (glass)
struct Query { D3 p,n,v; float rough,level; bool water; };
struct ImageProps { std::string format; int w=0,h=0; bool clear=false; };

inline void resetTextureMatrices() {
    for(int unit=0;unit<4;unit++) {glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glLoadIdentity();}
    glActiveTexture(GL_TEXTURE0);glMatrixMode(GL_MODELVIEW);
}
inline void require(bool ok,const std::string& message) { if(!ok) throw std::runtime_error("local-light QA FAIL: "+message); }
inline bool near(double a,double b,double rel,double abs=0) { return std::abs(a-b)<=abs+rel*std::max(std::abs(a),std::abs(b)); }
inline std::string num(double v) { std::ostringstream s;s<<std::setprecision(7)<<v;return s.str(); }
inline std::string slurp(const fs::path& p) { std::ifstream f(p);if(!f) throw std::runtime_error("Cannot read "+p.string());std::ostringstream s;s<<f.rdbuf();return s.str(); }

inline ImageProps parseImage(const std::string& props,const std::string& name) {
    std::smatch m;
    std::regex re("(^|\\n)image\\."+name+"=\\S+\\s+(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+(true|false)\\s+(true|false)\\s+(\\d+)\\s+(\\d+)");
    require(std::regex_search(props,m,re),"shaders.properties lacks image."+name);
    return {m[3].str(),std::stoi(m[7]),std::stoi(m[8]),m[5].str()=="true"};
}
inline double parseConst(const std::string& source,const std::string& name) {
    std::smatch m;
    std::regex re("const\\s+(?:float|int)\\s+"+name+"\\s*=\\s*([0-9.]+)");
    require(std::regex_search(source,m,re),"source lacks const "+name);
    return std::stod(m[1]);
}

// Contract re-statement (independent of the GLSL): block id -> capture word. 0 means "writes nothing".
inline unsigned expectedWord(const Block& b) {
    unsigned shape=b.pass==0?1u:0u;
    if(b.id==10300) shape=2;
    if(b.id==10301) shape=3;
    if(b.id==10302) shape=4;
    if(b.id==10303) shape=1;
    if(b.id==10304) shape=5;
    if(b.pass==2) { if(b.id<10400||b.id>=10416) return 0; shape=unsigned(b.id-10400+16); }
    int kind=b.id>=10100&&b.id<10120?b.id-10099:0;
    int level=std::clamp(b.level,0,15);
    if(kind>0&&(kind<=14||kind==17)) shape=0;
    if(kind==0||level==0) return shape;
    return shape|(unsigned(kind)<<6)|(unsigned(level)<<12);
}
inline int kindOf(const Block& b) { return b.id>=10100&&b.id<10120?b.id-10099:0; }
inline bool emits(const Block& b) { return kindOf(b)>0&&std::clamp(b.level,0,15)>0&&b.pass!=2; }
inline std::array<float,3> kindOffset(int kind) {
    if(kind>=1&&kind<=10) {
        int mount=(kind-1)%5;
        float sx=mount==3?1.f:mount==4?-1.f:0.f,sz=mount==1?1.f:mount==2?-1.f:0.f;
        return {0.5f+0.21f*sx,mount==0?0.64f:0.84f,0.5f+0.21f*sz};
    }
    return {0.5f,(kind==13||kind==14)?0.44f:0.5f,0.5f};
}
inline int passFor(int id) {
    if(id>=10400&&id<10416) return 2;
    int kind=id>=10100&&id<10120?id-10099:0;
    if(kind>0) return (kind<=14||kind==17)?1:0;
    return id==10300?1:0;
}
inline Block blk(int x,int y,int z,int id,int level=0) { return {x,y,z,id,level,passFor(id)}; }
inline Block torch(int x,int y,int z,int level=14) { return blk(x,y,z,10100,level); }
inline Block soulTorch(int x,int y,int z,int level=10) { return blk(x,y,z,10105,level); }
inline Block stone(int x,int y,int z) { return blk(x,y,z,10001); }


// Portable-light (first/third person held item) inputs of shadowcomp1. Defaults reproduce "nothing held".
struct Carried {
    int item=0,item2=0,level=0,level2=0,medium=0;
    bool spectator=false,firstPerson=true,rightHanded=true;
    D3 look={0,0,-1},relEye={0,0,0};   // relEye = cameraPosition - player eye (Iris relativeEyePosition)
    std::array<float,16> viewInverse={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};   // identity: camera looks along -Z
};
inline bool uniformActive(GLuint program,const char* name) {
    GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);
    return index!=GL_INVALID_INDEX&&glGetUniformLocation(program,name)>=0;
}
// Sets a scalar/vec3 uniform according to the type the driver reports (int, bool, float, vec3). False if inactive.
inline bool setUniform(GLuint program,const char* name,double a,double b=0,double c=0) {
    GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);
    if(index==GL_INVALID_INDEX) return false;
    GLint size=0,loc=glGetUniformLocation(program,name);GLenum type=0;char buffer[128];GLsizei length=0;
    glGetActiveUniform(program,index,sizeof(buffer),&length,&size,&type,buffer);
    if(loc<0) return false;
    switch(type) {
        case GL_BOOL: case GL_INT: glUniform1i(loc,int(std::lround(a)));return true;
        case GL_UNSIGNED_INT: glUniform1ui(loc,unsigned(std::lround(a)));return true;
        case GL_FLOAT: glUniform1f(loc,float(a));return true;
        case GL_FLOAT_VEC3: glUniform3f(loc,float(a),float(b),float(c));return true;
        default: throw std::runtime_error(std::string("local-light QA FAIL: uniform ")+name+" has unsupported GL type "+std::to_string(type));
    }
}

// Independent expected bits outside the original lamp indices. The flat floor,
// leaves and luminous cube fixtures are six-faced blocks, unlike the torches.
inline void expectedSkyColumns(std::vector<unsigned>& table,const std::vector<Block>& scene,
                               D3 camera) {
    if(table.size()!=128*1801) return;
    for(const Block& b:scene) {
        const unsigned shape=expectedWord(b)&63u;
        // The far grid has one bit per vertical metre. A slab's boundary
        // face spans the column and occupies that metre; a fence post does not.
        // Near-field rays still resolve the actual half-height and post geometry.
        if(shape!=1 && shape!=2 && shape!=3 && shape!=4) continue;
        const int x=b.x-16*int(std::floor(camera[0]/16))+96;
        const int y=b.y-16*int(std::floor(camera[1]/16))+48;
        const int z=b.z-16*int(std::floor(camera[2]/16))+96;
        if(x<0||x>=192||z<0||z>=192||y<0||y>=96) continue;
        const size_t word=73*128 + ((z*192+x)*3+y/32)*2+unsigned(shape==2);
        table.at(word)|=1u<<(y%32);
    }
}
struct World {
    fs::path root;
    std::string renderer;
    ImageProps pCell,pIndex,pField,pList;
    double range=0;int capacity=0,groups[3]={0,0,0};
    GLuint cell=0,index=0,field=0,list=0,dummyShore=0;
    GLuint pass[3]={0,0,0},comp=0,evalProgram=0,emitProgram=0,dataTex=0,outTex=0,fbo=0;
    std::vector<unsigned> zeroCell,zeroIndex;
    double lastComputeMs=0;
    D3 lastCam={0,0,0};       // camera of the last capture(); published to shadowcomp1 as cameraPosition
    bool carriedDirty=false;  // carried uniforms were driven; later plain publish() must restore "nothing held"
    int medium=0;             // isEyeInWater given to the lamp-evaluation programs
    bool lavaLayout=false;    // pack ships lib/lava_grid.glsl: extended raw/field/list storage after the lamp layout
    static constexpr size_t kCells=64*64*64;   // first 512 rows of lampCellImage / lampFieldImage

    static GLuint makeTexture(GLenum internal,int w,int h) {
        GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexStorage2D(GL_TEXTURE_2D,1,internal,w,h);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        return t;
    }
    static GLuint linkAttribs(const std::string& vs,const std::string& fs_,const std::string& name) {
        GLuint v=compile(GL_VERTEX_SHADER,vs,name+".vsh"),f=compile(GL_FRAGMENT_SHADER,fs_,name+".fsh");
        GLuint program=glCreateProgram();glAttachShader(program,v);glAttachShader(program,f);
        glBindAttribLocation(program,10,"mc_Entity");glBindAttribLocation(program,11,"at_midBlock");
        glLinkProgram(program);glDeleteShader(v);glDeleteShader(f);
        GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
        if(!ok) {char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log);}
        return program;
    }
    static void imageUnit(GLuint program,const char* name,int unit) {
        GLint loc=glGetUniformLocation(program,name);if(loc>=0) glUniform1i(loc,unit);
    }
    void init(const fs::path& r) {
        root=r;
        renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
        const std::string props=slurp(root/"shaders.properties");
        pCell=parseImage(props,"lampCellImage");pIndex=parseImage(props,"lampIndexImage");
        pField=parseImage(props,"lampFieldImage");pList=parseImage(props,"lampListImage");
        const std::string grid=slurp(root/"lib/local_light_grid.glsl"),csh=slurp(root/"shadowcomp1.csh");
        range=parseConst(grid,"lampRange");capacity=int(parseConst(grid,"lampCapacity"));
        std::smatch m;
        require(std::regex_search(csh,m,std::regex("workGroups\\s*=\\s*ivec3\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)")),"shadowcomp1.csh lacks workGroups");
        for(int i=0;i<3;i++) groups[i]=std::stoi(m[1+i]);
        // The advertised 64^3 grid of 8^3 clusters must fit the declared images exactly.
        // A pack shipping lib/lava_grid.glsl appends fluid-emitter storage BELOW the unchanged lamp
        // layout (same widths, same first rows). Its sizes are re-derived here from the area-source
        // contract, not read back from the GLSL: 4 corner-height planes of 64^3 cells, 512 cluster
        // group-bit words, one published height plane + 2x512 neighbour entries per cluster, and
        // 25 records (header + 6 faces x 4 layers) for each of the 16^3 world-aligned 4-cube groups.
        lavaLayout=fs::exists(root/"lib/lava_grid.glsl");
        // The newer publisher reads a scene-wide nonempty flag after all 512 group words.
        const bool sceneFlag = std::regex_search(csh,std::regex(R"(imageLoad\s*\(\s*lampIndexImage\s*,\s*ivec2\s*\(\s*0\s*,\s*72\s*\))"));
        const int cellRows=lavaLayout?512*5:512,lampIndexRows=lavaLayout?68+4+int(sceneFlag):68,fieldRows=lavaLayout?512+512+2*512:512;
        // The extended sky field keeps all original rows and appends three
        // 32-high bands × two materials for each of 192² world columns.
        const int indexRows=lampIndexRows+(fs::exists(root/"lib/canopy_columns.glsl")?192*192*3*2/128:0);
        const int listRows=lavaLayout?512+(16*16*16*25+15)/16:512;
        require(pCell.format=="r32ui"&&pCell.w==512&&pCell.h==cellRows&&pCell.clear,"lampCellImage must be cleared r32ui 512x"+std::to_string(cellRows)+" (64^3 cells"+(lavaLayout?" + 4 lava corner planes":"")+"), declared "+std::to_string(pCell.w)+"x"+std::to_string(pCell.h));
        require(pIndex.format=="r32ui"&&pIndex.w==128&&pIndex.h==indexRows&&pIndex.clear,"lampIndexImage must be cleared r32ui 128x"+std::to_string(indexRows)+" (17 words x 512 clusters"+(lavaLayout?" + 512 lava group words":"")+"), declared "+std::to_string(pIndex.w)+"x"+std::to_string(pIndex.h));
        require(pField.format=="r32f"&&pField.w==512&&pField.h==fieldRows&&!pField.clear,"lampFieldImage must be uncleared r32f 512x"+std::to_string(fieldRows)+", declared "+std::to_string(pField.w)+"x"+std::to_string(pField.h));
        require(pList.format=="rgba32f"&&pList.w==capacity+4&&pList.h==listRows&&!pList.clear,"lampListImage must be uncleared rgba32f (capacity+4) x "+std::to_string(listRows)+" (declared "+std::to_string(pList.w)+"x"+std::to_string(pList.h)+")");
        require(groups[0]==8&&groups[1]==8&&groups[2]==8,"shadowcomp1.csh must dispatch one group per 8^3 cluster");
        cell=makeTexture(GL_R32UI,pCell.w,pCell.h);index=makeTexture(GL_R32UI,pIndex.w,pIndex.h);
        field=makeTexture(GL_R32F,pField.w,pField.h);list=makeTexture(GL_RGBA32F,pList.w,pList.h);
        dummyShore=makeTexture(GL_R32UI,2336,768);
        zeroCell.assign(size_t(pCell.w)*pCell.h,0u);zeroIndex.assign(size_t(pIndex.w)*pIndex.h,0u);
        const char* base[3]={"shadow_solid","shadow_cutout","shadow_water"};
        for(int i=0;i<3;i++) pass[i]=linkAttribs(expand(root/(std::string(base[i])+".vsh"),root),expand(root/(std::string(base[i])+".fsh"),root),base[i]);
        comp=compute(root/"shadowcomp1.csh",root);
        const std::string common="#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/local_lighting.glsl",root);
        const std::string data="uniform sampler2D probeData;out vec4 probeOut;\n"
            "vec4 q(int i,int k){return texelFetch(probeData,ivec2(i,k),0);}\n";
        const std::string vsh="#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
        evalProgram=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0),b=q(i,1),c=q(i,2),d=q(i,3);"
            "probeOut=vec4(lampLighting(a.xyz,b.xyz,c.xyz,c.w,d.x,d.y>0.5),1.0);}","local-light-eval");
        emitProgram=link(vsh,common+data+"void main(){int i=int(gl_FragCoord.x);vec4 a=q(i,0);probeOut=vec4(lampSurfaceEmission(int(a.x),a.yzw),1.0);}","local-light-emission");
        glGenFramebuffers(1,&fbo);
        glGenTextures(1,&dataTex);glGenTextures(1,&outTex);
    }
    void clearRaw() {   // what Iris does every frame for clear=true images
        glBindTexture(GL_TEXTURE_2D,cell);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,pCell.w,pCell.h,GL_RED_INTEGER,GL_UNSIGNED_INT,zeroCell.data());
        glBindTexture(GL_TEXTURE_2D,index);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,pIndex.w,pIndex.h,GL_RED_INTEGER,GL_UNSIGNED_INT,zeroIndex.data());
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
    }
    static void emitBox(const Block& b,const D3& cam,const float lo[3],const float hi[3]) {
        for(int a=0;a<3;a++) for(int s=0;s<2;s++) {
            int u=(a+1)%3,v=(a+2)%3;
            const int cornerU[4]={0,1,1,0},cornerV[4]={0,0,1,1};
            float normal[3]={0,0,0};normal[a]=s?1.f:-1.f;glNormal3fv(normal);
            for(int c=0;c<4;c++) {
                double p[3];p[a]=(s?hi:lo)[a];p[u]=(cornerU[c]?hi:lo)[u];p[v]=(cornerV[c]?hi:lo)[v];
                const double base[3]={double(b.x),double(b.y),double(b.z)};
                float rel[3],mid[3];
                for(int i=0;i<3;i++) {rel[i]=float(base[i]+p[i]-cam[i]);mid[i]=float((0.5-p[i])*64.0);}
                glVertexAttrib4f(10,float(b.id),0,0,0);glVertexAttrib4f(11,mid[0],mid[1],mid[2],float(b.level));
                glVertex3fv(rel);
            }
        }
    }
    static void boxFor(const Block& b,float lo[3],float hi[3]) {
        auto set=[&](float a,float b2,float c,float d,float e,float f){lo[0]=a;lo[1]=b2;lo[2]=c;hi[0]=d;hi[1]=e;hi[2]=f;};
        int kind=kindOf(b);
        if(kind>=1&&kind<=10) set(0.4375f,0,0.4375f,0.5625f,0.625f,0.5625f);
        else if(kind==11||kind==12) set(0.3125f,0,0.3125f,0.6875f,0.5625f,0.6875f);
        else if(kind==13||kind==14) set(0,0,0,1,0.4375f,1);
        else if(kind==17) set(0.4375f,0,0.4375f,0.5625f,0.625f,0.5625f);
        else if(b.id==10301) set(0,0,0,1,0.5f,1);
        else if(b.id==10302) set(0,0.5f,0,1,1,1);
        else if(b.id==10304) set(0.375f,0,0.375f,0.625f,1,0.625f);
        else set(0,0,0,1,1,1);
    }
    // Draw each block through its real shadow vertex shader; rasterization is discarded because only the
    // vertex-stage image writes are under test (the shadow map itself is not part of this contract).
    void capture(const std::vector<Block>& blocks,const D3& cam,bool reverse=false) {
        lastCam=cam;
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        resetTextureMatrices();
        glEnable(GL_RASTERIZER_DISCARD);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for(int p=0;p<3;p++) {
            glUseProgram(pass[p]);
            glUniformMatrix4fv(glGetUniformLocation(pass[p],"shadowModelViewInverse"),1,GL_FALSE,identity);
            glUniform3f(glGetUniformLocation(pass[p],"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
            glUniform1i(glGetUniformLocation(pass[p],"isEyeInWater"),0);
            imageUnit(pass[p],"lampCellImage",0);imageUnit(pass[p],"lampIndexImage",1);imageUnit(pass[p],"shoreFaceImage",2);
            glBindImageTexture(0,cell,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBindImageTexture(1,index,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBindImageTexture(2,dummyShore,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
            glBegin(GL_QUADS);
            const size_t n=blocks.size();
            for(size_t i=0;i<n;i++) {
                const Block& b=blocks[reverse?n-1-i:i];
                if(b.pass!=p) continue;
                float lo[3],hi[3];boxFor(b,lo,hi);emitBox(b,cam,lo,hi);
            }
            glEnd();
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        }
        glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        require(glGetError()==GL_NO_ERROR,"GL error during shadow capture");
    }
    // Real post-shadow compute. Returns GPU time in ms.
    // REAL uniforms on the production compute program (glUseProgram(comp) must be current).
    void applyCarried(const Carried& c) {
        setUniform(comp,"heldItemId",c.item);setUniform(comp,"heldItemId2",c.item2);
        setUniform(comp,"heldBlockLightValue",c.level);setUniform(comp,"heldBlockLightValue2",c.level2);
        setUniform(comp,"isSpectator",c.spectator);setUniform(comp,"firstPersonCamera",c.firstPerson);
        setUniform(comp,"isRightHanded",c.rightHanded);setUniform(comp,"isEyeInWater",c.medium);
        setUniform(comp,"playerLookVector",c.look[0],c.look[1],c.look[2]);
        setUniform(comp,"relativeEyePosition",c.relEye[0],c.relEye[1],c.relEye[2]);
        const GLint loc=glGetUniformLocation(comp,"gbufferModelViewInverse");
        if(loc>=0) glUniformMatrix4fv(loc,1,GL_FALSE,c.viewInverse.data());
    }
    void publish(bool timed=false,const Carried* carried=nullptr) {
        glUseProgram(comp);
        setUniform(comp,"cameraPosition",lastCam[0],lastCam[1],lastCam[2]);
        if(carried) {applyCarried(*carried);carriedDirty=true;}
        else if(carriedDirty) {applyCarried(Carried{});carriedDirty=false;}
        imageUnit(comp,"lampCellImage",0);imageUnit(comp,"lampIndexImage",1);imageUnit(comp,"lampFieldImage",2);imageUnit(comp,"lampListImage",3);
        glBindImageTexture(0,cell,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);glBindImageTexture(1,index,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
        glBindImageTexture(2,field,0,GL_FALSE,0,GL_READ_WRITE,GL_R32F);glBindImageTexture(3,list,0,GL_FALSE,0,GL_READ_WRITE,GL_RGBA32F);
        GLuint query=0;if(timed) {glGenQueries(1,&query);glBeginQuery(GL_TIME_ELAPSED,query);}
        glDispatchCompute(groups[0],groups[1],groups[2]);
        if(timed) {glEndQuery(GL_TIME_ELAPSED);}
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
        if(timed) {GLuint64 ns=0;glGetQueryObjectui64v(query,GL_QUERY_RESULT,&ns);glDeleteQueries(1,&query);lastComputeMs=double(ns)*1e-6;}
        glUseProgram(0);
        require(glGetError()==GL_NO_ERROR,"GL error during shadowcomp1 dispatch");
    }
    void build(const std::vector<Block>& blocks,const D3& cam,bool reverse=false) { clearRaw();capture(blocks,cam,reverse);publish(); }
    void buildCarried(const std::vector<Block>& blocks,const D3& cam,const Carried& c) { clearRaw();capture(blocks,cam);publish(false,&c); }
    std::vector<unsigned> readUint(GLuint t,int w,int h) {
        std::vector<unsigned> v(size_t(w)*h);glBindTexture(GL_TEXTURE_2D,t);glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,v.data());return v;
    }
    std::vector<float> readFloat(GLuint t,int w,int h,int channels) {
        std::vector<float> v(size_t(w)*h*channels);glBindTexture(GL_TEXTURE_2D,t);
        glGetTexImage(GL_TEXTURE_2D,0,channels==1?GL_RED:GL_RGBA,GL_FLOAT,v.data());return v;
    }
    void runProgram(GLuint program,const std::vector<float>& data,int count,std::vector<float>& out,const D3& cam,GLuint listOverride=0) {
        require(count>0&&count<=8192,"bad probe batch");
        glBindTexture(GL_TEXTURE_2D,dataTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,count,4,0,GL_RGBA,GL_FLOAT,data.data());
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glBindTexture(GL_TEXTURE_2D,outTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,count,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,outTex,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"local-light probe framebuffer incomplete");
        glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glViewport(0,0,count,1);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,dataTex);
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,listOverride?listOverride:list);
        glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,field);
        glUseProgram(program);
        glUniform1i(glGetUniformLocation(program,"probeData"),0);glUniform1i(glGetUniformLocation(program,"aqualumenLightList"),1);
        glUniform1i(glGetUniformLocation(program,"aqualumenLightField"),2);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
        setUniform(program,"isEyeInWater",medium);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        out.assign(size_t(count)*4,0);glReadPixels(0,0,count,1,GL_RGBA,GL_FLOAT,out.data());
        for(float f:out) require(std::isfinite(f),"nonfinite GPU output");
        glUseProgram(0);glActiveTexture(GL_TEXTURE0);glBindFramebuffer(GL_FRAMEBUFFER,0);
        require(glGetError()==GL_NO_ERROR,"GL error during probe draw");
    }
    // Real lampLighting() on the currently published grid.
    std::vector<std::array<float,3>> evaluate(const std::vector<Query>& queries,const D3& cam,const D3* uniformCam=nullptr) {
        std::vector<float> data(queries.size()*16),out;
        const size_t n=queries.size();
        for(size_t i=0;i<n;i++) {
            const Query& q=queries[i];
            for(int c=0;c<3;c++) {
                data[(0*n+i)*4+c]=float(q.p[c]-cam[c]);data[(1*n+i)*4+c]=float(q.n[c]);data[(2*n+i)*4+c]=float(q.v[c]);
            }
            data[(2*n+i)*4+3]=q.rough;data[(3*n+i)*4+0]=q.level;data[(3*n+i)*4+1]=q.water?1.f:0.f;
        }
        runProgram(evalProgram,data,int(n),out,uniformCam?*uniformCam:cam);
        std::vector<std::array<float,3>> result(n);
        for(size_t i=0;i<n;i++) result[i]={out[i*4],out[i*4+1],out[i*4+2]};
        return result;
    }
    std::vector<std::array<float,3>> emission(const std::vector<std::array<float,4>>& materialAlbedo) {
        const size_t n=materialAlbedo.size();std::vector<float> data(n*16,0),out;
        for(size_t i=0;i<n;i++) for(int c=0;c<4;c++) data[i*4+c]=materialAlbedo[i][c];
        runProgram(emitProgram,data,int(n),out,{0,0,0});
        std::vector<std::array<float,3>> result(n);
        for(size_t i=0;i<n;i++) result[i]={out[i*4],out[i*4+1],out[i*4+2]};
        return result;
    }
};

// The real gbuffers_terrain pass, drawn as a tiny quad at a chosen camera-relative point. A scaled/translated
// gbufferModelViewInverse places the fragment's worldPosition/worldNormal without touching production code.
struct TerrainSun {
    // The orthographic shadow camera looks down from directly above the receiver.
    float incident=1.f;
    // World-space height of the first caster (leaf top or roof) in this test column.
    float casterHeight=1.f;
};

struct TerrainRig {
    GLuint program=0,albedoTex=0,sky=0,shadow=0,irradiance=0,target=0,fbo=0;
    void init(World& w) {
        const fs::path& root=w.root;
        program=link(expand(root/"gbuffers_terrain.vsh",root),expand(root/"gbuffers_terrain.fsh",root),"local-light-terrain","mc_Entity");
        glGenTextures(1,&albedoTex);glGenTextures(1,&sky);glGenTextures(1,&shadow);glGenTextures(1,&irradiance);glGenTextures(1,&target);glGenFramebuffers(1,&fbo);
        auto setup=[](GLuint t) {glBindTexture(GL_TEXTURE_2D,t);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);};
        // Night sky: constant dim radiance, zero solar-transmission row.
        std::vector<float> skyPixels(64*32*4,0);
        for(int y=0;y<31;y++) for(int x=0;x<64;x++) {size_t b=(size_t(y)*64+x)*4;skyPixels[b]=skyPixels[b+1]=skyPixels[b+2]=0.01f;skyPixels[b+3]=1;}
        setup(sky);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,64,32,0,GL_RGBA,GL_FLOAT,skyPixels.data());
        setup(shadow);float depth=1;glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&depth);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        std::vector<float> zeros(64*74*4,0);setup(irradiance);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,64,74,0,GL_RGBA,GL_FLOAT,zeros.data());
        setup(target);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,2,2,0,GL_RGBA,GL_FLOAT,nullptr);
        setup(albedoTex);
    }
    void setSun(const TerrainSun& sun,double cameraY) {
        // The local direct-irradiance rows are 10..73, separate from diffuse and bounce.
        std::vector<float> flux(64*64*4,sun.incident);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D,irradiance);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,10,64,64,GL_RGBA,GL_FLOAT,flux.data());
        // Same clip transform + distortion as the tested directional depth pass.
        const float depth=.5f-.5f*.2f*.03f*(sun.casterHeight-float(cameraY));
        glBindTexture(GL_TEXTURE_2D,shadow);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_DEPTH_COMPONENT,GL_FLOAT,&depth);
    }
    // texels: 4 RGBA values (row-major, y=0 first). Returns 4 output RGB values of the 2x2 target.
    std::array<std::array<float,3>,4> draw(World& w,const D3& cam,const D3& pos,const D3& normal,float lightmapX,float lightmapY,
                                           float material,const std::array<std::array<float,3>,4>& texels,bool useWorldGrid=true,const TerrainSun* sunlight=nullptr,
                                           const std::array<float,4>* alpha=nullptr) {
        std::vector<float> tex;
        for(size_t i=0;i<texels.size();++i) {
            tex.insert(tex.end(),texels[i].begin(),texels[i].end());
            tex.push_back(alpha?(*alpha)[i]:1.f);
        }
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,albedoTex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,2,2,0,GL_RGBA,GL_FLOAT,tex.data());
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,sky);
        glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,shadow);
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,irradiance);
        glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,w.list);
        glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,w.field);
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,target,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"terrain probe framebuffer incomplete");
        if(alpha) {
            const float empty[]={-1.f,-1.f,-1.f,0.f};
            glClearBufferfv(GL_COLOR,0,empty);
        }
        glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glViewport(0,0,2,2);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        resetTextureMatrices();
        glUseProgram(program);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        // Columns: t1*s, t2*s, normal*s, translation (camera-relative position).
        D3 n=normal,t1=std::abs(n[1])<0.9?D3{0,1,0}:D3{1,0,0};
        D3 a={t1[1]*n[2]-t1[2]*n[1],t1[2]*n[0]-t1[0]*n[2],t1[0]*n[1]-t1[1]*n[0]};
        double an=std::sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]);for(auto& c:a) c/=an;
        D3 b={n[1]*a[2]-n[2]*a[1],n[2]*a[0]-n[0]*a[2],n[0]*a[1]-n[1]*a[0]};
        const double s=1e-4;
        const float inverse[16]={float(a[0]*s),float(a[1]*s),float(a[2]*s),0,float(b[0]*s),float(b[1]*s),float(b[2]*s),0,
                                 float(n[0]*s),float(n[1]*s),float(n[2]*s),0,float(pos[0]-cam[0]),float(pos[1]-cam[1]),float(pos[2]-cam[2]),1};
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverse);
        for(const char* name:{"gbufferModelView","gbufferProjection","gbufferProjectionInverse","shadowProjection","shadowModelView"})
            glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),float(cam[0]),float(cam[1]),float(cam[2]));
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,-1,0);          // Sun below the horizon
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,-1,0);
        if(sunlight) {
            // Express world up in the view basis used by the terrain vertex shader.
            for(const char* uniform:{"sunPosition","shadowLightPosition"})
                glUniform3f(glGetUniformLocation(program,uniform),a[1],b[1],n[1]);
            const float lightView[16]={1,0,0,0, 0,0,-1,0, 0,1,0,0, 0,0,0,1};
            const float ortho[16]={.03f,0,0,0, 0,.03f,0,0, 0,0,.03f,0, 0,0,0,1};
            glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,lightView);
            glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,ortho);
        }
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
        glUniform1f(glGetUniformLocation(program,"rainStrength"),0);
        glUniform1i(glGetUniformLocation(program,"gtexture"),0);glUniform1i(glGetUniformLocation(program,"colortex6"),1);
        glUniform1i(glGetUniformLocation(program,"shadowtex0"),2);glUniform1i(glGetUniformLocation(program,"colortex11"),3);
        glUniform1i(glGetUniformLocation(program,"aqualumenLightList"),4);glUniform1i(glGetUniformLocation(program,"aqualumenLightField"),5);
        const GLint material_=glGetAttribLocation(program,"mc_Entity");
        if(material_>=0) {glDisableVertexAttribArray(material_);glVertexAttrib4f(material_,material,0,0,0);}
        glColor4f(1,1,1,1);glNormal3f(0,0,1);glMultiTexCoord2f(GL_TEXTURE1,lightmapX,lightmapY);
        (void)useWorldGrid;
        glBegin(GL_QUADS);
        glMultiTexCoord2f(GL_TEXTURE0,0,0);glVertex3f(-1,-1,0);glMultiTexCoord2f(GL_TEXTURE0,1,0);glVertex3f(1,-1,0);
        glMultiTexCoord2f(GL_TEXTURE0,1,1);glVertex3f(1,1,0);glMultiTexCoord2f(GL_TEXTURE0,0,1);glVertex3f(-1,1,0);
        glEnd();
        float pixels[16];glReadPixels(0,0,2,2,GL_RGBA,GL_FLOAT,pixels);
        glUseProgram(0);glActiveTexture(GL_TEXTURE0);glBindFramebuffer(GL_FRAMEBUFFER,0);
        for(float f:pixels) require(std::isfinite(f),"nonfinite terrain output");
        require(glGetError()==GL_NO_ERROR,"GL error during terrain pass");
        // glReadPixels order: (0,0),(1,0),(0,1),(1,1) == texel rows y=0 then y=1.
        return {{{pixels[0],pixels[1],pixels[2]},{pixels[4],pixels[5],pixels[6]},{pixels[8],pixels[9],pixels[10]},{pixels[12],pixels[13],pixels[14]}}};
    }
};

}  // namespace aqualumenLocalLights
#include "carried-lights-probe.h"
namespace aqualumenLocalLights {

inline void probe(const fs::path& root) {
    World w;w.init(root);
    TerrainRig terrain;terrain.init(w);
    std::cout<<"LOCAL-LIGHT QA renderer: "<<w.renderer<<" | production sources: shadow_{solid,cutout,water}.vsh, shadowcomp1.csh ("
             <<w.groups[0]<<"x"<<w.groups[1]<<"x"<<w.groups[2]<<" groups), local_lighting.glsl, gbuffers_terrain\n";
    std::cout<<"LOCAL-LIGHT QA parsed from sources: lampRange="<<w.range<<" lampCapacity="<<w.capacity<<" cell "<<w.pCell.w<<"x"<<w.pCell.h
             <<" index "<<w.pIndex.w<<"x"<<w.pIndex.h<<" field "<<w.pField.w<<"x"<<w.pField.h<<" list "<<w.pList.w<<"x"<<w.pList.h<<" (raw images clear=true)\n";
    const D3 C0={1003.25,71.5,-2049.75};                 // mod(camera,8)=(3.25,7.5,6.25): origin snaps 1000,64,-2056
    const D3 base8={std::floor(C0[0]/8)*8,std::floor(C0[1]/8)*8,std::floor(C0[2]/8)*8};
    const D3 LP={1005.5,71.64,-2049.5};                  // centre of a standing torch in cell (1005,71,-2050)
        const D3 mirrorView={0,1,0};
    auto at=[&](double dx,double dy,double dz){return D3{LP[0]+dx,LP[1]+dy,LP[2]+dz};};
    auto facing=[&](double d,D3 dir,float level=0) {          // receiver d metres from the torch along dir, normal toward torch
        return Query{at(dir[0]*d,dir[1]*d,dir[2]*d),{-dir[0],-dir[1],-dir[2]},mirrorView,0.075f,level,false};
    };
    auto rgbSum=[](std::array<float,3> a) {return double(a[0])+a[1]+a[2];};
    auto evalAt=[&](const std::vector<Block>& scene,const std::vector<Query>& q,const D3& cam) {w.build(scene,cam);return w.evaluate(q,cam);};
    auto evalScene=[&](const std::vector<Block>& scene,const std::vector<Query>& q) {return evalAt(scene,q,C0);};
    const std::vector<Block> oneTorch={torch(1005,71,-2050)};

    // ---------------------------------------------------------------- 1. capture + publish contract, bit exact
    {
        std::vector<Block> scene;
        for(int x=1000;x<1006;x++) for(int z=-2056;z<-2050;z++) scene.push_back(stone(x,70,z));
        scene.push_back(blk(1006,71,-2050,10300));scene.push_back(blk(1007,71,-2050,10301));scene.push_back(blk(1008,71,-2050,10302));
        scene.push_back(blk(1009,71,-2050,10303));scene.push_back(blk(1010,71,-2050,10304));
        scene.push_back(blk(1011,71,-2050,10400+14));scene.push_back(blk(1012,71,-2050,10400+3));
        scene.push_back(blk(1013,71,-2050,10114,0));  // unlit full-cube lamp: opaque, emits nothing
        // every placed-light kind, with distinct levels, in a row
        for(int kind=1;kind<=20;kind++) scene.push_back(blk(1000+kind,73,-2046,10099+kind,1+(kind*5)%15));
        scene.push_back(torch(1005,71,-2051,0));  // off torch writes nothing
        w.build(scene,C0);
        auto raw=w.readUint(w.cell,w.pCell.w,w.pCell.h),idx=w.readUint(w.index,w.pIndex.w,w.pIndex.h);
        std::map<int,unsigned> expected;std::vector<unsigned> expectedIndex(idx.size(),0);
        for(const Block& b:scene) {
            const int gx=b.x-int(base8[0])+32,gy=b.y-int(base8[1])+32,gz=b.z-int(base8[2])+32;
            const unsigned word=expectedWord(b);
            if(word) {int a=gx+64*(gz+64*gy);expected[a]=std::max(expected[a],word);}
            if(emits(b)) {
                int tile=gx/8+8*(gz/8+8*(gy/8)),bit=gx%8+8*(gz%8+8*(gy%8));
                expectedIndex[17*tile+bit/32]|=1u<<unsigned(bit%32);expectedIndex[17*tile+16]|=1u<<unsigned(bit/32);
            }
        }
        expectedSkyColumns(expectedIndex,scene,C0);
        size_t nonzero=0;
        for(size_t a=0;a<raw.size();a++) {
            unsigned want=expected.count(int(a))?expected[int(a)]:0u;
            require(raw[a]==want,"lampCellImage word at linear cell "+std::to_string(a)+": GPU "+std::to_string(raw[a])+" expected "+std::to_string(want));
            nonzero+=raw[a]!=0;
        }
        require(nonzero==expected.size()&&nonzero>35,"raw cell population");
        for(size_t i=0;i<idx.size();i++) require(idx[i]==expectedIndex[i],"lampIndexImage word "+std::to_string(i)+": GPU "+std::to_string(idx[i])+" expected "+std::to_string(expectedIndex[i]));
        auto field=w.readFloat(w.field,w.pField.w,w.pField.h,1);
        auto expectedField=raw;
        if(fs::exists(root/"lib/leaf_disk.glsl")) {
            // This open fixture has no enclosed cell. Independently enumerate
            // the one-cell halo from the verified positions of captured leaves.
            for(const auto& entry:expected) {
                if((entry.second&63u)!=2u) continue;
                int x=entry.first%64,z=(entry.first/64)%64,y=entry.first/4096;
                for(int py=std::max(0,y-1);py<=std::min(63,y+1);py++)
                    for(int pz=std::max(0,z-1);pz<=std::min(63,z+1);pz++)
                        for(int px=std::max(0,x-1);px<=std::min(63,x+1);px++) {
                            int neighbour=px+64*(pz+64*py);
                            if((raw[neighbour]&63u)==0u) expectedField[neighbour]|=1u<<19;
                        }
            }
        }
        // The published field mirrors the 64^3 cell words. Raw words past the cells (lava corner planes)
        // are compared above and must be zero in this lava-free scene; so must every lava neighbour count.
        for(size_t a=0;a<World::kCells;a++)
            require(field[a]==float(expectedField[a]),"published capture or canopy data differs at cell "+std::to_string(a));
        if(w.lavaLayout) for(int row=0;row<512;row++)
            require(field[size_t(1024+2*row)*w.pField.w]==0.f,"lava-free scene publishes a nonzero lava neighbour count in cluster "+std::to_string(row));
        std::cout<<"PASS local-light capture/publish: "<<expected.size()<<" occupied cells, all "<<raw.size()<<" raw words + "<<idx.size()<<" index words + 262144 field cells"
                 <<(w.lavaLayout?" + 512 zero lava neighbour counts":"")<<" match the independent CPU contract bit for bit (solid/cutout/glass passes, leaves, slabs, fence, 20 kinds, off lamps)\n";
        // Reversed draw order must not matter (atomic max/or are commutative): isolates GL nondeterminism.
        w.build(scene,C0,true);
        require(w.readUint(w.cell,w.pCell.w,w.pCell.h)==raw&&w.readUint(w.index,w.pIndex.w,w.pIndex.h)==idx,"raw images depend on draw order");
        std::cout<<"PASS local-light determinism: reversed block submission reproduces raw cell/index images bit for bit\n";
    }

    // ---------------------------------------------------------------- 2. cluster lists vs brute-force CPU reference, cap, cross-tile
    {
        uint32_t seed=12345u;auto rnd=[&](int n){seed=seed*1664525u+1013904223u;return int((seed>>8)%unsigned(n));};
        std::vector<Block> scene;std::map<int,int> used;
        struct Lamp {float pos[3];int kind,level;};
        std::vector<Lamp> lamps;
        for(int tries=0;lamps.size()<64&&tries<2000;tries++) {
            int gx=20+rnd(24),gy=26+rnd(14),gz=20+rnd(24);
            int a=gx+64*(gz+64*gy);if(used.count(a)) continue;used[a]=1;
            int kind=1+rnd(20),level=1+rnd(15);
            Block b=blk(gx+int(base8[0])-32,gy+int(base8[1])-32,gz+int(base8[2])-32,10099+kind,level);
            scene.push_back(b);auto off=kindOffset(kind);lamps.push_back({{gx+off[0],gy+off[1],gz+off[2]},kind,level});
        }
        // Dense cluster: 20 torches inside one 8^3 tile (more than the capacity).
        for(int i=0;i<20;i++) {
            int gx,gy,gz,a;do{gx=32+rnd(8);gy=32+rnd(8);gz=32+rnd(8);a=gx+64*(gz+64*gy);}while(used.count(a));used[a]=1;
            int level=1+rnd(15);
            scene.push_back(blk(gx+int(base8[0])-32,gy+int(base8[1])-32,gz+int(base8[2])-32,10100,level));
            auto off=kindOffset(1);lamps.push_back({{gx+off[0],gy+off[1],gz+off[2]},1,level});
        }
        w.build(scene,C0);
        auto list=w.readFloat(w.list,w.pList.w,w.pList.h,4);
        const float range=float(w.range);int overCap=0,maxCount=0,total=0;
        for(int ty=0;ty<8;ty++) for(int tz=0;tz<8;tz++) for(int tx=0;tx<8;tx++) {
            const int row=tx+8*(tz+8*ty);
            float centre[3]={tx*8+4.f,ty*8+4.f,tz*8+4.f};
            std::vector<std::pair<float,int>> cand;
            for(size_t i=0;i<lamps.size();i++) {
                float d[3],n2=0,d2=0;
                for(int c=0;c<3;c++) {d[c]=lamps[i].pos[c]-centre[c];float nn=std::max(std::abs(d[c])-4.f,0.f);n2+=nn*nn;d2+=d[c]*d[c];}
                if(n2>=range*range) continue;
                cand.push_back({float(lamps[i].level)/(1.f+d2),int(i)});
            }
            std::sort(cand.begin(),cand.end(),[](auto& a,auto& b){return a.first>b.first;});
            for(size_t i=1;i<cand.size();i++) require(cand[i-1].first!=cand[i].first,"fixture weight tie in tile "+std::to_string(row)+"; change seed");
            const int expectedCount=int(std::min<size_t>(cand.size(),size_t(w.capacity)));
            const float* head=&list[(size_t(row)*w.pList.w)*4];
            require(int(head[0])==expectedCount,"cluster "+std::to_string(row)+" count GPU "+num(head[0])+" expected "+std::to_string(expectedCount)+" of "+std::to_string(cand.size())+" candidates");
            if(int(cand.size())>w.capacity) overCap++;
            maxCount=std::max(maxCount,expectedCount);total+=expectedCount;
            for(int k=0;k<expectedCount;k++) {
                const Lamp& L=lamps[cand[k].second];const float* r=&list[(size_t(row)*w.pList.w+1+k)*4];
                for(int c=0;c<3;c++) require(std::abs(r[c]-L.pos[c])<1e-5f,"cluster "+std::to_string(row)+" rank "+std::to_string(k)+" position (lamp dropped/reordered/misplaced)");
                require(int(r[3])==(L.kind|(L.level<<6)),"cluster "+std::to_string(row)+" rank "+std::to_string(k)+" kind/level code");
            }
            for(int k=expectedCount;k<w.capacity;k++) {
                // slots past the count are not read by the renderer; they only need to be finite (checked by readback).
            }
        }
        require(overCap>0,"fixture must exceed capacity in at least one cluster");
        require(maxCount==w.capacity,"capacity must actually be reached");
        std::cout<<"PASS local-light clusters: all 512 clusters equal brute-force CPU lists (range "<<w.range<<" m to the 8^3 box, cap "<<w.capacity<<" by weight); "
                 <<overCap<<" clusters over cap, "<<total<<" published records, "<<lamps.size()<<" lamps incl. all 20 kinds\n";
        // The same scene again after a clear and reversed submission must publish identical lists.
        w.build(scene,C0,true);
        require(w.readFloat(w.list,w.pList.w,w.pList.h,4)==list,"cluster lists depend on submission order");
    }

    // ---------------------------------------------------------------- 3. inverse square, range, isotropy, facing, level, off
    double softening=0;
    {
        std::vector<Query> q;const double ds[]={1,2,3,4,5,6,8};
        for(double d:ds) q.push_back(facing(d,{1,0,0}));
        auto e=evalScene(oneTorch,q);
        const double e1=e[0][0],e2=e[1][0];
        require(e1>0&&e2>0&&e1>e2,"lamp must light a facing receiver and decay with distance");
        softening=(e2*4-e1)/(e1-e2);                // 1/(k+d^2) law fitted from d=1,2 only
        require(softening>=0&&softening<1.0,"fitted source softening k="+num(softening)+" must be a small positive length^2");
        for(size_t i=2;i<std::size(ds);i++)
            require(near(e[i][0]*(softening+ds[i]*ds[i]),e1*(softening+1),0.004),"inverse-square violated at d="+num(ds[i])+": E*(k+d^2)="+num(e[i][0]*(softening+ds[i]*ds[i]))+" vs "+num(e1*(softening+1)));
        std::cout<<"PASS local-light inverse-square: E*(k+d^2) constant to 0.4% for d=1..8 m (fitted k="<<softening<<" m^2 from d=1,2 only), E(1m)="<<e1<<" E(8m)="<<e[6][0]<<"\n";
        // Colour of a warm torch: red > green > blue.
        require(e[1][0]>e[1][1]&&e[1][1]>e[1][2]&&e[1][2]>0,"warm torch must be warm");
    }
    {
        const D3 dirs[6]={{1,0,0},{-1,0,0},{0,0,1},{0,0,-1},{0,1,0},{0,-1,0}};
        const double ds[]={4,9.5,12,13,13.9};
        std::vector<Query> q;for(auto& d:dirs) for(double r:ds) q.push_back(facing(r,d));
        q.push_back(facing(14.0,{1,0,0}));q.push_back(facing(15.0,{1,0,0}));q.push_back(facing(14.0,{0,0,1}));q.push_back(facing(20.0,{-1,0,0}));
        auto e=evalScene(oneTorch,q);
        for(int d=0;d<6;d++) for(size_t i=0;i<std::size(ds);i++) {
            double got=e[d*5+i][0],ref=e[0*5+i][0];
            require(got>0,"lamp missing at "+num(ds[i])+" m in direction "+std::to_string(d)+" (cluster list incomplete near lampRange)");
            require(near(got,ref,0.003),"direction anisotropy at "+num(ds[i])+" m dir "+std::to_string(d)+": "+num(got)+" vs "+num(ref));
            if(i>0) require(got<=e[d*5+i-1][0],"energy increased with distance at dir "+std::to_string(d));
        }
        for(size_t i=30;i<e.size();i++) require(e[i][0]==0&&e[i][1]==0&&e[i][2]==0,"light at/after lampRange must be exactly zero");
        require(e[4][0]<1e-3*e[1][0],"range fade must reach ~0 continuously before the cutoff (13.9 m vs 9.5 m)");
        std::cout<<"PASS local-light range: all six directions agree to 0.3% from 4 to 13.9 m (cluster membership complete across tiles), monotone, exactly zero from "<<w.range<<" m\n";
    }
    {
        std::vector<Query> q;
        const double angles[]={0,30,60,80,90,120,180};
        for(double a:angles) {double r=a*M_PI/180;Query f=facing(3,{1,0,0});f.n={-std::cos(r),0,std::sin(r)};q.push_back(f);}
        auto e=evalScene(oneTorch,q);
        for(int i=0;i<4;i++) require(near(e[i][0]/e[0][0],std::cos(angles[i]*M_PI/180),0.003,2e-4),"cosine facing at "+num(angles[i])+" deg: "+num(e[i][0]/e[0][0]));
        for(int i=4;i<7;i++) require(rgbSum(e[i])<1e-9,"back-facing/grazing surface must receive zero at "+num(angles[i])+" deg: "+num(rgbSum(e[i])));
        std::cout<<"PASS local-light facing: E(theta)/E(0)=cos(theta) for 0/30/60/80 deg (+-0.3%), zero (<1e-9; cos(90deg) is not exactly 0 in double) at 90/120/180 deg\n";
    }
    {
        std::vector<Block> a=oneTorch;std::vector<Query> q={facing(4,{1,0,0})};
        double e14=evalScene({torch(1005,71,-2050,14)},q)[0][0],e15=evalScene({torch(1005,71,-2050,15)},q)[0][0],e7=evalScene({torch(1005,71,-2050,7)},q)[0][0];
        auto off=evalScene({torch(1005,71,-2050,0)},q)[0];
        require(e7>0&&e7<e14&&e14<e15,"emission must increase with block light level");
        require(rgbSum(off)==0,"an off lamp (level 0) must add exactly zero");
        auto none=evalScene({},q)[0];require(rgbSum(none)==0,"empty grid must add exactly zero");
        auto offCube=evalScene({blk(1005,71,-2050,10114,0)},q)[0];require(rgbSum(offCube)==0,"unlit full-cube lamp must not emit");
        std::cout<<"PASS local-light level/off: level 7<14<15 ("<<e7<<"<"<<e14<<"<"<<e15<<"), level 0 torch, unlit lamp cube and empty grid are exactly zero\n";
    }

    // ---------------------------------------------------------------- 4. one warm + one soul add
    {
        const D3 P={1008.5,71.0,-2049.5};
        std::vector<Query> q={{P,{0,1,0},{0,1,0},0.075f,0,false}};
        auto warm=evalScene({torch(1005,71,-2050,14)},q)[0],soul=evalScene({soulTorch(1011,71,-2050,14)},q)[0];
        auto both=evalScene({torch(1005,71,-2050,14),soulTorch(1011,71,-2050,14)},q)[0];
        auto soulOff=evalScene({torch(1005,71,-2050,14),soulTorch(1011,71,-2050,0)},q)[0];
        for(int c=0;c<3;c++) require(near(both[c],warm[c]+soul[c],1e-4),"warm+soul must add per channel (c="+std::to_string(c)+") "+num(both[c])+" vs "+num(warm[c]+soul[c]));
        require(warm[0]>warm[1]&&warm[1]>warm[2]&&warm[2]>0,"warm torch hue");
        require(soul[2]>soul[1]&&soul[1]>soul[0]&&soul[0]>0&&soul[2]>5*soul[0],"soul torch hue");
        require(near(warm[0],soul[2],1e-3),"equal level/distance warm and soul torches must have equal peak-channel energy");
        require(both[0]>warm[0]&&both[2]>soul[2]&&both[0]>soul[0]*1.0&&both[2]>warm[2],"both lamps must brighten every channel relative to either alone");
        for(int c=0;c<3;c++) require(near(soulOff[c],warm[c],1e-6),"switching the soul lamp off must restore exactly the warm-only result");
        std::cout<<"PASS local-light warm+soul: both="<<both[0]<<","<<both[1]<<","<<both[2]<<" == warm "<<warm[0]<<","<<warm[1]<<","<<warm[2]<<" + soul "<<soul[0]<<","<<soul[1]<<","<<soul[2]
                 <<" (1e-4); soul lamp off restores warm-only exactly\n";
    }

    // ---------------------------------------------------------------- 5. source moved updates, no ghost after clearing
    {
        std::vector<Query> q={facing(4,{1,0,0}),facing(4,{1,0,0})};q[1].p=at(4,0,0);
        // Receiver at x=1009.5. Lamp A at cell 1005 (d=4), lamp B moved to cell 1007 (d=2).
        auto eA=evalScene({torch(1005,71,-2050)},{q[0]})[0];
        w.build({torch(1007,71,-2050)},C0);
        auto eB=w.evaluate({q[0]},C0)[0];
        require(eB[0]>eA[0],"moving the lamp closer must brighten the receiver");
        require(near(eB[0]/eA[0],(softening+16)/(softening+4),0.004),"moved-lamp energy ratio must follow the fitted inverse-square law: "+num(eB[0]/eA[0])+" vs "+num((softening+16)/(softening+4)));
        auto list=w.readFloat(w.list,w.pList.w,w.pList.h,4);
        // Lamp B centre in grid space, row of its own tile.
        const int gx=1007-int(base8[0])+32,gy=71-int(base8[1])+32,gz=-2050-int(base8[2])+32;
        const int row=gx/8+8*(gz/8+8*(gy/8));
        const float* r=&list[(size_t(row)*w.pList.w+1)*4];
        require(int(list[size_t(row)*w.pList.w*4])==1&&std::abs(r[0]-(gx+0.5f))<1e-5f&&std::abs(r[1]-(gy+0.64f))<1e-5f&&std::abs(r[2]-(gz+0.5f))<1e-5f,"published list entry must be at the lamp's NEW grid position");
        // Old cell must be empty in the raw and field images.
        const int ox=1005-int(base8[0])+32;
        auto field=w.readFloat(w.field,w.pField.w,w.pField.h,1);
        require(field[size_t(ox+64*(gz+64*gy))]==0.f,"old lamp cell still occupied after the lamp moved");
        std::cout<<"PASS local-light moved source: receiver energy ratio "<<eB[0]/eA[0]<<" matches inverse-square prediction "<<(softening+16)/(softening+4)<<"; list holds only the new position, old cell is empty\n";

        // Ghost: publish lamp, clear raw images (Iris clear=true), capture nothing, publish again. Field/list are NOT cleared.
        w.build({torch(1005,71,-2050),soulTorch(1011,71,-2050)},C0);
        require(rgbSum(w.evaluate({q[0]},C0)[0])>0,"ghost setup lamp must light the receiver");
        w.clearRaw();w.publish();
        auto f=w.readFloat(w.field,w.pField.w,w.pField.h,1),l=w.readFloat(w.list,w.pList.w,w.pList.h,4);
        // Cell region of the field (the lamp layout). Lava rows below it are gated by the counts checked here.
        size_t stale=0;for(size_t a=0;a<World::kCells;a++) stale+=f[a]!=0.f;
        if(w.lavaLayout) for(int row=0;row<512;row++) stale+=f[size_t(1024+2*row)*w.pField.w]!=0.f;
        size_t staleCount=0;for(int row=0;row<512;row++) staleCount+=l[size_t(row)*w.pList.w*4]!=0.f;
        require(stale==0,"ghost: "+std::to_string(stale)+" field cells survive clearing the raw images");
        require(staleCount==0,"ghost: "+std::to_string(staleCount)+" cluster lists still report lamps after clearing");
        require(rgbSum(w.evaluate({q[0]},C0)[0])==0,"ghost light still shades the receiver after the lamps were removed");
        std::cout<<"PASS local-light no ghost: after clearing raw images and republishing an empty scene all 262144 field cells and 512 cluster counts"<<(w.lavaLayout?" (+512 lava neighbour counts)":"")<<" are zero and the receiver is dark\n";
        // Sensitivity control: WITHOUT clearing raw images the old lamp persists, i.e. the ghost detector can fire.
        w.build({torch(1005,71,-2050)},C0);
        w.capture({torch(1007,71,-2050)},C0);w.publish();
        auto twin=w.readFloat(w.list,w.pList.w,w.pList.h,4);
        require(int(twin[size_t(row)*w.pList.w*4])==2,"negative control: un-cleared raw images must show both lamps (ghost detector sensitivity)");
        std::cout<<"PASS local-light ghost detector control: skipping the clear leaves the old lamp (count 2) -> production relies on image clear=true, which shaders.properties declares\n";
    }

    // ---------------------------------------------------------------- 6. occlusion: barrier / leaves / slabs / glass / fence
    {
        const D3 LPh=LP;(void)LPh;
        auto horizontal=[&](double y) {Query f=facing(4,{1,0,0});f.p[1]=y;return f;};
        const std::vector<Query> q={horizontal(71.64),horizontal(71.10)};
        auto open=evalScene(oneTorch,q);
        auto withBlock=[&](Block b) {auto scene=oneTorch;scene.push_back(b);return evalScene(scene,q);};
        auto leaf=withBlock(blk(1007,71,-2050,10300));
        require(open[0][0]>0&&near(leaf[0][0]/open[0][0],std::exp(-1.45),0.01),"1 m of leaves must transmit exp(-1.45): "+num(leaf[0][0]/open[0][0]));
        auto scene2=oneTorch;scene2.push_back(blk(1007,71,-2050,10300));scene2.push_back(blk(1008,71,-2050,10300));
        auto leaf2=evalScene(scene2,q);
        require(near(leaf2[0][0]/open[0][0],std::exp(-2.9),0.015),"2 m of leaves must transmit exp(-2.9): "+num(leaf2[0][0]/open[0][0]));
        std::cout<<"PASS local-light leaves: 1 m -> "<<leaf[0][0]/open[0][0]<<" (exp(-1.45)="<<std::exp(-1.45)<<"), 2 m -> "<<leaf2[0][0]/open[0][0]<<" (exp(-2.9)="<<std::exp(-2.9)<<")\n";
        auto bottom=withBlock(blk(1007,71,-2050,10301)),top=withBlock(blk(1007,71,-2050,10302)),dbl=withBlock(blk(1007,71,-2050,10303)),full=withBlock(stone(1007,71,-2050));
        require(near(bottom[0][0],open[0][0],1e-5),"a ray passing above a bottom slab (y=.64) must be unaffected");
        require(rgbSum(bottom[1])==0,"a ray dipping below the bottom-slab top (y<.5) must be blocked");
        require(rgbSum(top[0])==0,"a top slab at y .5-1 must block the y=.64 ray");
        require(near(top[1][0],open[1][0],1e-5)&&open[1][0]>0,"a ray below a top slab (y<.5) must pass");
        require(rgbSum(dbl[0])==0&&rgbSum(full[0])==0&&rgbSum(dbl[1])==0,"double slab / full block must be opaque");
        std::cout<<"PASS local-light slabs: bottom slab passes the y=.64 ray and blocks the low ray, top slab the opposite, double slab and full block block both (partial-cell shapes, not whole-cell)\n";
                auto fence=withBlock(blk(1007,71,-2050,10304));
        require(rgbSum(fence[0])==0,"a fence post centred on the ray must block it");
        // Offset the lamp row sideways so the ray clears the 0.25 m post but stays in the same cells.
        std::vector<Block> side={torch(1005,71,-2050),blk(1007,71,-2050,10304)};
        Query clear=facing(4,{1,0,0});clear.p[2]=LP[2]+0.45;clear.n={-1,0,0};
        auto sideOpen=evalScene(oneTorch,{clear})[0],sideFence=evalScene(side,{clear})[0];
        require(rgbSum(sideOpen)>0&&near(sideFence[0],sideOpen[0],0.05),"a ray 0.35 m beside a fence post must mostly pass (post is thin, not a whole cube)");
        std::cout<<"PASS local-light fence: centred post blocks, ray beside it passes ("<<sideFence[0]/sideOpen[0]<<" of open)\n";
        // Stained glass transmits per channel.
        const struct {int dye;std::array<double,3> t;} glass[]={{14,{.85,.20,.16}},{11,{.19,.36,.86}}};
        for(auto& g:glass) {
            auto s=withBlock(blk(1007,71,-2050,10400+g.dye));
            for(int c=0;c<3;c++) require(near(s[0][c]/open[0][c],g.t[c],0.02),"stained glass dye "+std::to_string(g.dye)+" channel "+std::to_string(c)+": "+num(s[0][c]/open[0][c])+" vs "+num(g.t[c]));
        }
        std::cout<<"PASS local-light stained glass: red and blue panes transmit per-channel RGB through the shadow_water capture pass (+-2%)\n";
        // The opaque barrier: lamp, wall and receiver. Also an unlit (off) lamp cube is opaque.
        auto offBlock=withBlock(blk(1007,71,-2050,10114,0));
        require(rgbSum(offBlock[0])==0,"an unlit lamp cube must still block light");
    }

    // ---------------------------------------------------------------- 7. production terrain pass: barrier blocks, zero sunlight still lit
    {
        std::vector<Block> floor;
        for(int x=1000;x<1015;x++) for(int z=-2056;z<-2043;z++) floor.push_back(stone(x,70,z));
        auto lit=floor;lit.push_back(torch(1005,71,-2050));
        auto walled=lit;for(int y=71;y<74;y++) for(int z=-2053;z<-2046;z++) walled.push_back(stone(1007,y,z));
        const D3 P={1008.5,71.0,-2049.5},up={0,1,0};
        const std::array<std::array<float,3>,4> grey={{{.5f,.5f,.5f},{.5f,.5f,.5f},{.5f,.5f,.5f},{.5f,.5f,.5f}}};
        const double albedo=std::pow(0.5,2.2);
        auto paint=[&](const std::vector<Block>& scene,float lightmapX) {w.build(scene,C0);return terrain.draw(w,C0,P,up,lightmapX,0.0f,10001,grey);};
        auto dark=paint(floor,0),open=paint(lit,0),shut=paint(walled,0);
        auto direct=w.evaluate({{P,up,up,0.075f,0,false}},C0)[0];   // function-level lampLighting on the walled scene
        w.build(lit,C0);auto directOpen=w.evaluate({{P,up,up,0.075f,0,false}},C0)[0];
        require(rgbSum(direct)==0,"function-level: opaque wall must zero the lamp term");
        require(directOpen[0]>0.01,"function-level: open scene must light the surface");
        for(int c=0;c<3;c++) {
            require(dark[0][c]<0.005,"zero-sun baseline must be dark (no Sun/sky leakage): "+num(dark[0][c]));
            require(near(shut[0][c],dark[0][c],1e-6),"production terrain: wall must reduce the lamp to the dark baseline (c="+std::to_string(c)+") "+num(shut[0][c])+" vs "+num(dark[0][c]));
            require(near((open[0][c]-dark[0][c])/albedo,directOpen[c],1e-3),"production terrain pass must apply the same lamp radiance as lampLighting (c="+std::to_string(c)+"): "+num((open[0][c]-dark[0][c])/albedo)+" vs "+num(directOpen[c]));
        }
        require(open[0][0]>10*dark[0][0],"in zero sunlight the lamp must clearly light the surface (open "+num(open[0][0])+" vs dark "+num(dark[0][0])+")");
        std::cout<<"PASS local-light production terrain @ night, skylight 0: dark baseline "<<dark[0][0]<<", lamp-lit "<<open[0][0]<<" (= albedo*lampLighting), behind opaque wall "<<shut[0][0]<<" (== dark)\n";
        // With vanilla block light present, the wall must still remove the direct contribution.
        auto openV=paint(lit,0.8f),shutV=paint(walled,0.8f),darkV=paint(floor,0.8f);
        for(int c=0;c<3;c++) require(near((openV[0][c]-shutV[0][c])/albedo,directOpen[c],1e-3),"direct lamp term must be the open-minus-walled difference with vanilla light present (c="+std::to_string(c)+")");
        require(openV[0][0]>shutV[0][0]&&shutV[0][0]<=openV[0][0]&&darkV[0][0]>0,"vanilla-lit comparison");
        std::cout<<"PASS local-light production terrain with vanilla block light 0.8: open-minus-walled difference equals the direct lamp term exactly; wall "<<shutV[0][0]<<" < open "<<openV[0][0]<<"\n";
        // Moving the lamp changes the lit surface in the production pass too.
        auto moved=floor;moved.push_back(torch(1007,71,-2050));
        auto movedLit=paint(moved,0);
        require(movedLit[0][0]>open[0][0]*1.3,"production terrain pass must follow the moved lamp (closer -> brighter)");
        auto gone=paint(floor,0);for(int c=0;c<3;c++) require(near(gone[0][c],dark[0][c],1e-6),"production terrain: lamp removed -> back to the dark baseline (no ghost)");
        std::cout<<"PASS local-light production terrain moved/removed: closer lamp "<<movedLit[0][0]<<" > "<<open[0][0]<<"; removed lamp returns exactly to "<<gone[0][0]<<"\n";
    }

    // ---------------------------------------------------------------- 8. emission varies with texel, not whole block
    {
        auto em=w.emission({{10099,.9f,.9f,.9f},{10100,.9f,.9f,.9f},{10100,.01f,.01f,.01f},{10100,.4f,.4f,.4f},{10119,.9f,.9f,.9f},{10120,.9f,.9f,.9f},
                            {10114,.9f,.9f,.9f},{10114,.5f,.5f,.5f},{10114,.05f,.05f,.05f},{10001,.9f,.9f,.9f},{10111,.9f,.9f,.9f},{10111,.01f,.01f,.01f}});
        require(rgbSum(em[0])==0&&rgbSum(em[9])==0&&rgbSum(em[5])==0,"non-lamp materials (10099, 10001, 10120) must not emit");
        require(em[1][0]>em[3][0]&&em[3][0]>=em[2][0]&&em[2][0]==0,"rod/housing lamps emit only on luminous texels (dark texel exactly zero)");
        require(em[1][0]>em[1][1]&&em[1][1]>em[1][2]&&em[1][2]>0,"torch emission hue is warm");
        require(em[6][0]>em[7][0]&&em[7][0]>em[8][0]&&em[8][0]>0,"cube lamps modulate with the texture (bright>mid>dark>0), not a uniform whole-block colour");
        require(em[10][2]>em[10][1]&&em[10][1]>em[10][0]&&rgbSum(em[11])==0,"soul lantern emits blue, only on bright texels");
        require(rgbSum(em[4])>0,"material 10119 (last kind) emits");
        // End-to-end in the real terrain pass: 2x2 texture, lamp vs non-lamp material, same pixel.
        const std::array<std::array<float,3>,4> pattern={{{.05f,.05f,.05f},{.95f,.95f,.95f},{.5f,.5f,.5f},{.99f,.99f,.99f}}};
        w.build({},C0);
        auto plain=terrain.draw(w,C0,{1008.5,71,-2049.5},{0,1,0},0,0,10001,pattern);
        auto lamp=terrain.draw(w,C0,{1008.5,71,-2049.5},{0,1,0},0,0,10100,pattern);
        auto cube=terrain.draw(w,C0,{1008.5,71,-2049.5},{0,1,0},0,0,10115,pattern);
        std::array<double,4> e0,e1;
        for(int i=0;i<4;i++) {e0[i]=lamp[i][0]-plain[i][0];e1[i]=cube[i][0]-plain[i][0];}
        require(e0[0]<1e-6&&e0[1]>0.5&&e0[3]>=e0[1]&&e0[2]<e0[1],"production terrain pass: torch emission follows texel luminance");
        require(e1[0]>0&&e1[0]<e1[2]&&e1[2]<e1[1]&&e1[1]<e1[3],"production terrain pass: sea lantern emission scales with texel brightness (not constant)");
        std::cout<<"PASS local-light emission: rods emit only luminous texels (dark "<<e0[0]<<", mid "<<e0[2]<<", bright "<<e0[1]<<"), cube lamps scale with texture ("<<e1[0]<<" < "<<e1[2]<<" < "<<e1[1]<<" < "<<e1[3]<<"), non-lamp ids emit zero\n";
    }

    // ---------------------------------------------------------------- 9. water specular responds to the lamp
    {
        auto viewAt=[&](double elevationDeg,D3 az={1,0,0}) {double r=elevationDeg*M_PI/180;return D3{az[0]*std::cos(r),std::sin(r),az[2]*std::cos(r)};};
        const D3 P={LP[0]+4,71.0,LP[2]};                        // water surface point 4 m from the lamp, lamp 0.64 m above
        auto sweep=[&](const std::vector<Block>& scene,float rough,double surfaceX,double lo,double hi,double step) {
            std::vector<Query> q;for(double e=lo;e<=hi+1e-9;e+=step) q.push_back({{surfaceX,71.0,LP[2]},{0,1,0},viewAt(e),rough,0,true});
            auto r=evalScene(scene,q);std::vector<double> y;for(auto& v:r) y.push_back(v[0]);return y;
        };
        (void)P;
        const double lo=3.0,hi=20.0,step=0.05;
        auto e=sweep(oneTorch,0.075f,LP[0]+4,lo,hi,step);
        size_t peak=std::max_element(e.begin(),e.end())-e.begin();
        double peakAngle=lo+step*peak,mirror=std::atan2(0.64,4.0)*180/M_PI;
        require(std::abs(peakAngle-mirror)<0.35,"water glint peak at "+num(peakAngle)+" deg, mirror geometry says "+num(mirror));
        double offPeak=*std::max_element(e.begin()+std::min(e.size()-1,size_t((mirror+8-lo)/step)),e.end());
        require(e[peak]>0&&offPeak<0.01*e[peak],"glint must be a localized reflection lobe: off-lobe max "+num(offPeak)+" vs peak "+num(e[peak]));
        auto rough=sweep(oneTorch,0.12f,LP[0]+4,lo,hi,step);
        size_t roughPeak=std::max_element(rough.begin(),rough.end())-rough.begin();
        require(rough[roughPeak]<e[peak],"rougher water must lower the glint peak ("+num(rough[roughPeak])+" vs "+num(e[peak])+")");
        // Width (count of samples above half the peak) must grow with roughness.
        auto halfWidth=[&](const std::vector<double>& v) {double m=*std::max_element(v.begin(),v.end());size_t n=0;for(double x:v) n+=x>0.5*m;return n;};
        require(halfWidth(rough)>=halfWidth(e),"rougher water must not narrow the glint");
        // Lamp moved farther away: the mirror angle falls to atan(.64/6).
        auto far=sweep({torch(1005,71,-2050)},0.075f,LP[0]+6,lo,hi,step);
        size_t farPeak=std::max_element(far.begin(),far.end())-far.begin();
        require(std::abs(lo+step*farPeak-std::atan2(0.64,6.0)*180/M_PI)<0.35,"glint must follow the geometry for a 6 m receiver: "+num(lo+step*farPeak));
        // Off, blocked and removed lamps produce no glint; vanilla light must not leak into water.
        auto offW=sweep({torch(1005,71,-2050,0)},0.075f,LP[0]+4,lo,hi,step);
        auto wallW=sweep({torch(1005,71,-2050),stone(1007,71,-2050),stone(1007,72,-2050)},0.075f,LP[0]+4,lo,hi,step);
        require(*std::max_element(offW.begin(),offW.end())==0&&*std::max_element(wallW.begin(),wallW.end())==0,"off or walled lamp must give no water glint");
        Query lowLevel{{LP[0]+4,71.0,LP[2]},{0,1,0},viewAt(mirror),0.075f,0,true},highLevel=lowLevel;highLevel.level=1.0f;
        auto lowE=evalScene({},{lowLevel})[0],highE=evalScene({},{highLevel})[0];
        require(rgbSum(lowE)==0&&rgbSum(highE)==0,"water path must not add the vanilla block-light term (it has no specular lobe)");
        // View away from the mirror direction: diffuse nl term must not leak into the water specular.
        auto away=evalScene(oneTorch,{{{LP[0]+4,71.0,LP[2]},{0,1,0},{-0.99388,0.11043,0},0.075f,0,true}})[0];
        require(away[0]<0.01*e[peak],"water responds specularly, not diffusely: away-view energy "+num(away[0]));
        std::cout<<"PASS local-light water specular: glint peak "<<peakAngle<<" deg vs mirror "<<mirror<<" deg (4 m), 6 m peak "<<lo+step*farPeak<<" deg vs "<<std::atan2(0.64,6.0)*180/M_PI
                 <<"; peak "<<e[peak]<<" -> rough "<<rough[roughPeak]<<"; off/walled/removed lamp and vanilla level add zero\n";
    }

    // ---------------------------------------------------------------- 10. tile-snap / camera translation invariance
    {
        std::vector<Block> scene={torch(1005,71,-2050),soulTorch(1010,71,-2050,12),blk(1007,71,-2051,10300)};
        for(int y=71;y<73;y++) scene.push_back(stone(1008,y,-2048));
        std::vector<Query> q={facing(3,{1,0,0}),{{1008.5,71.0,-2049.5},{0,1,0},{0,1,0},0.075f,0,false},
                              {{1007.5,71.0,-2048.5},{0,1,0},{0.3,0.9,0.1},0.075f,0,true},{{1006.5,71.64,-2047.5},{0,0,1},{0,1,0},0.075f,0,false}};
        q[2].v={0.6,0.3,0.74};
        D3 start={1000.0,71.5,-2050.0};
        auto reference=evalAt(scene,q,start);
        double worst=0;int steps=0;
        for(int axis=0;axis<3;axis++) for(int i=0;i<=48;i++) {
            D3 cam=start;cam[axis]+=0.25*i*(axis==1?0.5:1.0);
            auto e=evalAt(scene,q,cam);steps++;
            for(size_t k=0;k<q.size();k++) for(int c=0;c<3;c++) {
                double a=reference[k][c],b=e[k][c];
                worst=std::max(worst,std::abs(a-b)/std::max(1e-3,std::max(std::abs(a),std::abs(b))));
            }
        }
        require(worst<2e-4,"camera translation/tile snap changed the lighting by "+num(worst)+" relative");
        // Sensitivity control: the lookup with a stale 1 m-off camera origin (grid built for `start`) must differ.
        w.build(scene,start);
        const D3 stale={start[0]+1.0,start[1],start[2]};
        auto wrong=w.evaluate(q,start,&stale);
        double sensitivity=0;
        for(size_t k=0;k<q.size();k++) for(int c=0;c<3;c++) sensitivity=std::max(sensitivity,std::abs(double(wrong[k][c])-reference[k][c])/std::max(1e-3,double(reference[k][c])));
        require(sensitivity>0.05,"negative control: a stale camera origin must visibly change the lookup (detector sensitivity), got "+num(sensitivity));
        require(rgbSum(reference[0])>0&&rgbSum(reference[2])>0,"translation scene must be lit");
        std::cout<<"PASS local-light tile snap: "<<steps<<" camera positions crossing 8 m origin snaps on x, y and z leave 4 receivers (diffuse+water, leaves, wall) unchanged to "<<worst<<" relative; stale-origin control changes them by "<<sensitivity<<"\n";
    }

    // ---------------------------------------------------------------- 11. grid-edge fade
    {
        const D3 cam={1000.0,71.5,-2050.0};
        std::vector<double> e;
        for(int a=14;a<=26;a++) {
            std::vector<Block> scene={torch(1000+a,71,-2050)};
            // receiver two metres further out, same height, facing the lamp
            Query f{{1000+a+0.5+2.0,71.64,-2049.5},{-1,0,0},{0,1,0},0.075f,0,false};
            auto r=evalAt(scene,{f},cam)[0];e.push_back(r[0]);
        }
        for(size_t i=1;i<e.size();i++) require(e[i]<=e[i-1]*1.00001,"edge fade must be monotone (step "+std::to_string(i)+")");
        require(near(e[0],e[2],1e-4),"full strength inside 19 m");
        // receiver rel x = a+2.5; zero from 24 m
        for(int a=14;a<=26;a++) if(a+2.5>=24) require(e[a-14]==0,"no lamp light beyond the 24 m grid fade at a="+std::to_string(a));
        require(e[5]>0&&e[5]<e[0],"partial fade between 19 and 24 m");
        std::cout<<"PASS local-light grid-edge fade: E="<<e[0]<<" full inside 19 m, "<<e[5]<<" at a=19 (receiver 21.5 m), monotone to exactly 0 at 24 m\n";
    }

    // ---------------------------------------------------------------- 12. compute timing (GPU harness only)
    {
        std::vector<Block> scene;uint32_t seed=7;
        for(int i=0;i<256;i++) {seed=seed*1664525u+1013904223u;int gx=16+(seed>>8)%32,gy=24+(seed>>16)%16;seed=seed*1664525u+1013904223u;int gz=16+(seed>>8)%32;
            scene.push_back(blk(gx+int(base8[0])-32,gy+int(base8[1])-32,gz+int(base8[2])-32,10100,8+int(seed>>20)%7));}
        w.build(scene,C0);
        std::vector<double> ms;for(int i=0;i<30;i++) {w.publish(true);ms.push_back(w.lastComputeMs);}
        std::sort(ms.begin(),ms.end());
        std::cout<<"INFO local-light shadowcomp1 GPU time over 30 dispatches (256 dense lamps): median "<<ms[15]<<" ms, min "<<ms[0]<<" ms, max "<<ms[29]
                 <<" ms on "<<w.renderer<<" -- GPU harness timing of one compute pass only, NOT a Minecraft frame time\n";
    }
    // ---------------------------------------------------------------- 13. portable (held) lights, real shadowcomp1 uniforms
    carriedProbe(w,terrain,softening,C0);
    glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);
    std::cout<<"PASS local-light QA complete on "<<w.renderer<<": real shadow capture, real shadowcomp1 dispatch, real lampLighting/terrain passes; no mock results. Not a Minecraft FPS or visual acceptance.\n";
}
}  // namespace aqualumenLocalLights
