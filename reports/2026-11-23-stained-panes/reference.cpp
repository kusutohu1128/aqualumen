// Independent double-precision disk integral through disjoint Minecraft model boxes.
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>
using V=std::array<double,3>;
static V normalize(V a) {double s=std::hypot(a[0],a[1],a[2]);for(auto& x:a)x/=s;return a;}
static V cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static double intersect(const double* box,V a,V direction) {
    double low=0.,high=1.;
    for(int k=0;k<3;k++){
        if(std::abs(direction[k])<1.e-12){if(a[k]<box[k] || a[k]>=box[k+3])return 0.;continue;}
        double lo=(box[k]-a[k])/direction[k],hi=(box[k+3]-a[k])/direction[k];
        low=std::max(low,std::min(lo,hi));high=std::min(high,std::max(lo,hi));
        if(high<=low)return 0.;
    }
    return high-low;
}
extern "C" void integrate(int n,const double* positions,int boxes,const double* shapes,int taps,double* out) {
    std::vector<std::array<double,2>> disk;
    for(int i=0;i<taps;i++){
        double phi=(i+.5)*2.399963229728653, r=.13*std::sqrt((i+.5)/taps);
        disk.push_back({r*std::cos(phi),r*std::sin(phi)});
    }
    #pragma omp parallel for
    for(int i=0;i<n;i++){
        V a={positions[3*i],positions[3*i+1],positions[3*i+2]},c={405.5,151.64,-407.5};
        V l=normalize({c[0]-a[0],c[1]-a[1],c[2]-a[2]});
        V u=normalize(cross(l,std::abs(l[1])<.9?V{0,1,0}:V{1,0,0})),v=cross(l,u);
        a[2]+=.025;V total={};
        for(auto uv:disk){
            V d;for(int k=0;k<3;k++)d[k]=c[k]+uv[0]*u[k]+uv[1]*v[k]-a[k];
            double rayLength=std::hypot(d[0],d[1],d[2]),paths[2]={0,0};
            for(int b=0;b<boxes;b++){
                const double* box=shapes+b*7;
                paths[int(box[6])]+=rayLength*intersect(box,a,d);
            }
            static const V red={std::log(.85),std::log(.20),std::log(.16)};
            static const V blue={std::log(.19),std::log(.36),std::log(.86)};
            for(int k=0;k<3;k++)total[k]+=std::exp(red[k]*paths[0]+blue[k]*paths[1]);
        }
        for(int k=0;k<3;k++)out[i*3+k]=total[k]/taps;
    }
}
