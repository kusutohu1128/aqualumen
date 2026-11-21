// Read the production entity vertex outputs. Off-grid points, rotating normals
// and the area integral exercise the moving receiver independently of the terrain solver.
namespace aqualumenAnimal {
using Vec=std::array<float,3>;
using Sample=std::array<float,7>;

double projectedFloor(Vec p,Vec n) {
    double sum=0;
    constexpr double step=.05;
    for(double x=-9.+step/2;x<10.;x+=step) for(double z=-9.+step/2;z<10.;z+=step) {
        const double dx=x-p[0],dy=-p[1],dz=z-p[2],rr=dx*dx+dy*dy+dz*dz;
        const double t=std::clamp((std::sqrt(rr)-9.)/3.,0.,1.);
        sum+=step*step*p[1]*std::max(0.,dx*n[0]+dy*n[1]+dz*n[2])/(3.141592653589793*rr*rr)*(1.-t*t*(3.-2.*t));
    }
    return sum;
}
void probe(const fs::path& root) {
    using World=aqualumenLocalLights::World;
    GLuint vs=compile(GL_VERTEX_SHADER,expand(root/"gbuffers_entities.vsh",root),"animal receiver");
    GLuint p=glCreateProgram();
    glAttachShader(p,vs);
    const char* varyings[]={"animalSkyAccess","animalReturn"};
    glTransformFeedbackVaryings(p,2,varyings,GL_INTERLEAVED_ATTRIBS);
    glLinkProgram(p);
    GLint ok;
    glGetProgramiv(p,GL_LINK_STATUS,&ok);
    if(!ok) {char log[4096];glGetProgramInfoLog(p,sizeof(log),nullptr,log);throw std::runtime_error(log);}
    glUseProgram(p);
    GLuint textures[6];
    const GLenum formats[]={GL_R32F,GL_RG32F,GL_RGBA16F,GL_R32UI,GL_RGBA32F,GL_R32UI};
    const int incidentHeight=aqualumenLocalLights::parseImage(aqualumenLocalLights::slurp(root/"shaders.properties"),"bounceIncidentImage").h;
    const int widths[]={512,198,1536,768,64,16},heights[]={2048,1090,incidentHeight,258,74,104};
    for(int i=0;i<6;i++) {
        glActiveTexture(GL_TEXTURE0+i);
        textures[i]=World::makeTexture(formats[i],widths[i],heights[i]);
        const bool integer=formats[i]==GL_R32UI;
        glClearTexImage(textures[i],0,integer?GL_RED_INTEGER:GL_RED,integer?GL_UNSIGNED_INT:GL_FLOAT,nullptr);
    }
    for(auto name:{"aqualumenDoorMask","aqualumenRawIndex"}) World::imageUnit(p,name,5);
    World::imageUnit(p,"aqualumenLightField",0);
    World::imageUnit(p,"aqualumenLampExposure",1);
    World::imageUnit(p,"aqualumenBounceIncident",2);
    World::imageUnit(p,"bounceSurfaceImage",0);
    World::imageUnit(p,"colortex11",4);
    glBindImageTexture(0,textures[3],0,GL_FALSE,0,GL_READ_ONLY,GL_R32UI);
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    glUniformMatrix4fv(glGetUniformLocation(p,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    const auto uniform=[&](const char* key,Vec v){glUniform3fv(glGetUniformLocation(p,key),1,v.data());};
    uniform("sunPosition",{0,1,0});
    std::vector<float> field(512*512),sky(2*198*1090);
    for(int x=23;x<42;x++) for(int z=23;z<42;z++) field[x+64*(z+64*31)]=1;
    glTextureSubImage2D(textures[0],0,0,0,512,512,GL_RED,GL_FLOAT,field.data());
    const float floor[]={1,.25,.0625,1};
    glClearTexImage(textures[2],0,GL_RGBA,GL_FLOAT,floor);
    // The lower hemisphere is bluer than either horizontal sky direction.
    float environment[6][4];
    for(int face=0;face<6;face++) for(int c=0;c<4;c++)
        environment[face][c]=(face==2 && c==2)?3.f:(face==1 && c==0)?2.f:1.f;
    glTextureSubImage2D(textures[4],0,0,0,6,1,GL_RGBA,GL_FLOAT,environment);
    // Linear horizontal sky gradient; one face sees less than the other.
    for(int vertex=0;vertex<33;vertex++) for(int face=0;face<6;face++) {
        float value=(float(vertex)/32.f)*(face==1?.25f:.75f);
        int q=int(std::round(value*2047));
        for(int row=1;row<1090;row++) {
            int off=2*(row*198+face*33+vertex);
            sky[off]=float(1+q+2048*q);
            sky[off+1]=value;
        }
    }
    glTextureSubImage2D(textures[1],0,0,0,198,1090,GL_RG,GL_FLOAT,sky.data());
    GLuint feedback;
    glGenBuffers(1,&feedback);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,feedback);
    glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,sizeof(Sample),nullptr,GL_STREAM_READ);
    glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,feedback);
    glEnable(GL_RASTERIZER_DISCARD);
    const auto draw=[&](int id,Vec position,Vec normal) {
        glUniform1i(glGetUniformLocation(p,"entityId"),id);
        glNormal3fv(normal.data());
        glBeginTransformFeedback(GL_POINTS);
        glBegin(GL_POINTS);glVertex3fv(position.data());glEnd();
        glEndTransformFeedback();
        Sample out;
        glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,sizeof(out),out.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Entity feedback draw failed");
        return out;
    };
    const auto near=[](double measured,double expected,double tolerance) {
        if(!(std::abs(measured-expected)<=tolerance))
            throw std::runtime_error("Animal light measured "+std::to_string(measured)+" vs "+std::to_string(expected));
    };
    const Vec point={.37f,1.31f,-.28f};
    for(Vec n:{Vec{0,-1,0},Vec{1,0,0},Vec{-.6f,-.8f,0},Vec{0,.6f,.8f},Vec{0,1,0}}) {
        Sample s=draw(21000,point,n);
        double oracle=projectedFloor(point,n);
        float ramp=(point[0]+16.f)/32.f;
        Vec access={};
        for(int c=0;c<3;c++) {
            double open=0,visible=0;
            for(int axis=0;axis<3;axis++) {
                int face=2*axis+int(n[axis]>0);
                double energy=n[axis]*n[axis]*environment[face][c];
                open+=energy;
                visible+=energy*(face==2?1.:ramp*(face==1?.25:.75));
            }
            access[c]=visible/open;
        }
        std::cout<<"animal normal "<<n[0]<<","<<n[1]<<","<<n[2]<<" sky "<<s[0]<<" ground "<<s[3]<<" integral "<<oracle<<'\n';
        for(int i=0;i<3;i++) {near(s[i],access[i],.001);near(s[3+i],oracle*floor[i],.028*floor[i]);}
        near(s[6],s[3],.0001);
    }
    const auto first=draw(21000,point,{1,0,0});
    const auto moved=draw(21000,{point[0]+.5f,point[1],point[2]},{1,0,0});
    near(moved[0]-first[0],.5*.25/32.,.0003);
    const auto player=draw(21001,point,{1,0,0});
    for(int i=0;i<7;i++) near(player[i],first[i],.00001);
    const auto outside=draw(21002,point,{1,0,0});
    for(int i=0;i<7;i++) near(outside[i],i<3?1.:0.,.00001);
    const unsigned water=1u<<18;
    int column=16+32*15;
    glTextureSubImage2D(textures[3],0,column%768,256+column/768,1,1,GL_RED_INTEGER,GL_UNSIGNED_INT,&water);
    const auto immersed=draw(21000,point,{1,0,0});
    for(int i=3;i<7;i++) near(immersed[i],0,.00001);
    glClearTexImage(textures[3],0,GL_RED_INTEGER,GL_UNSIGNED_INT,nullptr);
    uniform("sunPosition",{0,-1,0});
    const auto night=draw(21000,point,{1,0,0});
    for(int i=3;i<7;i++) near(night[i],0,.00001);
    glUniform1i(glGetUniformLocation(p,"aqualumenDimension"),-1);
    const auto nether=draw(21000,point,{1,0,0});
    for(int i=0;i<7;i++) near(nether[i],i<3?1.:0.,.00001);
    glDisable(GL_RASTERIZER_DISCARD);
    glDeleteBuffers(1,&feedback);glDeleteTextures(6,textures);glDeleteProgram(p);glDeleteShader(vs);
    std::cout<<"PASS moving mesh sky, reflected ground, unlisted draws, wet column, night and dimension\n";
}
}
