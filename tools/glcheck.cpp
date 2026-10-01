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
GLuint link(const std::string& vs,const std::string& fragment,const std::string& name) {
    GLuint v=compile(GL_VERTEX_SHADER,vs,name+".vsh"),f=compile(GL_FRAGMENT_SHADER,fragment,name+".fsh");
    GLuint program=glCreateProgram();glAttachShader(program,v);glAttachShader(program,f);glLinkProgram(program);
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
int main(int argc,char** argv) {
    try {
        if(argc<2) throw std::runtime_error("usage: glcheck <shaders> [width height | --foreground-haze-probe]");
        const bool foregroundHazeOnly=argc>2 && std::string(argv[2])=="--foreground-haze-probe";
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
        int width=foregroundHazeOnly?16:(argc>2?std::stoi(argv[2]):2560),height=foregroundHazeOnly?16:(argc>3?std::stoi(argv[3]):1440);
        EGLint surfaceAttrs[]={EGL_WIDTH,width,EGL_HEIGHT,height,EGL_NONE};
        EGLSurface surface=eglCreatePbufferSurface(display,config,surfaceAttrs);
        EGLint contextAttrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
        if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context)) throw std::runtime_error("Cannot create GL compatibility context");
        std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\nGL: "<<glGetString(GL_VERSION)<<'\n';
        fs::path root=argv[1];
        if(foregroundHazeOnly) {
            foregroundShadowHazeProbe(root);
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
            "void main(){float distance;vec3 ray=traceCase==0?normalize(vec3(0.7,-0.7,-0.14)):vec3(0,0,-1);float seed=traceCase==0?0.3:1.0;vec2 hit=refractionTrace(vec3(0),ray,vec2(0.5),seed,true,0.0,distance);gl_FragColor=vec4(hit,distance,1.0);}";
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
        if(std::abs(measured[0]-0.5f)>0.00001f || std::abs(measured[1]-0.5f)>0.00001f || std::abs(measured[2]-0.3f)>0.00001f)
            throw std::runtime_error("Unconverged refraction must preserve original UV and Snell-depth fallback; path "+std::to_string(measured[2]));
        std::cout<<"PASS GPU production refraction trace: offscreen after unconverged iterate preserves original UV and initial optical path\n";
        receiverDepth=0.0f;glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_FLOAT,&receiverDepth);
        glUniform1i(glGetUniformLocation(trace,"traceCase"),1);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,measured);
        if(std::abs(measured[0]-0.5f)>0.00001f || std::abs(measured[1]-0.5f)>0.00001f || measured[2]!=1.0f)
            throw std::runtime_error("Converged refraction must commit the valid ray-distance hit");
        std::cout<<"PASS GPU production refraction trace: converged receiver commits valid 1m ray-distance hit\n";
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
        std::cout<<files.size()<<" program pairs compiled and linked. This is not a Minecraft FPS benchmark.\n";
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);
        return 0;
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
