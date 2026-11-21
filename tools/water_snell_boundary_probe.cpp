// CPU-only host of the authored GLSL node. No OpenGL headers or context.
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

struct dvec3;
struct vec3 {
    float x, y, z;
    explicit vec3(float a = 0.0f) : x(a), y(a), z(a) {}
    vec3(float a, float b, float c) : x(a), y(b), z(c) {}
    explicit vec3(const dvec3& a);
};
struct dvec3 {
    double x, y, z;
    explicit dvec3(double a = 0.0) : x(a), y(a), z(a) {}
    dvec3(double a, double b, double c) : x(a), y(b), z(c) {}
    explicit dvec3(vec3 a) : x(a.x), y(a.y), z(a.z) {}
};
vec3::vec3(const dvec3& a) : x(float(a.x)), y(float(a.y)), z(float(a.z)) {}
struct bvec3 { bool x, y, z; };
vec3 operator+(vec3 a, vec3 b) { return vec3(a.x+b.x,a.y+b.y,a.z+b.z); }
vec3 operator-(vec3 a, vec3 b) { return vec3(a.x-b.x,a.y-b.y,a.z-b.z); }
vec3 operator-(vec3 a) { return vec3(-a.x,-a.y,-a.z); }
vec3 operator*(vec3 a, float b) { return vec3(a.x*b,a.y*b,a.z*b); }
vec3 operator*(float a, vec3 b) { return b*a; }
vec3 operator/(vec3 a, float b) { return vec3(a.x/b,a.y/b,a.z/b); }
dvec3 operator+(dvec3 a,dvec3 b) { return dvec3(a.x+b.x,a.y+b.y,a.z+b.z); }
dvec3 operator-(dvec3 a,dvec3 b) { return dvec3(a.x-b.x,a.y-b.y,a.z-b.z); }
dvec3 operator-(dvec3 a) { return dvec3(-a.x,-a.y,-a.z); }
dvec3 operator*(dvec3 a,double b) { return dvec3(a.x*b,a.y*b,a.z*b); }
dvec3 operator*(double a,dvec3 b) { return b*a; }
dvec3 operator/(dvec3 a,double b) { return dvec3(a.x/b,a.y/b,a.z/b); }
float dot(vec3 a, vec3 b) { return (a.x*b.x+a.y*b.y)+a.z*b.z; }
double dot(dvec3 a,dvec3 b) { return (a.x*b.x+a.y*b.y)+a.z*b.z; }
float length(vec3 a) { return std::sqrt(dot(a,a)); }
double length(dvec3 a) { return std::sqrt(dot(a,a)); }
vec3 normalize(vec3 a) { return a/length(a); }
dvec3 normalize(dvec3 a) { return a/length(a); }
float sqrt(float a) { return std::sqrt(a); }
float abs(float a) { return std::abs(a); }
double abs(double a) { return std::abs(a); }
vec3 abs(vec3 a) { return vec3(abs(a.x),abs(a.y),abs(a.z)); }
dvec3 abs(dvec3 a) { return dvec3(std::abs(a.x),std::abs(a.y),std::abs(a.z)); }
float min(float a,float b) { return std::min(a,b); }
float max(float a,float b) { return std::max(a,b); }
double min(double a,double b) { return std::min(a,b); }
double max(double a,double b) { return std::max(a,b); }
float clamp(float a,float b,float c) { return min(max(a,b),c); }
double clamp(double a,double b,double c) { return min(max(a,b),c); }
double clamp(double a,float b,float c) { return clamp(a,double(b),double(c)); }
float pow(float a,float b) { return std::pow(a,b); }
float inversesqrt(float a) { return 1.0f/sqrt(a); }
double inversesqrt(double a) { return 1.0/std::sqrt(a); }
bool isnan(float a) { return std::isnan(a); }
bool isinf(float a) { return std::isinf(a); }
bool isnan(double a) { return std::isnan(a); }
bool isinf(double a) { return std::isinf(a); }
bvec3 isnan(vec3 a) { return {isnan(a.x),isnan(a.y),isnan(a.z)}; }
bvec3 isinf(vec3 a) { return {isinf(a.x),isinf(a.y),isinf(a.z)}; }
bvec3 isnan(dvec3 a) { return {isnan(a.x),isnan(a.y),isnan(a.z)}; }
bvec3 isinf(dvec3 a) { return {isinf(a.x),isinf(a.y),isinf(a.z)}; }
bool any(bvec3 a) { return a.x||a.y||a.z; }
vec3 reflect(vec3 i,vec3 n) { return i-2.0f*dot(n,i)*n; }
vec3 refract(vec3 i,vec3 n,float eta) {
    float d=dot(n,i),k=1.0f-eta*eta*(1.0f-d*d);
    return k<0.0f?vec3(0.0f):eta*i-(eta*d+sqrt(k))*n;
}

// This is the actual candidate function, not a C++ copy of its arithmetic.
#define AQUALUMEN_SNELL_CPU_HOST 1
#include "../shaders/lib/water_snell_inverse.glsl"

