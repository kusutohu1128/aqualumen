// Actual same-session slow64/fast64 source MAIN ABBA; not Minecraft FPS.
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
namespace fastTimingRetained {
#include "water_supported_sources_main.cpp"
}
namespace gh=fastTimingRetained::gh;
namespace old=fastTimingRetained::old;
namespace sun=fastTimingRetained::sun;
namespace fs=std::filesystem;
int main(int argc,char** argv){try {
    gh::require(argc==4,"usage: water_fast_inverse_timing SLOW_SOURCES FAST_SOURCES NEWOUTPUT");
    fs::path slow=argv[1],fast=argv[2],out=argv[3];
    gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"RTX3080Ti required");
    std::array<std::string,3> geometry;
    for(int i=0;i<3;++i){geometry[i]=old::readText(slow/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(geometry[i]==old::readText(fast/("geometry-stage"+std::to_string(i)+".glsl")),"Geometry changed");
        gh::require(gh::light::digest(geometry[i])==fastTimingRetained::prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);}
    const std::array<std::string,2> roles={"slow","fast"};std::array<GLuint,2> programs;
    std::array<std::string,2> fragments;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-fast-inverse-timing-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"programs\":[";
    for(int i=0;i<2;++i){fragments[i]=old::readText((i?fast:slow)/"enabled.fsh");old::writeText(out/(roles[i]+".fsh"),fragments[i]);
        if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},roles[i],report);}
    gh::tracer::Sources query;query.geometry=geometry;report<<"],\"sourceQueries\":[";
    sun::queriedSources(report,{programs[0],programs[1]},query,{fragments[0],fragments[1]});
    fastTimingRetained::Fixture fixture;fixture.configure(8,out);
    for(int i=0;i<2;++i){fixture.snapshot(programs[i],out/(roles[i]+"-actual-inputs"));
        auto capture=fixture.capture(programs[i],out,roles[i]+"-witness");
        const int p=4*(128*257+128);gh::require(capture.images[5][p+1]==1.f,"Measured operator inactive");}
    GLuint queryId=0;glGenQueries(1,&queryId);GLint bits=0;glGetQueryiv(GL_TIME_ELAPSED,GL_QUERY_COUNTER_BITS,&bits);
    gh::require(bits>=32,"GPU interval counter unavailable");
    auto draw=[&](int role){fixture.uniforms(programs[role]);glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);
        std::array<GLenum,8> buffers;for(int i=0;i<8;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(8,buffers.data());const float zero[4]={},one=1;
        for(int i=0;i<8;++i)glClearBufferfv(GL_COLOR,i,zero);glClearBufferfv(GL_DEPTH,0,&one);
        glBeginQuery(GL_TIME_ELAPSED,queryId);glDrawArrays(GL_PATCHES,0,6);glEndQuery(GL_TIME_ELAPSED);
        GLuint64 elapsed=0;glGetQueryObjectui64v(queryId,GL_QUERY_RESULT,&elapsed);
        gh::require(elapsed>0,"Nonpositive GPU interval");return elapsed;};
    for(int i=0;i<3;++i){draw(0);draw(1);}report<<"],\"queryCounterBits\":"<<bits<<",\"samples\":[";
    bool first=true;
    for(int round=0;round<12;++round)for(int role:{0,1,1,0}){
        auto elapsed=draw(role);if(!first)report<<',';first=false;
        report<<"{\"round\":"<<round<<",\"role\":"<<old::quote(roles[role])<<",\"ns\":"<<elapsed<<'}';}
    report<<"],\"MinecraftFPSMeasured\":false,\"fullFrameWaterCostMeasured\":false,\"shippingAccepted\":false,"
        "\"scope\":\"Same-session64-proposal original four-stage source MAIN;257x257 draw with one TEST evaluation pixel. Six warmups,12 ABBA rounds; excludes clear/readback/setup/compile. No FPS or whole-frame extrapolation.\"}\n";
    old::writeText(out/"result.json",report.str());
    old::writeText(out/"timing-source.cpp",old::readText("tools/water_fast_inverse_timing.cpp"));
    glDeleteQueries(1,&queryId);for(auto p:programs)glDeleteProgram(p);old::glOkay("same-session ABBA");
    std::cout<<"EXPORTED slow64/fast64 actual source MAIN ABBA; independent audit required\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
