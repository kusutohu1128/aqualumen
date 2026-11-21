// GPU regression for portable (first/third-person held-item) lights, driven through the REAL shadowcomp1 dispatch.
//
// Runs inside aqualumenLocalLights::probe() right after the placed-light checks and reuses its World/TerrainRig:
//   - Placed fixtures are still captured by the real shadow_*.vsh passes; held items are NOT mocked.
//   - Held-item state is injected only through the production uniforms of shadowcomp1.csh (World::applyCarried:
//     glUseProgram(comp) + glUniform*): heldItemId/2, heldBlockLightValue/2, isSpectator, firstPersonCamera,
//     isRightHanded, playerLookVector, relativeEyePosition, cameraPosition, gbufferModelViewInverse, isEyeInWater.
//   - Results are read back from the published lampListImage (records with code >= 1024 are held lights:
//     code = kind + level*64 + 1024) and through the production lampLighting() / gbuffers_terrain passes.
// Item ids are resolved from the pack's own item.properties by item name, never hard-coded here. Absolute hand
// offsets are not asserted (that is a design constant); only mirror, rotation, translation, occlusion and
// accounting invariants are. Packs whose shadowcomp1.csh does not consume heldItemId are skipped explicitly.
// Timings are GPU-harness timings of the compute pass, NOT Minecraft frame times.
#pragma once
namespace aqualumenLocalLights {

struct Rot {   // R = Ry(yaw)*Rx(pitch), view -> world, no roll. Identity looks along -Z.
    double m[3][3];
    D3 apply(const D3& v) const {
        return {m[0][0]*v[0]+m[0][1]*v[1]+m[0][2]*v[2],m[1][0]*v[0]+m[1][1]*v[1]+m[1][2]*v[2],m[2][0]*v[0]+m[2][1]*v[1]+m[2][2]*v[2]};
    }
    std::array<float,16> mat4() const {
        std::array<float,16> o{};
        for(int c=0;c<3;c++) for(int r=0;r<3;r++) o[size_t(c*4+r)]=float(m[r][c]);
        o[15]=1;return o;
    }
};
inline Rot rotation(double yawDeg,double pitchDeg) {
    const double y=yawDeg*M_PI/180,p=pitchDeg*M_PI/180,cy=std::cos(y),sy=std::sin(y),cp=std::cos(p),sp=std::sin(p);
    return {{{cy,sy*sp,sy*cp},{0,cp,-sp},{-sy,cy*sp,cy*cp}}};
}

struct HeldRec {
    std::array<float,4> raw{};D3 grid{},world{};int code=0;
    bool held() const { return code>=1024; }
    int kind() const { return (code-1024)%64; }
    int level() const { return (code-1024)/64; }
};
struct Snap {
    std::vector<std::vector<HeldRec>> rows;   // per cluster row, in published order
    std::vector<HeldRec> held;                // distinct held records (<=2)
};
inline bool sameRaw(const std::vector<HeldRec>& a,const std::vector<HeldRec>& b) {
    if(a.size()!=b.size()) return false;
    for(size_t i=0;i<a.size();i++) if(a[i].raw!=b[i].raw) return false;
    return true;
}
inline std::vector<HeldRec> placedOnly(const std::vector<HeldRec>& row) {
    std::vector<HeldRec> r;for(auto& h:row) if(!h.held()) r.push_back(h);return r;
}

// Validates the published list structure and returns it with world-space positions (grid origin = floor(camera/8)*8-32).
inline Snap carriedSnapshot(World& w,const D3& cam) {
    Snap s;s.rows.resize(512);
    auto list=w.readFloat(w.list,w.pList.w,w.pList.h,4);
    const int width=w.pList.w;
    const D3 base={std::floor(cam[0]/8)*8,std::floor(cam[1]/8)*8,std::floor(cam[2]/8)*8};
    for(int row=0;row<512;row++) {
        const float* head=&list[size_t(row)*width*4];
        const int count=int(head[0]);
        require(head[0]==std::floor(head[0])&&count>=0&&count<=width-1,"cluster "+std::to_string(row)+" count "+num(head[0])+" is not an integer in 0.."+std::to_string(width-1));
        bool seenHeld=false;int heldInRow=0;
        for(int k=0;k<count;k++) {
            const float* r=&list[(size_t(row)*width+1+k)*4];
            HeldRec h;
            for(int c=0;c<4;c++) {require(std::isfinite(r[c]),"nonfinite published record");h.raw[size_t(c)]=r[c];}
            h.code=int(std::lround(r[3]));
            require(h.code>0&&float(h.code)==r[3],"cluster "+std::to_string(row)+" record "+std::to_string(k)+" has invalid kind/level code "+num(r[3]));
            for(int c=0;c<3;c++) {h.grid[size_t(c)]=r[c];h.world[size_t(c)]=base[size_t(c)]+r[c]-32.0;}
            if(h.held()) {
                seenHeld=true;heldInRow++;
                bool known=false;
                for(auto& u:s.held) known|=u.code==h.code&&std::abs(u.grid[0]-h.grid[0])<1e-5&&std::abs(u.grid[1]-h.grid[1])<1e-5&&std::abs(u.grid[2]-h.grid[2])<1e-5;
                if(!known) s.held.push_back(h);
            } else require(!seenHeld,"cluster "+std::to_string(row)+": placed record after a held record (held lights must be appended after the placed ranking)");
            s.rows[size_t(row)].push_back(h);
        }
        require(heldInRow<=2,"cluster "+std::to_string(row)+" lists "+std::to_string(heldInRow)+" held records (max 2)");
    }
    require(s.held.size()<=2,"clusters disagree on the held light: "+std::to_string(s.held.size())+" distinct held records published (same item must have one position everywhere)");
    // Every cluster whose box is within range of a held light must list it, bit-identical in position.
    for(auto& u:s.held) for(int row=0;row<512;row++) {
        const int tx=row%8,tz=(row/8)%8,ty=row/64;
        const double centre[3]={tx*8+4.0,ty*8+4.0,tz*8+4.0};
        double n2=0;for(int c=0;c<3;c++) {double nn=std::max(std::abs(u.grid[size_t(c)]-centre[c])-4.0,0.0);n2+=nn*nn;}
        if(n2>=(w.range-0.5)*(w.range-0.5)) continue;
        bool found=false;
        for(auto& h:s.rows[size_t(row)]) found|=h.code==u.code&&h.grid==u.grid;
        require(found,"cluster "+std::to_string(row)+" is within lampRange of a held light but does not list it");
    }
    return s;
}

// item name -> item id from item.properties (fallback shaders.properties). Handles "\" continuations and "minecraft:".
inline std::map<std::string,int> parseItemIds(const fs::path& root) {
    std::string text;
    for(const char* f:{"item.properties","shaders.properties"}) if(fs::exists(root/f)) text+=slurp(root/f)+"\n";
    std::map<std::string,int> ids;
    std::istringstream in(text);std::string line,acc;
    const std::regex re("\\s*item\\.(\\d+)\\s*=\\s*(.*)");
    while(std::getline(in,line)) {
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        const bool cont=!line.empty()&&line.back()=='\\';
        if(cont) line.pop_back();
        acc+=line+(cont?" ":"");
        if(cont) continue;
        std::smatch m;
        if(std::regex_match(acc,m,re)) {
            std::istringstream tokens(m[2].str());std::string tok;
            while(tokens>>tok) {auto p=tok.find(':');ids[p==std::string::npos?tok:tok.substr(p+1)]=std::stoi(m[1].str());}
        }
        acc.clear();
    }
    return ids;
}

inline void carriedProbe(World& w,TerrainRig& terrain,double softening,const D3& C0) {
    const fs::path& root=w.root;
    if(expand(root/"shadowcomp1.csh",root).find("heldItemId")==std::string::npos) {
        std::cout<<"SKIP carried-light QA: shadowcomp1.csh does not consume heldItemId (historical pack without portable-light item definitions); placed-light QA above is unaffected\n";
        return;
    }
    const auto items=parseItemIds(root);
    auto itemId=[&](const char* name) {
        auto it=items.find(name);
        require(it!=items.end(),std::string("shadowcomp1.csh consumes heldItemId but item.properties maps no minecraft:")+name);
        return it->second;
    };
    const int idTorch=itemId("torch"),idSoul=itemId("soul_torch"),idLantern=itemId("lantern");
    auto needUniform=[&](const char* name,const char* why) {
        require(uniformActive(w.comp,name),std::string("shadowcomp1.csh does not consume uniform ")+name+" (inactive/optimised out): cannot verify "+why);
    };
    needUniform("heldItemId","held item selection");needUniform("heldBlockLightValue","held light level");needUniform("cameraPosition","grid-space publication");
    std::cout<<"CARRIED-LIGHT QA renderer: "<<w.renderer<<" | real shadowcomp1.csh dispatch with REAL uniforms; item ids from item.properties: torch="<<idTorch
             <<" soul_torch="<<idSoul<<" lantern="<<idLantern<<" (held records are list codes >= 1024: kind+level*64+1024)\n";

    // ------------------------------------------------------------------ helpers
    using Rows=std::vector<std::array<float,3>>;
    auto sub=[](D3 a,D3 b){return D3{a[0]-b[0],a[1]-b[1],a[2]-b[2]};};
    auto add=[](D3 a,D3 b){return D3{a[0]+b[0],a[1]+b[1],a[2]+b[2]};};
    auto mul=[](D3 a,double s){return D3{a[0]*s,a[1]*s,a[2]*s};};
    auto dist=[&](D3 a,D3 b){D3 d=sub(a,b);return std::sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);};
    auto rgbSum=[](std::array<float,3> a){return double(a[0])+a[1]+a[2];};
    auto carry=[](int item,int level,int item2=0,int level2=0) {Carried c;c.item=item;c.level=level;c.item2=item2;c.level2=level2;return c;};
    auto run=[&](const std::vector<Block>& scene,const D3& cam,const Carried& c) {w.buildCarried(scene,cam,c);return carriedSnapshot(w,cam);};
    auto lit=[&](const std::vector<Query>& q,const D3& cam,int medium=0) {w.medium=medium;auto r=w.evaluate(q,cam);w.medium=0;return r;};
    auto heldKind=[&](const Snap& s,int kind)->HeldRec {
        for(auto& h:s.held) if(h.kind()==kind) return h;
        throw std::runtime_error("local-light QA FAIL: no held record of kind "+std::to_string(kind)+" published");
    };
    auto facingFrom=[&](D3 p,double d,D3 dir) {return Query{add(p,mul(dir,d)),{-dir[0],-dir[1],-dir[2]},{0,1,0},0.075f,0,false};};
    const D3 up={0,1,0};
    const D3 E0=C0;
    const std::vector<Block> placedOne={torch(1005,71,-2050)};
    const int codeTorch14=1024+1+14*64;

