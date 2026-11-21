// NEW TEST ONLY. Agent builds/CPU-contracts; root exclusively executes GL.
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
#include <chrono>
#include <map>
#include <set>
#include <openssl/sha.h>
namespace frozenGHPhase {
#include "water_sun_prepared_main_probe.cpp"
}
namespace ghPhase {
namespace inherited=frozenGHPhase::preparedMain;
namespace prior=inherited::prior; namespace sun=inherited::sun;
namespace tracer=inherited::tracer; namespace old=inherited::old;
namespace light=inherited::light; namespace angular=inherited::angular;
namespace reason=inherited::reason; namespace support=inherited::support;
namespace fs=std::filesystem;
constexpr int size=inherited::size,outputs=inherited::outputs;
const std::string parentWaterSHA="dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4";
const std::string parentSunSHA="2a65aeec03f3ba645270b3672f9f01e69c50c5261dcdddfe87189a825c5fb9c9";
const std::string residualSHA="def6b357c619b42e437a533d5a0ee751272afa27ecc434206de9fd6a95bbfd9c";
// Includes inherited reason instrumentation, unlike the older native physical
// role which deliberately stripped it. Pin the actual b0fe ZIP expansion.
const std::string parentExpandedSHA="cbf8b6b9e631b804014d09b642126e828fee81610015b13b6ebe03837b59a09f";
const std::string parentPackSHA="b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452";
void require(bool condition,const std::string& why){if(!condition)throw std::runtime_error("INCONCLUSIVE GH-phase: "+why);}
struct Parent {std::array<std::string,3> geometry;std::string fragment,water,sunHelper,residual;};
Parent parent(const fs::path& root){
    Parent result;result.water=old::readText(root/"gbuffers_water.fsh");
    result.sunHelper=old::readText(root/"lib/water_residual_sun.glsl");result.residual=old::readText(root/"lib/water_residual.glsl");
    require(light::digest(result.water)==parentWaterSHA&&light::digest(result.sunHelper)==parentSunSHA&&light::digest(result.residual)==residualSHA,"frozen physical parent FS/helper pin differs");
    require(light::digest(old::readText(root/"lib/water_sun_support.glsl"))==inherited::preparedSHA,"prepared certificate pin differs");
    require(light::digest(old::readText(root/"lib/atmosphere.glsl"))==sun::atmosphereSHA,"native atmosphere pin differs");
    const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){result.geometry[i]=prior::expandOwner::expand(root/stages[i],root);require(light::digest(result.geometry[i])==prior::geometrySHA[i],"phase120 factor4 geometry pin differs");}
    result.fragment=prior::expandOwner::expand(root/"gbuffers_water.fsh",root);
    require(light::digest(result.fragment)==parentExpandedSHA,"expanded physical parent source pin differs");
    return result;
}
int cpuParent(const fs::path& root){const auto source=parent(root);std::cout<<"{\"schema\":\"aqualumen-gh-phase-cpu-parent-v1\",\"GLExecuted\":false,\"parent_sources_pinned\":true,\"geometry_stage_count\":3,\"expanded_parent_sha256\":"<<old::quote(light::digest(source.fragment))<<"}\n";return 0;}
std::string tag(const std::string& family,const std::string& name,const std::string& body){return "// AQUALUMEN_"+family+"_BEGIN:"+name+'\n'+body+"// AQUALUMEN_"+family+"_END:"+name+'\n';}
std::string phaseHelper(const std::string& original,int phase){
    require(phase==0||phase==45,"phase must be zero or45");
    auto result=inherited::replace(original,"#define AQUALUMEN_WATER_RESIDUAL\n","#define AQUALUMEN_WATER_RESIDUAL\n"+tag("GH_PHASE","DEFINE","#define WGP_GH_PHASE "+std::to_string(phase)+"\n"));
    const std::string node="        vec2 perturbation=vec2(rootX*nodes[x],crossTerm*nodes[x]+rootZ*nodes[z]);\n";
    return inherited::replace(result,node,tag("GH_PHASE","NODE_BEFORE","#if WGP_GH_PHASE == 0\n")+node+tag("GH_PHASE","NODE_AFTER",
        "#elif WGP_GH_PHASE == 45\n"
        "        vec2 WGP_standard=vec2(nodes[x]-nodes[z],nodes[x]+nodes[z])*0.7071067811865475244;\n"
        "        vec2 perturbation=vec2(rootX*WGP_standard.x,crossTerm*WGP_standard.x+rootZ*WGP_standard.y);\n"
        "#else\n#error Unapproved GH phase\n#endif\n"));
}
struct Sources {Parent original;std::array<std::string,2> physical,observer,metadata;};
void geometryAndArchive(const fs::path& root,const Parent& original){
    require(light::digest(old::readText(root.parent_path()/"GH-PHASE-original/parent.zip"))==parentPackSHA,"frozen archived parent ZIP pin differs");
    const char* stages[]={"gbuffers_water.vsh","gbuffers_water.tcs","gbuffers_water.tes"};
    for(int i=0;i<3;++i){require(prior::expandOwner::expand(root/stages[i],root)==original.geometry[i],"GH phase changed geometry");require(old::readText(root.parent_path()/("GH-PHASE-geometry-stage"+std::to_string(i)+".glsl"))==original.geometry[i],"archived geometry differs");}
    require(old::readText(root.parent_path()/"GH-PHASE-physical.fsh")==original.water,"archived physical water differs");
    require(old::readText(root.parent_path()/"GH-PHASE-physical-water_residual_sun.glsl")==original.sunHelper,"archived physical Sun helper differs");
}
std::string phaseMetadata(const fs::path& root,int phase,const std::string& role){
    const auto raw=old::readText(root.parent_path()/"WATER-GH-PHASE.json");require(raw.size()<=65536,"bounded phase metadata required");const auto metadata=inherited::JsonReader{raw}.parse();
    require(metadata.at("schema").str()=="aqualumen-water-gh-phase-v1"&&metadata.at("phase_degrees").integer()==phase&&metadata.at("role").str()==role,"phase metadata identity differs");
    require(metadata.at("parent_pack_sha256").str()==parentPackSHA&&metadata.at("test_only").flag()&&metadata.at("not_shipping").flag(),"phase TEST parent policy differs");
    require(!metadata.at("GL_accepted").flag()&&!metadata.at("Iris_accepted").flag()&&!metadata.at("shipping_accepted").flag(),"unexecuted acceptance claimed");return raw;
}
Sources physicalPhases(const std::array<fs::path,3>& roots){
    Sources result;result.original=parent(roots[0]);
    for(int mode=0;mode<2;++mode){const int phase=mode?45:0;const auto& root=roots[mode+1];geometryAndArchive(root,result.original);result.metadata[mode]=phaseMetadata(root,phase,"physical");
        const auto helper=phaseHelper(result.original.residual,phase);require(old::readText(root/"lib/water_residual.glsl")==helper,"actual GH perturbation differs from canonical rotation");
        require(old::readText(root/"lib/water_residual_sun.glsl")==result.original.sunHelper&&old::readText(root/"gbuffers_water.fsh")==result.original.water,"physical phase altered unchanged Sun/main");
        result.physical[mode]=inherited::replace(result.original.fragment,result.original.residual,helper);
        require(prior::expandOwner::expand(root/"gbuffers_water.fsh",root)==result.physical[mode]&&old::readText(root.parent_path()/"GH-PHASE-physical-expanded.fsh")==result.physical[mode],"physical phase expanded source recovery differs");
    }return result;
}
int cpuPhysicalPhase(const std::array<fs::path,3>& roots){physicalPhases(roots);std::cout<<"{\"GLExecuted\":false,\"phase0_literal_original_expression\":true,\"phase45_only_pre_Cholesky_rotation\":true}\n";return 0;}
std::string observedSun(const std::string& original){
    auto source=inherited::replace(original,"bool WNS_legacyApplied(); // removable bridge AFTER unchanged old helper\n","bool WNS_legacyApplied(); // removable bridge AFTER unchanged old helper\n"+tag("GH_OBSERVE","GLOBALS","vec4 WGP_readLegacyStatus();\nvec4 WGP_fullWR=vec4(0.0);\nvec4 WGP_baseWR=vec4(0.0);\n"));
    source=inherited::replace(source,"    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n","    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n"+tag("GH_OBSERVE","RESET","    WGP_fullWR=vec4(0.0);\n    WGP_baseWR=vec4(0.0);\n"));
    for(const auto& label:std::array<std::string,2>{"full","base"}){const auto anchor="    bool "+label+"Applied=WNS_legacyApplied();\n";source=inherited::replace(source,anchor,anchor+tag("GH_OBSERVE",label=="full"?"FULL":"BASE","    WGP_"+label+"WR=WGP_readLegacyStatus();\n"));}return source;
}
std::string observedWater(std::string source){
    const auto append=[&](const std::string& anchor,const std::string& name,const std::string& value){source=inherited::replace(source,anchor,anchor+tag("GH_OBSERVE",name,value));};
    source=inherited::replace(source,"/* RENDERTARGETS:0,9,10,11,12 */\n",tag("GH_OBSERVE","ROUTE","/* RENDERTARGETS:0,9,10,11,12,13,14,15 */\n"));
    append("bool WNS_legacyApplied() { return WR_status.y==1.0; }\n","BRIDGE","vec4 WGP_readLegacyStatus() { return WR_status; }\n");
    append("    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);\n","MAIN_RESET","    float WGP_callSeen=0.0;\n    float WGP_grazingResolved=0.0;\n");
    source=inherited::replace(source,"/* UNDERWATER_PROBE_END */\n        return;\n","/* UNDERWATER_PROBE_END */\n"+tag("GH_OBSERVE","NONWATER","        gl_FragData[5]=vec4(0.0);\n        gl_FragData[6]=vec4(0.0);\n        gl_FragData[7]=vec4(0.0);\n")+"        return;\n");
    append("        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n","GRAZING","        WGP_grazingResolved=resolved;\n");
    append("    if (aqualumenSunTestAuthorized==1) {\n","CALL","    WGP_callSeen=1.0;\n");
    return inherited::replace(source,"/* UNDERWATER_PROBE_END */\n}\n","/* UNDERWATER_PROBE_END */\n"+tag("GH_OBSERVE","STORE",
        "    gl_FragData[1]=WNS_reasons;\n"
        "    gl_FragData[2]=vec4(WNS_status.xy,WSP_counts.x+64.0*WSP_counts.y+4096.0*WSP_counts.z+262144.0*WSP_counts.w,WNS_status.w);\n"
        "    gl_FragData[3]=vec4(float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible),WGP_grazingResolved,float(receiverKind),reflectedHit.a);\n"
        "    gl_FragData[5]=WGP_fullWR;\n    gl_FragData[6]=WGP_baseWR;\n"
        "    gl_FragData[7]=vec4(max(color,vec3(0.0)),WGP_callSeen);\n")+"}\n");
}
std::string stripObservation(std::string source){
    const std::array<std::string,11> names={"GLOBALS","RESET","FULL","BASE","ROUTE","BRIDGE","MAIN_RESET","NONWATER","GRAZING","CALL","STORE"};
    for(const auto& name:names){const auto start="// AQUALUMEN_GH_OBSERVE_BEGIN:"+name+'\n',end="// AQUALUMEN_GH_OBSERVE_END:"+name+'\n';
        const auto at=source.find(start);require(at!=std::string::npos,"missing observation tag: "+name);source=tracer::eraseOne(source,start,end);
        if(name=="ROUTE")source.insert(at,"/* RENDERTARGETS:0,9,10,11,12 */\n");}
    require(source.find("AQUALUMEN_GH_OBSERVE_")==std::string::npos,"unexpected observation tag remains");return source;
}
Sources load(const std::array<fs::path,3>& roots){
    Sources result;result.original=parent(roots[0]);
    for(int mode=0;mode<2;++mode){const int phase=mode?45:0;const auto& root=roots[mode+1];geometryAndArchive(root,result.original);result.metadata[mode]=phaseMetadata(root,phase,"diagnostic");
        const auto residual=phaseHelper(result.original.residual,phase);require(old::readText(root/"lib/water_residual.glsl")==residual,"actual GH perturbation differs from canonical rotation");
        require(old::readText(root.parent_path()/"GH-PHASE-physical-water_residual.glsl")==residual,"archived phase residual differs");
        require(old::readText(root/"lib/water_residual_sun.glsl")==observedSun(result.original.sunHelper),"passive Sun status snapshot source differs");
        require(old::readText(root/"gbuffers_water.fsh")==observedWater(result.original.water),"passive water STORE/source differs");
        result.physical[mode]=inherited::replace(result.original.fragment,result.original.residual,residual);
        // The Sun source has nested includes; apply its exact passive anchors
        // to the expanded closure rather than replace an unexpanded file.
        result.observer[mode]=observedWater(observedSun(result.physical[mode]));
        require(old::readText(root.parent_path()/"GH-PHASE-physical-expanded.fsh")==result.physical[mode],"phase physical export differs");
        require(prior::expandOwner::expand(root/"gbuffers_water.fsh",root)==result.observer[mode]&&old::readText(root.parent_path()/"GH-PHASE-observed-expanded.fsh")==result.observer[mode],"actual included observation closure differs");
        require(stripObservation(result.observer[mode])==result.physical[mode],"observer does not recover its phase exactly");
    }return result;
}
int cpuContract(const std::array<fs::path,3>& roots){load(roots);std::cout<<"{\"schema\":\"aqualumen-gh-phase-cpu-contract-v1\",\"GLExecuted\":false,\"observer_recovers_each_phase_exact\":true,\"actual_water_draw_targets\":[0,9,10,11,12,13,14,15],\"source_Sun48_unchanged\":true,\"executed_Sun48_invariant_claim\":false}\n";return 0;}
bool pointAccounting(const float* values,int guard,bool positive){
    for(int i=0;i<32;++i)if(!std::isfinite(values[i]))return false;
    const float* why=values+4;const float* status=values+8;const float* main=values+12;
    const float* stage=values+16;const float* full=values+20;const float* base=values+24;const float* copy=values+28;
    if(stage[3]==0){for(int i=4;i<32;++i)if(values[i]!=0)return false;return true;}
    if(!prior::stageQualified(stage)||values[3]!=1||std::memcmp(values,copy,3*sizeof(float))!=0)return false;
    if(!reason::whole(main[0],15)||main[1]<0||main[1]>1||!reason::whole(main[2],2)||copy[3]!=guard)return false;
    const bool eligible=(int(main[0])&8)!=0;const int request=guard&&eligible;
    if(status[0]!=request||!reason::whole(status[1],1)||!reason::whole(status[3],48))return false;
    std::array<int,4> counts={};if(!support::countStatus(status[2],int(status[1]),int(status[3]),counts))return false;
    for(const auto* wr:{full,base}){
        if(!guard){for(int c=0;c<4;++c)if(wr[c]!=0)return false;}
        else if(!reason::whole(wr[0],1)||!reason::whole(wr[1],1)||!reason::whole(wr[3],18)||wr[1]!=int(eligible&&wr[0]==1))return false;
    }
    if(!request){for(int c=0;c<4;++c)if(why[c]!=0||status[c]!=0)return false;return true;}
    const std::array<float,4> originalStatus={status[0],status[1],0,status[3]};
    if(!reason::reasonAccounting(why,originalStatus.data(),1,positive))return false;
    if(!positive&&status[2]!=0)return false;
    return counts[2]<=status[3]&&counts[2]<=why[3]&&why[1]+why[2]+why[3]<=48-counts[0];
}
int cpuReadback(const fs::path& path,int guard,int positive){
    require((guard==0||guard==1)&&(positive==0||positive==1),"Boolean readback fixtures required");
    require(fs::is_regular_file(path)&&fs::file_size(path)==32*sizeof(float),"exact eight-slot binary32 point required");
    std::array<float,32> values={};std::ifstream input(path,std::ios::binary);input.read(reinterpret_cast<char*>(values.data()),sizeof(values));require(bool(input),"complete raw point required");
    require(pointAccounting(values.data(),guard,positive),"same-draw observation contract rejected");
    std::cout<<"{\"schema\":\"aqualumen-gh-phase-cpu-readback-v1\",\"GLExecuted\":false,\"syntheticOnly\":true,\"same_draw_copy_exact\":true,\"full_WR_valid_applied\":["<<values[20]<<','<<values[21]<<"],\"base_WR_valid_applied\":["<<values[24]<<','<<values[25]<<"],\"physical_accepted\":false}\n";return 0;
}
const std::array<std::string,5> labels={"parent","phase0-physical","phase0-observer","phase45-physical","phase45-observer"};
fs::path ownedOutput;
std::vector<float> rgb(const std::vector<float>& values){require(values.size()%4==0,"RGBA comparison input required");std::vector<float> result;result.reserve(values.size()/4*3);for(std::size_t p=0;p<values.size();p+=4)result.insert(result.end(),values.begin()+p,values.begin()+p+3);return result;}
void drawState(sun::Fixture& fixture,GLuint program,bool observer,const fs::path& directory){
    GLint current=0,fbo=0,viewport[4]={},patch=0;glGetIntegerv(GL_CURRENT_PROGRAM,&current);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&fbo);glGetIntegerv(GL_VIEWPORT,viewport);glGetIntegerv(GL_PATCH_VERTICES,&patch);
    require(current==GLint(program)&&fbo==GLint(fixture.fbo)&&viewport[0]==0&&viewport[1]==0&&viewport[2]==size&&viewport[3]==size&&patch==3&&!glIsEnabled(GL_CULL_FACE)&&!glIsEnabled(GL_BLEND),"actual draw state differs from immutable fixture");
    std::ostringstream out;out<<"{\"program\":"<<current<<",\"framebuffer\":"<<fbo<<",\"viewport\":[0,0,"<<size<<','<<size<<"],\"patch_vertices\":"<<patch<<",\"culling\":false,\"blend\":false,\"actual_draw_routes\":[";
    for(int slot=0;slot<outputs;++slot){GLint route=0,object=0,type=0;glGetIntegerv(GL_DRAW_BUFFER0+slot,&route);glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+slot,GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME,&object);glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+slot,GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE,&type);
        require(route==GLint(slot<(observer?8:5)?GL_COLOR_ATTACHMENT0+slot:GL_NONE)&&type==GL_TEXTURE&&object==GLint(fixture.targets[slot]),"actual draw route/attachment object differs");
        if(slot){out<<',';}out<<"{\"slot\":"<<slot<<",\"route\":"<<route<<",\"object_type\":"<<type<<",\"texture\":"<<object<<'}';}
    out<<"],\"queried_after_repeat_draw\":true}\n";old::writeText(directory/"actual-draw-state.json",out.str());old::glOkay("GH actual draw state query");
}
std::array<float,32> point(const old::Capture& frame,int p){std::array<float,32> result={};for(int slot=0;slot<8;++slot)std::copy_n(frame.images[slot].data()+p,4,result.data()+slot*4);return result;}
void samples(std::ostringstream& out,const std::array<old::Capture,5>& frames){
    out<<'[';for(std::size_t i=0;i<sun::pixels.size();++i){if(i)out<<',';const auto pixel=sun::pixels[i];const int p=(pixel.second*size+pixel.first)*4;out<<"{\"pixel\":["<<pixel.first<<','<<pixel.second<<"],\"phase_records\":[";
        for(int mode=0;mode<2;++mode){if(mode)out<<',';const auto values=point(frames[2+2*mode],p);angular::numbers(out,values);}out<<"]}";}out<<']';
}
int run(const std::array<fs::path,3>& roots,const fs::path& output){
    require(!fs::exists(output)&&!fs::is_symlink(output),"NEW output required");const auto source=load(roots);
    require(fs::create_directories(output),"cannot create NEW native output");ownedOutput=output;
    const std::array<std::string,5> fragments={source.original.fragment,source.physical[0],source.observer[0],source.physical[1],source.observer[1]};
    for(int i=0;i<5;++i)old::writeText(output/(labels[i]+"-expanded.fsh"),fragments[i]);
    for(int i=0;i<3;++i)old::writeText(output/("geometry-stage"+std::to_string(i)+".glsl"),source.original.geometry[i]);
    for(int mode=0;mode<2;++mode)old::writeText(output/("phase"+std::to_string(mode?45:0)+"-pack-metadata.json"),source.metadata[mode]);
    const auto host=old::readText("tools/water_gh_phase_probe.cpp");old::writeText(output/"probe-source.cpp",host);
    const auto executable=old::readText(fs::canonical("/proc/self/exe"));const auto sourceSHA=light::digest(host),binarySHA=light::digest(executable);
    const std::uint16_t endian=1;require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian host required");
    old::Context context;const auto* renderer=glGetString(GL_RENDERER);const auto* vendor=glGetString(GL_VENDOR);
    require(renderer&&vendor&&std::string(reinterpret_cast<const char*>(renderer)).find("RTX 3080 Ti")!=std::string::npos&&std::string(reinterpret_cast<const char*>(vendor)).find("NVIDIA")!=std::string::npos,"actual NVIDIA RTX3080Ti required");
    require(epoxy_has_gl_extension("GL_ARB_gpu_shader_fp64"),"actual fp64 extension required");GLint drawLimit=0,attachmentLimit=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&drawLimit);glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&attachmentLimit);require(drawLimit>=8&&attachmentLimit>=8,"eight actual color draw attachments required");sun::Fixture fixture;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-gh-phase-native-v1\",\"nativeGLExecuted\":true,\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"vendor\":"<<old::quote(reinterpret_cast<const char*>(vendor))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"GL_ARB_gpu_shader_fp64\":true,\"MAX_DRAW_BUFFERS\":"<<drawLimit<<",\"MAX_COLOR_ATTACHMENTS\":"<<attachmentLimit<<",\"size\":"<<size<<",\"fixed_phase_seconds\":120,\"probe_source_sha256\":"<<old::quote(sourceSHA)<<",\"executable_sha256\":"<<old::quote(binarySHA)<<",\"parent_pack_sha256\":"<<old::quote(parentPackSHA)<<",\"rawFormat\":\"little-endian binary32; bottom-left origin\",\"policy\":{\"parent_phase0_all5_bits_exact\":true,\"observer_C0_depth_TES_bits_exact\":true,\"C15_C0_RGB_bits_exact\":true,\"repeat_bits_exact\":true,\"central_ROI_center\":[128,128],\"central_ROI_radius\":40,\"central_ROI_points\":5025,\"phase45_admission_equality_required\":false},\"programs\":[";
    std::array<GLuint,5> programs={};for(int i=0;i<5;++i){if(i)report<<',';programs[i]=old::makeProgram({{GL_VERTEX_SHADER,source.original.geometry[0]},{GL_TESS_CONTROL_SHADER,source.original.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.original.geometry[2]},{GL_FRAGMENT_SHADER,fragments[i]}},labels[i],report);}report<<"],\"cases\":[";
    bool qualified=true,accepted=true;
    for(int scenario=0;scenario<6;++scenario){const bool wide=scenario>=4,positive=wide||scenario>=2;const int guard=wide?1:scenario%2,aperture=wide?(scenario==4?60:90):2;
        const std::string name=wide?"wide"+std::to_string(aperture)+"-cachepositive-guard1":"central2-cache"+std::string(positive?"positive":"zero")+"-guard"+std::to_string(guard);
        const auto directory=output/name;require(fs::create_directory(directory),"NEW case directory required");fixture.scene(2,0,positive,directory);if(aperture==60)reason::wideProjection(fixture);if(aperture==90)support::wide90(fixture);
        if(scenario){report<<',';}report<<"{\"path\":"<<old::quote(name)<<",\"aperture_degrees\":"<<aperture<<",\"positive_cache\":"<<(positive?"true":"false")<<",\"guard\":"<<guard<<",\"central_acceptance_case\":"<<(wide?"false":"true")<<",\"queried_program_sources\":[";
        tracer::Sources query;query.geometry=source.original.geometry;for(int mode=0;mode<2;++mode){if(mode)report<<',';sun::queriedSources(report,{programs[1+2*mode],programs[2+2*mode]},query,{fragments[1+2*mode],fragments[2+2*mode]});}report<<',';sun::queriedSources(report,{programs[0],programs[1]},query,{fragments[0],fragments[1]});report<<']';
        std::array<old::Capture,5> frames,repeats;std::array<std::vector<float>,8> inputReference={};
        for(int role=0;role<5;++role){const bool observer=role==2||role==4;frames[role]=prior::capture(fixture,programs[role],guard,observer,directory,labels[role]);repeats[role]=prior::capture(fixture,programs[role],guard,observer,directory,labels[role]+"-repeat");
            const auto inputDirectory=directory/(labels[role]+"-actual-inputs");require(fs::create_directory(inputDirectory),"NEW input directory required");drawState(fixture,programs[role],observer,inputDirectory);const auto inputs=sun::snapshotInputs(fixture,programs[role],inputDirectory);prior::guardSnapshot(programs[role],guard,inputDirectory,"actual-inputs");
            if(role)for(int unit=0;unit<8;++unit)require(inherited::bitsEqual(inputs[unit],inputReference[unit]),"actual input texture words differ across roles/phases");else inputReference=inputs;}
        report<<",\"comparisons\":[";bool first=true,caseAccepted=true;const auto compare=[&](const std::string& label,const std::vector<float>& a,const std::vector<float>& b){caseAccepted=inherited::exact(report,first,label,a,b)&&caseAccepted;};
        for(int role=0;role<5;++role){for(int slot=0;slot<8;++slot)compare(labels[role]+"-slot"+std::to_string(slot)+"-repeat",frames[role].images[slot],repeats[role].images[slot]);compare(labels[role]+"-depth-repeat",frames[role].depth,repeats[role].depth);}
        for(int slot=0;slot<5;++slot){compare("parent-phase0-physical-slot"+std::to_string(slot)+"-exact",frames[0].images[slot],frames[1].images[slot]);}compare("parent-phase0-physical-depth-exact",frames[0].depth,frames[1].depth);
        for(int mode=0;mode<2;++mode){const int physical=1+2*mode,observer=physical+1;const auto label="phase"+std::to_string(mode?45:0);
            compare(label+"-observer-C0-passive-exact",frames[physical].images[0],frames[observer].images[0]);compare(label+"-observer-depth-passive-exact",frames[physical].depth,frames[observer].depth);compare(label+"-observer-TES-passive-exact",frames[physical].images[4],frames[observer].images[4]);compare(label+"-same-draw-C15-C0-RGB-exact",rgb(frames[observer].images[0]),rgb(frames[observer].images[7]));}
        compare("crossphase-physical-depth-exact",frames[1].depth,frames[3].depth);compare("crossphase-physical-TES-exact",frames[1].images[4],frames[3].images[4]);
        std::array<int,2> stageWater={},accounted={},centralInput={},fullValid={},fullApplied={},baseValid={},baseApplied={},SunApplied={};std::array<long long,4> changedWR={},colorByWRChange={};long long changedSun=0,colorChanged=0;double sameAdmissionMax=0,changedAdmissionMax=0;bool phase0Application=true;
        std::vector<std::uint32_t> masks(size*size,0);
        for(int y=0;y<size;++y)for(int x=0;x<size;++x){const int pixel=y*size+x,p=pixel*4;std::array<std::array<float,32>,2> values={point(frames[2],p),point(frames[4],p)};
            for(int mode=0;mode<2;++mode){const auto& value=values[mode];const bool water=value[19]>0;stageWater[mode]+=water;accounted[mode]+=pointAccounting(value.data(),guard,positive);
                if(water){fullValid[mode]+=value[20]==1;fullApplied[mode]+=value[21]==1;baseValid[mode]+=value[24]==1;baseApplied[mode]+=value[25]==1;SunApplied[mode]+=value[9]==1;}
                if(!wide&&(x-128)*(x-128)+(y-128)*(y-128)<=1600){const bool domain=water&&prior::stageQualified(value.data()+16)&&value[3]==1&&value[12]==15&&value[31]==guard&&pointAccounting(value.data(),guard,positive);centralInput[mode]+=domain;
                    if(mode==0)phase0Application=phase0Application&&value[8]==guard&&value[9]==int(guard&&positive)&&value[11]==0&&(!guard||(value[20]==1&&value[21]==1&&value[24]==1&&value[25]==1));}}
            const int offsets[]={20,21,24,25};std::uint32_t mask=0;for(int i=0;i<4;++i)if(values[0][offsets[i]]!=values[1][offsets[i]]){mask|=1u<<i;++changedWR[i];}
            if(values[0][8]!=values[1][8]){mask|=16;}if(values[0][9]!=values[1][9]){mask|=32;++changedSun;}
            const bool changed=std::memcmp(values[0].data(),values[1].data(),3*sizeof(float))!=0;double delta=0;for(int c=0;c<3;++c)delta=std::max(delta,std::abs(double(values[0][c])-values[1][c]));
            if(changed){mask|=64;++colorChanged;for(int i=0;i<4;++i)colorByWRChange[i]+=(mask&(1u<<i))!=0;}
            if(mask&15)changedAdmissionMax=std::max(changedAdmissionMax,delta);else sameAdmissionMax=std::max(sameAdmissionMax,delta);masks[pixel]=mask;}
        const std::string maskRaw(reinterpret_cast<const char*>(masks.data()),masks.size()*sizeof(std::uint32_t));old::writeText(directory/"cross-phase-admission-mask.u32",maskRaw);
        const bool caseQualified=accounted[0]==size*size&&accounted[1]==size*size&&stageWater[0]>0&&stageWater[1]>0&&(wide||(centralInput[0]==5025&&centralInput[1]==5025));
        const bool originalApplication=wide||phase0Application;qualified=qualified&&caseQualified;accepted=accepted&&caseAccepted&&originalApplication;
        report<<"],\"canvas_points\":"<<size*size<<",\"stage_water_points\":";angular::numbers(report,stageWater);report<<",\"accounted_points\":";angular::numbers(report,accounted);report<<",\"central_input_domain_points\":";angular::numbers(report,centralInput);
        report<<",\"full_WR_valid_points\":";angular::numbers(report,fullValid);report<<",\"full_WR_applied_points\":";angular::numbers(report,fullApplied);report<<",\"base_WR_valid_points\":";angular::numbers(report,baseValid);report<<",\"base_WR_applied_points\":";angular::numbers(report,baseApplied);report<<",\"Sun_applied_points\":";angular::numbers(report,SunApplied);
        report<<",\"changed_WR_xy_counts_fullValid_fullApplied_baseValid_baseApplied\":";angular::numbers(report,changedWR);report<<",\"color_changed_points_with_each_WR_xy_change\":";angular::numbers(report,colorByWRChange);
        report<<",\"changed_Sun_applied_points\":"<<changedSun<<",\"color_changed_points\":"<<colorChanged<<",\"C0_RGB_max_delta_same_WR_xy\":"<<sameAdmissionMax<<",\"C0_RGB_max_delta_changed_WR_xy\":"<<changedAdmissionMax<<",\"cross_phase_mask_file\":\"cross-phase-admission-mask.u32\",\"cross_phase_mask_sha256\":"<<old::quote(light::digest(maskRaw))<<",\"fixed_six_samples\":";samples(report,frames);
        report<<",\"fixture_qualified\":"<<(caseQualified?"true":"false")<<",\"phase0_original_central_application_gate\":"<<(wide?"null":phase0Application?"true":"false")<<",\"source_input_passivity_accepted\":"<<(caseAccepted?"true":"false")<<'}';
    }
    const char* status=!qualified?"INCONCLUSIVE":accepted?"PASS":"RED";
    report<<"],\"case_count\":6,\"fixture_qualified\":"<<(qualified?"true":"false")<<",\"accepted\":"<<(qualified&&accepted?"true":"false")<<",\"status\":"<<old::quote(status)<<",\"physical_accepted\":false,\"visual_band_cause_proven\":false,\"cloud_scene_reproduced\":false,\"Iris_accepted\":false,\"pixel_AA_accepted\":false,\"FPS_accepted\":false,\"shipping_accepted\":false,\"covariance_exported\":false,\"source_Sun48_unchanged\":true,\"executed_Sun48_invariant_claim\":false,\"scope\":\"Actual four-stage native phase/passive-observer qualification only. Strict binary32 including signed zero; no crossphase color/admission equality or physical quality acceptance. Both original central input domains retain all5025 points; phase0 alone retains the old empirical application gate. Wide60/90 keep all raster maps and descriptive admission/color changes, not a quality gate. C15 RGB is same-water-invocation C0, C12 is interpolated TES marker not tess invocation/count. Actual clouds are BLACK in inherited open fixture, so fine-band/rim visual diagnosis still requires actual Iris cloud scenes. Status/counters cannot prove continuity, visibility, energy or correctness.\"}\n";
    old::writeText(output/"result.json",report.str());for(const auto program:programs)glDeleteProgram(program);std::cout<<status<<" GH-phase native "<<output<<'\n';return !qualified?2:accepted?0:1;
}
}
int main(int argc,char** argv){try{
    if(argc==3&&std::string(argv[1])=="--cpu-parent")return ghPhase::cpuParent(std::filesystem::absolute(argv[2]));
    if(argc==5&&std::string(argv[1])=="--cpu-readback")return ghPhase::cpuReadback(std::filesystem::absolute(argv[2]),std::stoi(argv[3]),std::stoi(argv[4]));
    if(argc==5&&std::string(argv[1])=="--cpu-physical-phase")return ghPhase::cpuPhysicalPhase({std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4])});
    if(argc==5&&std::string(argv[1])=="--cpu-contract")return ghPhase::cpuContract({std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4])});
    if(argc==5)return ghPhase::run({std::filesystem::absolute(argv[1]),std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3])},std::filesystem::absolute(argv[4]));
    std::cerr<<"usage: water_gh_phase_probe --cpu-contract PARENT_SHADERS PHASE0_DIAGNOSTIC PHASE45_DIAGNOSTIC\n       --cpu-parent PARENT_SHADERS | --cpu-physical-phase PARENT PHASE0_PHYSICAL PHASE45_PHYSICAL\n       --cpu-readback SYNTHETIC32.f32 GUARD POSITIVE_CACHE\n       PARENT_SHADERS PHASE0_DIAGNOSTIC PHASE45_DIAGNOSTIC NEW_OUTPUT\n";return 2;
}catch(const std::exception& failure){std::cerr<<failure.what()<<'\n';if(!ghPhase::ownedOutput.empty())try{ghPhase::old::writeText(ghPhase::ownedOutput/"failure.txt",std::string(failure.what())+'\n');}catch(...){}return 2;}}
