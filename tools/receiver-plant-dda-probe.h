#ifndef AQUALUMEN_RECEIVER_PLANT_DDA_PROBE
#define AQUALUMEN_RECEIVER_PLANT_DDA_PROBE
void receiverPlantDdaProbe(const fs::path& root,bool shaded=false) {
    std::string fragment=std::string("#version 330 compatibility\n#define AQUALUMEN_PLANT_RECEIVER\n")
        +(shaded?"#define AQUALUMEN_PLANT_SHADED_RECEIVER\n":"")
        +expand(root/"lib/settings.glsl",root)+expand(root/"lib/water.glsl",root)
        +(shaded?expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)
            +expand(root/"lib/shadows.glsl",root)+expand(root/"lib/lighting.glsl",root)
            :"vec3 receiverSolarTransmission(vec3 p,sampler2D s){return vec3(0.0);}\n")
        +"uniform sampler2D colortex6;uniform int colorMode;\n"
        +expand(root/"lib/water_receiver.glsl",root)+expand(root/"lib/water_plant_backend.glsl",root)+R"(
bool waterReceiverSurfaceCorners(ivec3 cell,vec4 geometry,out vec4 heights){heights=vec4(0.0);return false;}
void main(){WaterReceiver hit=waterReceiverFirst(vec3(0.5,3.5,0.5),vec3(0.0,-1.0,0.0));
    gl_FragColor=colorMode==1?vec4(hit.color,float(hit.sourceReady)):vec4(float(hit.known),float(hit.sourceReady),hit.travel,hit.normal.x);}
)";
    GLuint program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"receiver-plant-dda");
    GLuint textures[13],framebuffer;glGenTextures(13,textures);glGenFramebuffers(1,&framebuffer);glUseProgram(program);
    std::vector<float> cells={3,0,0,0, 2,0,0,0, 0,0,0,0, 2,0,0,0};
    std::vector<float> source(16,0),sun(16,0),faces(16,0);
    for(int row=0;row<4;row++){source[row*4]=.75f;source[row*4+3]=1;sun[row*4+3]=1;faces[row*4+1]=faces[row*4+3]=1;}
    std::vector<float> primitives={.1f,2.42f,.1f,.5f, .9f,2.58f,.1f,.5f, .9f,2.58f,.9f,.5f, .5f,.5f,.5f,1,
        .1f,2.42f,.1f,.5f, .9f,2.58f,.9f,.5f, .1f,2.42f,.9f,.5f, .5f,.5f,.5f,1};
    auto upload=[&](int unit,int width,int height,const std::vector<float>& values){
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,0);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,values.data());
    };
    upload(0,1,4,cells);upload(1,1,4,source);upload(2,1,4,sun);upload(3,1,4,faces);
    upload(4,4,2,primitives);upload(5,1,1,{1,1,1,0});upload(6,1,1,{0,0,0,0});
    std::vector<float> headers(1024,0),indices(1024,0);
    for(int cell=0;cell<4;cell++){headers[cell*4+2]=headers[cell*4+3]=1;}
    headers[9]=2;headers[12]=2;
    headers[16]=1;headers[17]=4;headers[18]=1;headers[19]=2;headers[20]=2;indices[4]=1;
    upload(7,256,1,headers);upload(8,256,1,indices);
    if(shaded) {
        std::vector<float> material;
        for(int primitive=0;primitive<2;primitive++)for(int corner=0;corner<3;corner++)
            material.insert(material.end(),{.5f,.5f,1,0,.8f,0,0,.5f});
        upload(9,6,2,material);upload(10,64,32,std::vector<float>(64*32*4,0));
        upload(11,64,32,std::vector<float>(64*32*4,0));
        glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,textures[12]);
        float depth=1;glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&depth);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        glUniform1i(glGetUniformLocation(program,"aqualumenPlantMaterial"),9);
        glUniform1i(glGetUniformLocation(program,"colortex6"),10);glUniform1i(glGetUniformLocation(program,"colortex7"),11);
        glUniform1i(glGetUniformLocation(program,"shadowtex0"),12);
        const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for(const char* name:{"gbufferModelViewInverse","shadowModelView","shadowProjection"})
            glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,-1,0);
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,-1,0);
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    }
    const char* names[]={"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces","aqualumenPlantPrimitives","aqualumenPlantAtlas"};
    for(int unit=0;unit<6;unit++)glUniform1i(glGetUniformLocation(program,names[unit]),unit);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),2);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunMode"),0);
    glUniform3i(glGetUniformLocation(program,"aqualumenReceiverSize"),1,4,1);
    glUniform3f(glGetUniformLocation(program,"aqualumenReceiverOrigin"),0,0,0);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantHeaders"),7);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantIndices"),8);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantReady"),1);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantMemberships"),2);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantTriangles"),2);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantAtlasOwned"),1);
    glUniform3i(glGetUniformLocation(program,"aqualumenPlantSize"),1,4,1);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);glViewport(0,0,1,1);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("Plant DDA framebuffer incomplete");
    auto draw=[&](){glBegin(GL_TRIANGLE_STRIP);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(-1,1);glVertex2f(1,1);glEnd();
        std::array<float,4> result;glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,result.data());return result;};
    int checkIndex=0;
    auto check=[&](float known,float ready,float travel){checkIndex++;auto actual=draw();
        if(actual[0]!=known || actual[1]!=ready || std::abs(actual[2]-travel)>1e-5f)
            throw std::runtime_error("Joint plant/opaque DDA result mismatch at check "+std::to_string(checkIndex)+": actual="+std::to_string(actual[0])+","+
                std::to_string(actual[1])+","+std::to_string(actual[2])+" expected="+std::to_string(known)+","+
                std::to_string(ready)+","+std::to_string(travel));};
    headers[10]=0;upload(7,256,1,headers);check(0,0,0);
    headers[10]=1;upload(7,256,1,headers);check(1,1,2.5f);
    upload(5,1,1,{1,1,1,1});check(1,shaded?1:0,1);
    auto diagonal=draw();if(std::abs(diagonal[3])<.1f)throw std::runtime_error("Plant normal incorrectly became cube UP");
    if(shaded) {
        glUniform1i(glGetUniformLocation(program,"colorMode"),1);auto color=draw();
        double expected=std::pow(.8,2.2)*(2+.003);
        if(std::abs(color[0]-expected)>1e-6 || color[1]!=0 || color[2]!=0 || color[3]!=1)
            throw std::runtime_error("DDA plant source RGB differs from its own material shading");
        glUniform1i(glGetUniformLocation(program,"colorMode"),0);
    }
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantReady"),0);check(0,0,0);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantReady"),1);
    auto originalHeaders=headers;
    for(int channel=0;channel<4;channel++)headers[4+channel]=originalHeaders[8+channel];
    headers[8]=2;headers[9]=0;
    upload(7,256,1,headers);
    glUniform3i(glGetUniformLocation(program,"aqualumenPlantReceiverOffset"),0,-1,0);check(1,shaded?1:0,1);
    headers=originalHeaders;upload(7,256,1,headers);
    glUniform3i(glGetUniformLocation(program,"aqualumenPlantReceiverOffset"),0,1,0);check(0,0,0);
    glUniform3i(glGetUniformLocation(program,"aqualumenPlantReceiverOffset"),2147483647,0,0);check(0,0,0);
    glUniform3i(glGetUniformLocation(program,"aqualumenPlantReceiverOffset"),0,0,0);
    glUniform1f(glGetUniformLocation(program,"aqualumenPlantLod"),1);check(0,0,0);
    glUniform1f(glGetUniformLocation(program,"aqualumenPlantLod"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantAtlasOwned"),0);check(0,0,1);
    glUniform1i(glGetUniformLocation(program,"aqualumenPlantAtlasOwned"),1);
    headers[20]=3;upload(7,256,1,headers);check(0,0,0);
    headers[20]=2;upload(7,256,1,headers);
    indices[4]=0;upload(8,256,1,indices);check(0,0,0);
    indices[4]=1;upload(8,256,1,indices);
    for(int triangle=0;triangle<2;triangle++)for(int vertex=0;vertex<3;vertex++) {
        primitives[triangle*16+vertex*4]-=10;
        primitives[triangle*16+vertex*4+2]+=7;
    }
    upload(4,4,2,primitives);
    glUniform3f(glGetUniformLocation(program,"aqualumenPlantReference"),10,0,-7);check(1,shaded?1:0,1);
    for(int triangle=0;triangle<2;triangle++)for(int vertex=0;vertex<3;vertex++) {
        primitives[triangle*16+vertex*4]+=10;
        primitives[triangle*16+vertex*4+2]-=7;
    }
    upload(4,4,2,primitives);
    glUniform3f(glGetUniformLocation(program,"aqualumenPlantReference"),0,0,0);
    upload(5,1,1,{1,1,1,0});primitives[15]=primitives[31]=0;upload(4,4,2,primitives);check(0,0,1);
    primitives[15]=primitives[31]=1;upload(4,4,2,primitives);
    headers[11]=0;upload(7,256,1,headers);check(0,0,0);
    headers[11]=1;upload(7,256,1,headers);
    cells[8]=3;upload(0,1,4,cells);upload(5,1,1,{1,1,1,1});check(1,1,.5f);
    cells[8]=4;cells[9]=.2f;cells[10]=cells[11]=1;upload(0,1,4,cells);check(0,0,0);
    cells[8]=2;cells[9]=cells[10]=cells[11]=0;upload(0,1,4,cells);upload(5,1,1,{1,1,1,0});check(1,1,2.5f);
    cells[4]=0;headers[6]=0;upload(0,1,4,cells);upload(7,256,1,headers);check(0,0,0);
    glDeleteProgram(program);glDeleteTextures(13,textures);glDeleteFramebuffers(1,&framebuffer);
    if(shaded)std::cout<<"PASS GPU DDA plant shading callback: first leaf supplies own red material radiance, transparent hole reaches floor, earlier bank/unknown/interface guards retained; not Minecraft visual acceptance\n";
    std::cout<<"PASS GPU production DDA published plant backend: indexed transparent leaf reaches paired floor, opaque diagonal leaf stops without borrowed radiance, unknown alpha/fluid/model blocks, earlier bank and interface/unknown remain authoritative; supplied fixtures, not live publication\n";
}
#endif
