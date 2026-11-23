"""Track the same receiver after the source, tree, camera and animal change."""
from score import *
from grove import STAGES

def main():
    meter=HERE/"grove-hull-meter";normal=HERE/"grove-release"
    maps={}; rgb={}; report={}
    for stage in STAGES:
        path=meter/(stage+"-ingame.png");check_record(meter,path)
        lamps,pos,axis=unpack(path,1)
        vis=lamps[:,:,0]
        body=(vis[:,:,2]&8)!=0
        assert not (body&(vis[:,:,2]%4==2)).any()
        maps[stage]=(vis,pos)
        path=normal/(stage+"-ingame.png");check_record(normal,path)
        rgb[stage]=np.array(Image.open(path).convert("RGB"))[:-5,::8]@WEIGHTS
        report[stage]=dict(calls=int((vis[:,:,2]>=64).sum()),body=int(body.sum()),maxOnBody=int(vis[:,:,1][body].max(initial=0)))
    for stage in ("shade","extinguished"): assert report[stage]["calls"]==0
    assert report["walk"]["body"]>1000
    vis,p=maps["torch"]
    face=face_from_geometry(p,np.array([409.48,152.62,-405.95]))
    x,y,z=np.moveaxis(p,-1,0);trunk,q=maps["trunk"];home,h=maps["home"];cut,c=maps["trunk-cut"]
    samePos=(np.max(abs(p-q),axis=2)<.001)&(np.max(abs(p-h),axis=2)<.001)&(np.max(abs(p-c),axis=2)<.001)
    sameCall=samePos&(vis[:,:,2]>=64)&(trunk[:,:,2]>=64)&(home[:,:,2]>=64)&(cut[:,:,2]>=64)
    surfaces={"floor":(face==4)&(abs(y-151)<.006)&(x>404)&(x<410)&(z> -412)&(z< -405),
              "wall":(face==6)&(abs(z+412)<.006)&(x>404)&(x<410)&(y>151)&(y<155)}
    for name,faceMask in surfaces.items():
        watched=faceMask&sameCall
        umbra=watched&(vis[:,:,1]==255)&(trunk[:,:,1]==0)&(home[:,:,1]==0)&(cut[:,:,1]==255)
        assert umbra.sum()>100
        litDelta=(rgb["torch"]-rgb["shade"])[watched]
        oldDelta=(rgb["extinguished"]-rgb["shade"])[watched]
        report[name]=dict(matched=int(watched.sum()),umbraRestored=int(umbra.sum()),medianTorchLift=float(np.median(litDelta)),
                          afterRemovalMedianAbsDisplayDelta=float(np.median(abs(oldDelta))),
                          afterRemovalP95AbsDisplayDelta=float(np.quantile(abs(oldDelta),.95)))
    text=(meter/"client.log").read_text()
    import re
    matches=re.findall(r"\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)",text)
    points=np.array(matches,dtype=float)/1000.
    assert len(points)>3
    report["cowPositions"]=len(points)
    report["cowDisplacementMetres"]=float(np.linalg.norm(points[-1]-points[0]))
    (HERE/"room-edits.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__": main()
