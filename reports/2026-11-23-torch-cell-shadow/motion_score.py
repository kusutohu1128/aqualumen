"""Check old and proposed lighting on the same decoded frames of a live crossing."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import check_record

def analyze(folder):
    photo=folder/"walk-ingame.png"
    digest=check_record(folder,photo)
    assert digest=="77ba63d6f58ab225510b4c255b86a8dd14bc8a68b3aa94331235589c00bbb7c5"
    check_record(folder,folder/"walk-cleared-ingame.png")
    movie=folder/"cow-motion.mkv"
    track=[]
    log=(folder/"client.log").read_text()
    section=log.split("[Server] AQ_WALK_START",1)[1].split("[Server] AQ_WALK_END",1)[0]
    for x,y,z in re.findall(r"\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)",section):
        track.append([int(x)/1000,int(y)/1000,int(z)/1000])
    assert len(track)>10
    dist=float(np.linalg.norm(np.diff(np.asarray(track),axis=0),axis=1).sum())
    assert dist>1.
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,width,height,avg_frame_rate,pix_fmt","-of","json",movie]))["streams"][0]
    assert (probe["codec_name"],probe["width"],probe["height"])==("ffv1",1280,720)
    prev=None;seen=set();frames=0;registered=0;changes=0;changeErrors=0;coverage=[];samples=[]
    with subprocess.Popen(["ffmpeg","-v","error","-threads","2","-i",movie,"-f","rawvideo","-pix_fmt","rgb24",
                           "-threads","1","pipe:1"],stdout=subprocess.PIPE) as ff:
        while True:
            raw=ff.stdout.read(1280*720*3)
            if not raw:break
            assert len(raw)==1280*720*3
            im=np.frombuffer(raw,np.uint8).reshape(720,1280,3)
            assert np.array_equal(im[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
            cells=im[:-5].reshape(715,160,8,3)
            assert (cells[:,:,7,1]==183).all() and (cells[:,:,7,2]==1).all()
            light=cells[:,:,0];fa=light[:,:,2]
            old,new=light[:,:,0],light[:,:,1]
            active=fa>=64;body=active & ((fa&8)!=0)
            newClear=active&((fa&32)!=0)&((fa&16)==0)
            codedPos=cells[:,:,4:7].astype(np.int32)@np.array([1,256,65536],np.int32)
            wall=(abs(codedPos[:,:,2]/65536.-20)<.006) & (codedPos[:,:,0]>20*65536) & (codedPos[:,:,0]<26*65536)
            wall&=(codedPos[:,:,1]>23*65536)&(codedPos[:,:,1]<27*65536)&active
            visHash=hashlib.sha256(light[wall].tobytes()).hexdigest()
            key=hashlib.sha256(light.tobytes()+codedPos.tobytes()).hexdigest()
            sample=dict(index=frames,wall=int(wall.sum()),bodyOnWall=int((body&wall).sum()),wallHash=visHash,
                        changedVisibility=int(((old!=new)&active).sum()))
            samples.append(sample)
            frames+=1
            if key not in seen:
                seen.add(key)
                coverage.append(dict(active=int(active.sum()),body=int(body.sum()),
                                     dark=int((active&((fa&16)!=0)).sum()),added=int((active&((fa&32)!=0)).sum()),partial=int((active&(new>0)&(new<255)).sum()),
                                     different=sample["changedVisibility"],newClear=int(newClear.sum()),
                                     newClearWithBody=int((newClear&body).sum()),
                                     bodyShadedNewClear=int((newClear&body&(old<255)).sum())))
            if prev is not None:
                pp,po,pn,pw=prev
                same=(codedPos==pp).all(axis=-1)&wall&pw
                dOld=old.astype(np.int16)-po
                dNew=new.astype(np.int16)-pn
                registered+=int(same.sum())
                changes+=int((same & (dOld!=0)).sum())
                changeErrors+=int((same & (dOld!=dNew)).sum())
            prev=codedPos,old.astype(np.int16),new.astype(np.int16),wall
        assert ff.wait()==0
    assert frames>75 and len(seen)>8 and changes>0
    with movie.open("rb") as stream:
        movie_hash=hashlib.file_digest(stream,"sha256").hexdigest()
    data=dict(packSha256=digest,movieSha256=movie_hash,source=probe,
              capturedFrames=frames,uniqueFields=len(seen),cowTravelMetres=dist,trackedPoses=len(track),
              uniqueFieldTotals={k:sum(s[k] for s in coverage) for k in coverage[0]},
              matchedWallTransitions=registered,changingWallSamples=changes,unequalChanges=changeErrors,
              distinctWallStates=len({f["wallHash"] for f in samples}),frames=samples)
    (folder/"motion-score.json").write_text(json.dumps(data,indent=2)+"\n")
    print({k:v for k,v in data.items() if k not in ("source","packSha256","movieSha256","frames")})
    assert data["uniqueFieldTotals"]["different"]==0 and changeErrors==0
    if folder.name=="glass-cow-motion":
        assert data["uniqueFieldTotals"]["bodyShadedNewClear"]>0

if __name__=="__main__":
    analyze(HERE/sys.argv[1])
