"""Quantify actual lit pixels while the second ground block and cow enter and leave."""
import json
import re
import sys
from grid import HERE
from score import (ROOM_ANCHOR,ROOM_SOURCE,check_record,face_from_geometry,integral,moments,np,unpack)


def score(folder):
    receipt=json.loads((folder/"complete.json").read_text())
    geometry=json.loads((folder/"geometry.json").read_text())
    poses={};stats={}
    for stage in receipt["stages"]:
        path=folder/(stage+"-ingame.png")
        check_record(folder,path)
        texture,p,_=unpack(path,1)
        light=texture[:,:,0];poses[stage]=(p,light)
        if stage in ("near-cow","walk","extinguished"):continue
        face=face_from_geometry(p,np.array([409.48,152.62,-405.95]))
        x,y,z=np.moveaxis(p,-1,0)
        wall=(face==6)&(abs(z+412)<.006)&(x>404)&(x<410)&(y>151)&(y<155)
        floor=(face==4)&(abs(y-151)<.006)&(x>404)&(x<410)&(z>-412)&(z< -405)
        valid=(wall|floor)&(light[:,:,2]>=64)&((light[:,:,2]&12)==0)
        grid=np.zeros((64,64,64),np.uint8)
        tree=[(406,151,-410),(406,152,-410)] if stage in geometry["trunkPresent"] else []
        def ray(cells):
            grid.fill(0)
            for pos in cells:grid[tuple(np.array(pos)-ROOM_ANCHOR)]=1
            return integral(p,face,valid,ROOM_SOURCE[0],ROOM_ANCHOR,grid)
        body=ray(tree)
        step=geometry["singleStep"][stage]
        blocks=[geometry["steps"][step]] if step else []
        total=ray(tree+blocks)
        soil=ray(blocks)
        partial=(total>.005)&(total<.995)
        union=partial&(np.minimum(body,soil)-total>.01)
        pair=light[:,:,2]%4==3
        row={}
        for description,use in (("partial",partial),("wall",partial&wall),("floor",partial&floor),
                                ("darkerThanEither",union),("pairDarkerThanEither",union&pair)):
            row[description]=[moments(abs(light[:,:,i]/255.-total)[use]) for i in (0,1)]
        stats[stage]=row

    def compare(first,second,scope):
        p,a=poses[first];q,b=poses[second]
        valid=(np.max(abs(p-q),axis=2)<.001)&(a[:,:,2]>=64)&(b[:,:,2]>=64)&scope
        return moments(abs(b[:,:,1].astype(int)-a[:,:,1].astype(int))[valid]/255.)
    p,trunk=poses["trunk"]
    stats["restoration"]=compare("trunk","cut-step",(trunk[:,:,1]>0)&(trunk[:,:,1]<255))
    p,l=poses["touching"]
    # This segment from the torch to the eastern back wall lies wholly
    # opposite the western cow. Match only geometry and active broad tests.
    far=(p[:,:,0]>409)&(abs(p[:,:,2]+412)<.006)&(p[:,:,1]>151)&(p[:,:,1]<155)
    far&=(l[:,:,1]>2)&(l[:,:,1]<253)&((poses["walk"][1][:,:,2]&8)!=0)
    stats["farCowDifference"]=compare("touching","walk",far)
    stats["afterCowDifference"]=compare("touching","walk-cleared",far)
    p,near=poses["near-cow"]
    same=np.max(abs(poses["touching"][0]-p),axis=2)<.001
    withCow=same&(l[:,:,1]>2)&(l[:,:,1]<253)&((near[:,:,2]&8)!=0)
    darkened=withCow&(l[:,:,1].astype(int)-near[:,:,1].astype(int)>2)
    stats["cowDarkenedPartial"]=int(darkened.sum())
    stats["restoredWhereCowCastShadow"]=compare("touching","walk-cleared",darkened)
    xy=re.findall(r"\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)",(folder/"client.log").read_text())
    pos=np.array(xy,dtype=float)/1000.
    assert len(pos)>3
    stats["cowTravelMetres"]=float(np.linalg.norm(pos[-1]-pos[0]))
    return stats

if __name__=="__main__":
    folder=HERE/sys.argv[1]
    (HERE/(folder.name+"-score.json")).write_text(json.dumps(score(folder),indent=2)+"\n")
