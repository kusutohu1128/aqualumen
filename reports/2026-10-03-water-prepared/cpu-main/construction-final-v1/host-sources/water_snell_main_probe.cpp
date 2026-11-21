// TEST ONLY: CPU construction is agent-runnable; root exclusively owns GL.
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
namespace frozenSnellMain {
#include "water_residual_sun_reason_probe.cpp"
}
namespace snellMain {
namespace reason=frozenSnellMain::sunReasonProbe;
namespace prior=reason::prior; namespace sun=reason::sun; namespace tracer=reason::tracer;
namespace old=reason::old; namespace angular=reason::angular; namespace light=reason::light;
namespace fs=std::filesystem;
constexpr int size=reason::size,outputs=reason::outputs;
const std::string nodeSHA="4338e67785ec1bb5cf9fb7dca99f31d1913081277bae5afcbf9f46e3d4330e27";
const std::string inputBegin="// AQUALUMEN_SNELL_INPUT_STORE_BEGIN\n",inputEnd="// AQUALUMEN_SNELL_INPUT_STORE_END\n";
bool ownedArtifacts=false;
void require(bool okay,const std::string& why){if(!okay)throw std::runtime_error("INCONCLUSIVE Snell main: "+why);}
std::string field(const std::string& json,const std::string& key){
    const std::regex pattern("\\\""+key+"\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");
    std::sregex_iterator first(json.begin(),json.end(),pattern),end;require(first!=end,"metadata field missing: "+key);
    const auto value=(*first)[1].str();require(++first==end,"duplicate metadata field: "+key);return value;
}
std::string stripInputs(std::string source){
    const std::array<std::string,8> names={"GLOBALS","ENTRY","COVARIANCE","TARGET0","TARGET1","TARGET2","TARGET3","TARGET4"};
    for(const auto& name:names)source=tracer::eraseOne(source,"// AQUALUMEN_SNELL_INPUT_BEGIN:"+name+"\n","// AQUALUMEN_SNELL_INPUT_END:"+name+"\n");
    require(source.find("AQUALUMEN_SNELL_INPUT_")==std::string::npos,"unknown input tag remains");return source;
}
std::string restoreStable(std::string source,bool expanded){
    source=tracer::eraseOne(source,"// AQUALUMEN_SNELL_MAIN_MODULE_BEGIN\n","// AQUALUMEN_SNELL_MAIN_MODULE_END\n");
    const std::array<std::pair<std::string,std::string>,4> spans={{{"BRANCH",
        "        vec3 facet=axis/sqrt(axis2);\n        float facing=dot(facet,viewToEye);\n        float transmittedDot=dot(target,facet);\n        float discriminant=1.0-eta*eta*(1.0-facing*facing);\n        nodeValid=facet.y<0.0 && facing>0.0 && transmittedDot<0.0\n            && discriminant>0.0 && WNS_finite(discriminant);\n"},
        {"RAY","        vec3 transmitted=refract(-viewToEye,facet,eta);\n"},
        {"JACOBIAN","        float jacobian=k2*abs(transmittedDot)/(axis2*pow(abs(facet.y),3.0));\n"},
        {"TRANSMISSION","        float transmission=1.0-waterFresnel(facing,eta,1.0);\n"}}};
    for(const auto& span:spans){const auto begin="// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:"+span.first+"\n",end="// AQUALUMEN_SNELL_MAIN_REPLACE_END:"+span.first+"\n";
        const auto index=source.find(begin);require(index!=std::string::npos,"stable span missing");
        source=tracer::eraseOne(source,begin,end);source.insert(index,span.second);}
    if(expanded)source=tracer::eraseOne(source,"// AQUALUMEN_SNELL_MAIN_EXTENSION_BEGIN\n","// AQUALUMEN_SNELL_MAIN_EXTENSION_END\n");
    require(source.find("AQUALUMEN_SNELL_MAIN_")==std::string::npos,"unknown stable tag remains");return source;
}
struct Sources {std::array<std::string,3> geometry;std::array<std::array<std::string,3>,2> fragment;std::array<std::array<std::string,2>,2> metadata;};
Sources load(const std::array<fs::path,4>& roots){
    Sources result;const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    std::array<std::string,2> reasonHelpers;
    for(int mode=0;mode<2;++mode)for(int observer=0;observer<2;++observer){const auto& root=roots[mode+2*observer];
        const auto manifest=old::readText(root.parent_path()/"WATER-SNELL-MAIN.json");require(manifest.size()<32768,"metadata too large");result.metadata[mode][observer]=manifest;
        require(field(manifest,"schema")=="aqualumen-water-snell-main-v1"&&field(manifest,"mode")== (mode?"stable":"old")&&field(manifest,"observe")== (observer?"inputs":"reasons"),"metadata role differs");
        require(field(manifest,"parent_helper_sha256")==reason::helperSHA,"frozen reason helper provenance differs");
        const auto helper=old::readText(root/"lib/water_residual_sun.glsl"),water=old::readText(root/"gbuffers_water.fsh");
        require(light::digest(helper)==field(manifest,"helper_sha256")&&light::digest(water)==field(manifest,"observer_water_fs_sha256"),"actual helper/FS digest differs");
        const auto expectedHelper=old::readText(root.parent_path()/"SNELL-MAIN-reason-helper.glsl");
        require(light::digest(expectedHelper)==field(manifest,"reason_helper_sha256"),"archived reason helper digest differs");
        require((observer?stripInputs(helper):helper)==expectedHelper,"input helper erasure differs");
        if(!observer)reasonHelpers[mode]=helper;else require(expectedHelper==reasonHelpers[mode],"role helpers differ");
        require(light::digest(mode?restoreStable(expectedHelper,false):expectedHelper)==reason::helperSHA,"stable helper exact restoration differs");
        if(mode){const auto originalNode=old::readText(root.parent_path()/"PARENT-SNELL-MAIN-node.glsl");
            require(light::digest(originalNode)==nodeSHA,"original stable module pin differs");
            const auto adaptedNode=old::readText(root/"lib/water_snell_inverse.glsl");
            const auto expectedNode=angular::replaceOne(originalNode,"#ifndef AQUALUMEN_SNELL_CPU_HOST\n#extension GL_ARB_gpu_shader_fp64 : require\n#endif\n","");
            require(adaptedNode==expectedNode&&light::digest(adaptedNode)==field(manifest,"node_adapted_sha256"),"adapted stable module bytes/pin differ");}
        const auto physicalRaw=old::readText(root.parent_path()/"SNELL-MAIN-physical.fsh");require(light::digest(physicalRaw)==field(manifest,"physical_water_fs_sha256"),"archived physical digest differs");
        const auto rawRecovered=tracer::eraseOne(water,observer?inputBegin:reason::reasonStoreBegin,observer?inputEnd:reason::reasonStoreEnd);
        require(rawRecovered==physicalRaw,"raw STORE removal differs");
        const auto expanded=prior::expandOwner::expand(root/"gbuffers_water.fsh",root);
        auto recovered=tracer::eraseOne(expanded,observer?inputBegin:reason::reasonStoreBegin,observer?inputEnd:reason::reasonStoreEnd);
        if(observer)recovered=stripInputs(recovered);
        recovered=reason::stripReasons(recovered);
        auto physical=prior::expandOwner::expand(root.parent_path()/"SNELL-MAIN-physical.fsh",root);
        if(observer)physical=stripInputs(physical);
        physical=reason::stripReasons(physical);require(recovered==physical,"expanded observer must recover same physical main exactly");
        if(!observer)result.fragment[mode][0]=physical;else require(physical==result.fragment[mode][0],"physical role differs");
        result.fragment[mode][observer+1]=expanded;
        for(int stage=0;stage<3;++stage){const auto geometry=prior::expandOwner::expand(root/stages[stage],root);
            require(light::digest(geometry)==prior::geometrySHA[stage],"phase120 factor4 geometry pin differs");
            if(mode==0&&observer==0)result.geometry[stage]=geometry;else require(result.geometry[stage]==geometry,"geometry source changed");}
        require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"stock atmosphere pin differs");
        require(physical.find("    if (aqualumenSunTestAuthorized==1) {\n"+prior::originalCall+"    }\n")!=std::string::npos,"actual caller uniform guard differs");
    }
    require(restoreStable(result.fragment[1][0],true)==result.fragment[0][0],"stable physical source recovery differs");
    require(light::digest(prior::removeGuard(result.fragment[0][0]))==prior::capExpandedSHA,"original guarded physical CAP pin differs");
    return result;
}
int cpuContract(const std::array<fs::path,4>& roots){const auto source=load(roots);require(!source.fragment[1][2].empty(),"empty input observer");
    std::cout<<"{\"schema\":\"aqualumen-snell-main-construction-v1\",\"GLExecuted\":false,\"observer_recovers_variant_physical_exact\":true,\"stable_restores_old_math_exact\":true,\"roles\":[\"physical\",\"reasons\",\"inputs\"]}\n";return 0;}
