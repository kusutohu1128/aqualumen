// Direct Sun -> horizontal Lambertian floor -> vertical receiver, in grid metres.
namespace aqualumenGround {
void probe(const fs::path& root) {
    GLuint solar=compute(root/"prepare3.csh",root),gather=compute(root/"prepare4.csh",root);
    GLuint tex[5];glGenTextures(5,tex);
    auto storage=[&](int unit,GLenum format,int width,int height) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,tex[unit]);
        glTexStorage2D(GL_TEXTURE_2D,1,format,width,height);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    };
    storage(0,GL_R32F,512,2048);storage(1,GL_RGBA32F,64,74);
    storage(2,GL_RGBA16F,1536,aqualumenLocalLights::parseImage(aqualumenLocalLights::slurp(root/"shaders.properties"),"bounceIncidentImage").h);storage(3,GL_R32UI,768,258);
    storage(4,GL_DEPTH_COMPONENT32F,16,16);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
    const float one=1,white[4]={1,1,1,1};
    glClearTexImage(tex[4],0,GL_DEPTH_COMPONENT,GL_FLOAT,&one);
    glClearTexImage(tex[1],0,GL_RGBA,GL_FLOAT,white);
    glClearTexImage(tex[2],0,GL_RGBA,GL_FLOAT,nullptr);
    glBindImageTexture(0,tex[3],0,GL_FALSE,0,GL_READ_ONLY,GL_R32UI);
    glBindImageTexture(1,tex[2],0,GL_FALSE,0,GL_WRITE_ONLY,GL_RGBA16F);
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    auto address=[](int x,int y,int z,int face) {
        return 6*(((x-16)&31)+32*(((z-16)&31)+32*((y-16)&31)))+face;
    };
    constexpr int receivingFace=4;
    auto run=[&](const char* label,unsigned pigment,bool roof,bool wall,bool day,bool markFloor,bool flooded=false,float cameraX=0,int worldOffset=0) {
        const int shift=worldOffset-8*int(std::floor(cameraX/8));
        const int addressBark=address(32+shift,34,32,receivingFace);
        std::vector<float> cells(512*2048,0);
        std::vector<unsigned> surfaces(768*258,0);
        auto solid=[&](int x,int y,int z) {cells[x+shift+64*(z+64*y)]=1;};
        solid(32,34,32);surfaces[addressBark]=0x80ffffffu;
        for(int x=23;x<=41;x++) for(int z=23;z<=31;z++) {
            solid(x,31,z);
            if(flooded) surfaces[256*768+(x-16)+32*(z-16)]=1u<<(32-16);
            if(markFloor) surfaces[address(x+shift,31,z,3)]=0x80000000u|pigment;
            if(roof) solid(x,38,z);
            if(wall && z==31) for(int y=32;y<=36;y++) solid(x,y,z);
        }
        glTextureSubImage2D(tex[0],0,0,0,512,2048,GL_RED,GL_FLOAT,cells.data());
        glTextureSubImage2D(tex[3],0,0,0,768,258,GL_RED_INTEGER,GL_UNSIGNED_INT,surfaces.data());
        for(GLuint p:{solar,gather}) {
            glUseProgram(p);
            auto integer=[&](const char* key,int v){glUniform1i(glGetUniformLocation(p,key),v);};
            integer("bounceSurfaceImage",0);integer("bounceIncidentImage",1);
            integer("aqualumenLightField",0);integer("colortex11",1);integer("colortex6",1);
            integer("aqualumenBounceIncident",2);integer("shadowtex0",4);
            for(const char* key:{"gbufferModelViewInverse","shadowProjection","shadowModelView"})
                glUniformMatrix4fv(glGetUniformLocation(p,key),1,GL_FALSE,identity);
            glUniform3f(glGetUniformLocation(p,"cameraPosition"),cameraX,0,0);
            glUniform3f(glGetUniformLocation(p,"sunPosition"),0,day?1:-1,0);
            glDispatchCompute(96,32,1);
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT|GL_TEXTURE_FETCH_BARRIER_BIT|GL_TEXTURE_UPDATE_BARRIER_BIT);
        }
        std::array<float,4> sample{};
        glGetTextureSubImage(tex[2],0,2*(addressBark%768),1024+2*(addressBark/768),0,
                             1,1,1,GL_RGBA,GL_FLOAT,sizeof(sample),sample.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("ground-return dispatch or read failed");
        std::cout<<label<<" = "<<sample[0]<<" "<<sample[1]<<" "<<sample[2]<<" coverage tag "<<sample[3]<<'\n';
        return sample;
    };
    auto open=run("white floor",0xffffff,false,false,true,true);
    auto red=run("red floor",0x1030ff,false,false,true,true);
    auto roof=run("same red floor, blocked sunlight",0x1030ff,true,false,true,true);
    auto wall=run("white floor behind opaque wall",0xffffff,false,true,true,true);
    auto missing=run("unpublished floor",0xffffff,false,false,true,false);
    auto water=run("floor under water",0xffffff,false,false,true,true,true);
    auto night=run("same white floor, night",0xffffff,false,false,false,true);
    auto before=run("west of grid boundary",0xffffff,false,false,true,true,false,7.99f,8);
    auto after=run("east of grid boundary",0xffffff,false,false,true,true,false,8.01f,8);
    for(int c=0;c<4;c++)
        if(std::abs(before[c]-after[c])>.001 || std::abs(open[c]-after[c])>.001)
            throw std::runtime_error("A stationary face changed when the camera crossed the grid boundary");
    // Integrate projected solid angle independently over the actual rectangle.
    // Receiver is the low-x/low-y quarter of the north face. Distances over
    // nine metres have the pack's smooth hand-over to the far environment.
    double oracle=0;
    constexpr double ds=.04;
    for(double x=23+ds/2;x<42;x+=ds) for(double z=23+ds/2;z<32;z+=ds) {
        double dx=x-32.25,dz=32-z,dy=2.25,r2=dx*dx+dz*dz+dy*dy;
        double t=std::clamp((std::sqrt(r2)-9.)/3.,0.,1.);
        oracle+=ds*ds*dy*dz/(3.141592653589793*r2*r2)*(1.-t*t*(3.-2.*t));
    }
    std::cout<<"independent area integral "<<oracle<<'\n';
    if(!(std::abs(open[0]-oracle)<.045 && open[0]>.2 && std::abs(open[3]-1.-open[0])<.002 &&
         std::abs(red[0]-open[0])<.001 && std::abs(red[1]/open[1]-std::pow(48./255,2.2))<.002 &&
         std::abs(red[2]/open[2]-std::pow(16./255,2.2))<.002 &&
         roof[0]==0 && std::abs(roof[3]-open[3])<.002 && wall[0]==0 && missing[3]==1 && water[3]==1 && water[0]==0 && night[3]==0))
        throw std::runtime_error("Incorrect local sunlight transport on one or more paths");
    glDeleteTextures(5,tex);glDeleteProgram(solar);glDeleteProgram(gather);
    std::cout<<"PASS single daylight return, roof, second-leg blocker, missing surface, water and night\n";
}
}
