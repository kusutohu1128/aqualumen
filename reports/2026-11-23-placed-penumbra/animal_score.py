"""Identify the static penumbra while the cow crosses on the other side of the lamp."""
from score import *
folder=HERE/(sys.argv[1] if len(sys.argv)>1 else "cow-and-trunk")
poses={}
for stage in ("trunk","walk","walk-cleared"):
    f=folder/(stage+"-ingame.png");check_record(folder,f);poses[stage]=unpack(f,1)
left,p,n=poses["trunk"];moving,q,_=poses["walk"];restored,r,_=poses["walk-cleared"]
a,b,c=[v[:,:,0] for v in (left,moving,restored)]
face=face_from_geometry(p,np.array([409.48,152.62,-405.95]))
# The photographed cow's initial centre is west of x405 while the lamp is at
# x405.5. Restrict the receiver and all disk rays to the opposite half-space.
valid=(p[:,:,0]>409.)&(np.max(abs(p-q),axis=2)<.001)&(np.max(abs(p-r),axis=2)<.001)
valid&=(face==6)&(abs(p[:,:,2]+412.)<.006)&(p[:,:,1]>151.)&(p[:,:,1]<155.)
valid&=(a[:,:,2]>=64)&(b[:,:,2]>=64)&(c[:,:,2]>=64)
partial=valid&(a[:,:,1]>2)&(a[:,:,1]<253)&((b[:,:,2]&8)!=0)
dst=abs(a[:,:,1].astype(int)-b[:,:,1].astype(int))
back=abs(a[:,:,1].astype(int)-c[:,:,1].astype(int))
report=dict(matched=int(valid.sum()),partiallyLitWithBroadAnimal=int(partial.sum()),changeWithCow=moments(dst[partial]/255.),
            returnAfterCow=moments(back[partial]/255.),changedByMoreThanTwoBytes=int(((dst>2)&partial).sum()))
oldShadow=valid&(a[:,:,0]==255)&(b[:,:,0]==0)&(c[:,:,0]==255)
# Also track genuine direct-light occlusions throughout the room, including
# the floor and areas to the west in which this cow does cross the lamp rays.
registered=(np.max(abs(p-q),axis=2)<.001)&(np.max(abs(p-r),axis=2)<.001)
lit=registered&(a[:,:,2]>=64)&(b[:,:,2]>=64)&(c[:,:,2]>=64)&(a[:,:,0]==255)&(c[:,:,0]==255)&(b[:,:,0]==0)
report["actorFullShadows"]=int(lit.sum())
report["actorFullShadowsPreserved"]=int((lit&(b[:,:,1]==0)).sum())
report["farWallFullAnimalShadows"]=int(oldShadow.sum())
report["jointCalls"]=int(((b[:,:,2]%4)==3).sum())
if (folder/"near-cow-ingame.png").exists():
    path=folder/"near-cow-ingame.png";check_record(folder,path)
    near,np_,_=unpack(path,1);d=near[:,:,0];method=d[:,:,2]%4
    match=(np.max(abs(p-np_),axis=2)<.001)&(a[:,:,2]>=64)&(d[:,:,2]>=64)
    before=a[:,:,1].astype(int);now=d[:,:,1].astype(int)
    intersect=match&(method==3)&(before>2)&(before<253)
    report["nearAnimal"]=dict(jointLitPartial=int(intersect.sum()),darkerBeyondTwoBytes=int((intersect&(before-now>2)).sum()),
        meanAdditionalOcclusion=moments((before-now)[intersect]/255.),
        fullShadowsOverPreviouslyLit=int((match&(before==255)&(now==0)).sum()))

(HERE/("animal-overlap.json" if folder.name=="cow-and-trunk" else "animal-joint.json")).write_text(json.dumps(report,indent=2)+"\n")
