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
#include <array>
#include <iomanip>
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
#include "solar-radiometry-probe.h"

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
    // At this coarse target assert presence and the physical peak-radiance
    // bound, not integrated disk energy. Coverage cannot exceed one; the old
    // SOLAR*20 upper bound is invalid after disk/beam energy calibration.
    // The independent angular-integral probe checks the actual energy, while
    // this underwater regression still requires the TIR sample to stay dark.
    float solarCache[4]={1,1,1,1};
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,textures[2]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,solarCache);
    const auto withSun=draw(redCamera);
    const size_t centre=(32*size+32)*4;
    const std::string solarSource=expand(root/"prepare.fsh",root);
    const auto sourceSolar=aqualumenSolarProbeDetail::declaredSolar(solarSource);
    const std::regex radiusDeclaration("const\\s+float\\s+SUN_ANGULAR_RADIUS\\s*=\\s*([0-9]+(?:\\.[0-9]*)?)\\s*;");
    std::smatch radiusMatch;
    if(!std::regex_search(solarSource,radiusMatch,radiusDeclaration))
        throw std::runtime_error("Underwater Sun bound requires the public angular-radius declaration");
    const double radius=std::stod(radiusMatch[1]);
    if(!std::isfinite(radius) || radius<=0 || radius>=pi/2)
        throw std::runtime_error("Underwater Sun bound requires a positive finite angular radius below pi/2");
    const double normalReflectance=std::pow((eta-1)/(eta+1),2);
    const double transmittedPeak=(1-normalReflectance)/(pi*std::pow(std::sin(radius),2));
    std::cout<<"GPU underwater analytic Sun presence centre red "<<withSun[centre]
             <<"; calibrated transmitted peak bound "<<sourceSolar[0]*transmittedPeak<<"\n";
    if(withSun[centre]<1.0f)
        throw std::runtime_error("Underwater full sky must retain the analytic Sun disk omitted from the LUT");
    for(int c=0;c<3;++c) if(withSun[centre+c]<0 || withSun[centre+c]>sourceSolar[c]*transmittedPeak*(1+1e-5))
        throw std::runtime_error("Underwater analytic Sun must not exceed its unit-coverage Fresnel peak bound");
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
    // This fixture has a confirmed horizontal column: mean surface Y=-1,
    // solid bed Y=-2. Keep its positive receiver control under the new public
    // local-depth interface, rather than silently treating missing data as 1m.
    GLuint shallowColumnTexture;glGenTextures(1,&shallowColumnTexture);
    glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,shallowColumnTexture);
    const float shallowColumn[4]={1,-1,1,0};
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,shallowColumn);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glUniform1i(glGetUniformLocation(program,"aqualumenBathymetry"),6);
    glUniform4f(glGetUniformLocation(program,"aqualumenBathymetryGrid"),-32,-32,64,-1);
    glUniform1i(glGetUniformLocation(program,"aqualumenBathymetryReady"),1);
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
    // receiver's Sun-attributed component changes from zero to red. This tests
    // channel attribution, not positive focusing: incident Sun replacement
    // also changes the base direct term while total receiver RGB stays fixed.
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
    std::cout<<"GPU shallow fixed total receiver/Sun/cache, black to red direct attribution: red-only receiver attribution delta "<<largestRedFocus<<", unrelated green/blue change "<<largestUnrelatedFocus<<"\n";
    if(largestRedFocus<0.001f || largestUnrelatedFocus>0.00001f) throw std::runtime_error("Water must respond only in the receiver's Sun-attributed red channel, not unchanged diffuse/block green or blue");
    std::cout<<"PASS GPU production water main: isolated direct-Sun receiver attribution\n";
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
    glDeleteTextures(1,&shallowColumnTexture);
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
    // With fixed total C0, varying C8 measures isolated receiver attribution,
    // including replacement by incoming attenuation; it is not a focus oracle.
    std::cout<<"GPU production underwater composite fixed C0/Sun/cache, red-only C8: red-only receiver attribution delta "<<largestRedFocus<<", unrelated green/blue change "<<largestUnrelatedFocus<<"\n";
    if(largestRedFocus<0.001f || largestUnrelatedFocus>0.00001f) throw std::runtime_error("Underwater composite must retain isolated direct-Sun receiver attribution");
    std::cout<<"PASS GPU production underwater composite: isolated direct-Sun receiver attribution\n";
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
        std::cout<<"GPU underwater composite "<<(filter==GL_NEAREST?"NEAREST":"LINEAR")<<" varying-depth inputs: matched receiver attribution delta "<<matchedFocus<<", nearer surface's behind-Sun leak "<<mismatchedFocus<<"\n";
        if(matchedFocus<0.001f || mismatchedFocus>0.00001f) throw std::runtime_error("Underwater composite must retain matching opaque receiver attribution and reject a nearer depth-writing layer");
    }
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(8,textures);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"PASS GPU production underwater composite: filtered matching-depth attribution and mismatched-layer rejection\n";
}
// The real underwater composite must transport the receiver's raw direct Sun
// through the surface-to-bed water leg, not just the fixed bed-to-eye leg.
// Use the legal flat-wave/clarity settings; paired receiver-Sun draws cancel
// common diffuse/medium scattering without replacing any production shader.
void waterIncidentDepthProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Water incident-depth regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846,clarity=1.0;
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float inverseView[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const float shadowProjection[16]={0.25f,0,0,0,0,0.25f,0,0,0,0,0.25f,0,0,0,0,1};
    std::string fragment=expand(root/"composite.fsh",root);
    for(const auto& setting:std::vector<std::pair<std::string,std::string>>{{"WAVE_HEIGHT","0.0"},{"WATER_CLARITY","1.0"}}) {
        const auto start=fragment.find("#define "+setting.first+" ");
        if(start==std::string::npos) throw std::runtime_error("Cannot configure public "+setting.first+" setting");
        fragment.replace(start,fragment.find('\n',start)-start,"#define "+setting.first+" "+setting.second);
    }
    GLuint program=link(expand(root/"composite.vsh",root),fragment,"water-incident-depth-main-probe");
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[6]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Water incident-depth framebuffer incomplete");
    const float black[4]={0,0,0,1},bedDepth=0.5f*((a*(-1.0f)+b)/1.0f)+0.5f,shadowDepth=1;
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const size_t base=(y*skyWidth+x)*4;for(int c=0;c<3;++c) skyPixels[base+c]=0.02f;skyPixels[base+3]=1;
    }
    for(int c=0;c<3;++c) skyPixels[((skyHeight-1)*skyWidth)*4+c]=0.25f;
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==1) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&bedDepth);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,(unit==2||unit==3)?skyWidth:1,(unit==2||unit==3)?skyHeight:1,0,GL_RGBA,GL_FLOAT,(unit==2||unit==3)?skyPixels.data():black);
    }
    glUseProgram(program);glUniform1i(glGetUniformLocation(program,"colortex0"),0);glUniform1i(glGetUniformLocation(program,"depthtex0"),1);
    glUniform1i(glGetUniformLocation(program,"depthtex1"),1);glUniform1i(glGetUniformLocation(program,"colortex6"),2);glUniform1i(glGetUniformLocation(program,"colortex7"),3);
    glUniform1i(glGetUniformLocation(program,"shadowtex0"),4);glUniform1i(glGetUniformLocation(program,"colortex8"),5);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
    glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,inverseView);
    glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,identity);glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,shadowProjection);
    glUniform1i(glGetUniformLocation(program,"isEyeInWater"),1);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"aqualumenActive"),1);
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,1); // upward world Sun, normal incidence
    glUniform1f(glGetUniformLocation(program,"far"),128);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();
    const float background[4]={0.05f,0.06f,0.07f,1},directSun[4]={0.2f,0.15f,0.1f,1};
    float sunlit[4];for(int c=0;c<3;++c) sunlit[c]=background[c]+directSun[c];sunlit[3]=1;
    auto draw=[&](float surfaceHeight,bool receiverSun) {
        glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,surfaceHeight);
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[0]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiverSun?sunlit:background);
        glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiverSun?directSun:black);
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        std::vector<float> output(4);glReadPixels(size/2,size/2,1,1,GL_RGBA,GL_FLOAT,output.data());
        for(float value:output) if(!std::isfinite(value)) throw std::runtime_error("Nonfinite water incident-depth output");
        if(output[3]!=1 || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Water incident-depth production-main alpha/GL failure");
        return output;
    };
    const float surfaceHeights[2]={0.5f,2.5f};
    double response[2][3];
    for(int depth=0;depth<2;++depth) {
        const auto zero=draw(surfaceHeights[depth],false),lit=draw(surfaceHeights[depth],true),repeat=draw(surfaceHeights[depth],true);
        for(int c=0;c<3;++c) {
            if(std::abs(lit[c]-repeat[c])>0.000001f) throw std::runtime_error("Water incident-depth regression must be deterministic");
            response[depth][c]=double(lit[c])-zero[c];
            if(response[depth][c]<=0.0001) throw std::runtime_error("A real receiver must retain positive direct-Sun response, not delete all Sun");
        }
        std::cout<<"GPU production composite incident depth "<<(surfaceHeights[depth]+1.0f)<<"m, fixed 1m eye leg: zero-C8 RGB "<<zero[0]<<","<<zero[1]<<","<<zero[2]
                 <<"; receiver-Sun delta "<<response[depth][0]<<","<<response[depth][1]<<","<<response[depth][2]<<"\n";
    }
    // Independent homogeneous-medium Beer oracle using the project's unchanged
    // effective extinction contract. Surface Fresnel and fixed outgoing path
    // cancel; neither GLSL caustic nor transmission helper is copied/called.
    const double sigma[3]={0.32,0.085,0.035};double largestError=0;
    for(int c=0;c<3;++c) {
        const double ratio=response[1][c]/response[0][c],expected=std::exp(-sigma[c]*2.0/clarity);
        largestError=std::max(largestError,std::abs(ratio-expected));
        std::cout<<"GPU receiver-Sun incident +2m channel "<<c<<": observed ratio "<<ratio<<", Beer reference "<<expected<<"\n";
    }
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    if(largestError>0.00002) throw std::runtime_error("Production composite must attenuate the incident surface-to-bed Sun leg while the outgoing eye leg remains fixed");
    std::cout<<"PASS GPU production composite: receiver-Sun incident-depth Beer ratio, positive paired receiver response\n";
    // A ratio cancels entry reflection, so separately check absolute transported
    // receiver-Sun power. The normal-incidence interface admits (1-F0) of the
    // dry collimated beam; no radiance n^2 conversion applies to receiver flux.
    // This CPU oracle uses physical interface/Beer laws, not shader helpers.
    constexpr double waterIor=1.333;
    const double reflection=std::pow((1.0-waterIor)/(1.0+waterIor),2.0);
    double largestEntryError=0;
    for(int c=0;c<3;++c) {
        const double expected=double(directSun[c])*std::exp(-sigma[c]*2.5/clarity)*(1.0-reflection);
        largestEntryError=std::max(largestEntryError,std::abs(response[0][c]-expected));
        std::cout<<"GPU receiver-Sun normal entry channel "<<c<<": observed delta "<<response[0][c]
                 <<", 1.5m incident + 1m eye Beer/Fresnel reference "<<expected<<", reflected fraction "<<reflection<<"\n";
    }
    if(largestEntryError>0.000002) throw std::runtime_error("Production composite must remove reflected Sun beam power at normal-incidence water entry, separately from incident/outgoing extinction");
    std::cout<<"PASS GPU production composite: absolute normal-incidence water-entry Fresnel and separate incident/outgoing Beer transport\n";
}
// An above-water eye sees a fixed flat interface and a genuine horizontal bed.
// Coherently paired immutable total/Sun snapshots isolate receiver direct Sun.
// Lowering the bed adds the same two metres to the incoming and outgoing water
// legs; interface Fresnel, air light, reflection and common scatter cancel.
void aboveWaterIncidentDepthProbe(const fs::path& root) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Above-water incident-depth regression requires real NVIDIA GL");
    constexpr int size=65,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846,clarity=1.0;
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float view[16]={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const float inverseView[16]={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    auto flatWaterSource=[&](const fs::path& file) {
        std::string source=expand(file,root);
        for(const auto& setting:std::vector<std::pair<std::string,std::string>>{{"WAVE_HEIGHT","0.0"},{"WATER_CLARITY","1.0"},{"WATER_ROUGHNESS","0.12"}}) {
            const auto start=source.find("#define "+setting.first+" ");
            if(start==std::string::npos) throw std::runtime_error("Cannot configure public "+setting.first+" setting");
            source.replace(start,source.find('\n',start)-start,"#define "+setting.first+" "+setting.second);
        }
        return source;
    };
    GLuint program=link(flatWaterSource(root/"gbuffers_water.vsh"),flatWaterSource(root/"gbuffers_water.fsh"),"above-water-incident-depth-main-probe","mc_Entity");
    GLuint textures[7],framebuffer;glGenTextures(7,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glBindTexture(GL_TEXTURE_2D,textures[6]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Above-water incident-depth framebuffer incomplete");
    const float white[4]={1,1,1,1},black[4]={0,0,0,1},initialDepth=0.5f*((a*(-2.5f)+b)/2.5f)+0.5f,shadowDepth=1;
    std::vector<float> skyPixels(skyWidth*skyHeight*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {
        const size_t base=(y*skyWidth+x)*4;for(int c=0;c<3;++c) skyPixels[base+c]=0.02f;skyPixels[base+3]=1;
    }
    for(int c=0;c<3;++c) skyPixels[((skyHeight-1)*skyWidth)*4+c]=0.25f;
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,1,1,0,GL_RED,GL_FLOAT,&initialDepth);
        else if(unit==4) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        } else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==2?skyWidth:1,unit==2?skyHeight:1,0,GL_RGBA,GL_FLOAT,unit==2?skyPixels.data():(unit==0?white:black));
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
    glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0); // No dynamic ripples: real flat water geometry.
    glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);
    glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,1);
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
    const float background[4]={0.05f,0.06f,0.07f,1},directSun[4]={0.2f,0.15f,0.1f,1};
    float sunlit[4];for(int c=0;c<3;++c) sunlit[c]=background[c]+directSun[c];sunlit[3]=1;
    auto draw=[&](float waterDepth,bool receiverSun) {
        // Constant perspective depth is a true horizontal bed for this vertical
        // camera. The centre ray is normal to both interface and bed; its
        // reflected ray points upward and cannot see this submerged receiver.
        const float bedDistance=1.0f+waterDepth,depth=0.5f*((a*(-bedDistance)+b)/bedDistance)+0.5f;
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&depth);
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiverSun?sunlit:background);
        glActiveTexture(GL_TEXTURE5);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_FLOAT,receiverSun?directSun:black);
        const float extent=1.2f/f;
        glBegin(GL_QUADS);glVertex3f(-extent,-1,-extent);glVertex3f(extent,-1,-extent);glVertex3f(extent,-1,extent);glVertex3f(-extent,-1,extent);glEnd();
        std::vector<float> output(4);glReadPixels(size/2,size/2,1,1,GL_RGBA,GL_FLOAT,output.data());
        for(float value:output) if(!std::isfinite(value)) throw std::runtime_error("Nonfinite above-water incident-depth output");
        if(output[3]!=1 || glGetError()!=GL_NO_ERROR) throw std::runtime_error("Above-water incident-depth production-main alpha/GL failure");
        return output;
    };
    const float depths[2]={1.5f,3.5f};double response[2][3];
    for(int depth=0;depth<2;++depth) {
        const auto zero=draw(depths[depth],false),lit=draw(depths[depth],true),repeat=draw(depths[depth],true);
        for(int c=0;c<3;++c) {
            if(std::abs(lit[c]-repeat[c])>0.000001f) throw std::runtime_error("Above-water incident-depth regression must be deterministic");
            response[depth][c]=double(lit[c])-zero[c];
            if(response[depth][c]<=0.0001) throw std::runtime_error("Visible real opaque bed must retain positive coloured receiver-Sun response");
        }
        std::cout<<"GPU production above-water bed depth "<<depths[depth]<<"m, fixed eye/interface: zero-C8 RGB "<<zero[0]<<","<<zero[1]<<","<<zero[2]
                 <<"; coherent C4/C8 receiver-Sun delta "<<response[depth][0]<<","<<response[depth][1]<<","<<response[depth][2]<<"\n";
    }
    const double sigma[3]={0.32,0.085,0.035};double largestError=0;
    for(int c=0;c<3;++c) {
        const double ratio=response[1][c]/response[0][c],expected=std::exp(-sigma[c]*4.0/clarity);
        largestError=std::max(largestError,std::abs(ratio-expected));
        std::cout<<"GPU above-water receiver-Sun bed +2m channel "<<c<<": observed ratio "<<ratio<<", independent two-leg Beer reference "<<expected<<"\n";
    }
    glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();
    glUseProgram(0);glDeleteProgram(program);glDeleteTextures(7,textures);glDeleteFramebuffers(1,&framebuffer);
    // The exact zenith Sun glint is common to each pair but costs subtraction
    // precision in RGBA32F. This tolerance is still over 200x smaller than the
    // least separated eye-only/two-leg expected ratios (the blue channel).
    if(largestError>0.00025) throw std::runtime_error("Above-water production water must transport receiver Sun through both surface-to-bed and bed-to-surface legs, not only the outgoing eye path");
    std::cout<<"PASS GPU production above-water water main: positive real-bed response and independent two-leg incident-depth Beer ratio\n";
}
// Opt-in investigation, deliberately absent from default acceptance. All four
// programs retain real production main and the unchanged production vertex
// program. Only the explicitly authorized fragment ablations differ.
std::string instrumentShoreCausal(const std::string& original,bool traceObservations=true) {
    std::string source=original;
    auto once=[](std::string& text,const std::string& old,const std::string& replacement) {
        const auto at=text.find(old);
        if(at==std::string::npos || text.find(old,at+old.size())!=std::string::npos) throw std::runtime_error("DEBUG-shore-causal observation seam changed: "+old);
        text.replace(at,old.size(),replacement);
    };
    const auto reflectionBegin=source.find("vec4 reflectionTrace(");
    if(reflectionBegin==std::string::npos) throw std::runtime_error("DEBUG-shore-causal reflection observation seam missing");
    source.insert(reflectionBegin,"// DEBUG-shore-causal: passive reflected-source footprint observation.\nuniform int DEBUG_shoreReflectionIteration;\nvec4 DEBUG_shoreReflectionSource=vec4(-1.0);\nvec4 DEBUG_shoreReflectionBracket=vec4(0.0);\nvec4 DEBUG_shoreReflectionPoint=vec4(0.0);\n");
    once(source,"        vec3 scene=viewPosition(screen,depth);",
        "        vec3 scene=viewPosition(screen,depth);\n        if(i==DEBUG_shoreReflectionIteration) { DEBUG_shoreReflectionBracket=vec4(q.z,scene.z,previous.z,max(0.4,travel*0.06)); DEBUG_shoreReflectionPoint=vec4(q,travel); }");
    once(source,"            return vec4(mix(fallback,texture(colortex4,screen).rgb,edge*confidence),length(farHit-viewStart));",
        "            DEBUG_shoreReflectionSource=vec4(screen,edge,confidence);\n            return vec4(mix(fallback,texture(colortex4,screen).rgb,edge*confidence),length(farHit-viewStart));");
    const auto begin=source.find("vec2 refractionTrace("),end=source.find("\nvoid main()",begin);
    if(begin==std::string::npos || end==std::string::npos) throw std::runtime_error("DEBUG-shore-causal production trace missing");
    std::string trace=source.substr(begin,end-begin);
    const std::string declarations=R"GLSL(
// DEBUG-shore-causal: observation stores in the original invocation only.
uniform int DEBUG_shoreCausalMode;
uniform int DEBUG_shoreCausalIteration;
vec4 DEBUG_shoreCausalTravel=vec4(0.0);
vec4 DEBUG_shoreCausalReceiver=vec4(0.0);
vec4 DEBUG_shoreCausalResidual=vec4(0.0);
vec4 DEBUG_shoreCausalReason=vec4(0.0);
vec4 DEBUG_shoreCausalTexel=vec4(0.0);
vec4 DEBUG_shoreCausalOrigin=vec4(0.0);
vec4 DEBUG_shoreCausalRay=vec4(0.0);
vec2 DEBUG_shoreCausalReturned=vec2(-1.0);
)GLSL";
    // The visible-bed regression observes only actual main state, so changes
    // to the production traversal do not require re-creating its iteration
    // control flow here. Full causal capture still records the original call.
    if(traceObservations) {
    once(trace,"    if (abs(ray.z) < 0.02) return original;","    if (abs(ray.z) < 0.02) { DEBUG_shoreCausalReason.x=2.0; return original; }");
    once(trace,"        vec4 projected = gbufferProjection * vec4(origin + ray * travel, 1.0);",R"GLSL(        if (i==DEBUG_shoreCausalIteration) {
            DEBUG_shoreCausalTravel=vec4(travel,0.0,-1.0,-1.0);
            DEBUG_shoreCausalResidual.w=float(i);
            DEBUG_shoreCausalReason.x=1.0;
            DEBUG_shoreCausalOrigin=vec4(origin,upperSurface?1.0:0.0);
            DEBUG_shoreCausalRay=vec4(ray,initialPath);
        }
        vec4 projected = gbufferProjection * vec4(origin + ray * travel, 1.0);
        if (i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalTravel.y=projected.w;)GLSL");
    once(trace,"        if (projected.w <= 0.0) break;","        if (projected.w <= 0.0) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=3.0; break;}");
    once(trace,"        vec2 candidate = projected.xy / projected.w * 0.5 + 0.5;",R"GLSL(        vec2 candidate = projected.xy / projected.w * 0.5 + 0.5;
        if(i==DEBUG_shoreCausalIteration) {
            DEBUG_shoreCausalTravel.zw=candidate;
            DEBUG_shoreCausalTexel=vec4(vec2(textureSize(depthtex1,0)),candidate*vec2(textureSize(depthtex1,0)));
        })GLSL");
    once(trace,"        if (any(lessThan(candidate, vec2(0.001))) || any(greaterThan(candidate, vec2(0.999)))) break;","        if (any(lessThan(candidate, vec2(0.001))) || any(greaterThan(candidate, vec2(0.999)))) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=4.0; break;}");
    once(trace,"        float depth = texture(depthtex1, candidate).r;","        float depth = texture(depthtex1, candidate).r;\n        if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReceiver.x=depth;");
    once(trace,"            if (upperSurface) break;","            if (upperSurface) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=5.0; break;}");
    once(trace,"            receiverKind = 2;","            receiverKind = 2;\n            if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=5.0;");
    once(trace,"        vec3 receiver = viewPosition(candidate, depth);",R"GLSL(        vec3 receiver = viewPosition(candidate, depth);
        if(i==DEBUG_shoreCausalIteration) {
            DEBUG_shoreCausalReceiver.yzw=receiver;
            DEBUG_shoreCausalReason.y=relativeWorld(receiver).y+cameraPosition.y;
            DEBUG_shoreCausalReason.z=origin.z+0.025-receiver.z;
            DEBUG_shoreCausalReason.w=surfaceY+0.08-DEBUG_shoreCausalReason.y;
        })GLSL");
    once(trace,"        if (receiver.z > origin.z + 0.025) break;","        if (receiver.z > origin.z + 0.025) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=6.0; break;}");
    once(trace,"        if (upperSurface && relativeWorld(receiver).y + cameraPosition.y > surfaceY + 0.08) break;","        if (upperSurface && relativeWorld(receiver).y + cameraPosition.y > surfaceY + 0.08) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=7.0; break;}");
    once(trace,"        float nextTravel = (receiver.z - origin.z) / ray.z;","        float nextTravel = (receiver.z - origin.z) / ray.z;\n        if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalResidual.x=nextTravel;");
    once(trace,"        if (nextTravel <= 0.0) break;","        if (nextTravel <= 0.0) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=8.0; break;}");
    once(trace,"        float residual=abs(nextTravel-travel);","        float residual=abs(nextTravel-travel);\n        if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalResidual.yz=vec2(residual,tolerance);");
    once(trace,"            receiverKind = 1;","            receiverKind = 1;\n            if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=9.0;");
    once(trace,"        if (upperSurface && i==8) break;","        if (upperSurface && i==8) {if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=10.0; break;}\n        if(i==DEBUG_shoreCausalIteration) DEBUG_shoreCausalReason.x=11.0;");
    }
    source.replace(begin,end-begin,declarations+trace);
    // Observe the production call's result without depending on its internal
    // parameter list; this also permits replaying a frozen pre-fix source.
    const std::string callPrefix="        vec2 refracted=refractionTrace(";
    const auto callBegin=source.find(callPrefix),callEnd=source.find(';',callBegin);
    if(callBegin==std::string::npos||callEnd==std::string::npos
        ||source.find(callPrefix,callBegin+callPrefix.size())!=std::string::npos)
        throw std::runtime_error("DEBUG-shore-causal original call observation seam changed");
    const std::string actualCall=source.substr(callBegin,callEnd-callBegin+1);
    once(source,actualCall,actualCall+"\n        DEBUG_shoreCausalReturned=refracted;");
    once(source,"    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);",R"GLSL(    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
    if(DEBUG_shoreCausalMode==0) {
        gl_FragData[1]=vec4(worldPosition,verticalDepth);
        gl_FragData[2]=vec4(viewPos,initialPath);
        gl_FragData[3]=vec4(n,thickness);
        gl_FragData[4]=vec4(transmitted,receiverConfidence);
        gl_FragData[5]=vec4(transmittedView,float(receiverKind));
        gl_FragData[6]=vec4(DEBUG_shoreCausalReturned,screen);
        gl_FragData[7]=vec4(fresnel,footprint,slopeVariance,normalVariance);
    } else if(DEBUG_shoreCausalMode==1) {
        gl_FragData[1]=DEBUG_shoreCausalTravel;
        gl_FragData[2]=DEBUG_shoreCausalReceiver;
        gl_FragData[3]=DEBUG_shoreCausalResidual;
        gl_FragData[4]=DEBUG_shoreCausalReason;
        gl_FragData[5]=DEBUG_shoreCausalTexel;
        gl_FragData[6]=DEBUG_shoreCausalOrigin;
        gl_FragData[7]=DEBUG_shoreCausalRay;
    } else if(DEBUG_shoreCausalMode==2) {
        gl_FragData[1]=vec4(viewPos+normalView*0.06,reflectedHit.a);
        gl_FragData[2]=vec4(reflected,fresnel);
        gl_FragData[3]=vec4(mat3(gbufferModelView)*reflected,receiverConfidence);
        gl_FragData[4]=vec4(refraction,thickness);
        gl_FragData[5]=vec4(reflection,initialPath);
        gl_FragData[6]=vec4(behind,float(receiverKind));
        gl_FragData[7]=vec4(color,1.0);
    } else if(DEBUG_shoreCausalMode==3) {
        gl_FragData[1]=DEBUG_shoreReflectionSource;
        gl_FragData[2]=vec4(reflectedHit.rgb,reflectedHit.a);
        gl_FragData[3]=vec4(reflected,fresnel);
        gl_FragData[4]=vec4(viewPos,worldPosition.y);
        gl_FragData[5]=vec4(n,roughness);
        gl_FragData[6]=vec4(DEBUG_shoreCausalReturned,screen);
        gl_FragData[7]=vec4(color,1.0);
    } else {
        gl_FragData[1]=DEBUG_shoreReflectionBracket;
        gl_FragData[2]=DEBUG_shoreReflectionPoint;
        gl_FragData[3]=DEBUG_shoreReflectionSource;
        gl_FragData[4]=vec4(reflectedHit.rgb,reflectedHit.a);
        gl_FragData[5]=vec4(n,fresnel);
        gl_FragData[6]=vec4(viewPos,worldPosition.y);
        gl_FragData[7]=vec4(color,1.0);
    })GLSL");
    return source;
}
struct ShoreCausalTarget {
    int x,y;
    std::array<float,2> shifts;
    float phase=1.25f;
    fs::path artifactDirectory;
    GLint filter=GL_NEAREST;
};
void shoreDiagnosticProbe(const fs::path& root,bool causalOnly=false,bool visibleBedOnly=false,
                          const ShoreCausalTarget* target=nullptr,bool reflectionReceiverOnly=false) {
    const std::string renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(renderer.find("NVIDIA")==std::string::npos) throw std::runtime_error("Stepped shore diagnostic requires real NVIDIA GL");
    constexpr int size=129,skyWidth=64,skyHeight=32;
    constexpr double pi=3.14159265358979323846;
    const fs::path artifacts=target&&!target->artifactDirectory.empty()?target->artifactDirectory
        :(reflectionReceiverOnly?fs::path("build/shore-v0.8-visible-reflection")
        :(target?fs::path(std::string(visibleBedOnly?"build/shore-v0.8-visible-bed-target-":"build/shore-v0.8-causal-target-")+std::to_string(target->x)+"-"+std::to_string(target->y)+"-phase-"+std::to_string(target->phase)+(target->filter==GL_LINEAR?"-linear":"-nearest"))
        :(visibleBedOnly?"build/shore-v0.8-visible-bed":(causalOnly?"build/shore-v0.8-causal":"build/shore-v0.8-diagnostic"))));
    if(target&&!target->artifactDirectory.empty()&&fs::exists(artifacts))
        throw std::runtime_error("Explicit shore artifact directory must be new: "+artifacts.string());
    fs::create_directories(artifacts);
    const float f=1.0f/std::tan(30.0*pi/180.0),nearPlane=0.1f,farPlane=128;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const std::string vertex=expand(root/"gbuffers_water.vsh",root);
    std::string baseline=expand(root/"gbuffers_water.fsh",root);
    auto replaceOnce=[](std::string& source,const std::string& old,const std::string& replacement) {
        const auto position=source.find(old);
        if(position==std::string::npos || source.find(old,position+old.size())!=std::string::npos)
            throw std::runtime_error("Diagnostic override must replace exactly one production expression: "+old);
        source.replace(position,old.size(),replacement);
    };
    const auto foam=baseline.find("#define SHORE_FOAM ");
    if(foam==std::string::npos) throw std::runtime_error("Missing public foam setting");
    baseline.replace(foam,baseline.find('\n',foam)-foam,"#define SHORE_FOAM 0.0");
    const char* names[]={"baseline",causalOnly?"instrumented":"face-normal","environment-only","legacy-view-depth-optics"};
    std::array<std::string,4> fragments={baseline,baseline,baseline,baseline};
    if(causalOnly) fragments[1]=instrumentShoreCausal(baseline,!visibleBedOnly);
    else {
        replaceOnce(fragments[1],"    vec3 normalView=mat3(gbufferModelView)*n;","    n=geometricNormal;\n    vec3 normalView=mat3(gbufferModelView)*n;");
        replaceOnce(fragments[2],"    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,environment,upperSurface&&!underwater,worldPosition.y);","    vec4 reflectedHit=vec4(environment,-1.0);");
        // Explicit diagnostic contrast with the former camera-depth-dependent
        // optical normal. Not a production path, acceptance gate or depth map.
        replaceOnce(fragments[3],"    vec3 normalView=mat3(gbufferModelView)*n;",
            "    if(upperSurface) { vec3 DEBUG_legacyWave=waveStateFiltered(absolutePosition.xz,frameTimeCounter,footprint,underwater?64.0:verticalDepth,slopeVariance); n=normalize(vec3(-DEBUG_legacyWave.y,1.0,-DEBUG_legacyWave.z)); if(dot(n,geometricNormal)<0.0) n=-n; }\n    vec3 normalView=mat3(gbufferModelView)*n;");
    }
    {std::ofstream file(artifacts/"production-unchanged.vsh");file<<vertex;}
    std::array<GLuint,4> programs={0,0,0,0};
    for(int variant=0;variant<(causalOnly?2:4);++variant) {
        std::ofstream file(artifacts/(std::string(names[variant])+".fsh"));file<<fragments[variant];file.close();
        programs[variant]=link(vertex,fragments[variant],std::string("shore-diagnostic-")+names[variant],"mc_Entity");
    }
    // Exact independent world boxes, not hand-painted depth bands or a copy of
    // the shader's marcher. Union entries are visible faces of closed solids.
    struct Box {std::array<double,3> lo,hi;int part,id;};
    struct Scene {
        std::vector<float> depth=std::vector<float>(size*size,1),colour=std::vector<float>(size*size*4,0);
        std::vector<int> face=std::vector<int>(size*size,-1),part=std::vector<int>(size*size,-1);
        std::vector<float> height=std::vector<float>(size*size,0);
    };
    auto makeBoxes=[&](float shift) {
        std::vector<Box> boxes;
        for(int z=-24;z<0;++z) {
            // Clamp the near-eye threshold: the camera must not start inside
            // the dry solid. All bank faces translate coherently with shift.
            const double edge=shift+std::max(0.0,std::floor((-double(z)-0.5-2.0)/4.0));
            const double boundaries[4]={-8.0+shift,edge,edge+1,8.0+shift},tops[3]={-1.75,-0.75,0.25};
            for(int part=0;part<3;++part) if(boundaries[part]<boundaries[part+1])
                boxes.push_back({{boundaries[part],-4,double(z)},{boundaries[part+1],tops[part],double(z+1)},part,(z+24)*3+part});
        }
        boxes.push_back({{-2,0,-6.1},{2,1.5,-6},3,1000});
        return boxes;
    };
    auto scene=[&](float shift,int source) {
        const auto boxes=makeBoxes(shift);
        Scene result;
        for(int y=0;y<size;++y) for(int x=0;x<size;++x) {
            const double direction[3]={(2.0*(x+0.5)/size-1.0)/f,(2.0*(y+0.5)/size-1.0)/f,-1};
            double nearest=farPlane;const Box* hit=nullptr;int hitAxis=-1;
            for(const auto& box:boxes) {
                double entry=0,exit=farPlane;int axis=-1;bool miss=false;
                for(int c=0;c<3;++c) {
                    if(std::abs(direction[c])<1e-12) {if(0<box.lo[c]||0>box.hi[c]) miss=true;continue;}
                    double t0=box.lo[c]/direction[c],t1=box.hi[c]/direction[c];if(t0>t1) std::swap(t0,t1);
                    if(t0>entry) {entry=t0;axis=c;}exit=std::min(exit,t1);
                    if(entry>exit) {miss=true;break;}
                }
                if(!miss && entry>nearPlane && entry<nearest) {nearest=entry;hit=&box;hitAxis=axis;}
            }
            const size_t pixel=y*size+x,base=pixel*4;result.colour[base+3]=1;
            if(!hit) {for(int c=0;c<3;++c) result.colour[base+c]=0.04f;continue;}
            const float height=nearest*direction[1];result.height[pixel]=height;
            result.face[pixel]=hit->id*3+hitAxis;result.part[pixel]=hit->part;
            result.depth[pixel]=0.5f*((a*(-float(nearest))+b)/float(nearest))+0.5f;
            for(int c=0;c<3;++c) result.colour[base+c]=hit->part==3?0.08f:(height< -0.5f?0.25f:(c==0?0.12f:(c==1?0.10f:0.08f)));
            if(source==1 && hit->part==3) result.colour[base]=0.45f;
            if(source==2 && hit->part==0 && height< -1.5f) result.colour[base+1]+=0.18f;
            if(source==3 && hit->part==1 && height< -0.5f) result.colour[base+1]+=0.18f;
            if(source==4 && hit->part==2 && height>= -0.5f) result.colour[base]+=0.18f;
        }
        return result;
    };
    GLuint textures[8],framebuffer;glGenTextures(8,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glBindTexture(GL_TEXTURE_2D,textures[6]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[6],0);
    glBindTexture(GL_TEXTURE_2D,textures[7]);glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,size,size,0,GL_DEPTH_COMPONENT,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,textures[7],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Shore diagnostic framebuffer incomplete");
    GLuint debugTextures[7]={0,0,0,0,0,0,0};
    if(causalOnly) {
        GLint attachments=0,buffers=0;glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);glGetIntegerv(GL_MAX_DRAW_BUFFERS,&buffers);
        if(attachments<8 || buffers<8) throw std::runtime_error("DEBUG-shore-causal needs eight real MRT attachments");
        glGenTextures(7,debugTextures);glActiveTexture(GL_TEXTURE8);
        GLenum draws[8];draws[0]=GL_COLOR_ATTACHMENT0;
        for(int i=0;i<7;++i) {glBindTexture(GL_TEXTURE_2D,debugTextures[i]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);draws[i+1]=GL_COLOR_ATTACHMENT0+i+1;glFramebufferTexture2D(GL_FRAMEBUFFER,draws[i+1],GL_TEXTURE_2D,debugTextures[i],0);}
        glDrawBuffers(8,draws);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("DEBUG-shore-causal MRT framebuffer incomplete");
    }
    const float white[4]={1,1,1,1},shadowDepth=1;
    std::vector<float> sky(skyWidth*skyHeight*4,0),black(size*size*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {const size_t base=(y*skyWidth+x)*4;for(int c=0;c<3;++c) sky[base+c]=0.04f;sky[base+3]=1;}
    for(size_t base=0;base<black.size();base+=4) black[base+3]=1;
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,size,size,0,GL_RED,GL_FLOAT,nullptr);
        else if(unit==4) {glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadowDepth);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);}
        else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==0?1:(unit==2?skyWidth:size),unit==0?1:(unit==2?skyHeight:size),0,GL_RGBA,GL_FLOAT,unit==0?white:(unit==2?sky.data():black.data()));
    }
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8"};
    for(GLuint program:programs) {
        if(program==0) continue;
        glUseProgram(program);for(int unit=0;unit<6;++unit) glUniform1i(glGetUniformLocation(program,samplers[unit]),unit);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
        for(const char* name:{"gbufferModelView","gbufferModelViewInverse","shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),target?target->phase:1.25f);
        const GLint material=glGetAttribLocation(program,"mc_Entity");if(material<0) throw std::runtime_error("Missing production water material attribute");
        glDisableVertexAttribArray(material);glVertexAttrib4f(material,10000,0,0,0);
    }
    glPushAttrib(GL_ENABLE_BIT|GL_CURRENT_BIT|GL_VIEWPORT_BIT|GL_TRANSFORM_BIT|GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
    glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_FALSE);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,size,size);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadMatrixf(projection);
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);glClearColor(0,0,0,0);
    auto draw=[&](int variant,const Scene& input,GLint filter) {
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,input.colour.data());
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,textures[3]);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RED,GL_FLOAT,input.depth.data());
        // Separate attachment allocation; never bind it to a sampled unit.
        glActiveTexture(GL_TEXTURE7);glBindTexture(GL_TEXTURE_2D,textures[7]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,input.depth.data());
        glUseProgram(programs[variant]);glClear(GL_COLOR_BUFFER_BIT);glBegin(GL_QUADS);
        for(int z=-24;z<0;++z) for(int x=-8;x<8;++x) {glVertex3f(x,-0.5f,z);glVertex3f(x+1,-0.5f,z);glVertex3f(x+1,-0.5f,z+1);glVertex3f(x,-0.5f,z+1);}
        glEnd();std::vector<float> output(size*size*4);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,output.data());
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Shore diagnostic production-main GL failure");
        for(size_t pixel=0;pixel<size*size;++pixel) {for(int c=0;c<4;++c) if(!std::isfinite(output[pixel*4+c])) throw std::runtime_error("Nonfinite shore diagnostic output");if(output[pixel*4+3]!=0 && output[pixel*4+3]!=1) throw std::runtime_error("Shore diagnostic alpha must identify clear versus water");}
        return output;
    };
    auto save=[&](const std::string& name,const std::vector<float>& pixels) {
        std::ofstream raw(artifacts/(name+".rgba32f"),std::ios::binary);raw.write(reinterpret_cast<const char*>(pixels.data()),pixels.size()*sizeof(float));
        std::ofstream pfm(artifacts/(name+".pfm"),std::ios::binary);pfm<<"PF\n"<<size<<" "<<size<<"\n-1.0\n";
        for(size_t pixel=0;pixel<size*size;++pixel) pfm.write(reinterpret_cast<const char*>(pixels.data()+pixel*4),3*sizeof(float));
    };
    auto roi=[](int pixel) {const int x=pixel%size,y=pixel/size;return x>=20 && x<=108 && y>=10 && y<=56;};
    auto maxDifference=[&](const std::vector<float>& left,const std::vector<float>& right,int* where=nullptr,bool onlyWater=true) {
        float largest=0;for(int pixel=0;pixel<size*size;++pixel) if(roi(pixel) && (!onlyWater||(left[pixel*4+3]==1 && right[pixel*4+3]==1)))
            for(int c=0;c<3;++c) if(std::abs(left[pixel*4+c]-right[pixel*4+c])>largest) {largest=std::abs(left[pixel*4+c]-right[pixel*4+c]);if(where) *where=pixel;}
        return largest;
    };
    auto cleanup=[&]() {
        glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();glPopAttrib();glUseProgram(0);
        for(GLuint program:programs) if(program!=0) glDeleteProgram(program);
        if(causalOnly) glDeleteTextures(7,debugTextures);
        glDeleteTextures(8,textures);glDeleteFramebuffers(1,&framebuffer);
    };
    if(causalOnly) {
        using V3=std::array<double,3>;
        struct Hit {bool valid=false,inside=false,boundary=false;int id=-1,part=-1,axis=-1,side=0;double travel=0;V3 point={0,0,0},colour={0,0,0};};
        auto physical=[&](float shift,const V3& origin,const V3& ray) {
            struct Interval {double entry,exit;Box box;int inAxis,outAxis,inSide,outSide;};
            std::vector<Interval> intervals;bool inside=false,boundary=false;
            for(const Box& box:makeBoxes(shift)) {
                double entry=-1e30,exit=1e30;int inAxis=-1,outAxis=-1,inSide=0,outSide=0;bool miss=false,onFace=false;
                for(int c=0;c<3;++c) {
                    if(std::abs(origin[c]-box.lo[c])<1e-7 || std::abs(origin[c]-box.hi[c])<1e-7) onFace=true;
                    if(std::abs(ray[c])<1e-12) {if(origin[c]<box.lo[c]||origin[c]>box.hi[c]) miss=true;continue;}
                    double t0=(box.lo[c]-origin[c])/ray[c],t1=(box.hi[c]-origin[c])/ray[c];int s0=-1,s1=1;
                    if(t0>t1) {std::swap(t0,t1);std::swap(s0,s1);}
                    if(t0>entry) {entry=t0;inAxis=c;inSide=s0;}if(t1<exit) {exit=t1;outAxis=c;outSide=s1;}
                    if(entry>exit) {miss=true;break;}
                }
                if(!miss && exit>1e-7) {intervals.push_back({entry,exit,box,inAxis,outAxis,inSide,outSide});if(entry<0) {inside=true;if(onFace) boundary=true;}if(std::abs(entry)<1e-7) boundary=true;}
            }
            Hit result;result.inside=inside;result.boundary=boundary;
            if(intervals.empty()) return result;
            std::sort(intervals.begin(),intervals.end(),[](const Interval& l,const Interval& r){return l.entry<r.entry;});
            Interval chosen=intervals.front();double travel=chosen.entry;int axis=chosen.inAxis,side=chosen.inSide;
            if(inside) {
                // Merge touching/overlapping intervals of the closed union so
                // an origin inside a solid exits its EXTERIOR, not an internal
                // partition between adjacent fixture boxes.
                double exit=0;for(const auto& interval:intervals) {
                    if(interval.entry>exit+1e-8) break;
                    if(interval.exit>exit) {exit=interval.exit;chosen=interval;}
                }
                travel=exit;axis=chosen.outAxis;side=chosen.outSide;
            }
            if(travel<=1e-7 || travel>128) return result;
            result.valid=true;result.travel=travel;result.id=chosen.box.id;result.part=chosen.box.part;result.axis=axis;result.side=side;
            // Classify the shared scene palette only after the entire receiver
            // position is filled: red must not observe the default point.y.
            for(int c=0;c<3;++c) result.point[c]=origin[c]+ray[c]*travel;
            for(int c=0;c<3;++c) result.colour[c]=result.part==3?0.08:(float(result.point[1])< -0.5f?0.25:(c==0?0.12:(c==1?0.10:0.08)));
            if(std::abs(chosen.entry-chosen.exit)<1e-7) result.boundary=true;
            return result;
        };
        auto capture=[&](int mode,int iteration,const Scene& input,GLint filter,int pixel,const std::vector<float>& reference) {
            glUseProgram(programs[1]);glUniform1i(glGetUniformLocation(programs[1],"DEBUG_shoreCausalMode"),mode);glUniform1i(glGetUniformLocation(programs[1],"DEBUG_shoreCausalIteration"),iteration);
            const auto output=draw(1,input,filter);float difference=0;
            for(size_t i=0;i<output.size();++i) {difference=std::max(difference,std::abs(output[i]-reference[i]));if(i%4==3 && output[i]!=reference[i]) throw std::runtime_error("DEBUG-shore-causal instrumentation changed water coverage");}
            if(difference>0.000001f) throw std::runtime_error("DEBUG-shore-causal instrumentation perturbed real main C0");
            std::array<std::array<float,4>,7> data;
            for(int attachment=1;attachment<8;++attachment) {glReadBuffer(GL_COLOR_ATTACHMENT0+attachment);glReadPixels(pixel%size,pixel/size,1,1,GL_RGBA,GL_FLOAT,data[attachment-1].data());for(float value:data[attachment-1]) if(!std::isfinite(value)) throw std::runtime_error("DEBUG-shore-causal nonfinite observation");}
            glReadBuffer(GL_COLOR_ATTACHMENT0);if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("DEBUG-shore-causal MRT read error");
            std::cout<<"DEBUG-shore-causal C0 observation mode="<<mode<<" iteration="<<iteration<<" full-image max RGB/alpha difference="<<difference<<"\n";
            return data;
        };
        if(reflectionReceiverOnly) {
            constexpr int pixel=49*size+85;
            constexpr double tag=0.18,roundoff=0.000002;
            const float shifts[2]={0.0442343801f,0.0442421921f};
            std::ofstream evidence(artifacts/"visible-reflection.csv");
            evidence<<std::setprecision(12)<<"endpoint,shift,surfaceY,trueWallY,biasedWallY,physicalU,physicalV,sourceResponse,expectedFresnelGain,actualReportedFresnel,SSRtravel,SSRsampleU,SSRsampleV,edge,confidence\n";
            std::ofstream manifest(artifacts/"fixture-manifest.txt");
            manifest<<"Actual unchanged water main/vsh; SHORE_FOAM=0. LINEAR129x129,FOV60,phase1.25,C8/Solar0.\n"
                    <<"Only dry part2 bank C4 red is tagged +.18 at y>=-.5. Transmission/proxy must be untagged.\n"
                    <<"Independent closed-box intersections qualify interface and biased reflection rays, physical visibility, four actual LINEAR texel-centre source supports, constant palette/tag.\n"
                    <<"Oracle is sampled-facet source retention F*.18, not a rough-BSDF integrated finite-wall model.\n";
            bool failed=false;
            std::ofstream brackets(artifacts/"reflection-brackets.csv");
            brackets<<std::setprecision(12)<<"endpoint,iteration,qZ,sceneZ,previousZ,historicalOvershootLimit,qX,qY,qZcopy,travel,sourceU,sourceV,edge,confidence\n";
            for(int endpoint=0;endpoint<2;++endpoint) {
                const float shift=shifts[endpoint];const Scene input=scene(shift,0),tagged=scene(shift,4);
                const auto neutral=draw(0,input,GL_LINEAR),output=draw(0,tagged,GL_LINEAR),repeat=draw(0,tagged,GL_LINEAR);
                if(neutral[pixel*4+3]!=1 || output[pixel*4+3]!=1 || maxDifference(output,repeat,nullptr,false)!=0)
                    throw std::runtime_error("Reflected-source fixture must retain water coverage and deterministic output");
                const auto state=capture(0,0,input,GL_LINEAR,pixel,neutral);
                const auto transport=capture(2,0,input,GL_LINEAR,pixel,neutral);
                const auto reflected=capture(3,0,input,GL_LINEAR,pixel,neutral);
                for(int iteration=0;iteration<8;++iteration) {
                    glUseProgram(programs[1]);glUniform1i(glGetUniformLocation(programs[1],"DEBUG_shoreReflectionIteration"),iteration);
                    const auto step=capture(4,0,input,GL_LINEAR,pixel,neutral);
                    brackets<<endpoint<<","<<iteration;for(int slot:{0,1,2}) for(float value:step[slot]) brackets<<","<<value;brackets<<"\n";
                }
                const V3 origin={state[0][0],state[0][1],state[0][2]},normal={state[2][0],state[2][1],state[2][2]};
                const V3 mirror={transport[1][0],transport[1][1],transport[1][2]},biased={transport[0][0],transport[0][1],transport[0][2]};
                const Hit trueWall=physical(shift,origin,mirror),wall=physical(shift,biased,mirror);
                const V3 transmission={state[3][0],state[3][1],state[3][2]};const Hit bed=physical(shift,origin,transmission);
                if(!trueWall.valid || !wall.valid || trueWall.inside || wall.inside || trueWall.boundary || wall.boundary
                    || trueWall.part!=2 || wall.part!=2 || trueWall.axis!=0 || wall.axis!=0 || trueWall.side!=-1 || wall.side!=-1
                    || trueWall.point[1]<=-0.5 || wall.point[1]<=-0.5 || wall.point[1]<=origin[1]
                    || !bed.valid || bed.point[1]>=-0.5 || state[4][3]!=1)
                    throw std::runtime_error("Reflected-source physical ray/receiver qualification failed");
                auto project=[&](const V3& point) {return std::array<double,2>{0.5+0.5*f*point[0]/(-point[2]),0.5+0.5*f*point[1]/(-point[2])};};
                auto support=[&](const std::array<double,2>& uv,bool taggedWall) {
                    const double tx=uv[0]*size-0.5,ty=uv[1]*size-0.5;const int ix=int(std::floor(tx)),iy=int(std::floor(ty));
                    if(ix<0 || iy<0 || ix+1>=size || iy+1>=size) throw std::runtime_error("Reflected-source support is offscreen");
                    for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                        const int x=ix+dx,y=iy+dy,q=y*size+x;
                        const double difference=tagged.colour[q*4]-input.colour[q*4];
                        if(std::abs(difference-(taggedWall?tag:0.0))>0.0000001)
                            throw std::runtime_error("Reflected-source LINEAR tag footprint crosses an actual source edge or transmission leak at "+std::to_string(x)+","+std::to_string(y)+"; height="+std::to_string(input.height[q])+"; expectedTag="+std::to_string(taggedWall)+"; tag="+std::to_string(difference));
                        if(taggedWall) {
                            const V3 eyeRay={(2.0*(x+0.5)/size-1.0)/f,(2.0*(y+0.5)/size-1.0)/f,-1};const Hit sample=physical(shift,{0,0,0},eyeRay);
                            if(!sample.valid || sample.part!=2 || sample.axis!=wall.axis || sample.side!=wall.side || sample.point[1]<=-0.5
                                || std::abs(sample.point[0]-wall.point[0])>1e-7)
                                throw std::runtime_error("Reflected-source LINEAR support crosses a real wall/visibility edge");
                            for(int c=0;c<3;++c) if(std::abs(input.colour[q*4+c]-wall.colour[c])>0.0000001)
                                throw std::runtime_error("Reflected-source LINEAR palette is not uniform");
                        }
                    }
                };
                for(const Hit* hit:{&trueWall,&wall}) {
                    const Hit visible=physical(shift,{0,0,0},hit->point);double error=0;
                    for(int c=0;c<3;++c) error+=std::pow(visible.point[c]-hit->point[c],2);
                    if(!visible.valid || std::sqrt(error)>0.0001) throw std::runtime_error("Reflected wall is not actually camera visible");
                    support(project(hit->point),true);
                }
                support({state[5][0],state[5][1]},false);support({state[5][2],state[5][3]},false);
                if(reflected[0][0]>=0) support({reflected[0][0],reflected[0][1]},true);
                double eyeLength=0,ci=0;for(double value:origin) eyeLength+=value*value;eyeLength=std::sqrt(eyeLength);
                for(int c=0;c<3;++c) ci+=normal[c]*(-origin[c]/eyeLength);
                ci=std::clamp(ci,0.0,1.0);
                const double eta=1.333,ct=std::sqrt(1-(1-ci*ci)/(eta*eta));
                const double rs=(ci-eta*ct)/(ci+eta*ct),rp=(eta*ci-ct)/(eta*ci+ct);
                const double expected=tag*0.5*(rs*rs+rp*rp),response=output[pixel*4]-neutral[pixel*4];
                if(std::abs(output[pixel*4+1]-neutral[pixel*4+1])>roundoff || std::abs(output[pixel*4+2]-neutral[pixel*4+2])>roundoff)
                    throw std::runtime_error("Red-only reflected source leaked into unrelated channels");
                failed=failed || std::abs(response-expected)>roundoff;
                const auto uv=project(wall.point);
                // Real-main negatives use sources that cannot reach either
                // optical ray here: an off-ray above-water panel and a deep
                // submerged bed. Qualify actual sampled transmission/proxy
                // footprints as untagged before asserting public C0 zero.
                for(int source:{1,2}) {
                    const Scene forbidden=scene(shift,source);
                    auto untaggedSupport=[&](double u,double v) {
                        const int ix=int(std::floor(u*size-0.5)),iy=int(std::floor(v*size-0.5));
                        if(ix<0 || iy<0 || ix+1>=size || iy+1>=size) throw std::runtime_error("Reflected-source negative support is offscreen");
                        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                            const int q=((iy+dy)*size+ix+dx)*4;
                            for(int c=0;c<3;++c) if(forbidden.colour[q+c]!=input.colour[q+c])
                                throw std::runtime_error("Reflected-source negative leaks through a legitimate sampled receiver");
                        }
                    };
                    untaggedSupport(state[5][0],state[5][1]);untaggedSupport(state[5][2],state[5][3]);
                    untaggedSupport(uv[0],uv[1]);
                    if(reflected[0][0]>=0) untaggedSupport(reflected[0][0],reflected[0][1]);
                    if((source==1 && (wall.part==3 || bed.part==3)) || (source==2 && (wall.part==0 || bed.part==0)))
                        throw std::runtime_error("Reflected-source negative is actually on a physical first receiver");
                    const auto negative=draw(0,forbidden,GL_LINEAR);
                    double delta=0;for(int c=0;c<3;++c) delta=std::max(delta,std::abs(double(negative[pixel*4+c])-neutral[pixel*4+c]));
                    std::cout<<"DEBUG-shore-visible-reflection negative endpoint="<<endpoint<<" source="<<(source==1?"off-ray-dry-panel":"submerged-deep-bed")<<" publicC0delta="<<delta<<"\n";
                    if(delta>roundoff) throw std::runtime_error("Off-ray/drowned source must not enter qualified reflected-wall output");
                }
                evidence<<endpoint<<","<<shift<<","<<origin[1]<<","<<trueWall.point[1]<<","<<wall.point[1]<<","<<uv[0]<<","<<uv[1]<<","<<response<<","<<expected<<","<<state[6][0]<<","<<transport[0][3];
                for(float value:reflected[0]) evidence<<","<<value;
                evidence<<"\n";
                save("endpoint"+std::to_string(endpoint)+"-neutral",neutral);save("endpoint"+std::to_string(endpoint)+"-tagged",output);
                std::cout<<std::setprecision(12)<<"DEBUG-shore-visible-reflection endpoint="<<endpoint<<" sourceResponse="<<response<<" independentFresnelGain="<<expected<<" SSRtravel="<<transport[0][3]<<" sourceUV/edge/confidence="<<reflected[0][0]<<","<<reflected[0][1]<<","<<reflected[0][2]<<","<<reflected[0][3]<<"\n";
            }
            cleanup();
            if(failed) throw std::runtime_error("Production water must retain the uniformly tagged camera-visible wall on both sides of a sampled-facet reflection cut");
            std::cout<<"PASS GPU public water main: qualified visible-wall sampled-facet reflection source retained\n";return;
        }
        if(visibleBedOnly) {
            // ONE public-output regression: a ray still reaches the same
            // camera-visible, uniformly tagged planar bed on both sides of
            // the diagnosed solver cut. Its radiance cannot disappear merely
            // because quantized screen-depth iteration alternates texels.
            constexpr double tag=0.18,greenSigma=0.085,clarity=1.0;
            int pixel=target?target->y*size+target->x:46*size+65;
            float fixturePhase=target?target->phase:1.25f;
            const GLint fixtureFilter=target?target->filter:GL_NEAREST;
            const std::array<float,2> endpoints=target?target->shifts:std::array<float,2>{0.0464765616f,0.0464843735f};
            if(!target) {
                // A change to the physical optical facet can move the old
                // pixel's FIRST receiver from the deep floor to the bank.
                // Select by independent visibility/footprint qualification
                // BEFORE evaluating tagged source responses; never by PASS.
                std::array<Scene,2> inputs={scene(endpoints[0],0),scene(endpoints[1],0)};
                std::array<std::vector<float>,2> clears={draw(0,inputs[0],fixtureFilter),draw(0,inputs[1],fixtureFilter)};
                auto qualified=[&](int candidate) {
                    for(int endpoint=0;endpoint<2;++endpoint) {
                        const auto& input=inputs[endpoint];
                        if(input.part[candidate]!=1 || clears[endpoint][candidate*4+3]!=1) return false;
                        const auto data=capture(0,0,input,fixtureFilter,candidate,clears[endpoint]);
                        const V3 origin={data[0][0],data[0][1],data[0][2]},ray={data[3][0],data[3][1],data[3][2]};
                        const Hit hit=physical(endpoints[endpoint],origin,ray);
                        if(!hit.valid || hit.part!=0 || hit.axis!=1 || hit.side!=1 || hit.inside || hit.boundary || hit.point[1]>=-1.5) return false;
                        const Hit camera=physical(endpoints[endpoint],{0,0,0},hit.point);
                        double error=0;for(int c=0;c<3;++c) error+=std::pow(hit.point[c]-camera.point[c],2);
                        if(!camera.valid || camera.inside || camera.boundary || std::sqrt(error)>=0.0001) return false;
                        const double u=0.5+0.5*f*hit.point[0]/(-hit.point[2]),v=0.5+0.5*f*hit.point[1]/(-hit.point[2]);
                        if(!(u>0.01 && u<0.99 && v>0.01 && v<0.99)) return false;
                        const int cx=int(std::floor(u*size)),cy=int(std::floor(v*size));
                        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                            const V3 cornerRay={(2.0*(cx+dx)/size-1)/f,(2.0*(cy+dy)/size-1)/f,-1};
                            const Hit corner=physical(endpoints[endpoint],{0,0,0},cornerRay);
                            if(!corner.valid || corner.inside || corner.boundary || corner.part!=0 || corner.axis!=1 || corner.side!=1 || std::abs(corner.point[1]-hit.point[1])>1e-7) return false;
                        }
                        const auto info=capture(2,0,input,fixtureFilter,candidate,clears[endpoint]);
                        const V3 mirrorOrigin={info[0][0],info[0][1],info[0][2]},mirrorRay={info[1][0],info[1][1],info[1][2]};
                        const Hit mirror=physical(endpoints[endpoint],mirrorOrigin,mirrorRay);
                        if(mirror.valid || mirror.inside || mirror.boundary || info[0][3]>=0) return false;
                    }
                    return true;
                };
                std::vector<int> candidates={pixel};
                for(int y=34;y<=58;++y) for(int x=58;x<=94;++x)
                    if(y*size+x!=pixel) candidates.push_back(y*size+x);
                bool found=false;
                // Phase is also selected from physical/input qualification,
                // never a tagged response. Coarse facets can lawfully point
                // into the bank at one phase and toward the deep bed at another.
                for(float phase:{1.25f,0.0f,0.5f,1.0f,1.5f,2.0f,2.5f,3.0f}) {
                    fixturePhase=phase;
                    for(GLuint program:programs) if(program) {glUseProgram(program);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),phase);}
                    clears={draw(0,inputs[0],fixtureFilter),draw(0,inputs[1],fixtureFilter)};
                    for(int candidate:candidates) if(qualified(candidate)) {pixel=candidate;found=true;break;}
                    if(found) break;
                }
                if(!found) throw std::runtime_error("INCONCLUSIVE visible-bed fixture: no independently visible floor/proxy/footprint control under the current optical facet");
                std::cout<<"DEBUG-shore-visible-bed qualification-only selected pixel="<<pixel%size<<","<<pixel/size<<" phase="<<fixturePhase<<" before source responses; frozen historical65,46/phase1.25 remains separately preserved\n";
            }
            double responses[2]={0,0},expected[2]={0,0},allowance[2]={0,0};
            V3 points[2];
            std::ofstream evidence(artifacts/"visible-bed.csv");
            evidence<<std::setprecision(12)<<"endpoint,shift,originalPart,hitPart,hitAxis,hitSide,cameraVisible,physicalTravel,planePixelRadius,fresnel,expectedResponse,response,lowerBound,upperBound,C0Gneutral,C0Gtagged,kind,confidence,reportedOpticalPath\n";
            std::ofstream manifest(artifacts/"fixture-manifest.txt");
            manifest<<"DEBUG-shore-visible-bed: unchanged production main/vsh, public SHORE_FOAM=0;129x129,FOV60,phase="<<fixturePhase<<",WAVE_HEIGHT=.12,C8/Sun0\n"
                    <<"Exact "<<(fixtureFilter==GL_LINEAR?"LINEAR":"NEAREST")<<" causal bracket pixel"<<pixel%size<<","<<pixel/size<<"; shifts "<<std::setprecision(10)<<endpoints[0]<<","<<endpoints[1]<<"; paired C4 green+.18 on physical deep bed only; depth/geometry/lighting identical within each pair.\n"
                    <<"Independent closed union supplies first Snell-ray receiver and camera visibility. Standard dielectric Fresnel plus declared green extinction .085/m predicts paired source response.\n"
                    <<"Tolerance is the projected receiver's camera-pixel cell plane-Z extent mapped onto the Snell ray, plus 2e-6 RGBA32F subtraction roundoff; no arbitrary image-seam threshold.\n";
            // Retain nonvacuous actual reflection/deep-source controls from the
            // same closed fixture. Their presence is not a claim that this
            // selected pixel itself has an SSR geometry hit.
            const Scene control=scene(0,0);
            const auto clear=draw(0,control,fixtureFilter),reflection=draw(0,scene(0,1),fixtureFilter),bed=draw(0,scene(0,2),fixtureFilter);
            const double reflectionResponse=maxDifference(clear,reflection),deepResponse=maxDifference(clear,bed);
            if(reflectionResponse<=0 || deepResponse<=0) throw std::runtime_error("Visible-bed fixture must retain actual reflected and deep receiver source responses");
            std::cout<<"DEBUG-shore-visible-bed positive fixture controls reflection="<<reflectionResponse<<" deep="<<deepResponse<<"\n";
            bool failed=false;
            for(int endpoint=0;endpoint<2;++endpoint) {
                const float shift=endpoints[endpoint];const Scene input=scene(shift,0),tagged=scene(shift,2);
                const auto neutral=draw(0,input,fixtureFilter),output=draw(0,tagged,fixtureFilter),repeat=draw(0,tagged,fixtureFilter);
                if(neutral[pixel*4+3]!=1 || output[pixel*4+3]!=1 || maxDifference(output,repeat,nullptr,false)!=0)
                    throw std::runtime_error("Visible-bed fixture must have stable actual water coverage and deterministic paired source output");
                // Observe the neutral main invocation only, then compare its
                // C0 to the genuine public output; no second marcher is used.
                const auto data=capture(0,0,input,fixtureFilter,pixel,neutral);
                const auto transport=capture(2,0,input,fixtureFilter,pixel,neutral);
                const auto taggedTransport=capture(2,0,tagged,fixtureFilter,pixel,output);
                for(int c=0;c<3;++c) if(std::abs(taggedTransport[4][c]-transport[4][c])>0.000002f)
                    throw std::runtime_error("Deep-bed source tag must not alter the actual reflected radiance");
                std::ofstream stateFile(artifacts/("endpoint"+std::to_string(endpoint)+"-observations.csv"));
                stateFile<<std::setprecision(12)<<"mode,source,attachment,x,y,z,w\n";
                for(int mode:{0,2}) for(int attachment=0;attachment<7;++attachment) {
                    const auto& values=mode==0?data[attachment]:transport[attachment];
                    stateFile<<mode<<",neutral,"<<attachment+1;for(float value:values) stateFile<<","<<value;stateFile<<"\n";
                    if(mode==2) {stateFile<<mode<<",tagged,"<<attachment+1;for(float value:taggedTransport[attachment]) stateFile<<","<<value;stateFile<<"\n";}
                }
                const V3 origin={data[0][0],data[0][1],data[0][2]},ray={data[3][0],data[3][1],data[3][2]};
                const Hit hit=physical(shift,origin,ray),camera=hit.valid?physical(shift,{0,0,0},hit.point):Hit{};
                double visibilityError=0;for(int c=0;c<3;++c) visibilityError+=std::pow(hit.point[c]-camera.point[c],2);
                const bool visible=hit.valid && camera.valid && !camera.inside && !camera.boundary && std::sqrt(visibilityError)<0.0001;
                if(!hit.valid || hit.part!=0 || hit.axis!=1 || hit.side!=1 || hit.inside || hit.boundary || !visible || hit.point[1]>=-1.5 || input.part[pixel]!=1)
                    throw std::runtime_error("Visible-bed regression is unqualified: retain a visible horizontal deep receiver and an untagged original riser proxy");
                // SSR or a geometric source switch would invalidate a uniquely
                // transmitted-tag oracle. Both are independently excluded.
                const V3 reflectedOrigin={transport[0][0],transport[0][1],transport[0][2]},reflectedRay={transport[1][0],transport[1][1],transport[1][2]};
                const Hit reflectedReceiver=physical(shift,reflectedOrigin,reflectedRay);
                if(reflectedReceiver.valid || reflectedReceiver.inside || reflectedReceiver.boundary || transport[0][3]>=0)
                    throw std::runtime_error("Visible-bed selected pixel unexpectedly acquired a reflected geometry source");
                const double u=0.5+0.5*f*hit.point[0]/(-hit.point[2]),v=0.5+0.5*f*hit.point[1]/(-hit.point[2]);
                const int cellX=int(std::floor(u*size)),cellY=int(std::floor(v*size));double pathRadius=0;
                for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                    const V3 cornerRay={(2.0*(cellX+dx)/size-1.0)/f,(2.0*(cellY+dy)/size-1.0)/f,-1};
                    const Hit corner=physical(shift,{0,0,0},cornerRay);
                    // Adjacent closed-box partitions on the same top plane are
                    // allowed: IDs alone do not denote a radiance/visibility edge.
                    if(!corner.valid || corner.inside || corner.boundary || corner.part!=0 || corner.axis!=1 || corner.side!=1 || std::abs(corner.point[1]-hit.point[1])>1e-7)
                        throw std::runtime_error("Visible-bed error bound crosses a genuine projected receiver/occlusion edge");
                    pathRadius=std::max(pathRadius,std::abs((corner.point[2]-origin[2])/ray[2]-hit.travel));
                }
                // Independent physical Fresnel (from observed optical facet,
                // not the production Fresnel output) and Beer response. The
                // paired draws cancel common sky, reflection and in-scattering.
                double eyeLength=0,cosIncident=0;for(double value:origin) eyeLength+=value*value;eyeLength=std::sqrt(eyeLength);
                for(int c=0;c<3;++c) cosIncident+=data[2][c]*(-origin[c]/eyeLength);
                cosIncident=std::clamp(cosIncident,0.0,1.0);
                const double eta=1.333,cosTransmitted=std::sqrt(1.0-(1.0-cosIncident*cosIncident)/(eta*eta));
                const double perpendicular=(cosIncident-eta*cosTransmitted)/(cosIncident+eta*cosTransmitted),parallel=(eta*cosIncident-cosTransmitted)/(eta*cosIncident+cosTransmitted);
                const double fresnel=0.5*(perpendicular*perpendicular+parallel*parallel);
                const double lower=tag*(1-fresnel)*std::exp(-greenSigma*(hit.travel+pathRadius)/clarity)-0.000002;
                const double upper=tag*(1-fresnel)*std::exp(-greenSigma*std::max(0.0,hit.travel-pathRadius)/clarity)+0.000002;
                expected[endpoint]=tag*(1-fresnel)*std::exp(-greenSigma*hit.travel/clarity);
                responses[endpoint]=output[pixel*4+1]-neutral[pixel*4+1];allowance[endpoint]=std::max(expected[endpoint]-lower,upper-expected[endpoint]);points[endpoint]=hit.point;
                failed=failed || responses[endpoint]<lower || responses[endpoint]>upper;
                save("endpoint"+std::to_string(endpoint)+"-neutral",neutral);save("endpoint"+std::to_string(endpoint)+"-deep-tag",output);
                evidence<<endpoint<<","<<shift<<","<<input.part[pixel]<<","<<hit.part<<","<<hit.axis<<","<<hit.side<<","<<visible<<","<<hit.travel<<","<<pathRadius<<","<<fresnel<<","<<expected[endpoint]<<","<<responses[endpoint]<<","<<lower<<","<<upper<<","<<neutral[pixel*4+1]<<","<<output[pixel*4+1]<<","<<data[4][3]<<","<<data[3][3]<<","<<data[2][3]<<"\n";
                std::cout<<std::setprecision(12)<<"DEBUG-shore-visible-bed endpoint="<<endpoint<<" b="<<shift<<" actual paired G response="<<responses[endpoint]<<" independent expected="<<expected[endpoint]<<" plane-pixel bound=["<<lower<<","<<upper<<"] physicalPath="<<hit.travel<<" pixelRadius="<<pathRadius<<" kind/confidence/path="<<data[4][3]<<"/"<<data[3][3]<<"/"<<data[2][3]<<"\n";
            }
            double movement=0;for(int c=0;c<3;++c) movement+=std::pow(points[0][c]-points[1][c],2);
            const double responseDifference=std::abs(responses[1]-responses[0]),physicalBound=std::abs(expected[1]-expected[0])+allowance[0]+allowance[1];
            failed=failed || responseDifference>physicalBound;
            std::cout<<"DEBUG-shore-visible-bed continuous physical receiver motion="<<std::sqrt(movement)<<"m actual response difference="<<responseDifference<<" physical plus one-pixel bound="<<physicalBound<<"\n";
            cleanup();
            if(failed) throw std::runtime_error("Production water must retain transmitted radiance from the same camera-visible planar deep bed across a quantized depth iteration cut");
            std::cout<<"PASS GPU public water main: "<<(fixtureFilter==GL_LINEAR?"LINEAR":"NEAREST")<<" visible deep receiver radiance retained within independent physical/plane-pixel transport bound\n";
            if(!target) {
                // Freeze the already independently qualified pixel/phase and
                // test the SAME geometry/transport bound with depth filtering.
                // A NEAREST-only fix must not silently regress LINEAR inputs.
                ShoreCausalTarget linearTarget={pixel%size,pixel/size,endpoints,fixturePhase,{},GL_LINEAR};
                shoreDiagnosticProbe(root,true,true,&linearTarget);
            }
            return;
        }
        std::ofstream manifest(artifacts/"fixture-manifest.txt");manifest<<"DEBUG-shore-causal\nProduction vsh unchanged; common public SHORE_FOAM=0.\n129x129 FOV60 near.1 far128 identity view, cameraPosition(0,62,0), waterY-.5 one-metre quads, phase="<<(target?target->phase:1.25f)<<", no ripples; closed slab union matches original shore diagnostic.\nC8 and reserved solar cache zero; RGB LUT.04; GL_LESS with separate seeded opaque depth attachment and depth writes off.\nCoordinates world/view camera-relative; physical boxes are camera-relative, no synthetic eye offset.\nReason0 notexecuted,1 entered,2 rayZ,3 clipW,4 screen,5 sky,6 foreground,7 aboveSurface,8 nextTravel,9 accepted,10 finalResidual,11 refinement.\n";
        std::ofstream state(artifacts/"state.csv"),iterations(artifacts/"iterations.csv"),texels(artifacts/"depth-texels.csv"),hits(artifacts/"physical-receivers.csv");
        state<<std::setprecision(10);iterations<<std::setprecision(10);texels<<std::setprecision(10);hits<<std::setprecision(12);
        state<<"filter,endpoint,shift,mode,attachment,x,y,z,w\n";
        iterations<<"filter,endpoint,shift,iteration,reason,travel,clipW,u,v,depth,receiverX,receiverY,receiverZ,nextTravel,residual,tolerance,receiverAbsY,bankClearance,surfaceClearance\n";
        texels<<"filter,endpoint,shift,iteration,texelX,texelY,weight,face,part,worldY,depth,C4R,C4G,C4B\n";
        hits<<"filter,endpoint,shift,ray,valid,inside,boundary,boxId,part,axis,side,travel,hitX,hitY,hitZ,C4R,C4G,C4B,cameraVisible,cameraOcclusionDistance,belowFragmentY\n";
        const int pixel=target?target->y*size+target->x:46*size+65;
        const float endpoints[2][2]={{0.0464765616f,0.0464843735f},{0.0484453142f,0.0484531298f}};
        for(int filterIndex=0;filterIndex<2;++filterIndex) {
            const GLint filter=filterIndex==0?GL_NEAREST:GL_LINEAR;const char* filterName=filterIndex==0?"NEAREST":"LINEAR";
            std::array<Hit,2> refractedHits;std::array<std::array<std::array<float,4>,7>,2> top;
            for(int endpoint=0;endpoint<2;++endpoint) {
                const float shift=target?target->shifts[endpoint]:endpoints[filterIndex][endpoint];const Scene input=scene(shift,0);const auto reference=draw(0,input,filter);
                save(std::string(filterName)+"-"+std::to_string(endpoint)+"-baseline",reference);
                std::ofstream inputFile(artifacts/(std::string(filterName)+"-"+std::to_string(endpoint)+"-input.csv"));inputFile<<std::setprecision(10)<<"x,y,face,part,worldY,depth,C4R,C4G,C4B\n";
                for(int q=0;q<size*size;++q) inputFile<<q%size<<","<<q/size<<","<<input.face[q]<<","<<input.part[q]<<","<<input.height[q]<<","<<input.depth[q]<<","<<input.colour[q*4]<<","<<input.colour[q*4+1]<<","<<input.colour[q*4+2]<<"\n";
                top[endpoint]=capture(0,0,input,filter,pixel,reference);const auto transport=capture(2,0,input,filter,pixel,reference);
                for(int mode:{0,2}) {const auto& data=mode==0?top[endpoint]:transport;for(int attachment=0;attachment<7;++attachment) {state<<filterName<<","<<endpoint<<","<<shift<<","<<mode<<","<<attachment+1;for(float value:data[attachment]) state<<","<<value;state<<"\n";}}
                std::cout<<std::setprecision(10)<<"DEBUG-shore-causal "<<filterName<<" endpoint="<<endpoint<<" b="<<shift<<" pixel="<<pixel%size<<","<<pixel/size<<" C0="<<reference[pixel*4]<<","<<reference[pixel*4+1]<<","<<reference[pixel*4+2]
                         <<" origin="<<top[endpoint][0][0]<<","<<top[endpoint][0][1]<<","<<top[endpoint][0][2]<<" verticalDepth="<<top[endpoint][0][3]<<" initialPath="<<top[endpoint][1][3]
                         <<" n="<<top[endpoint][2][0]<<","<<top[endpoint][2][1]<<","<<top[endpoint][2][2]<<" transmitted="<<top[endpoint][3][0]<<","<<top[endpoint][3][1]<<","<<top[endpoint][3][2]
                         <<" kind="<<top[endpoint][4][3]<<" confidence="<<top[endpoint][3][3]<<" opticalPath="<<top[endpoint][2][3]<<" returnedUV="<<top[endpoint][5][0]<<","<<top[endpoint][5][1]<<"\n";
                for(int rayIndex=0;rayIndex<2;++rayIndex) {
                    const auto& originData=rayIndex==0?top[endpoint][0]:transport[0];const auto& rayData=rayIndex==0?top[endpoint][3]:transport[1];
                    const V3 origin={originData[0],originData[1],originData[2]},ray={rayData[0],rayData[1],rayData[2]};const Hit hit=physical(shift,origin,ray);
                    if(rayIndex==0) refractedHits[endpoint]=hit;
                    const Hit camera=hit.valid?physical(shift,{0,0,0},hit.point):Hit{};double occlusionDistance=0;
                    for(int c=0;c<3;++c) occlusionDistance+=std::pow(camera.point[c]-hit.point[c],2);
                    occlusionDistance=std::sqrt(occlusionDistance);
                    const bool visible=hit.valid && camera.valid && occlusionDistance<0.0001;
                    hits<<filterName<<","<<endpoint<<","<<shift<<","<<(rayIndex==0?"refracted":"reflected")<<","<<hit.valid<<","<<hit.inside<<","<<hit.boundary<<","<<hit.id<<","<<hit.part<<","<<hit.axis<<","<<hit.side<<","<<hit.travel;
                    for(double value:hit.point) hits<<","<<value;
                    for(double value:hit.colour) hits<<","<<value;
                    hits<<","<<visible<<","<<occlusionDistance<<","<<(hit.valid && hit.point[1]<top[endpoint][0][1])<<"\n";
                    std::cout<<"DEBUG-shore-causal physical "<<(rayIndex==0?"refracted":"reflected")<<" firstBox="<<hit.id<<" part="<<hit.part<<" axis/side="<<hit.axis<<"/"<<hit.side<<" t="<<hit.travel<<" point="<<hit.point[0]<<","<<hit.point[1]<<","<<hit.point[2]<<" C4="<<hit.colour[0]<<","<<hit.colour[1]<<","<<hit.colour[2]<<" cameraVisible="<<visible<<" cameraOcclusionDistance="<<occlusionDistance<<" insideOrigin="<<hit.inside<<" boundaryAmbiguous="<<hit.boundary<<"\n";
                }
                for(int iteration=0;iteration<9;++iteration) {
                    const auto data=capture(1,iteration,input,filter,pixel,reference);const float reason=data[3][0];
                    iterations<<filterName<<","<<endpoint<<","<<shift<<","<<iteration<<","<<reason;
                    for(float value:data[0]) iterations<<","<<value;
                    for(float value:data[1]) iterations<<","<<value;
                    iterations<<","<<data[2][0]<<","<<data[2][1]<<","<<data[2][2]<<","<<data[3][1]<<","<<data[3][2]<<","<<data[3][3]<<"\n";
                    std::cout<<"DEBUG-shore-causal step "<<filterName<<" endpoint="<<endpoint<<" i="<<iteration<<" reason="<<reason<<" travel="<<data[0][0]<<" UV="<<data[0][2]<<","<<data[0][3]<<" depth="<<data[1][0]<<" receiver="<<data[1][1]<<","<<data[1][2]<<","<<data[1][3]<<" residual/tolerance="<<data[2][1]<<"/"<<data[2][2]<<"\n";
                    if(reason==0 || reason==2 || reason==3 || reason==4) continue;
                    const double u=data[0][2]*size,v=data[0][3]*size;
                    const int x0=int(std::floor(filter==GL_NEAREST?u:u-0.5)),y0=int(std::floor(filter==GL_NEAREST?v:v-0.5));
                    const double fractionX=u-0.5-x0,fractionY=v-0.5-y0;const int extent=filter==GL_NEAREST?1:2;
                    for(int dy=0;dy<extent;++dy) for(int dx=0;dx<extent;++dx) {
                        const int x=std::clamp(x0+dx,0,size-1),y=std::clamp(y0+dy,0,size-1),q=y*size+x;
                        const double weight=filter==GL_NEAREST?1:(dx?fractionX:1-fractionX)*(dy?fractionY:1-fractionY);
                        texels<<filterName<<","<<endpoint<<","<<shift<<","<<iteration<<","<<x<<","<<y<<","<<weight<<","<<input.face[q]<<","<<input.part[q]<<","<<input.height[q]<<","<<input.depth[q]<<","<<input.colour[q*4]<<","<<input.colour[q*4+1]<<","<<input.colour[q*4+2]<<"\n";
                    }
                }
            }
            double receiverMovement=0,colourChange=0;for(int c=0;c<3;++c) {receiverMovement+=std::pow(refractedHits[0].point[c]-refractedHits[1].point[c],2);colourChange=std::max(colourChange,std::abs(refractedHits[0].colour[c]-refractedHits[1].colour[c]));}
            std::cout<<"DEBUG-shore-causal independent first physical receiver endpoint movement="<<std::sqrt(receiverMovement)<<"m C4difference="<<colourChange<<" box="<<refractedHits[0].id<<"→"<<refractedHits[1].id<<" part="<<refractedHits[0].part<<"→"<<refractedHits[1].part<<" (identity alone is not a continuity oracle)\n";
        }
        cleanup();std::cout<<"DEBUG-shore-causal complete: targeted observations only, no shipping change or default acceptance assertion\n";return;
    }
    const Scene neutral=scene(0,0),reflection=scene(0,1),deep=scene(0,2),shallow=scene(0,3);
    // Read actual displaced/rasterized depth through the unchanged production
    // vertex program. RMS wave height is not a peak-displacement assumption.
    Scene geometryInput=neutral;std::fill(geometryInput.depth.begin(),geometryInput.depth.end(),1.0f);
    glDepthMask(GL_TRUE);draw(0,geometryInput,GL_NEAREST);
    std::vector<float> geometryDepth(size*size),surfaceY(size*size,0);
    glReadPixels(0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,geometryDepth.data());glDepthMask(GL_FALSE);
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Actual production water geometry depth read failed");
    for(int pixel=0;pixel<size*size;++pixel) if(geometryDepth[pixel]<0.999999f) {
        const float travel=b/(2*geometryDepth[pixel]-1+a),rayY=(2.0f*(pixel/size+0.5f)/size-1)/f;
        surfaceY[pixel]=travel*rayY;
    }
    std::ofstream inputs(artifacts/"inputs.csv");inputs<<"x,y,depth,worldY,face,part,actualWaterY,waterDepth\n";
    for(int pixel=0;pixel<size*size;++pixel) inputs<<pixel%size<<","<<pixel/size<<","<<std::setprecision(9)<<neutral.depth[pixel]<<","<<neutral.height[pixel]<<","<<neutral.face[pixel]<<","<<neutral.part[pixel]<<","<<surfaceY[pixel]<<","<<geometryDepth[pixel]<<"\n";
    std::cout<<"DIAGNOSTIC frozen phase1.25,129x129,FOV60,waterY-.5,bank B=b+max(0,floor((-z-2)/4)),C8/Sun0,foam0\n";
    std::cout<<"DIAGNOSTIC ROI x20..108 y10..56, original view ray below horizon, alpha1 in both endpoints; actual source/visibility edges are not failures\n";
    std::array<std::vector<float>,4> neutralOutputs;
    std::array<float,4> tagResponses;
    std::array<std::vector<float>,4> deepOutputs,shallowOutputs;
    // Nonvacuous source controls precede any perturbation or apparent seam.
    for(GLint filter:{GL_NEAREST,GL_LINEAR}) for(int variant=0;variant<4;++variant) {
        const auto clear=draw(variant,neutral,filter),tag=draw(variant,reflection,filter),bed=draw(variant,deep,filter),ledge=draw(variant,shallow,filter),repeat=draw(variant,neutral,filter);
        if(filter==GL_NEAREST) {neutralOutputs[variant]=clear;deepOutputs[variant]=bed;shallowOutputs[variant]=ledge;}
        tagResponses[variant]=maxDifference(clear,tag);
        const float deepResponse=maxDifference(clear,bed),shallowResponse=maxDifference(clear,ledge),repeatError=maxDifference(clear,repeat,nullptr,false);
        int count=0;for(int pixel=0;pixel<size*size;++pixel) if(roi(pixel)&&clear[pixel*4+3]==1) ++count;
        std::cout<<"DIAGNOSTIC "<<(filter==GL_NEAREST?"NEAREST":"LINEAR")<<" "<<names[variant]<<" controls: waterROI="<<count<<" reflectionTag="<<tagResponses[variant]<<" deepBed="<<deepResponse<<" shallowLedge="<<shallowResponse<<" deterministicRepeat="<<repeatError<<"\n";
        if(count<100 || deepResponse<=0.00001f || repeatError>0.000001f) throw std::runtime_error("Shore diagnostic is vacuous or nondeterministic: retain actual deep receiver before interpreting bands");
        if((variant==0||variant==1) && tagResponses[variant]<=0.00001f) throw std::runtime_error("Above-water reflection target has no real production-main response; do not hide an absent SSR positive control");
        if(variant==2 && tagResponses[variant]>0.000001f) throw std::runtime_error("Reflection-only target reaches refraction/proxy in the selected ROI; correct fixture provenance before interpreting SSR override");
        const std::string prefix=std::string(names[variant])+(filter==GL_LINEAR?"-LINEAR":"");
        save(prefix+"-neutral",clear);save(prefix+"-reflection-tag",tag);save(prefix+"-deep-tag",bed);save(prefix+"-shallow-tag",ledge);
        std::ofstream responses(artifacts/(prefix+"-responses.csv"));responses<<"x,y,alpha,reflectionR,deepG,shallowG\n";
        for(int pixel=0;pixel<size*size;++pixel) if(roi(pixel)) responses<<pixel%size<<","<<pixel/size<<","<<clear[pixel*4+3]<<","<<std::setprecision(9)<<tag[pixel*4]-clear[pixel*4]<<","<<bed[pixel*4+1]-clear[pixel*4+1]<<","<<ledge[pixel*4+1]-clear[pixel*4+1]<<"\n";
    }
    for(int variant=1;variant<4;++variant) std::cout<<"DIAGNOSTIC "<<names[variant]<<" versus baseline max rawHDR ROI difference "<<maxDifference(neutralOutputs[0],neutralOutputs[variant])<<"\n";
    std::ofstream greenFields(artifacts/"green-source-path-difference.csv");greenFields<<"x,y,originalFace,originalPart,originalY,deepResponseBaselineMinusEnv,shallowResponseBaselineMinusEnv\n";
    float greenPathDifference[2]={0,0};int greenWhere[2]={-1,-1};
    for(int pixel=0;pixel<size*size;++pixel) if(roi(pixel) && neutralOutputs[0][pixel*4+3]==1 && neutralOutputs[2][pixel*4+3]==1) {
        float difference[2];
        for(int tag=0;tag<2;++tag) {
            const auto& outputs=tag==0?deepOutputs:shallowOutputs;
            difference[tag]=(outputs[0][pixel*4+1]-neutralOutputs[0][pixel*4+1])-(outputs[2][pixel*4+1]-neutralOutputs[2][pixel*4+1]);
            if(std::abs(difference[tag])>greenPathDifference[tag]) {greenPathDifference[tag]=std::abs(difference[tag]);greenWhere[tag]=pixel;}
        }
        greenFields<<pixel%size<<","<<pixel/size<<","<<neutral.face[pixel]<<","<<neutral.part[pixel]<<","<<neutral.height[pixel]<<","<<std::setprecision(9)<<difference[0]<<","<<difference[1]<<"\n";
    }
    for(int tag=0;tag<2;++tag) {
        const int pixel=greenWhere[tag];std::cout<<"DIAGNOSTIC NEAREST pointwise "<<(tag==0?"deep-bed part0":"shallow-ledge part1")<<" green response baseline-minus-environment-only max="<<greenPathDifference[tag];
        if(pixel>=0) std::cout<<" at "<<pixel%size<<","<<pixel/size<<" originalFace="<<neutral.face[pixel]<<" originalPart="<<neutral.part[pixel]<<" originalY="<<neutral.height[pixel];
        std::cout<<"\n";
    }
    float deepChange=0,minimumDeepClearance=farPlane;int deepCount=0;
    for(int y=10;y<=56;++y) for(int x=20;x<=108;++x) {
        const int pixel=y*size+x;bool safe=neutral.part[pixel]==0 && neutral.height[pixel]<-1.7f;
        // Guard full derivative quad as depth64 changes normal derivatives too.
        const int quadX=x&~1,quadY=y&~1;
        float clearance=farPlane;
        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {const int q=(quadY+dy)*size+quadX+dx;if(neutral.part[q]!=0 || neutral.height[q]>=-1.7f || geometryDepth[q]>=0.999999f) safe=false;clearance=std::min(clearance,surfaceY[q]-neutral.height[q]);}
        if(clearance<0.85f) safe=false;
        if(safe && neutralOutputs[0][pixel*4+3]==1 && neutralOutputs[3][pixel*4+3]==1) {++deepCount;minimumDeepClearance=std::min(minimumDeepClearance,clearance);for(int c=0;c<3;++c) deepChange=std::max(deepChange,std::abs(neutralOutputs[0][pixel*4+c]-neutralOutputs[3][pixel*4+c]));}
    }
    std::cout<<"DIAGNOSTIC depth64 safely-deep derivative-quad ROI count="<<deepCount<<" minimum measured water/receiver clearance="<<minimumDeepClearance<<"m max rawHDR change="<<deepChange<<"\n";
    if(deepCount<100 || deepChange>0.000001f) throw std::runtime_error("Depth64 override changes safely-deep pixels; diagnostic isolation or depth qualification failed");
    auto stableOriginal=[&](const Scene& l,const Scene& r,const std::vector<float>& lo,const std::vector<float>& hi,int pixel,float shiftL,float shiftR,GLint filter) {
        const int quadX=(pixel%size)&~1,quadY=(pixel/size)&~1,pad=filter==GL_LINEAR?1:0;
        for(int dy=-pad;dy<2+pad;++dy) for(int dx=-pad;dx<2+pad;++dx) {
            const int x=quadX+dx,y=quadY+dy;if(x<0||x>=size||y<0||y>=size) return false;
            const int q=y*size+x;
            if(l.face[q]<0 || l.face[q]!=r.face[q] || l.part[q]!=r.part[q] || l.part[q]==3 || lo[q*4+3]!=1 || hi[q*4+3]!=1) return false;
            // Same face can cross the deliberately sharp wet/dry input palette
            // at worldY=-.5. Qualify actual total C4, not identity alone.
            for(int c=0;c<3;++c) if(std::abs(l.colour[q*4+c]-r.colour[q*4+c])>0.000001f) return false;
            const float travelL=b/(2*l.depth[q]-1+a),travelR=b/(2*r.depth[q]-1+a),rayX=(2.0f*(x+0.5f)/size-1)/f;
            if(std::abs(travelL*rayX-shiftL)>7.5f || std::abs(travelR*rayX-shiftR)>7.5f || travelL>23 || travelR>23 || travelL<0.5f || travelR<0.5f) return false;
        }
        return true;
    };
    std::ofstream jumps(artifacts/"jumps.csv");jumps<<"filter,qualification,variant,x,y,qualifiedCoarsePairs,coarseLower,coarseUpper,coarseJump,fineLower,fineUpper,fineJump,lowerFace,upperFace,lowerPart,upperPart,lowerY,upperY,lowerR,lowerG,lowerB,upperR,upperG,upperB,lowerAlpha,upperAlpha,tagDeltaLower,tagDeltaUpper\n";
    std::ofstream endpointInputs(artifacts/"endpoint-inputs.csv");endpointInputs<<"filter,qualification,variant,endpoint,shift,x,y,face,part,worldY,depth,C4R,C4G,C4B,alpha,actualWaterY\n";
    std::ofstream comparisons(artifacts/"same-baseline-bracket.csv");comparisons<<"filter,qualification,variant,x,y,baselineFineLower,baselineFineUpper,samePixelRGBjump\n";
    for(GLint filter:{GL_NEAREST,GL_LINEAR}) for(bool qualified:{false,true}) for(int variant=0;variant<4;++variant) {
        float lower=-0.05f,upper=lower,largest=0,previousShift=lower;int worst=-1;size_t qualifiedPairs=0;
        Scene previousScene=scene(lower,0);auto previous=draw(variant,previousScene,filter),left=previous,right=previous;
        for(int step=1;step<=50;++step) {
            const float shift=-0.05f+0.002f*step;const Scene currentScene=scene(shift,0);const auto current=draw(variant,currentScene,filter);
            for(int pixel=0;pixel<size*size;++pixel) if(roi(pixel) && previous[pixel*4+3]==1 && current[pixel*4+3]==1
                && (!qualified || stableOriginal(previousScene,currentScene,previous,current,pixel,previousShift,shift,filter))) {
                ++qualifiedPairs;
                for(int c=0;c<3;++c) if(std::abs(previous[pixel*4+c]-current[pixel*4+c])>largest) {largest=std::abs(previous[pixel*4+c]-current[pixel*4+c]);lower=previousShift;upper=shift;worst=pixel;left=previous;right=current;}
            }
            previous=current;previousScene=currentScene;previousShift=shift;
        }
        if(worst<0 || qualifiedPairs<1000) throw std::runtime_error("Shore diagnostic has no qualified perturbation population; do not hide absent coverage");
        const float coarseLower=lower,coarseUpper=upper;
        auto atPixel=[&](const std::vector<float>& l,const std::vector<float>& r) {float difference=0;for(int c=0;c<3;++c) difference=std::max(difference,std::abs(l[worst*4+c]-r[worst*4+c]));return difference;};
        bool refinementQualificationLost=false;
        for(int refine=0;refine<8;++refine) {
            const float mid=(lower+upper)*0.5f;const Scene middleScene=scene(mid,0);const auto middle=draw(variant,middleScene,filter);
            if(middle[worst*4+3]!=1 || (qualified && (!stableOriginal(scene(lower,0),middleScene,left,middle,worst,lower,mid,filter)
                || !stableOriginal(middleScene,scene(upper,0),middle,right,worst,mid,upper,filter)))) {refinementQualificationLost=true;break;}
            if(atPixel(left,middle)>atPixel(middle,right)) {upper=mid;right=middle;}else {lower=mid;left=middle;}
        }
        const auto inputLower=scene(lower,0),inputUpper=scene(upper,0);
        const auto tagLower=draw(variant,scene(lower,1),filter),tagUpper=draw(variant,scene(upper,1),filter);
        const float responseLower=tagLower[worst*4]-left[worst*4],responseUpper=tagUpper[worst*4]-right[worst*4];
        const char* filterName=filter==GL_NEAREST?"NEAREST":"LINEAR",*qualification=qualified?"stable-original-quad":"raw";
        std::cout<<std::setprecision(9)<<"DIAGNOSTIC "<<filterName<<" "<<qualification<<" "<<names[variant]<<" qualifiedCoarsePairs="<<qualifiedPairs<<" largest coarse bracket="<<coarseLower<<".."<<coarseUpper<<" pixel="<<worst%size<<","<<worst/size<<" RGBjump="<<largest
                 <<"; fixed-pixel refined="<<lower<<".."<<upper<<" perturbation="<<upper-lower<<" RGBjump="<<atPixel(left,right)<<" originalFace="<<inputLower.face[worst]<<"→"<<inputUpper.face[worst]
                 <<" part="<<inputLower.part[worst]<<"→"<<inputUpper.part[worst]<<" originalY="<<inputLower.height[worst]<<"→"<<inputUpper.height[worst]
                 <<" originalC4=("<<inputLower.colour[worst*4]<<","<<inputLower.colour[worst*4+1]<<","<<inputLower.colour[worst*4+2]<<")→("<<inputUpper.colour[worst*4]<<","<<inputUpper.colour[worst*4+1]<<","<<inputUpper.colour[worst*4+2]<<")"
                 <<" alpha="<<left[worst*4+3]<<"→"<<right[worst*4+3]<<" reflectionTag="<<responseLower<<"→"<<responseUpper<<" refinementQualificationLost="<<refinementQualificationLost<<"\n";
        jumps<<filterName<<","<<qualification<<","<<names[variant]<<","<<worst%size<<","<<worst/size<<","<<qualifiedPairs<<","<<coarseLower<<","<<coarseUpper<<","<<largest<<","<<lower<<","<<upper<<","<<atPixel(left,right)<<","<<inputLower.face[worst]<<","<<inputUpper.face[worst]<<","<<inputLower.part[worst]<<","<<inputUpper.part[worst]<<","<<inputLower.height[worst]<<","<<inputUpper.height[worst];
        for(const Scene* input:{&inputLower,&inputUpper}) for(int c=0;c<3;++c) jumps<<","<<input->colour[worst*4+c];
        jumps<<","<<left[worst*4+3]<<","<<right[worst*4+3]<<","<<responseLower<<","<<responseUpper<<"\n";
        const int quadX=(worst%size)&~1,quadY=(worst/size)&~1,pad=filter==GL_LINEAR?1:0;
        for(int endpoint=0;endpoint<2;++endpoint) {
            const Scene& input=endpoint==0?inputLower:inputUpper;const auto& output=endpoint==0?left:right;
            for(int dy=-pad;dy<2+pad;++dy) for(int dx=-pad;dx<2+pad;++dx) {
                const int x=quadX+dx,y=quadY+dy,q=y*size+x;
                endpointInputs<<filterName<<","<<qualification<<","<<names[variant]<<","<<endpoint<<","<<(endpoint==0?lower:upper)<<","<<x<<","<<y<<","<<input.face[q]<<","<<input.part[q]<<","<<std::setprecision(9)<<input.height[q]<<","<<input.depth[q];
                for(int c=0;c<3;++c) endpointInputs<<","<<input.colour[q*4+c];
                endpointInputs<<","<<output[q*4+3]<<","<<surfaceY[q]<<"\n";
            }
        }
        const std::string prefix=std::string(names[variant])+"-"+filterName+"-"+qualification;
        save(prefix+"-coarse-lower",draw(variant,scene(coarseLower,0),filter));save(prefix+"-coarse-upper",draw(variant,scene(coarseUpper,0),filter));save(prefix+"-fine-lower",left);save(prefix+"-fine-upper",right);
        // Compare exactly the baseline's pixel/endpoints, not independently
        // selected maxima, before describing any ablation as a seam A/B.
        if(variant==0) for(int other=0;other<4;++other) {
            const auto lo=draw(other,inputLower,filter),hi=draw(other,inputUpper,filter);
            std::cout<<"DIAGNOSTIC same-baseline bracket "<<filterName<<" "<<qualification<<" "<<names[other]<<" pixel="<<worst%size<<","<<worst/size<<" RGBjump="<<atPixel(lo,hi)<<"\n";
            comparisons<<filterName<<","<<qualification<<","<<names[other]<<","<<worst%size<<","<<worst/size<<","<<lower<<","<<upper<<","<<atPixel(lo,hi)<<"\n";
        }
    }
    cleanup();
    std::cout<<"DIAGNOSTIC complete: source controls/isolation valid; jumps are measurements, NOT a physical-edge smoothness assertion or Minecraft FPS measurement\n";
}
#include "water-optical-depth-probe.h"
#include "bathymetry-gradient-probe.h"
#include "solar-cloud-probe.h"
#include "water-radiance-probe.h"
#include "underwater-angular-probe.h"
#include "underwater-backface-probe.h"
int main(int argc,char** argv) {
    try {
        if(argc<2) throw std::runtime_error("usage: glcheck <shaders> [width height | --foreground-haze-probe | --underwater-sky-only | --shallow-water-only | --shore-continuity-only | --underwater-caustic-only | --water-incident-only | --above-water-incident-only | --shore-diagnostic-only | --shore-causal-only | --shore-visible-bed-only | --shore-causal-target x y lower upper | --shore-visible-bed-target x y lower upper | --solar-coherence-only | --solar-weather-only | --solar-coverage-only | --solar-1440p-only | --solar-phase-only]");
        const bool foregroundHazeOnly=argc>2 && std::string(argv[2])=="--foreground-haze-probe";
        const bool waterOpticalDepthOnly=argc>2 && std::string(argv[2])=="--water-optical-depth-only";
        const bool waterBathymetryOnly=argc>2 && std::string(argv[2])=="--water-bathymetry-only";
        const bool waterRadianceOnly=argc>2 && std::string(argv[2])=="--water-radiance-only";
        const bool underwaterAngularOnly=argc>2 && std::string(argv[2])=="--underwater-angular-only";
        const bool underwaterNearReflectionOnly=argc>2 && std::string(argv[2])=="--underwater-near-reflection-only";
        const bool underwaterBackfaceOnly=argc>2 && std::string(argv[2])=="--underwater-backface-only";
        if(underwaterBackfaceOnly) {
            if(argc!=4||fs::path(argv[3]).empty()||fs::exists(fs::path(argv[3])))
                throw std::runtime_error("usage: glcheck <shaders> --underwater-backface-only NEW-artifact-directory; confirmed same-plane +/-top; reject overwrite before EGL");
        }
        const bool compileOnly=argc>2 && std::string(argv[2])=="--compile-only";
        if(compileOnly&&argc!=3)throw std::runtime_error("usage: glcheck <shaders> --compile-only; compile/link only, no behavior test");
        aqualumenUnderwaterAngularDetail::Input underwaterAngularInput;
        if(underwaterAngularOnly||underwaterNearReflectionOnly) {
            if((argc!=4&&argc!=5)||(underwaterNearReflectionOnly&&argc!=4))
                throw std::runtime_error(underwaterNearReflectionOnly
                    ?"usage: glcheck <shaders> --underwater-near-reflection-only NEW-artifact-directory; frozen native near-wall receiver, not actual scene"
                    :"usage: glcheck <shaders> --underwater-angular-only NEW-artifact-directory [four-matrix-packet]; bounded flat angular replay, not actual scene");
            const fs::path artifact=argv[3];
            if(artifact.empty()||fs::exists(artifact))
                throw std::runtime_error("Underwater-angular requires a nonempty NEW artifact directory before EGL initialization");
            underwaterAngularInput=aqualumenUnderwaterAngularDetail::input(argc==5?fs::path(argv[4]):fs::path{});
        }
        if(waterRadianceOnly&&argc!=3&&argc!=4)
            throw std::runtime_error("usage: glcheck <shaders> --water-radiance-only [new-artifact-directory]; fixed flat1.5m/zenith/vertical centre32,32");
        if(waterRadianceOnly) {
            const fs::path artifact=argc==4?fs::path(argv[3]):fs::path("build/water-direct-radiance");
            if(artifact.empty()||fs::exists(artifact))
                throw std::runtime_error("Water-radiance requires a nonempty NEW artifact directory; reject overwrite before EGL initialization");
        }
        const bool firstVisibleBedLinearOnly=argc>2 && std::string(argv[2])=="--first-visible-bed-linear-only";
        const bool firstVisibleBedWavesOnly=argc>2 && std::string(argv[2])=="--first-visible-bed-waves-only";
        const bool firstVisibleBedOnly=argc>2 && (std::string(argv[2])=="--first-visible-bed-only"||firstVisibleBedLinearOnly||firstVisibleBedWavesOnly);
        if(firstVisibleBedWavesOnly&&argc!=3&&argc!=4)
            throw std::runtime_error("usage: glcheck <shaders> --first-visible-bed-waves-only [new-artifact-directory]; fixed65,48/phase1.25/WAVE_HEIGHT.12/NEAREST");
        const bool bathymetryGradientOnly=argc>2 && std::string(argv[2])=="--bathymetry-gradient-only";
        if(bathymetryGradientOnly && argc!=3 && argc!=4)
            throw std::runtime_error("usage: glcheck <shaders> --bathymetry-gradient-only [new-artifact-directory]");
        const bool waterDepthOnly=waterOpticalDepthOnly||waterBathymetryOnly||bathymetryGradientOnly||firstVisibleBedOnly;
        if(waterDepthOnly && argc!=3 && argc!=4 && argc!=6)
            throw std::runtime_error("usage: glcheck <shaders> --water-{optical-depth,bathymetry}-only or --first-visible-bed-only [new-artifact-directory [x y]]");
        const bool underwaterSkyOnly=argc>2 && std::string(argv[2])=="--underwater-sky-only";
        const bool shallowWaterOnly=argc>2 && std::string(argv[2])=="--shallow-water-only";
        const bool shoreContinuityOnly=argc>2 && std::string(argv[2])=="--shore-continuity-only";
        const bool underwaterCausticOnly=argc>2 && std::string(argv[2])=="--underwater-caustic-only";
        const bool waterIncidentOnly=argc>2 && std::string(argv[2])=="--water-incident-only";
        const bool aboveWaterIncidentOnly=argc>2 && std::string(argv[2])=="--above-water-incident-only";
        const bool shoreDiagnosticOnly=argc>2 && std::string(argv[2])=="--shore-diagnostic-only";
        const bool shoreCausalOnly=argc>2 && std::string(argv[2])=="--shore-causal-only";
        const bool shoreCausalTargetOnly=argc>2 && std::string(argv[2])=="--shore-causal-target";
        const bool shoreVisibleBedLinearTargetOnly=argc>2 && std::string(argv[2])=="--shore-visible-bed-linear-target";
        const bool shoreVisibleBedTargetOnly=argc>2 && (std::string(argv[2])=="--shore-visible-bed-target"||shoreVisibleBedLinearTargetOnly);
        ShoreCausalTarget causalTarget={0,0,{0,0},1.25f,{}};
        if(shoreCausalTargetOnly || shoreVisibleBedTargetOnly) {
            if(argc<7 || argc>9) throw std::runtime_error("usage: glcheck <shaders> --shore-{causal,visible-bed}-target x y lowerShift upperShift [phase [new-artifact-directory]]");
            causalTarget={std::stoi(argv[3]),std::stoi(argv[4]),{std::stof(argv[5]),std::stof(argv[6])},argc>=8?std::stof(argv[7]):1.25f,argc==9?fs::path(argv[8]):fs::path{}};
            causalTarget.filter=shoreVisibleBedLinearTargetOnly?GL_LINEAR:GL_NEAREST;
            if(causalTarget.x<1 || causalTarget.x>127 || causalTarget.y<1 || causalTarget.y>127
                || !std::isfinite(causalTarget.shifts[0]) || !std::isfinite(causalTarget.shifts[1])
                || !std::isfinite(causalTarget.phase) || causalTarget.phase<0.0f
                || causalTarget.shifts[0]<-0.05f || causalTarget.shifts[1]>0.05f
                || causalTarget.shifts[0]>=causalTarget.shifts[1])
                throw std::runtime_error("Causal target must be an interior 129x129 pixel and an ordered finite shift pair in [-.05,.05]");
        }
        const bool shoreVisibleBedOnly=argc>2 && std::string(argv[2])=="--shore-visible-bed-only";
        const bool shoreReflectionOnly=argc>2 && std::string(argv[2])=="--shore-reflection-only";
        const bool solarCoherenceOnly=argc>2 && std::string(argv[2])=="--solar-coherence-only";
        const bool solarWeatherOnly=argc>2 && std::string(argv[2])=="--solar-weather-only";
        const bool solarCoverageOnly=argc>2 && std::string(argv[2])=="--solar-coverage-only";
        const bool solar1440pOnly=argc>2 && std::string(argv[2])=="--solar-1440p-only";
        const bool solarPhaseOnly=argc>2 && std::string(argv[2])=="--solar-phase-only";
        const bool solarCloudObserverOnly=argc>2 && std::string(argv[2])=="--solar-cloud-observer-only";
        if(solarCloudObserverOnly && argc!=3 && argc!=4 && argc!=6)
            throw std::runtime_error("usage: glcheck <shaders> --solar-cloud-observer-only [new-artifact-directory [half-separation phase]]");
        const bool solarOnly=solarCoherenceOnly||solarWeatherOnly||solarCoverageOnly||solar1440pOnly||solarPhaseOnly||solarCloudObserverOnly;
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
        int width=compileOnly?1:(underwaterAngularOnly||underwaterNearReflectionOnly)?underwaterAngularInput.width:(solarOnly?1:(shoreDiagnosticOnly||shoreCausalOnly||shoreCausalTargetOnly||shoreVisibleBedTargetOnly||shoreVisibleBedOnly||shoreReflectionOnly||waterDepthOnly)?129:((underwaterBackfaceOnly||waterRadianceOnly||underwaterSkyOnly||shallowWaterOnly||shoreContinuityOnly||underwaterCausticOnly||waterIncidentOnly||aboveWaterIncidentOnly)?65:(foregroundHazeOnly?16:(argc>2?std::stoi(argv[2]):2560)))),height=compileOnly?1:(underwaterAngularOnly||underwaterNearReflectionOnly)?underwaterAngularInput.height:(solarOnly?1:(shoreDiagnosticOnly||shoreCausalOnly||shoreCausalTargetOnly||shoreVisibleBedTargetOnly||shoreVisibleBedOnly||shoreReflectionOnly||waterDepthOnly)?129:((underwaterBackfaceOnly||waterRadianceOnly||underwaterSkyOnly||shallowWaterOnly||shoreContinuityOnly||underwaterCausticOnly||waterIncidentOnly||aboveWaterIncidentOnly)?65:(foregroundHazeOnly?16:(argc>3?std::stoi(argv[3]):1440))));
        EGLint surfaceAttrs[]={EGL_WIDTH,width,EGL_HEIGHT,height,EGL_NONE};
        EGLSurface surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("Cannot create GL compatibility context");
        std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\nGL: "<<glGetString(GL_VERSION)<<'\n';
        fs::path root=argv[1];
        if(underwaterBackfaceOnly) {
            productionUnderwaterBackfaceProbe(root,fs::path(argv[3]));
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(underwaterAngularOnly||underwaterNearReflectionOnly) {
            productionUnderwaterAngularProbe(root,fs::path(argv[3]),underwaterAngularInput,underwaterNearReflectionOnly);
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(waterRadianceOnly) {
            productionWaterDirectRadianceProbe(root,argc==4?fs::path(argv[3]):fs::path("build/water-direct-radiance"));
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(solarCloudObserverOnly) {
            productionSolarCloudObserverInvariantProbe(root,argc>=4?fs::path(argv[3]):fs::path("build/solar-cloud-observer"),
                argc==6?std::stof(argv[4]):-1.0f,argc==6?std::stof(argv[5]):-1.0f);
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(bathymetryGradientOnly) {
            productionBathymetryGradientProbe(root,argc==4?fs::path(argv[3]):fs::path("build/bathymetry-gradient"));
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(waterDepthOnly) {
            productionWaterOpticalDepthProbe(root,argc>=4?fs::path(argv[3]):fs::path(firstVisibleBedWavesOnly?"build/first-visible-bed-waves":firstVisibleBedOnly?"build/first-visible-bed":waterBathymetryOnly?"build/water-bathymetry":"build/water-optical-depth"),true,
                argc==6?std::stoi(argv[4]):-1,argc==6?std::stoi(argv[5]):-1,waterBathymetryOnly||firstVisibleBedOnly,firstVisibleBedOnly,firstVisibleBedLinearOnly?GL_LINEAR:GL_NEAREST,firstVisibleBedWavesOnly);
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(shoreCausalTargetOnly || shoreVisibleBedTargetOnly || shoreReflectionOnly) {
            shoreDiagnosticProbe(root,true,shoreVisibleBedTargetOnly,shoreReflectionOnly?nullptr:&causalTarget,shoreReflectionOnly);
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            return 0;
        }
        if(foregroundHazeOnly || underwaterSkyOnly || shallowWaterOnly || shoreContinuityOnly || underwaterCausticOnly || waterIncidentOnly || aboveWaterIncidentOnly || shoreDiagnosticOnly || shoreCausalOnly || shoreVisibleBedOnly || solarOnly) {
            if(shoreVisibleBedOnly) shoreDiagnosticProbe(root,true,true);else if(solarPhaseOnly) productionSolarBeamCoherenceProbe(root,0.0f,2560,1440,60.0f,0.37f);else if(solarCoverageOnly) productionSolarBeamCoherenceProbe(root,0.0f,1600,900,60.0f);else if(solar1440pOnly) productionSolarBeamCoherenceProbe(root,0.0f,2560,1440,60.0f);else if(solarWeatherOnly) productionSolarBeamCoherenceProbe(root,1.0f);else if(solarCoherenceOnly) productionSolarBeamCoherenceProbe(root);else if(shoreCausalOnly) shoreDiagnosticProbe(root,true);else if(shoreDiagnosticOnly) shoreDiagnosticProbe(root);else if(aboveWaterIncidentOnly) aboveWaterIncidentDepthProbe(root);else if(waterIncidentOnly) waterIncidentDepthProbe(root);else if(underwaterCausticOnly) underwaterCausticProbe(root);else if(shoreContinuityOnly) shoreContinuityProbe(root);else if(shallowWaterOnly) {shallowWaterProbe(root);terrainSunSnapshotProbe(root);shoreContinuityProbe(root);}else if(underwaterSkyOnly) underwaterSkyProbe(root);else foregroundShadowHazeProbe(root);
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
        if(compileOnly) {
            std::vector<fs::path> computeFiles;
            for(auto& entry:fs::directory_iterator(root))if(entry.path().extension()==".csh")computeFiles.push_back(entry.path());
            std::sort(computeFiles.begin(),computeFiles.end());
            for(const auto& file:computeFiles){GLuint program=compute(file,root);glDeleteProgram(program);std::cout<<"PASS compile/link "<<file.filename().string()<<'\n';}
            eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
            std::cout<<"PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance\n";return 0;
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
            "void main(){float distance;int receiverKind;float receiverConfidence;vec3 ray=traceCase==0?normalize(vec3(0.7,-0.7,-0.14)):vec3(0,0,-1);float seed=traceCase==0?0.3:1.0;vec2 hit=refractionTrace(vec3(0),ray,vec2(0.5),seed,seed,true,0.0,distance,receiverKind,receiverConfidence);gl_FragColor=vec4(hit,distance,float(receiverKind));}";
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
        waterIncidentDepthProbe(root);
        aboveWaterIncidentDepthProbe(root);
        shoreDiagnosticProbe(root,true,true);
        shoreDiagnosticProbe(root,true,false,nullptr,true);
        productionSolarBeamCoherenceProbe(root);
        productionSolarBeamCoherenceProbe(root,1.0f);
        productionSolarBeamCoherenceProbe(root,0.0f,1600,900,60.0f);
        productionSolarBeamCoherenceProbe(root,0.0f,2560,1440,60.0f);
        productionSolarBeamCoherenceProbe(root,0.0f,2560,1440,60.0f,0.37f);
        std::cout<<files.size()<<" program pairs compiled and linked. This is not a Minecraft FPS benchmark.\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        return 0;
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
