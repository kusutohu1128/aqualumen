// TEST ONLY. CPU construction/build here; root alone owns GL/game execution.
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
namespace frozenSunIris {
#include "water_residual_sun_probe.cpp"
}
namespace sunIrisProbe {
namespace sun=frozenSunIris::sunProbe;
namespace tracer=sun::tracer;
namespace old=sun::old;
namespace angular=sun::angular;
namespace light=sun::light;
namespace expandOwner=frozenSunIris::frozenNativeSun::frozenResidualLight::frozenResidualAngular::frozenResolvedNative;
namespace fs=std::filesystem;
constexpr int size=sun::size,outputs=sun::outputs;
const std::string storeBegin="// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_BEGIN\n",storeEnd="// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_END\n";
const std::string callBegin="// AQUALUMEN_SUN_IRIS_GUARD_CALL_BEGIN\n",callEnd="// AQUALUMEN_SUN_IRIS_GUARD_CALL_END\n";
const std::string uniformBegin="// AQUALUMEN_SUN_IRIS_GUARD_UNIFORM_BEGIN\n",uniformEnd="// AQUALUMEN_SUN_IRIS_GUARD_UNIFORM_END\n";
const std::string configBegin="// AQUALUMEN_SUN_IRIS_CONFIG_BEGIN\n",configEnd="// AQUALUMEN_SUN_IRIS_CONFIG_END\n";
const std::string originalCall="    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n";
const std::string capHelperSHA="a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3";
const std::string capExpandedSHA="3f446979bd875a947eafbbed13509f4d158f229dc30edc07ed914a6ff8b9f11d";
const std::array<std::string,3> geometrySHA={"5cb5cde275882a57395d34e1bdd7e2ccf852051cbcb5d421995e1a76557401fd","bcdebf3c355194c6be1f901a2c8b582ec7eeb4d1ae5fb5ce6dcc23143a9df932","973e088388ddec93565cb5aaa47f0bbd397703d7a381f900b19f8ed1d1765b6b"};
const std::string observerStore=storeBegin+"    gl_FragData[1]=WR_coefficients;\n    gl_FragData[2]=WNS_status;\n    gl_FragData[3]=vec4(WR_covariance,float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible));\n"+storeEnd;
bool ownedArtifacts=false;
void require(bool okay,const std::string& text){if(!okay)throw std::runtime_error("INCONCLUSIVE native-Sun Iris passivity: "+text);}
std::string physicalFromObserver(const std::string& source){return tracer::eraseOne(source,storeBegin,storeEnd);}
std::string removeGuard(std::string source){
    const auto at=source.find(callBegin),end=source.find(callEnd,at);
    require(at!=std::string::npos&&end!=std::string::npos&&source.find(callBegin,at+callBegin.size())==std::string::npos&&source.find(callEnd,end+callEnd.size())==std::string::npos,"guard-call seam absent/ambiguous");
    source.replace(at,end+callEnd.size()-at,originalCall);
    return tracer::eraseOne(tracer::eraseOne(source,configBegin,configEnd),uniformBegin,uniformEnd);
}
struct Sources {std::array<std::string,3> geometry;std::string cap,resolved;std::array<std::string,2> physical,observer;};
Sources load(const fs::path& capRoot,const std::array<fs::path,2>& roots){
    Sources result;const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){result.geometry[i]=expandOwner::expand(capRoot/stages[i],capRoot);require(light::digest(result.geometry[i])==geometrySHA[i],"frozen actual native geometry pin differs");for(const auto& root:roots)require(result.geometry[i]==expandOwner::expand(root/stages[i],root),"original geometry stage changed");}
    result.cap=expandOwner::expand(capRoot/"gbuffers_water.fsh",capRoot);
    require(light::digest(result.cap)==capExpandedSHA,"frozen actual expanded CAP pin differs");
    result.resolved=tracer::disabled(sun::removeInner(result.cap));
    require(light::digest(old::readText(capRoot/"lib/water_residual_sun.glsl"))==capHelperSHA,"CAP helper pin differs");
    for(int enabled:{0,1}){
        const auto& root=roots[enabled];result.observer[enabled]=expandOwner::expand(root/"gbuffers_water.fsh",root);
        result.physical[enabled]=expandOwner::expand(root.parent_path()/"PARENT-SUN-IRIS-physical.fsh",root);
        require(physicalFromObserver(result.observer[enabled])==result.physical[enabled],"public observer recovery must equal archived guarded physical FS exactly");
        require(removeGuard(result.physical[enabled])==result.cap,"guard/config/call recovery must equal CAP FS exactly");
        require(light::digest(old::readText(root/"lib/water_residual_sun.glsl"))==capHelperSHA,"guarded pack changed approved CAP helper");
        require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"guarded stock atmosphere differs");
        require(result.physical[enabled].find("uniform int aqualumenSunTestAuthorized;\n")!=std::string::npos,"typed authorization guard missing");
        require(result.physical[enabled].find("    if (aqualumenSunTestAuthorized==1) {\n"+originalCall+"    }\n")!=std::string::npos,"guard must skip actual helper call, not merely pass false eligibility");
        require(result.physical[enabled].find(configBegin+"#define NATIVE_SUN_ENABLED "+std::to_string(enabled)+"\n"+configEnd)!=std::string::npos,"actual configured enabled block differs, not the helper default");
        require(result.observer[enabled].find("    gl_FragData[1]=WR_coefficients;\n")!=std::string::npos&&result.observer[enabled].find("    gl_FragData[2]=WNS_status;\n")!=std::string::npos,"actual WR/WNS STORE fields missing");
        require(result.geometry[0].find("#define frameTimeCounter 120.0\n")!=std::string::npos&&result.physical[enabled].find("#define frameTimeCounter 120.0\n")!=std::string::npos,"shared phase120 missing");
    }
    return result;
}
int cpuContract(const fs::path& capRoot,const std::array<fs::path,2>& roots){const auto sources=load(capRoot,roots);require(!sources.resolved.empty(),"resolved recovery empty");std::cout<<"PASS CPU actual Iris observer/physical recovery and caller-if guard; no GL\n";return 0;}
int cpuConstruction(const fs::path& savedCAP){
    const auto original=old::readText(savedCAP);
    require(original.size()>=2&&original.substr(original.size()-2)=="}\n"&&original.find("    gl_FragData[4]=tessStageCoord;\n")!=std::string::npos,"actual saved CAP final-water/TES source required");
    const auto observer=original.substr(0,original.size()-2)+observerStore+original.substr(original.size()-2);
    require(physicalFromObserver(observer)==original,"public actual-source STORE construction must recover exact original CAP main");
    std::cout<<"PASS CPU actual saved CAP main + removable builder STORE recovery; no shader/GL execution\n";return 0;
}
void setGuard(sun::Fixture& fixture,GLuint program,int guard){
    require(guard==0||guard==1,"fixed guard0/1 only");fixture.uniforms(program);
    const char* name="aqualumenSunTestAuthorized";GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);
    const GLint location=glGetUniformLocation(program,name);GLint type=0,count=0;
    require(index!=GL_INVALID_INDEX&&location>=0,"actual authorization guard inactive/absent");
    glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&count);
    require(type==GL_INT&&count==1,"actual authorization must be scalar int count1");
    glUniform1i(location,guard);GLint value=-1;glGetUniformiv(program,location,&value);require(value==guard,"actual authorization value differs");old::glOkay("actual typed guard");
}
void guardSnapshot(GLuint program,int guard,const fs::path& directory,const std::string& label){
    const char* name="aqualumenSunTestAuthorized";GLuint index=GL_INVALID_INDEX;GLint before=0,after=0;
    glGetIntegerv(GL_CURRENT_PROGRAM,&before);require(before==GLint(program),"guard query requires actual current program");
    glGetUniformIndices(program,1,&name,&index);const GLint location=glGetUniformLocation(program,name);GLint type=0,count=0,value=-1;
    require(index!=GL_INVALID_INDEX&&location>=0,"queried guard absent");glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&count);glGetUniformiv(program,location,&value);glGetIntegerv(GL_CURRENT_PROGRAM,&after);
    require(type==GL_INT&&count==1&&value==guard&&before==after,"typed queried authorization/state mismatch");
    std::ostringstream out;out<<"{\"schema\":\"aqualumen-native-sun-iris-guard-input-v1\",\"program\":"<<program<<",\"currentProgramBefore\":"<<before<<",\"currentProgramAfter\":"<<after<<",\"name\":\"aqualumenSunTestAuthorized\",\"type\":"<<type<<",\"size\":"<<count<<",\"value\":"<<value<<"}\n";
    old::writeText(directory/(label+"-guard.json"),out.str());old::glOkay("passive actual guard query");
}
old::Capture capture(sun::Fixture& fixture,GLuint program,int guard,bool observer,const fs::path& directory,const std::string& label){
    if(guard>=0)setGuard(fixture,program,guard);
    // The inherited draw reapplies all pinned fixture inputs but does not reset
    // the new guard. Query again after every actual draw, not only host intent.
    auto result=sun::draw(fixture,program,observer,directory,label);
    if(guard>=0){GLint value=-1;glGetUniformiv(program,glGetUniformLocation(program,"aqualumenSunTestAuthorized"),&value);require(value==guard,"guard changed during actual draw");guardSnapshot(program,guard,directory,label);}
    return result;
}
int run(const fs::path& capRoot,const std::array<fs::path,2>& roots,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required");const auto source=load(capRoot,roots);
    require(fs::create_directories(artifacts),"cannot create NEW artifacts");ownedArtifacts=true;
    old::writeText(artifacts/"cap-expanded.fsh",source.cap);old::writeText(artifacts/"resolved-expanded.fsh",source.resolved);
    for(int i=0;i<3;++i)old::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),source.geometry[i]);
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA required");sun::Fixture fixture;
    GLint patch=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);require(patch==3&&!glIsEnabled(GL_CULL_FACE),"actual patcharity3/culling-off fixture required");
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-native-sun-iris-passivity-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"aperture_degrees\":2,\"rainStrength\":0,\"actual_patch_arity\":"<<patch<<",\"culling_enabled\":false,\"cap_helper_sha256\":"<<old::quote(capHelperSHA)<<",\"policy\":{\"C0_absolute\":"<<tracer::passiveAbsolute<<",\"C0_relative\":"<<tracer::passiveRelative<<",\"depth_absolute\":"<<tracer::depthTolerance<<",\"C12_absolute\":0,\"repeat_absolute\":0,\"coefficient_absolute\":"<<tracer::coefficientTolerance<<"},\"observer_roles\":{\"C9\":\"actual WR coefficients\",\"C10\":\"actual WNS requested/applied/kind/rejections\",\"C11\":\"WR covariance + original known+2upper+4UW+8eligibility\",\"C12\":\"unchanged interpolated TES output, not fragment invocation/count\"},\"programs\":[";
    std::array<std::array<GLuint,2>,2> programs={};bool first=true;
    for(int enabled:{0,1})for(int role:{0,1}){if(!first)report<<',';first=false;programs[enabled][role]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,role?source.observer[enabled]:source.physical[enabled]}},"guarded"+std::to_string(enabled)+(role?"-observer":"-physical"),report);}
    report<<',';const GLuint resolvedProgram=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.resolved}},"recovered-resolved",report);report<<"],\"cases\":[";
    std::array<old::Capture,2> references;for(int positive:{0,1}){const auto dir=artifacts/(positive?"resolved-cachepositive":"resolved-cachezero");require(fs::create_directory(dir),"NEW resolved cache reference required");fixture.scene(2,0,bool(positive),dir);references[positive]=capture(fixture,resolvedProgram,-1,false,dir,"pure");const auto repeat=capture(fixture,resolvedProgram,-1,false,dir,"pure-repeat");require(references[positive].images==repeat.images&&references[positive].depth==repeat.depth,"resolved reference repeat not exact");}
    bool accepted=true,qualified=true;int caseIndex=0;
    for(int positive:{0,1})for(int enabled:{0,1})for(int guard:{0,1}){
        const std::string name="cache"+std::string(positive?"positive":"zero")+"-enabled"+std::to_string(enabled)+"-guard"+std::to_string(guard);const auto dir=artifacts/name;require(fs::create_directory(dir),"NEW case directory required");fixture.scene(2,0,bool(positive),dir);
        for(int role:{0,1})old::writeText(dir/(role?"observer-expanded.fsh":"pure-expanded.fsh"),role?source.observer[enabled]:source.physical[enabled]);
        if(caseIndex++){report<<',';}report<<"{\"path\":"<<old::quote(name)<<",\"positive_cache\":"<<(positive?"true":"false")<<",\"enabled\":"<<enabled<<",\"guard\":"<<guard<<",\"pureSourceSHA256\":"<<old::quote(light::digest(source.physical[enabled]))<<",\"observerSourceSHA256\":"<<old::quote(light::digest(source.observer[enabled]))<<",\"program_ids\":["<<programs[enabled][0]<<','<<programs[enabled][1]<<"],\"queriedProgramSources\":";
        tracer::Sources queried;queried.geometry=source.geometry;sun::queriedSources(report,programs[enabled],queried,{{source.physical[enabled],source.observer[enabled]}});
        const auto pure=capture(fixture,programs[enabled][0],guard,false,dir,"pure"),pureRepeat=capture(fixture,programs[enabled][0],guard,false,dir,"pure-repeat"),observed=capture(fixture,programs[enabled][1],guard,true,dir,"observer"),repeat=capture(fixture,programs[enabled][1],guard,true,dir,"observer-repeat");
        sun::snapshotInputs(fixture,programs[enabled][1],dir);guardSnapshot(programs[enabled][1],guard,dir,"actual-inputs");
        report<<",\"comparisons\":[";bool comparisonFirst=true,caseAccepted=true;auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double abs,double rel=0){caseAccepted=tracer::compare(report,comparisonFirst,label,a,b,abs,rel)&&caseAccepted;};
        for(int slot=0;slot<outputs;++slot){compare("pure-slot"+std::to_string(slot)+"-repeat",pure.images[slot],pureRepeat.images[slot],0);compare("observer-slot"+std::to_string(slot)+"-repeat",observed.images[slot],repeat.images[slot],0);}
        compare("pure-depth-repeat",pure.depth,pureRepeat.depth,0);compare("observer-depth-repeat",observed.depth,repeat.depth,0);
        compare("observer-C0-neutral",pure.images[0],observed.images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare("observer-depth-neutral",pure.depth,observed.depth,tracer::depthTolerance);compare("observer-C12-exact",pure.images[4],observed.images[4],0);
        if(!guard){compare("guard0-C0-recovered-resolved",pure.images[0],references[positive].images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare("guard0-depth-recovered-resolved",pure.depth,references[positive].depth,tracer::depthTolerance);compare("guard0-C12-recovered-resolved",pure.images[4],references[positive].images[4],0);}
        int roi=0,domain=0,statusMatches=0;const int requested=guard&&enabled,applied=requested&&positive;
        for(int y=0;y<size;++y)for(int x=0;x<size;++x){if((x-128)*(x-128)+(y-128)*(y-128)>1600)continue;++roi;const int p=(y*size+x)*4;const auto* coefficients=&observed.images[1][p];const auto* status=&observed.images[2][p];const auto* cov=&observed.images[3][p];bool pointDomain=cov[3]==15&&pure.images[0][p+3]==1&&observed.images[0][p+3]==1&&pure.images[4][p+3]==1&&observed.images[4][p+3]==1;
            if(guard){const double determinant=double(cov[0])*cov[2]-double(cov[1])*cov[1];pointDomain=pointDomain&&cov[0]>0&&cov[2]>0&&determinant>0&&double(cov[0])+cov[2]>1e-5&&coefficients[0]>0&&std::abs(double(coefficients[0])-1)<=tracer::coefficientTolerance&&coefficients[1]>=0&&coefficients[2]>=0&&coefficients[3]>=0&&coefficients[3]<=coefficients[1]+tracer::coefficientTolerance&&std::abs(double(coefficients[1])+coefficients[2]-coefficients[0])<=tracer::coefficientTolerance;}
            // New receiver/domain rejection is not a feature success/failure.
            pointDomain=pointDomain&&status[3]==0;domain+=pointDomain;
            bool match=status[0]==requested&&status[1]==applied&&status[2]==0&&status[3]==0;
            if(!guard){for(int c=0;c<4;++c)match=match&&coefficients[c]==0&&status[c]==0;for(int c=0;c<3;++c)match=match&&cov[c]==0;}
            statusMatches+=match;
        }
        const bool caseQualified=roi==5025&&domain==roi;const bool casePass=caseAccepted&&statusMatches==roi;qualified=qualified&&caseQualified;accepted=accepted&&casePass;
        report<<"],\"ROI_points\":"<<roi<<",\"ROI_qualified_points\":"<<domain<<",\"expected_requested\":"<<requested<<",\"expected_applied\":"<<applied<<",\"ROI_status_matches\":"<<statusMatches<<",\"fixture_qualified\":"<<(caseQualified?"true":"false")<<",\"passivity_and_application_accepted\":"<<(casePass?"true":"false")<<",\"samples\":[";
        for(std::size_t i=0;i<sun::pixels.size();++i){if(i)report<<',';const auto pixel=sun::pixels[i];const int p=(pixel.second*size+pixel.first)*4;report<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"WR_coefficients\":";angular::four(report,&observed.images[1][p]);report<<",\"WNS_status\":";angular::four(report,&observed.images[2][p]);report<<",\"covariance_original_flags\":";angular::four(report,&observed.images[3][p]);report<<",\"TES_C12\":";angular::four(report,&observed.images[4][p]);report<<'}';}report<<'}';
    }
    const auto status=!qualified?"INCONCLUSIVE":accepted?"PASS":"RED";report<<"],\"case_count\":"<<caseIndex<<",\"fixture_qualified\":"<<(qualified?"true":"false")<<",\"accepted\":"<<(qualified&&accepted?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"native_pixel_AA_accepted\":false,\"Iris_accepted\":false,\"visual_accepted\":false,\"FPS_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Actual-main native guard/application and observation passivity only. Same configured guard/enable pure versus observer; no active-vs-inactive C0 neutrality claim. WR coefficient closure is not direct WR valid/minFacing/opaque telemetry. Originalflags preserve computed eligibility before authorization. C12 is interpolated TES output, not fragment invocation or primitive count. Fixed clear2degree open NEAREST/base-level fixture; no nativepixel-AA, physical model, arbitrary receiver/covariance, Iris, motion, FPS or shipping adoption.\"}\n";
    old::writeText(artifacts/"result.json",report.str());for(const auto& pair:programs)for(auto id:pair)glDeleteProgram(id);glDeleteProgram(resolvedProgram);std::cout<<status<<" native Sun Iris passivity "<<artifacts<<'\n';return !qualified?2:accepted?0:1;
}
}
int main(int argc,char** argv){try{
    if(argc==3&&std::string(argv[1])=="--cpu-construction")return sunIrisProbe::cpuConstruction(std::filesystem::absolute(argv[2]));
    if(argc==5&&std::string(argv[1])=="--cpu-contract")return sunIrisProbe::cpuContract(std::filesystem::absolute(argv[2]),{{std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4])}});
    if(argc==5)return sunIrisProbe::run(std::filesystem::absolute(argv[1]),{{std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3])}},std::filesystem::absolute(argv[4]));
    std::cerr<<"usage: water_residual_sun_iris_probe <CAP-shaders> <guarded0-shaders> <guarded1-shaders> <NEW-output>\n       water_residual_sun_iris_probe --cpu-contract <CAP-shaders> <guarded0-shaders> <guarded1-shaders>\n       water_residual_sun_iris_probe --cpu-construction <frozen-expanded-CAP-FS>\n";return 2;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(sunIrisProbe::ownedArtifacts&&argc==5)try{sunIrisProbe::old::writeText(std::filesystem::absolute(argv[4])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}}
