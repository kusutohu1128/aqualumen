"""Read adjacent horizontal pixels at every x for the three missing edge orientations."""
import sys
from pack import HERE,ROOT,WORK,build,replace
from single_block import CUBES,Field,screen,guarded
STAGES=["north-east","east","south-east"]
NAME="Aqualumen-Placed-Torch-Horizontal-Edges.zip"
def across(name,s):
    s=screen(name,s)
    if name=="shaders/final.fsh":
        s=replace(s,"int group=px.x/12,side=(px.x%12)/6,lane=px.x%6;","int group=px.y/12,side=(px.y%12)/6,lane=px.y%6;")
        s=replace(s,"ivec2 q=ivec2(12*group+side,px.y);","ivec2 q=ivec2(px.x,12*group+side);")
    return s
class Rows(Field):
    def self_test(self,names):assert names==STAGES
if __name__=="__main__":
    if sys.argv[1]=="build":print(build(WORK/NAME,across));raise SystemExit()
    assert guarded.sha(WORK/NAME)==sys.argv[1]
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(WORK/NAME,"one-block-horizontal","off",fixed,HERE,Rows)
