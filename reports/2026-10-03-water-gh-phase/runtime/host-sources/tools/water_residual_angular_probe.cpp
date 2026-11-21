// TEST ONLY. CPU construction/compilation; root exclusively owns GL execution.
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
#include <string>
#include <regex>
#include <limits>
#include <cstdint>
#include <cstddef>
#include <cstring>
namespace frozenResidualAngular {
#include "water_residual_interface_probe.cpp"
}
namespace angularProbe {
namespace tracer=frozenResidualAngular::waterResidualProbe;
namespace old=tracer::old;
namespace fs=std::filesystem;
const std::string sourceReturn="    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());\n";
const std::string sourceBegin="// ANGULAR_SOURCE_BEGIN\n",sourceEnd="// ANGULAR_SOURCE_END\n";
void require(bool value,const std::string& message){if(!value)throw std::runtime_error("INCONCLUSIVE residual-angular: "+message);}
std::string replaceOne(std::string source,const std::string& oldText,const std::string& newText){
    const auto at=source.find(oldText);require(at!=std::string::npos&&source.find(oldText,at+oldText.size())==std::string::npos,"replacement seam absent/ambiguous");source.replace(at,oldText.size(),newText);return source;
}
std::string sourceVariant(const std::string& source,const std::string& name,double sigma){
    require(source.find(sourceBegin)==std::string::npos&&source.find(sourceEnd)==std::string::npos,"existing angular source marker");
    std::string expression;
    if(name=="constant")expression="vec3(0.25,0.125,0.0625)";
    else if(name=="dark")expression="vec3(0.0)";
    else{require((name=="narrow"&&sigma==.00465)||(name=="broad"&&sigma==.08),"unapproved angular source");
        std::ostringstream value;value<<std::setprecision(17)<<sigma;
        expression="vec3(0.25,0.125,0.0625)*exp(-dot(normalize(ray)-vec3(0.0,1.0,0.0),normalize(ray)-vec3(0.0,1.0,0.0))/(2.0*"+value.str()+"*"+value.str()+"))";}
    return replaceOne(source,sourceReturn,sourceBegin+"    return sampleSky(lut,ray)+"+expression+";\n"+sourceEnd);
}
std::string recoverSource(std::string source){
    const auto at=source.find(sourceBegin);require(at!=std::string::npos&&source.find(sourceBegin,at+sourceBegin.size())==std::string::npos,"source marker absent/ambiguous");const auto end=source.find(sourceEnd,at);require(end!=std::string::npos&&source.find(sourceEnd,end+sourceEnd.size())==std::string::npos,"source end absent/ambiguous");source.replace(at,end+sourceEnd.size()-at,sourceReturn);return source;
}
struct Rule {int order;std::vector<double> nodes,weights;};
const std::array<Rule,3> rules={{{3,{-1.7320508075688772,0,1.7320508075688772},{1.0/6,2.0/3,1.0/6}},
    {9,{-4.512745863399784,-3.2054290028564694,-2.076847978677831,-1.0232556637891337,0,1.0232556637891337,2.076847978677831,3.2054290028564694,4.512745863399784},
       {2.2345844007746925e-05,.002789141321231767,.04991640676521791,.24409750289493967,.40634920634920674,.24409750289493967,.04991640676521791,.002789141321231767,2.2345844007746925e-05}},
    {17,{-6.889122439895331,-5.7444600786594044,-4.778531589629981,-3.900065717198009,-3.0737971753281905,-2.2810194402529875,-1.5098833077967422,-.7518426007038957,0,.7518426007038957,1.5098833077967422,2.2810194402529875,3.0737971753281905,3.900065717198009,4.778531589629981,5.7444600786594044,6.889122439895331},
        {2.5843149193916504e-11,2.8080161179304337e-08,4.01267944797981e-06,.00016849143155133964,.0028589460622846273,.023086657025710985,.09740637116272113,.226706308468977,.2995383701266052,.226706308468977,.09740637116272113,.023086657025710985,.0028589460622846273,.00016849143155133964,4.01267944797981e-06,2.8080161179304337e-08,2.5843149193916504e-11}}}};
const std::string ruleGuard="#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER 3\n#endif\n#if WATER_RESIDUAL_ORDER != 3\n#error This TEST slice implements only the declared order-three rule\n#endif\n";
const std::string ruleBody="    const float nodes[3]=float[3](-1.7320508075688772,0.0,1.7320508075688772);\n    const float weights[3]=float[3](1.0/6.0,2.0/3.0,1.0/6.0);\n    for (int x=0;x<3;++x) for (int z=0;z<3;++z) {\n";
const std::string guardBegin="// ANGULAR_RULE_GUARD_BEGIN\n",guardEnd="// ANGULAR_RULE_GUARD_END\n",bodyBegin="// ANGULAR_RULE_BODY_BEGIN\n",bodyEnd="// ANGULAR_RULE_BODY_END\n";
const Rule& getRule(int order){for(const auto& rule:rules)if(rule.order==order)return rule;throw std::runtime_error("INCONCLUSIVE residual-angular: unapproved quadrature order");}
std::string arrayText(const std::vector<double>& values){std::ostringstream out;out<<std::scientific<<std::setprecision(17);for(std::size_t i=0;i<values.size();++i){if(i)out<<',';out<<values[i];}return out.str();}
std::string ruleVariant(const std::string& source,int order){
    const auto& rule=getRule(order);require(source.find(guardBegin)==std::string::npos&&source.find(bodyBegin)==std::string::npos,"existing rule marker");
    // Validate the original guard/body even when retaining GH3 byte-for-byte.
    replaceOne(source,ruleGuard,ruleGuard);replaceOne(source,ruleBody,ruleBody);if(order==3)return source;
    const auto n=std::to_string(order);const auto guard=guardBegin+"#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER "+n+"\n#endif\n#if WATER_RESIDUAL_ORDER != "+n+"\n#error Angular TEST rule must match declared order\n#endif\n"+guardEnd;
    const auto body=bodyBegin+"    const float nodes["+n+"]=float["+n+"]("+arrayText(rule.nodes)+");\n    const float weights["+n+"]=float["+n+"]("+arrayText(rule.weights)+");\n    for (int x=0;x<"+n+";++x) for (int z=0;z<"+n+";++z) {\n"+bodyEnd;
    return replaceOne(replaceOne(source,ruleGuard,guard),ruleBody,body);
}
std::string recoverBlock(std::string source,const std::string& begin,const std::string& end,const std::string& replacement){
    const auto at=source.find(begin);require(at!=std::string::npos&&source.find(begin,at+begin.size())==std::string::npos,"rule marker absent/ambiguous");const auto finish=source.find(end,at);require(finish!=std::string::npos&&source.find(end,finish+end.size())==std::string::npos,"rule end absent/ambiguous");source.replace(at,finish+end.size()-at,replacement);return source;
}
std::string recoverRule(const std::string& source,int order){return order==3?source:recoverBlock(recoverBlock(source,guardBegin,guardEnd,ruleGuard),bodyBegin,bodyEnd,ruleBody);}
void moments(){for(const auto& rule:rules){require(rule.nodes.size()==std::size_t(rule.order)&&rule.weights.size()==rule.nodes.size(),"rule array arity");
    for(int degree=0;degree<2*rule.order;++degree){double value=0,expected=degree%2?0:1;for(int k=2;k<=degree;k+=2)expected*=k-1;
        double scale=0;for(std::size_t i=0;i<rule.nodes.size();++i){require(rule.weights[i]>0&&std::isfinite(rule.nodes[i]),"nonpositive/nonfinite rule");const double term=rule.weights[i]*std::pow(rule.nodes[i],degree);value+=term;scale+=std::abs(term);}
        require(std::abs(value-expected)<=2e-11*std::max({1.0,std::abs(expected),scale}),"standard normal rule moment failed");}
    for(int degree:{0,1,2,4}){double value=0;for(std::size_t i=0;i<rule.nodes.size();++i)value+=double(float(rule.weights[i]))*std::pow(double(float(rule.nodes[i])),degree);const double expected=degree==4?3:degree==1?0:1;require(std::abs(value-expected)<=2e-6,"binary32 rule moment failed");}
}}
std::string observed(const std::string& source){
    auto result=replaceOne(tracer::observed(source,true),"    gl_FragData[5]=WR_sources;\n","    gl_FragData[5]=vec4(v,float(residualEligible));\n");
    require(tracer::recoveredObserver(result)==source,"eye-ray observer recovery differs from actual main");return result;
}
int cpuContract(const fs::path& parent,const fs::path& test){
    const auto loaded=tracer::load(parent,test);
    const auto gaussian=sourceVariant(loaded.active,"narrow",.00465);
    require(gaussian!=loaded.active&&gaussian.find(sourceReturn)==std::string::npos,"public narrow source must replace analytic disks");
    require(recoverSource(gaussian)==loaded.active,"source removal must recover exact actual main");
    require(ruleVariant(gaussian,9)!=gaussian,"public GH9 rule must differ from GH3");
    moments();for(const auto& rule:rules){const auto variant=ruleVariant(gaussian,rule.order);require(recoverRule(variant,rule.order)==gaussian,"only rule guard/arrays/loop bounds may differ");require(rule.order!=3||variant==gaussian,"GH3 must remain untouched");}
    const auto observer=observed(gaussian);require(observer.find("    gl_FragData[5]=vec4(v,float(residualEligible));\n")!=std::string::npos,"public observer must expose the actual eye ray, not source masses");
    require(tracer::recoveredObserver(observer)==gaussian,"observer removal must recover exact main");
    for(const auto& name:{"narrow","broad","constant","dark"}){const double sigma=std::string(name)=="narrow"?.00465:std::string(name)=="broad"?.08:0;
        const auto light=sourceVariant(loaded.active,name,sigma);require(recoverSource(light)==loaded.active,"each source must recover original");
        for(const auto& rule:rules){const auto source=ruleVariant(light,rule.order);require(recoverSource(recoverRule(tracer::recoveredObserver(observed(source)),rule.order))==loaded.active,"combined recovery differs");}}
    bool rejected=false;try{sourceVariant(loaded.active+sourceReturn,"narrow",.00465);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous environment return must reject");
    rejected=false;try{ruleVariant(loaded.active+ruleBody,9);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous rule must reject");
    rejected=false;try{tracer::load(parent,test);tracer::disabled(loaded.active+tracer::hookBegin);}catch(const std::exception&){rejected=true;}require(rejected,"ambiguous main hook must reject");
    std::cout<<"PASS CPU all4 source/all3 rule/eye-STORE exact recovery, GH double+binary32 moments, ambiguous seams rejection; no GL execution\n";return 0;
}
constexpr int size=tracer::size,outputs=tracer::outputs;
bool ownedArtifacts=false;
template<class Values> void numbers(std::ostringstream& out,const Values& values){out<<'[';for(std::size_t i=0;i<values.size();++i){if(i)out<<',';out<<values[i];}out<<']';}
void four(std::ostringstream& out,const float* values){numbers(out,std::array<float,4>{values[0],values[1],values[2],values[3]});}
void openBlack(tracer::Fixture& fixture,const fs::path& directory){
    fixture.scenario(false,false,directory);const float y=fixture.surface;
    auto a=old::vertex(-.9f,y,-.9f),b=old::vertex(-.9f,y,.9f),c=old::vertex(.9f,y,.9f),d=old::vertex(.9f,y,-.9f);
    std::vector<old::Vertex> vertices={a,b,c,a,c,d};for(auto& vertex:vertices){vertex.lightmap[0]=0;vertex.lightmap[1]=1;}
    fixture.upload(vertices,directory/"uploaded-open-water-vertices.f32");
    std::vector<float> black(64*32*4,0);for(std::size_t p=3;p<black.size();p+=4)black[p]=1;
    for(int unit:{2,7})old::Fixture::allocate(fixture.samplers[unit],GL_RGBA32F,64,32,GL_RGBA,black.data());
    old::glOkay("black sky and solar cache fixture");
}
old::Capture draw(tracer::Fixture& fixture,GLuint program,bool observer,const fs::path& directory,const std::string& label){
    fixture.uniforms(program);glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);
    std::array<GLenum,outputs> buffers={};for(int i=0;i<outputs;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
    glDrawBuffers(outputs,buffers.data());const float zero[4]={},one=1;
    for(int i=0;i<outputs;++i){glClearBufferfv(GL_COLOR,i,zero);}
    glClearBufferfv(GL_DEPTH,0,&one);
    // Pure original main writes slots0-4; slots5-7 remain cleared inactive storage.
    glDrawBuffers(observer?outputs:5,buffers.data());glDrawArrays(GL_PATCHES,0,6);old::Capture capture;
    for(int i=0;i<outputs;++i){auto& values=capture.images[i];values.assign(size*size*4,NAN);glReadBuffer(buffers[i]);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,values.data());
        require(std::all_of(values.begin(),values.end(),[](float value){return std::isfinite(value);}),"nonfinite actual MRT");old::writeRaw(directory/(label+"-slot"+std::to_string(i)+".rgba32f"),values);}
    capture.depth.assign(size*size,NAN);glReadPixels(0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,capture.depth.data());
    require(std::all_of(capture.depth.begin(),capture.depth.end(),[](float value){return std::isfinite(value);}),"nonfinite actual depth");old::writeRaw(directory/(label+"-depth.f32"),capture.depth);old::glOkay("angular actual-main draw/readback");return capture;
}
std::array<std::vector<float>,8> snapshotInputs(tracer::Fixture& fixture,GLuint program,const fs::path& directory){
    fixture.uniforms(program);GLint activeBefore=0,programBefore=0,bindingBefore=0;glGetIntegerv(GL_ACTIVE_TEXTURE,&activeBefore);glGetIntegerv(GL_CURRENT_PROGRAM,&programBefore);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bindingBefore);
    require(programBefore==GLint(program),"actual observer program differs");std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-native-residual-angular-inputs-v1\",\"program\":"<<program<<",\"currentProgramBefore\":"<<programBefore<<",\"activeTextureBefore\":"<<activeBefore<<",\"textureBindingBefore\":"<<bindingBefore<<",\"matrices\":{";
    const std::array<std::pair<const char*,old::M4>,4> matrices={{{"gbufferProjection",fixture.projection},{"gbufferProjectionInverse",fixture.inverseProjection},{"gbufferModelView",old::up},{"gbufferModelViewInverse",old::upInverse}}};
    for(std::size_t i=0;i<matrices.size();++i){const char* name=matrices[i].first;const GLint location=glGetUniformLocation(program,name);GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);GLint type=0,count=0;
        require(location>=0&&index!=GL_INVALID_INDEX,"actual matrix absent");glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&count);require(type==GL_FLOAT_MAT4&&count==1,"actual matrix type/count differs");old::M4 actual={};glGetUniformfv(program,location,actual.data());require(actual==matrices[i].second,"actual queried matrix differs from uploaded fixture");if(i)report<<',';report<<old::quote(name)<<':';numbers(report,actual);}
    old::M4 fixedProjection={},fixedView={};glGetFloatv(GL_PROJECTION_MATRIX,fixedProjection.data());glGetFloatv(GL_MODELVIEW_MATRIX,fixedView.data());require(fixedProjection==fixture.projection&&fixedView==old::up,"actual fixed-function matrices differ");report<<"},\"fixedFunctionProjection\":";numbers(report,fixedProjection);report<<",\"fixedFunctionModelView\":";numbers(report,fixedView);
    const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
    std::array<std::vector<float>,8> inputs={};report<<",\"samplers\":[";
    for(int unit=0;unit<8;++unit){glActiveTexture(GL_TEXTURE0+unit);GLint bound=0,sampler=0,uniformUnit=-1;glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);glGetUniformiv(program,glGetUniformLocation(program,names[unit]),&uniformUnit);require(GLuint(bound)==fixture.samplers[unit]&&sampler==0&&uniformUnit==unit,"actual sampler binding differs");
        GLint format=0,w=0,h=0,minFilter=0,magFilter=0,compareMode=0,wrapS=0,wrapT=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,&minFilter);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,&magFilter);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,&compareMode);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,&wrapS);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,&wrapT);
        const int widths[]={1,size,64,size,1,1,64,64},heights[]={1,size,32,size,1,1,64,32};const int formats[]={GL_RGBA32F,GL_RGBA32F,GL_RGBA32F,GL_DEPTH_COMPONENT32F,GL_DEPTH_COMPONENT32F,GL_RGBA16F,GL_RGBA32F,GL_RGBA32F};require(w==widths[unit]&&h==heights[unit]&&format==formats[unit]&&minFilter==GL_NEAREST&&magFilter==GL_NEAREST,"actual input storage/filter differs");const int components=(unit==3||unit==4)?1:4;auto& values=inputs[unit];values.assign(std::size_t(w)*h*components,NAN);glGetTexImage(GL_TEXTURE_2D,0,components==1?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,values.data());require(std::all_of(values.begin(),values.end(),[](float value){return std::isfinite(value);}),"nonfinite actual input texture");
        if(unit==2||unit==7){for(std::size_t p=0;p<values.size();p+=4)require(values[p]==0&&values[p+1]==0&&values[p+2]==0&&values[p+3]==1,"sky/cache must be black, including reserved solar row");}
        if(unit==3)require(std::all_of(values.begin(),values.end(),[](float value){return value==1;}),"opaque depth must be open sky");
        const std::string file="input-sampler"+std::to_string(unit)+(components==1?".f32":".rgba32f");old::writeRaw(directory/file,values);if(unit)report<<',';report<<"{\"unit\":"<<unit<<",\"name\":"<<old::quote(names[unit])<<",\"texture\":"<<bound<<",\"internalFormat\":"<<format<<",\"width\":"<<w<<",\"height\":"<<h<<",\"components\":"<<components<<",\"minFilter\":"<<minFilter<<",\"magFilter\":"<<magFilter<<",\"compareMode\":"<<compareMode<<",\"wrapS\":"<<wrapS<<",\"wrapT\":"<<wrapT<<",\"file\":"<<old::quote(file)<<'}';}
    report<<"],\"targets\":[";for(int i=0;i<=outputs;++i){const GLuint texture=i==outputs?fixture.depth:fixture.targets[i];glBindTexture(GL_TEXTURE_2D,texture);GLint format=0,w=0,h=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&w);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&h);require(w==size&&h==size&&format==GLint(i==outputs?GL_DEPTH_COMPONENT32F:GL_RGBA32F),"actual MRT/depth storage differs");if(i==outputs)report<<"],\"depth\":";else if(i)report<<',';report<<"{\"slot\":"<<i<<",\"texture\":"<<texture<<",\"internalFormat\":"<<format<<",\"width\":"<<w<<",\"height\":"<<h<<'}';}
    glBindTexture(GL_TEXTURE_2D,fixture.samplers[7]);glActiveTexture(GLenum(activeBefore));GLint activeAfter=0,programAfter=0,bindingAfter=0;glGetIntegerv(GL_ACTIVE_TEXTURE,&activeAfter);glGetIntegerv(GL_CURRENT_PROGRAM,&programAfter);glGetIntegerv(GL_TEXTURE_BINDING_2D,&bindingAfter);require(activeAfter==activeBefore&&programAfter==programBefore&&bindingAfter==bindingBefore,"input query state did not restore");report<<",\"currentProgramAfter\":"<<programAfter<<",\"activeTextureAfter\":"<<activeAfter<<",\"textureBindingAfter\":"<<bindingAfter<<",\"bindingRestored\":true}";old::writeText(directory/"actual-inputs.json",report.str()+"\n");old::glOkay("actual queried storage/input matrices");return inputs;
}
bool domain(const old::Capture& frame,int p){const auto& flags=frame.images[6];const auto& status=frame.images[4];return flags[p]==1&&flags[p+1]==1&&flags[p+2]==1&&flags[p+3]==1&&frame.images[5][p+3]==1&&frame.images[7][p+3]==1&&status[p]==1&&status[p+1]==1&&status[p+2]>0&&status[p+3]==0;}
std::vector<float> channels(const std::vector<float>& rgba,bool alpha){std::vector<float> result;result.reserve(rgba.size()/(alpha?4:1));for(std::size_t p=0;p<rgba.size();p+=4){if(alpha)result.push_back(rgba[p+3]);else for(int c=0;c<3;++c)result.push_back(rgba[p+c]);}return result;}
constexpr double crossArithmetic=8*std::numeric_limits<float>::epsilon();
int run(const fs::path& parent,const fs::path& test,const fs::path& artifacts){
    static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,"binary32 raw format");const std::uint32_t endian=1;require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little endian raw export required");
    require(!fs::exists(artifacts)&&!fs::is_symlink(artifacts),"NEW artifacts required");cpuContract(parent,test);const auto loaded=tracer::load(parent,test);require(fs::create_directories(artifacts),"cannot create artifact directory");ownedArtifacts=true;
    old::writeText(artifacts/"source-original-expanded.fsh",loaded.active);old::writeText(artifacts/"parent-expanded.fsh",loaded.parent);for(int i=0;i<3;++i)old::writeText(artifacts/("geometry-stage"+std::to_string(i)+".glsl"),loaded.geometry[i]);
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);require(renderer&&std::string(reinterpret_cast<const char*>(renderer)).find("NVIDIA")!=std::string::npos,"actual NVIDIA renderer required");tracer::Fixture fixture;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-native-residual-angular-v1\",\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"sourceUnits\":\"fixed-peak directional radiance; CHORD Gaussian, not calibrated solar beam\",\"geometry_sources_identical\":true,\"disabled_source_recovers_parent_exact\":true,\"observer_recovers_original_exact\":true,\"source_transform_recovers_original_exact\":true,\"rule_transform_recovers_original_exact\":true,\"culling_enabled\":false,\"pure_draw_buffer_slots\":[0,1,2,3,4],\"pure_cleared_inactive_slots\":[5,6,7],\"observer_slot5\":\"actual viewToEye xyz / residualEligible\",\"rawFormat\":\"little-endian binary32 bottom-left origin\",\"policy\":{\"C0_absolute\":"<<tracer::passiveAbsolute<<",\"C0_relative\":"<<tracer::passiveRelative<<",\"depth_absolute\":"<<tracer::depthTolerance<<",\"coefficient_absolute\":"<<tracer::coefficientTolerance<<",\"double_moment_scaled\":2e-11,\"binary32_moment_absolute\":2e-6,\"ROI_center\":[128,128],\"ROI_integer_radius\":40,\"peak_fraction\":0.2,\"component_neighbors\":8,\"luminance\":[0.2126,0.7152,0.0722]},\"cases\":[";
    bool qualified=true,firstCase=true;std::array<std::vector<float>,8> referenceInputs={};old::Capture reference;bool haveReference=false;
    for(const auto& sourceName:{"narrow","broad","constant","dark"})for(const auto& rule:rules){const std::string name=sourceName;const double sigma=name=="narrow"?.00465:name=="broad"?.08:0;const std::string path=name+"-gh"+std::to_string(rule.order);const auto directory=artifacts/path;fs::create_directory(directory);
        const auto pureSource=ruleVariant(sourceVariant(loaded.active,name,sigma),rule.order),observerSource=observed(pureSource);require(recoverSource(recoverRule(tracer::recoveredObserver(observerSource),rule.order))==loaded.active,"compiled source recovery failed");old::writeText(directory/"pure-expanded.fsh",pureSource);old::writeText(directory/"observer-expanded.fsh",observerSource);
        if(!firstCase){report<<',';}
        firstCase=false;report<<"{\"source\":"<<old::quote(name)<<",\"sigma\":";if(sigma)report<<sigma;else report<<"null";report<<",\"rule\":"<<rule.order<<",\"path\":"<<old::quote(path)<<",\"programs\":[";
        std::array<GLuint,2> programs={};for(int i=0;i<2;++i){if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,loaded.geometry[0]},{GL_TESS_CONTROL_SHADER,loaded.geometry[1]},{GL_TESS_EVALUATION_SHADER,loaded.geometry[2]},{GL_FRAGMENT_SHADER,i?observerSource:pureSource}},path+(i?"-observer":"-pure"),report);}
        report<<"],\"program_ids\":["<<programs[0]<<','<<programs[1]<<']';openBlack(fixture,directory);
        const auto pure=draw(fixture,programs[0],false,directory,"pure"),pureRepeat=draw(fixture,programs[0],false,directory,"pure-repeat"),observer=draw(fixture,programs[1],true,directory,"observer"),observerRepeat=draw(fixture,programs[1],true,directory,"observer-repeat");const auto inputs=snapshotInputs(fixture,programs[1],directory);
        report<<",\"comparisons\":[";bool first=true,caseQualified=true;
        for(int slot=0;slot<outputs;++slot){caseQualified=tracer::compare(report,first,"pure-slot"+std::to_string(slot)+"-repeat",pure.images[slot],pureRepeat.images[slot],0)&&caseQualified;caseQualified=tracer::compare(report,first,"observer-slot"+std::to_string(slot)+"-repeat",observer.images[slot],observerRepeat.images[slot],0)&&caseQualified;}
        caseQualified=tracer::compare(report,first,"pure-depth-repeat",pure.depth,pureRepeat.depth,0)&&caseQualified;caseQualified=tracer::compare(report,first,"observer-depth-repeat",observer.depth,observerRepeat.depth,0)&&caseQualified;caseQualified=tracer::compare(report,first,"observer-C0-passive",pure.images[0],observer.images[0],tracer::passiveAbsolute,tracer::passiveRelative)&&caseQualified;caseQualified=tracer::compare(report,first,"observer-depth-passive",pure.depth,observer.depth,tracer::depthTolerance)&&caseQualified;
        if(haveReference){require(inputs==referenceInputs,"actual immutable inputs changed across source/rule");
            for(int slot:{1,5,7}){caseQualified=tracer::compare(report,first,"common-slot"+std::to_string(slot)+"-xyz-EPS8",channels(reference.images[slot],false),channels(observer.images[slot],false),crossArithmetic,crossArithmetic)&&caseQualified;
                caseQualified=tracer::compare(report,first,"common-slot"+std::to_string(slot)+"-alpha-exact",channels(reference.images[slot],true),channels(observer.images[slot],true),0)&&caseQualified;}
            for(int slot:{2,6}){caseQualified=tracer::compare(report,first,"common-slot"+std::to_string(slot)+"-exact",reference.images[slot],observer.images[slot],0)&&caseQualified;}
            caseQualified=tracer::compare(report,first,"common-depth-exact",reference.depth,observer.depth,0)&&caseQualified;
        }else{reference=observer;referenceInputs=inputs;haveReference=true;}
        report<<"],\"samples\":[";for(std::size_t s=0;s<tracer::pixels.size();++s){const auto pixel=tracer::pixels[s];const int p=(pixel.second*size+pixel.first)*4;const auto* coeff=&observer.images[3][p];const auto* cov=&observer.images[2][p];const double determinant=double(cov[0])*cov[2]-double(cov[1])*cov[1];const bool coefficientOkay=std::abs(double(coeff[0])-1)<=tracer::coefficientTolerance&&coeff[1]>=0&&coeff[2]>=0&&coeff[3]>=0&&coeff[3]<=coeff[1]+tracer::coefficientTolerance&&std::abs(double(coeff[1])+coeff[2]-coeff[0])<=tracer::coefficientTolerance;
            const bool sampleDomain=domain(observer,p)&&observer.images[1][p+3]==1&&observer.images[2][p+3]==.035f&&cov[0]>=0&&cov[2]>=0&&determinant>=0&&double(cov[0])+cov[2]>tracer::covarianceTraceMinimum;caseQualified=sampleDomain&&coefficientOkay&&caseQualified;
            double constantError=0;if(name=="constant"||name=="dark"){for(int c=0;c<3;++c){const double expected=double(observer.images[7][p+c])*coeff[1]+(name=="constant"?double(tracer::constantTag[c])*coeff[2]:0);constantError=std::max(constantError,std::abs(double(observer.images[0][p+c])-expected));}caseQualified=constantError<=tracer::coefficientTolerance&&caseQualified;}
            if(s){report<<',';}
            report<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"normal_grazing\":";four(report,&observer.images[1][p]);report<<",\"covariance_footprint\":";four(report,cov);report<<",\"coefficients\":";four(report,coeff);report<<",\"status\":";four(report,&observer.images[4][p]);report<<",\"eye_eligible\":";four(report,&observer.images[5][p]);report<<",\"production_flags\":";four(report,&observer.images[6][p]);report<<",\"scatter_eligible\":";four(report,&observer.images[7][p]);report<<",\"C0\":";four(report,&observer.images[0][p]);report<<",\"domainQualified\":"<<(sampleDomain?"true":"false")<<",\"coefficientQualified\":"<<(coefficientOkay?"true":"false")<<",\"constant_source_max_absolute\":"<<constantError<<'}';}
        int roiPoints=0,roiDomainPoints=0;for(int y=128-40;y<=128+40;++y)for(int x=128-40;x<=128+40;++x)if((x-128)*(x-128)+(y-128)*(y-128)<=40*40){++roiPoints;if(domain(observer,(y*size+x)*4))++roiDomainPoints;}
        const bool domainQualified=roiPoints==roiDomainPoints;caseQualified=domainQualified&&caseQualified;qualified=qualified&&caseQualified;report<<"],\"ROI_points\":"<<roiPoints<<",\"ROI_domain_points\":"<<roiDomainPoints<<",\"domainQualified\":"<<(domainQualified?"true":"false")<<",\"qualified\":"<<(caseQualified?"true":"false")<<'}';for(auto program:programs)glDeleteProgram(program);
    }
    report<<"],\"accepted\":"<<(qualified?"true":"false")<<",\"status\":"<<old::quote(qualified?"PASS":"INCONCLUSIVE")<<",\"quality_accepted\":false,\"energy_accepted\":false,\"Iris_accepted\":false,\"natural_accepted\":false,\"shipping_accepted\":false,\"scope\":\"Actual original-main derivative-free CHORD Gaussian source/rule diagnostic only. Fixed peak radiance, not calibrated Sun/beam. No survival renormalization. Domain failure is INCONCLUSIVE. No critical-angle/visibility-tail/energy/reciprocity/appearance/motion/FPS adoption.\"}\n";old::writeText(artifacts/"result.json",report.str());std::cout<<(qualified?"PASS":"INCONCLUSIVE")<<" actual-main residual-angular observations "<<artifacts<<'\n';return qualified?0:2;
}
}
int main(int argc,char** argv){try{if(argc==4&&std::string(argv[1])=="--cpu-contract")return angularProbe::cpuContract(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));if(argc==4)return angularProbe::run(std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));std::cerr<<"usage: water_residual_angular_probe <resolved-parent-shaders> <residual-shaders> <NEW-artifacts>\n       water_residual_angular_probe --cpu-contract <resolved-parent-shaders> <residual-shaders>\n";return 2;}catch(const std::exception& error){std::cerr<<error.what()<<'\n';if(angularProbe::ownedArtifacts)try{angularProbe::old::writeText(std::filesystem::absolute(argv[3])/"failure.txt",std::string(error.what())+'\n');}catch(...){}return 2;}}
