"""Compare calibrated F2 visibility against independent finite-disk ray intersections."""
import ctypes as ct
from hashlib import sha256
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from pack import HERE, ROOT, WORK

DENSITY=HERE.parent/"2026-11-23-torch-density"
ROOM_SOURCE=np.array([[405.5,151.64,-407.5]])
FOREST_SOURCES=np.array([[207.5,64.64,359.5],[210.5,64.64,359.5],[205.5,64.64,357.5],[208.5,64.64,360.5]])
ROOM_ANCHOR=np.array([384,128,-432],np.int32)
FOREST_ANCHOR=np.array([176,32,320],np.int32)
WEIGHTS=np.array([.2126,.7152,.0722])

def unpack(photo,scene):
    with Image.open(photo) as im: rgb=np.array(im.convert("RGB"))
    assert np.array_equal(rgb[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
    lanes=rgb[:-5].reshape(rgb.shape[0]-5,-1,8,3)
    assert (lanes[:,:,7,1]==183).all() and (lanes[:,:,7,2]==scene).all()
    lamp=lanes[:,:,:4].copy()
    pos=lanes[:,:,4:7].astype(np.int32)@np.array([1,256,65536])
    return lamp,pos/65536.+(ROOM_ANCHOR if scene==1 else FOREST_ANCHOR),lanes[:,:,7,0]

def face_from_geometry(pos,eye):
    # The marker's alpha channel reads zero in Iris. Recover only a single
    # unambiguous integer-aligned surface facing the camera, excluding edges.
    near=abs(pos-np.rint(pos))<.0005
    single=near.sum(axis=2)==1
    axis=np.argmax(near,axis=2)
    sign=np.take_along_axis(eye-pos,axis[:,:,None],axis=2)[:,:,0]>0
    return np.where(single,1+2*axis+sign,0).astype(np.uint8)

def worldgrid():
    sys.path.insert(0,str(HERE.parent/"2026-11-20-local-light/forest-tools"))
    from worldread import World
    world=World()
    grid=np.full((64,64,64),2,np.uint8)
    cubes={"stone","grass_block","dirt","gravel","sand","andesite","granite","diorite",
           "red_mushroom_block","mushroom_stem","deepslate","bedrock","clay","tuff"}
    for a,b,c in np.ndindex(grid.shape):
        x,y,z=FOREST_ANCHOR+(a,b,c)
        name=world.name(int(x),int(y),int(z))
        name=name.removeprefix("minecraft:") if name else "unknown"
        if name in ("air","cave_air","void_air"): grid[a,b,c]=0
        elif name in cubes or name.endswith(("_log","_ore")): grid[a,b,c]=1
    assert world.unchanged()
    for e in FOREST_SOURCES:
        assert grid[tuple(np.floor(e).astype(int)-FOREST_ANCHOR)]==0
    return grid

def integral(pos,normal,mask,source,anchor,grid,bias=None):
    lib=ct.CDLL(str(WORK/"disk_reference.so"))
    run=lib.integrate
    run.argtypes=[ct.c_int]+[ct.c_void_p]*7
    run.restype=None
    p=np.ascontiguousarray(pos[mask]); n=np.ascontiguousarray(normal[mask])
    out=np.empty(n.size,np.float32)
    offset=np.ascontiguousarray(bias[mask]) if bias is not None else None
    run(n.size,p.ctypes.data,n.ctypes.data,offset.ctypes.data if offset is not None else None,
        *(v.ctypes.data for v in (source,anchor,grid,out)))
    ref=np.full(mask.shape,-1.);ref[mask]=out
    return ref

def moments(a):
    return dict(n=int(a.size),mean=float(np.mean(a)),p95=float(np.quantile(a,.95)),max=float(a.max())) if a.size else dict(n=0)

def paired(lamp,pos,norm,source,anchor,grid,valid,bias=None):
    old,new,flags=np.moveaxis(lamp,-1,0)
    method=flags%4
    eligible=valid & (norm>0) & (flags>=64) & ((flags&12)==0)
    ref=integral(pos,norm,eligible,source,anchor,grid,bias)
    old=old/255.;new=new/255.
    partial=(ref>.005)&(ref<.995)
    comparable=ref>=0
    absolute=[abs(q-ref) for q in (old,new)]
    data=dict(calls=int((flags>=64).sum()),body=int(((flags&8)!=0).sum()),classified=int(comparable.sum()),
              analytic=int(((method==2)&eligible).sum()),partial=int(partial.sum()),
              partialAnalytic=int(((method==2)&partial).sum()),
              partialErrors=[moments(err[partial]) for err in absolute],
              allErrors=[moments(err[comparable]) for err in absolute])
    # x is sampled every eight columns. y-neighbours are true adjacent pixels.
    dpos=np.diff(pos,axis=0)
    samePlane=np.zeros(norm[:-1].shape,bool)
    for axis in range(3):
        samePlane|=np.isin(norm[:-1],[1+2*axis,2+2*axis])&(abs(dpos[:,:,axis])<.00025)
    validPair=comparable[:-1]&comparable[1:]&(norm[:-1]==norm[1:])&samePlane&(np.linalg.norm(dpos,axis=2)<.09)
    mixed=validPair&((method[:-1]==2)!=(method[1:]==2))
    softEdge=mixed&(partial[:-1]|partial[1:])
    errors=[abs(np.diff(q,axis=0)-np.diff(ref,axis=0)) for q in (old,new)]
    data["mixedPairs"]=int(mixed.sum())
    data["mixedErrors"]=[moments(e[mixed]) for e in errors]
    data["mixedPartialErrors"]=[moments(e[softEdge]) for e in errors]
    increase=errors[1]-errors[0]
    data["worseMixedOverTwoBytes"]=int((mixed&(increase>2/255.)).sum())
    if mixed.any():
        y,x=np.unravel_index(np.where(mixed,increase,-np.inf).argmax(),mixed.shape)
        data["worstChange"]=dict(x=int(8*x),y=int(y),p=pos[y:y+2,x].tolist(),
            methods=method[y:y+2,x].tolist(),old=old[y:y+2,x].tolist(),new=new[y:y+2,x].tolist(),ref=ref[y:y+2,x].tolist())
    return data,ref

def check_record(folder,path):
    r=json.loads((folder/"complete.json").read_text())
    assert r["complete"] and not r["failure"] and r["originalWorldAndConfigUnchanged"]
    assert r["shaderpackLogged"] and r["packSha256"]==r["sourcePackShaNow"] and "RTX 3080 Ti" in r["gl"]["renderer"]
    p=json.loads((folder/"preflight.json").read_text());assert p["labAfter"]==p["labBefore"] and not p["foreignObservations"]
    assert sha256(path.read_bytes()).hexdigest()==r["screenshots"][path.name.removesuffix("-ingame.png")]["ingame"]
    return r["packSha256"]

def score_room(folder,stage):
    photo=folder/f"{stage}-ingame.png"
    lamp,pos,norm=unpack(photo,1)
    norm=face_from_geometry(pos,np.array([407.83 if stage=="shifted" else 409.48,152.62,-405.95]))
    x,y,z=np.moveaxis(pos,-1,0)
    floor=(x>404)&(x<410)&(z> -412)&(z< -405)&(abs(y-151.)<.006)&(norm==4)
    wall=(x>404)&(x<410)&(y>151)&(y<155)&(abs(z+412.)<.006)&(norm==6)
    grid=np.zeros((64,64,64),np.uint8)
    if stage in ("trunk","shifted","home"):
        for p in ((406,151,-410),(406,152,-410)): grid[tuple(p-ROOM_ANCHOR)]=1
    out=dict(allCalls=int((lamp[:,:,:,2]>=64).sum()),body=int(((lamp[:,:,:,2]&8)!=0).sum()))
    for name,face in (("floor",floor),("wall",wall)):
        result,ref=paired(lamp[:,:,0],pos,norm,ROOM_SOURCE[0],ROOM_ANCHOR,grid,face)
        out[name]=result
        if stage=="trunk": np.save(WORK/f"trunk-{name}-reference.npy",ref)
    return out

if __name__=="__main__":
    folder=Path(sys.argv[2]).resolve()
    if sys.argv[1]=="room":
        out={}
        for stage in ("shade","torch","trunk","shifted","home","trunk-cut","extinguished","walk","walk-cleared"):
            sha=check_record(folder,folder/f"{stage}-ingame.png")
            out[stage]=score_room(folder,stage)
        path=HERE/(folder.name+"-score.json")
    else:
        path=HERE/(folder.name+"-score.json")
        img=folder/"birch-4-ingame.png";sha=check_record(folder,img)
        lamps,pos,_=unpack(img,2);norm=face_from_geometry(pos,np.array([208.5,65.62,355.5]));grid=worldgrid();out=[]
        # Include only receivers backed by an independently witnessed full world cube.
        nvec=np.zeros_like(pos)
        for a in range(3): nvec[:,:,a]=(norm==2*a+2).astype(float)-(norm==2*a+1)
        inside=np.floor(pos-.005*nvec).astype(int)-FOREST_ANCHOR
        inside=np.clip(inside,0,63)
        validReceiver=grid[tuple(np.moveaxis(inside,-1,0))]==1
        for i,s in enumerate(FOREST_SOURCES):
            valid=validReceiver
            data,ref=paired(lamps[:,:,i],pos,norm,s,FOREST_ANCHOR,grid,valid)
            out.append(data)
    path.write_text(json.dumps(dict(packSha=sha,results=out),indent=2)+"\n")
    print(path)
