#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace fs = std::filesystem;
constexpr double pi = 3.14159265358979323846;
constexpr int mapSide = 2048;
constexpr int receiverSide = 129;
constexpr double halfWidth = 72.0;
constexpr double halfDepth = 144.0;
constexpr double depthMetres = halfDepth * 10.0;
using Matrix = std::array<float, 16>;
const Matrix identity = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
const Matrix shadowView = {1,0,0,0, 0,0,-1,0, 0,1,0,0, 0,0,0,1};
const Matrix shadowViewInverse = {1,0,0,0, 0,0,1,0, 0,-1,0,0, 0,0,0,1};

struct Vec2 { double x, y; };
struct Vec3 { double x, y, z; };
struct Plane { Vec2 centre; double height, slope, halfExtent, gridPhase; };
enum class DistortionPosition { CentreVertex, OffAxis, OriginCrossing };
struct SelfPlane { Plane receiver; DistortionPosition position; double degrees; };
struct ContactBox { Plane receiver; double bottomGap, thickness, halfExtent; };
struct Cutout { Plane receiver; double height, halfExtent; int alphaCells; };
struct Bounds { Plane receiver; Vec3 point; bool inside; };
struct Empty { Plane receiver; };
using Geometry = std::variant<Empty, SelfPlane, ContactBox, Cutout, Bounds>;
enum class MapKind { Rasterized, AnalyticPlane, AnalyticBlocked };
enum class Target { FullyLit, FullyBlocked, SelfLit, AlphaMask };
struct Scenario {
    std::string name;
    Geometry geometry;
    MapKind mapKind;
    Target target;
    bool positiveControl;
};
struct Vertex { Vec3 position; Vec2 uv; };
struct Triangle { std::array<Vertex, 3> vertices; };
struct ReceiverResult {
    std::vector<float> rgba;
    int selected = 0, wrong = 0;
    double minimum = 1, maximum = 0, mean = 0;
    bool targetPassed = false;
};
struct MapResidual {
    int measured = 0;
    double minimumMetres = 0, maximumMetres = 0, rmsMetres = 0, p99AbsoluteMetres = 0;
};
struct ScenarioResult {
    Scenario scenario;
    ReceiverResult receiver;
    MapResidual residual;
    int writtenDepthTexels;
};

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

std::string json(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c == '\n') out << "\\n";
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec;
        else out << c;
    }
    out << '"';
    return out.str();
}

void writeText(const fs::path& path, const std::string& value) {
    require(!fs::exists(path), "refuse existing artifact " + path.string());
    std::ofstream out(path);
    out << value;
    require(bool(out), "artifact write failed " + path.string());
}

void writeRaw(const fs::path& path, const std::vector<float>& values) {
    require(!fs::exists(path), "refuse existing artifact " + path.string());
    std::ofstream out(path, std::ios::binary);
    out.write(reinterpret_cast<const char*>(values.data()), std::streamsize(values.size() * sizeof(float)));
    require(bool(out), "float artifact write failed");
}

void writePreview(const fs::path& path, const ReceiverResult& result) {
    require(!fs::exists(path), "refuse existing preview");
    std::ofstream out(path, std::ios::binary);
    out << "P6\n" << receiverSide << ' ' << receiverSide << "\n255\n";
    for (int y = receiverSide - 1; y >= 0; --y) for (int x = 0; x < receiverSide; ++x) {
        const auto v = static_cast<unsigned char>(std::lround(std::clamp(result.rgba[(y * receiverSide + x) * 4], 0.0f, 1.0f) * 255));
        const unsigned char rgb[] = {v, v, v};
        out.write(reinterpret_cast<const char*>(rgb), 3);
    }
    require(bool(out), "preview write failed");
}

std::string expand(const fs::path& file, const fs::path& root, int level = 0) {
    require(level < 32, "include cycle");
    const auto canonical = fs::weakly_canonical(file);
    const auto relative = canonical.lexically_relative(fs::canonical(root));
    require(!relative.empty() && *relative.begin() != "..", "include escaped shader root");
    std::ifstream input(canonical);
    require(bool(input), "cannot read " + canonical.string());
    std::ostringstream out;
    for (std::string line; std::getline(input, line);) {
        if (line.rfind("#include", 0) == 0) {
            const auto begin = line.find('"'), end = line.find('"', begin + 1);
            require(begin != std::string::npos && end != std::string::npos && end > begin + 1, "malformed include");
            const auto name = line.substr(begin + 1, end - begin - 1);
            out << expand(root / (name.front() == '/' ? name.substr(1) : name), root, level + 1);
        } else out << line << '\n';
    }
    return out.str();
}

Matrix projection() {
    return {float(1 / halfWidth),0,0,0, 0,float(1 / halfWidth),0,0,
            0,0,float(1 / halfDepth),0, 0,0,0,1};
}

Matrix inverseProjection() {
    return {float(halfWidth),0,0,0, 0,float(halfWidth),0,0,
            0,0,float(halfDepth),0, 0,0,0,1};
}

void identityProduct(const Matrix& a, const Matrix& b) {
    for (int row = 0; row < 4; ++row) for (int col = 0; col < 4; ++col) {
        double value = 0;
        for (int k = 0; k < 4; ++k) value += double(a[k * 4 + row]) * b[col * 4 + k];
        require(std::abs(value - (row == col ? 1.0 : 0.0)) < 2e-6, "matrix inverse/product assertion failed");
    }
}