    // ------------------------------------------------------------------ A. nothing held: defaults and explicit zeros
    {
        w.build(placedOne,E0);   // plain publish(): the carried uniforms of this program have never been written
        Snap baseline=carriedSnapshot(w,E0);
        require(baseline.held.empty(),"default (never-written) carried uniforms must publish no held light");
        size_t placedRows=0;for(auto& r:baseline.rows) placedRows+=!r.empty();
        require(placedRows>0,"placed torch must still be published (control)");
        struct Case {const char* name;Carried c;};
        std::vector<Case> cases;
        cases.push_back({"explicit zeros",Carried{}});
        cases.push_back({"block-light value 14 without an item id",carry(0,14,0,14)});
        cases.push_back({"mapped items with block-light value 0",carry(idTorch,0,idSoul,0)});
        cases.push_back({"unmapped ids (11199, a placed-torch block id 10100)",carry(11199,14,10100,14)});
        for(auto& k:cases) {
            Snap s=run(placedOne,E0,k.c);
            require(s.held.empty(),std::string("held light published for: ")+k.name);
            for(int row=0;row<512;row++) require(sameRaw(s.rows[size_t(row)],baseline.rows[size_t(row)]),std::string("placed records changed for: ")+k.name);
        }
        w.build({},E0);
        for(auto& r:carriedSnapshot(w,E0).rows) require(r.empty(),"empty world must publish empty lists");
        std::cout<<"PASS carried none: never-written uniforms and "<<cases.size()<<" explicit no-light states (zeros, level without id, id without level, unmapped ids) publish no held record and leave all "<<placedRows<<" placed rows bit-identical\n";
    }

