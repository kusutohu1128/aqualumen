// Eliminate inverse segment depth to project each voxel onto the emitter plane.
// Coordinates on that plane are measured in units of the torch radius.
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

using V = std::array<double,3>;
struct Point { double x,y; };
struct Halfplane {
    double c,x,y;
    double at(Point p) const { return c+x*p.x+y*p.y; }
};
using Polygon = std::vector<Point>;
constexpr double pi = 3.14159265358979323846;

static V cross(V a,V b) {
    return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
}
static V normalized(V v,double length) {
    double norm=std::sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);
    for(auto& x:v) x*=length/norm;
    return v;
}
static void clip(Polygon& polygon,Halfplane edge) {
    if(polygon.empty()) return;
    Polygon out;
    Point a=polygon.back();
    double va=edge.at(a);
    for(auto b:polygon) {
        double vb=edge.at(b);
        if((va<0.)!=(vb<0.)) {
            double t=va/(va-vb);
            out.push_back({a.x+t*(b.x-a.x),a.y+t*(b.y-a.y)});
        }
        if(vb>=0.) out.push_back(b);
        a=b;va=vb;
    }
    polygon.swap(out);
}
static Polygon footprint(V lo,V hi,V delta,V u,V v) {
    Polygon polygon={{-1,-1},{1,-1},{1,1},{-1,1}};
    // lo*s <= delta+u*x+v*y <= hi*s, with s=1/t >= 1.
    std::vector<Halfplane> lower={{1,0,0}},upper;
    for(int k=0;k<3;k++) {
        if(lo[k]==0.) clip(polygon,{delta[k],u[k],v[k]});
        else (lo[k]>0.?upper:lower).push_back({delta[k]/lo[k],u[k]/lo[k],v[k]/lo[k]});
        if(hi[k]==0.) clip(polygon,{-delta[k],-u[k],-v[k]});
        else (hi[k]>0.?lower:upper).push_back({delta[k]/hi[k],u[k]/hi[k],v[k]/hi[k]});
    }
    for(auto high:upper) for(auto low:lower)
        clip(polygon,{high.c-low.c,high.x-low.x,high.y-low.y});
    return polygon;
}
// Green's theorem on the clipped polygon. Outside the unit circle an edge
// contributes the signed sector angle; inside it contributes a triangle.
static double diskArea(const Polygon& p) {
    if(p.size()<3) return 0.;
    double sum=0.;
    Point a=p.back();
    for(auto b:p) {
        double dx=b.x-a.x,dy=b.y-a.y;
        double len=dx*dx+dy*dy;
        if(len<1e-24) { a=b;continue; }
        double dot=a.x*dx+a.y*dy;
        double disc=dot*dot-len*(a.x*a.x+a.y*a.y-1.);
        std::array<double,4> cut={0.,1.,1.,1.};
        if(disc>0.) {
            double root=std::sqrt(disc);
            cut[1]=std::clamp((-dot-root)/len,0.,1.);
            cut[2]=std::clamp((-dot+root)/len,0.,1.);
        }
        for(int j=0;j<3;j++) {
            double t=cut[j],s=cut[j+1];
            if(s<=t) continue;
            Point l={a.x+t*dx,a.y+t*dy},r={a.x+s*dx,a.y+s*dy};
            double mx=(l.x+r.x)*.5,my=(l.y+r.y)*.5;
            double det=l.x*r.y-l.y*r.x;
            sum+=mx*mx+my*my<1.?det:std::atan2(det,l.x*r.x+l.y*r.y);
        }
        a=b;
    }
    return std::clamp(sum/(2*pi),0.,1.);
}

extern "C" void pairArea(int count,const float* packed,double* out) {
    for(int i=0;i<count;i++) {
        const float* row=packed+28*i;
        auto vec=[&](int j)->V{return {row[4*j],row[4*j+1],row[4*j+2]};};
        Polygon a=footprint(vec(0),vec(1),vec(4),vec(5),vec(6));
        Polygon b=footprint(vec(2),vec(3),vec(4),vec(5),vec(6));
        Polygon both=a;
        if(b.size()<3 || diskArea(b)<1e-14) both.clear();
        else {
            Point last=b.back();
            for(auto next:b) {
                double dx=next.x-last.x,dy=next.y-last.y;
                clip(both,{dy*last.x-dx*last.y,-dy,dx});
                last=next;
            }
        }
        out[i]=std::clamp(1.-diskArea(a)-diskArea(b)+diskArea(both),0.,1.);
    }
}

extern "C" void classify(int count,const double* positions,const double* origins,const double* lamp,
                         int blocks,const int* cubes,int* touched,int* cuboid,double* visible) {
    for(int i=0;i<count;i++) {
        V start{},delta{},l{};
        for(int k=0;k<3;k++) {
            start[k]=origins[3*i+k];delta[k]=lamp[k]-start[k];l[k]=lamp[k]-positions[3*i+k];
        }
        l=normalized(l,1.);
        V u=normalized(cross(l,std::abs(l[1])<.9?V{0,1,0}:V{1,0,0}),.13),v=cross(l,u);
        std::array<int,3> first={100000,100000,100000},last={-100000,-100000,-100000};
        int n=0;
        for(int j=0;j<blocks;j++) {
            V lo{},hi{};
            for(int k=0;k<3;k++) {lo[k]=cubes[3*j+k]-start[k];hi[k]=lo[k]+1.;}
            if(diskArea(footprint(lo,hi,delta,u,v))<1e-10) continue;
            n++;
            for(int k=0;k<3;k++) {
                first[k]=std::min(first[k],cubes[3*j+k]); last[k]=std::max(last[k],cubes[3*j+k]);
            }
        }
        touched[i]=n;cuboid[i]=0;visible[i]=-1.;
        if(n==0) {visible[i]=1.;continue;}
        if(n!=(last[0]-first[0]+1)*(last[1]-first[1]+1)*(last[2]-first[2]+1)) continue;
        V lo{},hi{};
        for(int k=0;k<3;k++) {lo[k]=first[k]-start[k];hi[k]=last[k]+1.-start[k];}
        cuboid[i]=1;visible[i]=1.-diskArea(footprint(lo,hi,delta,u,v));
    }
}
