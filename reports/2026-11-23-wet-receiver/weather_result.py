"""Compare the final, weather-composited image during real server rain changes."""
from hashlib import sha256
import json
import subprocess
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from weather_cycle import HERE,STEPS,SHA,SHIPPED_SHA

PATCHES={"warmReflection":(64,100,128,164),"nearbyStone":(320,72,384,136)}


def read(p):
    return json.loads(p.read_text())


def transition(folder,mode,info):
    movie=folder/(mode+"-floor.mkv")
    pts=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_packets",
        "-show_entries","packet=pts_time","-of","json",str(movie)]))["packets"]
    times=np.array([float(row["pts_time"]) for row in pts])
    assert times[0]==0 and np.all(np.diff(times)>0) and times[-1]>10.7 and 308<=len(times)<=331
    cap=cv2.VideoCapture(str(movie))
    rgb={k:[] for k in PATCHES}
    while True:
        ok,bgr=cap.read()
        if not ok:break
        assert bgr.shape==(200,480,3)
        for k,(x,y,r,b) in PATCHES.items():
            rgb[k].append(np.median(bgr[y:b,x:r,::-1],axis=(0,1)))
    cap.release()
    # The capture progress records when the server command enters the log.
    # Leave a full second on either side for the recorder and server sampling.
    split=info["lastMuxedFrameBeforeSwitch"]-1
    assert 65<=split<len(times)-65
    summary={}
    for k,values in rgb.items():
        values=np.array(values)
        assert len(values)==len(times)
        lum=values@np.array([.2126,.7152,.0722])
        steps=abs(np.diff(lum))
        index=int(np.argmax(steps))
        summary[k]=dict(beforeRGB=np.median(values[split-60:split-30],axis=0).tolist(),
                        endRGB=np.median(values[-31:-1],axis=0).tolist(),
                        maxStep=float(steps[index]),maxStepTime=float(times[index+1]),
                        p99Step=float(np.quantile(steps,.99)),endLuma=float(np.median(lum[-31:-1])))
    return dict(frames=len(times),durationSeconds=float(times[-1]),maxCaptureGapMs=float(np.max(np.diff(times))*1000),
                commandAtApproxFrame=split,crop=info["cropXYWH"],patches=summary)


def main():
    rows={}
    geometry=None
    canv=Image.new("RGB",(1080,548),"#142020")
    draw=ImageDraw.Draw(canv)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",15)
    for row,(label,digest) in enumerate((("reference",SHA),("wet-plane",SHIPPED_SHA))):
        folder=HERE/("weather-cycle-"+label)
        run=read(folder/"complete.json");pre=read(folder/"preflight.json")
        assert run["complete"] and not run["failure"] and run["originalWorldAndConfigUnchanged"] and run["shaderpackLogged"]
        assert run["packSha256"]==run["sourcePackShaNow"]==digest and run["stages"]==list(STEPS)
        assert run["size"]==[1600,900] and "RTX 3080 Ti" in run["gl"]["renderer"]
        assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
        g=read(folder/"geometry.json")
        if geometry is not None:assert geometry==g
        geometry=g
        log=(folder/"client.log").read_text()
        captures=read(folder/"weather-capture.json")
        rows[label]={}
        for mode,stage in (("rain","rain-start"),("clear","rain-stop")):
            ready=log.index("AQLAVA_READY_"+stage+"_END")
            switch=log.index("AQ_WEATHER_SWITCH_"+mode+"_END",ready)
            still=log.index("AQLAVA_STILL_"+stage+"_END",switch)
            assert ready<switch<still
            rows[label][mode]=transition(folder,mode,captures[mode])
        sampled={}
        for stage in STEPS:
            path=folder/(stage+"-ingame.png")
            assert sha256(path.read_bytes()).hexdigest()==run["screenshots"][stage]["ingame"]
            with Image.open(path) as photograph:
                cropped=photograph.convert("RGB").crop((0,676,480,876))
                sampled[stage]={k:np.median(np.asarray(cropped.crop(bounds)),axis=(0,1)).tolist()
                                for k,bounds in PATCHES.items()}
        rows[label]["stillPhotos"]=sampled
        for col,(stage,tag) in enumerate((("dry-start","雨を降らせる前"),("soaked","雨が続いた床"),("drying","雨が止んだ後"))):
            path=folder/(stage+"-ingame.png")
            assert sha256(path.read_bytes()).hexdigest()==run["screenshots"][stage]["ingame"]
            with Image.open(path) as im:
                thumb=im.convert("RGB").crop((0,520,640,900)).resize((360,214),Image.Resampling.LANCZOS)
            x,y=360*col,274*row
            canv.paste(thumb,(x,y))
            draw.text((x+6,y+223),("プレビュー13" if row==0 else "水膜補正版")+"　"+tag,font=font,fill="white")
    canv.save(HERE/"weather-cycle.jpg",quality=95)
    (HERE/"weather-cycle.json").write_text(json.dumps(dict(patchXYXYWithinCrop=PATCHES,runs=rows),indent=2)+"\n")
    for side,conditions in rows.items():
        print(side,[(k,conditions[k]["patches"]["warmReflection"]) for k in ("rain","clear")])


if __name__=="__main__":
    main()
