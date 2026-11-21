#ifndef AQUALUMEN_SOLAR_RADIOMETRY_PROBE_H
#define AQUALUMEN_SOLAR_RADIOMETRY_PROBE_H

// One pending production-main regression, not a recorded GPU RED or a fix.
// Include in glcheck.cpp after link(), then call only after its caller owns the
// NVIDIA compatibility-context/GPU slot. No context or shader is substituted.
#include <epoxy/gl.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// Existing glcheck helpers; all arguments are explicit, so no default-argument
// declarations are needed here. This also permits CPU-only syntax checking.
std::string expand(const std::filesystem::path&, const std::filesystem::path&, int);
GLuint link(const std::string&, const std::string&, const std::string&, const char*);

namespace aqualumenSolarProbeDetail {
using Vec3 = std::array<double, 3>;
constexpr double pi = 3.1415926535897932384626433832795;

inline double dot(const Vec3& a, const Vec3& b) {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return {a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]};
}
inline Vec3 normalized(Vec3 a) {
    const double length = std::sqrt(dot(a, a));
    if (!(length > 0) || !std::isfinite(length))
        throw std::runtime_error("Solar coherence fixture has an invalid CPU ray");
    for (double& value : a) value /= length;
    return a;
}
inline double triangleSolidAngle(const Vec3& a, const Vec3& b, const Vec3& c) {
    return 2.0*std::atan2(std::abs(dot(a, cross(b, c))), 1.0+dot(a,b)+dot(b,c)+dot(c,a));
}
inline double quadSolidAngle(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d) {
    return triangleSolidAngle(a,b,c)+triangleSolidAngle(a,c,d);
}

// Independent double-precision reconstruction from the exact float matrices
// supplied to production viewPosition()/inverse-view, not copied GLSL helpers.
inline Vec3 worldRay(double u, double v, const std::array<float,16>& inverseProjection,
                     const std::array<float,16>& inverseView) {
    const std::array<double,4> clip = {u*2-1, v*2-1, 1, 1};
    std::array<double,4> view = {};
    for (int row=0; row<4; ++row)
        for (int col=0; col<4; ++col) view[row] += inverseProjection[col*4+row]*clip[col];
    if (!(view[3] > 0) || !std::isfinite(view[3]))
        throw std::runtime_error("Solar coherence fixture has an invalid projection division");
    Vec3 world = {};
    for (int row=0; row<3; ++row)
        for (int col=0; col<3; ++col) world[row] += inverseView[col*4+row]*view[col]/view[3];
    return normalized(world);
}

inline GLenum declaredFormat(const std::string& prepare, int target) {
    const std::regex declaration("const\\s+int\\s+colortex"+std::to_string(target)+
                                 "Format\\s*=\\s*(RGBA16F|RGBA32F)\\s*;");
    const std::sregex_iterator begin(prepare.begin(),prepare.end(),declaration), end;
    if (begin==end)
        throw std::runtime_error("Solar probe requires a literal RGBA16F/RGBA32F declaration for C"+std::to_string(target));
    const std::string format=(*begin)[1];
    auto next=begin;
    if (++next!=end) throw std::runtime_error("Ambiguous solar probe format declaration for C"+std::to_string(target));
    return format=="RGBA16F" ? GL_RGBA16F : GL_RGBA32F;
}
inline const char* formatName(GLenum format) { return format==GL_RGBA16F ? "RGBA16F" : "RGBA32F"; }

