// TEST ONLY: CPU compilation/contracts here; root exclusively runs GL/game.
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
namespace frozenResidualObserve {
#include "water_residual_interface_probe.cpp"
}

namespace waterResidualObserve {
namespace tracer=frozenResidualObserve::waterResidualProbe;
namespace setup=frozenResidualObserve::frozenResolvedNative::resolvedNormalProbe;
namespace fs=std::filesystem;
constexpr int size=tracer::size,outputs=tracer::outputs;
// Reuse the policies fixed before v1 execution; not universal error bounds.
constexpr double c0Absolute=tracer::passiveAbsolute,c0Relative=tracer::passiveRelative;
constexpr double depthAbsolute=tracer::depthTolerance,coefficientTolerance=tracer::coefficientTolerance;
const std::string begin="// AQUALUMEN_RESIDUAL_OBSERVE_STORE_BEGIN\n";
const std::string end="// AQUALUMEN_RESIDUAL_OBSERVE_STORE_END\n";
const std::string store=begin+
    "    gl_FragData[1]=WR_coefficients;\n"
    "    gl_FragData[2]=WR_status;\n"
    "    gl_FragData[3]=vec4(WR_covariance,float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible));\n"+end;
bool ownedArtifacts=false;
void require(bool okay,const std::string& message){if(!okay)throw std::runtime_error("INCONCLUSIVE residual-observe: "+message);}
std::string recovered(std::string source){
    const auto at=source.find(begin);
    require(at!=std::string::npos&&source.compare(at,store.size(),store)==0&&
        at+store.size()+2==source.size()&&source.substr(source.size()-2)=="}\n",
        "only the exact final coefficient/status/covariance-flags STORE is permitted");
    return tracer::eraseOne(source,begin,end);
}
struct Sources {std::array<std::string,3> geometry;std::string base,observe;};
Sources load(const fs::path& base,const fs::path& observe){
    Sources result;const char* names[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){result.geometry[i]=frozenResidualObserve::frozenResolvedNative::expand(base/names[i],base);
        require(result.geometry[i]==frozenResidualObserve::frozenResolvedNative::expand(observe/names[i],observe),"geometry stages/includes differ");}
    result.base=frozenResidualObserve::frozenResolvedNative::expand(base/"gbuffers_water.fsh",base);
    result.observe=frozenResidualObserve::frozenResolvedNative::expand(observe/"gbuffers_water.fsh",observe);
    require(recovered(result.observe)==result.base,"removing final STORE does not recover exact physical FS");
    require(result.base.find("color=waterResidualInterface(")!=std::string::npos&&
        result.base.find("gl_FragData[4]=tessStageCoord;")!=std::string::npos,"physical/TES source chain absent");
    require(result.geometry[0].find("#define frameTimeCounter 120.0\n")!=std::string::npos&&
        result.base.find("#define frameTimeCounter 120.0\n")!=std::string::npos,"fixed phase120 absent");
    return result;
}
int cpuContract(const fs::path& base,const fs::path& observe){
    load(base,observe);std::cout<<"PASS CPU exact geometry and actual final STORE recovery; no GL execution\n";return 0;
}
setup::Capture draw(tracer::Fixture& fixture,GLuint program,const fs::path& directory,const std::string& label){
    fixture.uniforms(program);glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);
    std::array<GLenum,outputs> buffers={};for(int i=0;i<outputs;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
    glDrawBuffers(outputs,buffers.data());const float zero[4]={},one=1;
    for(int i=0;i<outputs;++i)glClearBufferfv(GL_COLOR,i,zero);
    glClearBufferfv(GL_DEPTH,0,&one);
    // Both original FS programs write slots0-4 only. Do not enable undefined
    // shader outputs5-7; those readbacks are cleared inactive storage only.
    glDrawBuffers(5,buffers.data());glDrawArrays(GL_PATCHES,0,6);
    setup::Capture capture;
    for(int slot=0;slot<outputs;++slot){auto& image=capture.images[slot];image.assign(size*size*4,NAN);
        glReadBuffer(buffers[slot]);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,image.data());
        require(std::all_of(image.begin(),image.end(),[](float v){return std::isfinite(v);}),"nonfinite actual MRT readback");
        setup::writeRaw(directory/(label+"-slot"+std::to_string(slot)+".rgba32f"),image);}
    capture.depth.assign(size*size,NAN);glReadPixels(0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,capture.depth.data());
    require(std::all_of(capture.depth.begin(),capture.depth.end(),[](float v){return std::isfinite(v);}),"nonfinite actual depth");
    setup::writeRaw(directory/(label+"-depth.f32"),capture.depth);setup::glOkay("actual physical/observe main draw/readback");return capture;
}
void four(std::ostringstream& report,const float* values){report<<'[';for(int c=0;c<4;++c){if(c)report<<',';report<<values[c];}report<<']';}
int run(const fs::path& baseRoot,const fs::path& observeRoot,const fs::path& artifacts){
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifact directory required");
    const auto sources=load(baseRoot,observeRoot);require(fs::create_directories(artifacts),"cannot create artifacts");ownedArtifacts=true;
    setup::writeText(artifacts/"base-expanded.fsh",sources.base);setup::writeText(artifacts/"observe-expanded.fsh",sources.observe);
    for(int i=0;i<3;++i)setup::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),sources.geometry[i]);
    setup::Context context;const auto* renderer=glGetString(GL_RENDERER);
    require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA required");
    tracer::Fixture fixture;std::ostringstream report;report<<std::setprecision(12);
    report<<"{\"schema\":\"aqualumen-native-residual-observe-v1\",\"renderer\":"<<setup::quote(reinterpret_cast<const char*>(renderer))
        <<",\"GL\":"<<setup::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size
        <<",\"phase_seconds\":120,\"geometry_sources_identical\":true,\"STORE_removal_recovers_physical_exact\":true,\"culling_enabled\":false"
        <<",\"draw_buffer_slots\":[0,1,2,3,4],\"cleared_inactive_storage_slots\":[5,6,7]"
        <<",\"policy\":{\"C0_absolute\":"<<c0Absolute<<",\"C0_relative\":"<<c0Relative
        <<",\"depth_absolute\":"<<depthAbsolute<<",\"coefficient_absolute\":"<<coefficientTolerance
        <<",\"TES_flag_absolute\":"<<8*std::numeric_limits<float>::epsilon()<<",\"TES_simplex_absolute\":0.00002},\"programs\":[";
    std::array<GLuint,2> programs={};for(int i=0;i<2;++i){if(i)report<<',';
        programs[i]=setup::makeProgram({{GL_VERTEX_SHADER,sources.geometry[0]},{GL_TESS_CONTROL_SHADER,sources.geometry[1]},
            {GL_TESS_EVALUATION_SHADER,sources.geometry[2]},{GL_FRAGMENT_SHADER,i?sources.observe:sources.base}},i?"observe":"physical",report);}
    report<<"],\"cases\":[";bool accepted=true;int appliedPoints=0;
    const char* names[]={"directional-known-underwater","constant-known-underwater","air-negative","unknown-negative"};
    for(int kind=0;kind<4;++kind){const auto directory=artifacts/names[kind];fs::create_directory(directory);
        fixture.openScenario(kind==2,kind==3,kind!=1,directory);
        const auto base=draw(fixture,programs[0],directory,"physical"),baseRepeat=draw(fixture,programs[0],directory,"physical-repeat");
        const auto observe=draw(fixture,programs[1],directory,"observe"),observeRepeat=draw(fixture,programs[1],directory,"observe-repeat");
        if(kind)report<<',';
        report<<"{\"name\":"<<setup::quote(names[kind])<<",\"comparisons\":[";bool first=true;
        for(int slot=0;slot<outputs;++slot){accepted=tracer::compare(report,first,"physical-slot"+std::to_string(slot)+"-repeat",base.images[slot],baseRepeat.images[slot],0)&&accepted;
            accepted=tracer::compare(report,first,"observe-slot"+std::to_string(slot)+"-repeat",observe.images[slot],observeRepeat.images[slot],0)&&accepted;}
        accepted=tracer::compare(report,first,"physical-depth-repeat",base.depth,baseRepeat.depth,0)&&accepted;
        accepted=tracer::compare(report,first,"observe-depth-repeat",observe.depth,observeRepeat.depth,0)&&accepted;
        accepted=tracer::compare(report,first,"actual-observe-C0-passive",base.images[0],observe.images[0],c0Absolute,c0Relative)&&accepted;
        accepted=tracer::compare(report,first,"actual-observe-depth-passive",base.depth,observe.depth,depthAbsolute)&&accepted;
        accepted=tracer::compare(report,first,"actual-observe-C12-exact",base.images[4],observe.images[4],0)&&accepted;
        report<<"],\"samples\":[";
        for(std::size_t i=0;i<tracer::pixels.size();++i){const auto pixel=tracer::pixels[i];const int p=(pixel.second*size+pixel.first)*4;
            const float* coefficients=&observe.images[1][p],*status=&observe.images[2][p],*cov=&observe.images[3][p],*stage=&observe.images[4][p];
            require(cov[3]>=0&&cov[3]<=15&&cov[3]==std::floor(cov[3]),"invalid actual production flagword");
            const int flags=int(cov[3]);const int expected=kind<2?15:kind==2?3:6;
            require(flags==expected,"actual known/upper/underwater/eligible domain differs from fixture");
            require(base.images[1][p+3]==float(kind!=3)&&base.images[2][p+1]==float(kind!=2)&&base.images[2][p+2]==1,
                "base physical known/underwater/water fields disagree with observer domain");
            require(std::abs(stage[3]-1)<=8*std::numeric_limits<float>::epsilon()&&std::abs(stage[0]+stage[1]+stage[2]-1)<=2e-5,
                "actual original C12 TES marker/simplex missing");
            for(int c=0;c<3;++c)require(stage[c]>=-2e-5&&stage[c]<=1+2e-5,"actual C12 outside simplex");
            const double determinant=double(cov[0])*cov[2]-double(cov[1])*cov[1];bool pointAccepted=true;
            if(kind<2){pointAccepted=status[0]==1&&status[1]==1&&status[2]>0&&status[3]==0&&cov[0]>=0&&cov[2]>=0&&determinant>=0
                &&std::abs(coefficients[0]-1)<=coefficientTolerance&&coefficients[1]>=0&&coefficients[2]>=0&&coefficients[3]>=0
                &&coefficients[1]<=coefficients[0]+coefficientTolerance&&coefficients[3]<=coefficients[1]+coefficientTolerance
                &&std::abs(double(coefficients[1])+coefficients[2]-coefficients[0])<=coefficientTolerance;
                if(pointAccepted)++appliedPoints;
            }else pointAccepted=status[1]==0;
            accepted=pointAccepted&&accepted;if(i)report<<',';
            report<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"productionFlags\":"<<flags<<",\"coefficients\":";four(report,coefficients);
            report<<",\"status\":";four(report,status);report<<",\"covariance_flags\":";four(report,cov);report<<",\"C12\":";four(report,stage);
            report<<",\"covariance_determinant\":"<<determinant<<",\"physical_C0\":";four(report,&base.images[0][p]);
            report<<",\"observe_C0\":";four(report,&observe.images[0][p]);report<<",\"C0_delta_vector\":"<<setup::distance3(base.images[0],observe.images[0],p)
                <<",\"accepted\":"<<(pointAccepted?"true":"false")<<'}';}
        report<<"]}";}
    report<<"],\"known_applied_points\":"<<appliedPoints<<",\"accepted\":"<<(accepted?"true":"false")
        <<",\"operatorPhysicsAccepted\":false,\"IrisAccepted\":false,\"visualAccepted\":false,\"shippingAccepted\":false"
        <<",\"scope\":\"Actual existing four-stage physical versus final-STORE-only FS observability/passivity gate at 28 selected native texels. C9-C11 semantics are deliberately overwritten; only C0/depth/C12 passivity is compared. Slots5-7 are cleared inactive attachments, not shader-output proof. No new quadrature oracle, source-class mass, energy/reciprocity, per-node visibility, draw-count, Iris, natural image, motion or FPS acceptance.\"}\n";
    setup::writeText(artifacts/"result.json",report.str());for(auto program:programs)glDeleteProgram(program);
    std::cout<<(accepted?"PASS":"RED")<<" actual residual observe STORE passivity "<<artifacts<<'\n';return accepted?0:1;
}
}

int main(int argc,char** argv){
    try{
        if(argc==4&&std::string(argv[1])=="--cpu-contract")return waterResidualObserve::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));
        if(argc==4)return waterResidualObserve::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));
        std::cerr<<"usage: water_residual_observe_probe <base-physical-shaders> <observe-shaders> <NEW-artifacts>\n       water_residual_observe_probe --cpu-contract <base-physical-shaders> <observe-shaders>\n";return 2;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(waterResidualObserve::ownedArtifacts)try{
        frozenResidualObserve::frozenResolvedNative::resolvedNormalProbe::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(error.what())+'\n');
        }catch(...){}return 2;}
}
