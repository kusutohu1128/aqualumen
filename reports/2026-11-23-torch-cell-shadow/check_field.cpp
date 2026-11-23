// The build script imports the shared EGL and light-grid helpers from the first
// cache probe. Test both the persistent path and a fresh field on each edit.
#include "original_cache_helpers.h"

static constexpr int width=512, height=15008;
static void demand(bool ok, const std::string &message) {
    if(!ok) throw std::runtime_error(message);
}

struct RayCheck { bool any=false; bool common=false; };
static RayCheck crossings(Point receiver, Light light, Block block) {
    // Independent double-precision segment/cube slab intersections. A common
    // interior t on all 64 corner rays places their entire convex hull inside.
    auto source=emitter(light);
    double radius=light.kind==16?.42:.13, commonEnter=0.,commonLeave=1.;
    bool any=false;
    for(int start=0;start<8;start++) for(int end=0;end<8;end++) {
        double enter=0., leave=1.;
        for(int axis=0;axis<3;axis++) {
            double a=receiver[axis]+((start>>axis)&1);
            double b=source[axis]+(((end>>axis)&1)?radius:-radius);
            double lo=block.world[axis],hi=lo+1.;
            if(std::abs(b-a)<1e-12) {
                if(a<=lo || a>=hi) { enter=1.; leave=0.; break; }
                continue;
            }
            double t1=(lo-a)/(b-a),t2=(hi-a)/(b-a);
            enter=std::max(enter,std::min(t1,t2));
            leave=std::min(leave,std::max(t1,t2));
            if(leave<=enter) break;
        }
        any|=leave>enter+1e-7;
        commonEnter=std::max(commonEnter,enter);
        commonLeave=std::min(commonLeave,leave);
    }
    return {any,commonLeave>commonEnter+1e-7};
}

static void writeTex(GLuint id,GLenum format,int y,int w,int h,const std::vector<float>& data) {
    glBindTexture(GL_TEXTURE_2D,id);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,y,w,h,format,GL_FLOAT,data.data());
}

static std::vector<float> readBand(GLuint id,int y,int h) {
    std::vector<float> out(width*h);
    glGetTextureSubImage(id,0,0,y,0,width,h,1,GL_RED,GL_FLOAT,out.size()*sizeof(float),out.data());
    return out;
}

