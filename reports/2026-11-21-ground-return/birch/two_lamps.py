"""Display-space controls for two independent lamps on the same shaded birch."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
SCENES=("ground-noon","ground-evening","ground-low-sun","air-shadow-backlit","air-sunlit-front","air-backlit-open","opaque-near-magenta")
ROLES=("off","warm","soul","both","both-wall","soul-wall","both-reopen")
TITLES=("消灯","松明","魂の松明","二本を点灯","松明側に石を積む","石を残して松明を消す","石を外して二本を点灯")
REGION=(775,760,818,811)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path);parser.add_argument("out",type=Path)
    args=parser.parse_args()
    args.out.mkdir(exist_ok=False)
    timing=json.loads((args.capture/"timing.json").read_text())
    assert timing["worldAndConfigUnchanged"] and "RTX 3080 Ti" in timing["renderer"]
    tiles=[]; rows={}; rgb={}
    for role,scene in zip(ROLES,SCENES,strict=True):
        base=args.capture/"capture"/scene
        row=json.loads(base.with_suffix(".json").read_text())
        field=row["opaque_fixture"]
        assert field["variant"]==role and field["actual_server_world_time"]==9800 and field["camera_eye_match"]
        assert field["forest_light"]["pre_sample_validation"]["passed"] and row["pack_sha256"]==timing["sha256"]
        assert row["shader_active"] and not row["shader_fallback"]
        assert row["actual_camera_position"]==[208.5,65.61999988555908,355.5] and row["actual_camera_rotation"]==[12.7,-2.]
        cleanup=json.loads((base.parent/(scene+"-fixture-cleanup.json")).read_text())
        assert cleanup["cleanup_complete"] and cleanup["forest_post_cleanup_validation"]["passed"]
        cells=cleanup["expected_cells"]; blocks={c["expected_block"] for c in cells}
        assert ("minecraft:torch" in blocks) == (role=="warm" or role.startswith("both"))
        assert ("minecraft:soul_torch" in blocks) == (role.startswith("soul") or role.startswith("both"))
        assert ("minecraft:stone" in blocks) == role.endswith("wall")
        im=Image.open(base.with_suffix(".png")).convert("RGB")
        rgb[role]=np.asarray(im.crop(REGION)).mean((0,1))
        rows[role]={"displayRGB":rgb[role].round(3).tolist(),"placed":cells,"timing":timing["samples"][role],
                    "sha256":hashlib.sha256(base.with_suffix(".png").read_bytes()).hexdigest()}
        tiles.append(im)
    warmDiff=rgb["both"]-rgb["soul"]
    afterWall=rgb["both-wall"]-rgb["soul-wall"]
    restored=rgb["both-reopen"]-rgb["both"]
    assert warmDiff[0]>20 and (rgb["soul"]-rgb["off"])[2]>40 and (rgb["both-wall"]-rgb["off"])[2]>40
    assert abs(afterWall[0]) < warmDiff[0]*.2 and max(abs(restored))<6
    (args.out/"measurements.json").write_text(json.dumps({"renderer":timing["renderer"],"sha256":timing["sha256"],
        "region":REGION,"rows":rows,"bothMinusSoulOpenRGB":warmDiff.round(3).tolist(),
        "bothMinusSoulBehindStoneRGB":afterWall.round(3).tolist(),"reopenedMinusFirstBothRGB":restored.round(3).tolist(),
        "units":"display RGB (0-255); sequential fixed-pose real Minecraft frames"},indent=2)+"\n")
    sheet=Image.new("RGB",(1472,837),"#17201d");pen=ImageDraw.Draw(sheet)
    path="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    head=ImageFont.truetype(path,34);body=ImageFont.truetype(path,22);small=ImageFont.truetype(path,18)
    pen.text((12,5),"木陰の白樺を、二つの灯りで照らす",font=head,fill="white")
    for i,(im,title) in enumerate(zip(tiles,TITLES,strict=True)):
        x=368*(i%4); y=66+380*(i//4)
        pen.text((x+6,y),title,font=body,fill="#f1efe7")
        sheet.paste(im.resize((364,205),Image.Resampling.LANCZOS),(x,y+36))
        crop=im.crop((730,670,1080,795))
        sheet.paste(crop,(x+5,y+246))
    x,y=1110,502
    pen.text((x,y),"同じ幹を拡大",font=body,fill="white")
    for line in ("普通の松明は暖色、","魂の松明は青色。","石を積んだ状態で松明を","消した場面も比較した。"):
        y+=40;pen.text((x,y),line,font=small,fill="#bdcdc4")
    sheet.save(args.out/"two-lamps.jpg",quality=94,subsampling=0)
if __name__=="__main__":
    main()