Vec2 distort(Vec2 p) {
    const double scale = std::max(0.15 + 0.85 * std::hypot(p.x, p.y), 0.15);
    return {p.x / scale, p.y / scale};
}

bool undistort(Vec2 q, Vec2& result) {
    const double radius = std::hypot(q.x, q.y);
    const double denominator = 1 - 0.85 * radius;
    if (denominator <= 0) return false;
    const double scale = 0.15 / denominator;
    result = {q.x * scale, q.y * scale};
    return std::isfinite(result.x) && std::isfinite(result.y);
}

double planeHeight(const Plane& plane, double x) {
    return plane.height + plane.slope * (x - plane.centre.x);
}

Plane receiver(const Geometry& geometry) {
    if (const auto* bounds = std::get_if<Bounds>(&geometry)) {
        Plane plane = bounds->receiver;
        plane.centre = {bounds->point.x,bounds->point.z};
        plane.height = bounds->point.y;
        return plane;
    }
    return std::visit([](const auto& value) { return value.receiver; }, geometry);
}

void addQuad(std::vector<Triangle>& triangles, const std::array<Vec3, 4>& p,
             const std::array<Vec2, 4>& uv) {
    triangles.push_back({{{{p[0], uv[0]}, {p[1], uv[1]}, {p[2], uv[2]}}}});
    triangles.push_back({{{{p[0], uv[0]}, {p[2], uv[2]}, {p[3], uv[3]}}}});
}

void addPlane(std::vector<Triangle>& triangles, const Plane& plane, double elevation = 0) {
    const double xStep = 1/std::sqrt(1+plane.slope*plane.slope);
    const int xCells = int(std::ceil(plane.halfExtent * 2/xStep));
    const int zCells = int(std::ceil(plane.halfExtent * 2));
    const double beginX = plane.centre.x - xCells*xStep*0.5 + plane.gridPhase*xStep;
    const double beginZ = plane.centre.y - zCells*0.5 + plane.gridPhase;
    for (int z = 0; z < zCells; ++z) for (int x = 0; x < xCells; ++x) {
        const double x0 = beginX+x*xStep, z0 = beginZ+z;
        const std::array<Vec3, 4> p = {{{x0, planeHeight(plane, x0) + elevation, z0},
            {x0 + xStep, planeHeight(plane, x0 + xStep) + elevation, z0},
            {x0 + xStep, planeHeight(plane, x0 + xStep) + elevation, z0 + 1},
            {x0, planeHeight(plane, x0) + elevation, z0 + 1}}};
        const double u = double(x)/xCells, v = double(z)/zCells;
        addQuad(triangles, p, {{{u,v}, {u+1.0/xCells,v}, {u+1.0/xCells,v+1.0/zCells}, {u,v+1.0/zCells}}});
    }
}

void addBox(std::vector<Triangle>& triangles, const ContactBox& box) {
    Plane top = box.receiver;
    top.halfExtent = box.halfExtent;
    top.gridPhase = 0;
    addPlane(triangles, top, box.bottomGap + box.thickness);
    addPlane(triangles, top, box.bottomGap);
    const int cells = int(std::ceil(2 * box.halfExtent));
    const double x0 = top.centre.x - cells * 0.5, z0 = top.centre.y - cells * 0.5;
    const double bottom = top.height + box.bottomGap, upper = bottom + box.thickness;
    for (int i = 0; i < cells; ++i) {
        const double a = x0 + i, b = z0 + i;
        const std::array<Vec2, 4> uv = {{{0,0}, {1,0}, {1,1}, {0,1}}};
        addQuad(triangles, {{{a,bottom,z0}, {a+1,bottom,z0}, {a+1,upper,z0}, {a,upper,z0}}}, uv);
        addQuad(triangles, {{{a,bottom,z0+cells}, {a+1,bottom,z0+cells}, {a+1,upper,z0+cells}, {a,upper,z0+cells}}}, uv);
        addQuad(triangles, {{{x0,bottom,b}, {x0,bottom,b+1}, {x0,upper,b+1}, {x0,upper,b}}}, uv);
        addQuad(triangles, {{{x0+cells,bottom,b}, {x0+cells,bottom,b+1}, {x0+cells,upper,b+1}, {x0+cells,upper,b}}}, uv);
    }
}

std::vector<Triangle> geometryFor(const Scenario& scenario) {
    std::vector<Triangle> triangles;
    if (scenario.mapKind != MapKind::Rasterized) return triangles;
    if (const auto* plane = std::get_if<SelfPlane>(&scenario.geometry)) addPlane(triangles, plane->receiver);
    if (const auto* box = std::get_if<ContactBox>(&scenario.geometry)) {
        require(box->receiver.slope == 0, "contact-box sides require a horizontal receiver");
        addPlane(triangles, box->receiver);
        addBox(triangles, *box);
    }
    if (const auto* cutout = std::get_if<Cutout>(&scenario.geometry)) {
        Plane sheet = cutout->receiver;
        sheet.height = cutout->height;
        sheet.halfExtent = cutout->halfExtent;
        addPlane(triangles, sheet);
    }
    return triangles;
}