// Read the producer's public incident-light scale, never replace SOLAR in a
// shader or reproduce sunDisk(). Reject nonliteral/ambiguous fixture inputs.
inline Vec3 declaredSolar(const std::string& prepare) {
    const std::string number="([+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?)";
    const std::regex declaration("const\\s+vec3\\s+SOLAR\\s*=\\s*vec3\\s*\\(\\s*"+number+
                                 "\\s*,\\s*"+number+"\\s*,\\s*"+number+"\\s*\\)\\s*;");
    const std::sregex_iterator begin(prepare.begin(),prepare.end(),declaration), end;
    if (begin==end) throw std::runtime_error("Solar probe requires the actual literal vec3 SOLAR incident-light scale");
    auto next=begin;
    if (++next!=end) throw std::runtime_error("Ambiguous SOLAR incident-light scale in expanded prepare");
    Vec3 solar={};
    for (int c=0; c<3; ++c) {
        solar[c]=std::stod((*begin)[c+1]);
        if (!(solar[c]>0) || !std::isfinite(solar[c]))
            throw std::runtime_error("Invalid positive SOLAR incident-light scale");
    }
    return solar;
}

// Expected RED must clean up just as GREEN does. Preserve caller state and do
// not leave sampled output aliases, programs, matrices or pixel-buffer state.
struct Fixture {
    std::array<GLuint,2> programs = {};
    std::array<GLuint,10> textures = {};
    std::array<GLuint,2> framebuffers = {};
    GLint previousProgram=0, previousDrawFbo=0, previousReadFbo=0;
    GLint previousActiveTexture=0, previousMatrixMode=0, previousPackBuffer=0, previousUnpackBuffer=0;
    std::array<GLfloat,16> modelView = {}, projection = {};
    std::array<std::array<GLfloat,16>,2> textureMatrices = {};
    std::array<GLint,6> textureBindings = {};
    GLint material=-1, materialEnabled=0;
    std::array<GLfloat,4> materialValue = {};

    Fixture() {
        glGetIntegerv(GL_CURRENT_PROGRAM,&previousProgram);
        glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&previousDrawFbo);
        glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&previousReadFbo);
        glGetIntegerv(GL_ACTIVE_TEXTURE,&previousActiveTexture);
        glGetIntegerv(GL_MATRIX_MODE,&previousMatrixMode);
        glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&previousPackBuffer);
        glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&previousUnpackBuffer);
        glGetFloatv(GL_MODELVIEW_MATRIX,modelView.data());
        glGetFloatv(GL_PROJECTION_MATRIX,projection.data());
        glPushAttrib(GL_ALL_ATTRIB_BITS);
        glPushClientAttrib(GL_CLIENT_PIXEL_STORE_BIT);
        for (int unit=0; unit<6; ++unit) {
            glActiveTexture(GL_TEXTURE0+unit);
            glGetIntegerv(GL_TEXTURE_BINDING_2D,&textureBindings[unit]);
            if (unit<2) glGetFloatv(GL_TEXTURE_MATRIX,textureMatrices[unit].data());
        }
        glBindBuffer(GL_PIXEL_PACK_BUFFER,0);
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
        glPixelStorei(GL_PACK_ALIGNMENT,1);
        glPixelStorei(GL_UNPACK_ALIGNMENT,1);
        for (GLenum parameter : {GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS,
                                 GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS})
            glPixelStorei(parameter,0);
        glPixelStorei(GL_PACK_SWAP_BYTES,GL_FALSE);
        glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
        glGenTextures(static_cast<GLsizei>(textures.size()),textures.data());
        glGenFramebuffers(static_cast<GLsizei>(framebuffers.size()),framebuffers.data());
    }
    Fixture(const Fixture&)=delete;
    Fixture& operator=(const Fixture&)=delete;
    ~Fixture() {
        glUseProgram(static_cast<GLuint>(previousProgram));
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER,static_cast<GLuint>(previousDrawFbo));
        glBindFramebuffer(GL_READ_FRAMEBUFFER,static_cast<GLuint>(previousReadFbo));
        if (material>=0) {
            glVertexAttrib4fv(static_cast<GLuint>(material),materialValue.data());
            if (materialEnabled) glEnableVertexAttribArray(static_cast<GLuint>(material));
            else glDisableVertexAttribArray(static_cast<GLuint>(material));
        }
        glMatrixMode(GL_MODELVIEW); glLoadMatrixf(modelView.data());
        glMatrixMode(GL_PROJECTION); glLoadMatrixf(projection.data());
        for (int unit=0; unit<6; ++unit) {
            glActiveTexture(GL_TEXTURE0+unit);
            glBindTexture(GL_TEXTURE_2D,static_cast<GLuint>(textureBindings[unit]));
            if (unit<2) { glMatrixMode(GL_TEXTURE); glLoadMatrixf(textureMatrices[unit].data()); }
        }
        for (GLuint program : programs) if (program) glDeleteProgram(program);
        glDeleteTextures(static_cast<GLsizei>(textures.size()),textures.data());
        glDeleteFramebuffers(static_cast<GLsizei>(framebuffers.size()),framebuffers.data());
        glPopClientAttrib();
        glPopAttrib();
        glBindBuffer(GL_PIXEL_PACK_BUFFER,static_cast<GLuint>(previousPackBuffer));
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER,static_cast<GLuint>(previousUnpackBuffer));
        glActiveTexture(static_cast<GLenum>(previousActiveTexture));
        glMatrixMode(static_cast<GLenum>(previousMatrixMode));
    }
};
} // namespace aqualumenSolarProbeDetail

