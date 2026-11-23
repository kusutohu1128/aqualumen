// Replay the actual Iris-linked fullscreen sources with one published lava cell.
// A positive control for judging which birch-only diagnostic changes can ship.
#pragma once
#include <cstring>

namespace aqualumenIdle {
using aqualumenLava::require;
using Pixel = std::array<float,4>;

struct Settings {
    int width=4,height=4,dimension=0;
    bool composite=false,water=false,pending=false,sky=false,leaf=false,film=false,wetBed=false;
    float normal=-4,blockLight=0,skyLight=0;
    Pixel scene={0,0,0,1}, daylight={0,0,0,1};
};
using Attachments = std::vector<std::vector<unsigned char>>;

inline GLuint texture(GLenum format, GLenum type, GLenum external, const void* value, int width=4, int height=4) {
    GLuint id; glGenTextures(1,&id); glBindTexture(GL_TEXTURE_2D,id);
    glTexStorage2D(GL_TEXTURE_2D,1,format,width,height);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glClearTexImage(id,0,external,type,value);
    return id;
}

inline Pixel draw(GLuint program, const Settings& f, aqualumenLava::Rig& rig, Attachments* native=nullptr, const Attachments* opaque=nullptr) {
    const Pixel black={0,0,0,0}, half={f.sky?1.f:.5f,0,0,1};
    const Pixel clearSun={f.daylight[0],f.daylight[1],f.daylight[2],f.pending?(f.leaf?-2.f:-1.f):1.f};
    const Pixel bed={.65f,.78f,.49f, f.wetBed?1798.f:0.f};
    const Pixel encoded={16777215,4095+4096*std::round(f.blockLight*4095),f.film?8391679.f:0.f,f.normal};
    auto input=[&](GLenum format,GLenum layout,const Pixel& value){
        return texture(format,GL_FLOAT,layout,value.data(),f.width,f.height);
    };
    const GLuint zero=texture(GL_RGBA32F,GL_FLOAT,GL_RGBA,black.data());
    const GLuint depth=input(GL_R32F,GL_RED,half),sun=input(GL_RGBA16F,GL_RGBA,clearSun);
    const GLuint packed=input(GL_RGBA32F,GL_RGBA,encoded),color=input(GL_RGBA32F,GL_RGBA,f.scene);
    const GLuint material=input(GL_RGBA16F,GL_RGBA,bed);
    const Pixel lamp={f.blockLight,0,0,0};
    const GLuint lampTarget=input(GL_R16F,GL_RED,lamp);
    const GLuint sky=texture(GL_RGBA32F,GL_FLOAT,GL_RGBA,f.daylight.data(),64,32);
    if(opaque) {
        // Restore the three native opaque attachments consumed after translucent geometry.
        glBindTexture(GL_TEXTURE_2D,color);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,f.width,f.height,GL_RGBA,GL_FLOAT,(*opaque)[0].data());
        glBindTexture(GL_TEXTURE_2D,sun);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,f.width,f.height,GL_RGBA,GL_HALF_FLOAT,(*opaque)[2].data());
        glBindTexture(GL_TEXTURE_2D,material);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,f.width,f.height,GL_RGBA,GL_HALF_FLOAT,(*opaque)[3].data());
    }
    const float one=1;
    const GLuint shadow=texture(GL_DEPTH_COMPONENT32F,GL_FLOAT,GL_DEPTH_COMPONENT,&one);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
    glUseProgram(program);
    int unit=0;
    auto bind=[&](const char* name,GLuint tex){
        const GLint loc=glGetUniformLocation(program,name);
        if(loc<0) return;
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,tex);glUniform1i(loc,unit++);
    };
    for(auto name:{"shadowcolor0","shadowcolor1","aqualumenBounceIncident"}) bind(name,zero);
    bind("colortex14",lampTarget);bind("colortex0",color);bind("colortex9",material);bind("colortex10",material);
    for(auto name:{"colortex6","colortex7","colortex11"}) bind(name,sky);
    bind("colortex8",sun);bind("colortex5",sun);bind("colortex15",packed);bind("depthtex0",depth);bind("depthtex1",depth);
    bind("shadowtex0",shadow);bind("aqualumenLightField",rig.w.field);bind("aqualumenLightList",rig.w.list);
    bind("aqualumenRawIndex",rig.w.index);
    // link() gave every integer entity / door sampler a complete, empty high unit.
    const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const float inverse[]={.125f,0,0,0,0,.125f,0,0,0,0,-1,0,0,0,-2,1};
    for(auto name:{"gbufferModelView","gbufferModelViewInverse","gbufferProjection","shadowProjection","shadowModelView"})
        glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverse);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),rig.cam[0],rig.cam[1],rig.cam[2]);
    glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),f.dimension);
    glUniform1f(glGetUniformLocation(program,"wetness"),f.film?1.f:0.f);
    glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),7.5f);
    glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),static_cast<int>(240*f.blockLight),static_cast<int>(240*f.skyLight));
    for(auto name:{"sunPosition","shadowLightPosition"}) glUniform3f(glGetUniformLocation(program,name),0,1,0);
    glUniform1f(glGetUniformLocation(program,"far"),128);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),f.water);
    glUniform1f(glGetUniformLocation(program,"viewWidth"),f.width);
    glUniform1f(glGetUniformLocation(program,"viewHeight"),f.height);
    glActiveTexture(GL_TEXTURE0+unit); // Allocate draw targets on an unused unit.
    GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    const GLenum formats[]={GL_RGBA32F,GL_RGBA32F,GL_RGBA16F,GL_RGBA16F,GL_R16F};
    GLenum buffers[5];GLuint targets[5];
    int count=f.composite?1:5;
    for(int i=0;i<count;i++){
        targets[i]=texture(formats[i],GL_FLOAT,i==4?GL_RED:GL_RGBA,black.data(),f.width,f.height);
        buffers[i]=GL_COLOR_ATTACHMENT0+i;
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[i],GL_TEXTURE_2D,targets[i],0);
    }
    glDrawBuffers(count,buffers);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"fullscreen replay FBO");
    const float corners[]={0,0,1,0,0,1,1,1};
    GLuint vao,vbo;glGenVertexArrays(1,&vao);glBindVertexArray(vao);
    glGenBuffers(1,&vbo);glBindBuffer(GL_ARRAY_BUFFER,vbo);
    glBufferData(GL_ARRAY_BUFFER,sizeof(corners),corners,GL_STATIC_DRAW);
    for(auto name:{"Position","UV0"}){
        GLint attribute=glGetAttribLocation(program,name);
        if(attribute<0 && std::string(name)=="UV0") continue; // A route-only program can discard UV.
        require(attribute>=0,"missing fullscreen position");
        glEnableVertexAttribArray(attribute);glVertexAttribPointer(attribute,2,GL_FLOAT,GL_FALSE,0,nullptr);
    }
    glViewport(0,0,f.width,f.height);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);
    glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    Pixel result;glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(2,2,1,1,GL_RGBA,GL_FLOAT,result.data());
    if(native) {
        glPixelStorei(GL_PACK_ALIGNMENT,1);
        for(int i=0;i<count;i++){
            const bool fp32=i<2;
            const int channels=i==4?1:4;
            std::vector<unsigned char> bytes(size_t(f.width)*f.height*channels*(fp32?4:2));
            glReadBuffer(buffers[i]);
            glReadPixels(0,0,f.width,f.height,i==4?GL_RED:GL_RGBA,fp32?GL_FLOAT:GL_HALF_FLOAT,bytes.data());
            for(size_t off=0;off<bytes.size();off+=fp32?4:2){
                if(fp32){float value;std::memcpy(&value,&bytes[off],4);require(std::isfinite(value),"nonfinite native float");}
                else {uint16_t value;std::memcpy(&value,&bytes[off],2);require((value&0x7c00)!=0x7c00,"nonfinite native half");}
            }
            native->push_back(std::move(bytes));
        }
        glPixelStorei(GL_PACK_ALIGNMENT,4);
    }
    require(glGetError()==GL_NO_ERROR,"fullscreen replay GL state");
    for(float value:result) require(std::isfinite(value),"nonfinite receiver");
    glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);glBindVertexArray(0);
    glDeleteBuffers(1,&vbo);glDeleteVertexArrays(1,&vao);glDeleteFramebuffers(1,&fbo);
    glDeleteTextures(count,targets);
    const GLuint inputs[]={zero,depth,sun,packed,shadow,color,material,sky,lampTarget};glDeleteTextures(9,inputs);glActiveTexture(GL_TEXTURE0);
    return result;
}

