#ifndef AQUALUMEN_UNDERWATER_BACKFACE_PROBE_H
#define AQUALUMEN_UNDERWATER_BACKFACE_PROBE_H

// ONE regression: the two windings of the SAME confirmed top interface must
// have the same displaced geometry and eye-oriented optical normal. Native
// GL supplies the +/-Y normals observed in the real Sodium/Iris vertex path;
// this does not emulate Sodium encoding, live world meshing, or natural-rim SSR.
// The retained same-top slice runs first. Separate true-bottom/unknown-negative
// controls then reject invented displacement, column knowledge or promotion.
#include "underwater-angular-probe.h"

namespace aqualumenUnderwaterBackfaceDetail {
constexpr int size=65,centre=32;
constexpr float meanY=3.25f,columnDepth=4.0f,phase=120.0f;
using aqualumenWaterRadianceDetail::arithmeticBound;
using aqualumenWaterRadianceDetail::textFile;
using aqualumenWaterRadianceDetail::rawFile;
inline void qualify(bool value,const std::string& message) {
    if(!value)throw std::runtime_error("INCONCLUSIVE underwater-backface: "+message);
}
inline std::string options(std::string source) {
    for(const auto& item:std::array<std::pair<std::string,std::string>,2>{{{"WAVE_HEIGHT","0.12"},{"SHORE_FOAM","0.0"}}}) {
        const std::string anchor="#define "+item.first+" ";const auto at=source.find(anchor);
        qualify(at!=std::string::npos&&source.find(anchor,at+anchor.size())==std::string::npos,"public option absent/ambiguous");
        source.replace(at,source.find('\n',at)-at,anchor+item.second);
    }
    return source;
}
struct Capture {std::array<std::vector<float>,6> image;std::vector<float> vertices;};
inline double difference(const std::vector<float>& a,const std::vector<float>& b) {
    qualify(a.size()==b.size(),"readback sizes differ");double result=0;
    for(size_t i=0;i<a.size();++i)result=std::max(result,std::abs(double(a[i])-b[i]));
    return result;
}
struct Feedback {
    GLuint buffer=0;GLint previous=0,indexed=0;
    Feedback(){glGetIntegerv(GL_TRANSFORM_FEEDBACK_BUFFER_BINDING,&previous);glGetIntegeri_v(GL_TRANSFORM_FEEDBACK_BUFFER_BINDING,0,&indexed);glGenBuffers(1,&buffer);}
    ~Feedback(){glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,GLuint(indexed));glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,GLuint(previous));glDeleteBuffers(1,&buffer);}
};
}

