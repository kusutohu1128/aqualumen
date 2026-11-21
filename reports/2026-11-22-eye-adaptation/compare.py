"""Compare native F2 samples for matched views and draw the actual exposure history at the cave."""
import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt

here=Path(__file__).resolve().parent
fontfile="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(fontfile)
plt.rcParams["font.family"]=font_manager.FontProperties(fname=fontfile).get_name()


def json_at(path):
    return json.loads(path.read_text())


def plot_cave(records,areas):
    fig,axes=plt.subplots(2,1,figsize=(10.5,5.7),layout="constrained",sharey=True)
    for ax,rec,color in zip(axes,records,("#997448","#1579a0")):
        name=Path(rec["path"]).name
        with (here/(name+".csv")).open() as stream:
            samples=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(stream)]
        def time_at(shot):
            frame=rec["photos"][shot]["frame"]
            return min(samples,key=lambda v:abs(v["frame"]-frame))["seconds"]
        start=time_at("empty-again")
        stop=time_at("opening-again")
        rows=[r for r in samples if start-1<=r["seconds"]<=stop+.5]
        ax.plot([r["seconds"]-start for r in rows],[r["exposure"] for r in rows],color=color,lw=1.8)
        for i,(shot,title) in enumerate(zip(areas,("雨空","岩壁","雨空"))):
            t=time_at(shot)-start
            y=rec["photos"][shot]["exposure"]
            ax.scatter(t,y,s=19,color=color,zorder=3)
            ax.annotate(title,(t,y),xytext=(-4,7 if y<12 else -15),textcoords="offset points",ha="right")
        ax.set_title("プレビュー"+name[-1],loc="left",fontweight="bold")
        ax.set_ylabel("露出倍率")
        ax.set_ylim(.5,17)
        ax.grid(color="#d5dbde",linewidth=.6)
    axes[-1].set_xlabel("松明をしまって岩壁を向いた撮影時点からの秒数")
    fig.suptitle("同じ石段で視線を往復したときの露出",fontweight="bold")
    fig.savefig(here/"cave-exposure.png",dpi=150)
    plt.close(fig)


def main():
    cave=[json_at(here/f"cave-iris{i}.json") for i in (7,8)]
    village=[json_at(here/f"window-iris{i}.json") for i in (7,8)]
    areas=("opening","stone-after-opening","opening-again")
    output={"village":{},"cave":{}}
    for group,records,shots in (("village",village,("original-beam","closed-beam","relocated-beam","rear-window","daylight")),
                                ("cave",cave,("unlit","warm","soul","empty-again",*areas,"placed-warm","back-in-forest"))):
        for shot in shots:
            out={}
            for i,rec in zip((7,8),records):
                d=rec["photos"][shot]
                out[str(i)]={k:d[k] for k in ("exposure","lampGain","sceneR","sceneG","sceneB","localLuminance","displayRGB","instantSky","worldTime","rain")}
            output[group][shot]=out
    poses=[]
    for rec in cave:
        run=here.parent/rec["path"]
        doc=json_at(run/"complete.json")
        for label in areas:
            obs=doc["results"][label]
            poses.append(obs["xyz"])
        assert doc["results"].get("completed")==["natural-cave"]
    assert max(math.dist(p,q) for p in poses for q in poses)<.12,poses
    output["cave"]["fixedFeet"]=poses
    (here/"comparison.json").write_text(json.dumps(output,indent=2)+"\n")
    plot_cave(cave,areas)
    gallery=Image.new("RGB",(2*576,3*360),(20,24,24))
    labels=("石段の奥から雨空を見る","岩壁に視線を戻す","手持ちの松明で岩を照らす")
    pen=ImageDraw.Draw(gallery);font=ImageFont.truetype(fontfile,20)
    for row,(shot,title) in enumerate(zip(("opening","stone-after-opening","warm"),labels)):
        for col,rec in enumerate(cave):
            photo=here.parent/rec["path"]/(shot+"-ingame.png")
            assert hashlib.sha256(photo.read_bytes()).hexdigest()==rec["photos"][shot]["sha256"]
            x,y=col*576,row*360
            gallery.paste(Image.open(photo).convert("RGB").resize((576,324),Image.Resampling.LANCZOS),(x,y))
            pen.text((x+10,y+326),f"プレビュー{7+col}　{title}",font=font,fill="white")
    gallery.save(here/"cave.jpg",quality=94)


if __name__=="__main__":
    main()
