// Standalone native GL proof for release/shaders/lib/rain_shelter*.glsl.
// Build: tools/rain-shelter-probe.sh   Run: build/rain-shelter-probe release/shaders [report.json]
#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <array>
#include <stdexcept>
#include <filesystem>
namespace fs = std::filesystem;
static std::string root;
struct Fail : std::runtime_error { using std::runtime_error::runtime_error; };

static std::string slurp(const std::string& p) {
    std::ifstream f(p); if (!f) throw Fail("missing " + p);
    std::stringstream s; s << f.rdbuf(); return s.str();
}
static std::string expand(const std::string& src) {
    std::stringstream in(src); std::string line, out;
    while (std::getline(in, line)) {
        auto q = line.find("#include \"");
        if (q == 0) {
            auto a = line.find('"') + 1, b = line.rfind('"');
            out += expand(slurp(root + line.substr(a, b - a))) + "\n";
        } else out += line + "\n";
    }
    return out;
}
static GLuint compile(GLenum type, const std::string& src, std::string& log) {
    GLuint s = glCreateShader(type);
    const char* c = src.c_str(); glShaderSource(s, 1, &c, nullptr); glCompileShader(s);
    GLint ok = 0; glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    GLint n = 0; glGetShaderiv(s, GL_INFO_LOG_LENGTH, &n);
    log.assign(n > 1 ? n : 1, 0); glGetShaderInfoLog(s, n, nullptr, log.data());
    if (!ok) { glDeleteShader(s); return 0; }
    return s;
}
static GLuint program(std::vector<GLuint> shaders, std::function<void(GLuint)> bind, std::string& log) {
    GLuint p = glCreateProgram();
    for (auto s : shaders) glAttachShader(p, s);
    if (bind) bind(p);
    glLinkProgram(p);
    GLint ok = 0; glGetProgramiv(p, GL_LINK_STATUS, &ok);
    GLint n = 0; glGetProgramiv(p, GL_INFO_LOG_LENGTH, &n);
    log.assign(n > 1 ? n : 1, 0); glGetProgramInfoLog(p, n, nullptr, log.data());
    return ok ? p : 0;
}

struct Face { float p[3]; float n[3]; float id; float mid[4]; };
struct Probe {
    GLuint img = 0, captureProg[4] = {}, queryProg = 0, vao = 0, vbo = 0, ssboIn = 0, ssboOut = 0;
    double cam[3] = {0, 0, 0};
    std::vector<Face> faces;
    std::vector<std::string> notes;
    int checks = 0, failures = 0;
    std::string json;

