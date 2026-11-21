// TEST ONLY. Root exclusively owns GL/game execution. Compile on CPU only.
// Preinclude all frozen implementation headers outside the wrapper: its own
// main-renaming macro is internally undefined, so an outer main macro alone
// cannot rename its final entry point. Namespace wrapping keeps it non-entry.
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
namespace frozenResolvedNative {
#include "water_resolved_normal_probe.cpp"
}

namespace waterResidualProbe {
namespace old=frozenResolvedNative::resolvedNormalProbe;
namespace fs=std::filesystem;
constexpr int size=old::size,outputs=old::outputs;
// Declared before any native execution. Local empirical arithmetic policies,
// not a GLSL transcendental bound, physical-energy proof or old-RED revision.
constexpr double coefficientTolerance=2e-5,psdTolerance=1e-7;
constexpr double covarianceTraceMinimum=1e-5,responseMinimum=1e-5;
constexpr double arithmeticTolerance=8*std::numeric_limits<float>::epsilon();
constexpr double airRadianceScale=.25;
constexpr double passiveAbsolute=5e-4,passiveRelative=2e-4,depthTolerance=2e-6;
constexpr std::array<float,3> constantTag={.25f,.125f,.0625f};
const std::string includeBegin="// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n",includeEnd="// AQUALUMEN_RESIDUAL_INCLUDE_END\n";
const std::string hookBegin="// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n",hookEnd="// AQUALUMEN_RESIDUAL_HOOK_END\n";
const std::string storeBegin="\n// RESIDUAL_NATIVE_STORE_BEGIN\n",storeEnd="// RESIDUAL_NATIVE_STORE_END\n";
bool ownedArtifacts=false;
void require(bool okay,const std::string& text){if(!okay)throw std::runtime_error("INCONCLUSIVE residual-interface: "+text);}
std::string eraseOne(std::string source,const std::string& begin,const std::string& end){
    auto at=source.find(begin);require(at!=std::string::npos&&source.find(begin,at+begin.size())==std::string::npos,"tag absent/ambiguous: "+begin);
    auto finish=source.find(end,at+begin.size());require(finish!=std::string::npos&&source.find(end,finish+end.size())==std::string::npos,"end tag absent/ambiguous: "+end);
    source.erase(at,finish+end.size()-at);return source;
}
std::string disabled(const std::string& source){return eraseOne(eraseOne(source,hookBegin,hookEnd),includeBegin,includeEnd);}
std::string recoveredObserver(std::string source);
std::string observed(const std::string& original,bool residual){
    auto source=original;
    const auto after=[&](const std::string& anchor,const std::string& text){auto at=source.find(anchor);require(at!=std::string::npos&&source.find(anchor,at+anchor.size())==std::string::npos,"observation anchor absent/ambiguous");source.insert(at+anchor.size(),storeBegin+text+storeEnd);};
    after("void main() {\n","    float OBS_residualGrazing=-1.0;\n");
    after("        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n","        OBS_residualGrazing=resolved;\n");
    const auto final=[&](const std::string& anchor,const std::string& terminator,const std::string& text){auto at=source.find(anchor);require(at!=std::string::npos&&source.find(anchor,at+anchor.size())==std::string::npos,"final observation seam ambiguous");at=source.find(terminator,at+anchor.size());require(at!=std::string::npos,"final terminator absent");source.insert(at,storeBegin+text+storeEnd);};
    std::string zero;for(int i=1;i<outputs;++i)zero+="    gl_FragData["+std::to_string(i)+"]=vec4(0.0);\n";
    final("        gl_FragData[0]=vec4(lit,tex.a);\n","        return;",zero);
    std::string fields="    gl_FragData[1]=vec4(n,OBS_residualGrazing);\n";
    fields+=residual?"    gl_FragData[2]=vec4(WR_covariance,max(footprint*1.25,0.035));\n    gl_FragData[3]=WR_coefficients;\n    gl_FragData[4]=WR_status;\n    gl_FragData[5]=WR_sources;\n":"    gl_FragData[2]=vec4(0.0,0.0,0.0,max(footprint*1.25,0.035));\n    gl_FragData[3]=vec4(0.0);\n    gl_FragData[4]=vec4(0.0);\n    gl_FragData[5]=vec4(0.0);\n";
    fields+="    gl_FragData[6]=vec4(float(localColumnKnown),float(upperSurface),float(underwater),1.0);\n    gl_FragData[7]=vec4(scatter,"+std::string(residual?"float(residualEligible)":"0.0")+");\n";
    final("    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n","\n}",fields);
    require(recoveredObserver(source)==original,"passive STORE removal must recover exact original bytes");
    return source;
}
std::string recoveredObserver(std::string source){
    for(auto at=source.find(storeBegin);at!=std::string::npos;at=source.find(storeBegin)){auto end=source.find(storeEnd,at);require(end!=std::string::npos,"malformed observer block");source.erase(at,end+storeEnd.size()-at);}return source;
}
struct Sources {std::array<std::string,3> geometry;std::string parent,active,inactive,activeObserver,inactiveObserver;};
Sources load(const fs::path& parentRoot,const fs::path& testRoot){
    Sources result;const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){result.geometry[i]=frozenResolvedNative::expand(parentRoot/stages[i],parentRoot);require(result.geometry[i]==frozenResolvedNative::expand(testRoot/stages[i],testRoot),"geometry stages/includes changed");}
    result.parent=frozenResolvedNative::expand(parentRoot/"gbuffers_water.fsh",parentRoot);result.active=frozenResolvedNative::expand(testRoot/"gbuffers_water.fsh",testRoot);result.inactive=disabled(result.active);
    require(result.inactive==result.parent,"disabled tagged hook/include must recover byte-identical parent expanded FS");
    require(result.active.find("waveResidualCovariance(")!=std::string::npos&&result.active.find("color=waterResidualInterface(")!=std::string::npos,"actual-main residual helper/call absent");
    require(result.geometry[0].find("#define frameTimeCounter 120.0\n")!=std::string::npos&&result.active.find("#define frameTimeCounter 120.0\n")!=std::string::npos,"shared fixed phase120 missing");
    result.activeObserver=observed(result.active,true);result.inactiveObserver=observed(result.inactive,false);
    require(recoveredObserver(result.activeObserver)==result.active&&recoveredObserver(result.inactiveObserver)==result.inactive,"passive STORE removal differs from original main");return result;
}
struct Fixture:old::Fixture {
    void openScenario(bool air,bool unknown,bool directional,const fs::path& directory){
        scenario(air,unknown,directory);
        const float y=surface;auto a=old::vertex(-.9f,y,-.9f),b=old::vertex(-.9f,y,.9f),c=old::vertex(.9f,y,.9f),d=old::vertex(.9f,y,-.9f);
        std::vector<old::Vertex> vertices={a,b,c,a,c,d};for(auto& v:vertices){v.lightmap[0]=0;v.lightmap[1]=1;}upload(vertices,directory/"uploaded-open-water-vertices.f32");
        std::vector<float> sky(64*32*4,0);for(int row=0;row<32;++row)for(int x=0;x<64;++x){const int p=(row*64+x)*4;sky[p+3]=1;for(int colour=0;colour<3;++colour)sky[p+colour]=row==31?0:(directional?(row>=29?constantTag[colour]:0):constantTag[colour]);}
        for(int unit:{2,7}){allocate(samplers[unit],GL_RGBA32F,64,32,GL_RGBA,sky.data());std::vector<float> actual(sky.size(),NAN);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());require(actual==sky,"actual directional/constant LUT readback differs");old::writeRaw(directory/(std::string(unit==2?"actual-sky":"actual-clear-sky")+".rgba32f"),actual);}old::glOkay("actual open source fixture");
    }
};
bool compare(std::ostringstream& report,bool& first,const std::string& label,const std::vector<float>& a,const std::vector<float>& b,double abs,double rel=0){return old::comparison(report,first,label,a,b,abs,rel);}
std::array<std::pair<int,int>,7> pixels={{{size/2-24,size/2+12},{size/2+24,size/2-12},{size/2-16,size/2-24},{size/2+16,size/2+24},{size/2-12,size/2+8},{size/2+8,size/2-20},{size/2+20,size/2+4}}};
int run(const fs::path& parentRoot,const fs::path& testRoot,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact path required");const auto sources=load(parentRoot,testRoot);require(fs::create_directories(artifacts),"cannot create new artifacts");ownedArtifacts=true;
    old::writeText(artifacts/"parent-expanded.fsh",sources.parent);old::writeText(artifacts/"active-expanded.fsh",sources.active);old::writeText(artifacts/"inactive-expanded.fsh",sources.inactive);old::writeText(artifacts/"active-observed.fsh",sources.activeObserver);old::writeText(artifacts/"inactive-observed.fsh",sources.inactiveObserver);
    for(int i=0;i<3;++i)old::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),sources.geometry[i]);
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"native NVIDIA renderer required");Fixture fixture;
    std::ostringstream report;report<<std::setprecision(12)<<"{\"schema\":\"aqualumen-native-residual-interface-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"geometry_sources_identical\":true,\"disabled_source_recovers_parent_exact\":true,\"observer_recovers_original_exact\":true,\"phase_seconds\":120,\"culling_enabled\":false,\"quadrature_order\":3,\"policy\":{\"coefficient_absolute\":"<<coefficientTolerance<<",\"PSD_determinant_absolute\":"<<psdTolerance<<",\"nonzero_covariance_trace_minimum\":"<<covarianceTraceMinimum<<",\"directional_response_minimum\":"<<responseMinimum<<",\"required_response_points\":3,\"air_arithmetic_absolute\":"<<arithmeticTolerance<<",\"air_arithmetic_relative\":"<<arithmeticTolerance<<",\"air_C0_reference_radiance_scale\":"<<airRadianceScale<<",\"passive_C0_absolute\":"<<passiveAbsolute<<",\"passive_C0_relative\":"<<passiveRelative<<",\"passive_depth_absolute\":"<<depthTolerance<<"},\"programs\":[";
    std::array<GLuint,4> programs={};const std::array<std::string,4> fsSources={sources.inactive,sources.inactiveObserver,sources.active,sources.activeObserver};
    for(int i=0;i<4;++i){if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,sources.geometry[0]},{GL_TESS_CONTROL_SHADER,sources.geometry[1]},{GL_TESS_EVALUATION_SHADER,sources.geometry[2]},{GL_FRAGMENT_SHADER,fsSources[i]}},"residual-"+std::to_string(i),report);}
    report<<"],\"cases\":[";bool accepted=true;std::size_t responsePoints=0;
    for(int kind=0;kind<4;++kind){const char* names[]={"directional-known-underwater","constant-known-underwater","air-negative","unknown-negative"};const auto dir=artifacts/names[kind];fs::create_directory(dir);fixture.openScenario(kind==2,kind==3,kind!=1,dir);if(kind)report<<',';report<<"{\"name\":"<<old::quote(names[kind])<<",\"comparisons\":[";bool first=true;std::array<old::Capture,2> observedFrames={};
        for(int active=0;active<2;++active){const auto label=std::string(active?"active":"inactive");const auto pure=fixture.draw(programs[active*2],false,dir,label+"-pure"),pureRepeat=fixture.draw(programs[active*2],false,dir,label+"-pure-repeat");observedFrames[active]=fixture.draw(programs[active*2+1],true,dir,label+"-observer");const auto repeat=fixture.draw(programs[active*2+1],true,dir,label+"-observer-repeat");
            accepted=compare(report,first,label+"-C0-repeat",pure.images[0],pureRepeat.images[0],0)&&accepted;accepted=compare(report,first,label+"-depth-repeat",pure.depth,pureRepeat.depth,0)&&accepted;accepted=compare(report,first,label+"-observer-C0-neutral",pure.images[0],observedFrames[active].images[0],passiveAbsolute,passiveRelative)&&accepted;accepted=compare(report,first,label+"-observer-depth-neutral",pure.depth,observedFrames[active].depth,depthTolerance)&&accepted;
            for(int slot=0;slot<outputs;++slot){accepted=compare(report,first,label+"-observer-slot"+std::to_string(slot)+"-repeat",observedFrames[active].images[slot],repeat.images[slot],0)&&accepted;}accepted=compare(report,first,label+"-observer-depth-repeat",observedFrames[active].depth,repeat.depth,0)&&accepted;
        }
        accepted=compare(report,first,"active-inactive-depth-exact",observedFrames[0].depth,observedFrames[1].depth,0)&&accepted;accepted=compare(report,first,"active-inactive-flags-exact",observedFrames[0].images[6],observedFrames[1].images[6],0)&&accepted;
        if(kind>=2){accepted=compare(report,first,"inactive-path-C0-local-arithmetic",observedFrames[0].images[0],observedFrames[1].images[0],arithmeticTolerance*airRadianceScale,arithmeticTolerance)&&accepted;accepted=compare(report,first,"inactive-path-normal-local-arithmetic",observedFrames[0].images[1],observedFrames[1].images[1],arithmeticTolerance,arithmeticTolerance)&&accepted;}
        report<<"],\"samples\":[";
        for(std::size_t s=0;s<pixels.size();++s){const auto pixel=pixels[s];const int p=(pixel.second*size+pixel.first)*4;const auto& baseline=observedFrames[0];const auto& active=observedFrames[1];
            for(const auto& frame:observedFrames){require(frame.images[6][p+3]==1&&frame.images[6][p+1]==1&&frame.images[6][p+2]==float(kind!=2)&&frame.images[6][p]==float(kind!=3),"selected pixel lacks actual water/upper/eye/known qualification");require(frame.images[1][p+3]==1,"selected pixel grazing correction is active");require(frame.images[2][p+3]==.035f,"selected pixel misses fixed .035 footprint floor");}
            const float* cov=&active.images[2][p];const float* coeff=&active.images[3][p];const float* status=&active.images[4][p];const float* source=&active.images[5][p];const double trace=double(cov[0])+cov[2],det=double(cov[0])*cov[2]-double(cov[1])*cov[1];
            const double response=old::distance3(active.images[0],baseline.images[0],p);bool sampleAccepted=true;double constantError=0;
            if(kind<2){require(active.images[7][p+3]==1,"actual production residualEligible is false");require(cov[0]>=0&&cov[2]>=0&&det>=-psdTolerance&&trace>covarianceTraceMinimum,"nonzero PSD residual covariance not qualified");
                sampleAccepted=status[0]==1&&status[1]==1&&status[2]>0&&status[3]==0&&coeff[0]>0&&std::abs(coeff[0]-1)<=coefficientTolerance&&coeff[1]>=0&&coeff[2]>=0&&coeff[3]>=0&&coeff[3]<=coeff[1]+coefficientTolerance&&coeff[1]<=coeff[0]+coefficientTolerance&&std::abs(double(coeff[1])+coeff[2]-coeff[0])<=coefficientTolerance&&std::abs(source[0]-coeff[2])<=coefficientTolerance&&std::abs(source[1]-coeff[1])<=coefficientTolerance&&source[2]==0&&source[3]==0;
                if(kind==0&&response>=responseMinimum)++responsePoints;
                if(kind==1){double squared=0;for(int c=0;c<3;++c){const double expected=double(active.images[7][p+c])*coeff[1]+double(constantTag[c])*coeff[2];const double delta=double(active.images[0][p+c])-expected;squared+=delta*delta;}constantError=std::sqrt(squared);sampleAccepted=sampleAccepted&&constantError<=coefficientTolerance;}
            }else{sampleAccepted=status[1]==0;}
            accepted=sampleAccepted&&accepted;if(s)report<<',';report<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"covariance\":["<<cov[0]<<','<<cov[1]<<','<<cov[2]<<"],\"covariance_trace\":"<<trace<<",\"covariance_determinant\":"<<det<<",\"coefficients\":["<<coeff[0]<<','<<coeff[1]<<','<<coeff[2]<<','<<coeff[3]<<"],\"status\":["<<status[0]<<','<<status[1]<<','<<status[2]<<','<<status[3]<<"],\"source_masses\":["<<source[0]<<','<<source[1]<<','<<source[2]<<','<<source[3]<<"],\"actual_C0_response_vector\":"<<response<<",\"constant_source_C0_error_vector\":"<<constantError<<",\"accepted\":"<<(sampleAccepted?"true":"false")<<'}';
        }report<<"]}";
    }
    accepted=accepted&&responsePoints>=3;report<<"],\"directional_response_points\":"<<responsePoints<<",\"accepted\":"<<(accepted?"true":"false")<<",\"scope\":\"Actual original-main four-stage near-central known uniform-column zero-gradient/ripple tracer. Constant-source coefficient conservation is not physical radiance/flux conservation or reciprocity. No critical-angle sweep, tail/visibility proof, offscreen geometry reconstruction, Iris or visual/FPS acceptance. Local air arithmetic policy declared before this experiment; prior frozen RED unchanged.\"}\n";old::writeText(artifacts/"result.json",report.str());for(auto id:programs)glDeleteProgram(id);std::cout<<(accepted?"PASS":"RED")<<" actual-main residual-interface tracer "<<artifacts<<'\n';return accepted?0:1;
}
int cpuContract(const fs::path& parent,const fs::path& test){const auto source=load(parent,test);require(source.inactive==source.parent,"disabled recovery");bool rejected=false;try{disabled(source.active+hookBegin);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous actual hook tag must fail closed");std::cout<<"PASS CPU actual-pack hook/observer recovery and ambiguous-tag rejection; no GL execution\n";return 0;}
}
int main(int argc,char** argv){
    try{if(argc==4&&std::string(argv[1])=="--cpu-contract")return waterResidualProbe::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));if(argc!=4){std::cerr<<"usage: water_residual_interface_probe <resolved-parent-shaders> <residual-TEST-shaders> <NEW-artifacts>\n       water_residual_interface_probe --cpu-contract <resolved-parent-shaders> <residual-TEST-shaders>\n";return 2;}return waterResidualProbe::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));}
    catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(waterResidualProbe::ownedArtifacts)try{frozenResolvedNative::resolvedNormalProbe::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}
}
