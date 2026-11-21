"""Decode the five interleaved scanlines of the Iris readback pack in actual Minecraft frames."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("--partial", action="store_true")
args = parser.parse_args()
run = args.run
plan = json.loads((run / "plan.json").read_text())
progress = json.loads((run / ("progress.json" if args.partial else "complete.json")).read_text())
if not args.partial:
    assert progress["sourceUnchanged"] and progress["diagnosticShader"]
    progress = progress["samples"]

def read_patch(rgb, rect):
    x0, y0, x1, y1 = rect
    patch = rgb[y0:y1,x0:x1]
    row = (len(rgb) - 1 - np.arange(y0,y1)) % 5
    assert all(np.count_nonzero(row == i) >= 2 for i in range(5))
    display, weather, film, encoded, material = (patch[row == i] for i in range(5))
    # Decode each sample before averaging the nonlinear lobe energy.
    # Code 255 carries only a lower bound. Decode its lower bin edge rather
    # than assigning an arbitrarily large radiance to a clipped channel.
    squared = np.minimum(encoded,254.5/255.0)**2
    energy = squared/(1.0-squared)
    values = {k: float(v) for k,v in zip(
        ("displayR","displayG","displayB","rain","wetness","rainBiome","access","film","roughness","lamp","sun","sky","meshSky","tag"),
        np.concatenate([np.mean(buf,axis=(0,1)) for buf in (display,weather,film,energy)] + [np.mean(material,axis=(0,1))[:2]]))}
    for i,key in enumerate(("lamp","sun","sky")):
        values[key+"SaturationFraction"]=float(np.mean(encoded[:,:,i]>=1.0))
    return values

data = {}
patches = [p for p in plan["patches"] if p["valid"]]
for phase, obs in progress.items():
    image = run / (phase + ".png")
    assert hashlib.sha256(image.read_bytes()).hexdigest() == obs["sha256"]
    rgb = np.asarray(Image.open(image).convert("RGB"),dtype=np.float64)/255
    assert rgb.shape == (720,1280,3)
    data[phase] = {p["name"]: read_patch(rgb,p["patch"]) for p in patches}
    m = data[phase].get("stone-mirror-a") or data[phase]["sun-mirror"]
    print(phase,round(obs["captureSeconds"],1),*(round(m[k],4) for k in ("rain","wetness","rainBiome","access","film","roughness","lamp","sky","meshSky","tag")))

if args.partial:
    raise SystemExit()
def sample(state,channel,patch="stone-mirror-a"):
    return data[state][patch][channel]
def s(state,channel):
    return sample(state,channel)
checks = {} if "sun-mirror" in data[next(iter(data))] else {
    "ray_hits_stone_and_smooth": all(abs(sample("rain25","tag",p["name"]) - (0.5 if p["block"]=="minecraft:stone" else 1.0))<0.03 for p in patches if p["block"] in ("minecraft:stone","minecraft:smooth_stone")),
    "rain_biome_at_measurement": s("rain25","rainBiome")>.98,
    "rain_builds_a_film": s("dry","film")<.01 and s("rain25","film")>.5,
    "roof_keeps_matched_stone_and_smooth_dry": all(sample("rain25","film",p["name"])<.025 for p in patches if not p["exposed"] and p["block"] in ("minecraft:stone","minecraft:smooth_stone")),
    "glass_and_stone_shelter": all(s(k,"access")<.05 and s(k,"film")<.025 and s(k,"wetness")>.8 for k in ("glass","stone")),
    "roof_opening_restores_film": s("open_again","access")>.9 and s("open_again","film")>.5,
    "lamp_off_and_back": s("lamp_back","lamp")>.01 and s("lamp_off","lamp")<.05*s("lamp_back","lamp") and abs(s("lamp_off","film")-s("lamp_back","film"))<.02,
    "drying_continues_after_rain": s("after9","rain")<.02 and s("after9","wetness")>s("after24","wetness")>s("after48","wetness")>s("after80","wetness"),
    "drying_removes_film": s("after9","film")>s("after48","film") and s("after80","film")<.08
}
if "sun-mirror" in data[next(iter(data))] and "wet" in data:
    def solar(phase,key):
        return sample(phase,key,"sun-mirror")
    checks={
        "world_patch_is_smooth_stone":all(solar(k,"tag")>.98 for k in data),
        "dry_control_has_no_coat":solar("day_dry","film")<.01 and solar("day_dry","sun")<.0001,
        "wet_surface_sees_sun":solar("wet","film")>.75 and solar("wet","sun")>.01,
        "vertical_wall_occludes_sun_without_sheltering_rain":solar("wall","sun")<.05*solar("wet","sun") and solar("wall","access")>.95 and abs(solar("wall","film")-solar("wet","film"))<.03,
        "removal_restores_direct_glint":solar("unwall","sun")>.01 and solar("unwall","sun")>12*solar("clearing","sun"),
        "mirror_view_brighter_than_side_view":min(solar("unwall","sun"),solar("back","sun"))>3*solar("side","sun"),
        "lamp_removed_in_every_phase":all(solar(k,"lamp")<.0001 for k in data)
    }
if "sunlit" in data:
    def solar(phase,key):
        return sample(phase,key,"sun-mirror")
    checks={
        "same_floor_and_no_lamp":all(solar(k,"tag")>.98 and solar(k,"lamp")<.0001 for k in data),
        "overcast_removes_direct_light":solar("overcast","sun")<.0001 and solar("overcast","film")>.75,
        "dry_has_no_glint":solar("day_dry","sun")<.0001 and solar("day_dry","film")<.01,
        "same_clear_sky":all(solar(k,"rain")<.01 for k in ("sunlit","shade","restored","side","back")),
        "wet_floor_stays_exposed_to_rain":all(solar(k,"access")>.95 and solar(k,"film")>.25 for k in ("sunlit","shade","restored")),
        "wall_blocks_bracketed_direct_light":min(solar("sunlit","sun"),solar("restored","sun"))>.01 and solar("shade","sun")<.05*min(solar("sunlit","sun"),solar("restored","sun")),
        "camera_angle_controls_glint":min(solar("restored","sun"),solar("back","sun"))>3*solar("side","sun")
    }
report = {"method":"Private Minecraft diagnostic PNG. RGB8 scanlines from the final program at the same analytical world patches in every phase. Values below one code point cannot resolve tiny signals.","checks":checks,"source":str(run.name),"patches":patches,"samples":progress,"measurements":data}
target = run / "measured.json"
target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(checks)
raise SystemExit(not all(checks.values()))
