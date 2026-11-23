"""Track image features during the straight entry beneath the overhang."""
from hashlib import sha256
import json
import subprocess
import sys

import cv2
import numpy as np

from room import HERE
from measure import TRIAL_SHA
from release import SHA as RELEASE_SHA

WOOD=HERE.parent/"2026-11-21-animal-light/woodland"


def track(a,b,points):
    options=dict(winSize=(21,21),maxLevel=3,
                 criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,25,.02))
    moved,ok,_=cv2.calcOpticalFlowPyrLK(a,b,points,None,**options)
    back,reverse,_=cv2.calcOpticalFlowPyrLK(b,a,moved,None,**options)
    p=points[:,0];q=moved[:,0]
    valid=ok[:,0].astype(bool)&reverse[:,0].astype(bool)&(np.linalg.norm(p-back[:,0],axis=1)<.6)
    valid&=(q[:,0]>=12)&(q[:,1]>=12)&(q[:,0]<788)&(q[:,1]<438)
    return q,valid


def values(im,points):
    # Bilinear samples of the same 5x5 display-pixel aperture in each frame.
    offsets=np.arange(-2,3,dtype='float32')
    xx,yy=np.meshgrid(offsets,offsets)
    return cv2.remap(im,points[:,0,None]+xx.ravel(),points[:,1,None]+yy.ravel(),
                     cv2.INTER_LINEAR).astype(float)


def correlation(p,q):
    p=p-p.mean(axis=1,keepdims=True)
    q=q-q.mean(axis=1,keepdims=True)
    return (p*q).sum(axis=1)/np.maximum(1.,np.linalg.norm(p,axis=1)*np.linalg.norm(q,axis=1))


def analyze(run):
    r=json.loads((run/"complete.json").read_text())
    rainy=(run/"frozen-sky.json").exists()
    replay={"camp-rain-reference":RELEASE_SHA,"camp-rain-wet-plane":"8df2a8fcd645d58f0423d8b9974f99a186022d345c44a2ef9404b05a9c6a52c2"}
    if run.name in replay:
        assert rainy and r["packSha256"]==replay[run.name] and r["revisit"]["sourceRun"]=="lake-to-stone-camp"
    else:
        assert r["packSha256"]==(TRIAL_SHA if rainy else RELEASE_SHA)
    assert r["cleanExit"] and not r["logErrors"] and r["labFilesUnchanged"] and r["previousSaveUnchanged"]
    assert r["results"]["completed"]==["cross-the-lit-camp" if run.name in replay else "light-the-stone-overhang"]
    poses=r["results"]["crossing"]
    start,end=[poses[k] for k in ("before","after")]
    assert end["xyz"][0]-start["xyz"][0]>4.5 and abs(end["xyz"][2]-start["xyz"][2])<.2
    assert start["xyz"][1]==end["xyz"][1]==71.
    movie=run/"under-stone.mkv"
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_packets","-show_entries","packet=pts_time:format=duration","-of","json",str(movie)]))
    times=[float(row["pts_time"]) for row in probe["packets"]]
    assert abs(float(probe["format"]["duration"])-4)<.04 and times[0]==0 and times[-1]>3.9
    assert all(b>a for a,b in zip(times,times[1:]))
    camera=cv2.VideoCapture(str(movie))
    assert camera.isOpened() and camera.get(cv2.CAP_PROP_FPS)==30
    # Camera-only movement aims horizontally along +X with measured downward pitch.
    horizon=224.5-225./np.tan(np.radians(35))*np.tan(np.radians(start["angle"][1]))
    focus=np.array([399.5,horizon])
    unique=[];indices=[];fingerprints=[];i=0
    while True:
        ok,bgr=camera.read()
        if not ok:break
        reduced=cv2.resize(bgr,(800,450),interpolation=cv2.INTER_AREA)
        lum=cv2.transform(reduced,np.array([[.0722,.7152,.2126]],dtype='float32'))
        fingerprint=sha256(lum.tobytes()).digest()
        if not fingerprints or fingerprints[-1]!=fingerprint:
            unique.append(lum);indices.append(i);fingerprints.append(fingerprint)
        i+=1
    camera.release()
    assert i==len(times) and len(unique)>10
    mask=np.zeros((450,800),dtype='uint8')
    mask[75:364,30:600]=255
    mask[211:239,384:416]=0
    residuals=[];attempts=0;matched=0;triplets=0;peak=None
    for j in range(1,len(unique)-1):
        a,b,c=unique[j-1:j+2]
        points=cv2.goodFeaturesToTrack(b,maxCorners=360,qualityLevel=.02,minDistance=6,mask=mask)
        if points is None:continue
        p=points[:,0]
        last,ok1=track(b,a,points); nxt,ok2=track(b,c,points)
        r0=p-last; r1=nxt-p
        speed0=np.linalg.norm(r0,axis=1);speed1=np.linalg.norm(r1,axis=1)
        valid=ok1&ok2
        if valid.sum()<25 or min(np.median(speed0[valid]),np.median(speed1[valid]))<.65:continue
        attempts+=len(p);triplets+=1
        unit=(p-focus)/np.maximum(1.,np.linalg.norm(p-focus,axis=1,keepdims=True))
        for shift,speed in ((r0,speed0),(r1,speed1)):
            forward=(shift*unit).sum(axis=1)
            lateral=abs(shift[:,0]*unit[:,1]-shift[:,1]*unit[:,0])
            valid &= (speed>.65)&(forward>0)&(lateral<.6+.16*speed)
        va,vb,vc=values(a,last),values(b,p),values(c,nxt)
        valid &= (correlation(va,vb)>.90)&(correlation(vb,vc)>.90)
        if not valid.any():continue
        matched+=int(valid.sum())
        la,lb,lc=[x.mean(axis=1) for x in (va,vb,vc)]
        fraction=speed0/np.maximum(.0001,speed0+speed1)
        err=abs(lb-(la+(lc-la)*fraction))
        residuals.extend(err[valid].tolist())
        k=np.where(valid,err,-1).argmax()
        if peak is None or err[k]>peak["residual"]:
            peak={"residual":float(err[k]),"frameIDs":indices[j-1:j+2],"stepsLuma":[round(float(v[k]),2) for v in (la,lb,lc)],
                  "pointsHalfSize":[np.round(v[k],2).tolist() for v in (last,p,nxt)]}
    assert matched>=120 and triplets>=4,(triplets,attempts,matched)
    qs=np.quantile(residuals,[.5,.95,.99])
    return dict(pack=r["packSha256"],renderer=r["renderer"],rainy=rainy,frames=i,distinct=len(unique),
        captureMaxGapMs=round(1000*max(np.diff(times)),1),
        start=start["xyz"],end=end["xyz"],cameraAngles=[start["angle"],end["angle"]],
        triplets=triplets,featuresTested=attempts,accepted=matched,
        deviationMedianP95P99=qs.tolist(),largest=peak,opencv=cv2.__version__)


def main():
    run=WOOD/sys.argv[1]
    data=analyze(run)
    (HERE/(run.name+"-motion.json")).write_text(json.dumps(data,indent=2)+"\n")
    print({k:data[k] for k in ("frames","distinct","triplets","accepted","deviationMedianP95P99","largest")})


if __name__=="__main__":
    main()
