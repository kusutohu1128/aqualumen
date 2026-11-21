// TEST ONLY. Root exclusively owns GL/game; only --cpu-* is agent-runnable.
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
#include <openssl/sha.h>
namespace frozenReasonNative {
#include "water_residual_sun_iris_probe_v2.cpp"
}
namespace sunReasonProbe {
namespace prior=frozenReasonNative::sunIrisProbe;
namespace sun=prior::sun; namespace tracer=prior::tracer; namespace old=prior::old;
namespace angular=prior::angular; namespace light=prior::light; namespace fs=std::filesystem;
constexpr int size=prior::size,outputs=prior::outputs;
const std::string reasonStoreBegin="// AQUALUMEN_SUN_REASONS_STORE_BEGIN\n",reasonStoreEnd="// AQUALUMEN_SUN_REASONS_STORE_END\n";
const std::string metadataSHA="6cbb71c6363cd746b2565d0953ab62a4d12b8e24a69fdc9026bac676db4f07cc";
const std::string helperSHA="3a39ab9442d4ad37a7d21110f44b8b94eb3689313bdaa7602ea9f5f1722f407c";
const std::string observerRawSHA="b6747e3a13d7991eb304f3db3fa8884e4cb5fd4d6b23d610247f2255f9df26f4";
bool ownedArtifacts=false;
const std::array<std::string,7> tags={"GLOBALS","RESET","TARGET","BRANCH","RAYS","KERNEL","RECEIVER"};
void require(bool okay,const std::string& why){if(!okay)throw std::runtime_error("INCONCLUSIVE passive Sun reasons: "+why);}
std::string stripReasons(std::string source){
    for(const auto& name:tags){const std::string begin="// AQUALUMEN_SUN_REASONS_BEGIN:"+name+"\n",end="// AQUALUMEN_SUN_REASONS_END:"+name+"\n";
        if(source.find(begin)!=std::string::npos||source.find(end)!=std::string::npos)source=tracer::eraseOne(source,begin,end);}
    require(source.find("AQUALUMEN_SUN_REASONS_")==std::string::npos,"unknown/unmatched diagnostic tag");return source;
}
int cpuRecovery(const fs::path& root){
    const auto original=old::readText(root/"lib/water_residual_sun.glsl");
    require(light::digest(original)==prior::capHelperSHA,"actual pinned uninstrumented helper required");
    const std::string observed="// AQUALUMEN_SUN_REASONS_BEGIN:GLOBALS\nvec4 WNS_reasons=vec4(0.0);\n// AQUALUMEN_SUN_REASONS_END:GLOBALS\n"+original;
    require(stripReasons(observed)==original,"public observation erasure must recover actual original helper exactly");
    std::cout<<"PASS CPU actual helper + passive-reason erasure; no GL\n";return 0;
}
bool whole(float value,int maximum){return std::isfinite(value)&&value>=0&&value<=maximum&&value==std::floor(value);}
bool reasonAccounting(const float* reasons,const float* status,int guard,bool source){
    if(!whole(reasons[0],9))return false;
    for(int c=1;c<4;++c)if(!whole(reasons[c],48))return false;
    if(!whole(status[0],1)||!whole(status[1],1)||status[2]!=0||!whole(status[3],48))return false;
    const float sum=reasons[1]+reasons[2]+reasons[3];const bool zero=reasons[0]==0&&sum==0;
    if(sum>48)return false;
    if(!guard)return zero&&status[0]==0&&status[1]==0&&status[3]==0;
    if(status[0]!=1)return false;
    if(!source)return zero&&status[1]==0&&status[3]==0;
    if(status[1]==1)return zero&&status[3]==0;
    if(sum==0)return zero&&(status[3]==0||status[3]==1); // uncategorized pre/post-loop fallback
    if(sum!=status[3]||reasons[0]==0)return false;
    const int first=int(reasons[0]);
    return first==3||first==9?reasons[1]>0:first==6||first==7?reasons[2]>0:reasons[3]>0;
}
int cpuAccounting(int argc,char** argv){
    require(argc==11,"reason4/request/app/rejection/guard/source required");std::array<float,4> reasons={},status={};
    for(int i=0;i<4;++i){reasons[i]=std::stof(argv[i+2]);}
    status={std::stof(argv[6]),std::stof(argv[7]),0,std::stof(argv[8])};
    const int guard=std::stoi(argv[9]),source=std::stoi(argv[10]);require((guard==0||guard==1)&&(source==0||source==1),"fixed Boolean CPU inputs required");
    std::cout<<(reasonAccounting(reasons.data(),status.data(),guard,source)?"QUALIFIED\n":"REJECTED\n");return 0;
}
struct Sources {std::array<std::string,3> geometry;std::array<std::string,3> fragment;std::string metadata,originalHelper,reasonHelper;};
Sources load(const fs::path& original,const fs::path& reason){
    Sources result;const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){result.geometry[i]=prior::expandOwner::expand(original/stages[i],original);
        require(light::digest(result.geometry[i])==prior::geometrySHA[i],"original phase120 factor4 geometry pin differs");
        require(result.geometry[i]==prior::expandOwner::expand(reason/stages[i],reason),"reason observation changed a geometry stage");}
    const auto physicalRaw=old::readText(original.parent_path()/"PARENT-SUN-IRIS-physical.fsh");
    result.fragment[0]=prior::expandOwner::expand(original.parent_path()/"PARENT-SUN-IRIS-physical.fsh",original);
    result.fragment[1]=prior::expandOwner::expand(original/"gbuffers_water.fsh",original);
    require(prior::physicalFromObserver(result.fragment[1])==result.fragment[0],"original coefficient observer recovery differs");
    require(light::digest(prior::removeGuard(result.fragment[0]))==prior::capExpandedSHA,"original guarded1 parent CAP pin differs");
    require(result.fragment[0].find(prior::configBegin+"#define NATIVE_SUN_ENABLED 1\n"+prior::configEnd)!=std::string::npos,"original must be enabled1");
    require(result.fragment[0].find("    if (aqualumenSunTestAuthorized==1) {\n"+prior::originalCall+"    }\n")!=std::string::npos,"original actual caller-if authorization differs");
    result.originalHelper=old::readText(original/"lib/water_residual_sun.glsl");
    require(light::digest(result.originalHelper)==prior::capHelperSHA,"original a070 helper pin differs");
    result.metadata=old::readText(reason.parent_path()/"WATER-RESIDUAL-SUN-REASONS.json");
    require(result.metadata.size()<=32768&&light::digest(result.metadata)==metadataSHA,"exact authoritative reason metadata pin differs");
    require(result.metadata.find("\"schema\": \"aqualumen-water-residual-sun-reasons-v1\"")!=std::string::npos&&result.metadata.find("\"loop_only\": true")!=std::string::npos,"reason schema/loop-only protocol differs");
    require(old::readText(reason.parent_path()/"PARENT-SUN-REASONS-physical.fsh")==physicalRaw,"reason archived physical raw main differs from actual original");
    require(old::readText(reason.parent_path()/"PARENT-SUN-REASONS-helper.glsl")==result.originalHelper,"reason archived helper differs from actual original");
    result.reasonHelper=old::readText(reason/"lib/water_residual_sun.glsl");
    require(light::digest(result.reasonHelper)==helperSHA&&stripReasons(result.reasonHelper)==result.originalHelper,"instrumented helper exact recovery/pin differs");
    const auto reasonRaw=old::readText(reason/"gbuffers_water.fsh");
    require(light::digest(reasonRaw)==observerRawSHA&&tracer::eraseOne(reasonRaw,reasonStoreBegin,reasonStoreEnd)==physicalRaw,"reason STORE/raw main recovery differs");
    result.fragment[2]=prior::expandOwner::expand(reason/"gbuffers_water.fsh",reason);
    require(stripReasons(tracer::eraseOne(result.fragment[2],reasonStoreBegin,reasonStoreEnd))==result.fragment[0],"expanded reason observation must recover original physical main/helper exactly");
    for(const auto& root:{original,reason})require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"stock atmosphere source pin differs");
    return result;
}
int cpuContract(const fs::path& original,const fs::path& reason){const auto source=load(original,reason);require(!source.fragment[2].empty(),"empty actual reason observer");std::cout<<"PASS CPU actual pack geometry/helper/guarded main recovery; no GL\n";return 0;}
void wideProjection(sun::Fixture& fixture){
    // NEW nonacceptance fixture: ONLY the projection changes; inherited plane,
    // bathymetry, phase, Sun/cache and original optics remain byte-identical.
    const float focal=float(1/std::tan(3.14159265358979323846/6)),near=.01f,far=128,a=-(far+near)/(far-near),b=-2*far*near/(far-near);
    fixture.aperture=60;fixture.projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};
    fixture.inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,0,1/b,0,0,-1,a/b};
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(fixture.projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(old::up.data());old::glOkay("new wide projection only");
}
bool coefficientDomain(const float* c){return c[0]>0&&std::abs(double(c[0])-1)<=tracer::coefficientTolerance&&c[1]>=0&&c[2]>=0&&c[3]>=0&&c[3]<=c[1]+tracer::coefficientTolerance&&std::abs(double(c[1])+c[2]-c[0])<=tracer::coefficientTolerance;}
bool covarianceDomain(const float* c){return c[0]>0&&c[2]>0&&double(c[0])*c[2]-double(c[1])*c[1]>0&&double(c[0])+c[2]>1e-5;}
void samples(std::ostringstream& out,const old::Capture& original,const old::Capture& reason){
    out<<'[';for(std::size_t i=0;i<sun::pixels.size();++i){if(i)out<<',';const auto pixel=sun::pixels[i];const int p=(pixel.second*size+pixel.first)*4;
        out<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"original_WR_coefficients\":";angular::four(out,&original.images[1][p]);
        out<<",\"original_WNS_status\":";angular::four(out,&original.images[2][p]);out<<",\"reason_payload\":";angular::four(out,&reason.images[1][p]);
        out<<",\"reason_WNS_status\":";angular::four(out,&reason.images[2][p]);out<<",\"covariance_original_flags\":";angular::four(out,&reason.images[3][p]);out<<",\"TES_C12\":";angular::four(out,&reason.images[4][p]);out<<'}';}out<<']';
}
int run(const fs::path& originalRoot,const fs::path& reasonRoot,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required");const auto source=load(originalRoot,reasonRoot);
    require(fs::create_directories(artifacts),"cannot create NEW artifacts");ownedArtifacts=true;
    old::writeText(artifacts/"reason-metadata.json",source.metadata);old::writeText(artifacts/"original-helper.glsl",source.originalHelper);old::writeText(artifacts/"reason-helper.glsl",source.reasonHelper);
    for(int i=0;i<3;++i)old::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),source.geometry[i]);
    const std::array<std::string,3> roles={"original-physical","original-coefficient-observer","reason-observer"};
    for(int i=0;i<3;++i)old::writeText(artifacts/(roles[i]+"-expanded.fsh"),source.fragment[i]);
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA required");sun::Fixture fixture;
    GLint patch=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);require(patch==3&&!glIsEnabled(GL_CULL_FACE),"actual patcharity3/culling-off required");
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-native-sun-reasons-passivity-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"actual_patch_arity\":"<<patch<<",\"culling_enabled\":false,\"reason_metadata_sha256\":"<<old::quote(metadataSHA)<<",\"original_helper_sha256\":"<<old::quote(prior::capHelperSHA)<<",\"reason_helper_sha256\":"<<old::quote(helperSHA)<<",\"policy\":{\"C0_absolute\":"<<tracer::passiveAbsolute<<",\"C0_relative\":"<<tracer::passiveRelative<<",\"depth_absolute\":"<<tracer::depthTolerance<<",\"C12_absolute\":0,\"repeat_absolute\":0,\"coefficient_absolute\":"<<tracer::coefficientTolerance<<"},\"programs\":[";
    std::array<GLuint,3> programs={};for(int i=0;i<3;++i){if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.fragment[i]}},roles[i],report);}report<<"],\"cases\":[";
    bool allQualified=true,allAccepted=true;int caseIndex=0;
    for(int scenario=0;scenario<5;++scenario){const bool wide=scenario==4,positive=wide||scenario>=2;const int guard=wide?1:scenario%2;
        const std::string name=wide?"wide60-cachepositive-guard1":"central2-cache"+std::string(positive?"positive":"zero")+"-guard"+std::to_string(guard);
        const auto dir=artifacts/name;require(fs::create_directory(dir),"NEW case directory required");fixture.scene(2,0,positive,dir);if(wide)wideProjection(fixture);
        if(caseIndex++){report<<',';}report<<"{\"path\":"<<old::quote(name)<<",\"aperture_degrees\":"<<(wide?60:2)<<",\"positive_cache\":"<<(positive?"true":"false")<<",\"guard\":"<<guard<<",\"central_acceptance_case\":"<<(wide?"false":"true")<<",\"queriedProgramSourcesOriginal\":";
        tracer::Sources query;query.geometry=source.geometry;sun::queriedSources(report,{{programs[0],programs[1]}},query,{{source.fragment[0],source.fragment[1]}});
        report<<",\"queriedProgramSourcesReason\":";sun::queriedSources(report,{{programs[0],programs[2]}},query,{{source.fragment[0],source.fragment[2]}});
        std::array<old::Capture,3> frames,repeats;
        for(int role=0;role<3;++role){frames[role]=prior::capture(fixture,programs[role],guard,role!=0,dir,roles[role]);repeats[role]=prior::capture(fixture,programs[role],guard,role!=0,dir,roles[role]+"-repeat");
            const auto inputDir=dir/(roles[role]+"-inputs");require(fs::create_directory(inputDir),"NEW role input snapshot required");sun::snapshotInputs(fixture,programs[role],inputDir);prior::guardSnapshot(programs[role],guard,inputDir,"actual-inputs");}
        report<<",\"comparisons\":[";bool comparisonFirst=true,caseAccepted=true;
        auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double absolute,double relative=0){caseAccepted=tracer::compare(report,comparisonFirst,label,a,b,absolute,relative)&&caseAccepted;};
        for(int role=0;role<3;++role){for(int slot=0;slot<outputs;++slot)compare(roles[role]+"-slot"+std::to_string(slot)+"-repeat",frames[role].images[slot],repeats[role].images[slot],0);compare(roles[role]+"-depth-repeat",frames[role].depth,repeats[role].depth,0);}
        for(int role:{1,2}){compare(roles[role]+"-C0-neutral",frames[0].images[0],frames[role].images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare(roles[role]+"-depth-neutral",frames[0].depth,frames[role].depth,tracer::depthTolerance);compare(roles[role]+"-C12-exact",frames[0].images[4],frames[role].images[4],0);}
        compare("original-vs-reason-C10-WNS-exact",frames[1].images[2],frames[2].images[2],0);
        compare("original-vs-reason-C11-covFlags-exact",frames[1].images[3],frames[2].images[3],0);
        int inspected=0,qualified=0,accounted=0,statusMatched=0,stageWater=0,nonwater=0,unadmitted=0,rejectedPixels=0,loopRejected=0;std::array<long long,10> firstCounts={};std::array<long long,3> grouped={};
        for(int y=0;y<size;++y)for(int x=0;x<size;++x){if(!wide&&(x-128)*(x-128)+(y-128)*(y-128)>1600)continue;const int p=(y*size+x)*4;
            const auto* coefficients=&frames[1].images[1][p];const auto* originalStatus=&frames[1].images[2][p];const auto* cov=&frames[1].images[3][p];const auto* reasons=&frames[2].images[1][p];const auto* status=&frames[2].images[2][p];const auto* reasonCov=&frames[2].images[3][p];
            if(wide){if(frames[0].images[4][p+3]==0){++nonwater;continue;}++stageWater;
                require(prior::stageQualified(&frames[0].images[4][p])&&whole(cov[3],15)&&whole(reasonCov[3],15),"wide stage/originalflags malformed");
                if(cov[3]!=15){++unadmitted;continue;}}
            ++inspected;bool domain=cov[3]==15&&reasonCov[3]==15&&frames[0].images[0][p+3]==1&&frames[1].images[0][p+3]==1&&frames[2].images[0][p+3]==1;
            for(int role=0;role<3;++role)domain=domain&&prior::stageQualified(&frames[role].images[4][p]);
            if(guard){domain=domain&&covarianceDomain(cov)&&covarianceDomain(reasonCov);if(!wide)domain=domain&&coefficientDomain(coefficients)&&originalStatus[3]==0&&status[3]==0;}
            else{for(int c=0;c<4;++c)domain=domain&&coefficients[c]==0&&originalStatus[c]==0;for(int c=0;c<3;++c)domain=domain&&cov[c]==0&&reasonCov[c]==0;}
            qualified+=domain;const bool accounting=reasonAccounting(reasons,status,guard,positive);accounted+=accounting;
            bool matches=whole(originalStatus[0],1)&&whole(originalStatus[1],1)&&originalStatus[2]==0&&whole(originalStatus[3],48)&&originalStatus[0]==guard;
            if(!wide)matches=matches&&originalStatus[1]==int(guard&&positive)&&originalStatus[3]==0&&status[0]==guard&&status[1]==int(guard&&positive)&&status[3]==0;
            statusMatched+=matches;if(accounting){++firstCounts[int(reasons[0])];for(int c=0;c<3;++c)grouped[c]+=int(reasons[c+1]);rejectedPixels+=status[3]>0;loopRejected+=reasons[1]+reasons[2]+reasons[3]>0;}
        }
        const bool caseQualified=inspected>0&&qualified==inspected&&(!wide?inspected==5025:true);
        const bool casePass=caseAccepted&&accounted==inspected&&statusMatched==inspected&&(!wide||loopRejected>0);
        allQualified=allQualified&&caseQualified;allAccepted=allAccepted&&casePass;
        report<<"],\"inspected_points\":"<<inspected<<",\"qualified_points\":"<<qualified<<",\"reason_accounting_points\":"<<accounted<<",\"status_expected_points\":"<<statusMatched<<",\"all_canvas_pixels\":"<<size*size<<",\"wide_stage_water_points\":"<<stageWater<<",\"wide_nonwater_points\":"<<nonwater<<",\"wide_unadmitted_points\":"<<unadmitted<<",\"rejected_points\":"<<rejectedPixels<<",\"loop_rejected_points\":"<<loopRejected<<",\"first_reason_histogram_0_to_9\":";angular::numbers(report,firstCounts);report<<",\"grouped_failed_node_totals\":";angular::numbers(report,grouped);
        report<<",\"fixture_qualified\":"<<(caseQualified?"true":"false")<<",\"passivity_and_reason_accounting_accepted\":"<<(casePass?"true":"false")<<",\"fixed_six_samples\":";samples(report,frames[1],frames[2]);report<<'}';
    }
    const auto status=!allQualified?"INCONCLUSIVE":allAccepted?"PASS":"RED";report<<"],\"case_count\":"<<caseIndex<<",\"fixture_qualified\":"<<(allQualified?"true":"false")<<",\"accepted\":"<<(allQualified&&allAccepted?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"physical_fix_accepted\":false,\"pixel_AA_accepted\":false,\"Iris_accepted\":false,\"visual_accepted\":false,\"FPS_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Passive same-main reason instrumentation only. Original coefficient observer supplies unchanged central domain; reason C9 is first failed NODE and grouped node counts, never mass/R/T/TIR. Four central5025 cases retain original corpus and gates. Wide60 covers every eligible known-water raster pixel on the same inherited finite plane, is separate descriptive rejection evidence, not central acceptance or physical application proof. Category3 reflected and9 transmitted hemisphere, 6/7 receiver,8 other/nonfinite; pre/post rejection1 may have zero reasons. Counters are not lost radiance/visibility support. C12 interpolated TES output, not invocation/count. No physical fix, pixel-AA, Iris, appearance, motion, FPS or shipping claim.\"}\n";
    old::writeText(artifacts/"result.json",report.str());for(auto program:programs)glDeleteProgram(program);std::cout<<status<<" native passive Sun reasons "<<artifacts<<'\n';return !allQualified?2:allAccepted?0:1;
}
}
int main(int argc,char** argv){try{
    if(argc==4&&std::string(argv[1])=="--cpu-contract")return sunReasonProbe::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));
    if(argc==11&&std::string(argv[1])=="--cpu-accounting")return sunReasonProbe::cpuAccounting(argc,argv);
    if(argc==3&&std::string(argv[1])=="--cpu-recovery")return sunReasonProbe::cpuRecovery(std::filesystem::absolute(argv[2]));
    if(argc==4)return sunReasonProbe::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));
    std::cerr<<"usage: water_residual_sun_reason_probe ORIGINAL_GUARDED1_SHADERS REASON_SHADERS NEW_OUTPUT\n       --cpu-contract ORIGINAL_GUARDED1_SHADERS REASON_SHADERS\n       --cpu-recovery ORIGINAL_GUARDED1_SHADERS\n";return 2;
}catch(const std::exception& failure){std::cerr<<failure.what()<<'\n';if(sunReasonProbe::ownedArtifacts&&argc==4)try{sunReasonProbe::old::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(failure.what())+'\n');}catch(...){}return 2;}}
