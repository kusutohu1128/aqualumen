#define main aqualumen_paired_native_unused_main
#include "water_paired_native.cpp"
#undef main

struct OverlayCapture {
    std::vector<float> color,classification,point,depth;
};

struct OverlayFixture {
    Fixture base;
    std::array<GLuint,2> extra={};
    OverlayFixture() {
        const float a=base.projection[10],b=base.projection[14];
        base.inverseProjection={1/base.projection[0],0,0,0,0,1/base.projection[5],0,0,0,0,0,1/b,0,0,-1,a/b};
        glGenTextures(2,extra.data());glBindFramebuffer(GL_FRAMEBUFFER,base.framebuffer);
        for(int i=0;i<2;++i) {
            glActiveTexture(GL_TEXTURE14);glBindTexture(GL_TEXTURE_2D,extra[i]);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glTexImage2D(GL_TEXTURE_2D,0,i?GL_DEPTH_COMPONENT32F:GL_RGBA32F,side,side,0,i?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,nullptr);
            glFramebufferTexture2D(GL_FRAMEBUFFER,i?GL_DEPTH_ATTACHMENT:GL_COLOR_ATTACHMENT4,GL_TEXTURE_2D,extra[i],0);
        }
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"overlay FBO incomplete");
    }
    ~OverlayFixture(){glDeleteTextures(2,extra.data());}
    void quad() {
        glBegin(GL_QUADS);for(auto p:std::array<std::array<float,2>,4>{{{{-.25f,-.25f}},{{.25f,-.25f}},{{.25f,.25f}},{{-.25f,.25f}}}}) {
            glMultiTexCoord2f(GL_TEXTURE0,.5f,.5f);glVertex2f(p[0],p[1]);
        }glEnd();
    }
    OverlayCapture read() {
        OverlayCapture c;
        for(auto pair:std::array<std::pair<GLenum,std::vector<float>*>,3>{{{GL_COLOR_ATTACHMENT0,&c.color},{GL_COLOR_ATTACHMENT1,&c.classification},{GL_COLOR_ATTACHMENT4,&c.point}}}) {
            pair.second->resize(pixels*4);glReadBuffer(pair.first);glReadPixels(0,0,side,side,GL_RGBA,GL_FLOAT,pair.second->data());
            for(float v:*pair.second)require(std::isfinite(v),"overlay nonfinite");
        }
        c.depth.resize(pixels);glReadPixels(0,0,side,side,GL_DEPTH_COMPONENT,GL_FLOAT,c.depth.data());
        require(glGetError()==GL_NO_ERROR,"overlay GL error");return c;
    }
    OverlayCapture draw(GLuint p,bool instrumented,bool markerBlend,bool depthWrite,float alpha,float windowDepth) {
        base.uniforms(p,0,true);
        glBindFramebuffer(GL_FRAMEBUFFER,base.framebuffer);
        const GLenum draws[]={GL_COLOR_ATTACHMENT0,GL_NONE,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT4};glDrawBuffers(4,draws);
        const float color[4]={.1f,.2f,.3f,1},water[4]={2,.3f,4,1},point[4]={.1f,3,.2f,.97f},depth=.97f;
        glClearBufferfv(GL_COLOR,0,color);glClearBufferfv(GL_COLOR,2,water);glClearBufferfv(GL_COLOR,3,point);
        glDepthMask(GL_TRUE);glClearBufferfv(GL_DEPTH,0,&depth);
        glDrawBuffers(instrumented?4:2,draws);
        glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glDepthMask(depthWrite?GL_TRUE:GL_FALSE);
        glEnablei(GL_BLEND,0);glBlendFuncSeparatei(0,GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);
        for(int i:{2,3}) {
            if(markerBlend){glEnablei(GL_BLEND,i);glBlendFuncSeparatei(i,GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);}
            else glDisablei(GL_BLEND,i);
        }
        const float texel[4]={.8f,.7f,.6f,alpha};glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,base.textures[0]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,texel);
        glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
        glTranslatef(0,0,windowDepth*2-1);glColor4f(1,1,1,1);quad();return read();
    }
    OverlayCapture reclaim(GLuint p) {
        glUseProgram(p);const GLenum draws[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT4};glDrawBuffers(3,draws);
        for(int i=0;i<3;++i)glDisablei(GL_BLEND,i);
        glDepthMask(GL_TRUE);glMatrixMode(GL_MODELVIEW);glLoadIdentity();quad();return read();
    }
};

