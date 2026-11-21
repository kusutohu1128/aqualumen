// Exercise the actual shadow capture, light-list compute and terrain material program.
// Sample a visible face at its world boundary. Change only the emitter or the blocker.
namespace aqualumenLeafLight {
using namespace aqualumenLocalLights;
using RGB=std::array<float,3>;

inline int probe(const fs::path& root) {
    World w;
    w.init(root);
    TerrainRig terrain;
    terrain.init(w);
    const D3 camera={-3.5,-1.5,0.5};
    const D3 side={0,0.64,0.5},west={-1,0,0};
    const D3 below={0.5,0,0.5},down={0,-1,0};
    const Block leaf={0,0,0,10300,0,1},rock={0,0,0,10001,0,0};
    const Block warm={3,0,0,10100,14,1},soul={3,0,0,10105,10,1};
    const Block facing={-4,0,0,10100,14,1},wall={2,0,0,10001,0,0},layer={2,0,0,10300,0,1};
    const RGB gray={.75f,.75f,.75f};
    const std::array<RGB,4> atlas={gray,gray,gray,gray};
    auto draw=[&](std::vector<Block> blocks,const D3& point,const D3& normal,const TerrainSun* sun=nullptr) {
        w.build(blocks,camera);
        if(sun) terrain.setSun(*sun,camera[1]);
        return terrain.draw(w,camera,point,normal,0,sun?1:0,blocks.front().id,atlas,true,sun)[0];
    };
    auto delta=[](RGB a,RGB b) {return RGB{a[0]-b[0],a[1]-b[1],a[2]-b[2]};};
    auto y=[](RGB c) {return .2126*c[0]+.7152*c[1]+.0722*c[2];};
    auto maxAbs=[](RGB c){return std::max({std::abs(c[0]),std::abs(c[1]),std::abs(c[2])});};
    const RGB night=draw({leaf},side,west),stoneNight=draw({rock},side,west);
    const RGB front=delta(draw({leaf,facing},side,west),night);
    const RGB back=delta(draw({leaf,warm},side,west),night);
    const RGB blue=delta(draw({leaf,soul},side,west),night);
    const RGB opaque=delta(draw({rock,warm},side,west),stoneNight);
    const RGB blocked=delta(draw({leaf,wall,warm},side,west),draw({leaf,wall},side,west));
    const RGB layered=delta(draw({leaf,layer,warm},side,west),draw({leaf,layer},side,west));
    auto print=[](const char* name,RGB c){std::cout<<"LEAF "<<name<<" RGB "<<c[0]<<" "<<c[1]<<" "<<c[2]<<"\n";};
    print("lamp front",front);print("lamp behind",back);print("soul behind",blue);
    print("opaque back",opaque);print("wall",blocked);print("second layer",layered);
    int failed=0;
    auto check=[&](bool ok,const char* note){std::cout<<(ok?"PASS ":"FAIL ")<<note<<"\n";if(!ok) ++failed;};
    check(y(front)>.001,"front-facing torch illuminates leaf");
    check(y(back)>.0001 && y(back)<y(front),"backlit leaf transmits less light than a front-facing leaf");
    check(blue[2]>.00005 && blue[2]>blue[0] && back[0]>back[2],"backlit leaf preserves distinct warm and soul spectra");
    check(maxAbs(opaque)<.00002,"opaque receiver excludes backside illumination");
    check(maxAbs(blocked)<.00002,"stone between emitter and leaf closes local path");
    check(y(layered)>.000005 && y(layered)<y(back)*.9,"extra foliage attenuates rear illumination");
    const Block second={-3,0,1,10105,10,1};
    const RGB openSecond=delta(draw({leaf,second},side,west),night);
    const RGB both=delta(draw({leaf,warm,second},side,west),night);
    const RGB sum={back[0]+openSecond[0],back[1]+openSecond[1],back[2]+openSecond[2]};
    const RGB withWall=delta(draw({leaf,wall,warm,second},side,west),draw({leaf,wall},side,west));
    check(maxAbs(delta(both,sum))<.00005 && y(openSecond)>.001 && y(both)>y(openSecond)+.0001,
          "independent front and back emitters add in linear radiance");
    check(maxAbs(delta(withWall,openSecond))<.00005,"blocker removes only the light behind the leaf");
    Carried carried;
    carried.item=11101;carried.level=14;carried.firstPerson=false;
    carried.relEye={camera[0]-3.2,camera[1]-1.0,camera[2]-.5};
    auto handheld=[&](const std::vector<Block>& cells) {
        w.buildCarried(cells,camera,carried);
        return terrain.draw(w,camera,side,west,0,0,leaf.id,atlas)[0];
    };
    const RGB heldBack=delta(handheld({leaf}),night);
    const RGB heldBlocked=delta(handheld({leaf,wall}),draw({leaf,wall},side,west));
    print("held torch behind",heldBack);print("held torch with wall",heldBlocked);
    check(heldBack[0]>.0001 && heldBack[0]>heldBack[2] && maxAbs(heldBlocked)<.00002,
          "held torch lights the leaf through the same open path and respects the wall");
    w.build({leaf,warm},camera);
    const std::array<float,4> coverage={0.f,.09f,.11f,1.f};
    const auto cutout=terrain.draw(w,camera,side,west,0,0,leaf.id,atlas,true,nullptr,&coverage);
    check(cutout[0][0]==-1.f && cutout[1][1]==-1.f && cutout[2][0]>0.f && cutout[3][0]>0.f,
          "backlighting preserves the vanilla leaf silhouette and its open texels");
    TerrainSun clear,roof,cloud;
    roof.casterHeight=12.f;cloud.incident=0.f;
    const RGB solar=delta(draw({leaf},below,down,&clear),draw({leaf},below,down,&cloud));
    const RGB roofSun=delta(draw({leaf},below,down,&roof),draw({leaf},below,down,&cloud));
    const RGB rockSun=delta(draw({rock},below,down,&clear),draw({rock},below,down,&cloud));
    const D3 top={.5,1,.5},up={0,1,0};
    const RGB frontSun=delta(draw({leaf},top,up,&clear),draw({leaf},top,up,&cloud));
    // The closest possible opaque roof touches the leaf. A large self-shadow
    // bias would accidentally jump beyond a one-block ceiling in this case.
    const Block cap={0,1,0,10001,0,0};
    TerrainSun touching;touching.casterHeight=2.f;
    const RGB nearRoof=delta(draw({leaf,cap},below,down,&touching),draw({leaf,cap},below,down,&cloud));
    print("sun with touching stone",nearRoof);
    check(maxAbs(nearRoof)<.00002,"a one-block-thick roof touching the receiver closes solar transmission");
    print("sun front",frontSun);print("sun under leaf",solar);print("sun under roof",roofSun);print("sun under stone",rockSun);
    check(y(frontSun)>.01 && y(solar)>.001 && y(solar)<y(frontSun),"open solar path reaches a bounded leaf underside");
    check(maxAbs(roofSun)<.00002 && maxAbs(rockSun)<.00002,"shadow depth and opaque receiver each exclude underside sunlight");
    // A roof can be known only to the real Sun shadow map (e.g. just
    // beyond the voxel capture). Do not step through it to escape self-shadow.
    const D3 distantEye={-23.5,-1.5,.5};
    auto sunAt=[&](const D3& eye,const D3& point,const D3& normal,const Block& owner,const TerrainSun& sky,
                   const std::array<RGB,4>& colors) {
        w.build({owner},eye);
        terrain.setSun(sky,eye[1]);
        return terrain.draw(w,eye,point,normal,0,1,owner.id,colors,true,&sky)[0];
    };
    const RGB farOpen=delta(sunAt(distantEye,below,down,leaf,clear,atlas),sunAt(distantEye,below,down,leaf,cloud,atlas));
    const RGB farCovered=delta(sunAt(distantEye,below,down,leaf,touching,atlas),sunAt(distantEye,below,down,leaf,cloud,atlas));
    const RGB nearCovered=delta(draw({leaf},below,down,&touching),draw({leaf},below,down,&cloud));
    print("outside local coverage, open",farOpen);print("outside local coverage, roof",farCovered);
    check(y(farOpen)>.0001 && maxAbs(farCovered)<.00002 && maxAbs(nearCovered)<.00002,
          "a shadow-map-only one-block roof stays closed inside and outside local tracing");
    const RGB white={1,1,1};
    const std::array<RGB,4> whiteAtlas={white,white,white,white};
    const RGB whiteFront=delta(sunAt(camera,top,up,leaf,clear,whiteAtlas),sunAt(camera,top,up,leaf,cloud,whiteAtlas));
    const RGB whiteBack=delta(sunAt(camera,below,down,leaf,clear,whiteAtlas),sunAt(camera,below,down,leaf,cloud,whiteAtlas));
    const RGB whiteCeiling=delta(sunAt(camera,top,up,rock,clear,whiteAtlas),sunAt(camera,top,up,rock,cloud,whiteAtlas));
    bool bounded=true;
    for(size_t c=0;c<3;c++) bounded&=(whiteFront[c]+whiteBack[c]<=whiteCeiling[c]+.0002);
    check(bounded,"even the brightest atlas texels stay within the incident energy budget");
    // Capture an ordinary lamp inside six one-cell-thick supports. The
    // published field can mark the enclosed air but must preserve the lamp's
    // kind and level. Moving one support out of reach must clear the flag.
    std::vector<Block> supports={{0,0,0,10100,14,1},{-1,0,0,10300,0,1},
        {1,0,0,10300,0,1},{0,-2,0,10001,0,0},{0,2,0,10001,0,0},
        {0,0,-1,10300,0,1},{0,0,4,10300,0,1}};
    auto centralWords=[&]() {
        const D3 origin={0,0,0};
        w.build(supports,origin);
        const auto raw=w.readUint(w.cell,w.pCell.w,w.pCell.h);
        const auto field=w.readFloat(w.field,w.pField.w,w.pField.h,1);
        const size_t centre=32+64*(32+64*32);
        return std::pair<unsigned,unsigned>{raw.at(centre),unsigned(field.at(centre))};
    };
    const auto enclosed=centralWords();
    supports.back().z=5;
    const auto open=centralWords();
    const unsigned neighbourhood=fs::exists(root/"lib/leaf_disk.glsl")?1u<<19:0u;
    check(enclosed.first!=0 && (enclosed.first&63u)==0 &&
          enclosed.second==(enclosed.first|(1u<<20)|neighbourhood) &&
          open.first==enclosed.first && open.second==(open.first|neighbourhood),
          "published enclosed-air bit preserves emitting cells and clears after opening the canopy");
    std::cout<<"LEAF optical checks failed="<<failed<<" on "<<w.renderer<<"\n";
    return failed;
}
} // namespace aqualumenLeafLight
// Native regression from a synthetic asymmetric atlas through the shipping shadow
// vertices, image publication, and the segment queried by the terrain lamp pass.
namespace aqualumenFoliageCast {
// Translate a disk and receiver together across an atlas leaf, including both
// outer edges. Its normal stays along Z, so the reference disk is in XY.
inline void checkLeafPenumbra(aqualumenDoor::Rig& rig,const fs::path& root) {
    using namespace aqualumenDoor;
    const std::string vertex="#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}";
    const std::string frag="#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)
        +expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/local_lighting.glsl",root)+R"(
uniform sampler2D probeData;
out vec4 result;
void main() {
    vec3 a=texelFetch(probeData,ivec2(int(gl_FragCoord.x),0),0).xyz;
    LampOccluders occluders;
    occluders.entityTest=false;
    occluders.entities=entityBounds();
    occluders.toRelative=vec3(0);
    occluders.work=entityWorkBudget;
    occluders.leafVolume=false;
    occluders.leafCell=ivec3(-1);
    result=vec4(lampVisibility(a,a+vec3(0,0,4),vec3(0,0,1),.13,false,occluders),1);
})";
    const GLuint program=link(vertex,frag,"leaf-penumbra-eval");
    constexpr int positions=96,rows=3,referenceSamples=256;
    std::vector<float> data;
    std::vector<Ray> rays;
    for(int row=0;row<rows;row++) for(int i=0;i<positions;i++) {
        const D3 a={31.90+1.2*(i+.5)/positions,32.17+.31*row,30.2};
        data.insert(data.end(),{float(a[0]),float(a[1]),float(a[2]),1.f});
        for(int k=0;k<referenceSamples;k++) {
            const double radius=.13*std::sqrt((k+.5)/referenceSamples);
            const double angle=k*2.399963229728653+1.271;
            const D3 b={a[0]+radius*std::cos(angle),a[1]+radius*std::sin(angle),a[2]+4};
            rays.push_back({a,b,false,""});
        }
    }
    const auto filtered=rig.evalRows(program,data,positions*rows,1);
    glDeleteProgram(program);
    const auto pointSamples=rig.transmission(rays);
    std::vector<double> errors;
    double squaredError=0;
    for(int i=0;i<positions*rows;i++) {
        double reference=0;
        for(int k=0;k<referenceSamples;k++) reference+=pointSamples[i*referenceSamples+k][1];
        const double error=std::abs(filtered[4*i+1]-reference/referenceSamples);
        errors.push_back(error);
        squaredError+=error*error;
    }
    std::sort(errors.begin(),errors.end());
    const double rms=std::sqrt(squaredError/errors.size()),p95=errors[errors.size()*95/100];
    std::cout<<"FOLIAGE PENUMBRA "<<errors.size()<<" receivers, "<<referenceSamples
             <<" disk rays per reference: RMS "<<rms<<", P95 "<<p95<<"\n";
    if(!(rms<.025 && p95<.060))
        throw std::runtime_error("leaf penumbra diverged from the dense finite-source reference");
}

inline void probe(const fs::path& root) {
    using namespace aqualumenDoor;
    Rig rig;rig.init(root);
    const int key=8;
    const double ox=Atlas::ox(key),oy=Atlas::oy(key),N=Atlas::N;
    const double centre[2]={(ox+8)/N,(oy+8)/N};
    const D3 offset=rig.gridOffset();
    auto publish=[&](std::array<uint8_t,3> pigment,std::array<float,3> tint,int layerCount) {
        rig.clearFrame();
        auto pixels=rig.atlas.rgba;
        for(int y=0;y<16;y++) for(int x=0;x<16;x++) {
            size_t base=4*(size_t(Atlas::oy(key)+y)*Atlas::N+Atlas::ox(key)+x);
            std::copy(pigment.begin(),pigment.end(),pixels.begin()+base);
        }
        aqualumenLocalLights::resetTextureMatrices();
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();glMatrixMode(GL_PROJECTION);glLoadIdentity();
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,rig.atlasTex);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,Atlas::N,Atlas::N,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
        glGenerateMipmap(GL_TEXTURE_2D);
        glEnable(GL_RASTERIZER_DISCARD);rig.useShadowState(rig.cutout);
        glBegin(GL_QUADS);
        const int us[]={0,1,1,0},vs[]={0,0,1,1};
        Rig::V vertices[4];
        for(int i=0;i<4;i++)
            vertices[i]={{double(us[i]),double(1-vs[i]),1},{(ox+16*us[i])/N,(oy+16*vs[i])/N}};
        const double normal[]={0,0,1};
        for(int i=0;i<layerCount;i++) {
            const int cell[]={32,32,32+i};
            Rig::emitQuad(cell,10300,0,vertices,normal,centre,offset.data(),rig.cam.data(),tint.data());
        }
        glEnd();glMemoryBarrier(GL_ALL_BARRIER_BITS);glDisable(GL_RASTERIZER_DISCARD);glUseProgram(0);
        rig.publish();
    };
    publish({160,160,160},{1,1,1},1);
    checkLeafPenumbra(rig,root);
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
    const auto neutral=rig.transmission(rays);
    publish({160,160,160},{.36f,.87f,.26f},1);
    const auto green=rig.transmission(rays);
    publish({235,92,148},{1,1,1},1);
    const auto pink=rig.transmission(rays);
    int wrong=0,counts[3]={};
    double sums[3]={},maxAsymmetry=0,mean=0;
    double lo[]={1,1,1},hi[]={0,0,0};
    for(size_t i=0;i<rays.size();++i) {
        int c=sheets[i];
        const auto& n=neutral[i];const auto& g=green[i];const auto& p=pink[i];
        if(i%2) maxAsymmetry=std::max(maxAsymmetry,std::abs(double(n[1]-neutral[i-1][1])));
        if(c==0) wrong+=n[0]<.8 || std::abs(g[0]-p[0])>.00002;
        else wrong+=!(g[1]>g[0] && p[0]>p[1] && p[2]>p[1]);
        wrong+=n[1]<0 || n[1]>1 || std::abs(n[0]-n[1])>.00002;
        sums[c]+=n[1];counts[c]++;mean+=n[1];
        lo[c]=std::min(lo[c],double(n[1]));hi[c]=std::max(hi[c],double(n[1]));
    }
    mean/=neutral.size();
    std::cout<<"PROJECTED FOLIAGE native rays "<<rays.size()<<" x neutral, green biome, pink atlas; "<<rig.renderer<<"\n";
    for(int i=0;i<3;i++) std::cout<<"covered faces "<<i<<" rays "<<counts[i]<<" mean "<<sums[i]/std::max(counts[i],1)<<"\n";
    std::cout<<"wrong="<<wrong<<" reciprocal-error="<<maxAsymmetry<<" mean="<<mean<<"\n";
    if(wrong || maxAsymmetry>.0001 || !(hi[2]<lo[1] && hi[1]<lo[0]) || std::abs(mean-std::exp(-1.45))>.07)
        throw std::runtime_error("captured sprite, biome tint, or canopy mean failed");
    // A ray through the same two open texels in consecutive cubes encounters
    // unresolved medium at the interface. Bound it between stone and an open gap.
    std::vector<Ray> stacked;
    for(size_t i=1024;i<rays.size();i+=2) if(sheets[i]==0) {
        Ray r=rays[i];r.b[2]=34.5;stacked.push_back(r);
    }
    publish({160,160,160},{1,1,1},2);
    for(auto value:rig.transmission(stacked)) if(value[1]<=0 || value[1]>=lo[0]*.8)
        throw std::runtime_error("contiguous foliage did not attenuate at its internal boundary");
    if(fs::exists(root/"lib/leaf_disk.glsl")) {
        publish({160,160,160},{1,1,1},1);
        const std::string code="#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)
            +expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/local_lighting.glsl",root)+R"(
out vec4 result;
void main() {
    vec3 a=vec3(32.048,32.43,30.2);
    ivec3 cell;int word;
    bool clear=singleLeafCone(a,a+vec3(0,0,4),vec3(.13,0,0),vec3(0,.13,0),false,cell,word);
    result=vec4(float(clear));
})";
        GLuint classify=link("#version 430 compatibility\nvoid main(){gl_Position=gl_Vertex;}",code,"leaf-cone-blocker");
        auto isolated=[&]() { return rig.evalRows(classify,std::vector<float>(4),1,1).front()>.5f; };
        if(!isolated()) throw std::runtime_error("isolated leaf was not recognized");
        Scene nearReceiver;
        nearReceiver.cubes.push_back({{31,32,30}});
        rig.capture(nearReceiver,false,false);rig.publish();
        if(!isolated()) throw std::runtime_error("a cube outside the narrow end falsely intersects the cone");
        Scene offAxis;
        offAxis.cubes.push_back({{31,32,33}});
        rig.capture(offAxis,false,false);rig.publish();
        if(isolated()) throw std::runtime_error("single-leaf shortcut missed an off-axis stone blocker");
        glDeleteProgram(classify);
        std::cout<<"PASS finite leaf disk excludes an off-axis blocker across the rim of the emitter\n";
    }
    rig.frame({});
    for(auto value:rig.transmission(rays)) if(value[0]<.9999) throw std::runtime_error("removed foliage left a shadow");
}
}
