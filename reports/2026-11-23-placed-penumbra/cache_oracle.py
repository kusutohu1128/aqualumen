"""Exercise the earlier cache transition fixture with an independent box reference."""
from pathlib import Path
import subprocess
from zipfile import ZipFile
from pack import HERE, ROOT, NAME, WORK, replace


ORACLE=r"""
                bool canBox=d2<=14.1f*14.1f && l.kind>=1 && l.kind<=10;
                Point first=hi,last=lo;
                int count=0;
                for(int a=0;a<3;a++) canBox&=lo[a]>=origin[a] && hi[a]<origin[a]+64;
                for(auto b:blocks) {
                    bool inside=true;
                    for(int a=0;a<3;a++) inside&=b.world[a]>=lo[a] && b.world[a]<=hi[a];
                    if(!inside) continue;
                    count++;
                    canBox&=!b.partial && b.world!=l.world;
                    for(int a=0;a<3;a++) {
                        first[a]=std::min(first[a],b.world[a]);
                        last[a]=std::max(last[a],b.world[a]);
                    }
                }
                int volume=1,word=0;
                for(int a=0;a<3;a++) {
                    volume*=last[a]-first[a]+1;
                    if(count>0) word+=((first[a]-lo[a])+16*(last[a]-lo[a]))*(1<<(8*a));
                }
                canBox&=count && volume==count;
                if(canBox!=bool(mask&(1<<(12+i)))) throw std::runtime_error(std::string(name)+" wrong cuboid flag");
                if(canBox) {
                    boxes++;
                    int address=(2720+i*512)*512+linear(ring(world,63),64);
                    if(result[address]!=float(1+word)) throw std::runtime_error(std::string(name)+" wrong cuboid bounds");
                }
"""

def prepare():
    fixture=HERE.parent/"2026-11-23-torch-open-volume/cache_probe.cpp"
    s=fixture.read_text().replace('"../../tools/glcheck.cpp"',f'"{ROOT}/tools/glcheck.cpp"')
    s=replace(s,"image(0,1,512,2720)","image(0,1,512,8864)")
    s=replace(s,"result(512*2720)","result(512*8864)")
    s=replace(s,"int active=0,hits=0,reused=0;","int active=0,hits=0,reused=0,boxes=0;")
    s=replace(s,"                active++;",ORACLE+"                active++;")
    s=replace(s,'<<hits<<" "<<reused','<<hits<<" "<<reused<<" "<<boxes')
    p='    blocks.back().partial=true;frame("opaque-to-glass");'
    s=replace(s,p,p+"""
    blocks.back().partial=false;
    blocks.push_back({{-18,65,0},false});frame("stacked-logs");
    blocks.push_back({{-18,65,1},false});frame("concave-corner");
    blocks.push_back({{-18,64,1},false});frame("filled-rectangle");
    blocks.push_back({lights[0].world,false});frame("terminal-voxel");
    for(int j=0;j<4;j++) blocks.pop_back();""")
    cpp=WORK/"cache_oracle.cpp"
    cpp.write_text(s)
    with ZipFile(WORK/NAME) as src:
        src.extractall(WORK/"normal")
    subprocess.run(["c++","-std=c++17","-O2",str(cpp),"-o",str(WORK/"cache-oracle"),"-lepoxy","-lEGL"],check=True)

if __name__=="__main__":
    prepare()
