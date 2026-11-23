"""Read independent horizontal neighbours with the shader's actual ray origins."""
from score import *
folder=DENSITY/sys.argv[1]
path=folder/"birch-4-ingame.png"
digest=check_record(folder,path)
rgb=np.array(Image.open(path).convert("RGB"))
assert np.array_equal(rgb[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
# GL bottom-up strips; omit the calibration block, transpose for horizontal pairs.
lanes=rgb[::-1].reshape(-1,16,rgb.shape[1],3)[1:].transpose(2,0,1,3)
assert (lanes[:,:,10]==[51,183,2]).all()
def number(z): return z.astype(np.int32)@np.array([1,256,65536])
p=number(lanes[:,:,4:7])/65536.+FOREST_ANCHOR
bias=number(lanes[:,:,7:10])/1048576.-1.
eye=np.array([208.5,65.62,355.5])
face=face_from_geometry(p,eye)
grid=worldgrid()
normal=np.stack([(face==2*a+2).astype(float)-(face==2*a+1) for a in range(3)],axis=2)
coords=np.floor(p-.005*normal).astype(int)-FOREST_ANCHOR
whole=grid[tuple(np.moveaxis(np.clip(coords,0,63),-1,0))]==1
hasLight=(lanes[:,:,:4,2]>=64).any(axis=2)
aligned=(abs(bias-.025*normal).max(axis=2)<.001)
valid=(face>0)&whole&aligned
def stat(a):return {k:float(v) for k,v in zip(("min","median","max"),np.quantile(a,[0,.5,1]))}
counts=dict(biasLength=stat(np.linalg.norm(bias,axis=2)[(face>0)&hasLight&whole]),
            fullCubeWithLight=int(((face>0)&hasLight&whole).sum()),aligned=int((valid&hasLight).sum()))
lights=[]
for i,src in enumerate(FOREST_SOURCES):
    d,ref=paired(lanes[:,:,i],p,face,src,FOREST_ANCHOR,grid,valid,bias)
    # paired() consumes the first array dimension, now actual adjacent columns.
    lights.append(d)
(HERE/"horizontal.json").write_text(json.dumps(dict(packSha=digest,readback=counts,lights=lights),indent=2)+"\n")
