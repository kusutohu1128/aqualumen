#ifndef AQUALUMEN_WATER_OPTICAL_DEPTH_PROBE_H
#define AQUALUMEN_WATER_OPTICAL_DEPTH_PROBE_H

// Opt-in production-main tracer bullet. Include immediately before glcheck's
// main(), after expand/link/instrumentShoreCausal. Calling this requires the
// caller's exclusive NVIDIA GPU slot; preparing/including it does not run GL.
// No production algorithm, spectrum, marcher or bathymetry is reproduced here.
#include <epoxy/gl.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

std::string expand(const std::filesystem::path&,const std::filesystem::path&,int);
GLuint link(const std::string&,const std::string&,const std::string&,const char*);
std::string instrumentShoreCausal(const std::string&,bool);

namespace aqualumenWaterOpticalDepthDetail {
using V3=std::array<double,3>;
constexpr int size=129,skyWidth=64,skyHeight=32;
constexpr double pi=3.14159265358979323846,sourceIncrement=double(0.45f)-double(0.08f);
inline double dot(const V3& a,const V3& b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline V3 add(const V3& a,const V3& b,double scale=1) {return {a[0]+scale*b[0],a[1]+scale*b[1],a[2]+scale*b[2]};}
inline V3 normalized(V3 a) {
    const double length=std::sqrt(dot(a,a));
    if(!(length>0)||!std::isfinite(length)) throw std::runtime_error("DEBUG-water-optical-depth invalid CPU direction");
    for(double& value:a) value/=length;
    return a;
}
inline V3 reflected(const V3& incident,const V3& normal) {return add(incident,normal,-2*dot(incident,normal));}
// Independent unpolarized dielectric law, not a call/copy of a GLSL helper.
// Its normal comes from actual raster geometry, NOT the depth-dependent n.
inline double facetFresnel(double cosine) {
    constexpr double index=1.333;
    const double c=std::clamp(cosine,0.0,1.0),t=std::sqrt(1-(1-c*c)/(index*index));
    const double s=(c-index*t)/(c+index*t),p=(index*c-t)/(index*c+t);
    return (s*s+p*p)/2;
}
struct Box {V3 lo,hi;int id;};
struct Hit {
    bool valid=false,inside=false,tangent=false;
    int id=-1,axis=-1,side=0;
    double travel=0;
    V3 point={0,0,0};
};
// All retained fixture rays start outside its closed union. Inside/on-boundary
// origins are explicitly unresolved, not silently treated as a clear path.
inline Hit firstHit(const std::vector<Box>& boxes,const V3& origin,const V3& ray) {
    Hit result;double nearest=128;
    for(const Box& box:boxes) {
        double entry=-std::numeric_limits<double>::infinity(),exit=std::numeric_limits<double>::infinity();
        int axis=-1,side=0;bool miss=false,inside=true;
        for(int c=0;c<3;++c) {
            inside=inside&&origin[c]>=box.lo[c]&&origin[c]<=box.hi[c];
            if(std::abs(ray[c])<1e-12) {if(origin[c]<box.lo[c]||origin[c]>box.hi[c]) miss=true;continue;}
            double lo=(box.lo[c]-origin[c])/ray[c],hi=(box.hi[c]-origin[c])/ray[c];int nearSide=-1;
            if(lo>hi) {std::swap(lo,hi);nearSide=1;}
            if(lo>entry) {entry=lo;axis=c;side=nearSide;}
            exit=std::min(exit,hi);if(entry>exit) {miss=true;break;}
        }
        if(inside) {result.inside=true;return result;}
        if(!miss&&entry>1e-7&&entry<nearest&&exit>=entry) {
            nearest=entry;result.valid=true;result.id=box.id;result.axis=axis;result.side=side;
            result.travel=entry;result.tangent=exit-entry<1e-7;result.point=add(origin,ray,entry);
        }
    }
    return result;
}
inline bool cameraVisible(const std::vector<Box>& boxes,const Hit& hit) {
    if(!hit.valid||hit.inside||hit.tangent) return false;
    const Hit camera=firstHit(boxes,{0,0,0},normalized(hit.point));
    if(!camera.valid||camera.inside||camera.tangent||camera.id!=hit.id) return false;
    double error=0;for(int c=0;c<3;++c) error+=std::pow(camera.point[c]-hit.point[c],2);
    return std::sqrt(error)<1e-5;
}
struct Scene {
    std::vector<float> depth=std::vector<float>(size*size,1),colour=std::vector<float>(size*size*4,0);
    std::vector<int> id=std::vector<int>(size*size,-1);
    std::vector<V3> receiver=std::vector<V3>(size*size,{0,0,0});
};
inline Scene scene(const std::vector<Box>& boxes,bool tag,float f,float a,float b) {
    Scene result;
    for(int y=0;y<size;++y) for(int x=0;x<size;++x) {
        const int pixel=y*size+x,base=pixel*4;
        const V3 ray={(2.0*(x+0.5)/size-1)/f,(2.0*(y+0.5)/size-1)/f,-1};
        const Hit hit=firstHit(boxes,{0,0,0},ray);
        if(hit.inside) throw std::runtime_error("DEBUG-water-optical-depth camera lies inside fixture solid");
        result.colour[base+3]=1;
        for(int c=0;c<3;++c) result.colour[base+c]=hit.valid?(hit.id==2?0.08f:0.25f):0.04f;
        if(!hit.valid) continue;
        result.id[pixel]=hit.id;result.receiver[pixel]=hit.point;
        const float travel=float(hit.travel);
        result.depth[pixel]=0.5f*((a*(-travel)+b)/travel)+0.5f;
        if(tag&&hit.id==2) result.colour[base]=0.45f;
    }
    return result;
}
struct Capture {std::vector<float> colour;std::array<std::vector<float>,7> state;};
inline V3 value(const std::vector<float>& pixels,int pixel) {return {pixels[pixel*4],pixels[pixel*4+1],pixels[pixel*4+2]};}
inline double difference(const std::vector<float>& a,const std::vector<float>& b) {
    if(a.size()!=b.size()) throw std::runtime_error("DEBUG-water-optical-depth capture size mismatch");
    double error=0;for(size_t i=0;i<a.size();++i) error=std::max(error,std::abs(double(a[i])-b[i]));return error;
}
inline void save(const std::filesystem::path& path,const std::vector<float>& pixels) {
    std::ofstream output(path,std::ios::binary);
    output.write(reinterpret_cast<const char*>(pixels.data()),pixels.size()*sizeof(float));
    if(!output) throw std::runtime_error("Cannot save water optical-depth evidence "+path.string());
}
struct Fixture {
    std::array<GLuint,2> programs={};std::array<GLuint,16> textures={};GLuint framebuffer=0;
    GLint program=0,drawFbo=0,readFbo=0,active=0,matrixMode=0,packBuffer=0,unpackBuffer=0,materialEnabled=0;
    std::array<GLint,9> bindings={};std::array<GLfloat,4> materialValue={};
    Fixture() {
        glGetIntegerv(GL_CURRENT_PROGRAM,&program);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&drawFbo);
        glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&readFbo);glGetIntegerv(GL_ACTIVE_TEXTURE,&active);
        glGetIntegerv(GL_MATRIX_MODE,&matrixMode);glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&packBuffer);
        glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&unpackBuffer);
        glGetVertexAttribiv(10,GL_VERTEX_ATTRIB_ARRAY_ENABLED,&materialEnabled);glGetVertexAttribfv(10,GL_CURRENT_VERTEX_ATTRIB,materialValue.data());
        glPushAttrib(GL_ALL_ATTRIB_BITS);glPushClientAttrib(GL_CLIENT_PIXEL_STORE_BIT);
        for(int unit=0;unit<9;++unit) {glActiveTexture(GL_TEXTURE0+unit);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bindings[unit]);}
        glBindBuffer(GL_PIXEL_PACK_BUFFER,0);glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
        glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
        glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glMatrixMode(GL_PROJECTION);glPushMatrix();
        for(int unit=0;unit<2;++unit) {glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glPushMatrix();glLoadIdentity();}
        glGenTextures(GLsizei(textures.size()),textures.data());glGenFramebuffers(1,&framebuffer);
    }
    ~Fixture() {
        for(int unit=0;unit<2;++unit) {glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glPopMatrix();}
        glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glPopMatrix();
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER,drawFbo);glBindFramebuffer(GL_READ_FRAMEBUFFER,readFbo);
        glPopClientAttrib();glPopAttrib();
        glBindBuffer(GL_PIXEL_PACK_BUFFER,packBuffer);glBindBuffer(GL_PIXEL_UNPACK_BUFFER,unpackBuffer);
        for(int unit=0;unit<9;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,bindings[unit]);}
        glVertexAttrib4fv(10,materialValue.data());if(materialEnabled) glEnableVertexAttribArray(10);else glDisableVertexAttribArray(10);
        glUseProgram(program);glActiveTexture(active);glMatrixMode(matrixMode);
        for(GLuint id:programs) if(id) glDeleteProgram(id);
        glDeleteTextures(GLsizei(textures.size()),textures.data());glDeleteFramebuffers(1,&framebuffer);
    }
};
} // namespace aqualumenWaterOpticalDepthDetail

