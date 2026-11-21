// NEW TEST differential node probe; CPU construction only for agents.
#define main frozen_support_node_main
#include "water_sun_support_node_probe.cpp"
#undef main

namespace preparedNode {
using namespace supportNode;
constexpr const char* preparedSHA="ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441";
constexpr const char* dependencySHA="f183963ee155c89dcbd8be3e36ccd7d313ccadccde4d1d9bb5b4c2ab16ae16f7";
constexpr const char* fixtureSourceSHA="f4abe4cbde553c44258e2c2f2f9e437809f67af9c350823ac4627dcfb1a5bb67";
const std::array<std::string,3> roles={"old","wrapper","reused"};
const std::array<std::string,6> intervals={"vx","vy","vz","E","K2","downScale"};
struct Extra { Bits bits; int cpuClass; };
const std::array<Extra,32> additional={{
    {{{0x7f800000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0xff800000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x7fc00001u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000001u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x807fffffu,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x40400000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0x80000000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0x3f800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x7f800000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x7fc00001u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000001u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x80000000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0xbf800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3f800000u}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x40000001u}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x80000000u}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x7f800000u}}, -1},
    {{{0x00000000u,0xbf000000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x40000000u}}, -1},
    {{{0x40000000u,0xc0000000u,0x40000000u,0x40000000u,0x40000000u,0x40000000u,0x40000000u}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x3f400000u,0x3f800000u,0x00000000u,0x3fa00000u}}, -1},
    {{{0x3f800000u,0xbf000000u,0x00000000u,0x40000000u,0x3fa00000u,0x00000000u,0x3fa00000u}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x3f61a448u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, -1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, 1},
    {{{0x00000000u,0xbf800000u,0x00000000u,0x00000000u,0x40000000u,0x00000000u,0x3faa9fbeu}}, 1},
    {{{0x80000000u,0xbf800000u,0x80000000u,0x80000000u,0x3f800000u,0x80000000u,0x3faa9fbeu}}, 1},
    {{{0x80000000u,0xbf800000u,0x80000000u,0x80000000u,0x40000000u,0x80000000u,0x3faa9fbeu}}, 1},
    {{{0x00000000u,0xbf666666u,0x00000000u,0x00000000u,0x3f800000u,0x00000000u,0x3faa9fbeu}}, 1},
    {{{0x00000000u,0xbf666666u,0x00000000u,0x00000000u,0x40000000u,0x00000000u,0x3faa9fbeu}}, 1},
    {{{0x80000000u,0xbf666666u,0x80000000u,0x80000000u,0x3f800000u,0x80000000u,0x3faa9fbeu}}, 1},
    {{{0x80000000u,0xbf666666u,0x80000000u,0x80000000u,0x40000000u,0x80000000u,0x3faa9fbeu}}, 1},
}};
struct Group { std::size_t start,count; };
struct Source {
    supportNode::Sources frozen;
    std::string prepared,additionalJSON;
    std::array<std::string,3> fragment;
    std::vector<Case> cases;
    std::vector<Group> groups;
};
bool owned=false;
std::string oldContext=R"GLSL(
struct WSPViewContext { WSPInterval vx; WSPInterval vy; WSPInterval vz;
    WSPInterval E; WSPInterval K2; WSPInterval downScale; bool valid; };