int markerCount(const OverlayCapture& c) {
    int marked=0;
    for(int i=0;i<pixels;++i) {
        const int a=i*4;
        if(c.point[a+3]==-3) {
            ++marked;for(int k=0;k<4;++k)require(c.classification[a+k]==0,"nonwater C12 not exact zero");
            for(int k=0;k<3;++k)require(c.point[a+k]==0,"nonwater point not exact zero");
        }
    }
    return marked;
}

int main(int argc,char** argv) {
    try {
        require(argc==4,"usage: ownership-native CONTROL_ROOT PAIRED_ROOT NEW_OUTPUT");
        const fs::path control=argv[1],paired=argv[2],out=argv[3];require(!fs::exists(out),"overlay output exists");fs::create_directories(out);
        Context context;OverlayFixture fixture;
        for(const std::string name:{"gbuffers_textured","gbuffers_textured_lit"}) {
            const auto old=program(source(control/(name+".vsh"),control),source(control/(name+".fsh"),control)),
                marked=program(source(paired/(name+".vsh"),paired),source(paired/(name+".fsh"),paired));
            for(bool depthWrite:{false,true}) {
                const auto a=fixture.draw(old,false,false,depthWrite,.5f,.75f),b=fixture.draw(marked,true,false,depthWrite,.5f,.75f);
                require(equal(a.color,b.color)&&equal(a.depth,b.depth),"nonwater observer changed C0/depth");
                const int count=markerCount(b);require(count>100&&markerCount(a)==0,"overlay witness vacuous");
                for(int i=0;i<pixels;++i)require(a.classification[i*4+3]==1,"old overlay did not retain stale water mask");
                int depthChanges=0;for(float value:b.depth)depthChanges+=value!=.97f;
                require(depthWrite?depthChanges==count:depthChanges==0,"depth-mask ownership conflated");
                const std::string prefix=name+(depthWrite?"-depth-write":"-depth-retained");
                raw(out/(prefix+"-C0.rgba32f"),b.color);raw(out/(prefix+"-C12.rgba32f"),b.classification);
                raw(out/(prefix+"-C3.rgba32f"),b.point);raw(out/(prefix+"-depth.r32f"),b.depth);
                std::cout<<prefix<<" markers="<<count<<" stale_old="<<count<<" C0_depth_exact=1 depth_changes="<<depthChanges<<'\n';
            }
            const auto blended=fixture.draw(marked,true,true,true,.5f,.75f);
            require(markerCount(blended)==0,"blend-on negative control failed to reject");
            const auto discarded=fixture.draw(marked,true,false,true,.05f,.75f),occluded=fixture.draw(marked,true,false,true,.5f,.99f);
            require(markerCount(discarded)==0&&markerCount(occluded)==0,"discard/occlusion erased water records");
            for(const auto* c:{&discarded,&occluded})for(int i=0;i<pixels;++i)
                require(c->classification[i*4+3]==1&&c->point[i*4+3]==.97f&&c->depth[i]==.97f,"rejected overlay changed water state");
            fixture.draw(marked,true,false,false,.5f,.75f);
            const auto reclaim=program(source(paired/(name+".vsh"),paired),"#version 330 compatibility\nvoid main(){gl_FragData[0]=vec4(.1,.2,.3,1);gl_FragData[1]=vec4(2,.3,4,1);gl_FragData[2]=vec4(.1,3,.2,.97);gl_FragDepth=.5;}");
            const auto reclaimed=fixture.reclaim(reclaim);require(markerCount(reclaimed)==0,"synthetic water protocol reclaim failed");
            std::cout<<name<<" blend_mutant_rejected=1 discard_preserved=1 occluded_preserved=1 synthetic_water_protocol_reclaim=1\n";
            glDeleteProgram(old);glDeleteProgram(marked);glDeleteProgram(reclaim);
        }
        std::cout<<"ownership_protocol_complete=1\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
