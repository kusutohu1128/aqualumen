#ifndef AQUALUMEN_RECEIVER_SOURCE_PROBE
#define AQUALUMEN_RECEIVER_SOURCE_PROBE
void receiverSourceProbe(const fs::path& root) {
    GLuint program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",expand(root/"prepare1.fsh",root),"receiver-source-draw");
    GLuint textures[13],framebuffer;glGenTextures(13,textures);glGenFramebuffers(1,&framebuffer);
    std::array<std::array<float,4>,5> inputs={{{.5f,.25f,.125f,1},{.8f,.6f,.4f,1},{0,1,0,1},{0,0,0,1},{1,0,.5f,1}}};
    for(int index=0;index<13;++index) {
        glActiveTexture(GL_TEXTURE0+index);glBindTexture(GL_TEXTURE_2D,textures[index]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(index==7) {
            float depth=1;glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&depth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else {
            std::vector<float> pixels(index==5||index==6?64*32*4:4,0);
            if(index<5)std::copy(inputs[index].begin(),inputs[index].end(),pixels.begin());
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,index==5||index==6?64:1,index==5||index==6?32:1,0,GL_RGBA,GL_FLOAT,pixels.data());
        }
    }
    glUseProgram(program);
    const char* names[]={"receiverInputTexel","receiverInputTint","receiverInputNormal","receiverInputPosition","receiverInputLightmap","colortex6","colortex7","shadowtex0"};
    for(int unit=0;unit<8;++unit)glUniform1i(glGetUniformLocation(program,names[unit]),unit);
    glUniform1i(glGetUniformLocation(program,"receiverInputUv"),10);
    glUniform1i(glGetUniformLocation(program,"receiverInputGradients"),11);
    glUniform1i(glGetUniformLocation(program,"receiverAtlas"),12);
    const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,identity);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,-1,0);
    glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,-1,0);
    glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform2i(glGetUniformLocation(program,"receiverInputSize"),1,1);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    const GLenum outputs[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};
    for(int index=0;index<2;++index)glFramebufferTexture2D(GL_FRAMEBUFFER,outputs[index],GL_TEXTURE_2D,textures[8+index],0);
    glDrawBuffers(2,outputs);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("Receiver source framebuffer incomplete");
    glViewport(0,0,1,1);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);
    auto draw=[&]() {
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        std::array<std::array<float,4>,2> result;
        for(int index=0;index<2;++index){glReadBuffer(outputs[index]);glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,result[index].data());}
        if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("Receiver source draw/readback GL error");
        return result;
    };
    auto positive=draw();
    const double block[]={2,1.12,.5};
    for(int channel=0;channel<3;++channel) {
        double expected=std::pow(double(inputs[0][channel])*inputs[1][channel],2.2)*(block[channel]+.006*.5);
        if(!std::isfinite(positive[0][channel]) || std::abs(positive[0][channel]-expected)>1e-6 || positive[1][channel]!=0)
            throw std::runtime_error("Receiver source differs from independent material/block-light reference");
    }
    if(positive[0][3]!=1 || positive[1][3]!=1)throw std::runtime_error("Receiver source readiness is not paired");
    auto reject=[&]() {
        auto result=draw();
        for(const auto& output:result)for(float value:output)if(value!=0)throw std::runtime_error("Unqualified receiver input became radiance");
    };
    auto replace=[&](int slot,const std::array<float,4>& data) {
        glActiveTexture(GL_TEXTURE0+slot);glBindTexture(GL_TEXTURE_2D,textures[slot]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,data.data());
    };
    GLint alphaMode=glGetUniformLocation(program,"receiverAlphaMode");
    if(alphaMode<0)throw std::runtime_error("Missing explicit receiver alpha qualification");
    replace(0,{.5f,.25f,.125f,.5f});reject();
    glUniform1i(alphaMode,1);
    for(float alpha:{.1f,.5f,1.0f}) {
        replace(0,{.5f,.25f,.125f,alpha});auto result=draw();
        for(int target=0;target<2;target++)for(int channel=0;channel<4;channel++)
            if(std::abs(result[target][channel]-positive[target][channel])>1e-6)
                throw std::runtime_error("Cutout source differs from admitted opaque source");
    }
    for(float alpha:{0.0f,.099f,1.01f,std::numeric_limits<float>::quiet_NaN()}) {
        replace(0,{.5f,.25f,.125f,alpha});reject();
    }
    replace(0,inputs[0]);glUniform1i(alphaMode,2);reject();glUniform1i(alphaMode,0);
    std::cout<<"PASS receiver alpha modes: strict opaque retained, cutout threshold/paired RGB, invalid alpha/mode rejected\n";
    glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,textures[6]);
    const std::array<float,4> emptyCache={0,0,0,0};
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,emptyCache.data());
    glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);
    const std::array<float,4> transmission={1,1,1,1};
    glTexSubImage2D(GL_TEXTURE_2D,0,0,31,1,1,GL_RGBA,GL_FLOAT,transmission.data());
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
    glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,1,0);
    replace(4,{0,1,.5f,1});
    auto verifySun=[&](double gate) {
        auto result=draw();
        const double solar[]={18,17.6,17};
        for(int channel=0;channel<3;++channel) {
            double albedo=std::pow(double(inputs[0][channel])*inputs[1][channel],2.2);
            double direct=albedo*solar[channel]*gate/std::acos(-1.0);
            double total=direct+albedo*.003;
            if(!std::isfinite(result[0][channel]) || !std::isfinite(result[1][channel]) ||
               std::abs(result[0][channel]-total)>2e-6 || std::abs(result[1][channel]-direct)>2e-6)
                throw std::runtime_error("Receiver source differs from independent direct-Sun reference");
        }
        if(result[0][3]!=1 || result[1][3]!=1)throw std::runtime_error("Solar receiver readiness is not paired");
    };
    verifySun(1);
    glUniform1f(glGetUniformLocation(program,"rainStrength"),.4f);verifySun(1-.85*.4);
    glUniform1f(glGetUniformLocation(program,"rainStrength"),0);
    glActiveTexture(GL_TEXTURE7);glBindTexture(GL_TEXTURE_2D,textures[7]);
    float blockedDepth=0;glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_DEPTH_COMPONENT,GL_FLOAT,&blockedDepth);verifySun(0);
    float litDepth=1;glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_DEPTH_COMPONENT,GL_FLOAT,&litDepth);
    replace(4,{0,0,.5f,1});verifySun(0);replace(4,inputs[4]);
    auto unavailable=inputs[0];unavailable[3]=0;replace(0,unavailable);reject();replace(0,inputs[0]);
    auto invalid=inputs[2];invalid[1]=2;replace(2,invalid);reject();replace(2,inputs[2]);
    auto nonfinite=inputs[0];nonfinite[0]=std::numeric_limits<float>::quiet_NaN();replace(0,nonfinite);reject();replace(0,inputs[0]);
    auto badAo=inputs[4];badAo[2]=2;replace(4,badAo);reject();replace(4,inputs[4]);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,-1,0);
    glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,-1,0);
    glUniform1i(glGetUniformLocation(program,"receiverTexelMode"),1);
    replace(10,{.5f,.5f,0,1});replace(11,{0,0,0,0});
    glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,textures[12]);
    const std::array<float,16> atlas={0,0,0,1,1,.5f,.25f,1,1,.5f,.25f,1,0,0,0,1};
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,2,2,0,GL_RGBA,GL_FLOAT,atlas.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    const std::array<float,4> mip={.2f,.4f,.6f,1};
    glTexImage2D(GL_TEXTURE_2D,1,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,mip.data());
    auto verifyAtlas=[&](const std::array<float,4>& filtered) {
        auto result=draw();
        for(int channel=0;channel<3;++channel) {
            double expected=std::pow(double(filtered[channel])*inputs[1][channel],2.2)*(block[channel]+.003);
            if(std::abs(result[0][channel]-expected)>1e-6 || result[1][channel]!=0)
                throw std::runtime_error("Receiver atlas filtering differs from independent RGB reference");
        }
        if(result[0][3]!=1 || result[1][3]!=1)throw std::runtime_error("Atlas receiver readiness is not paired");
    };
    verifyAtlas(inputs[0]);
    replace(11,{1,0,0,1});verifyAtlas(mip);
    replace(10,{.5f,.5f,0,0});reject();replace(10,{.5f,.5f,0,1});
    replace(10,{1.1f,.5f,0,1});reject();replace(10,{.5f,.5f,0,1});
    replace(11,{std::numeric_limits<float>::quiet_NaN(),0,0,0});reject();replace(11,{0,0,0,0});
    replace(11,{std::numeric_limits<float>::infinity(),0,0,0});reject();replace(11,{0,0,0,0});
    replace(11,{1,0,0,1});replace(12,{.2f,.4f,.6f,.5f});
    glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,textures[12]);
    const std::array<float,4> translucentMip={.2f,.4f,.6f,.5f};
    glTexSubImage2D(GL_TEXTURE_2D,1,0,0,1,1,GL_RGBA,GL_FLOAT,translucentMip.data());reject();
    glUniform1i(glGetUniformLocation(program,"receiverTexelMode"),2);reject();
    glUniform1i(glGetUniformLocation(program,"receiverTexelMode"),0);
    glUniform2i(glGetUniformLocation(program,"receiverInputSize"),2,1);reject();
    glUniform2i(glGetUniformLocation(program,"receiverInputSize"),3,1);
    for(int slot=0;slot<5;++slot) {
        std::array<float,12> lanes={};
        for(int lane=0;lane<3;++lane)std::copy(inputs[slot].begin(),inputs[slot].end(),lanes.begin()+lane*4);
        if(slot==0) { lanes[7]=0; lanes[8]=.25f; lanes[9]=.5f; lanes[10]=.75f; }
        glActiveTexture(GL_TEXTURE0+slot);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,3,1,0,GL_RGBA,GL_FLOAT,lanes.data());
    }
    for(int slot=8;slot<10;++slot) {
        glActiveTexture(GL_TEXTURE0+slot);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,3,1,0,GL_RGBA,GL_FLOAT,nullptr);
    }
    glUniform1i(glGetUniformLocation(program,"receiverTexelMode"),1);
    const std::array<float,12> batchUv={.25f,.5f,0,1,.25f,.5f,0,0,.75f,.5f,0,1};
    const std::array<float,12> batchGradients={};
    for(int slot:{10,11}) {
        glActiveTexture(GL_TEXTURE0+slot);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,3,1,0,GL_RGBA,GL_FLOAT,slot==10?batchUv.data():batchGradients.data());
    }
    const std::array<float,8> batchAtlas={.2f,.4f,.6f,1,.7f,.5f,.3f,1};
    glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,textures[12]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,2,1,0,GL_RGBA,GL_FLOAT,batchAtlas.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,0);
    glViewport(0,0,3,1);
    glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
    std::array<std::array<float,12>,2> batch={};
    for(int output=0;output<2;++output) {
        glReadBuffer(outputs[output]);glReadPixels(0,0,3,1,GL_RGBA,GL_FLOAT,batch[output].data());
        for(int channel=4;channel<8;++channel)if(batch[output][channel]!=0)
            throw std::runtime_error("Unqualified batch lane supplied radiance/readiness");
    }
    for(int lane:{0,2}) {
        for(int channel=0;channel<3;++channel) {
            double texel=batchAtlas[(lane==0?0:4)+channel];
            double expected=std::pow(texel*inputs[1][channel],2.2)*(block[channel]+.003);
            if(std::abs(batch[0][lane*4+channel]-expected)>1e-6 || batch[1][lane*4+channel]!=0)
                throw std::runtime_error("Batch lane address/radiance differs from independent reference");
        }
        if(batch[0][lane*4+3]!=1 || batch[1][lane*4+3]!=1)
            throw std::runtime_error("Valid batch lane lost paired readiness");
    }
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("Batch source draw/readback GL error");
    glDeleteProgram(program);
    std::string plantFragment="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)
        +expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)
        +expand(root/"lib/shadows.glsl",root)+expand(root/"lib/lighting.glsl",root)
        +expand(root/"lib/water_plant_shading.glsl",root)+R"(