WSPViewContext oldViewContext(vec3 rawV,float eta) {
    WSPViewContext c;
    c.vx=WSP_point(rawV.x);c.vy=WSP_point(rawV.y);c.vz=WSP_point(rawV.z);
    WSPInterval e=WSP_point(eta),one=WSP_interval(16777216,16777216);
    c.E=WSP_mul(e,e);
    WSPInterval V=WSP_add(WSP_add(WSP_mul(c.vx,c.vx),WSP_mul(c.vy,c.vy)),WSP_mul(c.vz,c.vz));
    c.K2=WSP_add(one,WSP_mul(c.E,WSP_sub(V,one)));
    c.downScale=WSP_mul(c.E,WSP_mul(c.vy,c.vy));
    uint vY=floatBitsToUint(rawV.y),eBits=floatBitsToUint(eta);
    c.valid=c.vx.valid&&c.vy.valid&&c.vz.valid&&e.valid
        &&(vY&0x80000000u)!=0u&&(vY&0x7fffffffu)!=0u
        &&eBits>0x3f800000u&&eBits<=0x40000000u&&c.E.valid&&V.valid&&c.K2.valid
        &&c.downScale.valid&&V.lo>0&&c.K2.lo>0;
    return c;
}
)GLSL";
std::string makeFragment(const std::string& module,int role) {
    std::string fs="#version 330 compatibility\n"+module+"\n";
    if(role==0) fs+=oldContext;
    fs+="uniform uvec3 wspViewBits; uniform uvec3 wspTargets[48]; uniform uint wspEtaBits;\n"
        "uniform int wspCount; uniform int wspSelected;\n";
    for(int slot=0;slot<8;++slot) fs+="layout(location="+std::to_string(slot)+") out uvec4 wsp"+std::to_string(slot)+";\n";
    fs+="void main(){vec3 v=uintBitsToFloat(wspViewBits);float eta=uintBitsToFloat(wspEtaBits);\n";
    fs+=role==0?"WSPViewContext context=oldViewContext(v,eta);\n":"WSPViewContext context=waterSunSupportPrepareView(v,eta);\n";
    fs+="int selectedClass=-2;uint checksum=0u;\nfor (int node=0;node<wspCount;++node){\n"
        "vec3 t=uintBitsToFloat(wspTargets[node]);int c=";
    fs+=role==2?"waterSunSupportClassPrepared(context,t);\n":"waterSunSupportClass(v,t,eta);\n";
    fs+="checksum+=uint(c+1)*uint(node+1);if(node==wspSelected)selectedClass=c;}\n"
        "wsp0=uvec4(uint(selectedClass+1),floatBitsToUint(v));\n"
        "wsp1=uvec4(floatBitsToUint(uintBitsToFloat(wspTargets[wspSelected])),floatBitsToUint(eta));\n";
    for(int i=0;i<6;++i) {
        const std::string field="context."+intervals[std::size_t(i)];
        fs+="wsp"+std::to_string(i+2)+"=uvec4(uint("+field+".lo),uint("+field+".hi),uint("+field+".valid),";
        fs+=i==0?"checksum);\n":i==1?"uint(wspCount));\n":i==2?"uint(context.valid));\n":"0u);\n";
    }
    return fs+"}\n";
}
Source loadPrepared(const fs::path& old,const fs::path& prepared,const fs::path& corpus) {
    Source s;s.frozen=supportNode::load(old,corpus);s.prepared=read(prepared);
    require(digest(s.prepared)==preparedSHA,"prepared source SHA differs");
    const fs::path tools=fs::path(__FILE__).parent_path();
    require(digest(read(tools/"water_sun_support_node_probe.cpp"))==dependencySHA,"included utility SHA differs");
    require(digest(read(tools/"test_water_sun_prepared.py"))==fixtureSourceSHA,"additional CPU fixture source SHA differs");
    s.cases=s.frozen.cases;
    std::ostringstream extra;extra<<"{\"schema\":\"aqualumen-prepared-node-additional-v1\",\"fixtureSourceSHA256\":"
        <<quote(fixtureSourceSHA)<<",\"CPUFixtureOnly\":true,\"physicalOracle\":false,\"cases\":[";
    for(std::size_t i=0;i<additional.size();++i) {
        const auto& a=additional[i];s.cases.push_back({a.bits,-2,a.cpuClass});
        if(i)extra<<',';
        extra<<"{\"index\":"<<i<<",\"origin\":"<<quote(i<24?"invalid-boundary":"signed-zero-nonunit")
            <<",\"inputBits\":"<<numbers(a.bits.data(),7)<<",\"cpuClass\":"<<a.cpuClass<<'}';
    }
    s.additionalJSON=extra.str()+"]}\n";
    for(std::size_t start=0;start<s.cases.size();) {
        std::size_t count=1;
        while(start+count<s.cases.size()&&count<48) {
            const auto& a=s.cases[start].bits;const auto& b=s.cases[start+count].bits;
            if(!std::equal(a.begin(),a.begin()+3,b.begin())||a[6]!=b[6])break;
            ++count;
        }
        s.groups.push_back({start,count});start+=count;
    }
    s.fragment[0]=makeFragment(s.frozen.module,0);
    s.fragment[1]=makeFragment(s.prepared,1);s.fragment[2]=makeFragment(s.prepared,2);return s;
}
int cpu(const Source& s) {
    std::cout<<"{\"schema\":\"aqualumen-prepared-node-construction-v1\",\"nativeGLExecuted\":false,"
        "\"count\":"<<s.cases.size()<<",\"frozenCount\":344,\"additionalCount\":32,\"groupCount\":"<<s.groups.size()
        <<",\"roles\":[\"old\",\"wrapper\",\"reused\"],\"intervals\":[\"vx\",\"vy\",\"vz\",\"E\",\"K2\",\"downScale\"],"
        "\"targetCount\":8,\"sourceSHA256\":{\"old\":"<<quote(moduleSHA)<<",\"prepared\":"<<quote(preparedSHA)
        <<",\"corpus\":"<<quote(corpusSHA)<<",\"utilities\":"<<quote(dependencySHA)<<"},\"fragmentSources\":{";
    for(int role=0;role<3;++role){if(role)std::cout<<',';std::cout<<quote(roles[role])<<':'<<quote(s.fragment[role]);}
    std::cout<<"},\"additionalInputs\":"<<s.additionalJSON<<"}\n";return 0;
}
struct Program { GLuint id=0; std::array<GLint,5> locations={}; std::array<GLint,48> targets={}; };
std::string eightState(GLuint program,GLuint fbo,int x) {
    const auto base=state(program,fbo,x);
    for(int slot=0;slot<8;++slot) {
        GLint draw=0;glGetIntegerv(GL_DRAW_BUFFER0+slot,&draw);
        require(draw==GLint(GL_COLOR_ATTACHMENT0+slot),"eight actual integer draw routes differ");
    }
    glOkay("eight-output actual state");return base;
}
Program makeProgram(const Source& s,int role,const fs::path& output,std::ostringstream& report) {
    Program p;p.id=glCreateProgram();
    for(const auto& entry:std::array<std::pair<GLenum,std::string>,2>{{
        {GL_VERTEX_SHADER,vertex},{GL_FRAGMENT_SHADER,s.fragment[std::size_t(role)]}}}) {
        GLuint sh=shader(entry.first,entry.second);glAttachShader(p.id,sh);glDeleteShader(sh);
    }
    glLinkProgram(p.id);GLint linked=0;glGetProgramiv(p.id,GL_LINK_STATUS,&linked);
    if(!linked){char log[16384]={};glGetProgramInfoLog(p.id,sizeof(log),nullptr,log);throw std::runtime_error(log);}
    std::array<GLuint,2> attached={};GLsizei attachedCount=0;glGetAttachedShaders(p.id,2,&attachedCount,attached.data());
    require(attachedCount==2,"exact two actual stages required");bool haveVS=false,haveFS=false;
    for(GLuint sh:attached) {
        GLint type=0,length=0;glGetShaderiv(sh,GL_SHADER_TYPE,&type);glGetShaderiv(sh,GL_SHADER_SOURCE_LENGTH,&length);
        require(length>0&&length<65536,"bounded attached source required");
        std::string bytes(std::size_t(length),'\0');GLsizei used=0;glGetShaderSource(sh,length,&used,bytes.data());bytes.resize(std::size_t(used));
        bool vs=type==GL_VERTEX_SHADER;require(vs||type==GL_FRAGMENT_SHADER,"unexpected actual stage");
        require(!(vs?haveVS:haveFS),"duplicate attached type");if(vs)haveVS=true;else haveFS=true;
        require(bytes==(vs?vertex:s.fragment[std::size_t(role)]),"actual attached source differs");
        write(output/(roles[std::size_t(role)]+(vs?"-attached-vertex.glsl":"-attached-fragment.glsl")),bytes);
    }
    require(haveVS&&haveFS,"missing attached stage");
    const char* names[]={"wspViewBits","wspTargets[0]","wspEtaBits","wspCount","wspSelected"};
    GLuint indices[5]={};GLint types[5]={},sizes[5]={};glGetUniformIndices(p.id,5,names,indices);
    for(GLuint index:indices)require(index!=GL_INVALID_INDEX,"active typed uniform missing");
    glGetActiveUniformsiv(p.id,5,indices,GL_UNIFORM_TYPE,types);glGetActiveUniformsiv(p.id,5,indices,GL_UNIFORM_SIZE,sizes);
    if(role)report<<',';
    report<<"{\"role\":"<<quote(roles[std::size_t(role)])<<",\"program\":"<<p.id
        <<",\"vertexSHA256\":"<<quote(digest(vertex))<<",\"fragmentSHA256\":"<<quote(digest(s.fragment[std::size_t(role)]))
        <<",\"attachedTypes\":["<<GL_VERTEX_SHADER<<','<<GL_FRAGMENT_SHADER<<"],\"uniforms\":[";
    for(int i=0;i<5;++i) {
        p.locations[std::size_t(i)]=glGetUniformLocation(p.id,names[i]);
        const GLint expected=i<2?GL_UNSIGNED_INT_VEC3:i==2?GL_UNSIGNED_INT:GL_INT;
        require(p.locations[std::size_t(i)]>=0&&types[i]==expected&&sizes[i]==(i==1?48:1),"actual uniform type/size/location differs");
        if(i)report<<',';
        report<<"{\"name\":"<<quote(names[i])<<",\"type\":"<<types[i]<<",\"size\":"<<sizes[i]
            <<",\"location\":"<<p.locations[std::size_t(i)]<<'}';
    }
    report<<"]}";
    for(int node=0;node<48;++node) {
        p.targets[std::size_t(node)]=glGetUniformLocation(p.id,("wspTargets["+std::to_string(node)+"]").c_str());
        require(p.targets[std::size_t(node)]>=0,"actual target array element missing");
    }
    for(int slot=0;slot<8;++slot)require(glGetFragDataLocation(p.id,("wsp"+std::to_string(slot)).c_str())==slot,"actual eight output locations differ");
    glOkay("program attached/input/output reflection");return p;
}
int renderPrepared(const Source& s,const fs::path& output) {
    static_assert(sizeof(std::uint32_t)==4,"uint32 output required");
    const std::uint32_t one=1;require(*reinterpret_cast<const unsigned char*>(&one)==1,"little-endian host required");
    require(!fs::exists(output)&&!fs::is_symlink(output),"NEW output required");
    Context context;
    const auto* rt=glGetString(GL_RENDERER);const auto* vt=glGetString(GL_VERSION);const auto* lt=glGetString(GL_SHADING_LANGUAGE_VERSION);
    const auto* vendorText=glGetString(GL_VENDOR);
    require(rt&&vt&&lt&&vendorText,"renderer strings missing");const std::string renderer(reinterpret_cast<const char*>(rt));
    const std::string vendor(reinterpret_cast<const char*>(vendorText));
    require(vendor.find("NVIDIA")!=std::string::npos,"actual NVIDIA vendor required");
    require(renderer.find("RTX 3080 Ti")!=std::string::npos,"actual RTX 3080 Ti renderer required");
    GLint maxDraw=0,maxAttachments=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&maxDraw);glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS,&maxAttachments);
    require(maxDraw>=8&&maxAttachments>=8,"eight integer targets unavailable");
    require(fs::create_directories(output),"NEW output creation failed");owned=true;
    write(output/"old-module.glsl",s.frozen.module);write(output/"prepared-module.glsl",s.prepared);
    write(output/"cases.json",s.frozen.corpus);write(output/"additional-inputs.json",s.additionalJSON);
    std::vector<std::uint32_t> inputs;for(const auto& c:s.cases)inputs.insert(inputs.end(),c.bits.begin(),c.bits.end());
    write(output/"input-bits.u32",words(inputs));
    std::ostringstream programs;std::array<Program,3> linked={};
    for(int role=0;role<3;++role)linked[std::size_t(role)]=makeProgram(s,role,output,programs);
    std::array<GLuint,8> textures={};std::array<GLenum,8> buffers={};GLuint fbo=0;
    glGenTextures(8,textures.data());glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    for(int slot=0;slot<8;++slot) {
        buffers[std::size_t(slot)]=GL_COLOR_ATTACHMENT0+slot;glBindTexture(GL_TEXTURE_2D,textures[std::size_t(slot)]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32UI,GLsizei(s.cases.size()),1,0,GL_RGBA_INTEGER,GL_UNSIGNED_INT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        GLint format=0,width=0,height=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&width);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&height);
        require(format==GL_RGBA32UI&&width==GLint(s.cases.size())&&height==1,"actual target storage differs");
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[std::size_t(slot)],GL_TEXTURE_2D,textures[std::size_t(slot)],0);
        GLint component=0,object=0;glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,buffers[std::size_t(slot)],GL_FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE,&component);
        glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,buffers[std::size_t(slot)],GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME,&object);
        require(component==GL_UNSIGNED_INT&&object==GLint(textures[std::size_t(slot)]),"actual integer attachment differs");
    }
    glDrawBuffers(8,buffers.data());require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"integer FBO incomplete");
    for(GLenum cap:{GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,GL_DITHER,GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB,GL_RASTERIZER_DISCARD,GL_COLOR_LOGIC_OP})glDisable(cap);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glBindBuffer(GL_PIXEL_PACK_BUFFER,0);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    using Maps=std::array<std::vector<std::uint32_t>,8>;
    std::array<std::array<Maps,2>,3> capture;std::ostringstream uploads,rawHashes;bool firstUpload=true,firstHash=true;
    for(int role=0;role<3;++role)for(int repeat=0;repeat<2;++repeat) {
        const auto& p=linked[std::size_t(role)];glUseProgram(p.id);
        const GLuint sentinel[4]={0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu};
        for(int slot=0;slot<8;++slot)glClearBufferuiv(GL_COLOR,slot,sentinel);
        for(std::size_t gi=0;gi<s.groups.size();++gi) {
            const auto& group=s.groups[gi];const auto& view=s.cases[group.start].bits;
            std::array<GLuint,144> targets={};
            for(std::size_t node=0;node<group.count;++node)std::copy_n(s.cases[group.start+node].bits.data()+3,3,targets.data()+3*node);
            glUniform3uiv(p.locations[0],1,view.data());glUniform3uiv(p.locations[1],48,targets.data());
            glUniform1ui(p.locations[2],view[6]);glUniform1i(p.locations[3],GLint(group.count));
            for(std::size_t node=0;node<group.count;++node) {
                const std::size_t index=group.start+node;glUniform1i(p.locations[4],GLint(node));
                auto query=[&]() {
                    Bits bits={};std::array<GLuint,144> actualTargets={};GLint count=0,selected=0;
                    glGetUniformuiv(p.id,p.locations[0],bits.data());glGetUniformuiv(p.id,p.locations[2],bits.data()+6);
                    for(int k=0;k<48;++k)glGetUniformuiv(p.id,p.targets[std::size_t(k)],actualTargets.data()+3*k);
                    glGetUniformiv(p.id,p.locations[3],&count);glGetUniformiv(p.id,p.locations[4],&selected);
                    require(actualTargets==targets&&count==GLint(group.count)&&selected==GLint(node),"queried target/count/selected differs");
                    std::copy_n(actualTargets.data()+3*node,3,bits.data()+3);
                    require(bits==s.cases[index].bits,"actual raw input bits differ");glOkay("typed bit queries");return bits;
                };
                const auto before=query();glViewport(GLint(index),0,1,1);const auto beforeState=eightState(p.id,fbo,int(index));
                glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
                const auto after=query();require(eightState(p.id,fbo,int(index))==beforeState,"draw state changed");
                if(!firstUpload)uploads<<',';
                firstUpload=false;
                uploads<<"{\"role\":"<<quote(roles[std::size_t(role)])<<",\"repeat\":"<<repeat<<",\"index\":"<<index
                    <<",\"group\":"<<gi<<",\"count\":"<<group.count<<",\"selected\":"<<node
                    <<",\"beforeBits\":"<<numbers(before.data(),7)<<",\"afterBits\":"<<numbers(after.data(),7)
                    <<",\"all48TargetBitsSHA256\":"<<quote(digest(std::string(reinterpret_cast<const char*>(targets.data()),sizeof(targets))))
                    <<",\"actualState\":"<<beforeState<<",\"allEightDrawRoutesQueriedExact\":true";
                if(node==0)uploads<<",\"actual48TargetBits\":"<<numbers(targets.data(),144);
                uploads<<'}';
            }
        }
        for(int slot=0;slot<8;++slot) {
            auto& map=capture[std::size_t(role)][std::size_t(repeat)][std::size_t(slot)];map.resize(s.cases.size()*4);
            glReadBuffer(buffers[std::size_t(slot)]);glReadPixels(0,0,GLsizei(s.cases.size()),1,GL_RGBA_INTEGER,GL_UNSIGNED_INT,map.data());
            const std::string name=roles[std::size_t(role)]+"-"+(repeat?"repeat-":"")+"slot"+std::to_string(slot)+".rgba32ui";
            write(output/name,words(map));if(!firstHash)rawHashes<<',';firstHash=false;rawHashes<<quote(name)<<':'<<quote(digest(words(map)));
        }
        glOkay("all integer captures");
    }
    bool echo=true,classesEqual=true,cpuMatch=true,intervalsEqual=true,contextEqual=true,checksumEqual=true,repeats=true,additionalMatch=true,qualified=true;
    for(int role=0;role<3;++role)repeats=repeats&&(capture[std::size_t(role)][0]==capture[std::size_t(role)][1]);
    std::ostringstream results;
    for(std::size_t index=0;index<s.cases.size();++index) {
        const auto& c=s.cases[index];std::array<int,3> actual={};
        for(int role=0;role<3;++role) {
            const auto& maps=capture[std::size_t(role)][0];const auto* a=maps[0].data()+4*index;const auto* b=maps[1].data()+4*index;
            echo=echo&&std::equal(c.bits.begin(),c.bits.begin()+3,a+1)&&std::equal(c.bits.begin()+3,c.bits.end(),b);
            qualified=qualified&&a[0]<=2u;actual[std::size_t(role)]=a[0]<=2u?int(a[0])-1:-2;
            cpuMatch=cpuMatch&&actual[std::size_t(role)]==c.cpuClass;
            if(index>=344)additionalMatch=additionalMatch&&actual[std::size_t(role)]==c.cpuClass;
            for(int slot=2;slot<8;++slot)qualified=qualified&&maps[std::size_t(slot)][4*index+2]<=1u;
            qualified=qualified&&maps[4][4*index+3]<=1u;
        }
        classesEqual=classesEqual&&actual[0]==actual[1]&&actual[0]==actual[2];
        for(int role=1;role<3;++role)for(int slot=2;slot<8;++slot)
            intervalsEqual=intervalsEqual&&std::equal(capture[0][0][std::size_t(slot)].data()+4*index,capture[0][0][std::size_t(slot)].data()+4*index+3,
                capture[std::size_t(role)][0][std::size_t(slot)].data()+4*index);
        for(int role=1;role<3;++role)contextEqual=contextEqual&&capture[0][0][4][4*index+3]==capture[std::size_t(role)][0][4][4*index+3];
        if(index)results<<',';
        results<<"{\"index\":"<<index<<",\"origin\":"<<quote(index<344?"frozen344":index<368?"additional-invalid-boundary":"additional-signed-zero-nonunit")
            <<",\"classes\":["<<actual[0]<<','<<actual[1]<<','<<actual[2]<<"],\"cpuClass\":"<<c.cpuClass<<'}';
    }
    for(const auto& group:s.groups) {
        std::uint32_t expected=0;for(std::size_t node=0;node<group.count;++node)expected+=std::uint32_t(s.cases[group.start+node].cpuClass+1)*std::uint32_t(node+1);
        for(std::size_t node=0;node<group.count;++node)for(int role=0;role<3;++role) {
            const auto& maps=capture[std::size_t(role)][0];const std::size_t word=4*(group.start+node)+3;
            checksumEqual=checksumEqual&&maps[2][word]==expected&&maps[3][word]==group.count;
        }
    }
    qualified=qualified&&echo;const bool accepted=qualified&&classesEqual&&cpuMatch&&intervalsEqual&&contextEqual&&checksumEqual&&repeats&&additionalMatch;
    const std::string status=!qualified?"INCONCLUSIVE":accepted?"PASS":"RED";
    std::ostringstream report;report<<"{\"schema\":\"aqualumen-prepared-node-native-v1\",\"renderer\":"<<quote(renderer)
        <<",\"vendor\":"<<quote(vendor)<<",\"GL\":"<<quote(reinterpret_cast<const char*>(vt))<<",\"GLSL\":"<<quote(reinterpret_cast<const char*>(lt))
        <<",\"sourceSHA256\":{\"old\":"<<quote(moduleSHA)<<",\"prepared\":"<<quote(preparedSHA)<<",\"corpus\":"<<quote(corpusSHA)
        <<",\"utilities\":"<<quote(dependencySHA)<<",\"fixtureSource\":"<<quote(fixtureSourceSHA)<<"},\"count\":376,\"frozenCount\":344,\"additionalCount\":32"
        <<",\"roles\":[\"old\",\"wrapper\",\"reused\"],\"width\":376,\"height\":1,\"targetInternalFormat\":"<<GL_RGBA32UI
        <<",\"targetCount\":8,\"intervals\":[\"vx\",\"vy\",\"vz\",\"E\",\"K2\",\"downScale\"],\"rawByteOrder\":\"little-endian uint32; interval endpoints signed int32 bit patterns\""
        <<",\"programs\":["<<programs.str()<<"],\"uploads\":["<<uploads.str()<<"],\"results\":["<<results.str()<<"],\"rawSHA256\":{"<<rawHashes.str()<<"}";
    auto flag=[&](const char* name,bool value){report<<",\""<<name<<"\":"<<(value?"true":"false");};
    flag("rawInputEchoExact",echo);flag("classesEqual",classesEqual);flag("matchesLiteralCPUClass",cpuMatch);
    flag("allSixIntervalTriplesEqual",intervalsEqual);flag("contextValidEqual",contextEqual);flag("groupChecksumsEqual",checksumEqual);
    flag("repeatByteIdentical",repeats);flag("additionalMatchesLiteralCPUCases",additionalMatch);flag("accepted",accepted);
    report<<",\"status\":"<<quote(status)<<",\"nativeGLExecuted\":true,\"physicalOracleForAdditional\":false,\"waterMainExecuted\":false,"
        "\"IrisAccepted\":false,\"shippingAccepted\":false,\"performanceAccepted\":false,\"scope\":\"Standalone raw integer certificate identity only; no actual water-main, physical/energy/AA/visual or speed acceptance.\"}\n";
    write(output/"result.json",report.str());
    for(const auto& p:linked)glDeleteProgram(p.id);
    glDeleteTextures(8,textures.data());glDeleteFramebuffers(1,&fbo);
    std::cout<<status<<" prepared node differential376 "<<output<<'\n';return !qualified?2:accepted?0:1;
}
}
int main(int argc,char** argv) {
    try {
        if(argc==5&&std::string(argv[1])=="--cpu-contract")
            return preparedNode::cpu(preparedNode::loadPrepared(argv[2],argv[3],argv[4]));
        if(argc==6&&std::string(argv[1])=="--gpu")
            return preparedNode::renderPrepared(preparedNode::loadPrepared(argv[2],argv[3],argv[4]),argv[5]);
        throw std::runtime_error("usage: --cpu-contract OLD PREPARED CORPUS | --gpu OLD PREPARED CORPUS NEWOUTPUT");
    } catch(const std::exception& error){
        std::cerr<<error.what()<<'\n';
        if(preparedNode::owned&&argc==6)try{supportNode::write(supportNode::fs::path(argv[5])/"failure.txt",std::string(error.what())+'\n');}catch(...){}
        return 2;
    }
}
