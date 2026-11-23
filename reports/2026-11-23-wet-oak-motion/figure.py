"""Render the measured grass luminance along each real direction of travel."""

import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

here = Path(__file__).resolve().parent
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update(
    {"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)
source = json.loads((here / "motion.json").read_text())
fig, axs = plt.subplots(1, 2, figsize=(10.8, 4.35), layout="constrained")
for ax, prefix, title in zip(axs, ["empty", "slow-empty"], ["通常の歩行", "しゃがみ歩き"]):
    for direction, name, col in (("east", "往路", "#23626d"), ("west", "復路", "#b64c24")):
        pts = source["legs"][prefix + "-" + direction]["series"]
        for field, style, tag in (("auto", "-", "通常露出"), ("fixed", "--", "固定露出")):
            ax.plot(
                [p["x"] for p in pts],
                [p[field] for p in pts],
                style,
                marker=".",
                markersize=3.5,
                color=col,
                lw=1.5,
                label=name + "・" + tag,
            )
    ax.axvline(568, ls=":", color="#50555a", lw=1)
    ax.set(xlabel="カメラのワールド座標 X（m）", title=title, xlim=(567, 569), ylim=(0, 80))
    ax.ticklabel_format(useOffset=False)
    ax.grid(axis="y", alpha=0.2)
axs[0].set_ylabel("草130地点の表示輝度中央値（0〜255）")
axs[1].legend(loc="lower right", fontsize=8, framealpha=0.94)
fig.suptitle("雨のオーク林の設置灯を、手ぶらで往復　｜　点線は照明格子の境界", fontsize=13)
fig.savefig(here / "wet-grass.png", dpi=155)
