"""Measure ordinary screenshot differences on static terrain separately from visibility."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import DENSITY, check_record, unpack, face_from_geometry, worldgrid, FOREST_ANCHOR


def read(label):
    folder=DENSITY/label
    path=folder/"birch-4-ingame.png"
    digest=check_record(folder,path)
    with Image.open(path) as photo:
        return digest,np.asarray(photo.convert("RGB"),dtype=np.float32)


def compare(labels):
    meter=DENSITY/"gp-density-double-box-polygon-meter"
    path=meter/"birch-4-ingame.png"
    check_record(meter,path)
    lights,p,measured=unpack(path,2)
    face=face_from_geometry(p,np.array([208.5,65.62,355.5]))
    n=np.stack([(face==2*j+2).astype(float)-(face==2*j+1) for j in range(3)],axis=2)
    cell=np.floor(p-.005*n).astype(int)-FOREST_ANCHOR
    grid=worldgrid()
    solid=(face!=0)&((measured==0)|(measured==face))&(grid[tuple(np.moveaxis(np.clip(cell,0,63),-1,0))]==1)
    lit=(lights[:,:,:,2]>=64)&((lights[:,:,:,2]&12)==0)
    soft=((lights[:,:,:,1]>2)&(lights[:,:,:,1]<253)&lit).any(axis=2)
    valid=solid&soft
    base,whole=read("gp-density-paired-release")
    a=whole[:-5,::8]
    out={}
    for label in labels:
        digest,img=read(label)
        b=img[:-5,::8]
        assert b.shape==a.shape
        rgb=b[valid]-a[valid]
        dy=abs(rgb@np.array([.2126,.7152,.0722]))
        out[label]=dict(pack=digest,probes=int(valid.sum()),rgbIdentical=int((rgb==0).all(axis=1).sum()),
                        meanDisplayLuma=float(dy.mean()),p95DisplayLuma=float(np.quantile(dy,.95)),max=float(dy.max()))
    return dict(basePack=base,size=[2560,1440],units="8-bit display RGB and Rec709 luma",summary=out)


if __name__=="__main__":
    print(json.dumps(compare(sys.argv[1:]),indent=2))
