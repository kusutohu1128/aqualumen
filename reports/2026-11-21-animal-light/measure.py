"""Compare matched Minecraft F2 and two bracketing private-display captures."""
from pathlib import Path
from hashlib import sha256
from statistics import mean
import json
from PIL import Image, ImageDraw, ImageFont, ImageStat

here=Path(__file__).resolve().parent
root=here.parents[1]
font_path="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def font(size):
    return ImageFont.truetype(font_path,size,index=0)

boxes={"wall":(608,263,638,281),"wall_control":(1000,295,1013,309),"cow_rump":(454,328,478,345),
       "cow_side":(367,377,393,387),"cow_leg":(381,429,389,440)}
light_names=["warm-empty","soul-empty","both-empty","warm-west","soul-west","both-west","warm-east","soul-east","both-east","both-restored"]
day_names=["day-white","day-red","day-white-roof","day-red-roof"]

def values(run, expected):
    base=here/run
    receipt=json.loads((base/"complete.json").read_text())
    assert receipt["complete"] and receipt["originalWorldAndConfigUnchanged"] and receipt["size"]==[1280,720]
    assert "RTX 3080 Ti" in receipt["gl"]["renderer"] and receipt["packSha256"]==expected
    result={}
    for name,shots in receipt["screenshots"].items():
        result[name]={}
        for tag,record in shots.items():
            path=base/f"{name}-{tag}.png"
            assert sha256(path.read_bytes()).hexdigest()==record
            with Image.open(path) as image:
                rgb=image.convert("RGB")
                result[name][tag]={k:[round(v,3) for v in ImageStat.Stat(rgb.crop(box)).mean] for k,box in boxes.items()}
    return result

def panel_canvas(cols,rows,width,height):
    return Image.new("RGB",(cols*width,rows*height),(25,28,30))

def pic(canvas,run,name,box,xy,extent,label,mark=None):
    with Image.open(here/run/f"{name}-ingame.png") as src:
        crop=src.convert("RGB").crop(box)
    if mark:
        x,y,r,b=boxes[mark]
        ImageDraw.Draw(crop).rectangle((x-box[0]-2,y-box[1]-2,r-box[0]+1,b-box[1]+1),outline=(255,250,204),width=2)
    size=(extent[0],extent[1]-38)
    canvas.paste(crop.resize(size,Image.Resampling.LANCZOS),xy)
    ImageDraw.Draw(canvas).text((xy[0]+10,xy[1]+size[1]+4),label,font=font(19),fill="white")

def main():
    archives=[root/"dist"/f"Aqualumen-1.9.0-preview.{i}.zip" for i in (5,6)]
    hashes=[sha256(p.read_bytes()).hexdigest() for p in archives]
    old,new=values("baseline-daylight",hashes[0]),values("c2",hashes[1])
    assert set(new)==set(light_names+day_names) and set(old)==set(day_names)
    for tag in ("ingame","x11-a","x11-b"):
        for region in ("cow_rump","cow_side","cow_leg"):
            white,red,covered_white,covered_red=[new[n][tag][region] for n in day_names]
            assert white[1]-red[1]>14 and (red[0]-red[1])-(white[0]-white[1])>9
            assert max(abs(a-b) for a,b in zip(covered_white,covered_red))<4
            assert max(abs(a-b) for a,b in zip(old["day-white"][tag][region],old["day-red"][tag][region]))<3
        def wall(name): return new[name][tag]["wall"]
        assert wall("both-empty")[0]-wall("both-west")[0]>27
        assert wall("both-empty")[2]-wall("both-east")[2]>17
        assert wall("warm-empty")[0]-wall("warm-west")[0]>25 and abs(wall("warm-empty")[0]-wall("warm-east")[0])<5
        assert wall("soul-empty")[2]-wall("soul-east")[2]>17 and abs(wall("soul-empty")[2]-wall("soul-west")[2])<5
        assert max(abs(a-b) for a,b in zip(wall("both-empty"),wall("both-restored")))<4
    (here/"measurements.json").write_text(json.dumps(dict(coordinates="top-left origin; half-open pixel rectangles in 1280x720; mean RGB8 after display mapping",
        boxes=boxes,preview5=old,preview6=new,sha256=hashes),indent=2)+"\n")
    wall=panel_canvas(2,2,560,342)
    for i,(name,label) in enumerate([("both-empty","二灯を点灯"),("both-west","牛が西側で暖色を遮る"),
                                     ("both-east","牛が東側で青い光を遮る"),("both-restored","牛が去った後")]):
        pic(wall,"c2",name,(300,183,940,531),(i%2*560,i//2*342),(560,342),label,"wall")
    wall.save(here/"two-shadows.jpg",quality=93)
    coat=panel_canvas(2,3,400,338)
    for i,(folder,n,label) in enumerate([("baseline-daylight","day-white","旧版　白い床"),("baseline-daylight","day-red","旧版　赤い床"),
                                          ("c2","day-white","新版　白い床"),("c2","day-red","新版　赤い床"),
                                          ("c2","day-white-roof","新版　白い床に屋根"),("c2","day-red-roof","新版　赤い床に屋根")]):
        pic(coat,folder,n,(266,251,554,467),(i%2*400,i//2*338),(400,338),label,"cow_rump")
    coat.save(here/"coat.jpg",quality=94)
if __name__=="__main__":
    main()
