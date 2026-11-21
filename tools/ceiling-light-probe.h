// Read back each reflection order from the installed compute sources. The rooms
// share the independent area-integral fixture in the ceiling-return report.
#pragma once
namespace aqualumenCeiling {
using namespace aqualumenBounce;

inline Scene room(RGB8 a,RGB8 b,int shutter,bool lit) {
    Scene s;
    auto box=[&](Cell lo,Cell hi,int face=-1,RGB8 pigment={}) {
        for(int x=lo[0];x<hi[0];++x) for(int y=lo[1];y<hi[1];++y) for(int z=lo[2];z<hi[2];++z) {
            Cell c={x,y+64,z};s.stone(c);
            if(face>=0) s.surf(c,face,pigment);
        }
    };
    box({6,0,0},{7,3,4},0,a);
    box({3,0,5},{6,4,6},4,b);
    box({6,4,3},{8,5,5},2,{255,255,255});
    box({0,0,1},{1,3,4});box({1,0,1},{4,3,2});box({1,0,3},{4,3,4});
    box({1,0,2},{4,1,3});box({1,2,2},{4,3,3});
    if(shutter==1) box({4,1,2},{5,2,3});
    if(shutter==2) box({3,0,4},{7,4,5});
    if(shutter==3) box({6,3,3},{8,4,5});
    if(shutter==4) box({6,0,4},{7,4,5});
    if(lit) s.lamp({1,65,2},10110,15);
    return s;
}

inline void probe(const fs::path& root) {
    Rig rig;rig.init(root);
    check(rig.pInc.h==2048,"ceiling bank missing");
    GLuint stage=compute(root/"shadowcomp4.csh",root);
    int groups[3];Rig::expectDispatch("shadowcomp4",LL::slurp(root/"shadowcomp4.csh"),groups);
    const D3 camera={5.5,66.1,2.5};
    auto measure=[&](std::string label,RGB8 a,RGB8 b,int shutter,bool lit) {
        Images first=rig.build(room(a,b,shutter,lit),camera);
        rig.dispatch(stage,groups,camera,true);
        std::array<D3,3> observed;
        for(int i=0;i<3;++i) {
            const Cell ceiling=i==2?Cell{7,68,4}:Cell{6,68,3};
            int lane=i==1?3:0;
            // The first two ceiling patches are on the same block; patch axes on -Y are z,x.
            check(lum(rig.sub4(first.exit,ceiling,2)[lane])<1e-6,"direct entered ceiling");
            check(lum(rig.sub4(first.inc,ceiling,2)[lane])<1e-6,"first reflection entered ceiling");
            auto addr=faceAddress(toLocal(ceiling,camera),2);
            float rgba[4]={};
            glGetTextureSubImage(rig.incTex,0,2*addr[0]+(lane&1),1536+2*addr[1]+(lane>>1),
                                 0,1,1,1,GL_RGBA,GL_FLOAT,sizeof(rgba),rgba);
            observed[i]={rgba[0],rgba[1],rgba[2]};
            for(double c:observed[i]) check(std::isfinite(c) && c>=0,"invalid second reflection");
            std::cout<<"ceiling "<<label<<" "<<i<<" linear RGB "<<rgba[0]<<" "<<rgba[1]<<" "<<rgba[2]<<"\n";
        }
        return observed;
    };
    const RGB8 white={255,255,255};
    const auto baseline=measure("white-white",white,white,0,true);
    const auto coloured=measure("red-white",{190,64,32},white,0,true);
    const auto darkWall=measure("white-grey",white,{128,128,128},0,true);
    const double cpu[]={.000151176599,.000111945788,.000054331527};
    const double lampIntensity=11.*std::pow(15./14.,2);
    for(int i=0;i<3;++i) {
        const double ratio=baseline[i][0]/(cpu[i]*lampIntensity);
        std::cout<<"ceiling GPU/point-area oracle "<<i<<" "<<ratio<<'\n';
        check(ratio>.45 && ratio<1.8,"second return outside sampling envelope");
        for(int c=0;c<3;++c) {
            double a=coloured[i][c]/baseline[i][c],b=darkWall[i][c]/baseline[i][c];
            check(std::abs(a-decode({190,64,32})[c])<.005,"wall A pigment");
            check(std::abs(b-decode({128,128,128})[c])<.005,"wall B pigment");
        }
    }
    for(int shutter=0;shutter<=3;++shutter) {
        auto dark=measure(shutter?"shutter-"+std::to_string(shutter):"extinguished",white,white,shutter,shutter>0);
        for(auto v:dark) check(lum(v)<1e-6,"light survived a closed path");
    }
    auto side=measure("side-screen",white,white,4,true);
    check(side[0][0]>0 && lum(side[1])<1e-6 && lum(side[2])<1e-6,"vertical screen must darken the two far exposed patches");
    auto restored=measure("reopened",white,white,0,true);
    check(restored==baseline,"stale or flickering second return");
    glDeleteProgram(stage);
    std::cout<<"PASS ceiling-return: two independent pigments, three shutters, off/on and separated reflection orders\n";
}
}