    // variant 0 solid, 1 cutout, 2 glass, 3 none (entity/block entity)
    void build() {
        const char* defs[4] = {"#define LOCAL_SOLID\n", "#define LOCAL_CUTOUT\n", "#define LOCAL_GLASS\n", ""};
        for (int v = 0; v < 4; ++v) {
            std::string vs = std::string("#version 430 compatibility\n") + defs[v] +
                "in vec4 mc_Entity;\nin vec4 at_midBlock;\nin vec3 aPos;\nin vec3 aNormal;\n"
                "#include \"/lib/rain_shelter_capture.glsl\"\nvoid main(){captureRainShelter(aPos,aNormal);gl_Position=vec4(2,2,2,1);gl_PointSize=1.0;}\n";
            std::string log;
            GLuint s = compile(GL_VERTEX_SHADER, expand(vs), log);
            if (!s) throw Fail("capture compile v" + std::to_string(v) + ": " + log);
            std::string fs = "#version 430 compatibility\nvoid main(){}\n";
            GLuint f = compile(GL_FRAGMENT_SHADER, fs, log);
            captureProg[v] = program({s, f}, [](GLuint p) {
                glBindAttribLocation(p, 0, "aPos"); glBindAttribLocation(p, 1, "aNormal");
                glBindAttribLocation(p, 2, "mc_Entity"); glBindAttribLocation(p, 3, "at_midBlock"); }, log);
            if (!captureProg[v]) throw Fail("capture link v" + std::to_string(v) + ": " + log);
        }
        std::string cs = "#version 430 compatibility\n#define RAIN_SHELTER_TERRAIN\nlayout(local_size_x=1) in;\n"
            "#include \"/lib/rain_shelter.glsl\"\nlayout(std430,binding=0) readonly buffer In{vec4 q[];};\n"
            "layout(std430,binding=1) writeonly buffer Out{float r[];};\n"
            "void main(){uint i=gl_GlobalInvocationID.x;r[i]=rainExposure(q[2*i].xyz,q[2*i+1].xyz,q[2*i].w);}\n";
        std::string log;
        GLuint s = compile(GL_COMPUTE_SHADER, expand(cs), log);
        if (!s) throw Fail("query compile: " + log);
        queryProg = program({s}, nullptr, log);
        if (!queryProg) throw Fail("query link: " + log);
        glGenTextures(1, &img);
        glBindTexture(GL_TEXTURE_2D, img);
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R32UI, 512, 129);
        glGenVertexArrays(1, &vao); glGenBuffers(1, &vbo); glGenBuffers(1, &ssboIn); glGenBuffers(1, &ssboOut);
    }
    void clear() { // equals Iris clear=true
        GLuint z = 0; glClearTexImage(img, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, &z);
    }
    void setCamera(double x, double y, double z) { cam[0] = x; cam[1] = y; cam[2] = z; }
    // top/bottom face of one block cell; corner vertices relative to camera
    void quad(int bx, int by, int bz, double y0, double y1x, double x0, double x1, double z0, double z1, float nx, float ny, float nz, float id, bool horiz = true) {
        (void)y1x; (void)horiz;
        double cx = bx + 0.5, cy = by + 0.5, cz = bz + 0.5;
        double xs[2] = {bx + x0, bx + x1}, zs[2] = {bz + z0, bz + z1};
        for (int i = 0; i < 4; ++i) {
            double wx = xs[i & 1], wz = zs[i >> 1], wy = by + y0;
            Face f{{float(wx - cam[0]), float(wy - cam[1]), float(wz - cam[2])}, {nx, ny, nz}, id,
                   {float((cx - wx) * 64), float((cy - wy) * 64), float((cz - wz) * 64), 0}};
            faces.push_back(f);
        }
    }
    void top(int bx, int by, int bz, double h, float id = 10001) { quad(bx, by, bz, h, 0, 0, 1, 0, 1, 0, 1, 0, id); }
    void capture(int variant) {
        glUseProgram(captureProg[variant]);
        glUniform3f(glGetUniformLocation(captureProg[variant], "cameraPosition"), float(cam[0]), float(cam[1]), float(cam[2]));
        glBindImageTexture(0, img, 0, GL_FALSE, 0, GL_READ_WRITE, GL_R32UI);
        GLint loc = glGetUniformLocation(captureProg[variant], "entityMetaImage");
        if (loc >= 0) glUniform1i(loc, 0);
        glBindVertexArray(vao); glBindBuffer(GL_ARRAY_BUFFER, vbo);
        glBufferData(GL_ARRAY_BUFFER, faces.size() * sizeof(Face), faces.data(), GL_STREAM_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Face), (void*)0);
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Face), (void*)12);
        glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, sizeof(Face), (void*)24);
        glVertexAttribPointer(3, 4, GL_FLOAT, GL_FALSE, sizeof(Face), (void*)28);
        for (int i = 0; i < 4; ++i) glEnableVertexAttribArray(i);
        glEnable(GL_RASTERIZER_DISCARD);
        glDrawArrays(GL_POINTS, 0, GLsizei(faces.size()));
        glDisable(GL_RASTERIZER_DISCARD);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
        faces.clear();
    }
    struct Q { double x, y, z, sky; };
    std::vector<float> query(const std::vector<Q>& qs) {
        std::vector<float> in;
        for (auto& q : qs) { // camera-relative
            in.insert(in.end(), {float(q.x - cam[0]), float(q.y - cam[1]), float(q.z - cam[2]), float(q.sky), 0, 1, 0, 0});
        }
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssboIn);
        glBufferData(GL_SHADER_STORAGE_BUFFER, in.size() * 4, in.data(), GL_STREAM_DRAW);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, ssboIn);
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssboOut);
        glBufferData(GL_SHADER_STORAGE_BUFFER, qs.size() * 4, nullptr, GL_STREAM_READ);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, ssboOut);
        glUseProgram(queryProg);
        glUniform3f(glGetUniformLocation(queryProg, "cameraPosition"), float(cam[0]), float(cam[1]), float(cam[2]));
        glBindImageTexture(0, img, 0, GL_FALSE, 0, GL_READ_ONLY, GL_R32UI);
        glUniform1i(glGetUniformLocation(queryProg, "entityMetaImage"), 0);
        glDispatchCompute(GLuint(qs.size()), 1, 1);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
        std::vector<float> out(qs.size());
        glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, out.size() * 4, out.data());
        return out;
    }
    int nonzero() {
        std::vector<unsigned> d(512 * 129);
        glGetTextureImage(img, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, GLsizei(d.size() * 4), d.data());
        int n = 0; for (size_t i = 512; i < d.size(); ++i) n += d[i] != 0; return n;
    }
    void expect(const std::string& name, double got, double lo, double hi, const std::string& tag) {
        ++checks; bool ok = got >= lo - 1e-4 && got <= hi + 1e-4; failures += !ok;
        char b[512]; snprintf(b, sizeof b, "{\"scene\":\"%s\",\"test\":\"%s\",\"value\":%.5f,\"range\":[%.3f,%.3f],\"pass\":%s}",
                              tag.c_str(), name.c_str(), got, lo, hi, ok ? "true" : "false");
        json += (json.empty() ? "" : ",\n") + std::string(b);
        std::printf("%s %-9s %-44s %.4f in [%.2f,%.2f]\n", ok ? "PASS" : "FAIL", tag.c_str(), name.c_str(), got, lo, hi);
    }
    void expectInt(const std::string& name, int got, int want, const std::string& tag) {
        expect(name, got, want, want, tag);
    }
};

