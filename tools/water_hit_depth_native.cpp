#define main aqualumen_paired_native_unused_main
#include "water_paired_native.cpp"
#undef main

struct DepthCapture {
    std::array<std::vector<float>,8> color;
    std::vector<float> depth;
};

struct DepthFixture {
    Fixture base;
    std::array<GLuint,7> extra={};
    explicit DepthFixture() {
        base.projection[0]*=3;base.projection[5]*=3;
        const float a=base.projection[10],b=base.projection[14];
        base.inverseProjection={1/base.projection[0],0,0,0,0,1/base.projection[5],0,0,0,0,0,1/b,0,0,-1,a/b};
        for(int r=0;r<4;++r)for(int c=0;c<4;++c) {
            double product=0;for(int k=0;k<4;++k)product+=double(base.projection[k*4+r])*base.inverseProjection[c*4+k];
            require(std::abs(product-(r==c?1:0))<2e-6,"native projection inverse is not identity");
        }
        std::cout<<"projection_inverse_identity=1\n";
        glGenTextures(extra.size(),extra.data());
        for(int i=0;i<7;++i) {
            glActiveTexture(GL_TEXTURE15);glBindTexture(GL_TEXTURE_2D,extra[i]);
            for(GLenum p:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,p,GL_NEAREST);
            if(i<6) {
                glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,side,side,0,GL_RGBA,GL_FLOAT,nullptr);
                glBindFramebuffer(GL_FRAMEBUFFER,base.framebuffer);
                glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT2+i,GL_TEXTURE_2D,extra[i],0);
            }else glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,side,side,0,GL_DEPTH_COMPONENT,GL_FLOAT,nullptr);
        }
        glBindFramebuffer(GL_FRAMEBUFFER,base.framebuffer);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,extra[6],0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"eight MRT depth framebuffer incomplete");
    }
    ~DepthFixture(){glDeleteTextures(extra.size(),extra.data());}
    DepthCapture draw(GLuint p,const std::vector<float>& opaque,float material=10000,bool underwater=true,bool known=true,bool paired=true) {
        require(opaque.size()==pixels,"opaque dimensions");
        for(GLuint texture:{base.textures[3],extra[6]}) {
            glActiveTexture(GL_TEXTURE15);glBindTexture(GL_TEXTURE_2D,texture);
            glTexSubImage2D(GL_TEXTURE_2D,0,0,0,side,side,GL_DEPTH_COMPONENT,GL_FLOAT,opaque.data());
        }
        base.uniforms(p,0,underwater);
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(base.projection.data());
        glMatrixMode(GL_MODELVIEW);glLoadMatrixf(base.view.data());
        glUniform1i(glGetUniformLocation(p,"aqualumenBathymetryReady"),known?1:0);
        glBindFramebuffer(GL_FRAMEBUFFER,base.framebuffer);
        std::array<GLenum,8> draws;
        const float sentinel[4]={.25f,.375f,.5f,1},zero[4]={};
        for(int i=0;i<8;++i)draws[i]=GL_COLOR_ATTACHMENT0+i;
        glDrawBuffers(draws.size(),draws.data());
        for(int i=0;i<8;++i){glClearBufferfv(GL_COLOR,i,i?zero:sentinel);glDisablei(GL_BLEND,i);}
        glDrawBuffers(paired?8:1,draws.data());
        glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glDepthMask(GL_TRUE);glDepthRange(0,1);
        glVertexAttrib4f(10,material,0,0,0);
        const float extent=material==10000?.5f:2.0f;
        const std::array<std::array<float,3>,4> vertices={{{-extent,3.25f,-extent},{-extent,3.25f,extent},{extent,3.25f,extent},{extent,3.25f,-extent}}};
        glBegin(GL_TRIANGLES);for(int i:{0,1,2,0,2,3})glVertex3fv(vertices[i].data());glEnd();
        DepthCapture c;
        for(int i=0;i<8;++i) {
            c.color[i].resize(pixels*4);glReadBuffer(draws[i]);
            glReadPixels(0,0,side,side,GL_RGBA,GL_FLOAT,c.color[i].data());
            for(float v:c.color[i])require(std::isfinite(v),"nonfinite eight MRT value");
        }
        c.depth.resize(pixels);glReadPixels(0,0,side,side,GL_DEPTH_COMPONENT,GL_FLOAT,c.depth.data());
        std::vector<float> immutableOpaque(pixels);
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,base.textures[3]);
        glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT,immutableOpaque.data());
        require(equal(opaque,immutableOpaque),"opaque depth snapshot changed");
        require(glGetError()==GL_NO_ERROR,"depth fixture GL error");return c;
    }
    std::vector<float> composite(GLuint p) {
        GLuint framebuffer=0;std::array<GLuint,2> textures={};
        glGenFramebuffers(1,&framebuffer);glGenTextures(textures.size(),textures.data());
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        for(int i=0;i<2;++i) {
            glActiveTexture(GL_TEXTURE15);glBindTexture(GL_TEXTURE_2D,textures[i]);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,side,side,0,GL_RGBA,GL_FLOAT,nullptr);
            glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,textures[i],0);
        }
        const GLenum targets[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,targets);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"composite depth framebuffer incomplete");
        base.uniforms(p,0,true);
        glUniform1i(glGetUniformLocation(p,"colortex0"),12);glActiveTexture(GL_TEXTURE12);glBindTexture(GL_TEXTURE_2D,base.textures[12]);
        glUniform1i(glGetUniformLocation(p,"depthtex0"),14);glActiveTexture(GL_TEXTURE14);glBindTexture(GL_TEXTURE_2D,extra[6]);
        std::vector<float> sampledDepth(pixels);glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT,sampledDepth.data());
        std::array<float,16> actualInverse={};glGetUniformfv(p,glGetUniformLocation(p,"gbufferProjectionInverse"),actualInverse.data());
        std::cout<<"composite_bound_depth_center="<<sampledDepth[pixels/2]<<" inverse_projection_coefficients="
            <<actualInverse[0]<<','<<actualInverse[5]<<','<<actualInverse[11]<<','<<actualInverse[14]<<','<<actualInverse[15]<<'\n';
        glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisablei(GL_BLEND,0);glDisablei(GL_BLEND,1);
        glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
        glBegin(GL_QUADS);for(auto uv:std::array<std::array<float,2>,4>{{{{0,0}},{{1,0}},{{1,1}},{{0,1}}}}) {
            glMultiTexCoord2f(GL_TEXTURE0,uv[0],uv[1]);glVertex2f(uv[0]*2-1,uv[1]*2-1);
        }glEnd();
        std::vector<float> values(pixels*4);glReadBuffer(GL_COLOR_ATTACHMENT1);glReadPixels(0,0,side,side,GL_RGBA,GL_FLOAT,values.data());
        require(glGetError()==GL_NO_ERROR,"composite distance GL error");
        glDeleteTextures(textures.size(),textures.data());glDeleteFramebuffers(1,&framebuffer);return values;
    }
    double window(const std::vector<float>& point,int pixel)const {
        std::array<double,4> p={point[pixel*4],point[pixel*4+1],point[pixel*4+2],1},v={},clip={};
        for(int r=0;r<4;++r)for(int c=0;c<4;++c)v[r]+=base.view[c*4+r]*p[c];
        for(int r=0;r<4;++r)for(int c=0;c<4;++c)clip[r]+=base.projection[c*4+r]*v[c];
        return .5*(clip[2]/clip[3]+1);
    }
};

