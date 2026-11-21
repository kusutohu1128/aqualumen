"""Build a side-by-side figure and a short real-time sequence from ordinary Minecraft captures."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 21)
small = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 17)
states = (("warm_rain", "ランタン"), ("lamp_off", "消灯"), ("soul_rain", "魂のランタン"))
runs = [(root / "take-8", "従来の雨の照明"), (root / "take-9", "1.7.0  光源ごとの照明")]
width, height, band = 560, 315, 35

def frames(run, state):
    receipt = json.loads((run / "complete.json").read_text())
    assert not receipt["diagnosticShader"] and receipt["sourceUnchanged"]
    path = run / (state + ".mkv")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["samples"][state]["sha256"]
    buffer = subprocess.check_output([
        "ffmpeg", "-v", "error", "-threads", "2", "-i", str(path), "-filter_threads", "1",
        "-vf", f"scale={width}:{height}:flags=lanczos", "-pix_fmt", "rgb24",
        "-threads", "1", "-f", "rawvideo", "pipe:1"])
    seq = np.frombuffer(buffer, dtype=np.uint8).reshape(-1, height, width, 3)
    assert len(seq) == 32
    return seq

def label(image, xy, text, face=font):
    ImageDraw.Draw(image).text(xy, text, font=face, fill=(234,236,239))

def draw():
    still = Image.new("RGB", (width*3, (height+band)*2+38), "#172126")
    clip = root / "rain-lights.mp4"
    args = ["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",
            f"{width*2}x{height+band+36}","-framerate","8","-i","pipe:0","-c:v","libx264",
            "-threads","3","-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",str(clip)]
    with subprocess.Popen(args,stdin=subprocess.PIPE) as movie:
        for i,(state,title) in enumerate(states):
            group = [frames(run,state) for run,_ in runs]
            for j,(_,style) in enumerate(runs):
                x,y = width*i,38+(height+band)*j
                label(still,(x+12,y+4),style,small)
                still.paste(Image.fromarray(group[j][12]), (x,y+band))
            label(still,(width*i+12,3),title)
            for left,right in zip(*group):
                cell = Image.new("RGB",(width*2,height+band+36),"#172126")
                label(cell,(12,3),title)
                for j,frame in enumerate((left,right)):
                    label(cell,(width*j+12,40),runs[j][1],small)
                    cell.paste(Image.fromarray(frame),(width*j,band+36))
                movie.stdin.write(cell.tobytes())
        movie.stdin.close()
        assert movie.wait()==0
    still.save(root / "rain-lights.jpg",quality=94,subsampling=0)

if __name__ == "__main__":
    draw()