// Same world relative to an arbitrary integer anchor, to cover negative coordinates.
static void scene(Probe& P, int ox, int oy, int oz, double cx, double cy, double cz, const std::string&) {
    P.setCamera(cx, cy, cz); P.clear();
    // ground top at oy+64; use cell by=oy+63 top 1.0
    for (int x = -140; x <= 140; ++x) { // long strip along x, rows z=0..8
        for (int z = 0; z <= 8; ++z) P.top(ox + x, oy + 63, oz + z, 1.0);
        if (P.faces.size() > 60000) P.capture(0);
    }
    P.capture(0);
    // Eaves/roof: solid roof 3 blocks above ground over x 10..13 z 1..3 (cell y=oy+66 ... top at oy+67)
    for (int x = 10; x <= 13; ++x) for (int z = 1; z <= 3; ++z) P.top(ox + x, oy + 66, oz + z, 1.0);
    // bright glass roof over x 20..22 z 1..3, clear glass (id 0)
    for (int x = 20; x <= 22; ++x) for (int z = 1; z <= 3; ++z) P.top(ox + x, oy + 66, oz + z, 1.0, 0.0f);
    // slab ceiling 0.5 m over x 30..31 (bottom slab at cell oy+65: top y=65.5)
    for (int x = 30; x <= 31; ++x) P.top(ox + x, oy + 65, oz + 1, 0.5, 10301);
    // carpet 1/16 and snow 0.25 on the ground: surfaces, not roofs
    P.top(ox + 40, oy + 64, oz + 1, 0.0625); P.top(ox + 42, oy + 64, oz + 1, 0.25);
    // water: bed at x=50 (ground replaced by lower bed) -> water cell oy+63 surface 0.875 above bed top at oy+63
    for (int x = 50; x <= 52; ++x) { P.top(ox + x, oy + 62, oz + 10, 1.0); }
    for (int x = 50; x <= 51; ++x) P.quad(ox + x, oy + 63, oz + 10, 0.875, 0, 0, 1, 0, 1, 0, 1, 0, 10000);
    P.quad(ox + 52, oy + 63, oz + 10, 0.11, 0, 0, 1, 0, 1, 0, 1, 0, 10000); // thin film
    // leaves canopy at x=60
    P.top(ox + 60, oy + 66, oz + 1, 1.0, 10300);
    // false-blocker controls above ground at x=70..: cross quad, torch top, fence top, wall face
    P.quad(ox + 70, oy + 64, oz + 1, 1.0, 0, 0, 1, 0, 1, 0.7071f, 0.0f, 0.7071f, 0); // diagonal quad
    P.top(ox + 71, oy + 64, oz + 1, 0.625, 10100); // torch top
    P.top(ox + 72, oy + 64, oz + 1, 1.5, 10304);   // fence
    P.quad(ox + 73, oy + 64, oz + 1, 3.0, 0, 0, 1, 0, 1, 1, 0, 0, 0);   // vertical wall
    // beyond-range roof (x offset 128 cell -> outside box) and edge roof at +127
    P.top(ox + 127, oy + 66, oz + 1, 1.0);
    P.top(ox + 128, oy + 66, oz + 1, 1.0); // outside
    P.capture(0);
    // glass-variant capture of translucent items repeated through variant 2
    P.top(ox + 21, oy + 70, oz + 7, 1.0, 10400); P.capture(2);
    // water also arrives via the glass program
    P.capture(2);
}

