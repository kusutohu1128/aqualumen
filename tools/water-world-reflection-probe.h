#ifndef AQUALUMEN_WATER_WORLD_REFLECTION_PROBE
#define AQUALUMEN_WATER_WORLD_REFLECTION_PROBE
#include "receiver-run-probe.h"
#include "receiver-plant-dda-probe.h"
void waterWorldReflectionProbe(const fs::path& root) {
    receiverRunProbe(root);
    receiverPlantDdaProbe(root);
    receiverPlantDdaProbe(root,true);
    GLuint sourceProgram=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",expand(root/"prepare1.fsh",root),"receiver-source-shared-shading");
    glDeleteProgram(sourceProgram);
    std::cout<<"PASS compile/link receiver source shared shading; not a source draw or renderer integration\n";
    std::string fragment="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)
        +expand(root/"lib/water.glsl",root)
        +"uniform sampler2D colortex6; vec3 receiverSolarTransmission(vec3 p,sampler2D s){return vec3(0.0);}\n"
        +expand(root/"lib/water_receiver.glsl",root)+R"(
uniform vec3 receiverProbeOrigin;
uniform vec3 receiverProbeDirection;
uniform int receiverProbeInterface;
uniform int receiverProbeSurfaceReady;
uniform vec4 receiverProbeHeights;
uniform vec3 receiverProbeEnd;
bool waterReceiverSurfaceCorners(ivec3 cell,vec4 geometry,out vec4 heights) {
    heights=receiverProbeHeights+geometry.g-0.001;return receiverProbeSurfaceReady==1;
}
void main() {
    if(receiverProbeInterface==2) {
        gl_FragColor=vec4(float(waterReceiverBelowBoth(receiverProbeOrigin,receiverProbeEnd,receiverProbeHeights)));return;
    }
    WaterReceiver receiver=receiverProbeInterface==1?waterReceiverFirstFromInterface(receiverProbeOrigin,receiverProbeDirection)
        :waterReceiverFirst(receiverProbeOrigin,receiverProbeDirection);
    gl_FragColor=vec4(receiver.sourceReady?receiver.color*waterTransmission(receiver.travel):vec3(0.0),receiver.sourceReady?receiver.travel:-1.0);
}
)";
    GLuint program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"water-world-reflection");
    GLuint textures[5],framebuffer;
    glGenTextures(5,textures);glGenFramebuffers(1,&framebuffer);
    std::vector<float> cells(4*16*4,0),source(cells.size(),0),direct(cells.size(),0),faces(cells.size(),0);
    for(int z=0;z<4;++z)for(int y=0;y<4;++y)for(int x=0;x<4;++x) {
        int offset=(x+(y*4+z)*4)*4;
        cells[offset]=y==0?3.0f:2.0f;
        source[offset]=0.75f;source[offset+3]=1;
        direct[offset+3]=1;
        faces[offset+1]=1;faces[offset+3]=1;
    }
    glUseProgram(program);
    for(int unit=0;unit<3;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        const auto& values=unit==0?cells:unit==1?source:direct;
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,4,16,0,GL_RGBA,GL_FLOAT,values.data());
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    }
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverCells"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverSource"),1);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverSun"),2);
    glUniform3i(glGetUniformLocation(program,"aqualumenReceiverSize"),4,4,4);
    glUniform3f(glGetUniformLocation(program,"aqualumenReceiverOrigin"),0,0,0);
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.5f,.5f);
    glUniform3f(glGetUniformLocation(program,"receiverProbeDirection"),0,-1,0);
    glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,textures[4]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,4,16,0,GL_RGBA,GL_FLOAT,faces.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverFaces"),4);
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[3],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("World reflection probe framebuffer incomplete");
    glViewport(0,0,1,1);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);
    auto draw=[&](int ready) {
        glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),ready);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        std::array<float,4> result;glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,result.data());return result;
    };
    auto positive=draw(1),disabled=draw(0);
    const std::string clarityToken="#define WATER_CLARITY ";
    auto clarityAt=fragment.find(clarityToken);
    if(clarityAt==std::string::npos)throw std::runtime_error("Water clarity literal unavailable");
    float clarity=std::stof(fragment.substr(clarityAt+clarityToken.size()));
    float expected=0.75f*std::exp(-0.32f*1.5f/clarity);
    if(std::abs(positive[0]-expected)>1e-5f || positive[1]!=0 || positive[2]!=0 || positive[3]!=1.5f || disabled[0]!=0 || disabled[3]!=-1)
        throw std::runtime_error("World reflection source/travel or disabled readiness failed");
    auto ownedFace=draw(2);
    if(std::abs(ownedFace[0]-expected)>1e-5f || ownedFace[3]!=1.5f)throw std::runtime_error("Matching owned receiver face rejected");
    faces[1]=-1;
    glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,textures[4]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,16,GL_RGBA,GL_FLOAT,faces.data());
    auto wrongFace=draw(2);
    if(wrongFace[0]!=0 || wrongFace[3]!=-1)throw std::runtime_error("Opposite receiver face supplied radiance");
    faces[1]=1;
    glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,textures[4]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,16,GL_RGBA,GL_FLOAT,faces.data());
    int partialOffset=(0+4*(2*4+0))*4;
    cells[partialOffset]=4;cells[partialOffset+1]=.8888889f;cells[partialOffset+2]=1;cells[partialOffset+3]=1;
    auto uploadCells=[&]() {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[0]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,16,GL_RGBA,GL_FLOAT,cells.data());
    };
    uploadCells();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.1f,.5f);
    auto partial=draw(2);
    float partialExpected=.75f*std::exp(-.32f*1.1f/clarity);
    if(std::abs(partial[0]-partialExpected)>1e-5f || std::abs(partial[3]-1.1f)>1e-5f)
        throw std::runtime_error("Qualified lower partial-water segment rejected");
    auto rejectPartial=[&]() {
        auto result=draw(2);
        if(result[0]!=0 || result[3]!=-1)throw std::runtime_error("Unqualified partial-water/air interval became a reflection");
    };
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.88f,.5f);rejectPartial();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.1f,.5f);
    glUniform3f(glGetUniformLocation(program,"receiverProbeDirection"),0,1,0);rejectPartial();
    glUniform3f(glGetUniformLocation(program,"receiverProbeDirection"),0,-1,0);
    cells[partialOffset+2]=0;uploadCells();rejectPartial();cells[partialOffset+2]=1;
    cells[partialOffset+1]=std::numeric_limits<float>::quiet_NaN();uploadCells();rejectPartial();
    cells[partialOffset+1]=1;uploadCells();rejectPartial();
    cells[partialOffset+1]=1.8888889f;uploadCells();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.5f,.5f);
    auto cap=draw(2);
    if(std::abs(cap[0]-expected)>1e-5f || cap[3]!=1.5f)
        throw std::runtime_error("Qualified underlying water cap rejected");
    cells[partialOffset+1]=1.01f;uploadCells();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.99f,.5f);rejectPartial();
    cells[partialOffset+1]=2;uploadCells();rejectPartial();
    cells[partialOffset+1]=.8888889f;uploadCells();
    glUniform1i(glGetUniformLocation(program,"receiverProbeInterface"),1);
    glUniform1i(glGetUniformLocation(program,"receiverProbeSurfaceReady"),1);
    glUniform4f(glGetUniformLocation(program,"receiverProbeHeights"),0,0,0,0);
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.88f,.5f);
    auto interfaceHit=draw(2);
    float interfaceExpected=.75f*std::exp(-.32f*1.88f/clarity);
    if(std::abs(interfaceHit[0]-interfaceExpected)>1e-5f || std::abs(interfaceHit[3]-1.88f)>1e-5f)
        throw std::runtime_error("Qualified near-interface geometry did not reach the owned source");
    glUniform1i(glGetUniformLocation(program,"receiverProbeSurfaceReady"),0);rejectPartial();
    glUniform1i(glGetUniformLocation(program,"receiverProbeSurfaceReady"),1);
    glUniform4f(glGetUniformLocation(program,"receiverProbeHeights"),std::numeric_limits<float>::quiet_NaN(),0,0,0);rejectPartial();
    glUniform4f(glGetUniformLocation(program,"receiverProbeHeights"),0,0,0,0);
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.89f,.5f);rejectPartial();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.88f,.5f);
    glUniform3f(glGetUniformLocation(program,"receiverProbeDirection"),0,1,0);rejectPartial();
    glUniform3f(glGetUniformLocation(program,"receiverProbeDirection"),0,-1,0);
    int upperOffset=(0+4*(3*4+0))*4;
    cells[upperOffset]=5;cells[upperOffset+1]=-.1111111f;cells[upperOffset+2]=1;cells[upperOffset+3]=1;uploadCells();
    glUniform4f(glGetUniformLocation(program,"receiverProbeHeights"),.2f,.2f,.2f,.2f);
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,3.02f,.5f);
    auto upperHit=draw(2);
    float upperExpected=.75f*std::exp(-.32f*2.02f/clarity);
    if(std::abs(upperHit[0]-upperExpected)>1e-5f || std::abs(upperHit[3]-2.02f)>1e-5f)
        throw std::runtime_error("Deformed crest upper-cap segment did not reach the owned source");
    glUniform1i(glGetUniformLocation(program,"receiverProbeInterface"),0);rejectPartial();
    glUniform1i(glGetUniformLocation(program,"receiverProbeInterface"),1);
    cells[upperOffset+2]=0;uploadCells();rejectPartial();
    cells[upperOffset]=2;cells[upperOffset+1]=0;cells[upperOffset+2]=0;cells[upperOffset+3]=0;uploadCells();
    glUniform1i(glGetUniformLocation(program,"receiverProbeInterface"),2);
    auto interval=[&](const std::array<float,3>& start,const std::array<float,3>& end,const std::array<float,4>& heights,bool allowed) {
        glUniform3fv(glGetUniformLocation(program,"receiverProbeOrigin"),1,start.data());
        glUniform3fv(glGetUniformLocation(program,"receiverProbeEnd"),1,end.data());
        glUniform4fv(glGetUniformLocation(program,"receiverProbeHeights"),1,heights.data());
        auto result=draw(2);
        for(float value:result)if(value!=(allowed?1.0f:0.0f))throw std::runtime_error("Piecewise triangle interval qualification failed");
    };
    interval({.1f,.72f,.2f},{.8f,.90f,.3f},{.7f,1.0f,.8f,1.1f},true);
    interval({.1f,.72f,.2f},{.8f,1.0f,.3f},{.7f,1.0f,.8f,1.1f},false);
    interval({.1f,.5f,.2f},{1.0f,.5f,.65f},{1,0,0,1},false);
    interval({-.01f,0,.2f},{.8f,0,.3f},{1,1,1,1},false);
    interval({.1f,0,.2f},{.8f,0,.3f},{1,std::numeric_limits<float>::quiet_NaN(),1,1},false);
    glUniform1i(glGetUniformLocation(program,"receiverProbeInterface"),0);
    cells[partialOffset]=2;uploadCells();
    glUniform3f(glGetUniformLocation(program,"receiverProbeOrigin"),.5f,2.5f,.5f);
    source[3]=0;
    glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,16,GL_RGBA,GL_FLOAT,source.data());
    auto unavailable=draw(1);
    if(unavailable[0]!=0 || unavailable[3]!=-1)throw std::runtime_error("Unavailable first source became a reflection");
    glDeleteProgram(program);glDeleteTextures(5,textures);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"PASS GPU bounded world reflection receiver: supplied red source, full/lower partial/cap and qualified near-interface/upper-crest Beer paths; both-diagonal interval/air-crossing/unknown/nonfinite/disabled/source negatives; not production MAIN, live corner ownership or runtime receiver-hit acceptance\n";
}
#endif
