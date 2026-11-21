// Actual MAIN/source adapter, genuine tilted native camera and opaque plane.
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
namespace frozenSourceAdapter {
#include "water_supported_sources_main.cpp"
}
namespace old=frozenSourceAdapter::old;
namespace gh=frozenSourceAdapter::gh;
namespace sun=frozenSourceAdapter::sun;
namespace fs=std::filesystem;
struct TiltFixture:frozenSourceAdapter::Fixture {
    old::M4 model={},inverse={};float plane=6.0f;
    void tilted(bool tag,const fs::path& dir) {
        configure(0,dir);
        const double vx=.21253617107868195,vy=.6171247363090515,vz=.7576183080673218;
        const double norm=std::sqrt(vx*vx+vy*vy+vz*vz);
        const std::array<double,3> f={vx/norm,vy/norm,vz/norm};
        const double horizontal=std::hypot(f[0],f[2]);
        const std::array<double,3> right={-f[2]/horizontal,0,f[0]/horizontal};
        const std::array<double,3> up={right[1]*f[2]-right[2]*f[1],right[2]*f[0]-right[0]*f[2],right[0]*f[1]-right[1]*f[0]};
        model[15]=inverse[15]=1;
        for(int column=0;column<3;++column){model[column*4]=float(right[column]);model[column*4+1]=float(up[column]);model[column*4+2]=float(-f[column]);}
        for(int column=0;column<3;++column)for(int row=0;row<3;++row)inverse[column*4+row]=model[row*4+column];
        const float focal=float(1/std::tan(60.*3.14159265358979323846/360.));
        projection[0]=projection[5]=focal;inverseProjection[0]=inverseProjection[5]=1/focal;
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(model.data());
        auto a=old::vertex(-12,surface,-12),b=old::vertex(-12,surface,12),c=old::vertex(12,surface,12),d=old::vertex(12,surface,-12);
        std::vector<old::Vertex> vertices={a,b,c,a,c,d};for(auto& v:vertices){v.lightmap[0]=0;v.lightmap[1]=1;}
        upload(vertices,dir/"actual-tilted-water-vertices.f32");
        const float value=.5f*((projection[10]*(-plane)+projection[14])/plane+1);
        std::vector<float> depth(257*257,value),colour(257*257*4,0);
        for(std::size_t p=0;p<colour.size();p+=4){colour[p+1]=tag?.125f:0.f;colour[p+3]=1;}
        old::Fixture::allocate(samplers[3],GL_DEPTH_COMPONENT32F,257,257,GL_DEPTH_COMPONENT,depth.data());
        old::Fixture::allocate(samplers[1],GL_RGBA32F,257,257,GL_RGBA,colour.data());
        old::glOkay("actual tilted camera/planar opaque source");
    }
    void uniforms(GLuint id) {
        frozenSourceAdapter::Fixture::uniforms(id);
        glUniformMatrix4fv(glGetUniformLocation(id,"gbufferModelView"),1,GL_FALSE,model.data());
        glUniformMatrix4fv(glGetUniformLocation(id,"gbufferModelViewInverse"),1,GL_FALSE,inverse.data());
        std::array<float,3> s={};for(int row=0;row<3;++row)for(int c=0;c<3;++c)s[row]+=model[c*4+row]*worldSun[c];
        glUniform3fv(glGetUniformLocation(id,"sunPosition"),1,s.data());old::glOkay("actual tilted uniforms");
    }
    old::Capture draw(GLuint id,const fs::path& dir,const std::string& label) {
        uniforms(id);glBindFramebuffer(GL_FRAMEBUFFER,fbo);std::array<GLenum,8> buffers;
        for(int i=0;i<8;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;glDrawBuffers(8,buffers.data());
        const float zero[4]={},one=1;for(int i=0;i<8;++i)glClearBufferfv(GL_COLOR,i,zero);glClearBufferfv(GL_DEPTH,0,&one);
        glDrawArrays(GL_PATCHES,0,6);old::Capture output;
        for(int i=0;i<8;++i){output.images[i].assign(257*257*4,NAN);glReadBuffer(buffers[i]);
            glReadPixels(0,0,257,257,GL_RGBA,GL_FLOAT,output.images[i].data());
            for(float v:output.images[i])gh::require(std::isfinite(v),"Nonfinite tilted MRT");
            old::writeRaw(dir/(label+"-slot"+std::to_string(i)+".rgba32f"),output.images[i]);}
        output.depth.assign(257*257,NAN);glReadPixels(0,0,257,257,GL_DEPTH_COMPONENT,GL_FLOAT,output.depth.data());
        old::writeRaw(dir/(label+"-depth.f32"),output.depth);old::glOkay("actual tilted draw/readback");return output;
    }
    void inputs(GLuint id,const fs::path& dir) {
        gh::require(fs::create_directory(dir),"NEW actual tilted inputs");uniforms(id);
        std::ostringstream report;report<<std::setprecision(17)<<"{\"matrices\":{";
        const char* matrices[]={"gbufferProjection","gbufferProjectionInverse","gbufferModelView","gbufferModelViewInverse"};
        const std::array<old::M4,4> expected={projection,inverseProjection,model,inverse};
        for(int i=0;i<4;++i){old::M4 value;glGetUniformfv(id,glGetUniformLocation(id,matrices[i]),value.data());
            gh::require(value==expected[i],"Actual tilted matrix differs");if(i)report<<',';report<<old::quote(matrices[i])<<':';gh::angular::numbers(report,value);}
        report<<"},\"planeViewDistance\":"<<plane<<",\"TESTAuthorized\":1,\"samplers\":[";
        const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
        for(int i=0;i<8;++i){GLint unit=-1,w=0,h=0,format=0,bound=0;
            glGetUniformiv(id,glGetUniformLocation(id,names[i]),&unit);gh::require(unit==i,"Actual named tilted sampler differs");
            glActiveTexture(GL_TEXTURE0+i);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);gh::require(GLuint(bound)==samplers[i],"Actual bound tilted texture differs");
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
            bool depth=i==3||i==4;std::vector<float> data(w*h*(depth?1:4),NAN);
            glGetTexImage(GL_TEXTURE_2D,0,depth?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,data.data());
            old::writeRaw(dir/("input-sampler"+std::to_string(i)+".f32"),data);
            if(i)report<<',';report<<"{\"name\":"<<old::quote(names[i])<<",\"unit\":"<<unit<<",\"width\":"<<w<<",\"height\":"<<h<<",\"format\":"<<format<<'}';}
        report<<"]}\n";old::writeText(dir/"state.json",report.str());old::glOkay("actual tilted source snapshot");
    }
};
int main(int argc,char** argv){try {
    gh::require(argc==3,"usage: water_supported_reflector_main READ_ONLY_SOURCES NEW_OUTPUT");
    const fs::path sources=argv[1],out=argv[2];gh::require(!fs::exists(out)&&fs::create_directories(out),"NEW tilted evidence required");
    old::Context context;const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    gh::require(renderer.find("RTX 3080 Ti")!=std::string::npos,"Actual RTX3080Ti required");
    std::array<std::string,3> geometry;for(int i=0;i<3;++i){geometry[i]=old::readText(sources/("geometry-stage"+std::to_string(i)+".glsl"));
        gh::require(gh::light::digest(geometry[i])==frozenSourceAdapter::prior::geometrySHA[i],"Original geometry differs");
        old::writeText(out/("geometry-stage"+std::to_string(i)+".glsl"),geometry[i]);}
    const std::array<std::string,3> roles={"enabled","ledger","disabled"};std::array<GLuint,3> programs;std::array<std::string,3> fragments;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-supported-reflector-main-v1\",\"renderer\":"<<old::quote(renderer)
        <<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"programs\":[";
    for(int i=0;i<3;++i){fragments[i]=old::readText(sources/(roles[i]+".fsh"));old::writeText(out/(roles[i]+".fsh"),fragments[i]);
        if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,geometry[0]},{GL_TESS_CONTROL_SHADER,geometry[1]},
            {GL_TESS_EVALUATION_SHADER,geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},roles[i],report);}
    gh::tracer::Sources query;query.geometry=geometry;report<<"],\"sourceQueries\":[";
    for(int i=1;i<3;++i){if(i>1)report<<',';sun::queriedSources(report,{programs[0],programs[i]},query,{fragments[0],fragments[i]});}
    TiltFixture fixture;std::array<std::array<old::Capture,3>,2> frames;bool exact=true;
    report<<"],\"cases\":[";
    for(int tag=0;tag<2;++tag){const std::string name=tag?"green":"black";const auto dir=out/name;gh::require(fs::create_directory(dir),"NEW tilted case required");
        fixture.tilted(tag,dir);if(tag)report<<',';report<<"{\"name\":"<<old::quote(name)<<",\"selected\":[";
        const int p=4*(128*257+128);
        for(int i=0;i<3;++i){frames[tag][i]=fixture.draw(programs[i],dir,roles[i]);auto repeat=fixture.draw(programs[i],dir,roles[i]+"-repeat");
            for(int slot=0;slot<8;++slot)exact=(frames[tag][i].images[slot]==repeat.images[slot])&&exact;
            exact=(frames[tag][i].depth==repeat.depth)&&exact;
            if(i)exact=(frames[tag][i].images[4]==frames[tag][0].images[4]&&frames[tag][i].depth==frames[tag][0].depth)&&exact;
            fixture.inputs(programs[i],dir/(roles[i]+"-actual-inputs"));
            if(i)report<<',';report<<"{\"role\":"<<old::quote(roles[i])<<",\"MRT\":[";
            for(int slot=0;slot<8;++slot){if(slot)report<<',';gh::angular::four(report,&frames[tag][i].images[slot][p]);}report<<"]}";
        }
        exact=(frames[tag][0].images[0]==frames[tag][1].images[0])&&exact;
        report<<"]}";std::cout<<"captured tilted "<<name<<std::endl;
    }
    const int p=4*(128*257+128);
    bool positive=frames[1][0].images[5][p+1]==1&&frames[1][1].images[3][p]>0
        &&frames[1][0].images[7][p+1]>0&&frames[0][0].images[7][p+1]==0;
    report<<"],\"exactControls\":"<<(exact?"true":"false")<<",\"positiveReflection\":"<<(positive?"true":"false")
        <<",\"IrisAccepted\":false,\"visualAccepted\":false,\"shippingAccepted\":false,"
        "\"scope\":\"Actual original MAIN source adapter at one TEST pixel, tilted real native camera, expanded uploaded water VBO and real opaque depth/C4. Not matched whole-Iris geometry, first-object/false-hit/energy or motion acceptance.\"}\n";
    old::writeText(out/"result.json",report.str());old::writeText(out/"probe-source.cpp",old::readText("tools/water_supported_reflector_main.cpp"));
    for(auto program:programs)glDeleteProgram(program);std::cout<<(exact&&positive?"PASS":"RED")<<" actual reflected opaque-source response\n";return exact&&positive?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
