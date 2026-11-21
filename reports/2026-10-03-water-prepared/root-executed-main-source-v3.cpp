// NEW TEST ONLY: CPU construction is agent-runnable; root exclusively owns GL.
// This translation unit reuses, but never edits, the pinned public-main seam.
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
namespace retainedPreparedMain {
#include "water_sun_support_probe.cpp"
}
namespace preparedMain {
namespace support=retainedPreparedMain::supportProbe;
namespace prior=support::prior; namespace priorMain=support::priorMain;
namespace sun=support::sun; namespace reason=support::reason;
namespace tracer=support::tracer; namespace old=support::old;
namespace angular=support::angular; namespace light=support::light;
namespace fs=std::filesystem;
constexpr int size=support::size,outputs=support::outputs;
static_assert(outputs==8,"separate all48 observer requires eight existing targets");
const std::string preparedSHA="ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441";
const std::string oldProbeSHA="f4c1b8b3d2dd9e7085bddd57ee1b9e848d2979558300d732e77d928752800f02";
const std::string corpusSHA="24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48";
const std::string nodeUtilitiesSHA="f183963ee155c89dcbd8be3e36ccd7d313ccadccde4d1d9bb5b4c2ab16ae16f7";
const std::string nodeFixtureSHA="f4abe4cbde553c44258e2c2f2f9e437809f67af9c350823ac4627dcfb1a5bb67";
const std::string oldCall="        int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);\n";
const std::string newCall="        int WSP_supportClass=waterSunSupportClassPrepared(WPM_viewContext,target);\n";
const std::string contextBegin="// AQUALUMEN_PREPARED_MAIN_CONTEXT_BEGIN\n";
const std::string contextEnd="// AQUALUMEN_PREPARED_MAIN_CONTEXT_END\n";
const std::string context="    WSPViewContext WPM_viewContext=waterSunSupportPrepareView(viewToEye,eta);\n";
const std::array<std::string,4> roles={"physical","reasons","inputs","all48"};
const std::array<std::string,2> modes={"old","prepared"};
fs::path ownedOutput;
void require(bool okay,const std::string& why){if(!okay)throw std::runtime_error("INCONCLUSIVE prepared main: "+why);}
std::size_t occurrences(const std::string& source,const std::string& needle){
    std::size_t count=0,at=0;while((at=source.find(needle,at))!=std::string::npos){++count;at+=needle.size();}return count;
}
std::string replace(const std::string& source,const std::string& needle,const std::string& replacement){
    require(occurrences(source,needle)==1,"absent/ambiguous replacement anchor");
    auto result=source;result.replace(result.find(needle),needle.size(),replacement);return result;
}
std::string observerSpan(const std::string& name,const std::string& code){
    return "// AQUALUMEN_PREPARED_TARGET_BEGIN:"+name+"\n"+code+"// AQUALUMEN_PREPARED_TARGET_END:"+name+"\n";
}
std::string stripObserver(std::string source){
    for(const auto& name:std::array<std::string,5>{"GLOBALS","RESET","TARGET","NODE","STORE"}){
        source=tracer::eraseOne(source,"// AQUALUMEN_PREPARED_TARGET_BEGIN:"+name+"\n","// AQUALUMEN_PREPARED_TARGET_END:"+name+"\n");
    }require(source.find("AQUALUMEN_PREPARED_TARGET_")==std::string::npos,"unknown observer tag remains");return source;
}
std::string all48Observer(const std::string& physical,const std::string& call){
    // STORE-only scratch variables. No extra certificate call, preparation,
    // normalization, early return or control-flow change in the old baseline.
    auto result=replace(physical,"vec4 WSP_counts=vec4(0.0);\n","vec4 WSP_counts=vec4(0.0);\n"+observerSpan("GLOBALS",
        "uniform int WPM_requestedNode;\nvec4 WPM_target=vec4(0.0);\nvec4 WPM_view=vec4(0.0);\nvec4 WPM_class=vec4(0.0);\n"));
    result=replace(result,"    WSP_counts=vec4(0.0);\n","    WSP_counts=vec4(0.0);\n"+observerSpan("RESET",
        "    WPM_target=vec4(0.0);WPM_view=vec4(0.0);WPM_class=vec4(0.0);\n"));
    const std::string targetAnchor="        vec3 axis=k*target+eta*viewToEye;\n";
    result=replace(result,targetAnchor,observerSpan("TARGET",
        "        if (WPM_requestedNode==r*12+j) {\n"
        "            WPM_target=vec4(target,float(r*12+j+1));\n"
        "            WPM_view=vec4(viewToEye,eta);\n"
        "            WPM_class.z=float(r*12+j);WPM_class.w=1.0;\n"
        "        }\n")+targetAnchor);
    result=replace(result,call,call+observerSpan("NODE",
        "        if (WPM_requestedNode==r*12+j) {\n"
        "            WPM_class.x=float(WSP_supportClass+1);WPM_class.y=1.0;\n"
        "        }\n"));
    const auto close=result.rfind('}');require(close!=std::string::npos,"main final brace absent");
    result.insert(close,observerSpan("STORE","    gl_FragData[5]=WPM_target;\n    gl_FragData[6]=WPM_view;\n    gl_FragData[7]=WPM_class;\n"));
    require(stripObserver(result)==physical,"all48 observer erasure differs from physical");return result;
}
struct Sources {
    std::array<std::string,3> geometry;
    std::array<std::array<std::string,4>,2> fragment;
    std::array<std::array<std::string,2>,2> metadata;
    std::string oldHelper,preparedHelper;
};
std::string recoverPrepared(std::string source,const Sources& loaded){
    source=replace(source,loaded.preparedHelper,loaded.oldHelper);
    source=tracer::eraseOne(source,contextBegin,contextEnd);
    return replace(source,newCall,oldCall);
}
Sources construct(const std::array<fs::path,4>& roots,const fs::path& prepared){
    const auto inherited=support::load(roots);Sources result;
    result.geometry=inherited.geometry;result.metadata=inherited.metadata;
    result.oldHelper=old::readText(roots[1]/"lib/water_sun_support.glsl");
    result.preparedHelper=old::readText(prepared);
    require(light::digest(result.oldHelper)==support::certificateSHA,"old literal helper pin differs");
    require(light::digest(result.preparedHelper)==preparedSHA,"prepared literal helper pin differs");
    require(light::digest(old::readText("tools/water_sun_support_probe.cpp"))==oldProbeSHA,"retained host support source pin differs");
    const std::string anchor="    float integral=0.0;\n    if (valid) for (int r=0;r<4;++r) for (int j=0;j<12;++j) {\n";
    for(int role=0;role<3;++role){
        result.fragment[0][role]=inherited.fragment[1][role];
        auto candidate=replace(result.fragment[0][role],result.oldHelper,result.preparedHelper);
        candidate=replace(candidate,anchor,"    float integral=0.0;\n"+contextBegin+context+contextEnd+
            "    if (valid) for (int r=0;r<4;++r) for (int j=0;j<12;++j) {\n");
        candidate=replace(candidate,oldCall,newCall);
        require(recoverPrepared(candidate,result)==result.fragment[0][role],"prepared source does not exactly recover old role");
        require(occurrences(candidate,context)==1&&occurrences(candidate,newCall)==1,"context/call site count differs");
        require(candidate.find("if (!WPM_viewContext.valid)")==std::string::npos,"invalid-context shortcut forbidden");
        result.fragment[1][role]=candidate;
    }
    for(int mode=0;mode<2;++mode)result.fragment[mode][3]=all48Observer(result.fragment[mode][0],mode?newCall:oldCall);
    require(recoverPrepared(result.fragment[1][3],result)==result.fragment[0][3],"prepared all48 observer does not recover old observer");
    return result;
}
void newOutput(const fs::path& path){
    require(!fs::exists(path)&&!fs::is_symlink(path),"NEW output required");require(fs::create_directories(path),"cannot create output");ownedOutput=path;
}
std::string saveSources(const Sources& source,const fs::path& output){
    std::ostringstream manifest;manifest<<"{\"schema\":\"aqualumen-prepared-main-source-v1\",\"GLExecuted\":false,\"old_helper_sha256\":"<<old::quote(support::certificateSHA)<<",\"prepared_helper_sha256\":"<<old::quote(preparedSHA)<<",\"sources\":[";
    bool first=true;auto save=[&](const std::string& name,const std::string& value){old::writeText(output/name,value);if(!first)manifest<<',';first=false;manifest<<"{\"file\":"<<old::quote(name)<<",\"sha256\":"<<old::quote(light::digest(value))<<",\"bytes\":"<<value.size()<<'}';};
    save("old-water-sun-support.glsl",source.oldHelper);save("prepared-water-sun-support.glsl",source.preparedHelper);
    for(int stage=0;stage<3;++stage)save("geometry-stage"+std::to_string(stage)+".glsl",source.geometry[stage]);
    for(int mode=0;mode<2;++mode){for(int role=0;role<4;++role)save(modes[mode]+"-"+roles[role]+"-expanded.fsh",source.fragment[mode][role]);
        for(int observer=0;observer<2;++observer)save(modes[mode]+"-parent-"+roles[observer+1]+"-metadata.json",source.metadata[1][observer]);}
    // Recoverable exact compile support tree (local quoted includes only).
    std::set<fs::path> seen;std::vector<fs::path> pending={"tools/water_sun_prepared_main_probe.cpp"};
    require(fs::create_directory(output/"host-sources"),"NEW host source directory required");
    const std::regex localInclude("#include \\\"([^\\\"]+)\\\"");
    while(!pending.empty()){
        const auto path=pending.back();pending.pop_back();if(!seen.insert(path).second)continue;
        require(path.parent_path()==fs::path("tools"),"support include must remain inside tools");
        const auto value=old::readText(path);save("host-sources/"+path.filename().string(),value);
        for(std::sregex_iterator it(value.begin(),value.end(),localInclude),end;it!=end;++it){
            const auto next=path.parent_path()/(*it)[1].str();require(next.lexically_normal().parent_path()==fs::path("tools"),"nonlocal support include forbidden");pending.push_back(next.lexically_normal());
        }
    }
    const auto test=old::readText("tools/test_water_sun_prepared_main_probe.py");save("host-sources/test_water_sun_prepared_main_probe.py",test);
    manifest<<"],\"prepared_recovers_old_exact\":true,\"all48_observer_recovers_physical_exact\":true,\"node_generation_and_loop_unchanged\":true,\"invalid_context_shortcut\":false,\"cap_context_declarations\":1,\"node_class_call_sites\":1,\"roles\":[\"physical\",\"reasons\",\"inputs\",\"all48\"]}\n";
    old::writeText(output/"source-manifest.json",manifest.str());return manifest.str();
}
int cpuContract(const std::array<fs::path,4>& roots,const fs::path& prepared,const fs::path& output){
    require(!fs::exists(output)&&!fs::is_symlink(output),"NEW output required");const auto source=construct(roots,prepared);newOutput(output);std::cout<<saveSources(source,output);return 0;
}
// Small bounded strict JSON reader for the externally produced node gate.
// Reject duplicate keys, malformed/trailing data and wrong types; never execute
// the node fixture here or elevate a synthetic CPU packet to native proof.
struct Json {
    enum Kind {Object,Array,String,Number,Boolean,Null} kind=Null;
    std::map<std::string,Json> object;std::vector<Json> array;
    std::string text;double number=0;bool boolean=false;
    const Json& at(const std::string& key)const{require(kind==Object&&object.count(key)==1,"node gate key missing: "+key);return object.at(key);}
    bool flag()const{require(kind==Boolean,"node gate boolean type required");return boolean;}
    const std::string& str()const{require(kind==String,"node gate string type required");return text;}
    int integer()const{require(kind==Number&&number>=0&&number<=100000&&number==std::floor(number),"bounded node gate integer required");return int(number);}
};
struct JsonReader {
    const std::string& source;std::size_t p=0;
    void space(){while(p<source.size()&&(source[p]==' '||source[p]=='\n'||source[p]=='\t'||source[p]=='\r'))++p;}
    bool take(char c){space();if(p<source.size()&&source[p]==c){++p;return true;}return false;}
    std::string string(){
        require(take('"'),"node gate JSON string expected");std::string result;
        while(p<source.size()){
            const char c=source[p++];if(c=='"')return result;require(static_cast<unsigned char>(c)>=32,"node gate control character");
            if(c!='\\'){result+=c;continue;}
            require(p<source.size(),"node gate incomplete escape");const char e=source[p++];
            if(e=='"'||e=='\\'||e=='/')result+=e;
            else if(e=='b')result+='\b';else if(e=='f')result+='\f';else if(e=='n')result+='\n';else if(e=='r')result+='\r';else if(e=='t')result+='\t';
            else if(e=='u'){
                require(p+4<=source.size(),"node gate incomplete Unicode escape");unsigned code=0;
                for(int i=0;i<4;++i){const char h=source[p++];const int digit=h>='0'&&h<='9'?h-'0':h>='a'&&h<='f'?h-'a'+10:h>='A'&&h<='F'?h-'A'+10:-1;require(digit>=0,"invalid Unicode escape");code=code*16+unsigned(digit);}
                require(code<128,"gate identity keys require ASCII escaped codepoints");result+=char(code);
            }else require(false,"invalid JSON escape");
        }require(false,"unterminated node gate JSON string");return {};
    }
    Json value(int depth=0){
        require(depth<=32,"bounded JSON depth required");space();require(p<source.size(),"node gate JSON value absent");Json result;
        if(take('{')){result.kind=Json::Object;if(take('}'))return result;do{const auto key=string();require(take(':'),"JSON colon absent");require(result.object.emplace(key,value(depth+1)).second,"duplicate node gate key");if(take('}'))return result;}while(take(','));require(false,"JSON object delimiter absent");}
        else if(take('[')){result.kind=Json::Array;if(take(']'))return result;do{result.array.push_back(value(depth+1));require(result.array.size()<=100000,"bounded JSON array required");if(take(']'))return result;}while(take(','));require(false,"JSON array delimiter absent");}
        else if(source[p]=='"'){result.kind=Json::String;result.text=string();return result;}
        else if(source.compare(p,4,"true")==0){p+=4;result.kind=Json::Boolean;result.boolean=true;return result;}
        else if(source.compare(p,5,"false")==0){p+=5;result.kind=Json::Boolean;return result;}
        else if(source.compare(p,4,"null")==0){p+=4;return result;}
        else{
            const auto begin=p;if(source[p]=='-')++p;require(p<source.size(),"JSON number absent");
            if(source[p]=='0')++p;else{require(source[p]>='1'&&source[p]<='9',"JSON number integer absent");while(p<source.size()&&source[p]>='0'&&source[p]<='9')++p;}
            if(p<source.size()&&source[p]=='.'){++p;const auto fractional=p;while(p<source.size()&&source[p]>='0'&&source[p]<='9')++p;require(p>fractional,"JSON fraction absent");}
            if(p<source.size()&&(source[p]=='e'||source[p]=='E')){++p;if(p<source.size()&&(source[p]=='+'||source[p]=='-'))++p;const auto exponent=p;while(p<source.size()&&source[p]>='0'&&source[p]<='9')++p;require(p>exponent,"JSON exponent absent");}
            result.kind=Json::Number;result.number=std::stod(source.substr(begin,p-begin));require(std::isfinite(result.number),"nonfinite JSON number");return result;
        }require(false,"invalid JSON");return {};
    }
    Json parse(){auto result=value();space();require(p==source.size(),"trailing node gate JSON data");return result;}
};
std::string nodeGate(const fs::path& path,bool allowSynthetic){
    require(fs::is_regular_file(path)&&fs::file_size(path)>0&&fs::file_size(path)<=8388608,"bounded node gate file required");
    const auto raw=old::readText(path);const auto data=JsonReader{raw}.parse();
    require(data.at("schema").str()=="aqualumen-prepared-node-native-v1","node gate schema differs");
    const bool synthetic=data.object.count("syntheticOnly")&&data.at("syntheticOnly").flag();
    require(!synthetic||allowSynthetic,"synthetic CPU node gate forbidden for native execution");
    require(data.at("nativeGLExecuted").flag()&&data.at("accepted").flag()&&data.at("status").str()=="PASS","actual accepted native node PASS required");
    const auto& renderer=data.at("renderer").str();require(renderer.find("NVIDIA")!=std::string::npos&&renderer.find("RTX 3080 Ti")!=std::string::npos,"node gate actual NVIDIA RTX3080Ti required");
    require(data.at("vendor").str().find("NVIDIA")!=std::string::npos,"node gate actual NVIDIA vendor required");
    require(data.at("count").integer()==376&&data.at("frozenCount").integer()==344&&data.at("additionalCount").integer()==32,"node gate full frozen/additional corpus required");
    const auto& roleArray=data.at("roles");require(roleArray.kind==Json::Array&&roleArray.array.size()==3,"node gate role array differs");
    const std::array<std::string,3> expectedRoles={"old","wrapper","reused"};for(int i=0;i<3;++i)require(roleArray.array[i].str()==expectedRoles[i],"node gate old/wrapper/reused required");
    const auto& hashes=data.at("sourceSHA256");require(hashes.at("old").str()==support::certificateSHA&&hashes.at("prepared").str()==preparedSHA&&hashes.at("corpus").str()==corpusSHA,"node gate exact old/prepared/corpus source pin differs");
    require(hashes.at("utilities").str()==nodeUtilitiesSHA&&hashes.at("fixtureSource").str()==nodeFixtureSHA,"node gate literal utilities/additional fixture source pin differs");
    for(const char* key:{"rawInputEchoExact","classesEqual","matchesLiteralCPUClass","allSixIntervalTriplesEqual","contextValidEqual","groupChecksumsEqual","repeatByteIdentical","additionalMatchesLiteralCPUCases"})require(data.at(key).flag(),std::string("node gate strict check false: ")+key);
    require(!data.at("physicalOracleForAdditional").flag(),"additional physical scope must not be promoted");return raw;
}
int cpuGate(const fs::path& path,bool synthetic){
    const auto raw=nodeGate(path,synthetic);std::cout<<"{\"GLExecuted\":false,\"syntheticOnly\":"<<(synthetic?"true":"false")<<",\"native_gate_accepted\":"<<(synthetic?"false":"true")<<",\"node_gate_sha256\":"<<old::quote(light::digest(raw))<<"}\n";return 0;
}
std::vector<float> rawFloats(const fs::path& path){
    require(fs::is_regular_file(path),"regular raw file required");const auto bytes=fs::file_size(path);
    require(bytes>0&&bytes<=16777216&&bytes%sizeof(float)==0,"bounded whole binary32 raw data required");
    std::vector<float> values(bytes/sizeof(float),NAN);std::ifstream input(path,std::ios::binary);input.read(reinterpret_cast<char*>(values.data()),std::streamsize(bytes));
    require(bool(input)&&std::all_of(values.begin(),values.end(),[](float x){return std::isfinite(x);}),"finite raw binary32 required");return values;
}
bool bitsEqual(const std::vector<float>& a,const std::vector<float>& b){return a.size()==b.size()&&(a.empty()||std::memcmp(a.data(),b.data(),a.size()*sizeof(float))==0);}
int cpuRawEqual(const fs::path& a,const fs::path& b){
    const bool equal=bitsEqual(rawFloats(a),rawFloats(b));std::cout<<"{\"GLExecuted\":false,\"syntheticOnly\":true,\"binary32_bits_equal\":"<<(equal?"true":"false")<<"}\n";return equal?0:1;
}
struct TimerOptions {int warmup=2,measurement=6,maxSeconds=900;};
void checkTimerOptions(const TimerOptions& options){
    require(options.warmup>=1&&options.warmup<=4&&options.measurement>=1&&options.measurement<=12
        &&options.maxSeconds>=10&&options.maxSeconds<=3600,"timer bounds: warmup1..4 measurement1..12 max-seconds10..3600");
}
int strictInteger(const std::string& value){
    require(!value.empty()&&value.size()<=6&&std::all_of(value.begin(),value.end(),[](char c){return c>='0'&&c<='9';}),"decimal whole option required");return std::stoi(value);
}
int cpuTimerOptions(const TimerOptions& options){
    checkTimerOptions(options);std::cout<<"{\"GLExecuted\":false,\"warmup_cycles\":"<<options.warmup<<",\"measurement_cycles\":"<<options.measurement<<",\"max_seconds\":"<<options.maxSeconds<<",\"measured_draws_per_variant_per_fixture\":"<<options.measurement*2<<",\"query_scope\":\"glDrawArrays(GL_PATCHES,0,6) only\"}\n";return 0;
}
struct Budget {
    std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();int seconds;
    explicit Budget(int limit):seconds(limit){}
    void check()const{require(std::chrono::steady_clock::now()-start<std::chrono::seconds(seconds),"wall budget exceeded between GL calls; driver calls cannot be interrupted");}
};
std::string vectorSHA(const std::vector<float>& values){return light::digest(std::string(reinterpret_cast<const char*>(values.data()),values.size()*sizeof(float)));}
bool exact(std::ostringstream& report,bool& first,const std::string& label,const std::vector<float>& a,const std::vector<float>& b){
    require(a.size()==b.size(),"comparison sizes differ");std::size_t mismatches=0;double largest=0;
    for(std::size_t i=0;i<a.size();++i){std::uint32_t x=0,y=0;std::memcpy(&x,&a[i],4);std::memcpy(&y,&b[i],4);mismatches+=x!=y;largest=std::max(largest,std::abs(double(a[i])-b[i]));}
    if(!first)report<<',';
    first=false;report<<"{\"label\":"<<old::quote(label)<<",\"elements\":"<<a.size()<<",\"mismatching_words\":"<<mismatches<<",\"max_absolute_delta\":"<<largest<<",\"absolute_policy\":0,\"relative_policy\":0,\"signed_zero_bits_compared\":true,\"a_sha256\":"<<old::quote(vectorSHA(a))<<",\"b_sha256\":"<<old::quote(vectorSHA(b))<<",\"accepted\":"<<(mismatches==0?"true":"false")<<'}';return mismatches==0;
}
void prepareDraw(sun::Fixture& fixture,GLuint program,int guard,bool observer){
    // Exact setup order inherited from prior::capture + sun::draw. All of this
    // lies OUTSIDE the elapsed query, including uniform application and clears.
    prior::setGuard(fixture,program,guard);fixture.uniforms(program);
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.fbo);std::array<GLenum,outputs> buffers={};
    for(int i=0;i<outputs;++i)buffers[i]=GL_COLOR_ATTACHMENT0+i;
    glDrawBuffers(outputs,buffers.data());const float zero[4]={},one=1;
    for(int i=0;i<outputs;++i)glClearBufferfv(GL_COLOR,i,zero);
    glClearBufferfv(GL_DEPTH,0,&one);
    glDrawBuffers(observer?outputs:5,buffers.data());old::glOkay("prepared main exact draw setup");
}
void typedNode(GLuint program,int node){
    require(node>=0&&node<48,"bounded requested node required");const char* name="WPM_requestedNode";GLuint index=GL_INVALID_INDEX;
    glGetUniformIndices(program,1,&name,&index);const GLint location=glGetUniformLocation(program,name);GLint type=0,count=0,value=-1;
    GLint current=0;glGetIntegerv(GL_CURRENT_PROGRAM,&current);require(current==GLint(program),"all48 observed program must actually be current");
    require(index!=GL_INVALID_INDEX&&location>=0,"all48 requested node absent");glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&count);
    require(type==GL_INT&&count==1,"all48 requested node must be active scalar int");glUniform1i(location,node);glGetUniformiv(program,location,&value);require(value==node,"actual requested node value differs");
}
std::string nodeDrawState(sun::Fixture& fixture,GLuint program,int node,int guard){
    GLint current=0,framebuffer=0,viewport[4]={},vao=0,patch=0;
    glGetIntegerv(GL_CURRENT_PROGRAM,&current);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&framebuffer);glGetIntegerv(GL_VIEWPORT,viewport);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);glGetIntegerv(GL_PATCH_VERTICES,&patch);
    std::array<GLint,outputs> drawBuffers={};for(int slot=0;slot<outputs;++slot){glGetIntegerv(GL_DRAW_BUFFER0+slot,&drawBuffers[slot]);require(drawBuffers[slot]==GLint(GL_COLOR_ATTACHMENT0+slot),"all48 actual eight-route mismatch");}
    require(current==GLint(program)&&framebuffer==GLint(fixture.fbo)&&viewport[0]==0&&viewport[1]==0&&viewport[2]==size&&viewport[3]==size&&patch==3&&!glIsEnabled(GL_CULL_FACE),"all48 actual program/FBO/viewport/patch/culling mismatch");
    std::ostringstream state;state<<"{\"expectedProgram\":"<<program<<",\"currentProgram\":"<<current<<",\"drawFramebuffer\":"<<framebuffer<<",\"viewport\":["<<viewport[0]<<','<<viewport[1]<<','<<viewport[2]<<','<<viewport[3]<<"],\"VAO\":"<<vao<<",\"patchVertices\":"<<patch<<",\"drawBuffers\":";angular::numbers(state,drawBuffers);
    const std::array<std::pair<const char*,int>,2> uniforms={{{"WPM_requestedNode",node},{"aqualumenSunTestAuthorized",guard}}};
    for(int i=0;i<2;++i){const char* name=uniforms[i].first;GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);const GLint location=glGetUniformLocation(program,name);GLint type=0,count=0,value=-1;
        require(index!=GL_INVALID_INDEX&&location>=0,"all48 active typed uniform absent");glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&count);glGetUniformiv(program,location,&value);
        require(type==GL_INT&&count==1&&value==uniforms[i].second,"all48 actual typed requested-node/guard mismatch");
        state<<",\""<<(i?"guard":"requestedNode")<<"\":{\"name\":"<<old::quote(name)<<",\"type\":"<<type<<",\"size\":"<<count<<",\"location\":"<<location<<",\"value\":"<<value<<'}';
    }state<<'}';old::glOkay("actual all48 draw-state query");return state.str();
}
old::Capture captureNode(sun::Fixture& fixture,GLuint program,int guard,int node,std::string& state){
    prepareDraw(fixture,program,guard,true);typedNode(program,node);const auto before=nodeDrawState(fixture,program,node,guard);
    glDrawArrays(GL_PATCHES,0,6);const auto after=nodeDrawState(fixture,program,node,guard);require(before==after,"all48 actual draw state changed");
    state="{\"before\":"+before+",\"after\":"+after+",\"draw_state_unchanged\":true}";
    old::Capture result;
    for(int slot=0;slot<outputs;++slot){auto& values=result.images[slot];values.assign(size*size*4,NAN);glReadBuffer(GL_COLOR_ATTACHMENT0+slot);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,values.data());require(std::all_of(values.begin(),values.end(),[](float x){return std::isfinite(x);}),"nonfinite all48 MRT");}
    result.depth.assign(size*size,NAN);glReadPixels(0,0,size,size,GL_DEPTH_COMPONENT,GL_FLOAT,result.depth.data());require(std::all_of(result.depth.begin(),result.depth.end(),[](float x){return std::isfinite(x);}),"nonfinite all48 depth");
    GLint requested=-1,authorized=-1;glGetUniformiv(program,glGetUniformLocation(program,"WPM_requestedNode"),&requested);glGetUniformiv(program,glGetUniformLocation(program,"aqualumenSunTestAuthorized"),&authorized);
    require(requested==node&&authorized==guard,"node/guard changed in actual all48 draw");old::glOkay("all48 full-view original main draw/readback");return result;
}
struct TimerQuery {
    GLuint id=0;GLint counterBits=0;
    TimerQuery(){
        require(epoxy_gl_version()>=33||epoxy_has_gl_extension("GL_ARB_timer_query"),"actual elapsed timer query extension required");
        glGetQueryiv(GL_TIME_ELAPSED,GL_QUERY_COUNTER_BITS,&counterBits);GLint active=0;glGetQueryiv(GL_TIME_ELAPSED,GL_CURRENT_QUERY,&active);
        require(counterBits>0&&counterBits<=64&&active==0,"elapsed timer counter/idle state required");glGenQueries(1,&id);require(id!=0,"elapsed query object required");old::glOkay("elapsed query creation only");
    }
    ~TimerQuery(){if(id)glDeleteQueries(1,&id);}
};
std::uint64_t timedDraw(sun::Fixture& fixture,GLuint program,int guard,TimerQuery& query,const Budget& budget,std::ostringstream& states,bool& first,const std::string& inputReceiptSHA,const std::string& inputPayloadSHA,const std::string& fragmentSHA){
    budget.check();prepareDraw(fixture,program,guard,false);
    GLint current=0,framebuffer=0,viewport[4]={},patch=0,vao=0,activeQuery=0;
    glGetIntegerv(GL_CURRENT_PROGRAM,&current);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&framebuffer);glGetIntegerv(GL_VIEWPORT,viewport);glGetIntegerv(GL_PATCH_VERTICES,&patch);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);glGetQueryiv(GL_TIME_ELAPSED,GL_CURRENT_QUERY,&activeQuery);
    require(current==GLint(program)&&framebuffer==GLint(fixture.fbo)&&viewport[0]==0&&viewport[1]==0&&viewport[2]==size&&viewport[3]==size&&patch==3&&!glIsEnabled(GL_CULL_FACE)&&activeQuery==0,"actual timed draw program/FBO/viewport/patch/culling/query state differs");
    std::array<GLint,outputs> drawBuffers={};for(int slot=0;slot<outputs;++slot){glGetIntegerv(GL_DRAW_BUFFER0+slot,&drawBuffers[slot]);require(drawBuffers[slot]==GLint(slot<5?GL_COLOR_ATTACHMENT0+slot:GL_NONE),"timer physical must retain five original draw buffers");}
    const char* guardName="aqualumenSunTestAuthorized";GLuint guardIndex=GL_INVALID_INDEX;const GLint guardLocation=glGetUniformLocation(program,guardName);GLint guardType=0,guardSize=0,guardBefore=-1,guardAfter=-1;
    glGetUniformIndices(program,1,&guardName,&guardIndex);require(guardIndex!=GL_INVALID_INDEX&&guardLocation>=0,"actual timed guard absent");
    glGetActiveUniformsiv(program,1,&guardIndex,GL_UNIFORM_TYPE,&guardType);glGetActiveUniformsiv(program,1,&guardIndex,GL_UNIFORM_SIZE,&guardSize);glGetUniformiv(program,guardLocation,&guardBefore);
    require(guardType==GL_INT&&guardSize==1&&guardBefore==guard,"actual timed guard must be typed scalar int equal requested input");
    // EXCLUSIVELY the water draw. Synchronization/setup/readback/output wait
    // occur outside the query; no main or certificate instrumentation is added.
    glFinish();budget.check();
    glBeginQuery(GL_TIME_ELAPSED,query.id);
    glDrawArrays(GL_PATCHES,0,6);
    glEndQuery(GL_TIME_ELAPSED);
    glFlush();GLint available=0;const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    while(!available){budget.check();require(std::chrono::steady_clock::now()<deadline,"elapsed result not available within10s");glGetQueryObjectiv(query.id,GL_QUERY_RESULT_AVAILABLE,&available);}
    GLuint64 raw=0;glGetQueryObjectui64v(query.id,GL_QUERY_RESULT,&raw);require(raw>0&&raw<=60000000000ULL,"elapsed raw nanoseconds outside finite declared range1..60e9");
    GLint afterProgram=0,afterFramebuffer=0,afterViewport[4]={},afterVAO=0,afterQuery=0;
    glGetIntegerv(GL_CURRENT_PROGRAM,&afterProgram);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&afterFramebuffer);glGetIntegerv(GL_VIEWPORT,afterViewport);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&afterVAO);glGetQueryiv(GL_TIME_ELAPSED,GL_CURRENT_QUERY,&afterQuery);
    glGetUniformiv(program,guardLocation,&guardAfter);require(guardAfter==guardBefore,"actual timed guard changed during query draw");
    require(afterProgram==current&&afterFramebuffer==framebuffer&&std::equal(viewport,viewport+4,afterViewport)&&afterVAO==vao&&afterQuery==0,"elapsed query changed actual draw state");old::glOkay("elapsed physical draw result/state");
    if(!first)states<<',';
    first=false;states<<"{\"program\":"<<program<<",\"currentProgramBefore\":"<<current<<",\"currentProgramAfter\":"<<afterProgram<<",\"framebuffer\":"<<framebuffer<<",\"viewport\":["<<viewport[0]<<','<<viewport[1]<<','<<viewport[2]<<','<<viewport[3]<<"],\"VAO\":"<<vao<<",\"patchVertices\":"<<patch<<",\"drawBuffers\":";angular::numbers(states,drawBuffers);states<<",\"guard\":{\"name\":\"aqualumenSunTestAuthorized\",\"type\":"<<guardType<<",\"size\":"<<guardSize<<",\"location\":"<<guardLocation<<",\"actualBefore\":"<<guardBefore<<",\"actualAfter\":"<<guardAfter<<"},\"actual_input_receipt_sha256\":"<<old::quote(inputReceiptSHA)<<",\"actual_texture_payload_sha256\":"<<old::quote(inputPayloadSHA)<<",\"queried_fragment_source_sha256\":"<<old::quote(fragmentSHA)<<",\"counterBits\":"<<query.counterBits<<",\"elapsed_ns\":"<<raw<<",\"stateUnchanged\":true}";return std::uint64_t(raw);
}
struct Programs {
    std::array<std::array<GLuint,4>,2> value={};
    ~Programs(){for(const auto& row:value)for(GLuint id:row)if(id)glDeleteProgram(id);}
};
struct Scenario {
    bool wide=false,positive=false;int guard=0,aperture=2;std::string name;
    explicit Scenario(int index){
        require(index>=0&&index<6,"six frozen scenarios only");wide=index>=4;positive=wide||index>=2;guard=wide?1:index%2;aperture=wide?(index==4?60:90):2;
        name=wide?"wide"+std::to_string(aperture)+"-cachepositive-guard1":"central2-cache"+std::string(positive?"positive":"zero")+"-guard"+std::to_string(guard);
    }
    void apply(sun::Fixture& fixture,const fs::path& directory)const{
        fixture.scene(2,0,positive,directory);if(aperture==60)reason::wideProjection(fixture);if(aperture==90)support::wide90(fixture);
    }
};
bool domain(const Scenario& scenario,const std::array<std::array<old::Capture,3>,2>& frames,std::ostringstream& report){
    std::array<int,2> inspected={},qualified={},accounted={},applied={},complete={};
    std::array<std::array<long long,4>,2> totals={};
    for(int mode=0;mode<2;++mode)for(int y=0;y<size;++y)for(int x=0;x<size;++x){
        if(!scenario.wide&&(x-128)*(x-128)+(y-128)*(y-128)>1600)continue;
        const int p=(y*size+x)*4;const auto* covariance=&frames[mode][1].images[3][p];
        if(scenario.wide&&(frames[mode][0].images[4][p+3]==0||covariance[3]!=15))continue;
        ++inspected[mode];const auto* status=&frames[mode][1].images[2][p];const auto* reasons=&frames[mode][1].images[1][p];
        bool valid=covariance[3]==15&&prior::stageQualified(&frames[mode][0].images[4][p])&&prior::stageQualified(&frames[mode][1].images[4][p]);
        for(int role=0;role<3;++role)valid=valid&&frames[mode][role].images[0][p+3]==1;
        if(scenario.guard)valid=valid&&reason::covarianceDomain(covariance);else for(int c=0;c<3;++c)valid=valid&&covariance[c]==0;
        if(!scenario.wide)valid=valid&&status[0]==scenario.guard&&status[1]==int(scenario.guard&&scenario.positive)&&status[3]==0;
        qualified[mode]+=valid;std::array<float,16> values={};
        for(int slot=1;slot<5;++slot)std::copy_n(&frames[mode][2].images[slot][p],4,values.data()+(slot-1)*4);
        std::array<int,4> counts={};const bool okay=support::accounting(values.data(),reasons,status,scenario.guard,scenario.positive,true,counts);accounted[mode]+=okay;
        if(okay)for(int c=0;c<4;++c)totals[mode][c]+=counts[c];
        applied[mode]+=status[1]==1;complete[mode]+=okay&&counts[3]==48;
    }
    bool valid=true;for(int mode=0;mode<2;++mode)valid=valid&&inspected[mode]>0&&inspected[mode]==qualified[mode]&&inspected[mode]==accounted[mode]&&(scenario.wide||inspected[mode]==5025);
    report<<"{\"inspected_old_prepared\":";angular::numbers(report,inspected);report<<",\"qualified_old_prepared\":";angular::numbers(report,qualified);report<<",\"count_accounted_old_prepared\":";angular::numbers(report,accounted);report<<",\"applied_old_prepared\":";angular::numbers(report,applied);report<<",\"complete48_old_prepared\":";angular::numbers(report,complete);report<<",\"class_totals_old_prepared\":[";angular::numbers(report,totals[0]);report<<',';angular::numbers(report,totals[1]);report<<"],\"qualified\":"<<(valid?"true":"false")<<'}';return valid;
}
struct NodeResult {bool neutral=true,input=true,classes=true,ledger=true;long long generated=0,called=0;};
using NodeMaps=std::array<std::array<const std::vector<float>*,3>,2>;
std::string saveNodeMaps(int node,const NodeMaps& maps,const fs::path& directory,const std::string& prefix){
    require(node>=0&&node<48,"bounded archive node required");const std::array<std::string,3> names={"target","view","class"};
    std::ostringstream result;result<<"{\"node\":"<<node<<",\"duplicate_maps_omitted\":false,\"maps\":[";bool first=true;
    for(int mode=0;mode<2;++mode)for(int kind=0;kind<3;++kind){
        require(maps[mode][kind]!=nullptr&&maps[mode][kind]->size()==std::size_t(size)*size*4,"exact full-view node archive size required");
        const auto& values=*maps[mode][kind];require(std::all_of(values.begin(),values.end(),[](float x){return std::isfinite(x);}),"finite archived node map required");
        const auto file="node"+std::to_string(node)+"-"+modes[mode]+"-"+names[kind]+".rgba32f";
        require(!fs::exists(directory/file)&&!fs::is_symlink(directory/file),"node map overwrite forbidden");old::writeRaw(directory/file,values);
        if(!first)result<<',';
        first=false;result<<"{\"mode\":"<<old::quote(modes[mode])<<",\"slot\":"<<kind+5<<",\"kind\":"<<old::quote(names[kind])<<",\"file\":"<<old::quote(prefix+file)<<",\"bytes\":"<<values.size()*sizeof(float)<<",\"sha256\":"<<old::quote(vectorSHA(values))<<'}';
    }result<<"]}";return result.str();
}
int cpuArchiveNode(const std::array<fs::path,6>& files,int node,const fs::path& output){
    require(!fs::exists(output)&&!fs::is_symlink(output),"NEW output required");
    std::array<std::array<std::vector<float>,3>,2> values;NodeMaps maps={};
    for(int mode=0;mode<2;++mode)for(int kind=0;kind<3;++kind){values[mode][kind]=rawFloats(files[mode*3+kind]);maps[mode][kind]=&values[mode][kind];require(values[mode][kind].size()==std::size_t(size)*size*4,"exact full-view synthetic node map required");}
    require(node>=0&&node<48,"bounded archive node required");newOutput(output);const auto saved=saveNodeMaps(node,maps,output,"");
    // This public CPU branch exercises the SAME archival routine as actual GL
    // capture, but its inputs are never reported as GPU bindings or shader hits.
    const auto payload="{\"GLExecuted\":false,\"syntheticOnly\":true,"+saved.substr(1);
    old::writeText(output/"synthetic-archive.json",payload+"\n");std::cout<<payload<<'\n';return 0;
}
NodeResult all48(sun::Fixture& fixture,const Scenario& scenario,const Sources& source,const Programs& programs,
                 const std::array<std::array<old::Capture,3>,2>& frames,const fs::path& directory,
                 std::ostringstream& report,const Budget& budget){
    const auto targetDirectory=directory/"all48-targets";require(fs::create_directory(targetDirectory),"NEW all48 target directory required");
    NodeResult result;std::vector<std::array<int,4>> ledger(std::size_t(size)*size);std::vector<float> viewReference;
    report<<"{\"node_count\":48,\"target_observer_recovers_physical_exact\":true,\"node_order\":\"r*12+j, r0..3/j0..11\",\"records\":[";
    for(int node=0;node<48;++node){
        std::array<std::string,2> drawStates;
        budget.check();const auto a=captureNode(fixture,programs.value[0][3],scenario.guard,node,drawStates[0]);budget.check();const auto b=captureNode(fixture,programs.value[1][3],scenario.guard,node,drawStates[1]);
        if(node)report<<',';
        report<<"{\"node\":"<<node<<",\"requested_uniform_type\":"<<GL_INT<<",\"requested_uniform_size\":1,\"comparisons\":[";bool first=true;
        for(int mode=0;mode<2;++mode){const auto& observed=mode?b:a;
            for(int slot=0;slot<5;++slot)result.neutral=exact(report,first,modes[mode]+"-all48-slot"+std::to_string(slot)+"-physical-neutral",frames[mode][0].images[slot],observed.images[slot])&&result.neutral;
            result.neutral=exact(report,first,modes[mode]+"-all48-depth-physical-neutral",frames[mode][0].depth,observed.depth)&&result.neutral;
        }
        for(int slot=0;slot<outputs;++slot){const bool same=exact(report,first,"old-prepared-all48-slot"+std::to_string(slot),a.images[slot],b.images[slot]);if(slot==5||slot==6)result.input=same&&result.input;else result.classes=same&&result.classes;}
        result.classes=exact(report,first,"old-prepared-all48-depth",a.depth,b.depth)&&result.classes;
        if(node){result.input=exact(report,first,"raw-view-eta-all-nodes-exact",viewReference,a.images[6])&&result.input;}
        else viewReference=a.images[6];
        long long generated=0,called=0;
        for(int pixel=0;pixel<size*size;++pixel){const int p=pixel*4;const auto* target=&a.images[5][p];const auto* status=&a.images[7][p];
            if(status[3]==0){for(int slot=5;slot<8;++slot)for(int c=0;c<4;++c)result.input=(a.images[slot][p+c]==0)&&result.input;continue;}
            result.input=(status[3]==1&&status[2]==node&&target[3]==node+1&&a.images[6][p+3]==1.333f)&&result.input;++generated;
            if(status[1]==0){result.input=status[0]==0&&result.input;continue;}
            result.input=(status[1]==1&&reason::whole(status[0],2))&&result.input;++called;
            if(status[1]==1&&reason::whole(status[0],2)){const int c=status[0]==0?2:status[0]==1?0:1;++ledger[pixel][c];++ledger[pixel][3];}
        }
        const NodeMaps maps={{{&a.images[5],&a.images[6],&a.images[7]},{&b.images[5],&b.images[6],&b.images[7]}}};
        const auto saved=saveNodeMaps(node,maps,targetDirectory,"all48-targets/");
        result.generated+=generated;result.called+=called;
        report<<"],\"generated_pixels\":"<<generated<<",\"class_called_pixels\":"<<called<<",\"saved_maps\":"<<saved<<",\"actual_draw_state\":{\"old\":"<<drawStates[0]<<",\"prepared\":"<<drawStates[1]<<"},\"fragment_source_sha256\":{\"old\":"<<old::quote(light::digest(source.fragment[0][3]))<<",\"prepared\":"<<old::quote(light::digest(source.fragment[1][3]))<<"}}";
    }
    long long ledgerQualified=0;
    for(int pixel=0;pixel<size*size;++pixel){std::array<int,4> expected={};const bool decoded=support::decodeCounts(frames[0][1].images[2][pixel*4+2],expected);const bool same=decoded&&ledger[pixel]==expected;result.ledger=same&&result.ledger;ledgerQualified+=same;}
    if(scenario.guard&&scenario.positive)result.input=result.generated>0&&result.called>0&&result.input;
    else result.input=result.generated==0&&result.called==0&&result.input;
    report<<"],\"generated_node_pixel_pairs\":"<<result.generated<<",\"called_node_pixel_pairs\":"<<result.called<<",\"full_view_countword_ledger_qualified_pixels\":"<<ledgerQualified<<",\"all48_target_view_bits_equal\":"<<(result.input?"true":"false")<<",\"all48_class_ledger_equal\":"<<(result.classes&&result.ledger?"true":"false")<<",\"whole_physical_observer_neutral\":"<<(result.neutral?"true":"false")<<",\"observer_sourceSHA256\":["<<old::quote(light::digest(source.fragment[0][3]))<<','<<old::quote(light::digest(source.fragment[1][3]))<<"]}";
    return result;
}
int run(const std::array<fs::path,4>& roots,const fs::path& prepared,const fs::path& output,const fs::path& gate,const TimerOptions& options,const fs::path& executable){
    static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,"binary32 required");const std::uint32_t endian=1;
    require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian required");checkTimerOptions(options);
    require(!fs::exists(output)&&!fs::is_symlink(output),"NEW output required");
    const auto gateRaw=nodeGate(gate,false);const auto source=construct(roots,prepared);
    newOutput(output);const auto manifest=saveSources(source,output);old::writeText(output/"node-gate-result.json",gateRaw);
    const auto binary=old::readText(executable);require(!binary.empty(),"actual executable readback required");old::writeText(output/"executed-binary",binary);
    Budget budget(options.maxSeconds);old::Context context;const auto* renderer=glGetString(GL_RENDERER);const auto* vendor=glGetString(GL_VENDOR);
    require(renderer&&vendor&&std::string(reinterpret_cast<const char*>(renderer)).find("RTX 3080 Ti")!=std::string::npos&&std::string(reinterpret_cast<const char*>(vendor)).find("NVIDIA")!=std::string::npos,"actual NVIDIA RTX3080Ti required");
    require(epoxy_has_gl_extension("GL_ARB_gpu_shader_fp64"),"retained actual fp64 support required");sun::Fixture fixture;Programs programs;
    std::ostringstream report;report<<std::setprecision(17)<<"{\"schema\":\"aqualumen-prepared-main-native-v1\",\"nativeGLExecuted\":true,\"renderer\":"<<old::quote(reinterpret_cast<const char*>(renderer))<<",\"vendor\":"<<old::quote(reinterpret_cast<const char*>(vendor))<<",\"GL\":"<<old::quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<",\"size\":"<<size<<",\"phase_seconds\":120,\"source_manifest_sha256\":"<<old::quote(light::digest(manifest))<<",\"executable_sha256\":"<<old::quote(light::digest(binary))<<",\"node_gate_sha256\":"<<old::quote(light::digest(gateRaw))<<",\"node_gate_accepted_before_any_GL\":true,\"rawFormat\":\"little-endian binary32; bottom-left origin\",\"policy\":{\"full_C0_depth_TES_maps_counts_reasons_absolute\":0,\"relative\":0,\"raw48_target_view_class_bits_exact\":true,\"signed_zero_preserved\":true},\"programs\":[";
    bool firstProgram=true;for(int mode=0;mode<2;++mode)for(int role=0;role<4;++role){budget.check();if(!firstProgram)report<<',';firstProgram=false;
        programs.value[mode][role]=old::makeProgram({{GL_VERTEX_SHADER,source.geometry[0]},{GL_TESS_CONTROL_SHADER,source.geometry[1]},{GL_TESS_EVALUATION_SHADER,source.geometry[2]},{GL_FRAGMENT_SHADER,source.fragment[mode][role]}},modes[mode]+"-"+roles[role],report);}
    report<<"],\"cases\":[";bool allQualified=true,allAccepted=true;
    for(int scenarioIndex=0;scenarioIndex<6;++scenarioIndex){
        budget.check();const Scenario scenario(scenarioIndex);const auto directory=output/scenario.name;require(fs::create_directory(directory),"NEW main case required");scenario.apply(fixture,directory);
        if(scenarioIndex)report<<',';
        report<<"{\"path\":"<<old::quote(scenario.name)<<",\"guard\":"<<scenario.guard<<",\"positive_cache\":"<<(scenario.positive?"true":"false")<<",\"aperture_degrees\":"<<scenario.aperture<<",\"queried_program_sources\":[";
        tracer::Sources query;query.geometry=source.geometry;
        for(int role=0;role<4;++role){if(role)report<<',';sun::queriedSources(report,{programs.value[0][role],programs.value[1][role]},query,{source.fragment[0][role],source.fragment[1][role]});}report<<']';
        std::array<std::array<old::Capture,3>,2> frames,repeats;
        std::array<std::vector<float>,8> referenceInputs={};bool haveInputs=false;
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){
            const auto label=modes[mode]+"-"+roles[role];budget.check();frames[mode][role]=prior::capture(fixture,programs.value[mode][role],scenario.guard,role!=0,directory,label);
            budget.check();repeats[mode][role]=prior::capture(fixture,programs.value[mode][role],scenario.guard,role!=0,directory,label+"-repeat");
            const auto inputsDirectory=directory/(label+"-actual-inputs");require(fs::create_directory(inputsDirectory),"NEW input snapshot required");
            const auto inputs=sun::snapshotInputs(fixture,programs.value[mode][role],inputsDirectory);prior::guardSnapshot(programs.value[mode][role],scenario.guard,inputsDirectory,"actual-inputs");
            if(haveInputs){for(int unit=0;unit<8;++unit)require(bitsEqual(referenceInputs[unit],inputs[unit]),"actual input texture bits differ across old/prepared roles");}
            else{referenceInputs=inputs;haveInputs=true;}
        }
        for(int mode=0;mode<2;++mode){const auto inputsDirectory=directory/(modes[mode]+"-all48-actual-inputs");require(fs::create_directory(inputsDirectory),"NEW all48 input snapshot required");
            prior::setGuard(fixture,programs.value[mode][3],scenario.guard);
            const auto values=sun::snapshotInputs(fixture,programs.value[mode][3],inputsDirectory);prior::guardSnapshot(programs.value[mode][3],scenario.guard,inputsDirectory,"actual-inputs");
            for(int unit=0;unit<8;++unit)require(bitsEqual(referenceInputs[unit],values[unit]),"actual all48 texture input bits differ from physical source");
        }
        bool qualified=true,accepted=true,first=true;report<<",\"comparisons\":[";
        for(int mode=0;mode<2;++mode)for(int role=0;role<3;++role){const auto label=modes[mode]+"-"+roles[role];
            for(int slot=0;slot<outputs;++slot)qualified=exact(report,first,label+"-slot"+std::to_string(slot)+"-repeat",frames[mode][role].images[slot],repeats[mode][role].images[slot])&&qualified;
            qualified=exact(report,first,label+"-depth-repeat",frames[mode][role].depth,repeats[mode][role].depth)&&qualified;
            if(role){qualified=exact(report,first,label+"-C0-physical-neutral",frames[mode][0].images[0],frames[mode][role].images[0])&&qualified;qualified=exact(report,first,label+"-depth-physical-neutral",frames[mode][0].depth,frames[mode][role].depth)&&qualified;}
            if(role==1)qualified=exact(report,first,label+"-TES-physical-neutral",frames[mode][0].images[4],frames[mode][role].images[4])&&qualified;
        }
        for(int role=0;role<3;++role){for(int slot=0;slot<outputs;++slot)accepted=exact(report,first,"old-prepared-"+roles[role]+"-slot"+std::to_string(slot),frames[0][role].images[slot],frames[1][role].images[slot])&&accepted;
            accepted=exact(report,first,"old-prepared-"+roles[role]+"-depth",frames[0][role].depth,frames[1][role].depth)&&accepted;}
        report<<"],\"domain_and_count_accounting\":";qualified=domain(scenario,frames,report)&&qualified;
        report<<",\"all48_inputs_classes\":";const auto nodes=all48(fixture,scenario,source,programs,frames,directory,report,budget);
        qualified=nodes.neutral&&nodes.input&&nodes.ledger&&qualified;accepted=nodes.classes&&accepted;
        allQualified=allQualified&&qualified;allAccepted=allAccepted&&accepted;
        report<<",\"qualified\":"<<(qualified?"true":"false")<<",\"accepted\":"<<(qualified&&accepted?"true":"false")<<'}';
        // Keep a recoverable partial report if a later soft-budget/driver/API
        // qualification fails; it is deliberately not a completed JSON PASS.
        old::writeText(output/"partial-report.txt",report.str());
    }
    report<<"],\"main_fixture_qualified\":"<<(allQualified?"true":"false")<<",\"main_differential_accepted\":"<<(allQualified&&allAccepted?"true":"false")<<",\"timer\":";
    if(allQualified&&allAccepted){
        TimerQuery query;std::ostringstream csv;csv<<"fixture,stage,cycle,position,variant,elapsed_ns\n";std::ostringstream states;states<<'[';bool firstState=true;
        std::ostringstream timerInputs;timerInputs<<'[';bool firstTimerInputs=true;
        const std::array<int,4> abba={0,1,1,0};
        for(int scenarioIndex=0;scenarioIndex<6;++scenarioIndex){const Scenario scenario(scenarioIndex);const auto directory=output/scenario.name;budget.check();scenario.apply(fixture,directory);
            std::array<std::string,2> receiptSHA,payloadSHA;std::array<std::vector<float>,8> referenceInputs={};
            if(!firstTimerInputs)timerInputs<<',';
            firstTimerInputs=false;timerInputs<<"{\"fixture\":"<<old::quote(scenario.name)<<",\"queried_program_sources\":";
            tracer::Sources querySource;querySource.geometry=source.geometry;sun::queriedSources(timerInputs,{programs.value[0][0],programs.value[1][0]},querySource,{source.fragment[0][0],source.fragment[1][0]});timerInputs<<",\"actual_inputs\":[";
            for(int mode=0;mode<2;++mode){const auto inputDirectory=directory/("timer-"+modes[mode]+"-actual-inputs");require(fs::create_directory(inputDirectory),"NEW timer actual input receipt required");
                prior::setGuard(fixture,programs.value[mode][0],scenario.guard);
                const auto values=sun::snapshotInputs(fixture,programs.value[mode][0],inputDirectory);prior::guardSnapshot(programs.value[mode][0],scenario.guard,inputDirectory,"timer");
                if(mode){for(int unit=0;unit<8;++unit)require(bitsEqual(values[unit],referenceInputs[unit]),"timer old/prepared actual texture payload differs");}else referenceInputs=values;
                std::string payload;for(const auto& value:values)payload.append(reinterpret_cast<const char*>(value.data()),value.size()*sizeof(float));payloadSHA[mode]=light::digest(payload);
                const auto receipt=old::readText(inputDirectory/"actual-inputs.json");receiptSHA[mode]=light::digest(receipt);
                if(mode)timerInputs<<',';
                timerInputs<<"{\"variant\":"<<old::quote(modes[mode])<<",\"receipt\":"<<old::quote(scenario.name+"/timer-"+modes[mode]+"-actual-inputs/actual-inputs.json")<<",\"receipt_sha256\":"<<old::quote(receiptSHA[mode])<<",\"texture_payload_sha256\":"<<old::quote(payloadSHA[mode])<<'}';
            }timerInputs<<"]}";
            for(int stage=0;stage<2;++stage){const int cycles=stage?options.measurement:options.warmup;
                for(int cycle=0;cycle<cycles;++cycle)for(int position=0;position<4;++position){const int mode=abba[position];const auto raw=timedDraw(fixture,programs.value[mode][0],scenario.guard,query,budget,states,firstState,receiptSHA[mode],payloadSHA[mode],light::digest(source.fragment[mode][0]));csv<<scenario.name<<','<<(stage?"measured":"warmup")<<','<<cycle<<','<<position<<','<<modes[mode]<<','<<raw<<'\n';old::writeText(output/"draw-timer.csv",csv.str());}
            }
        }
        states<<']';timerInputs<<']';old::writeText(output/"draw-timer-state.json",states.str()+"\n");old::writeText(output/"draw-timer-inputs.json",timerInputs.str()+"\n");
        report<<"{\"executed\":true,\"query\":\"GL_TIME_ELAPSED\",\"counterBits\":"<<query.counterBits<<",\"scope\":\"only glDrawArrays(GL_PATCHES,0,6); setup/uniforms/clear/glFinish/readback/wait/output excluded\",\"alternation\":\"ABBA old/prepared/prepared/old\",\"warmup_cycles\":"<<options.warmup<<",\"measurement_cycles\":"<<options.measurement<<",\"samples_per_variant_per_fixture\":"<<options.measurement*2<<",\"raw_integer_ns_file\":\"draw-timer.csv\",\"state_file\":\"draw-timer-state.json\",\"raw_csv_sha256\":"<<old::quote(light::digest(csv.str()))<<",\"state_sha256\":"<<old::quote(light::digest(states.str()+"\n"))<<",\"physical_role\":\"STORE-free inherited physical source; inherited counters and MRT0..4 retained, slots5..7 inactive\",\"Minecraft_FPS\":false}";
    }else report<<"{\"executed\":false,\"reason\":\"main/source/input/observer identity not fully accepted\"}";
    const auto status=!allQualified?"INCONCLUSIVE":allAccepted?"PASS":"RED";
    report<<",\"status\":"<<old::quote(status)<<",\"accepted\":"<<(allQualified&&allAccepted?"true":"false")<<",\"max_wall_seconds_between_calls\":"<<options.maxSeconds<<",\"Iris_accepted\":false,\"visual_accepted\":false,\"physics_accepted\":false,\"shipping_accepted\":false,\"FPS_accepted\":false,\"scope\":\"One test-only literal prepared-view integer-context hoist inside the original 48-node water cap main. Unmodified geometry, node generation, inverse, ledger, fallback and physical shader main; exact reversible source transformations. Full-view old/prepared differential is stricter than retained empirical gates (zero binary32 bit mismatches). All48 requested-node programs are separate passive observers with no repeated certificate calls. Node gate is externally executed and copied/hash-pinned before any GL; this does not rerun or authenticate it. Timing reports isolated native fixture water draws, retaining source counters/five MRTs; no Minecraft, appearance, energy correctness, universal speedup or shipping acceptance. Wall timeout checked between GL calls cannot interrupt a hung driver call.\"}\n";
    old::writeText(output/"result.json",report.str());std::cout<<status<<" prepared actual-main differential/timer "<<output<<'\n';return !allQualified?2:allAccepted?0:1;
}
}
int main(int argc,char** argv){try{
    if(argc==8&&std::string(argv[1])=="--cpu-contract")return preparedMain::cpuContract(
        {std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4]),std::filesystem::absolute(argv[5])},std::filesystem::absolute(argv[6]),std::filesystem::absolute(argv[7]));
    if(argc==4&&std::string(argv[1])=="--cpu-raw-equal")return preparedMain::cpuRawEqual(std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]));
    if(argc==3&&(std::string(argv[1])=="--cpu-gate"||std::string(argv[1])=="--cpu-gate-synthetic"))return preparedMain::cpuGate(std::filesystem::absolute(argv[2]),std::string(argv[1])=="--cpu-gate-synthetic");
    if(argc==5&&std::string(argv[1])=="--cpu-timer-options")return preparedMain::cpuTimerOptions({preparedMain::strictInteger(argv[2]),preparedMain::strictInteger(argv[3]),preparedMain::strictInteger(argv[4])});
    if(argc==10&&std::string(argv[1])=="--cpu-archive-node")return preparedMain::cpuArchiveNode(
        {std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4]),std::filesystem::absolute(argv[5]),std::filesystem::absolute(argv[6]),std::filesystem::absolute(argv[7])},preparedMain::strictInteger(argv[8]),std::filesystem::absolute(argv[9]));
    if(argc>=10&&std::string(argv[1])=="--native"){
        preparedMain::require(std::string(argv[8])=="--node-gate-result"&&(argc-10)%2==0,"explicit node gate and paired options required");
        preparedMain::TimerOptions options;std::set<std::string> seen;
        for(int i=10;i<argc;i+=2){const std::string key=argv[i];preparedMain::require(seen.insert(key).second,"duplicate timer option");const int value=preparedMain::strictInteger(argv[i+1]);if(key=="--warmup-cycles")options.warmup=value;else if(key=="--measure-cycles")options.measurement=value;else if(key=="--max-seconds")options.maxSeconds=value;else preparedMain::require(false,"unknown timer option");}
        return preparedMain::run({std::filesystem::absolute(argv[2]),std::filesystem::absolute(argv[3]),std::filesystem::absolute(argv[4]),std::filesystem::absolute(argv[5])},std::filesystem::absolute(argv[6]),std::filesystem::absolute(argv[7]),std::filesystem::absolute(argv[9]),options,std::filesystem::canonical("/proc/self/exe"));
    }
    std::cerr<<"usage: water_sun_prepared_main_probe --cpu-contract REJECT_REASON ZERO_REASON REJECT_INPUT ZERO_INPUT PREPARED_GLSL NEW_OUTPUT\n"
        "       --cpu-raw-equal A.f32 B.f32\n       --cpu-gate NODE_RESULT.json\n       --cpu-gate-synthetic SYNTHETIC.json\n       --cpu-timer-options WARMUP_CYCLES MEASURE_CYCLES MAX_SECONDS\n"
        "       --cpu-archive-node OLD_TARGET OLD_VIEW OLD_CLASS PREPARED_TARGET PREPARED_VIEW PREPARED_CLASS NODE NEW_OUTPUT\n"
        "       --native REJECT_REASON ZERO_REASON REJECT_INPUT ZERO_INPUT PREPARED_GLSL NEW_OUTPUT --node-gate-result NODE_RESULT.json [--warmup-cycles 2 --measure-cycles 6 --max-seconds 900]\n";return 2;
}catch(const std::exception& failure){std::cerr<<failure.what()<<'\n';if(!preparedMain::ownedOutput.empty())try{preparedMain::old::writeText(preparedMain::ownedOutput/"failure.txt",std::string(failure.what())+'\n');}catch(...){}return 2;}}
