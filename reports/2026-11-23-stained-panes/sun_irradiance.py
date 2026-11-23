"""Compare measured incident solar colour on floor points against the actual pane model."""
import argparse
import json
import numpy as np
from PIL import Image
from score import HERE,reader,rectangles
from sun_room import STAGES,block

parser=argparse.ArgumentParser()
parser.add_argument("--filtered",action="store_true")
parser.add_argument("--run-label")
args=parser.parse_args()
filtered=args.filtered
label=args.run_label or ("sun-filtered-meter" if filtered else "sun-meter")
assert label in ("sun-meter","sun-filtered-meter","sun-filtered-meter-r2")
folder=HERE/label
eye=np.array([409.48,152.62,-405.95])
source=HERE/"pane"/"air-ingame.png"
reader.check_record(source.parent,source)
_,p,_=reader.unpack(source,1)
geo=json.loads((folder/"geometry.json").read_text())
assert geo["camera"]==json.loads((source.parent/"geometry.json").read_text())["camera"]
floor=(reader.face_from_geometry(p,eye)==4)&(abs(p[:,:,1]-151)<.0005)
floor&=(p[:,:,0]>404.05)&(p[:,:,0]<409.95)&(p[:,:,2]>-411.95)&(p[:,:,2]<-405.05)
def readout(stage):
    path=folder/(stage+"-ingame.png");reader.check_record(folder,path)
    pic=np.asarray(Image.open(path).convert("RGB"));assert np.array_equal(pic[-3,:256,0],np.arange(256))
    lanes=pic.reshape(pic.shape[0],-1,4,3).astype(np.uint32)
    bits=lanes[:,:,0] | (lanes[:,:,1]<<8) | (lanes[:,:,2]<<16) | (lanes[:,:,3]<<24)
    values=bits.view(np.float32);vec=values[-2,0].astype(float)
    assert np.all(values[-2]==vec) and abs(np.linalg.norm(vec)-1)<1e-5,vec
    return vec,values[:-5,::2,:].astype(float)
def interval(start,dirs,lo,hi,tmax):
    low=np.zeros(p.shape[:2]);high=np.full_like(low,tmax)
    for k in range(3):
        a=start[:,:,k];d=dirs[...,k]
        valid=(a>=lo[k])&(a<hi[k]);parallel=abs(d)<1e-8
        den=np.where(parallel,1.,d);s=(lo[k]-a)/den;t=(hi[k]-a)/den
        low=np.maximum(low,np.where(parallel,np.where(valid,0.,tmax),np.minimum(s,t)))
        high=np.minimum(high,np.where(parallel,np.where(valid,tmax,0.),np.maximum(s,t)))
    return np.maximum(0,high-low)
sky={};beams={}
for stage in STAGES:
    sky[stage],beams[stage]=readout(stage)
d=sky["red"];assert all(np.allclose(d,v,atol=1.e-5) for v in sky.values())
# Restrict both eyes to floor visible with the thick control in place.
eye_orig=np.broadcast_to(eye,p.shape)
view=interval(eye_orig,p-eye,[405.96,150.96,-411.04],[407.04,154.04,-407.96],1.)
floor &= view==0
boxes=rectangles([(406,z,block("red",z)) for z in range(-411,-408)])
travel=np.zeros(p.shape[:2])
for x,y,z,X,Y,Z,_ in boxes:
    travel+=interval(p,d,[x,y,z],[X,154.,Z],512.)
opened=beams["open-late"]
mask=floor & (opened.min(axis=2)>.025) & (travel>.06)
control=floor & (opened.min(axis=2)>.025) & (travel==0.)
def metrics(valid):
    if not valid.any():return {"count":0}
    m=opened[valid]
    calc={};observed={}
    for stage,unit in (("red",[.85,.20,.16]),("blue",[.19,.36,.86])):
        calc[stage]=np.array(unit)**travel[valid,None]
        observed[stage]=beams[stage][valid]/m
    residuals={s:np.max(np.abs(observed[s]-calc[s]),axis=1) for s in calc}
    return dict(count=int(valid.sum()),medianGlassPath=float(np.median(travel[valid])),
                exactRGBMatchRedBlue=int(np.all(beams["red"][valid]==beams["blue"][valid],axis=1).sum()),
                referenceMedianTransmission={s:np.median(v,axis=0).tolist() for s,v in calc.items()},
                observedMedianTransmission={s:np.median(v,axis=0).tolist() for s,v in observed.items()},
                maxChannelErrorP95={s:float(np.quantile(v,.95)) for s,v in residuals.items()},
                medianStoneToOpen=np.median(beams["stone"][valid]/m,axis=0).tolist(),
                zeroSolarUnderStone=int(np.all(beams["stone"][valid]==0.,axis=1).sum()),
                maxOpenRepeat=float(np.max(abs(beams["open-early"][valid]-m))))
result=dict(sunDirection=d.tolist(),directlySunlitPanePaths=metrics(mask),clearPaths=metrics(control),
            description="C8 opaque solar radiance before display, half-float texture read back as exact float values. Single sun direction for the model, no separate sky or bounce terms.")
ordinary=HERE/("sun-filtered" if filtered else "sun-window")
if (ordinary/"complete.json").is_file():
    display={}
    for colour in ("red","blue"):
        photo=ordinary/(colour+"-ingame.png")
        reader.check_record(ordinary,photo)
        display[colour]=np.asarray(Image.open(photo).convert("RGB"),int)[:-5,::8,:]
    for label,selected in (("directlySunlitPanePaths",mask),("clearPaths",control)):
        delta=display["red"][selected]-display["blue"][selected]
        result[label]["ordinaryDisplay"]=dict(
            medianRedVersusBlueRGB=np.median(delta,axis=0).tolist(),
            medianRedMinusBlueChroma=float(np.median(delta[:,0]-delta[:,2])),
            medianRGB={c:np.median(v[selected],axis=0).tolist() for c,v in display.items()})
(HERE/(("sun-filtered-direct" if filtered else "sun-direct")+".json")).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
