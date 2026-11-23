"""Check uploaded tight-hull certificates against an independent double interval test."""
import subprocess
from zipfile import ZipFile
from pack import WORK,replace
from swept import NORMAL,METER

REFERENCE=r"""
                if(!canBox && d2<=14.1f*14.1f && l.kind>=1 && l.kind<=10) {
                    canBox=true; count=0;first=hi;last=lo;word=0;
                    for(int a=0;a<3;a++) canBox&=lo[a]>=origin[a] && hi[a]<origin[a]+64;
                    for(auto b:blocks) {
                        bool inside=true;
                        for(int a=0;a<3;a++) inside&=b.world[a]>=lo[a] && b.world[a]<=hi[a];
                        if(!inside) continue;
                        double tMin=0.,tMax=1.;
                        for(int a=0;a<3;a++) {
                            // Separate the two endpoint boxes from the voxel's lower
                            // and upper planes, then intersect their admissible times.
                            double margins[2][2]={
                                {world[a]+1.0001-b.world[a],e[a]+.1302-b.world[a]},
                                {b.world[a]+1.0001-world[a],b.world[a]+1.1302-e[a]}};
                            for(auto &m:margins) {
                                if(m[0]<0 && m[1]<0) inside=false;
                                if(m[0]<0 && m[1]>=0) tMin=std::max(tMin,m[0]/(m[0]-m[1]));
                                if(m[0]>=0 && m[1]<0) tMax=std::min(tMax,m[0]/(m[0]-m[1]));
                            }
                        }
                        if(!inside || tMin>tMax+.00001) continue;
                        count++;
                        canBox&=!b.partial && b.world!=l.world;
                        for(int a=0;a<3;a++) {
                            first[a]=std::min(first[a],b.world[a]);
                            last[a]=std::max(last[a],b.world[a]);
                        }
                    }
                    volume=1;
                    for(int a=0;a<3;a++) {
                        volume*=last[a]-first[a]+1;
                        if(count>0) word+=((first[a]-lo[a])+16*(last[a]-lo[a]))*(1<<(8*a));
                    }
                    canBox&=count && volume==count;
                }
"""
def prepare():
    cpp=WORK/"hull_reference.cpp"
    s=(WORK/"cache_oracle.cpp").read_text()
    insert="                if(canBox!=bool(mask"
    s=replace(s,insert,REFERENCE+insert)
    # Verify the actual off-axis geometry that caused the original forest seam.
    before='    return 0;\n} catch'
    s=replace(s,before,'''    camera={208,65,355}; lights={{{210,64,359},1}};
    blocks={{{209,64,360},false},{{209,64,361},false},{{210,64,361},false}};frame("natural-birch-edge");
    blocks.back().partial=true;frame("outside-cone-material-edit");
    blocks.push_back({{208,64,360},true});frame("leaf-in-cone");
'''+before)
    cpp.write_text(s)
    for folder,pack in (("hull",NORMAL),("hull-meter",METER)):
        with ZipFile(WORK/pack) as archive: archive.extractall(WORK/folder)
    subprocess.run(["c++","-std=c++17","-O2",str(cpp),"-o",str(WORK/"hull-oracle"),"-lepoxy","-lEGL"],check=True)
if __name__=="__main__":
    prepare()
