// TEST ONLY. Root exclusively owns native GL; CPU construction/compile here.
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
namespace frozenResidualLight {
#include "water_residual_angular_probe.cpp"
}
namespace lightProbe {
namespace angular=frozenResidualLight::angularProbe;
namespace tracer=angular::tracer;
namespace old=angular::old;
namespace fs=std::filesystem;
const std::string configBegin="// LIGHT_NATIVE_CONFIG_BEGIN\n",configEnd="// LIGHT_NATIVE_CONFIG_END\n";
const std::string baselinePath="reports/2026-10-03-water-residual-angular/native-angular-v1/source-original-expanded.fsh";
const std::string baselineSHA="62837f5fe0cdfa21c509be48db408941164d7b5a96c853d57c5c4de0a09698b3";
void require(bool okay,const std::string& text){if(!okay)throw std::runtime_error("INCONCLUSIVE residual-light: "+text);}
std::string digest(const std::string& text){unsigned char bytes[SHA256_DIGEST_LENGTH]={};SHA256(reinterpret_cast<const unsigned char*>(text.data()),text.size(),bytes);std::ostringstream out;out<<std::hex<<std::setfill('0');for(unsigned char value:bytes)out<<std::setw(2)<<unsigned(value);return out.str();}
std::string baseline(){auto source=old::readText(baselinePath);require(source.size()<=262144&&digest(source)==baselineSHA,"frozen actual guard baseline digest differs");return source;}
std::string configured(const std::string& source,int enabled,int kind){
    require((enabled==0||enabled==1)&&kind>=1&&kind<=4,"unapproved light configuration");
    require(source.find(configBegin)==std::string::npos&&source.find(configEnd)==std::string::npos,"existing configuration marker");
    return angular::replaceOne(source,tracer::includeBegin,tracer::includeBegin+configBegin+"#define WLS_LIGHT_ENABLED "+std::to_string(enabled)+"\n#define WLS_SOURCE_KIND "+std::to_string(kind)+"\n"+configEnd);
}
std::string recoverConfig(const std::string& source){return tracer::eraseOne(source,configBegin,configEnd);}
std::string observed(const std::string& source){
    const auto result=angular::replaceOne(angular::observed(source),"    gl_FragData[7]=vec4(scatter,float(residualEligible));\n","    gl_FragData[7]=vec4(scatter,WLS_status.y);\n");
    require(tracer::recoveredObserver(result)==source,"light status STORE removal must recover actual main");return result;
}
int cpuConstruction(){
    const auto original=tracer::includeBegin+"// Synthetic construction-only marker fixture\n"+tracer::includeEnd;
    const auto candidate=configured(original,1,1);
    require(candidate.find("#define WLS_LIGHT_ENABLED 1\n")!=std::string::npos&&candidate.find("#define WLS_SOURCE_KIND 1\n")!=std::string::npos,"public candidate construction must supply actual macros before helpers");
    require(recoverConfig(candidate)==original,"configuration removal must recover original bytes");
    for(int enabled:{0,1})for(int kind:{1,2,3,4})require(recoverConfig(configured(original,enabled,kind))==original,"all configurations must recover exact source");
    bool rejected=false;try{configured(original+tracer::includeBegin,1,1);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous helper marker must reject");
    const auto source=baseline();const auto observer=observed(source);
    require(observer.find("    gl_FragData[7]=vec4(scatter,WLS_status.y);\n")!=std::string::npos,"public STORE must expose actual source-applied status, not eligibility");
    require(tracer::recoveredObserver(observer)==source,"observer must recover exact source");
    std::cout<<"PASS CPU light configuration construction; no GL/shader execution\n";return 0;
}
std::string removeInner(std::string source){
    for(const auto& tag:{"INCLUDE","RESTORE_ENV","CALL_BEGIN_ALIAS","CALL_END_ALIAS"}){
        source=tracer::eraseOne(source,"// AQUALUMEN_LIGHT_"+std::string(tag)+"_BEGIN\n","// AQUALUMEN_LIGHT_"+std::string(tag)+"_END\n");
    }
    return source;
}
int cpuContract(const fs::path& parent,const fs::path& test){
    cpuConstruction();const auto loaded=tracer::load(parent,test);const auto physical=removeInner(loaded.active);
    require(digest(physical)==baselineSHA&&physical==baseline(),"LIGHT-only erasure must recover pinned actual guard baseline");
    require(loaded.active.find("#define waterResidualInterface waterResidualLightInterface\n")!=std::string::npos&&loaded.active.find("vec4 WLS_status")!=std::string::npos,"light alias/actual status missing");
    require(angular::ruleVariant(physical,3)==physical,"GH3 must remain untouched");
    for(int kind:{1,2,3,4})for(int enabled:{0,1}){const char* names[]={"narrow","broad","constant","dark"};const auto light=angular::sourceVariant(loaded.active,names[kind-1],kind==1?.00465:kind==2?.08:0);const auto source=configured(light,enabled,kind);
        require(angular::recoverSource(recoverConfig(tracer::recoveredObserver(observed(source))))==loaded.active,"all source/configuration/STORE removal must recover actual pack");}
    std::cout<<"PASS CPU pinned physical/resolved recovery, unchanged GH3, all4source/control-candidate/STORE configuration contracts; no GL execution\n";return 0;
}
constexpr int size=tracer::size,outputs=tracer::outputs;
constexpr double numericAbsolute=2e-6,numericRelative=2e-4;
const std::string oraclePath="reports/2026-10-03-water-residual-angular/CPU-reference/actual-supplemental-oracle.json";
const std::string oracleSHA="f8ec3ab6a5e330abdad8e493d913e54f2481a308dc1612fdf1c5106987d9d2c5";
struct Target {int x,y;std::array<float,3> n,v;std::array<double,3> expected;};
const std::array<Target,6> targets={{{128,128,{-.06522385776042938f,-.9967667460441589f,-.046924784779548645f},{-2.0954757928848267e-9f,-1.f,2.786691766232252e-9f},{.008620047860082714,.004310023930041357,.0021550119650206785}},
    {132,131,{-.07786130160093307f,-.9956422448158264f,-.05132262781262398f},{-.01796698570251465f,-.9997477531433105f,-.013475103303790092f},{.013054451421566662,.006527225710783331,.0032636128553916654}},
    {123,127,{-.048757828772068024f,-.9978235960006714f,-.04439356550574303f},{.02245987579226494f,-.9997376799583435f,.004493821412324905f},{.0032931954429157133,.0016465977214578566,.0008232988607289283}},
    {132,135,{-.0782957375049591f,-.9953653216362f,-.05583534017205238f},{-.017959587275981903f,-.9993446469306946f,-.031428832560777664f},{.003249341819018176,.001624670909509088,.000812335454754544}},
    {132,127,{-.0771719440817833f,-.995934247970581f,-.04646927863359451f},{-.017967700958251953f,-.9998283982276917f,.004493507090955973f},{.004662952074109474,.002331476037054737,.0011657380185273686}},
    {142,134,{-.10337456315755844f,-.9931023716926575f,-.05532897636294365f},{-.06275273114442825f,-.9976667761802673f,-.026892496272921562f},{.0027144296933907888,.0013572148466953944,.0006786074233476972}}}};
const std::array<float,3> pinnedCov={.006807451602071524f,.0027949956711381674f,.002802651608362794f};
bool ownedArtifacts=false;
bool arithmetic(double a,double b){return std::abs(a-b)<=angular::crossArithmetic*(1+std::abs(b));}
bool legacyDomain(const old::Capture& frame,int p){const auto& flags=frame.images[6];const auto& status=frame.images[4];return flags[p]==1&&flags[p+1]==1&&flags[p+2]==1&&flags[p+3]==1&&frame.images[5][p+3]==1&&status[p]==1&&status[p+1]==1&&status[p+2]>0&&status[p+3]==0;}
bool coefficients(const old::Capture& frame,int p){const auto& a=frame.images[3];const auto& c=frame.images[2];return std::abs(double(a[p])-1)<=tracer::coefficientTolerance&&a[p+1]>=0&&a[p+2]>=0&&a[p+3]>=0&&a[p+3]<=a[p+1]+tracer::coefficientTolerance&&std::abs(double(a[p+1])+a[p+2]-a[p])<=tracer::coefficientTolerance&&c[p]>=0&&c[p+2]>=0&&double(c[p])*c[p+2]-double(c[p+1])*c[p+1]>=0&&double(c[p])+c[p+2]>tracer::covarianceTraceMinimum;}
int run(const fs::path& parent,const fs::path& test,const fs::path& artifacts){
    static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,"binary32 export");const std::uint32_t endian=1;require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little endian required");
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifacts required");cpuContract(parent,test);const auto oracle=old::readText(oraclePath);require(oracle.size()<=1048576&&digest(oracle)==oracleSHA,"frozen continuous oracle digest differs");
    const auto loaded=tracer::load(parent,test);require(fs::create_directories(artifacts),"cannot create artifacts");ownedArtifacts=true;
    old::writeText(artifacts/"source-original-expanded.fsh",loaded.active);old::writeText(artifacts/"guard-baseline-expanded.fsh",baseline());old::writeText(artifacts/"resolved-parent-expanded.fsh",loaded.parent);old::writeText(artifacts/"frozen-continuous-oracle.json",oracle);
    for(int i=0;i<3;++i){old::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),loaded.geometry[i]);}
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"NVIDIA required");tracer::Fixture fixture;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-native-residual-light-v1\",\"size\":"<<size<<",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"baselineSHA256\":"<<old::quote(baselineSHA)<<",\"oracleSHA256\":"<<old::quote(oracleSHA)<<",\"activeExpandedSHA256\":"<<old::quote(digest(loaded.active))<<",\"phase_seconds\":120,\"quadrature_order\":3,\"sourceUnits\":\"fixed-peak directional radiance; CHORD Gaussian, not calibrated solar beam\",\"pure_draw_buffer_slots\":[0,1,2,3,4],\"pure_cleared_inactive_slots\":[5,6,7],\"observer_slot5\":\"actual viewToEye xyz / residualEligible\",\"observer_slot7\":\"scatter xyz / actual WLS_status.y sourceApplied\",\"rawFormat\":\"little-endian binary32 bottom-left origin\",\"policy\":{\"numeric_absolute\":"<<numericAbsolute<<",\"numeric_relative\":"<<numericRelative<<",\"passive_C0_absolute\":"<<tracer::passiveAbsolute<<",\"passive_C0_relative\":"<<tracer::passiveRelative<<",\"passive_depth_absolute\":"<<tracer::depthTolerance<<",\"coefficient_absolute\":"<<tracer::coefficientTolerance<<",\"common_xyz_absolute_relative\":"<<angular::crossArithmetic<<",\"ROI_center\":[128,128],\"ROI_integer_radius\":40},\"geometry_sources_identical\":true,\"light_inner_erasure_recovers_pinned_baseline_exact\":true,\"outer_erasure_recovers_resolved_exact\":true,\"observer_source_config_erasure_recovers_active_exact\":true,\"cases\":[";
    std::array<std::array<old::Capture,2>,8> saved;std::array<std::vector<float>,8> referenceInputs={};old::Capture reference;bool haveReference=false,telemetry=true,domainOkay=true,featureOkay=true,otherControls=true;
    const std::array<std::string,4> names={"narrow","broad","constant","dark"};
    for(int kind=1;kind<=4;++kind)for(int enabled=0;enabled<=1;++enabled){const int index=(kind-1)*2+enabled;const auto& name=names[kind-1];const auto path=name+(enabled?"-candidate":"-control");const auto directory=artifacts/path;require(fs::create_directory(directory),"new case directory required");
        const auto source=configured(angular::sourceVariant(loaded.active,name,kind==1?.00465:kind==2?.08:0),enabled,kind),observerSource=observed(source);require(angular::recoverSource(recoverConfig(tracer::recoveredObserver(observerSource)))==loaded.active,"compiled source recovery differs");old::writeText(directory/"pure-expanded.fsh",source);old::writeText(directory/"observer-expanded.fsh",observerSource);
        if(index){report<<',';}report<<"{\"source\":"<<old::quote(name)<<",\"source_kind\":"<<kind<<",\"light_enabled\":"<<enabled<<",\"path\":"<<old::quote(path)<<",\"pureSourceSHA256\":"<<old::quote(digest(source))<<",\"observerSourceSHA256\":"<<old::quote(digest(observerSource))<<",\"programs\":[";
        std::array<GLuint,2> programs={};for(int i=0;i<2;++i){if(i){report<<',';}programs[i]=old::makeProgram({{GL_VERTEX_SHADER,loaded.geometry[0]},{GL_TESS_CONTROL_SHADER,loaded.geometry[1]},{GL_TESS_EVALUATION_SHADER,loaded.geometry[2]},{GL_FRAGMENT_SHADER,i?observerSource:source}},path+(i?"-observer":"-pure"),report);}
        report<<"],\"program_ids\":["<<programs[0]<<','<<programs[1]<<']';angular::openBlack(fixture,directory);auto pure=angular::draw(fixture,programs[0],false,directory,"pure");const auto pureRepeat=angular::draw(fixture,programs[0],false,directory,"pure-repeat");auto frame=angular::draw(fixture,programs[1],true,directory,"observer");const auto observerRepeat=angular::draw(fixture,programs[1],true,directory,"observer-repeat");const auto inputs=angular::snapshotInputs(fixture,programs[1],directory);
        report<<",\"comparisons\":[";bool first=true,caseTelemetry=true;auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double abs,double rel=0){const bool okay=tracer::compare(report,first,label,a,b,abs,rel);caseTelemetry=okay&&caseTelemetry;};
        for(int slot=0;slot<outputs;++slot){compare("pure-slot"+std::to_string(slot)+"-repeat",pure.images[slot],pureRepeat.images[slot],0);compare("observer-slot"+std::to_string(slot)+"-repeat",frame.images[slot],observerRepeat.images[slot],0);}
        compare("pure-depth-repeat",pure.depth,pureRepeat.depth,0);compare("observer-depth-repeat",frame.depth,observerRepeat.depth,0);compare("observer-C0-passive",pure.images[0],frame.images[0],tracer::passiveAbsolute,tracer::passiveRelative);compare("observer-depth-passive",pure.depth,frame.depth,tracer::depthTolerance);
        if(haveReference){require(inputs==referenceInputs,"immutable actual input textures changed");for(int slot:{1,5,7}){compare("common-slot"+std::to_string(slot)+"-xyz-EPS8",angular::channels(reference.images[slot],false),angular::channels(frame.images[slot],false),angular::crossArithmetic,angular::crossArithmetic);if(slot!=7){compare("common-slot"+std::to_string(slot)+"-alpha-exact",angular::channels(reference.images[slot],true),angular::channels(frame.images[slot],true),0);}}
            for(int slot:{2,6}){compare("common-slot"+std::to_string(slot)+"-exact",reference.images[slot],frame.images[slot],0);}compare("common-depth-exact",reference.depth,frame.depth,0);compare("common-legacy-coefficients",reference.images[3],frame.images[3],tracer::coefficientTolerance);
        }else{reference=frame;referenceInputs=inputs;haveReference=true;}
        if(kind>1&&enabled){bool controlFirst=first;otherControls=tracer::compare(report,controlFirst,"control-candidate-pure-C0-EPS8",saved[index-1][0].images[0],pure.images[0],angular::crossArithmetic,angular::crossArithmetic)&&otherControls;otherControls=tracer::compare(report,controlFirst,"control-candidate-observer-C0-EPS8",saved[index-1][1].images[0],frame.images[0],angular::crossArithmetic,angular::crossArithmetic)&&otherControls;}
        int roi=0,legacy=0,applied=0;const int expectedApplied=kind==1&&enabled?1:0;for(int y=88;y<=168;++y)for(int x=88;x<=168;++x)if((x-128)*(x-128)+(y-128)*(y-128)<=1600){++roi;const int p=(y*size+x)*4;if(legacyDomain(frame,p)&&coefficients(frame,p)){++legacy;}if(frame.images[7][p+3]==expectedApplied){++applied;}}
        bool pinOkay=true;report<<"],\"samples\":[";for(std::size_t s=0;s<targets.size();++s){const auto& target=targets[s];const int p=(target.y*size+target.x)*4;for(int c=0;c<3;++c){pinOkay=pinOkay&&arithmetic(frame.images[1][p+c],target.n[c])&&arithmetic(frame.images[5][p+c],target.v[c])&&frame.images[2][p+c]==pinnedCov[c];}pinOkay=pinOkay&&frame.images[1][p+3]==1&&frame.images[2][p+3]==.035f;
            if(s){report<<',';}report<<"{\"pixel\":["<<target.x<<','<<target.y<<"],\"normal_grazing\":";angular::four(report,&frame.images[1][p]);report<<",\"covariance_footprint\":";angular::four(report,&frame.images[2][p]);report<<",\"coefficients\":";angular::four(report,&frame.images[3][p]);report<<",\"status\":";angular::four(report,&frame.images[4][p]);report<<",\"eye_eligible\":";angular::four(report,&frame.images[5][p]);report<<",\"production_flags\":";angular::four(report,&frame.images[6][p]);report<<",\"scatter_sourceApplied\":";angular::four(report,&frame.images[7][p]);report<<",\"pureTotalC0\":";angular::four(report,&pure.images[0][p]);report<<",\"observerTotalC0\":";angular::four(report,&frame.images[0][p]);report<<'}';}
        const bool caseDomain=roi==5025&&legacy==roi&&pinOkay;domainOkay=domainOkay&&caseDomain;featureOkay=featureOkay&&(applied==roi);telemetry=telemetry&&caseTelemetry;
        report<<"],\"ROI_points\":"<<roi<<",\"ROI_legacy_domain_points\":"<<legacy<<",\"ROI_expected_source_applied\":"<<expectedApplied<<",\"ROI_source_applied_matching_points\":"<<applied<<",\"referenceVectorsQualified\":"<<(pinOkay?"true":"false")<<",\"domainQualified\":"<<(caseDomain?"true":"false")<<",\"telemetryQualified\":"<<(caseTelemetry?"true":"false")<<'}';saved[index][0]=std::move(pure);saved[index][1]=std::move(frame);for(auto program:programs){glDeleteProgram(program);}
    }
    bool numericOkay=true,controlMiss=false;report<<"],\"fixedSourceDeltaChecks\":[";for(int enabled=0;enabled<=1;++enabled)for(int observedMode=0;observedMode<=1;++observedMode)for(std::size_t s=0;s<targets.size();++s){const auto& target=targets[s];const int p=(target.y*size+target.x)*4;std::array<double,3> delta={},error={},bounds={};bool okay=true;for(int c=0;c<3;++c){delta[c]=double(saved[enabled][observedMode].images[0][p+c])-double(saved[6][observedMode].images[0][p+c]);error[c]=std::abs(delta[c]-target.expected[c]);bounds[c]=numericAbsolute+numericRelative*std::abs(target.expected[c]);okay=okay&&error[c]<=bounds[c];}
        if(enabled){numericOkay=numericOkay&&okay;}else{controlMiss=controlMiss||!okay;}if(enabled||observedMode||s){report<<',';}report<<"{\"role\":"<<old::quote(enabled?"candidate":"control")<<",\"observation\":"<<old::quote(observedMode?"observer":"pure")<<",\"pixel\":["<<target.x<<','<<target.y<<"],\"totalC0\":";angular::four(report,&saved[enabled][observedMode].images[0][p]);report<<",\"darkControlTotalC0\":";angular::four(report,&saved[6][observedMode].images[0][p]);report<<",\"sourceDelta\":";angular::numbers(report,delta);report<<",\"expectedSourceDelta\":";angular::numbers(report,target.expected);report<<",\"absoluteError\":";angular::numbers(report,error);report<<",\"bound\":";angular::numbers(report,bounds);report<<",\"matchesContinuousReference\":"<<(okay?"true":"false")<<'}';}
    const bool qualified=telemetry&&domainOkay;const bool passed=qualified&&featureOkay&&numericOkay&&controlMiss&&otherControls;const std::string status=!qualified?"INCONCLUSIVE":passed?"PASS":"RED";
    report<<"],\"telemetryAccepted\":"<<(telemetry?"true":"false")<<",\"legacyDomainQualified\":"<<(domainOkay?"true":"false")<<",\"sourceAppliedQualified\":"<<(featureOkay?"true":"false")<<",\"fixedContinuousReferenceAccepted\":"<<(numericOkay?"true":"false")<<",\"oldAliasNegativeControlObserved\":"<<(controlMiss?"true":"false")<<",\"nonNarrowControlsAccepted\":"<<(otherControls?"true":"false")<<",\"accepted\":"<<(passed?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"quality_accepted\":false,\"energy_accepted\":false,\"reciprocity_accepted\":false,\"Iris_accepted\":false,\"natural_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Fixed controlled original-main continuous narrow-source integral at six pinned qualified vectors only. Actual narrow minus actual dark CONTROL source_difference_C0, not total C0 or guessed scatter. All5025 ROI legacy domain and requested narrow feature application required. Qualified numeric/application failures are RED; malformed telemetry/domain is INCONCLUSIVE. Pure slots5-7 are inactive cleared storage only. No calibrated Sun, visibility-tail, energy, visual, motion or FPS adoption.\"}\n";old::writeText(artifacts/"result.json",report.str());std::cout<<status<<" actual-main residual-light "<<artifacts<<'\n';return !qualified?2:passed?0:1;
}
}
int main(int argc,char** argv){try{if(argc==2&&std::string(argv[1])=="--cpu-construction")return lightProbe::cpuConstruction();if(argc==4&&std::string(argv[1])=="--cpu-contract")return lightProbe::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));if(argc==4)return lightProbe::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));std::cerr<<"usage: water_residual_light_probe --cpu-construction | --cpu-contract parentShaders testShaders | parentShaders testShaders NEWartifacts\n";return 2;}catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(lightProbe::ownedArtifacts)try{lightProbe::old::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}}
