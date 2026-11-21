// Real-GPU regression for the lamp display stage (adaptive exposure + emissive glow).
// Runs the production setup1.csh / composite3.csh compute and composite1/2 fragment passes.
// Expected values are independent re-statements (weighted mean -> 1/(1+3.5m), tau 0.45 onset / 1.8 recovery,
// normalised blur), not copies of shader text. GPU-harness results, NOT Minecraft frame times.
// Include after expand/compile/link/compute helpers; call lampDisplayProbe(root) after the local-lights probe.
#pragma once
inline void lampDisplayProbe(const fs::path& root,bool daylightWindow=false) {
    auto need=[](bool ok,const std::string& m){ if(!ok) throw std::runtime_error("lamp-display QA FAIL: "+m); };
    auto tex=[](GLenum internal,GLenum format,int w,int h,const std::vector<float>& data,GLenum filter=GL_NEAREST) {
        GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);
        glTexImage2D(GL_TEXTURE_2D,0,internal,w,h,0,format,GL_FLOAT,data.empty()?nullptr:data.data());
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        return t;
    };
    auto bind=[](int unit,GLuint t){ glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,t); };
    auto loc=[&](GLuint p,const char* n){ return glGetUniformLocation(p,n); };   // -1 (optimised out) is ignored; behaviour checks then fail
    auto ident=[&](GLuint p,const char* n){ const float m[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};glUniformMatrix4fv(loc(p,n),1,GL_FALSE,m); };

    // ---- compute: setup1 + composite3 ----
    GLuint setup=compute(root/"setup1.csh",root),meter=compute(root/"composite3.csh",root);
    GLuint state=tex(GL_RG32F,GL_RG,daylightWindow?198:1,daylightWindow?1090:1,{});
    auto readState=[&](int x=0){ std::array<float,2> v{};glMemoryBarrier(GL_ALL_BARRIER_BITS);glGetTextureSubImage(state,0,x,0,0,1,1,1,GL_RG,GL_FLOAT,sizeof(v),v.data());return v; };
    auto writeState=[&](float a,float b){ float v[2]={a,b};glBindTexture(GL_TEXTURE_2D,state);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RG,GL_FLOAT,v); };
    writeState(0.3f,5.f);
    glBindImageTexture(0,state,0,GL_FALSE,0,GL_READ_WRITE,GL_RG32F);
    glUseProgram(setup);glDispatchCompute(1,1,1);
    auto s0=readState();
    need(s0[0]==1.f&&s0[1]==1729.f,"setup1 must initialise exposure=1 with the 1729 sentinel");

    // localLum is the measured incident block-light and emission luminance
    // for this opaque surface, independent of the source inventory.
    auto step=[&](float prev,float sentinel,float dt,float lum,float localLum,bool night,float depth=0.5f,float opaqueDepth=0.5f,int skylight=240,int litColumns=16,int medium=0)->float {
        const int N=16;
        std::vector<float> c(N*N*4,lum),receiver(N*N*4,0.f),z(N*N,depth),zOpaque(N*N,opaqueDepth);
        for(int i=0;i<N*N;i++) {
            if(i%N>=litColumns) c[4*i]=c[4*i+1]=c[4*i+2]=0.f;
            c[4*i+3]=1;receiver[4*i]=localLum;
        }
        GLuint tc=tex(GL_RGBA32F,GL_RGBA,N,N,c),td=tex(GL_R32F,GL_RED,N,N,z);
        GLuint tl=tex(GL_RGBA32F,GL_RGBA,N,N,receiver),to=tex(GL_R32F,GL_RED,N,N,zOpaque);
        writeState(prev,sentinel);
        glUseProgram(meter);
        bind(0,tc);bind(1,td);bind(2,tl);bind(3,to);
        glUniform1i(loc(meter,"colortex0"),0);glUniform1i(loc(meter,"depthtex0"),1);glUniform1i(loc(meter,"colortex14"),2);glUniform1i(loc(meter,"depthtex1"),3);
        glUniform1i(loc(meter,"lampExposureImage"),0);
        ident(meter,"gbufferModelViewInverse");ident(meter,"gbufferProjectionInverse");
        glUniform3f(loc(meter,"cameraPosition"),0,0,0);
        glUniform3f(loc(meter,"sunPosition"),0,night?-1.f:1.f,0);
        glUniform1i(loc(meter,"aqualumenDimension"),0);
        glUniform1i(loc(meter,"isEyeInWater"),medium);
        glUniform1f(loc(meter,"frameTime"),dt);
        glUniform2i(loc(meter,"eyeBrightnessSmooth"),0,skylight);
        glBindImageTexture(0,state,0,GL_FALSE,0,GL_READ_WRITE,GL_RG32F);
        glDispatchCompute(1,1,1);
        auto out=readState();
        glDeleteTextures(4,std::array<GLuint,4>{tc,td,tl,to}.data());
        need(std::isfinite(out[0])&&out[0]>=0.125f-1e-6f&&out[0]<=1.f+1e-6f,"exposure left [0.125,1]");
        need(out[1]==1729.f,"sentinel lost after composite3");
        return out[0];
    };
    const float lum=0.02f;                                  // meter = 16*0.02-0.12 = 0.2 -> desired 1/(1+3.5*0.2)
    const double desired=1.0/(1.0+3.5*(16.0*lum-0.12));
    auto expectStep=[&](double prev,double target,double dt){ double tau=prev>target?0.45:1.8;return prev+(target-prev)*(1.0-std::exp(-std::min(std::max(dt,0.0),0.25)/tau)); };
    auto close=[&](double a,double b,const char* m){ need(std::abs(a-b)<2e-5,std::string(m)+": got "+std::to_string(a)+" want "+std::to_string(b)); };
    float onset=step(1.f,1729.f,0.1f,lum,2,true);
    close(onset,expectStep(1.0,desired,0.1),"night+lamp onset follows prev/dt");
    need(onset<1.f&&onset>desired,"onset must move toward but not past the target");
    close(step(1.f,1729.f,0.1f,1.0f,lum,true),onset,"only local fraction of a bright shaded surface drives the meter");
    close(step(1.f,1729.f,0.1f,lum,lum,true,0.2f,0.7f),1.0,"near glass/water hides opaque-surface meter behind it");
    close(step(1.f,1729.f,0.1f,lum,lum,false,0.5f,0.5f,0),onset,"fully enclosed cave responds the same at noon and at midnight");
    float recover=step(0.25f,1729.f,0.1f,lum,0,true);       // no local lamps: target is 1
    close(recover,expectStep(0.25,1.0,0.1),"no-lamp recovery");
    float onsetFrac=(1.0-onset)/(1.0-desired),recoverFrac=(recover-0.25)/0.75;
    need(onsetFrac>2.5*recoverFrac,"onset must be faster than recovery (same dt)");
    close(step(0.25f,1729.f,0.1f,lum,2,false),expectStep(0.25,1.0,0.1),"daytime lamps do not dim");
    close(step(1.f,1729.f,0.1f,lum,2,true,1.f),1.0,"sky pixels never drive exposure");
    close(step(0.6f,1729.f,0.0f,lum,2,true),0.6,"dt=0 keeps state");
    close(step(1.f,1729.f,9.f,lum,2,true),expectStep(1.0,desired,0.25),"dt clamped to 0.25 s");
    close(step(0.8f,0.f,0.1f,100.f,100.f,true),expectStep(1.0,0.125,0.1),"uninitialised state restarts at 1; bright scene reaches the exposure floor");
    close(step(1.f,1729.f,0.25f,100.f,100.f,true),expectStep(1.0,0.125,0.25),"bright floor 0.125");

    // ---- fragment quarters: composite1 (tag-gated 4x4 downsample) + composite2 (normalised blur) ----
    if(daylightWindow) {
        auto clear=[&]{
            glUseProgram(setup);glDispatchCompute(1,1,1);glMemoryBarrier(GL_ALL_BARRIER_BITS);
            need(readState(1)[1]==0.f,"old daylight history survived world setup");
        };
        auto view=[&](float surface,float lamps,bool night,int columns=16,float front=.5f,float opaque=.5f,int medium=0,float dt=.1f){
            step(1,1729,dt,surface,lamps,night,front,opaque,0,columns,medium);
            return readState(1);
        };
        clear();
        auto dark=view(.001f,0,false);
        need(dark[1]==1730.f,"daylight meter was not written");
        close(dark[0],4.,"unlit room starts at four exposure stops");
        auto opening=view(1.f,0,false);
        close(opening[0],4.*std::exp(-.1/.38),"bright daylight entering a dark room");
        clear();close(view(1.f,0,false,8)[0],2.,"half the metering weight sees the window");
        clear();close(view(1.f,1.f,false)[0],4.,"torchlit geometry cannot masquerade as daylight");
        clear();close(view(1.f,0,true)[0],4.,"no daylight metering at midnight");
        clear();close(view(1.f,0,false,16,.2f,.6f)[0],4.,"translucent cover hides the opaque receiver");
        clear();close(view(1.f,0,false,16,.2f,1.f)[0],0.,"view of daylight sky through glass");
        auto recovering=view(.001f,0,false);
        close(recovering[0],4.*(1.-std::exp(-.1/1.65)),"eye gains exposure slowly in the dark");
        clear();view(.001f,0,false);
        for(int i=0;i<10;i++)view(1.f,0,false,16,.5f,.5f,0,.01f);
        close(readState(1)[0],opening[0],"subdividing the same interval gives the same gain");
        need(view(1.f,0,false,16,.2f,.6f,1)[1]==0,"air history crossed the water surface");
        close(view(.001f,0,false)[0],4.,"emerging from water starts with the actual view");
        std::cout<<"PASS daylight exposure: aperture coverage, source separation, sky behind glass, onset/recovery, frame rate and immersion reset\n";
    }
    const int Q=16;
    GLuint progs[2]={link(expand(root/"composite1.vsh",root),expand(root/"composite1.fsh",root),"lamp-glow-1"),
                     link(expand(root/"composite2.vsh",root),expand(root/"composite2.fsh",root),"lamp-glow-2")};
    GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    auto quad=[&]{ glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd(); };
    struct Glow { std::vector<float> img;double total,far; };
    // tag: material.a of the texel (negative = lamp emitter); z0/z1: depthtex0 / depthtex1 at the texel.
    auto glow=[&](float tag,float z0,float z1,int N=64)->Glow {
        std::vector<float> col(N*N*4,0.f),mat(N*N*4,0.f),d0(N*N,0.5f),d1(N*N,0.5f);
        const int sx=34,sy=34,i=sy*N+sx;                    // quarter texel (8,8)
        col[i*4]=4;col[i*4+1]=3;col[i*4+2]=2;col[i*4+3]=1;
        mat[i*4]=2;mat[i*4+1]=1.5f;mat[i*4+2]=1;mat[i*4+3]=tag;
        for(int k=0;k<N*N;k++) if(k!=i) mat[k*4+3]=0;        // ordinary surfaces: tag 0
        d0[i]=z0;d1[i]=z1;
        GLuint t0=tex(GL_RGBA32F,GL_RGBA,N,N,col),t10=tex(GL_RGBA32F,GL_RGBA,N,N,mat),dd0=tex(GL_R32F,GL_RED,N,N,d0),dd1=tex(GL_R32F,GL_RED,N,N,d1);
        GLuint t12=tex(GL_RGBA32F,GL_RGBA,Q,Q,{},GL_LINEAR),t13=tex(GL_RGBA32F,GL_RGBA,Q,Q,{},GL_LINEAR);
        glViewport(0,0,Q,Q);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t12,0);glDrawBuffer(GL_COLOR_ATTACHMENT0);
        need(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"glow fbo 1 incomplete");
        glUseProgram(progs[0]);bind(0,t0);bind(1,t10);bind(2,dd0);bind(3,dd1);
        glUniform1i(loc(progs[0],"colortex0"),0);glUniform1i(loc(progs[0],"colortex10"),1);
        glUniform1i(loc(progs[0],"depthtex0"),2);glUniform1i(loc(progs[0],"depthtex1"),3);
        quad();
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t13,0);
        glUseProgram(progs[1]);bind(0,t12);glUniform1i(loc(progs[1],"colortex12"),0);
        quad();
        Glow g{std::vector<float>(Q*Q*4),0,0};
        glReadPixels(0,0,Q,Q,GL_RGBA,GL_FLOAT,g.img.data());
        for(int y=0;y<Q;y++) for(int x=0;x<Q;x++) {
            float r=g.img[(y*Q+x)*4];
            need(std::isfinite(r)&&r>=0,"glow produced nonfinite/negative value");
            g.total+=r;if(std::max(std::abs(x-8),std::abs(y-8))>=5) g.far=std::max(g.far,double(r));
        }
        glDeleteTextures(6,std::array<GLuint,6>{t0,t10,dd0,dd1,t12,t13}.data());
        return g;
    };
    Glow lit=glow(-1.f,0.5f,0.5f);
    const double wantEnergy=std::min(2.0,4.0)/16.0;          // red: min(emission cap 2, colour 4) spread over 16 samples
    need(std::abs(lit.total-wantEnergy)<=1e-3*wantEnergy+1e-6,"tagged texel energy not normalised: "+std::to_string(lit.total));
    need(lit.img[(8*Q+8)*4]>0,"tagged texel has no glow at its centre");
    need(lit.img[(8*Q+10)*4]>0&&lit.img[(10*Q+8)*4]>0,"glow does not reach the neighbourhood");
    need(lit.far==0.0,"glow leaked >=5 quarter texels away");
    need(lit.img[(8*Q+8)*4]>=lit.img[(8*Q+10)*4],"glow not peaked at its source");
    need(glow(0.f,0.5f,0.5f).total==0.0,"bright ordinary wall (tag 0) must not glow");
    need(glow(-1.f,0.4f,0.5f).total==0.0,"emitter behind nearer translucent depth must not glow");
    need(glow(-1.f,1.0f,1.0f).total==0.0,"sky depth must not glow");
    const double oddExpected=2.0*Q*Q/(65.0*65.0);
    need(std::abs(glow(-1.f,0.5f,0.5f,65).total-oddExpected)<2e-4,"odd viewport lost fractional source area");
    glUseProgram(0);
    glBindFramebuffer(GL_FRAMEBUFFER,0);
    glDeleteFramebuffers(1,&fbo);
    glDeleteTextures(1,&state);
    glDeleteProgram(setup);
    glDeleteProgram(meter);
    for(GLuint program:progs) glDeleteProgram(program);
    std::cout<<"PASS lamp display: lit-night adaptation, recovery, day/sky controls and compact visible-source glow; normalized integral "
             <<lit.total<<", no halo from ordinary walls or hidden emitters, odd 65px input conserved\n";
}
