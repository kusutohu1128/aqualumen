// NEW draw-only bounded native timing, not Minecraft FPS/full-frame water cost.
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
namespace sourceTimingRetained {
#include "water_supported_sources_main.cpp"
}
namespace gh=sourceTimingRetained::gh;
namespace old=sourceTimingRetained::old;
namespace sun=sourceTimingRetained::sun;
namespace fs=std::filesystem;
int main(int argc,char** argv){try {
    gh::require(argc==3,"usage: water_supported_sources_timing SOURCES NEW_OUTPUT");
    fs::path source=argv[1],out=argv[2];gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual RTX3080Ti required");
    std::array<std::string,3> geometry;for(int i=0;i<3;++i){geometry[i]=old::readText(source/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(gh::light::digest(geometry[i])==sourceTimingRetained::prior::geometrySHA[i],"Geometry differs");}
    std::ostringstream report;report<<std::setprecision(17)<<"{\"renderer\":"<<old::quote(renderer)<<",\"programs\":[";
    const std::array<std::string,2> roles={"disabled","enabled"};std::array<GLuint,2> programs;
    for(int i=0;i<2;++i){if(i)report<<',';const auto fragment=old::readText(source/(roles[i]+".fsh"));
        old::writeText(out/(roles[i]+".fsh"),fragment);
        programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragment}},roles[i],report);}
    sourceTimingRetained::Fixture fixture;fixture.configure(8,out);
    for(int i=0;i<2;++i){fixture.snapshot(programs[i],out/(roles[i]+"-actual-inputs"));
        auto capture=fixture.capture(programs[i],out,roles[i]+"-witness");const int p=4*(128*257+128);
        gh::require(capture.images[5][p+1]==float(i),"Measured TEST application differs");}
    GLuint query=0;glGenQueries(1,&query);GLint bits=0;glGetQueryiv(GL_TIME_ELAPSED,GL_QUERY_COUNTER_BITS,&bits);
    gh::require(bits>=32,"GPU timestamp counter unavailable");
    auto draw=[&](int role){fixture.uniforms(programs[role]);glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);
        std::array<GLenum,8> buffers;for(int i=0;i<8;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(8,buffers.data());const float zero[4]={},one=1;
        for(int i=0;i<8;++i)glClearBufferfv(GL_COLOR,i,zero);glClearBufferfv(GL_DEPTH,0,&one);
        glBeginQuery(GL_TIME_ELAPSED,query);glDrawArrays(GL_PATCHES,0,6);glEndQuery(GL_TIME_ELAPSED);
        GLuint64 elapsed=0;glGetQueryObjectui64v(query,GL_QUERY_RESULT,&elapsed);
        gh::require(elapsed>0,"Nonpositive GPU interval");return elapsed;};
    for(int i=0;i<3;++i){draw(0);draw(1);}report<<"],\"queryCounterBits\":"<<bits<<",\"samples\":[";
    bool first=true;for(int round=0;round<12;++round)for(int role:{0,1,1,0}){const auto elapsed=draw(role);
        if(!first)report<<',';first=false;report<<"{\"round\":"<<round<<",\"role\":"<<old::quote(roles[role])<<",\"ns\":"<<elapsed<<'}';}
    report<<"],\"MinecraftFPSMeasured\":false,\"fullFrameWaterCostMeasured\":false,\"shippingAccepted\":false,"
        "\"scope\":\"257x257 original four-stage draw with one native TEST evaluation pixel. Six warmup draws then 12 ABBA rounds. No compile/readback/clear/CPU setup in query. Not a pixel-cost extrapolation or Minecraft timing.\"}\n";
    old::writeText(out/"result.json",report.str());old::writeText(out/"timing-source.cpp",old::readText("tools/water_supported_sources_timing.cpp"));
    glDeleteQueries(1,&query);for(auto p:programs)glDeleteProgram(p);old::glOkay("NEW draw-only timing");std::cout<<"PASS bounded draw-only ABBA timing\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