uniform sampler2D attributes,primitives,atlas,sky;
uniform int owned;uniform vec2 hitUv;
void main(){vec3 total,direct;bool ready=waterPlantShadeHit(attributes,primitives,atlas,sky,
1,0,vec3(.75,1,.5),vec3(0,-1,0),1.0,hitUv,vec3(0),0.0,0,owned==1,total,direct);
gl_FragData[0]=vec4(total,float(ready));gl_FragData[1]=vec4(direct,float(ready));}
)";
    program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",plantFragment,"plant-hit-source-draw");
    glUseProgram(program);
    auto plantUpload=[&](int unit,int width,int height,const std::vector<float>& values){
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,values.data());
    };
    plantUpload(0,6,1,{0,0,1,0, .8f,.6f,.4f,.5f, 1,0,1,0, .8f,.6f,.4f,.5f, 1,1,1,0, .8f,.6f,.4f,.5f});
    plantUpload(1,4,1,{0,0,0,0, 1,0,0,1, 1,0,1,1, 0,0,1,1});
    plantUpload(5,64,32,std::vector<float>(64*32*4,0));
    plantUpload(6,64,32,std::vector<float>(64*32*4,0));
    plantUpload(8,1,1,{0,0,0,0});plantUpload(9,1,1,{0,0,0,0});
    plantUpload(12,1,1,{.5f,.25f,.125f,.5f});
    glUniform1i(glGetUniformLocation(program,"attributes"),0);glUniform1i(glGetUniformLocation(program,"primitives"),1);
    glUniform1i(glGetUniformLocation(program,"atlas"),12);glUniform1i(glGetUniformLocation(program,"sky"),5);
    glUniform1i(glGetUniformLocation(program,"colortex7"),6);glUniform1i(glGetUniformLocation(program,"shadowtex0"),7);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,identity);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,-1,0);
    glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,-1,0);
    glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform1i(glGetUniformLocation(program,"owned"),1);glUniform2f(glGetUniformLocation(program,"hitUv"),.75f,.5f);
    glViewport(0,0,1,1);
    auto plant=draw();
    for(int channel=0;channel<3;channel++) {
        double expected=std::pow(double(inputs[0][channel])*inputs[1][channel],2.2)*(block[channel]+.003);
        if(std::abs(plant[0][channel]-expected)>1e-6 || plant[1][channel]!=0)
            throw std::runtime_error("Plant ray-hit shade differs from independent material/blocklight reference");
    }
    if(plant[0][3]!=1 || plant[1][3]!=1)throw std::runtime_error("Plant ray-hit shade lost paired readiness");
    glUniform1i(glGetUniformLocation(program,"owned"),0);reject();
    glUniform1i(glGetUniformLocation(program,"owned"),1);
    glUniform2f(glGetUniformLocation(program,"hitUv"),.7f,.5f);reject();
    glUniform2f(glGetUniformLocation(program,"hitUv"),.75f,.5f);
    plantUpload(1,4,1,{0,0,0,0, 1,0,0,1, 1,0,1,1, 0,0,1,0});reject();
    plantUpload(1,4,1,{0,0,0,0, 1,0,0,1, 1,0,1,1, 0,0,1,1});
    plantUpload(12,1,1,{.5f,.25f,.125f,0});reject();
    std::cout<<"PASS GPU actual plant ray-hit source shading: independent tinted/blocklight RGB, paired total/Sun readiness, cutout hole/atlas ownership/foreign UV rejection; not live reflection acceptance\n";
    glDeleteProgram(program);glDeleteTextures(13,textures);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"PASS GPU actual receiver source stage: independent tinted material/block-light and legacy-cache direct Sun RGB, rain/shadow/skylight gates, paired readiness; textureGrad bilinear/explicit mip footprints and distinct atlas batch lanes with an unavailable middle lane; missing/nonfinite/normal/AO/extent/UV/gradient/mode/translucent negatives; not separate clear-cache/cloud or Minecraft source ownership acceptance\n";
}
#endif