std::vector<Scenario> scenarios() {
    const Plane flat = {{0,0},0,0,6,0};
    std::vector<Scenario> values = {
        {"control-empty-lit", Empty{flat}, MapKind::Rasterized, Target::FullyLit, true},
        {"control-solid-blocked", ContactBox{flat,2.0,0.01,3}, MapKind::Rasterized, Target::FullyBlocked, true},
        {"contact-gap-004m", ContactBox{flat,0.04,0.01,3}, MapKind::Rasterized, Target::FullyBlocked, false},
        {"cutout-alpha", Cutout{flat,2.0,4,4}, MapKind::Rasterized, Target::AlphaMask, true}
    };
    struct Position { const char* name; Vec2 centre; double phase; DistortionPosition kind; };
    const std::array<Position,3> positions = {{{"centre",{0,0},0,DistortionPosition::CentreVertex},
        {"offaxis",{32,20},0,DistortionPosition::OffAxis},
        {"origin-crossing",{0,0},0.5,DistortionPosition::OriginCrossing}}};
    for (double degrees : {0.0,30.0,60.0}) for (const auto& position : positions) {
        Plane plane = {position.centre,0,std::tan(degrees*pi/180),6,position.phase};
        const std::string label = position.name + std::string("-") + std::to_string(int(degrees));
        values.push_back({"raster-self-"+label, SelfPlane{plane,position.kind,degrees}, MapKind::Rasterized, Target::SelfLit, false});
        values.push_back({"analytic-self-"+label, SelfPlane{plane,position.kind,degrees}, MapKind::AnalyticPlane, Target::SelfLit, false});
    }
    for (double x : {-82.0,-65.0,65.0,82.0}) {
        Plane plane = flat;
        plane.centre = {x,0};
        const bool inside = std::abs(x) < 72;
        values.push_back({"bounds-x-"+std::to_string(int(x)), Bounds{plane,{x,0,0},inside}, MapKind::AnalyticBlocked,
                          inside ? Target::FullyBlocked : Target::FullyLit, true});
    }
    return values;
}

void cpuTests() {
    identityProduct(projection(), inverseProjection());
    identityProduct(inverseProjection(), projection());
    identityProduct(shadowView, shadowViewInverse);
    identityProduct(shadowViewInverse, shadowView);
    for (Vec2 point : std::array<Vec2,5>{{{0,0},{0.001,0.002},{0.5,0.25},{-0.75,0.2},{1,1}}}) {
        const auto q = distort(point);
        Vec2 restored;
        require(undistort(q, restored), "valid inverse distortion rejected");
        require(std::hypot(restored.x-point.x, restored.y-point.y) < 1e-12, "inverse distortion round trip failed");
    }
    Vec2 outside;
    require(!undistort({1.2,1.2}, outside), "unreachable distorted coordinate accepted");
    const auto cases = scenarios();
    require(cases.size() == 26, "scenario coverage count changed");
    int self = 0, contact = 0, cutout = 0;
    for (const auto& scenario : cases) {
        if (std::holds_alternative<SelfPlane>(scenario.geometry)) ++self;
        if (std::holds_alternative<ContactBox>(scenario.geometry)) ++contact;
        if (std::holds_alternative<Cutout>(scenario.geometry)) ++cutout;
        if (const auto* bounds = std::get_if<Bounds>(&scenario.geometry)) {
            const auto q = distort({bounds->point.x/halfWidth,bounds->point.z/halfWidth});
            const bool inside = q.x*0.5+0.5 > 0.002 && q.x*0.5+0.5 < 0.998
                             && q.y*0.5+0.5 > 0.002 && q.y*0.5+0.5 < 0.998;
            require(inside == bounds->inside,"bound expectation disagrees with exact distortion");
            require(scenario.target == (inside?Target::FullyBlocked:Target::FullyLit),"bound target is inconsistent");
        }
        const auto triangles = geometryFor(scenario);
        for (const auto& triangle : triangles) {
            for (const auto& vertex : triangle.vertices)
                require(std::isfinite(vertex.position.x) && std::isfinite(vertex.position.y) && std::isfinite(vertex.position.z), "nonfinite geometry");
            for (int i = 0; i < 3; ++i) {
                const auto a = triangle.vertices[i].position, b = triangle.vertices[(i+1)%3].position;
                const double edge = std::sqrt((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z));
                require(edge <= std::sqrt(2.0)+1e-9,"caster triangle exceeds one-metre face diagonal");
            }
        }
    }
    require(self == 18 && contact == 2 && cutout == 1, "typed geometry coverage incomplete");
    const auto& crossing = std::get<SelfPlane>(cases[8].geometry);
    require(crossing.position == DistortionPosition::OriginCrossing && crossing.receiver.gridPhase == 0.5,
            "origin-crossing face phase lost");
    require(std::abs(0.00015 * depthMetres - 0.216) < 1e-12, "legacy normalized bias conversion wrong");
    std::cout << "cpu_projection_inverse=pass\ncpu_shadow_view_inverse=pass\ncpu_distortion_inverse=pass\n"
              << "cpu_typed_scenarios=26\ncpu_origin_crossing_faces=pass\ncpu_one_metre_faces=pass\n"
              << "cpu_bounds_expectation=pass\nlegacy_fixed_depth_bias_metres=0.216\n";
}

void glOkay(const std::string& operation) {
    const GLenum error = glGetError();
    require(error == GL_NO_ERROR, operation + " GL error " + std::to_string(error));
}

