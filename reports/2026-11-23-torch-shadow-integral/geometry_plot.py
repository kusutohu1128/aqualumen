"""Plot the two in-game light paths that led to the terrain geometry changes."""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sweep_score import HERE, POSES, FOREST_ANCHOR, FOREST_SOURCES, check_record, face_from_geometry, integral, unpack, worldgrid


def readings(record, grid, candidate):
    x,y=record["screen"]
    lamp=record["lamp"]
    series=[]
    for stage,camera in POSES.items():
        samples={}
        positions=[]
        flags=[]
        for folder,key in (("birch-two-caps","three"),(candidate,"geometry")):
            photo=HERE/folder/(stage+"-ingame.png")
            check_record(photo.parent,photo)
            lights,points,_=unpack(photo,2)
            value=lights[y,x//8,lamp]
            flags.append(int(value[2]))
            samples[key]=int(value[1])/255.
            positions.append(points[y:y+1,x//8:x//8+1])
        if not all(f>=64 and not f&12 for f in flags):
            series.append(dict(offsetCm=round((camera-209)*100),flags=flags,
                               reference=None,geometry=None,three=None))
            continue
        assert np.max(abs(positions[0]-positions[1]))<.001
        face=face_from_geometry(positions[0],np.array([camera,65.62,355.5]))
        assert face.item()==record["face"]
        ref=integral(positions[0],face,np.ones((1,1),bool),FOREST_SOURCES[lamp],FOREST_ANCHOR,grid).item()
        assert ref>=0.
        series.append(dict(offsetCm=round((camera-209)*100),point=positions[0].ravel().tolist(),reference=ref,**samples))
    return dict(screen=[x,y],torch=lamp,series=series)


if __name__=="__main__":
    assert sys.argv[1:] in ([],["--joint"])
    joint=bool(sys.argv[1:])
    stem="joint-light" if joint else "geometry-light"
    grid=worldgrid()
    cases=[("Grass in the birch forest","birch-transitions.json"),("Three diagonal blocks","cone-sweep.json")]
    data={}
    fig,axes=plt.subplots(1,2,figsize=(9,3.7),sharey=True,constrained_layout=True)
    for axis,(title,path) in zip(axes,cases,strict=True):
        record=json.loads((HERE/path).read_text())["worstByPoseAndLamp"][0]
        data[title]=readings(record,grid,"birch-joint" if joint else "birch-cone64")
        series=data[title]["series"]
        for key,label,color,mark,style in (("three","Three-sample blend","#8c593f","s","--"),
                                           ("geometry","Geometry pack","#2876a8","o","-"),
                                           ("reference","8,192-ray reference","#294e2b","x",":")):
            values=np.asarray([p[key] for p in series],dtype=float)*100
            axis.plot([p["offsetCm"] for p in series],values,label=label,
                      color=color,marker=mark,linestyle=style,markerfacecolor="none",markersize=7)
        axis.set(title=title,xlabel="Camera offset (cm)",xticks=[-4,-2,0,2,4],ylim=(-3,103))
        axis.grid(axis="y",alpha=.25)
    axes[0].set_ylabel("Visible torch area (%)")
    axes[0].legend(frameon=False)
    fig.savefig(HERE/(stem+".png"),dpi=160)
    (HERE/(stem+".json")).write_text(json.dumps(data,indent=2)+"\n")
