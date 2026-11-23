"""Measure ordinary floor pixels that see the lamp-side of an afternoon window."""
import argparse
import json
import numpy as np
from PIL import Image
from score import HERE,reader

parser=argparse.ArgumentParser()
parser.add_argument("--filtered",action="store_true")
filtered=parser.parse_args().filtered
folder=HERE/("sun-filtered" if filtered else "sun-window")
geo=json.loads((folder/"geometry.json").read_text())
old=HERE/"pane"
assert geo["camera"]==json.loads((old/"geometry.json").read_text())["camera"]
room=json.loads((folder/"complete.json").read_text())
assert room["complete"] and room["size"]==[1280,720]
eye=np.array([409.48,152.62,-405.95])
meter=old/"air-ingame.png";reader.check_record(old,meter)
_,p,_=reader.unpack(meter,1)
floor=((abs(p[:,:,1]-151)<.0005) & (reader.face_from_geometry(p,eye)==4)
       & (p[:,:,0]>404.05) & (p[:,:,0]<409.95) & (p[:,:,2]>-411.95) & (p[:,:,2]<-405.05))
# Reject a slightly larger volume than the thick opaque control, including
# every direct view through the glass texture and the edge-filter footprint.
low=np.array([405.96,150.96,-411.04]);high=np.array([407.04,154.04,-407.96])
with np.errstate(divide="ignore",invalid="ignore"):
    a=(low-eye)/(p-eye);b=(high-eye)/(p-eye)
seen=np.maximum(np.minimum(a,b).max(axis=2),0)<np.minimum(np.maximum(a,b).min(axis=2),1)
floor &= ~seen
imgs={}
for stage in room["stages"]:
    img=folder/(stage+"-ingame.png")
    reader.check_record(folder,img)
    imgs[stage]=np.asarray(Image.open(img).convert("RGB"),float)[:-5,::8]
luma=np.array([.2126,.7152,.0722]);opened=imgs["open-late"]
shadow=(opened-imgs["stone"])@luma
floor_light=(opened@luma)
red_blue=imgs["red"]-imgs["blue"]
def stats(mask):
    if not mask.any():return {"count":0}
    data=dict(count=int(mask.sum()),positionMedian=np.median(p[mask],axis=0).tolist(),
              medianRGB={k:np.median(v[mask],axis=0).tolist() for k,v in imgs.items()},
              medianRedMinusBlueRGB=np.median(red_blue[mask],axis=0).tolist(),
              medianRedMinusBlueChroma=float(np.median((red_blue[:,:,0]-red_blue[:,:,2])[mask])),
              medianOpaqueDarkening=float(np.median(shadow[mask])),
              medianOpenEarlyToLateDrift=float(np.median(((imgs["open-early"]-opened)@luma)[mask])))
    return data
# Use the ordinary stone image solely to select the candidate receiving floor;
# never use the difference between the two coloured images to select it.
behind=floor & (shadow>22) & (floor_light>50)
unshadowed=floor & (abs(shadow)<5) & (floor_light>50)
score={"floorSamples":int(floor.sum()),"darkenedByStone":stats(behind),"outsideStoneShadow":stats(unshadowed),
       "redMinusBlueAllFloor":stats(floor),"sampleColumnsEvery":8,
       "note":"Display pixels outside the conservative camera silhouette, with automatic exposure and diffuse lighting active. This is not a measurement of incident solar irradiance."}
(HERE/(("sun-filtered-display" if filtered else "sun-display")+".json")).write_text(json.dumps(score,indent=2)+"\n")
print(json.dumps(score))
