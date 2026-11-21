// TEST actual original four-stage MAIN with real source textures/tracers.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <cmath>
#include <array>
#include <iomanip>
#include <string>
#include <regex>
#include <limits>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <chrono>
#include <map>
#include <set>
#include <openssl/sha.h>
namespace retainedSourceMain {
#include "water_supported_rgb_main.cpp"
}
namespace gh=retainedSourceMain::gh;
namespace old=retainedSourceMain::old;
namespace sun=retainedSourceMain::sun;
namespace prior=retainedSourceMain::prior;
namespace inherited=retainedSourceMain::inherited;
namespace fs=std::filesystem;
const std::array<std::string,5> roles={"enabled","disabled","strict","invalid","ledger"};
const std::array<std::string,10> cases={"zero","diffuse","sun","rain","sun-absent","opaque-narrow","cave","moon","wide-sun","wide-opaque"};

struct Fixture: sun::Fixture {
    std::array<float,3> worldSun={.24f,.15f,.959f};
    void configure(int kind,const fs::path& dir) {
        scene(2,kind==3?.5f:0.f,false,dir);
        if(kind>=8) {
            const float focal=float(1/std::tan(170.*3.14159265358979323846/360.));
            projection[0]=projection[5]=focal;
            inverseProjection[0]=inverseProjection[5]=1/focal;
            glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());
        }
        worldSun=kind==4?std::array<float,3>{0,1,0}:std::array<float,3>{.24f,.15f,.959f};
        if(kind==7)for(auto& a:worldSun)a=-a;
        std::vector<float> sky(64*32*4,0);
        for(std::size_t p=3;p<sky.size();p+=4)sky[p]=1;
        if(kind==1||kind==6)for(int row=0;row<31;++row)for(int x=0;x<64;++x)
            sky[(row*64+x)*4]=.25f;
        if((kind>=2&&kind<=6)||kind>=8) {
            sky[(31*64)*4]=.5f;sky[(31*64)*4+1]=.625f;sky[(31*64)*4+2]=.75f;
        }
        old::Fixture::allocate(samplers[2],GL_RGBA32F,64,32,GL_RGBA,sky.data());
        if(kind==5||kind==9) {
            // Actual planar opaque depth, not callback/source-kind override.
            // Far enough beyond the displaced interface; foreground guard stays.
            const float distance=surface+1.f;
            const float clipZ=projection[10]*(-distance)+projection[14];
            const float depthValue=.5f*(clipZ/distance+1.f);
            std::vector<float> depth(gh::size*gh::size,depthValue);
            old::Fixture::allocate(samplers[3],GL_DEPTH_COMPONENT32F,gh::size,gh::size,
                GL_DEPTH_COMPONENT,depth.data());
            std::vector<float> receiver(gh::size*gh::size*4,0);
            for(std::size_t p=0;p<receiver.size();p+=4){receiver[p+1]=.125f;receiver[p+3]=1.f;}
            old::Fixture::allocate(samplers[1],GL_RGBA32F,gh::size,gh::size,GL_RGBA,receiver.data());
        }
        if(kind==6) {
            auto a=old::vertex(-.9f,surface,-.9f),b=old::vertex(-.9f,surface,.9f);
            auto c=old::vertex(.9f,surface,.9f),d=old::vertex(.9f,surface,-.9f);
            std::vector<old::Vertex> vertices={a,b,c,a,c,d};
            for(auto& v:vertices){v.lightmap[0]=0;v.lightmap[1]=0;}
            upload(vertices,dir/"uploaded-cave-water-vertices.f32");
        }
        old::glOkay("NEW real source fixture");
    }
    void uniforms(GLuint id) {
        sun::Fixture::uniforms(id);
        std::array<float,3> viewSun={};
        for(int row=0;row<3;++row)for(int c=0;c<3;++c)
            viewSun[row]+=old::up[c*4+row]*worldSun[c];
        glUniform3fv(glGetUniformLocation(id,"sunPosition"),1,viewSun.data());
        old::glOkay("actual inclined source uniform");
    }
    old::Capture capture(GLuint id,const fs::path& dir,const std::string& name) {
        uniforms(id);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
        std::array<GLenum,8> buffers={};for(int i=0;i<8;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(8,buffers.data());const float zero[4]={},one=1;
        for(int i=0;i<8;++i)glClearBufferfv(GL_COLOR,i,zero);
        glClearBufferfv(GL_DEPTH,0,&one);glDrawArrays(GL_PATCHES,0,6);
        old::Capture out;
        for(int slot=0;slot<8;++slot) {
            out.images[slot].assign(gh::size*gh::size*4,NAN);glReadBuffer(buffers[slot]);
            glReadPixels(0,0,gh::size,gh::size,GL_RGBA,GL_FLOAT,out.images[slot].data());
            for(float a:out.images[slot])gh::require(std::isfinite(a),"nonfinite actual source MRT");
            old::writeRaw(dir/(name+"-slot"+std::to_string(slot)+".rgba32f"),out.images[slot]);
        }
        out.depth.assign(gh::size*gh::size,NAN);
        glReadPixels(0,0,gh::size,gh::size,GL_DEPTH_COMPONENT,GL_FLOAT,out.depth.data());
        old::writeRaw(dir/(name+"-depth.f32"),out.depth);old::glOkay("actual source draw/readback");
        return out;
    }
    void snapshot(GLuint id,const fs::path& dir) {
        gh::require(fs::create_directory(dir),"NEW source input snapshot");uniforms(id);
        const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0",
            "colortex8","aqualumenBathymetry","colortex7"};
        std::ostringstream report;report<<std::setprecision(17)<<"{\"matrices\":{";
        const char* matrices[]={"gbufferProjection","gbufferProjectionInverse","gbufferModelView","gbufferModelViewInverse"};
        const std::array<old::M4,4> expected={projection,inverseProjection,old::up,old::upInverse};
        for(int i=0;i<4;++i){old::M4 data={};glGetUniformfv(id,glGetUniformLocation(id,matrices[i]),data.data());
            gh::require(data==expected[i],"actual matrix differs");if(i)report<<',';report<<old::quote(matrices[i])<<':';gh::angular::numbers(report,data);}
        report<<"},\"sunPosition\":";std::array<float,3> source={};
        glGetUniformfv(id,glGetUniformLocation(id,"sunPosition"),source.data());gh::angular::numbers(report,source);
        report<<",\"worldSunInput\":";gh::angular::numbers(report,worldSun);
        float actualRain=-1;glGetUniformfv(id,glGetUniformLocation(id,"rainStrength"),&actualRain);
        gh::require(actualRain==rain,"actual rain differs");report<<",\"rainStrength\":"<<actualRain<<",\"samplers\":[";
        for(int unit=0;unit<8;++unit) {
            GLint value=-1,w=0,h=0,format=0;glGetUniformiv(id,glGetUniformLocation(id,names[unit]),&value);
            gh::require(value==unit,"actual named source sampler differs");glActiveTexture(GL_TEXTURE0+unit);
            GLint bound=0;glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);gh::require(GLuint(bound)==samplers[unit],"actual source texture differs");
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
            bool depth=unit==3||unit==4;std::vector<float> data(w*h*(depth?1:4),NAN);
            glGetTexImage(GL_TEXTURE_2D,0,depth?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,data.data());
            old::writeRaw(dir/("input-sampler"+std::to_string(unit)+".f32"),data);
            if(unit)report<<',';report<<"{\"name\":"<<old::quote(names[unit])<<",\"unit\":"<<value
                <<",\"width\":"<<w<<",\"height\":"<<h<<",\"format\":"<<format<<'}';
        }
        report<<"]}\n";old::writeText(dir/"state.json",report.str());old::glOkay("actual source inputs snapshot");
    }
};

