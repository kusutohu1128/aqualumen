"""Read positions from ordinary F3 screenshots using the installed Minecraft font."""
import io
import json
import re
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from PIL import Image

@lru_cache(maxsize=1)
def font():
    root=Path(__file__).resolve().parents[3]
    runtime=json.loads((root/"reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    archive=next(f for f in runtime["cp"] if f.endswith("/minecraft-1.21.1-client.jar"))
    with ZipFile(archive) as z:
        providers=json.loads(z.read("assets/minecraft/font/include/default.json"))["providers"]
        spec=next(p for p in providers if p.get("file")=="minecraft:font/ascii.png")
        pixels=np.asarray(Image.open(io.BytesIO(z.read("assets/minecraft/textures/font/ascii.png"))).convert("RGBA"))[:,:,3]>127
    glyphs={" ":np.zeros((8,4),dtype=bool)}
    for y,line in enumerate(spec["chars"]):
        for x,char in enumerate(line):
            glyph=pixels[8*y:8*y+8,8*x:8*x+8]
            if glyph.any():
                width=np.where(glyph)[1].max()+1
                glyphs[char]=np.pad(glyph[:,:width],[(0,0),(0,1)])
    return glyphs

def row_text(rgb,prefix,alphabet):
    glyphs=font()
    label=np.hstack([glyphs[c] for c in prefix])
    # F3 text has a fixed 0xdddddd foreground at integer GUI scale.
    mask=(rgb[:min(1100,len(rgb)),:min(1600,rgb.shape[1]),:3]==221).all(axis=2)
    for scale in (2,3,4,1):
        bits=mask[scale//2::scale,scale//2::scale]
        for start in (2,1,3):
            area=bits[:,start:start+label.shape[1]]
            if len(area)<8:continue
            rows=np.lib.stride_tricks.sliding_window_view(area,8,axis=0).transpose(0,2,1)
            matches=np.where(np.count_nonzero(rows!=label,axis=(1,2))<=1)[0]
            for top in matches:
                line=bits[top:top+8]
                offset=start+label.shape[1]
                result=""
                while offset+8<line.shape[1] and len(result)<65:
                    for c in alphabet:
                        glyph=glyphs[c]
                        if np.array_equal(line[:,offset:offset+glyph.shape[1]],glyph):
                            result+=c
                            offset+=glyph.shape[1]
                            break
                    else:break
                    if result.endswith("    "):break
                return result.rstrip()
    return None

def target_block(rgb,scale=2):
    # Vanilla right-aligns each line of its targeted-block panel.
    glyphs=font()
    label=np.hstack([glyphs[c] for c in "Targeted Block: "])
    bits=(rgb[scale//2::scale,scale//2::scale,:3]==221).all(axis=2)
    bits=bits[:,bits.shape[1]//2:]
    powers=2**np.arange(8,dtype=np.uint8)
    mask=np.lib.stride_tricks.sliding_window_view(bits,8,axis=0)@powers
    needle=(label.T@powers).tobytes()
    for y,encoded in enumerate(mask):
        x=encoded.tobytes().find(needle)
        if x<0:continue
        x+=len(needle)
        pos=""
        for _ in range(35):
            for c in "0123456789-, ":
                glyph=glyphs[c]
                if np.array_equal(bits[y:y+8,x:x+glyph.shape[1]],glyph):
                    pos+=c
                    x+=glyph.shape[1]
                    break
            else:break
        values=re.findall(r"-?[0-9]+",pos)
        if len(values)==3:return tuple(map(int,values))
    return None

def target_flag(rgb,name,scale=2):
    # Vanilla draws targeted-block boolean values green (true) or red (false).
    glyphs=font()
    label=np.hstack([glyphs[c] for c in f"{name}: "])
    bits=(rgb[scale//2::scale,scale//2::scale,:3]==221).all(axis=2)
    half=bits.shape[1]//2
    bits=bits[:,half:]
    powers=2**np.arange(8,dtype=np.uint8)
    mask=np.lib.stride_tricks.sliding_window_view(bits,8,axis=0)@powers
    needle=(label.T@powers).tobytes()
    for y,encoded in enumerate(mask):
        x=encoded.tobytes().find(needle)
        if x<0:continue
        x+=len(needle)
        win=np.asarray(rgb[scale*y:scale*(y+8),max(0,scale//2+scale*(half+x)-4):scale//2+scale*(half+x)+20]).reshape(-1,3).astype(int)
        cand=win[win.max(1)-win.min(1)>60]
        if not len(cand):return None
        green=np.all(np.abs(cand-[85,255,85])<=40,axis=1).sum()
        red=np.all(np.abs(cand-[255,85,85])<=40,axis=1).sum()
        if green*2>len(cand):return True
        if red*2>len(cand):return False
        return None
    return None

def position(rgb):
    row=row_text(rgb,"XYZ: ","0123456789-./ ")
    if row:
        match=re.match(r"(-?[0-9]+\.[0-9]+) / (-?[0-9]+\.[0-9]+) / (-?[0-9]+\.[0-9]+)",row)
        if match:return tuple(map(float,match.groups()))
    return None

if __name__=="__main__":
    import sys
    for p in sys.argv[1:]:
        rgb=np.asarray(Image.open(p).convert("RGB"))
        print(p,position(rgb),row_text(rgb,"Block: ","0123456789- "))
