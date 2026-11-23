"""Draw the five actual torch readings at the forest location found in the initial sweep."""
from pathlib import Path
import json
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import unpack,check_record,worldgrid,face_from_geometry,integral,FOREST_ANCHOR,FOREST_SOURCES
from sweep_score import POSES


def record():
    worst=json.loads((HERE/"birch-transitions.json").read_text())["worstByPoseAndLamp"][0]
    x,y=worst["screen"];lamp=worst["lamp"]
    grid=worldgrid()
    points=[]
    for stage,eyeX in POSES.items():
        values={}
        positions=[]
        for variant,folder in (("previous","birch-two-caps"),("trial","birch-motion24")):
            folder=HERE/folder
            file=folder/(stage+"-ingame.png")
            check_record(folder,file)
            l,p,n=unpack(file,2)
            point=p[y:y+1,x//8:x//8+1,:]
            positions.append(point)
            flag=int(l[y,x//8,lamp,2])
            assert flag>=64 and not flag&12
            values[variant]=int(l[y,x//8,lamp,1])/255
        assert np.max(abs(positions[0]-positions[1]))<.001
        face=face_from_geometry(point,np.array([eyeX,65.62,355.5]))
        assert int(face.item())==4
        ref=integral(point,face,np.ones((1,1),bool),FOREST_SOURCES[lamp],FOREST_ANCHOR,grid).item()
        assert ref>=0.
        points.append(dict(x=eyeX,point=point.ravel().tolist(),reference=ref,**values))
    return points


if __name__=="__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import sys
    assert sys.argv[1:] in ([],["--alternatives"])
    alternatives=bool(sys.argv[1:])
    if alternatives:
        data=json.loads((HERE/"track.json").read_text())
        worst=json.loads((HERE/"birch-transitions.json").read_text())["worstByPoseAndLamp"][0]
        x,y=worst["screen"]
        lamp=worst["lamp"]
        for point,stage in zip(data,POSES,strict=True):
            assert point["x"]==POSES[stage]
            for key in ("adaptive12","cone"):
                folder=HERE/("birch-"+key)
                photo=folder/(stage+"-ingame.png")
                check_record(folder,photo)
                lights,pos,_=unpack(photo,2)
                assert np.max(abs(pos[y,x//8]-point["point"]))<.001
                sample=lights[y,x//8,lamp]
                assert sample[2]>=64 and not sample[2]&12
                point[key]=int(sample[1])/255
    else:
        data=record()
    (HERE/("track-alternatives.json" if alternatives else "track.json")).write_text(json.dumps(data,indent=2)+"\n")
    fig,ax=plt.subplots(figsize=(7,3.8),constrained_layout=True)
    series=[("previous","Three-sample blend","#8a4b25","s"),("trial","24-sample blend","#246aa3","o")]
    if alternatives:
        series.extend([("adaptive12","Adaptive 12 samples","#796299","d"),("cone","Whole-disk blocker search","#ce6a28","+")])
    series.append(("reference","8,192-ray reference","#257444","x"))
    for value,label,color,mark in series:
        ax.plot([round((p["x"]-209)*100) for p in data],[100*p[value] for p in data],marker=mark,
                linewidth=1.7,color=color,label=label)
    ax.set(xlabel="Camera offset from block boundary (cm)",ylabel="Visible torch area (%)",ylim=(-2,102),
           title="Torchlight on the same grass surface during an 8 cm camera sweep",xticks=[-4,-2,0,2,4])
    ax.grid(axis="y",alpha=.25);ax.legend(frameon=False)
    fig.savefig(HERE/("grass-light-alternatives.png" if alternatives else "grass-light.png"),dpi=150)
