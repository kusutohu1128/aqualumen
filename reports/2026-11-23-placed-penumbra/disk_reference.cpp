// Independent segment/AABB quadrature against the known static world. Mark
// ambiguous non-cubic materials unknown before scoring any visibility.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

using V = std::array<double,3>;
constexpr int samples=8192;
constexpr double radius=.13;
static V cross(const V& a,const V& b) {
    return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
}
static void scaleTo(V& a,double length) {
    double norm=std::sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]);
    for(auto &v:a) v*=length/norm;
}
static bool hit(const V& start,const V& delta,const V& block,double pad) {
    double near=0.,far=1.;
    for(int j=0;j<3;j++) {
        double lo=block[j]-pad-start[j],hi=block[j]+1.+pad-start[j];
        if(std::abs(delta[j])<1e-13) {
            if(lo>=0. || hi<=0.) return false;
        } else {
            double a=lo/delta[j],b=hi/delta[j];
            near=std::max(near,std::min(a,b));
            far=std::min(far,std::max(a,b));
            if(near>=far) return false;
        }
    }
    return true;
}
extern "C" void integrate(int count,const double* positions,const uint8_t* normals,
    const double* offsets,const double* source,const int* anchor,const uint8_t* grid,float* output) {
    V lamp={source[0],source[1],source[2]};
    std::vector<std::array<double,2>> disk(samples);
    for(int j=0;j<samples;j++) {
        double r=std::sqrt((j+.5)/samples),angle=(j+.5)*2.399963229728653;
        disk[j]={r*std::cos(angle),r*std::sin(angle)};
    }
    #pragma omp parallel for schedule(dynamic,128)
    for(int i=0;i<count;i++) {
        V start{},delta{},direction{};
        int lo[3],hi[3];
        bool outside=false;
        for(int j=0;j<3;j++) {
            double p=positions[i*3+j];
            double normal=normals[i]==2*j+1?-1.:normals[i]==2*j+2?1.:0.;
            start[j]=p+(offsets?offsets[3*i+j]:.025*normal);
            delta[j]=lamp[j]-start[j];
            direction[j]=lamp[j]-p;
            lo[j]=int(std::floor(std::min(start[j],lamp[j]-radius)))-anchor[j];
            hi[j]=int(std::floor(std::max(start[j],lamp[j]+radius)))-anchor[j];
            outside|=lo[j]<0 || hi[j]>=64;
        }
        output[i]=-1.f;
        if(outside || !normals[i]) continue;
        std::vector<V> boxes;
        bool blocked=false,complex=false;
        for(int x=lo[0];x<=hi[0] && !blocked;x++)
        for(int y=lo[1];y<=hi[1] && !blocked;y++)
        for(int z=lo[2];z<=hi[2] && !blocked;z++) {
            uint8_t material=grid[(64*x+y)*64+z];
            if(!material) continue;
            V block={double(x+anchor[0]),double(y+anchor[1]),double(z+anchor[2])};
            if(!hit(start,delta,block,radius+.00001)) continue;
            if(material!=1) {complex=true;continue;}
            if(hit(start,delta,block,-radius-.00001)) blocked=true;
            else boxes.push_back(block);
        }
        if(blocked) {output[i]=0.;continue;}
        if(complex) continue;
        if(boxes.empty()) {output[i]=1.;continue;}
        scaleTo(direction,1.);
        V u=cross(direction,std::abs(direction[1])<.9?V{0,1,0}:V{1,0,0});
        scaleTo(u,radius);
        V v=cross(direction,u);
        int visible=0;
        for(auto pt:disk) {
            V ray;
            for(int a=0;a<3;a++) ray[a]=delta[a]+pt[0]*u[a]+pt[1]*v[a];
            bool clear=true;
            for(const auto &b:boxes) if(hit(start,ray,b,0.)) {clear=false;break;}
            visible+=clear;
        }
        output[i]=float(visible)/samples;
    }
}