int main(int argc,char** argv) {try {
    gh::require(argc==3,"usage: water_supported_sources_main SOURCES NEW_OUTPUT");
    fs::path sources=argv[1],out=argv[2];gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual RTX3080Ti required");
    std::array<std::string,3> geometry;for(int i=0;i<3;++i){geometry[i]=old::readText(sources/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(gh::light::digest(geometry[i])==prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);}
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-supported-sources-main-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<gh::size<<",\"programs\":[";
    std::array<GLuint,5> programs;std::array<std::string,5> fragments;
    for(int i=0;i<5;++i){fragments[i]=old::readText(sources/(roles[i]+".fsh"));old::writeText(out/(roles[i]+".fsh"),fragments[i]);
        if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},roles[i],report);}
    gh::tracer::Sources query;query.geometry=geometry;report<<"],\"sourceQueries\":[";
    for(int i=1;i<5;++i){if(i>1)report<<',';sun::queriedSources(report,{programs[0],programs[i]},query,{fragments[0],fragments[i]});}
    Fixture fixture;report<<"],\"cases\":[";bool exact=true;
    for(int kind=0;kind<int(cases.size());++kind){const auto dir=out/cases[kind];gh::require(fs::create_directory(dir),"NEW case required");fixture.configure(kind,dir);
        if(kind)report<<',';report<<"{\"name\":"<<old::quote(cases[kind])<<",\"selected\":[";
        std::array<old::Capture,5> frames;const int p=4*(128*gh::size+128);
        for(int i=0;i<5;++i){frames[i]=fixture.capture(programs[i],dir,roles[i]);auto again=fixture.capture(programs[i],dir,roles[i]+"-repeat");
            for(int slot=0;slot<8;++slot)exact=(frames[i].images[slot]==again.images[slot])&&exact;
            exact=(frames[i].depth==again.depth)&&exact;
            if(i){exact=(frames[i].images[4]==frames[0].images[4]&&frames[i].depth==frames[0].depth)&&exact;}
            fixture.snapshot(programs[i],dir/(roles[i]+"-actual-inputs"));
            if(i)report<<',';report<<"{\"role\":"<<old::quote(roles[i])<<",\"C0\":";gh::angular::four(report,&frames[i].images[0][p]);
            report<<",\"status\":";gh::angular::four(report,&frames[i].images[5][p]);
            report<<",\"slot1\":";gh::angular::four(report,&frames[i].images[1][p]);
            report<<",\"slot2\":";gh::angular::four(report,&frames[i].images[2][p]);
            report<<",\"slot3\":";gh::angular::four(report,&frames[i].images[3][p]);
            report<<",\"slot6\":";gh::angular::four(report,&frames[i].images[6][p]);
            report<<",\"slot7\":";gh::angular::four(report,&frames[i].images[7][p]);report<<'}';
        }
        exact=(frames[0].images[0]==frames[4].images[0])&&exact;
        exact=(frames[1].images[0]==frames[2].images[0]&&frames[1].images[0]==frames[3].images[0])&&exact;
        report<<"]}";std::cout<<"captured "<<cases[kind]<<std::endl;
    }
    report<<"],\"exactControls\":"<<(exact?"true":"false")<<",\"IrisAccepted\":false,\"visualAccepted\":false,\"shippingAccepted\":false,"
        "\"scope\":\"Actual original four-stage MAIN at one native TEST pixel, actual LUT/cache/depth/C4 and inclined Sun uniforms. Proxies explicit; independent raw/numeric audit required.\"}\n";
    old::writeText(out/"result.json",report.str());old::writeText(out/"probe-source.cpp",old::readText("tools/water_supported_sources_main.cpp"));
    for(auto p:programs)glDeleteProgram(p);std::cout<<(exact?"PASS":"RED")<<" source adapter raw controls\n";return exact?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