inline void diagnostic(const fs::path& shaders,const fs::path& submitted) {
    aqualumenLava::Rig rig;rig.init(shaders);
    for(const std::string program:{"composite","deferred"}){
        const bool water=program=="composite";
        GLuint handles[2];
        for(int i=0;i<2;i++){
            auto dir=submitted/(i?(water?"gp-idle-src-comp-pragma":"gp-idle-src-def-five"):"gp-idle-src-p3");
            handles[i]=link(aqualumenLocalLights::slurp(dir/(program+".vsh")),aqualumenLocalLights::slurp(dir/(program+".fsh")),program);
        }
        for(bool lava:{false,true}){
            aqualumenLava::Scene scene;
            if(lava) scene.lava.push_back({1,1,-2,{.85,.85,.85,.85}});
            rig.build(scene);
            Settings f;f.composite=water;f.water=water;f.pending=lava;
            const auto full=draw(handles[0],f,rig),lean=draw(handles[1],f,rig);
            std::cout<<std::setprecision(9)<<"C0 "<<program<<" lava="<<lava<<" p3="<<full[0]<<","<<full[1]<<","<<full[2]
                     <<" diagnostic="<<lean[0]<<","<<lean[1]<<","<<lean[2]<<std::endl;
            require(lava ? full[0]>lean[0]+1e-6f : std::memcmp(full.data(),lean.data(),sizeof(Pixel))==0,
                    program+" positive / empty receiver control");
        }
        glDeleteProgram(handles[0]);glDeleteProgram(handles[1]);
    }
}
inline GLuint captured(const fs::path& dir,const std::string& name,bool trace) {
    using aqualumenLocalLights::slurp;
    const auto vertex=slurp(dir/(name+".vsh"));
    auto fragment=slurp(dir/(name+".fsh"));
    if(trace) {
        // Only this unmeasured copy writes a route id. The entire original main selects the route.
        const std::string entry="void main() {";
        auto main=fragment.find(entry);require(main!=std::string::npos,"missing captured main");
        fragment.replace(main,entry.size(),"void idleOriginal() {");
        auto first=fragment.find("void "+(name=="deferred"?std::string("deferredEmptyGrid"):std::string("compositeAir"))+"() {");
        fragment.insert(fragment.find('\n')+1,"float idleHeavy=1.0;\n");
        if(first!=std::string::npos){
            const std::string signature=name=="deferred"?"void deferredEmptyGrid() {":"void compositeAir() {";
            fragment.insert(fragment.find(signature)+signature.size(),"idleHeavy=0.0;");
        }
        fragment+="\nvoid main(){ idleOriginal(); iris_FragData0=vec4(idleHeavy); }\n";
    }
    return link(vertex,fragment,dir.filename().string()+"/"+name);
}

