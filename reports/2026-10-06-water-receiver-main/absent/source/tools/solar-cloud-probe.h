#ifndef AQUALUMEN_SOLAR_CLOUD_PROBE_H
#define AQUALUMEN_SOLAR_CLOUD_PROBE_H

// Opt-in production prepare -> terrain -> deferred source-consistency fixture.
// Include before glcheck main(), then call ONLY with the caller's GPU slot.
// Preparing this header is not a recorded RED. No cloud-density algorithm,
// lighting body, force-cloud constant or physical-depth oracle is substituted.
#include "solar-radiometry-probe.h"
#include <cstdint>
#include <fstream>
#include <limits>

namespace aqualumenSolarCloudDetail {
using M4=std::array<float,16>;
using V3=std::array<double,3>;
using V4=std::array<float,4>;
constexpr int lutWidth=64,lutHeight=32,receiverSize=17;
constexpr double pi=3.14159265358979323846;
constexpr double receiverHeight=63.0,cameraHeight=127.0;
const M4 identity={1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
const V3 receiverWorld={0,receiverHeight,0};

inline double dot(const V3& a,const V3& b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline V3 cross(const V3& a,const V3& b) {return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
inline V3 normalized(V3 a) {
    const double length=std::sqrt(dot(a,a));
    if(!(length>0)||!std::isfinite(length)) throw std::runtime_error("DEBUG-solar-cloud invalid fixture vector");
    for(double& value:a) value/=length;
    return a;
}
struct Pose {V3 camera;M4 view,inverse,shadowView,shadowProjection;V3 viewSun;};
inline Pose pose(const V3& camera,const V3& receiver) {
    Pose result;result.camera=camera;
    // Keep the same world receiver, but avoid the old 64m/2m grazing view.
    // Its raster interpolation error is not a reason to relax the receiver's
    // position guard. The two eyes now have the same 64m vertical separation.
    const V3 forward=normalized({receiver[0]-result.camera[0],receiver[1]-result.camera[1],receiver[2]-result.camera[2]});
    const V3 referenceUp=std::abs(forward[1])>0.99?V3{0,0,1}:V3{0,1,0};
    const V3 right=normalized(cross(forward,referenceUp)),up=cross(right,forward);
    result.view={float(right[0]),float(up[0]),float(-forward[0]),0,
                 float(right[1]),float(up[1]),float(-forward[1]),0,
                 float(right[2]),float(up[2]),float(-forward[2]),0, 0,0,0,1};
    result.inverse=identity;
    for(int row=0;row<3;++row) for(int col=0;col<3;++col) result.inverse[col*4+row]=result.view[row*4+col];
    result.viewSun={result.view[4],result.view[5],result.view[6]};
    // A fixed world shadow projection around the receiver, with a fully-lit
    // depth-comparison texture. Moving the eye cannot move an occluder here.
    result.shadowView=identity;
    for(int c=0;c<3;++c) result.shadowView[12+c]=float(result.camera[c]-receiver[c]);
    result.shadowProjection={0.001f,0,0,0, 0,0.001f,0,0, 0,0,0.001f,0, 0,0,0,1};
    return result;
}
inline Pose pose(double offset,const V3& receiver=receiverWorld) {
    return pose({receiver[0]+offset,cameraHeight,receiver[2]},receiver);
}
inline Pose referencePose(const V3& receiver) {
    // A cache-only prepare invocation at the receiver's actual world origin.
    // Look below it rather than normalizing a zero camera-to-receiver vector.
    return pose(receiver,{receiver[0],receiver[1]-1.0,receiver[2]});
}
inline M4 projection() {
    const float f=float(1.0/std::tan(55.0*pi/360.0)),near=0.1f,far=1024;
    return {f,0,0,0, 0,f,0,0, 0,0,-(far+near)/(far-near),-1, 0,0,-2*far*near/(far-near),0};
}
inline M4 inverseProjection(const M4& p) {
    return {1/p[0],0,0,0, 0,1/p[5],0,0, 0,0,0,1/p[14], 0,0,-1,p[10]/p[14]};
}
// Half an ULP in the queried storage format, including subnormal spacing.
// An exact power of two uses its larger adjacent spacing conservatively.
inline double storageRoundoff(GLenum format,double value) {
    if(!std::isfinite(value)) throw std::runtime_error("DEBUG-solar-cloud nonfinite value in quantization bound");
    const int precision=format==GL_RGBA16F?11:format==GL_RGBA32F?24:0;
    if(!precision) throw std::runtime_error("DEBUG-solar-cloud unsupported FP storage format");
    int exponent=0;std::frexp(std::abs(value),&exponent);
    const double minimum=std::ldexp(1.0,format==GL_RGBA16F?-24:-149);
    const double spacing=value==0?minimum:std::max(minimum,std::ldexp(1.0,exponent-precision));
    return 0.5*spacing;
}
inline double arithmeticBound(double beamScale) {
    // gamma_256 under the binary32 round-to-nearest arithmetic model covers
    // the short matrix/normal/lighting chain. This is a declared conservative
    // numerical allowance, not a formal accuracy guarantee for every driver's
    // transcendental intrinsics. White albedo and exact zenith remove pow and
    // angular sensitivity from the intended source-response comparison.
    constexpr double unit=0.5*double(std::numeric_limits<float>::epsilon());
    return (256*unit/(1-256*unit))*beamScale;
}
inline double lightmapInterpolationAllowance() {
    // Declared gamma_8 allowance at unit scale under binary32 round-to-nearest:
    // gamma_n=n*u/(1-n*u), u=epsilon/2. This is approximately four ULPs at 1,
    // not a driver-independent theorem about every rasterizer implementation.
    // It admits constant-one varying interpolation's observed one-ULP error,
    // while rejecting meaningful changes to this fixed skylight input.
    constexpr double unit=0.5*double(std::numeric_limits<float>::epsilon());
    return 8*unit/(1-8*unit);
}
inline void textFile(const std::filesystem::path& path,const std::string& text) {
    std::ofstream output(path);output<<text;
    if(!output) throw std::runtime_error("Cannot save solar-cloud evidence "+path.string());
}
inline void rawFile(const std::filesystem::path& path,const std::vector<float>& values) {
    std::ofstream output(path,std::ios::binary);
    output.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()*sizeof(float)));
    if(!output) throw std::runtime_error("Cannot save solar-cloud raw evidence "+path.string());
}
inline double maxDifference(const std::vector<float>& a,const std::vector<float>& b) {
    if(a.size()!=b.size()) throw std::runtime_error("DEBUG-solar-cloud unequal capture sizes");
    double result=0;for(size_t i=0;i<a.size();++i) result=std::max(result,std::abs(double(a[i])-b[i]));return result;
}
inline void finite(const std::vector<float>& data) {
    for(float value:data) if(!std::isfinite(value)) throw std::runtime_error("DEBUG-solar-cloud nonfinite GPU output");
}
struct ExtraProgram {GLuint id=0;~ExtraProgram(){if(id)glDeleteProgram(id);}};
struct ExtraAttachment {
    GLuint texture=0,framebuffer=0;
    ExtraAttachment(){glGenTextures(1,&texture);glGenFramebuffers(1,&framebuffer);}
    ExtraAttachment(const ExtraAttachment&)=delete;
    ExtraAttachment& operator=(const ExtraAttachment&)=delete;
    ~ExtraAttachment(){if(framebuffer)glDeleteFramebuffers(1,&framebuffer);if(texture)glDeleteTextures(1,&texture);}
};
struct InputReadbackState {
    std::array<GLint,6> samplers={};
    std::array<GLint,3> clamps={};
    const std::array<GLenum,3> clampTargets={GL_CLAMP_READ_COLOR,GL_CLAMP_FRAGMENT_COLOR,GL_CLAMP_VERTEX_COLOR};
    InputReadbackState() {
        // Sampler objects override a texture's filtering/compare parameters.
        // Do not inherit an unrelated sampler or an HDR-clamping readback.
        for(GLuint unit=0;unit<samplers.size();++unit) {glGetIntegeri_v(GL_SAMPLER_BINDING,unit,&samplers[unit]);glBindSampler(unit,0);}
        for(size_t i=0;i<clamps.size();++i) {glGetIntegerv(clampTargets[i],&clamps[i]);glClampColor(clampTargets[i],GL_FALSE);}
    }
    ~InputReadbackState() {
        for(GLuint unit=0;unit<samplers.size();++unit) glBindSampler(unit,GLuint(samplers[unit]));
        for(size_t i=0;i<clamps.size();++i) glClampColor(clampTargets[i],GLenum(clamps[i]));
    }
};
struct Cache {V4 cloudy,clear;};
struct CloudInterval {double nominal=0,lower=0,upper=0;};
inline CloudInterval cloudInterval(const Cache& cache,int channel,GLenum cloudyFormat,GLenum clearFormat) {
    const double cloud=cache.cloudy[channel],clear=cache.clear[channel];
    const double cloudError=storageRoundoff(cloudyFormat,cloud)+arithmeticBound(cloud);
    const double clearError=storageRoundoff(clearFormat,clear)+arithmeticBound(clear);
    if(!(clear>clearError)||!(cloud>cloudError)||cloud>clear+cloudError+clearError||clear>1+clearError)
        throw std::runtime_error("INCONCLUSIVE solar-cloud source: invalid positive cloudy/clear cache ratio");
    // Each half-float producer cache is an independently quantized value.
    // Do not cancel its uncertainty merely because C6/C7 share clear air.
    const CloudInterval result={cloud/clear,std::max(0.0,(cloud-cloudError)/(clear+clearError)),
        std::min(1.0,(cloud+cloudError)/(clear-clearError))};
    if(!std::isfinite(result.nominal)||result.lower>result.upper)
        throw std::runtime_error("INCONCLUSIVE solar-cloud source: empty/nonfinite physical cloud-ratio interval");
    return result;
}
struct Capture {std::array<std::vector<float>,5> outputs;};
} // namespace aqualumenSolarCloudDetail

// Public invariant: identical world receiver + static world cloud/Sun field
// gives identical direct-Sun C5, irrespective of observer position. The two
// cameras are symmetric around the receiver under zenith Sun; even the current
// local spherical-cloud tangent approximation has equal receiver-ray heights.
// One fixed-size point supplies the exact receiver through the original VS/FS;
// this checks receiver shading, not interpolated broad-terrain rasterization.
// This is NOT exact cloud optical-depth, full cloud/atmosphere transport, water
// shading, Iris allocation/runtime, morphology or temporal visual acceptance.
// Fixed P/Q prepare references supply positive receiver-local absolute source
// controls; dropping all clouds cannot pass their resolved attenuation/contrast.
// The original deferred main must copy actual C5 to immutable C8. These are
// procedural model consistency checks, not an exact cloud-depth oracle.
// Auto-selection examines ONLY actual prepare C6/C7 cache inputs, BEFORE any
// terrain program is compiled/drawn. Freeze the saved positive separation and
// nonnegative phase on GREEN. Existing artifact directories are never replaced.
inline void productionSolarCloudObserverInvariantProbe(const std::filesystem::path& root,
    const std::filesystem::path& artifacts="build/solar-cloud-observer",
    float frozenHalfSeparation=-1.0f,float frozenPhase=-1.0f) {
    using namespace aqualumenSolarCloudDetail;
    using aqualumenSolarProbeDetail::declaredFormat;
    using aqualumenSolarProbeDetail::formatName;
    const bool frozen=frozenHalfSeparation!=-1.0f||frozenPhase!=-1.0f;
    if(frozen&&(!std::isfinite(frozenHalfSeparation)||frozenHalfSeparation<1||frozenHalfSeparation>128
        ||!std::isfinite(frozenPhase)||frozenPhase<0||frozenPhase>120))
        throw std::runtime_error("Solar-cloud frozen pair requires half-separation [1,128] and phase [0,120]");
    const auto* rendererBytes=glGetString(GL_RENDERER);const auto* versionBytes=glGetString(GL_VERSION);
    const std::string renderer=rendererBytes?reinterpret_cast<const char*>(rendererBytes):"";
    if(renderer.find("NVIDIA")==std::string::npos)
        throw std::runtime_error("Solar-cloud production observer probe requires actual NVIDIA GL");
    GLint major=0,minor=0,profile=0,draws=0,attachments=0,units=0;
    glGetIntegerv(GL_MAJOR_VERSION,&major);glGetIntegerv(GL_MINOR_VERSION,&minor);glGetIntegerv(GL_CONTEXT_PROFILE_MASK,&profile);
    glGetIntegerv(GL_MAX_DRAW_BUFFERS,&draws);glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&units);
    if(major<3||(major==3&&minor<3)||!(profile&GL_CONTEXT_COMPATIBILITY_PROFILE_BIT)||draws<5||attachments<5||units<6)
        throw std::runtime_error("Solar-cloud probe requires GL3.3 compatibility, five MRTs and six fragment units");
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud probe entered with a GL error");
    if(std::filesystem::exists(artifacts)) throw std::runtime_error("Preserve solar-cloud artifacts; choose a NEW directory");
    std::filesystem::create_directories(artifacts);
    const std::string prepareVertex=expand(root/"prepare.vsh",root,0),prepareFragment=expand(root/"prepare.fsh",root,0);
    const std::string terrainVertex=expand(root/"gbuffers_terrain.vsh",root,0),terrainFragment=expand(root/"gbuffers_terrain.fsh",root,0);
    const std::string deferredVertex=expand(root/"deferred.vsh",root,0),deferredFragment=expand(root/"deferred.fsh",root,0);
    const auto solar=aqualumenSolarProbeDetail::declaredSolar(prepareFragment);
    const std::array<GLenum,4> formats={declaredFormat(prepareFragment,6),declaredFormat(prepareFragment,7),
        declaredFormat(prepareFragment,0),declaredFormat(prepareFragment,5)};
    const GLenum snapshotColorFormat=declaredFormat(prepareFragment,4),snapshotSunFormat=declaredFormat(prepareFragment,8);
    if(snapshotColorFormat!=GL_RGBA32F)
        throw std::runtime_error("Solar-cloud fixture auxiliary reuse requires the declared C4 RGBA32F storage");
    for(const auto& entry:std::array<std::pair<std::string,std::string>,6>{{
        {"production-prepare.vsh",prepareVertex},{"production-prepare.fsh",prepareFragment},
        {"production-terrain.vsh",terrainVertex},{"production-terrain.fsh",terrainFragment},
        {"production-deferred.vsh",deferredVertex},{"production-deferred.fsh",deferredFragment}}}) textFile(artifacts/entry.first,entry.second);
    InputReadbackState inputReadbackState;
    aqualumenSolarProbeDetail::Fixture fixture;
    // Compatibility pixel-transfer scales/biases affect GL_FLOAT readbacks.
    // Fixture's GL_ALL_ATTRIB_BITS snapshot restores these after any RED.
    for(GLenum parameter:{GL_RED_SCALE,GL_GREEN_SCALE,GL_BLUE_SCALE,GL_ALPHA_SCALE,GL_DEPTH_SCALE}) glPixelTransferf(parameter,1);
    for(GLenum parameter:{GL_RED_BIAS,GL_GREEN_BIAS,GL_BLUE_BIAS,GL_ALPHA_BIAS,GL_DEPTH_BIAS}) glPixelTransferf(parameter,0);
    glPixelTransferi(GL_MAP_COLOR,GL_FALSE);
    fixture.programs[0]=link(prepareVertex,prepareFragment,"DEBUG-solar-cloud-production-prepare",nullptr);
    const auto& textures=fixture.textures;
    const float white[4]={1,1,1,1},shadow=1;
    std::ofstream storage(artifacts/"storage.csv");storage<<"texture,internalFormat,width,height\n";
    for(int index=0;index<10;++index) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[index]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        const int width=index<2?1:index<4?lutWidth:receiverSize,height=index<2?1:index<4?lutHeight:receiverSize;
        const GLenum format=index==1||index==9?GL_DEPTH_COMPONENT32F:index==2?formats[0]:index==3?formats[1]:index==4?formats[2]:index==5?formats[3]:index>=6?GL_RGBA32F:GL_RGBA16F;
        glTexImage2D(GL_TEXTURE_2D,0,GLint(format),width,height,0,index==1||index==9?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,index==0?white:index==1?&shadow:nullptr);
        if(index==1) {glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);}
        GLint queried=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&queried);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        if(GLenum(queried)!=format||w!=width||h!=height) throw std::runtime_error("Solar-cloud actual storage differs from declared fixture allocation");
        storage<<index<<","<<queried<<","<<w<<","<<h<<"\n";
        std::cout<<"DEBUG-solar-cloud storage texture="<<index<<" format="<<queried<<" size="<<w<<"x"<<h<<"\n";
    }
    const GLenum outputBuffers[5]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2,GL_COLOR_ATTACHMENT3,GL_COLOR_ATTACHMENT4};
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]);
    for(int i=0;i<2;++i) glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[i],GL_TEXTURE_2D,textures[2+i],0);
    glDrawBuffers(2,outputBuffers);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Solar-cloud prepare FBO incomplete");
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[1]);
    for(int i=0;i<5;++i) glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[i],GL_TEXTURE_2D,textures[4+i],0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,textures[9],0);glDrawBuffers(5,outputBuffers);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Solar-cloud terrain FBO incomplete");
    for(GLenum cap:{GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,
        GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE,
        GL_POINT_SMOOTH,GL_PROGRAM_POINT_SIZE,GL_POINT_SPRITE}) glDisable(cap);
    // Normalize compatibility point state, all preserved by the fixture's
    // GL_ALL_ATTRIB_BITS scope. Do not inherit distance attenuation or a size
    // clamp that turns the intended one-pixel receiver into a larger sprite.
    const GLfloat pointAttenuation[3]={1,0,0};
    glPointParameterfv(GL_POINT_DISTANCE_ATTENUATION,pointAttenuation);
    glPointParameterf(GL_POINT_SIZE_MIN,1);glPointParameterf(GL_POINT_SIZE_MAX,1);
    glPointSize(1);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
    for(int unit=0;unit<2;++unit) {glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glLoadIdentity();}
    const M4 project=projection(),inverseProject=inverseProjection(project);
    const auto uniforms=[&](GLuint program,const Pose& p,float phase,bool prepare) {
        glUseProgram(program);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,p.view.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,p.inverse.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,project.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProject.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,p.shadowView.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,p.shadowProjection.data());
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),float(p.camera[0]),float(p.camera[1]),float(p.camera[2]));
        glUniform3f(glGetUniformLocation(program,"sunPosition"),float(p.viewSun[0]),float(p.viewSun[1]),float(p.viewSun[2]));
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),float(p.viewSun[0]),float(p.viewSun[1]),float(p.viewSun[2]));
        glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),phase);
        for(const char* name:{"rainStrength","wetness"}) glUniform1f(glGetUniformLocation(program,name),0);
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);
        glUniform1i(glGetUniformLocation(program,"worldTime"),6000);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),float(prepare?lutWidth:receiverSize));
        glUniform1f(glGetUniformLocation(program,"viewHeight"),float(prepare?lutHeight:receiverSize));glUniform1f(glGetUniformLocation(program,"far"),1024);
        glUniform1i(glGetUniformLocation(program,"gtexture"),0);glUniform1i(glGetUniformLocation(program,"colortex6"),1);
        glUniform1i(glGetUniformLocation(program,"colortex7"),2);glUniform1i(glGetUniformLocation(program,"shadowtex0"),3);
    };
    const auto read=[&](GLenum attachment,int width,int height) {
        std::vector<float> values(size_t(width)*height*4);glReadBuffer(attachment);
        glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,values.data());finite(values);return values;
    };
    const auto drawPrepare=[&](const Pose& p,float phase,const std::string& prefix) {
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]);glDrawBuffers(2,outputBuffers);
        glViewport(0,0,lutWidth,lutHeight);glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisable(GL_SCISSOR_TEST);
        const float zero[4]={0,0,0,0};for(int i=0;i<2;++i) glClearBufferfv(GL_COLOR,i,zero);
        for(int unit=0;unit<6;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,0);}
        uniforms(fixture.programs[0],p,phase,true);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        // Actual prepare main, at its genuine reserved-cache coordinates. The
        // full viewport/quad preserves derivatives; scissor restricts stored
        // writes to the cache. Helper lanes may still execute other branches.
        glEnable(GL_SCISSOR_TEST);glScissor(0,lutHeight-1,1,1);
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);
        glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();glDisable(GL_SCISSOR_TEST);
        const auto cloudy=read(outputBuffers[0],lutWidth,lutHeight),clear=read(outputBuffers[1],lutWidth,lutHeight);
        Cache result;const int pixel=(lutHeight-1)*lutWidth*4;
        for(int c=0;c<4;++c) {result.cloudy[c]=cloudy[pixel+c];result.clear[c]=clear[pixel+c];}
        if(!prefix.empty()) {rawFile(artifacts/(prefix+"-C6.rgba32f"),cloudy);rawFile(artifacts/(prefix+"-C7.rgba32f"),clear);}
        if(result.cloudy[3]!=1||result.clear[3]!=1) throw std::runtime_error("Solar-cloud production cache texel must have alpha1");
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud prepare GL error");
        return result;
    };
    std::ofstream qualification(artifacts/"cache-qualification.csv");
    qualification<<std::setprecision(12)<<"phase,halfSeparation,endpoint,channel,cloudCache,clearCache,cloudRatio,positiveSourceGap,qualificationBound,selected\n";
    std::array<Cache,2> caches;float halfSeparation=0,phase=0;bool found=false;
    const auto qualify=[&](float distance,float time) {
        const std::array<Cache,2> current={drawPrepare(pose(-distance),time,""),drawPrepare(pose(distance),time,"")};
        bool positive=true,distinct=false;double gap=0,bound=0;
        for(int c=0;c<3;++c) {
            for(int endpoint=0;endpoint<2;++endpoint) {
                const double cloud=current[endpoint].cloudy[c],clear=current[endpoint].clear[c];
                positive=positive&&cloud>storageRoundoff(formats[0],cloud)&&clear>storageRoundoff(formats[1],clear)
                    &&clear<=1+storageRoundoff(formats[1],clear)&&cloud<=clear+storageRoundoff(formats[0],cloud)+storageRoundoff(formats[1],clear);
            }
            if(current[0].clear[c]!=current[1].clear[c]) positive=false;
            const double sourceGap=solar[c]/pi*(std::abs(double(current[0].cloudy[c])-current[1].cloudy[c])
                -storageRoundoff(formats[0],current[0].cloudy[c])-storageRoundoff(formats[0],current[1].cloudy[c]));
            const double fullBeam=solar[c]/pi;
            const double uncertainty=2*storageRoundoff(formats[3],fullBeam)+arithmeticBound(fullBeam);
            distinct=distinct||sourceGap>4*uncertainty;gap=std::max(gap,sourceGap);bound=std::max(bound,4*uncertainty);
        }
        const bool selected=positive&&distinct;
        for(int endpoint=0;endpoint<2;++endpoint) for(int c=0;c<3;++c)
            qualification<<time<<","<<distance<<","<<endpoint<<","<<c<<","<<current[endpoint].cloudy[c]<<","<<current[endpoint].clear[c]
                <<","<<(current[endpoint].clear[c]>0?current[endpoint].cloudy[c]/current[endpoint].clear[c]:0)<<","<<gap<<","<<bound<<","<<selected<<"\n";
        if(selected) {halfSeparation=distance;phase=time;caches=current;found=true;}return selected;
    };
    if(frozen) qualify(frozenHalfSeparation,frozenPhase);
    else for(float time:{0.0f,24.0f,60.0f,120.0f}) {
        for(float distance:{8.0f,16.0f,32.0f,64.0f,96.0f,128.0f}) if(qualify(distance,time)) break;
        if(found) break;
    }
    qualification.flush();
    if(!qualification) throw std::runtime_error("Cannot save solar-cloud input qualification evidence");
    if(!found) throw std::runtime_error("INCONCLUSIVE solar-cloud fixture: no qualified distinct positive observer cloud-cache inputs; no C5 evaluated");
    // Fixed field points, not a search over successful terrain output. P may
    // be clear; Q must show resolved attenuation and a distinct local source.
    // Qualify both solely through original prepare before ANY terrain draw.
    const std::array<V3,2> receivers={receiverWorld,V3{-64,receiverHeight,0}};
    std::array<Cache,2> referenceCaches;
    std::array<std::array<CloudInterval,3>,2> referenceCloud;
    std::ofstream fieldQualification(artifacts/"receiver-source-qualification.csv");
    fieldQualification<<std::setprecision(12)<<"receiver,worldX,worldY,worldZ,channel,referenceC6,referenceC7,cloudFactor,cloudLower,cloudUpper,observerClearC7,expectedC5,expectedClearC5,resolvedSourceGap,qualificationBound\n";
    bool attenuatedQ=false,spatiallyDistinct=false;
    for(int receiver=0;receiver<2;++receiver) {
        referenceCaches[receiver]=drawPrepare(referencePose(receivers[receiver]),phase,"receiver"+std::to_string(receiver)+"-reference");
        for(int c=0;c<3;++c) referenceCloud[receiver][c]=cloudInterval(referenceCaches[receiver],c,formats[0],formats[1]);
    }
    for(int c=0;c<3;++c) {
        if(referenceCaches[0].clear[c]!=referenceCaches[1].clear[c])
            throw std::runtime_error("INCONCLUSIVE solar-cloud source: equal-height receiver references do not share clear atmosphere");
        const double observerClear=caches[0].clear[c],observerClearError=storageRoundoff(formats[1],observerClear);
        const double beam=solar[c]/pi,clearBeam=beam*observerClear;
        const double sourceGap=beam*std::max(0.0,observerClear-observerClearError)*std::max({0.0,
            referenceCloud[0][c].lower-referenceCloud[1][c].upper,
            referenceCloud[1][c].lower-referenceCloud[0][c].upper});
        const double bound=4*(2*storageRoundoff(formats[3],clearBeam)+arithmeticBound(beam));
        spatiallyDistinct=spatiallyDistinct||sourceGap>bound;
        attenuatedQ=attenuatedQ||beam*std::max(0.0,observerClear-observerClearError)*(1-referenceCloud[1][c].upper)>bound;
        for(int receiver=0;receiver<2;++receiver) {
            const auto& r=receivers[receiver];const auto& column=referenceCloud[receiver][c];
            fieldQualification<<receiver<<","<<r[0]<<","<<r[1]<<","<<r[2]<<","<<c<<","<<referenceCaches[receiver].cloudy[c]
                <<","<<referenceCaches[receiver].clear[c]<<","<<column.nominal<<","<<column.lower<<","<<column.upper
                <<","<<observerClear<<","<<clearBeam*column.nominal<<","<<clearBeam<<","<<sourceGap<<","<<bound<<"\n";
        }
    }
    fieldQualification.flush();
    if(!fieldQualification) throw std::runtime_error("Cannot save solar-cloud fixed-field source qualification");
    if(!spatiallyDistinct||!attenuatedQ)
        throw std::runtime_error("INCONCLUSIVE solar-cloud fixed P/Q: receiver prepare sources lack resolved contrast or positive Q attenuation; no C5 evaluated");
    // Only now compile/draw the real terrain main. Selection cannot depend on
    // its direct-Sun output or on a deliberately chosen failing response.
    fixture.programs[1]=link(terrainVertex,terrainFragment,"DEBUG-solar-cloud-production-terrain","mc_Entity");
    std::string observation=terrainFragment;
    const std::string anchor="    gl_FragData[1]=vec4(sunRadiance,1.0);";
    const auto at=observation.find(anchor);
    if(at==std::string::npos||observation.find(anchor,at+anchor.size())!=std::string::npos)
        throw std::runtime_error("Solar-cloud passive terrain observation STORE seam changed");
    observation.insert(at+anchor.size(),"\n    gl_FragData[2]=vec4(worldPosition+cameraPosition,1.0);\n    gl_FragData[3]=vec4(normal,lightmap.y);\n    gl_FragData[4]=vec4(albedo,lightmap.x);");
    textFile(artifacts/"observation-terrain.fsh",observation);ExtraProgram observer;
    observer.id=link(terrainVertex,observation,"DEBUG-solar-cloud-passive-terrain","mc_Entity");
    fixture.material=glGetAttribLocation(fixture.programs[1],"mc_Entity");
    if(fixture.material>=0) {
        glGetVertexAttribiv(GLuint(fixture.material),GL_VERTEX_ATTRIB_ARRAY_ENABLED,&fixture.materialEnabled);
        glGetVertexAttribfv(GLuint(fixture.material),GL_CURRENT_VERTEX_ATTRIB,fixture.materialValue.data());
        glDisableVertexAttribArray(GLuint(fixture.material));glVertexAttrib4f(GLuint(fixture.material),1,0,0,0);
    }
    const auto drawTerrain=[&](GLuint program,const Pose& p,const V3& receiver) {
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[1]);glDrawBuffers(5,outputBuffers);glViewport(0,0,receiverSize,receiverSize);
        glDisable(GL_SCISSOR_TEST);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_TRUE);glClearDepth(1);
        const float zero[4]={0,0,0,0};for(int i=0;i<5;++i) glClearBufferfv(GL_COLOR,i,zero);glClear(GL_DEPTH_BUFFER_BIT);
        // The unchanged production main defines only its two MRT outputs.
        // Never read undefined auxiliary outputs as if they were observations.
        const bool observing=program==observer.id;
        glDrawBuffers(observing?5:2,outputBuffers);
        for(int unit=0;unit<6;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,unit==0?textures[0]:unit==1?textures[2]:unit==2?textures[3]:unit==3?textures[1]:0);}
        uniforms(program,p,phase,false);glMatrixMode(GL_MODELVIEW);glLoadMatrixf(p.view.data());glMatrixMode(GL_PROJECTION);glLoadMatrixf(project.data());
        glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE0,0.5f,0.5f);glMultiTexCoord2f(GL_TEXTURE1,0,1);
        // A single exact world receiver avoids the huge clipped quad's
        // barycentric interpolation error. C5 uses no screen derivatives;
        // its albedo and scene-shadow textures are constant 1x1 inputs.
        glBegin(GL_POINTS);
        glVertex3f(float(receiver[0]-p.camera[0]),float(receiver[1]-p.camera[1]),float(receiver[2]-p.camera[2]));
        glEnd();
        Capture result;
        for(int i=0;i<5;++i) result.outputs[i]=observing||i<2?read(outputBuffers[i],receiverSize,receiverSize)
            :std::vector<float>(size_t(receiverSize)*receiverSize*4,0);
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud terrain GL error");
        return result;
    };
    // Separate actual-declared outputs avoid sampling the same texture that
    // deferred writes. Reuse only the already-read passive 32F attachments for
    // C0/C4; the Sun snapshot gets its own queried declared-format attachment.
    if(formats[2]!=GL_RGBA32F)
        throw std::runtime_error("Solar-cloud fixture auxiliary reuse requires the declared C0 RGBA32F storage");
    ExtraProgram deferred;deferred.id=link(deferredVertex,deferredFragment,"DEBUG-solar-cloud-production-deferred",nullptr);
    ExtraAttachment snapshot;
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,snapshot.texture);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D,0,GLint(snapshotSunFormat),receiverSize,receiverSize,0,GL_RGBA,GL_FLOAT,nullptr);
    GLint snapshotFormat=0,snapshotWidth=0,snapshotHeight=0;
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&snapshotFormat);
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&snapshotWidth);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&snapshotHeight);
    if(GLenum(snapshotFormat)!=snapshotSunFormat||snapshotWidth!=receiverSize||snapshotHeight!=receiverSize)
        throw std::runtime_error("Solar-cloud deferred C8 actual allocation differs from declared format/size");
    storage<<"deferredC8,"<<snapshotFormat<<","<<snapshotWidth<<","<<snapshotHeight<<"\n";
    glBindFramebuffer(GL_FRAMEBUFFER,snapshot.framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[0],GL_TEXTURE_2D,textures[6],0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[1],GL_TEXTURE_2D,textures[7],0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[2],GL_TEXTURE_2D,snapshot.texture,0);glDrawBuffers(3,outputBuffers);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Solar-cloud deferred FBO incomplete");
    const auto drawDeferred=[&](const Pose& p,const std::string& prefix,const Capture& terrain) {
        glBindFramebuffer(GL_FRAMEBUFFER,snapshot.framebuffer);glDrawBuffers(3,outputBuffers);glViewport(0,0,receiverSize,receiverSize);
        glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisable(GL_SCISSOR_TEST);
        const float zero[4]={0,0,0,0};for(int i=0;i<3;++i) glClearBufferfv(GL_COLOR,i,zero);
        for(int unit=0;unit<6;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,
            unit==0?textures[4]:unit==1?textures[2]:unit==2?textures[5]:unit==3?textures[9]:0);}
        uniforms(deferred.id,p,phase,false);
        glUniform1i(glGetUniformLocation(deferred.id,"colortex0"),0);glUniform1i(glGetUniformLocation(deferred.id,"colortex6"),1);
        glUniform1i(glGetUniformLocation(deferred.id,"colortex5"),2);glUniform1i(glGetUniformLocation(deferred.id,"depthtex1"),3);
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);
        glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);glEnd();
        std::array<std::vector<float>,3> copied;
        for(int i=0;i<3;++i) {copied[i]=read(outputBuffers[i],receiverSize,receiverSize);
            rawFile(artifacts/(prefix+"-deferred-C"+std::to_string(i==0?0:i==1?4:8)+".rgba32f"),copied[i]);}
        const int pixel=(receiverSize/2)*receiverSize+receiverSize/2;
        for(int c=0;c<4;++c) {
            if(copied[0][pixel*4+c]!=terrain.outputs[0][pixel*4+c]||copied[1][pixel*4+c]!=terrain.outputs[0][pixel*4+c])
                throw std::runtime_error("Production deferred changed the opaque receiver C0/C4 copy");
            const double original=terrain.outputs[1][pixel*4+c],copy=copied[2][pixel*4+c];
            if(std::abs(original-copy)>storageRoundoff(formats[3],original)+storageRoundoff(snapshotSunFormat,copy))
                throw std::runtime_error("Production deferred did not retain positive opaque direct-Sun C5 in C8");
        }
        for(int p=0;p<receiverSize*receiverSize;++p) if(p!=pixel)
            for(int c=0;c<3;++c) if(copied[2][p*4+c]!=0)
                throw std::runtime_error("Production deferred invented direct-Sun C8 on a cleared sky pixel");
        // Simulate a later C5 overwrite without running deferred again. The
        // retained C8 must remain the actual original program's copied value.
        const float laterSun[4]={19,11,7,1};
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[1]);glDrawBuffers(2,outputBuffers);
        glClearBufferfv(GL_COLOR,1,laterSun);
        const auto overwritten=read(outputBuffers[1],receiverSize,receiverSize);
        rawFile(artifacts/(prefix+"-later-C5-overwrite.rgba32f"),overwritten);
        for(int c=0;c<4;++c) if(overwritten[pixel*4+c]!=laterSun[c])
            throw std::runtime_error("Solar-cloud C8 retention control did not actually overwrite C5");
        if(overwritten[pixel*4]==copied[2][pixel*4]&&overwritten[pixel*4+1]==copied[2][pixel*4+1]
            &&overwritten[pixel*4+2]==copied[2][pixel*4+2])
            throw std::runtime_error("Solar-cloud C8 retention control lacks a distinct positive C5 overwrite");
        glBindFramebuffer(GL_FRAMEBUFFER,snapshot.framebuffer);
        const auto retained=read(outputBuffers[2],receiverSize,receiverSize);
        rawFile(artifacts/(prefix+"-deferred-C8-after-C5-overwrite.rgba32f"),retained);
        if(maxDifference(copied[2],retained)!=0)
            throw std::runtime_error("Production deferred C8 snapshot changed after a later C5 overwrite");
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud deferred GL error");
        return copied[2];
    };
    std::ostringstream manifest;manifest<<std::setprecision(12)
        <<"DEBUG-solar-cloud fixed-field source consistency + observer invariance + original deferred C8, NOT exact optical-depth/visual/Iris acceptance\nRenderer="<<renderer
        <<"\nGL="<<(versionBytes?reinterpret_cast<const char*>(versionBytes):"unknown")
        <<"\nFrozen halfSeparation="<<halfSeparation<<" phase="<<phase
        <<"\nFixed P=(0,"<<receiverHeight<<",0), Q=(-64,"<<receiverHeight<<",0), cameras=(receiverX+-halfSeparation,"<<cameraHeight<<",receiverZ), worldSun=(0,1,0), rain=0, wetness=0, whiteAlbedo, lightmap=(0,1), AO=1, fullyLitWorldShadow\n"
        <<"Terrain receiver: original VS/FS, one GL_POINTS vertex at receiverWorld-camera, fixed size1 at the center of17x17; smoothing/program point size/sprites off, attenuation=(1,0,0), min/max size1. Receiver shading only, NOT broad-terrain raster appearance.\n"
        <<"Actual prepare cache-only scissor at (0,"<<lutHeight-1<<") of "<<lutWidth<<"x"<<lutHeight<<" full viewport/quad; sky rows cleared, no sky radiance stored; helper invocations may execute outside scissor.\n"
        <<"C6="<<formatName(formats[0])<<" C7="<<formatName(formats[1])<<" C0="<<formatName(formats[2])<<" C5="<<formatName(formats[3])
        <<" C4="<<formatName(snapshotColorFormat)<<" C8="<<formatName(snapshotSunFormat)<<"; all formats queried. Raw rgba32f files are GL_FLOAT readbacks, not claims of32F storage.\n"
        <<"Sampler objects unbound; compatibility pixel-transfer scales/biases/map and color clamps neutralized; caller states restored by RAII.\n"
        <<"Quantization allowance=sum half-ULP actual C5 storage + gamma256(binary32)*SOLAR/pi; no image-aesthetic tolerance. Expanded unchanged sources retained for external SHA256.\n"
        <<"Fixed skylight input interpolation allowance=gamma8(binary32)="<<lightmapInterpolationAllowance()<<" at unit scale; world-position/normal/albedo/Sun guards unchanged.\n"
        <<"Fixed P/Q references: original prepare camera at actual receiver position Y63, shader altitude clamp2; ratio=referenceC6/referenceC7. Expected C5=(SOLAR/pi)*actual observerC7 at Y127 (altitude64)*receiver ratio. Both cache numerator/denominator half-ULPs and declared binary32 allowances widen an outward ratio interval; observer clear half-ULP and C5 storage are also bounded.\n"
        <<"References qualified from prepare before terrain: positive channels, fixed P/Q resolved contrast, and nontrivial Q attenuation. No terrain-output-driven receiver/phase search. This preserves the existing observer clear-air altitude approximation and tangent-column/weather model; it is NOT an independent exact-density/physical-depth oracle.\n"
        <<"Each observer prepare cache is regenerated and checked immediately before terrain, so reference cache writes cannot replace the actual observer input.\n"
        <<"Original deferred fullscreen VS/FS copies original terrain C0/C5/depth into distinct C0/C4/C8 targets. C8 must retain positive opaque C5, zero sky RGB, and remain unchanged after later C5 clear to (19,11,7,1) without rerunning deferred. No analytic C8 substitute.\n";
    textFile(artifacts/"fixture.txt",manifest.str());
    std::cout<<"DEBUG-solar-cloud selected input-only halfSeparation="<<halfSeparation<<" phase="<<phase<<" renderer="<<renderer<<"\n";
    std::ofstream matrices(artifacts/"matrices.csv"),evidence(artifacts/"receiver.csv");
    matrices<<std::setprecision(12)<<"receiver,endpoint,matrix,index,value\n";
    evidence<<std::setprecision(12)<<"receiver,endpoint,channel,worldReceiver,normal,albedo,worldSun,cloudCache,clearCache,C0,C5,observerC0Error,observerC5Error,repeatError,referenceCloudFactor,expectedC5,expectedLower,expectedUpper,absoluteResponseBound,absoluteResponsePass,C8\n";
    const int pixel=(receiverSize/2)*receiverSize+receiverSize/2;
    std::array<std::array<V4,2>,2> direct;
    std::array<std::array<Cache,2>,2> observerCaches;
    std::array<std::array<std::array<double,3>,2>,2> responseBounds;
    bool failed=false;
    for(int receiver=0;receiver<2;++receiver) for(int endpoint=0;endpoint<2;++endpoint) {
        const V3& receiverPosition=receivers[receiver];
        const Pose p=pose(endpoint?halfSeparation:-halfSeparation,receiverPosition);
        const std::string prefix=(receiver?"receiver1-":"")+std::string("endpoint")+std::to_string(endpoint);
        const Cache repeatedCache=drawPrepare(p,phase,prefix),repeatCache=drawPrepare(p,phase,"");
        if(repeatedCache.cloudy!=repeatCache.cloudy||repeatedCache.clear!=repeatCache.clear
            ||(!receiver&&(repeatedCache.cloudy!=caches[endpoint].cloudy||repeatedCache.clear!=caches[endpoint].clear)))
            throw std::runtime_error("Solar-cloud selected prepare inputs are not deterministic");
        observerCaches[receiver][endpoint]=repeatedCache;
        for(int c=0;c<3;++c) {
            cloudInterval(repeatedCache,c,formats[0],formats[1]);
            if(repeatedCache.clear[c]!=caches[0].clear[c])
                throw std::runtime_error("INCONCLUSIVE solar-cloud observer: equal-height clear cache changed across fixed P/Q eyes");
        }
        const auto ordinary=drawTerrain(fixture.programs[1],p,receiverPosition),repeat=drawTerrain(fixture.programs[1],p,receiverPosition),
            observed=drawTerrain(observer.id,p,receiverPosition);
        for(int i=0;i<5;++i) rawFile(artifacts/(prefix+(i==0?"-C0":i==1?"-C5":"-state"+std::to_string(i))+".rgba32f"),observed.outputs[i]);
        rawFile(artifacts/(prefix+"-production-C0.rgba32f"),ordinary.outputs[0]);rawFile(artifacts/(prefix+"-production-C5.rgba32f"),ordinary.outputs[1]);
        rawFile(artifacts/(prefix+"-repeat-C0.rgba32f"),repeat.outputs[0]);rawFile(artifacts/(prefix+"-repeat-C5.rgba32f"),repeat.outputs[1]);
        const double repeatError=std::max(maxDifference(ordinary.outputs[0],repeat.outputs[0]),maxDifference(ordinary.outputs[1],repeat.outputs[1]));
        if(repeatError!=0) throw std::runtime_error("Solar-cloud actual production receiver output is not deterministic");
        if(ordinary.outputs[0][pixel*4+3]!=1||ordinary.outputs[1][pixel*4+3]!=1||observed.outputs[2][pixel*4+3]!=1)
            throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: missing fixed-world target coverage");
        // Read back and redraw the unchanged production program for deferred,
        // never use the passive observer's C5 as its source.
        const auto deferredSource=drawTerrain(fixture.programs[1],p,receiverPosition);
        if(maxDifference(ordinary.outputs[0],deferredSource.outputs[0])!=0||maxDifference(ordinary.outputs[1],deferredSource.outputs[1])!=0)
            throw std::runtime_error("Solar-cloud original terrain changed before deferred copy");
        const auto copiedSun=drawDeferred(p,prefix,deferredSource);
        std::array<double,3> worldSun={};for(int row=0;row<3;++row) for(int col=0;col<3;++col) worldSun[row]+=p.inverse[col*4+row]*p.viewSun[col];worldSun=normalized(worldSun);
        for(int c=0;c<3;++c) {
            const double coordinateAllowance=16*double(std::numeric_limits<float>::epsilon())*std::max({1.0,double(halfSeparation),std::abs(receiverPosition[c])});
            if(std::abs(observed.outputs[2][pixel*4+c]-receiverPosition[c])>coordinateAllowance
                ||std::abs(observed.outputs[3][pixel*4+c]-(c==1?1.0:0.0))>16*double(std::numeric_limits<float>::epsilon())
                ||observed.outputs[4][pixel*4+c]!=1||std::abs(worldSun[c]-(c==1?1.0:0.0))>16*double(std::numeric_limits<float>::epsilon()))
                throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: world position/normal/albedo/Sun inputs changed");
            direct[receiver][endpoint][c]=ordinary.outputs[1][pixel*4+c];
            if(!(direct[receiver][endpoint][c]>storageRoundoff(formats[3],direct[receiver][endpoint][c])))
                throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: no positive direct-Sun output");
            const double clear=repeatedCache.clear[c],clearError=storageRoundoff(formats[1],clear),beam=solar[c]/pi;
            const auto& source=referenceCloud[receiver][c];
            const double expected=beam*clear*source.nominal;
            const double lower=beam*std::max(0.0,clear-clearError)*source.lower,upper=beam*(clear+clearError)*source.upper;
            const double outputError=storageRoundoff(formats[3],direct[receiver][endpoint][c])+arithmeticBound(beam);
            const double responseBound=std::max(expected-lower,upper-expected)+outputError;
            responseBounds[receiver][endpoint][c]=responseBound;
            const bool pass=direct[receiver][endpoint][c]>=lower-outputError&&direct[receiver][endpoint][c]<=upper+outputError;
            failed=failed||!pass;
            evidence<<receiver<<","<<endpoint<<","<<c<<","<<observed.outputs[2][pixel*4+c]<<","<<observed.outputs[3][pixel*4+c]<<","<<observed.outputs[4][pixel*4+c]
                <<","<<worldSun[c]<<","<<repeatedCache.cloudy[c]<<","<<clear<<","<<ordinary.outputs[0][pixel*4+c]<<","<<direct[receiver][endpoint][c]
                <<","<<maxDifference(ordinary.outputs[0],observed.outputs[0])<<","<<maxDifference(ordinary.outputs[1],observed.outputs[1])<<","<<repeatError
                <<","<<source.nominal<<","<<expected<<","<<lower<<","<<upper<<","<<responseBound<<","<<pass<<","<<copiedSun[pixel*4+c]<<"\n";
            std::cout<<"DEBUG-solar-cloud receiver="<<receiver<<" endpoint="<<endpoint<<" channel="<<c<<" expectedC5="<<expected
                <<" actualC5="<<direct[receiver][endpoint][c]<<" responseBound="<<responseBound<<" absolutePass="<<pass<<"\n";
        }
        if(std::abs(double(observed.outputs[3][pixel*4+3])-1)>lightmapInterpolationAllowance()||observed.outputs[4][pixel*4+3]!=0)
            throw std::runtime_error("Solar-cloud fixed lightmap input was not retained");
        for(int attachment=0;attachment<2;++attachment) for(size_t i=0;i<ordinary.outputs[attachment].size();++i) {
            const double value=ordinary.outputs[attachment][i],observedValue=observed.outputs[attachment][i];
            if(std::abs(value-observedValue)>storageRoundoff(attachment?formats[3]:formats[2],value)
                +storageRoundoff(attachment?formats[3]:formats[2],observedValue)+arithmeticBound(solar[i%4==3?0:i%4]/pi))
                throw std::runtime_error("Solar-cloud passive MRT changes actual production C0/C5");
        }
        for(const auto& item:std::array<std::pair<const char*,M4>,6>{{{"view",p.view},{"inverse",p.inverse},{"projection",project},{"inverseProjection",inverseProject},{"shadowView",p.shadowView},{"shadowProjection",p.shadowProjection}}})
            for(int i=0;i<16;++i) matrices<<receiver<<","<<endpoint<<","<<item.first<<","<<i<<","<<item.second[i]<<"\n";
        const double observationError=std::max(maxDifference(ordinary.outputs[0],observed.outputs[0]),maxDifference(ordinary.outputs[1],observed.outputs[1]));
        std::cout<<"DEBUG-solar-cloud receiver="<<receiver<<" endpoint="<<endpoint<<" C5=("<<direct[receiver][endpoint][0]<<","<<direct[receiver][endpoint][1]<<","<<direct[receiver][endpoint][2]
            <<") observationError="<<observationError<<" repeatError="<<repeatError<<" originalDeferredC8=retained\n";
    }
    std::ofstream result(artifacts/"invariance.csv"),contrast(artifacts/"receiver-source-response.csv");
    result<<std::setprecision(12)<<"receiver,channel,C5A,C5B,absoluteDifference,quantizationArithmeticBound,predictedCameraCacheRatio,observedC5Ratio,pass\n";
    contrast<<std::setprecision(12)<<"endpoint,channel,expectedPQDifference,actualPQDifference,absoluteDifferenceError,responseBound,nonzeroResponse,pass\n";
    bool positiveFieldResponse=false;
    for(int receiver=0;receiver<2;++receiver) for(int c=0;c<3;++c) {
        const double difference=std::abs(double(direct[receiver][0][c])-direct[receiver][1][c]);
        const double bound=storageRoundoff(formats[3],direct[receiver][0][c])+storageRoundoff(formats[3],direct[receiver][1][c])+arithmeticBound(solar[c]/pi);
        const bool pass=difference<=bound;failed=failed||!pass;
        const double cacheRatio=observerCaches[receiver][1].cloudy[c]/observerCaches[receiver][0].cloudy[c];
        result<<receiver<<","<<c<<","<<direct[receiver][0][c]<<","<<direct[receiver][1][c]<<","<<difference<<","<<bound<<","<<cacheRatio
            <<","<<double(direct[receiver][1][c])/direct[receiver][0][c]<<","<<pass<<"\n";
        std::cout<<std::setprecision(12)<<"DEBUG-solar-cloud receiver="<<receiver<<" channel="<<c<<" fixed-world C5 difference="<<difference<<" format/FP bound="<<bound
            <<" camera-cache ratio="<<cacheRatio<<" C5 ratio="<<double(direct[receiver][1][c])/direct[receiver][0][c]<<"\n";
    }
    for(int endpoint=0;endpoint<2;++endpoint) for(int c=0;c<3;++c) {
        const double expected=solar[c]/pi*caches[0].clear[c]*(referenceCloud[0][c].nominal-referenceCloud[1][c].nominal);
        const double actual=double(direct[0][endpoint][c])-direct[1][endpoint][c];
        const double bound=responseBounds[0][endpoint][c]+responseBounds[1][endpoint][c];
        const bool nonzero=std::abs(actual)>bound,pass=std::abs(actual-expected)<=bound;
        positiveFieldResponse=positiveFieldResponse||nonzero;failed=failed||!pass;
        contrast<<endpoint<<","<<c<<","<<expected<<","<<actual<<","<<std::abs(actual-expected)<<","<<bound<<","<<nonzero<<","<<pass<<"\n";
    }
    failed=failed||!positiveFieldResponse;
    matrices.flush();evidence.flush();storage.flush();result.flush();contrast.flush();
    if(!matrices||!evidence||!storage||!result||!contrast) throw std::runtime_error("Cannot save solar-cloud evidence tables");
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud probe final GL error");
    if(failed) throw std::runtime_error("Production receiver Sun must follow qualified local cloud source, remain observer-invariant and preserve a nonzero P/Q response");
    std::cout<<"PASS GPU production prepare/terrain/deferred: bounded fixed P/Q local-cloud absolute source, positive spatial attenuation, observer invariance and immutable C8; NOT exact optical-depth, broad-terrain raster, water or real-view acceptance\n";
}

#endif
