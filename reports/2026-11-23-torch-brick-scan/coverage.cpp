// Independently enumerate the reference cuboid and the row-pruned grid in binary32.
// A cell may contain any material, so compare all cone-touched cells before material lookup.
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

using Vec = std::array<float,3>;
using Cell = std::array<int,3>;
struct Window {float lo, hi;};
struct Range {int lo, hi;};
struct Shot {Vec start, delta, spread; Cell source, first, last;};

bool touches(const Shot &s, Cell c, Vec spread) {
    Window t{0,1};
    for (int k=0;k<3;++k) {
        float lower=c[k]-s.start[k], upper=lower+1;
        float fast=s.delta[k]+spread[k], slow=s.delta[k]-spread[k];
        if (fast>1e-7f) t.lo=std::max(t.lo,lower/fast);
        else if (fast< -1e-7f) t.hi=std::min(t.hi,lower/fast);
        else if (lower>0) return false;
        if (slow>1e-7f) t.hi=std::min(t.hi,upper/slow);
        else if (slow< -1e-7f) t.lo=std::max(t.lo,upper/slow);
        else if (upper<0) return false;
    }
    return t.lo<=t.hi;
}

Window slab(const Shot &s, int k, int brick) {
    float pad=s.spread[k]+.0001f;
    float a=2*brick-s.start[k]-pad, b=2*brick+2-s.start[k]+pad;
    if (std::abs(s.delta[k])<1e-7f)
        return a<=0 && b>=0 ? Window{0,1}:Window{1,0};
    a/=s.delta[k]; b/=s.delta[k];
    return {std::max(0.f,std::min(a,b)),std::min(1.f,std::max(a,b))};
}

Range limits(const Shot &s,int k, Window t) {
    float a=s.start[k]+s.delta[k]*t.lo, b=s.start[k]+s.delta[k]*t.hi;
    float pad=s.spread[k]+.0001f;
    return {std::max(s.first[k],int(std::floor((std::min(a,b)-pad)*.5f))),
            std::min(s.last[k],int(std::floor((std::max(a,b)+pad)*.5f)))};
}

using Hits=std::vector<Cell>;
void visit(const Shot &s,int x,int y,int z,Hits &hits) {
    for (int bit=0;bit<8;++bit) {
        Cell c{2*x+(bit&1),2*y+(bit>>2),2*z+((bit>>1)&1)};
        if (c!=s.source && touches(s,c,s.spread)) hits.push_back(c);
    }
}

int main() {
    constexpr int trials=55000;
    std::mt19937 rng(308060);
    std::uniform_real_distribution<float> offset(-14.f,14.f), radius(.02f,.38f);
    long long full=0,pruned=0,cells=0,grazing=0, counts[10]{};
    Hits before,after;
    for(int n=0;n<trials;++n) {
        Shot s{};
        for(int k=0;k<3;++k) {
            s.source[k]=rng()%64;
            float source=s.source[k]+(k==1?.64f:.5f);
            s.spread[k]=std::min(radius(rng),.35f);
            float start=source+offset(rng);
            if(n%3==0 && k==n%7%3) start=std::round(start);
            if(n%9==0 && k==(n+1)%3) start=source;
            if(n%23==0 && k==0) start=std::nextafter(std::round(start),source);
            s.start[k]=std::clamp(start,0.f,63.99999f);
            s.delta[k]=source-s.start[k];
            s.first[k]=int(std::floor(std::min(s.start[k],source-s.spread[k])))/2;
            s.last[k]=int(std::floor(std::max(s.start[k],source+s.spread[k])))/2;
        }
        before.clear(); after.clear();
        for(int y=s.first[1];y<=s.last[1];++y)
            for(int z=s.first[2];z<=s.last[2];++z)
                for(int x=s.first[0];x<=s.last[0];++x) {
                    ++full; visit(s,x,y,z,before);
                }
        for(int y=s.first[1];y<=s.last[1];++y) {
            Window yw=slab(s,1,y);
            if(yw.lo>yw.hi) continue;
            Range zs=limits(s,2,yw);
            for(int z=zs.lo;z<=zs.hi;++z) {
                Window zw=slab(s,2,z), yz{std::max(yw.lo,zw.lo),std::min(yw.hi,zw.hi)};
                if(yz.lo>yz.hi) continue;
                Range xs=limits(s,0,yz);
                for(int x=xs.lo;x<=xs.hi;++x) {++pruned;visit(s,x,y,z,after);}
            }
        }
        assert(before==after);
        cells+=before.size();
        int blockers=0;
        for(const Cell &c:before) {
            if(!touches(s,c,Vec{})) ++grazing;
            // Deterministic sparse solid occupancy for branch-threshold coverage.
            if((unsigned(c[0]*19+c[1]*17+c[2]*23+n)%11)<3) ++blockers;
        }
        ++counts[std::min(blockers,9)];
    }
    std::printf("{\"rays\":%d,\"referenceBricks\":%lld,\"rowBricks\":%lld,"
                "\"orderedCellsCompared\":%lld,\"cellsMissedByCenterRay\":%lld,"
                "\"orderedListMismatches\":0,\"blockers0to8Then9Plus\":[",trials,full,pruned,cells,grazing);
    for(int i=0;i<10;++i) std::printf("%s%lld",i?",":"",counts[i]);
    std::puts("]}");
}