bool inputAccounting(const float* values,const float* reasons,const float* status,int guard,bool positive){
    for(int c=0;c<16;++c)if(!std::isfinite(values[c]))return false;
    if(!reason::reasonAccounting(reasons,status,guard,positive)||values[3]!=guard||values[7]!=status[0]||values[11]!=15)return false;
    if(!guard){for(int c=0;c<16;++c)if(c!=11&&values[c]!=0)return false;return true;}
    for(int start:{0,4}){double norm=0;for(int c=0;c<3;++c)norm+=double(values[start+c])*values[start+c];if(std::abs(norm-1)>8*angular::crossArithmetic)return false;}
    const float encoded=values[15],sum=reasons[1]+reasons[2]+reasons[3];
    if(encoded==0){return values[12]==0&&values[13]==0&&values[14]==0&&sum==0&&reasons[0]==0;}
    if(!reason::whole(encoded,624))return false;
    const int first=int(encoded)/64,index=int(encoded)%64;
    if(first<1||first>9||index<1||index>48||first!=reasons[0]||sum==0)return false;
    double norm=0;for(int c=12;c<15;++c)norm+=double(values[c])*values[c];return norm>0&&std::abs(norm-1)<=8*angular::crossArithmetic;
}
int cpuReadback(const fs::path& file,int guard,int positive){
    require((guard==0||guard==1)&&(positive==0||positive==1),"Boolean CPU guard/source required");
    require(fs::file_size(file)==24*sizeof(float),"one exact24-float observation required");
    std::array<float,24> values={};std::ifstream input(file,std::ios::binary);input.read(reinterpret_cast<char*>(values.data()),sizeof(values));require(bool(input),"cannot read observation");
    require(inputAccounting(values.data(),values.data()+16,values.data()+20,guard,positive),"synthetic observation contract rejected");
    std::cout<<"{\"schema\":\"aqualumen-snell-main-readback-construction-v1\",\"GLExecuted\":false,\"syntheticOnly\":true,\"observation\":"<<old::quote(values[15]==0?"NO_FAILED_TARGET_OBSERVED":"FIRST_FAILED_TARGET_OBSERVED")<<"}\n";return 0;
}
std::vector<float> central(const std::vector<float>& values){std::vector<float> result;
    for(int y=88;y<=168;++y)for(int x=88;x<=168;++x)if((x-128)*(x-128)+(y-128)*(y-128)<=1600){const int p=(y*size+x)*4;result.insert(result.end(),values.begin()+p,values.begin()+p+4);}
    return result;
}
void sample(std::ostringstream& out,const std::array<std::array<old::Capture,3>,2>& frames){
    out<<'[';for(std::size_t i=0;i<sun::pixels.size();++i){if(i)out<<',';const auto point=sun::pixels[i];const int p=(point.second*size+point.first)*4;
        out<<"{\"pixel\":["<<point.first<<','<<point.second<<"],\"variants\":[";
        for(int mode=0;mode<2;++mode){if(mode)out<<',';out<<"{\"mode\":"<<old::quote(mode?"stable":"old")<<",\"physical_C0\":";angular::four(out,&frames[mode][0].images[0][p]);
            out<<",\"reason_C9\":";angular::four(out,&frames[mode][1].images[1][p]);out<<",\"WNS_status\":";angular::four(out,&frames[mode][1].images[2][p]);
            out<<",\"inputs\":[";for(int slot=1;slot<5;++slot){if(slot>1)out<<',';angular::four(out,&frames[mode][2].images[slot][p]);}out<<"]}";}out<<"]}";}out<<']';
}
int run(const std::array<fs::path,4>& roots,const fs::path& artifacts){
    static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,"binary32 required");const std::uint32_t endian=1;
    require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian required");require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW output required");const auto source=load(roots);
    require(fs::create_directories(artifacts),"cannot create NEW output");ownedArtifacts=true;
    const std::array<std::string,3> roles={"physical","reasons","inputs"};const std::array<std::string,2> modes={"old","stable"};
    for(int stage=0;stage<3;++stage)old::writeText(artifacts/("geometry-stage"+std::to_string(stage)+".glsl"),source.geometry[stage]);
    for(int mode=0;mode<2;++mode){for(int role=0;role<3;++role)old::writeText(artifacts/(modes[mode]+"-"+roles[role]+"-expanded.fsh"),source.fragment[mode][role]);
        for(int observer=0;observer<2;++observer)old::writeText(artifacts/(modes[mode]+"-"+roles[observer+1]+"-metadata.json"),source.metadata[mode][observer]);}
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("RTX 3080 Ti")!=std::string::npos,"actual RTX3080Ti required");
    require(epoxy_has_gl_extension("GL_ARB_gpu_shader_fp64"),"actual fp64 extension required");sun::Fixture fixture;GLint patch=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);require(patch==3&&!glIsEnabled(GL_CULL_FACE),"patch3/culling-off required");
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-snell-main-native-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"fp64Available\":true,\"size\":"<<size<<",\"phase_seconds\":120,\"patch_arity\":"<<patch<<",\"geometry_sources_identical\":true,\"source_recovery_qualified\":true,\"rawFormat\":\"little-endian binary32 bottom-left origin\",\"input_C12_is_TES\":false,\"same_draw_input_payload\":true,\"policy\":{\"observer_C0_absolute\":"<<tracer::passiveAbsolute<<",\"observer_C0_relative\":"<<tracer::passiveRelative<<",\"depth_absolute\":"<<tracer::depthTolerance<<",\"cross_variant_C0_absolute\":2e-6,\"cross_variant_C0_relative\":2e-4,\"cross_variant_mean_view_XYZ_absolute_relative\":"<<angular::crossArithmetic<<",\"repeat_absolute\":0,\"reason_TES_absolute\":0,\"ROI_center\":[128,128],\"ROI_radius\":40},\"programs\":[";
    std::array<std::array<GLuint,3>,2> programs={};bool firstProgram=true;
    for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){if(!firstProgram)report<<',';firstProgram=false;
        programs[mode][role]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.fragment[mode][role]}},modes[mode]+"-"+roles[role],report);}
    report<<"],\"cases\":[";bool allQualified=true,allAccepted=true;
    for(int scenario=0;scenario<5;++scenario){const bool wide=scenario==4,positive=wide||scenario>=2;const int guard=wide?1:scenario%2;
        const std::string name=wide?"wide60-cachepositive-guard1":"central2-cache"+std::string(positive?"positive":"zero")+"-guard"+std::to_string(guard);
        const auto directory=artifacts/name;require(fs::create_directory(directory),"NEW case directory required");fixture.scene(2,0,positive,directory);if(wide)reason::wideProjection(fixture);
        if(scenario){report<<',';}report<<"{\"path\":"<<old::quote(name)<<",\"aperture_degrees\":"<<(wide?60:2)<<",\"positive_cache\":"<<(positive?"true":"false")<<",\"guard\":"<<guard<<",\"central_acceptance_case\":"<<(wide?"false":"true")<<",\"queried_program_sources\":[";
        tracer::Sources query;query.geometry=source.geometry;bool firstQuery=true;
        for(int mode=0;mode<2;++mode)for(int role=1;role<3;++role){if(!firstQuery)report<<',';firstQuery=false;sun::queriedSources(report,{programs[mode][0],programs[mode][role]},query,{source.fragment[mode][0],source.fragment[mode][role]});}
        report<<']';
        std::array<std::array<old::Capture,3>,2> frames,repeats;std::array<std::vector<float>,8> referenceInputs={};bool haveInputs=false;
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){const auto label=modes[mode]+"-"+roles[role];
            frames[mode][role]=prior::capture(fixture,programs[mode][role],guard,role!=0,directory,label);repeats[mode][role]=prior::capture(fixture,programs[mode][role],guard,role!=0,directory,label+"-repeat");
            const auto inputDirectory=directory/(label+"-actual-inputs");require(fs::create_directory(inputDirectory),"NEW role inputs directory required");
            const auto inputs=sun::snapshotInputs(fixture,programs[mode][role],inputDirectory);prior::guardSnapshot(programs[mode][role],guard,inputDirectory,"actual-inputs");
            if(haveInputs)require(inputs==referenceInputs,"actual texture inputs differ across variants/roles");else{referenceInputs=inputs;haveInputs=true;}}
        report<<",\"comparisons\":[";bool firstComparison=true,caseAccepted=true;
        auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double absolute,double relative=0){caseAccepted=tracer::compare(report,firstComparison,label,a,b,absolute,relative)&&caseAccepted;};
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){const auto label=modes[mode]+"-"+roles[role];
            for(int slot=0;slot<outputs;++slot)compare(label+"-slot"+std::to_string(slot)+"-repeat",frames[mode][role].images[slot],repeats[mode][role].images[slot],0);
            compare(label+"-depth-repeat",frames[mode][role].depth,repeats[mode][role].depth,0);
            if(role){compare(label+"-C0-passive",frames[mode][0].images[0],frames[mode][role].images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare(label+"-depth-passive",frames[mode][0].depth,frames[mode][role].depth,tracer::depthTolerance);}
            if(role==1)compare(label+"-C12-TES-exact",frames[mode][0].images[4],frames[mode][1].images[4],0);}
        for(int mode=0;mode<2;++mode)compare(modes[mode]+"-reason-input-covariance-flags-exact",frames[mode][1].images[3],frames[mode][2].images[3],0);
        for(int slot:{1,2}){compare("cross-variant-input-slot"+std::to_string(slot)+"-XYZ-EPS8",angular::channels(frames[0][2].images[slot],false),angular::channels(frames[1][2].images[slot],false),angular::crossArithmetic,angular::crossArithmetic);
            compare("cross-variant-input-slot"+std::to_string(slot)+"-alpha-exact",angular::channels(frames[0][2].images[slot],true),angular::channels(frames[1][2].images[slot],true),0);}
        compare("cross-variant-input-covariance-flags-exact",frames[0][2].images[3],frames[1][2].images[3],0);compare("cross-variant-physical-depth-exact",frames[0][0].depth,frames[1][0].depth,0);
        compare("cross-variant-physical-TES-exact",frames[0][0].images[4],frames[1][0].images[4],0);
        if(!wide){const bool regression=!guard||!positive;compare(regression?"old-stable-C0-regression":"old-stable-C0-central-optical-comparison",regression?frames[0][0].images[0]:central(frames[0][0].images[0]),regression?frames[1][0].images[0]:central(frames[1][0].images[0]),2e-6,2e-4);}
        std::array<int,2> inspected={},qualified={},accounted={},applied={},firstTargets={};std::array<std::array<int,10>,2> firstReasons={};
        for(int mode=0;mode<2;++mode)for(int y=0;y<size;++y)for(int x=0;x<size;++x){if(!wide&&(x-128)*(x-128)+(y-128)*(y-128)>1600)continue;const int p=(y*size+x)*4;
            const auto* covariance=&frames[mode][1].images[3][p];if(wide&&(frames[mode][0].images[4][p+3]==0||covariance[3]!=15))continue;
            ++inspected[mode];const auto* reasons=&frames[mode][1].images[1][p];const auto* status=&frames[mode][1].images[2][p];
            bool domain=covariance[3]==15&&prior::stageQualified(&frames[mode][0].images[4][p])&&prior::stageQualified(&frames[mode][1].images[4][p]);
            for(int role=0;role<3;++role)domain=domain&&frames[mode][role].images[0][p+3]==1;
            if(guard)domain=domain&&reason::covarianceDomain(covariance);else for(int c=0;c<3;++c)domain=domain&&covariance[c]==0;
            if(!wide)domain=domain&&status[0]==guard&&status[1]==int(guard&&positive)&&status[3]==0;
            qualified[mode]+=domain;std::array<float,16> inputValues={};for(int slot=1;slot<5;++slot)std::copy_n(&frames[mode][2].images[slot][p],4,inputValues.data()+(slot-1)*4);
            const bool accounting=inputAccounting(inputValues.data(),reasons,status,guard,positive);accounted[mode]+=accounting;
            applied[mode]+=status[1]==1;firstTargets[mode]+=inputValues[15]>0;if(reason::whole(reasons[0],9))++firstReasons[mode][int(reasons[0])];}
        bool caseQualified=true,caseAccounting=true;for(int mode=0;mode<2;++mode){caseQualified=caseQualified&&inspected[mode]>0&&qualified[mode]==inspected[mode]&&(wide||inspected[mode]==5025);caseAccounting=caseAccounting&&accounted[mode]==inspected[mode];}
        const bool centralAccepted=caseAccepted&&caseAccounting;allQualified=allQualified&&(wide||caseQualified);allAccepted=allAccepted&&centralAccepted;
        report<<"],\"inspected_points_old_stable\":";angular::numbers(report,inspected);report<<",\"domain_qualified_points_old_stable\":";angular::numbers(report,qualified);report<<",\"input_accounted_points_old_stable\":";angular::numbers(report,accounted);
        report<<",\"applied_points_old_stable\":";angular::numbers(report,applied);report<<",\"first_failed_target_points_old_stable\":";angular::numbers(report,firstTargets);report<<",\"first_reason_histograms_old_stable\":[";angular::numbers(report,firstReasons[0]);report<<',';angular::numbers(report,firstReasons[1]);
        report<<"],\"fixture_qualified\":"<<(caseQualified?"true":"false")<<",\"passivity_input_accounting_and_regression_accepted\":"<<(centralAccepted?"true":"false")<<",\"fixed_six_samples\":";sample(report,frames);report<<'}';
    }
    const auto status=!allQualified?"INCONCLUSIVE":allAccepted?"PASS":"RED";
    report<<"],\"case_count\":5,\"fixture_qualified\":"<<(allQualified?"true":"false")<<",\"accepted\":"<<(allQualified&&allAccepted?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"forced_critical_fixture\":false,\"numeric_bug_reproduced\":false,\"physics_accepted\":false,\"pixel_AA_accepted\":false,\"Iris_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Actual four-stage water-main call/passivity/regression and first-failed generated-target export. No forced mean/view/caller or optical RED claim. Central5025 remains fixed; wide60 is descriptive eligible raster evidence, not new acceptance corpus. Input C12 carries actual first failed target plus packed index/reason, never TES; no target means not observed, not physical zero. Old/stable positive C0 comparison is an empirical interior regression gate, not an energy/reference oracle or full cap qualification.\"}\n";
    old::writeText(artifacts/"result.json",report.str());for(const auto& row:programs)for(const auto program:row)glDeleteProgram(program);
    std::cout<<status<<" actual-water-main export "<<artifacts<<'\n';return !allQualified?2:allAccepted?0:1;
}
}
int main(int argc,char** argv){try{if(argc==6&&std::string(argv[1])=="--cpu-contract")return snellMain::cpuContract({std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4]),std::filesystem::absolute(argv[5])});
    if(argc==5&&std::string(argv[1])=="--cpu-readback")return snellMain::cpuReadback(std::filesystem::absolute(argv[2]),std::stoi(argv[3]),std::stoi(argv[4]));
    if(argc==6)return snellMain::run({std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4])},std::filesystem::absolute(argv[5]));
    std::cerr<<"usage: water_snell_main_probe --cpu-contract OLD_REASON STABLE_REASON OLD_INPUT STABLE_INPUT\n       --cpu-readback PAYLOAD24.f32 GUARD POSITIVE_CACHE\n       OLD_REASON STABLE_REASON OLD_INPUT STABLE_INPUT NEW_OUTPUT\n";return 2;
}catch(const std::exception& failure){std::cerr<<failure.what()<<'\n';
    if(snellMain::ownedArtifacts&&argc==6)try{snellMain::old::writeText(std::filesystem::absolute(argv[5])/"failure.txt",std::string(failure.what())+'\n');}catch(...){}
    return 2;}}
