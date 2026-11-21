"""Relate real displayed bark patches to the surveyed torch and the distance along the actual trunk face."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"fixture"))
import fixture
from torch_pixels import regions

def run(root):
    levels=json.loads((root/"torch-pixels.json").read_text())["phases"]
    source=np.array([5.71,-58.16,-8.5])
    report={}
    for phase,info in levels.items():
        f,r,u=np.array(fixture.basis(*info["rotation"]))
        p0=np.array(info["eyeFeet"])+[0,1.62,0]
        images=[np.asarray(Image.open(root/f"{phase}-oak-torch-{k}.jpg").convert("RGB"))/255 for k in ("on","off","restored")]
        h,w=images[0].shape[:2]
        rays=f+(((np.arange(w)+.5)/w*2-1)*fixture.TAN*(w/h))[None,:,None]*r+((1-(np.arange(h)+.5)/h*2)*fixture.TAN)[:,None,None]*u
        pos=p0+rays*((6-p0[0])/rays[:,:,0])[:,:,None]
        distance=np.linalg.norm(pos-source,axis=2)
        z=pos[:,:,2]
        valid=((z>-8.93)&(z<-8.78)|(z>-8.22)&(z<-8.07))&(pos[:,:,1]>-59.92)&(pos[:,:,1]<-57.45)
        valid[int(h*.88):]=False
        linear=[np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4) for x in images]
        Ys=[x@np.array([.2126,.7152,.0722]) for x in linear]
        deltas=(Ys[0]+Ys[2])*.5-Ys[1]
        ratio=(Ys[0]+Ys[2])*.5/np.maximum(Ys[1],.001)
        bands=[]
        for a,b in ((.29,.45),(.45,.65),(.65,.85),(.85,1.1),(1.1,1.35),(1.35,1.6),(1.6,2)):
            m=valid&(distance>=a)&(distance<b)
            if m.sum()<30:continue
            bands.append({"metres":[a,b],"pixels":int(m.sum()),"medianDisplayDeltaY":round(float(np.median(deltas[m])),4),
               "medianDisplayRatio":round(float(np.median(ratio[m])),2),
               "redClippedFraction":round(float((images[0][:,:,0][m]>=250/255).mean()),4)})
        known={}
        for name in ("oakBarkAboveFlame","oakBarkBesideFlame"):
            x0,y0,x1,y1=[round(z*(w if i%2==0 else h)) for i,z in enumerate(regions[name])]
            known[name]={"medianWorldY":round(float(np.median(pos[y0:y1,x0:x1,1])),3),"medianSourceDistance":round(float(np.median(distance[y0:y1,x0:x1])),3)}
        report[phase]={"regions":known,"bands":bands}
    data={"method":"Intersect rays from the surveyed real player camera with the west trunk face at x=6. Exclude the central flame, top/bottom edges, hand and HUD with two side strips on the same trunk. Source is the release west-wall torch anchor. Image includes texture, display response, AO and reflected light; this is not bare irradiance.","worldSource":source.tolist(),"phases":report}
    (root/"bark-falloff.json").write_text(json.dumps(data,indent=2)+"\n")
    for name,s in report.items():print(name,s["regions"],[(q["metres"],q["medianDisplayRatio"],q["redClippedFraction"]) for q in s["bands"]])
if __name__=="__main__":run(Path(sys.argv[1]))
