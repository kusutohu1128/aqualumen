// Passive actual MAIN SSBO: original reflected source, same geometry/textures.
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
namespace boundaryRetained {
#include "water_supported_reflector_main.cpp"
}
namespace old=boundaryRetained::old;
namespace gh=boundaryRetained::gh;
namespace sun=boundaryRetained::sun;
namespace fs=std::filesystem;

void writeBuffer(const fs::path& path,const std::vector<std::uint32_t>& data) {
    gh::require(!fs::exists(path),"NEW node readback required");
    std::ofstream file(path,std::ios::binary);
    file.write(reinterpret_cast<const char*>(data.data()),data.size()*sizeof(std::uint32_t));
    gh::require(bool(file),"Node readback write failed");
}

int main(int argc,char** argv){try {
    gh::require(argc==3,"usage: water_source_boundary_probe SOURCES NEW_OUTPUT");
    fs::path sources=argv[1],out=argv[2];
    gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW output required");
    old::Context context;std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"RTX3080Ti required");
    std::array<std::string,3> geometry;
    for(int i=0;i<3;++i){
        geometry[i]=old::readText(sources/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(gh::light::digest(geometry[i])==boundaryRetained::frozenSourceAdapter::prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);
    }
    const std::array<std::string,2> roles={"baseline","observer"};
    std::array<GLuint,2> programs;std::array<std::string,2> fragments;
    std::ostringstream report;report<<std::setprecision(17)
        <<"{\"schema\":\"aqualumen-source-boundary-main-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"recordStrideVec4\":22,\"recordCapacity\":4096,\"programs\":[";
    for(int i=0;i<2;++i){
        fragments[i]=old::readText(sources/(roles[i]+".fsh"));
        old::writeText(out/(roles[i]+".fsh"),fragments[i]);if(i)report<<',';
        programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},roles[i],report);
    }
    auto block=glGetProgramResourceIndex(programs[1],GL_SHADER_STORAGE_BLOCK,"WSB_Observation");
    gh::require(block!=GL_INVALID_INDEX,"Actual SSBO block inactive");
    glShaderStorageBlockBinding(programs[1],block,0);
    auto variable=glGetProgramResourceIndex(programs[1],GL_BUFFER_VARIABLE,"WSB_records[0]");
    gh::require(variable!=GL_INVALID_INDEX,"Actual SSBO records inactive");
    const GLenum properties[]={GL_OFFSET,GL_ARRAY_STRIDE,GL_TYPE};GLint layout[3]={};
    glGetProgramResourceiv(programs[1],GL_BUFFER_VARIABLE,variable,3,properties,3,nullptr,layout);
    gh::require(layout[0]==16&&layout[1]==16&&layout[2]==GL_FLOAT_VEC4,"Actual SSBO layout differs");
    gh::tracer::Sources query;query.geometry=geometry;report<<"],\"sourceQueries\":[";
    sun::queriedSources(report,{programs[0],programs[1]},query,{fragments[0],fragments[1]});
    report<<"],\"SSBOOffset\":"<<layout[0]<<",\"SSBOArrayStride\":"<<layout[1]<<",\"SSBOType\":"<<layout[2]<<",\"cases\":[";
    GLuint storage=0;glGenBuffers(1,&storage);glBindBuffer(GL_SHADER_STORAGE_BUFFER,storage);
    std::vector<std::uint32_t> initial(4+4096*22*4,0x7fc00000u);
    std::fill(initial.begin(),initial.begin()+4,0u);
    glBufferData(GL_SHADER_STORAGE_BUFFER,initial.size()*4,initial.data(),GL_DYNAMIC_READ);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,storage);
    boundaryRetained::TiltFixture fixture;bool passive=true,repeated=true;
    for(int tag=0;tag<2;++tag){
        std::string name=tag?"green":"black";auto dir=out/name;
        gh::require(fs::create_directory(dir),"NEW tag required");fixture.tilted(tag,dir);
        std::array<old::Capture,2> captures;
        if(tag)report<<',';report<<"{\"name\":"<<old::quote(name)<<",\"counts\":[";
        for(int role=0;role<2;++role){
            std::array<std::vector<std::uint32_t>,2> raw;
            for(int repeat=0;repeat<2;++repeat){
                glBindBuffer(GL_SHADER_STORAGE_BUFFER,storage);
                glBufferSubData(GL_SHADER_STORAGE_BUFFER,0,initial.size()*4,initial.data());
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,storage);GLint bound=0;
                glGetIntegeri_v(GL_SHADER_STORAGE_BUFFER_BINDING,0,&bound);
                gh::require(GLuint(bound)==storage,"Actual SSBO binding differs");
                std::string label=roles[role]+(repeat?"-repeat":"");
                auto capture=fixture.draw(programs[role],dir,label);
                glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT|GL_BUFFER_UPDATE_BARRIER_BIT);
                raw[repeat]=initial;
                glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,initial.size()*4,raw[repeat].data());
                gh::require(raw[repeat][1]==0,"Record overflow");
                gh::require(role?raw[repeat][0]>0:raw[repeat][0]==0,"Actual observer invocation wrong");
                writeBuffer(dir/(label+"-nodes.bin"),raw[repeat]);
                if(!repeat)captures[role]=capture;
                else{
                    for(int slot=0;slot<8;++slot)repeated=(capture.images[slot]==captures[role].images[slot])&&repeated;
                    repeated=(capture.depth==captures[role].depth)&&repeated;
                }
            }
            repeated=(raw[0]==raw[1])&&repeated;
            fixture.inputs(programs[role],dir/(roles[role]+"-actual-inputs"));
            if(role)report<<',';report<<raw[0][0];
        }
        for(int slot=0;slot<8;++slot)passive=(captures[0].images[slot]==captures[1].images[slot])&&passive;
        passive=(captures[0].depth==captures[1].depth)&&passive;
        report<<"]}";std::cout<<"observed "<<name<<std::endl;
    }
    report<<"],\"producerPassiveExact\":"<<(passive?"true":"false")
        <<",\"producerRepeatExact\":"<<(repeated?"true":"false")
        <<",\"IrisAccepted\":false,\"physicalFixClaimed\":false,"
        "\"scope\":\"Passive per-node source observer in actual original MAIN, one native TEST pixel. SSBO/readback/stages/textures captured; independent passivity, probability/radiometry and first-plane oracle required.\"}\n";
    old::writeText(out/"result.json",report.str());
    old::writeText(out/"probe-source.cpp",old::readText("tools/water_source_boundary_probe.cpp"));
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,0);glDeleteBuffers(1,&storage);
    for(auto id:programs)glDeleteProgram(id);old::glOkay("passive node readback");
    std::cout<<(passive&&repeated?"PASS":"RED")<<" observer raw passivity/repeat\n";return passive&&repeated?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
