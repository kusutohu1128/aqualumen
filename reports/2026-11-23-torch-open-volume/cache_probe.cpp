// Drive the packaged compute programs across consecutive frames. The input
// bitmaps are synthetic. The reference scans the original list of blockers.
#define main aqualumenFullCheckMain
#include "../../tools/glcheck.cpp"
#undef main
using Point=std::array<int,3>;

static void context() {
    auto platform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    EGLDisplay display=platform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
    if(!eglInitialize(display,nullptr,nullptr)) {
        auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
        EGLDeviceEXT device; EGLint count=0;
        if(!query || !query(1,&device,&count) || count==0) throw std::runtime_error("no EGL device");
        display=platform(EGL_PLATFORM_DEVICE_EXT,device,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("EGL device init");
    }
    if(!eglBindAPI(EGL_OPENGL_API)) throw std::runtime_error("no GL");
    EGLint attr[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
    EGLConfig cfg; EGLint n=0;
    if(!eglChooseConfig(display,attr,&cfg,1,&n) || !n) throw std::runtime_error("no EGL config");
    EGLint p[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
    EGLSurface s=eglCreatePbufferSurface(display,cfg,p);
    EGLint c[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
    EGLContext ctx=eglCreateContext(display,cfg,EGL_NO_CONTEXT,c);
    if(!eglMakeCurrent(display,s,s,ctx)) throw std::runtime_error("EGL current");
}
static int linear(Point p,int width) { return p[0]+width*(p[2]+width*p[1]); }
static Point add(Point a,Point b,int sign=1) {
    for(int i=0;i<3;i++) a[i]+=sign*b[i];
    return a;
}
static Point ring(Point v,int mask) { for(auto &c:v) c&=mask; return v; }
static GLuint image(int unit,int channels,int w,int h) {
    GLenum format=channels==1?GL_R32F:GL_RGBA32F;
    GLuint id; glGenTextures(1,&id);glBindTexture(GL_TEXTURE_2D,id);
    glTexStorage2D(GL_TEXTURE_2D,1,format,w,h);
    glBindImageTexture(unit,id,0,GL_FALSE,0,GL_READ_WRITE,format);
    return id;
}
static void run(GLuint program,int groupsY,int groupsZ,Point camera) {
    glUseProgram(program);
    glUniform1i(glGetUniformLocation(program,"lampFieldImage"),0);
    glUniform1i(glGetUniformLocation(program,"lampListImage"),1);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),camera[0]+.125f,camera[1]+.5f,camera[2]+.75f);
    glDispatchCompute(8,groupsY,groupsZ);
    glMemoryBarrier(GL_ALL_BARRIER_BITS);
}
struct Block {Point world; bool partial;};
struct Light {Point world; int kind;};
static std::array<float,3> emitter(Light l) {
    // Floor torch, north-wall torch and sea lantern, as encoded by lampOffset.
    return {l.world[0]+.5f,l.world[1]+(l.kind==1?.64f:l.kind==2?.84f:.5f),
            l.world[2]+(l.kind==2?.71f:.5f)};
}
int main(int argc,char** argv) try {
    if(argc!=2) throw std::runtime_error("expected extracted shader directory");
    context();
    fs::path root=argv[1];
    auto reset=compute(root/"setup2.csh",root), changes=compute(root/"shadowcomp5.csh",root), build=compute(root/"shadowcomp6.csh",root);
    auto field=image(0,1,512,2720),list=image(1,4,16,512);
    float poison=37.;
    glClearTexImage(field,0,GL_RED,GL_FLOAT,&poison);
    run(reset,1,1,{0,0,0});
    std::cout<<"renderer "<<glGetString(GL_RENDERER)<<"\n";
    Point camera={-18,65,-2};
    std::vector<Light> lights={{{-17,64,-1},1},{{-21,66,4},2}};
    std::vector<Block> blocks={{{-15,63,-4},false},{{-14,64,4},true}};
    auto frame=[&](const char *name) {
        Point origin;
        for(int i=0;i<3;i++) origin[i]=int(std::floor(camera[i]/8.))*8-32;
        std::vector<float> bricks(32768,0.f),records(16*512*4,0.f),result(512*2720);
        for(const auto &b:blocks) {
            auto pos=add(b.world,origin,-1);
            if(*std::min_element(pos.begin(),pos.end())<0 || *std::max_element(pos.begin(),pos.end())>63) continue;
            int voxel=linear(ring(pos,1),2);
            for(auto &n:pos) n/=2;
            auto &w=bricks[linear(pos,32)];
            w=float(int(w)|(1<<(voxel+(b.partial?8:0))));
        }
        std::vector<std::vector<Light>> perTile(512);
        for(int y=0;y<8;y++) for(int z=0;z<8;z++) for(int x=0;x<8;x++) {
            int row=linear({x,y,z},8);
            for(auto l:lights) {
                auto e=emitter(l);float dist=0;
                for(int a=0;a<3;a++) {
                    e[a]-=origin[a];
                    float d=std::max(0.f,std::abs(e[a]-(Point{x,y,z}[a]*8+4.f))-4.f);
                    dist+=d*d;
                }
                if(dist>=196.f) continue;
                perTile[row].push_back(l);
                int i=(row*16+int(perTile[row].size()))*4;
                for(int a=0;a<3;a++) records[i+a]=e[a];
                records[i+3]=14*64+l.kind;
            }
            records[64*row]=perTile[row].size();
        }
        glBindTexture(GL_TEXTURE_2D,field);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,2048,512,64,GL_RED,GL_FLOAT,bricks.data());
        glBindTexture(GL_TEXTURE_2D,list);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,512,GL_RGBA,GL_FLOAT,records.data());
        glMemoryBarrier(GL_ALL_BARRIER_BITS);run(changes,8,8,camera);run(build,8,8,camera);
        glBindTexture(GL_TEXTURE_2D,field);glGetTexImage(GL_TEXTURE_2D,0,GL_RED,GL_FLOAT,result.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("compute or readback error");
        int active=0,hits=0,reused=0;
        for(int y=0;y<64;y++) for(int z=0;z<64;z++) for(int x=0;x<64;x++) {
            const Point cell={x,y,z},world=add(cell,origin),tile={x/8,y/8,z/8};
            const auto& lamps=perTile[linear(tile,8)];
            if(lamps.empty()) continue;
            Point ringTile=ring(world,63);
            for(int &n:ringTile) n/=8;
            bool cached=result[2688*512+linear(ringTile,8)*32+18]==0;
            int mask=int(result[2112*512+linear(ring(world,63),64)]);
            for(size_t i=0;i<lamps.size();i++) {
                auto l=lamps[i];auto e=emitter(l);float d2=0;
                Point lo,hi;
                for(int a=0;a<3;a++) {
                    float d=std::max(0.f,std::abs(e[a]-world[a]-.5f)-.5f);d2+=d*d;
                    float radius=l.kind==16?.42f:.13f;
                    lo[a]=std::min(world[a],int(std::floor(e[a]-radius-.0001f)));
                    hi[a]=std::max(world[a],int(std::floor(e[a]+radius+.0001f)));
                }
                bool clear=d2<=14.1f*14.1f;
                for(int a=0;a<3;a++) if(lo[a]<origin[a] || hi[a]>=origin[a]+64) clear=false;
                for(const auto& b:blocks) {
                    bool inside=true;
                    for(int a=0;a<3;a++) inside=inside && b.world[a]>=lo[a] && b.world[a]<=hi[a];
                    if(inside) clear=false;
                }
                if(clear!=bool(mask&(1<<i))) throw std::runtime_error(std::string(name)+" stale or missing cache bit");
                active++;hits+=clear;reused+=clear && cached;
            }
        }
        std::cout<<name<<" "<<active<<" "<<hits<<" "<<reused<<"\n";
        return reused;
    };
    if(frame("initial")!=0 || frame("still")==0) throw std::runtime_error("cache did not persist");
    blocks.push_back({{-18,64,0},false});frame("trunk-added");
    blocks.back().partial=true;frame("opaque-to-glass");
    blocks.pop_back();frame("trunk-removed");
    std::swap(lights[0],lights[1]);frame("slots-reordered");
    lights.pop_back();frame("torch-removed");
    lights.clear();frame("dark");
    blocks.push_back({{-15,64,1},true});frame("leaf-edited-in-dark");
    lights.push_back({{-17,64,-1},1});frame("torch-returned");
    lights[0].kind=16;frame("larger-emitter");
    camera[0]+=8;frame("across-tile");
    camera[0]+=64;for(auto &l:lights) l.world[0]+=64;frame("ring-address-reused");
    camera[0]-=72;lights[0].world[0]-=64;frame("return");
    return 0;
} catch(const std::exception &e) {std::cerr<<e.what()<<"\n";return 1;}
