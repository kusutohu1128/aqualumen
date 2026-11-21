// NEW TEST actual four-stage MAIN, both supported source contributions.
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
namespace retainedRgbMain {
#include "water_supported_main_red.cpp"
}
namespace priorRgb=retainedRgbMain::supportedMain;
namespace gh=retainedRgbMain::ghPhase;
namespace old=priorRgb::old;
namespace sun=priorRgb::sun;
namespace prior=priorRgb::prior;
namespace inherited=priorRgb::inherited;
namespace fs=std::filesystem;
int main(int argc,char** argv) {try {
    gh::require(argc==3,"usage: water_supported_rgb_main SOURCES NEW_OUTPUT");
    fs::path sources=argv[1],out=argv[2];
    gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;
    std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual RTX3080Ti required");
    std::array<std::string,3> geometry;
    for(int i=0;i<3;++i){geometry[i]=old::readText(sources/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(gh::light::digest(geometry[i])==prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);}
    const std::array<std::string,7> roles={"zero","air","water","both","disabled","unknown","invalid"};
    std::array<GLuint,7> programs;std::array<std::string,7> fragments;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-supported-rgb-main-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"size\":"<<gh::size<<",\"programs\":[";
    for(int role=0;role<7;++role){fragments[role]=old::readText(sources/(roles[role]+".fsh"));
        old::writeText(out/(roles[role]+".fsh"),fragments[role]);if(role)report<<',';
        programs[role]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[role]}},roles[role],report);}
    sun::Fixture fixture;const auto dir=out/"matched-Iris-callsite";gh::require(fs::create_directory(dir),"NEW case required");
    fixture.scene(2,0,true,dir);
    report<<"],\"sourceQueries\":[";gh::tracer::Sources query;query.geometry=geometry;
    for(int i=1;i<7;++i){if(i>1)report<<',';sun::queriedSources(report,{programs[0],programs[i]},query,{fragments[0],fragments[i]});}
    report<<"],\"comparisons\":[";bool first=true,controls=true;
    auto compare=[&](const std::string& name,const auto& a,const auto& b){controls=inherited::exact(report,first,name,a,b)&&controls;};
    std::array<old::Capture,7> frames;
    std::array<std::vector<float>,8> inputs;
    for(int role=0;role<7;++role){frames[role]=prior::capture(fixture,programs[role],1,true,dir,roles[role]);
        auto repeat=prior::capture(fixture,programs[role],1,true,dir,roles[role]+"-repeat");
        for(int slot=0;slot<8;++slot)compare(roles[role]+"-repeat-slot"+std::to_string(slot),frames[role].images[slot],repeat.images[slot]);
        compare(roles[role]+"-repeat-depth",frames[role].depth,repeat.depth);
        auto folder=dir/(roles[role]+"-actual-inputs");gh::require(fs::create_directory(folder),"NEW input directory required");
        gh::drawState(fixture,programs[role],true,folder);auto actual=sun::snapshotInputs(fixture,programs[role],folder);
        if(role){for(int unit=0;unit<8;++unit)compare(roles[role]+"-source-input"+std::to_string(unit),actual[unit],inputs[unit]);
            compare(roles[role]+"-TES-exact",frames[role].images[4],frames[0].images[4]);
            compare(roles[role]+"-depth-exact",frames[role].depth,frames[0].depth);
            if(role!=6)for(int slot=2;slot<4;++slot)compare(roles[role]+"-raw-input-slot"+std::to_string(slot),frames[role].images[slot],frames[0].images[slot]);
        }else inputs=actual;
    }
    const int p=4*((gh::size/2)*gh::size+gh::size/2);
    const std::array<float,3> n={-.024761740118265152f,-.9978660345077515f,.06041766330599785f};
    const std::array<float,3> v={-.21253617107868195f,-.6171247363090515f,-.7576183080673218f};
    const std::array<float,3> c={.006807451602071524f,.0027949956711381674f,.002802651608362794f};
    bool numeric=true;
    report<<"],\"selected\":[";
    for(int role=0;role<7;++role){if(role)report<<',';
        for(int j=0;j<3;++j)gh::require(frames[role].images[1][p+j]==n[j]&&frames[role].images[2][p+j]==v[j]&&frames[role].images[3][p+j]==(role==6?0.f:c[j]),"Matched actual n/v/C or explicit invalid-control bits differ");
        gh::require(frames[role].images[2][p+3]==(role==6?0.f:1.f)&&frames[role].images[3][p+3]==1.333f,"Prepared input class or eta changed");
        gh::require(frames[role].images[5][p+1]==(role<4?1.f:0.f),"Interface application inconsistent");
        const double expectedR=(role==1||role==3)?.25*.024413612290197072:0;
        const double expectedG=(role==2||role==3)?.125*.9686803269959403:0;
        if(role<4){numeric=numeric&&std::abs(frames[role].images[0][p]-expectedR)<=.25*6.882722458039415e-6
            &&std::abs(frames[role].images[0][p+1]-expectedG)<=.125*(2e-6+2e-4*.9686803269959403)
            &&frames[role].images[0][p+2]==0;}
        report<<"{\"role\":"<<old::quote(roles[role])<<",\"C0\":";
        gh::angular::four(report,&frames[role].images[0][p]);report<<",\"status\":";gh::angular::four(report,&frames[role].images[5][p]);
        report<<",\"transmitted\":";gh::angular::four(report,&frames[role].images[6][p]);report<<",\"reflected\":";gh::angular::four(report,&frames[role].images[7][p]);report<<'}';
    }
    report<<"],\"controlsPassed\":"<<(controls?"true":"false")<<",\"sourceResponseGatesPassed\":"<<(numeric?"true":"false")
        <<",\"scope\":\"Actual original four-stage MAIN, one native TEST evaluation pixel and controlled nonblack air/water sources. Full RGB single-scattering interface, not added tag. No actual source-trace/Sun48/Iris/motion or whole-frame causal acceptance.\","
        "\"IrisAccepted\":false,\"visualAccepted\":false,\"shippingAccepted\":false}\n";
    old::writeText(out/"result.json",report.str());old::writeText(out/"probe-source.cpp",old::readText("tools/water_supported_rgb_main.cpp"));
    for(auto program:programs)glDeleteProgram(program);
    std::cout<<(controls&&numeric?"GREEN":"RED")<<" actual-MAIN supported R+T source responses\n";return controls&&numeric?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
