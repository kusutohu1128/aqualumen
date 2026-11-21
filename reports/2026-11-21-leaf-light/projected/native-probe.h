// Native regression from a synthetic asymmetric atlas through the shipping shadow
// vertices, image publication, and the segment queried by the terrain lamp pass.
namespace aqualumenFoliageCast {
inline void probe(const fs::path& root) {
    using namespace aqualumenDoor;
    Rig rig;rig.init(root);rig.clearFrame();
    const int cell[]={32,32,32},key=8;
    const double ox=Atlas::ox(key),oy=Atlas::oy(key),N=Atlas::N;
    const double centre[2]={(ox+8)/N,(oy+8)/N};
    const D3 offset=rig.gridOffset();
    aqualumenLocalLights::resetTextureMatrices();
    glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,rig.atlasTex);
    glEnable(GL_RASTERIZER_DISCARD);rig.useShadowState(rig.cutout);
    glBegin(GL_QUADS);
    const int us[]={0,1,1,0},vs[]={0,0,1,1};
    Rig::V vertices[4];
    for(int i=0;i<4;i++) {
        vertices[i]={{double(us[i]),double(1-vs[i]),1},{(ox+16*us[i])/N,(oy+16*vs[i])/N}};
    }
    const double normal[]={0,0,1};
    Rig::emitQuad(cell,10300,0,vertices,normal,centre,offset.data(),rig.cam.data());
    glEnd();glMemoryBarrier(GL_ALL_BARRIER_BITS);glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
    rig.publish();
    std::vector<Ray> rays;
    std::vector<int> sheets;
    for(int axis=0;axis<3;axis++) for(int v=0;v<16;v++) for(int u=0;u<16;u++) {
        D3 first={32.5,32.5,32.5},last=first;
        const double h=(u+.5)/16.,k=(v+.5)/16.;
        if(axis==0) first[2]=last[2]=32+h,first[1]=last[1]=33-k;
        if(axis==1) first[0]=last[0]=32+h,first[2]=last[2]=32+k;
        if(axis==2) first[0]=last[0]=32+h,first[1]=last[1]=33-k;
        first[axis]=31.5;last[axis]=33.5;
        const int count=int(Atlas::opaque(key,u,v))+int(Atlas::opaque(key,axis==1?u:15-u,axis==1?15-v:v));
        rays.push_back({first,last,false,"forward"});sheets.push_back(count);
        rays.push_back({last,first,false,"reverse"});sheets.push_back(count);
    }
    const auto output=rig.transmission(rays);
    double sums[3]={},maxAsymmetry=0;
    int counts[3]={},wrong=0;
    for(size_t i=0;i<output.size();i++) {
        const auto rgb=output[i];const int count=sheets[i];
        sums[count]+=rgb[1];counts[count]++;
        if(i%2) maxAsymmetry=std::max(maxAsymmetry,std::abs(double(rgb[1]-output[i-1][1])));
        if(count==0) wrong+=rgb[0]<.65 || std::abs(rgb[0]-rgb[1])>.001;
        else wrong+=rgb[1]<(count==1?.23f:.07f) || rgb[1]>(count==1?.40f:.19f) || rgb[1]<rgb[0] || rgb[1]<rgb[2];
    }
    std::cout<<"FOLIAGE projected light on "<<rig.renderer<<"\n";
    for(int i=0;i<3;i++) std::cout<<"atlas layers "<<i<<" rays "<<counts[i]<<" mean G "<<sums[i]/std::max(counts[i],1)<<"\n";
    std::cout<<"wrong="<<wrong<<" reciprocal-error="<<maxAsymmetry<<"\n";
    if(wrong || maxAsymmetry>.0001) throw std::runtime_error("projected foliage did not follow the captured cutout");
    rig.frame({});
    for(auto value:rig.transmission(rays)) if(value[0]<.9999) throw std::runtime_error("removed foliage left a shadow");
}
}