int main(int argc, char** argv) try {
    root = argc > 1 ? argv[1] : "release/shaders"; root += "/";
    std::string reportPath = argc > 2 ? argv[2] : "reports/2026-11-21-rain-eaves/shelter/probe-report.json";
    auto platform = reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
    EGLDisplay d = platform ? platform(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, nullptr) : eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (!eglInitialize(d, nullptr, nullptr)) {
        auto qd = reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
        std::array<EGLDeviceEXT, 16> dev{}; EGLint n = 0;
        if (!qd || !qd(16, dev.data(), &n) || n < 1) throw Fail("no EGL device");
        d = platform(EGL_PLATFORM_DEVICE_EXT, dev[0], nullptr);
        if (!eglInitialize(d, nullptr, nullptr)) throw Fail("EGL init failed");
    }
    eglBindAPI(EGL_OPENGL_API);
    const EGLint ca[] = {EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT, EGL_NONE};
    EGLConfig cfg; EGLint cnt = 0;
    if (!eglChooseConfig(d, ca, &cfg, 1, &cnt) || cnt != 1) throw Fail("no EGL config");
    const EGLint sa[] = {EGL_WIDTH, 4, EGL_HEIGHT, 4, EGL_NONE};
    EGLSurface sf = eglCreatePbufferSurface(d, cfg, sa);
    const EGLint xa[] = {EGL_CONTEXT_MAJOR_VERSION, 4, EGL_CONTEXT_MINOR_VERSION, 3,
                         EGL_CONTEXT_OPENGL_PROFILE_MASK, EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT, EGL_NONE};
    EGLContext cx = eglCreateContext(d, cfg, EGL_NO_CONTEXT, xa);
    if (cx == EGL_NO_CONTEXT || !eglMakeCurrent(d, sf, sf, cx)) throw Fail("GL 4.3 compatibility context unavailable");
    std::string renderer = (const char*)glGetString(GL_RENDERER), vendor = (const char*)glGetString(GL_VENDOR),
                version = (const char*)glGetString(GL_VERSION);
    std::printf("GL_RENDERER=%s\nGL_VENDOR=%s\nGL_VERSION=%s\n", renderer.c_str(), vendor.c_str(), version.c_str());
    GLint lim[6] = {};
    glGetIntegerv(GL_MAX_IMAGE_UNITS, &lim[0]); glGetIntegerv(GL_MAX_VERTEX_IMAGE_UNIFORMS, &lim[1]);
    glGetIntegerv(GL_MAX_FRAGMENT_IMAGE_UNIFORMS, &lim[2]); glGetIntegerv(GL_MAX_COMBINED_IMAGE_UNIFORMS, &lim[3]);
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &lim[4]); glGetIntegerv(GL_MAX_COMPUTE_IMAGE_UNIFORMS, &lim[5]);
    std::printf("limits: imageUnits=%d vertexImages=%d fragmentImages=%d combinedImages=%d texSize=%d computeImages=%d\n",
                lim[0], lim[1], lim[2], lim[3], lim[4], lim[5]);

    Probe P; P.build();
    // Sentries across the entire entity metadata row must survive roof capture.
    P.clear(); P.setCamera(0, 0, 0);
    std::vector<GLuint> meta(512); for (unsigned i = 0; i < meta.size(); ++i) meta[i] = 50000u+i;
    glBindTexture(GL_TEXTURE_2D,P.img);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,512,1,GL_RED_INTEGER,GL_UNSIGNED_INT,meta.data());
    P.top(-128,0,-128,1); P.top(127,0,127,1); P.capture(0);
    std::vector<GLuint> atlas(512*129);
    glGetTextureImage(P.img,0,GL_RED_INTEGER,GL_UNSIGNED_INT,GLsizei(atlas.size()*4),atlas.data());
    P.expectInt("all entity metadata preserved", std::equal(meta.begin(),meta.end(),atlas.begin()),1,"atlas");
    P.expectInt("first rain address written", atlas.at(512)!=0,1,"atlas");
    P.expectInt("last rain address written", atlas.back()!=0,1,"atlas");
    struct Cam { const char* tag; int ox, oy, oz; double cx, cy, cz; };
    for (Cam c : {Cam{"positive", 0, 0, 0, 5.3, 66.25, 3.5}, Cam{"negative", -3000, -80, -5000, -3000 + 5.3, -80 + 66.25 - 1.0, -5000 + 3.5},
                  Cam{"neg-frac", -1000, -10, -70000, -1000 + 5.0, -10 + 66.6, -70000 + 3.75}}) {
        scene(P, c.ox, c.oy, c.oz, c.cx, c.cy, c.cz, c.tag);
        std::string t = c.tag;
        auto Q = [&](double x, double y, double z, double sky) { return Probe::Q{c.ox + x, c.oy + y, c.oz + z, sky}; };
        // x,z are cell offsets + .5; y absolute-from-oy
        auto one = [&](double x, double y, double z, double sky) { return P.query({Q(x + 0.5, y, z + 0.5, sky)})[0]; };
        P.expect("ground itself, open sky", one(0, 64, 2, 1), 0.98, 1, t);
        P.expect("ground, cave skylight guard", one(0, 64, 2, 0.1), 0, 0.02, t);
        P.expect("under solid roof, skyLight=1", one(11, 64, 2, 1), 0, 0.02, t);
        P.expect("top of the solid roof itself", one(11, 67, 2, 1), 0.98, 1, t);
        P.expect("just past the eave (x=14)", one(14, 64, 2, 1), 0.98, 1, t);
        P.expect("under bright clear glass, skyLight=1", one(21, 64, 2, 1), 0, 0.02, t);
        P.expect("under bottom-slab ceiling 0.5 m", one(30, 64, 1, 1), 0, 0.02, t);
        P.expect("carpet 1/16 is a surface", one(40, 64.0625, 1, 1), 0.98, 1, t);
        P.expect("ground under carpet column", one(40, 64, 1, 1), 0.98, 1, t);
        P.expect("snow 0.25 column", one(42, 64, 1, 1), 0.98, 1, t);
        P.expect("immersed bed under 0.875 water", one(50, 63, 10, 1), 0, 0.02, t);
        P.expect("bed under thin 0.11 water film", one(52, 63, 10, 1), 0.98, 1, t);
        P.expect("under leaves", one(60, 64, 1, 0.8), 0, 0.02, t);
        P.expect("cross/diagonal quad is no blocker", one(70, 64, 1, 1), 0.98, 1, t);
        P.expect("torch top is no blocker", one(71, 64, 1, 1), 0.98, 1, t);
        P.expect("fence top is no blocker", one(72, 64, 1, 1), 0.98, 1, t);
        P.expect("vertical wall quad is no blocker", one(73, 64, 1, 1), 0.98, 1, t);
        P.expect("beyond range: proxy sky=1", one(129, 64, 1, 1), 0.98, 1, t);
        P.expect("beyond range: proxy sky=0.5", one(129, 64, 1, 0.5), 0, 0.02, t);
        P.expect("far past capture, roof ignored", one(128, 64, 1, 1), 0.98, 1, t);
        // fade: eave at x=11 is distance ~6; place a same query at fade distance via 127 column
        P.expect("normal not upward returns proxy", P.query({Probe::Q{c.ox + 11.5, c.oy + 64.0, c.oz + 2.5, 1.0}})[0], 0, 0.02, t);
        P.json += "";
        int nz = P.nonzero();
        P.expect("image has writes after capture (>0)", nz > 0 ? 1 : 0, 1, 1, t);
        // Nonterrain variant writes nothing
        P.clear(); P.top(c.ox + 11, c.oy + 66, c.oz + 2, 1.0); P.capture(3);
        P.expectInt("entity/blockentity variant writes nothing", P.nonzero(), 0, t);
        // clear/reset: capture then Iris-style clear then query -> proxy
        P.top(c.ox + 11, c.oy + 66, c.oz + 2, 1.0); P.capture(0);
        P.expect("roof captured then queried", one(11, 64, 2, 1), 0, 0.02, t);
        P.clear();
        P.expect("after clear: no data -> sky proxy", one(11, 64, 2, 1), 0.98, 1, t);
        P.expect("after clear: proxy sky=0.5", one(11, 64, 2, 0.5), 0, 0.02, t);
    }
    // Boundary writes over/out of range: only the +127 / -128 columns fit; verify count precisely.
    P.setCamera(0.0, 0.0, 0.0); P.clear();
    for (int x : {-129, -128, 127, 128}) P.top(x, 0, 0, 1.0);
    P.capture(0);
    P.expectInt("boundary: cells -129,-128,127,128 -> 2 written (-128,127)", P.nonzero(), 2, "boundary");
    // Fade range: roof at x=110 with open sky query at same -> blended
    P.clear(); P.top(110, 0, 0, 1.0); P.top(110, 3, 0, 1.0); P.capture(0);
    float f110 = P.query({Probe::Q{110.5, 1.0, 0.5, 1.0}})[0];
    float f90 = P.query({Probe::Q{90.5, 1.0, 0.5, 1.0}})[0];
    P.expect("fade: 110 m blended between map(0) and proxy(1)", f110, 0.05, 0.95, "boundary");
    P.top(90, 0, 0, 1.0); P.top(90, 3, 0, 1.0); P.capture(0);
    f90 = P.query({Probe::Q{90.5, 1.0, 0.5, 1.0}})[0];
    P.expect("fade: 90 m fully map (sheltered)", f90, 0, 0.02, "boundary");
    // Underwater: camera below water; same map, receiver bed -> sheltered. camera inside bed query
    P.setCamera(0.5, 61.5, 0.5); P.clear();
    P.top(0, 62, 0, 1.0); P.quad(0, 63, 0, 0.875, 0, 0, 1, 0, 1, 0, 1, 0, 10000); P.top(1, 62, 0, 1.0);

    P.capture(2);
    P.expect("underwater camera: bed sheltered", P.query({Probe::Q{0.5, 63.0, 0.5, 1.0}})[0], 0, 0.02, "underwater");
    P.expect("underwater camera: neighbouring dry bed", P.query({Probe::Q{1.5, 63.0, 0.5, 1.0}})[0], 0.98, 1, "underwater");

    // Compile-only checks of the real include chain at #version 330 (extension wrapper) and non-terrain guard.
    struct C { const char* name; std::string src; bool wantOk; };
    std::string h330 = "#version 330 compatibility\n";
    std::vector<C> comp = {
        {"fragment 330, include first, terrain", h330 + "#define RAIN_SHELTER_TERRAIN\n#include \"/lib/rain_shelter.glsl\"\nin vec3 p;out vec4 o;void main(){o=vec4(rainExposure(p,vec3(0,1,0),0.9));}\n", true},
        {"fragment 330, after settings tokens", h330 + "#include \"/lib/settings.glsl\"\n#define RAIN_SHELTER_TERRAIN\n#include \"/lib/rain_shelter.glsl\"\nin vec3 p;out vec4 o;void main(){o=vec4(rainExposure(p,vec3(0,1,0),0.9));}\n", true},
        {"fragment 330, nonterrain (no image)", h330 + "#include \"/lib/rain_shelter.glsl\"\nin vec3 p;out vec4 o;void main(){o=vec4(rainExposure(p,vec3(0,1,0),0.9));}\n", true},
        {"fragment 430, terrain", "#version 430 compatibility\n#include \"/lib/settings.glsl\"\n#define RAIN_SHELTER_TERRAIN\n#include \"/lib/rain_shelter.glsl\"\nin vec3 p;out vec4 o;void main(){o=vec4(rainExposure(p,vec3(0,1,0),0.9));}\n", true},
    };
    for (auto& c : comp) {
        std::string log; GLuint s = compile(GL_FRAGMENT_SHADER, expand(c.src), log);
        ++P.checks; bool ok = (s != 0) == c.wantOk; P.failures += !ok;
        std::printf("%s compile %-44s %s\n", ok ? "PASS" : "FAIL", c.name, s ? "ok" : log.c_str());
        P.json += ",\n{\"scene\":\"compile\",\"test\":\"" + std::string(c.name) + "\",\"pass\":" + (ok ? "true" : "false") + "}";
    }
    // Link every shipped stage. The entity geometry shader owns row 0 of the same
    // image, while only terrain vertex shaders populate the roof atlas.
    for (const char* n : {"shadow", "shadow_solid", "shadow_cutout", "shadow_water", "shadow_entities"}) {
        std::string diagnostic;
        std::vector<GLuint> stages;
        std::string stem = root + n;
        bool geometry = fs::exists(stem + ".gsh");
        auto stage = [&](GLenum type, const std::string& path) {
            GLuint shader = compile(type, expand(slurp(path)), diagnostic);
            if (!shader) throw Fail(path + ": " + diagnostic);
            stages.push_back(shader);
        };
        stage(GL_VERTEX_SHADER, stem + ".vsh");
        if (geometry) stage(GL_GEOMETRY_SHADER, stem + ".gsh");
        stage(GL_FRAGMENT_SHADER, fs::exists(stem + ".fsh") ? stem + ".fsh" : root + "shadow.fsh");
        GLuint linked = program(stages, nullptr, diagnostic);
        if (!linked) throw Fail(stem + ": " + diagnostic);
        bool terrain = std::string(n) == "shadow_solid" || std::string(n) == "shadow_cutout" || std::string(n) == "shadow_water";
        GLuint uniform = glGetProgramResourceIndex(linked, GL_UNIFORM, "entityMetaImage");
        GLint owners[2] = {};
        const GLenum fields[] = {GL_REFERENCED_BY_VERTEX_SHADER, GL_REFERENCED_BY_GEOMETRY_SHADER};
        if (uniform != GL_INVALID_INDEX)
            glGetProgramResourceiv(linked, GL_UNIFORM, uniform, 2, fields, 2, nullptr, owners);
        P.expectInt(std::string(n) + " vertex rain writes", owners[0], terrain, "shipped");
        P.expectInt(std::string(n) + " geometry metadata writes", owners[1], std::string(n) == "shadow_entities", "shipped");
        glDeleteProgram(linked);
        for (GLuint shader : stages) glDeleteShader(shader);
    }
    std::istringstream properties(slurp(root + "shaders.properties"));
    int images = 0;
    bool storage = false;
    std::string line;
    while (std::getline(properties, line)) {
        if (line.rfind("image.", 0) == 0) ++images;
        if (line == "image.entityMetaImage=aqualumenEntityMeta red_integer r32ui unsigned_int true false 512 129") storage = true;
    }
    P.expect("Iris 1.8.8 custom image limit", images, 1, 16, "pack");
    P.expectInt("cleared R32UI metadata and roof atlas declared", storage, 1, "pack");
    std::ofstream out(reportPath);
    out << "{\n\"renderer\":\"" << renderer << "\",\"vendor\":\"" << vendor << "\",\"version\":\"" << version << "\",\n"
        << "\"limits\":{\"maxImageUnits\":" << lim[0] << ",\"maxVertexImageUniforms\":" << lim[1] << ",\"maxFragmentImageUniforms\":" << lim[2]
        << ",\"maxCombinedImageUniforms\":" << lim[3] << ",\"maxTextureSize\":" << lim[4] << ",\"maxComputeImageUniforms\":" << lim[5] << "},\n"
        << "\"checks\":" << P.checks << ",\"failures\":" << P.failures << ",\n\"results\":[\n" << P.json << "\n]}\n";
    std::printf("checks=%d failures=%d\n", P.checks, P.failures);
    return P.failures ? 1 : 0;
} catch (const std::exception& e) { std::fprintf(stderr, "probe error: %s\n", e.what()); return 2; }
