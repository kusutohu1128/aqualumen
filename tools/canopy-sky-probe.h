// Exercise the pack's prepare2 sky transport with explicit geometry and directional environment radiance.
namespace aqualumenCanopy {
void probe(const fs::path& root) {
    const GLuint program=compute(root/"prepare2.csh",root);
    glUseProgram(program);
    GLuint textures[3];
    glGenTextures(3,textures);
    const auto storage=[&](int unit,GLenum format,int width,int height) {
        glActiveTexture(GL_TEXTURE0+unit);
        glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexStorage2D(GL_TEXTURE_2D,1,format,width,height);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    };
    storage(0,GL_R32F,512,2048);
    storage(1,GL_RGBA32F,64,74);
    storage(2,GL_RG32F,198,1090);
    const float meter[2]={.57f,1729.f};
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RG,GL_FLOAT,meter);
    glBindImageTexture(0,textures[2],0,GL_FALSE,0,GL_WRITE_ONLY,GL_RG32F);
    glUniform1i(glGetUniformLocation(program,"lampExposureImage"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenLightField"),0);
    glUniform1i(glGetUniformLocation(program,"colortex11"),1);
    glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    using RGB=std::array<float,3>;
    std::vector<float> cells(64*64*64),sky(64*2*4,0);
    const auto environment=[&](const RGB& east,const RGB& west,const RGB& lower) {
        for(int i=0;i<32;i++) {
            const double ring=i/8,shift=ring*.61803399;
            double angle=.7853981634*(i%8+.19+shift-std::floor(shift));
            RGB upper=std::cos(angle)>0?east:west;
            for(int channel=0;channel<3;channel++) {
                sky[(6+i)*4+channel]=upper[channel];
                sky[(64+6+i)*4+channel]=lower[channel];
            }
        }
        glActiveTexture(GL_TEXTURE1);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,2,GL_RGBA,GL_FLOAT,sky.data());
    };
    const auto dispatch=[&](float cameraX) {
        glActiveTexture(GL_TEXTURE0);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,512,GL_RED,GL_FLOAT,cells.data());
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),cameraX,0,0);
        glDispatchCompute(33,17,17);
        glMemoryBarrier(GL_TEXTURE_UPDATE_BARRIER_BIT|GL_TEXTURE_FETCH_BARRIER_BIT|GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Canopy sky probe dispatch failed");
    };
    const auto read=[&](int vertexX,int face) {
        std::array<float,2> value{};
        glGetTextureSubImage(textures[2],0,vertexX+33*face,1+16+33*16,0,1,1,1,GL_RG,GL_FLOAT,
                             sizeof(value),value.data());
        if(value[0]<1) throw std::runtime_error("Canopy sky probe read an unwritten vertex");
        const int packed=int(value[0])-1;
        return RGB{float(packed&2047)/2047.f,float(packed>>11)/2047.f,value[1]};
    };
    const auto near=[&](const char* label, RGB actual,RGB expected,float tolerance=.003f) {
        std::cout<<label<<": "<<actual[0]<<", "<<actual[1]<<", "<<actual[2]<<'\n';
        for(int i=0;i<3;i++) if(!(std::abs(actual[i]-expected[i])<=tolerance))
            throw std::runtime_error(std::string("Incorrect directional sky: ")+label);
    };
    const RGB white{1,1,1},black{0,0,0},redSky{4,1,.5},blueSky{.5,1,4};
    environment(redSky,blueSky,black);
    dispatch(0);
    near("Open sky",read(16,3),white);
    auto wall=[&](int x) {
        for(int y=32;y<46;y++) for(int z=18;z<46;z++) cells[x+64*(z+64*y)]=1;
    };
    wall(32);
    dispatch(0);
    near("Eastern wall below warm eastern sky",read(16,3),{1.f/9,.5,8.f/9});
    near("Face looking away from the eastern wall",read(16,0),white);
    near("Face looking into the eastern wall",read(16,1),black);
    environment(blueSky,redSky,white);
    dispatch(0);
    near("Same wall, sky colours exchange sides",read(16,3),{8.f/9,.5,1.f/9});
    // An upper-hemisphere obstruction does not absorb the separate lower environment.
    RGB lower=read(16,1);
    if(!(lower[0]>.6 && lower[2]<.3 && lower[1]>.48 && lower[1]<.52))
        throw std::runtime_error("Canopy lost lower-hemisphere radiance");
    environment(white,white,black);
    auto roof=[&](int material) {
        std::fill(cells.begin(),cells.end(),0);
        for(int x=18;x<46;x++) for(int z=18;z<46;z++) cells[x+64*(z+64*33)]=material;
    };
    roof(1);
    dispatch(0);
    near("Full roof",read(16,3),black);
    roof(2);
    dispatch(0);
    auto leaves=read(16,3);
    // A horizontal homogeneous metre transmits exp(-1.45/cos(theta)).
    double integral=0;
    for(int i=0;i<10000;i++) {
        double mu=(i+.5)/10000;
        integral+=2*mu*std::exp(-1.45/mu)/10000;
    }
    float value=static_cast<float>(integral);
    near("Single leaf layer against dense angular integral",leaves,{value,value,value},.014);
    roof(30); // red stained glass from the pack's material table
    dispatch(0);
    RGB glass=read(16,3);
    if(!(glass[0]>.6 && glass[1]<.2 && glass[2]<.15))
        throw std::runtime_error("Canopy lost red-glass selectivity");
    std::fill(cells.begin(),cells.end(),0);
    wall(32);
    dispatch(7.875f);
    auto before=read(9,3); // world lattice vertex 0, cell address 32
    std::fill(cells.begin(),cells.end(),0);
    wall(24);              // captured field shifts eight blocks with the camera
    dispatch(8.125f);
    near("Fixed world vertex across camera grid shift",read(8,3),before,.0001);
    near("Grid shift exercises a half-occluded vertex",before,{.5,.5,.5});
    roof(0);
    dispatch(0);
    near("Removed roof",read(16,3),white);
    float meterAfter[2]={};
    glGetTextureSubImage(textures[2],0,0,0,0,1,1,1,GL_RG,GL_FLOAT,sizeof(meterAfter),meterAfter);
    if(meterAfter[0]!=meter[0] || meterAfter[1]!=meter[1]) throw std::runtime_error("Canopy overwrote eye adaptation");
    glDeleteProgram(program);
    glDeleteTextures(3,textures);
    std::cout<<"PASS canopy sky transport, direction, geometry and camera continuity\n";
}
}