    // ------------------------------------------------------------------ B. one main-hand light: record, mapping, translation
    const Carried torchMain=carry(idTorch,14);
    Snap single=run({},E0,torchMain);
    require(single.held.size()==1,"one held torch must publish exactly one held record, got "+std::to_string(single.held.size()));
    const D3 o0=sub(single.held[0].world,E0);   // right-hand main offset from the eye, first person, looking -Z
    {
        const HeldRec& h=single.held[0];
        require(h.code==codeTorch14,"torch/14 must publish code kind+level*64+1024="+std::to_string(codeTorch14)+", got "+std::to_string(h.code));
        require(dist(h.world,E0)>0.1&&dist(h.world,E0)<1.5,"hand light must sit 0.1..1.5 m from the eye, got "+num(dist(h.world,E0)));
        require(o0[0]>0.05,"right-handed main-hand light must be right of the eye (+X when looking -Z): dx="+num(o0[0]));
        require(o0[2]<0.05,"hand light must not be behind the eye (looking -Z): dz="+num(o0[2]));
        const D3 Eb={E0[0]+17.0,E0[1]-3.0,E0[2]+9.5};
        Snap moved=run({},Eb,torchMain);
        require(moved.held.size()==1&&dist(sub(moved.held[0].world,Eb),o0)<2e-4,"hand offset must not depend on world position / grid snap");
        std::cout<<"PASS carried main hand: torch/14 publishes one record code "<<h.code<<" in every cluster within "<<w.range<<" m, eye-relative offset ("<<o0[0]<<","<<o0[1]<<","<<o0[2]
                 <<") (right of eye, not behind), identical after moving the player across grid snaps\n";
    }

    // ------------------------------------------------------------------ C. handedness mirror
    {
        auto offset=[&](bool right,bool mainHand) {
            Carried c=mainHand?carry(idTorch,14):carry(0,0,idTorch,14);c.rightHanded=right;needUniform("isRightHanded","handedness");
            Snap s=run({},E0,c);require(s.held.size()==1,"one light expected for the handedness case");return sub(s.held[0].world,E0);
        };
        const D3 rm=offset(true,true),ro=offset(true,false),lm=offset(false,true),lo=offset(false,false);
        require(rm[0]>0.05&&ro[0]<-0.05&&lm[0]<-0.05&&lo[0]>0.05,"main/off hands must be on opposite sides, flipped by isRightHanded: "+num(rm[0])+","+num(ro[0])+","+num(lm[0])+","+num(lo[0]));
        auto mirrored=[&](D3 a,D3 b) {return std::abs(a[0]+b[0])<2e-4&&std::abs(a[1]-b[1])<2e-4&&std::abs(a[2]-b[2])<2e-4;};
        require(mirrored(rm,ro)&&mirrored(rm,lm)&&mirrored(ro,lo),"off hand and left-handed main hand must be exact X-mirrors of the right-handed main hand");
        require(dist(rm,lo)<2e-4&&dist(ro,lm)<2e-4,"left-handed off hand must equal right-handed main hand");
        require(std::abs(rm[0]-ro[0])>0.2,"the two hands must be visibly separated, got "+num(std::abs(rm[0]-ro[0]))+" m");
        std::cout<<"PASS carried handedness: main/off x="<<rm[0]<<"/"<<ro[0]<<" right-handed, mirrored exactly (y,z unchanged, <2e-4 m) for left-handed; hands "<<std::abs(rm[0]-ro[0])<<" m apart\n";
    }

    // ------------------------------------------------------------------ D. first person follows the view (yaw/pitch)
    {
        double worst=0;
        const std::pair<double,double> views[]={{90,0},{-37,0},{180,0},{25,-30},{-140,40}};
        for(auto& v:views) {
            Rot R=rotation(v.first,v.second);
            Carried c=torchMain;c.viewInverse=R.mat4();c.look=R.apply({0,0,-1});
            Snap s=run({},E0,c);require(s.held.size()==1,"one light expected under a rotated first-person view");
            D3 expect=R.apply(o0),got=sub(s.held[0].world,E0);
            worst=std::max(worst,dist(expect,got));
            require(dist(expect,got)<3e-4,"first-person hand offset must rotate with the camera (yaw "+num(v.first)+", pitch "+num(v.second)+"): got ("+num(got[0])+","+num(got[1])+","+num(got[2])+") expected ("+num(expect[0])+","+num(expect[1])+","+num(expect[2])+")");
        }
        std::cout<<"PASS carried first-person view: offset == R*offset(look -Z) for 5 yaw/pitch views (180 deg, +-90, pitch +-40) within "<<worst<<" m\n";
    }