inline std::pair<std::vector<unsigned char>,std::array<float,4>> display(
    GLuint final,GLuint exposure,const Settings& f,const Attachments& opaque,const Attachments& air) {
    const Pixel zero={0,0,0,0},z={f.sky?1.f:.5f,0,0,0};
    glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    auto upload=[&](GLenum format,GLenum layout,GLenum type,const auto& bytes){
        GLuint t=texture(format,GL_FLOAT,layout,zero.data(),f.width,f.height);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,f.width,f.height,layout,type,bytes.data());
        return t;
    };
    GLuint scene=upload(GL_RGBA32F,GL_RGBA,GL_FLOAT,air[0]);
    GLuint bed=upload(GL_RGBA16F,GL_RGBA,GL_HALF_FLOAT,opaque[3]);
    GLuint lamps=upload(GL_R16F,GL_RED,GL_HALF_FLOAT,opaque[4]);
    GLuint depth=texture(GL_R32F,GL_FLOAT,GL_RED,z.data(),f.width,f.height);
    // Keep a controlled bloom input and a populated adaptation history identical in both arms.
    GLuint bloom=texture(GL_RGBA16F,GL_FLOAT,GL_RGBA,f.daylight.data(),4,4);
    GLuint hist=texture(GL_RG32F,GL_FLOAT,GL_RG,zero.data(),2,1);
    std::array<float,4> state={.83f,1729.f,3.f,1730.f};
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,2,1,GL_RG,GL_FLOAT,state.data());
    GLuint target=texture(GL_RGBA8,GL_FLOAT,GL_RGBA,zero.data(),f.width,f.height);
    for(GLuint p:{exposure,final}){
        glUseProgram(p);
        int unit=0;
        auto bind=[&](const char* uniform,GLuint t){
            GLint loc=glGetUniformLocation(p,uniform);
            if(loc<0)return;
            glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,t);glUniform1i(loc,unit++);
        };
        bind("colortex0",scene);bind("colortex10",bed);bind("colortex13",bloom);bind("colortex14",lamps);
        bind("depthtex0",depth);bind("depthtex1",depth);bind("aqualumenLampExposure",hist);
        glUniform1f(glGetUniformLocation(p,"viewWidth"),f.width);glUniform1f(glGetUniformLocation(p,"viewHeight"),f.height);
        glUniform1i(glGetUniformLocation(p,"aqualumenDimension"),f.dimension);glUniform1i(glGetUniformLocation(p,"isEyeInWater"),f.water);
        glUniform2i(glGetUniformLocation(p,"eyeBrightnessSmooth"),int(240*f.blockLight),int(240*f.skyLight));
        const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        glUniformMatrix4fv(glGetUniformLocation(p,"gbufferModelViewInverse"),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(p,"sunPosition"),0,1,0);
        if(p==exposure){
            glUniform1f(glGetUniformLocation(p,"frameTime"),.03f);
            glUniform1i(glGetUniformLocation(p,"lampExposureImage"),0);
            glBindImageTexture(0,hist,0,GL_FALSE,0,GL_READ_WRITE,GL_RG32F);
            glDispatchCompute(1,1,1);glMemoryBarrier(GL_ALL_BARRIER_BITS);
        }
    }
    GLuint fb;glGenFramebuffers(1,&fb);glBindFramebuffer(GL_FRAMEBUFFER,fb);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,target,0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"final display FBO");
    glViewport(0,0,f.width,f.height);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    glBegin(GL_QUADS);
    for(auto uv:std::array<std::array<float,2>,4>{{{0,0},{1,0},{1,1},{0,1}}}){
        glTexCoord2fv(uv.data());glVertex2f(uv[0]*2-1,uv[1]*2-1);
    }
    glEnd();
    std::vector<unsigned char> bytes(size_t(f.width)*f.height*4);
    glReadPixels(0,0,f.width,f.height,GL_RGBA,GL_UNSIGNED_BYTE,bytes.data());
    glBindTexture(GL_TEXTURE_2D,hist);glGetTexImage(GL_TEXTURE_2D,0,GL_RG,GL_FLOAT,state.data());
    for(auto v:state)require(std::isfinite(v),"nonfinite exposure");
    require(state[1]==1729.f && state[3]==(!f.water && f.dimension==0?1730.f:0.f),"exposure tags");
    require(glGetError()==GL_NO_ERROR,"display replay GL state");
    glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fb);
    const GLuint ids[]={scene,bed,lamps,depth,bloom,hist,target};glDeleteTextures(7,ids);
    glPixelStorei(GL_UNPACK_ALIGNMENT,4);glActiveTexture(GL_TEXTURE0);
    return {std::move(bytes),state};
}

