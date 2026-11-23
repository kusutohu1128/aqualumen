"""Track one patch on the front stone face from the reference half of a lossless game recording."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

from curves import HERE,LUMA

WOOD=HERE.parent/"2026-11-21-animal-light/woodland"
RECT=(95,168,235,264)
W,H=1600,450


def positions(old,template,source):
    # x=596 is the outer edge of this stone plane at z=426. Project its
    # initial position at the middle of the sampled rows with the saved FOV.
    # Once visible against the dark trees, this edge distinguishes repeated
    # copies of the stone texture even when the game skips a rendered frame.
    x,y,right,bottom=RECT
    row=(y+bottom)//2
    focal=225./np.tan(np.deg2rad(35.))
    pitch=np.deg2rad(3.9)
    depth=(427.502-426.)/(np.cos(pitch)+np.sin(pitch)*(225.-row)/focal)
    initialEdge=400.+(596.-598.433)*focal/depth
    sample=source[row-12:row+13].astype(int)
    red,green=sample[:,:,0],sample[:,:,1]
    warm=(red>105)&(green>.68*red)&(green<.80*red)
    edge=int(np.argmax(np.convolve((np.mean(warm,axis=0)>.70).astype(int),np.ones(12,int),"valid")==12))
    if edge<3:
        lo,hi=x-4,min(800-(right-x),int(x-initialEdge+15))
    else:
        estimate=x+edge-initialEdge
        lo,hi=max(0,int(estimate)-20),min(800-(right-x),int(estimate)+20)
    rows=np.arange(y,bottom,7)
    grid=np.arange(right-x)[None,None,:]+np.arange(lo,hi+1)[None,:,None]
    slope=-np.sin(pitch)/(focal*np.cos(pitch)+(225.-row)*np.sin(pitch))
    coords=grid+(rows-row)[:,None,None]*slope*(np.arange(lo,hi+1)-x)[None,:,None]
    x0=np.clip(np.floor(coords).astype(int),0,798)
    f=np.clip(coords-x0,0.,1.)
    strips=old[rows[:,None,None],x0]*(1-f)+old[rows[:,None,None],x0+1]*f
    strips-=strips.mean(axis=-1,keepdims=True)
    corr=np.mean((strips*template[:,None,:]).mean(axis=-1)/np.maximum(np.sqrt((strips*strips).mean(axis=-1)),.001),axis=0)
    best=int(np.argmax(corr))
    return lo+best,float(corr[best]),slope



def main(balanced):
    run=WOOD/("midtones-display-sidestep" if balanced else "diffuse-display-sidestep")
    record=json.loads((run/"complete.json").read_text())
    assert record["results"]["completed"]==["paired-sidestep-along-the-niche"] and not record["results"].get("failed")
    assert record["cleanExit"] and record["previousSaveUnchanged"] and record["labFilesUnchanged"] and not record["logErrors"]
    assert record["walkedAfterReloadMetres"]>3. and abs(record["results"]["sidestep"]["heading"][0])==180.
    movie=run/"paired-motion.mkv"
    proc=subprocess.Popen(["ffmpeg","-v","error","-threads","2","-i",str(movie),"-f","rawvideo","-pix_fmt","rgb24","pipe:1"],stdout=subprocess.PIPE)
    x,y,right,bottom=RECT
    track=[]
    changes={"moving":[],"holding":[]}
    previous=None
    last=x
    for frame in iter(lambda:proc.stdout.read(W*H*3),b""):
        assert len(frame)==W*H*3
        raw=np.frombuffer(frame,np.uint8).reshape(H,W,3)
        bright=raw[:,:800,1].astype(float)
        # Suppress the broad carried-light gradient when matching the stone pattern.
        bright=np.roll(bright,-3,axis=1)-np.roll(bright,3,axis=1)
        if not track:
            template=bright[y:bottom:7,x:right].copy()
            template-=template.mean(axis=-1,keepdims=True)
            template/=np.sqrt((template*template).mean(axis=-1,keepdims=True))
        pos,corr,slope=positions(bright,template,raw[:,:800])
        track.append([pos,round(corr,5)])
        rows=np.arange(y,bottom)
        coords=pos+np.arange(right-x)[None,:]+(rows-(y+bottom)//2)[:,None]*slope*(pos-x)
        xi=np.floor(coords).astype(int)
        frac=coords-xi
        crop=np.stack([(raw[rows[:,None],xi+d]@LUMA)*(1-frac)+(raw[rows[:,None],xi+d+1]@LUMA)*frac for d in (0,800)])
        if previous is not None:
            if abs(pos-last)>1:
                mode="moving"
            else:
                mode="holding"
            changes[mode].append(np.abs(crop-previous).reshape(2,-1))
        previous=crop
        last=pos
    assert proc.wait()==0
    xx=np.array(track)
    assert len(xx)>=100 and xx[:,0].max()-x>300 and abs(xx[-1,0]-x)<8 and xx[:,1].min()>.75, (len(xx),xx.min(axis=0),xx.max(axis=0),xx[-1])
    groups={}
    for group,frames in changes.items():
        samples=np.concatenate(frames,axis=1)
        groups[group]=dict(transitions=len(frames),statistics="absolute display code luma difference at tracked points between video frames",
            mean=samples.mean(axis=1).tolist(), p95=np.quantile(samples,.95,axis=1).tolist(), p99=np.quantile(samples,.99,axis=1).tolist(),
            aboveFourCodes=(samples>4.).mean(axis=1).tolist())
    data=dict(videoSha256=hashlib.sha256(movie.read_bytes()).hexdigest(),rect=RECT,frames=len(xx),fps=24,walkedMetres=record["walkedAfterReloadMetres"],
              pairs=["Rows","Diffuse Display"],positionAndCorrelation=track,groups=groups,
              limits="Integer registration on the reference half. Residual includes resampling and real lighting changes. Frame capture can duplicate game frames.")
    (HERE/("default-motion.json" if balanced else "motion.json")).write_text(json.dumps(data,indent=2)+"\n")
    print(groups)

if __name__=="__main__":
    main("--balanced" in sys.argv)