    // ------------------------------------------------------------------ E. item/level mapping, equivalence with a placed lamp, range, glint
    const D3 Lt={1005.5,71.75,-2049.5};            // staged held-light position
    const D3 Es=sub(Lt,o0);                        // eye that puts the right-hand main light at Lt
    {
        const struct {const char* name;int id;int kind;} mapped[]={{"torch",idTorch,1},{"soul_torch",idSoul,6},{"lantern",idLantern,11}};
        for(auto& m:mapped) for(int level:{7,14,15}) {
            Snap s=run({},Es,carry(m.id,level));
            require(s.held.size()==1&&s.held[0].kind()==m.kind&&s.held[0].level()==level,std::string(m.name)+" level "+std::to_string(level)+" must publish kind "+std::to_string(m.kind)+" level "+std::to_string(level));
            require(dist(s.held[0].world,Lt)<3e-4,"staged light position drifted for "+std::string(m.name));
        }
        // Held light must emit like a placed lamp of the same kind and level (same lampLighting law, same softening).
        auto heldConst=[&](int id,int level) {
            run({},Es,carry(id,level));auto e=lit({facingFrom(Lt,3.0,{1,0,0})},Es)[0];return std::array<double,3>{e[0]*(softening+9.0),e[1]*(softening+9.0),e[2]*(softening+9.0)};
        };
        auto placedConst=[&](int kind,int level) {
            Block b=blk(1005,71,-2050,10099+kind,level);auto off=kindOffset(kind);
            D3 lp={1005+double(off[0]),71+double(off[1]),-2050+double(off[2])};
            w.build({b},E0);auto e=lit({facingFrom(lp,3.0,{1,0,0})},E0)[0];return std::array<double,3>{e[0]*(softening+9.0),e[1]*(softening+9.0),e[2]*(softening+9.0)};
        };
        double worstRatio=0;
        const struct {int id,kind,level;} eq[]={{idTorch,1,14},{idTorch,1,7},{idSoul,6,14},{idLantern,11,14}};
        for(auto& q:eq) {
            auto h=heldConst(q.id,q.level),p=placedConst(q.kind,q.level);
            for(int c=0;c<3;c++) {
                if(p[size_t(c)]<1e-6) {require(h[size_t(c)]<1e-6,"held light channel must match placed lamp (zero channel)");continue;}
                require(near(h[size_t(c)],p[size_t(c)],0.01),"held kind "+std::to_string(q.kind)+" level "+std::to_string(q.level)+" channel "+std::to_string(c)+" must emit like a placed lamp: "+num(h[size_t(c)])+" vs "+num(p[size_t(c)]));
                worstRatio=std::max(worstRatio,std::abs(h[size_t(c)]/p[size_t(c)]-1));
            }
        }
        // Level ordering and hue through the real compute inputs.
        auto at3=[&](const Carried& c) {run({},Es,c);return lit({facingFrom(Lt,3.0,{1,0,0})},Es)[0];};
        auto l7=at3(carry(idTorch,7)),l14=at3(carry(idTorch,14)),l15=at3(carry(idTorch,15));
        require(l7[0]>0&&l7[0]<l14[0]&&l14[0]<l15[0],"held light must brighten with heldBlockLightValue 7<14<15");
        auto warm=at3(carry(idTorch,14)),soul=at3(carry(idSoul,14)),lantern=at3(carry(idLantern,14));
        require(warm[0]>warm[1]&&warm[1]>warm[2]&&warm[2]>0,"held torch hue must be warm");
        require(soul[2]>soul[1]&&soul[1]>soul[0]&&soul[0]>0,"held soul torch hue must be blue");
        require(lantern[0]>lantern[2]&&rgbSum(lantern)>0,"held lantern must be warm and non-zero");
        std::cout<<"PASS carried mapping: torch->kind 1, soul_torch->6, lantern->11 at levels 7/14/15; each emits like a placed lamp of equal kind/level within "<<worstRatio*100<<"% (E*(k+d^2)); level 7<14<15 ("
                 <<l7[0]<<"<"<<l14[0]<<"<"<<l15[0]<<"); torch warm, soul torch blue\n";

        // Range through the cluster lists: six directions agree, exactly zero from lampRange.
        run({},Es,carry(idTorch,14));
        const D3 dirs[6]={{1,0,0},{-1,0,0},{0,0,1},{0,0,-1},{0,1,0},{0,-1,0}};
        const double ds[]={4,9.5,13,13.9};
        std::vector<Query> q;for(auto& d:dirs) for(double r:ds) q.push_back(facingFrom(Lt,r,d));
        for(auto& d:dirs) {q.push_back(facingFrom(Lt,14.0,d));q.push_back(facingFrom(Lt,15.0,d));}
        auto e=lit(q,Es);
        for(int d=0;d<6;d++) for(size_t i=0;i<4;i++) {
            double got=e[size_t(d)*4+i][0],ref=e[i][0];
            require(got>0&&near(got,ref,0.004),"held light range/anisotropy at "+num(ds[i])+" m dir "+std::to_string(d)+": "+num(got)+" vs "+num(ref));
        }
        for(size_t i=24;i<e.size();i++) require(rgbSum(e[i])==0,"held light must be exactly zero at/after lampRange");
        std::cout<<"PASS carried range: all six directions agree to 0.4% from 4 to 13.9 m through the cluster lists, exactly zero from "<<w.range<<" m\n";

        // Water glint: specular lobe peaks at the mirror geometry of the actual held position.
        const double surfaceY=71.0,h=Lt[1]-surfaceY;
        auto sweep=[&](float rough,double dx) {
            std::vector<Query> g;for(double el=3.0;el<=25.0+1e-9;el+=0.05) {double r=el*M_PI/180;g.push_back({{Lt[0]+dx,surfaceY,Lt[2]},{0,1,0},{std::cos(r),std::sin(r),0},rough,0,true});}
            auto r=lit(g,Es);std::vector<double> y;for(auto& v:r) y.push_back(v[0]);return y;
        };
        auto g=sweep(0.075f,4.0);
        size_t peak=size_t(std::max_element(g.begin(),g.end())-g.begin());
        const double peakAngle=3.0+0.05*double(peak),mirror=std::atan2(h,4.0)*180/M_PI;
        require(std::abs(peakAngle-mirror)<0.4,"held-light water glint peak "+num(peakAngle)+" deg vs mirror geometry "+num(mirror));
        const size_t skip=std::min(g.size()-1,size_t((mirror+8-3.0)/0.05));
        require(g[peak]>0&&*std::max_element(g.begin()+long(skip),g.end())<0.01*g[peak],"held glint must be a localized lobe");
        auto gFar=sweep(0.075f,6.0);
        size_t farPeak=size_t(std::max_element(gFar.begin(),gFar.end())-gFar.begin());
        require(std::abs(3.0+0.05*double(farPeak)-std::atan2(h,6.0)*180/M_PI)<0.4,"held glint must follow geometry for a 6 m receiver");
        auto rough=sweep(0.12f,4.0);
        require(*std::max_element(rough.begin(),rough.end())<g[peak],"rougher water must lower the held glint");
        std::cout<<"PASS carried water glint: peak "<<peakAngle<<" deg vs mirror "<<mirror<<" deg (4 m), 6 m peak "<<3.0+0.05*double(farPeak)<<" vs "<<std::atan2(h,6.0)*180/M_PI<<" deg, peak "<<g[peak]<<" -> rough "<<*std::max_element(rough.begin(),rough.end())<<"\n";
    }

