#ifndef AQUALUMEN_RECEIVER_RUN_PROBE
#define AQUALUMEN_RECEIVER_RUN_PROBE
void receiverRunProbe(const fs::path& root) {
    std::string fragment="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)
        +expand(root/"lib/water.glsl",root)
        +"uniform sampler2D colortex6;vec3 receiverSolarTransmission(vec3 p,sampler2D s){return vec3(0.0);}\n"
        +expand(root/"lib/water_receiver.glsl",root)+R"(
uniform sampler2D probeHeaders;
uniform sampler2D probeRanges;
uniform sampler2D probeCells;
uniform ivec3 probeSize;
uniform int probeRecords;
uniform int probeMode;
uniform vec3 probeOrigin;
uniform vec3 probeDirection;
bool waterReceiverSurfaceCorners(ivec3 cell,vec4 geometry,out vec4 heights) {
    heights=vec4(0.0);return false;
}
void main() {
    if(probeMode>=2) {
        WaterReceiver receiver=waterReceiverFirst(probeOrigin,probeDirection);
        if(probeMode==4) { gl_FragColor=vec4(float(receiver.known),float(receiver.sourceReady),receiver.travel,receiver.normal.x);return; }
        gl_FragColor=!receiver.sourceReady?vec4(-99.0):probeMode==2
            ?vec4(receiver.color*waterTransmission(receiver.travel),receiver.travel):vec4(receiver.point,1.0);
        return;
    }
    int row=int(gl_FragCoord.y);
    ivec3 cell=ivec3(int(gl_FragCoord.x),row/95,row%95);
    vec4 geometry;int sourceIndex,recordIndex;
    bool ready=receiverRunCell(probeHeaders,probeRanges,probeCells,probeSize,probeRecords,cell,geometry,sourceIndex,recordIndex);
    gl_FragColor=!ready?vec4(-99.0):probeMode==0?geometry:vec4(float(sourceIndex),float(recordIndex),1.0,1.0);
}
)";
    GLuint program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"receiver-run-lookup");
    constexpr int width=95,depth=95,height=36,records=width*depth*7,rows=(records+255)/256;
    std::vector<float> headers(width*depth*4,0),ranges(256*rows*4,0),cells(ranges.size(),0);
    const int first[7]={0,10,11,29,30,31,32},length[7]={10,1,18,1,1,1,4};
    const float kind[7]={0,3,2,4,4,5,0},level[7]={0,0,0,1.8888889f,.8888889f,-.1111111f,0};
    for(int z=0;z<depth;z++)for(int x=0;x<width;x++) {
        int column=x+width*z;headers[column*4]=column*7;headers[column*4+1]=7;
        for(int run=0;run<7;run++) {
            int offset=(column*7+run)*4;
            ranges[offset]=first[run];ranges[offset+1]=length[run];
            ranges[offset+2]=run==1?x+width*(10*depth+z):-1;
            cells[offset]=kind[run];cells[offset+1]=level[run];
            if(run>=3 && run<=5)cells[offset+2]=cells[offset+3]=1;
        }
    }
    std::vector<float> source(cells.size(),0),sun(cells.size(),0),faces(cells.size(),0);
    for(int column=0;column<width*depth;column++) {
        int offset=(column*7+1)*4;
        source[offset]=.75f;source[offset+3]=1;sun[offset]=.1f;sun[offset+3]=1;
        faces[offset+1]=1;faces[offset+3]=1;
    }
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glUseProgram(program);
    for(int unit=0;unit<7;unit++) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        int textureWidth=unit==0?width:unit==3?width:256;
        int textureHeight=unit==0?depth:unit==3?height*depth:rows;
        const float* data=unit==0?headers.data():unit==1?ranges.data():unit==2?cells.data()
            :unit==4?source.data():unit==5?sun.data():unit==6?faces.data():nullptr;
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,textureWidth,textureHeight,0,GL_RGBA,GL_FLOAT,data);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    }
    glUniform1i(glGetUniformLocation(program,"probeHeaders"),0);
    glUniform1i(glGetUniformLocation(program,"probeRanges"),1);
    glUniform1i(glGetUniformLocation(program,"probeCells"),2);
    glUniform3i(glGetUniformLocation(program,"probeSize"),width,height,depth);
    glUniform1i(glGetUniformLocation(program,"probeRecords"),records);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunHeaders"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunRanges"),1);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverCells"),2);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverSource"),4);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverSun"),5);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverFaces"),6);
    glUniform3i(glGetUniformLocation(program,"aqualumenReceiverSize"),width,height,depth);
    glUniform3f(glGetUniformLocation(program,"aqualumenReceiverOrigin"),0,0,0);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunCount"),records);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunMode"),1);
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),2);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[3],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("Receiver run framebuffer incomplete");
    glViewport(0,0,width,height*depth);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_SCISSOR_TEST);
    auto draw=[&]() { glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd(); };
    std::vector<float> pixels(width*height*depth*4);
    for(int mode=0;mode<2;mode++) {
        glUniform1i(glGetUniformLocation(program,"probeMode"),mode);draw();
        glReadPixels(0,0,width,height*depth,GL_RGBA,GL_FLOAT,pixels.data());
        for(int y=0;y<height;y++)for(int z=0;z<depth;z++)for(int x=0;x<width;x++) {
            int run=0;while(run<6 && y>=first[run+1])run++;
            int offset=(x+width*(y*depth+z))*4,column=x+width*z;
            std::array<float,4> expected=mode==0?std::array<float,4>{kind[run],level[run],run>=3&&run<=5?1.0f:0.0f,run>=3&&run<=5?1.0f:0.0f}
                :std::array<float,4>{run==1?float(x+width*(10*depth+z)):-1.0f,float(column*7+run),1,1};
            for(int channel=0;channel<4;channel++)if(pixels[offset+channel]!=expected[channel])
                throw std::runtime_error("Receiver run dense reconstruction/source address mismatch");
        }
    }
    glEnable(GL_SCISSOR_TEST);glScissor(0,0,1,1);
    auto reject=[&]() {
        draw();std::array<float,4> result;glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,result.data());
        for(float value:result)if(value!=-99)throw std::runtime_error("Malformed receiver run admitted");
    };
    auto upload=[&](int unit,const std::vector<float>& data,int textureWidth,int textureHeight) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,textureWidth,textureHeight,GL_RGBA,GL_FLOAT,data.data());
    };
    headers[0]=.5f;upload(0,headers,width,depth);reject();
    headers[0]=0;headers[1]=65;upload(0,headers,width,depth);reject();
    headers[1]=7;upload(0,headers,width,depth);
    ranges[1]=0;upload(1,ranges,256,rows);reject();
    ranges[1]=10;ranges[2]=0;upload(1,ranges,256,rows);reject();
    ranges[2]=-1;upload(1,ranges,256,rows);
    cells[0]=7;upload(2,cells,256,rows);reject();
    cells[0]=std::numeric_limits<float>::quiet_NaN();upload(2,cells,256,rows);reject();
    cells[0]=0;upload(2,cells,256,rows);
    glUniform1i(glGetUniformLocation(program,"probeRecords"),0);reject();
    glUniform1i(glGetUniformLocation(program,"probeRecords"),records);
    glUniform3i(glGetUniformLocation(program,"probeSize"),96,height,depth);reject();
    glUniform3i(glGetUniformLocation(program,"probeSize"),width,height,depth);
    const float rayX=std::sqrt(.75f),originY=28.4f,travel=(originY-11.0f)/.5f;
    const float hitX=47.5f+rayX*travel;
    glUniform3f(glGetUniformLocation(program,"probeOrigin"),47.5f,originY,47.5f);
    glUniform3f(glGetUniformLocation(program,"probeDirection"),rayX,-.5f,0);
    glUniform1i(glGetUniformLocation(program,"probeMode"),2);
    auto result=[&]() { draw();std::array<float,4> value;glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,value.data());return value; };
    auto reflected=result();
    const std::string clarityToken="#define WATER_CLARITY ";
    auto clarityAt=fragment.find(clarityToken);
    if(clarityAt==std::string::npos)throw std::runtime_error("Run probe water clarity unavailable");
    float clarity=std::stof(fragment.substr(clarityAt+clarityToken.size()));
    float expected=.75f*std::exp(-.32f*travel/clarity);
    if(std::abs(reflected[0]-expected)>1e-5f || reflected[1]!=0 || reflected[2]!=0 || std::abs(reflected[3]-travel)>1e-4f)
        throw std::runtime_error("Compressed distant floor source/Beer/travel mismatch");
    glUniform1i(glGetUniformLocation(program,"probeMode"),3);
    auto point=result();
    if(std::abs(point[0]-hitX)>1e-4f || std::abs(point[1]-11)>1e-4f || point[2]!=47.5f || point[3]!=1 || hitX-47.5f<=16)
        throw std::runtime_error("Compressed distant floor point or beyond-old-window sensitivity mismatch");
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunMode"),0);reject();
    glUniform1i(glGetUniformLocation(program,"aqualumenReceiverRunMode"),1);
    int floorOffset=((int(hitX)+width*47)*7+1)*4;
    source[floorOffset+3]=0;upload(4,source,256,rows);reject();
    source[floorOffset+3]=1;upload(4,source,256,rows);
    sun[floorOffset+3]=0;upload(5,sun,256,rows);reject();
    sun[floorOffset+3]=1;upload(5,sun,256,rows);
    faces[floorOffset+1]=-1;upload(6,faces,256,rows);reject();
    faces[floorOffset+1]=1;upload(6,faces,256,rows);
    int obstacleOffset=((67+width*47)*7+2)*4;
    cells[obstacleOffset]=0;upload(2,cells,256,rows);reject();
    for(int tag=1;tag<=9;tag++) {
        cells[obstacleOffset+1]=float(tag);upload(2,cells,256,rows);reject();
    }
    cells[obstacleOffset+1]=0;
    cells[obstacleOffset]=3;upload(2,cells,256,rows);reject();
    source[obstacleOffset]=.75f;source[obstacleOffset+3]=1;
    sun[obstacleOffset+3]=1;faces[obstacleOffset]=-1;faces[obstacleOffset+3]=1;
    upload(4,source,256,rows);upload(5,sun,256,rows);upload(6,faces,256,rows);reject();
    cells[obstacleOffset]=0;cells[obstacleOffset+1]=8;upload(2,cells,256,rows);reject();
    cells[obstacleOffset]=3;cells[obstacleOffset+1]=0;upload(2,cells,256,rows);
    glUniform1i(glGetUniformLocation(program,"probeMode"),4);
    auto blocker=result();
    if(blocker[0]!=1 || blocker[1]!=0 || std::abs(blocker[2]-(67.0f-47.5f)/rayX)>1e-4f || blocker[3]!=-1)
        throw std::runtime_error("Merged unlit opaque run did not remain authoritative first geometry");
    glUniform1i(glGetUniformLocation(program,"probeMode"),3);
    cells[obstacleOffset]=2;upload(2,cells,256,rows);
    glUniform3f(glGetUniformLocation(program,"probeOrigin"),1.5f,originY,47.5f);
    glUniform3f(glGetUniformLocation(program,"probeDirection"),std::sqrt(.99f),-.1f,0);reject();
    glDisable(GL_SCISSOR_TEST);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"PASS GPU receiver run lookup: all 324900 supplied cells and opaque source addresses exact; fractional/count/range/nonopaque-source/unsupported/nonfinite/disabled/extent negatives; not live capture or source shading\n";
    std::cout<<"PASS GPU compressed DDA: supplied red floor beyond old horizontal window, independent point/travel/Beer; merged unlit solid remains first known geometry even with forged ready channels; unknown subtype tags reject even with forged ready channels; dense-mode/source/Sun/face/unknown/48m negatives; not Minecraft source ownership or visual acceptance\n";
}
#endif
