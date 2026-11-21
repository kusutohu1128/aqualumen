"""Compare the observed white wall with the shadow geometrically cast by a raised pillar."""
import argparse
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def normalized(v):
    return v/np.linalg.norm(v)

def intersects(a, b, lo, hi):
    d=b-a
    inv=1/np.where(np.abs(d)>1e-8, d, 1e-8)
    t0=(lo-a)*inv
    t1=(hi-a)*inv
    enter=np.maximum(0,np.minimum(t0,t1).max(axis=-1))
    leave=np.minimum(1,np.maximum(t0,t1).min(axis=-1))
    return enter<leave

def masks(width, height, eye, aim):
    forward=normalized(aim-eye)
    right=normalized(np.cross(forward,[0,1,0]))
    up=np.cross(right,forward)
    y,x=np.mgrid[:height:3,:width:3]
    sf=np.tan(np.deg2rad(35))*2/height
    d=forward+(x+.5-width/2)[:,:,None]*right*sf+(height/2-y-.5)[:,:,None]*up*sf
    w=eye+(366-eye[2])/np.maximum(d[:,:,2,None],1e-6)*d
    lo=np.array([202.,173.,364.]); hi=lo+[1,3,1]
    valid=(w[:,:,0]>199.2)&(w[:,:,0]<208.8)&(w[:,:,1]>173.3)&(w[:,:,1]<177.9)
    valid &= ~intersects(eye,w,lo-.08,hi+.08)
    # At a fixed wall point, every top-face lava ray passes at z=364.5.
    # Entirely inside the pillar there implies complete direct occlusion.
    # At four corners of the emitting square the four corresponding wall-to-top
    # rays bound this convex bundle. To qualify an open receiver, all four rays
    # must also be on the same side for the full thickness of the pillar.
    groups={}
    for width, label in [(1,"one"),(3,"nine")]:
        half=width/2
        c=np.array([202.5,172.9,361.5])
        corners=[c+np.array([i*half,0,j*half]) for i in (-1,1) for j in (-1,1)]
        def crossing(z):
            return np.stack([w+(src-w)*((z-w[:,:,2])/(src[2]-w[:,:,2]))[:,:,None] for src in corners])
        mid=crossing(364.5)
        full=valid & (mid[:,:,:,0].min(axis=0)>202.1)&(mid[:,:,:,0].max(axis=0)<202.9)
        full &= (mid[:,:,:,1].min(axis=0)>173.1)&(mid[:,:,:,1].max(axis=0)<175.9)
        both=np.concatenate([crossing(364),crossing(365)])
        open_mask=valid & ((both[:,:,:,0].max(axis=0)<201.8)|(both[:,:,:,0].min(axis=0)>203.2))
        groups[label]={"fullyBlocked":full,"geometricallyOpen":open_mask}
    # Growing the pool exposes emitting area around the edge. Compare exactly
    # the small source's shadowed receivers before and after the change.
    groups["nine"]["sameWallAsSmallShadow"]=groups["one"]["fullyBlocked"]
    groups["nine"]["sameWallAsSmallOpen"]=groups["one"]["geometricallyOpen"]
    return groups

p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path,nargs='?'); args=p.parse_args()
eye=np.array([205.5,174.62,362.5]); aim=np.array([202.5,173.64,366.])
groups=masks(1280,720,eye,aim)
if not args.run:
    print({k:{g:int(m.sum()) for g,m in maps.items()} for k,maps in groups.items()})
    raise SystemExit
r=args.run
g=json.loads((r/'geometry.json').read_text())
assert np.allclose(eye,g['eye']) and np.allclose(aim,g['target']) and g['cameraFov']==70
cert=json.loads((r/'complete.json').read_text())
def sample(label):
    return np.asarray(Image.open(r/(label+'.png')).convert('RGB'),dtype='f4')[::3,::3]
result={"pack":cert["pack"],"sha256":cert["sha256"],"renderer":cert["renderer"],"metrics":{}}
for n,maps in groups.items():
    open_frame=sample(n+'-open'); pillar=sample(n+'-pillar')
    d0=sample('dark');d1=sample('dark-pillar')
    values={}
    for q,m in maps.items():
        if not m.any(): continue
        row={"samples":int(m.sum())}
        for k,im in [('darkOpen',d0),('darkPillar',d1),('open',open_frame),('pillar',pillar),('openAdded',open_frame-d0),('pillarAdded',pillar-d1)]:
            row[k]=np.round(np.median(im[m],axis=0),2).tolist()
        values[q]=row
    result['metrics'][n]=values
result['oneRepeatMedianAbsRGB']=np.median(np.abs(sample('one-open')-sample('one-again')),axis=(0,1)).tolist()
result['darkRepeatMedianAbsRGB']=np.median(np.abs(sample('dark')-sample('dark-again')),axis=(0,1)).tolist()
result['units']='Median display RGB code values. Indirect illumination and exposure also contribute; a fully blocked receiver has no straight path to the modeled horizontal surface.'
(r/'wall-light.json').write_text(json.dumps(result,indent=2)+'\n')
sheet=Image.new('RGB',(1440,311),'#191c1b')
draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20)
for i,(label,caption) in enumerate([('one-open','溶岩一マス'),('one-pillar','溶岩と壁の間に石柱'),('nine-pillar','石柱を残し、溶岩を九マスに拡大')]):
    photo=Image.open(r/(label+'.png')).convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
    sheet.paste(photo,(i*480,0));draw.text((i*480+9,277),caption,fill='white',font=font)
sheet.save(r/'lava-wall.jpg',quality=92)
print(json.dumps(result['metrics']))