// fixedX/fixedY freeze a qualified first-run pixel for a subsequent GREEN; use
// its saved fixture.csv. Auto-selection is qualification-only, before judging
// gain invariance. Failure to obtain a source/geometry control is INCONCLUSIVE,
// not a fabricated RED or a passing regression. Artifacts never overwrite.
inline void productionWaterOpticalDepthProbe(const std::filesystem::path& root,
    const std::filesystem::path& artifacts="build/water-optical-depth",
    bool enforceInvariant=true,int fixedX=-1,int fixedY=-1,bool bathymetryEnabled=false,
    bool firstVisibleBedOnly=false,GLenum firstBedFilter=GL_NEAREST,
    bool firstVisibleBedWavesOnly=false) {
    using namespace aqualumenWaterOpticalDepthDetail;
    firstVisibleBedOnly=firstVisibleBedOnly||firstVisibleBedWavesOnly;
    bathymetryEnabled=bathymetryEnabled||firstVisibleBedOnly;
    if(firstVisibleBedOnly&&firstBedFilter!=GL_NEAREST&&firstBedFilter!=GL_LINEAR)
        throw std::runtime_error("First-visible-bed filter must be NEAREST or LINEAR");
    if(firstVisibleBedWavesOnly&&firstBedFilter!=GL_NEAREST)
        throw std::runtime_error("First-visible-bed waves slice qualifies NEAREST only");
    const auto* renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(!renderer||std::string(renderer).find("NVIDIA")==std::string::npos)
        throw std::runtime_error("Water optical-depth probe requires real NVIDIA GL");
    if((fixedX<0)!=(fixedY<0)||fixedX>=size||fixedY>=size||fixedX< -1||fixedY< -1)
        throw std::runtime_error("Invalid frozen optical-depth fixture pixel");
    if(std::filesystem::exists(artifacts)) throw std::runtime_error("Preserve previous optical-depth evidence; choose a new artifact directory");
    std::filesystem::create_directories(artifacts);
    const float f=float(1/std::tan(pi/6)),nearPlane=0.1f,farPlane=128;
    const float a=-(farPlane+nearPlane)/(farPlane-nearPlane),b=-2*farPlane*nearPlane/(farPlane-nearPlane);
    const float projection[16]={f,0,0,0,0,f,0,0,0,0,a,-1,0,0,b,0};
    const float inverseProjection[16]={1/f,0,0,0,0,1/f,0,0,0,0,0,1/b,0,0,-1,a/b};
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    std::string vertex=expand(root/"gbuffers_water.vsh",root,0);
    std::string fragment=expand(root/"gbuffers_water.fsh",root,0);
    const auto foam=fragment.find("#define SHORE_FOAM ");
    if(foam==std::string::npos) throw std::runtime_error("Public SHORE_FOAM option missing");
    fragment.replace(foam,fragment.find('\n',foam)-foam,"#define SHORE_FOAM 0.0");
    if(firstVisibleBedOnly) {
        // The waves extension retains one predeclared nonzero public setting.
        // The existing flat-interface test and default behavior stay unchanged.
        // The real vertex and fragment main bodies remain unchanged.
        for(std::string* source:{&vertex,&fragment}) {
            const std::string option="#define WAVE_HEIGHT ";
            const auto at=source->find(option);
            if(at==std::string::npos||source->find(option,at+option.size())!=std::string::npos)
                throw std::runtime_error("Public WAVE_HEIGHT option missing or ambiguous");
            source->replace(at,source->find('\n',at)-at,firstVisibleBedWavesOnly?"#define WAVE_HEIGHT 0.12":"#define WAVE_HEIGHT 0.0");
        }
    }
    std::string observationSource=instrumentShoreCausal(fragment,false);
    // Replace an observation STORE only, never the main body/trace calculation.
    // mode2 is a uniform branch. C0 comparison below checks compiler effects.
    const std::string old="        gl_FragData[3]=vec4(mat3(gbufferModelView)*reflected,receiverConfidence);";
    const auto seam=observationSource.find(old);
    if(seam==std::string::npos||observationSource.find(old,seam+old.size())!=std::string::npos)
        throw std::runtime_error("Water optical-depth geometry-observation seam changed");
    observationSource.replace(seam,old.size(),"        gl_FragData[3]=vec4(normalize(cross(dFdx(worldPosition),dFdy(worldPosition))),0.0);");
    if(bathymetryEnabled) {
        // Observe the column already used by the original main invocation;
        // never sample the bathymetry helper again for instrumentation.
        const std::string columnStore="        gl_FragData[7]=vec4(fresnel,footprint,slopeVariance,normalVariance);";
        const auto at=observationSource.find(columnStore);
        if(at==std::string::npos||observationSource.find(columnStore,at+columnStore.size())!=std::string::npos)
            throw std::runtime_error("Bathymetry column-observation STORE seam changed");
        observationSource.replace(at,columnStore.size(),"        gl_FragData[7]=vec4(localColumn,float(localColumnKnown));");
        const std::string meanStore="        gl_FragData[6]=vec4(behind,float(receiverKind));";
        const auto meanAt=observationSource.find(meanStore);
        if(meanAt==std::string::npos||observationSource.find(meanStore,meanAt+meanStore.size())!=std::string::npos)
            throw std::runtime_error("Bathymetry mean-surface observation STORE seam changed");
        observationSource.replace(meanAt,meanStore.size(),"        gl_FragData[6]=vec4(waterMeanSurfaceY,float(localColumnKnown),localColumn.x,waterUnknownWeight);");
    }
    for(const auto& entry:std::array<std::pair<std::string,std::string>,3>{{{"production.vsh",vertex},{"production-foam0.fsh",fragment},{"observation-only.fsh",observationSource}}}) {
        std::ofstream file(artifacts/entry.first);file<<entry.second;if(!file) throw std::runtime_error("Cannot save expanded optical-depth source");
    }
    Fixture fixture;
    fixture.programs[0]=link(vertex,fragment,"water-optical-depth-production-main","mc_Entity");
    fixture.programs[1]=link(vertex,observationSource,"DEBUG-water-optical-depth-observation","mc_Entity");
    if(firstVisibleBedWavesOnly) {
        const char* outputs[]={"worldPosition","waterMeanSurfaceY","waterUnknownWeight"};
        glTransformFeedbackVaryings(fixture.programs[1],3,outputs,GL_INTERLEAVED_ATTRIBS);
        glLinkProgram(fixture.programs[1]);
        GLint linked=GL_FALSE;glGetProgramiv(fixture.programs[1],GL_LINK_STATUS,&linked);
        if(linked!=GL_TRUE) throw std::runtime_error("First-visible-bed actual VS transform-feedback link failed");
        // All sampler/uniform locations and the retained mc_Entity binding
        // are checked/set below AFTER this relink. C0 neutrality tests this
        // observer program against the unmodified production link separately.
    }
    GLint attachments=0,buffers=0;glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);glGetIntegerv(GL_MAX_DRAW_BUFFERS,&buffers);
    if(attachments<8||buffers<8) throw std::runtime_error("Optical-depth actual-state capture requires eight MRT attachments");
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);
    GLenum draws[8];
    for(int attachment=0;attachment<8;++attachment) {
        glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,fixture.textures[attachment==0?6:7+attachment]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
        draws[attachment]=GL_COLOR_ATTACHMENT0+attachment;
        glFramebufferTexture2D(GL_FRAMEBUFFER,draws[attachment],GL_TEXTURE_2D,fixture.textures[attachment==0?6:7+attachment],0);
    }
    glBindTexture(GL_TEXTURE_2D,fixture.textures[7]);glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,size,size,0,GL_DEPTH_COMPONENT,GL_FLOAT,nullptr);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,fixture.textures[7],0);
    glDrawBuffers(8,draws);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) throw std::runtime_error("Optical-depth separate-output framebuffer incomplete");
    const float white[4]={1,1,1,1},shadow=1;
    std::vector<float> sky(skyWidth*skyHeight*4,0),black(size*size*4,0);
    for(int y=0;y<skyHeight-1;++y) for(int x=0;x<skyWidth;++x) {const int base=(y*skyWidth+x)*4;for(int c=0;c<3;++c) sky[base+c]=0.04f;sky[base+3]=1;}
    for(size_t i=3;i<black.size();i+=4) black[i]=1; // Solar cache RGB and C8 remain exactly zero.
    for(int unit=0;unit<6;++unit) {
        glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,fixture.textures[unit]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        if(unit==3) glTexImage2D(GL_TEXTURE_2D,0,GL_R32F,size,size,0,GL_RED,GL_FLOAT,nullptr);
        else if(unit==4) {glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT32F,1,1,0,GL_DEPTH_COMPONENT,GL_FLOAT,&shadow);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);}
        else glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,unit==0?1:(unit==2?skyWidth:size),unit==0?1:(unit==2?skyHeight:size),0,GL_RGBA,GL_FLOAT,unit==0?white:(unit==2?sky.data():black.data()));
    }
    // Independent native-fixture input, separate from every output attachment.
    // The fixture's undisplaced mean interface is -.5 and its local bed is
    // -1.75, so the actual column depth is 1.25m. The frozen RED pixel's
    // ~1.177m depth below its displaced surface is not mean-surface bathymetry.
    constexpr int bathymetrySize=64;
    constexpr float meanSurfaceY=-0.5f;
    const float localFloorY=firstVisibleBedOnly?-2.5f:-1.75f;
    std::vector<float> bathymetry(bathymetrySize*bathymetrySize*4,0.0f);
    for(size_t i=0;i<bathymetry.size();i+=4) {
        bathymetry[i]=meanSurfaceY-localFloorY;
        bathymetry[i+1]=meanSurfaceY;
        bathymetry[i+2]=bathymetryEnabled?1.0f:0.0f;
    }
    glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,fixture.textures[15]);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,bathymetrySize,bathymetrySize,0,GL_RGBA,GL_FLOAT,bathymetry.data());
    GLint queriedWidth=0,queriedHeight=0,queriedFormat=0;
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&queriedWidth);
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&queriedHeight);
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&queriedFormat);
    if(queriedWidth!=bathymetrySize||queriedHeight!=bathymetrySize||queriedFormat!=GL_RGBA32F)
        throw std::runtime_error("Actual native bathymetry storage does not match the declared 64x64 RGBA32F input");
    if(bathymetryEnabled) {
        save(artifacts/"bathymetry-input.rgba32f",bathymetry);
        std::ofstream input(artifacts/"bathymetry-input.txt");
        input<<"Actual sampler input: unit6,64x64,RGBA32F,NEAREST,Ready1; grid=(-32,-32,64,-.5).\n"
             <<"Queried storage width="<<queriedWidth<<",height="<<queriedHeight<<",format="<<queriedFormat<<".\n"
             <<"Columns=("<<meanSurfaceY-localFloorY<<",-.5,1,0); undisplaced water meanY=-.5, physical local bedY="<<localFloorY<<".\n"
             <<"Same valid native-fixture input in both remote-box states; this is not a null-map fallback GREEN or a live Mod world-binding claim.\n";
        if(!input) throw std::runtime_error("Cannot save actual bathymetry input evidence");
    }
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8"};
    for(GLuint program:fixture.programs) {
        glUseProgram(program);for(int unit=0;unit<6;++unit) glUniform1i(glGetUniformLocation(program,samplers[unit]),unit);
        const GLint bathymetrySampler=glGetUniformLocation(program,"aqualumenBathymetry");
        const GLint bathymetryGrid=glGetUniformLocation(program,"aqualumenBathymetryGrid");
        const GLint bathymetryReady=glGetUniformLocation(program,"aqualumenBathymetryReady");
        if(bathymetryEnabled&&(bathymetrySampler<0||bathymetryGrid<0||bathymetryReady<0))
            throw std::runtime_error("INCONCLUSIVE bathymetry fixture: production shader does not expose the loaded-world input contract");
        glUniform1i(bathymetrySampler,6);glUniform4f(bathymetryGrid,-32,-32,64,meanSurfaceY);
        glUniform1i(bathymetryReady,bathymetryEnabled?1:0);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,projection);
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,inverseProjection);
        for(const char* name:{"gbufferModelView","gbufferModelViewInverse","shadowProjection","shadowModelView"}) glUniformMatrix4fv(glGetUniformLocation(program,name),1,GL_FALSE,identity);
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,62,0);glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),1.25f);
        if(glGetAttribLocation(program,"mc_Entity")!=10) throw std::runtime_error("Water material attribute binding changed");
    }
    glDisableVertexAttribArray(10);glVertexAttrib4f(10,10000,0,0,0);
    glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glDepthMask(GL_FALSE);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glDisable(GL_SCISSOR_TEST);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glViewport(0,0,size,size);
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE1,0,1);glClearColor(0,0,0,0);
    auto draw=[&](const Scene& input,int mode) {
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,fixture.textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,input.colour.data());
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,fixture.textures[3]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RED,GL_FLOAT,input.depth.data());
        glActiveTexture(GL_TEXTURE7);glBindTexture(GL_TEXTURE_2D,fixture.textures[7]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,input.depth.data());
        const GLuint program=fixture.programs[mode<0?0:1];glUseProgram(program);
        if(mode>=0) glUniform1i(glGetUniformLocation(program,"DEBUG_shoreCausalMode"),mode);
        glClear(GL_COLOR_BUFFER_BIT);glBegin(firstVisibleBedWavesOnly?GL_TRIANGLES:GL_QUADS);
        for(int z=-24;z<0;++z) for(int x=-8;x<8;++x) {
            glVertex3f(x,-0.5f,z);glVertex3f(x+1,-0.5f,z);glVertex3f(x+1,-0.5f,z+1);
            if(firstVisibleBedWavesOnly) {glVertex3f(x,-0.5f,z);glVertex3f(x+1,-0.5f,z+1);}
            glVertex3f(x,-0.5f,z+1);
        }
        glEnd();Capture result;result.colour.resize(size*size*4);
        glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.colour.data());
        if(mode>=0) for(int attachment=1;attachment<8;++attachment) {result.state[attachment-1].resize(size*size*4);glReadBuffer(GL_COLOR_ATTACHMENT0+attachment);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.state[attachment-1].data());}
        glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Optical-depth actual main GL error");
        // Reject NaN/Inf BEFORE qualification or any difference/threshold
        // comparisons: std::max/abs comparisons alone can silently ignore NaN.
        auto requireFiniteReadback=[&](const std::vector<float>& field,int attachment) {
            for(size_t component=0;component<field.size();++component) if(!std::isfinite(field[component])) {
                const size_t pixel=component/4;
                throw std::runtime_error("Nonfinite optical-depth readback: mode="+std::to_string(mode)
                    +" attachment="+std::to_string(attachment)+" pixel="+std::to_string(pixel%size)
                    +","+std::to_string(pixel/size)+" channel="+std::to_string(component%4)
                    +" value="+std::to_string(field[component]));
            }
        };
        requireFiniteReadback(result.colour,0);
        if(mode>=0) for(size_t attachment=0;attachment<result.state.size();++attachment)
            requireFiniteReadback(result.state[attachment],int(attachment)+1);
        for(int q=0;q<size*size;++q) if(result.colour[q*4+3]!=0&&result.colour[q*4+3]!=1) throw std::runtime_error("Invalid optical-depth water-coverage alpha");
        return result;
    };
    if(firstVisibleBedOnly) {
        // Public C0 is the acceptance boundary. The actual original invocation
        // is observed, never replaced by a copied marcher or a forced hit.
        const int x=fixedX<0?65:fixedX,y=fixedY<0?48:fixedY,pixel=y*size+x,index=pixel*4;
        constexpr float shelfTop=-2.5f,stepZ=-8.0f;
        constexpr float neutralGreen=0.25f,tagGreen=neutralGreen+0.18f;
        const double increment=double(tagGreen)-double(neutralGreen);
        const double epsilon=std::numeric_limits<float>::epsilon();
        const std::string clarityOption="#define WATER_CLARITY ";
        const auto clarityAt=fragment.find(clarityOption);
        double clarity=0;
        if(clarityAt!=std::string::npos) {
            std::istringstream value(fragment.substr(clarityAt+clarityOption.size()));value>>clarity;
        }
        if(!std::isfinite(clarity)||clarity<=0)
            throw std::runtime_error("First-visible-bed public WATER_CLARITY input is unavailable");
        auto require=[](bool condition,const std::string& reason) {
            if(!condition) throw std::runtime_error("INCONCLUSIVE first-visible-bed fixture: "+reason);
        };
        for(int unit:{1,3}) {
            glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,fixture.textures[unit]);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,firstBedFilter);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,firstBedFilter);
        }
        auto cameraRay=[&](double u,double v) {return V3{(2*u-1)/f,(2*v-1)/f,-1};};
        auto projectedUV=[&](const V3& point) {
            return std::array<double,2>{0.5+0.5*f*point[0]/(-point[2]),0.5+0.5*f*point[1]/(-point[2])};
        };
        auto refractedFacet=[](const V3& incident,const V3& normal) {
            constexpr double ratio=1.0/1.333;
            const double cosine=-dot(incident,normal),square=1-ratio*ratio*(1-cosine*cosine);
            if(cosine<=0||square<=0) throw std::runtime_error("INCONCLUSIVE first-visible-bed Snell interface");
            return add(add({0,0,0},incident,ratio),normal,ratio*cosine-std::sqrt(square));
        };
        auto nearBedScene=[&](const std::vector<Box>& boxes,bool tagged) {
            Scene result=scene(boxes,false,f,a,b);
            if(tagged) for(int k=0;k<size*size;++k) if(result.id[k]==0) result.colour[k*4+1]=tagGreen;
            return result;
        };
        auto uploadColumns=[&](float remoteDepth,const std::string& name) {
            for(int z=0;z<bathymetrySize;++z) for(int u=0;u<bathymetrySize;++u) {
                const float worldX=-32.0f+u+0.5f,worldZ=-32.0f+z+0.5f;
                const int k=(z*bathymetrySize+u)*4;
                const bool inside=worldX>-20&&worldX<20&&worldZ< -0.05f;
                bathymetry[k]=worldZ<stepZ?remoteDepth:2.0f;
                bathymetry[k+1]=meanSurfaceY;bathymetry[k+2]=inside?1.0f:0.0f;bathymetry[k+3]=0;
            }
            glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,fixture.textures[15]);
            glTexSubImage2D(GL_TEXTURE_2D,0,0,0,bathymetrySize,bathymetrySize,GL_RGBA,GL_FLOAT,bathymetry.data());
            save(artifacts/(name+"-bathymetry.rgba32f"),bathymetry);
        };
        // New waves case only: one-metre upper-face mesh x[-8,8], z[-24,0],
        // 425 original-VS point outputs. The FS draw uses explicit ABC/ACD
        // triangles, so its surface can be checked without copying wave math
        // or guessing a compatibility QUADS triangulation.
        constexpr int meshWidth=17,meshHeight=25,vertexStride=5;
        auto captureVertices=[&](const std::string& name) {
            std::vector<float> vertices(meshWidth*meshHeight*vertexStride,std::numeric_limits<float>::quiet_NaN());
            GLint generic=0,indexed=0,previousProgram=0;GLint64 start=0,length=0;
            glGetIntegerv(GL_TRANSFORM_FEEDBACK_BUFFER_BINDING,&generic);
            glGetIntegeri_v(GL_TRANSFORM_FEEDBACK_BUFFER_BINDING,0,&indexed);
            glGetInteger64i_v(GL_TRANSFORM_FEEDBACK_BUFFER_START,0,&start);
            glGetInteger64i_v(GL_TRANSFORM_FEEDBACK_BUFFER_SIZE,0,&length);
            glGetIntegerv(GL_CURRENT_PROGRAM,&previousProgram);
            const bool discard=glIsEnabled(GL_RASTERIZER_DISCARD)==GL_TRUE;
            GLuint buffer=0;glGenBuffers(1,&buffer);
            struct RestoreVSReadback {
                GLuint buffer;GLint generic,indexed,program;GLint64 start,length;bool discard;
                ~RestoreVSReadback() {
                    if(indexed&&length>0) glBindBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,indexed,start,length);
                    else glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,indexed);
                    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,generic);
                    if(discard) glEnable(GL_RASTERIZER_DISCARD);else glDisable(GL_RASTERIZER_DISCARD);
                    glUseProgram(program);glDeleteBuffers(1,&buffer);
                }
            } restore{buffer,generic,indexed,previousProgram,start,length,discard};
            glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,buffer);
            glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,GLsizeiptr(vertices.size()*sizeof(float)),nullptr,GL_STREAM_READ);
            glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,buffer);
            glUseProgram(fixture.programs[1]);glEnable(GL_RASTERIZER_DISCARD);
            glBeginTransformFeedback(GL_POINTS);glBegin(GL_POINTS);
            for(int z=-24;z<=0;++z) for(int u=-8;u<=8;++u) glVertex3f(u,meanSurfaceY,z);
            glEnd();glEndTransformFeedback();
            glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,GLsizeiptr(vertices.size()*sizeof(float)),vertices.data());
            require(glGetError()==GL_NO_ERROR,"actual VS transform-feedback capture failed");
            save(artifacts/(name+"-original-VS-grid.xyz-mean-unknown.f32"),vertices);
            for(float component:vertices) require(std::isfinite(component),"actual VS output is missing or nonfinite");
            return vertices;
        };
        GLint rasterSubpixelBits=0;double rasterSnapPixels=0;
        // Rasterized vertex positions have finite subpixel precision. For
        // positive barycentric weights, the original-vs-snapped screen point
        // is a convex combination of per-vertex half-grid offsets. This is a
        // hardware-derived geometry qualification, NOT a measured-error or
        // Beer/color/path allowance.
        const double rasterArithmeticPixels=8*epsilon*size;
        if(firstVisibleBedWavesOnly) {
            glGetIntegerv(GL_SUBPIXEL_BITS,&rasterSubpixelBits);
            require(rasterSubpixelBits>=0&&rasterSubpixelBits<=30,"invalid actual raster subpixel precision");
            rasterSnapPixels=std::ldexp(0.5,-rasterSubpixelBits);
            std::ofstream precision(artifacts/"raster-precision.txt");
            precision<<std::setprecision(14)<<"Actual GL_SUBPIXEL_BITS="<<rasterSubpixelBits
                <<"\nHalf-grid per-vertex screen snapping envelope (pixels)="<<rasterSnapPixels
                <<"\nFloat32 multiply/divide/viewport arithmetic envelope (8 epsilon*width pixels)="<<rasterArithmeticPixels
                <<"\nPositive barycentric interpolation keeps the backprojected point within the convex vertex-snap envelope. Original-VS physical first-surface membership is checked separately. Transport bounds are unchanged.\n";
            if(!precision)throw std::runtime_error("Cannot save actual raster precision");
        }
        struct SurfaceHit {bool valid=false;double travel=0;V3 point={};int triangle=-1,ties=0;std::array<int,3> vertices={};bool allKnown=true;V3 barycentric={};};
        auto meshFirstSurface=[&](const std::vector<float>& vertices,const V3& ray) {
            SurfaceHit result;double nearest=std::numeric_limits<double>::infinity();
            auto cross=[](const V3& u,const V3& v) {return V3{u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]};};
            auto point=[&](int k) {return V3{vertices[k*vertexStride],vertices[k*vertexStride+1],vertices[k*vertexStride+2]};};
            for(int z=0;z<meshHeight-1;++z) for(int u=0;u<meshWidth-1;++u) {
                const int A=z*meshWidth+u,B=A+1,C=A+meshWidth+1,D=A+meshWidth;
                const std::array<std::array<int,3>,2> triangles={{{A,B,C},{A,C,D}}};
                for(int part=0;part<2;++part) {
                    const auto triangle=triangles[part];const V3 p=point(triangle[0]);
                    const V3 ab=add(point(triangle[1]),p,-1),ac=add(point(triangle[2]),p,-1),h=cross(ray,ac);
                    const double determinant=dot(ab,h);if(std::abs(determinant)<1e-12) continue;
                    const V3 s=add({0,0,0},p,-1),q=cross(s,ab);
                    const double b1=dot(s,h)/determinant,b2=dot(ray,q)/determinant,t=dot(ac,q)/determinant;
                    if(b1< -1e-10||b2< -1e-10||b1+b2>1+1e-10||t<=0) continue;
                    const V3 hit=add({0,0,0},ray,t);
                    const double tolerance=64*epsilon*std::max(1.0,std::abs(t));
                    if(result.valid&&std::abs(t-nearest)<=tolerance) {
                        double error=0;for(int c=0;c<3;++c) error=std::max(error,std::abs(hit[c]-result.point[c]));
                        require(error<=tolerance,"first water mesh surface has a noncoincident ray/triangle tie");
                        for(int vertexIndex:triangle) result.allKnown=result.allKnown&&vertices[vertexIndex*vertexStride+4]==0;
                        ++result.ties;continue; // Shared-edge same-position hits are explicitly recorded.
                    }
                    if(t<nearest) {
                        nearest=t;result={true,t,hit,((z*(meshWidth-1)+u)*2+part),1,triangle};
                        result.barycentric={1-b1-b2,b1,b2};
                        for(int vertexIndex:triangle) result.allKnown=result.allKnown&&vertices[vertexIndex*vertexStride+4]==0;
                    }
                }
            }
            return result;
        };
        struct BedResult {
            std::string name;float remoteDepth=0;
            std::vector<Box> boxes;Scene neutral,tagged;
            Capture clear,tag;std::array<Capture,3> observation,tagObservation;
            std::vector<float> vsVertices;
            Hit first;V3 point={},normal={},ray={};
            int sourceX=0,sourceY=0,returnedX=-1,returnedY=-1,returnedBox=-1,kind=0;
            double fresnel=0,pathLow=0,pathHigh=0,responseLow=0,responseHigh=0;
            double response=0,path=0,confidence=0,neutrality=0,repeat=0,noise=0;
        };
        std::array<BedResult,3> results;
        // The short-seed case is a renderer/source positive control, not a
        // replacement algorithm. 6/8m both returning zero must not pass.
        const std::array<float,3> remoteDepths={2.0f,6.0f,8.0f};
        const std::array<std::string,3> names={firstVisibleBedWavesOnly?"remote-depth2-control":"flat-positive-control","remote-depth6","remote-depth8"};
        std::ofstream records(artifacts/"first-visible-bed.csv");
        records<<std::setprecision(14)<<"state,x,y,remoteDepth,firstBox,axis,side,firstT,firstX,firstY,firstZ,cameraVisible,sourceTexelX,sourceTexelY,originalBox,kind,confidence,initialPath,opticalPath,returnedU,returnedV,returnedBox,pathLow,pathHigh,F,greenIncrement,response,responseLow,responseHigh,observerC0error,repeat,floatBound\n";
        std::ofstream qualification(artifacts/"first-visible-bed-qualification.csv");
        qualification<<std::setprecision(14)<<"state,x,y,waterAlpha,worldX,worldY,worldZ,localDepth,gradX,gradZ,known,meanY,unknownWeight,originalBox,firstBox,firstT,firstX,firstY,firstZ,cameraVisible,snellError\n";
        std::ofstream meshRecords;
        if(firstVisibleBedWavesOnly) {
            meshRecords.open(artifacts/"first-visible-bed-mesh.csv");
            meshRecords<<std::setprecision(14)<<"state,x,y,triangle,coincidentFirstHits,meshX,meshY,meshZ,FSX,FSY,FSZ,positionError,vertex0,vertex1,vertex2,barycentric0,barycentric1,barycentric2,screenOffsetX,screenOffsetY,snapPixels,arithmeticPixels\n";
        }
        double peak=1,geometryError=0;
        for(int state=0;state<3;++state) {
            BedResult& result=results[state];result.name=names[state];result.remoteDepth=remoteDepths[state];
            result.boxes={{{-20,-16,stepZ},{20,shelfTop,-0.05},0},
                          {{-20,-16,-120},{20,meanSurfaceY-result.remoteDepth,stepZ},1}};
            uploadColumns(result.remoteDepth,result.name);
            if(firstVisibleBedWavesOnly) result.vsVertices=captureVertices(result.name);
            result.neutral=nearBedScene(result.boxes,false);result.tagged=nearBedScene(result.boxes,true);
            result.clear=draw(result.neutral,-1);result.tag=draw(result.tagged,-1);
            const auto repeated=draw(result.tagged,-1);
            result.repeat=difference(result.tag.colour,repeated.colour);
            save(artifacts/(result.name+"-repeat-C0.rgba32f"),repeated.colour);
            for(int mode=0;mode<3;++mode) {
                const int actualMode=mode==0?0:(mode==1?2:3);
                result.observation[mode]=draw(result.neutral,actualMode);
                result.tagObservation[mode]=draw(result.tagged,actualMode);
                save(artifacts/(result.name+"-mode"+std::to_string(actualMode)+"-C0.rgba32f"),result.observation[mode].colour);
                save(artifacts/(result.name+"-mode"+std::to_string(actualMode)+"-tag-C0.rgba32f"),result.tagObservation[mode].colour);
                result.neutrality=std::max({result.neutrality,
                    difference(result.clear.colour,result.observation[mode].colour),
                    difference(result.tag.colour,result.tagObservation[mode].colour)});
            }
            save(artifacts/(result.name+"-neutral.rgba32f"),result.clear.colour);
            save(artifacts/(result.name+"-shelf-green-tag.rgba32f"),result.tag.colour);
            save(artifacts/(result.name+"-depth.r32f"),result.neutral.depth);
            save(artifacts/(result.name+"-C4.rgba32f"),result.neutral.colour);
            save(artifacts/(result.name+"-tag-C4.rgba32f"),result.tagged.colour);
            for(int mode=0;mode<3;++mode) for(int attachment=0;attachment<7;++attachment) {
                const std::string stem=result.name+"-mode"+std::to_string(mode==0?0:(mode==1?2:3))+"-mrt"+std::to_string(attachment+1);
                save(artifacts/(stem+".rgba32f"),result.observation[mode].state[attachment]);
                save(artifacts/(stem+"-tag.rgba32f"),result.tagObservation[mode].state[attachment]);
            }
            for(float component:result.clear.colour) peak=std::max(peak,std::abs(double(component)));
            for(float component:result.tag.colour) peak=std::max(peak,std::abs(double(component)));
            result.noise=64*epsilon*peak+8*(result.neutrality+result.repeat);
            require(result.neutrality<=64*epsilon*peak&&result.repeat<=64*epsilon*peak,"observer or deterministic repeat changes production C0");
            const Capture& geometry=result.observation[0];const Capture& transport=result.observation[1];
            // Qualify the entire derivative quad from geometry and source
            // inputs BEFORE interpreting any state's public color response.
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                const int q=((y&~1)+dy)*size+(x&~1)+dx,offset=q*4;
                const V3 point=value(geometry.state[0],q),viewPoint=value(geometry.state[1],q);
                V3 facet=normalized(value(transport.state[2],q));if(facet[1]<0) for(double& c:facet)c=-c;
                const V3 optical=value(geometry.state[2],q),actualRay=value(geometry.state[3],q);
                const V3 referenceNormal=firstVisibleBedWavesOnly?normalized(optical):facet;
                const V3 ray=refractedFacet(normalized(point),referenceNormal);
                const Hit local=firstHit(result.boxes,point,{0,-1,0}),first=firstHit(result.boxes,point,ray);
                double snellError=0;
                for(int c=0;c<3;++c) {
                    snellError=std::max(snellError,std::abs(ray[c]-actualRay[c]));
                    if(!firstVisibleBedWavesOnly)
                        require(std::abs(optical[c]-facet[c])<=64*epsilon,"flat public wave option does not use the geometric facet");
                    require(std::abs(point[c]-viewPoint[c])<=64*epsilon*std::max(1.0,std::abs(point[c])),"fixture identity-view coordinate basis differs");
                    if(state>0) geometryError=std::max({geometryError,
                        std::abs(point[c]-results[0].observation[0].state[0][offset+c]),
                        std::abs(optical[c]-results[0].observation[0].state[2][offset+c]),
                        std::abs(actualRay[c]-results[0].observation[0].state[3][offset+c])});
                }
                require(result.clear.colour[offset+3]==1&&result.tag.colour[offset+3]==1,"not a water-covered derivative quad");
                if(!firstVisibleBedWavesOnly) {
                    require(std::abs(point[1]-meanSurfaceY)<=64*epsilon&&facet[1]>1-64*epsilon,"real VS does not produce the specified flat interface");
                } else {
                    require(std::abs(std::sqrt(dot(optical,optical))-1)<=64*epsilon
                        &&dot(optical,facet)>0&&-dot(optical,normalized(point))>0,"nonzero-wave optical normal is not unit/front-facing on the actual surface");
                    const auto observedScreen=projectedUV(point);
                    const double offsetX=observedScreen[0]*size-(q%size+.5),offsetY=observedScreen[1]*size-(q/size+.5);
                    require(std::abs(offsetX)<=rasterSnapPixels+rasterArithmeticPixels
                        &&std::abs(offsetY)<=rasterSnapPixels+rasterArithmeticPixels,"FS backprojection leaves the independently derived raster vertex-snap envelope");
                    // The backprojected actual sample ray accounts for raster
                    // vertex snapping; its FIRST intersection must still be
                    // the original-VS triangle containing the observed P.
                    const SurfaceHit surface=meshFirstSurface(result.vsVertices,normalized(point));
                    require(surface.valid&&surface.allKnown,"actual VS mesh has no unique known first surface");
                    double positionError=0;
                    for(int c=0;c<3;++c) positionError=std::max(positionError,std::abs(surface.point[c]-point[c]));
                    require(positionError<=64*epsilon*std::max(1.0,std::abs(point[2])),"FS position differs from independently raycast original-VS triangles");
                    for(int vertexIndex:surface.vertices) {
                        require(std::abs(result.vsVertices[vertexIndex*vertexStride+3]-meanSurfaceY)<=64*epsilon,"first VS triangle uses another mean surface");
                        if(state>0) for(int c=0;c<vertexStride;++c)
                            geometryError=std::max(geometryError,std::abs(double(result.vsVertices[vertexIndex*vertexStride+c])-results[0].vsVertices[vertexIndex*vertexStride+c]));
                    }
                    meshRecords<<result.name<<","<<q%size<<","<<q/size<<","<<surface.triangle<<","<<surface.ties;
                    for(double component:surface.point)meshRecords<<","<<component;
                    for(double component:point)meshRecords<<","<<component;
                    meshRecords<<","<<positionError;for(int vertexIndex:surface.vertices)meshRecords<<","<<vertexIndex;
                    for(double weight:surface.barycentric)meshRecords<<","<<weight;
                    meshRecords<<","<<offsetX<<","<<offsetY<<","<<rasterSnapPixels<<","<<rasterArithmeticPixels<<"\n";
                }
                require(snellError<=64*epsilon,"actual transmitted direction differs from independent dielectric law");
                require(local.valid&&!local.inside&&!local.tangent&&local.id==0&&local.axis==1&&local.side==1,"local column is not over the specified shelf");
                require(first.valid&&!first.inside&&!first.tangent&&first.id==0&&first.axis==1&&first.side==1&&cameraVisible(result.boxes,first),"first transmitted shelf is absent, unresolved or camera-occluded");
                require(first.point[2]>stepZ+1&&first.point[2]< -0.25,"first shelf receiver is near a real step/field edge");
                require(result.neutral.id[q]==1&&result.tagged.colour[offset+1]==result.neutral.colour[offset+1],"original-UV proxy is not an untagged remote floor");
                require(geometry.state[6][offset+3]==1&&std::abs(geometry.state[6][offset]-2)<=64*epsilon
                    &&std::abs(geometry.state[6][offset+1])<=64*epsilon&&std::abs(geometry.state[6][offset+2])<=64*epsilon
                    &&transport.state[5][offset+1]==1&&transport.state[5][offset+3]==0
                    &&std::abs(transport.state[5][offset]-meanSurfaceY)<=64*epsilon,"real VS/FS did not use the confirmed two-metre column");
                qualification<<result.name<<","<<q%size<<","<<q/size<<","<<result.clear.colour[offset+3];
                for(double component:point)qualification<<","<<component;
                for(int c=0;c<4;++c)qualification<<","<<geometry.state[6][offset+c];
                qualification<<","<<transport.state[5][offset]<<","<<transport.state[5][offset+3]<<","<<result.neutral.id[q]<<","<<first.id<<","<<first.travel;
                for(double component:first.point)qualification<<","<<component;
                qualification<<",1,"<<snellError<<"\n";
                if(q==pixel) {result.point=point;result.normal=referenceNormal;result.ray=ray;result.first=first;}
            }
            require(geometryError<=64*epsilon*std::max(1.0,std::abs(result.point[2])),"remote floor changed local water geometry/normal/ray");
            result.fresnel=facetFresnel(-dot(normalized(result.point),result.normal));
            const auto uv=projectedUV(result.first.point);
            require(uv[0]>.06&&uv[0]<.94&&uv[1]>.06&&uv[1]<.94,"physical first bed is not safely inside the viewport");
            result.sourceX=int(std::floor(uv[0]*size));result.sourceY=int(std::floor(uv[1]*size));
            const int sourcePixel=result.sourceY*size+result.sourceX;
            require(result.neutral.id[sourcePixel]==0&&result.tagged.colour[sourcePixel*4+1]-result.neutral.colour[sourcePixel*4+1]==float(increment),"the actual screen texture lacks the near-bed source");
            if(firstBedFilter==GL_LINEAR) {
                const int left=int(std::floor(uv[0]*size-.5)),bottom=int(std::floor(uv[1]*size-.5));
                for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                    const int u=left+dx,v=bottom+dy;
                    require(u>=0&&u<size&&v>=0&&v<size,"physical LINEAR source support leaves the viewport");
                    const int q=v*size+u;
                    require(result.neutral.id[q]==0&&result.tagged.colour[q*4+1]-result.neutral.colour[q*4+1]==float(increment),"physical LINEAR support straddles a source/visibility boundary");
                }
            }
            result.pathLow=std::numeric_limits<double>::infinity();result.pathHigh=0;
            // Camera-texel footprint on the physical plane, not a private
            // screen-depth iteration/reprojection oracle.
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                const Hit corner=firstHit(result.boxes,{0,0,0},cameraRay(double(result.sourceX+dx)/size,double(result.sourceY+dy)/size));
                require(corner.valid&&!corner.inside&&!corner.tangent&&corner.id==0&&corner.axis==1&&corner.side==1,"source texel straddles an actual visibility/source boundary");
                const double travel=(corner.point[2]-result.point[2])/result.ray[2];
                require(travel>0&&std::isfinite(travel),"undefined source-footprint optical path");
                result.pathLow=std::min(result.pathLow,travel);result.pathHigh=std::max(result.pathHigh,travel);
            }
            const float storedDepth=result.neutral.depth[sourcePixel];
            for(float depth:{std::nextafter(storedDepth,-std::numeric_limits<float>::infinity()),
                             storedDepth,std::nextafter(storedDepth,std::numeric_limits<float>::infinity())}) {
                const double z=-double(b)/(2*double(depth)-1+double(a));
                const double travel=(z-result.point[2])/result.ray[2];
                require(std::isfinite(travel)&&travel>0,"R32F source depth cannot represent a positive ray path");
                result.pathLow=std::min(result.pathLow,travel);result.pathHigh=std::max(result.pathHigh,travel);
            }
            const double pathRoundoff=64*epsilon*std::max({1.0,std::abs(result.point[2]),std::abs(result.first.point[2]),result.pathHigh})/std::abs(result.ray[2]);
            result.pathLow=std::max(0.0,result.pathLow-pathRoundoff);result.pathHigh+=pathRoundoff;
            result.responseLow=increment*(1-result.fresnel)*std::exp(-0.085*result.pathHigh/clarity);
            result.responseHigh=increment*(1-result.fresnel)*std::exp(-0.085*result.pathLow/clarity);
            require(result.responseLow>16*result.noise,"independent source expectation is not resolved above float/observer noise");
            const V3 reflectedRay=value(transport.state[1],pixel),reflectionOrigin=value(transport.state[0],pixel);
            const Hit reflectedHit=firstHit(result.boxes,reflectionOrigin,reflectedRay);
            require(reflectedRay[1]>0&&!reflectedHit.valid&&!reflectedHit.inside,"tagged shelf is a possible physical reflection receiver");
            const Capture& taggedTransport=result.tagObservation[1];
            for(int c=0;c<3;++c)
                require(std::abs(double(taggedTransport.state[4][index+c])-transport.state[4][index+c])<=result.noise,"near-bed tag also changes the SSR/reflection branch");
            const auto& reflectedSource=result.observation[2].state[0];
            if(reflectedSource[index]>=0&&reflectedSource[index+1]>=0) {
                const int u=std::clamp(int(std::floor(reflectedSource[index]*size)),0,size-1);
                const int v=std::clamp(int(std::floor(reflectedSource[index+1]*size)),0,size-1);
                require(result.neutral.id[v*size+u]!=0,"actual SSR accepted the tagged shelf");
            }
            for(int c:{0,2}) require(std::abs(double(result.tag.colour[index+c])-result.clear.colour[index+c])<=result.noise,"green-only source changes another C0 channel");
            result.response=double(result.tag.colour[index+1])-result.clear.colour[index+1];
            result.path=geometry.state[2][index+3];result.confidence=geometry.state[3][index+3];
            result.kind=int(geometry.state[4][index+3]);
            const double returnedU=geometry.state[5][index],returnedV=geometry.state[5][index+1];
            if(returnedU>=0&&returnedU<1&&returnedV>=0&&returnedV<1) {
                const int u=int(std::floor(returnedU*size)),v=int(std::floor(returnedV*size));
                result.returnedX=u;result.returnedY=v;
                result.returnedBox=result.neutral.id[v*size+u];
            }
            records<<result.name<<","<<x<<","<<y<<","<<result.remoteDepth<<","<<result.first.id<<","<<result.first.axis<<","<<result.first.side<<","<<result.first.travel;
            for(double component:result.first.point)records<<","<<component;
            records<<",1,"<<result.sourceX<<","<<result.sourceY<<","<<result.neutral.id[pixel]<<","<<result.kind<<","<<result.confidence
                <<","<<geometry.state[1][index+3]<<","<<result.path<<","<<returnedU<<","<<returnedV<<","<<result.returnedBox
                <<","<<result.pathLow<<","<<result.pathHigh<<","<<result.fresnel<<","<<increment<<","<<result.response
                <<","<<result.responseLow<<","<<result.responseHigh<<","<<result.neutrality<<","<<result.repeat<<","<<result.noise<<"\n";
            std::cout<<std::setprecision(14)<<"DEBUG-first-visible-bed "<<result.name<<" pixel="<<x<<","<<y
                <<" physicalFirstT="<<result.first.travel<<" cameraVisible=1 localDepth=2 originalBox="<<result.neutral.id[pixel]
                <<" kind="<<result.kind<<" confidence="<<result.confidence<<" initialPath="<<geometry.state[1][index+3]<<" path="<<result.path
                <<" returnedBox="<<result.returnedBox<<" response="<<result.response<<" expected=["<<result.responseLow<<","<<result.responseHigh
                <<"] pathFootprint=["<<result.pathLow<<","<<result.pathHigh<<"] observationC0error="<<result.neutrality
                <<" repeat="<<result.repeat<<" floatBound="<<result.noise<<"\n";
        }
        records.close();qualification.close();
        if(!records||!qualification) throw std::runtime_error("Cannot save first-visible-bed qualification evidence");
        if(firstVisibleBedWavesOnly) {meshRecords.close();if(!meshRecords)throw std::runtime_error("Cannot save first-visible-bed VS mesh qualification");}
        auto retainedFirstSource=[](const BedResult& result) {
            return result.kind==1&&result.returnedBox==0
                &&result.returnedX==result.sourceX&&result.returnedY==result.sourceY
                &&result.path>=result.pathLow&&result.path<=result.pathHigh
                &&result.response>=result.responseLow-result.noise&&result.response<=result.responseHigh+result.noise;
        };
        if(!firstVisibleBedWavesOnly)
            require(retainedFirstSource(results[0]),"flat positive control does not resolve the visible near-bed source (not a behavioral RED)");
        bool passed=true;for(int state=firstVisibleBedWavesOnly?0:1;state<3;++state) passed=passed&&retainedFirstSource(results[state]);
        std::cout<<"DEBUG-first-visible-bed filter="<<(firstBedFilter==GL_LINEAR?"LINEAR":"NEAREST")<<" public WAVE_HEIGHT="<<(firstVisibleBedWavesOnly?"0.12":"0")<<"/SHORE_FOAM=0, real VS/main, actual known 2m column; C8/Sun=0. Three coherent closed-box inputs retain one camera-visible first shelf; only the remote original-view floor changes. No local-depth hit or forced-confidence oracle.\n";
        if(firstVisibleBedWavesOnly)
            std::cout<<"DEBUG-first-visible-bed waves scope: fixed phase1.25/pixel65,48, 1m explicit TRIANGLES x[-8,8]/z[-24,0], original-VS 425-point transform feedback; independent first surface and transport GIVEN the actual FS optical normal. This does not verify the wave spectrum, shipping mesh topology or natural shore appearance.\n";
        if(enforceInvariant&&!passed)
            throw std::runtime_error("A camera-visible first near-bed source must retain its independently bounded Beer/Fresnel C0 response and near-bed optical path when only the remote original-view floor changes");
        std::cout<<(enforceInvariant?"PASS":"DIAGNOSTIC")<<" production water main first-visible-bed "<<(passed?"retained":"source/path loss (no GREEN claim)")<<"; geometryDelta="<<geometryError<<"\n";
        return;
    }
    const std::vector<Box> baseBoxes={{{-20,-4,-32},{20,-1.75,-0.05},0},{{-16,0,-12.1},{16,12,-12},2}};
    const auto base=draw(scene(baseBoxes,false,f,a,b),-1),baseTag=draw(scene(baseBoxes,true,f,a,b),-1);
    const auto geometry=draw(scene(baseBoxes,false,f,a,b),0),transport=draw(scene(baseBoxes,false,f,a,b),2);
    const double firstNeutrality=std::max(difference(base.colour,geometry.colour),difference(base.colour,transport.colour));
    if(firstNeutrality>1e-6) throw std::runtime_error("Optical-depth observations perturb baseline production C0/coverage");
    std::vector<int> candidates;
    if(fixedX>=0) candidates.push_back(fixedY*size+fixedX);
    else for(int y=36;y<=48;y+=2) for(int x=56;x<=72;x+=2) candidates.push_back(y*size+x);
    std::ofstream controls(artifacts/"candidate-controls.csv");controls<<std::setprecision(12)<<"x,y,qualified,reason,highResponse,lowResponse,trueFacetFresnel,neutrality,repeat,geometryDelta\n";
    bool qualified=false;double observed[2]={0,0},oracleFresnel=0,numericalBound=0;int retained=-1;
    std::array<std::vector<Box>,2> retainedBoxes;
    std::array<Scene,2> retainedInputs;
    for(int pixel:candidates) {
        const int x=pixel%size,y=pixel/size,baseIndex=pixel*4;
        if(base.colour[baseIndex+3]!=1||baseTag.colour[baseIndex]-base.colour[baseIndex]<=1e-5) {controls<<x<<","<<y<<",0,no_initial_reflection_source,0,0,0,0,0,0\n";continue;}
        const V3 p=value(geometry.state[0],pixel),eye={0,0,0};
        if(p[1]>=-0.15||p[1]<=-0.8) {controls<<x<<","<<y<<",0,unsuitable_surface_height,0,0,0,0,0,0\n";continue;}
        V3 facet=normalized(value(transport.state[2],pixel));if(facet[1]<0) for(double& c:facet) c=-c;
        const V3 toEye=normalized(add(eye,p,-1)),incident=add({0,0,0},toEye,-1),trueRay=reflected(incident,facet);
        const double fresnel=facetFresnel(dot(facet,toEye));
        const double lambda=0.25/(-p[1]);const V3 q=add(p,p,lambda);
        const Box high={{q[0]-0.8,-4,q[2]-0.25},{q[0]+0.8,p[1]-0.25,q[2]+0.25},1};
        Box low=high;low.hi[1]=-1.8;
        if(q[2]+0.25>=p[2]-0.2||trueRay[1]<=0||trueRay[2]>=-0.1||fresnel<=1e-4) {controls<<x<<","<<y<<",0,unqualified_true_facet,0,0,"<<fresnel<<",0,0,0\n";continue;}
        std::array<std::vector<Box>,2> boxes={baseBoxes,baseBoxes};boxes[0].push_back(high);boxes[1].push_back(low);
        std::array<Scene,2> neutral={scene(boxes[0],false,f,a,b),scene(boxes[1],false,f,a,b)};
        bool inputQualified=true;
        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
            const int z=(y&~1)+dy,u=(x&~1)+dx,k=z*size+u;
            const V3 point=value(geometry.state[0],k);
            const Hit local0=firstHit(boxes[0],point,{0,-1,0}),local1=firstHit(boxes[1],point,{0,-1,0});
            if(base.colour[k*4+3]!=1||neutral[0].id[k]!=1||neutral[1].id[k]!=0||point[1]-neutral[0].receiver[k][1]<0.10||point[1]-neutral[0].receiver[k][1]>0.5||point[1]-neutral[1].receiver[k][1]<0.85||!local0.valid||!local1.valid||local0.id!=0||local1.id!=0) inputQualified=false;
        }
        const Hit true0=firstHit(boxes[0],add(p,facet,0.06),trueRay),true1=firstHit(boxes[1],add(p,facet,0.06),trueRay);
        if(!inputQualified||true0.id!=2||true1.id!=2||!cameraVisible(boxes[0],true0)||!cameraVisible(boxes[1],true1)) {controls<<x<<","<<y<<",0,remote_or_local_geometry_control,0,0,"<<fresnel<<",0,0,0\n";continue;}
        std::array<Capture,2> clear,tag,top,info,source;
        double repeatError=0,neutrality=firstNeutrality,geometryDelta=0,peak=1;
        bool sourceQualified=true;std::array<Hit,2> physical;
        for(int state=0;state<2;++state) {
            clear[state]=draw(neutral[state],-1);tag[state]=draw(scene(boxes[state],true,f,a,b),-1);
            const auto repeat=draw(scene(boxes[state],true,f,a,b),-1);repeatError=std::max(repeatError,difference(tag[state].colour,repeat.colour));
            top[state]=draw(neutral[state],0);info[state]=draw(neutral[state],2);source[state]=draw(neutral[state],3);
            neutrality=std::max({neutrality,difference(clear[state].colour,top[state].colour),difference(clear[state].colour,info[state].colour),difference(clear[state].colour,source[state].colour)});
            const auto tagObserved=draw(scene(boxes[state],true,f,a,b),2);neutrality=std::max(neutrality,difference(tag[state].colour,tagObserved.colour));
            observed[state]=double(tag[state].colour[baseIndex])-clear[state].colour[baseIndex];
            const V3 origin=value(info[state].state[0],pixel),ray=value(info[state].state[1],pixel),transmitted=value(top[state].state[3],pixel);
            physical[state]=firstHit(boxes[state],origin,ray);
            const V3 receiver=physical[state].point;
            const double projectedU=receiver[0]/(-receiver[2])*f*0.5+0.5,projectedV=receiver[1]/(-receiver[2])*f*0.5+0.5;
            if(clear[state].colour[baseIndex+3]!=1||tag[state].colour[baseIndex+3]!=1||observed[state]<=1e-5||ray[1]<=0||ray[2]>=-0.1||transmitted[1]>=0||physical[state].id!=2||!cameraVisible(boxes[state],physical[state])||info[state].state[0][baseIndex+3]<=0||receiver[1]<0.15||receiver[1]>11.5||std::abs(receiver[0])>15||projectedU<0.10||projectedU>0.90||projectedV<0.55||projectedV>0.95) sourceQualified=false;
            // mode3 observes the ORIGINAL reflectionTrace invocation's final
            // UV and weight. With NEAREST, provenance is exactly one texel.
            const double sourceU=source[state].state[0][baseIndex],sourceV=source[state].state[0][baseIndex+1];
            const int sourceX=std::clamp(int(std::floor(sourceU*size)),0,size-1),sourceY=std::clamp(int(std::floor(sourceV*size)),0,size-1);
            if(!std::isfinite(sourceU)||!std::isfinite(sourceV)||sourceU<=0||sourceU>=1||sourceV<=0.5||sourceV>=1||neutral[state].id[sourceY*size+sourceX]!=2||source[state].state[0][baseIndex+2]<=0||source[state].state[0][baseIndex+3]<=0) sourceQualified=false;
            for(int c=1;c<3;++c) if(std::abs(double(tag[state].colour[baseIndex+c])-clear[state].colour[baseIndex+c])>1e-6) sourceQualified=false;
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                const int k=((y&~1)+dy)*size+(x&~1)+dx;
                if(clear[state].colour[k*4+3]!=1||top[state].colour[k*4+3]!=1) sourceQualified=false;
                if(bathymetryEnabled&&(top[state].state[6][k*4+3]!=1.0f
                    ||std::abs(top[state].state[6][k*4]-(meanSurfaceY-localFloorY))>1e-6
                    ||std::abs(top[state].state[6][k*4+1])>1e-6||std::abs(top[state].state[6][k*4+2])>1e-6
                    ||std::abs(info[state].state[5][k*4]-meanSurfaceY)>1e-6
                    ||info[state].state[5][k*4+3]!=0.0f)) {
                    std::cout<<std::setprecision(14)<<"DEBUG-water-bathymetry constant-column qualification state="<<state
                             <<" quad="<<k%size<<","<<k/size<<" known="<<top[state].state[6][k*4+3]
                             <<" depth="<<top[state].state[6][k*4]<<" gradX="<<top[state].state[6][k*4+1]
                             <<" gradZ="<<top[state].state[6][k*4+2]<<" meanSurfaceY="<<info[state].state[5][k*4]
                             <<" unknownWeight="<<info[state].state[5][k*4+3]<<"\n";
                    throw std::runtime_error("Valid bathymetry fixture did not use the actual constant column in the original fragment invocation");
                }
                for(int c=0;c<3;++c) geometryDelta=std::max({geometryDelta,std::abs(double(top[state].state[0][k*4+c])-geometry.state[0][k*4+c]),std::abs(double(info[state].state[2][k*4+c])-transport.state[2][k*4+c])});
                if(bathymetryEnabled) for(int c=0;c<3;++c)
                    geometryDelta=std::max(geometryDelta,std::abs(double(top[state].state[2][k*4+c])-geometry.state[2][k*4+c]));
            }
            for(float v:clear[state].colour) peak=std::max(peak,std::abs(double(v)));
            for(float v:tag[state].colour) peak=std::max(peak,std::abs(double(v)));
        }
        if(neutrality>1e-6||repeatError>1e-6||geometryDelta>1e-6) throw std::runtime_error("Optical-depth neutrality/repeat/unchanged geometry control failed");
        controls<<x<<","<<y<<","<<sourceQualified<<","<<(sourceQualified?"qualified":"absent_or_occluded_reflection_source")<<","<<observed[0]<<","<<observed[1]<<","<<fresnel<<","<<neutrality<<","<<repeatError<<","<<geometryDelta<<"\n";
        if(!sourceQualified) continue;
        retained=pixel;qualified=true;oracleFresnel=fresnel;
        retainedBoxes=boxes;retainedInputs=neutral;
        // Conservative float32 subtraction/roundoff allowance, plus measured
        // repeat/observer error. This is not an aesthetic seam threshold.
        numericalBound=64*std::numeric_limits<float>::epsilon()*peak+8*(repeatError+neutrality);
        std::ofstream description(artifacts/"fixture.csv");description<<std::setprecision(14)<<"x,y,pointX,pointY,pointZ,boxLoX,boxLoZ,boxHiX,boxHiZ,highTop,lowTop,localFloor,phase,tagDelta,trueFacetFresnel,numericalBound\n"<<x<<","<<y<<","<<p[0]<<","<<p[1]<<","<<p[2]<<","<<high.lo[0]<<","<<high.lo[2]<<","<<high.hi[0]<<","<<high.hi[2]<<","<<high.hi[1]<<","<<low.hi[1]<<",-1.75,1.25,"<<sourceIncrement<<","<<fresnel<<","<<numericalBound<<"\n";
        std::ofstream states(artifacts/"actual-state.csv");states<<std::setprecision(14)<<"state,mode,attachment,x,y,z,w\n";
        std::ofstream receivers(artifacts/"physical-receivers.csv");receivers<<std::setprecision(14)<<"state,firstBox,axis,side,travel,x,y,z,cameraVisible,trueFacetGain,observedGain,actualSSR_U,actualSSR_V,edge,confidence,actualSSR_texelX,actualSSR_texelY,actualSSR_box\n";
        for(int state=0;state<2;++state) {
            const std::string name=state==0?"high":"low";
            save(artifacts/(name+"-neutral.rgba32f"),clear[state].colour);save(artifacts/(name+"-wall-tag.rgba32f"),tag[state].colour);
            save(artifacts/(name+"-depth.r32f"),neutral[state].depth);save(artifacts/(name+"-C4.rgba32f"),neutral[state].colour);
            for(int mode:{0,2,3}) {
                const auto& capture=mode==0?top[state]:(mode==2?info[state]:source[state]);
                for(int attachment=0;attachment<7;++attachment) {
                    states<<name<<","<<mode<<","<<attachment+1;for(int c=0;c<4;++c) states<<","<<capture.state[attachment][baseIndex+c];states<<"\n";
                    save(artifacts/(name+"-mode"+std::to_string(mode)+"-mrt"+std::to_string(attachment+1)+".rgba32f"),capture.state[attachment]);
                }
            }
            const Hit& hit=physical[state];receivers<<name<<","<<hit.id<<","<<hit.axis<<","<<hit.side<<","<<hit.travel;for(double c:hit.point) receivers<<","<<c;receivers<<",1,"<<fresnel<<","<<observed[state]/sourceIncrement;
            for(int c=0;c<4;++c) receivers<<","<<source[state].state[0][baseIndex+c];
            const int tx=std::clamp(int(std::floor(source[state].state[0][baseIndex]*size)),0,size-1),ty=std::clamp(int(std::floor(source[state].state[0][baseIndex+1]*size)),0,size-1);
            receivers<<","<<tx<<","<<ty<<","<<neutral[state].id[ty*size+tx]<<"\n";
            std::cout<<std::setprecision(12)<<"DEBUG-water-optical-depth "<<name<<" pixel="<<x<<","<<y<<" originalDepth="<<top[state].state[0][baseIndex+3]<<" opticalN="<<top[state].state[2][baseIndex]<<","<<top[state].state[2][baseIndex+1]<<","<<top[state].state[2][baseIndex+2]<<" sourceResponse="<<observed[state]<<" physicalFirstWall="<<hit.id<<" cameraVisible=1 geometryDelta="<<geometryDelta<<" observationC0error="<<neutrality<<" repeat="<<repeatError<<"\n";
        }
        break; // Never select a pixel based on whether it violates invariance.
    }
    controls.close();
    if(!qualified) throw std::runtime_error("INCONCLUSIVE water optical-depth fixture: no nonvacuous same-wall/local-geometry control; inspect candidate-controls.csv (not behavioral RED)");
    const double delta=std::abs(observed[0]-observed[1]);
    std::cout<<std::setprecision(12)<<"DEBUG-water-optical-depth fixed pixel="<<retained%size<<","<<retained/size<<" true-raster-facet Fresnel reference="<<oracleFresnel<<" pure-facet tagged delta="<<sourceIncrement*oracleFresnel<<" observedGainHigh="<<observed[0]/sourceIncrement<<" observedGainLow="<<observed[1]/sourceIncrement<<" sourceResponseDifference="<<delta<<" float/repeatBound="<<numericalBound<<"\n";
    std::cout<<"DEBUG-water-optical-depth absolute facet gain is a geometric reference, not a calibrated bump/SSR integration assertion; invariant remote-occluder response is the tested behavior. Sources/fields are saved; freeze fixture.csv pixel for GREEN.\n";
    if(enforceInvariant&&delta>numericalBound)
        throw std::runtime_error("Same water geometry/local depth and independently visible reflection source must not change source gain with an unrelated submerged original-view receiver");
    std::cout<<(enforceInvariant?"PASS":"DIAGNOSTIC")<<" production water main: qualified reflected-source remote-view-depth "<<(delta<=numericalBound?"invariance":"difference (no GREEN claim)")
             <<(bathymetryEnabled?" with actual valid bathymetry texture input":" without bathymetry texture input")<<"\n";
    if(!bathymetryEnabled) return;

    // Next vertical slice: change the REAL local floor and its column together.
    // No spectrum/wave calculation is copied: height and n are outputs of the
    // original production VS/main. A fixed raster pixel is not a fixed-XZ
    // vertex-amplitude sample, so no analytic amplitude-ratio oracle is used.
    std::array<Capture,2> positiveTop,positiveInfo;
    const float positiveDepths[2]={0.25f,meanSurfaceY-localFloorY};
    std::ofstream positive(artifacts/"positive-depth-controls.csv");
    positive<<std::setprecision(14)<<"state,columnDepth,physicalFloorY,actualMeanY,rasterVSheight,opticalNx,opticalNy,opticalNz,wallResponse,refractionTagDelta,reflectionTagDelta,fresnelGain,neutrality,repeat\n";
    double positiveRepeat=0,positiveNeutrality=0;
    for(int state=0;state<2;++state) {
        const std::string name=state==0?"positive-shallow":"positive-deep";
        auto boxes=baseBoxes;boxes[0].hi[1]=meanSurfaceY-positiveDepths[state];
        for(size_t i=0;i<bathymetry.size();i+=4) bathymetry[i]=positiveDepths[state];
        glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,fixture.textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,bathymetrySize,bathymetrySize,GL_RGBA,GL_FLOAT,bathymetry.data());
        save(artifacts/(name+"-bathymetry.rgba32f"),bathymetry);
        const auto input=scene(boxes,false,f,a,b),tagInput=scene(boxes,true,f,a,b);
        const auto clear=draw(input,-1),tag=draw(tagInput,-1),repeat=draw(tagInput,-1);
        positiveTop[state]=draw(input,0);positiveInfo[state]=draw(input,2);
        const auto source=draw(input,3),tagObserved=draw(tagInput,2);
        const auto& top=positiveTop[state];const auto& info=positiveInfo[state];
        const double repeatError=difference(tag.colour,repeat.colour);
        const double neutrality=std::max({difference(clear.colour,top.colour),difference(clear.colour,info.colour),difference(clear.colour,source.colour),difference(tag.colour,tagObserved.colour)});
        positiveRepeat=std::max(positiveRepeat,repeatError);positiveNeutrality=std::max(positiveNeutrality,neutrality);
        save(artifacts/(name+"-neutral.rgba32f"),clear.colour);save(artifacts/(name+"-wall-tag.rgba32f"),tag.colour);
        save(artifacts/(name+"-depth.r32f"),input.depth);save(artifacts/(name+"-C4.rgba32f"),input.colour);
        for(int attachment=0;attachment<7;++attachment) {
            save(artifacts/(name+"-mode0-mrt"+std::to_string(attachment+1)+".rgba32f"),top.state[attachment]);
            save(artifacts/(name+"-mode2-mrt"+std::to_string(attachment+1)+".rgba32f"),info.state[attachment]);
            save(artifacts/(name+"-mode3-mrt"+std::to_string(attachment+1)+".rgba32f"),source.state[attachment]);
        }
        const int index=retained*4,x=retained%size,y=retained/size;
        const V3 p=value(top.state[0],retained),n=value(top.state[2],retained);
        const V3 ray=value(info.state[1],retained),biased=value(info.state[0],retained);
        const Hit trueWall=firstHit(boxes,p,ray),wall=firstHit(boxes,biased,ray);
        const Hit bed=firstHit(boxes,p,value(top.state[3],retained));
        if(!trueWall.valid||!wall.valid||trueWall.id!=2||wall.id!=2||!cameraVisible(boxes,trueWall)||!cameraVisible(boxes,wall)
            ||trueWall.point[1]<=p[1]||wall.point[1]<=p[1]||!bed.valid||bed.id!=0||!cameraVisible(boxes,bed))
            throw std::runtime_error("INCONCLUSIVE physical shallow/deep input: true/biased reflected wall or transmitted floor not independently camera visible");
        auto untagged=[&](double u,double v) {
            if(!(u>0&&u<1&&v>0&&v<1)) return false;
            const int k=int(std::floor(v*size))*size+int(std::floor(u*size));
            return std::abs(double(tagInput.colour[k*4])-input.colour[k*4])<1e-7;
        };
        if(!untagged(top.state[5][index],top.state[5][index+1])||!untagged(top.state[5][index+2],top.state[5][index+3]))
            throw std::runtime_error("INCONCLUSIVE shallow/deep input: actual refraction or original proxy samples a tagged wall");
        const double u=source.state[0][index],v=source.state[0][index+1];
        if(!(u>0&&u<1&&v>0&&v<1)||source.state[0][index+2]<=0||source.state[0][index+3]<=0
            ||input.id[int(std::floor(v*size))*size+int(std::floor(u*size))]!=2)
            throw std::runtime_error("INCONCLUSIVE shallow/deep input: actual production SSR does not sample the visible wall");
        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
            const int k=((y&~1)+dy)*size+(x&~1)+dx;
            const V3 point=value(top.state[0],k);
            const Hit local=firstHit(boxes,point,{0,-1,0});
            if(clear.colour[k*4+3]!=1||tag.colour[k*4+3]!=1||!local.valid||local.id!=0||!cameraVisible(boxes,local)
                ||std::abs(local.point[1]-boxes[0].hi[1])>1e-6
                ||std::abs(info.state[5][k*4]-meanSurfaceY)>1e-6||info.state[5][k*4+3]!=0.0f
                ||std::abs((info.state[5][k*4]-local.point[1])-positiveDepths[state])>1e-6
                ||top.state[6][k*4+3]!=1||std::abs(top.state[6][k*4]-positiveDepths[state])>1e-6
                ||std::abs(top.state[6][k*4+1])>1e-6||std::abs(top.state[6][k*4+2])>1e-6)
                throw std::runtime_error("INCONCLUSIVE shallow/deep input: actual local bed, mean surface or used constant column is unqualified");
        }
        const double gain=facetFresnel(dot(normalized(n),normalized(add({0,0,0},p,-1))));
        const double response=double(tag.colour[index])-clear.colour[index];
        const double refractionDelta=double(tagObserved.state[3][index])-info.state[3][index];
        const double reflectionDelta=double(tagObserved.state[4][index])-info.state[4][index];
        if(neutrality>1e-6||repeatError>1e-6||response<=1e-5||reflectionDelta<=1e-5||std::abs(refractionDelta)>1e-6
            ||std::abs(response-gain*reflectionDelta)>numericalBound)
            throw std::runtime_error("Physical shallow/deep bathymetry must retain a nonvacuous reflection-only public source response with neutral observations");
        for(int c=1;c<3;++c) if(std::abs(double(tag.colour[index+c])-clear.colour[index+c])>1e-6)
            throw std::runtime_error("Red-only shallow/deep reflected source changed unrelated channels");
        positive<<name<<","<<positiveDepths[state]<<","<<boxes[0].hi[1]<<","<<info.state[5][index]<<","<<p[1];
        for(double component:n) positive<<","<<component;
        positive<<","<<response<<","<<refractionDelta<<","<<reflectionDelta<<","<<gain<<","<<neutrality<<","<<repeatError<<"\n";
    }
    double heightChange=0,normalChange=0;
    for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
        const int k=((retained/size&~1)+dy)*size+(retained%size&~1)+dx;
        heightChange=std::max(heightChange,std::abs(double(positiveTop[0].state[0][k*4+1])-positiveTop[1].state[0][k*4+1]));
        for(int c=0;c<3;++c) normalChange=std::max(normalChange,std::abs(double(positiveTop[0].state[2][k*4+c])-positiveTop[1].state[2][k*4+c]));
    }
    const double fieldBound=64*std::numeric_limits<float>::epsilon()+8*(positiveRepeat+positiveNeutrality);
    std::cout<<std::setprecision(12)<<"DEBUG-water-bathymetry physical shallow/deep: raster-interpolated VS height change="<<heightChange<<" optical normal change="<<normalChange<<" conservative float/repeat field bound="<<fieldBound<<"\n";
    if(heightChange<=fieldBound||normalChange<=fieldBound)
        throw std::runtime_error("Physical shallow versus deep bathymetry must affect BOTH actual VS geometry and the observed optical normal, not only one stage or an unused texture");
    std::cout<<"PASS production water main: independently qualified physical shallow/deep column changes actual VS geometry and optical normal, with positive reflection-only source responses\n";

    // One fallback slice: each unavailable input must decline known-column
    // optics, without deriving waves from the unrelated view-depth receiver.
    // Geometry/normal differences from KNOWN fine-wave optics are intentional;
    // only equivalent unavailable inputs and the remote-box pair are compared.
    auto setBathymetry=[&](bool ready,float validity,float surface,float originX,float originZ) {
        for(size_t i=0;i<bathymetry.size();i+=4) {
            bathymetry[i]=meanSurfaceY-localFloorY;bathymetry[i+1]=surface;bathymetry[i+2]=validity;bathymetry[i+3]=0;
        }
        glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,fixture.textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,bathymetrySize,bathymetrySize,GL_RGBA,GL_FLOAT,bathymetry.data());
        for(GLuint program:fixture.programs) {
            glUseProgram(program);glUniform1i(glGetUniformLocation(program,"aqualumenBathymetryReady"),ready?1:0);
            glUniform4f(glGetUniformLocation(program,"aqualumenBathymetryGrid"),originX,originZ,64,meanSurfaceY);
        }
    };
    struct FallbackCapture {std::array<Capture,2> top,info;std::array<double,2> response={};};
    std::ofstream fallbackEvidence(artifacts/"fallback-controls.csv");
    fallbackEvidence<<std::setprecision(14)<<"case,state,known,columnDepth,meanY,unknownWeight,sourceResponse,refractionTagDelta,reflectionTagDelta,fresnel,neutrality,repeat\n";
    auto fallback=[&](const std::string& name,double expectedSampledDepth,bool allVerticesUnknown) {
        FallbackCapture result;
        save(artifacts/(name+"-bathymetry.rgba32f"),bathymetry);
        for(int state=0;state<2;++state) {
            const auto tagInput=scene(retainedBoxes[state],true,f,a,b);
            const auto clear=draw(retainedInputs[state],-1),tag=draw(tagInput,-1),repeat=draw(tagInput,-1);
            result.top[state]=draw(retainedInputs[state],0);result.info[state]=draw(retainedInputs[state],2);
            const auto source=draw(retainedInputs[state],3),tagObserved=draw(tagInput,2);
            const auto& top=result.top[state];const auto& info=result.info[state];
            const double repeatError=difference(tag.colour,repeat.colour);
            const double neutrality=std::max({difference(clear.colour,top.colour),difference(clear.colour,info.colour),difference(clear.colour,source.colour),difference(tag.colour,tagObserved.colour)});
            const int index=retained*4,x=retained%size,y=retained/size;
            const V3 p=value(top.state[0],retained),n=value(top.state[2],retained),ray=value(info.state[1],retained);
            const Hit trueWall=firstHit(retainedBoxes[state],p,ray),wall=firstHit(retainedBoxes[state],value(info.state[0],retained),ray);
            const Hit transmitted=firstHit(retainedBoxes[state],p,value(top.state[3],retained));
            if(!trueWall.valid||!wall.valid||trueWall.id!=2||wall.id!=2||!cameraVisible(retainedBoxes[state],trueWall)
                ||!cameraVisible(retainedBoxes[state],wall)||trueWall.point[1]<=p[1]||wall.point[1]<=p[1]
                ||!transmitted.valid||transmitted.id==2)
                throw std::runtime_error("INCONCLUSIVE fallback fixture: true/biased reflection or untagged transmitted source is unqualified");
            auto untagged=[&](double u,double v) {
                if(!(u>0&&u<1&&v>0&&v<1)) return false;
                const int k=int(std::floor(v*size))*size+int(std::floor(u*size));
                return std::abs(double(tagInput.colour[k*4])-retainedInputs[state].colour[k*4])<1e-7;
            };
            if(!untagged(top.state[5][index],top.state[5][index+1])||!untagged(top.state[5][index+2],top.state[5][index+3]))
                throw std::runtime_error("INCONCLUSIVE fallback fixture: actual transmission/proxy acquires the reflected source tag");
            const double u=source.state[0][index],v=source.state[0][index+1];
            if(!(u>0&&u<1&&v>0&&v<1)||source.state[0][index+2]<=0||source.state[0][index+3]<=0
                ||retainedInputs[state].id[int(std::floor(v*size))*size+int(std::floor(u*size))]!=2)
                throw std::runtime_error("INCONCLUSIVE fallback fixture: actual SSR does not sample the independently visible wall");
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                const int k=((y&~1)+dy)*size+(x&~1)+dx;
                const V3 point=value(top.state[0],k);const Hit local=firstHit(retainedBoxes[state],point,{0,-1,0});
                if(clear.colour[k*4+3]!=1||tag.colour[k*4+3]!=1||!local.valid||local.id!=0
                    ||std::abs((meanSurfaceY-local.point[1])-(meanSurfaceY-localFloorY))>1e-6)
                    throw std::runtime_error("INCONCLUSIVE fallback fixture: actual local bed or raster coverage changed");
                const bool declined=allVerticesUnknown||k==retained;
                if(std::abs(top.state[6][k*4]-expectedSampledDepth)>1e-6
                    ||std::abs(top.state[6][k*4+1])>1e-6||std::abs(top.state[6][k*4+2])>1e-6
                    ||std::abs(info.state[5][k*4]-meanSurfaceY)>1e-6
                    ||(declined&&(top.state[6][k*4+3]!=0||info.state[5][k*4+3]<=0)))
                    throw std::runtime_error("Unavailable bathymetry must decline known-column optics in the original fragment invocation");
            }
            const double gain=facetFresnel(dot(normalized(n),normalized(add({0,0,0},p,-1))));
            result.response[state]=double(tag.colour[index])-clear.colour[index];
            const double refractionDelta=double(tagObserved.state[3][index])-info.state[3][index];
            const double reflectionDelta=double(tagObserved.state[4][index])-info.state[4][index];
            if(neutrality>1e-6||repeatError>1e-6||result.response[state]<=1e-5||reflectionDelta<=1e-5
                ||std::abs(refractionDelta)>1e-6||std::abs(result.response[state]-gain*reflectionDelta)>numericalBound)
                throw std::runtime_error("Fallback optics must retain a nonvacuous reflection-only public source with neutral observations");
            for(int c=1;c<3;++c) if(std::abs(double(tag.colour[index+c])-clear.colour[index+c])>1e-6)
                throw std::runtime_error("Red-only fallback reflected source changed unrelated channels");
            fallbackEvidence<<name<<","<<state<<","<<top.state[6][index+3]<<","<<top.state[6][index]<<","<<info.state[5][index]<<","<<info.state[5][index+3]<<","<<result.response[state]<<","<<refractionDelta<<","<<reflectionDelta<<","<<gain<<","<<neutrality<<","<<repeatError<<"\n";
            const std::string stem=name+(state==0?"-high":"-low");
            save(artifacts/(stem+"-neutral.rgba32f"),clear.colour);save(artifacts/(stem+"-wall-tag.rgba32f"),tag.colour);
            for(int attachment=0;attachment<7;++attachment) {
                save(artifacts/(stem+"-mode0-mrt"+std::to_string(attachment+1)+".rgba32f"),top.state[attachment]);
                save(artifacts/(stem+"-mode2-mrt"+std::to_string(attachment+1)+".rgba32f"),info.state[attachment]);
                save(artifacts/(stem+"-mode3-mrt"+std::to_string(attachment+1)+".rgba32f"),source.state[attachment]);
            }
        }
        double remoteFieldDifference=0;
        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
            const int k=((retained/size&~1)+dy)*size+(retained%size&~1)+dx;
            for(int c=0;c<3;++c) remoteFieldDifference=std::max({remoteFieldDifference,
                std::abs(double(result.top[0].state[0][k*4+c])-result.top[1].state[0][k*4+c]),
                std::abs(double(result.top[0].state[2][k*4+c])-result.top[1].state[2][k*4+c])});
        }
        const double responseDifference=std::abs(result.response[0]-result.response[1]);
        if(remoteFieldDifference>fieldBound||responseDifference>numericalBound)
            throw std::runtime_error("Unknown-column fallback must not derive wave geometry/optical normals or reflected gain from remote view depth");
        std::cout<<std::setprecision(12)<<"PASS production water main fallback "<<name<<": known0, remote geometry/normal delta="<<remoteFieldDifference<<" reflected-source response delta="<<responseDifference<<"; coarse-facet versus known fine-wave differences are intentional\n";
        return result;
    };
    struct MissingInput {const char* name;bool ready;float validity,surface,originX,originZ;};
    const MissingInput missing[]={
        {"fallback-ready0",false,1,meanSurfaceY,-32,-32},
        {"fallback-all-invalid",true,0,meanSurfaceY,-32,-32},
        {"fallback-out-of-map",true,1,meanSurfaceY,100,100},
        {"fallback-surface-mismatch",true,1,meanSurfaceY+0.5f,-32,-32}
    };
    FallbackCapture unavailableReference;
    for(int caseIndex=0;caseIndex<4;++caseIndex) {
        const auto& input=missing[caseIndex];setBathymetry(input.ready,input.validity,input.surface,input.originX,input.originZ);
        const auto result=fallback(input.name,0,true);
        if(caseIndex==0) unavailableReference=result;
        else for(int state=0;state<2;++state) {
            double fieldDifference=0;
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                const int k=((retained/size&~1)+dy)*size+(retained%size&~1)+dx;
                for(int c=0;c<3;++c) fieldDifference=std::max({fieldDifference,
                    std::abs(double(result.top[state].state[0][k*4+c])-unavailableReference.top[state].state[0][k*4+c]),
                    std::abs(double(result.top[state].state[2][k*4+c])-unavailableReference.top[state].state[2][k*4+c])});
            }
            if(fieldDifference>fieldBound||std::abs(result.response[state]-unavailableReference.response[state])>numericalBound)
                throw std::runtime_error("Equivalent unavailable bathymetry inputs must retain the same real coarse-facet fallback");
        }
    }

    // A local fragment column can be valid while a contributing mesh vertex
    // lacks data. Select a missing cell only by raw sampled column/vertex-weight
    // qualification, BEFORE testing Known or source gain. A broken Known gate
    // must fail the following behavior assertion, not hide as INCONCLUSIVE.
    // The public input's one-metre mesh/grid layout is known; no wave model is
    // duplicated to find candidate cells outside this raster quad's columns.
    using Cell=std::array<int,2>;
    std::vector<Cell> fragmentCells,vertexCells;
    auto append=[](std::vector<Cell>& cells,Cell cell) {
        if(cell[0]>=0&&cell[0]<bathymetrySize&&cell[1]>=0&&cell[1]<bathymetrySize
            &&std::find(cells.begin(),cells.end(),cell)==cells.end()) cells.push_back(cell);
    };
    for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
        const int k=((retained/size&~1)+dy)*size+(retained%size&~1)+dx;
        const V3 p=value(positiveTop[1].state[0],k);
        const int fx=int(std::floor(p[0]+32-0.5)),fz=int(std::floor(p[2]+32-0.5));
        for(int tz=0;tz<2;++tz) for(int tx=0;tx<2;++tx) append(fragmentCells,{fx+tx,fz+tz});
        const int meshX=int(std::floor(p[0])),meshZ=int(std::floor(p[2]));
        for(int vz=0;vz<2;++vz) for(int vx=0;vx<2;++vx) {
            const int bx=int(std::floor(meshX+vx+32-0.5)),bz=int(std::floor(meshZ+vz+32-0.5));
            for(int tz=0;tz<2;++tz) for(int tx=0;tx<2;++tx) append(vertexCells,{bx+tx,bz+tz});
        }
    }
    std::ofstream cornerSelection(artifacts/"unknown-corner-selection.csv");
    cornerSelection<<std::setprecision(14)<<"invalidTexelX,invalidTexelZ,selectedKnown,selectedColumnDepth,unknownWeight,wholeQuadColumnsValid,qualifiedBeforeSourceAssertion\n";
    bool cornerQualified=false;
    for(const Cell& cell:vertexCells) {
        if(std::find(fragmentCells.begin(),fragmentCells.end(),cell)!=fragmentCells.end()) continue;
        setBathymetry(true,1,meanSurfaceY,-32,-32);
        bathymetry[(cell[1]*bathymetrySize+cell[0])*4+2]=0;
        glActiveTexture(GL_TEXTURE6);glBindTexture(GL_TEXTURE_2D,fixture.textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,bathymetrySize,bathymetrySize,GL_RGBA,GL_FLOAT,bathymetry.data());
        const auto column=draw(retainedInputs[0],0),mean=draw(retainedInputs[0],2);
        const int index=retained*4;
        bool quadColumns=true;
        for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
            const int k=((retained/size&~1)+dy)*size+(retained%size&~1)+dx;
            quadColumns=quadColumns&&column.colour[k*4+3]==1
                &&std::abs(column.state[6][k*4]-(meanSurfaceY-localFloorY))<=1e-6
                &&std::abs(column.state[6][k*4+1])<=1e-6&&std::abs(column.state[6][k*4+2])<=1e-6;
        }
        const bool selected=quadColumns&&mean.state[5][index+3]>0;
        cornerSelection<<cell[0]<<","<<cell[1]<<","<<column.state[6][index+3]<<","<<column.state[6][index]<<","<<mean.state[5][index+3]<<","<<quadColumns<<","<<selected<<"\n";
        if(!selected) continue;
        fallback("fallback-unknown-corner-"+std::to_string(cell[0])+"-"+std::to_string(cell[1]),meanSurfaceY-localFloorY,false);
        cornerQualified=true;break;
    }
    if(!cornerQualified)
        throw std::runtime_error("INCONCLUSIVE primitive-boundary input: no contributing unknown vertex with a valid actual fragment column; no missing-vertex GREEN claim");
}

#endif