namespace host {
constexpr const char* frozenLegacySha=
    "a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3";

bool finite(vec3 a) { return !any(isnan(a))&&!any(isinf(a)); }

// Separately labelled port of the frozen parent cap node (not an oracle).
WaterSnellNode legacyControl(vec3 view,vec3 target,float eta) {
    WaterSnellNode out;
    out.facet=vec3(0.0f);out.ray=vec3(0.0f);out.facing=0.0f;
    out.transmittedCosine=0.0f;out.jacobian=0.0f;out.transmission=0.0f;
    out.status=-1;
    float target2=dot(target,target);
    float k2=1.0f+eta*eta*(dot(view,view)-1.0f);
    if (!finite(view)||!finite(target)||!std::isfinite(eta)||eta<=0.0f
        ||!std::isfinite(k2)||k2<=0.0f||target2<=0.0f) return out;
    target=normalize(target);
    float k=sqrt(k2);
    vec3 axis=k*target+eta*view;
    float axis2=dot(axis,axis);
    if (!std::isfinite(axis2)||axis2<=0.0f) return out;
    out.facet=axis/sqrt(axis2);
    out.facing=dot(out.facet,view);
    out.transmittedCosine=dot(target,out.facet);
    float discriminant=1.0f-eta*eta*(1.0f-out.facing*out.facing);
    if (!(out.facet.y<0.0f&&out.facing>0.0f&&out.transmittedCosine<0.0f
        &&discriminant>0.0f&&std::isfinite(discriminant))) return out;
    out.ray=refract(-view,out.facet,eta);
    vec3 reflected=reflect(-view,out.facet);
    vec3 reconstruction=abs(out.ray-k*target);
    float inverseBound=(8.0f*1.1920928955078125e-7f)*max(max(1.0f,k),eta);
    if (!finite(out.ray)||!finite(reflected)
        ||max(max(reconstruction.x,reconstruction.y),reconstruction.z)>inverseBound
        ||dot(out.ray,out.ray)<1e-6f||out.ray.y<=0.0f||reflected.y>=0.0f) return out;
    float ci=clamp(out.facing,0.0f,1.0f);
    float sinTransmitted2=eta*eta*(1.0f-ci*ci);
    float transmission=0.0f;
    if (sinTransmitted2<1.0f) {
        float ct=sqrt(1.0f-sinTransmitted2);
        float rs=(eta*ci-ct)/max(eta*ci+ct,1e-5f);
        float rp=(ci-eta*ct)/max(ci+eta*ct,1e-5f);
        transmission=1.0f-0.5f*(rs*rs+rp*rp);
    }
    out.jacobian=k2*abs(out.transmittedCosine)/(axis2*pow(abs(out.facet.y),3.0f));
    out.transmission=transmission;
    if (!std::isfinite(out.jacobian)||out.jacobian<=0.0f
        ||!std::isfinite(transmission)||transmission<0.0f||transmission>1.0f) return out;
    out.status=1;
    return out;
}

float parse(const char* text) {
    std::size_t used=0;float value=std::stof(text,&used);
    if (used!=std::strlen(text)||!std::isfinite(value))
        throw std::invalid_argument("finite binary32 number required");
    return value;
}
void number(float a) { if (std::isfinite(a)) std::cout<<a; else std::cout<<"null"; }
void vector(vec3 a) {
    std::cout<<'[';number(a.x);std::cout<<',';number(a.y);std::cout<<',';
    number(a.z);std::cout<<']';
}
void bits(float a) {
    std::uint32_t value;std::memcpy(&value,&a,sizeof(value));
    std::cout<<'"'<<std::hex<<std::setw(8)<<std::setfill('0')<<value
             <<std::dec<<std::setfill(' ')<<'"';
}
void vectorBits(vec3 a) {
    std::cout<<'[';bits(a.x);std::cout<<',';bits(a.y);std::cout<<',';bits(a.z);std::cout<<']';
}
void node(const WaterSnellNode& n) {
    std::cout<<"{\"status\":"<<n.status<<",\"facet\":";vector(n.facet);
    std::cout<<",\"ray\":";vector(n.ray);
    std::cout<<",\"facing\":";number(n.facing);
    std::cout<<",\"transmittedCosine\":";number(n.transmittedCosine);
    std::cout<<",\"jacobian\":";number(n.jacobian);
    std::cout<<",\"transmission\":";number(n.transmission);std::cout<<'}';
}
}

int main(int argc,char** argv) {
    try {
        static_assert(sizeof(float)==4&&std::numeric_limits<float>::is_iec559,
                      "IEEE binary32 required");
        if (std::fesetround(FE_TONEAREST)!=0) throw std::runtime_error("nearest-even unavailable");
        if (argc!=9||std::string(argv[1])!="--node")
            throw std::invalid_argument("usage: water_snell_boundary_probe --node VX VY VZ TX TY TZ ETA");
        vec3 view(host::parse(argv[2]),host::parse(argv[3]),host::parse(argv[4]));
        vec3 target(host::parse(argv[5]),host::parse(argv[6]),host::parse(argv[7]));
        float eta=host::parse(argv[8]);
        auto candidate=waterSnellNode(view,target,eta);
        auto legacy=host::legacyControl(view,target,eta);
        std::cout<<std::setprecision(17)
                 <<"{\"schema\":\"aqualumen-cpu-snell-node-host-v1\",\"CPUOnly\":true,"
                 <<"\"nativeGLExecuted\":false,\"rounding\":\"FE_TONEAREST\","
                 <<"\"fpContract\":\"off\",\"fastMath\":false,\"view\":";
        host::vector(view);std::cout<<",\"viewBits\":";host::vectorBits(view);
        std::cout<<",\"generatedTargetInput\":";host::vector(target);
        std::cout<<",\"generatedTargetInputBits\":";host::vectorBits(target);
        std::cout<<",\"eta\":";host::number(eta);std::cout<<",\"etaBits\":";host::bits(eta);
        std::cout<<",\"candidate\":";host::node(candidate);
        std::cout<<",\"legacyControl\":";host::node(legacy);
        std::cout<<",\"legacyControlSourceSha256\":\""<<host::frozenLegacySha
                 <<"\",\"scope\":\"Authored GLSL node compiled as CPU C++; legacy port is a control, not an independent oracle or GPU/Iris/physical acceptance.\"}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';return 2;
    }
}
