#ifndef AQUALUMEN_WATER_RADIANCE_PROBE_H
#define AQUALUMEN_WATER_RADIANCE_PROBE_H

// Opt-in ONE tracer bullet for the declared dry Lambertian direct-Sun C8
// component. This source alone is neither GPU RED nor a shipping correction.
// Original VS/FS main are retained; only public flat/foam options and passive
// MRT STOREs differ. No production marcher/wave/caustic algorithm is copied.
#include "water-optical-depth-probe.h"
#include "solar-radiometry-probe.h"
#include <regex>

namespace aqualumenWaterRadianceDetail {
using V3=std::array<double,3>;
using M4=std::array<float,16>;
constexpr int size=65,skyWidth=64,skyHeight=32,centre=size/2;
constexpr double index=1.333,waterY=-2.0,bedY=-3.5,cameraWorldY=65.0;
const M4 identity={1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
const M4 view={1,0,0,0, 0,0,1,0, 0,-1,0,0, 0,0,0,1};
const M4 inverseView={1,0,0,0, 0,0,-1,0, 0,1,0,0, 0,0,0,1};
const M4 shadowProjection={0.01f,0,0,0, 0,0.01f,0,0, 0,0,0.01f,0, 0,0,0,1};
using aqualumenWaterOpticalDepthDetail::dot;
using aqualumenWaterOpticalDepthDetail::add;
using aqualumenWaterOpticalDepthDetail::normalized;
using aqualumenWaterOpticalDepthDetail::firstHit;
using aqualumenWaterOpticalDepthDetail::Box;
inline void qualify(bool condition,const std::string& message) {
    if(!condition) throw std::runtime_error("INCONCLUSIVE water-radiance qualification: "+message);
}
inline void finite(const std::vector<float>& values) {
    for(float value:values) qualify(std::isfinite(value),"nonfinite supplied/read-back GPU data");
}
inline double difference(const std::vector<float>& a,const std::vector<float>& b) {
    qualify(a.size()==b.size(),"unequal capture size");
    double result=0;for(size_t i=0;i<a.size();++i) result=std::max(result,std::abs(double(a[i])-b[i]));return result;
}
inline void textFile(const std::filesystem::path& path,const std::string& text) {
    std::ofstream output(path);output<<text;if(!output) throw std::runtime_error("Cannot save water-radiance evidence "+path.string());
}
inline void rawFile(const std::filesystem::path& path,const std::vector<float>& values) {
    std::ofstream output(path,std::ios::binary);output.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()*sizeof(float)));
    if(!output) throw std::runtime_error("Cannot save water-radiance raw evidence "+path.string());
}
inline double arithmeticBound(double scale,int operations=512) {
    // Declared gamma_n binary32 rounding allowance, not an accuracy theorem
    // for arbitrary driver transcendentals. Full common C0 magnitude is used.
    constexpr double u=0.5*double(std::numeric_limits<float>::epsilon());
    return operations*u/(1-operations*u)*std::abs(scale);
}
inline double storageRoundoff(GLenum format,double value) {
    qualify(std::isfinite(value),"nonfinite storage error argument");
    const int precision=format==GL_RGBA16F?11:format==GL_RGBA32F?24:0;
    qualify(precision!=0,"unsupported declared C0/C4/C8 format");
    int exponent=0;std::frexp(std::abs(value),&exponent);
    const double minimum=std::ldexp(1.0,format==GL_RGBA16F?-24:-149);
    return 0.5*(value==0?minimum:std::max(minimum,std::ldexp(1.0,exponent-precision)));
}
inline std::string flatOptions(std::string source) {
    for(const std::string name:{"WAVE_HEIGHT","SHORE_FOAM"}) {
        const std::string option="#define "+name+" ";const auto at=source.find(option);
        qualify(at!=std::string::npos&&source.find(option,at+option.size())==std::string::npos,"public "+name+" option absent/ambiguous");
        source.replace(at,source.find('\n',at)-at,option+"0.0");
    }
    return source;
}
inline double clarity(const std::string& fragment) {
    const std::regex pattern("#define\\s+WATER_CLARITY\\s+([0-9]+(?:\\.[0-9]*)?)");
    const std::sregex_iterator begin(fragment.begin(),fragment.end(),pattern),end;qualify(begin!=end,"literal WATER_CLARITY missing");
    auto next=begin;qualify(++next==end,"ambiguous WATER_CLARITY");
    const double result=std::stod((*begin)[1]);qualify(result>0&&std::isfinite(result),"invalid WATER_CLARITY");return result;
}
inline V3 extinction(const std::string& fragment) {
    const std::string number="([0-9]+(?:\\.[0-9]*)?(?:[eE][+-]?[0-9]+)?)";
    const std::regex pattern("return\\s+exp\\s*\\(\\s*-vec3\\s*\\(\\s*"+number+"\\s*,\\s*"+number+"\\s*,\\s*"+number+
        "\\s*\\)\\s*\\*\\s*max\\(distance,0\\.0\\)\\s*/\\s*WATER_CLARITY\\s*\\)");
    const std::sregex_iterator begin(fragment.begin(),fragment.end(),pattern),end;qualify(begin!=end,"literal effective RGB extinction missing");
    auto next=begin;qualify(++next==end,"ambiguous water extinction");
    V3 result={};for(int c=0;c<3;++c) {result[c]=std::stod((*begin)[c+1]);qualify(result[c]>0&&std::isfinite(result[c]),"nonpositive extinction");}return result;
}
inline V3 refracted(const V3& incident,const V3& normal) {
    // Independent Snell geometry for this air->water view ray, not GLSL code.
    const double cosine=-dot(incident,normal),eta=1/index;
    qualify(cosine>0,"view ray does not enter the upper surface");
    const double transmittedCosine=std::sqrt(1-eta*eta*(1-cosine*cosine));
    return normalized(add(add(incident,normal,cosine),normal,-transmittedCosine/eta));
}
inline double fresnel(double cosine) {
    // Independent unpolarized boundary law in double precision.
    const double c=std::clamp(cosine,0.0,1.0),t=std::sqrt(1-(1-c*c)/(index*index));
    const double s=(c-index*t)/(c+index*t),p=(index*c-t)/(index*c+t);return 0.5*(s*s+p*p);
}
inline V3 transform(const M4& matrix,const V3& point) {
    V3 result={};for(int row=0;row<3;++row) {result[row]=matrix[12+row];for(int col=0;col<3;++col) result[row]+=matrix[col*4+row]*point[col];}return result;
}
inline V3 unproject(double u,double v,double depth,const M4& inverseProjection) {
    const std::array<double,4> clip={2*u-1,2*v-1,2*depth-1,1};std::array<double,4> result={};
    for(int row=0;row<4;++row) for(int col=0;col<4;++col) result[row]+=inverseProjection[col*4+row]*clip[col];
    qualify(result[3]>0&&std::isfinite(result[3]),"invalid independent homogeneous unprojection");
    return transform(inverseView,{result[0]/result[3],result[1]/result[3],result[2]/result[3]});
}
inline std::array<double,2> project(const V3& position,const M4& projection) {
    const auto p=transform(view,position);std::array<double,4> clip={};
    for(int row=0;row<4;++row) {clip[row]=projection[12+row];for(int col=0;col<3;++col) clip[row]+=projection[col*4+row]*p[col];}
    qualify(clip[3]>0,"physical bed lies behind camera");return {clip[0]/clip[3]*0.5+0.5,clip[1]/clip[3]*0.5+0.5};
}
struct SamplerState {
    std::array<GLint,9> samplers={};std::array<GLint,3> clamps={};
    const std::array<GLenum,3> targets={GL_CLAMP_READ_COLOR,GL_CLAMP_FRAGMENT_COLOR,GL_CLAMP_VERTEX_COLOR};
    SamplerState() {
        for(GLuint unit=0;unit<samplers.size();++unit) {glGetIntegeri_v(GL_SAMPLER_BINDING,unit,&samplers[unit]);glBindSampler(unit,0);}
        for(size_t i=0;i<targets.size();++i) {glGetIntegerv(targets[i],&clamps[i]);glClampColor(targets[i],GL_FALSE);}
    }
    ~SamplerState() {
        for(GLuint unit=0;unit<samplers.size();++unit) glBindSampler(unit,GLuint(samplers[unit]));
        for(size_t i=0;i<targets.size();++i) glClampColor(targets[i],GLenum(clamps[i]));
    }
};
struct Capture {std::array<std::vector<float>,8> output;};
} // namespace aqualumenWaterRadianceDetail

