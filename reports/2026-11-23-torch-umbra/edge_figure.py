"""Plot the measured wall pixels beside the three-point and filled-disk visibility estimates."""

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

here = Path(__file__).resolve().parent
study = json.loads((here/"wall-edge.json").read_text())
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family":"Noto Sans CJK JP", "font.size":9,
                     "axes.spines.right":False, "axes.spines.top":False})
fig, axes = plt.subplots(2,2, figsize=(9.2,5.1), layout="constrained", sharex="col")
for i,(name,title) in enumerate((("left","柱を左から見る"),("right","柱を右から見る"))):
    row=study[name]
    # Use the single continuous visible edge nearest the camera's X.
    groups = [[]]
    for point in row["samples"]:
        if groups[-1] and point["worldX"]-groups[-1][-1]["worldX"] > .011:
            groups.append([])
        groups[-1].append(point)
    points=min(groups,key=lambda g:min(abs(p["worldX"]-row["cameraX"]) for p in g))
    x=np.array([p["worldX"] for p in points])
    axes[0,i].plot(x,[p["disk"] for p in points],color="#16798a",lw=2.3,label="円盤上の8,192点")
    axes[0,i].step(x,[p["threeTaps"] for p in points],color="#b15329",where="mid",lw=1.7,label="現行の3点")
    axes[0,i].set_title(title)
    axes[0,i].set_ylim(-.05,1.05)
    axes[1,i].plot(x,[p["clearY"]-p["oakY"] for p in points],color="#3e5658",lw=1.6)
    axes[1,i].set_xlabel("壁のワールド座標 X（m）")
    axes[1,i].set_ylim(0,28)
    for a in axes[:,i]:
        a.ticklabel_format(useOffset=False)
        a.grid(axis="y",alpha=.18)
axes[0,0].legend(fontsize=8)
axes[0,0].set_ylabel("光源が見える割合（計算値）")
axes[1,0].set_ylabel("柱を外したときの表示輝度差\n（実ゲーム、0〜255階調）")
fig.suptitle("手持ちの松明がオークの柱の縁に作る半影")
fig.savefig(here/"wall-edge.png",dpi=145)