    // ------------------------------------------------------------------ F. two hands: mixed items add, same items give two records
    {
        const Carried mixed=carry(idTorch,14,idSoul,12);
        Snap s=run({},Es,mixed);
        require(s.held.size()==2,"two held items must publish two records, got "+std::to_string(s.held.size()));
        HeldRec a=heldKind(s,1),b=heldKind(s,6);
        require(a.level()==14&&b.level()==12,"main/off levels must be kept per hand");
        require(a.world[0]>b.world[0],"right-handed main (torch) must be right of the off hand (soul torch)");
        const std::vector<Query> q={facingFrom(a.world,2.0,{1,0,0}),facingFrom(b.world,2.0,{-1,0,0}),{{Lt[0],Lt[1]-1.2,Lt[2]-1.0},{0,1,0},{0,1,0},0.075f,0,false}};
        auto both=lit(q,Es);
        run({},Es,carry(idTorch,14));auto mainOnly=lit(q,Es);
        run({},Es,carry(0,0,idSoul,12));auto offOnly=lit(q,Es);
        for(size_t i=0;i<q.size();i++) for(int c=0;c<3;c++)
            require(near(both[i][size_t(c)],mainOnly[i][size_t(c)]+offOnly[i][size_t(c)],1e-4,1e-7),"torch+soul must add per channel (receiver "+std::to_string(i)+" c="+std::to_string(c)+"): "+num(both[i][size_t(c)])+" vs "+num(mainOnly[i][size_t(c)]+offOnly[i][size_t(c)]));
        require(both[2][0]>mainOnly[2][0]&&both[2][2]>offOnly[2][2]&&offOnly[2][2]>offOnly[2][0],"off-hand soul torch must brighten blue and stay blue");
        // Same item twice: two distinct records with the same code. Swapping hands swaps positions, not the set.
        Snap tt=run({},Es,carry(idTorch,14,idTorch,14));
        require(tt.held.size()==2&&tt.held[0].code==tt.held[1].code&&dist(tt.held[0].world,tt.held[1].world)>0.2,"torch in both hands must give two separated records of equal code");
        Snap swapped=run({},Es,carry(idSoul,12,idTorch,14));
        HeldRec sa=heldKind(swapped,1),sb=heldKind(swapped,6);
        require(sa.world[0]<sb.world[0]&&dist(sa.world,b.world)<2e-4&&dist(sb.world,a.world)<2e-4,"swapping the items between hands must swap the positions exactly");
        std::cout<<"PASS carried dual: torch(main,14)+soul torch(off,12) publish two records, energy == main-only + off-only per channel (1e-4) at 3 receivers; torch in both hands = 2 records; swapping hands swaps positions\n";
    }

    // ------------------------------------------------------------------ G. capacity and vanilla attribution
    {
        // 20 torches in one 8^3 tile plus a ring of lamps: placed ranking saturates at lampCapacity.
        std::vector<Block> scene;std::set<int> used;
        const D3 base={std::floor(E0[0]/8)*8,std::floor(E0[1]/8)*8,std::floor(E0[2]/8)*8};
        uint32_t seed=987654321u;auto rnd=[&](int n){seed=seed*1664525u+1013904223u;return int((seed>>8)%unsigned(n));};
        for(int i=0;i<40;i++) {
            int gx=20+rnd(24),gy=26+rnd(14),gz=20+rnd(24),a=gx+64*(gz+64*gy);
            if(!used.insert(a).second) {i--;continue;}
            scene.push_back(blk(gx+int(base[0])-32,gy+int(base[1])-32,gz+int(base[2])-32,10100,1+rnd(15)));
        }
        const Carried two=carry(idTorch,15,idSoul,15);
        w.build(scene,E0);Snap without=carriedSnapshot(w,E0);
        Snap with=run(scene,E0,two);
        require(with.held.size()==2,"held lights must be published in a saturated world");
        int saturated=0,maxCount=0;
        for(int row=0;row<512;row++) {
            auto p=placedOnly(with.rows[size_t(row)]);
            require(sameRaw(p,placedOnly(without.rows[size_t(row)])),"cluster "+std::to_string(row)+": held lights changed the placed ranking/records (they must not consume or reorder placed capacity)");
            require(int(p.size())==int(without.rows[size_t(row)].size()),"cluster "+std::to_string(row)+" placed count changed");
            if(int(p.size())==w.capacity) {
                saturated++;
                int heldHere=int(with.rows[size_t(row)].size())-int(p.size());
                const int tx=row%8,tz=(row/8)%8,ty=row/64;
                bool within=false;
                for(auto& u:with.held) {double n2=0;for(int c=0;c<3;c++) {double nn=std::max(std::abs(u.grid[size_t(c)]-(c==0?tx:c==1?ty:tz)*8.0-4.0)-4.0,0.0);n2+=nn*nn;}within|=n2<(w.range-0.5)*(w.range-0.5);}
                if(within) require(heldHere==2,"saturated cluster "+std::to_string(row)+" must still carry both held lights, has "+std::to_string(heldHere));
            }
            maxCount=std::max(maxCount,int(with.rows[size_t(row)].size()));
        }
        require(saturated>0,"fixture must saturate the placed capacity");
        require(maxCount<=w.pList.w-1,"list overflow");
        std::cout<<"PASS carried capacity: "<<saturated<<" clusters at the placed cap of "<<w.capacity<<" keep bit-identical placed records and still gain both held lights (max "<<maxCount<<" records of "<<w.pList.w-1<<" slots)\n";
    }
    {
        // Vanilla block-light attribution must come from placed lamps only: a held record adds exactly its direct term.
        const std::vector<Block> placed={torch(1008,71,-2047)};
        const D3 rcv[3]={{Lt[0]+0.2,Lt[1]-0.9,Lt[2]+0.1},{Lt[0]-1.5,Lt[1]-1.0,Lt[2]},{1008.5,71.0,-2046.5}};
        std::vector<Query> q0,q8;
        for(auto& p:rcv) {q0.push_back({p,up,up,0.075f,0,false});q8.push_back({p,up,up,0.075f,0.8f,false});}
        for(int context=0;context<2;context++) {
            const std::vector<Block> scene=context?placed:std::vector<Block>{};
            w.build(scene,Es);auto base0=w.evaluate(q0,Es),base8=w.evaluate(q8,Es);
            run(scene,Es,carry(idTorch,14,idSoul,13));
            auto held0=w.evaluate(q0,Es),held8=w.evaluate(q8,Es);
            for(size_t i=0;i<q0.size();i++) for(int c=0;c<3;c++) {
                const double direct=double(held0[i][size_t(c)])-base0[i][size_t(c)],withVanilla=double(held8[i][size_t(c)])-base8[i][size_t(c)];
                require(near(withVanilla,direct,1e-4,1e-6),std::string("vanilla attribution leaked into held light (")+(context?"with placed lamp":"no placed lamp")+", receiver "+std::to_string(i)+" c="+std::to_string(c)+"): +"+num(withVanilla)+" with vanilla 0.8 vs +"+num(direct)+" direct");
                if(context==0&&i==0) require(direct>0||c==0,"held light must light the near receiver");
            }
        }
        // Same through the production terrain pass.
        const std::array<std::array<float,3>,4> grey={{{.5f,.5f,.5f},{.5f,.5f,.5f},{.5f,.5f,.5f},{.5f,.5f,.5f}}};
        const double albedo=std::pow(0.5,2.2);
        w.build({},Es);auto dark8=terrain.draw(w,Es,rcv[0],up,0.8f,0.0f,10001,grey),dark0=terrain.draw(w,Es,rcv[0],up,0.0f,0.0f,10001,grey);
        run({},Es,carry(idTorch,14,idSoul,13));
        auto open8=terrain.draw(w,Es,rcv[0],up,0.8f,0.0f,10001,grey),open0=terrain.draw(w,Es,rcv[0],up,0.0f,0.0f,10001,grey);
        auto direct=w.evaluate({q0[0]},Es)[0];
        for(int c=0;c<3;c++) {
            require(near((open0[0][size_t(c)]-dark0[0][size_t(c)])/albedo,direct[size_t(c)],2e-3,1e-6),"production terrain pass must apply the held lampLighting radiance (c="+std::to_string(c)+")");
            require(near((open8[0][size_t(c)]-dark8[0][size_t(c)])/albedo,direct[size_t(c)],2e-3,1e-6),"production terrain pass with vanilla light 0.8 must add exactly the held direct term (c="+std::to_string(c)+"): "+num((open8[0][size_t(c)]-dark8[0][size_t(c)])/albedo)+" vs "+num(direct[size_t(c)]));
        }
        std::cout<<"PASS carried vanilla attribution: with vanilla block light 0.8 the held records add exactly their direct term (1e-4) with and without a placed lamp; production terrain pass difference "
                 <<(open8[0][0]-dark8[0][0])/albedo<<" == direct "<<direct[0]<<"\n";
    }