struct Context {
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    std::string renderer, vendor, version;
    Context() {
        const auto platform = reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
        require(platform, "EGL platform extension absent");
        display = platform(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, nullptr);
        if (!eglInitialize(display, nullptr, nullptr)) {
            const auto query = reinterpret_cast<PFNEGLQUERYDEVICESEXTPROC>(eglGetProcAddress("eglQueryDevicesEXT"));
            std::array<EGLDeviceEXT,16> devices{};
            EGLint count = 0;
            require(query && query(devices.size(), devices.data(), &count) && count > 0, "EGL device absent");
            display = platform(EGL_PLATFORM_DEVICE_EXT, devices[0], nullptr);
            require(eglInitialize(display, nullptr, nullptr), "EGL device initialization failed");
        }
        require(eglBindAPI(EGL_OPENGL_API), "OpenGL API absent");
        const EGLint configAttributes[] = {EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,
            EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
        EGLConfig config;
        EGLint count = 0;
        require(eglChooseConfig(display, configAttributes, &config, 1, &count) && count == 1, "no EGL config");
        const EGLint surfaceAttributes[] = {EGL_WIDTH,receiverSide,EGL_HEIGHT,receiverSide,EGL_NONE};
        surface = eglCreatePbufferSurface(display, config, surfaceAttributes);
        const EGLint contextAttributes[] = {EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,
            EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_COMPATIBILITY_PROFILE_BIT,EGL_NONE};
        context = eglCreateContext(display, config, EGL_NO_CONTEXT, contextAttributes);
        require(surface != EGL_NO_SURFACE && context != EGL_NO_CONTEXT && eglMakeCurrent(display, surface, surface, context),
                "owned OpenGL compatibility context unavailable");
        renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
        vendor = reinterpret_cast<const char*>(glGetString(GL_VENDOR));
        version = reinterpret_cast<const char*>(glGetString(GL_VERSION));
        require(vendor.find("NVIDIA") != std::string::npos && renderer.find("NVIDIA") != std::string::npos,
                "real NVIDIA renderer required, observed " + renderer);
        glOkay("context creation");
        std::cout << "renderer=" << renderer << "\nversion=" << version << '\n';
    }
    ~Context() {
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
        eglDestroyContext(display,context);
        eglDestroySurface(display,surface);
        eglTerminate(display);
    }
};

GLuint compile(GLenum stage, const std::string& text, const std::string& label) {
    const GLuint shader = glCreateShader(stage);
    const char* pointer = text.c_str();
    glShaderSource(shader,1,&pointer,nullptr);
    glCompileShader(shader);
    GLint okay = 0;
    glGetShaderiv(shader,GL_COMPILE_STATUS,&okay);
    if (!okay) {
        std::array<char,65536> log{};
        glGetShaderInfoLog(shader,log.size(),nullptr,log.data());
        throw std::runtime_error(label + " compile failed " + log.data());
    }
    return shader;
}

GLuint link(const std::string& vertex, const std::string& fragment, const std::string& label) {
    const GLuint vs = compile(GL_VERTEX_SHADER,vertex,label+" vertex");
    const GLuint fs = compile(GL_FRAGMENT_SHADER,fragment,label+" fragment");
    const GLuint program = glCreateProgram();
    glAttachShader(program,vs);
    glAttachShader(program,fs);
    glLinkProgram(program);
    glDeleteShader(vs);
    glDeleteShader(fs);
    GLint okay = 0;
    glGetProgramiv(program,GL_LINK_STATUS,&okay);
    if (!okay) {
        std::array<char,65536> log{};
        glGetProgramInfoLog(program,log.size(),nullptr,log.data());
        throw std::runtime_error(label + " link failed " + log.data());
    }
    return program;
}

std::string receiverShader(const fs::path& root, const std::string& algorithm) {
    std::ostringstream out;
    out << "#version 330 compatibility\n" << expand(root/"lib/settings.glsl",root)
        << expand(root/"lib/uniforms.glsl",root) << expand(root/"lib/shadows.glsl",root);
    if (algorithm == "land") out << expand(root/"lib/land_shadows.glsl",root);
    out << R"(
uniform vec2 fixtureCentre;
uniform float fixtureHeight;
uniform float fixtureSlope;
uniform float fixtureSpan;
void main() {
    vec2 xz=fixtureCentre+(gl_FragCoord.xy/129.0-0.5)*fixtureSpan;
    vec3 point=vec3(xz.x,fixtureHeight+fixtureSlope*(xz.x-fixtureCentre.x),xz.y);
    vec3 normal=normalize(vec3(-fixtureSlope,1.0,0.0));
    vec4 clip=shadowProjection*shadowModelView*vec4(point,1.0);
    vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
    float visibility=)" << (algorithm == "legacy" ? "shadowVisibility" : "landShadowVisibility") << R"((point,normal);
    gl_FragData[0]=vec4(visibility,coord.z,coord.x,coord.y);
}
)";
    return out.str();
}

