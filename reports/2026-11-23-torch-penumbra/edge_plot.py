"""Registered wall profiles beside their visible-source reference."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

here=Path(__file__).resolve().parent
data=json.loads((here/"room.json").read_text())
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family":"Noto Sans CJK JP","font.size":9,"axes.spines.top":False,"axes.spines.right":False})
fig,axes=plt.subplots(2,2,figsize=(9,5),layout="constrained",sharex="col")
for i,(side,pose) in enumerate([("left",405.9),("right",407.3)]):
    row=min(data["edges"][side],key=lambda r:min(abs(x-pose) for x in r["worldX"]))
    xs=row["worldX"]
    for label,title,color in (("preview12","プレビュー12","#ae572e"),("study","試作","#087e85")):
        axes[0,i].plot(xs,row[label]["shadowLoss"],label=title,color=color,lw=2)
    axes[0,i].set_title(["柱を左から見る","柱を右から見る"][i])
    axes[0,i].set_ylim(0,29)
    axes[1,i].plot(xs,row["disk"],lw=2,color="#415a65")
    axes[1,i].set_ylim(-.04,1.04)
    axes[1,i].set_xlabel("壁のワールド座標 X（m）")
    for ax in axes[:,i]:
        ax.grid(axis="y",alpha=.2)
        ax.ticklabel_format(useOffset=False)
axes[0,0].set_ylabel("柱を外したときの表示輝度差\n（Minecraftの実画面、0–255）")
axes[1,0].set_ylabel("光源が見える割合\n（幾何計算、8,192本）")
axes[0,0].legend()
fig.suptitle("手に持った松明がオークの柱を照らすときの半影")
fig.savefig(here/"wall-profiles.png",dpi=145)