    // ------------------------------------------------------------------ H. occlusion of the held light + placed switching
    {
        auto litAt=[&](const std::vector<Block>& scene,const std::vector<Query>& q) {run(scene,Es,torchMain);w.medium=0;return w.evaluate(q,Es);};
        auto wallAt=[&](int x,int ymin,int ymax,int zmin,int zmax,int id=10001) {
            std::vector<Block> v;for(int y=ymin;y<=ymax;y++) for(int z=zmin;z<=zmax;z++) v.push_back(blk(x,y,z,id));return v;
        };
        const Query afar=facingFrom(Lt,3.5,{1,0,0}),afar2=[&]{Query r=facingFrom(Lt,3.5,{1,0,0});r.p[2]+=0.3;return r;}(),anear=facingFrom(Lt,1.0,{1,0,0});
        auto open=litAt({},{afar,afar2,anear});
        require(open[0][0]>0&&open[1][0]>0&&open[2][0]>0,"held light must light the occlusion receivers");
        auto wall=litAt(wallAt(1007,70,72,-2052,-2048),{afar,afar2,anear});
        require(rgbSum(wall[0])==0&&rgbSum(wall[1])==0,"an opaque wall between the held light and the receiver must give exactly zero");
        require(near(wall[2][0],open[2][0],1e-5),"receiver in front of the wall must be unaffected");
        // Partial slab: a bottom slab (y 0..0.5) passes the lamp-height ray and blocks a low ray.
        Query lowRay=facingFrom(Lt,3.0,{1,0,0});lowRay.p[1]=71.05;
        Query highRay=facingFrom(Lt,3.0,{1,0,0});
        auto slabOpen=litAt({},{highRay,lowRay}),slab=litAt({blk(1006,71,-2050,10301)},{highRay,lowRay});
        require(slabOpen[0][0]>0&&slabOpen[1][0]>0,"slab receivers must be lit in the open");
        require(near(slab[0][0],slabOpen[0][0],1e-5),"a ray above a bottom slab must be unaffected");
        require(rgbSum(slab[1])==0,"a ray dipping into a bottom slab must be blocked");
        // Stained glass transmits per channel.
        const struct {int dye;std::array<double,3> t;} glass[]={{14,{.85,.20,.16}},{11,{.19,.36,.86}}};
        auto glassOpen=litAt({},{highRay})[0];
        for(auto& gl:glass) {
            auto s=litAt({blk(1006,71,-2050,10400+gl.dye)},{highRay})[0];
            for(int c=0;c<3;c++) require(near(s[size_t(c)]/glassOpen[size_t(c)],gl.t[size_t(c)],0.02),"held light through stained glass dye "+std::to_string(gl.dye)+" channel "+std::to_string(c)+": "+num(s[size_t(c)]/glassOpen[size_t(c)])+" vs "+num(gl.t[size_t(c)]));
        }
        std::cout<<"PASS carried occlusion: wall blocks the held light exactly (0 behind, "<<wall[2][0]/open[2][0]<<" in front), bottom slab passes the high ray and blocks the low one, red/blue stained glass transmit per channel (+-2%)\n";

        // Placed lamp switched off / removed and held item removed: additive and independent.
        const D3 rc={1007.5,71.0,-2048.5};
        const std::vector<Query> q={{rc,up,up,0.075f,0,false},{{1006.5,71.0,-2049.0},up,up,0.075f,0,false}};
        auto onOff=[&](int level,bool present,const Carried& c)->Rows {
            std::vector<Block> scene;if(present) scene.push_back(torch(1009,71,-2048,level));
            run(scene,Es,c);return w.evaluate(q,Es);
        };
        auto both=onOff(12,true,torchMain),heldOnly=onOff(12,false,torchMain),placedOnly_=onOff(12,true,carry(0,0)),off=onOff(0,true,torchMain),none=onOff(12,false,carry(0,0));
        for(size_t i=0;i<q.size();i++) for(int c=0;c<3;c++) {
            require(near(both[i][size_t(c)],heldOnly[i][size_t(c)]+placedOnly_[i][size_t(c)],1e-4,1e-7),"placed and held light must add (receiver "+std::to_string(i)+")");
            require(near(off[i][size_t(c)],heldOnly[i][size_t(c)],1e-6,1e-8),"switching the placed lamp off must leave exactly the held light");
        }
        require(rgbSum(none[0])==0&&rgbSum(none[1])==0,"removing both lights must leave no ghost");
        require(rgbSum(heldOnly[0])>0&&rgbSum(placedOnly_[0])>0,"both sources must contribute at the receiver");
        std::cout<<"PASS carried placed/held independence: placed torch on/off/removed and held item removed leave the other light exactly intact; both = sum (1e-4); nothing left behind\n";
    }