struct Fixture {
    GLuint map = 0, alpha = 0, output = 0, shadowFramebuffer = 0, outputFramebuffer = 0, sampler = 0;
    GLuint casterProgram, receiverProgram;
    explicit Fixture(GLuint caster, GLuint lookup) : casterProgram(caster), receiverProgram(lookup) {
        glGenTextures(1,&map);
        glBindTexture(GL_TEXTURE_2D,map);
        glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT24,mapSide,mapSide,0,GL_DEPTH_COMPONENT,GL_UNSIGNED_INT,nullptr);
        for (GLenum filter : {GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER}) glTexParameteri(GL_TEXTURE_2D,filter,GL_LINEAR);
        for (GLenum wrap : {GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T}) glTexParameteri(GL_TEXTURE_2D,wrap,GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        GLint format = 0, bits = 0, type = 0;
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_DEPTH_SIZE,&bits);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_DEPTH_TYPE,&type);
        require(format == GL_DEPTH_COMPONENT24 && bits == 24 && type == GL_UNSIGNED_NORMALIZED,
                "shadow map is not D24 UNORM");
        glGenSamplers(1,&sampler);
        for (GLenum filter : {GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER}) glSamplerParameteri(sampler,filter,GL_LINEAR);
        for (GLenum wrap : {GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T}) glSamplerParameteri(sampler,wrap,GL_CLAMP_TO_EDGE);
        glSamplerParameteri(sampler,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);
        glSamplerParameteri(sampler,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
        glGenFramebuffers(1,&shadowFramebuffer);
        glBindFramebuffer(GL_FRAMEBUFFER,shadowFramebuffer);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,map,0);
        glDrawBuffer(GL_NONE);
        glReadBuffer(GL_NONE);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE,"shadow framebuffer incomplete");
        glGenTextures(1,&alpha);
        glBindTexture(GL_TEXTURE_2D,alpha);
        const std::array<unsigned char,4> white = {255,255,255,255};
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,white.data());
        for (GLenum filter : {GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER}) glTexParameteri(GL_TEXTURE_2D,filter,GL_NEAREST);
        for (GLenum wrap : {GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T}) glTexParameteri(GL_TEXTURE_2D,wrap,GL_CLAMP_TO_EDGE);
        glGenTextures(1,&output);
        glBindTexture(GL_TEXTURE_2D,output);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,receiverSide,receiverSide,0,GL_RGBA,GL_FLOAT,nullptr);
        glGenFramebuffers(1,&outputFramebuffer);
        glBindFramebuffer(GL_FRAMEBUFFER,outputFramebuffer);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,output,0);
        glDrawBuffer(GL_COLOR_ATTACHMENT0);
        glReadBuffer(GL_COLOR_ATTACHMENT0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE,"receiver framebuffer incomplete");
        for (GLenum cap : {GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,
                           GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL}) glDisable(cap);
        glDepthRange(0,1);
        glColor4f(1,1,1,1);
        glMatrixMode(GL_TEXTURE);
        glLoadIdentity();
        glMatrixMode(GL_MODELVIEW);
        glOkay("fixture allocation");
    }
    ~Fixture() {
        glBindFramebuffer(GL_FRAMEBUFFER,0);
        glBindSampler(0,0);
        for (GLuint texture : {map,alpha,output}) glDeleteTextures(1,&texture);
        for (GLuint framebuffer : {shadowFramebuffer,outputFramebuffer}) glDeleteFramebuffers(1,&framebuffer);
        glDeleteSamplers(1,&sampler);
    }
    void matrices(GLuint program) {
        const auto p = projection();
        glUniformMatrix4fv(glGetUniformLocation(program,"shadowProjection"),1,GL_FALSE,p.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"shadowModelView"),1,GL_FALSE,shadowView.data());
        glUniformMatrix4fv(glGetUniformLocation(program,"gbufferModelViewInverse"),1,GL_FALSE,identity.data());
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),0,1,0);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),0,1,0);
    }
    void alphaTexture(int cells) {
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D,alpha);
        const int side = cells > 0 ? cells : 1;
        std::vector<unsigned char> data(side*side*4,255);
        if (cells > 0) for (int y = 0; y < side; ++y) for (int x = 0; x < side; ++x)
            data[(y*side+x)*4+3] = (x+y)%2 ? 0 : 255;
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,side,side,0,GL_RGBA,GL_UNSIGNED_BYTE,data.data());
    }
    void rasterMap(const Scenario& scenario) {
        glActiveTexture(GL_TEXTURE1);
        glBindTexture(GL_TEXTURE_2D,0);
        glBindSampler(1,0);
        glActiveTexture(GL_TEXTURE0);
        glBindSampler(0,0);
        glBindTexture(GL_TEXTURE_2D,alpha);
        const auto* cutout = std::get_if<Cutout>(&scenario.geometry);
        alphaTexture(cutout ? cutout->alphaCells : 0);
        glBindFramebuffer(GL_FRAMEBUFFER,shadowFramebuffer);
        glViewport(0,0,mapSide,mapSide);
        glEnable(GL_DEPTH_TEST);
        glDepthMask(GL_TRUE);
        glDepthFunc(GL_LEQUAL);
        glClearDepth(1);
        glClear(GL_DEPTH_BUFFER_BIT);
        glUseProgram(casterProgram);
        glUniform1i(glGetUniformLocation(casterProgram,"gtexture"),0);
        require(glGetUniformLocation(casterProgram,"shadowtex0") < 0,"caster unexpectedly samples attached shadow map");
        const auto p = projection();
        glMatrixMode(GL_PROJECTION);
        glLoadMatrixf(p.data());
        glMatrixMode(GL_MODELVIEW);
        glLoadMatrixf(shadowView.data());
        const auto triangles = geometryFor(scenario);
        glBegin(GL_TRIANGLES);
        for (const auto& triangle : triangles) for (const auto& vertex : triangle.vertices) {
            glMultiTexCoord2f(GL_TEXTURE0,float(vertex.uv.x),float(vertex.uv.y));
            glVertex3f(float(vertex.position.x),float(vertex.position.y),float(vertex.position.z));
        }
        glEnd();
        glOkay("real ordinary caster rasterization");
    }
    std::vector<float> analyticMap(const Scenario& scenario) {
        const auto plane = receiver(scenario.geometry);
        std::vector<float> values(mapSide*mapSide,1);
        for (int y = 0; y < mapSide; ++y) for (int x = 0; x < mapSide; ++x) {
            if (scenario.mapKind == MapKind::AnalyticBlocked) { values[y*mapSide+x] = 0; continue; }
            Vec2 p;
            if (!undistort({2*(x+0.5)/mapSide-1,2*(y+0.5)/mapSide-1},p)) continue;
            const double depth = 0.5-planeHeight(plane,p.x*halfWidth)/depthMetres;
            if (depth > 0 && depth < 1) values[y*mapSide+x] = float(depth);
        }
        glBindFramebuffer(GL_FRAMEBUFFER,outputFramebuffer);
        glActiveTexture(GL_TEXTURE0);
        glBindSampler(0,0);
        glBindTexture(GL_TEXTURE_2D,map);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,mapSide,mapSide,GL_DEPTH_COMPONENT,GL_FLOAT,values.data());
        glOkay("secondary analytic depth upload");
        return values;
    }
    std::vector<float> readMap() {
        glBindFramebuffer(GL_FRAMEBUFFER,outputFramebuffer);
        glActiveTexture(GL_TEXTURE0);
        glBindSampler(0,0);
        glBindTexture(GL_TEXTURE_2D,map);
        std::vector<float> values(mapSide*mapSide);
        glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT,values.data());
        for (float value : values) require(std::isfinite(value) && value >= 0 && value <= 1,"invalid D24 readback");
        glOkay("shadow map readback");
        return values;
    }
    ReceiverResult evaluate(const Scenario& scenario) {
        const auto plane = receiver(scenario.geometry);
        glBindFramebuffer(GL_FRAMEBUFFER,outputFramebuffer);
        GLint object = 0;
        glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME,&object);
        require(GLuint(object) == output && output != map && output != alpha,"receiver feedback or attachment mismatch");
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D,map);
        glBindSampler(0,sampler);
        GLint comparison = 0, filter = 0, binding = 0;
        glGetSamplerParameteriv(sampler,GL_TEXTURE_COMPARE_FUNC,&comparison);
        glGetSamplerParameteriv(sampler,GL_TEXTURE_MIN_FILTER,&filter);
        glGetIntegeri_v(GL_SAMPLER_BINDING,0,&binding);
        require(comparison == GL_LEQUAL && filter == GL_LINEAR && GLuint(binding) == sampler,"comparison sampler state drifted");
        glUseProgram(receiverProgram);
        matrices(receiverProgram);
        glUniform1i(glGetUniformLocation(receiverProgram,"shadowtex0"),0);
        glUniform2f(glGetUniformLocation(receiverProgram,"fixtureCentre"),float(plane.centre.x),float(plane.centre.y));
        glUniform1f(glGetUniformLocation(receiverProgram,"fixtureHeight"),float(plane.height));
        glUniform1f(glGetUniformLocation(receiverProgram,"fixtureSlope"),float(plane.slope));
        glUniform1f(glGetUniformLocation(receiverProgram,"fixtureSpan"),std::holds_alternative<Bounds>(scenario.geometry)?0.01f:4.0f);
        glViewport(0,0,receiverSide,receiverSide);
        glDisable(GL_DEPTH_TEST);
        glDepthMask(GL_FALSE);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        const float marker[] = {-99,-99,-99,-99};
        glClearBufferfv(GL_COLOR,0,marker);
        glBegin(GL_TRIANGLES);
        for (Vec2 p : std::array<Vec2,6>{{{-1,-1},{1,-1},{1,1},{-1,-1},{1,1},{-1,1}}}) glVertex2f(float(p.x),float(p.y));
        glEnd();
        ReceiverResult result;
        result.rgba.resize(receiverSide*receiverSide*4);
        glReadPixels(0,0,receiverSide,receiverSide,GL_RGBA,GL_FLOAT,result.rgba.data());
        glOkay("actual selected shadow lookup");
        for (int y = 0; y < receiverSide; ++y) for (int x = 0; x < receiverSide; ++x) {
            const int at = (y*receiverSide+x)*4;
            for (int c = 0; c < 4; ++c) require(std::isfinite(result.rgba[at+c]),"nonfinite lookup result");
            const double visibility = result.rgba[at];
            require(visibility >= -1e-6 && visibility <= 1+1e-6,"lookup visibility outside unit interval");
            bool selected = true;
            bool expectedLit = scenario.target != Target::FullyBlocked;
            if (scenario.target == Target::AlphaMask) {
                const auto& cutout = std::get<Cutout>(scenario.geometry);
                const double worldX = plane.centre.x+((x+0.5)/receiverSide-0.5)*4;
                const double worldZ = plane.centre.y+((y+0.5)/receiverSide-0.5)*4;
                const double u = (worldX-(plane.centre.x-cutout.halfExtent))/(2*cutout.halfExtent)*cutout.alphaCells;
                const double v = (worldZ-(plane.centre.y-cutout.halfExtent))/(2*cutout.halfExtent)*cutout.alphaCells;
                const double fx = u-std::floor(u), fy = v-std::floor(v);
                selected = fx > 0.2 && fx < 0.8 && fy > 0.2 && fy < 0.8;
                expectedLit = (int(std::floor(u))+int(std::floor(v)))%2 != 0;
            }
            if (!selected) continue;
            ++result.selected;
            result.minimum = std::min(result.minimum,visibility);
            result.maximum = std::max(result.maximum,visibility);
            result.mean += visibility;
            result.wrong += expectedLit ? visibility < 0.99 : visibility > 0.01;
        }
        require(result.selected > 100,"receiver target region is vacuous");
        result.mean /= result.selected;
        result.targetPassed = double(result.wrong)/result.selected <= 0.001;
        return result;
    }
};

