// New TEST only: original four-stage public MAIN, passive legacy branch ledger.
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
namespace retainedLegacyBranch {
#include "water_gh_phase_probe.cpp"
}
namespace ghPhase=retainedLegacyBranch::ghPhase;
namespace legacyBranch {
namespace old=ghPhase::old; namespace sun=ghPhase::sun;
namespace prior=ghPhase::prior; namespace inherited=ghPhase::inherited;
namespace fs=std::filesystem;
using ghPhase::require;
fs::path owned;
std::string strip(std::string source) {
    for(const auto& name:std::array<std::string,11>{"GLOBALS","INPUT","NODE","TRANSMITTED_RECEIVER",
        "REFLECTED_RECEIVER","NOTE","PROTOTYPE","SAVE","RESET","STORE","UNUSED"}) {
        if(name=="UNUSED")continue;
        source=ghPhase::tracer::eraseOne(source,"// AQUALUMEN_WLB_BEGIN:"+name+'\n',"// AQUALUMEN_WLB_END:"+name+'\n');
    }
    require(source.find("AQUALUMEN_WLB_")==std::string::npos,"ledger tags remain");return source;
}
struct Sources {std::array<std::string,3> geometry;std::array<std::array<std::string,5>,2> fs;};
Sources load(const fs::path& root) {
    Sources s;
    for(int i=0;i<3;++i){s.geometry[i]=old::readText(root/("geometry-stage"+std::to_string(i)+".glsl"));
        require(ghPhase::light::digest(s.geometry[i])==prior::geometrySHA[i],"pinned actual geometry expansion differs");}
    const std::array<std::string,2> pins={"4e7150930111ba21c5d210495488e331d7f6987ec8a797153ab3ac60adc859e5","b88b2c6e190227e320db82669d7d087f4fa874d0a433fd9f9079ba0fd15fb4b5"};
    for(int phase=0;phase<2;++phase){const auto stem="phase"+std::to_string(phase?45:0);
        s.fs[phase][0]=old::readText(root/(stem+"-parent.fsh"));require(ghPhase::light::digest(s.fs[phase][0])==pins[phase],"canonical parent digest differs");
        for(int call=0;call<2;++call){s.fs[phase][1+call]=old::readText(root/(stem+(call?"-base.fsh":"-full.fsh")));
            require(strip(s.fs[phase][1+call])==s.fs[phase][0],"compiled ledger source does not recover exact original");
            require(s.fs[phase][1+call].find("WLB_mask|=128;")!=std::string::npos&&s.fs[phase][1+call].find("WLB_mask|=256;")!=std::string::npos,"inactive ledger source");
            const auto anchor=std::string("#version 330 compatibility\n");
            s.fs[phase][3+call]=inherited::replace(s.fs[phase][1+call],anchor,anchor+"#define WLB_NATIVE_EXPORT_TES 1\n");
        }
    }return s;
}
bool accounted(const old::Capture& frame,int p) {
    const auto& n=frame.images[1];const auto& v=frame.images[2];const auto& c=frame.images[3];
    const auto& st=frame.images[4];const auto& m=frame.images[5];const auto& t=frame.images[6];const auto& r=frame.images[7];
    if(m[p+3]==0){for(int slot=1;slot<8;++slot)for(int j=0;j<4;++j)if(frame.images[slot][p+j]!=0)return false;return true;}
    const int mask=int(m[p]),first=int(m[p+1]),node=int(m[p+2]),failures=int(m[p+3])-16;
    if(m[p]!=mask||mask<0||mask>2047||m[p+1]!=first||m[p+2]!=node||m[p+3]!=16+failures||failures<0||failures>9)return false;
    if(n[p+3]!=0&&n[p+3]!=1)return false;
    if(st[p]!=int(mask==0)||st[p+1]!=int(mask==0&&n[p+3]==1))return false;
    if(mask==0){if(first!=0||node!=-2||failures!=0)return false;}
    else if(first<=0||(first&(first-1))!=0||(mask&first)==0)return false;
    if(mask&63){if(node!=-1||first>32)return false;}else if(mask!=0&&(node<0||node>8||failures==0))return false;
    if(mask==0||node==-1){for(int j=0;j<4;++j)if(t[p+j]!=0||r[p+j]!=0)return false;}
    if(node>=0){if(t[p+3]!=0&&t[p+3]!=1)return false;
        if(first==64&&r[p+3]>0)return false;
        if(first==128&&r[p+1]<0)return false;
        if(first==256&&(t[p+3]!=0||t[p+1]>0))return false;
        if((first==512||first==1024)&&st[p+3]<=0)return false;}
    double normN=0,normV=0;for(int j=0;j<3;++j){normN+=double(n[p+j])*n[p+j];normV+=double(v[p+j])*v[p+j];}
    if(std::abs(normN-1)>2e-5||std::abs(normV-1)>2e-5||c[p+3]!=std::abs(n[p+1]))return false;
    return true;
}
int run(const fs::path& sourceRoot,const fs::path& output,bool matchedIris) {
    auto source=load(sourceRoot);
    if(matchedIris) {
        // Same call-site override in parent and all observation roles. Geometry,
        // n/v used by the rest of MAIN, source inputs, and eligibility are intact.
        // Exact binary32 vectors observed at actual Iris (1114,155), phase45 full.
        const std::string anchor="color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),";
        const std::string replacement="color=waterResidualInterface(color,"
            "vec3(-0.024761740118265152,-0.9978660345077515,0.06041766330599785),"
            "vec3(-0.21253617107868195,-0.6171247363090515,-0.7576183080673218),"
            "worldPosition,viewPos,max(footprint*1.25,0.035),";
        for(auto& row:source.fs)for(auto& text:row)text=inherited::replace(text,anchor,replacement);
    }
    require(!fs::exists(output)&&!fs::is_symlink(output),"new native output required");
    require(fs::create_directories(output),"cannot create output");owned=output;
    old::writeText(output/"probe-source.cpp",old::readText("tools/water_legacy_branch_probe.cpp"));
    old::Context context;
    const auto renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    require(renderer&&std::string(renderer).find("RTX 3080 Ti")!=std::string::npos,"actual RTX3080Ti required");
    sun::Fixture fixture;
    const std::array<std::string,5> names={"parent","full","base","full-tes","base-tes"};
    std::array<std::array<GLuint,5>,2> programs={};
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-legacy-branch-native-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<ghPhase::size
        <<",\"matchedIrisCallArguments\":"<<(matchedIris?"true":"false")
        <<",\"fixtureScope\":"<<old::quote(matchedIris?
            "Actual Iris binary32 n/v at1114,155 substituted identically only at original MAIN legacy/Sun call site. Covariance must match actual Iris without override. Not whole-Iris scene replay.":
            "Retained central2/wide90 native production MAIN fixtures; not actual Iris.")
        <<",\"executableSha256\":"<<old::quote(ghPhase::light::digest(old::readText(fs::canonical("/proc/self/exe"))))<<",\"programs\":[";
    bool comma=false;
    for(int phase=0;phase<2;++phase)for(int role=0;role<5;++role){if(comma)report<<',';comma=true;
        const auto label="phase"+std::to_string(phase?45:0)+"-"+names[role];
        old::writeText(output/(label+".fsh"),source.fs[phase][role]);
        programs[phase][role]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},
            {GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.fs[phase][role]}},label,report);}
    for(int i=0;i<3;++i)old::writeText(output/("geometry-stage"+std::to_string(i)+".glsl"),source.geometry[i]);
    report<<"],\"cases\":[";bool accepted=true;
    for(int scenario=0;scenario<(matchedIris?1:2);++scenario){const auto dir=output/(matchedIris?"matched-Iris-callsite":scenario?"wide90":"central2");require(fs::create_directory(dir),"new case required");
        fixture.scene(2,0,true,dir);if(scenario)ghPhase::support::wide90(fixture);
        if(scenario)report<<',';
        report<<"{\"name\":"<<old::quote(dir.filename().string())<<",\"sourceQueries\":[";
        ghPhase::tracer::Sources query;query.geometry=source.geometry;bool firstQuery=true;
        for(int phase=0;phase<2;++phase)for(int role=1;role<5;++role){if(!firstQuery)report<<',';firstQuery=false;
            sun::queriedSources(report,{programs[phase][0],programs[phase][role]},query,{source.fs[phase][0],source.fs[phase][role]});}
        report<<"],\"comparisons\":[";bool first=true;const auto compare=[&](const std::string& label,const auto& a,const auto& b){accepted=inherited::exact(report,first,label,a,b)&&accepted;};
        std::array<std::array<old::Capture,5>,2> frames;
        std::array<std::vector<float>,8> inputReference={};bool haveInputs=false;
        for(int phase=0;phase<2;++phase)for(int role=0;role<5;++role){const auto label="phase"+std::to_string(phase?45:0)+"-"+names[role];
            auto frame=prior::capture(fixture,programs[phase][role],1,true,dir,label);
            auto repeat=prior::capture(fixture,programs[phase][role],1,true,dir,label+"-repeat");
            for(int slot=0;slot<8;++slot)compare(label+"-slot"+std::to_string(slot)+"-repeat",frame.images[slot],repeat.images[slot]);
            compare(label+"-depth-repeat",frame.depth,repeat.depth);frames[phase][role]=std::move(frame);
            auto inputDir=dir/(label+"-actual-inputs");require(fs::create_directory(inputDir),"new inputs required");
            ghPhase::drawState(fixture,programs[phase][role],true,inputDir);
            auto inputs=sun::snapshotInputs(fixture,programs[phase][role],inputDir);
            if(haveInputs)for(int unit=0;unit<8;++unit)require(inherited::bitsEqual(inputs[unit],inputReference[unit]),"inputs differ between roles");
            else {inputReference=inputs;haveInputs=true;}
            if(role){compare(label+"-C0-passive",frames[phase][0].images[0],frames[phase][role].images[0]);compare(label+"-depth-passive",frames[phase][0].depth,frames[phase][role].depth);}
        }
        for(int phase=0;phase<2;++phase)for(int call=0;call<2;++call){const auto label="phase"+std::to_string(phase?45:0)+(call?"-base":"-full");
            compare(label+"-alternate-export-TES-passive",frames[phase][0].images[4],frames[phase][3+call].images[1]);
            for(int slot=2;slot<8;++slot)compare(label+"-alternate-export-slot"+std::to_string(slot)+"-equal",frames[phase][1+call].images[slot],frames[phase][3+call].images[slot]);}
        if(matchedIris)for(int phase=0;phase<2;++phase)for(int call=0;call<2;++call) {
            const auto& f=frames[phase][1+call];
            const int p=4*((ghPhase::size/2)*ghPhase::size+ghPhase::size/2);
            const std::array<float,3> n={-0.024761740118265152f,-0.9978660345077515f,0.06041766330599785f};
            const std::array<float,3> v={-0.21253617107868195f,-0.6171247363090515f,-0.7576183080673218f};
            const std::array<float,3> c={0.006807451602071524f,0.0027949956711381674f,0.002802651608362794f};
            for(int j=0;j<3;++j)require(f.images[1][p+j]==n[j]&&f.images[2][p+j]==v[j]&&f.images[3][p+j]==c[j],"Actual matched Iris input bits differ");
            require(f.images[1][p+3]==1,"Matched eligible point inactive");
            if(phase)require(f.images[5][p]==256&&f.images[5][p+1]==256&&f.images[5][p+2]==1&&f.images[5][p+3]==17&&f.images[6][p+1]<0&&f.images[6][p+3]==0,
                "Matched first transmitted-hemisphere failure not reproduced");
            else require(f.images[5][p]==0&&f.images[4][p]==1&&f.images[4][p+1]==1,"Matched phase0 positive control absent");
        }
        report<<"],\"ledgerCounts\":[";
        for(int phase=0;phase<2;++phase){if(phase)report<<',';std::array<int,2> active={},good={},rejected={};
            for(int call=0;call<2;++call)for(int p=0;p<ghPhase::size*ghPhase::size*4;p+=4){const auto& f=frames[phase][1+call];
                active[call]+=f.images[5][p+3]>0;rejected[call]+=f.images[5][p]>0;good[call]+=accounted(f,p);}
            require(active[0]>0&&active[1]>0&&good[0]==ghPhase::size*ghPhase::size&&good[1]==ghPhase::size*ghPhase::size,"ledger accounting inactive or malformed");
            report<<"{\"phase\":"<<(phase?45:0)<<",\"active\":";ghPhase::angular::numbers(report,active);report<<",\"accounted\":";ghPhase::angular::numbers(report,good);
            report<<",\"rejected\":";ghPhase::angular::numbers(report,rejected);report<<'}';
        }report<<"]}";
    }
    report<<"],\"accepted\":"<<(accepted?"true":"false")<<",\"physicalAccepted\":false,\"IrisAccepted\":false,\"visualAccepted\":false,\"opticalFixImplemented\":false,"
        "\"TESObservationScope\":\"Native-only alternate export replaces normal with previously stored TES. Exact original ledger C0/depth and alternate-export C0/depth/TES are separate observed routes.\"}\n";
    old::writeText(output/"result.json",report.str());for(auto row:programs)for(auto p:row)glDeleteProgram(p);
    std::cout<<(accepted?"PASS":"RED")<<" legacy ledger passivity "<<output<<'\n';return accepted?0:1;
}
}
int main(int argc,char** argv){try{if(argc!=3&&argc!=4){std::cerr<<"usage: water_legacy_branch_probe NEW_CANONICAL_SOURCES NEW_NATIVE_OUTPUT [matched-iris]\n";return 2;}
    if(argc==4&&std::string(argv[3])!="matched-iris")throw std::runtime_error("Unknown fixture option");
    return legacyBranch::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),argc==4);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(!legacyBranch::owned.empty())ghPhase::old::writeText(legacyBranch::owned/"failure.txt",std::string(e.what())+'\n');return 2;}}