    // ------------------------------------------------------------------ I. wall / contact clipping around the camera
    {
        const std::array<const char*,3> axisName={"x","y","z"};
        int cases=0;double minClear=1e9;
        for(int a=0;a<3;a++) {
            if(std::abs(o0[size_t(a)])<0.08) continue;
            const int sgn=o0[size_t(a)]>0?1:-1;const int b=(a+1)%3,cc=(a+2)%3;
            const int face=a==0?1010:a==1?72:-2054;
            for(double r:{2.5,1.5,1.0,0.6,0.1}) {
                D3 eye=E0;eye[size_t(a)]=face-sgn*r*std::abs(o0[size_t(a)]);
                const D3 Pexpected=add(eye,o0);
                std::vector<Block> wallScene;
                for(int i=-6;i<=6;i++) for(int j=-6;j<=6;j++) {
                    int p[3];p[a]=sgn>0?face:face-1;p[b]=int(std::floor(Pexpected[size_t(b)]))+i;p[cc]=int(std::floor(Pexpected[size_t(cc)]))+j;
                    wallScene.push_back(stone(p[0],p[1],p[2]));
                }
                Snap s=run(wallScene,eye,torchMain);
                require(s.held.size()==1,"held light vanished with a wall at r="+num(r)+" along "+axisName[size_t(a)]);
                const D3 P=s.held[0].world;
                const double clearance=-sgn*(P[size_t(a)]-face);   // >0: on the player's side of the face
                require(clearance>0,"held light is inside/behind a wall along "+std::string(axisName[size_t(a)])+" (r="+num(r)+"): clearance "+num(clearance));
                minClear=std::min(minClear,clearance);
                // Receivers: near side lit; just behind the 1 m wall exactly dark; same receivers lit without the wall.
                D3 dirB={0,0,0};dirB[size_t(b)]=1;
                D3 n={0,0,0};n[size_t(a)]=-sgn;
                Query nearQ{add(P,dirB),{-dirB[0],-dirB[1],-dirB[2]},up,0.075f,0,false};
                std::vector<Query> far;
                for(double lateral:{0.0,0.3}) {
                    D3 p=P;p[size_t(a)]=face+sgn*1.4;p[size_t(b)]+=lateral;
                    far.push_back(Query{p,n,up,0.075f,0,false});
                }
                std::vector<Query> all=far;all.push_back(nearQ);
                auto res=w.evaluate(all,eye);
                require(rgbSum(res[0])==0&&rgbSum(res[1])==0,"light leaked behind a 1 m wall along "+std::string(axisName[size_t(a)])+" (r="+num(r)+", clearance "+num(clearance)+" m): "+num(res[0][0])+","+num(res[1][0]));
                require(rgbSum(res[2])>0,"near-side receiver must stay lit with a wall along "+std::string(axisName[size_t(a)])+" (r="+num(r)+")");
                Snap freeS=run({},eye,torchMain);
                auto ctrl=w.evaluate(far,eye);
                require(freeS.held.size()==1&&rgbSum(ctrl[0])>0,"negative control: the same far receivers must be lit without the wall (r="+num(r)+")");
                cases++;
            }
        }
        require(cases>=5,"clipping fixture must cover at least one axis");
        std::cout<<"PASS carried wall clipping: "<<cases<<" cases (wall/floor on each hand-offset axis; light 1.5x free to eye 0.1x from the face) keep the light on the player's side (min clearance "<<minClear
                 <<" m), exactly dark behind a 1 m wall at two lateral points, near receiver lit, open control lit\n";
    }

    // ------------------------------------------------------------------ J. third person: follows the player, not the camera
    {
        needUniform("relativeEyePosition","third-person anchoring");needUniform("firstPersonCamera","first/third person switch");needUniform("playerLookVector","third-person orientation");
        const D3 head={1003.25,71.5,-2049.75};
        struct Cam {D3 pos;Rot view;};
        const Cam cams[]={{add(head,{0,0,4}),rotation(0,0)},{add(head,{1.5,1.0,3.25}),rotation(-20,-10)},{add(head,{-3.0,0.5,-2.5}),rotation(180,0)},{add(head,{0,0,-4}),rotation(180,0)}};
        auto third=[&](const D3& eye,const Cam& c,bool right=true,bool mainHand=true) {
            Carried t=mainHand?carry(idTorch,14):carry(0,0,idTorch,14);t.firstPerson=false;t.rightHanded=right;
            t.relEye=sub(add(eye,sub(c.pos,head)),eye);t.viewInverse=c.view.mat4();t.look={0,0,-1};
            D3 camPos=add(eye,sub(c.pos,head));
            Snap s=run({},camPos,t);require(s.held.size()==1,"one third-person light expected");return std::make_pair(s.held[0].world,camPos);
        };
        auto ref=third(head,cams[0]);
        const D3 rel=sub(ref.first,head);
        require(dist(ref.first,head)<1.5,"third-person light must sit within 1.5 m of the player's eye, got "+num(dist(ref.first,head)));
        require(dist(ref.first,ref.second)>2.0,"third-person light must not follow the camera (camera is 4 m away)");
        require(rel[0]>0.05,"third-person main hand of a right-handed player looking -Z must be on +X");
        double worst=0;
        for(auto& c:cams) {auto r=third(head,c);worst=std::max(worst,dist(r.first,ref.first));
            require(dist(r.first,ref.first)<3e-4,"third-person light must stay at the same world point when only the camera moves (camera "+num(c.pos[0])+","+num(c.pos[1])+","+num(c.pos[2])+"): moved "+num(dist(r.first,ref.first))+" m");}
        const D3 step={2.0,0.0,-1.0};double worstMove=0;
        for(auto& c:cams) {
            const D3 head2=add(head,step);
            Carried t=carry(idTorch,14);t.firstPerson=false;t.relEye=sub(c.pos,head);t.viewInverse=c.view.mat4();t.look={0,0,-1};
            Snap s=run({},add(c.pos,step),t);require(s.held.size()==1,"one light expected after the player moves");
            worstMove=std::max(worstMove,dist(sub(s.held[0].world,head2),rel));
            require(dist(sub(s.held[0].world,head2),rel)<3e-4,"third-person light must move with the player ("+num(dist(sub(s.held[0].world,head2),rel))+" m error)");
        }
        // Left-handed / off hand mirror in third person too.
        auto lm=third(head,cams[0],false,true),ro=third(head,cams[0],true,false);
        require(lm.first[0]<head[0]-0.05&&ro.first[0]<head[0]-0.05,"third-person left-handed main and right-handed off hand must be on -X");
        require(std::abs((lm.first[0]-head[0])+(ref.first[0]-head[0]))<2e-4,"third-person hands must be mirrored about the eye");
        std::cout<<"PASS carried third person: same eye, 4 cameras (behind, above-side, in front with 180 deg view) move the light by <"<<worst<<" m; moving player by (2,0,-1) moves it with the player (<"<<worstMove
                 <<" m); light "<<dist(ref.first,head)<<" m from the eye, "<<dist(ref.first,ref.second)<<" m from the camera; hands mirrored\n";
        // Look vector turns the third-person hand with the body.
        Carried t=carry(idTorch,14);t.firstPerson=false;t.relEye={0,0,4};t.look={-1,0,0};   // looking -X: right is -Z... (right = look x up)
        Snap s=run({},add(head,{0,0,4}),t);
        const D3 turned=sub(s.held[0].world,head);
        require(std::abs(turned[2]-(-rel[0]))<3e-4||std::abs(turned[2]-rel[0])<3e-4,"third-person offset must turn with playerLookVector: got z="+num(turned[2])+" for look -X");
        require(dist(turned,rel)>0.1,"third-person offset must change when the player turns");
    }