MapResidual mapResidual(const Scenario& scenario, const std::vector<float>& depth) {
    MapResidual result;
    if (!std::holds_alternative<SelfPlane>(scenario.geometry)) return result;
    const auto plane = receiver(scenario.geometry);
    std::vector<double> absolute;
    double square = 0;
    for (int y = 0; y < mapSide; ++y) for (int x = 0; x < mapSide; ++x) {
        const float stored = depth[y*mapSide+x];
        if (stored == 1) continue;
        Vec2 p;
        if (!undistort({2*(x+0.5)/mapSide-1,2*(y+0.5)/mapSide-1},p)) continue;
        const double worldX = p.x*halfWidth, worldZ = p.y*halfWidth;
        if (std::abs(worldX-plane.centre.x) > 2 || std::abs(worldZ-plane.centre.y) > 2) continue;
        const double ideal = 0.5-planeHeight(plane,worldX)/depthMetres;
        const double error = (stored-ideal)*depthMetres;
        require(std::isfinite(error),"nonfinite vertex-warp residual");
        ++result.measured;
        if (result.measured == 1) result.minimumMetres = result.maximumMetres = error;
        result.minimumMetres = std::min(result.minimumMetres,error);
        result.maximumMetres = std::max(result.maximumMetres,error);
        square += error*error;
        absolute.push_back(std::abs(error));
    }
    require(result.measured > 100,"self-plane residual measurement is vacuous");
    result.rmsMetres = std::sqrt(square/result.measured);
    std::sort(absolute.begin(),absolute.end());
    result.p99AbsoluteMetres = absolute[size_t(std::floor((absolute.size()-1)*0.99))];
    return result;
}

