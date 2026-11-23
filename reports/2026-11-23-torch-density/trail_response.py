"""Compare both displays on geometrically registered terrain during the same turn and climb."""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
RUN = HERE.parent/"2026-11-21-animal-light/woodland/oak-night-pair"
ORDINARY = RUN.with_name("oak-night-trail")
W, H = 800, 450
WEIGHTS = np.array([.2126,.7152,.0722],dtype=np.float32)
MASKS = {"bark":(255,0,0), "riser":(0,255,0), "lower":(0,0,255), "upper":(0,255,255), "farTerrain":(255,0,255)}


def readout(pixel):
    r,g,tag = map(int,pixel)
    assert tag==173
    return round(32*(r*256+g)/65535,4)


def read_frame(frame):
    stock = frame[:H,:W]
    trial = frame[:H,W:]
    mask = frame[H:,:W]
    gains = [readout(frame[770,x]) for x in (1000,1450)]
    result = dict(gain=gains)
    category = {k:np.all(mask==rgb,axis=2) for k,rgb in MASKS.items()}
    # Encoded display luminance in 8-bit code values, for the same scene pixels.
    lumas = [im @ WEIGHTS for im in (stock,trial)]
    for name,selected in category.items():
        if selected.sum()<40:
            continue
        result[name] = dict(n=int(selected.sum()),p10p50p90=[
            np.percentile(luma[selected],[10,50,90]).round(2).tolist() for luma in lumas])
        if name in ("bark","riser","upper"):
            peaks=[np.max(im[selected],axis=1) for im in (stock,trial)]
            result[name]["brightestChannel"]=[dict(p99=float(np.percentile(peak,99)),
                                                   maximum=int(peak.max()), at255=int((peak==255).sum()))
                                              for peak in peaks]
    if "riser" in result and "upper" in result:
        # A step seen from below has its tread directly above its vertical face.
        distance=np.zeros((H,W),dtype=np.uint8)
        for dy in range(1,9):
            candidates=category["riser"][dy:] & category["upper"][:-dy] & (distance[dy:]==0)
            distance[dy:][candidates]=dy
        rows,cols=np.nonzero(distance)
        if rows.size>=20:
            above=rows-distance[rows,cols]
            result["upperLip"]=dict(n=int(rows.size),medianAbsDifference=[
                round(float(np.median(np.abs(luma[rows,cols]-luma[above,cols]))),2) for luma in lumas])
    return result


def verify(folder):
    receipt=json.loads((folder/"complete.json").read_text())
    assert receipt["cleanExit"] and not receipt["logErrors"] and not receipt["results"].get("failed")
    assert all(receipt[k] for k in ("labFilesUnchanged","modsUnchanged","previousSaveUnchanged","worldZipUnchanged"))
    assert not receipt["benchmarkSentinelPresent"] and receipt["savedLevel"]["allowCommands"]==0
    assert receipt["results"]["landing"]["xyz"][1]==64 and receipt["results"]["closeOak"]["xyz"][1]==63
    return receipt


def main():
    ordinary=verify(ORDINARY)
    receipt=verify(RUN)
    path=receipt["results"]
    assert receipt["packSha256"]=="15a06f14f9997b2f8a7dd249d14bf02281bb1799f24d52e8e4dfd7a2e3f22de1"
    assert receipt["revisit"]==ordinary["revisit"]
    stills={}
    for name in ("close-wood","above-step","waymark"):
        im=np.asarray(Image.open(RUN/(name+"-ingame.png")).convert("RGB"))
        stills[name]=read_frame(im)
    assert stills["close-wood"]["bark"]["n"]>1000
    start=path["turnStart"]-1.
    fps=12
    cmd=["ffmpeg","-v","error","-ss",str(start),"-i",str(RUN/"journey.mkv"),"-t",
         str(path["walkEnd"]-start),"-threads","1","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
    photo=None
    series=[]
    excluded=[]
    frame_index=0
    with subprocess.Popen(cmd,stdout=subprocess.PIPE) as ff:
        while data:=ff.stdout.read(W*H*12):
            frame=np.frombuffer(data,np.uint8).reshape(H*2,W*2,3)
            stamp=round(start+frame_index/fps,3)
            frame_index+=1
            # The debug HUD drawn after the shader tints the readout on landing.
            if any(frame[770,x,2]!=173 for x in (1000,1450)):
                excluded.append(stamp)
                continue
            rec=read_frame(frame)
            rec["videoSeconds"]=stamp
            series.append(rec)
            # Choose maximum visible riser coverage among frames with a measured top edge.
            if "upperLip" in rec and (photo is None or rec["riser"]["n"]>photo[0]["riser"]["n"]):
                photo=(rec,frame.copy())
        assert ff.wait()==0
    assert photo is not None
    turn_frame=photo[1]
    close=np.asarray(Image.open(RUN/"close-wood-ingame.png").convert("RGB"))
    sheet=Image.new("RGB",(1200,870),(27,31,34))
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",21)
    draw.text((12,5),"プレビュー10",font=font)
    draw.text((613,5),"色の強い光で露出を下げた試作",font=font)
    for im,y,title in [(close,40,"松明を持ってオークの幹に近づいたところ"),(turn_frame,440,"振り向いて草の段差に踏み出したところ")]:
        for i in (0,1):
            panel=Image.fromarray(im[:H,W*i:W*(i+1)])
            sheet.paste(panel.resize((600,338),Image.Resampling.LANCZOS),(600*i,y))
        draw.text((10,y+341),title,font=font)
    draw.text((12,825),"左右は同一フレーム。足場の集計には深度と保存地形から特定した画素を使用。",font=font)
    sheet.save(HERE/"night-trail.jpg",quality=93)
    report=dict(packs=[ordinary["packSha256"],receipt["packSha256"]],renderer=receipt["renderer"],
                stills=stills,stepFrame=photo[0],frames=series,hudObscuredSeconds=excluded,
                controls="One HDR image per frame, independent temporal histories. Half-size panels use identical texel centers. "
                         "Terrain mask uses visible opaque pixel world coordinates. Edge is a riser pixel at most eight pixels below the tread in the same screen column. "
                         "Video sampling is 12 Hz on the private 1600x900 display. Quantiles are gamma-encoded display luma, not scene radiance. "
                         "The route was traversed by scripted controls; human usability is not measured.")
    (HERE/"night-trail.json").write_text(json.dumps(report,indent=2)+"\n")
    print("wood",stills["close-wood"].get("bark"),stills["close-wood"]["gain"])
    print("step",photo[0])
    print("landing",stills["above-step"])


if __name__=="__main__":
    main()