int main(int argc,char** argv) {
    try {
        require(argc==6,"usage: water-hit-depth-native BASE_CONTROL_ROOT BASE_PAIRED_ROOT CANDIDATE_CONTROL_ROOT CANDIDATE_PAIRED_ROOT NEW_OUTPUT");
        fs::path baseControl=argv[1],base=argv[2],candidateControl=argv[3],candidate=argv[4],out=argv[5];
        require(!fs::exists(out),"depth output exists");fs::create_directories(out);
        Context context;DepthFixture fixture;
        const auto old=program(source(base/"gbuffers_water.vsh",base),source(base/"gbuffers_water.fsh",base)),
            fixed=program(source(candidate/"gbuffers_water.vsh",candidate),source(candidate/"gbuffers_water.fsh",candidate)),
            composite=program(source(candidate/"composite.vsh",candidate),source(candidate/"composite.fsh",candidate)),
            oldControl=program(source(baseControl/"gbuffers_water.vsh",baseControl),source(baseControl/"gbuffers_water.fsh",baseControl)),
            fixedControl=program(source(candidateControl/"gbuffers_water.vsh",candidateControl),source(candidateControl/"gbuffers_water.fsh",candidateControl));
        const std::vector<float> clear(pixels,1);
        const auto before=fixture.draw(old,clear),after=fixture.draw(fixed,clear);
        const auto baselinePassive=fixture.draw(oldControl,clear,10000,true,true,false),
            candidatePassive=fixture.draw(fixedControl,clear,10000,true,true,false);
        require(equal(before.color[0],baselinePassive.color[0])&&equal(before.depth,baselinePassive.depth),"baseline eight MRT passivity");
        require(equal(after.color[0],candidatePassive.color[0])&&equal(after.depth,candidatePassive.depth),"candidate eight MRT passivity");
        const auto transport=fixture.composite(composite);
        raw(out/"old-depth.r32f",before.depth);raw(out/"candidate-depth.r32f",after.depth);
        raw(out/"candidate-point.rgba32f",after.color[4]);raw(out/"composite-transport.rgba32f",transport);
        int active=0,oldMismatch=0,newMismatch=0,distanceMismatch=0,transmissionMismatch=0;
        double maxDepth=0,maxDistance=0,maxTransmission=0;
        std::vector<float> straddle(pixels,1);int farther=0,nearer=0;
        for(int i=0;i<pixels;++i) {
            const int a=i*4;if(after.color[1][a+3]!=1||after.color[4][a+3]<0)continue;
            ++active;const double z=fixture.window(after.color[4],i),raster=fixture.window(after.color[2],i);
            oldMismatch+=std::abs(before.depth[i]-z)>2e-7;
            const double error=std::abs(after.depth[i]-z);maxDepth=std::max(maxDepth,error);newMismatch+=error>2e-7;
            const double x=after.color[4][a],y=after.color[4][a+1],zz=after.color[4][a+2],distance=std::sqrt(x*x+y*y+zz*zz);
            const double derror=std::abs(transport[a]-distance);maxDistance=std::max(maxDistance,derror);distanceMismatch+=derror>5e-5;
            for(int c=0;c<3;++c) {
                const double sigma[3]={.32,.085,.035},expected=std::exp(-sigma[c]*transport[a]);
                const double terror=std::abs(transport[a+1+c]-expected);maxTransmission=std::max(maxTransmission,terror);transmissionMismatch+=terror>3e-7;
            }
            if(std::abs(z-raster)>2e-6) {
                straddle[i]=float((z+raster)*.5);if(z>raster)++farther;else ++nearer;
            }
        }
        std::cout<<"active="<<active<<" old_depth_mismatch="<<oldMismatch<<" candidate_depth_mismatch="<<newMismatch
            <<" distance_mismatch="<<distanceMismatch<<" transmission_mismatch="<<transmissionMismatch
            <<" max_depth_error="<<maxDepth<<" max_distance_error="<<maxDistance<<" max_transmission_error="<<maxTransmission<<'\n';
        require(active>1000&&oldMismatch>100&&newMismatch==0&&distanceMismatch==0&&transmissionMismatch==0,"primary depth/distance fail-first regression");
        require(farther>10&&nearer>10,"both opaque straddle directions must be nonvacuous");
        const auto oldOccluded=fixture.draw(old,straddle),newOccluded=fixture.draw(fixed,straddle);
        int oldWrong=0,newWrong=0;
        for(int i=0;i<pixels;++i)if(straddle[i]<1) {
            const int a=i*4;const bool expectWater=fixture.window(after.color[4],i)<=straddle[i];
            oldWrong+=(oldOccluded.color[1][a+3]==1)!=expectWater;
            newWrong+=(newOccluded.color[1][a+3]==1)!=expectWater;
            const double expectedDepth=expectWater?fixture.window(after.color[4],i):straddle[i];
            require(std::abs(newOccluded.depth[i]-expectedDepth)<=2e-7,"straddle stored wrong depth");
        }
        std::cout<<"optical_farther_straddles="<<farther<<" optical_nearer_straddles="<<nearer
            <<" old_occlusion_wrong="<<oldWrong<<" candidate_occlusion_wrong="<<newWrong<<'\n';
        raw(out/"opaque-straddle.r32f",straddle);raw(out/"occluded-candidate-depth.r32f",newOccluded.depth);
        require(oldWrong==farther+nearer&&newWrong==0,"both-direction late depth correction failed");
        const auto blocked=fixture.draw(fixed,std::vector<float>(pixels,.1f));
        for(int i=0;i<pixels;++i)require(blocked.color[1][i*4+3]==0&&blocked.depth[i]==.1f,"fully blocking ceiling leaked");
        std::cout<<"blocking_ceiling_leaks=0\neight_mrt_water_passivity=1\n";
        struct Fallback {const char* name;float material;bool underwater,known;};
        for(const auto c:std::array<Fallback,3>{{{"air",10000,false,true},{"unknown-water",10000,true,false},{"nonwater",1,true,true}}}) {
            const auto a=fixture.draw(old,clear,c.material,c.underwater,c.known),b=fixture.draw(fixed,clear,c.material,c.underwater,c.known);
            require(equal(a.color[0],b.color[0])&&equal(a.depth,b.depth),std::string(c.name)+" fallback changed");
            std::cout<<c.name<<"_color_depth_exact=1\n";
        }
        std::cout<<"depth_consistency_complete=1\n";
        glDeleteProgram(old);glDeleteProgram(fixed);glDeleteProgram(composite);glDeleteProgram(oldControl);glDeleteProgram(fixedControl);return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
