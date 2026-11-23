"""Compare the cached and traced lamp on a changing grove and a moving animal."""
import hashlib
import json
import re
import subprocess
import numpy as np
from window_room import HERE
from score import reader

def extract(lanes,p):
    x,y,z=np.moveaxis(p,-1,0)
    live=lanes[:,:,2,0]==1
    wall=live&(abs(z+412)<.0005)&(x>404.04)&(x<409.96)&(y>151.04)&(y<154.96)
    floor=live&(abs(y-151)<.0005)&(x>404.04)&(x<409.96)&(z> -411.96)&(z< -405.04)
    return wall,floor

def stats(lanes,mask):
    a,b=lanes[:,:,0][mask],lanes[:,:,1][mask]
    diff=abs(a.astype(int)-b).max(axis=1)
    return dict(points=int(mask.sum()), fast=int((lanes[:,:,3,0][mask]==1).sum()),
                maximumBytes=int(diff.max(initial=0)), differences=int((diff>0).sum()), beyondOne=int((diff>1).sum()))

def video(movie):
    seen=set();frames=0;uncalibrated=[];coverage=[];wall_luma=[]
    summed=dict(samples=0,cached=0,changed=0,changedOverOne=0,maxBytes=0)
    prior=None;prior_mask=None;prior_pos=None
    ff=subprocess.Popen(["ffmpeg","-v","error","-threads","2","-i",movie,"-pix_fmt","rgb24","-f","rawvideo","-threads","1","pipe:1"],stdout=subprocess.PIPE)
    while True:
        raw=ff.stdout.read(1280*720*3)
        if not raw:break
        assert len(raw)==1280*720*3
        a=np.frombuffer(raw,np.uint8).reshape(720,1280,3);frames+=1
        lanes=a[:-5].reshape(715,160,8,3)
        if (not np.array_equal(a[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
                or not (lanes[:,:,7,1]==183).all() or not (lanes[:,:,7,2]==1).all()):
            uncalibrated.append(frames-1)
            prior=prior_mask=prior_pos=None
            continue
        pos=(lanes[:,:,4:7].astype(np.int32)@np.array([1,256,65536]))/65536.+reader.ROOM_ANCHOR
        w,f=extract(lanes,pos);mask=w|f
        coverage.append(int(mask.sum()))
        wall_luma.append(float(lanes[:,:,0,0][w].mean()) if w.any() else None)
        key=hashlib.blake2s(lanes[:,:,0:2][mask].tobytes()+mask.tobytes()).digest()
        if key in seen:continue
        seen.add(key)
        rgb=lanes[:,:,0].astype(np.int16)
        delta=abs(rgb-lanes[:,:,1]).max(2)
        summed["samples"]+=int(mask.sum());summed["cached"]+=int((mask&(lanes[:,:,3,0]==1)).sum())
        summed["maxBytes"]=max(summed["maxBytes"],int(delta[mask].max(initial=0)))
        if prior is not None:
            active=mask&prior_mask&(pos==prior_pos).all(2)&(abs(rgb-prior).max(2)>6)
            summed["changed"]+=int(active.sum());summed["changedOverOne"]+=int((active&(delta>1)).sum())
        prior,prior_mask,prior_pos=rgb,mask,pos
    assert ff.wait()==0
    assert len(coverage)>10,(movie,frames,uncalibrated)
    return dict(frames=frames,uncalibratedFrameIndices=uncalibrated,distinctFields=len(seen),moving=summed,firstValidReceivers=coverage[0],
                lastValidReceivers=coverage[-1],minValidReceivers=min(coverage),maxValidReceivers=max(coverage),
                firstWallRed=wall_luma[0],lastWallRed=wall_luma[-1],
                sha256=hashlib.sha256(movie.read_bytes()).hexdigest())

def analyze():
    folder=HERE/"grove-edits"
    record=json.loads((folder/"complete.json").read_text())
    rows={};samples={}
    for s in record["stages"]:
        photo=folder/(s+"-ingame.png")
        reader.check_record(folder,photo)
        l,p,_=reader.unpack(photo,1);w,f=extract(l,p)
        rows[s]=dict(wall=stats(l,w),grass=stats(l,f));samples[s]=(l,p,w,f)
    for s in ("shade","extinguished"):
        assert rows[s]["grass"]["points"]==rows[s]["wall"]["points"]==0
    response={}
    for index,name in ((2,"wall"),(3,"grass")):
        l,p,*_=samples["torch"]
        t,q,*_=samples["trunk"]
        c,r,*_=samples["trunk-cut"]
        same=samples["torch"][index]&samples["trunk"][index]&samples["trunk-cut"][index]&(p==q).all(2)&(p==r).all(2)
        # Red remains the strongest channel of this pane. A ray hidden by the
        # birch trunk goes dark across all three channels.
        lit=l[:,:,0,0]>180
        shadow=same&lit&(t[:,:,0,0]<32)
        response[name]=dict(paired=int(same.sum()),unobstructed=int((same&lit).sum()),trunkShadow=int(shadow.sum()),
                            recoveredAfterCut=int((shadow&(c[:,:,0,0]>180)).sum()))
    positions=re.findall(r'\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)',(folder/"client.log").read_text())
    track=np.asarray(positions,dtype=float)/1000
    assert len(track)>10
    clips={s:video(folder/(s+".mkv")) for s in ("cow-motion","lighting","planting-trunk","cutting-trunk","extinguishing")}
    result=dict(stages=rows,edits=response,clips=clips,
                cowMeasuredMetres=float(np.linalg.norm(np.diff(track,axis=0),axis=1).sum()),cowPositionCount=len(track))
    (HERE/"grove.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="stages"}))
if __name__=="__main__":analyze()