inline void compare(const fs::path& root,const fs::path& reference,const fs::path& candidate) {
    aqualumenLava::Rig rig;rig.init(root);
    const std::array<std::string,2> names={"deferred","composite"};
    GLuint original[2],changed[2],route[2];
    for(int p=0;p<2;p++){
        original[p]=captured(reference,names[p],false);
        changed[p]=captured(candidate,names[p],false);
        route[p]=captured(candidate,names[p],true);
    }
    aqualumenLava::Scene empty, elevated;
    elevated.lava.push_back({1,1,-2,{.85,.85,.85,.85}});
    rig.build(empty);
    Settings f;
    for(int p=0;p<2;p++){
        f.composite=p==1;
        auto pixel=draw(route[p],f,rig);
        std::cout<<"empty "<<names[p]<<" heavy entry="<<pixel[0]<<std::endl;
        require(pixel[0]==0,"empty frame still enters heavy-capable "+names[p]+" body");
    }
    GLuint final=link(expand(root/"final.vsh",root),expand(root/"final.fsh",root),"idle-display");
    GLuint exposure=compute(root/"composite3.csh",root);
    auto pair=[&](const std::string& label,const aqualumenLava::Scene& scene,Settings f){
        rig.build(scene);
        if(label=="held-torch"){
            aqualumenLocalLights::Carried carried;carried.item=10100;carried.level=14;
            rig.w.publish(false,&carried);
        }
        Attachments opaque[2];
        for(int p=0;p<2;p++){
            f.composite=p==1;
            auto selection=draw(route[p],f,rig);
            require(selection[0]==(p==0?!scene.lava.empty():f.water),"wrong full/idle path in "+label+" "+names[p]);
            Attachments a,b;
            draw(original[p],f,rig,&a,p?&opaque[0]:nullptr);
            draw(changed[p],f,rig,&b,p?&opaque[1]:nullptr);
            require(a.size()==b.size(),"attachment count");
            for(size_t i=0;i<a.size();i++) {
                require(a[i].size()==b[i].size(),"attachment dimensions");
                if(a[i]!=b[i]){
                    auto off=std::mismatch(a[i].begin(),a[i].end(),b[i].begin()).first-a[i].begin();
                    int bytes=i<2?4:2,channels=i==4?1:4;
                    size_t pixel=off/(bytes*channels);
                    uint32_t before=0,after=0;
                    std::memcpy(&before,a[i].data()+off/bytes*bytes,bytes);
                    std::memcpy(&after,b[i].data()+off/bytes*bytes,bytes);
                    std::cout<<"MISMATCH "<<label<<" "<<names[p]<<" attachment="<<i<<" xy="<<pixel%f.width<<","<<pixel/f.width
                             <<" component="<<off/bytes%channels<<" p8=0x"<<std::hex<<before<<" candidate=0x"<<after<<std::dec<<std::endl;
                    throw std::runtime_error("native attachment bitwise equality failed");
                }
            }
            if(!p){opaque[0]=a;opaque[1]=b;}
            else {
                auto da=display(final,exposure,f,opaque[0],a),db=display(final,exposure,f,opaque[1],b);
                require(da.first==db.first && std::memcmp(da.second.data(),db.second.data(),sizeof(da.second))==0,
                        label+" final RGBA8 or RG32F history differs");
            }
            std::cout<<"EQUAL "<<label<<" "<<names[p]<<" "<<f.width<<"x"<<f.height<<" attachments="<<a.size()<<std::endl;
        }
    };
    f.width=33;f.height=17;f.scene={.153f,.272f,.341f,1.f};f.daylight={.17f,.32f,.46f,1.f};f.skyLight=.8f;
    pair("dry-air",empty,f);
    f.sky=true;pair("sky",empty,f);f.sky=false;
    f.water=true;pair("submerged-empty",empty,f);
    f.pending=true;pair("submerged-elevated-lava",elevated,f);f.water=false;
    rig.cam={202.5,174,368.0};f.normal=-5;
    for(int pool:{1,9}) for(bool pillar:{false,true}) for(bool torch:{false,true}) {
        auto room=aqualumenLava::room(pool,pillar,torch);
        pair("room-"+std::to_string(pool)+(pillar?"-pillar":"-open")+(torch?"-torch":"-unlit"),room,f);
    }
    f.film=true;f.leaf=true;f.wetBed=true;
    pair("wet-leaf",aqualumenLava::room(9,true,true),f);
    f.pending=false;pair("covered-pending",aqualumenLava::room(9,false,false),f);
    rig.cam={208.5,65.62,355.5};f.normal=-4;f.film=false;f.leaf=false;f.wetBed=false;
    pair("birch-off-receiver",empty,f);
    aqualumenLava::Scene torch;torch.blocks.push_back(aqualumenLocalLights::torch(207,64,359,14));
    pair("birch-torch-receiver",torch,f);
    aqualumenLava::Scene two;two.blocks={aqualumenLocalLights::torch(208,65,354),aqualumenLocalLights::soulTorch(209,65,354)};
    f.blockLight=.73f;f.skyLight=0;pair("two-lamps",two,f);
    f.water=true;pair("held-torch",empty,f);f.water=false;
    rig.cam={8.5,0,0};f.pending=true;pair("grid-crossing-offscreen",elevated,f);
    f.pending=false;pair("removed-lava",empty,f);f.pending=true;pair("returned-lava",elevated,f);
    aqualumenLava::Scene dense;
    for(int x=0;x<12;x++)for(int z=-6;z<6;z++)dense.lava.push_back({x,1,z,{.85,.85,.85,.85}});
    pair("dense-144-cell",dense,f);f.pending=false;
    f.dimension=-1;pair("nether-fog",empty,f);f.dimension=1;pair("end-fog",empty,f);
    f.dimension=0;f.width=2560;f.height=1440;pair("dry-native",empty,f);
    glDeleteProgram(final);glDeleteProgram(exposure);
    for(int p=0;p<2;p++){glDeleteProgram(original[p]);glDeleteProgram(changed[p]);glDeleteProgram(route[p]);}
}

}
