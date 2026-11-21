// NEW TEST ONLY. CPU construction is allowed; root exclusively owns GL.
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
namespace frozenSupport {
#include "water_snell_main_probe.cpp"
}
namespace supportProbe {
namespace priorMain=frozenSupport::snellMain;
namespace reason=priorMain::reason; namespace prior=priorMain::prior;
namespace sun=priorMain::sun; namespace tracer=priorMain::tracer;
namespace old=priorMain::old; namespace angular=priorMain::angular;
namespace light=priorMain::light; namespace fs=std::filesystem;
constexpr int size=priorMain::size,outputs=priorMain::outputs;
bool ownedArtifacts=false;
void require(bool okay,const std::string& why){if(!okay)throw std::runtime_error("INCONCLUSIVE Sun support: "+why);}
const std::array<std::string,2> parentHelpers={"a0f5a99736429e07a839cf8b7c0ec2c67f5f19486600b714a924dc947b7ff9fd","0d62d7b6d9067934c62787677070eb7aa923c7b4eff67ec3250a218d0af3579e"};
const std::array<std::string,2> parentWaters={"9ff50e1232b6c1a3e2478b9dfaa97ce223dddef58ed11fb6b088fdca22a856c1","2163974162c8656811b18a595f0fa950279db3cdebff431204f07bcbdee430a9"};
const std::string parentPhysical="dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4";
const std::string certificateSHA="f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a";
struct Sources {std::array<std::string,3> geometry;std::array<std::array<std::string,3>,2> fragment;std::array<std::array<std::string,2>,2> metadata;};
Sources loadReject(const std::array<fs::path,2>& roots){
    Sources result;const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int observer=0;observer<2;++observer){const auto& root=roots[observer];
        const auto metadata=old::readText(root.parent_path()/"WATER-SUN-SUPPORT.json");require(metadata.size()<32768,"bounded metadata required");
        require(priorMain::field(metadata,"schema")=="aqualumen-water-sun-support-v1"&&priorMain::field(metadata,"mode")=="reject"&&priorMain::field(metadata,"observe")== (observer?"inputs":"reasons"),"reject metadata role differs");
        result.metadata[0][observer]=metadata;
        const auto helper=old::readText(root/"lib/water_residual_sun.glsl"),water=old::readText(root/"gbuffers_water.fsh");
        const auto physicalRaw=old::readText(root.parent_path()/"PARENT-SUN-SUPPORT-physical.fsh");
        require(light::digest(helper)==parentHelpers[observer]&&light::digest(water)==parentWaters[observer]&&light::digest(physicalRaw)==parentPhysical,"frozen reject source pin differs");
        require(helper==old::readText(root.parent_path()/"PARENT-SUN-SUPPORT-helper.glsl")&&water==old::readText(root.parent_path()/"PARENT-SUN-SUPPORT-water.fsh"),"reject parent bytes differ");
        require(light::digest(helper)==priorMain::field(metadata,"helper_sha256")&&light::digest(water)==priorMain::field(metadata,"observer_water_fs_sha256"),"metadata source digest differs");
        require(tracer::eraseOne(water,observer?priorMain::inputBegin:reason::reasonStoreBegin,observer?priorMain::inputEnd:reason::reasonStoreEnd)==physicalRaw,"raw observer exact recovery differs");
        auto expanded=prior::expandOwner::expand(root/"gbuffers_water.fsh",root);
        auto physical=tracer::eraseOne(expanded,observer?priorMain::inputBegin:reason::reasonStoreBegin,observer?priorMain::inputEnd:reason::reasonStoreEnd);
        if(observer){physical=priorMain::stripInputs(physical);}physical=reason::stripReasons(physical);
        if(observer){require(physical==result.fragment[0][0],"physical observer roles differ");}else{result.fragment[0][0]=physical;}
        result.fragment[0][observer+1]=expanded;
        const auto originalNode=old::readText(root.parent_path()/"PARENT-SNELL-MAIN-node.glsl");require(light::digest(originalNode)==priorMain::nodeSHA,"original inverse module pin differs");
        const auto adapted=angular::replaceOne(originalNode,"#ifndef AQUALUMEN_SNELL_CPU_HOST\n#extension GL_ARB_gpu_shader_fp64 : require\n#endif\n","");
        require(old::readText(root/"lib/water_snell_inverse.glsl")==adapted,"adapted stable module differs");
        for(int stage=0;stage<3;++stage){const auto source=prior::expandOwner::expand(root/stages[stage],root);require(light::digest(source)==prior::geometrySHA[stage],"phase120 factor4 geometry pin differs");
            if(observer){require(source==result.geometry[stage],"geometry roles differ");}else{result.geometry[stage]=source;}}
        require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"native atmosphere pin differs");
        require(light::digest(prior::removeGuard(priorMain::restoreStable(physical,true)))==prior::capExpandedSHA,"frozen guarded CAP recovery differs");
    }return result;
}
std::string restoreSupport(std::string source){
    for(const auto& name:std::array<std::string,4>{"INCLUDE","RESET","POLICY","QUALIFICATION"}){
        const auto begin="// AQUALUMEN_SUN_SUPPORT_BEGIN:"+name+"\n",end="// AQUALUMEN_SUN_SUPPORT_END:"+name+"\n";
        const auto position=source.find(begin);require(position!=std::string::npos,"support tag missing: "+name);
        source=tracer::eraseOne(source,begin,end);
        if(name=="QUALIFICATION")source.insert(position,"        nodeValid=snell.status==1;\n");
    }require(source.find("AQUALUMEN_SUN_SUPPORT_")==std::string::npos,"unknown support tag remains");return source;
}
Sources load(const std::array<fs::path,4>& roots){
    auto result=loadReject({roots[0],roots[2]});const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int observer=0;observer<2;++observer){const auto& root=roots[1+2*observer];
        const auto metadata=old::readText(root.parent_path()/"WATER-SUN-SUPPORT.json");require(metadata.size()<32768,"bounded metadata required");
        require(priorMain::field(metadata,"schema")=="aqualumen-water-sun-support-v1"&&priorMain::field(metadata,"mode")=="zero"&&priorMain::field(metadata,"observe")== (observer?"inputs":"reasons"),"zero metadata role differs");
        result.metadata[1][observer]=metadata;
        const auto helper=old::readText(root/"lib/water_residual_sun.glsl"),water=old::readText(root/"gbuffers_water.fsh");
        require(light::digest(helper)==priorMain::field(metadata,"helper_sha256")&&light::digest(water)==priorMain::field(metadata,"observer_water_fs_sha256"),"zero actual helper/FS digest differs");
        require(light::digest(old::readText(root/"lib/water_sun_support.glsl"))==certificateSHA,"Q24 certificate source pin differs");
        require(light::digest(restoreSupport(helper))==parentHelpers[observer],"support helper exact parent recovery differs");
        const auto parentWater=old::readText(root.parent_path()/"PARENT-SUN-SUPPORT-water.fsh");require(light::digest(parentWater)==parentWaters[observer],"zero archived parent water differs");
        const auto parentHelper=old::readText(root.parent_path()/"PARENT-SUN-SUPPORT-helper.glsl");require(restoreSupport(helper)==parentHelper,"zero parent helper bytes differ");
        const auto physicalRaw=old::readText(root.parent_path()/"SUN-SUPPORT-physical.fsh");require(light::digest(physicalRaw)==parentPhysical,"zero physical raw main differs");
        const auto rawRecovered=tracer::eraseOne(water,observer?priorMain::inputBegin:"// AQUALUMEN_SUN_SUPPORT_STORE_BEGIN\n",observer?priorMain::inputEnd:"// AQUALUMEN_SUN_SUPPORT_STORE_END\n");
        require(rawRecovered==physicalRaw,"zero raw STORE removal differs");
        auto expanded=prior::expandOwner::expand(root/"gbuffers_water.fsh",root);
        auto physical=tracer::eraseOne(expanded,observer?priorMain::inputBegin:"// AQUALUMEN_SUN_SUPPORT_STORE_BEGIN\n",observer?priorMain::inputEnd:"// AQUALUMEN_SUN_SUPPORT_STORE_END\n");
        if(observer){physical=priorMain::stripInputs(physical);}physical=reason::stripReasons(physical);
        if(observer){require(physical==result.fragment[1][0],"zero physical roles differ");}else{result.fragment[1][0]=physical;}
        result.fragment[1][observer+1]=expanded;
        require(restoreSupport(physical)==result.fragment[0][0],"expanded zero policy exact recovery differs");
        const auto node=old::readText(root/"lib/water_snell_inverse.glsl");require(node==old::readText(roots[2*observer]/"lib/water_snell_inverse.glsl"),"support changed stable inverse node");
        for(int stage=0;stage<3;++stage)require(prior::expandOwner::expand(root/stages[stage],root)==result.geometry[stage],"support changed geometry stage");
        require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"support changed native atmosphere");
    }return result;
}
int cpuContract(const std::array<fs::path,2>& roots){loadReject(roots);std::cout<<"{\"schema\":\"aqualumen-water-sun-support-construction-v1\",\"GLExecuted\":false,\"reject_parent_source_exact\":true,\"observer_recovers_variant_physical_exact\":true}\n";return 0;}
int cpuContract(const std::array<fs::path,4>& roots){load(roots);std::cout<<"{\"schema\":\"aqualumen-water-sun-support-construction-v1\",\"GLExecuted\":false,\"reject_parent_source_exact\":true,\"observer_recovers_variant_physical_exact\":true,\"zero_restores_reject_exact\":true,\"roles\":[\"physical\",\"reasons\",\"inputs\"]}\n";return 0;}
bool decodeCounts(float packed,std::array<int,4>& counts){
    if(!reason::whole(packed,16777215))return false;
    const auto word=std::uint32_t(packed);for(int i=0;i<4;++i)counts[i]=int((word>>(6*i))&63u);
    return counts[0]<=48&&counts[1]<=48&&counts[2]<=48&&counts[3]<=48&&counts[0]+counts[1]+counts[2]==counts[3];
}
bool countStatus(float packed,int applied,int rejected,std::array<int,4>& counts){
    if(!decodeCounts(packed,counts)||(applied!=0&&applied!=1)||rejected<0||rejected>48)return false;
    if(applied)return counts[3]==48&&counts[2]==0&&rejected==0;
    return counts[2]==0||rejected>0;
}
int cpuCounts(const char* word,const char* applied,const char* rejected){
    std::array<int,4> counts={};require(countStatus(std::stof(word),std::stoi(applied),std::stoi(rejected),counts),"certificate count/status contract rejected");
    std::ostringstream report;report<<"{\"schema\":\"aqualumen-sun-support-count-construction-v1\",\"GLExecuted\":false,\"syntheticOnly\":true,\"counts\":";angular::numbers(report,counts);
    report<<",\"continuum_zero_proven\":false}\n";std::cout<<report.str();return 0;
}
bool accounting(const float* values,const float* reasons,const float* status,int guard,bool positive,bool zero,std::array<int,4>& counts){
    for(int c=0;c<16;++c)if(!std::isfinite(values[c]))return false;
    if(!reason::whole(status[0],1)||!reason::whole(status[1],1)||!reason::whole(status[3],48))return false;
    if(!zero){if(status[2]!=0)return false;counts={};}
    else if(!countStatus(status[2],int(status[1]),int(status[3]),counts))return false;
    // Rejection accounting concerns original requested/applied/rejection fields;
    // z is separately decoded above, never misreported as native source kind.
    const std::array<float,4> originalStatus={status[0],status[1],0,status[3]};
    if(!reason::reasonAccounting(reasons,originalStatus.data(),guard,positive)||values[3]!=guard||values[7]!=status[0]||values[11]!=15)return false;
    if(zero&&(((!guard||!positive)&&status[2]!=0)||counts[2]>status[3]||counts[2]>reasons[3]||reasons[1]+reasons[2]+reasons[3]>48-counts[0]))return false;
    if(!guard){for(int c=0;c<16;++c)if(c!=11&&values[c]!=0)return false;return true;}
    for(int start:{0,4}){double norm=0;for(int c=0;c<3;++c)norm+=double(values[start+c])*values[start+c];if(std::abs(norm-1)>8*angular::crossArithmetic)return false;}
    const float encoded=values[15],sum=reasons[1]+reasons[2]+reasons[3];
    if(encoded==0)return values[12]==0&&values[13]==0&&values[14]==0&&sum==0&&reasons[0]==0;
    if(!reason::whole(encoded,624))return false;
    const int first=int(encoded)/64,index=int(encoded)%64;if(first<1||first>9||index<1||index>48||first!=reasons[0]||sum==0)return false;
    double norm=0;for(int c=12;c<15;++c)norm+=double(values[c])*values[c];return norm>0&&std::abs(norm-1)<=8*angular::crossArithmetic;
}
int cpuReadback(const fs::path& path,int guard,int positive,int zero){
    require((guard==0||guard==1)&&(positive==0||positive==1)&&(zero==0||zero==1),"Boolean CPU inputs required");require(fs::file_size(path)==24*sizeof(float),"exact24-float observation required");
    std::array<float,24> values={};std::ifstream input(path,std::ios::binary);input.read(reinterpret_cast<char*>(values.data()),sizeof(values));require(bool(input),"cannot read CPU observation");
    std::array<int,4> counts={};require(accounting(values.data(),values.data()+16,values.data()+20,guard,positive,zero,counts),"input/reason/count contract rejected");
    std::ostringstream report;report<<"{\"GLExecuted\":false,\"syntheticOnly\":true,\"counts\":";angular::numbers(report,counts);report<<"}\n";std::cout<<report.str();return 0;
}
void wide90(sun::Fixture& fixture){
    const float focal=float(1/std::tan(3.14159265358979323846/4)),near=.01f,far=128,a=-(far+near)/(far-near),b=-2*far*near/(far-near);
    fixture.aperture=90;fixture.projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};
    fixture.inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,0,1/b,0,0,-1,a/b};
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(fixture.projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(old::up.data());old::glOkay("support wide90 projection only");
}
void samples(std::ostringstream& out,const std::array<std::array<old::Capture,3>,2>& frames){
    out<<'[';for(std::size_t i=0;i<sun::pixels.size();++i){if(i)out<<',';const auto point=sun::pixels[i];const int p=(point.second*size+point.first)*4;
        out<<"{\"pixel\":["<<point.first<<','<<point.second<<"],\"variants\":[";
        for(int mode=0;mode<2;++mode){if(mode)out<<',';out<<"{\"mode\":"<<old::quote(mode?"zero":"reject")<<",\"physical_C0\":";angular::four(out,&frames[mode][0].images[0][p]);
            out<<",\"reason_C9\":";angular::four(out,&frames[mode][1].images[1][p]);out<<",\"WNS_requested_applied_countword_rejected\":";angular::four(out,&frames[mode][1].images[2][p]);
            out<<",\"certificate_counts_collected\":"<<(mode?"true":"false")<<",\"counts_zero_support_unknown_calls\":";std::array<int,4> counts={};require(decodeCounts(frames[mode][1].images[2][p+2],counts),"selected countword malformed");angular::numbers(out,counts);
            out<<",\"inputs\":[";for(int slot=1;slot<5;++slot){if(slot>1)out<<',';angular::four(out,&frames[mode][2].images[slot][p]);}out<<"]}";}
        out<<"]}";}out<<']';
}
int run(const std::array<fs::path,4>& roots,const fs::path& artifacts){
    static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,"binary32 required");const std::uint32_t endian=1;
    require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian required");require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW output required");const auto source=load(roots);
    require(fs::create_directories(artifacts),"cannot create NEW output");ownedArtifacts=true;
    const std::array<std::string,3> roles={"physical","reasons","inputs"};const std::array<std::string,2> modes={"reject","zero"};
    for(int stage=0;stage<3;++stage)old::writeText(artifacts/("geometry-stage"+std::to_string(stage)+".glsl"),source.geometry[stage]);
    for(int mode=0;mode<2;++mode){for(int role=0;role<3;++role)old::writeText(artifacts/(modes[mode]+"-"+roles[role]+"-expanded.fsh"),source.fragment[mode][role]);
        for(int observer=0;observer<2;++observer)old::writeText(artifacts/(modes[mode]+"-"+roles[observer+1]+"-metadata.json"),source.metadata[mode][observer]);}
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("RTX 3080 Ti")!=std::string::npos,"actual RTX3080Ti required");
    require(epoxy_has_gl_extension("GL_ARB_gpu_shader_fp64"),"actual retained fp64 extension required");sun::Fixture fixture;GLint patch=0;glGetIntegerv(GL_PATCH_VERTICES,&patch);require(patch==3&&!glIsEnabled(GL_CULL_FACE),"patch3/culling-off required");
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-water-sun-support-native-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"patch_arity\":"<<patch<<",\"geometry_sources_identical\":true,\"source_recovery_qualified\":true,\"rawFormat\":\"little-endian binary32 bottom-left origin\",\"input_C12_is_TES\":false,\"same_draw_input_payload\":true,\"actual_shader_output_slots\":[0,1,2,3,4],\"inactive_cleared_slots\":[5,6,7],\"policy\":{\"observer_C0_absolute\":"<<tracer::passiveAbsolute<<",\"observer_C0_relative\":"<<tracer::passiveRelative<<",\"depth_absolute\":"<<tracer::depthTolerance<<",\"cross_variant_C0_absolute\":2e-6,\"cross_variant_C0_relative\":2e-4,\"cross_variant_mean_view_XYZ_absolute_relative\":"<<angular::crossArithmetic<<",\"repeat_absolute\":0,\"reason_TES_absolute\":0,\"ROI_center\":[128,128],\"ROI_radius\":40},\"programs\":[";
    std::array<std::array<GLuint,3>,2> programs={};bool firstProgram=true;
    for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){if(!firstProgram)report<<',';firstProgram=false;
        programs[mode][role]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.fragment[mode][role]}},modes[mode]+"-"+roles[role],report);}
    report<<"],\"cases\":[";bool allQualified=true,allAccepted=true;long long observedZeroNodes=0;
    for(int scenario=0;scenario<6;++scenario){const bool wide=scenario>=4,positive=wide||scenario>=2;const int guard=wide?1:scenario%2,aperture=wide?(scenario==4?60:90):2;
        const std::string name=wide?"wide"+std::to_string(aperture)+"-cachepositive-guard1":"central2-cache"+std::string(positive?"positive":"zero")+"-guard"+std::to_string(guard);
        const auto directory=artifacts/name;require(fs::create_directory(directory),"NEW case directory required");fixture.scene(2,0,positive,directory);if(scenario==4)reason::wideProjection(fixture);if(scenario==5)wide90(fixture);
        if(scenario){report<<',';}report<<"{\"path\":"<<old::quote(name)<<",\"aperture_degrees\":"<<aperture<<",\"positive_cache\":"<<(positive?"true":"false")<<",\"guard\":"<<guard<<",\"central_acceptance_case\":"<<(wide?"false":"true")<<",\"queried_program_sources\":[";
        tracer::Sources query;query.geometry=source.geometry;bool firstQuery=true;
        for(int mode=0;mode<2;++mode){for(int role=1;role<3;++role){if(!firstQuery)report<<',';firstQuery=false;sun::queriedSources(report,{programs[mode][0],programs[mode][role]},query,{source.fragment[mode][0],source.fragment[mode][role]});}}report<<']';
        std::array<std::array<old::Capture,3>,2> frames,repeats;std::array<std::vector<float>,8> referenceInputs={};bool haveInputs=false;
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){const auto label=modes[mode]+"-"+roles[role];
            frames[mode][role]=prior::capture(fixture,programs[mode][role],guard,role!=0,directory,label);repeats[mode][role]=prior::capture(fixture,programs[mode][role],guard,role!=0,directory,label+"-repeat");
            const auto inputDirectory=directory/(label+"-actual-inputs");require(fs::create_directory(inputDirectory),"NEW actual input directory required");
            const auto inputs=sun::snapshotInputs(fixture,programs[mode][role],inputDirectory);prior::guardSnapshot(programs[mode][role],guard,inputDirectory,"actual-inputs");
            if(haveInputs)require(inputs==referenceInputs,"actual texture inputs differ across modes/roles");else{referenceInputs=inputs;haveInputs=true;}}
        report<<",\"comparisons\":[";bool firstComparison=true,caseAccepted=true;
        auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double absolute,double relative=0){caseAccepted=tracer::compare(report,firstComparison,label,a,b,absolute,relative)&&caseAccepted;};
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){const auto label=modes[mode]+"-"+roles[role];
            for(int slot=0;slot<outputs;++slot)compare(label+"-slot"+std::to_string(slot)+"-repeat",frames[mode][role].images[slot],repeats[mode][role].images[slot],0);
            compare(label+"-depth-repeat",frames[mode][role].depth,repeats[mode][role].depth,0);
            if(role){compare(label+"-C0-passive",frames[mode][0].images[0],frames[mode][role].images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare(label+"-depth-passive",frames[mode][0].depth,frames[mode][role].depth,tracer::depthTolerance);}
            if(role==1)compare(label+"-C12-TES-exact",frames[mode][0].images[4],frames[mode][1].images[4],0);}
        for(int mode=0;mode<2;++mode)compare(modes[mode]+"-reason-input-covariance-flags-exact",frames[mode][1].images[3],frames[mode][2].images[3],0);
        for(int slot:{1,2}){compare("cross-mode-input-slot"+std::to_string(slot)+"-XYZ-EPS8",angular::channels(frames[0][2].images[slot],false),angular::channels(frames[1][2].images[slot],false),angular::crossArithmetic,angular::crossArithmetic);
            compare("cross-mode-input-slot"+std::to_string(slot)+"-alpha-exact",angular::channels(frames[0][2].images[slot],true),angular::channels(frames[1][2].images[slot],true),0);}
        compare("cross-mode-input-covariance-flags-exact",frames[0][2].images[3],frames[1][2].images[3],0);compare("cross-mode-physical-depth-exact",frames[0][0].depth,frames[1][0].depth,0);compare("cross-mode-physical-TES-exact",frames[0][0].images[4],frames[1][0].images[4],0);
        if(!wide){const bool regression=!guard||!positive;compare(regression?"reject-zero-C0-regression":"reject-zero-C0-central-comparison",regression?frames[0][0].images[0]:priorMain::central(frames[0][0].images[0]),regression?frames[1][0].images[0]:priorMain::central(frames[1][0].images[0]),2e-6,2e-4);}
        std::array<int,2> inspected={},qualified={},accounted={},applied={},firstTargets={},nonwater={},unadmitted={},completeLedgers={},zeroBranches={};
        std::array<std::array<long long,4>,2> totalCounts={};std::array<std::array<int,10>,2> firstReasons={};double wideC0Difference=0;
        for(int mode=0;mode<2;++mode)for(int y=0;y<size;++y)for(int x=0;x<size;++x){if(!wide&&(x-128)*(x-128)+(y-128)*(y-128)>1600)continue;const int p=(y*size+x)*4;
            const auto* covariance=&frames[mode][1].images[3][p];if(wide){if(frames[mode][0].images[4][p+3]==0){++nonwater[mode];continue;}if(covariance[3]!=15){++unadmitted[mode];continue;}}
            ++inspected[mode];const auto* reasons=&frames[mode][1].images[1][p];const auto* status=&frames[mode][1].images[2][p];
            bool domain=covariance[3]==15&&prior::stageQualified(&frames[mode][0].images[4][p])&&prior::stageQualified(&frames[mode][1].images[4][p]);for(int role=0;role<3;++role)domain=domain&&frames[mode][role].images[0][p+3]==1;
            if(guard)domain=domain&&reason::covarianceDomain(covariance);else for(int c=0;c<3;++c)domain=domain&&covariance[c]==0;
            if(!wide){domain=domain&&status[0]==guard&&status[1]==int(guard&&positive)&&status[3]==0;}qualified[mode]+=domain;
            std::array<float,16> inputValues={};for(int slot=1;slot<5;++slot)std::copy_n(&frames[mode][2].images[slot][p],4,inputValues.data()+(slot-1)*4);
            std::array<int,4> counts={};const bool counted=accounting(inputValues.data(),reasons,status,guard,positive,mode==1,counts);accounted[mode]+=counted;
            if(counted){for(int c=0;c<4;++c)totalCounts[mode][c]+=counts[c];completeLedgers[mode]+=mode&&counts[3]==48;zeroBranches[mode]+=mode&&counts[0]>0;}
            applied[mode]+=status[1]==1;firstTargets[mode]+=inputValues[15]>0;if(reason::whole(reasons[0],9))++firstReasons[mode][int(reasons[0])];
            if(wide&&mode==0)for(int c=0;c<3;++c)wideC0Difference=std::max(wideC0Difference,std::abs(double(frames[0][0].images[0][p+c])-frames[1][0].images[0][p+c]));}
        bool caseQualified=true,caseAccounting=true;for(int mode=0;mode<2;++mode){caseQualified=caseQualified&&inspected[mode]>0&&qualified[mode]==inspected[mode]&&(wide||inspected[mode]==5025);caseAccounting=caseAccounting&&accounted[mode]==inspected[mode];}
        const bool casePass=caseAccepted&&caseAccounting;allQualified=allQualified&&caseQualified;allAccepted=allAccepted&&casePass;observedZeroNodes+=totalCounts[1][0];
        report<<"],\"inspected_points_reject_zero\":";angular::numbers(report,inspected);report<<",\"domain_qualified_points_reject_zero\":";angular::numbers(report,qualified);report<<",\"input_count_accounted_points_reject_zero\":";angular::numbers(report,accounted);
        report<<",\"applied_points_reject_zero\":";angular::numbers(report,applied);report<<",\"first_failed_target_points_reject_zero\":";angular::numbers(report,firstTargets);report<<",\"first_reason_histograms_reject_zero\":[";angular::numbers(report,firstReasons[0]);report<<',';angular::numbers(report,firstReasons[1]);
        report<<"],\"nonwater_points_reject_zero\":";angular::numbers(report,nonwater);report<<",\"unadmitted_points_reject_zero\":";angular::numbers(report,unadmitted);report<<",\"complete48_certificate_ledger_points_reject_zero\":";angular::numbers(report,completeLedgers);report<<",\"observed_zero_branch_points_reject_zero\":";angular::numbers(report,zeroBranches);
        report<<",\"certificate_class_totals_reject_zero\":[";angular::numbers(report,totalCounts[0]);report<<',';angular::numbers(report,totalCounts[1]);report<<"],\"reject_counts_collected\":false,\"zero_counts_collected\":true,\"wide_C0_max_delta_descriptive_only\":"<<wideC0Difference<<",\"fixture_qualified\":"<<(caseQualified?"true":"false")<<",\"passivity_accounting_regression_accepted\":"<<(casePass?"true":"false")<<",\"fixed_six_samples\":";samples(report,frames);report<<'}';
    }
    const auto status=!allQualified?"INCONCLUSIVE":allAccepted?"PASS":"RED";
    report<<"],\"case_count\":6,\"fixture_qualified\":"<<(allQualified?"true":"false")<<",\"accepted\":"<<(allQualified&&allAccepted?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"actual_observed_zero_nodes\":"<<observedZeroNodes<<",\"zero_branch_observed\":"<<(observedZeroNodes>0?"true":"false")<<",\"physics_accepted\":false,\"continuum_zero_proven\":false,\"pixel_AA_accepted\":false,\"Iris_accepted\":false,\"visual_accepted\":false,\"FPS_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Actual four-stage support-policy main/passivity/count-ledger export. Reject source and zero restoration are pinned; inherited full/base and unknown fallback remain intact. Zero branch evidence is reported from actual countword, never invented fixture inputs. Calls48 classifies only discrete quadrature targets, not continuum support or physical integral correctness. Four central fixed5025 cases preserve empirical regression gates. Wide60/90 cover every eligible raster fragment descriptively with no cross-policy C0 equality or appearance oracle. Input C12 is first failed target/index/reason, not TES. Slots5..7 are cleared inactive storage, not shader outputs.\"}\n";
    old::writeText(artifacts/"result.json",report.str());for(const auto& row:programs)for(const auto program:row)glDeleteProgram(program);std::cout<<status<<" actual support-policy export "<<artifacts<<'\n';return !allQualified?2:allAccepted?0:1;
}
}
int main(int argc,char** argv){try{
    if(argc==4&&std::string(argv[1])=="--cpu-contract")return supportProbe::cpuContract(std::array<std::filesystem::path,2>{std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3])});
    if(argc==6&&std::string(argv[1])=="--cpu-contract")return supportProbe::cpuContract(std::array<std::filesystem::path,4>{std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4]),std::filesystem::absolute(argv[5])});
    if(argc==5&&std::string(argv[1])=="--cpu-counts")return supportProbe::cpuCounts(argv[2],argv[3],argv[4]);
    if(argc==6&&std::string(argv[1])=="--cpu-readback")return supportProbe::cpuReadback(std::filesystem::absolute(argv[2]),std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5]));
    if(argc==6)return supportProbe::run({std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4])},std::filesystem::absolute(argv[5]));
    std::cerr<<"usage: water_sun_support_probe --cpu-contract REJECT_REASON ZERO_REASON REJECT_INPUT ZERO_INPUT\n       --cpu-counts COUNTWORD APPLIED REJECTED\n       --cpu-readback SYNTHETIC24.f32 GUARD POSITIVE_CACHE ZERO_MODE\n       REJECT_REASON ZERO_REASON REJECT_INPUT ZERO_INPUT NEW_OUTPUT\n";return 2;
}catch(const std::exception& failure){std::cerr<<failure.what()<<'\n';if(supportProbe::ownedArtifacts&&argc==6)try{supportProbe::old::writeText(std::filesystem::absolute(argv[5])/"failure.txt",std::string(failure.what())+'\n');}catch(...){}return 2;}}
