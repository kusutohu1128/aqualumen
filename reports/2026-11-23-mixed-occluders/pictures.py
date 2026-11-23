"""Make registered normal-render crops and a separate comparison of linear visibility."""
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont
from grid import HERE, check_record
from score import ROOM_ANCHOR, ROOM_SOURCE, WEIGHTS, face_from_geometry, integral, np, unpack

INK = "#f1f1ed"
MUTED = "#bbc7c6"
TEAL = "#82ddcf"
BACKGROUND = "#151c20"


def font(size):
    return ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size, index=0)


def label(draw, xy, text, size=20, color=INK):
    draw.text(xy, text, font=font(size), fill=color)


def photo(folder, stage):
    path = folder / (stage + "-ingame.png")
    check_record(folder, path)
    return Image.open(path).convert("RGB")


def wall():
    sheet = Image.new("RGB", (1160, 778), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    label(draw, (18, 6), "木陰の松明　幹と草ブロックが壁に落とす影", 29)
    crop_a = (570, 200, 716, 245)
    crop_b = (818, 201, 964, 246)
    measurements = {}
    for index, (run, title) in enumerate((("step-previous", "前の実験版"), ("step-polygon-ordinary", "今回の実験版"))):
        x = 16 + 575 * index
        label(draw, (x, 54), title, 22)
        touching = photo(HERE / run, "touching")
        separate = photo(HERE / run, "separate")
        measurements[run] = {}
        for stage, im, rect in (("touching", touching, (606,200,668,245)), ("separate", separate, (882,201,913,246))):
            luma = np.asarray(im.crop(rect)) @ WEIGHTS
            step = abs(np.diff(luma, axis=1)).max(axis=1)
            measurements[run][stage] = dict(crop=rect, rows=len(step), meanMaximumAdjacentStep=float(step.mean()),
                                            p95MaximumAdjacentStep=float(np.quantile(step,.95)),
                                            meanLeftMinusRight=float((luma[:,0]-luma[:,-1]).mean()))
        sheet.paste(touching.resize((552, 311), Image.Resampling.LANCZOS), (x, 88))
        draw.rectangle((x + crop_a[0]*552//1280, 88 + crop_a[1]*311//720,
                        x + crop_a[2]*552//1280, 88 + crop_a[3]*311//720), outline=TEAL, width=2)
        for row, (im, crop) in enumerate(((touching, crop_a), (separate, crop_b))):
            sheet.paste(im.crop(crop).resize((438,135), Image.Resampling.NEAREST), (x+57, 438+176*row))
    label(draw, (16, 402), "幹の横に草ブロックを置く　枠内の壁を3倍に拡大", 20, MUTED)
    label(draw, (16, 579), "草ブロックを斜めに移す　奥の壁と右壁の境を3倍に拡大", 20, MUTED)
    sheet.save(HERE / "paired-shadows.jpg", quality=96, subsampling=0)
    (HERE / "display.json").write_text(json.dumps(measurements, indent=2) + "\n")


def curve():
    stages = ("step-meter", "step-polygon-meter")
    coords, signals = [], []
    for name in stages:
        path = HERE / name / "separate-ingame.png"
        check_record(path.parent, path)
        tex, p, _ = unpack(path, 1)
        signals.append(tex[:,114,0,1] / 255.)
        coords.append(p[:,114:115])
    pos = coords[1]
    faces = face_from_geometry(pos, np.array([409.48,152.62,-405.95]))
    mask = (faces == 6) & (abs(pos[:,:,2] + 412.) < .006) & (abs(coords[0]-pos).max(axis=2) < .001)
    grid = np.zeros((64,64,64), np.uint8)
    for block in ([406,151,-410], [406,152,-410], [407,151,-409]):
        grid[tuple(block - ROOM_ANCHOR)] = 1
    ref = integral(pos, faces, mask, ROOM_SOURCE[0], ROOM_ANCHOR, grid)[:,0]
    start, end = 285, 321
    assert np.all(ref[start:end+1] >= 0)
    sheet = Image.new("RGB", (940,425), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    label(draw,(18,4),"草ブロックを斜めに置いたとき、壁から見える火の割合",26)
    label(draw,(18,47),"同じ壁の縦一列　ゲーム内の計測用画像と8,192本の独立した光線で比較",18,MUTED)
    left, right, top, bottom = 88, 895, 100, 333
    def xy(row, value):
        return (left+(row-start)*(right-left)/(end-start),bottom-value*(bottom-top))
    for fraction in (0,.25,.5,.75,1):
        _, y = xy(start, fraction)
        draw.line((left,y,right,y), fill="#40494d")
        label(draw,(24,y-13),str(int(fraction*100))+"%",16,MUTED)
    for row in (285,294,303,312,321):
        x, _ = xy(row, 0)
        label(draw,(x-14,bottom+1),str(row),15,MUTED)
    for values, color, width in ((signals[0],"#e8a467",3),(ref,"#ffffff",5),(signals[1],TEAL,2)):
        draw.line([xy(row,values[row]) for row in range(start,end+1)],fill=color,width=width)
    label(draw,(25,372),"途中の試作",17,"#e8a467")
    label(draw,(155,372),"参照",17)
    label(draw,(220,372),"修正版",17,TEAL)
    label(draw,(372,372),f"312行目　{signals[0][312]:.1%} → {signals[1][312]:.1%}（参照 {ref[312]:.1%}）",19)
    sheet.save(HERE / "wall-visibility.png")


def blind_review():
    sheet = Image.new("RGB",(1080,510),"#171b20")
    draw = ImageDraw.Draw(sheet)
    latin = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",21)
    for i, name in enumerate(("step-polygon-ordinary","step-previous")):
        im = photo(HERE / name, "touching")
        draw.text((i*540+6,2), "AB"[i], font=latin, fill="white")
        sheet.paste(im.resize((534,300),Image.Resampling.LANCZOS),(540*i,32))
        sheet.paste(im.crop((570,200,716,245)).resize((438,135),Image.Resampling.NEAREST),(540*i+48,353))
    sheet.save(HERE / "advisor-blind.jpg",quality=95,subsampling=0)


def survival(folder):
    labels = (("before-step", "白樺の根元"), ("after-step", "持ってきた土を置く"), ("torch-and-step", "幹の反対側に回る"))
    sheet = Image.new("RGB",(1350,313),BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for i,(name,title) in enumerate(labels):
        label(draw,(i*450+10,6),title,20)
        path = folder / (name + "-ingame.png")
        im = Image.open(path).convert("RGB")
        im.thumbnail((446,260),Image.Resampling.LANCZOS)
        sheet.paste(im,(i*450,45))
    sheet.save(HERE / "survival.jpg",quality=94,subsampling=0)


if __name__ == "__main__":
    if sys.argv[1:] == ["wall"]:
        wall()
        blind_review()
    elif sys.argv[1:] == ["curve"]:
        curve()
    else:
        survival(Path(sys.argv[1]))
