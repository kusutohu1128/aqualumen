// TEST ONLY. CPU compilation is allowed; root alone executes GL/game work.
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
namespace frozenResidualNative {
#include "water_residual_interface_probe.cpp"
}

namespace waterResidualBoundary {
namespace tracer=frozenResidualNative::waterResidualProbe;
namespace setup=frozenResidualNative::frozenResolvedNative::resolvedNormalProbe;
namespace fs=std::filesystem;
constexpr int size=tracer::size,outputs=tracer::outputs;
// Fixed BEFORE root execution. Local fixture arithmetic limits, not universal
// transcendental, physical-energy, reciprocity or old-result acceptance.
constexpr double arithmetic=8*std::numeric_limits<float>::epsilon();
constexpr double radianceScale=.25,coefficientTolerance=2e-5,scatterVectorTolerance=2e-5;
const std::string covarianceAssignment="WR_covariance=waveResidualCovariance(effectiveFootprint,columnDepth);";
const std::string invalidAssignment="WR_covariance=vec3(1e-8,2e-8,1e-8);";
bool ownedArtifacts=false;
void require(bool okay,const std::string& text){if(!okay)throw std::runtime_error("INCONCLUSIVE residual-boundary: "+text);}
std::string waveHeight(std::string source,const std::string& value,bool unusedTcs=false){
    const std::regex option("#define WAVE_HEIGHT ([^ \\n]+)");std::sregex_iterator at(source.begin(),source.end(),option),end;
    if(at==end){require(unusedTcs&&source.find("layout(vertices=3) out;")!=std::string::npos&&source.find("WAVE_HEIGHT")==std::string::npos&&source.find("waveState")==std::string::npos&&source.find("localWaveState")==std::string::npos&&source.find("waveSurface")==std::string::npos,"public WAVE_HEIGHT option missing in an applicable stage");return source;}
    const auto found=*at;require(++at==end,"public WAVE_HEIGHT option ambiguous");
    source.replace(std::size_t(found.position(1)),std::size_t(found.length(1)),value);return source;
}
std::string invalidCovariance(std::string source){
    const auto at=source.find(covarianceAssignment);require(at!=std::string::npos&&source.find(covarianceAssignment,at+covarianceAssignment.size())==std::string::npos,"actual helper covariance assignment missing/ambiguous");source.replace(at,covarianceAssignment.size(),invalidAssignment);
    auto recovered=source;recovered.replace(at,invalidAssignment.size(),covarianceAssignment);return source;
}
tracer::Sources variant(const tracer::Sources& original,int kind){
    auto source=original;
    if(kind<3){for(int i=0;i<3;++i)source.geometry[i]=waveHeight(source.geometry[i],"0.0",i==1);source.parent=waveHeight(source.parent,"0.0");source.active=waveHeight(source.active,"0.0");}
    if(kind==3){for(int i=0;i<3;++i)source.geometry[i]=waveHeight(source.geometry[i],"0.06",i==1);source.parent=waveHeight(source.parent,"0.06");source.active=waveHeight(source.active,"0.06");}
    require(source.geometry[1]==original.geometry[1],"inapplicable passthrough TCS must remain byte-identical");
    if(kind==4){const auto before=source.active;source.active=invalidCovariance(source.active);auto recovered=source.active;const auto at=recovered.find(invalidAssignment);recovered.replace(at,invalidAssignment.size(),covarianceAssignment);require(recovered==before,"invalid matrix fixture changes more than one literal assignment");}
    source.inactive=tracer::disabled(source.active);require(source.inactive==source.parent,"option/fixture disabled hook does not recover matching parent source");source.activeObserver=tracer::observed(source.active,true);source.inactiveObserver=tracer::observed(source.inactive,false);return source;
}
struct Fixture:tracer::Fixture {
    void prepare(int kind,const fs::path& directory){
        openScenario(kind==1,kind==2,false,directory);
        const double halfAngle=(kind==3?70.0:30.0)*3.14159265358979323846/180.0;const float focal=float(1/std::tan(halfAngle)),near=.01f,far=128,a=-(far+near)/(far-near),b=-2*far*near/(far-near);
        projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,0,1/b,0,0,-1,a/b};glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());
        if(kind==3){const float span=12,y=surface;auto a=setup::vertex(-span,y,-span),b=setup::vertex(-span,y,span),c=setup::vertex(span,y,span),d=setup::vertex(span,y,-span);std::vector<setup::Vertex> vertices={a,b,c,a,c,d};for(auto& v:vertices){v.lightmap[0]=0;v.lightmap[1]=1;}upload(vertices,directory/"uploaded-wide-water-vertices.f32");}
        setup::writeRaw(directory/"actual-projection.f32",std::vector<float>(projection.begin(),projection.end()));setup::glOkay("boundary option/view/source fixture");
    }
};
bool compare(std::ostringstream& report,bool& first,const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double abs,double rel=0){return tracer::compare(report,first,label,a,b,abs,rel);}
void jsonFour(std::ostringstream& report,const float* values){report<<'[';for(int c=0;c<4;++c){if(c)report<<',';report<<values[c];}report<<']';}
int run(const fs::path& parent,const fs::path& test,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required");const auto original=tracer::load(parent,test);require(fs::create_directories(artifacts),"cannot create new artifact directory");ownedArtifacts=true;
    setup::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");Fixture fixture;
    std::ostringstream report;report<<std::setprecision(12)<<"{\"schema\":\"aqualumen-native-residual-boundary-v1\",\"renderer\":"<<setup::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<setup::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"quadrature_order\":3,\"culling_enabled\":false,\"policy\":{\"arithmetic_absolute\":"<<arithmetic<<",\"arithmetic_relative\":"<<arithmetic<<",\"C0_reference_scale\":"<<radianceScale<<",\"coefficient_absolute\":"<<coefficientTolerance<<",\"scatter_C0_vector_absolute\":"<<scatterVectorTolerance<<",\"passive_C0_absolute\":"<<tracer::passiveAbsolute<<",\"passive_C0_relative\":"<<tracer::passiveRelative<<",\"passive_depth_absolute\":"<<tracer::depthTolerance<<"},\"cases\":[";
    bool accepted=true,allQualified=true;
    for(int kind=0;kind<5;++kind){const char* names[]={"zero-residual-same-mean","zero-wave-air-negative","zero-wave-unknown-negative","nonzero-all-TIR","invalid-covariance-input-contract"};const auto directory=artifacts/names[kind];fs::create_directory(directory);const auto sources=variant(original,kind);fixture.prepare(kind,directory);
        setup::writeText(directory/"active-expanded.fsh",sources.active);setup::writeText(directory/"inactive-expanded.fsh",sources.inactive);setup::writeText(directory/"active-observed.fsh",sources.activeObserver);setup::writeText(directory/"inactive-observed.fsh",sources.inactiveObserver);for(int i=0;i<3;++i)setup::writeText(directory/("geometry-stage"+std::to_string(i)+".glsl"),sources.geometry[i]);
        if(kind){report<<',';}
        report<<"{\"name\":"<<setup::quote(names[kind])<<",\"wave_height_option\":"<<(kind<3?"0":kind==3?"0.06":"0.12")<<",\"FOV_degrees\":"<<(kind==3?140:60)<<",\"source_override\":"<<setup::quote(kind==4?invalidAssignment:"public WAVE_HEIGHT in applicable VS/TES/FS; TCS unchanged")<<",\"setting_applicability\":{\"VS\":true,\"TCS\":false,\"TES\":true,\"FS\":true},\"TCS_source_unchanged\":true,\"disabled_source_recovers_matching_parent\":true,\"programs\":[";
        std::array<GLuint,4> programs={};const std::array<std::string,4> fragments={sources.inactive,sources.inactiveObserver,sources.active,sources.activeObserver};for(int i=0;i<4;++i){if(i)report<<',';programs[i]=setup::makeProgram({{GL_VERTEX_SHADER,sources.geometry[0]},{GL_TESS_CONTROL_SHADER,sources.geometry[1]},{GL_TESS_EVALUATION_SHADER,sources.geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},"boundary-"+std::to_string(kind)+"-"+std::to_string(i),report);}
        report<<"],\"comparisons\":[";bool first=true;std::array<setup::Capture,2> frames={};
        for(int active=0;active<2;++active){const auto label=std::string(active?"active":"inactive");const auto pure=fixture.draw(programs[active*2],false,directory,label+"-pure"),pureRepeat=fixture.draw(programs[active*2],false,directory,label+"-pure-repeat");frames[active]=fixture.draw(programs[active*2+1],true,directory,label+"-observer");const auto repeat=fixture.draw(programs[active*2+1],true,directory,label+"-observer-repeat");
            accepted=compare(report,first,label+"-pure-C0-repeat",pure.images[0],pureRepeat.images[0],0)&&accepted;accepted=compare(report,first,label+"-pure-depth-repeat",pure.depth,pureRepeat.depth,0)&&accepted;accepted=compare(report,first,label+"-passive-C0",pure.images[0],frames[active].images[0],tracer::passiveAbsolute,tracer::passiveRelative)&&accepted;accepted=compare(report,first,label+"-passive-depth",pure.depth,frames[active].depth,tracer::depthTolerance)&&accepted;
            for(int slot=0;slot<outputs;++slot){accepted=compare(report,first,label+"-observer-slot"+std::to_string(slot)+"-repeat",frames[active].images[slot],repeat.images[slot],0)&&accepted;}accepted=compare(report,first,label+"-observer-depth-repeat",frames[active].depth,repeat.depth,0)&&accepted;
        }
        accepted=compare(report,first,"cross-depth-exact",frames[0].depth,frames[1].depth,0)&&accepted;accepted=compare(report,first,"cross-flags-exact",frames[0].images[6],frames[1].images[6],0)&&accepted;
        if(kind!=3){accepted=compare(report,first,"matching-parent-C0-local-arithmetic",frames[0].images[0],frames[1].images[0],arithmetic*radianceScale,arithmetic)&&accepted;accepted=compare(report,first,"matching-parent-normal-local-arithmetic",frames[0].images[1],frames[1].images[1],arithmetic,arithmetic)&&accepted;}
        report<<"],\"samples\":[";std::vector<std::pair<int,int>> selected(tracer::pixels.begin(),tracer::pixels.end());if(kind==3)selected={{237,128},{235,128},{239,128},{237,126},{237,130}};bool caseQualified=true;
        for(std::size_t s=0;s<selected.size();++s){const auto pixel=selected[s];const int p=(pixel.second*size+pixel.first)*4;const auto& active=frames[1];const float* cov=&active.images[2][p];const float* coeff=&active.images[3][p];const float* status=&active.images[4][p];const float* sourcesOut=&active.images[5][p];
            bool qualified=true;for(const auto& frame:frames){qualified=qualified&&frame.images[6][p+3]==1&&frame.images[6][p+1]==1&&frame.images[6][p+2]==float(kind!=1)&&frame.images[6][p]==float(kind!=2)&&frame.images[1][p+3]==1&&frame.images[2][p+3]>=.035f;}
            bool sampleAccepted=true;double scatterError=0;const double trace=double(cov[0])+cov[2],determinant=double(cov[0])*cov[2]-double(cov[1])*cov[1];
            if(kind==0){qualified=qualified&&active.images[7][p+3]==1;sampleAccepted=cov[0]==0&&cov[1]==0&&cov[2]==0&&status[0]==1&&status[1]==1&&status[2]>0&&status[3]==0&&std::abs(coeff[0]-1)<=coefficientTolerance&&std::abs(double(coeff[1])+coeff[2]-coeff[0])<=coefficientTolerance&&coeff[1]>=0&&coeff[2]>=0&&coeff[3]==0&&std::abs(sourcesOut[0]-coeff[2])<=coefficientTolerance&&std::abs(sourcesOut[1]-coeff[1])<=coefficientTolerance&&sourcesOut[2]==0&&sourcesOut[3]==0;}
            if(kind==1||kind==2)sampleAccepted=status[1]==0;
            if(kind==3){qualified=qualified&&active.images[7][p+3]==1&&trace>0&&cov[0]>=0&&cov[2]>=0&&determinant>=-tracer::psdTolerance&&status[0]==1&&status[1]==1&&status[2]>0&&status[3]==0&&std::abs(coeff[3]-1)<=coefficientTolerance&&coeff[2]==0;
                double errorSquared=0;for(int c=0;c<3;++c){const double delta=double(active.images[0][p+c])-active.images[7][p+c];errorSquared+=delta*delta;}scatterError=std::sqrt(errorSquared);sampleAccepted=std::abs(coeff[0]-1)<=coefficientTolerance&&std::abs(coeff[1]-1)<=coefficientTolerance&&coeff[2]==0&&sourcesOut[0]==0&&std::abs(sourcesOut[1]-1)<=coefficientTolerance&&sourcesOut[2]==0&&sourcesOut[3]==0&&scatterError<=scatterVectorTolerance;}
            if(kind==4){qualified=qualified&&active.images[7][p+3]==1&&cov[0]==1e-8f&&cov[1]==2e-8f&&cov[2]==1e-8f&&determinant<0;sampleAccepted=status[0]==0&&status[1]==0;}
            caseQualified=caseQualified&&qualified;accepted=accepted&&sampleAccepted;if(s)report<<',';report<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"fixture_qualified\":"<<(qualified?"true":"false")<<",\"covariance\":["<<cov[0]<<','<<cov[1]<<','<<cov[2]<<"],\"covariance_trace\":"<<trace<<",\"covariance_determinant\":"<<determinant<<",\"coefficients\":";jsonFour(report,coeff);report<<",\"status\":";jsonFour(report,status);report<<",\"source_masses\":";jsonFour(report,sourcesOut);report<<",\"scatter_C0_error_vector\":"<<scatterError<<",\"accepted\":"<<(sampleAccepted?"true":"false")<<'}';
        }
        allQualified=allQualified&&caseQualified;report<<"],\"fixture_qualified\":"<<(caseQualified?"true":"false")<<'}';for(auto id:programs)glDeleteProgram(id);
    }
    report<<"],\"all_fixtures_qualified\":"<<(allQualified?"true":"false")<<",\"accepted\":"<<(accepted&&allQualified?"true":"false")<<",\"scope\":\"Actual-main finite GH3 boundary checks. Zero residual changes public WAVE_HEIGHT in applicable VS/TES/FS and keeps matching mean; passthrough TCS remains byte-identical. Nonzero all-TIR is qualified only at declared actual pixels/status; no forced classification, dense critical sweep, Gaussian tails, energy/reciprocity or quadrature-refinement proof. Invalid covariance literal is an explicitly overridden TEST helper-input contract, not a physical wave state. Predeclared local arithmetic does not revise prior frozen RED.\"}\n";setup::writeText(artifacts/"result.json",report.str());std::cout<<(!allQualified?"INCONCLUSIVE":accepted?"PASS":"RED")<<" actual-main residual boundaries "<<artifacts<<'\n';return !allQualified?2:accepted?0:1;
}
int cpuContract(const fs::path& parent,const fs::path& test){const auto original=tracer::load(parent,test);for(int kind=0;kind<5;++kind){const auto source=variant(original,kind);require(tracer::recoveredObserver(source.activeObserver)==source.active,"observer roundtrip");}bool rejected=false;try{invalidCovariance(original.active+covarianceAssignment);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous actual helper input assignment must fail closed");std::cout<<"PASS CPU applicable-stage option, unchanged TCS, literal-input-only and observer recovery contracts; no GL execution\n";return 0;}
}
int main(int argc,char** argv){try{if(argc==4&&std::string(argv[1])=="--cpu-contract")return waterResidualBoundary::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));if(argc!=4){std::cerr<<"usage: water_residual_boundary_probe <resolved-parent-shaders> <residual-TEST-shaders> <NEW-artifacts>\n       water_residual_boundary_probe --cpu-contract <resolved-parent-shaders> <residual-TEST-shaders>\n";return 2;}return waterResidualBoundary::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));}catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(waterResidualBoundary::ownedArtifacts)try{frozenResidualNative::frozenResolvedNative::resolvedNormalProbe::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}}