std::string mapName(MapKind kind) {
    if (kind == MapKind::Rasterized) return "real-ordinary-shadow-pass";
    if (kind == MapKind::AnalyticPlane) return "secondary-analytic-texel-plane";
    return "secondary-analytic-full-blocker";
}

std::string targetName(Target target) {
    if (target == Target::FullyLit) return "lit";
    if (target == Target::FullyBlocked) return "blocked";
    if (target == Target::SelfLit) return "self-lit";
    return "alpha-mask";
}

std::string report(const fs::path& root, const std::string& algorithm, const Context& context,
                   const std::vector<ScenarioResult>& results, bool controlsPassed, bool contactRed, bool allTargets) {
    std::ostringstream out;
    out << std::setprecision(17);
    out << "{\n  \"evidenceKind\": \"owned-native-synthetic-not-Minecraft\",\n  \"shaderRoot\": " << json(root.string())
        << ",\n  \"algorithm\": " << json(algorithm) << ",\n  \"renderer\": " << json(context.renderer)
        << ",\n  \"vendor\": " << json(context.vendor) << ",\n  \"version\": " << json(context.version)
        << ",\n  \"mapResolution\": 2048,\n  \"depthFormat\": \"DEPTH_COMPONENT24\",\n  \"depthBits\": 24,\n"
        << "  \"receiverResolution\": 129,\n  \"primaryReceiverSpanMetres\": 4,\n  \"boundReceiverSpanMetres\": 0.01,\n"
        << "  \"unitFaceEdgeMetres\": 1,\n  \"allowedWrongReceiverFraction\": 0.001,\n  \"visibilityLitThreshold\": 0.99,\n"
        << "  \"visibilityBlockedThreshold\": 0.01,\n"
        << "  \"compareFunction\": \"LEQUAL\",\n  \"compareFilter\": \"LINEAR\",\n  \"projectionInverseIdentity\": true,\n"
        << "  \"normalisedDepthToMetres\": " << depthMetres << ",\n  \"legacyFixedDepthBiasMetres\": " << depthMetres*0.00015
        << ",\n  \"positiveControlsPassed\": " << (controlsPassed?"true":"false")
        << ",\n  \"legacyContactLeakReproduced\": " << (contactRed?"true":"false")
        << ",\n  \"allPhysicalTargetsPassed\": " << (allTargets?"true":"false")
        << ",\n  \"limitations\": [\"Synthetic orthographic light and geometry, not Minecraft draw-state or visual acceptance.\","
        << "\"Real caster vertex-warp residual is reported separately and never erased by increasing a test bias.\","
        << "\"Analytic maps isolate receiver lookup behavior and do not count as real caster coverage.\","
        << "\"No frame-time or performance claim is measured.\"],\n  \"scenarios\": [\n";
    for (size_t i = 0; i < results.size(); ++i) {
        const auto& value = results[i];
        const auto plane = receiver(value.scenario.geometry);
        out << "    {\"name\": " << json(value.scenario.name) << ", \"map\": " << json(mapName(value.scenario.mapKind))
            << ", \"target\": " << json(targetName(value.scenario.target))
            << ", \"positiveControl\": " << (value.scenario.positiveControl?"true":"false")
            << ", \"centreXZ\": [" << plane.centre.x << ',' << plane.centre.y << "]"
            << ", \"planeSlope\": " << plane.slope << ", \"unitFaceGridPhase\": " << plane.gridPhase
            << ", \"writtenDepthTexels\": " << value.writtenDepthTexels << ", \"selectedReceiverPixels\": " << value.receiver.selected
            << ", \"wrongReceiverPixels\": " << value.receiver.wrong << ", \"meanVisibility\": " << value.receiver.mean
            << ", \"minimumVisibility\": " << value.receiver.minimum << ", \"maximumVisibility\": " << value.receiver.maximum
            << ", \"targetPassed\": " << (value.receiver.targetPassed?"true":"false")
            << ", \"mapResidualTexels\": " << value.residual.measured
            << ", \"mapResidualMinimumMetres\": " << value.residual.minimumMetres
            << ", \"mapResidualMaximumMetres\": " << value.residual.maximumMetres
            << ", \"mapResidualRmsMetres\": " << value.residual.rmsMetres
            << ", \"mapResidualP99AbsoluteMetres\": " << value.residual.p99AbsoluteMetres;
        if (const auto* box = std::get_if<ContactBox>(&value.scenario.geometry))
            out << ", \"blockerBottomGapMetres\": " << box->bottomGap << ", \"blockerThicknessMetres\": " << box->thickness;
        out << '}';
        if (i+1 != results.size()) out << ',';
        out << '\n';
    }
    out << "  ]\n}\n";
    return out.str();
}

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--cpu-self-test") { cpuTests(); return 0; }
        require(argc == 4, "usage: land-shadow-native SHADER_ROOT legacy|land NEW_OUTPUT, or --cpu-self-test");
        const fs::path root = fs::canonical(argv[1]), output = argv[3];
        const std::string algorithm = argv[2];
        require(algorithm == "legacy" || algorithm == "land", "unknown algorithm");
        require(!fs::exists(output), "output directory already exists");
        require(fs::is_directory(root) && fs::is_regular_file(root/"shadow.vsh") && fs::is_regular_file(root/"shadow.fsh"),
                "shader root does not contain the caster pair");
        cpuTests();
        const std::string vertex = expand(root/"shadow.vsh",root), fragment = expand(root/"shadow.fsh",root);
        const std::string lookup = receiverShader(root,algorithm);
        require(fs::create_directory(output), "cannot exclusively create output directory");
        writeText(output/"caster-expanded.vsh",vertex);
        writeText(output/"caster-expanded.fsh",fragment);
        writeText(output/"receiver-expanded.fsh",lookup);
        Context context;
        const std::string fullScreenVertex = "#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
        writeText(output/"receiver.vsh",fullScreenVertex);
        const GLuint caster = link(vertex,fragment,"unchanged-ordinary-caster");
        const GLuint evaluator = link(fullScreenVertex,lookup,"selected-production-shadow-lookup");
        bool controlsPassed = true, allTargets = true, contactRed = false;
        std::vector<ScenarioResult> results;
        {
            Fixture fixture(caster,evaluator);
            for (const auto& scenario : scenarios()) {
                if (scenario.mapKind == MapKind::Rasterized) fixture.rasterMap(scenario);
                else fixture.analyticMap(scenario);
                const auto depth = fixture.readMap();
                const int written = int(std::count_if(depth.begin(),depth.end(),[](float value){return value < 1;}));
                if (scenario.name == "control-empty-lit") require(written == 0,"empty-map positive control contains geometry");
                else require(written > 100,"caster/depth-map coverage is vacuous");
                const auto residual = mapResidual(scenario,depth);
                const auto visibility = fixture.evaluate(scenario);
                writeRaw(output/(scenario.name+".rgba32f"),visibility.rgba);
                writePreview(output/(scenario.name+".ppm"),visibility);
                if (scenario.name == "raster-self-origin-crossing-60") writeRaw(output/"real-caster-origin-crossing-60.depth32f",depth);
                if (scenario.positiveControl) controlsPassed = controlsPassed && visibility.targetPassed;
                allTargets = allTargets && visibility.targetPassed;
                if (scenario.name == "contact-gap-004m" && algorithm == "legacy")
                    contactRed = !visibility.targetPassed && visibility.mean > 0.95;
                std::cout << scenario.name << " selected=" << visibility.selected << " wrong=" << visibility.wrong
                          << " mean=" << visibility.mean << " target=" << (visibility.targetPassed?"pass":"red")
                          << " raster_residual_m=" << residual.minimumMetres << ',' << residual.maximumMetres << '\n';
                results.push_back({scenario,visibility,residual,written});
            }
        }
        writeText(output/"RESULT.json",report(root,algorithm,context,results,controlsPassed,contactRed,allTargets));
        glDeleteProgram(caster);
        glDeleteProgram(evaluator);
        glOkay("fixture completion");
        require(controlsPassed,"positive controls failed, fixture is not qualified");
        if (algorithm == "legacy") require(contactRed,"predicted legacy 4cm contact leak was not reproduced");
        std::cout << "fixture_qualified=1\nall_physical_targets_passed=" << allTargets << '\n';
        return algorithm == "land" && !allTargets ? 2 : 0;
    } catch (const std::exception& error) {
        std::cerr << "fixture_invalid=" << error.what() << '\n';
        return 1;
    }
}
