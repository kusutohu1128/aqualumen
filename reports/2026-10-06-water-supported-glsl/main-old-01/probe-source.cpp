// TEST-only actual original four-stage water MAIN source-control regression.
// Reuse sealed fixture/source readers; never edit or regenerate old evidence.
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
namespace retainedSupportedMain {
#include "water_legacy_branch_probe.cpp"
}
namespace legacyBranch=retainedSupportedMain::legacyBranch;
namespace ghPhase=retainedSupportedMain::ghPhase;

namespace supportedMain {
namespace old=legacyBranch::old;
namespace sun=legacyBranch::sun;
namespace prior=legacyBranch::prior;
namespace inherited=legacyBranch::inherited;
namespace fs=std::filesystem;
using ghPhase::require;

int run(const fs::path& root,const fs::path& out) {
    auto source=legacyBranch::load(root);
    require(!fs::exists(out)&&!fs::is_symlink(out),"NEW evidence directory required");
    require(fs::create_directories(out),"Cannot create evidence directory");
    old::Context context;
    std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual NVIDIA RTX3080Ti required");
    sun::Fixture fixture;
    std::ostringstream report;report<<std::setprecision(17)
        <<"{\"schema\":\"aqualumen-supported-original-main-red-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"size\":"<<ghPhase::size<<",\"programs\":[";
    // First actual Iris input is an admitted positive control; second is the
    // observed rejected input. Only call-site n/v and interface air source vary.
    const std::array<std::string,2> args={
        "vec3(-0.023401282727718353,-0.9980668425559998,0.05757466331124306),vec3(-0.19426403939723969,-0.6376394033432007,-0.745437741279602)",
        "vec3(-0.024761740118265152,-0.9978660345077515,0.06041766330599785),vec3(-0.21253617107868195,-0.6171247363090515,-0.7576183080673218)"};
    const std::array<std::array<float,3>,2> ns={{{-.023401282727718353f,-.9980668425559998f,.05757466331124306f},
        {-.024761740118265152f,-.9978660345077515f,.06041766330599785f}}};
    const std::array<std::array<float,3>,2> vs={{{-.19426403939723969f,-.6376394033432007f,-.745437741279602f},
        {-.21253617107868195f,-.6171247363090515f,-.7576183080673218f}}};
    const std::array<float,3> cs={.006807451602071524f,.0027949956711381674f,.002802651608362794f};
    std::array<std::array<GLuint,2>,2> programs;
    std::array<std::array<std::string,2>,2> fragments;
    bool comma=false;
    for(int input=0;input<2;++input)for(int tag=0;tag<2;++tag) {
        auto text=inherited::replace(source.fs[1][1],
            "color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),",
            "color=waterResidualInterface(color,"+args[input]+",worldPosition,viewPos,max(footprint*1.25,0.035),");
        text=inherited::replace(text,"vec3 airSky=environmentSkyRadiance(skyRay,colortex6);",
            "vec3 airSky="+std::string(tag?"vec3(0.25,0.0,0.0)":"vec3(0.0)")+";");
        const std::string label="input"+std::to_string(input)+(tag?"-red":"-zero");
        fragments[input][tag]=text;old::writeText(out/(label+".fsh"),text);
        if(comma)report<<',';comma=true;
        programs[input][tag]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},
            {GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},
            {GL_FRAGMENT_SHADER,text}},label,report);
    }
    for(int i=0;i<3;++i)old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),source.geometry[i]);
    report<<"],\"cases\":[";
    bool controls=true,optical=true;
    for(int input=0;input<2;++input) {
        const auto dir=out/("input"+std::to_string(input));require(fs::create_directory(dir),"NEW case required");
        fixture.scene(2,0,true,dir);
        if(input)report<<',';report<<"{\"input\":"<<input<<",\"sourceQueries\":[";
        ghPhase::tracer::Sources query;query.geometry=source.geometry;
        sun::queriedSources(report,{programs[input][0],programs[input][1]},query,fragments[input]);
        report<<"],\"comparisons\":[";bool first=true;
        auto compare=[&](const std::string& label,const auto& a,const auto& b){controls=inherited::exact(report,first,label,a,b)&&controls;};
        std::array<old::Capture,2> frames;
        std::array<std::vector<float>,8> inputs;
        for(int tag=0;tag<2;++tag) {
            const std::string label=tag?"red":"zero";
            frames[tag]=prior::capture(fixture,programs[input][tag],1,true,dir,label);
            auto repeat=prior::capture(fixture,programs[input][tag],1,true,dir,label+"-repeat");
            for(int slot=0;slot<8;++slot)compare(label+"-slot"+std::to_string(slot)+"-repeat",frames[tag].images[slot],repeat.images[slot]);
            compare(label+"-depth-repeat",frames[tag].depth,repeat.depth);
            const auto inputDir=dir/(label+"-actual-inputs");require(fs::create_directory(inputDir),"NEW inputs required");
            ghPhase::drawState(fixture,programs[input][tag],true,inputDir);
            auto actual=sun::snapshotInputs(fixture,programs[input][tag],inputDir);
            if(tag)for(int unit=0;unit<8;++unit)compare("source-pair-input"+std::to_string(unit),inputs[unit],actual[unit]);
            else inputs=actual;
        }
        for(int slot=1;slot<8;++slot)compare("source-pair-ledger"+std::to_string(slot),frames[0].images[slot],frames[1].images[slot]);
        compare("source-pair-depth",frames[0].depth,frames[1].depth);
        const int p=4*((ghPhase::size/2)*ghPhase::size+ghPhase::size/2);
        for(int tag=0;tag<2;++tag)for(int j=0;j<3;++j)
            require(frames[tag].images[1][p+j]==ns[input][j]&&frames[tag].images[2][p+j]==vs[input][j]
                &&frames[tag].images[3][p+j]==cs[j],"Actual MAIN call-site n/v/C bits differ");
        require(frames[0].images[1][p+3]==1,"Actual MAIN call inactive");
        if(input)require(frames[0].images[5][p]==256&&frames[0].images[4][p+1]==0,"Original failed admission absent");
        else require(frames[0].images[4][p+1]==1,"Admitted positive source control inactive");
        const double delta=double(frames[1].images[0][p])-frames[0].images[0][p];
        for(int q=0;q<ghPhase::size*ghPhase::size*4;q+=4)
            require(frames[0].images[0][q+1]==frames[1].images[0][q+1]
                &&frames[0].images[0][q+2]==frames[1].images[0][q+2],"Red source changed green/blue");
        if(input) optical=delta>0.25*(0.024413612290197072-6.882722458039415e-6);
        else require(delta>0,"Nonvacuous positive air-source control absent");
        report<<"],\"centerRedResponse\":"<<delta<<",\"legacyApplied\":"<<frames[0].images[4][p+1]
            <<",\"firstFailureMask\":"<<frames[0].images[5][p]<<"}";
    }
    report<<"],\"controlsPassed\":"<<(controls?"true":"false")
        <<",\"opticalRegressionPassed\":"<<(optical?"true":"false")
        <<",\"scope\":\"Original four-stage MAIN; only interface air-source zero/red and matched observed n/v call arguments. C matches without override. Not a whole-Iris replay or full physical closure.\","
        "\"visualAccepted\":false,\"shippingAccepted\":false}\n";
    old::writeText(out/"result.json",report.str());
    old::writeText(out/"probe-source.cpp",old::readText("tools/water_supported_main_red.cpp"));
    for(auto row:programs)for(auto program:row)glDeleteProgram(program);
    std::cout<<(controls&&optical?"GREEN":"RED")<<" original-MAIN supported-air source regression\n";
    return controls&&optical?0:1;
}
}
int main(int argc,char** argv) {try {
    if(argc!=3)throw std::runtime_error("usage: water_supported_main_red CANONICAL_SOURCES NEW_OUTPUT");
    return supportedMain::run(argv[1],argv[2]);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
