// Compile original pack programs with real GL, without requiring Minecraft.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <cmath>
namespace fs=std::filesystem;
std::string expand(const fs::path& file,const fs::path& root,int level=0) {
    if(level>32) throw std::runtime_error("Include cycle");
    std::ifstream input(file);
    if(!input) throw std::runtime_error("Cannot read "+file.string());
    std::ostringstream output;
    for(std::string line;std::getline(input,line);) {
        if(line.rfind("#include",0)==0) {
            auto begin=line.find('"'),end=line.find('"',begin+1);
            if(begin==std::string::npos||end==std::string::npos) throw std::runtime_error("Malformed include");
            auto name=line.substr(begin+1,end-begin-1);
            output<<expand(root/name.substr(name[0]=='/'?1:0),root,level+1);
        } else {
            output<<line<<'\n';
        }
    }
    return output.str();
}
GLuint compile(GLenum type,const std::string& source,const std::string& name) {
    GLuint shader=glCreateShader(type);
    const char* text=source.c_str();glShaderSource(shader,1,&text,nullptr);glCompileShader(shader);
    GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok) { char log[16384];glGetShaderInfoLog(shader,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log); }
    return shader;
}
GLuint link(const std::string& vs,const std::string& fragment,const std::string& name,const char* materialAttribute=nullptr) {
    GLuint v=compile(GL_VERTEX_SHADER,vs,name+".vsh"),f=compile(GL_FRAGMENT_SHADER,fragment,name+".fsh");
    GLuint program=glCreateProgram();glAttachShader(program,v);glAttachShader(program,f);
    if(materialAttribute) glBindAttribLocation(program,10,materialAttribute);
    glLinkProgram(program);
    glDeleteShader(v);glDeleteShader(f);
    GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) { char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log); }
    return program;
}
GLuint compute(const fs::path& file,const fs::path& root) {
    GLuint shader=compile(GL_COMPUTE_SHADER,expand(file,root),file.filename().string());
    GLuint program=glCreateProgram();glAttachShader(program,shader);glLinkProgram(program);glDeleteShader(shader);
    GLint ok;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) {char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(file.string()+": "+log);}
    return program;
}
void rippleProbe(const fs::path& root) {
    GLuint setup=compute(root/"setup.csh",root),first=compute(root/"begin.csh",root),second=compute(root/"begin1.csh",root);
    GLuint images[2];glGenTextures(2,images);
    for(auto texture:images) {glBindTexture(GL_TEXTURE_2D,texture);glTexStorage2D(GL_TEXTURE_2D,1,GL_RG32F,512,512);}
    auto dispatch=[&](GLuint program,float force,float delta,float shiftX,float reset) {
        glUseProgram(program);
        glUniform1i(glGetUniformLocation(program,"rippleImageA"),0);glUniform1i(glGetUniformLocation(program,"rippleImageB"),1);
        glUniform1i(glGetUniformLocation(program,"aqualumenActive"),force!=0?1:0);
        glUniform1f(glGetUniformLocation(program,"aqualumenDelta"),delta);
        glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,0);
        glUniform4f(glGetUniformLocation(program,"aqualumenShift"),shiftX,0,reset,0);
        for(int i=0;i<8;i++) {auto name="aqualumenContact"+std::to_string(i);glUniform4f(glGetUniformLocation(program,name.c_str()),0,0,i==0?force:0,0.65);}
        for(int i=0;i<2;i++) glBindImageTexture(i,images[i],0,GL_FALSE,0,GL_READ_WRITE,GL_RG32F);
        glDispatchCompute(32,32,1);glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT|GL_TEXTURE_FETCH_BARRIER_BIT|GL_SHADER_STORAGE_BARRIER_BIT);
    };
    auto read=[&]() {std::vector<float> data(512*512*2);glBindTexture(GL_TEXTURE_2D,images[0]);glGetTexImage(GL_TEXTURE_2D,0,GL_RG,GL_FLOAT,data.data());return data;};
    auto energy=[&](const std::vector<float>& data) {double sum=0;for(size_t i=0;i<data.size();i+=2) {if(!std::isfinite(data[i])||!std::isfinite(data[i+1])||std::abs(data[i])>=0.5) throw std::runtime_error("Unstable wave-height GPU output");sum+=data[i]*data[i]+data[i+1]*data[i+1]/6.25;}return sum;};
    dispatch(setup,0,0,0,0);
    if(energy(read())!=0) throw std::runtime_error("Ripple setup not zero initialized");
    // Stress max supported dt and source, then prove nonzero response and dissipated energy.
    for(int frame=0;frame<20;frame++) {dispatch(first,8,0.05,0,0);dispatch(second,8,0.05,0,0);}
    auto forced=read();double initial=energy(forced);
    if(initial<0.001) throw std::runtime_error("Ripple contact produced no response");
    dispatch(first,0,0,4,0);dispatch(second,0,0,0,0);
    auto shifted=read();
    for(int y=4;y<508;y++) for(int x=4;x<504;x++) for(int c=0;c<2;c++)
        if(std::abs(shifted[(y*512+x)*2+c]-forced[(y*512+x+4)*2+c])>0.000001) throw std::runtime_error("Ripple recenter does not preserve overlap");
    for(int frame=0;frame<200;frame++) {dispatch(first,0,0.05,0,0);dispatch(second,0,0.05,0,0);}
    double final=energy(read());
    if(final>=initial*0.15) throw std::runtime_error("Ripple damping probe failed");
    dispatch(first,0,0.05,0,1);dispatch(second,0,0.05,0,0);
    if(energy(read())!=0) throw std::runtime_error("Ripple teleport reset failed");
    std::cout<<"PASS GPU wave-height: zero setup, driven response, CFL max-dt stability, integer recenter, damping "<<initial<<" -> "<<final<<", teleport reset\n";
    glDeleteProgram(setup);glDeleteProgram(first);glDeleteProgram(second);glDeleteTextures(2,images);glUseProgram(0);
}
// Run the production composite on an opaque foreground with fixed depth/light.
// Only the far-background cloud radiance changes; output attachment is separate
// from every sampled texture, avoiding undefined framebuffer feedback.
void foregroundCloudProbe(const fs::path& root) {
    GLuint program=link(expand(root/"composite.vsh",root),expand(root/"composite.fsh",root),"foreground-cloud-probe");
    GLuint textures[5],framebuffer;glGenTextures(5,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glBindTexture(GL_TEXTURE_2D,textures[4]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[4],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Foreground probe framebuffer incomplete");
    const float surface[4]={0.05f,0.05f,0.05f,1.0f},depth=0.5f;
    for(int i=0;i<4;++i) {
        glActiveTexture(GL_TEXTURE0+i);glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(i==0) glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,surface);
        else if(i==1) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&depth);
        else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,4,4,0,GL_RGBA,GL_FLOAT,nullptr);
    }
    glUseProgram(program);glViewport(0,0,1,1);
    glUniform1i(glGetUniformLocation(program,"colortex0"),0);glUniform1i(glGetUniformLocation(program,"depthtex0"),1);
    glUniform1i(glGetUniformLocation(program,"colortex6"),2);glUniform1i(glGetUniformLocation(program,"colortex7"),3);
    glUniform1i(glGetUniformLocation(program,"shadowtex0"),4);
    GLuint shadow;glGenTextures(1,&shadow);glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,shadow);
    float shadowDepth=1;glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    float projectionInverse[16]={1,0,0,0,0,1,0,0,0,0,128,0,0,0,-128,1};
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,projectionInverse);
    for(const char* name:{"gbufferModelViewInverse","shadowProjection","shadowModelView"})
        glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);glUniform1f(glGetUniformLocation(program,"far"),768);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
    auto sky=[&](int unit,float cloud) {
        std::vector<float> pixels(4*4*4,0);
        for(int i=0;i<12;++i) {pixels[i*4]=0.2f+cloud;pixels[i*4+1]=0.4f+cloud;pixels[i*4+2]=0.6f+cloud;pixels[i*4+3]=1;}
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,4,GL_RGBA,GL_FLOAT,pixels.data());
    };
    sky(3,0); // fixed cloud-free atmosphere and solar cache in both runs
    auto draw=[&](float cloud) {
        sky(2,cloud);
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        float output[4];glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,output);
        if(!std::isfinite(output[0]) || output[3]!=1 || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Invalid foreground composite output");
        return output[0];
    };
    for(float metres:{16.0f,64.0f,128.0f}) {
        projectionInverse[10]=metres;projectionInverse[14]=-metres;
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,projectionInverse);
        float clear=draw(0),cloudy=draw(4),clearRepeat=draw(0);
        if(std::abs(clear-clearRepeat)>0.00001f) throw std::runtime_error("Foreground cloud probe is not deterministic");
        std::cout<<"GPU opaque foreground at "<<metres<<"m: clear "<<clear<<", background cloud "<<cloudy<<", difference "<<cloudy-clear<<"; alpha remains one\n";
        if(std::abs(cloudy-clear)>0.00001f)
            throw std::runtime_error("Opaque foreground must not inherit the pattern/radiance of clouds behind its depth");
    }
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(5,textures);glDeleteTextures(1,&shadow);glDeleteFramebuffers(1,&framebuffer);
}
// A low, forward solar aureole is not diffuse hemisphere illumination. With
// every sample of the camera-to-opaque-surface segment covered and shadowed,
// changing only that aureole must not brighten the foreground aerial haze.
// Exercise the unmodified production pair, with no sampled texture attached to
// its output framebuffer. This is a controlled regression, not screenshot replay.
void foregroundShadowHazeProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos)
        throw std::runtime_error("Foreground shadow/haze regression requires the real NVIDIA renderer, not software GL");
    constexpr int skyWidth=64,skyHeight=32;
    constexpr float pi=3.14159265358979323846f;
    GLuint program=link(expand(root/"composite.vsh",root),expand(root/"composite.fsh",root),"foreground-shadow-haze-probe");
    GLuint textures[6],framebuffer;glGenTextures(6,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[5]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[5],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Shadow/haze probe framebuffer incomplete");
    const float surface[4]={0.05f,0.05f,0.05f,1.0f},depth=0.5f,shadowDepth=0.0f;
    for(int i=0;i<5;++i) {
        glActiveTexture(GL_TEXTURE0+i);glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(i==0) glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,surface);
        else if(i==1) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&depth);
        else if(i==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,skyWidth,skyHeight,0,GL_RGBA,GL_FLOAT,nullptr);
    }
    glUseProgram(program);glViewport(0,0,1,1);
    const char* samplers[]={"colortex0","depthtex0","colortex6","colortex7","shadowtex0"};
    for(int i=0;i<5;++i) glUniform1i(glGetUniformLocation(program,samplers[i]),i);
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    // At UV(.5,.5), depth .5 this reconstructs view/world position (0,2,-8).
    // Model-view remains identity: the ray starts at the actual camera origin.
    float inverseProjection[16]={1,0,0,0,0,1,0,0,0,0,8,0,0,2,-8,1};
    float shadowProjection[16]={0.02f,0,0,0,0,0.02f,0,0,0,0,0.02f,0,0,0,0,1};
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);glUniform1f(glGetUniformLocation(program,"far"),768);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,2,-8);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,0,0);
    auto uploadSky=[&](int unit,float aureole,float solar=1.0f) {
        std::vector<float> pixels(skyWidth*skyHeight*4,0.0f);
        const float sunY=2.0f/std::sqrt(68.0f),sunZ=-8.0f/std::sqrt(68.0f),coneCos=std::cos(10.0f*pi/180.0f);
        for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
            // Match the public LUT parameterization, including its reserved row.
            const float azimuth=((x+0.5f)/skyWidth-0.5f)*2.0f*pi;
            const float elevation=(float(y)/(skyHeight-2)-0.5f)*pi;
            const float alignment=std::sin(elevation)*sunY+std::cos(elevation)*std::sin(azimuth)*sunZ;
            const size_t base=(y*skyWidth+x)*4;
            for(int c=0;c<3;++c) pixels[base+c]=0.01f+(alignment>coneCos?aureole:0.0f);
            pixels[base+3]=1.0f;
        }
        const size_t cache=(skyHeight-1)*skyWidth*4;
        pixels[cache]=pixels[cache+1]=pixels[cache+2]=solar;pixels[cache+3]=1.0f;
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,skyWidth,skyHeight,GL_RGBA,GL_FLOAT,pixels.data());
    };
    auto draw=[&](float aureole,float blocker=0.0f,float solar=1.0f) {
        uploadSky(2,0.0f,solar);
        uploadSky(3,aureole);
        glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,textures[4]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_DEPTH_COMPONENT,GL_FLOAT,&blocker);
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        std::vector<float> output(4);glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,output.data());
        for(int c=0;c<4;++c) if(!std::isfinite(output[c])) throw std::runtime_error("Nonfinite shadow/haze composite output");
        if(output[3]!=1.0f || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Invalid shadow/haze composite output");
        return output;
    };
    const auto clear=draw(0.0f),forwardSun=draw(4.0f),repeat=draw(0.0f);
    float largestDifference=0.0f;
    for(int c=0;c<3;++c) {
        if(std::abs(clear[c]-repeat[c])>0.00001f) throw std::runtime_error("Shadow/haze probe is not deterministic");
        largestDifference=std::max(largestDifference,std::abs(forwardSun[c]-clear[c]));
    }
    std::cout<<"GPU covered shadow at "<<std::sqrt(68.0f)<<"m: diffuse sky fixed, clear "<<clear[0]<<", forward solar aureole "<<forwardSun[0]<<", largest RGB difference "<<largestDifference<<"; alpha remains one\n";
    if(largestDifference>0.00001f)
        throw std::runtime_error("Opaque foreground in covered shadow must not gain forward-sun aerial haze when diffuse illumination is unchanged");
    std::cout<<"PASS GPU production composite: covered-shadow foreground rejects unrelated forward solar aureole\n";
    // A successful leak fix must still admit direct scattering from a covered,
    // unblocked sun path. Changing the cache alone must control that response.
    const auto lit=draw(0.0f,1.0f,1.0f),litWithoutSun=draw(0.0f,1.0f,0.0f);
    float smallestGain=1.0f,largestGain=0.0f;
    for(int c=0;c<3;++c) {
        if(std::abs(litWithoutSun[c]-clear[c])>0.00001f)
            throw std::runtime_error("Unblocked air with zero solar cache must retain only the unchanged ambient contribution");
        smallestGain=std::min(smallestGain,lit[c]-litWithoutSun[c]);
        largestGain=std::max(largestGain,lit[c]-litWithoutSun[c]);
    }
    if(smallestGain<0.00001f || largestGain>0.1f)
        throw std::runtime_error("Covered sunlit air must have a positive, bounded solar-cache-controlled scattering response");
    std::cout<<"PASS GPU production composite: covered sunlit air "<<lit[0]<<", zero-solar-cache "<<litWithoutSun[0]<<", positive direct gain "<<smallestGain<<".."<<largestGain<<"\n";
    // This fixture is below the model's sea-level reference, so both air
    // densities are exactly one. Compare the complete production result with
    // an independent double-precision homogeneous-medium solution, not a copy
    // of the shader's step integrator. These are the existing physical constants.
    const double betaR[3]={5.8e-6,13.5e-6,33.1e-6},betaM=2.1e-5;
    const double solar[3]={18.0,17.6,17.0},length=std::sqrt(68.0),g=0.76;
    const double phaseR=3.0/(8.0*std::acos(-1.0));
    const double phaseM=(1.0-g*g)/(4.0*std::acos(-1.0)*std::pow(1.0+g*g-2.0*g,1.5));
    double largestAnalyticError=0.0;
    for(int c=0;c<3;++c) {
        const double extinction=betaR[c]+1.1*betaM;
        const double transmission=std::exp(-extinction*length);
        // Constant sky .01 gives hemisphere source radiance .005.
        const double source=solar[c]*(betaR[c]*phaseR+betaM*phaseM)+(betaR[c]+betaM)*0.005;
        const double expected=surface[c]*transmission+source*(-std::expm1(-extinction*length))/extinction;
        largestAnalyticError=std::max(largestAnalyticError,std::abs(lit[c]-expected));
    }
    if(largestAnalyticError>0.0000005)
        throw std::runtime_error("Finite aerial transport must agree with constant-coefficient analytic integration");
    std::cout<<"PASS GPU production composite: independent homogeneous-air analytic solution, largest RGB error "<<largestAnalyticError<<"\n";
    // A lit texel outside the rendered shadow region cannot establish that the
    // sun reaches this air segment. Unknown coverage must fail closed for air.
    shadowProjection[12]=100.0f;
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    const auto unknown=draw(0.0f,1.0f,1.0f),unknownWithoutSun=draw(0.0f,1.0f,0.0f);
    for(int c=0;c<3;++c) if(std::abs(unknown[c]-clear[c])>0.00001f || std::abs(unknown[c]-unknownWithoutSun[c])>0.00001f)
        throw std::runtime_error("Unknown shadow coverage must not invent direct solar scattering");
    shadowProjection[12]=0.0f;
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    std::cout<<"PASS GPU production composite: outside shadow coverage "<<unknown[0]<<" retains ambient/extinction only, not fully-lit fallback\n";
    inverseProjection[13]=inverseProjection[14]=0.0f;
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    const auto zeroDistance=draw(4.0f,1.0f,1.0f);
    for(int c=0;c<3;++c) if(std::abs(zeroDistance[c]-surface[c])>0.0000001f)
        throw std::runtime_error("Zero camera-to-surface distance must preserve the input colour exactly");
    inverseProjection[13]=2.0f;inverseProjection[14]=-8.0f;
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    std::cout<<"PASS GPU production composite: zero-distance identity, finite output "<<zeroDistance[0]<<"\n";
    // Change the coordinate basis while preserving the same physical eye ray
    // and shadow projection. This is synthetic affine covariance, not a claim
    // that Iris normally offsets camera-relative coordinates by player height.
    float translatedEye[16],translatedShadow[16];
    std::copy(identity,identity+16,translatedEye);std::copy(identity,identity+16,translatedShadow);
    translatedEye[12]=64.0f;translatedShadow[12]=-64.0f;
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,translatedEye);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,translatedShadow);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),-64.0f,0.0f,0.0f);
    const auto translatedLit=draw(0.0f,1.0f,1.0f);
    for(int c=0;c<3;++c) if(std::abs(translatedLit[c]-lit[c])>0.000001f)
        throw std::runtime_error("Aerial scattering must follow the translated eye ray, not a ray starting at the coordinate origin");
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0.0f,0.0f,0.0f);
    std::cout<<"PASS GPU production composite: translated-eye/shadow covariance, sunlit output "<<translatedLit[0]<<"\n";
    // Exercise the exposed HAZE_DENSITY=0 option. Only the setting definition is
    // changed at compile time; the production fragment body remains untouched.
    std::string zeroDensitySource=expand(root/"composite.fsh",root);
    const auto setting=zeroDensitySource.find("#define HAZE_DENSITY ");
    if(setting==std::string::npos) throw std::runtime_error("Cannot locate public HAZE_DENSITY setting");
    zeroDensitySource.replace(setting,zeroDensitySource.find('\n',setting)-setting,"#define HAZE_DENSITY 0.0");
    const GLuint ordinaryProgram=program;
    program=link(expand(root/"composite.vsh",root),zeroDensitySource,"foreground-zero-haze-probe");
    glUseProgram(program);
    for(int i=0;i<5;++i) glUniform1i(glGetUniformLocation(program,samplers[i]),i);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);glUniform1f(glGetUniformLocation(program,"far"),768);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,2,-8);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,0,0);
    const auto zeroDensity=draw(4.0f,1.0f,1.0f);
    for(int c=0;c<3;++c) if(std::abs(zeroDensity[c]-surface[c])>0.0000001f)
        throw std::runtime_error("HAZE_DENSITY=0 must preserve opaque foreground despite a bright unblocked sun");
    std::cout<<"PASS GPU production composite: HAZE_DENSITY=0 identity, output "<<zeroDensity[0]<<"\n";
    glDeleteProgram(ordinaryProgram);
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(6,textures);glDeleteFramebuffers(1,&framebuffer);
}
void atmosphereLutProbe(const fs::path& root) {
    const int width=32,height=16;
    GLuint program=link(expand(root/"prepare.vsh",root),expand(root/"prepare.fsh",root),"atmosphere-mrt-probe");
    GLuint textures[2],framebuffer;glGenTextures(2,textures);glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    for(int i=0;i<2;++i) {
        glBindTexture(GL_TEXTURE_2D,textures[i]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,textures[i],0);
    }
    const GLenum outputs[2]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,outputs);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Atmosphere MRT framebuffer incomplete");
    glUseProgram(program);glViewport(0,0,width,height);
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity);
    glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),448.5f,65.72f,-383.5f);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0.2f,0.7f,0.3f);
    glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
    std::vector<float> cloudy(width*height*4),clear(cloudy.size());
    glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,cloudy.data());
    glReadBuffer(GL_COLOR_ATTACHMENT1);glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,clear.data());
    float largestDifference=0;
    for(int y=0;y<height;++y) for(int x=0;x<width;++x) {
        size_t base=(y*width+x)*4;
        for(int c=0;c<4;++c) if(!std::isfinite(cloudy[base+c]) || !std::isfinite(clear[base+c])) throw std::runtime_error("Nonfinite atmosphere MRT output");
        if(cloudy[base+3]!=1 || clear[base+3]!=1) throw std::runtime_error("Both atmosphere MRT branches must write their output");
        for(int c=0;c<3;++c) {
            if(y==height-1) {
                if(x==0 && (clear[base+c]<=0 || clear[base+c]>1 || cloudy[base+c]<0 || cloudy[base+c]>clear[base+c]+0.00001f)) throw std::runtime_error("Solar caches must separate atmosphere and cloud extinction");
                if(x>0 && (cloudy[base+c]!=0 || clear[base+c]!=0)) throw std::runtime_error("Both reserved cache rows must exclude sky radiance");
            } else {
                if(clear[base+c]<=0) throw std::runtime_error("Cloud-free atmosphere LUT was not populated");
                largestDifference=std::max(largestDifference,std::abs(cloudy[base+c]-clear[base+c]));
            }
        }
    }
    if(largestDifference<0.001f || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Cloud and atmosphere LUTs must remain independent nondegenerate outputs");
    std::cout<<"PASS GPU production prepare MRT: distinct cloud/atmosphere outputs (max difference "<<largestDifference<<"), both solar cache rows valid\n";
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(2,textures);glDeleteFramebuffers(1,&framebuffer);
}
// The real water vertex/fragment pair views a flat horizontal interface from
// below. Camera-sky colours are deliberately unrelated to two directional LUT
// patches. Both an in-viewport and an off-viewport transmitted ray must select
// that directional sky, not a successful/fallback camera-image UV.
void underwaterSkyProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Underwater sky regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846,eta=1.333;
    const float f=1.0f/std::tan(50.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    // Look vertically upward: world (x,y,z) maps to view (x,z,-y).
    const float view[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float inverseView[16]={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    auto flatWaterSource=[&](const fs::path& file) {
        std::string source=expand(file,root);
        const auto setting=source.find("#define WAVE_HEIGHT ");
        if(setting==std::string::npos) throw std::runtime_error("Cannot configure public WAVE_HEIGHT setting");
        source.replace(setting,source.find('\n',setting)-setting,"#define WAVE_HEIGHT 0.0");
        return source;
    };
    GLuint program=link(flatWaterSource(root/"gbuffers_water.vsh"),flatWaterSource(root/"gbuffers_water.fsh"),"underwater-sky-main-probe","mc_Entity");
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[6]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Underwater sky framebuffer incomplete");
    const float white[4]={1,1,1,1},black[4]={0,0,0,1},skyDepth=1.0f,shadowDepth=0.0f;
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&skyDepth);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==2?skyWidth:1,unit==2?skyHeight:1,0,GL_RGBA,GL_FLOAT,unit==0?white:(unit==5?black:nullptr));
    }
    const int samples[2]={39,50}; // ~20deg in-viewport, ~43deg off-viewport, both below TIR
    const float skyColours[2][3]={{0.2f,0.4f,0.6f},{0.6f,0.2f,0.4f}};
    double transmitted[2][3];
    for(int sample=0;sample<2;++sample) {
        const double tangent=(2.0*(samples[sample]+0.5)/size-1.0)/f;
        const double inverseLength=1.0/std::sqrt(1.0+2.0*tangent*tangent);
        transmitted[sample][0]=transmitted[sample][2]=eta*tangent*inverseLength;
        transmitted[sample][1]=std::sqrt(1.0-2.0*transmitted[sample][0]*transmitted[sample][0]);
        const double candidate=0.5+0.5*f*(tangent+48.0*transmitted[sample][0])/(1.0+48.0*transmitted[sample][1]);
        if((sample==0 && (candidate<0.001 || candidate>0.999)) || (sample==1 && candidate<=0.999))
            throw std::runtime_error("Underwater regression must cover both projected sky success and viewport miss");
        std::cout<<"GPU underwater ray "<<sample<<": incident "<<std::atan(std::sqrt(2.0)*tangent)*180.0/pi<<"deg, projected UV "<<candidate<<", "<<(sample==0?"in viewport":"outside viewport")<<"\n";
    }
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0.0f);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const double azimuth=((x+0.5)/skyWidth-0.5)*2.0*pi,elevation=(double(y)/(skyHeight-2)-0.5)*pi;
        const double ray[3]={std::cos(elevation)*std::cos(azimuth),std::sin(elevation),std::cos(elevation)*std::sin(azimuth)};
        const size_t base=(y*skyWidth+x)*4;
        for(int sample=0;sample<2;++sample) {
            double alignment=0;for(int c=0;c<3;++c) alignment+=ray[c]*transmitted[sample][c];
            if(alignment>std::cos(8.0*pi/180.0)) for(int c=0;c<3;++c) skyPixels[base+c]=skyColours[sample][c];
        }
        skyPixels[base+3]=1.0f;
    }
    // The patches miss all diffuse quadrature directions; the solar cache and
    // block light are zero. Reflection/scattering fallback therefore stays zero.
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,skyWidth,skyHeight,GL_RGBA,GL_FLOAT,skyPixels.data());
    glUseProgram(program);
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8"};
    for(int unit=0;unit<6;++unit) glUniform1i(glGetUniformLocation(program,samplers[unit]),unit);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,view);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverseView);
    for(const char* name:{"shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),1);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);
    glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,-1);
    const GLint material=glGetAttribLocation(program,"mc_Entity");
    if(material<0) throw std::runtime_error("Production water material attribute is missing");
    glDisableVertexAttribArray(material);glVertexAttrib4f(material,10000,0,0,0);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadMatrixf(view);
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadMatrixf(projection);
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    auto draw=[&](const float* cameraSky,const float* basisShift=nullptr) {
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,cameraSky);
        const float extent=1.0f/f;
        const float x=basisShift?basisShift[0]:0.0f,y=basisShift?basisShift[1]:0.0f,z=basisShift?basisShift[2]:0.0f;
        glBegin(GL_QUADS);glVertex3f(x-extent,y+1,z-extent);glVertex3f(x+extent,y+1,z-extent);glVertex3f(x+extent,y+1,z+extent);glVertex3f(x-extent,y+1,z+extent);glEnd();
        std::vector<float> output(size*size*4);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,output.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Underwater production-main GL error");
        for(int pixel:{samples[0],samples[1],32,55}) {
            const size_t base=(pixel*size+pixel)*4;
            for(int c=0;c<4;++c) if(!std::isfinite(output[base+c])) throw std::runtime_error("Nonfinite underwater sky output");
            if(output[base+3]!=1.0f) throw std::runtime_error("Water sky output must remain opaque");
        }
        return output;
    };
    const float redCamera[4]={1.0f,0.01f,0.01f,1.0f},greenCamera[4]={0.01f,1.0f,0.01f,1.0f};
    const auto red=draw(redCamera),green=draw(greenCamera),repeat=draw(redCamera);
    float largestCameraDifference=0.0f,largestColourError=0.0f;
    for(int sample=0;sample<2;++sample) {
        const size_t base=(samples[sample]*size+samples[sample])*4;
        float sum=0;for(int c=0;c<3;++c) sum+=red[base+c];
        const float scale=sum/(skyColours[sample][0]+skyColours[sample][1]+skyColours[sample][2]);
        for(int c=0;c<3;++c) {
            if(std::abs(red[base+c]-repeat[base+c])>0.00001f) throw std::runtime_error("Underwater sky regression is not deterministic");
            largestCameraDifference=std::max(largestCameraDifference,std::abs(red[base+c]-green[base+c]));
            largestColourError=std::max(largestColourError,std::abs(red[base+c]-skyColours[sample][c]*scale));
        }
        std::cout<<"GPU underwater sky "<<sample<<": red camera RGB "<<red[base]<<","<<red[base+1]<<","<<red[base+2]<<"; green camera RGB "<<green[base]<<","<<green[base+1]<<","<<green[base+2]<<"\n";
        if(scale<0.1f || scale>1.01f) throw std::runtime_error("Underwater sky must retain a positive bounded directional-LUT response");
    }
    if(largestCameraDifference>0.00001f || largestColourError>0.0001f)
        throw std::runtime_error("Underwater sky must use transmitted-direction LUT radiance both inside and outside viewport, not camera-sky UVs; camera difference "+std::to_string(largestCameraDifference));
    std::cout<<"PASS GPU production water main: in/off-viewport underwater sky selects directional LUT, camera-image difference "<<largestCameraDifference<<"\n";
    // Independent flat-interface Snell/Fresnel oracle. Reflection illumination
    // is zero in this fixture, so transmitted radiance is (1-R)*directional sky.
    double largestFresnelError=0.0;
    for(int sample=0;sample<2;++sample) {
        const double tangent=(2.0*(samples[sample]+0.5)/size-1.0)/f;
        const double ci=1.0/std::sqrt(1.0+2.0*tangent*tangent);
        const double ct=std::sqrt(1.0-eta*eta*(1.0-ci*ci));
        const double rs=(eta*ci-ct)/(eta*ci+ct),rp=(ci-eta*ct)/(ci+eta*ct);
        const double transmittedFraction=1.0-0.5*(rs*rs+rp*rp);
        const size_t base=(samples[sample]*size+samples[sample])*4;
        for(int c=0;c<3;++c) largestFresnelError=std::max(largestFresnelError,std::abs(red[base+c]-skyColours[sample][c]*transmittedFraction));
    }
    if(largestFresnelError>0.00002) throw std::runtime_error("Production underwater sky must preserve independent dielectric Fresnel attenuation");
    const size_t tirPixel=(55*size+55)*4;
    for(int c=0;c<3;++c) if(std::abs(red[tirPixel+c])>0.000001f || std::abs(green[tirPixel+c])>0.000001f)
        throw std::runtime_error("Above-critical underwater ray must reflect only, not transmit sky or camera-image radiance");
    std::cout<<"PASS GPU production water main: independent Fresnel maximum error "<<largestFresnelError<<", ~50deg TIR transmits no sky\n";
    // A visible opaque plane two metres above the eye is a real geometry hit,
    // not a sky/fallback classification. Preserve its camera-buffer radiance.
    float opaqueDepth=0.5f*(1.0f-a+b/2.0f);
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&opaqueDepth);
    const auto opaqueRed=draw(redCamera),opaqueGreen=draw(greenCamera);
    for(int sample=0;sample<2;++sample) {
        const size_t base=(samples[sample]*size+samples[sample])*4;
        if(opaqueRed[base]<0.5f || opaqueGreen[base+1]<0.5f || opaqueRed[base+1]>0.02f || opaqueGreen[base]>0.02f)
            throw std::runtime_error("Confirmed underwater opaque receiver must retain camera-buffer geometry radiance, not directional sky");
    }
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&skyDepth);
    std::cout<<"PASS GPU production water main: positive opaque receivers retain refracted scene colour\n";
    // The 80m opaque receiver exceeds the trace's 48m limit (or its viewport).
    // With zero skylight this unknown cave ray must not invent bright sky or
    // misclassify the original camera UV as a confirmed visible receiver.
    opaqueDepth=0.5f*(1.0f-a+b/80.0f);
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&opaqueDepth);
    glMultiTexCoord2f(GL_TEXTURE1,0,0);
    const auto caveRed=draw(redCamera),caveGreen=draw(greenCamera);
    float largestCaveValue=0.0f;
    for(int sample=0;sample<2;++sample) for(int c=0;c<3;++c) {
        const size_t base=(samples[sample]*size+samples[sample])*4;
        largestCaveValue=std::max(largestCaveValue,caveRed[base+c]);
        if(caveRed[base+c]<0.0f || caveRed[base+c]>0.0002f || std::abs(caveRed[base+c]-caveGreen[base+c])>0.000001f)
            throw std::runtime_error("Unknown underwater ray in a closed cave must remain dark and independent of unrelated camera colour");
    }
    glMultiTexCoord2f(GL_TEXTURE1,0,1);
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&skyDepth);
    std::cout<<"PASS GPU production water main: closed-cave unknown ray stays dark, max RGB "<<largestCaveValue<<"\n";
    // The bare LUT is black at zenith; positive centre radiance therefore proves
    // the analytic Sun/Moon disks survived the switch to full directional sky.
    // At this small target their fwidth footprint is coarse, so assert presence
    // and boundedness, not calibrated disk energy. The TIR sample must stay dark.
    float solarCache[4]={1,1,1,1};
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solarCache);
    const auto withSun=draw(redCamera);
    const size_t centre=(32*size+32)*4;
    if(withSun[centre]<1.0f || withSun[centre]>360.0f)
        throw std::runtime_error("Underwater full sky must retain the analytic Sun disk omitted from the LUT");
    for(int c=0;c<3;++c) if(std::abs(withSun[tirPixel+c])>0.000001f)
        throw std::runtime_error("Total internal reflection must not leak analytic sunlight from its safe sky substitute");
    solarCache[0]=solarCache[1]=solarCache[2]=0.0f;
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solarCache);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,1);
    const auto withMoon=draw(redCamera);
    if(withMoon[centre]<0.01f || withMoon[centre]>0.24f)
        throw std::runtime_error("Underwater full sky must retain the analytic Moon disk omitted from the LUT");
    for(int c=0;c<3;++c) if(std::abs(withMoon[tirPixel+c])>0.000001f)
        throw std::runtime_error("Total internal reflection must not leak analytic moonlight");
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,-1);
    std::cout<<"PASS GPU production water main: analytic Sun/Moon disks retained (centre red "<<withSun[centre]<<" / "<<withMoon[centre]<<"), neither leaks through TIR\n";
    // A consistent affine basis shift moves eye, surface, shadow coordinates
    // and cameraPosition together. Absolute water geometry and camera view are
    // unchanged; this is not an assumed 1.62m Iris/player-height correction.
    const float shift[3]={0.4f,0.3f,-0.2f};
    float shiftedView[16],shiftedInverse[16],shiftedShadow[16];
    std::copy(view,view+16,shiftedView);std::copy(inverseView,inverseView+16,shiftedInverse);std::copy(identity,identity+16,shiftedShadow);
    shiftedView[12]=-shift[0];shiftedView[13]=-shift[2];shiftedView[14]=shift[1];
    for(int c=0;c<3;++c) {shiftedInverse[12+c]=shift[c];shiftedShadow[12+c]=-shift[c];}
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,shiftedView);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,shiftedInverse);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,shiftedShadow);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),-shift[0],-shift[1],-shift[2]);
    glMatrixMode(GL_MODELVIEW);glLoadMatrixf(shiftedView);
    const auto shifted=draw(redCamera,shift);
    float largestBasisDifference=0.0f;
    for(int pixel:{samples[0],samples[1],55}) for(int c=0;c<3;++c) {
        const size_t base=(pixel*size+pixel)*4;
        largestBasisDifference=std::max(largestBasisDifference,std::abs(shifted[base+c]-red[base+c]));
    }
    std::cout<<"GPU underwater consistent translated eye/surface/shadow/height: largest RGB difference "<<largestBasisDifference<<"\n";
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    if(largestBasisDifference>0.00002f)
        throw std::runtime_error("Water view direction must originate at the inverse-modelview eye, not the coordinate origin");
    std::cout<<"PASS GPU production water main: consistent translated-eye covariance\n";
}
// Render real opaque terrain into both MRT outputs, then run real deferred
// into separate attachments. The receiver-Sun snapshot must agree with its
// producer, remain separate from total RGB, and survive later C5 mutations.
void terrainSunSnapshotProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Terrain Sun snapshot regression requires real NVIDIA GL");
    constexpr int size=8,skyWidth=64,skyHeight=32;
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const float view[16]={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const float inverseView[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float albedo[4]={0.5f,0.25f,0.125f,1},shadowDepth=1;
    GLuint terrain=link(expand(root/"gbuffers_terrain.vsh",root),expand(root/"gbuffers_terrain.fsh",root),"terrain-sun-mrt-probe","mc_Entity");
    GLuint deferred=link(expand(root/"deferred.vsh",root),expand(root/"deferred.fsh",root),"receiver-sun-snapshot-probe");
    GLuint textures[9],framebuffers[2];glGenTextures(9,textures);glGenFramebuffers(2,framebuffers);
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const size_t base=(y*skyWidth+x)*4;
        for(int c=0;c<3;++c) skyPixels[base+c]=0.03f;
        skyPixels[base+3]=1;
    }
    for(int i=0;i<9;++i) {
        glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(i==2 || i==5) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,i==2?1:size,i==2?1:size,0,GL_DEPTH_COMPONENT,GL_FLOAT,i==2?&shadowDepth:nullptr);
            if(i==2) {glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);}
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,i==0?1:(i==1?skyWidth:size),i==0?1:(i==1?skyHeight:size),0,GL_RGBA,GL_FLOAT,i==0?albedo:(i==1?skyPixels.data():nullptr));
    }
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffers[0]);
    for(int i=0;i<2;++i) glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,textures[3+i],0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,textures[5],0);
    const GLenum terrainOutputs[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,terrainOutputs);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Terrain Sun MRT framebuffer incomplete");
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffers[1]);
    for(int i=0;i<3;++i) glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i,GL_TEXTURE_2D,textures[6+i],0);
    const GLenum snapshotOutputs[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2};glDrawBuffers(3,snapshotOutputs);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Receiver Sun snapshot framebuffer incomplete");
    for(GLuint program:{terrain,deferred}) {
        glUseProgram(program);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,view);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverseView);
        for(const char* name:{"gbufferProjectionInverse","shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,1);
        glUniform1i(glGetUniformLocation(program,"colortex6"),1);
    }
    glUseProgram(terrain);glUniform1i(glGetUniformLocation(terrain,"gtexture"),0);glUniform1i(glGetUniformLocation(terrain,"shadowtex0"),2);
    const GLint material=glGetAttribLocation(terrain,"mc_Entity");
    if(material>=0) {glDisableVertexAttribArray(material);glVertexAttrib4f(material,1,0,0,0);}
    glUseProgram(deferred);
    glUniform1i(glGetUniformLocation(deferred,"colortex0"),3);glUniform1i(glGetUniformLocation(deferred,"colortex5"),4);glUniform1i(glGetUniformLocation(deferred,"depthtex1"),5);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT|GL_DEPTH_BUFFER_BIT);
    glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();
    auto readAttachment=[&](int attachment) {
        std::vector<float> pixels(size*size*4);glReadBuffer(GL_COLOR_ATTACHMENT0+attachment);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,pixels.data());
        for(float value:pixels) if(!std::isfinite(value)) throw std::runtime_error("Nonfinite terrain/deferred MRT output");
        return pixels;
    };
    float positiveSun=0,positiveDiffuse=0;
    for(int source=0;source<2;++source) {
        const float solar[4]={source==0?0.25f:0.0f,source==0?0.25f:0.0f,source==0?0.25f:0.0f,1};
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solar);
        // Do not bind any terrain output/depth as a sampled texture during
        // that pass. Deferred has a completely separate output framebuffer.
        for(int unit=0;unit<6;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,unit<3?textures[unit]:0);}
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffers[0]);glDrawBuffers(2,terrainOutputs);glUseProgram(terrain);
        glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LESS);glClearDepth(1);glClear(GL_DEPTH_BUFFER_BIT);
        glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view);
        glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0.5f,1);
        glBegin(GL_QUADS);glVertex3f(-1,-0.5f,-1);glVertex3f(1,-0.5f,-1);glVertex3f(1,-0.5f,1);glVertex3f(-1,-0.5f,1);glEnd();
        const auto total=readAttachment(0),direct=readAttachment(1);
        for(int unit=0;unit<6;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);}
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffers[1]);glDrawBuffers(3,snapshotOutputs);glUseProgram(deferred);glDisable(GL_DEPTH_TEST);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        const auto main=readAttachment(0),opaque=readAttachment(1),snapshot=readAttachment(2);
        for(size_t pixel=0;pixel<total.size();pixel+=4) {
            for(int c=0;c<3;++c) {
                if(direct[pixel+c]<0 || direct[pixel+c]>total[pixel+c]+0.000001f) throw std::runtime_error("Terrain direct Sun must remain a nonnegative component of total receiver RGB");
                if(source==0 && direct[pixel+c]<=0) throw std::runtime_error("Lit terrain failed to produce positive direct Sun");
                if(source==1 && direct[pixel+c]!=0) throw std::runtime_error("Zero solar cache must leave terrain diffuse/block illumination out of direct Sun");
                if(std::abs(main[pixel+c]-total[pixel+c])>0.000001f || std::abs(opaque[pixel+c]-total[pixel+c])>0.000001f || std::abs(snapshot[pixel+c]-direct[pixel+c])>0.000001f)
                    throw std::runtime_error("Real deferred must preserve matching opaque-total and direct-Sun MRT snapshots");
            }
            if(main[pixel+3]!=1 || opaque[pixel+3]!=1 || direct[pixel+3]!=1 || snapshot[pixel+3]!=1) throw std::runtime_error("Terrain/deferred MRT alpha must remain valid");
        }
        if(source==0) {
            positiveSun=direct[0];
            const std::vector<float> lateSun(size*size*4,0.99f);
            glActiveTexture(GL_TEXTURE4);glBindTexture(GL_TEXTURE_2D,textures[4]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,lateSun.data());
            if(readAttachment(2)!=snapshot) throw std::runtime_error("Later opaque-Sun buffer mutations must not mutate the deferred receiver snapshot");
        } else positiveDiffuse=total[0];
    }
    if(positiveDiffuse<=0 || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Terrain Sun MRT regression must retain positive diffuse/block light without GL errors");
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(terrain);glDeleteProgram(deferred);glDeleteTextures(9,textures);glDeleteFramebuffers(2,framebuffers);
    std::cout<<"PASS GPU production terrain/deferred MRT: positive direct Sun "<<positiveSun<<", zero-Sun diffuse/block RGB "<<positiveDiffuse<<", matching immutable C4/C8 snapshots\n";
}
// Real production water above a shallow opaque horizontal bed. The solar
// cache contains zero direct irradiance while the diffuse sky, geometry,
// waves, receiver RGB and all other inputs remain fixed. Moving an absent
// direct source cannot focus that unchanged diffuse/receiver illumination.
void shallowWaterProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Shallow water regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846;
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    // Downward camera: world (x,y,z) maps to view (x,-z,y). Water is
    // one metre below the eye and the real opaque receiver is one metre deeper.
    const float view[16]={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const float inverseView[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    GLuint program=link(expand(root/"gbuffers_water.vsh",root),expand(root/"gbuffers_water.fsh",root),"shallow-water-main-probe","mc_Entity");
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[6]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Shallow water framebuffer incomplete");
    const float white[4]={1,1,1,1},black[4]={0,0,0,1},bedDepth=0.5f*((a*(-2.0f)+b)/2.0f)+0.5f,shadowDepth=1.0f;
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0.0f);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const size_t base=(y*skyWidth+x)*4;
        for(int c=0;c<3;++c) skyPixels[base+c]=0.02f;
        skyPixels[base+3]=1.0f;
    }
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&bedDepth);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==2?skyWidth:1,unit==2?skyHeight:1,0,GL_RGBA,GL_FLOAT,unit==2?skyPixels.data():(unit==5?black:white));
    }
    glUseProgram(program);
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8"};
    for(int unit=0;unit<6;++unit) glUniform1i(glGetUniformLocation(program,samplers[unit]),unit);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,view);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverseView);
    for(const char* name:{"shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
    glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);
    glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);
    glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);
    const GLint material=glGetAttribLocation(program,"mc_Entity");
    if(material<0) throw std::runtime_error("Production water material attribute is missing");
    glDisableVertexAttribArray(material);glVertexAttrib4f(material,10000,0,0,0);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadMatrixf(view);
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadMatrixf(projection);
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    auto draw=[&](const float* receiver,bool highSun) {
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiver);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),highSun?0.0f:1.0f,0,highSun?1.0f:0.01f);
        const float extent=1.4f/f;
        glBegin(GL_QUADS);glVertex3f(-extent,-1,-extent);glVertex3f(extent,-1,-extent);glVertex3f(extent,-1,extent);glVertex3f(-extent,-1,extent);glEnd();
        std::vector<float> output(size*size*4);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,output.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Shallow water production-main GL error");
        for(int y=16;y<49;++y) for(int x=16;x<49;++x) {
            const size_t base=(y*size+x)*4;
            for(int c=0;c<4;++c) if(!std::isfinite(output[base+c])) throw std::runtime_error("Nonfinite shallow water output");
            if(output[base+3]!=1.0f) throw std::runtime_error("Shallow water output must remain opaque");
        }
        return output;
    };
    const float grey[4]={0.4f,0.4f,0.4f,1},red[4]={0.8f,0.1f,0.1f,1};
    const auto low=draw(grey,false),high=draw(grey,true),repeat=draw(grey,false),redReceiver=draw(red,false);
    float largestDirectionDifference=0.0f,largestReceiverDifference=0.0f;
    int worstX=0,worstY=0,worstChannel=0;
    for(int y=16;y<49;++y) for(int x=16;x<49;++x) for(int c=0;c<3;++c) {
        const size_t base=(y*size+x)*4+c;
        if(std::abs(low[base]-repeat[base])>0.000001f) throw std::runtime_error("Shallow water regression is not deterministic");
        const float difference=std::abs(low[base]-high[base]);
        if(difference>largestDirectionDifference) {largestDirectionDifference=difference;worstX=x;worstY=y;worstChannel=c;}
        largestReceiverDifference=std::max(largestReceiverDifference,std::abs(low[base]-redReceiver[base]));
    }
    const size_t worst=(worstY*size+worstX)*4;
    std::cout<<"GPU shallow real bed, zero direct solar cache: changing absent sun direction gives max RGB difference "<<largestDirectionDifference
             <<" at "<<worstX<<","<<worstY<<" channel "<<worstChannel<<"; low RGB "<<low[worst]<<","<<low[worst+1]<<","<<low[worst+2]
             <<"; high RGB "<<high[worst]<<","<<high[worst+1]<<","<<high[worst+2]<<"; receiver RGB control "<<largestReceiverDifference<<"\n";
    if(largestReceiverDifference<0.1f) throw std::runtime_error("Shallow water must still respond to genuine opaque receiver RGB");
    if(largestDirectionDifference>0.00001f) throw std::runtime_error("With zero direct solar energy, shallow water cannot focus unchanged receiver illumination according to an absent sun direction");
    std::cout<<"PASS GPU production water main: zero-direct-source caustic invariance, positive receiver RGB response\n";
    // Keep the total receiver and direct solar illumination fixed. Only the
    // receiver's Sun-attributed component changes from zero to red; focusing
    // must affect that red component, not its unchanged green/blue diffuse RGB.
    const float solar[4]={0.25f,0.25f,0.25f,1},directRed[4]={0.2f,0,0,1};
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solar);
    const auto allDiffuse=draw(grey,true);
    glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,directRed);
    const auto redDirect=draw(grey,true);
    float largestRedFocus=0.0f,largestUnrelatedFocus=0.0f;
    for(int y=16;y<49;++y) for(int x=16;x<49;++x) {
        const size_t base=(y*size+x)*4;
        largestRedFocus=std::max(largestRedFocus,std::abs(redDirect[base]-allDiffuse[base]));
        for(int c=1;c<3;++c) largestUnrelatedFocus=std::max(largestUnrelatedFocus,std::abs(redDirect[base+c]-allDiffuse[base+c]));
    }
    std::cout<<"GPU shallow fixed total receiver/Sun/cache, black to red direct attribution: red focus "<<largestRedFocus<<", unrelated green/blue change "<<largestUnrelatedFocus<<"\n";
    if(largestRedFocus<0.001f || largestUnrelatedFocus>0.00001f) throw std::runtime_error("Water must positively focus only the receiver's direct-Sun component, not diffuse/block illumination");
    std::cout<<"PASS GPU production water main: positive isolated direct-Sun receiver focusing\n";
    // A finite one-pixel shallow shelf lies on the original view ray; beyond
    // its visible footprint is sky. The bent transmitted ray leaves that
    // footprint, which supplies no confirmed opaque refracted receiver. Its
    // original-UV proxy may retain bed colour but must not acquire a caustic.
    constexpr int shelfX=39,shelfY=45;
    std::vector<float> shelfDepth(size*size,1.0f);shelfDepth[shelfY*size+shelfX]=bedDepth;
    glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,size,size,0,GL_RED,GL_FLOAT,shelfDepth.data());
    glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,black);
    const auto unknownDiffuse=draw(grey,true);
    glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,directRed);
    const auto unknownDirect=draw(grey,true);
    float unknownFocus=0.0f;
    const size_t shelf=(shelfY*size+shelfX)*4;
    for(int c=0;c<3;++c) unknownFocus=std::max(unknownFocus,std::abs(unknownDirect[shelf+c]-unknownDiffuse[shelf+c]));
    std::cout<<"GPU shallow finite-shelf unknown receiver: C8 attribution change "<<unknownFocus<<"; black RGB "<<unknownDiffuse[shelf]<<","<<unknownDiffuse[shelf+1]<<","<<unknownDiffuse[shelf+2]
             <<"; red RGB "<<unknownDirect[shelf]<<","<<unknownDirect[shelf+1]<<","<<unknownDirect[shelf+2]<<"\n";
    if(unknownFocus>0.00001f) throw std::runtime_error("An unconfirmed refracted receiver must not focus the original-UV proxy's direct-Sun illumination");
    std::cout<<"PASS GPU production water main: unknown refracted receiver cannot acquire proxy caustics\n";
    // Keep this original pixel's proxy RGB/Sun unchanged. The inward patch is
    // on its transmitted path, proven by positive focusing while it is a real
    // bed. Move only that patch above the interface/in front of the water: its
    // rejected direct-Sun/RGB must not leak through. The reflected ray points
    // outward, away from this inward patch; test its RGB separately as well.
    std::vector<float> fullBedDepth(size*size,bedDepth),bankDepth=fullBedDepth;
    std::vector<float> greyImage(size*size*4),brightBank(size*size*4),blackSun(size*size*4),patchSun(size*size*4);
    const float nearBankDepth=0.5f*((a*(-0.8f)+b)/0.8f)+0.5f;
    for(int y=0;y<size;++y) for(int x=0;x<size;++x) {
        const size_t pixel=y*size+x,base=pixel*4;
        std::copy(grey,grey+4,greyImage.begin()+base);std::copy(grey,grey+4,brightBank.begin()+base);
        std::copy(black,black+4,blackSun.begin()+base);std::copy(black,black+4,patchSun.begin()+base);
        if(x>=20 && x<=38 && y>=20 && y<=44) {
            bankDepth[pixel]=nearBankDepth;
            std::copy(directRed,directRed+4,patchSun.begin()+base);
            brightBank[base]=0.95f;brightBank[base+1]=0.7f;brightBank[base+2]=0.25f;
        }
    }
    auto image=[&](int unit,GLenum format,GLint internalFormat,const std::vector<float>& pixels) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexImage2D(GL_TEXTURE_2D,0,internalFormat,size,size,0,format,GL_FLOAT,pixels.data());
    };
    image(3,GL_RED,GL_R32F,fullBedDepth);image(1,GL_RGBA,GL_RGBA32F,greyImage);image(5,GL_RGBA,GL_RGBA32F,blackSun);
    const auto bedNoSun=draw(grey,true);
    image(5,GL_RGBA,GL_RGBA32F,patchSun);const auto bedPatchSun=draw(grey,true);
    image(3,GL_RED,GL_R32F,bankDepth);image(5,GL_RGBA,GL_RGBA32F,blackSun);const auto bankNoSun=draw(grey,true);
    image(5,GL_RGBA,GL_RGBA32F,patchSun);const auto bankPatchSun=draw(grey,true);
    image(1,GL_RGBA,GL_RGBA32F,brightBank);const auto bankBright=draw(grey,true);
    float genuinePatchResponse=0,bankSunLeak=0,bankRgbLeak=0;
    for(int c=0;c<3;++c) {
        genuinePatchResponse=std::max(genuinePatchResponse,std::abs(bedPatchSun[shelf+c]-bedNoSun[shelf+c]));
        bankSunLeak=std::max(bankSunLeak,std::abs(bankPatchSun[shelf+c]-bankNoSun[shelf+c]));
        bankRgbLeak=std::max(bankRgbLeak,std::abs(bankBright[shelf+c]-bankPatchSun[shelf+c]));
    }
    std::cout<<"GPU shallow candidate patch: real-bed response "<<genuinePatchResponse<<", rejected foreground bank Sun/RGB leaks "<<bankSunLeak<<"/"<<bankRgbLeak<<"\n";
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    if(genuinePatchResponse<0.001f || bankSunLeak>0.00001f || bankRgbLeak>0.00001f) throw std::runtime_error("Real water main must retain a genuine bed while rejecting foreground-bank RGB/Sun without modifying its proxy");
    std::cout<<"PASS GPU production water main: genuine bed control and isolated foreground-bank rejection\n";
}
// A continuous flat bed is projected analytically beneath real tessellated
// wavy water. Only its physical depth varies. Linear depth/colour sampling
// removes texel quantisation as a cause of an apparent acceptance-boundary
// jump. Locate and refine the largest output change without reproducing the
// tracer's acceptance rule: a finite RGB jump must vanish with perturbation.
void shoreContinuityProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Shore continuity regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32,pixelX=32,pixelY=20;
    constexpr double pi=3.14159265358979323846;
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f,eyeToWater=0.5f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadowDepth=1;
    GLuint program=link(expand(root/"gbuffers_water.vsh",root),expand(root/"gbuffers_water.fsh",root),"shore-continuity-main-probe","mc_Entity");
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[6]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Shore continuity framebuffer incomplete");
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0),depthPixels(size*size),colourPixels(size*size*4);
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,(unit==1||unit==3)?GL_LINEAR:GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,(unit==1||unit==3)?GL_LINEAR:GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,size,size,0,GL_RED,GL_FLOAT,nullptr);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==1?size:(unit==2?skyWidth:1),unit==1?size:(unit==2?skyHeight:1),0,GL_RGBA,GL_FLOAT,unit==0?white:(unit==2?skyPixels.data():(unit==5?black:nullptr)));
    }
    glUseProgram(program);
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8"};
    for(int unit=0;unit<6;++unit) glUniform1i(glGetUniformLocation(program,samplers[unit]),unit);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    for(const char* name:{"gbufferModelView","gbufferModelViewInverse","shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);
    glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);
    glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
    const GLint material=glGetAttribLocation(program,"mc_Entity");
    if(material<0) throw std::runtime_error("Production water material attribute is missing");
    glDisableVertexAttribArray(material);glVertexAttrib4f(material,10000,0,0,0);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT|GL_COLOR_BUFFER_BIT);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadMatrixf(projection);
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);glClearColor(0,0,0,0);
    auto draw=[&](float bedBelowWater) {
        for(int y=0;y<size;++y) for(int x=0;x<size;++x) {
            const float rayY=(2.0f*(y+0.5f)/size-1.0f)/f;
            const float travel=rayY<0?(eyeToWater+bedBelowWater)/(-rayY):farPlane+1;
            const size_t pixel=y*size+x,base=pixel*4;
            depthPixels[pixel]=travel<farPlane?0.5f*((a*(-travel)+b)/travel)+0.5f:1.0f;
            colourPixels[base]=travel<farPlane?0.2f:0.0f;colourPixels[base+1]=travel<farPlane?0.25f:0.0f;
            colourPixels[base+2]=travel<farPlane?0.5f+0.35f*std::sin(-travel*0.18f):0.0f;colourPixels[base+3]=1;
        }
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,colourPixels.data());
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RED,GL_FLOAT,depthPixels.data());
        glClear(GL_COLOR_BUFFER_BIT);glBegin(GL_QUADS);
        for(int z=-24;z<0;++z) for(int x=-8;x<8;++x) {
            glVertex3f(x,-eyeToWater,z);glVertex3f(x+1,-eyeToWater,z);glVertex3f(x+1,-eyeToWater,z+1);glVertex3f(x,-eyeToWater,z+1);
        }
        glEnd();
        std::vector<float> output(4);glReadPixels(pixelX,pixelY,1,1,GL_RGBA,GL_FLOAT,output.data());
        for(float value:output) if(!std::isfinite(value)) throw std::runtime_error("Nonfinite shore continuity output");
        if(output[3]!=1 || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Shore continuity production-main geometry/GL failure");
        return output;
    };
    auto difference=[](const std::vector<float>& left,const std::vector<float>& right) {
        float largest=0;for(int c=0;c<3;++c) largest=std::max(largest,std::abs(left[c]-right[c]));return largest;
    };
    float lower=1.2f,upper=lower,largestStep=0;
    auto previous=draw(lower),left=previous,right=previous;
    for(int step=1;step<=380;++step) {
        const float depth=1.2f+step*0.01f;const auto output=draw(depth);
        const float change=difference(previous,output);
        if(change>largestStep) {largestStep=change;lower=depth-0.01f;upper=depth;left=previous;right=output;}
        previous=output;
    }
    std::cout<<"GPU continuous bed coarse boundary: depth "<<lower<<".."<<upper<<"m, RGB change "<<largestStep<<"\n";
    for(int refine=0;refine<8;++refine) {
        const float midpoint=0.5f*(lower+upper);const auto middle=draw(midpoint);
        if(difference(left,middle)>difference(middle,right)) {upper=midpoint;right=middle;}
        else {lower=midpoint;left=middle;}
    }
    const float fineChange=difference(left,right);
    std::cout<<"GPU continuous bed refined boundary: depth "<<lower<<".."<<upper<<"m, perturbation "<<(upper-lower)<<"m, RGB change "<<fineChange
             <<"; lower RGB "<<left[0]<<","<<left[1]<<","<<left[2]<<"; upper RGB "<<right[0]<<","<<right[1]<<","<<right[2]<<"\n";
    // Keep the original RED interval as an explicit regression, rather than
    // allowing the output-guided search to silently pick a different seam.
    const float originalCoarse=difference(draw(2.59f),draw(2.60f));
    const float originalFine=difference(draw(2.59984375f),draw(2.5998828125f));
    std::cout<<"GPU original continuous-bed RED interval: 0.01m RGB change "<<originalCoarse<<", 3.90625e-05m RGB change "<<originalFine<<"\n";
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    if(fineChange>std::max(0.00001f,largestStep*0.1f)) throw std::runtime_error("A continuous receiver must not retain a finite refraction hit/fallback RGB jump as physical depth perturbation tends to zero");
    if(originalFine>std::max(0.00001f,originalCoarse*0.1f)) throw std::runtime_error("The original continuous-bed RED boundary must remain continuous under diminishing physical depth perturbation");
    std::cout<<"PASS GPU production water main: continuous receiver RGB change vanishes with physical depth perturbation\n";
}
// Underwater production composite views a real opaque bed below the active
// surface plane. An absent direct Sun must not focus the fixed total receiver
// radiance; depth, diffuse sky, shadow, waves and direct-Sun snapshot stay fixed.
void underwaterCausticProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Underwater caustic regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846;
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float inverseView[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const float shadowProjection[16]={0.25f,0,0,0,0,0.25f,0,0,0,0,0.25f,0,0,0,0,1};
    const float black[4]={0,0,0,1},bedDepth=0.5f*((a*(-1.0f)+b)/1.0f)+0.5f,shadowDepth=1;
    GLuint program=link(expand(root/"composite.vsh",root),expand(root/"composite.fsh",root),"underwater-caustic-main-probe");
    GLuint textures[8],framebuffer;glGenTextures(8,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[7]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[7],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Underwater caustic framebuffer incomplete");
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const size_t base=(y*skyWidth+x)*4;for(int c=0;c<3;++c) skyPixels[base+c]=0.02f;skyPixels[base+3]=1;
    }
    for(int unit=0;unit<7;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==1 || unit==6) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&bedDepth);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,(unit==2||unit==3)?skyWidth:1,(unit==2||unit==3)?skyHeight:1,0,GL_RGBA,GL_FLOAT,(unit==2||unit==3)?skyPixels.data():black);
    }
    glUseProgram(program);glUniform1i(glGetUniformLocation(program,"colortex0"),0);glUniform1i(glGetUniformLocation(program,"depthtex0"),1);
    glUniform1i(glGetUniformLocation(program,"depthtex1"),6);glUniform1i(glGetUniformLocation(program,"colortex6"),2);glUniform1i(glGetUniformLocation(program,"colortex7"),3);
    glUniform1i(glGetUniformLocation(program,"shadowtex0"),4);glUniform1i(glGetUniformLocation(program,"colortex8"),5);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverseView);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),1);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"aqualumenActive"),1);
    glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,0.5f);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
    glUniform1f(glGetUniformLocation(program,"far"),128);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();
    auto draw=[&](const float* receiver,bool highSun) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[0]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiver);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),highSun?0.0f:1.0f,0,highSun?1.0f:0.01f);
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        std::vector<float> output(size*size*4);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,output.data());
        for(int y=16;y<49;++y) for(int x=16;x<49;++x) {
            const size_t base=(y*size+x)*4;for(int c=0;c<4;++c) if(!std::isfinite(output[base+c])) throw std::runtime_error("Nonfinite underwater caustic output");
            if(output[base+3]!=1) throw std::runtime_error("Underwater composite alpha must remain one");
        }
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Underwater caustic production-main GL failure");
        return output;
    };
    const float grey[4]={0.4f,0.4f,0.4f,1},red[4]={0.8f,0.1f,0.1f,1};
    const auto low=draw(grey,false),high=draw(grey,true),repeat=draw(grey,false),redReceiver=draw(red,false);
    float largestDirectionDifference=0,largestReceiverDifference=0;
    for(int y=16;y<49;++y) for(int x=16;x<49;++x) for(int c=0;c<3;++c) {
        const size_t base=(y*size+x)*4+c;
        if(std::abs(low[base]-repeat[base])>0.000001f) throw std::runtime_error("Underwater caustic regression must be deterministic");
        largestDirectionDifference=std::max(largestDirectionDifference,std::abs(low[base]-high[base]));
        largestReceiverDifference=std::max(largestReceiverDifference,std::abs(low[base]-redReceiver[base]));
    }
    std::cout<<"GPU production underwater composite zero solar/C8: absent-Sun direction RGB difference "<<largestDirectionDifference<<", actual receiver RGB response "<<largestReceiverDifference<<"\n";
    if(largestReceiverDifference<0.1f) throw std::runtime_error("Underwater composite must retain genuine receiver RGB");
    if(largestDirectionDifference>0.00001f) throw std::runtime_error("Underwater composite cannot focus fixed receiver illumination using an absent direct Sun");
    std::cout<<"PASS GPU production underwater composite: zero-direct-source caustic invariance, genuine receiver RGB response\n";
    const float solar[4]={0.25f,0.25f,0.25f,1},directRed[4]={0.2f,0,0,1};
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solar);
    const auto allDiffuse=draw(grey,true);
    glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,directRed);
    const auto redDirect=draw(grey,true);
    float largestRedFocus=0,largestUnrelatedFocus=0;
    for(int y=16;y<49;++y) for(int x=16;x<49;++x) {
        const size_t base=(y*size+x)*4;
        largestRedFocus=std::max(largestRedFocus,std::abs(redDirect[base]-allDiffuse[base]));
        for(int c=1;c<3;++c) largestUnrelatedFocus=std::max(largestUnrelatedFocus,std::abs(redDirect[base+c]-allDiffuse[base+c]));
    }
    std::cout<<"GPU production underwater composite fixed C0/Sun/cache, red-only C8: red focus "<<largestRedFocus<<", unrelated green/blue change "<<largestUnrelatedFocus<<"\n";
    if(largestRedFocus<0.001f || largestUnrelatedFocus>0.00001f) throw std::runtime_error("Underwater composite must focus only positive direct-Sun receiver attribution");
    std::cout<<"PASS GPU production underwater composite: positive isolated direct-Sun focusing\n";
    constexpr int depthSize=64;
    std::vector<float> matchedDepth(depthSize*depthSize),nearerDepth(depthSize*depthSize);
    for(int y=0;y<depthSize;++y) for(int x=0;x<depthSize;++x) {
        // Perspective depth is affine in UV for an inclined plane. Use a
        // nonconstant field and a different input/output resolution so LINEAR
        // sampling genuinely interpolates, rather than testing a scalar texel.
        const float value=bedDepth+0.014f*(float(x)/(depthSize-1)-0.5f)+0.006f*(float(y)/(depthSize-1)-0.5f);
        matchedDepth[y*depthSize+x]=value;nearerDepth[y*depthSize+x]=value-0.025f;
    }
    auto attribution=[&](const float* colour) {
        std::vector<float> pixels(depthSize*depthSize*4);
        for(size_t base=0;base<pixels.size();base+=4) std::copy(colour,colour+4,pixels.begin()+base);
        glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);
        // C8 shares the exact opaque-depth pixel grid, as in real Iris.
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,depthSize,depthSize,0,GL_RGBA,GL_FLOAT,pixels.data());
    };
    for(GLint filter:{GL_NEAREST,GL_LINEAR}) {
        for(int unit:{1,6}) {
            glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);
            glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,depthSize,depthSize,0,GL_RED,GL_FLOAT,matchedDepth.data());
        }
        attribution(black);
        const auto matchedDiffuse=draw(grey,true);
        attribution(directRed);
        const auto matchedDirect=draw(grey,true);
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,depthSize,depthSize,GL_RED,GL_FLOAT,nearerDepth.data());
        attribution(black);
        const auto mismatchedDiffuse=draw(grey,true);
        attribution(directRed);
        const auto mismatchedDirect=draw(grey,true);
        float matchedFocus=0,mismatchedFocus=0;
        for(int y=16;y<49;++y) for(int x=16;x<49;++x) for(int c=0;c<3;++c) {
            const size_t base=(y*size+x)*4+c;
            matchedFocus=std::max(matchedFocus,std::abs(matchedDirect[base]-matchedDiffuse[base]));
            mismatchedFocus=std::max(mismatchedFocus,std::abs(mismatchedDirect[base]-mismatchedDiffuse[base]));
        }
        std::cout<<"GPU underwater composite "<<(filter==GL_NEAREST?"NEAREST":"LINEAR")<<" varying-depth inputs: matched positive focus "<<matchedFocus<<", nearer surface's behind-Sun leak "<<mismatchedFocus<<"\n";
        if(matchedFocus<0.001f || mismatchedFocus>0.00001f) throw std::runtime_error("Underwater composite must focus matching opaque receiver provenance and reject a nearer depth-writing layer");
    }
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(8,textures);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"PASS GPU production underwater composite: filtered matching-depth focus and mismatched-layer rejection\n";
}
int main(int argc,char** argv) {
    try {
        if(argc<2) throw std::runtime_error("usage: glcheck <shaders> [width height | --foreground-haze-probe | --underwater-sky-only | --shallow-water-only | --shore-continuity-only | --underwater-caustic-only]");
        const bool foregroundHazeOnly=argc>2 && std::string(argv[2])=="--foreground-haze-probe";
        const bool underwaterSkyOnly=argc>2 && std::string(argv[2])=="--underwater-sky-only";
        const bool shallowWaterOnly=argc>2 && std::string(argv[2])=="--shallow-water-only";
        const bool shoreContinuityOnly=argc>2 && std::string(argv[2])=="--shore-continuity-only";
        const bool underwaterCausticOnly=argc>2 && std::string(argv[2])=="--underwater-caustic-only";
        auto getPlatform=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
        EGLDisplay display=getPlatform(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
        if(!eglInitialize(display,nullptr,nullptr)) {
            auto query=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
            EGLDeviceEXT devices[8];EGLint count=0;
            if(!query || !query(8,devices,&count) || count==0) throw std::runtime_error("No EGL device");
            display=getPlatform(EGL_PLATFORM_DEVICE_EXT,devices[0],nullptr);
            if(!eglInitialize(display,nullptr,nullptr)) throw std::runtime_error("Cannot initialize EGL device");
        }
        eglBindAPI(EGL_OPENGL_API);
        EGLint cfg[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;EGLint count;eglChooseConfig(display,cfg,&config,1,&count);
        if(!count) throw std::runtime_error("No EGL config");
        int width=(underwaterSkyOnly||shallowWaterOnly||shoreContinuityOnly||underwaterCausticOnly)?65:(foregroundHazeOnly?16:(argc>2?std::stoi(argv[2]):2560)),height=(underwaterSkyOnly||shallowWaterOnly||shoreContinuityOnly||underwaterCausticOnly)?65:(foregroundHazeOnly?16:(argc>3?std::stoi(argv[3]):1440));
        EGLint surfaceAttrs[]={EGL_WIDTH,width,EGL_HEIGHT,height,EGL_NONE};
        EGLSurface surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("Cannot create GL compatibility context");
        std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\nGL: "<<glGetString(GL_VERSION)<<'\n';
        fs::path root=argv[1];
        if(foregroundHazeOnly || underwaterSkyOnly || shallowWaterOnly || shoreContinuityOnly || underwaterCausticOnly) {
            if(underwaterCausticOnly) underwaterCausticProbe(root);else if(shoreContinuityOnly) shoreContinuityProbe(root);else if(shallowWaterOnly) {shallowWaterProbe(root);terrainSunSnapshotProbe(root);shoreContinuityProbe(root);}else if(underwaterSkyOnly) underwaterSkyProbe(root);else foregroundShadowHazeProbe(root);
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        std::vector<fs::path> files;
        for(auto& entry:fs::directory_iterator(root)) if(entry.path().extension()==".vsh") files.push_back(entry.path());
        std::sort(files.begin(),files.end());
        for(auto file:files) {
            auto fragment=file;fragment.replace_extension(".fsh");
            GLuint program=link(expand(file,root),expand(fragment,root),file.stem().string());
            glDeleteProgram(program);std::cout<<"PASS "<<file.stem().string()<<'\n';
        }
        rippleProbe(root);
        GLuint framebuffer,texture;
        glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Probe framebuffer incomplete");
        std::string probe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/water.glsl",root)+
            "void main(){gl_FragColor=vec4(waterFresnel(1.0,1.0,1.333),waterFresnel(0.0,1.0,1.333),waterFresnel(0.5,1.333,1.0),waterTransmission(10.0).r);}";
        GLuint physics=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",probe,"physics-probe");
        glUseProgram(physics);glViewport(0,0,1,1);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        float measured[4];glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        const float expected[4]={0.02037319f,1.0f,1.0f,0.04076220f};
        for(int i=0;i<4;++i) if(!std::isfinite(measured[i]) || std::abs(measured[i]-expected[i])>0.00001f) throw std::runtime_error("Water physics GPU probe failed at channel "+std::to_string(i));
        std::cout<<"PASS GPU physics: normal-incidence Fresnel, grazing reflection, total internal reflection, 10m red extinction\n";
        glDeleteProgram(physics);
        std::string pathProbe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/water.glsl",root)+
            "void main(){vec3 ray=vec3(1.0/1.333,-sqrt(1.0-1.0/(1.333*1.333)),0.0);gl_FragColor=vec4(waterRefractionPath(1.0,ray,20.0,true,false),waterRefractionPath(1.0,ray,20.0,false,false),waterRefractionPath(1.0,ray,20.0,true,true),waterRefractionPath(0.0,ray,20.0,true,false));}";
        GLuint path=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",pathProbe,"water-path-probe");
        glUseProgram(path);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        const float snellPath=1.0f/std::sqrt(1.0f-1.0f/(1.333f*1.333f));
        if(!std::isfinite(measured[0]) || std::abs(measured[0]-snellPath)>0.00001f || measured[1]!=20 || measured[2]!=20 || measured[3]!=0)
            throw std::runtime_error("Shallow-water path must use Snell depth, preserve side/underwater paths and vanish at zero depth");
        std::cout<<"PASS GPU shallow refraction seed: 1m shore gives "<<measured[0]<<"m Snell path, not 20m grazing view distance; side/underwater preserved\n";
        glDeleteProgram(path);
        // Exercise the actual production tracer against a depth texture whose
        // first candidate is valid but whose next iterate projects offscreen.
        std::string waterSource=expand(root/"gbuffers_water.fsh",root);
        auto traceStart=waterSource.find("vec2 refractionTrace(");
        auto traceEnd=waterSource.find("\nvoid main()",traceStart);
        if(traceStart==std::string::npos || traceEnd==std::string::npos) throw std::runtime_error("Cannot locate production refraction tracer");
        std::string traceProbe="#version 330 compatibility\n"+expand(root/"lib/uniforms.glsl",root)+
            "uniform sampler2D depthtex1;uniform int traceCase;\n"+waterSource.substr(traceStart,traceEnd-traceStart)+
            "void main(){float distance;int receiverKind;float receiverConfidence;vec3 ray=traceCase==0?normalize(vec3(0.7,-0.7,-0.14)):vec3(0,0,-1);float seed=traceCase==0?0.3:1.0;vec2 hit=refractionTrace(vec3(0),ray,vec2(0.5),seed,true,0.0,distance,receiverKind,receiverConfidence);gl_FragColor=vec4(hit,distance,float(receiverKind));}";
        GLuint trace=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",traceProbe,"refraction-fallback-probe");
        GLuint depthTexture;glGenTextures(1,&depthTexture);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,depthTexture);
        float receiverDepth=0.05f;glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&receiverDepth);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glUseProgram(trace);glUniform1i(glGetUniformLocation(trace,"depthtex1"),0);
        const float traceIdentity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for(const char* name:{"gbufferProjection","gbufferProjectionInverse","gbufferModelViewInverse"})
            glUniformMatrix4fv(glGetUniformLocation(trace,name),1,GL_FALSE,traceIdentity);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        if(std::abs(measured[0]-0.5f)>0.00001f || std::abs(measured[1]-0.5f)>0.00001f || std::abs(measured[2]-0.3f)>0.00001f || measured[3]!=0.0f)
            throw std::runtime_error("Unconverged refraction must preserve original UV and Snell-depth fallback; path "+std::to_string(measured[2]));
        std::cout<<"PASS GPU production refraction trace: offscreen after unconverged iterate preserves original UV/path, classifies miss (not opaque)\n";
        receiverDepth=0.0f;glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&receiverDepth);
        glUniform1i(glGetUniformLocation(trace,"traceCase"),1);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        if(std::abs(measured[0]-0.5f)>0.00001f || std::abs(measured[1]-0.5f)>0.00001f || measured[2]!=1.0f || measured[3]!=1.0f)
            throw std::runtime_error("Converged refraction must commit the valid ray-distance hit");
        std::cout<<"PASS GPU production refraction trace: converged receiver commits valid 1m opaque hit\n";
        glDeleteProgram(trace);glDeleteTextures(1,&depthTexture);
        std::string scatterProbe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/water.glsl",root)+
            "void main(){vec3 dark=waterScatterRadiance(vec3(0));vec3 lit=waterScatterRadiance(vec3(1));gl_FragColor=vec4(max(dark.r,max(dark.g,dark.b)),lit.r,lit.b,waterScatterRadiance(vec3(-1)).b);}";
        GLuint scatter=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",scatterProbe,"water-scatter-probe");
        glUseProgram(scatter);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        if(measured[0]!=0 || measured[3]!=0 || !std::isfinite(measured[1]) || !std::isfinite(measured[2]) || measured[1]<=0 || measured[2]<=measured[1] || measured[2]>1.0f/(4.0f*3.141593f))
            throw std::runtime_error("Water scatter must be non-emitting, light-coupled and bounded");
        std::cout<<"PASS GPU water scattering: zero illumination emits zero; positive bounded response\n";
        glDeleteProgram(scatter);
        // This solar-column value has an independent high-resolution CPU
        // reference (~0.74646 blue); sixteen quadratic intervals yield ~0.74913.
        // It detects returning to coarse uniform steps that miss near-ground Mie.
        std::string atmosphereProbe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)+
            "void main(){gl_FragColor=vec4(solarTransmission(vec3(0.0,1.0,0.0),2.0),earthAtmosphere()?1.0:0.0);}";
        GLuint atmosphere=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",atmosphereProbe,"atmosphere-probe");
        glUseProgram(atmosphere);glUniform1i(glGetUniformLocation(atmosphere,"aqualumenDimension"),0);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        for(int i=0;i<3;++i) if(!std::isfinite(measured[i]) || measured[i]<=0 || measured[i]>1) throw std::runtime_error("Atmosphere solar transmission GPU output invalid");
        if(std::abs(measured[2]-0.74913f)>0.01f || measured[3]!=1.0f) throw std::runtime_error("Atmosphere near-ground solar column GPU probe failed");
        std::cout<<"PASS GPU atmosphere: near-ground Mie/Rayleigh solar column, zenith blue transmission "<<measured[2]<<" (reference 0.74646)\n";
        // Public sky lookup on a deliberately NEAREST-filtered texture: sky
        // reconstruction must blend samples, wrap azimuth and exclude the cache.
        GLuint skyTexture;glGenTextures(1,&skyTexture);glBindTexture(GL_TEXTURE_2D,skyTexture);
        float skyPixels[4*4*4];const float row[4]={0.1f,0.2f,0.6f,0.7f};
        for(int y=0;y<4;y++) for(int x=0;x<4;x++) for(int c=0;c<4;c++)
            skyPixels[(y*4+x)*4+c]=c==3?1.0f:(y==3?99.0f:y==2?0.15f:y==1?row[x]:0.05f);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,4,4,0,GL_RGBA,GL_FLOAT,skyPixels);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        std::string skyProbe="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)+
            "uniform sampler2D probeLut;void main(){gl_FragColor=vec4(sampleSky(probeLut,vec3(1,0,0)).r,sampleSky(probeLut,vec3(0,1,0)).r,sampleSky(probeLut,vec3(-1,0,0)).r,cachedSolarTransmission(probeLut).r);}";
        GLuint skyProgram=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",skyProbe,"sky-filter-probe");
        glUseProgram(skyProgram);glUniform1i(glGetUniformLocation(skyProgram,"probeLut"),0);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        const float skyExpected[4]={0.4f,0.15f,0.4f,99.0f};
        for(int i=0;i<4;i++) if(!std::isfinite(measured[i]) || std::abs(measured[i]-skyExpected[i])>0.0001f)
            throw std::runtime_error("Sky reconstruction must filter, wrap longitude and exclude reserved cache row; channel "+std::to_string(i)+" measured "+std::to_string(measured[i]));
        std::cout<<"PASS GPU sky lookup: bilinear reconstruction, azimuth wrap, solar-row exclusion\n";
        glDeleteProgram(skyProgram);glDeleteTextures(1,&skyTexture);
        glUseProgram(0);glDeleteProgram(atmosphere);glDeleteTextures(1,&texture);glDeleteFramebuffers(1,&framebuffer);
        // Exercise the actual final display pass with constant HDR inputs, not
        // a copied tone formula. Distinct bright radiances must remain distinct.
        GLuint displayProgram=link(expand(root/"final.vsh",root),expand(root/"final.fsh",root),"display-probe");
        GLuint displayTextures[2],displayFramebuffer;
        glGenTextures(2,displayTextures);glGenFramebuffers(1,&displayFramebuffer);
        glBindFramebuffer(GL_FRAMEBUFFER,displayFramebuffer);
        glBindTexture(GL_TEXTURE_2D,displayTextures[1]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,displayTextures[1],0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Display probe framebuffer incomplete");
        glUseProgram(displayProgram);
        glUniform1i(glGetUniformLocation(displayProgram,"colortex0"),0);
        glUniform1i(glGetUniformLocation(displayProgram,"aqualumenDimension"),1);
        glUniform1f(glGetUniformLocation(displayProgram,"viewWidth"),1);
        glUniform1f(glGetUniformLocation(displayProgram,"viewHeight"),1);
        const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        glUniformMatrix4fv(glGetUniformLocation(displayProgram,"gbufferModelViewInverse"),1,GL_FALSE,identity);
        glUniform3f(glGetUniformLocation(displayProgram,"sunPosition"),0,1,0);
        auto displaySample=[&](float value) {
            const float pixel[4]={value,value,value,1};
            glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,displayTextures[0]);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,pixel);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
            glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
            float out[4];glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,out);
            if(!std::isfinite(out[0]) || out[0]<0 || out[0]>1) throw std::runtime_error("Display tone output invalid");
            return out[0];
        };
        float bright=displaySample(16),brighter=displaySample(64);
        if(brighter-bright<0.001f || brighter>=1.0f) throw std::runtime_error("Display highlight shoulder clips distinct HDR radiances");
        std::cout<<"PASS GPU display: HDR16 "<<bright<<", HDR64 "<<brighter<<" remain distinct below display white\n";
        glUseProgram(0);glDeleteProgram(displayProgram);glDeleteTextures(2,displayTextures);glDeleteFramebuffers(1,&displayFramebuffer);
        foregroundCloudProbe(root);
        foregroundShadowHazeProbe(root);
        atmosphereLutProbe(root);
        underwaterSkyProbe(root);
        shallowWaterProbe(root);
        terrainSunSnapshotProbe(root);
        shoreContinuityProbe(root);
        underwaterCausticProbe(root);
        std::cout<<files.size()<<" program pairs compiled and linked. This is not a Minecraft FPS benchmark.\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        return 0;
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
