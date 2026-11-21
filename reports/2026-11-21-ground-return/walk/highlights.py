"""Make a short captioned cut of the two real survival sessions at normal speed."""
import json
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
TMP=HERE.parents[2]/"build/ground-return"
sessions=("return-to-water","ridge-revisit")
def at(run,key):
    return records[run]["results"][key]["pose"]["t"]+.28
def on_trail(run,prefix):
    positions=json.loads((HERE/run/"positions.json").read_text())
    hits=[p["t"] for p in positions if p["label"]==prefix]
    return hits[0]+.3

if __name__=="__main__":
    records={s:json.loads((HERE/s/"complete.json").read_text()) for s in sessions}
    first,second=sessions
    clips=[
        (first,at(first,"old-oak"),2.1,"前回のセーブから再開"),
        (first,at(first,"placed-torch"),2.1,"木の下に松明を置く"),
        (first,at(first,"lift-soul"),2.1,"魂の松明を手に持つ"),
        (first,on_trail(first,"carry-soul-2"),4.0,"水辺へ歩く"),
        (first,at(first,"waters-edge"),2.1,"水辺"),
        (second,at(second,"saved-fire"),2.0,"保存して開き直した木陰"),
        (second,on_trail(second,"east-trail-3"),4.0,"松明を残して木立を出る"),
        (second,at(second,"outside-with-soul"),2.0,"離れた場所で魂の松明を持つ"),
        (second,at(second,"outside-empty"),2.0,"手に持った灯りをしまう"),
        (second,on_trail(second,"west-trail-2"),3.5,"同じ道を引き返す"),
        (second,at(second,"warm-on-return"),2.0,"木の下の松明に戻る")]
    font="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    with tempfile.TemporaryDirectory(dir=TMP) as d:
        temp=Path(d)
        for i,(run,start,length,caption) in enumerate(clips):
            assert 0<=start<start+length<records[run]["seconds"]
            filt=f"scale=960:540,drawtext=fontfile={font}:text='{caption}':fontsize=23:fontcolor=white:box=1:boxcolor=black@0.66:boxborderw=8:x=18:y=h-th-16"
            subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",HERE/run/"journey.mkv",
                "-t",str(length),"-vf",filt,"-an","-c:v","libx264","-preset","fast","-crf","19","-threads","3",
                temp/f"clip{i:02}.mp4"],check=True)
        (temp/"list").write_text("".join(f"file clip{i:02}.mp4\n" for i in range(len(clips))))
        subprocess.run(["ffmpeg","-nostdin","-v","error","-n","-f","concat","-safe","1","-i",temp/"list",
                        "-c","copy","-movflags","+faststart",HERE/"walk.mp4"],check=True)
    (HERE/"clips.json").write_text(json.dumps(clips,ensure_ascii=False,indent=2)+"\n")
