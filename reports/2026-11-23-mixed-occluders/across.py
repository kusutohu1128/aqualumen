"""Score actual horizontal neighbours using the biased origins recorded in each frame."""
from hashlib import sha256
import json
import sys
from zipfile import ZipFile
from grid import HERE,WORK,DENSITY,check_record
from orthogonal import add_coordinates
from score import FOREST_ANCHOR,FOREST_SOURCES,Image,np,face_from_geometry,integral,moments,worldgrid


def build():
    path=WORK/"Aqualumen-Two-Box-Per-Row.zip"
    with ZipFile(WORK/"Aqualumen-Two-Opaque-Shadows-Polygon-Meter.zip") as src,ZipFile(path,"w") as dst:
        for entry in src.infolist():
            data=src.read(entry)
            if entry.filename.startswith("shaders/"):
                data=add_coordinates(entry.filename,data.decode()).encode()
            dst.writestr(entry,data)
    return path,sha256(path.read_bytes()).hexdigest()


def photo(folder):
    path=folder/"birch-4-ingame.png"
    digest=check_record(folder,path)
    with Image.open(path) as im:rgb=np.array(im.convert("RGB"))
    assert np.array_equal(rgb[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
    lanes=rgb[::-1].reshape(-1,16,rgb.shape[1],3)[1:].transpose(2,0,1,3)
    assert (lanes[:,:,10]==[51,183,2]).all()
    def number(t):return t.astype(np.int32)@np.array([1,256,65536])
    return digest,lanes[:,:,:4],number(lanes[:,:,4:7])/65536.+FOREST_ANCHOR,number(lanes[:,:,7:10])/1048576.-1.


def analyze():
    h0,old,p,bias=photo(DENSITY/"gp-density-placed-hull-coordinates")
    h1,new,q,offset=photo(DENSITY/"gp-density-double-box-polygon-horizontal")
    face=face_from_geometry(p,np.array([208.5,65.62,355.5]))
    normal=np.stack([(face==2*a+2).astype(float)-(face==2*a+1) for a in range(3)],axis=2)
    grid=worldgrid()
    inside=np.floor(p-.005*normal).astype(int)-FOREST_ANCHOR
    solid=grid[tuple(np.moveaxis(np.clip(inside,0,63),-1,0))]==1
    valid=(face>0)&solid&(abs(bias-.025*normal).max(axis=2)<.001)
    valid&=(abs(p-q).max(axis=2)<.001)&(abs(bias-offset).max(axis=2)<.001)
    dpos=np.diff(p,axis=0)
    same=(face[:-1]==face[1:])&(abs((normal[:-1]*dpos).sum(axis=2))<.00025)&(np.linalg.norm(dpos,axis=2)<.09)
    rows=[]
    for i,src in enumerate(FOREST_SOURCES):
        a,b=old[:,:,i],new[:,:,i]
        f,g=a[:,:,2],b[:,:,2]
        ref=integral(p,face,valid&(f>=64)&(g>=64)&((f&12)==0)&((g&12)==0),src,FOREST_ANCHOR,grid,bias)
        partial=(ref>.005)&(ref<.995)
        left=a[:,:,1]/255.;right=b[:,:,1]/255.
        err=[abs(np.diff(t,axis=0)-np.diff(ref,axis=0)) for t in (left,right)]
        edge=(ref[:-1]>=0)&(ref[1:]>=0)&same&np.diff(g%4==3,axis=0)&(partial[:-1]|partial[1:])
        rows.append(dict(partial=[moments(abs(t-ref)[partial]) for t in (left,right)],edgeErrors=[moments(v[edge]) for v in err],
                    worse2Bytes=int((edge&(err[1]-err[0]>2/255.)).sum()),better2Bytes=int((edge&(err[0]-err[1]>2/255.)).sum())))
    return dict(hashes=[h0,h1],lights=rows)

if __name__=="__main__":
    if sys.argv[1:]==["build"]: print(*build())
    else: (HERE/"horizontal.json").write_text(json.dumps(analyze(),indent=2)+"\n")
