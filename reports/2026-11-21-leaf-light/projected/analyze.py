"""Register the white wall in camera space, then compare its light to vanilla leaf cutouts."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import json
import sys
import numpy as np
from PIL import Image, ImageDraw

here=Path(__file__).resolve().parent
client=Path.home()/'.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar'
with ZipFile(client) as z:
    mask=np.asarray(Image.open(BytesIO(z.read('assets/minecraft/textures/block/oak_leaves.png'))).convert('RGBA'))[:,:,3]/255
assert mask.shape==(16,16)
def normalized(x):return x/np.linalg.norm(x,axis=-1,keepdims=True)
def analyze(p):
    with (p/'geometry.json').open() as f:g=json.load(f)
    eye=np.array(g['eye']);lamp=np.array(g['source']);cell=np.array(g['leaf']);target=np.array(g['target'])
    fw=normalized(target-eye);right=normalized(np.cross(fw,[0,1,0]));up=normalized(np.cross(right,fw))
    names=('open','foliage','stone','dark','soul','again')
    pics={n:np.asarray(Image.open(p/(n+'.png')).convert('RGB')) for n in names}
    height,width,_=pics['foliage'].shape
    yy,xx=np.mgrid[:height,:width]
    tan=np.tan(np.deg2rad(g['cameraFov'])/2)
    ray=fw+right*((xx+.5-width/2)*2*tan/height)[:,:,None]+up*((height/2-yy-.5)*2*tan/height)[:,:,None]
    wall=eye+ray*((g['wallZ']-eye[2])/np.maximum(ray[:,:,2],.001))[:,:,None]
    # Work only on wall patches whose full emitter disk crosses this block and
    # whose camera ray does not (even an opaque replacement must leave the patch visible).
    def interval(a,b):
        d=b-a
        inv=1/np.where(abs(d)>.000001,d,.000001)
        lo=(cell-a)*inv;hi=(cell+1-a)*inv
        return np.min(np.maximum(lo,hi),axis=-1),np.max(np.minimum(lo,hi),axis=-1)
    cam_out,cam_in=interval(eye,wall)
    visible=(cam_out<cam_in)&(wall[:,:,0]>198.08)&(wall[:,:,0]<209.92)&(wall[:,:,1]>173.08)&(wall[:,:,1]<179.92)
    def alpha(point,nearest=False):
        f=np.clip(point-cell,0,1)
        side=np.minimum(f,1-f).argmin(axis=-1)
        x,y,z=f.transpose(2,0,1)
        u=np.where(side==0,np.where(x<.5,z,1-z),np.where(side==1,x,np.where(z<.5,1-x,x)))
        v=np.where(side==1,np.where(y<.5,1-z,z),1-y)
        if nearest:
            return mask[np.clip((v*16).astype(int),0,15),np.clip((u*16).astype(int),0,15)]
        u,v=np.clip(u*16-.5,0,15),np.clip(v*16-.5,0,15)
        i,j=u.astype(int),v.astype(int);i2=np.minimum(i+1,15);j2=np.minimum(j+1,15)
        return (1-v+j)*((1-u+i)*mask[j,i]+(u-i)*mask[j,i2])+(v-j)*((1-u+i)*mask[j2,i]+(u-i)*mask[j2,i2])
    # The emitted disk orientation follows the ray. Three fixed disk samples in
    # the shader form an estimate, independent geometry and alpha come from Minecraft.
    receiver=wall.copy();receiver[:,:,2]-=.025
    l=normalized(lamp-wall)
    axis=np.zeros_like(l);axis[:,:,1]=1
    U=normalized(np.cross(l,axis))*.13;V=normalized(np.cross(l,U))*.13
    samples=[]
    nearestOpaque=[]
    for du,dv in ((.66,0),(-.33,.57156),(-.33,-.57156)):
        source=lamp+du*U+dv*V
        leave,enter=interval(receiver,source)
        visible&=(leave-enter>.12)&(enter>=0)&(leave<=1)
        d=source-receiver
        entry=receiver+enter[:,:,None]*d;exitPoint=receiver+leave[:,:,None]*d
        a,b=alpha(entry),alpha(exitPoint)
        nearestOpaque.append((alpha(entry,True)>.1).astype(int)+(alpha(exitPoint,True)>.1).astype(int))
        samples.append((1-.58*a)*(1-.58*b)*np.exp(-.28*np.linalg.norm(d,axis=-1)*np.maximum(leave-enter,0.0)))
    openness=np.mean(samples,axis=0)
    # Compare the same display channel on identical base geometry. Ground or sky
    # seen through the leaf itself is excluded by the camera-vs-block intersection.
    scalar={k:v[:,:,1].astype(float) for k,v in pics.items()}
    contrast=scalar['open']-scalar['stone']
    usable=visible&(contrast>12)
    assert np.sum(usable)>100
    score=(scalar['foliage']-scalar['stone'])/np.maximum(contrast,1)
    a,b=np.quantile(openness[usable],[.2,.8])
    dark=usable&(openness<=a);bright=usable&(openness>=b)
    summary=dict(pixels=int(np.sum(usable)),predictedQ20=float(a),predictedQ80=float(b),
                 normalizedGreenOnDense=float(np.median(score[dark])),normalizedGreenOnOpen=float(np.median(score[bright])),
                 predictedToObservedCorrelation=float(np.corrcoef(openness[usable],score[usable])[0,1]),
                 repeatedFrameMedianAbsDisplayDifference=float(np.median(abs(scalar['again']-scalar['foliage'])[usable])),
                 openMinusStoneMedian=float(np.median(contrast[usable])))
    # A second comparison uses binary alpha from the vanilla asset alone.
    # No coefficient in the foliage shader is used to decide a group.
    occupied=np.sum(nearestOpaque,axis=0)
    counts={}
    for n in range(7):
        group=usable&(occupied==n)
        if np.sum(group):
            counts[n]=dict(pixels=int(np.sum(group)),medianWallGreenFraction=float(np.median(score[group])))
    summary['vanillaOccupiedIntersectionsOfSix']=counts
    if (p/'open-white.png').is_file():
        white=np.asarray(Image.open(p/'open-white.png').convert('RGB')).astype(float)
        # Compare display RGB on the same wall texels under one sea lantern.
        # Use the geometry mask only; oak's texture does not select the samples
        # for birch or cherry. These are screenshot channel values, not spectra.
        rows={}
        for kind in ('oak','birch','cherry'):
            frame=np.asarray(Image.open(p/(kind+'-white.png')).convert('RGB')).astype(float)
            rows[kind]=dict(meanDisplayRGB=frame[usable].mean(axis=0).round(2).tolist(),
                            openMinusLeafMeanRGB=(white[usable]-frame[usable]).mean(axis=0).round(2).tolist())
        summary['seaLanternSameWall']=dict(samples=int(usable.sum()),uncoveredMeanRGB=white[usable].mean(axis=0).round(2).tolist(),species=rows)
    (p/'analysis-independent.json').write_text(json.dumps(summary,indent=2))
    ys,xs=np.where(usable)
    bb=(int(xs.min()-12),int(ys.min()-12),int(xs.max()+13),int(ys.max()+13))
    regions=[]
    for key in ('open','foliage','stone'):
        frame=Image.fromarray(pics[key]).crop(bb)
        frame.thumbnail((365,220))
        regions.append((key,frame))
    out=Image.new('RGB',(sum(w.width for _,w in regions),max(w.height for _,w in regions)+24))
    pen=ImageDraw.Draw(out);offset=0
    for name,w in regions:
        out.paste(w,(offset,0));pen.text((offset+3,w.height+4),name,fill='white');offset+=w.width
    out.save(p/'wall-comparison.png')
    print(p.name,summary,flush=True)
for name in sys.argv[1:]:analyze(here/name)
