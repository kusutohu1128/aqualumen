"""Show the actual diagnostic receivers versus the dense disk on the same Iris frame."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from PIL import Image

here=Path(__file__).resolve().parent
folder=here/"penumbra-joint-vertex-centre"
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family":"Noto Sans CJK JP","font.size":9})
fig,axes=plt.subplots(3,4,figsize=(11.8,5.9),layout="constrained")
pal=plt.colormaps['viridis'].copy();pal.set_bad("#d8d9d6")
for row,(name,title) in enumerate([("column","柱"),("mixed-centre","柱と牛"),("column-leaf","柱と白樺の葉")]):
    pic=np.array(Image.open(folder/(name+"-ingame.png")).convert("RGB"))
    top,ref=np.split(pic[16:64,16:144].astype(float)/255,2)
    visible=top[:,:,2]==1
    assert np.allclose(ref[:,:,2],173/255)
    axes[row,0].imshow(pic[90:600,360:920]);axes[row,0].axis("off")
    axes[row,0].set_title(title+"の実画面")
    for col,(field,label) in enumerate([(top[:,:,0],"プレビュー12"),(top[:,:,1],"手持ち灯の試作"),(ref[:,:,:2].mean(2),"192本の基準")],1):
        ax=axes[row,col]
        last=ax.imshow(np.ma.masked_where(~visible,field),origin="lower",extent=[404.95,406.56,151.11,152.53],
                       interpolation="nearest",aspect="auto",cmap=pal,vmin=0,vmax=1)
        if row==0: ax.set_title(label)
        if col==1: ax.set_ylabel("壁の高さ Y（m）")
        else: ax.tick_params(labelleft=False)
        if row==2: ax.set_xlabel("壁の X（m）")
        else: ax.tick_params(labelbottom=False)
        ax.ticklabel_format(useOffset=False)
fig.colorbar(last,ax=axes[:,1:].ravel().tolist(),label="松明の光が届く割合",shrink=.89)
fig.suptitle("同じMinecraftフレームで測った手持ち灯の影　　灰色はカメラから見えない壁")
fig.savefig(here/"mixed-shadows.png",dpi=130)
