// Same-session fast64 / probability8 ABBA, not a neutrality or FPS test.
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
namespace probabilityTimingRetained {
#include "water_fast_inverse_timing.cpp"
}
namespace gh=probabilityTimingRetained::gh;
namespace old=probabilityTimingRetained::old;
namespace sun=probabilityTimingRetained::sun;
namespace fastTimingRetained=probabilityTimingRetained::fastTimingRetained;
namespace fs=std::filesystem;

int main(int argc,char** argv){try {
    gh::require(argc==4,"usage: water_probability_timing BASELINE CANDIDATE NEWOUTPUT");
    fs::path baseline=argv[1],candidate=argv[2],out=argv[3];
    gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;
    std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"RTX3080Ti required");
    std::array<std::string,3> geometry;
    for(int i=0;i<3;++i){
        geometry[i]=old::readText(baseline/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(geometry[i]==old::readText(candidate/("geometry-stage"+std::to_string(i)+".glsl")),"Geometry changed");
        gh::require(gh::light::digest(geometry[i])==fastTimingRetained::prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);
    }
    const std::array<std::string,2> roles={"baseline","candidate"};
    std::array<GLuint,2> programs;std::array<std::string,2> fragments;
    std::ostringstream report;report<<std::setprecision(17)
        <<"{\"schema\":\"aqualumen-probability-timing-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"programs\":[";
    for(int i=0;i<2;++i){
        fragments[i]=old::readText((i?candidate:baseline)/"enabled.fsh");
        old::writeText(out/(roles[i]+".fsh"),fragments[i]);if(i)report<<',';
        programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},roles[i],report);
    }
    gh::tracer::Sources query;query.geometry=geometry;report<<"],\"sourceQueries\":[";
    sun::queriedSources(report,{programs[0],programs[1]},query,{fragments[0],fragments[1]});
    fastTimingRetained::Fixture fixture;fixture.configure(8,out);
    for(int i=0;i<2;++i){
        fixture.snapshot(programs[i],out/(roles[i]+"-actual-inputs"));
        auto capture=fixture.capture(programs[i],out,roles[i]+"-witness");
        gh::require(capture.images[5][4*(128*257+128)+1]==1.f,"Measured operator inactive");
    }
    GLuint queryId=0;glGenQueries(1,&queryId);GLint bits=0;
    glGetQueryiv(GL_TIME_ELAPSED,GL_QUERY_COUNTER_BITS,&bits);gh::require(bits>=32,"Counter unavailable");
    auto draw=[&](int role){
        fixture.uniforms(programs[role]);glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);
        std::array<GLenum,8> buffers;for(int i=0;i<8;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(8,buffers.data());const float zero[4]={},one=1;
        for(int i=0;i<8;++i)glClearBufferfv(GL_COLOR,i,zero);glClearBufferfv(GL_DEPTH,0,&one);
        glBeginQuery(GL_TIME_ELAPSED,queryId);glDrawArrays(GL_PATCHES,0,6);glEndQuery(GL_TIME_ELAPSED);
        GLuint64 ns=0;glGetQueryObjectui64v(queryId,GL_QUERY_RESULT,&ns);gh::require(ns>0,"Nonpositive interval");return ns;
    };
    for(int i=0;i<3;++i){draw(0);draw(1);}
    report<<"],\"queryCounterBits\":"<<bits<<",\"samples\":[";bool first=true;
    for(int round=0;round<12;++round)for(int role:{0,1,1,0}){
        auto ns=draw(role);if(!first)report<<',';first=false;
        report<<"{\"round\":"<<round<<",\"role\":"<<old::quote(roles[role])<<",\"ns\":"<<ns<<'}';
    }
    report<<"],\"MinecraftFPSMeasured\":false,\"fullFrameWaterCostMeasured\":false,"
        "\"scope\":\"Same-session fast64 versus per-panel probability8 original MAIN, one TEST pixel in257x257. Six warmups and12 ABBA rounds. Distinct quadratures, NOT neutrality/FPS/pixel-cost acceptance.\"}\n";
    old::writeText(out/"result.json",report.str());
    old::writeText(out/"timing-source.cpp",old::readText("tools/water_probability_timing.cpp"));
    glDeleteQueries(1,&queryId);for(auto program:programs)glDeleteProgram(program);
    old::glOkay("probability ABBA");std::cout<<"EXPORTED fast64/probability8 ABBA; independent audit required\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