// Expected source-unit inference: D is the declared dry receiver rho*E_air/pi.
// Zenith admission changes bed irradiance by Fresnel/Beer only. The distinct
// water->air directional-radiance exit supplies (n_air/n_water)^2 (PBRT4,
// Reflection Models/Dielectric BSDF, non-symmetric scattering). This fixture
// does not assert those units for B, ambient, miss proxies or volume scattering,
// and cannot accept cyan/serrated natural coasts or actual Iris/runtime binding.
inline void productionWaterDirectRadianceProbe(const std::filesystem::path& root,
    const std::filesystem::path& artifacts="build/water-direct-radiance") {
    using namespace aqualumenWaterRadianceDetail;
    using aqualumenSolarProbeDetail::declaredFormat;
    const auto* rendererBytes=glGetString(GL_RENDERER);const auto* versionBytes=glGetString(GL_VERSION);
    const std::string renderer=rendererBytes?reinterpret_cast<const char*>(rendererBytes):"";
    qualify(renderer.find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");
    GLint major=0,minor=0,profile=0,buffers=0,attachments=0,units=0;
    glGetIntegerv(GL_MAJOR_VERSION,&major);glGetIntegerv(GL_MINOR_VERSION,&minor);glGetIntegerv(GL_CONTEXT_PROFILE_MASK,&profile);
    glGetIntegerv(GL_MAX_DRAW_BUFFERS,&buffers);glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachments);glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&units);
    qualify((major>3||(major==3&&minor>=3))&&(profile&GL_CONTEXT_COMPATIBILITY_PROFILE_BIT)&&buffers>=8&&attachments>=8&&units>=9,
        "GL3.3 compatibility/eight MRTs/nine units required");
    qualify(glGetError()==GL_NO_ERROR,"entered with a GL error");
    if(std::filesystem::exists(artifacts)) throw std::runtime_error("Preserve water-radiance artifacts; choose a NEW directory");
    std::filesystem::create_directories(artifacts);
    const auto originalVertex=expand(root/"gbuffers_water.vsh",root,0),originalFragment=expand(root/"gbuffers_water.fsh",root,0);
    const auto vertex=flatOptions(originalVertex),fragment=flatOptions(originalFragment);
    const auto producer=expand(root/"prepare.fsh",root,0);
    const GLenum c0Format=declaredFormat(producer,0),c4Format=declaredFormat(producer,4),c8Format=declaredFormat(producer,8),
        c6Format=declaredFormat(producer,6),c7Format=declaredFormat(producer,7);
    const double waterClarity=clarity(fragment);const V3 beta=extinction(fragment);
    qualify(fragment.find("float etaTarget=underwater?1.0:1.333;")!=std::string::npos,"declared1.333 upper-interface IOR contract changed");
    const float focal=float(1/std::tan(aqualumenWaterOpticalDepthDetail::pi/6)),near=0.1f,far=128;
    const float a=-(far+near)/(far-near),b=-2*far*near/(far-near);
    const M4 projection={focal,0,0,0, 0,focal,0,0, 0,0,a,-1, 0,0,b,0};
    const M4 inverseProjection={1/focal,0,0,0, 0,1/focal,0,0, 0,0,0,1/b, 0,0,-1,a/b};
    const float encodedDepth=0.5f*((a*float(bedY)+b)/float(-bedY))+0.5f;
    qualify(encodedDepth>0&&encodedDepth<0.999999f,"physical bed cannot be represented as opaque depth");
    const std::vector<Box> boxes={{{-16,-4.5,-16},{16,bedY,16},1}};
    // A declared fixed pixel, never selected by kind/confidence/tagged output.
    const V3 intendedWater={0,waterY,0};const V3 down={0,-1,0},up={0,1,0};
    const auto first=firstHit(boxes,intendedWater,down),cameraFirst=firstHit(boxes,{0,0,0},down);
    qualify(first.valid&&!first.inside&&!first.tangent&&first.axis==1&&first.side==1&&first.travel==1.5
        &&cameraFirst.valid&&cameraFirst.axis==1&&cameraFirst.side==1,"independent closed-bed first hit invalid");
    const auto reflectionFirst=firstHit(boxes,intendedWater,up);
    qualify(!reflectionFirst.valid&&!reflectionFirst.inside,"physical upward reflection has a bed receiver");
    std::ofstream footprint(artifacts/"geometry-qualification.csv");
    footprint<<std::setprecision(14)<<"corner,u,v,waterX,waterY,waterZ,firstBedX,firstBedY,firstBedZ,outgoingPath,sourceU,sourceV,sourcePixelX,sourcePixelY\n";
    double pixelPathUncertainty=0;
    for(int corner=0;corner<4;++corner) {
        const double u=double(centre+(corner&1))/size,v=double(centre+((corner>>1)&1))/size;
        const V3 cameraRay=normalized(unproject(u,v,1,inverseProjection));
        qualify(cameraRay[1]<-0.9,"fixed camera pixel footprint is not a vertical non-grazing view");
        const V3 surface=add({0,0,0},cameraRay,waterY/cameraRay[1]);
        const V3 transmitted=refracted(cameraRay,up);const auto hit=firstHit(boxes,surface,transmitted);
        qualify(hit.valid&&!hit.inside&&!hit.tangent&&hit.id==1&&hit.axis==1&&hit.side==1,"pixel footprint crosses a real receiver/occlusion edge");
        const auto uv=project(hit.point,projection);const int x=int(std::floor(uv[0]*size)),y=int(std::floor(uv[1]*size));
        qualify(x==centre&&y==centre,"complete camera-pixel Snell footprint does not share one constant bed texel");
        const auto visible=firstHit(boxes,{0,0,0},normalized(hit.point));
        qualify(visible.valid&&visible.id==1&&visible.axis==1&&visible.side==1,"first refracted bed is not directly camera-visible");
        pixelPathUncertainty=std::max(pixelPathUncertainty,std::abs(hit.travel-first.travel));
        footprint<<corner<<","<<u<<","<<v<<","<<surface[0]<<","<<surface[1]<<","<<surface[2]<<","<<hit.point[0]<<","<<hit.point[1]<<","<<hit.point[2]
            <<","<<hit.travel<<","<<uv[0]<<","<<uv[1]<<","<<x<<","<<y<<"\n";
    }
    footprint.flush();if(!footprint) throw std::runtime_error("Cannot save water-radiance independent geometry qualification");
    // Every addition is a STORE of a value already evaluated by original main.
    // No new helper, branch, derivative, texture sample or marcher is inserted.
    std::string observed=fragment;
    const auto appendStore=[&](const std::string& anchor,const std::string& stores) {
        const auto at=observed.find(anchor);qualify(at!=std::string::npos&&observed.find(anchor,at+anchor.size())==std::string::npos,"passive STORE anchor changed");
        observed.insert(at+anchor.size(),"\n// DEBUG-water-radiance STORE begin\n"+stores+"\n// DEBUG-water-radiance STORE end\n");
    };
    appendStore("void main() {","    gl_FragData[1]=vec4(0.0);gl_FragData[2]=vec4(0.0);gl_FragData[3]=vec4(0.0);\n    gl_FragData[4]=vec4(0.0);gl_FragData[5]=vec4(0.0);gl_FragData[6]=vec4(0.0);gl_FragData[7]=vec4(0.0);");
    appendStore("        vec2 refracted=refractionTrace(viewPos,transmittedView,screen,initialPath,searchSeed,upperSurface&&!underwater,absolutePosition.y,thickness,receiverKind,receiverConfidence);",
        "        gl_FragData[5]=vec4(refracted,0.0,0.0);");
    appendStore("            behind=texture(colortex4,refracted).rgb;","            gl_FragData[6]=vec4(behind,1.0);");
    appendStore("            float focus=waterCaustic(floorPosition,absolutePosition.y,sun,causticPixelFootprint);","            gl_FragData[5].w=focus;");
    appendStore("            vec3 incidentTransmission=waterSunBeamTransmission(incidentDepth,sun);","            gl_FragData[7]=vec4(receiverSun,incidentDepth);");
    appendStore("    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,environment,upperSurface&&!underwater,worldPosition.y);",
        "    gl_FragData[5].z=reflectedHit.a;");
    appendStore("    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);",
        "    gl_FragData[1]=vec4(worldPosition,waterMeanSurfaceY);\n    gl_FragData[2]=vec4(n,fresnel);\n    gl_FragData[3]=vec4(transmitted,thickness);\n    gl_FragData[4]=vec4(receiverConfidence,float(receiverKind),initialPath,verticalDepth);");
    std::string recovered=observed;const std::string start="\n// DEBUG-water-radiance STORE begin\n",end="\n// DEBUG-water-radiance STORE end\n";
    for(auto at=recovered.find(start);at!=std::string::npos;at=recovered.find(start)) {
        const auto after=recovered.find(end,at);qualify(after!=std::string::npos,"unterminated passive STORE");recovered.erase(at,after+end.size()-at);
    }
    qualify(recovered==fragment,"removing passive STOREs does not recover byte-identical original public-option main");
    textFile(artifacts/"shipping-expanded.vsh",originalVertex);textFile(artifacts/"shipping-expanded.fsh",originalFragment);
    textFile(artifacts/"production-flat.vsh",vertex);textFile(artifacts/"production-flat-foam0.fsh",fragment);textFile(artifacts/"passive-stores.fsh",observed);
    SamplerState samplerState;aqualumenWaterOpticalDepthDetail::Fixture fixture;
    for(GLenum option:{GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS}) glPixelStorei(option,0);
    glPixelStorei(GL_PACK_SWAP_BYTES,GL_FALSE);glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
    for(GLenum option:{GL_RED_SCALE,GL_GREEN_SCALE,GL_BLUE_SCALE,GL_ALPHA_SCALE,GL_DEPTH_SCALE}) glPixelTransferf(option,1);
    for(GLenum option:{GL_RED_BIAS,GL_GREEN_BIAS,GL_BLUE_BIAS,GL_ALPHA_BIAS,GL_DEPTH_BIAS}) glPixelTransferf(option,0);
    glPixelTransferi(GL_MAP_COLOR,GL_FALSE);
    fixture.programs[0]=link(vertex,fragment,"DEBUG-water-radiance-original-main","mc_Entity");
    fixture.programs[1]=link(vertex,observed,"DEBUG-water-radiance-store-only-main","mc_Entity");
    const auto& textures=fixture.textures;const float white[4]={1,1,1,1},shadow=1;
    std::vector<float> sky(skyWidth*skyHeight*4,0),bathymetry(64*64*4,0),depth(size*size,encodedDepth);
    for(int y=0;y<skyHeight;++y) for(int x=0;x<skyWidth;++x) {
        const int p=(y*skyWidth+x)*4;for(int c=0;c<3;++c) sky[p+c]=y<skyHeight-1?0.04f:x==0?0.05f:0.0f;sky[p+3]=1;
    }
    for(size_t p=0;p<bathymetry.size();p+=4) {bathymetry[p]=1.5f;bathymetry[p+1]=float(waterY);bathymetry[p+2]=1;}
    std::ofstream storage(artifacts/"storage.csv");storage<<"texture,internalFormat,width,height\n";
    const auto allocate=[&](int slot,GLenum format,int width,int height,GLenum channels,const float* data) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        for(GLenum parameter:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER}) glTexParameteri(GL_TEXTURE_2D,parameter,GL_NEAREST);
        for(GLenum parameter:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T}) glTexParameteri(GL_TEXTURE_2D,parameter,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,GLint(format),width,height,0,channels,GL_FLOAT,data);
        GLint actual=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&actual);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);
        qualify(GLenum(actual)==format&&w==width&&h==height,"actual texture allocation/declared format mismatch");
        storage<<slot<<","<<actual<<","<<w<<","<<h<<"\n";
    };
    allocate(0,GL_RGBA32F,1,1,GL_RGBA,white);allocate(1,c4Format,size,size,GL_RGBA,nullptr);
    allocate(2,c6Format,skyWidth,skyHeight,GL_RGBA,sky.data());allocate(3,GL_DEPTH_COMPONENT32F,size,size,GL_DEPTH_COMPONENT,depth.data());
    allocate(4,GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
    allocate(5,c8Format,size,size,GL_RGBA,nullptr);allocate(7,c7Format,skyWidth,skyHeight,GL_RGBA,sky.data());
    allocate(15,GL_RGBA32F,64,64,GL_RGBA,bathymetry.data());
    GLenum draws[8];glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);
    for(int output=0;output<8;++output) {
        const int slot=output==0?6:7+output;allocate(slot,output==0?c0Format:GL_RGBA32F,size,size,GL_RGBA,nullptr);
        draws[output]=GL_COLOR_ATTACHMENT0+output;glFramebufferTexture2D(GL_FRAMEBUFFER,draws[output],GL_TEXTURE_2D,textures[slot],0);
    }
    glDrawBuffers(8,draws);qualify(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"separate-output MRT FBO incomplete");
    const auto readInput=[&](int slot,GLenum channels,int count) {
        std::vector<float> data(size_t(count),std::numeric_limits<float>::quiet_NaN());
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[slot]);glGetTexImage(GL_TEXTURE_2D,0,channels,GL_FLOAT,data.data());finite(data);return data;
    };
    const auto suppliedDepth=readInput(3,GL_DEPTH_COMPONENT,size*size);rawFile(artifacts/"actual-depth1.f32",suppliedDepth);
    qualify(suppliedDepth==depth,"actual supplied opaque depth differs from frozen analytic plane");
    const V3 decodedBed=unproject(0.5,0.5,suppliedDepth[centre*size+centre],inverseProjection);
    const double inputGeometryError=std::abs(decodedBed[1]-bedY)+arithmeticBound(-bedY,32);
    qualify(inputGeometryError<0.0001,"supplied depth unprojection does not reproduce the declared horizontal bed");
    rawFile(artifacts/"actual-bathymetry.rgba32f",readInput(15,GL_RGBA,64*64*4));
    rawFile(artifacts/"actual-C6.rgba32f",readInput(2,GL_RGBA,skyWidth*skyHeight*4));
    rawFile(artifacts/"actual-C7.rgba32f",readInput(7,GL_RGBA,skyWidth*skyHeight*4));
    const auto allColour=[&](const V3& rgb) {
        std::vector<float> data(size*size*4,1);for(int p=0;p<size*size;++p) for(int c=0;c<3;++c) data[p*4+c]=float(rgb[c]);return data;
    };
    const auto requestedSun=allColour({0.2,0.15,0.1});
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,requestedSun.data());
    const auto suppliedSun=readInput(5,GL_RGBA,size*size*4);rawFile(artifacts/"actual-positive-C8.rgba32f",suppliedSun);
    const V3 baseRgb={0.08,0.07,0.06};const auto requestedBase=allColour(baseRgb),zeroSun=allColour({0,0,0});
    auto requestedTagged=requestedBase;
    for(int p=0;p<size*size;++p) for(int c=0;c<3;++c) {
        qualify(suppliedSun[p*4+c]>storageRoundoff(c8Format,suppliedSun[p*4+c]),"actual C8 lacks a resolved positive RGB source");
        requestedTagged[p*4+c]=float(double(requestedBase[p*4+c])+suppliedSun[p*4+c]);
    }
    auto reflectionTagged=requestedBase;
    for(int y=0;y<size;++y) for(int x=0;x<size;++x) if(std::abs(x-centre)>2||std::abs(y-centre)>2)
        for(int c=0;c<3;++c) reflectionTagged[(y*size+x)*4+c]+=0.4f;
    const char* samplers[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
    const int unitsBySampler[]={0,1,2,3,4,5,6,7};
    for(GLuint program:fixture.programs) {
        glUseProgram(program);
        for(int sampler=0;sampler<8;++sampler) {const GLint at=glGetUniformLocation(program,samplers[sampler]);
            qualify(at>=0,"production sampler absent: "+std::string(samplers[sampler]));glUniform1i(at,unitsBySampler[sampler]);}
        for(const auto& matrix:std::array<std::pair<const char*,M4>,6>{{{"gbufferProjection",projection},{"gbufferProjectionInverse",inverseProjection},
            {"gbufferModelView",view},{"gbufferModelViewInverse",inverseView},{"shadowProjection",shadowProjection},{"shadowModelView",identity}}})
            glUniformMatrix4fv(glGetUniformLocation(program,matrix.first),1,GL_FALSE,matrix.second.data());
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,float(cameraWorldY),0);
        // view maps world +Y to view +Z, so actual world Sun remains zenith.
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,0,1);glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,0,1);
        glUniform1f(glGetUniformLocation(program,"viewWidth"),size);glUniform1f(glGetUniformLocation(program,"viewHeight"),size);
        glUniform1f(glGetUniformLocation(program,"far"),far);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),120.0f);
        glUniform1f(glGetUniformLocation(program,"rainStrength"),0);glUniform1f(glGetUniformLocation(program,"wetness"),0);
        glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);glUniform1i(glGetUniformLocation(program,"isEyeInWater"),0);
        glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);glUniform4f(glGetUniformLocation(program,"aqualumenGrid"),-32,-32,64,float(waterY));
        glUniform1i(glGetUniformLocation(program,"aqualumenBathymetryReady"),1);glUniform4f(glGetUniformLocation(program,"aqualumenBathymetryGrid"),-32,-32,64,float(waterY));
        glUniform1i(glGetUniformLocation(program,"worldTime"),6000);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
        qualify(glGetAttribLocation(program,"mc_Entity")==10,"water material attribute contract changed");
    }
    glDisableVertexAttribArray(10);glVertexAttrib4f(10,10000,0,0,0);
    for(GLenum cap:{GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,
        GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE}) glDisable(cap);
    glDepthMask(GL_FALSE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glViewport(0,0,size,size);
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(view.data());
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE0,0.5f,0.5f);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    const auto draw=[&](const std::vector<float>& colour,const std::vector<float>& sun,bool observe,const std::string& prefix) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,colour.data());
        const auto actualColour=readInput(1,GL_RGBA,size*size*4);rawFile(artifacts/(prefix+"-input-C4.rgba32f"),actualColour);
        glBindTexture(GL_TEXTURE_2D,textures[5]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,sun.data());
        const auto actualSun=readInput(5,GL_RGBA,size*size*4);rawFile(artifacts/(prefix+"-input-C8.rgba32f"),actualSun);
        for(int unit=0;unit<9;++unit) {glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,unit<6?textures[unit]:unit==6?textures[15]:unit==7?textures[7]:0);}
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);glDrawBuffers(8,draws);
        const float zero[4]={0,0,0,0};for(int output=0;output<8;++output) glClearBufferfv(GL_COLOR,output,zero);
        glDrawBuffers(observe?8:1,draws);glUseProgram(fixture.programs[observe?1:0]);
        // Same fixed planar surface through original VS; no depth attachment
        // feedback. CPU first-surface/first-bed qualification proves visibility.
        const float vertices[6][3]={{-4,float(waterY),-4},{4,float(waterY),-4},{4,float(waterY),4},
            {-4,float(waterY),-4},{4,float(waterY),4},{-4,float(waterY),4}};
        glBegin(GL_TRIANGLES);for(const auto& vertex:vertices) glVertex3fv(vertex);glEnd();
        Capture result;
        for(int output=0;output<(observe?8:1);++output) {
            result.output[output].assign(size*size*4,std::numeric_limits<float>::quiet_NaN());glReadBuffer(draws[output]);
            glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,result.output[output].data());finite(result.output[output]);
            rawFile(artifacts/(prefix+"-output"+std::to_string(output)+".rgba32f"),result.output[output]);
        }
        qualify(glGetError()==GL_NO_ERROR,"draw/readback GL error");return result;
    };
    const auto base=draw(requestedBase,zeroSun,false,"base"),baseRepeat=draw(requestedBase,zeroSun,false,"base-repeat"),
        baseObserved=draw(requestedBase,zeroSun,true,"base-observer");
    const auto tagged=draw(requestedTagged,suppliedSun,false,"positive"),taggedRepeat=draw(requestedTagged,suppliedSun,false,"positive-repeat"),
        taggedObserved=draw(requestedTagged,suppliedSun,true,"positive-observer");
    const auto zero=draw(requestedBase,zeroSun,false,"zero-tag"),zeroObserved=draw(requestedBase,zeroSun,true,"zero-tag-observer");
    const auto reflection=draw(reflectionTagged,zeroSun,false,"reflection-tag"),reflectionRepeat=draw(reflectionTagged,zeroSun,false,"reflection-tag-repeat"),
        reflectionObserved=draw(reflectionTagged,zeroSun,true,"reflection-tag-observer");
    const auto pairedReadback=[&](int slot,const std::vector<float>& input) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[slot]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,input.data());
        return readInput(slot,GL_RGBA,size*size*4);
    };
    const auto actualBase=pairedReadback(1,requestedBase),actualTagged=pairedReadback(1,requestedTagged),actualReflectionTag=pairedReadback(1,reflectionTagged);
    const int pixel=centre*size+centre,offset=pixel*4;
    for(int y=0;y<size;++y) for(int x=0;x<size;++x) for(int c=0;c<3;++c) {
        const int p=(y*size+x)*4+c;
        if(std::abs(x-centre)<=2&&std::abs(y-centre)<=2)
            qualify(actualReflectionTag[p]==actualBase[p],"negative reflection tag changed the complete constant refraction-source patch");
        else qualify(actualReflectionTag[p]>actualBase[p]+0.3,"negative reflection control lacks an actual positive outside-footprint tag");
    }
    for(const auto& pair:std::array<std::pair<const Capture*,const Capture*>,3>{{{&base,&baseRepeat},{&tagged,&taggedRepeat},{&reflection,&reflectionRepeat}}})
        qualify(difference(pair.first->output[0],pair.second->output[0])==0,"whole-image original-main repeat is nondeterministic");
    qualify(difference(base.output[0],zero.output[0])==0,"zero-source control changes actual C0");
    for(const auto& pair:std::array<std::pair<const Capture*,const Capture*>,4>{{{&base,&baseObserved},{&tagged,&taggedObserved},{&zero,&zeroObserved},{&reflection,&reflectionObserved}}})
        for(size_t p=0;p<pair.first->output[0].size();++p) {
            const double value=pair.first->output[0][p],other=pair.second->output[0][p];
            const double bound=storageRoundoff(c0Format,value)+storageRoundoff(c0Format,other)+arithmeticBound(std::abs(value)+std::abs(other));
            qualify(std::abs(value-other)<=bound,"store-only passive observer changes whole-image actual C0");
        }
    for(const Capture* capture:{&base,&tagged,&zero,&reflection})
        qualify(capture->output[0][offset+3]==1,"fixed original-main centre lacks water alpha1");
    const double coordinateBound=inputGeometryError+arithmeticBound(-waterY,32);
    for(const Capture* capture:{&baseObserved,&taggedObserved,&zeroObserved,&reflectionObserved}) {
        const auto& state=capture->output;
        for(int c=0;c<3;++c) {
            qualify(std::abs(state[1][offset+c]-intendedWater[c])<=coordinateBound,"actual original-VS water position changed");
            qualify(std::abs(state[2][offset+c]-up[c])<=arithmeticBound(1,32),"actual optical normal is not flat/upward");
            qualify(std::abs(state[3][offset+c]-down[c])<=arithmeticBound(1,32),"actual transmitted ray is not vertical");
        }
        qualify(std::abs(state[1][offset+3]-waterY)<=coordinateBound,"actual mean interface changed");
        qualify(state[4][offset]==1&&state[4][offset+1]==1,"actual centre lacks fully confident confirmed opaque receiver");
        qualify(state[5][offset+2]<0&&state[5][offset+3]==1,"actual reflection hits geometry or actual flat-wave caustic focus is not1");
        qualify(std::abs(state[5][offset]-0.5)<=arithmeticBound(1,32)&&std::abs(state[5][offset+1]-0.5)<=arithmeticBound(1,32),"actual receiver UV differs from independent first bed");
        const double pathBound=inputGeometryError+coordinateBound+pixelPathUncertainty+arithmeticBound(first.travel,64);
        for(double path:{double(state[3][offset+3]),double(state[4][offset+2]),double(state[4][offset+3]),double(state[7][offset+3])})
            qualify(std::abs(path-first.travel)<=pathBound,"actual source/outgoing/proxy path does not reproduce independent1.5m bed");
        qualify(std::abs(state[2][offset+3]-fresnel(1))<=arithmeticBound(1,64),"actual Fresnel differs from independent dielectric law");
    }
    for(int c=0;c<3;++c) {
        qualify(baseObserved.output[7][offset+c]==0&&zeroObserved.output[7][offset+c]==0,"zero control supplies a nonzero C8 component");
        qualify(taggedObserved.output[7][offset+c]==suppliedSun[offset+c],"actual sampled C8 differs from supplied source or clamp activates");
        qualify(taggedObserved.output[6][offset+c]==actualTagged[offset+c]&&baseObserved.output[6][offset+c]==actualBase[offset+c],"actual dry C4 source differs from its readback");
        qualify(actualBase[offset+c]>storageRoundoff(c4Format,actualBase[offset+c])&&actualTagged[offset+c]>suppliedSun[offset+c],"positive B margin does not exclude C8 clamp activation");
        qualify(reflection.output[0][offset+c]==base.output[0][offset+c],"outside-source-footprint reflection tag changes centre C0");
    }
    std::ostringstream manifest;manifest<<std::setprecision(14)
        <<"ONE fixed water direct-Sun radiance tracer bullet; no output-driven pixel search; preparing source is not GPU RED.\nRenderer="<<renderer
        <<"\nGL="<<(versionBytes?reinterpret_cast<const char*>(versionBytes):"unknown")
        <<"\nOriginal VS/FS main with public WAVE_HEIGHT0,SHORE_FOAM0; removed passive STORE blocks recover byte-identical public-option FS.\n"
        <<"Camera world=(0,65,0), interface worldY63/relativeY-2, closed horizontal bed worldY61.5/relativeY-3.5; true depth1.5m, zenith Sun, phase120, fixed65x65 centre32,32; view/projection and inputs saved.\n"
        <<"Original VS renders explicit planar ABC/ACD triangles, all valid64x64 bathymetry depth1.5/meanY-2, ripple inactive. No depth attachment is sampled/written: independent first interface/closed-bed geometry establishes visibility.\n"
        <<"NEAREST source/depth; all four independent camera-pixel Snell footprints hit the same visible closed-bed top/source texel before source algebra.\n"
        <<"Paired inputs C4=B+D8,C8=D8 versus C4=B,C8=0. D8 is actual declared-format readback, not unquantized requested(.2,.15,.1). Residual DeltaC4-D8 is propagated separately, not silently equated or counted as16F error twice.\n"
        <<"Common positive sky(.04)/Sun clear-cache(.05)/glint/scatter and covered fully-lit scene shadows held fixed. Zero tag and positively read-back off-refracted-footprint C4 tag preserve centre C0; other pixels can legitimately see that tag. Every original whole-image repeat is exact; whole-image passive neutrality uses queried C0 storage+declared gamma512 bound.\n"
        <<"Source unit inference ONLY: dry D8=rho*E_air/pi; entry irradiance gets (1-Fentry)*Beer, not n^2. Water-medium bed directional radiance exiting to air gets q=(1/1.333)^2. Expected RGB delta=D8*(1-Fentry)*(1-Fexit)*exp[-beta*(Lentry+Lexit)/clarity]*q.\n"
        <<"Reference: https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF#sec:non-symmetric-scattering\n"
        <<"Actual C0/C4/C8 storage queried; raw rgba32f means GL_FLOAT readback, not32F storage claim. gamma512 arithmetic at FULL tagged/base C0 magnitude plus half-ULPs, source residual, supplied-depth/geometry/pixel path and Fresnel allowances. Declared FP model is not a universal transcendental-accuracy proof.\n"
        <<"Not an assertion about B/ambient/proxy/scatter units, reverse sky entry, exact arbitrary bathymetry, caustic transport, natural shore color/serration, Iris binding or Minecraft FPS.\n"
        <<"C0format="<<c0Format<<" C4format="<<c4Format<<" C8format="<<c8Format<<" clarity="<<waterClarity<<" beta=("<<beta[0]<<","<<beta[1]<<","<<beta[2]
        <<") inputGeometryError="<<inputGeometryError<<" pixelPathUncertainty="<<pixelPathUncertainty<<"\n";
    textFile(artifacts/"fixture.txt",manifest.str());
    std::ostringstream matrices;matrices<<std::setprecision(14)<<"matrix,index,value\n";
    for(const auto& entry:std::array<std::pair<const char*,M4>,6>{{{"view",view},{"inverseView",inverseView},{"projection",projection},{"inverseProjection",inverseProjection},{"shadowProjection",shadowProjection},{"shadowView",identity}}})
        for(int i=0;i<16;++i) matrices<<entry.first<<","<<i<<","<<entry.second[i]<<"\n";
    textFile(artifacts/"matrices.csv",matrices.str());
    const double boundaryFresnel=fresnel(1),exitFactor=1/(index*index);
    const double fresnelUncertainty=arithmeticBound(1,64);
    const double pathUncertainty=inputGeometryError+coordinateBound+pixelPathUncertainty+arithmeticBound(first.travel,64);
    std::array<double,3> expected={},bound={},actual={};
    for(int c=0;c<3;++c) {
        const double d=suppliedSun[offset+c],transmission=std::exp(-beta[c]*(2*first.travel)/waterClarity);
        expected[c]=d*(1-boundaryFresnel)*(1-boundaryFresnel)*transmission*exitFactor;
        actual[c]=double(tagged.output[0][offset+c])-base.output[0][offset+c];
        const double residual=std::abs(double(actualTagged[offset+c])-actualBase[offset+c]-d);
        bound[c]=storageRoundoff(c0Format,tagged.output[0][offset+c])+storageRoundoff(c0Format,base.output[0][offset+c])
            +arithmeticBound(std::abs(double(tagged.output[0][offset+c]))+std::abs(double(base.output[0][offset+c]))+d)
            +residual*(1-boundaryFresnel)*std::exp(-beta[c]*first.travel/waterClarity)
            +expected[c]*(std::exp(beta[c]*2*pathUncertainty/waterClarity)-1
                +2*fresnelUncertainty/(1-boundaryFresnel-fresnelUncertainty)+arithmeticBound(1,128));
        qualify(expected[c]>4*bound[c]&&actual[c]>bound[c],"source/actual RGB response is not resolved above full output/geometry error budget");
    }
    // All source/geometry/neutral/positive/zero/reflection controls have passed
    // before judging the absolute radiance algebra, so a failure here is RED.
    std::ofstream response(artifacts/"absolute-response.csv");
    response<<std::setprecision(14)<<"channel,actualD8,actualDeltaC4,baseC0,tagC0,actualGain,expectedGain,absoluteError,fullBound,exitFactor,pass\n";
    bool failed=false;
    for(int c=0;c<3;++c) {
        const bool pass=std::abs(actual[c]-expected[c])<=bound[c];failed=failed||!pass;
        response<<c<<","<<suppliedSun[offset+c]<<","<<double(actualTagged[offset+c])-actualBase[offset+c]<<","<<base.output[0][offset+c]
            <<","<<tagged.output[0][offset+c]<<","<<actual[c]<<","<<expected[c]<<","<<std::abs(actual[c]-expected[c])<<","<<bound[c]<<","<<exitFactor<<","<<pass<<"\n";
        std::cout<<std::setprecision(14)<<"DEBUG-water-radiance qualified channel="<<c<<" actual="<<actual[c]<<" expected="<<expected[c]<<" fullBound="<<bound[c]
            <<" ratio="<<actual[c]/expected[c]<<" pass="<<pass<<"\n";
    }
    response.flush();storage.flush();if(!response||!storage) throw std::runtime_error("Cannot save water-radiance response/storage evidence");
    qualify(glGetError()==GL_NO_ERROR,"final GL error");
    if(failed) throw std::runtime_error("RED qualified original water main: known direct receiver radiance must include the water-to-air directional exit conversion");
    std::cout<<"PASS GPU original water VS/FS: qualified flat1.5m known C8 RGB absolute radiance increment, positive/zero/reflection controls and whole-image neutrality/repeat; NOT natural shore/ambient/proxy/Iris acceptance\n";
}

#endif
