"""Check cached two-box descriptors against sets of world voxels after geometry edits."""
import subprocess
from zipfile import ZipFile
from grid import HERE,PRIOR,ROOT,WORK
from build_trial import change


def prepare():
    # Reuse the preceding lifecycle fixture and independent double swept-box oracle.
    from hull_oracle import REFERENCE
    from cache_oracle import ORACLE
    fixture=(HERE.parent/"2026-11-23-torch-open-volume/cache_probe.cpp").read_text()
    fixture=fixture.replace("../../tools/glcheck.cpp",str(ROOT/"tools/glcheck.cpp"))
    fixture=change(fixture,"int active=0,hits=0,reused=0;","int active=0,hits=0,reused=0,boxes=0,pairs=0;")
    code=change(ORACLE,"                if(canBox!=bool(mask",REFERENCE+"                if(canBox!=bool(mask")
    code=change(code,"                bool canBox=","                std::set<Point> expected;bool two=false;\n                bool canBox=")
    code=change(code,"if(!inside || tMin>tMax+.00001) continue;","if(!inside || tMin>tMax+.00001) continue;\n                        expected.insert(b.world);")
    trigger="                    canBox&=count && volume==count;"
    code=change(code,trigger,"""                    if(canBox && count>1 && count<=12 && volume!=count) {
                        // Enumerate all boxes with both opposite corners occupied.
                        // The remaining points must fill a second disjoint box.
                        for(auto low:expected) for(auto high:expected) {
                            int v=1;
                            for(int a=0;a<3;a++) v*=std::max(0,high[a]-low[a]+1);
                            if(!v || v>=count) continue;
                            int n=0; Point rLo=last,rHi=first;
                            for(auto p:expected) {
                                bool in=true;for(int a=0;a<3;a++) in&=p[a]>=low[a] && p[a]<=high[a];
                                if(in) n++;
                                else for(int a=0;a<3;a++) { rLo[a]=std::min(rLo[a],p[a]);rHi[a]=std::max(rHi[a],p[a]); }
                            }
                            int rem=1;for(int a=0;a<3;a++) rem*=rHi[a]-rLo[a]+1;
                            if(n==v && rem==count-n) two=true;
                        }
                    }
                    canBox&=count && (volume==count || two);""")
    code=change(code,"                    if(result[address]!=float(1+word))", """                    if(two) {
                        if(result[address]>=0.) throw std::runtime_error(std::string(name)+" missing second box");
                        std::set<Point> decoded;
                        for(int rec:{int(-result[address]),int(result[address+6144*512])}) {
                            if(rec<=0 || rec>16777216) throw std::runtime_error("bad box payload");
                            int key=rec-1;Point a{},b{};
                            for(int k=0;k<3;k++) {
                                int byte=(key>>(k*8))&255;
                                a[k]=lo[k]+(byte&15);b[k]=lo[k]+(byte>>4);
                                if(b[k]<a[k]) throw std::runtime_error("reversed bounds");
                            }
                            for(int x=a[0];x<=b[0];x++) for(int y=a[1];y<=b[1];y++) for(int z=a[2];z<=b[2];z++)
                                if(!decoded.insert({x,y,z}).second) throw std::runtime_error("overlapping voxels");
                        }
                        if(decoded!=expected) throw std::runtime_error(std::string(name)+" wrong voxel union");
                        pairs++;
                    } else if(result[address]!=float(1+word))""")
    fixture=change(fixture,"                active++;",code+"                active++;")
    fixture=change(fixture,'<<hits<<" "<<reused','<<hits<<" "<<reused<<" "<<boxes<<" "<<pairs')
    fixture=fixture.replace("512,2720","512,15008").replace("512*2720","512*15008")
    before='    return 0;\n} catch'
    fixture=change(fixture,before,'''    camera={208,65,355}; lights={{{208,64,360},1}};
    blocks={{{209,64,360},false},{{209,65,360},false},{{209,66,360},false},{{209,64,361},false}};
    frame("trunk-and-grass");frame("unchanged-step");
    blocks.back().world[0]++;frame("disconnected-step");
    blocks.back().partial=true;frame("step-to-leaves");
    blocks.pop_back();frame("cut-step");
    blocks.push_back({{209,64,361},false});frame("step-returned");
    for(int z=1;z<=5;z++)for(int y=0;y<3;y++) blocks.push_back({{208,64+y,361+z},false});
    frame("many-occluders");
    blocks.clear();frame("clear-all");
'''+before)
    with ZipFile(WORK/"Aqualumen-Two-Opaque-Shadows.zip") as z:z.extractall(WORK/"trial")
    source=WORK/"cache_check.cpp"
    source.write_text("#include <set>\n"+fixture)
    subprocess.run(["c++","-O2","-std=c++17",str(source),"-o",str(WORK/"cache-check"),"-lepoxy","-lEGL"],check=True)

if __name__=="__main__":prepare()