// Public behavior: Sun radiance integrated over its visible angular support
// delivers the same perpendicular irradiance as real terrain's direct Sun.
// Preconditions: caller-owned current NVIDIA GL >=3.3 compatibility context,
// >=3 color attachments/draw buffers, >=6 fragment texture units; root is the
// shaders/ directory. All outputs are private FBOs: default surface may be 1x1.
inline void productionSolarBeamCoherenceProbe(const std::filesystem::path& root) {
    using namespace aqualumenSolarProbeDetail;
    const GLubyte* rendererBytes=glGetString(GL_RENDERER);
    const std::string renderer=rendererBytes ? reinterpret_cast<const char*>(rendererBytes) : "";
    if (renderer.find("NVIDIA")==std::string::npos)
        throw std::runtime_error("Production solar coherence requires the caller-owned real NVIDIA GL context");
    GLint major=0, minor=0, profile=0, drawBuffers=0, attachments=0, fragmentUnits=0, maxTextureSize=0;
    glGetIntegerv(GL_MAJOR_VERSION,&major); glGetIntegerv(GL_MINOR_VERSION,&minor);
    glGetIntegerv(GL_CONTEXT_PROFILE_MASK,&profile);
    glGetIntegerv(GL_MAX_DRAW_BUFFERS,&drawBuffers);
    glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);
    glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&fragmentUnits);
    glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxTextureSize);
    if (major<3 || (major==3 && minor<3) || !(profile&GL_CONTEXT_COMPATIBILITY_PROFILE_BIT) ||
        drawBuffers<3 || attachments<3 || fragmentUnits<6 || maxTextureSize<1024)
        throw std::runtime_error("Solar coherence requires GL 3.3 compatibility, 3 MRTs, 6 fragment texture units and 1024-pixel textures");
    if (glGetError()!=GL_NO_ERROR)
        throw std::runtime_error("Solar coherence entered with a GL error; do not interpret fixture errors as a radiometric RED");

    constexpr int terrainSize=8, size=512, skyWidth=1024, skyHeight=512;
    const std::array<float,16> identity={1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    const std::array<float,16> downView={1,0,0,0, 0,0,1,0, 0,-1,0,0, 0,0,0,1};
    const std::array<float,16> downInverse={1,0,0,0, 0,0,-1,0, 0,1,0,0, 0,0,0,1};
    const std::array<float,16> upView=downInverse, upInverse=downView;
    const float focal=static_cast<float>(1.0/std::tan(pi/180.0)); // 2-degree vertical FOV
    constexpr float nearPlane=0.1f, farPlane=128.0f;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane);
    const float b=-2.0f*farPlane*nearPlane/(farPlane-nearPlane);
    const std::array<float,16> skyProjection={focal,0,0,0, 0,focal,0,0, 0,0,a,-1, 0,0,b,0};
    const std::array<float,16> skyInverse={1/focal,0,0,0, 0,1/focal,0,0, 0,0,0,1/b, 0,0,-1,a/b};
    const Vec3 sun={0,1,0};

    // Corner-ray spherical areas are independent of the production disk code.
    // Four subquads check convergence of the central-cosine quadrature; neither
    // calculation assumes equal pixel solid angles or copies a solar formula.
    std::vector<double> weights(size*size);
    double totalOmega=0, totalProjected=0, refinedProjected=0;
    const auto ray=[&](double x,double y) { return worldRay(x/size,y/size,skyInverse,upInverse); };
    for (int y=0; y<size; ++y) for (int x=0; x<size; ++x) {
        const double omega=quadSolidAngle(ray(x,y),ray(x+1,y),ray(x+1,y+1),ray(x,y+1));
        if (!(omega>0) || !std::isfinite(omega)) throw std::runtime_error("Invalid spherical pixel solid angle");
        weights[y*size+x]=omega*std::max(dot(ray(x+0.5,y+0.5),sun),0.0);
        totalOmega+=omega;
        totalProjected+=weights[y*size+x];
        for (int sy=0; sy<2; ++sy) for (int sx=0; sx<2; ++sx) {
            const double left=x+sx*0.5, bottom=y+sy*0.5;
            const double subOmega=quadSolidAngle(ray(left,bottom),ray(left+0.5,bottom),
                                                ray(left+0.5,bottom+0.5),ray(left,bottom+0.5));
            refinedProjected+=subOmega*std::max(dot(ray(left+0.25,bottom+0.25),sun),0.0);
        }
    }
    // The corner rays use the rounded float inverse matrix, not double 1/focal.
    // Compare the analytic rectangle to that same actual camera aperture.
    const double tangent=skyInverse[0];
    const double rectangleOmega=4.0*std::atan2(tangent*tangent,std::sqrt(1+2*tangent*tangent));
    if (std::abs(totalOmega/rectangleOmega-1)>1e-9 ||
        std::abs(totalProjected/refinedProjected-1)>1e-7)
        throw std::runtime_error("Solar fixture solid-angle/cosine integration failed its independent convergence controls");

    const std::string prepare=expand(root/"prepare.fsh",root,0);
    const Vec3 sourceSolar=declaredSolar(prepare);
    const std::array<int,5> targets={0,4,5,8,6};
    std::array<GLenum,5> formats={};
    for (size_t i=0; i<targets.size(); ++i) formats[i]=declaredFormat(prepare,targets[i]);
    Fixture fixture;
    fixture.programs[0]=link(expand(root/"gbuffers_terrain.vsh",root,0),
                             expand(root/"gbuffers_terrain.fsh",root,0),"production-solar-terrain","mc_Entity");
    fixture.programs[1]=link(expand(root/"deferred.vsh",root,0),
                             expand(root/"deferred.fsh",root,0),"production-solar-deferred",nullptr);
    auto& textures=fixture.textures;
    const float white[4]={1,1,1,1}, depthOne=1;
    std::vector<float> blackSky(skyWidth*skyHeight*4,0);
    for (size_t i=3; i<blackSky.size(); i+=4) blackSky[i]=1;
    for (int i=0; i<10; ++i) {
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D,textures[i]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        const int width=i==0 || i==2 || i==9 ? 1 : i==1 ? skyWidth : i<6 ? terrainSize : size;
        const int height=i==1 ? skyHeight : width;
        if (i==2 || i==5 || i==9) {
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,width,height,0,GL_DEPTH_COMPONENT,GL_FLOAT,i==5 ? nullptr : &depthOne);
            if (i==2) {
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
            }
        } else {
            const GLenum format=i==1 ? formats[4] : i==3 || i==6 ? formats[0] : i==4 ? formats[2] : i==7 ? formats[1] : i==8 ? formats[3] : GL_RGBA16F;
            glTexImage2D(GL_TEXTURE_2D,0,static_cast<GLint>(format),width,height,0,GL_RGBA,GL_FLOAT,
                         i==0 ? white : i==1 ? blackSky.data() : nullptr);
            GLint actual=0, actualWidth=0, actualHeight=0;
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&actual);
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&actualWidth);
            glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&actualHeight);
            if (static_cast<GLenum>(actual)!=format || actualWidth!=width || actualHeight!=height)
                throw std::runtime_error("Solar fixture queried texture format/size differs from its allocation");
            if (i!=0) {
                const int target=i==1 ? 6 : i==3 || i==6 ? 0 : i==4 ? 5 : i==7 ? 4 : 8;
                std::cout<<"GPU solar allocation: "<<(i<6 ? "input/producer " : "deferred output ")
                         <<"C"<<target<<" "<<width<<"x"<<height<<" declared="<<formatName(format)
                         <<" queried="<<formatName(static_cast<GLenum>(actual))<<"\n";
            }
        }
    }
    const GLenum outputBuffers[3]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2};
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]);
    for (int i=0; i<2; ++i) glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[i],GL_TEXTURE_2D,textures[3+i],0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,textures[5],0);
    glDrawBuffers(2,outputBuffers);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Solar terrain MRT framebuffer incomplete");
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[1]);
    for (int i=0; i<3; ++i) glFramebufferTexture2D(GL_FRAMEBUFFER,outputBuffers[i],GL_TEXTURE_2D,textures[6+i],0);
    glDrawBuffers(3,outputBuffers);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Solar deferred MRT framebuffer incomplete");

    for (GLenum cap : {GL_BLEND,GL_CULL_FACE,GL_SCISSOR_TEST,GL_ALPHA_TEST,GL_STENCIL_TEST,
                       GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,
                       GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE}) glDisable(cap);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
    for (int unit=0; unit<2; ++unit) {
        glActiveTexture(GL_TEXTURE0+unit); glMatrixMode(GL_TEXTURE); glLoadIdentity();
    }
    fixture.material=glGetAttribLocation(fixture.programs[0],"mc_Entity");
    if (fixture.material>=0) {
        glGetVertexAttribiv(static_cast<GLuint>(fixture.material),GL_VERTEX_ATTRIB_ARRAY_ENABLED,&fixture.materialEnabled);
        glGetVertexAttribfv(static_cast<GLuint>(fixture.material),GL_CURRENT_VERTEX_ATTRIB,fixture.materialValue.data());
        glDisableVertexAttribArray(static_cast<GLuint>(fixture.material));
        glVertexAttrib4f(static_cast<GLuint>(fixture.material),1,0,0,0);
    }
    const auto commonUniforms=[&](GLuint program, bool sky) {
        glUseProgram(program);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,(sky ? upView : downView).data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,(sky ? upInverse : downInverse).data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,(sky ? skyProjection : identity).data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,(sky ? skyInverse : identity).data());
        for (const char* name : {"shadowProjection","shadowModelView"})
            glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity.data());
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,sky ? -1.0f : 1.0f);
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,0,sky ? -1.0f : 1.0f);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,65,0);
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);
        glUniform1i(glGetUniformLocation(program,"worldTime"),6000);
        glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
        for (const char* name : {"rainStrength","wetness","frameTimeCounter"}) glUniform1f(glGetUniformLocation(program,name),0);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),sky ? size : terrainSize);
        glUniform1f(glGetUniformLocation(program,"viewHeight"),sky ? size : terrainSize);
        glUniform1f(glGetUniformLocation(program,"far"),farPlane);
        glUniform1i(glGetUniformLocation(program,"colortex6"),1);
    };
    const auto bindInputs=[&](bool terrain, bool sky) {
        for (int unit=0; unit<6; ++unit) {
            glActiveTexture(GL_TEXTURE0+unit);
            glBindTexture(GL_TEXTURE_2D,terrain ? (unit<3 ? textures[unit] : 0) : textures[unit==5 && sky ? 9 : unit]);
        }
    };
    const float clearColor[4]={0,0,0,0};
    const auto clearOutputs=[&](int count) { for (int i=0; i<count; ++i) glClearBufferfv(GL_COLOR,i,clearColor); };
    const auto fullscreen=[]() {
        glMatrixMode(GL_MODELVIEW); glLoadIdentity();
        glMatrixMode(GL_PROJECTION); glLoadIdentity();
        glBegin(GL_QUADS);
        glTexCoord2f(0,0); glVertex2f(-1,-1); glTexCoord2f(1,0); glVertex2f(1,-1);
        glTexCoord2f(1,1); glVertex2f(1,1); glTexCoord2f(0,1); glVertex2f(-1,1);
        glEnd();
    };
    const auto read=[&](int attachment, int width) {
        std::vector<float> pixels(width*width*4);
        glReadBuffer(outputBuffers[attachment]);
        glReadPixels(0,0,width,width,GL_RGBA,GL_FLOAT,pixels.data());
        for (size_t i=0; i<pixels.size(); ++i)
            if (!std::isfinite(pixels[i]) || (i%4==3 && pixels[i]!=1))
                throw std::runtime_error("Solar coherence has nonfinite or unwritten MRT output");
        return pixels;
    };
    std::array<double,3> positiveBeam={}, positiveSky={};
    size_t illuminatedPixels=0;
    for (int source=0; source<2; ++source) { // zero control before the expected positive-source RED
        const float transmission=static_cast<float>(source);
        const float cache[4]={transmission,transmission,transmission,1};
        glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D,textures[1]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,skyHeight-1,1,1,GL_RGBA,GL_FLOAT,cache);
        bindInputs(true,false);
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]); glDrawBuffers(2,outputBuffers);
        glViewport(0,0,terrainSize,terrainSize); clearOutputs(2);
        glEnable(GL_DEPTH_TEST); glDepthMask(GL_TRUE); glDepthFunc(GL_LESS); glDepthRange(0,1);
        glClearBufferfv(GL_DEPTH,0,&depthOne);
        commonUniforms(fixture.programs[0],false);
        glUniform1i(glGetUniformLocation(fixture.programs[0],"gtexture"),0);
        glUniform1i(glGetUniformLocation(fixture.programs[0],"shadowtex0"),2);
        glMatrixMode(GL_PROJECTION); glLoadIdentity();
        glMatrixMode(GL_MODELVIEW); glLoadMatrixf(downView.data());
        glColor4f(1,1,1,1); glNormal3f(0,1,0);
        glMultiTexCoord2f(GL_TEXTURE0,0.5f,0.5f); glMultiTexCoord2f(GL_TEXTURE1,0,1);
        glBegin(GL_QUADS);
        glVertex3f(-1,-0.5f,-1); glVertex3f(1,-0.5f,-1);
        glVertex3f(1,-0.5f,1); glVertex3f(-1,-0.5f,1);
        glEnd();
        const auto terrainTotal=read(0,terrainSize), terrainSun=read(1,terrainSize);

        bindInputs(false,false);
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[1]); glDrawBuffers(3,outputBuffers);
        clearOutputs(3); glDisable(GL_DEPTH_TEST);
        commonUniforms(fixture.programs[1],false);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"colortex0"),3);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"colortex5"),4);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"depthtex1"),5);
        fullscreen();
        const auto opaqueMain=read(0,terrainSize), opaqueCopy=read(1,terrainSize), snapshot=read(2,terrainSize);
        for (size_t i=0; i<snapshot.size(); i+=4) for (int c=0; c<3; ++c) {
            if (opaqueMain[i+c]!=terrainTotal[i+c] || opaqueCopy[i+c]!=opaqueMain[i+c] || snapshot[i+c]!=terrainSun[i+c])
                throw std::runtime_error("Real deferred must preserve terrain C0/C4 and matching direct-Sun C5/C8");
            if (terrainSun[i+c]<0 || terrainSun[i+c]>terrainTotal[i+c] ||
                (source==0 && terrainSun[i+c]!=0) || (source==1 && !(terrainSun[i+c]>0)))
                throw std::runtime_error("Solar fixture failed its zero-cache/positive direct-source control");
            if (source==1) positiveBeam[c]+=pi*snapshot[i+c]/(terrainSize*terrainSize); // white albedo, n dot sun = 1
        }

        bindInputs(false,true);
        glViewport(0,0,size,size); clearOutputs(3);
        commonUniforms(fixture.programs[1],true);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"colortex0"),3);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"colortex5"),4);
        glUniform1i(glGetUniformLocation(fixture.programs[1],"depthtex1"),5);
        fullscreen();
        const auto skyMain=read(0,size), skyCopy=read(1,size), skySun=read(2,size);
        for (size_t i=0; i<weights.size(); ++i) {
            bool illuminated=false;
            for (int c=0; c<3; ++c) {
                const float value=skyMain[i*4+c];
                if (value<0 || skyCopy[i*4+c]!=value || skySun[i*4+c]!=0 || (source==0 && value!=0))
                    throw std::runtime_error("Real deferred sky must preserve C0=C4, omit receiver Sun C8, and vanish at zero cache");
                if (source==1) positiveSky[c]+=value*weights[i];
                illuminated=illuminated || value>0;
            }
            if (source==1 && illuminated) ++illuminatedPixels;
        }
        if (glGetError()!=GL_NO_ERROR) throw std::runtime_error("Solar coherence fixture GL error, not a valid radiometric result");
    }
    if (illuminatedPixels==0) throw std::runtime_error("Positive cache did not render a solar disk through the real deferred main");
    for (int c=0; c<3; ++c) {
        // T=1, n dot sun=1, full visibility/skylight, rain=0, white albedo.
        // 0.1% allows declared C5/C8 half-float quantization, not a missing
        // lighting factor. Do this before interpreting the unity comparison.
        if (!std::isfinite(positiveBeam[c]) || std::abs(positiveBeam[c]/sourceSolar[c]-1)>0.001) {
            std::ostringstream error;
            error<<"Solar fixture positive-beam calibration failed: channel "<<c<<", pi*C8="
                 <<std::setprecision(12)<<positiveBeam[c]<<", actual SOLAR="<<sourceSolar[c]<<", tolerance=0.1%";
            throw std::runtime_error(error.str());
        }
    }
    std::ostringstream result;
    result<<std::setprecision(12)<<"GPU production solar coherence: renderer="<<renderer
          <<"; sky="<<size<<"x"<<size<<", verticalFOV=2deg; T=1, rain=0, white Lambertian receiver; litPixels="
          <<illuminatedPixels<<"; rectangleOmega="<<totalOmega<<"; cosineRefinementRelative="
          <<std::abs(totalProjected/refinedProjected-1)<<"; actualSOLAR_RGB=(";
    for (int c=0; c<3; ++c) result<<(c ? "," : "")<<sourceSolar[c];
    result<<"); beamRGB=(";
    for (int c=0; c<3; ++c) result<<(c ? "," : "")<<positiveBeam[c];
    result<<"); integratedSkyRGB=(";
    for (int c=0; c<3; ++c) result<<(c ? "," : "")<<positiveSky[c];
    result<<"); sky/beamRGB=(";
    bool coherent=true;
    for (int c=0; c<3; ++c) {
        const double ratio=positiveSky[c]/positiveBeam[c];
        result<<(c ? "," : "")<<ratio;
        coherent=coherent && std::isfinite(ratio) && ratio>=0.98 && ratio<=1.02;
    }
    result<<"); unity acceptance=[0.98,1.02] per channel\n";
    std::cout<<result.str()<<std::flush;
    if (!coherent)
        throw std::runtime_error("FAIL production solar radiometry: integrated real deferred disk does not deliver real terrain beam irradiance within 2%");
    std::cout<<"PASS GPU production solar radiometry: terrain/deferred beam equals integrated sky disk; this is not an Iris visual/FPS acceptance\n";
}

#endif // AQUALUMEN_SOLAR_RADIOMETRY_PROBE_H