namespace aqualumenCanopy {
void probeColumns(const fs::path& root) {
    namespace LL=aqualumenLocalLights;
    LL::World world;
    world.init(root);
    const std::string body="#version 430 compatibility\n"
        +expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)
        +expand(root/"lib/canopy_receiver.glsl",root)
        +"layout(local_size_x=1) in;layout(rgba32f) uniform writeonly image2D resultImage;"
         "uniform vec3 receiver; void main(){imageStore(resultImage,ivec2(0),vec4(canopyAtVertex(receiver,vec3(0,1,0)),1));}";
    const GLuint cs=compile(GL_COMPUTE_SHADER,body,"canopy-receiver-probe");
    const GLuint query=glCreateProgram();
    glAttachShader(query,cs);glLinkProgram(query);glDeleteShader(cs);
    GLint ok=0;glGetProgramiv(query,GL_LINK_STATUS,&ok);
    if(!ok) throw std::runtime_error("Far receiver probe did not link");
    const GLuint lut=LL::World::makeTexture(GL_RGBA32F,64,74);
    std::vector<float> radiance(64*2*4,0.f);
    for(int i=0;i<32;i++) {
        double ring=i/8,shift=ring*.61803399;
        const bool east=std::cos(.7853981634*(i%8+.19+shift-std::floor(shift)))>0;
        radiance[4*(6+i)]=east?4.f:.5f;
        radiance[4*(6+i)+1]=1.f;
        radiance[4*(6+i)+2]=east?.5f:4.f;
    }
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,2,GL_RGBA,GL_FLOAT,radiance.data());
    const GLuint access=LL::World::makeTexture(GL_RG32F,198,1090);
    const float nearOpen[2]={4194304,1};
    glClearTexImage(access,0,GL_RG,GL_FLOAT,nearOpen);
    const GLuint out=LL::World::makeTexture(GL_RGBA32F,1,1);
    const GLuint gather=compute(root/"prepare2.csh",root);
    using RGB=std::array<float,3>;
    auto measure=[&](const std::vector<LL::Block>& blocks,LL::D3 camera,float height,bool includeNear=false) {
        world.clearRaw();
        world.capture(blocks,camera);
        glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT);
        auto bind=[](GLuint program,int unit,const char* name,GLuint texture) {
            glActiveTexture(GL_TEXTURE0+unit);
            glBindTexture(GL_TEXTURE_2D,texture);
            glUniform1i(glGetUniformLocation(program,name),unit);
        };
        if(includeNear) {
            world.publish();
            glUseProgram(gather);
            bind(gather,0,"aqualumenLightField",world.field);
            bind(gather,3,"colortex11",lut);
            glUniform3f(glGetUniformLocation(gather,"cameraPosition"),float(camera[0]),float(camera[1]),float(camera[2]));
            glBindImageTexture(6,access,0,GL_FALSE,0,GL_WRITE_ONLY,GL_RG32F);
            glUniform1i(glGetUniformLocation(gather,"lampExposureImage"),6);
            glDispatchCompute(33,17,17);
            glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT|GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
        }
        glUseProgram(query);
        bind(query,3,"colortex11",lut);
        bind(query,4,"aqualumenRawIndex",world.index);
        bind(query,5,"aqualumenLampExposure",access);
        glBindImageTexture(6,out,0,GL_FALSE,0,GL_WRITE_ONLY,GL_RGBA32F);
        glUniform1i(glGetUniformLocation(query,"resultImage"),6);
        glUniform3f(glGetUniformLocation(query,"cameraPosition"),float(camera[0]),float(camera[1]),float(camera[2]));
        glUniform3f(glGetUniformLocation(query,"receiver"),48.f-camera[0],height-camera[1],-camera[2]);
        glDispatchCompute(1,1,1);
        glMemoryBarrier(GL_TEXTURE_UPDATE_BARRIER_BIT);
        std::array<float,4> value;
        glGetTextureSubImage(out,0,0,0,0,1,1,1,GL_RGBA,GL_FLOAT,sizeof(value),value.data());
        if(value[3]!=1.f || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Far receiver readback failed");
        return RGB{value[0],value[1],value[2]};
    };
    auto near=[](const char* name,RGB actual,RGB expected,float tolerance) {
        std::cout<<name<<": "<<actual[0]<<", "<<actual[1]<<", "<<actual[2]<<'\n';
        for(int i=0;i<3;i++) if(!(std::abs(actual[i]-expected[i])<=tolerance))
            throw std::runtime_error(std::string("Far sky mismatch: ")+name);
    };
    const RGB white{1,1,1},black{0,0,0};
    const LL::D3 camera={0,0,0};
    std::vector<LL::Block> roof;
    auto addRoof=[&](bool half,bool leaves,int y) {
        roof.clear();
        for(int x=half?48:34;x<62;x++) for(int z=-14;z<14;z++)
            roof.push_back({x,y,z,leaves?10300:10001,0,leaves?1:0});
    };
    near("48 m open sky through actual terrain vertex access",measure(roof,camera,0),white,.002);
    addRoof(false,false,1);
    near("48 m solid roof captured outside lamp grid",measure(roof,camera,0),black,.002);
    for(auto& block:roof) {block.id=10114;block.level=15;}
    near("Luminous full-cube roof still blocks sky",measure(roof,camera,0),black,.002);
    for(int id:{10301,10302,10304}) {
        for(auto& block:roof) {block.id=id;block.level=0;}
        const bool slab=id!=10304;
        near(id==10301?"Wide lower slabs occupy their column":id==10302?"Wide upper slabs occupy their column":"Narrow fence posts leave the far column open",measure(roof,camera,0),slab?black:white,.002);
    }
    addRoof(true,false,1);
    const RGB asymmetric{1.f/9,.5,8.f/9};
    near("48 m solid half-roof under two-colour sky",measure(roof,camera,0),asymmetric,.002);
    near("Same roof after crossing far grid boundary",measure(roof,{16.1,0,0},0),asymmetric,.002);
    // One fixed vertex moves from the far-only solution through every part
    // of the fade to the near-only solution. Both use the same rendered blocks.
    for(double distance:{12.1,11.,10.,9.,7.9}) {
        std::string label="Same half-roof at eye distance "+std::to_string(distance);
        near(label.c_str(),measure(roof,{48.-distance,0,0},0,true),asymmetric,.002);
    }
    addRoof(false,true,1);
    near("48 m leaf roof through actual cutout capture",measure(roof,camera,0),{.12,.12,.12},.022);
    addRoof(false,false,16);
    near("Solid roof across a vertical 32-bit word boundary",measure(roof,camera,15),black,.002);
    near("Removed distant roof on next capture",measure({},camera,0),white,.002);
    glDeleteTextures(1,&lut);glDeleteTextures(1,&access);glDeleteTextures(1,&out);glDeleteProgram(query);glDeleteProgram(gather);
    std::cout<<"PASS far canopy capture, angular response, clearing and world anchoring\n";
}
}
