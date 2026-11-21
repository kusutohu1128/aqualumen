#ifndef AQUALUMEN_SOLAR_CLOUD_PROBE_H
#define AQUALUMEN_SOLAR_CLOUD_PROBE_H

// Opt-in, one-behavior production prepare -> terrain-main tracer bullet.
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
inline Pose pose(double cameraX) {
    Pose result;result.camera={cameraX,cameraHeight,0};
    // Keep the same world receiver, but avoid the old 64m/2m grazing view.
    // Its raster interpolation error is not a reason to relax the receiver's
    // position guard. The two eyes now have the same 64m vertical separation.
    const V3 forward=normalized({receiverWorld[0]-result.camera[0],receiverWorld[1]-result.camera[1],receiverWorld[2]-result.camera[2]}),
        right=normalized(cross(forward,{0,1,0})),up=cross(right,forward);
    result.view={float(right[0]),float(up[0]),float(-forward[0]),0,
                 float(right[1]),float(up[1]),float(-forward[1]),0,
                 float(right[2]),float(up[2]),float(-forward[2]),0, 0,0,0,1};
    result.inverse=identity;
    for(int row=0;row<3;++row) for(int col=0;col<3;++col) result.inverse[col*4+row]=result.view[row*4+col];
    result.viewSun={result.view[4],result.view[5],result.view[6]};
    // A fixed world shadow projection around the receiver, with a fully-lit
    // depth-comparison texture. Moving the eye cannot move an occluder here.
    result.shadowView=identity;
    for(int c=0;c<3;++c) result.shadowView[12+c]=float(result.camera[c]-receiverWorld[c]);
    result.shadowProjection={0.001f,0,0,0, 0,0.001f,0,0, 0,0,0.001f,0, 0,0,0,1};
    return result;
}
inline M4 projection() {
    const float f=float(1.0/std::tan(55.0*pi/360.0)),near=0.1f,far=1024;
    return {f,0,0,0, 0,f,0,0, 0,0,-(far+near)/(far-near),-1, 0,0,-2*far*near/(far-near),0};
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
// Invariance alone cannot distinguish a correct local shadow field from a
// shader that drops cloud attenuation entirely. Before shipping a later fix,
// retain positive P/Q receiver-local absolute cloud/source controls and the
// immutable deferred C8 copy; this first slice intentionally does not invent
// an exact optical-depth oracle or claim those other behaviors accepted.
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
    const auto solar=aqualumenSolarProbeDetail::declaredSolar(prepareFragment);
    const std::array<GLenum,4> formats={declaredFormat(prepareFragment,6),declaredFormat(prepareFragment,7),
        declaredFormat(prepareFragment,0),declaredFormat(prepareFragment,5)};
    for(const auto& entry:std::array<std::pair<std::string,std::string>,4>{{
        {"production-prepare.vsh",prepareVertex},{"production-prepare.fsh",prepareFragment},
        {"production-terrain.vsh",terrainVertex},{"production-terrain.fsh",terrainFragment}}}) textFile(artifacts/entry.first,entry.second);
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
    const M4 project=projection();
    const auto uniforms=[&](GLuint program,const Pose& p,float phase,bool prepare) {
        glUseProgram(program);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,p.view.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,p.inverse.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,project.data());
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
    const auto drawTerrain=[&](GLuint program,const Pose& p) {
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
        glVertex3f(float(receiverWorld[0]-p.camera[0]),float(receiverWorld[1]-p.camera[1]),float(receiverWorld[2]-p.camera[2]));
        glEnd();
        Capture result;
        for(int i=0;i<5;++i) result.outputs[i]=observing||i<2?read(outputBuffers[i],receiverSize,receiverSize)
            :std::vector<float>(size_t(receiverSize)*receiverSize*4,0);
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud terrain GL error");
        return result;
    };
    std::ostringstream manifest;manifest<<std::setprecision(12)
        <<"DEBUG-solar-cloud observer-invariance, NOT exact optical-depth/visual/Iris acceptance\nRenderer="<<renderer
        <<"\nGL="<<(versionBytes?reinterpret_cast<const char*>(versionBytes):"unknown")
        <<"\nFrozen halfSeparation="<<halfSeparation<<" phase="<<phase
        <<"\nWorldReceiver=(0,"<<receiverHeight<<",0), cameras=(+-halfSeparation,"<<cameraHeight<<",0), worldSun=(0,1,0), rain=0, wetness=0, whiteAlbedo, lightmap=(0,1), AO=1, fullyLitWorldShadow\n"
        <<"Terrain receiver: original VS/FS, one GL_POINTS vertex at receiverWorld-camera, fixed size1 at the center of17x17; smoothing/program point size/sprites off, attenuation=(1,0,0), min/max size1. Receiver shading only, NOT broad-terrain raster appearance.\n"
        <<"Actual prepare cache-only scissor at (0,"<<lutHeight-1<<") of "<<lutWidth<<"x"<<lutHeight<<" full viewport/quad; sky rows cleared, no sky radiance stored; helper invocations may execute outside scissor.\n"
        <<"C6="<<formatName(formats[0])<<" C7="<<formatName(formats[1])<<" C0="<<formatName(formats[2])<<" C5="<<formatName(formats[3])
        <<"; all formats queried. Raw rgba32f files are GL_FLOAT readbacks, not claims of32F storage.\n"
        <<"Sampler objects unbound; compatibility pixel-transfer scales/biases/map and color clamps neutralized; caller states restored by RAII.\n"
        <<"Quantization allowance=sum half-ULP actual C5 storage + gamma256(binary32)*SOLAR/pi; no image-aesthetic tolerance. Expanded unchanged sources retained for external SHA256.\n"
        <<"Fixed skylight input interpolation allowance=gamma8(binary32)="<<lightmapInterpolationAllowance()<<" at unit scale; world-position/normal/albedo/Sun guards unchanged.\n"
        <<"This first invariant does not certify nontrivial local cloud attenuation: true later GREEN also requires independent positive P/Q absolute receiver-cloud/source controls and immutable deferred C8 retention before shipping.\n";
    textFile(artifacts/"fixture.txt",manifest.str());
    std::cout<<"DEBUG-solar-cloud selected input-only halfSeparation="<<halfSeparation<<" phase="<<phase<<" renderer="<<renderer<<"\n";
    std::ofstream matrices(artifacts/"matrices.csv"),evidence(artifacts/"receiver.csv");
    matrices<<std::setprecision(12)<<"endpoint,matrix,index,value\n";
    evidence<<std::setprecision(12)<<"endpoint,channel,worldReceiver,normal,albedo,worldSun,cloudCache,clearCache,C0,C5,observerC0Error,observerC5Error,repeatError\n";
    const int pixel=(receiverSize/2)*receiverSize+receiverSize/2;
    std::array<V4,2> direct;bool failed=false;
    for(int endpoint=0;endpoint<2;++endpoint) {
        const Pose p=pose(endpoint?halfSeparation:-halfSeparation);const std::string prefix="endpoint"+std::to_string(endpoint);
        const Cache repeatedCache=drawPrepare(p,phase,prefix);
        if(repeatedCache.cloudy!=caches[endpoint].cloudy||repeatedCache.clear!=caches[endpoint].clear)
            throw std::runtime_error("Solar-cloud selected prepare inputs are not deterministic");
        const auto ordinary=drawTerrain(fixture.programs[1],p),repeat=drawTerrain(fixture.programs[1],p),observed=drawTerrain(observer.id,p);
        for(int i=0;i<5;++i) rawFile(artifacts/(prefix+(i==0?"-C0":i==1?"-C5":"-state"+std::to_string(i))+".rgba32f"),observed.outputs[i]);
        rawFile(artifacts/(prefix+"-production-C0.rgba32f"),ordinary.outputs[0]);rawFile(artifacts/(prefix+"-production-C5.rgba32f"),ordinary.outputs[1]);
        rawFile(artifacts/(prefix+"-repeat-C0.rgba32f"),repeat.outputs[0]);rawFile(artifacts/(prefix+"-repeat-C5.rgba32f"),repeat.outputs[1]);
        const double repeatError=std::max(maxDifference(ordinary.outputs[0],repeat.outputs[0]),maxDifference(ordinary.outputs[1],repeat.outputs[1]));
        if(repeatError!=0) throw std::runtime_error("Solar-cloud actual production receiver output is not deterministic");
        if(ordinary.outputs[0][pixel*4+3]!=1||ordinary.outputs[1][pixel*4+3]!=1||observed.outputs[2][pixel*4+3]!=1)
            throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: missing fixed-world target coverage");
        std::array<double,3> worldSun={};for(int row=0;row<3;++row) for(int col=0;col<3;++col) worldSun[row]+=p.inverse[col*4+row]*p.viewSun[col];worldSun=normalized(worldSun);
        for(int c=0;c<3;++c) {
            const double coordinateAllowance=16*double(std::numeric_limits<float>::epsilon())*std::max({1.0,double(halfSeparation),std::abs(receiverWorld[c])});
            if(std::abs(observed.outputs[2][pixel*4+c]-receiverWorld[c])>coordinateAllowance
                ||std::abs(observed.outputs[3][pixel*4+c]-(c==1?1.0:0.0))>16*double(std::numeric_limits<float>::epsilon())
                ||observed.outputs[4][pixel*4+c]!=1||std::abs(worldSun[c]-(c==1?1.0:0.0))>16*double(std::numeric_limits<float>::epsilon()))
                throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: world position/normal/albedo/Sun inputs changed");
            direct[endpoint][c]=ordinary.outputs[1][pixel*4+c];
            if(!(direct[endpoint][c]>storageRoundoff(formats[3],direct[endpoint][c])))
                throw std::runtime_error("INCONCLUSIVE solar-cloud receiver: no positive direct-Sun output");
            evidence<<endpoint<<","<<c<<","<<observed.outputs[2][pixel*4+c]<<","<<observed.outputs[3][pixel*4+c]<<","<<observed.outputs[4][pixel*4+c]
                <<","<<worldSun[c]<<","<<caches[endpoint].cloudy[c]<<","<<caches[endpoint].clear[c]<<","<<ordinary.outputs[0][pixel*4+c]<<","<<direct[endpoint][c]
                <<","<<maxDifference(ordinary.outputs[0],observed.outputs[0])<<","<<maxDifference(ordinary.outputs[1],observed.outputs[1])<<","<<repeatError<<"\n";
        }
        if(std::abs(double(observed.outputs[3][pixel*4+3])-1)>lightmapInterpolationAllowance()||observed.outputs[4][pixel*4+3]!=0)
            throw std::runtime_error("Solar-cloud fixed lightmap input was not retained");
        for(int attachment=0;attachment<2;++attachment) for(size_t i=0;i<ordinary.outputs[attachment].size();++i) {
            const double value=ordinary.outputs[attachment][i],observedValue=observed.outputs[attachment][i];
            if(std::abs(value-observedValue)>storageRoundoff(attachment?formats[3]:formats[2],value)
                +storageRoundoff(attachment?formats[3]:formats[2],observedValue)+arithmeticBound(solar[i%4==3?0:i%4]/pi))
                throw std::runtime_error("Solar-cloud passive MRT changes actual production C0/C5");
        }
        for(const auto& item:std::array<std::pair<const char*,M4>,5>{{{"view",p.view},{"inverse",p.inverse},{"projection",project},{"shadowView",p.shadowView},{"shadowProjection",p.shadowProjection}}})
            for(int i=0;i<16;++i) matrices<<endpoint<<","<<item.first<<","<<i<<","<<item.second[i]<<"\n";
        const double observationError=std::max(maxDifference(ordinary.outputs[0],observed.outputs[0]),maxDifference(ordinary.outputs[1],observed.outputs[1]));
        std::cout<<"DEBUG-solar-cloud endpoint="<<endpoint<<" C5=("<<direct[endpoint][0]<<","<<direct[endpoint][1]<<","<<direct[endpoint][2]
            <<") observationError="<<observationError<<" repeatError="<<repeatError<<"\n";
    }
    std::ofstream result(artifacts/"invariance.csv");result<<std::setprecision(12)<<"channel,C5A,C5B,absoluteDifference,quantizationArithmeticBound,predictedCameraCacheRatio,observedC5Ratio,pass\n";
    for(int c=0;c<3;++c) {
        const double difference=std::abs(double(direct[0][c])-direct[1][c]);
        const double bound=storageRoundoff(formats[3],direct[0][c])+storageRoundoff(formats[3],direct[1][c])+arithmeticBound(solar[c]/pi);
        const bool pass=difference<=bound;failed=failed||!pass;
        result<<c<<","<<direct[0][c]<<","<<direct[1][c]<<","<<difference<<","<<bound<<","<<caches[1].cloudy[c]/caches[0].cloudy[c]
            <<","<<double(direct[1][c])/direct[0][c]<<","<<pass<<"\n";
        std::cout<<std::setprecision(12)<<"DEBUG-solar-cloud channel="<<c<<" fixed-world C5 difference="<<difference<<" format/FP bound="<<bound
            <<" camera-cache ratio="<<caches[1].cloudy[c]/caches[0].cloudy[c]<<" C5 ratio="<<double(direct[1][c])/direct[0][c]<<"\n";
    }
    matrices.flush();evidence.flush();storage.flush();result.flush();
    if(!matrices||!evidence||!storage||!result) throw std::runtime_error("Cannot save solar-cloud evidence tables");
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar-cloud probe final GL error");
    if(failed) throw std::runtime_error("Production fixed-world direct Sun must not track observer-position cloud transmission");
    std::cout<<"PASS GPU production prepare/terrain: bounded fixed-world direct-Sun observer invariance ONLY; NOT receiver-local spatial cloud/source, deferred C8, exact optical-depth or real-view acceptance\n";
}

#endif