int main(int argc,char** argv) try {
    demand(argc==2,"expected extracted shader directory");
    context(); fs::path root=argv[1];
    auto changes=compute(root/"shadowcomp5.csh",root),build=compute(root/"shadowcomp6.csh",root);
    auto warm=image(0,1,width,height),cold=image(0,1,width,height),list=image(1,4,16,512);
    float zero=0.f;
    glClearTexImage(warm,0,GL_RED,GL_FLOAT,&zero);
    std::cout<<"renderer "<<glGetString(GL_RENDERER)<<"\n";
    Point camera={-18,65,-2};
    std::vector<Light> lights={{{-16,64,-1},1},{{-19,65,3},2}};
    std::vector<Block> blocks={{{-17,64,-1},false},{{-20,64,-1},true},{{-19,65,1},false}};
    int seenDark=0,seenOpen=0;
    auto frame=[&](const std::string &label) {
        Point origin; for(int i=0;i<3;i++) origin[i]=int(std::floor(camera[i]/8.))*8-32;
        std::vector<float> bricks(32768),records(16*512*4);
        for(auto b:blocks) {
            auto p=add(b.world,origin,-1);
            if(*std::min_element(p.begin(),p.end())<0 || *std::max_element(p.begin(),p.end())>63) continue;
            int bit=linear(ring(p,1),2)+(b.partial?8:0);
            for(auto& k:p) k/=2;
            auto& w=bricks[linear(p,32)]; w=float(int(w)|(1<<bit));
        }
        std::vector<std::vector<Light>> tiles(512);
        for(int y=0;y<8;y++) for(int z=0;z<8;z++) for(int x=0;x<8;x++) {
            Point tile={x,y,z};int row=linear(tile,8);
            for(auto l:lights) {
                auto e=emitter(l);float ds=0.;
                for(int k=0;k<3;k++) {
                    e[k]-=origin[k]; float d=std::max(0.f,std::abs(e[k]-(tile[k]*8+4.f))-4.f);ds+=d*d;
                }
                if(ds>=196.f) continue;
                tiles[row].push_back(l);
                int i=(row*16+int(tiles[row].size()))*4;
                for(int k=0;k<3;k++) records[i+k]=e[k];
                records[i+3]=14*64+l.kind;
            }
            records[row*64]=tiles[row].size();
        }
        writeTex(list,GL_RGBA,0,16,512,records);
        glClearTexImage(cold,0,GL_RED,GL_FLOAT,&zero);
        for(auto field:{warm,cold}) {
            writeTex(field,GL_RED,2048,512,64,bricks);
            glBindImageTexture(0,field,0,GL_FALSE,0,GL_READ_WRITE,GL_R32F);
            glMemoryBarrier(GL_ALL_BARRIER_BITS);
            run(changes,8,8,camera);run(build,8,8,camera);
        }
        auto kept=readBand(warm,2112,512), fresh=readBand(cold,2112,512), tags=readBand(warm,2688,32);
        // Only live slots can be consumed by terrain. Unused records may retain
        // arbitrary bytes, and second boxes are read only for negative records.
        int usedRows=std::max(1,int(lights.size()))*512;
        auto boxes=readBand(warm,2720,usedRows), newBoxes=readBand(cold,2720,usedRows);
        auto pairs=readBand(warm,8864,usedRows), newPairs=readBand(cold,8864,usedRows);
        int active=0,dark=0,open=0,reused=0,physical=0;
        for(int y=0;y<64;y++) for(int z=0;z<64;z++) for(int x=0;x<64;x++) {
            Point p=add({x,y,z},origin),tileRing=ring(p,63);
            for(auto &k:tileRing) k/=8;
            const auto &lamps=tiles[linear({x/8,y/8,z/8},8)];
            int addr=linear(ring(p,63),64),mask=int(kept[addr]);
            if(lamps.empty()) continue;
            demand(mask==int(fresh[addr]),label+" differs from a fresh rebuild");
            for(int i=0;i<int(lamps.size());i++) {
                int state=(mask>>i)&4097; active++;
                if(state==4096) {
                    int box=i*512*512+addr;
                    demand(boxes[box]==newBoxes[box] && boxes[box]!=0.f,label+" stale box");
                    if(boxes[box]<0.f) demand(pairs[box]==newPairs[box] && pairs[box]>0.f,label+" stale second box");
                }
                bool isDark=state==4097,isOpen=state==1;
                dark+=isDark;open+=isOpen;
                reused+=tags[linear(tileRing,8)*32+18]==0.f;
                if(!isDark && (!isOpen || addr%23!=0)) continue;
                bool solidProof=false;
                for(auto b:blocks) {
                    auto test=crossings(p,lamps[i],b);
                    demand(!isOpen || !test.any,label+" clear cell crosses a blocker");
                    solidProof|=!b.partial && test.common;
                }
                demand(!isDark || solidProof,label+" dark cell lacks a common solid slice");
                physical++;
            }
        }
        demand(glGetError()==GL_NO_ERROR,label+" GL error");
        if(label=="initial") demand(dark>0 && open>0 && reused==0,label+" fixture coverage");
        if(label=="still") demand(reused==active && reused>0,label+" cache persistence");
        if(label=="no-lights" || label=="edited-in-dark") demand(active==0,label+" inactive slots");
        seenOpen+=open;seenDark+=dark;
        std::cout<<label<<" "<<active<<" "<<open<<" "<<dark<<" "<<reused<<" "<<physical<<std::endl;
    };
    frame("initial");frame("still");
    blocks[0].partial=true;frame("trunk-to-glass");
    blocks.erase(blocks.begin());frame("trunk-removed");
    blocks.push_back({{-17,64,-1},false});frame("replanted");
    std::swap(lights[0],lights[1]);frame("reordered");
    lights.pop_back();frame("one-removed");
    lights[0].kind=1;frame("wall-to-floor");
    lights.clear();frame("no-lights");
    blocks.push_back({{-18,64,-1},true});frame("edited-in-dark");
    lights.push_back({{-16,64,-1},1});frame("relit");
    lights[0].kind=16;frame("larger-source");
    lights[0].kind=1;camera[0]+=8;frame("across-tile");
    camera[0]+=64;lights[0].world[0]+=64;frame("ring-lap");
    camera[0]-=72;lights[0].world[0]-=64;frame("return");
    demand(seenDark && seenOpen,"missing certificate coverage");
    return 0;
} catch(const std::exception &e) { std::cerr<<e.what()<<"\n";return 1; }