inline void productionUnderwaterBackfaceProbe(const std::filesystem::path& root,const std::filesystem::path& artifacts) {
    using namespace aqualumenUnderwaterBackfaceDetail;
    using aqualumenUnderwaterAngularDetail::M4;
    const auto* renderer=glGetString(GL_RENDERER);
    qualify(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");
    GLint buffers=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&buffers);qualify(buffers>=6,"six MRT outputs required");
    qualify(glGetError()==GL_NO_ERROR,"entered with GL error");
    qualify(!artifacts.empty()&&!std::filesystem::exists(artifacts),"NEW artifact directory required; preserve old evidence");
    std::filesystem::create_directories(artifacts);
    const auto originalVS=expand(root/"gbuffers_water.vsh",root,0),originalFS=expand(root/"gbuffers_water.fsh",root,0);
    const auto vs=options(originalVS),fs=options(originalFS);
    std::string observed=fs;
    const std::string prefix="\n// DEBUG-underwater-backface STORE begin\n",suffix="\n// DEBUG-underwater-backface STORE end\n";
    const auto store=[&](const std::string& anchor,const std::string& value) {
        const auto at=observed.find(anchor);qualify(at!=std::string::npos&&observed.find(anchor,at+anchor.size())==std::string::npos,"STORE anchor absent/ambiguous");
        observed.insert(at+anchor.size(),prefix+value+suffix);
    };
    // STORE an already evaluated raw helper result BEFORE the contributing-VS
    // gate; no second helper call, derivative, normal calculation or branch.
    store("    bool localColumnKnown=localWaterColumn(worldPosition.xz,waterMeanSurfaceY,localColumn);",
        "    gl_FragData[3]=vec4(localColumn,float(localColumnKnown));");
    store("    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);",
        "    gl_FragData[1]=vec4(worldPosition,waterMeanSurfaceY);\n"
        "    gl_FragData[2]=vec4(n,fresnel);\n"
        "    gl_FragData[4]=vec4(worldNormal,waterUnknownWeight);\n"
        "    gl_FragData[5]=vec4(float(localColumnKnown),float(upperSurface),float(underwater),1.0);");
    auto recovered=observed;for(auto at=recovered.find(prefix);at!=std::string::npos;at=recovered.find(prefix)) {
        const auto end=recovered.find(suffix,at);qualify(end!=std::string::npos,"unterminated STORE");recovered.erase(at,end+suffix.size()-at);
    }
    qualify(recovered==fs,"STORE removal does not recover byte-identical original option-main");
    textFile(artifacts/"shipping-expanded.vsh",originalVS);textFile(artifacts/"shipping-expanded.fsh",originalFS);
    textFile(artifacts/"production-options.vsh",vs);textFile(artifacts/"production-options.fsh",fs);textFile(artifacts/"passive-stores.fsh",observed);
    aqualumenWaterOpticalDepthDetail::Fixture fixture;aqualumenWaterRadianceDetail::SamplerState samplers;
    fixture.programs[0]=link(vs,fs,"backface-original-main","mc_Entity");
    fixture.programs[1]=link(vs,observed,"backface-store-only-main","mc_Entity");
    // Transform feedback exposes ORIGINAL VS outputs. Retained attributes and
    // every uniform are assigned AFTER relink; raster C0 neutrality is checked.
    const char* varying[]={"worldPosition","worldNormal","waterMeanSurfaceY","waterUnknownWeight"};
    for(GLuint program:fixture.programs){glTransformFeedbackVaryings(program,4,varying,GL_INTERLEAVED_ATTRIBS);glLinkProgram(program);
        GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);qualify(linked==GL_TRUE,"original VS feedback relink failed");}
    Feedback feedback;
    const auto& textures=fixture.textures;
    for(GLenum option:{GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS})glPixelStorei(option,0);
    glPixelStorei(GL_PACK_SWAP_BYTES,GL_FALSE);glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
    for(GLenum option:{GL_RED_SCALE,GL_GREEN_SCALE,GL_BLUE_SCALE,GL_ALPHA_SCALE,GL_DEPTH_SCALE})glPixelTransferf(option,1);
    for(GLenum option:{GL_RED_BIAS,GL_GREEN_BIAS,GL_BLUE_BIAS,GL_ALPHA_BIAS,GL_DEPTH_BIAS})glPixelTransferf(option,0);
    glPixelTransferi(GL_MAP_COLOR,GL_FALSE);
    const auto allocate=[&](int slot,GLenum format,int w,int h,GLenum channel,const float* data){
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        for(GLenum p:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,p,GL_NEAREST);
        for(GLenum p:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,p,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,format,w,h,0,channel,GL_FLOAT,data);
    };
    const int count=size*size;const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadow=0;
    std::vector<float> colour(count*4,0),depth(count,1),sky(64*32*4,0),bathymetry(64*64*4,0);
    for(int p=0;p<count;++p)colour[p*4+3]=1;
    for(int y=0;y<32;++y)for(int x=0;x<64;++x){const int p=(y*64+x)*4;sky[p+3]=1;for(int c=0;c<3;++c)sky[p+c]=y<31?.04f:0;}
    for(size_t p=0;p<bathymetry.size();p+=4){bathymetry[p]=columnDepth;bathymetry[p+1]=meanY;bathymetry[p+2]=1;}
    allocate(0,GL_RGBA32F,1,1,GL_RGBA,white);allocate(1,GL_RGBA32F,size,size,GL_RGBA,colour.data());
    allocate(2,GL_RGBA16F,64,32,GL_RGBA,sky.data());allocate(3,GL_DEPTH_COMPONENT32F,size,size,GL_DEPTH_COMPONENT,depth.data());
    allocate(4,GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
    allocate(5,GL_RGBA16F,1,1,GL_RGBA,black);allocate(7,GL_RGBA16F,64,32,GL_RGBA,sky.data());allocate(15,GL_RGBA32F,64,64,GL_RGBA,bathymetry.data());
    // Real uploaded bathymetry, not a relabelled null-map or duplicated wave.
    GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
    glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
    qualify(format==GL_RGBA32F&&w==64&&h==64,"actual bathymetry storage differs");
    auto actual=bathymetry;std::fill(actual.begin(),actual.end(),std::numeric_limits<float>::quiet_NaN());glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());
    for(size_t i=0;i<actual.size();++i)qualify(std::isfinite(actual[i])&&actual[i]==bathymetry[i],"actual bathymetry readback differs");
    rawFile(artifacts/"actual-bathymetry.rgba32f",actual);
    std::array<GLenum,6> draws={};glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);
    for(int i=0;i<6;++i){allocate(i==0?6:7+i,GL_RGBA32F,size,size,GL_RGBA,nullptr);draws[i]=GL_COLOR_ATTACHMENT0+i;
        glFramebufferTexture2D(GL_FRAMEBUFFER,draws[i],GL_TEXTURE_2D,textures[i==0?6:7+i],0);}
    glDrawBuffers(6,draws.data());qualify(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"separate-output framebuffer incomplete");
    const float focal=float(1/std::tan(30*aqualumenUnderwaterAngularDetail::pi/180)),near=.1f,far=128;
    const float a=-(far+near)/(far-near),b=-2*far*near/(far-near);
    const M4 projection={focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0};
    const M4 inverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,1/b,0,0,-1,a/b};
    const M4 view={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    const M4 inverseView={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const M4 downView={1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1};
    const M4 downInverseView={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
    for(GLuint program:fixture.programs){glUseProgram(program);
        const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
        for(int unit=0;unit<8;++unit){const GLint location=glGetUniformLocation(program,names[unit]);qualify(location>=0,"required actual sampler inactive");glUniform1i(location,unit);}
        for(const auto& item:std::array<std::pair<const char*,M4>,6>{{{"gbufferProjection",projection},{"gbufferProjectionInverse",inverseProjection},{"gbufferModelView",view},
            {"gbufferModelViewInverse",inverseView},{"shadowProjection",aqualumenWaterRadianceDetail::identity},{"shadowModelView",aqualumenWaterRadianceDetail::identity}}})
            glUniformMatrix4fv(glGetUniformLocation(program,item.first),1,GL_FALSE,item.second.data());
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,63,0);glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,-1);
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,0,-1);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);
        glUniform1f(glGetUniformLocation(program,"far"),128);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),phase);
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),1);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
        glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,meanY);
        const GLint ready=glGetUniformLocation(program,"aqualumenBathymetryReady"),grid=glGetUniformLocation(program,"aqualumenBathymetryGrid");
        qualify(ready>=0&&grid>=0,"active bathymetry contract unavailable");glUniform1i(ready,1);glUniform4f(grid,-32,-32,64,meanY);
        glUniform1f(glGetUniformLocation(program,"rainStrength"),0);glUniform1f(glGetUniformLocation(program,"wetness"),0);
        glUniform1i(glGetUniformLocation(program,"worldTime"),6000);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
    }
    for(GLenum cap:{GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,
        GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE})glDisable(cap);
    glDepthMask(GL_FALSE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glViewport(0,0,size,size);
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view.data());
    glDisableVertexAttribArray(10);glVertexAttrib4f(10,10000,0,0,0);glColor4f(1,1,1,1);
    glMultiTexCoord2f(GL_TEXTURE0,.5f,.5f);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    const std::array<std::array<float,3>,4> vertices={{{-.5f,meanY,-.5f},{-.5f,meanY,.5f},{.5f,meanY,.5f},{.5f,meanY,-.5f}}};
    const auto draw=[&](bool back,bool observe,const std::string& label,float planeY=meanY,bool lookingDown=false,float nearPlane=.1f){
        const GLuint program=fixture.programs[observe?1:0];glUseProgram(program);
        // Thin-fluid tests place the eye inside the supplied column. A closer
        // near plane is an explicit fixture input, not a production edit.
        const float pa=-(far+nearPlane)/(far-nearPlane),pb=-2*far*nearPlane/(far-nearPlane);
        const M4 currentProjection={focal,0,0,0,0,focal,0,0,0,0,pa,-1,0,0,pb,0};
        const M4 currentInverseProjection={1/focal,0,0,0,0,1/focal,0,0,0,0,1/pb,0,0,-1,pa/pb};
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjection"),1,GL_FALSE,currentProjection.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferProjectionInverse"),1,GL_FALSE,currentInverseProjection.data());
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(currentProjection.data());
        const M4& currentView=lookingDown?downView:view;
        const M4& currentInverse=lookingDown?downInverseView:inverseView;
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelView"),1,GL_FALSE,currentView.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,currentInverse.data());
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,lookingDown?1.0f:-1.0f);
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,0,lookingDown?1.0f:-1.0f);
        glMatrixMode(GL_MODELVIEW);glLoadMatrixf(currentView.data());
        auto currentVertices=vertices;for(auto& p:currentVertices)p[1]=planeY;
        for(int unit=0;unit<8;++unit){glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,unit==6?textures[15]:textures[unit]);}
        GLint bound=0,unit=-1,sampler=0;glGetUniformiv(program,glGetUniformLocation(program,"aqualumenBathymetry"),&unit);
        glActiveTexture(GL_TEXTURE0+6);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);
        qualify(unit==6&&GLuint(bound)==textures[15]&&sampler==0,"actual bathymetry sampler binding differs");
        glNormal3f(0,back?-1.0f:1.0f,0);Capture result;result.vertices.assign(4*8,std::numeric_limits<float>::quiet_NaN());
        glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,feedback.buffer);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,GLsizeiptr(result.vertices.size()*sizeof(float)),nullptr,GL_STREAM_READ);
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,feedback.buffer);glEnable(GL_RASTERIZER_DISCARD);
        glBeginTransformFeedback(GL_POINTS);glBegin(GL_POINTS);for(const auto& p:currentVertices)glVertex3fv(p.data());glEnd();glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);
        glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,GLsizeiptr(result.vertices.size()*sizeof(float)),result.vertices.data());
        for(float value:result.vertices)qualify(std::isfinite(value),"nonfinite actual original-VS output");
        rawFile(artifacts/(label+"-VS.f32"),result.vertices);
        glDrawBuffers(6,draws.data());const float zero[4]={};for(int i=0;i<6;++i)glClearBufferfv(GL_COLOR,i,zero);
        glDrawBuffers(observe?6:1,draws.data());const int front[6]={0,1,2,0,2,3},reverse[6]={0,3,2,0,2,1};
        glBegin(GL_TRIANGLES);for(int i:back?reverse:front)glVertex3fv(currentVertices[i].data());glEnd();
        for(int i=0;i<(observe?6:1);++i){result.image[i].assign(count*4,std::numeric_limits<float>::quiet_NaN());glReadBuffer(draws[i]);
            glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.image[i].data());for(float value:result.image[i])qualify(std::isfinite(value),"nonfinite original FS output");
            rawFile(artifacts/(label+"-C"+std::to_string(i)+".rgba32f"),result.image[i]);}
        qualify(glGetError()==GL_NO_ERROR,"GL error in original VS/FS draw/readback");return result;
    };
    const auto front=draw(false,false,"front-original"),frontRepeat=draw(false,false,"front-repeat"),frontObserved=draw(false,true,"front-store");
    const auto back=draw(true,false,"back-original"),backRepeat=draw(true,false,"back-repeat"),backObserved=draw(true,true,"back-store");
    const double observer=std::max(difference(front.image[0],frontObserved.image[0]),difference(back.image[0],backObserved.image[0]));
    const double repeat=std::max(difference(front.image[0],frontRepeat.image[0]),difference(back.image[0],backRepeat.image[0]));
    const double fieldBound=arithmeticBound(1+meanY,512);qualify(observer<=fieldBound&&repeat<=fieldBound,"whole-C0 STORE neutrality/repeat failed");
    double displacementPositive=0,vertexDifference=0;
    for(int i=0;i<4;++i){const int p=i*8;
        for(int c:{0,2}){qualify(front.vertices[p+c]==vertices[i][c]&&back.vertices[p+c]==vertices[i][c],"original VS changed horizontal positions");}
        qualify(front.vertices[p+6]==meanY&&back.vertices[p+6]==meanY,"actual undisplaced mean does not match supplied column");
        qualify(front.vertices[p+4]==1&&back.vertices[p+4]==-1,"normal inputs do not represent opposite top windings");
        qualify(front.vertices[p+7]==0,"positive front VS did not use known column");
        displacementPositive=std::max(displacementPositive,std::abs(double(front.vertices[p+1])-meanY));
        for(int c=0;c<3;++c)vertexDifference=std::max(vertexDifference,std::abs(double(front.vertices[p+c])-back.vertices[p+c]));
    }
    qualify(displacementPositive>8*fieldBound,"fixed nonzero-wave input is not sensitive to actual VS displacement");
    const int pixel=(centre*size+centre)*4;double normalDifference=0,positionDifference=0;
    for(const Capture* capture:{&frontObserved,&backObserved}){
        qualify(capture->image[0][pixel+3]==1&&capture->image[5][pixel+3]==1&&capture->image[5][pixel+2]==1,"fixed centre is not a rendered underwater water pixel");
        qualify(capture->image[3][pixel+3]==1&&std::abs(capture->image[3][pixel]-columnDepth)<=fieldBound,"raw FS helper did not see supplied known depth");
        double length=0;for(int c=0;c<3;++c)length+=double(capture->image[2][pixel+c])*capture->image[2][pixel+c];
        qualify(std::abs(length-1)<=fieldBound*4&&capture->image[2][pixel+1]<-.9,"optical normal is not unit/eye-facing below top interface");
    }
    qualify(frontObserved.image[5][pixel]==1&&frontObserved.image[4][pixel+3]==0,"front FS known-column positive control failed");
    qualify(frontObserved.image[0][pixel]+frontObserved.image[0][pixel+1]+frontObserved.image[0][pixel+2]>8*fieldBound,"whole-C0 neutrality lacks a positive radiance source");
    for(int c=0;c<3;++c){normalDifference=std::max(normalDifference,std::abs(double(frontObserved.image[2][pixel+c])-backObserved.image[2][pixel+c]));
        positionDifference=std::max(positionDifference,std::abs(double(frontObserved.image[1][pixel+c])-backObserved.image[1][pixel+c]));}
    const bool failed=vertexDifference>fieldBound||positionDifference>fieldBound||normalDifference>fieldBound
        ||backObserved.image[5][pixel]!=1||backObserved.image[4][pixel+3]!=0;
    std::ostringstream summary;summary<<std::setprecision(14)<<"scope=ONE confirmed same-plane top +/-normal/winding regression; not natural-rim acceptance\n"
        <<"size=65x65 pixel=32,32 meanY="<<meanY<<" meanDepth="<<columnDepth<<" phase="<<phase<<" WAVE_HEIGHT=.12 SHORE_FOAM=0\n"
        <<"actualInputRGBA32FExact=1 rawKnownFront=1 rawKnownBack=1\nwholeC0ObserverMax="<<observer<<" wholeC0RepeatMax="<<repeat
        <<"\npositiveVSDisplacement="<<displacementPositive<<" vertexPositionDifference="<<vertexDifference<<" fragmentPositionDifference="<<positionDifference
        <<" opticalNormalDifference="<<normalDifference<<" declaredBinary32Gamma512Bound="<<fieldBound
        <<"\nbackUnknownWeight="<<backObserved.image[4][pixel+3]<<" backFinalKnown="<<backObserved.image[5][pixel]<<" backUpperSurface="<<backObserved.image[5][pixel+1]
        <<"\nresult="<<(failed?"RED":"GREEN")<<"\nSeparate bottom/unknown controls follow only after this retained first slice succeeds.\n";
    textFile(artifacts/"SUMMARY.txt",summary.str());std::cout<<summary.str();
    if(failed)throw std::runtime_error("BEHAVIOR RED underwater-backface: same confirmed top has winding-dependent geometry/normal/known state");

    // Two bounded negatives, not a search over shader responses. The bottom is
    // exactly the confirmed column's lower boundary: 3.25 - 4 = -.75 metres.
    // The eye at relativeY0 is in that column; a rigid DOWN view makes the
    // negative face visible at the same fixed centre, without moving the map.
    // The unknown top retains the original upward view/mean height and changes
    // ONLY actual map validity. Neither unknown/bottom may be forced known.
    std::ostringstream negative;negative<<std::setprecision(14)
        <<"scope=two independent bounded negative inputs after retained known-top positive; not live Sodium mesh or natural-rim acceptance\n"
        <<"mapSurfaceY="<<meanY<<" mapDepth="<<columnDepth<<" bottomY="<<(meanY-columnDepth)
        <<" pixel=32,32 matrix=rigid-up-or-down eyeRelativeY=0 WAVE_HEIGHT=.12 phase=120\n";
    bool negativeFailed=false;
    for(int control=0;control<2;++control){
        const bool bottom=control==0;const std::string name=bottom?"true-bottom":"unknown-backtop";
        const float planeY=bottom?meanY-columnDepth:meanY,validity=bottom?1.0f:0.0f;
        auto supplied=bathymetry;for(size_t p=0;p<supplied.size();p+=4)supplied[p+2]=validity;
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,64,GL_RGBA,GL_FLOAT,supplied.data());
        std::vector<float> actualNegative(supplied.size(),std::numeric_limits<float>::quiet_NaN());
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actualNegative.data());
        for(size_t i=0;i<supplied.size();++i)qualify(std::isfinite(actualNegative[i])&&actualNegative[i]==supplied[i],"negative actual map does not equal frozen supplied input");
        rawFile(artifacts/(name+"-actual-bathymetry.rgba32f"),actualNegative);
        qualify(bottom?std::abs(meanY-planeY)>.12f:validity==0,"negative input does not independently reject known top classification");
        const auto original=draw(true,false,name+"-original",planeY,bottom),
            repeated=draw(true,false,name+"-repeat",planeY,bottom),
            observation=draw(true,true,name+"-store",planeY,bottom);
        const double observerDifference=difference(original.image[0],observation.image[0]),repeatDifference=difference(original.image[0],repeated.image[0]);
        qualify(observerDifference<=fieldBound&&repeatDifference<=fieldBound,"negative whole-C0 STORE neutrality/repeat failed");
        qualify(difference(original.vertices,observation.vertices)<=fieldBound&&difference(original.vertices,repeated.vertices)<=fieldBound,
            "negative original-VS STORE neutrality/repeat failed");
        qualify(observation.image[0][pixel+3]==1&&observation.image[5][pixel+3]==1&&observation.image[5][pixel+2]==1,
            "fixed negative centre is not a rendered underwater water face");
        double geometryDelta=0,vertexWeightDelta=0;
        for(int i=0;i<4;++i){const int p=i*8;
            qualify(original.vertices[p+3]==0&&original.vertices[p+4]==-1&&original.vertices[p+5]==0,
                "negative VS inputs do not represent a -Y horizontal fluid face");
            qualify(original.vertices[p+6]==planeY,"negative undisplaced mean input differs");
            for(int c=0;c<3;++c){const double expected=c==1?planeY:vertices[i][c];geometryDelta=std::max(geometryDelta,std::abs(double(original.vertices[p+c])-expected));}
            vertexWeightDelta=std::max(vertexWeightDelta,std::abs(double(original.vertices[p+7])-1.0));
        }
        // Constant one can interpolate to 1 +/- ULP in the FS (observed live
        // .99999994); VS weight=1 is exact. gamma8 is the declared binary32
        // few-operation interpolation allowance, NOT an epsilon known gate.
        const double interpolationBound=arithmeticBound(1,8);
        const double fragmentWeightDelta=std::abs(double(observation.image[4][pixel+3])-1);
        const double expectedNormalY=bottom?1.0:-1.0;
        double normalError=0;for(int c=0;c<3;++c)normalError=std::max(normalError,std::abs(double(observation.image[2][pixel+c])-(c==1?expectedNormalY:0.0)));
        const bool thisFailed=geometryDelta>fieldBound||vertexWeightDelta!=0||fragmentWeightDelta>interpolationBound
            ||observation.image[3][pixel+3]!=0||observation.image[5][pixel]!=0||observation.image[5][pixel+1]!=0
            ||std::abs(double(observation.image[1][pixel+1])-planeY)>fieldBound||normalError>fieldBound;
        negativeFailed=negativeFailed||thisFailed;
        negative<<name<<" actualInputRGBA32FExact=1 validity="<<validity<<" planeY="<<planeY
            <<" observerMax="<<observerDifference<<" repeatMax="<<repeatDifference
            <<" originalVSGeometryDelta="<<geometryDelta<<" originalVSWeightDelta="<<vertexWeightDelta
            <<" fragmentWeight="<<observation.image[4][pixel+3]<<" fragmentWeightGamma8Bound="<<interpolationBound
            <<" rawKnown="<<observation.image[3][pixel+3]<<" finalKnown="<<observation.image[5][pixel]
            <<" upperSurface="<<observation.image[5][pixel+1]<<" eyeOrientedNormalError="<<normalError
            <<" result="<<(thisFailed?"RED":"GREEN")<<"\n";
    }
    negative<<"declaredGeometryBinary32Gamma512Bound="<<fieldBound<<"\nresult="<<(negativeFailed?"RED":"GREEN")<<"\n";
    textFile(artifacts/"NEGATIVE-SUMMARY.txt",negative.str());std::cout<<negative.str();
    if(negativeFailed)throw std::runtime_error("BEHAVIOR RED underwater-backface: true bottom/unknown negative invented top displacement or column knowledge");

    // Tracer bullet for the height-tolerance alias: a cached valid 1/9 column
    // and a Sodium bottom at block+.001. This is an uploaded-interface safety
    // test, NOT proof that a live stone floor emits this occluded bottom.
    const float blockY=64.0f,cameraY=blockY+.05f;
    const float thinDepth=1.0f/9.0f,thinSurface=(blockY+thinDepth)-cameraY;
    const float thinBottom=(blockY+.001f)-cameraY;
    qualify(thinBottom<-.01f&&thinSurface>0&&std::abs(thinSurface-thinBottom)<.12f,
        "thin eye/near/height-tolerance inputs do not isolate the alias");
    auto thinMap=bathymetry;for(size_t p=0;p<thinMap.size();p+=4){thinMap[p]=thinDepth;thinMap[p+1]=thinSurface;thinMap[p+2]=1;}
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[15]);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,64,GL_RGBA,GL_FLOAT,thinMap.data());
    std::vector<float> thinActual(thinMap.size(),std::numeric_limits<float>::quiet_NaN());
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,thinActual.data());
    for(size_t i=0;i<thinMap.size();++i)qualify(std::isfinite(thinActual[i])&&thinActual[i]==thinMap[i],"thin actual map differs from supplied input");
    rawFile(artifacts/"thin-bottom-actual-bathymetry.rgba32f",thinActual);
    for(GLuint program:fixture.programs){glUseProgram(program);glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,cameraY,0);}
    const auto thinOriginal=draw(true,false,"thin-bottom-original",thinBottom,true,.01f),
        thinRepeated=draw(true,false,"thin-bottom-repeat",thinBottom,true,.01f),
        thinObserved=draw(true,true,"thin-bottom-store",thinBottom,true,.01f);
    const double thinObserver=difference(thinOriginal.image[0],thinObserved.image[0]),thinRepeat=difference(thinOriginal.image[0],thinRepeated.image[0]);
    qualify(thinObserver<=fieldBound&&thinRepeat<=fieldBound,"thin whole-C0 STORE neutrality/repeat failed");
    qualify(difference(thinOriginal.vertices,thinObserved.vertices)<=fieldBound&&difference(thinOriginal.vertices,thinRepeated.vertices)<=fieldBound,
        "thin original-VS STORE neutrality/repeat failed");
    qualify(thinObserved.image[0][pixel+3]==1&&thinObserved.image[5][pixel+3]==1&&thinObserved.image[5][pixel+2]==1,
        "fixed thin centre is not rendered underwater water");
    qualify(thinObserved.image[3][pixel+3]==1,"thin raw helper is not sensitive to the height-tolerance alias");
    double thinGeometryDelta=0,thinVertexWeightDelta=0,thinNormalError=0;
    for(int i=0;i<4;++i){const int p=i*8;
        qualify(thinOriginal.vertices[p+4]==-1&&thinOriginal.vertices[p+6]==thinBottom,"thin original VS input is not the pinned negative bottom");
        for(int c=0;c<3;++c){const double expected=c==1?thinBottom:vertices[i][c];thinGeometryDelta=std::max(thinGeometryDelta,std::abs(double(thinOriginal.vertices[p+c])-expected));}
        thinVertexWeightDelta=std::max(thinVertexWeightDelta,std::abs(double(thinOriginal.vertices[p+7])-1));
    }
    for(int c=0;c<3;++c)thinNormalError=std::max(thinNormalError,std::abs(double(thinObserved.image[2][pixel+c])-(c==1?1.0:0.0)));
    const double thinFragmentWeightDelta=std::abs(double(thinObserved.image[4][pixel+3])-1);
    const bool thinFailed=thinGeometryDelta>fieldBound||thinVertexWeightDelta!=0||thinFragmentWeightDelta>arithmeticBound(1,8)
        ||thinObserved.image[5][pixel]!=0||thinObserved.image[5][pixel+1]!=0||thinNormalError>fieldBound
        ||std::abs(double(thinObserved.image[1][pixel+1])-thinBottom)>fieldBound;
    std::ostringstream thinSummary;thinSummary<<std::setprecision(14)
        <<"scope=ONE supplied thin-column bottom alias; not live natural failure or visual acceptance\n"
        <<"blockY="<<blockY<<" cameraY="<<cameraY<<" columnDepth="<<thinDepth<<" relativeSurfaceY="<<thinSurface<<" relativeBottomY="<<thinBottom
        <<" inputBottomFraction="<<((thinBottom+cameraY)-std::floor(thinBottom+cameraY))<<" near=.01\n"
        <<"actualInputRGBA32FExact=1 observerMax="<<thinObserver<<" repeatMax="<<thinRepeat
        <<" originalVSGeometryDelta="<<thinGeometryDelta<<" originalVSWeightDelta="<<thinVertexWeightDelta
        <<" fragmentWeight="<<thinObserved.image[4][pixel+3]<<" rawKnown="<<thinObserved.image[3][pixel+3]
        <<" finalKnown="<<thinObserved.image[5][pixel]<<" upperSurface="<<thinObserved.image[5][pixel+1]<<" eyeOrientedNormalError="<<thinNormalError
        <<" declaredGeometryBinary32Gamma512Bound="<<fieldBound<<"\nresult="<<(thinFailed?"RED":"GREEN")<<"\n";
    textFile(artifacts/"THIN-SUMMARY.txt",thinSummary.str());std::cout<<thinSummary.str();
    if(thinFailed)throw std::runtime_error("BEHAVIOR RED underwater-backface: supplied thin-column bottom acquired top displacement/known state");

    // Only after the thin-bottom tracer passes, retain real tops on both sides
    // of block zero and at the vanilla height limits. The conservative 1/36
    // corner is a stress lower bound; 1/27 is the attainable isolated level-1
    // corner (Sodium skips the diagonal when both cardinal heights are zero).
    // A .001 near plane here is fixture-only, not Minecraft's camera setting.
    struct TopControl {const char* name;float height,depth;};
    const TopControl tops[]={{"conservative-corner",1.0f/36.0f-.001f,1.0f/9.0f},
        {"isolated-level1-corner",1.0f/27.0f-.001f,1.0f/9.0f},
        {"uniform-level1-top",1.0f/9.0f-.001f,1.0f/9.0f},
        {"source-height-top",8.0f/9.0f-.001f,8.0f/9.0f},{"full-height-top",1.0f-.001f,1.0f}};
    std::ostringstream topology;topology<<std::setprecision(14)
        <<"scope=five supplied top heights at five vanilla block heights; .001 fixture near; no live encoded mesh or natural acceptance\n";
    bool topologyFailed=false;
    for(float block:std::array<float,5>{-64,-1,0,64,319})for(const auto& top:tops){
        const float eye=block+.01f,topY=(block+top.height)-eye,surfaceY=(block+top.depth)-eye;
        const std::string name=std::string(top.name)+"-block"+std::to_string(int(block));
        qualify(topY>.001f&&std::abs(surfaceY-topY)<.12f,"top control does not pass unchanged column tolerance/near plane");
        auto map=bathymetry;for(size_t p=0;p<map.size();p+=4){map[p]=top.depth;map[p+1]=surfaceY;map[p+2]=1;}
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,64,GL_RGBA,GL_FLOAT,map.data());
        std::vector<float> readback(map.size(),std::numeric_limits<float>::quiet_NaN());
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,readback.data());
        for(size_t p=0;p<map.size();++p)qualify(std::isfinite(readback[p])&&readback[p]==map[p],"top control actual map differs");
        rawFile(artifacts/(name+"-actual-bathymetry.rgba32f"),readback);
        for(GLuint program:fixture.programs){glUseProgram(program);glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,eye,0);}
        const auto positive=draw(false,false,name+"-front",topY,false,.001f),
            negativeTop=draw(true,false,name+"-back",topY,false,.001f),
            positiveStore=draw(false,true,name+"-front-store",topY,false,.001f),
            negativeStore=draw(true,true,name+"-back-store",topY,false,.001f);
        const double neutral=std::max(difference(positive.image[0],positiveStore.image[0]),difference(negativeTop.image[0],negativeStore.image[0]));
        qualify(neutral<=fieldBound,"top control C0 STORE neutrality failed");
        double vertexDelta=0,positionDelta=0,normalDelta=0,positiveWave=0;
        bool known=true;
        for(int i=0;i<4;++i){const int p=i*8;
            qualify(positive.vertices[p+6]==topY&&negativeTop.vertices[p+6]==topY,"top undisplaced mean changed");
            qualify(positive.vertices[p+4]==1&&negativeTop.vertices[p+4]==-1,"top inputs are not opposite windings");
            positiveWave=std::max(positiveWave,std::abs(double(positive.vertices[p+1])-topY));
            known=known&&positive.vertices[p+7]==0&&negativeTop.vertices[p+7]==0;
            for(int c=0;c<3;++c)vertexDelta=std::max(vertexDelta,std::abs(double(positive.vertices[p+c])-negativeTop.vertices[p+c]));
        }
        qualify(positiveWave>8*fieldBound,"fixed top control wave lacks displacement sensitivity");
        for(const Capture* item:{&positiveStore,&negativeStore}){
            qualify(item->image[0][pixel+3]==1&&item->image[5][pixel+3]==1&&item->image[5][pixel+2]==1,"top fixed centre not rendered underwater water");
            qualify(item->image[3][pixel+3]==1,"top raw helper does not accept actual supplied map");
            known=known&&item->image[4][pixel+3]==0&&item->image[5][pixel]==1&&item->image[5][pixel+1]==1;
        }
        for(int c=0;c<3;++c){positionDelta=std::max(positionDelta,std::abs(double(positiveStore.image[1][pixel+c])-negativeStore.image[1][pixel+c]));
            normalDelta=std::max(normalDelta,std::abs(double(positiveStore.image[2][pixel+c])-negativeStore.image[2][pixel+c]));}
        const bool failedTop=!known||vertexDelta>fieldBound||positionDelta>fieldBound||normalDelta>fieldBound;
        topologyFailed=topologyFailed||failedTop;
        topology<<name<<" cameraY="<<eye<<" absoluteTopFraction="<<((topY+eye)-std::floor(topY+eye))
            <<" rawInputRGBA32FExact=1 wholeC0ObserverMax="<<neutral<<" positiveVSDisplacement="<<positiveWave
            <<" bothKnownUpper="<<known<<" vertexPositionDifference="<<vertexDelta<<" fragmentPositionDifference="<<positionDelta
            <<" opticalNormalDifference="<<normalDelta<<" result="<<(failedTop?"RED":"GREEN")<<"\n";
    }
    topology<<"declaredGeometryBinary32Gamma512Bound="<<fieldBound<<"\nresult="<<(topologyFailed?"RED":"GREEN")<<"\n";
    textFile(artifacts/"TOP-CONTROL-SUMMARY.txt",topology.str());std::cout<<topology.str();
    if(topologyFailed)throw std::runtime_error("BEHAVIOR RED underwater-backface: thin-bottom discriminator rejected genuine/conservative top controls");

    // The bottom's ordinary front-facing side is seen from BELOW the sheet in
    // AIR, not from inside the column. Enable real back-face culling and require
    // this side to render. A no-occlusion floor (e.g. pinned vanilla slime)
    // can provide a valid bathymetry column without suppressing this face.
    // No floor/occlusion/world-generation implementation is emulated here.
    glEnable(GL_CULL_FACE);glCullFace(GL_BACK);glFrontFace(GL_CCW);
    std::ostringstream airBottom;airBottom<<std::setprecision(14)
        <<"scope=five supplied front-facing thin bottoms from air; GL_BACK culling ON; no live mesh/floor reproduction\n";
    bool airBottomFailed=false;
    for(float block:std::array<float,5>{-64,-1,0,64,319}){
        // Below the one-block floor, rather than inside its collision volume.
        const float eye=block-1.05f,planeY=(block+.001f)-eye,surfaceY=(block+thinDepth)-eye;
        const std::string name="air-bottom-block"+std::to_string(int(block));
        qualify(planeY>.1f&&std::abs(surfaceY-planeY)<.12f,"air bottom near/height inputs do not isolate alias");
        auto map=bathymetry;for(size_t p=0;p<map.size();p+=4){map[p]=thinDepth;map[p+1]=surfaceY;map[p+2]=1;}
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[15]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,64,64,GL_RGBA,GL_FLOAT,map.data());
        std::vector<float> actualMap(map.size(),std::numeric_limits<float>::quiet_NaN());
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actualMap.data());
        for(size_t p=0;p<map.size();++p)qualify(std::isfinite(actualMap[p])&&actualMap[p]==map[p],"air bottom actual map differs");
        rawFile(artifacts/(name+"-actual-bathymetry.rgba32f"),actualMap);
        for(GLuint program:fixture.programs){glUseProgram(program);glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,eye,0);
            glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);}
        const auto original=draw(true,false,name+"-original",planeY,false,.1f),
            repeated=draw(true,false,name+"-repeat",planeY,false,.1f),
            observedBottom=draw(true,true,name+"-store",planeY,false,.1f);
        const double neutral=difference(original.image[0],observedBottom.image[0]),repeatDelta=difference(original.image[0],repeated.image[0]);
        qualify(neutral<=fieldBound&&repeatDelta<=fieldBound,"air bottom C0 STORE neutrality/repeat failed");
        qualify(difference(original.vertices,observedBottom.vertices)<=fieldBound&&difference(original.vertices,repeated.vertices)<=fieldBound,
            "air bottom VS STORE neutrality/repeat failed");
        qualify(observedBottom.image[0][pixel+3]==1&&observedBottom.image[5][pixel+3]==1&&observedBottom.image[5][pixel+2]==0,
            "culled air bottom fixed centre not front-facing rendered water in air");
        qualify(observedBottom.image[3][pixel+3]==1,"air bottom raw helper does not pass unchanged tolerance");
        double geometryDelta=0,weightDelta=0,normalError=0;
        for(int i=0;i<4;++i){const int p=i*8;
            qualify(original.vertices[p+4]==-1&&original.vertices[p+6]==planeY,"air bottom original VS inputs differ");
            for(int c=0;c<3;++c){const double expected=c==1?planeY:vertices[i][c];geometryDelta=std::max(geometryDelta,std::abs(double(original.vertices[p+c])-expected));}
            weightDelta=std::max(weightDelta,std::abs(double(original.vertices[p+7])-1));
        }
        for(int c=0;c<3;++c)normalError=std::max(normalError,std::abs(double(observedBottom.image[2][pixel+c])-(c==1?-1.0:0.0)));
        const bool failedBottom=geometryDelta>fieldBound||weightDelta!=0||normalError>fieldBound
            ||std::abs(double(observedBottom.image[4][pixel+3])-1)>arithmeticBound(1,8)
            ||std::abs(double(observedBottom.image[1][pixel+1])-planeY)>fieldBound
            ||observedBottom.image[5][pixel]!=0||observedBottom.image[5][pixel+1]!=0;
        airBottomFailed=airBottomFailed||failedBottom;
        airBottom<<name<<" cameraY="<<eye<<" bottomFraction="<<((planeY+eye)-std::floor(planeY+eye))
            <<" actualInputRGBA32FExact=1 wholeC0ObserverMax="<<neutral<<" wholeC0RepeatMax="<<repeatDelta
            <<" originalVSGeometryDelta="<<geometryDelta<<" originalVSWeightDelta="<<weightDelta
            <<" rawKnown="<<observedBottom.image[3][pixel+3]<<" finalKnown="<<observedBottom.image[5][pixel]
            <<" upperSurface="<<observedBottom.image[5][pixel+1]<<" eyeOrientedNormalError="<<normalError
            <<" result="<<(failedBottom?"RED":"GREEN")<<"\n";
    }
    glDisable(GL_CULL_FACE);
    airBottom<<"declaredGeometryBinary32Gamma512Bound="<<fieldBound<<"\nresult="<<(airBottomFailed?"RED":"GREEN")<<"\n";
    textFile(artifacts/"AIR-BOTTOM-SUMMARY.txt",airBottom.str());std::cout<<airBottom.str();
    if(airBottomFailed)throw std::runtime_error("BEHAVIOR RED underwater-backface: culled air-side thin bottom became a top");
}
#endif