    // ------------------------------------------------------------------ K. spectator
    {
        needUniform("isSpectator","spectator suppression");
        for(bool first:{true,false}) {
            Carried c=carry(idTorch,14,idSoul,14);c.firstPerson=first;c.relEye=first?D3{0,0,0}:D3{0,0,4};c.spectator=true;
            Snap s=run(placedOne,E0,c);
            require(s.held.empty(),"spectators must not carry a light");
            c.spectator=false;
            require(run(placedOne,E0,c).held.size()==2,"the same inputs must publish both lights when not spectating");
        }
        std::cout<<"PASS carried spectator: isSpectator suppresses both hands in first and third person; unchanged inputs publish both lights otherwise\n";
    }

    // ------------------------------------------------------------------ L. underwater
    {
        const std::string lampSources=expand(root/"shadowcomp1.csh",root)+expand(root/"lib/local_lighting.glsl",root);
        if(!std::regex_search(lampSources,std::regex("isEyeInWater|eyeBrightness|[Uu]nderwater|[Ss]ubmerged"))) {
            std::cout<<"SKIP carried underwater: neither shadowcomp1.csh nor lampLighting reads a medium input (isEyeInWater/eyeBrightness); torch extinction cannot be exercised\n";
        } else {
            const D3 P=Lt;
            auto energy=[&](int id,int medium)->double {
                Carried c=carry(id,14);c.medium=medium;run({},Es,c);
                return rgbSum(lit({facingFrom(P,3.0,{1,0,0})},Es,medium)[0]);
            };
            const double airTorch=energy(idTorch,0),airSoul=energy(idSoul,0),airLantern=energy(idLantern,0);
            require(airTorch>0&&airSoul>0&&airLantern>0,"in-air controls must light the receiver");
            require(energy(idTorch,1)==0,"a held torch must be extinguished underwater (isEyeInWater=1)");
            require(energy(idSoul,1)==0,"a held soul torch must be extinguished underwater");
            const double wetLantern=energy(idLantern,1);
            require(wetLantern>0,"an enclosed lantern keeps burning underwater");
            require(wetLantern<=airLantern*1.0001,"underwater lantern must not exceed its in-air energy");
            require(energy(idTorch,0)==airTorch,"leaving the water must restore the torch exactly");
            std::cout<<"PASS carried underwater: torch and soul torch -> exactly 0 with isEyeInWater=1 (air "<<airTorch<<", "<<airSoul<<"); lantern "<<wetLantern<<" vs air "<<airLantern<<"; air restored exactly\n";
            // Observation only (not asserted): isEyeInWater describes the CAMERA medium, so the hand's own medium is unknown in third person.
            Carried t=carry(idTorch,14);t.medium=1;t.firstPerson=false;t.relEye={0,0,4};
            Snap tp=run({},add(Es,{0,0,4}),t);
            std::cout<<"INFO carried underwater third person (camera submerged, isEyeInWater=1): "<<tp.held.size()<<" held torch record(s) published; the pack has no hand-medium input there\n";
        }
    }

    // ------------------------------------------------------------------ M. timing (GPU harness only)
    {
        std::vector<Block> scene;uint32_t seed=7;
        const D3 base={std::floor(E0[0]/8)*8,std::floor(E0[1]/8)*8,std::floor(E0[2]/8)*8};
        for(int i=0;i<256;i++) {seed=seed*1664525u+1013904223u;int gx=16+(seed>>8)%32,gy=24+(seed>>16)%16;seed=seed*1664525u+1013904223u;int gz=16+(seed>>8)%32;
            scene.push_back(blk(gx+int(base[0])-32,gy+int(base[1])-32,gz+int(base[2])-32,10100,8+int(seed>>20)%7));}
        auto median=[&](const Carried& c) {
            run(scene,E0,c);std::vector<double> ms;for(int i=0;i<30;i++) {w.publish(true,&c);ms.push_back(w.lastComputeMs);}
            std::sort(ms.begin(),ms.end());return ms[15];
        };
        const double none=median(Carried{}),dual=median(carry(idTorch,14,idSoul,14));
        std::cout<<"INFO carried shadowcomp1 GPU time over 30 dispatches (256 dense lamps): no held "<<none<<" ms, two held "<<dual<<" ms on "<<w.renderer
                 <<" -- GPU harness timing of one compute pass only, NOT a Minecraft frame time\n";
    }
    w.build({},E0);   // leave the shared World with carried uniforms restored to "nothing held"
    std::cout<<"PASS carried-light QA complete on "<<w.renderer<<": real shadowcomp1 dispatch driven only by production uniforms; no mock results. Not a Minecraft FPS or visual acceptance.\n";
}
}  // namespace aqualumenLocalLights
