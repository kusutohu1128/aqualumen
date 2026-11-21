// TEST ONLY. CPU construction is agent-runnable; root exclusively executes GL.
#include <epoxy/gl.h>
#include <epoxy/egl.h>
#include <openssl/sha.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace supportNode {
namespace fs = std::filesystem;
constexpr const char* moduleSHA = "f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a";
constexpr const char* corpusSHA = "24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48";
constexpr const char* rawFormat = "two RGBA32UI targets; class+1 and seven raw binary32 bit patterns";
using Bits = std::array<std::uint32_t, 7>;
struct Case { Bits bits; int exactClass; int cpuClass; };
struct Sources { std::string module, corpus, vertex, fragment; std::vector<Case> cases; };
bool ownedOutput = false;

void require(bool okay, const std::string& why) {
    if (!okay) throw std::runtime_error("INCONCLUSIVE support node: " + why);
}
std::string read(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(bool(input), "cannot read " + path.string());
    input.seekg(0, std::ios::end);
    const auto length = input.tellg();
    require(length >= 0 && length <= 1048576, "bounded source/corpus required");
    input.seekg(0);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}
std::string digest(const std::string& bytes) {
    unsigned char value[SHA256_DIGEST_LENGTH] = {};
    SHA256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(), value);
    std::ostringstream out; out << std::hex << std::setfill('0');
    for (unsigned char byte : value) out << std::setw(2) << unsigned(byte);
    return out.str();
}
std::string quote(const std::string& value) {
    std::ostringstream out; out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << char(c);
        else if (c == '\n') out << "\\n";
        else if (c == '\r') out << "\\r";
        else if (c == '\t') out << "\\t";
        else { require(c >= 32, "unsupported JSON control character"); out << char(c); }
    }
    return out.str() + '"';
}
const std::string vertex = "#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
std::string fragment(const std::string& module) {
    return "#version 330 compatibility\n" + module + "\n"
        "uniform uvec3 wspViewBits; uniform uvec3 wspTargetBits; uniform uint wspEtaBits;\n"
        "layout(location=0) out uvec4 wspClassAndView;\n"
        "layout(location=1) out uvec4 wspTargetAndEta;\n"
        "void main(){vec3 v=uintBitsToFloat(wspViewBits);vec3 t=uintBitsToFloat(wspTargetBits);\n"
        "float eta=uintBitsToFloat(wspEtaBits);int c=waterSunSupportClass(v,t,eta);\n"
        "wspClassAndView=uvec4(uint(c+1),floatBitsToUint(v));\n"
        "wspTargetAndEta=uvec4(floatBitsToUint(t),floatBitsToUint(eta));}\n";
}
Sources load(const fs::path& module, const fs::path& corpus) {
    Sources out; out.module = read(module); out.corpus = read(corpus);
    // Hard pins are checked BEFORE any GL call or output creation. Parsing is
    // deliberately only for this frozen corpus, not a permissive JSON reader.
    require(digest(out.module) == moduleSHA, "module source SHA differs");
    require(digest(out.corpus) == corpusSHA, "corpus source SHA differs");
    const std::regex entry("\\\"inputBits\\\"\\s*:\\s*\\[([^\\]]*)\\]\\s*,\\s*\\\"exactClass\\\"\\s*:\\s*(-?[01])\\s*,\\s*\\\"cpuClass\\\"\\s*:\\s*(-?[01])");
    const std::regex hex("\\\"([0-9a-f]{8})\\\"");
    for (std::sregex_iterator it(out.corpus.begin(), out.corpus.end(), entry), end; it != end; ++it) {
        Case c = {}; const auto values = (*it)[1].str(); std::size_t index = 0;
        for (std::sregex_iterator bit(values.begin(), values.end(), hex); bit != end; ++bit) {
            require(index < c.bits.size(), "too many input fields");
            c.bits[index++] = std::uint32_t(std::stoul((*bit)[1].str(), nullptr, 16));
        }
        require(index == c.bits.size(), "seven bit-preserving input fields required");
        c.exactClass = std::stoi((*it)[2].str()); c.cpuClass = std::stoi((*it)[3].str());
        require(c.cpuClass == -1 || c.cpuClass == c.exactClass, "false CPU certificate in corpus");
        out.cases.push_back(c);
    }
    require(out.cases.size() == 344, "exact fixed344 corpus required");
    out.vertex = vertex; out.fragment = fragment(out.module); return out;
}
std::string classes(const Sources& source) {
    std::array<int, 3> counts = {};
    for (const auto& c : source.cases) ++counts[std::size_t(c.cpuClass+1)];
    return "{\"absent\":" + std::to_string(counts[1]) + ",\"supported\":" +
        std::to_string(counts[2]) + ",\"unknown\":" + std::to_string(counts[0]) + '}';
}
int cpuContract(const Sources& source) {
    std::cout << "{\"schema\":\"aqualumen-support-node-construction-v1\",\"nativeGLExecuted\":false,"
        "\"count\":" << source.cases.size() << ",\"classes\":" << classes(source)
        << ",\"moduleSHA256\":" << quote(moduleSHA) << ",\"corpusSHA256\":" << quote(corpusSHA)
        << ",\"rawFormat\":" << quote(rawFormat) << ",\"vertexSource\":" << quote(source.vertex)
        << ",\"fragmentSource\":" << quote(source.fragment) << "}\n";
    return 0;
}
void write(const fs::path& path, const std::string& bytes) {
    std::ofstream out(path, std::ios::binary);
    out.write(bytes.data(), std::streamsize(bytes.size()));
    require(bool(out), "cannot write " + path.string());
}
struct Context {
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    Context() {
        auto platform = reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
        require(platform != nullptr, "EGL platform entry point missing");
        display = platform(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, nullptr);
        if (!eglInitialize(display, nullptr, nullptr)) {
            auto query = reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
            EGLDeviceEXT devices[8]; EGLint count = 0;
            require(query && query(8, devices, &count) && count > 0, "EGL device unavailable");
            display = platform(EGL_PLATFORM_DEVICE_EXT, devices[0], nullptr);
            require(eglInitialize(display, nullptr, nullptr), "EGL device initialization failed");
        }
        require(eglBindAPI(EGL_OPENGL_API), "cannot bind OpenGL API");
        const EGLint attrs[] = {EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
        EGLConfig config; EGLint count = 0;
        require(eglChooseConfig(display, attrs, &config, 1, &count) && count > 0, "EGL config unavailable");
        const EGLint size[] = {EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
        surface = eglCreatePbufferSurface(display, config, size);
        const EGLint profile[] = {EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,
            EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context = eglCreateContext(display, config, EGL_NO_CONTEXT, profile);
        require(surface != EGL_NO_SURFACE && context != EGL_NO_CONTEXT &&
            eglMakeCurrent(display, surface, surface, context), "GL compatibility context unavailable");
    }
    ~Context() {
        eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        eglDestroyContext(display, context); eglDestroySurface(display, surface); eglTerminate(display);
    }
};
void glOkay(const std::string& where) { require(glGetError() == GL_NO_ERROR, "GL error: " + where); }
GLuint shader(GLenum type, const std::string& source) {
    GLuint result = glCreateShader(type);
    const char* bytes = source.data(); const GLint length = GLint(source.size());
    glShaderSource(result, 1, &bytes, &length); glCompileShader(result);
    GLint okay = 0; glGetShaderiv(result, GL_COMPILE_STATUS, &okay);
    if (!okay) { char log[16384] = {}; glGetShaderInfoLog(result, sizeof(log), nullptr, log);
        throw std::runtime_error("INCONCLUSIVE support node compile: " + std::string(log)); }
    return result;
}
std::string numbers(const std::uint32_t* values, std::size_t count) {
    std::ostringstream out; out << '[';
    for (std::size_t i = 0; i < count; ++i) { if (i) out << ','; out << values[i]; }
    return out.str() + ']';
}
std::string words(const std::vector<std::uint32_t>& values) {
    return {reinterpret_cast<const char*>(values.data()), values.size()*sizeof(std::uint32_t)};
}
std::string state(GLuint program, GLuint fbo, int x) {
    GLint actualProgram=0, drawFbo=0, readFbo=0, viewport[4]={}, pack=0, pbo=0;
    glGetIntegerv(GL_CURRENT_PROGRAM, &actualProgram);
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &drawFbo); glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &readFbo);
    glGetIntegerv(GL_VIEWPORT, viewport); glGetIntegerv(GL_PACK_ALIGNMENT, &pack);
    glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &pbo);
    require(actualProgram == GLint(program) && drawFbo == GLint(fbo) && readFbo == GLint(fbo)
        && viewport[0] == x && viewport[1] == 0 && viewport[2] == 1 && viewport[3] == 1
        && pack == 1 && pbo == 0, "actual program/FBO/viewport/pack state differs");
    const std::array<GLenum,9> caps = {GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,
        GL_DITHER,GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB,GL_RASTERIZER_DISCARD,GL_COLOR_LOGIC_OP};
    for (const auto cap : caps) require(!glIsEnabled(cap), "unexpected raster capability enabled");
    for (int slot=0; slot<2; ++slot) { GLint draw=0; glGetIntegerv(GL_DRAW_BUFFER0+slot, &draw);
        require(draw == GLint(GL_COLOR_ATTACHMENT0+slot), "actual integer draw routing differs"); }
    GLboolean mask[4] = {}; glGetBooleanv(GL_COLOR_WRITEMASK, mask);
    require(mask[0] && mask[1] && mask[2] && mask[3], "color mask differs");
    GLint polygon[2] = {}; glGetIntegerv(GL_POLYGON_MODE, polygon);
    require(polygon[0] == GL_FILL && polygon[1] == GL_FILL, "actual polygon raster mode differs");
    glOkay("actual draw state query");
    std::ostringstream out;
    out << "{\"program\":" << actualProgram << ",\"drawFBO\":" << drawFbo
        << ",\"readFBO\":" << readFbo << ",\"viewport\":[" << x
        << ",0,1,1],\"packAlignment\":1,\"pixelPackBuffer\":0,\"disabledRasterCapabilities\":true,"
        "\"drawBuffers\":[" << GL_COLOR_ATTACHMENT0 << ',' << GL_COLOR_ATTACHMENT1 << "]}";
    return out.str();
}
int render(const Sources& source, const fs::path& output) {
    static_assert(sizeof(std::uint32_t) == 4 && sizeof(GLuint) == 4, "exact uint32 required");
    const std::uint32_t one = 1;
    require(*reinterpret_cast<const unsigned char*>(&one) == 1, "little-endian export host required");
    require(!fs::exists(output) && !fs::is_symlink(output), "NEW output required");
    Context context;
    const auto* rendererText = glGetString(GL_RENDERER); const auto* versionText = glGetString(GL_VERSION);
    const auto* languageText = glGetString(GL_SHADING_LANGUAGE_VERSION);
    require(rendererText && versionText && languageText, "actual renderer/version strings unavailable");
    const std::string renderer(reinterpret_cast<const char*>(rendererText));
    require(renderer.find("RTX 3080 Ti") != std::string::npos, "actual RTX 3080 Ti renderer required");
    GLuint program = glCreateProgram();
    for (const auto& entry : std::array<std::pair<GLenum,std::string>,2>{{
        {GL_VERTEX_SHADER,source.vertex},{GL_FRAGMENT_SHADER,source.fragment}}}) {
        const auto stage = shader(entry.first, entry.second); glAttachShader(program, stage); glDeleteShader(stage);
    }
    glLinkProgram(program); GLint linked=0; glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) { char log[16384] = {}; glGetProgramInfoLog(program,sizeof(log),nullptr,log);
        throw std::runtime_error("INCONCLUSIVE support node link: " + std::string(log)); }
    require(fs::create_directories(output), "cannot create NEW output"); ownedOutput = true;
    write(output/"module.glsl", source.module); write(output/"cases.json", source.corpus);
    std::array<GLuint,2> attached = {}; GLsizei attachedCount=0;
    glGetAttachedShaders(program,2,&attachedCount,attached.data());
    require(attachedCount == 2, "exactly two attached shader stages required");
    for (const auto stage : attached) {
        GLint type=0, length=0; glGetShaderiv(stage,GL_SHADER_TYPE,&type);
        glGetShaderiv(stage,GL_SHADER_SOURCE_LENGTH,&length);
        require(length > 0 && length < 65536, "bounded attached shader required");
        std::string actual(std::size_t(length), '\0'); GLsizei used=0;
        glGetShaderSource(stage,length,&used,actual.data()); actual.resize(std::size_t(used));
        const bool vertexStage = type == GL_VERTEX_SHADER;
        require(vertexStage || type == GL_FRAGMENT_SHADER, "unexpected attached shader type");
        require(actual == (vertexStage ? source.vertex : source.fragment), "actual attached source differs");
        write(output/(vertexStage ? "attached-vertex.glsl" : "attached-fragment.glsl"), actual);
    }
    const char* names[] = {"wspViewBits","wspTargetBits","wspEtaBits"};
    GLuint indices[3] = {}; GLint types[3] = {}, sizes[3] = {}, locations[3] = {};
    glGetUniformIndices(program,3,names,indices);
    for (const auto index : indices) require(index != GL_INVALID_INDEX, "active integer uniform missing");
    glGetActiveUniformsiv(program,3,indices,GL_UNIFORM_TYPE,types);
    glGetActiveUniformsiv(program,3,indices,GL_UNIFORM_SIZE,sizes);
    for (int i=0; i<3; ++i) {
        locations[i] = glGetUniformLocation(program,names[i]);
        require(locations[i] >= 0 && sizes[i] == 1 &&
            types[i] == (i<2 ? GL_UNSIGNED_INT_VEC3 : GL_UNSIGNED_INT), "actual typed integer uniform differs");
    }
    require(glGetFragDataLocation(program,"wspClassAndView") == 0 &&
        glGetFragDataLocation(program,"wspTargetAndEta") == 1, "actual integer output locations differ");
    std::array<GLuint,2> textures = {}; GLuint fbo=0;
    glGenTextures(2,textures.data()); glGenFramebuffers(1,&fbo); glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    const GLenum buffers[] = {GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};
    for (int slot=0; slot<2; ++slot) {
        glBindTexture(GL_TEXTURE_2D,textures[slot]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32UI,GLsizei(source.cases.size()),1,0,GL_RGBA_INTEGER,GL_UNSIGNED_INT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        GLint format=0,width=0,height=0;
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&width);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&height);
        require(format == GL_RGBA32UI && width == GLint(source.cases.size()) && height == 1, "actual RGBA32UI storage differs");
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[slot],GL_TEXTURE_2D,textures[slot],0);
        GLint component=0, object=0;
        glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,buffers[slot],GL_FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE,&component);
        glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,buffers[slot],GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME,&object);
        require(component == GL_UNSIGNED_INT && object == GLint(textures[slot]), "actual integer attachment differs");
    }
    glDrawBuffers(2,buffers); require(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE, "integer framebuffer incomplete");
    for (const auto cap : {GL_BLEND,GL_DEPTH_TEST,GL_CULL_FACE,GL_SCISSOR_TEST,GL_DITHER,
        GL_MULTISAMPLE,GL_FRAMEBUFFER_SRGB,GL_RASTERIZER_DISCARD,GL_COLOR_LOGIC_OP}) glDisable(cap);
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL); glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glPixelStorei(GL_PACK_ALIGNMENT,1); glPixelStorei(GL_UNPACK_ALIGNMENT,1); glUseProgram(program);
    glOkay("integer setup");
    std::vector<std::uint32_t> packedInputs;
    for (const auto& c : source.cases) packedInputs.insert(packedInputs.end(),c.bits.begin(),c.bits.end());
    write(output/"input-bits.u32",words(packedInputs));
    std::ostringstream report;
    report << "{\"schema\":\"aqualumen-support-node-native-v1\",\"renderer\":" << quote(renderer)
        << ",\"GL\":" << quote(reinterpret_cast<const char*>(versionText))
        << ",\"GLSL\":" << quote(reinterpret_cast<const char*>(languageText))
        << ",\"moduleSHA256\":" << quote(moduleSHA) << ",\"corpusSHA256\":" << quote(corpusSHA)
        << ",\"queriedVertexSHA256\":" << quote(digest(source.vertex))
        << ",\"queriedFragmentSHA256\":" << quote(digest(source.fragment))
        << ",\"inputBitsSHA256\":" << quote(digest(words(packedInputs)))
        << ",\"count\":" << source.cases.size() << ",\"width\":" << source.cases.size()
        << ",\"height\":1,\"targetInternalFormat\":" << GL_RGBA32UI
        << ",\"actualOutputLocations\":[0,1]"
        << ",\"rawFormat\":" << quote(rawFormat) << ",\"rawByteOrder\":\"little-endian uint32\",\"uniforms\":[";
    for (int i=0; i<3; ++i) { if(i) report << ',';
        report << "{\"name\":" << quote(names[i]) << ",\"type\":" << types[i]
            << ",\"size\":1,\"location\":" << locations[i] << '}'; }
    report << "],\"uploads\":[";
    std::array<std::array<std::vector<std::uint32_t>,2>,2> capture;
    std::array<std::array<std::string,2>,2> rawDigests;
    for (int repeat=0; repeat<2; ++repeat) {
        const GLuint sentinel[4] = {0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu};
        for(int slot=0;slot<2;++slot) glClearBufferuiv(GL_COLOR,slot,sentinel);
        for (std::size_t index=0; index<source.cases.size(); ++index) {
            const auto& values = source.cases[index].bits;
            glUniform3uiv(locations[0],1,values.data()); glUniform3uiv(locations[1],1,values.data()+3);
            glUniform1ui(locations[2],values[6]);
            auto query = [&]() {
                Bits actual = {}; glGetUniformuiv(program,locations[0],actual.data());
                glGetUniformuiv(program,locations[1],actual.data()+3); glGetUniformuiv(program,locations[2],actual.data()+6);
                require(actual == values, "queried uniform input bits differ"); glOkay("integer uniform query"); return actual;
            };
            const auto before = query(); glViewport(GLint(index),0,1,1);
            const auto beforeState = state(program,fbo,int(index));
            glBegin(GL_QUADS); glVertex2f(-1,-1); glVertex2f(1,-1); glVertex2f(1,1); glVertex2f(-1,1); glEnd();
            const auto after = query(); const auto afterState = state(program,fbo,int(index));
            require(beforeState == afterState, "draw/query altered certified raster state");
            if(repeat || index) report << ',';
            report << "{\"repeat\":" << repeat << ",\"index\":" << index
                << ",\"beforeBits\":" << numbers(before.data(),7) << ",\"afterBits\":" << numbers(after.data(),7)
                << ",\"actualState\":" << beforeState << '}';
        }
        for (int slot=0; slot<2; ++slot) {
            auto& values = capture[repeat][slot]; values.resize(source.cases.size()*4);
            glReadBuffer(buffers[slot]); glReadPixels(0,0,GLsizei(source.cases.size()),1,GL_RGBA_INTEGER,GL_UNSIGNED_INT,values.data());
            const auto bytes = words(values); rawDigests[repeat][slot] = digest(bytes);
            write(output/(std::string(repeat ? "repeat-" : "") + "slot" + std::to_string(slot) + ".rgba32ui"),bytes);
        }
        glOkay("integer draw/readback");
    }
    bool identical = capture[0] == capture[1], qualified = true, matches = true, exactSafe = true;
    report << "],\"results\":[";
    for (std::size_t i=0; i<source.cases.size(); ++i) {
        const auto& c=source.cases[i]; const auto* a=capture[0][0].data()+4*i; const auto* b=capture[0][1].data()+4*i;
        const bool bitEcho = std::equal(c.bits.begin(),c.bits.begin()+3,a+1) &&
            std::equal(c.bits.begin()+3,c.bits.end(),b);
        qualified = qualified && bitEcho && a[0] <= 2u;
        const int gpuClass = a[0] <= 2u ? int(a[0])-1 : -2;
        matches = matches && gpuClass == c.cpuClass;
        exactSafe = exactSafe && (gpuClass == -1 || gpuClass == c.exactClass);
        if(i) report << ',';
        report << "{\"index\":" << i << ",\"gpuClass\":" << gpuClass
            << ",\"cpuClass\":" << c.cpuClass << ",\"exactClass\":" << c.exactClass
            << ",\"rawInputEchoExact\":" << (bitEcho ? "true" : "false") << '}';
    }
    const bool accepted = qualified && identical && matches && exactSafe;
    const std::string status = !qualified ? "INCONCLUSIVE" : accepted ? "PASS" : "RED";
    report << "],\"rawSHA256\":{\"slot0\":" << quote(rawDigests[0][0]) << ",\"slot1\":" << quote(rawDigests[0][1])
        << ",\"repeat-slot0\":" << quote(rawDigests[1][0]) << ",\"repeat-slot1\":" << quote(rawDigests[1][1])
        << "},\"inputBitsQualified\":" << (qualified ? "true" : "false")
        << ",\"repeatByteIdentical\":" << (identical ? "true" : "false")
        << ",\"matchesLiteralCPUClass\":" << (matches ? "true" : "false")
        << ",\"noFalseExactCertificate\":" << (exactSafe ? "true" : "false")
        << ",\"accepted\":" << (accepted ? "true" : "false") << ",\"status\":" << quote(status)
        << ",\"nativeGLExecuted\":true,\"waterMainExecuted\":false,\"IrisAccepted\":false,\"shippingAccepted\":false,"
        "\"scope\":\"Pure literal integer support classifier344 fixed raw inputs only. No water-main, continuous-cap, energy, visibility, pixel-AA, visual or performance adoption. Unknown is preserved, never physical zero.\"}\n";
    write(output/"result.json",report.str());
    glDeleteProgram(program); glDeleteTextures(2,textures.data()); glDeleteFramebuffers(1,&fbo);
    std::cout << status << " standalone support classifier " << source.cases.size() << " cases " << output << '\n';
    return !qualified ? 2 : accepted ? 0 : 1;
}
}
int main(int argc, char** argv) {
    try {
        if (argc == 4 && std::string(argv[1]) == "--cpu-contract")
            return supportNode::cpuContract(supportNode::load(argv[2], argv[3]));
        if (argc == 5 && std::string(argv[1]) == "--gpu")
            return supportNode::render(supportNode::load(argv[2],argv[3]),argv[4]);
        throw std::runtime_error("usage: --cpu-contract MODULE CORPUS | --gpu MODULE CORPUS NEWOUTPUT");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        if (supportNode::ownedOutput && argc == 5) try {
            supportNode::write(std::filesystem::path(argv[4])/"failure.txt",std::string(error.what())+'\n');
        } catch (...) {}
        return 2;
    }
}
