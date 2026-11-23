"""Ordinary private survival continuation from the saved shaded oak."""
import argparse, fcntl, gzip, hashlib, json, math, os, re, shutil, string, subprocess, sys, tempfile, time, uuid
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "reports/2026-11-21-leaf-light/play"
sys.path.insert(0, str(ROOT / "reports/2026-11-21-rain-eaves/journey"))
sys.path.insert(0, str(ROOT / "tools"))
import hud            # noqa: E402
import route_fps      # noqa: E402
import ground_shadow_lab as g  # noqa: E402

STABLE_SHA = "c5d804e4a6776cf7df14b405f32a605d09451cab10aabb8b3fae4c5428c73af8"
AUTHORISED = {"34c151e670501acb3a1bd3de8cf4bcc4b809652882b3a0b4ce05a6f5c260f088": "Aqualumen-1.9.0-preview.6.zip"}
COMPILER = ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar"
COMPILER_SHA = "c51cda673efd3526645f9d532d4422f0b713772f85c95786795ab812d8ee5142"
OWN = ROOT / "build/animal-light/woodland"
run_root = Path(__file__).resolve().parent
site = json.loads((SRC / "site.json").read_text())


ap = argparse.ArgumentParser()
ap.add_argument("--trail",default="trail.json"); ap.add_argument("run"); ap.add_argument("pack", type=Path); ap.add_argument("world", type=Path)
ap.add_argument("--video", action="store_true"); ap.add_argument("--revisit-from")
ap.add_argument("--preflight", action="store_true"); ap.add_argument("--cache-source", type=Path)
ap.add_argument("--village", action="store_true", help="Continue the saved snowy village journey instead of the oak trail")
ap.add_argument("--play-checkpoint",action="store_true",help="Use the verified portable world ZIP as the actual starting save")
ap.add_argument("--move-window", action="store_true", help="Rebuild the windows of the saved spruce house in survival")
ap.add_argument("--visit-window", action="store_true", help="Inspect the remodeled house from the village path")
ap.add_argument("--exposure-walk", action="store_true", help="Walk between the village house and the exposed road")
ap.add_argument("--exposure-readout", action="store_true", help="Record the diagnostic strip in the private village copy")
ap.add_argument("--forest-cave", action="store_true", help="Descend the natural rock staircase on seed 20261123")
ap.add_argument("--return-oak", action="store_true", help="Return empty-handed to the persistent torch under the saved oak")
ap.add_argument("--isolate-oak",action="store_true",help="Separate the carried soul torch from the one saved behind the oak")
ap.add_argument("--cut-alcove",action="store_true",help="Mine a recess for a second light in the survival cave")
ap.add_argument("--night-trail", action="store_true", help="Walk from the lit oak to the raised grass path")
ap.add_argument("--oak-opening",action="store_true",help="Cut the lowest oak log and reuse it for a lantern post")
ap.add_argument("--forest-return-meter", choices=("stock","leaf","display","storm","storm-track","wet-motion","wet-components"), help="Read local reflection at the intact oak in the night trail copy")
ap.add_argument("--shore-trail",action="store_true",help="Walk from the saved oak lantern post to the lake in survival")
ap.add_argument("--meadow-shelter", action="store_true", help="Light a sheltered recess below the saved grazing meadow")
ap.add_argument("--shore-cave", choices=("survival","rain","camp-reference","camp-wet-plane","camp-niche","niche-birch","birch-step","birch-two-lights","birch-to-camp","niche-hand-cycle","widen-niche","display-sidestep","move-birch-torch","finish-birch-torch"), help="Continue the survival route from shore, camp or the lit birch")
ap.add_argument("--village-glass",choices=("forage","fit","porch-light","snow-trail","snow-screen","snow-home","window-view"),help="Gather dye, fit the window, light its porch or visit the snowfield")
args = ap.parse_args()
resume_window_view=args.village_glass=="window-view" and args.revisit_from in ("porch-window-dawn","porch-window-door-closed","hanging-street-lantern","home-street-window","east-stair-window")
if args.village_glass and (not args.village or args.revisit_from!={"forage":"lamp-road","fit":"house-poppy","porch-light":"house-red-window-r2","snow-trail":"red-window-porch-light","snow-screen":"snowfield-trail-lantern","snow-home":"dusk-glass-on-the-snow-trail","window-view":args.revisit_from if resume_window_view else "dusk-glass-home"}[args.village_glass] or
                           args.play_checkpoint!=(args.village_glass not in ("forage","snow-home") and not resume_window_view) or any((args.move_window,args.visit_window,args.exposure_walk,args.exposure_readout,args.shore_cave))):
    ap.error("The window outing continues the saved village and its verified dye run")
camp_replay=args.shore_cave in ("camp-reference","camp-wet-plane")
from_stone_camp=camp_replay or args.shore_cave in ("camp-niche","niche-birch")
shore_source="lake-to-stone-camp" if from_stone_camp else "lower-shore-torch"
if args.shore_cave=="niche-birch": shore_source="stone-torch-niche"
if args.shore_cave=="birch-step": shore_source="torch-birch-walk"
if args.shore_cave in ("niche-hand-cycle","widen-niche"): shore_source="row-scan-camp-walk"
if args.shore_cave in ("display-sidestep","move-birch-torch"): shore_source="stone-display-wider-camp"
if args.shore_cave=="finish-birch-torch": shore_source="cell-shadow-birch-relocation"
if args.shore_cave=="birch-to-camp": shore_source="raised-soul-torch"
if args.shore_cave=="birch-two-lights": shore_source="soil-step-and-torch"
if args.shore_cave and (not args.play_checkpoint or args.revisit_from!=shore_source or
                        any((args.village,args.forest_cave,args.forest_return_meter,args.shore_trail,args.meadow_shelter,
                             args.return_oak,args.isolate_oak,args.night_trail,args.oak_opening,args.exposure_readout))):
    ap.error(f"The stone overhang route starts at {shore_source}")
leaving_shelter = args.meadow_shelter and args.revisit_from == "meadow-shelter"
bank_screen = args.meadow_shelter and args.revisit_from == "meadow-lake-home"
shore_mining = args.meadow_shelter and args.revisit_from == "bank-light-at-dawn"
if args.meadow_shelter and (args.revisit_from not in ("lakeside-to-meadow", "meadow-shelter", "meadow-lake-home", "bank-light-at-dawn") or not args.play_checkpoint or
                            any((args.village, args.forest_cave, args.shore_trail, args.forest_return_meter,
                                 args.oak_opening, args.night_trail, args.isolate_oak, args.return_oak, args.exposure_readout))):
    ap.error("The meadow shelter continues the verified meadow trail archive")
pasture_lights=args.shore_trail and args.revisit_from=="lakeside-lanterns"
if args.shore_trail and (args.revisit_from not in ("oak-opening","lakeside-lanterns") or not args.play_checkpoint or any((args.village,args.forest_cave,args.night_trail,args.oak_opening,args.forest_return_meter,args.isolate_oak,args.return_oak))):
    ap.error("The shoreline route starts at the oak lantern post or the archived lakeside lanterns")
if args.forest_return_meter and (args.revisit_from!="oak-night-trail" or not args.play_checkpoint or any((args.village,args.forest_cave,args.oak_opening,args.night_trail,args.return_oak,args.isolate_oak,args.exposure_readout))):
    ap.error("The reflection meter uses the verified intact oak checkpoint")
finish_oak_post=args.oak_opening and args.revisit_from=="oak-opening-slabs"
if args.oak_opening and (not ((args.revisit_from=="oak-night-trail" and args.play_checkpoint) or
                              (finish_oak_post and not args.play_checkpoint)) or
                         any((args.village,args.forest_cave,args.return_oak,args.isolate_oak,args.night_trail,args.exposure_readout))):
    ap.error("The oak opening starts from the saved night-trail checkpoint")
if args.night_trail and (args.revisit_from!="two-flames-oak-r2" or not args.play_checkpoint or
                         any((args.village, args.forest_cave, args.return_oak, args.isolate_oak, args.exposure_readout))):
    ap.error("The night trail uses the verified two-light oak survival checkpoint")
if args.cut_alcove and (not args.forest_cave or args.exposure_readout): ap.error("The alcove belongs to the ordinary cave outing")
if args.return_oak and args.isolate_oak: ap.error("Select one oak outing")
if (args.return_oak or args.isolate_oak) and (args.village or args.forest_cave or not args.revisit_from):
    ap.error("The oak approach starts in a saved woodland world")
if not args.revisit_from and not args.forest_cave:
    ap.error("A previous save is required for this route")
if args.forest_cave and (args.village or args.play_checkpoint or args.exposure_walk):
    ap.error("The forest cave uses its own starter or saved cave run")
if args.exposure_walk and not args.village:
    ap.error("The road walk uses the saved village house")
if args.exposure_readout and not (args.village or args.forest_cave or args.isolate_oak):
    ap.error("Select a village, forest cave or isolated oak route for the meter")
if (args.move_window or args.visit_window) and (not args.village or args.play_checkpoint or (args.move_window and args.visit_window)):
    ap.error("Choose one village window action and a previous house save")
world_folder = "Aqualumen-Woodland"
village_source=ROOT/"reports/2026-11-21-settlement-light/playable"
if args.village:
    site=json.loads((village_source/"starter.json").read_text())
    world_folder=site["worldFolder"]
    run_root=ROOT/"reports/2026-11-22-ceiling-return/village"
    run_root.mkdir(exist_ok=True)
if args.forest_cave:
    run_root=ROOT/"reports/2026-11-22-forest-cave"
    site=json.loads((run_root/"starter.json").read_text())
    world_folder=site["worldFolder"]
if args.village or args.forest_cave:
    AUTHORISED["c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"]="Aqualumen-1.9.0-preview.7.zip"
W, H = 1600, 900
assert re.fullmatch(r"[a-z0-9-]+", args.run)
assert not args.revisit_from or re.fullmatch(r"[a-z0-9-]+", args.revisit_from)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")


def progress(msg):
    with (run_root / "progress.txt").open("a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


pack, world = args.pack.resolve(), args.world.resolve()
pack_sha, world_sha = sha(pack), sha(world)
eye_report = ROOT/"reports/2026-11-22-eye-adaptation"
if args.forest_return_meter:
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-canopy-return"))
    from pack import package,STOCK_SHA
    if args.forest_return_meter in ("storm","storm-track"):
        meter_path=ROOT/"dist/Aqualumen-1.9.0-preview.11.zip"
        assert pack_sha=="fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"
        meter_bytes=meter_path.read_bytes()
        sys.path.insert(0,str(ROOT/"reports/2026-11-23-leaf-tiles"))
    elif args.forest_return_meter in ("wet-motion","wet-components"):
        sys.path.insert(0,str(ROOT/"reports/2026-11-23-leaf-tiles"))
        sys.path.insert(0,str(ROOT/"reports/2026-11-23-wet-oak-motion"))
        from probe import package as wet_package
        meter_path,meter_bytes=wet_package(args.forest_return_meter=="wet-components")
    elif args.forest_return_meter=="display":
        sys.path.insert(0,str(ROOT/"reports/2026-11-23-leaf-tiles"))
        from packs import package as display_package
        meter_path,meter_bytes=display_package(comparison=True)
    else:
        meter_path,meter_bytes=package(args.forest_return_meter,True)
    assert meter_path==pack and meter_bytes==pack.read_bytes()
elif args.village_glass=="window-view":
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-camera-glass"))
    versions={"Aqualumen-Camera-Glass.zip":"2635806ad54b0a99e645b62d01a71d4cb310c63b4429778eaf217d1a54743dd3",
              "Aqualumen-Glass-View-Pass.zip":"0309eb7c180e1e4d27977463c438ab3fe135b2f5054a2c263eb6ca245de2b293"}
    assert pack.parent==ROOT/"dist" and versions[pack.name]==pack_sha
elif args.village_glass in ("snow-screen","snow-home"):
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-screen-windows"))
    packs={"Aqualumen-Window-Routing.zip":"4ad4d044c9b39b30929fbaa1d0878e42d10224a240243165ade74e8e6acda5e7",
           "Aqualumen-Window-Tiles.zip":"4a3f9b865ba9ddc727e8a0ff3e703c3843f6ca84c212d109d42d0e558fe0d802"}
    assert pack.parent==ROOT/"dist" and packs[pack.name]==pack_sha
elif args.village_glass=="snow-trail":
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-window-routing"))
    assert pack==ROOT/"dist/Aqualumen-Window-Routing.zip" and pack_sha=="4ad4d044c9b39b30929fbaa1d0878e42d10224a240243165ade74e8e6acda5e7"
elif args.village_glass=="porch-light":
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-pane-beam"))
    from beam_versions import PACKS
    name,digest=PACKS["control"]
    assert pack==ROOT/"dist"/f"Aqualumen-{name}.zip" and pack_sha==digest
elif args.village_glass:
    assert pack==ROOT/"build/stained-panes/Aqualumen-Stained-Panes.zip" and pack_sha=="e84240aba58a5905312c75b553a529f566dda0bf0a53f4769f731e50e634aa57"
elif args.shore_cave:
    tested = {"rain":("build/wet-receiver/Aqualumen-Wet-Receiver.zip","3e5608f94c0c53abe141f6e8ecc504d20143f13f39d8695844b3f6a86b2c5dcf"),
              "survival":("dist/Aqualumen-1.9.0-preview.13.zip","18e666ae93ada4daf0a31fb822c23e82dd2240bf581018d11c08a54f476fe385")}
    tested["camp-reference"]=tested["survival"]
    tested["camp-niche"]=tested["survival"]
    tested["niche-birch"]=("build/placed-penumbra/ordinary/Aqualumen-Placed-Penumbra-Study.zip","b224ea6f9424ad7dd8424f2c192e1708f97f734a802870cea42ebb722dcb4c02")
    tested["niche-hand-cycle"]=("build/torch-brick-scan/Aqualumen-Niche-Meter.zip","4f1a5290b4ed6acc9f242201f002fb1cfd4a5567cba39137e03246c59221fef7")
    if args.shore_cave=="niche-hand-cycle" and pack.name=="Aqualumen-Stone-Meter.zip":
        tested["niche-hand-cycle"]=("build/stone-display/Aqualumen-Stone-Meter.zip","3802f63d46ca49ac97e5f3113b18646d0f75e95d72786e21e87c6e7a6eeadd2a")
    if args.shore_cave=="niche-hand-cycle" and pack.name=="Aqualumen-Diffuse-Meter.zip":
        tested["niche-hand-cycle"]=("build/stone-display/Aqualumen-Diffuse-Meter.zip","a2635455d6a71bca255ad762d55bf1e960e5ac0eff5473963243c41773154c7d")
    tested["birch-to-camp"]=("build/torch-brick-scan/Aqualumen-Torch-rows.zip","2a69fd3773f3af3548bb0247db5903c3e1d1bf199d84e24cb72a4493636381c1")
    tested["birch-two-lights"]=("dist/Aqualumen-Torch-Shadow-Contours.zip","0ba3e7673ceef7d0f60529457e550e259006fe293b15390bcd3d38eebf500b2a")
    tested["birch-step"]=("build/mixed-occluders/ordinary/Aqualumen-Placed-Torch-Shadows.zip","9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1")
    tested["camp-wet-plane"]=("dist/Aqualumen-Wet-Plane-Study.zip","8df2a8fcd645d58f0423d8b9974f99a186022d345c44a2ef9404b05a9c6a52c2")
    tested["widen-niche"]=("build/stone-display/Aqualumen-Stone-Display.zip","98dc4b848a7d461d0a4ad1045e565edb97c739f3c40661fffc95df5bd574b53d")
    tested["display-sidestep"]=("build/stone-display/Aqualumen-Diffuse-Pair.zip","1d21920d5c47463d723e2efda6bae7f11f3ac7cfc7a50d7757d4ce52264a1ca3")
    if args.shore_cave=="niche-hand-cycle" and pack.name=="Aqualumen-Midtones-Meter.zip":
        tested["niche-hand-cycle"]=("build/stone-display/Aqualumen-Midtones-Meter.zip","0f0a06de7439ebbc979aeab90e756205b174ff56f5140581d0727181d5167e0e")
    if args.shore_cave=="display-sidestep" and pack.name=="Aqualumen-Midtones-Pair.zip":
        tested["display-sidestep"]=("build/stone-display/Aqualumen-Midtones-Pair.zip","47918fdda9d02e9e89fbb239182c77bbebf0543e38587a56a0e56ff1d1e9eedb")
    tested["move-birch-torch"]=("build/torch-cell-shadow/Aqualumen-Torch-Cell-Shadow.zip","14e849c5b54ee04db05c75216a75764e865d553b711e67b180ed328c6afb7db0")
    tested["finish-birch-torch"]=tested["move-birch-torch"]
    path,digest=tested[args.shore_cave]
    assert pack==ROOT/path and pack_sha==digest
elif shore_mining:
    study_root=ROOT/"build/visible-terrain"
    candidates={"Aqualumen-Visible-Terrain.zip":"0fd89fc4c8b3d638f6bc270c450d772817564559a4690cae01c10de78bd73a36",
                "Aqualumen-Ownership-Meter.zip":"aa82f618f9853b4c1bcd7b46dbf27223e130ea9b091938ceb591a63476c4a5c8"}
    assert pack.parent==study_root and candidates.get(pack.name)==pack_sha
elif bank_screen:
    assert pack==ROOT/"build/torch-penumbra/Aqualumen-Torch-Penumbra.zip"
    assert pack_sha=="4a0c68c66a5ded34e2d46ebe38d24c32177fbee2385271f0f01dd594aa34f096"
elif args.meadow_shelter:
    meadow_pack = (("Aqualumen-1.9.0-preview.12.zip", "be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2")
                   if leaving_shelter else
                   ("Aqualumen-Torch-Umbra.zip", "1b4ef25c23a9948ae0069e201f0de4fb14276e44869647a2215e9c0b26606a85"))
    assert pack == ROOT/"build/torch-umbra"/meadow_pack[0] and pack_sha == meadow_pack[1]
elif pasture_lights:
    assert pack==ROOT/"dist/Aqualumen-1.9.0-preview.11.zip" and pack_sha=="fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"
elif args.shore_trail:
    oak_stock="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    assert pack==ROOT/"dist/Aqualumen-1.9.0-preview.10.zip" and pack_sha==oak_stock
elif args.oak_opening:
    oak_stock="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    oak_packs={ROOT/"dist/Aqualumen-1.9.0-preview.10.zip":oak_stock,
               ROOT/"build/oak-shadow/Aqualumen-Solid-Slabs.zip":"de3225d1fd5ae469778293e8be4c974ce6f5f1060cef5fc01bfb73e92de61fe8"}
    assert pack in oak_packs and pack_sha==oak_packs[pack]
elif args.night_trail:
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-density"))
    if pack.name=="Aqualumen-1.9.0-preview.10.zip":
        assert pack==ROOT/"dist"/pack.name and pack_sha=="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    else:
        from trail_meter import PACK, diagnostic
        assert pack==PACK and pack.read_bytes()==diagnostic()
elif args.return_oak or (args.isolate_oak and not args.exposure_readout):
    assert pack == ROOT/"dist/Aqualumen-1.9.0-preview.8.zip"
    assert pack_sha == "2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72"
elif args.exposure_readout or ((args.exposure_walk or args.forest_cave) and pack.name=="Aqualumen-1.9.0-preview.8.zip"):
    sys.path.insert(0,str(eye_report))
    from meter import candidate, candidate_bytes, instrument, release, release_sha
    assert sha(release)==release_sha
    bark_readout=args.exposure_readout and (args.isolate_oak or
                    (args.forest_cave and pack.name=="Aqualumen-Bark-Response.zip"))
    if bark_readout:
        sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-density"))
        from bark_meter import diagnostic, PACK as bark_pack, MATERIAL as bark_material, RESPONSE as bark_response
        assert pack in (bark_pack,bark_material,bark_response)
        assert pack.read_bytes()==diagnostic(pack!=bark_pack,pack==bark_response)
        assert candidate.read_bytes()==candidate_bytes()
        if args.isolate_oak:
            assert args.revisit_from=="after-dusk-oak"
        else:
            assert pack==bark_response and not args.revisit_from
    if pack.name in ("Aqualumen-Window-Meter-8.zip",candidate.name):
        assert candidate.read_bytes()==candidate_bytes()
    if args.exposure_readout and not bark_readout:
        model={"Aqualumen-Window-Meter-7.zip":release,"Aqualumen-Window-Meter-8.zip":candidate}[pack.name]
        assert pack.parent==candidate.parent and pack.read_bytes()==instrument(model)
    elif not args.exposure_readout:
        assert pack==candidate
else:
    assert AUTHORISED.get(pack_sha) == pack.name, f"{pack.name} {pack_sha} not authorised"
assert sha(COMPILER) == COMPILER_SHA
orig = g.GAME.resolve()
original = {n: sha(orig / n) for n in ["config/iris.properties", "options.txt", "config/sodium-options.json"]}
mods = {n: sha(orig / "mods" / n) for n in g.lab.NORMAL_MODS}


def save_digest(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob("*")) if p.is_file() and p.name != "session.lock"}


from survival_client_log import client_errors, saved_without_errors

if args.revisit_from:
    previous_dir = (ROOT/"reports/2026-11-21-ground-return/walk" if args.revisit_from=="ridge-revisit" else run_root) / args.revisit_from
    if args.village and args.revisit_from=="village-to-plains": previous_dir=village_source/args.revisit_from
    previous = json.loads((previous_dir / "complete.json").read_text())
    previous_id = json.loads((previous_dir / "identity.json").read_text())
    assert previous["cleanExit"] and saved_without_errors(previous,previous_dir) and not previous["benchmarkSentinelPresent"]
    assert previous["worldZipSha256"] == world_sha
    prior_version=STABLE_SHA if args.village else "2fc286a1e07045eb0f7fc99a959a532161d521745d5939b29cb6acd4b48bcda3"
    previous_packs={pack_sha,prior_version}
    if args.shore_cave:
        previous_packs={tested["survival"][1] if from_stone_camp else "0fd89fc4c8b3d638f6bc270c450d772817564559a4690cae01c10de78bd73a36"}
        if args.shore_cave in ("niche-hand-cycle","widen-niche"): previous_packs={tested["birch-to-camp"][1]}
        if args.shore_cave in ("display-sidestep","move-birch-torch"): previous_packs={tested["widen-niche"][1]}
        if args.shore_cave=="finish-birch-torch": previous_packs={tested["move-birch-torch"][1]}
        if args.shore_cave=="birch-to-camp": previous_packs={tested["birch-two-lights"][1]}
        if args.shore_cave=="birch-two-lights": previous_packs={tested["birch-step"][1]}
        if args.shore_cave=="birch-step": previous_packs={tested["niche-birch"][1]}
    if args.meadow_shelter:
        previous_packs = ({"1b4ef25c23a9948ae0069e201f0de4fb14276e44869647a2215e9c0b26606a85"} if leaving_shelter else
                          {"fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"})
    if shore_mining:
        previous_packs={"4a0c68c66a5ded34e2d46ebe38d24c32177fbee2385271f0f01dd594aa34f096"}
    if bank_screen:
        previous_packs={"be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2"}
    if args.forest_return_meter: previous_packs={STOCK_SHA}
    if args.shore_trail: previous_packs={"a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"}
    if args.oak_opening:
        previous_packs={pack_sha} if finish_oak_post else {oak_stock}
        if finish_oak_post:
            assert pack.name=="Aqualumen-Solid-Slabs.zip" and len(previous["results"]["grassViews"])==6
    if args.isolate_oak and args.exposure_readout:
        previous_packs={sha(candidate)}
    if args.night_trail: previous_packs.add("2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72")
    if args.return_oak: previous_packs.update(AUTHORISED)
    if args.village_glass=="porch-light": previous_packs={"e84240aba58a5905312c75b553a529f566dda0bf0a53f4769f731e50e634aa57"}
    if args.village_glass=="window-view":
        if resume_window_view:
            failed=previous["results"]["failed"]
            assert len(failed)==1
            if args.revisit_from=="east-stair-window":
                assert "stalled before return-inside-with-view" in failed[0]["error"]
                previous_packs={versions["Aqualumen-Glass-View-Pass.zip"]}
            elif args.revisit_from=="home-street-window":
                assert "stalled before align-with-porch-door" in failed[0]["error"]
                previous_packs={versions["Aqualumen-Glass-View-Pass.zip"]}
            elif args.revisit_from=="hanging-street-lantern":
                assert abs(previous["savedPlayer"]["Pos"][2]-575.3)<.15 and previous["savedLevel"]["GameType"]==0
                previous_packs={versions["Aqualumen-Glass-View-Pass.zip"]}
            elif args.revisit_from=="porch-window-door-closed":
                assert previous["results"]["closedDoor"] and failed[0]["lastObservation"]["target"]==[-901,70,576]
                previous_packs={versions["Aqualumen-Glass-View-Pass.zip"]}
            else:
                assert failed[0]["lastObservation"]["target"]==[-902,71,576] and failed[0]["lastObservation"]["open"]
                previous_packs={versions["Aqualumen-Camera-Glass.zip"]}
        else:
            assert previous["results"]["returnedInside"]["xyz"][2]>576
            previous_packs={"4a3f9b865ba9ddc727e8a0ff3e703c3843f6ca84c212d109d42d0e558fe0d802"}
    if args.village_glass=="snow-home":
        assert previous["results"]["trailPanes"]==[[-896,71,507],[-895,71,507]] and previous["results"]["trailTorch"]==[-895,71,508]
        assert len(previous["results"]["failed"])==1 and "stalled before onto-porch" in previous["results"]["failed"][0]["error"]
        previous_packs={pack_sha}
    if args.village_glass=="snow-screen": previous_packs={"4ad4d044c9b39b30929fbaa1d0878e42d10224a240243165ade74e8e6acda5e7"}
    if args.village_glass=="snow-trail": previous_packs={"c84ea61f7ae5cc97872edaf6789bc5541297f4a253f7465d6e16dbc51b60443f"}
    if args.village_glass=="forage": previous_packs={"c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"}
    if args.village and (args.exposure_walk or args.exposure_readout):
        previous_packs.add("c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c")
    assert previous["packSha256"] in previous_packs
    if args.village or args.forest_cave: assert world_sha==site["sha256"]
    assert previous["savedPlayer"]["playerGameType"] == previous["savedLevel"]["allowCommands"] == 0
    assert previous_id["seed"] == site["seed"]
    saved_source = Path(previous_id["world"]).resolve()
    allowed_folders = ({world_folder, "Aqualumen-Homecoming", "Aqualumen-Window-House"}
                       if args.village else {world_folder, "Aqualumen-Woodland-Expedition"})
    if args.village_glass=="porch-light": allowed_folders.add("Aqualumen-Village-Poppy")
    if args.village_glass in ("snow-home","window-view"): allowed_folders.add("Aqualumen-Snowfield-Lantern")
    if resume_window_view: allowed_folders.add("Aqualumen-Snowfield-Red-Glass")
    if args.village_glass=="snow-screen": allowed_folders.add("Aqualumen-Lit-Red-Window")
    if args.village_glass=="snow-trail": allowed_folders.add("Aqualumen-Red-Window")
    if args.oak_opening or args.forest_return_meter or args.shore_trail: allowed_folders.update(("Aqualumen-Oak-Lights","Aqualumen-Oak-Night-Trail"))
    if pasture_lights: allowed_folders.add("Aqualumen-Oak-Lantern-Post")
    if args.meadow_shelter: allowed_folders.add("Aqualumen-Meadow-Trail" if leaving_shelter else "Aqualumen-Lakeside-Lanterns")
    if bank_screen: allowed_folders.add("Aqualumen-Meadow-Shelter")
    if shore_mining: allowed_folders.add("Aqualumen-Lake-Homecoming")
    if args.shore_cave: allowed_folders.add("Aqualumen-Low-Shore-Light" if from_stone_camp else "Aqualumen-Two-Sided-Shore")
    if args.shore_cave=="niche-birch": allowed_folders.add("Aqualumen-Stone-Camp")
    if args.shore_cave in ("niche-hand-cycle","widen-niche"): allowed_folders.add("Aqualumen-Birch-Two-Lights")
    if args.shore_cave in ("display-sidestep","move-birch-torch"): allowed_folders.add("Aqualumen-Birch-Camp-Path")
    if args.shore_cave=="finish-birch-torch": allowed_folders.add("Aqualumen-Widened-Torch-Niche")
    if args.shore_cave=="birch-to-camp": allowed_folders.add("Aqualumen-Birch-Soil-Step")
    if args.shore_cave=="birch-two-lights": allowed_folders.add("Aqualumen-Birch-Torch-Walk")
    if args.shore_cave=="birch-step": allowed_folders.add("Aqualumen-Torch-Niche")
    assert saved_source.name in allowed_folders and saved_source.parent==Path(previous["privateGameDir"]).resolve()/"saves"
    world_folder=saved_source.name
    assert saved_source.is_relative_to("/tmp") and not any(f.is_symlink() for f in saved_source.rglob("*"))
    if args.play_checkpoint:
        from zipfile import ZipFile
        checkpoint=json.loads((previous_dir/"save.json").read_text())
        archive=ROOT/checkpoint["archive"]
        assert archive.parent==ROOT/"dist" and sha(archive)==checkpoint["sha256"] and checkpoint["seed"]==site["seed"]
        restored=tempfile.TemporaryDirectory(prefix="aql-unpack-survival-")
        saved_source=Path(restored.name)
        world_folder=checkpoint["folder"]
        with ZipFile(archive) as z:
            assert {world_folder+"/"+n for n in checkpoint["members"]}==set(z.namelist())
            for n,digest in checkpoint["members"].items():
                dest=(saved_source/n).resolve()
                assert dest.is_relative_to(saved_source)
                data=z.read(world_folder+"/"+n)
                assert hashlib.sha256(data).hexdigest()==digest
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(data)
    source_player=previous["savedPlayer"]
    source_time=previous["savedLevel"]["Time"]
    source_metres=previous["walkMetres"]
else:
    from zipfile import ZipFile
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    from mcnbt import load_gz
    assert args.forest_cave and world_sha==site["sha256"]
    restored=tempfile.TemporaryDirectory(prefix="aql-forest-starter-")
    saved_source=Path(restored.name)
    with ZipFile(world) as archive:
        assert archive.namelist()==[world_folder+"/level.dat"]
        (saved_source/"level.dat").write_bytes(archive.read(archive.namelist()[0]))
    data=load_gz(saved_source/"level.dat")["Data"]
    assert data["WorldGenSettings"]["seed"]==site["seed"] and data["GameType"]==data["allowCommands"]==0
    source_player={k:data["Player"][k] for k in ("Pos","Rotation","playerGameType")}
    source_time=data["Time"]
    source_metres=0
saved_before = save_digest(saved_source)
out = run_root / args.run
out.mkdir()
if args.preflight:
    write(out / "preflight.json", {"pack": pack.name, "packSha256": pack_sha, "world": world_sha, "files": len(saved_before),
                                   "sourceTime": source_time})
    progress(f"preflight {args.run} ok"); print("preflight ok"); sys.exit(0)
write(out / "status.json", {"stage": "awaiting render lock"})
progress(f"{args.run}: waiting for exclusive render lock")
lock = open("/tmp/aql-render21-1000.lock", "a+b")
fcntl.flock(lock, fcntl.LOCK_EX)
t_lock = time.strftime("%H:%M:%S")
write(out / "status.json", {"stage": "running", "lockAcquired": t_lock})
progress(f"{args.run}: lock acquired {t_lock}")
base = Path(tempfile.mkdtemp(prefix="aql-canopy-woodland-"))
game = base / "minecraft"
for d in ("saves", "mods", "config", "shaderpacks"):
    (game / d).mkdir(parents=True)
for n in mods:
    shutil.copyfile(orig / "mods" / n, game / "mods" / n)
shutil.copyfile(COMPILER, game / "mods" / COMPILER.name)
assert {p.name for p in (game / "mods").iterdir()} == g.lab.NORMAL_MODS | {COMPILER.name}
shutil.copyfile(pack, game / "shaderpacks" / pack.name)
for n in ["config/iris.properties", "config/sodium-options.json"]:
    shutil.copyfile(orig / n, game / n)
iris = game / "config/iris.properties"
iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
opt = dict(g.lab.OPTIONS, fullscreen="false", maxFps="60", enableVsync="false", overrideWidth=str(W), overrideHeight=str(H), rawMouseInput="false",
           mouseSensitivity="0.5", guiScale="2", lang="en_us", forceUnicodeFont="false", pauseOnLostFocus="false", fov="0.0",
           fovEffectScale="0.0", bobView="false", reducedDebugInfo="false", autoJump="true")
(game / "options.txt").write_bytes(g.lab.replace_values((orig / "options.txt").read_bytes(), opt, ":"))
save = game / "saves" / world_folder
shutil.copytree(saved_source, save, ignore=shutil.ignore_patterns("session.lock"))
assert save_digest(save) == saved_before
if args.shore_cave=="niche-hand-cycle":
    from oak_approach import freeze_sky
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    assert base.parent==Path("/tmp") and save.parent==game/"saves" and not save.is_symlink()
    write(out/"frozen-sky.json",freeze_sky(save/"level.dat",source_time))
if args.shore_cave=="rain" or camp_replay:
    from oak_approach import freeze_sky
    sys.path.insert(0,str(ROOT/"reports/2026-11-23-leaf-tiles"))
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    from storm_walk import set_rain
    freeze_sky(save/"level.dat",source_time)
    write(out/"frozen-sky.json",set_rain(save/"level.dat",source_time))
if (args.isolate_oak and args.exposure_readout) or args.forest_return_meter in ("display","storm","storm-track","wet-motion","wet-components"):
    from oak_approach import freeze_sky
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    assert base.parent==Path("/tmp") and save.parent==game/"saves" and not save.is_symlink()
    weather=freeze_sky(save/"level.dat",68853 if args.forest_return_meter else 63746)
    if args.forest_return_meter in ("storm","storm-track","wet-motion","wet-components"):
        from storm_walk import set_rain
        weather=set_rain(save/"level.dat")
    write(out/"frozen-sky.json",weather)
revisit = {"sourceRun": args.revisit_from, "copiedFiles": len(saved_before), "sourceSavedPlayer": source_player,
           "sourceSavedTime": source_time, "sourceWalkMetres": source_metres}
cache = OWN / "driver-cache" / pack_sha[:16]
if args.cache_source and not cache.exists():
    cache.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(args.cache_source, cache)
    progress(f"driver cache copied from {args.cache_source} ({sum(f.stat().st_size for f in cache.rglob('*') if f.is_file())} bytes)")
cache.mkdir(parents=True, exist_ok=True)
guard_id = str(uuid.uuid4())
guard = base / "input-opt-in.json"
identity = {"run": guard_id, "game": str(game.resolve()), "world": str(save.resolve()), "worldZipSha256": world_sha, "seed": site["seed"]}
write(guard, identity); write(out / "identity.json", identity)
runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
DISPLAY_MIN = 240
vgl = Path((ROOT / "reports/2026-11-21-lava-light/runtime-v190/vgl-dir.txt").read_text().strip()) / "x/usr/lib"
assert (vgl / "libvglfaker.so").is_file() and (vgl / "libdlfaker.so").is_file()


def start_xvfb():
    for n in range(DISPLAY_MIN, DISPLAY_MIN + 40):
        if Path("/tmp/.X11-unix/X%d" % n).exists() or Path("/tmp/.X%d-lock" % n).exists():
            continue
        xl = (base / "xvfb.log").open("wb")
        pr = subprocess.Popen(["Xvfb", ":%d" % n, "-screen", "0", "%dx%dx24" % (W, H), "+extension", "GLX", "+extension", "RENDER", "-nolisten", "tcp", "-noreset"],
                              stdout=xl, stderr=xl, start_new_session=True)
        for _ in range(100):
            if Path("/tmp/.X11-unix/X%d" % n).exists() or pr.poll() is not None:
                break
            time.sleep(.1)
        if pr.poll() is None and Path("/tmp/.X11-unix/X%d" % n).exists():
            return pr, ":%d" % n
    raise RuntimeError("no free private display")


xvfb, display = start_xvfb()
assert int(display[1:]) >= DISPLAY_MIN and display != os.environ.get("DISPLAY")
env = {k: v for k, v in os.environ.items() if k not in ("WAYLAND_DISPLAY", "XAUTHORITY", "DISPLAY", "XDG_SESSION_TYPE", "LD_PRELOAD", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS")}
env.update(DISPLAY=display, ALSOFT_DRIVERS="null", __GL_SHADER_DISK_CACHE_PATH=str(cache), XDG_CACHE_HOME=str(base / "cache"),
           LD_PRELOAD="%s:%s" % (vgl / "libdlfaker.so", vgl / "libvglfaker.so"), VGL_DISPLAY="egl0", VGL_LOGO="0", VGL_COMPRESS="0", VGL_SPOIL="0", VGL_VERBOSE="1")
progress(f"{args.run}: private Xvfb {display}")
cmd = [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4", "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
       "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", "Woodwalker", "--version", "1.21.1", "--gameDir", str(game),
       "--assetsDir", str(orig.parents[2] / "assets"), "--assetIndex", "17", "--uuid", "00000000000040008000000000000308", "--accessToken", "0",
       "--userType", "legacy", "--width", str(W), "--height", str(H), "--quickPlaySingleplayer", world_folder]
logpath = out / "client.log"
obs, actions, fpsrec, stops = [], [], [], []
st = {"start": None, "wid": None, "debug": False, "proc": None, "hud": True}


def x(*a, timeout=6):
    return subprocess.check_output(["xdotool", *a], env=env, timeout=timeout, text=True, stderr=subprocess.DEVNULL).strip()


def log():
    return logpath.read_text(errors="replace")


def guard_ok():
    p = st["proc"]
    assert json.loads(guard.read_text()) == identity and p.poll() is None
    assert Path("/proc", str(p.pid), "cwd").resolve() == game.resolve()
    assert x("getwindowpid", st["wid"]) == str(p.pid) and x("getwindowfocus") == st["wid"]


def key(k):
    guard_ok(); x("key", k)


def hold(k, seconds):
    guard_ok(); x("keydown", k)
    try:
        time.sleep(seconds)
    finally:
        x("keyup", k)
    time.sleep(.25)


def click(button):
    guard_ok(); x("click", button); time.sleep(.5)


def mine(seconds):
    guard_ok()
    x("mousedown", "1")
    try:
        time.sleep(seconds)
    finally:
        x("mouseup", "1")
    time.sleep(.4)


def f3(active):
    if st["debug"] != active:
        key("F3"); time.sleep(.5 if active else .3); st["debug"] = active


def grab():
    d = subprocess.check_output(["ffmpeg", "-v", "error", "-f", "x11grab", "-window_id", st["wid"], "-i", display, "-frames:v", "1", "-threads", "1",
                                 "-pix_fmt", "bgr0", "-f", "rawvideo", "pipe:1"], env=env, timeout=8)
    assert len(d) == W * H * 4
    return Image.frombytes("RGB", (W, H), d, "raw", "BGRX")


def observe(label, keep=False):
    f3(True)
    for _ in range(6):
        im = grab(); rgb = np.asarray(im)
        pos = hud.position(rgb)
        ang = hud.row_text(rgb, "Facing: ", string.ascii_letters + "0123456789-.()/ ")
        m = re.search(r"\((-?[0-9.]+) / (-?[0-9.]+)\)", ang or "")
        if pos and m:
            break
        time.sleep(.3)
    else:
        im.save(out / "unreadable-hud.png"); raise RuntimeError("cannot read F3")
    rec = {"label": label, "t": round(time.monotonic() - st["start"], 2), "xyz": pos, "angle": list(map(float, m.groups())),
           "target": hud.target_block(rgb), "open": hud.target_flag(rgb, "open"), "fps": route_fps.fps(rgb[:80, :320])}
    if keep:
        f = f"f3-{len(obs):03d}-{label}.png"; im.save(out / f); rec["f3Image"] = f
    obs.append(rec); write(out / "positions.json", obs)
    if rec["fps"] is not None:
        fpsrec.append({"label": label, "fps": rec["fps"], "t": rec["t"]})
    f3(False)
    return rec


def turn(yaw, pitch, rec):
    dyaw = (yaw - rec["angle"][0] + 180) % 360 - 180
    dx = round(max(-470, min(470, dyaw / .15))); dy = round(max(-250, min(250, (pitch - rec["angle"][1]) / .15)))
    guard_ok(); x("mousemove_relative", "--", str(dx), str(dy)); time.sleep(.3)


def aim(point, label, want=None, tries=4):
    for _ in range(tries):
        o = observe(label)
        px, py, pz = o["xyz"]
        dx, dz = point[0] - px, point[2] - pz
        yaw = math.degrees(math.atan2(-dx, dz)); pitch = math.degrees(math.atan2(py + 1.62 - point[1], math.hypot(dx, dz)))
        d = ((yaw - o["angle"][0] + 180) % 360 - 180, pitch - o["angle"][1])
        if abs(d[0]) < .3 and abs(d[1]) < .3 and (want is None or o["target"] == want):
            return o
        turn(yaw, pitch, o)
    return observe(label + "-final")


def goto(wp, label, tol=.32):
    tx, ty, tz = wp
    for _ in range(26):
        o = observe(label)
        px, py, pz = o["xyz"]
        dx, dz = tx - px, tz - pz; d = math.hypot(dx, dz)
        if d < tol:
            return o
        heading = math.degrees(math.atan2(-dx, dz))
        error = (heading - o["angle"][0] + 180) % 360 - 180
        turn(heading, 0.0, o)
        if abs(error) > 65:
            continue
        climbing = ty > py + .35
        if climbing:
            guard_ok(); x("keydown", "space")
        try:
            hold("w", min(2.2 if climbing else 5.0, d) / 4.317 * .70)
        finally:
            if climbing: x("keyup", "space")
    raise RuntimeError(f"route stalled before {label}: {obs[-1]}")


def hide_hud(hidden):
    if st["hud"] == hidden:
        key("F1"); time.sleep(.4); st["hud"] = not hidden


def retain_f2(name, before):
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        new = set((game / "screenshots").glob("*.png")) - before
        if len(new) == 1:
            src = next(iter(new))
            if src.stat().st_size > 0 and src.read_bytes()[-8:-4] == b"IEND":
                shutil.copy2(src, out / f"{name}-ingame.png"); return f"{name}-ingame.png"
        time.sleep(.1)
    raise RuntimeError("no unique complete F2 screenshot for " + name)


def shot(name, still=1.0, f2=False):
    f3(False); hide_hud(True); time.sleep(still)
    grab().save(out / f"{name}.png")
    if f2:
        before = set((game / "screenshots").glob("*.png"))
        key("F2"); retain_f2(name, before)
    hide_hud(False)
    return f"{name}.png"


def attempt(fn, name, results):
    """Auxiliary action: on failure record the real world position and carry on."""
    try:
        fn()
        results.setdefault("completed", []).append(name)
    except Exception as e:  # noqa: BLE001
        results.setdefault("failed", []).append({"step": name, "error": repr(e)[:300], "lastObservation": obs[-1] if obs else None})
        progress(f"{args.run}: step {name} failed: {e!r:.200}")
        try:
            observe("after-failure-" + name, keep=True)
        except Exception:
            pass


def hotbar():
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    from mcnbt import load_gz
    players=list((saved_source/"playerdata").glob("*.dat"))
    assert len(players)==1
    return {str(i["Slot"]+1):i["id"] for i in load_gz(players[0])["Inventory"] if 0<=i["Slot"]<9}


def photograph_lights(prefix,point,already_facing=False):
    if not already_facing: aim(point,prefix)
    inventory=hotbar()
    controls=[("1","empty",None),("2","torch","minecraft:torch"),("3","soul-torch","minecraft:soul_torch"),("1","empty-restored",None)]
    assert all(inventory.get(k)==item for k,_,item in controls)
    photos=[]
    hide_hud(True)
    try:
        for k,label,item in controls:
            key(k); time.sleep(.7)
            before=set((game/"screenshots").glob("*.png"))
            key("F2")
            photos.append({"file":retain_f2(prefix+"-"+label,before),"key":k,"held":item,"t":round(time.monotonic()-st["start"],2)})
    finally:
        hide_hud(False)
    return photos


def trace_herd():
    import trail
    results["inventoryKeys"]=hotbar()
    if args.revisit_from=="pasture":
        results["oakPhotos"]=photograph_lights("oak",(602.8,70.,367.5))
    series=[]
    for leg in range(16):
        player_obs=observe("animal-trail-"+str(leg))
        # A single-player pause flushes the integrated server's normal save.
        offset=len(log())
        key("Escape")
        try:
            deadline=time.monotonic()+6
            while "Saving and pausing game" not in log()[offset:] and time.monotonic()<deadline:
                time.sleep(.15)
            assert "Saving and pausing game" in log()[offset:], "single-player pause unconfirmed"
            time.sleep(.7)
            route=trail.build(args.revisit_from,save,player_obs["xyz"],True)
        finally:
            key("Escape");time.sleep(.35)
        write(out/("herd-route-%02d.json"%leg),route)
        points=route["waypoints"]
        target=route["targetCow"]
        pos=target["position"]
        feet=player_obs["xyz"]
        dx,dz=pos[0]-feet[0],pos[2]-feet[2]
        distance=math.hypot(dx,dz)
        if distance<12. and trail.visible(tuple(map(math.floor,feet)),pos):
            yaw=math.degrees(math.atan2(-dx,dz))
            pitch=math.degrees(math.atan2(feet[1]+1.62-pos[1]-.9,distance))
            click("2")
            point=(pos[0],pos[1]+.9,pos[2])
            frame=aim(point,"face-grazing-"+str(leg),tries=6)
            if abs((yaw-frame["angle"][0]+180)%360-180)>1 or abs(pitch-frame["angle"][1])>1:
                continue
            photos=photograph_lights("graze-%02d"%leg,pos,True)
            series.append(dict(cow=target,range=distance,feet=feet,actualPose=frame,photos=photos))
            results["grazingSeries"]=series
            write(out/"sightings.json",series)
            if len(series)>=4 or len(series)>=2 and distance<4.:return
        if len(points)==1: continue
        for i,wp in enumerate(points[1:4]):
            goto(wp,"herd-%02d-%d"%(leg,i),.4)
    raise RuntimeError("herd kept moving beyond sight during the walk")


with logpath.open("xb") as stream:
    proc = subprocess.Popen(cmd, cwd=game, env=env, stdout=stream, stderr=stream, start_new_session=True)
    st["proc"] = proc
    video = vlog = strip = None
    results = {}
    try:
        dl = time.monotonic() + 900
        while "logged in with entity id" not in log():
            assert proc.poll() is None and time.monotonic() < dl, "never joined"
            time.sleep(.5)
        t_join = time.monotonic()
        assert "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in log() and "Using shaderpack: " + pack.name in log()
        dl = time.monotonic() + 900
        while "contact bridge initialized" not in log():
            assert proc.poll() is None and time.monotonic() < dl and "disabling shaders" not in log().lower(), "pipeline"
            time.sleep(.6)
        pipeline_s = round(time.monotonic() - t_join, 1)
        progress(f"{args.run}: joined, pipeline ready {pipeline_s}s")
        time.sleep(6)
        ids = x("search", "--all", "--onlyvisible", "--pid", str(proc.pid), "--name", "Minecraft").split()
        assert len(ids) == 1
        st["wid"] = ids[0]; x("windowfocus", "--sync", st["wid"]); guard_ok()
        x("mousemove", "--window", st["wid"], "800", "450"); time.sleep(.5)
        st["start"] = time.monotonic()
        if args.exposure_readout:
            from house import record_strip
            strip=record_strip(out,display,env)
            strip.__enter__()
        if args.video:
            vlog = (out / "video.log").open("xb")
            pair = args.night_trail and pack.name=="Aqualumen-Night-Trail-Pair.zip"
            video_options = (["-c:v","ffv1","-threads","3","-pix_fmt","bgr0"] if pair else
                             ["-c:v","libx264","-preset","veryfast","-crf","20","-threads","3","-pix_fmt","yuv420p"])
            video = subprocess.Popen(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-framerate", "12" if pair else "24",
                                      "-window_id", st["wid"], "-i", display, *video_options, str(out / "journey.mkv")],
                                     stdin=subprocess.PIPE, stdout=vlog, stderr=vlog, env=env)
        first = observe("spawn", keep=True)
        assert math.dist(first["xyz"], revisit["sourceSavedPlayer"]["Pos"]) < .03, (first, revisit)
        shot("spawn-first-camera")
        key("1")
        # 1. prove that input really turns the camera before any long walk
        ok = False
        for attempt_no in range(4):
            o = observe(f"yaw-proof-{attempt_no}")
            turn(o["angle"][0] + 20, 0.0, o)
            o2 = observe(f"yaw-proof-{attempt_no}-after")
            moved = abs((o2["angle"][0] - o["angle"][0] + 180) % 360 - 180)
            results.setdefault("yawProof", []).append({"before": o["angle"], "after": o2["angle"], "deg": round(moved, 2)})
            if moved > 5:
                ok = True; break
            x("mousemove", "--window", st["wid"], "800", "450"); click("2")   # middle click captures the mouse without attacking in survival
        progress(f"{args.run}: yaw proof ok={ok} {results['yawProof'][-1]}")
        assert ok, "mouse look does not change yaw on the private display"
        if not (args.village or args.forest_cave or args.return_oak or args.isolate_oak or args.night_trail or args.oak_opening or args.forest_return_meter or args.shore_trail or args.meadow_shelter or args.shore_cave):
            path=json.loads((run_root/args.trail).read_text())
            assert path["previous"]==args.revisit_from
        def outing():
            key("8")
            if args.revisit_from=="ridge-revisit":
                o=aim((561.5,63.35,422.5),"check-saved-fire",want=(561,63,422))
                assert o["target"]==(561,63,422)
                shot("saved-oak",f2=True)
            key("3")
            points=path["waypoints"]
            idx=min(range(len(points)),key=lambda i:math.dist(points[i],first["xyz"]))
            for i,point in enumerate(points[idx+1:],idx+1):
                position=goto(point,"trail-"+str(i),.42)
                if i in (8,26,38):
                    aim(points[min(i+3,len(points)-1)],"look-ahead")
                    shot("trail-"+str(i),f2=True)
            results["lastWaypoint"]=position if idx+1<len(points) else first
            sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
            from mcnbt import Region
            cows=[]
            for filename in (save/"entities").glob("*.mca"):
                r=Region(filename)
                for cx,cz in r.present():
                    for e in r.chunk(cx,cz).get("Entities",[]):
                        if e["id"]=="minecraft:cow":
                            cows.append(e["Pos"])
            point=min(cows,key=lambda pos: math.dist(pos,points[-1]))
            results["nearestSavedCow"]=point
            for slot,tag in [("1","empty-hand"),("3","soul-light"),("2","warm-light")]:
                key(slot)
                results[tag]=aim((point[0],point[1]+.9,point[2]),tag)
                shot(tag,1.2,f2=True)
            key("8")
            # Photograph neighbouring slopes too; grazing animals can leave the saved position.
            for angle in (-55,0,55):
                o=observe("pasture-pan")
                yaw=results["empty-hand"]["angle"][0]+angle
                turn(yaw,3,o)
                shot("pan-"+str(angle),f2=True)
        if args.village:
            sys.path.insert(0,str(run_root))
            from return_home import visit, relight, move_window, see_window
            if args.village_glass:
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-stained-panes"))
                if args.village_glass=="forage":
                    from village import forage
                    attempt(lambda: forage(saved_source,results,aim,goto,shot,key,click,observe),"bring-a-poppy-home",results)
                elif args.village_glass=="porch-light":
                    from porch import light_window
                    attempt(lambda: light_window(results,aim,goto,shot,key,click,observe),"light-the-window-porch",results)
                elif args.village_glass=="window-view":
                    from window_walk import visit_pane, view_street, porch_to_window, through_door
                    view={"east-stair-window":through_door,"home-street-window":porch_to_window,"hanging-street-lantern":porch_to_window,"porch-window-door-closed":view_street}.get(args.revisit_from,visit_pane)
                    attempt(lambda: view(results,aim,goto,shot,key,click,observe,x,guard_ok),"view-the-porch-lights-through-the-window",results)
                elif args.village_glass=="snow-home":
                    from windbreak import enter_from_porch
                    attempt(lambda: enter_from_porch(results,aim,goto,shot,key,click,observe,x,guard_ok),"enter-after-the-glass-outing",results)
                elif args.village_glass=="snow-screen":
                    from windbreak import build_screen
                    attempt(lambda: build_screen(saved_source,results,aim,goto,shot,key,click,mine,observe),"glass-beside-the-snowfield-lantern",results)
                elif args.village_glass=="snow-trail":
                    from snow_trail import mark_trail
                    attempt(lambda: mark_trail(saved_source,results,aim,goto,shot,key,click,observe),"light-the-snowfield-trail",results)
                else:
                    from fit_window import fit
                    attempt(lambda: fit(results,aim,goto,shot,key,click,x,guard_ok,grab,out),"craft-and-fit-the-red-window",results)
            elif args.move_window:
                attempt(lambda: move_window(results,aim,shot,key,click,mine,hotbar),"move-house-window",results)
            elif args.visit_window:
                attempt(lambda: see_window(results,aim,goto,shot,key,click,mine,observe),"window-from-porch",results)
            elif args.play_checkpoint and not args.exposure_walk:
                results["archiveLoaded"]=checkpoint["sha256"]
                attempt(lambda: relight(results,aim,shot,key,click),"relight-at-home",results)
            elif not args.exposure_walk:
                attempt(lambda: visit(village_source,first,results,aim,goto,shot,key,click,observe,hotbar),"snow-village-homecoming",results)
            if args.exposure_walk:
                sys.path.insert(0,str(eye_report))
                from house import walk
                attempt(lambda: walk(village_source,first,results,aim,goto,shot,key,click,observe),"porch-to-road-and-back",results)
        elif args.shore_cave:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-wet-receiver"))
            from headland import carry, revisit_camp
            if args.shore_cave=="niche-hand-cycle":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-brick-scan"))
                from camp_walk import sample_lamps
                attempt(lambda: sample_lamps(first,results,hotbar,aim,shot,key,turn,observe),"same-niche-hand-cycle",results)
            elif args.shore_cave=="finish-birch-torch":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-cell-shadow"))
                from birch_move import finish
                attempt(lambda: finish(results,hotbar,aim,goto,shot,key,click),"finish-the-birch-torch-relocation",results)
            elif args.shore_cave=="move-birch-torch":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-cell-shadow"))
                from birch_move import relocate
                attempt(lambda: relocate(saved_source,first,results,trail,hotbar,aim,goto,shot,key,click),
                        "move-the-saved-birch-torch",results)
            elif args.shore_cave=="display-sidestep":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-stone-display"))
                from camp_motion import record as record_sidestep
                attempt(lambda: record_sidestep(first,results,hotbar,aim,observe,hold,key,hide_hud,out,display,env,st["wid"]),
                        "paired-sidestep-along-the-niche",results)
            elif args.shore_cave=="widen-niche":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-stone-display"))
                from alcove import widen
                attempt(lambda: widen(first,results,hotbar,aim,goto,shot,key,mine),"widen-the-torch-niche",results)
            elif args.shore_cave=="birch-to-camp":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-brick-scan"))
                from camp_walk import return_to_camp
                attempt(lambda: return_to_camp(saved_source,first,results,trail,hotbar,aim,goto,shot,key,click),
                        "mark-the-return-path-to-the-stone-niche",results)
            elif args.shore_cave=="birch-two-lights":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-shadow-integral"))
                from birch_lights import place
                attempt(lambda: place(first,results,hotbar,aim,goto,shot,key,click),
                        "soul-torch-on-the-soil-step",results)
            elif args.shore_cave=="birch-step":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-mixed-occluders"))
                from birch_step import place
                attempt(lambda: place(first,results,hotbar,aim,goto,shot,key,click),
                        "soil-step-at-the-lit-birch",results)
            elif args.shore_cave=="niche-birch":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-placed-penumbra"))
                from birch_walk import walk as birch_walk
                attempt(lambda: birch_walk(saved_source,first,results,trail,hotbar,aim,goto,shot,key,click),
                        "place-a-torch-beside-the-birch",results)
            elif args.shore_cave=="camp-niche":
                sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-open-volume"))
                from camp_niche import cut
                attempt(lambda: cut(first,results,aim,goto,shot,key,click,mine,hotbar),
                        "cut-and-light-a-stone-niche",results)
            elif camp_replay:
                attempt(lambda: revisit_camp(first,results,aim,goto,shot,key,hotbar,turn,observe,hold,out,st,env),
                        "cross-the-lit-camp",results)
            else:
                attempt(lambda: carry(saved_source,first,results,trail,aim,goto,shot,key,click,hotbar,turn,observe,
                                  hold,out,st,env), "light-the-stone-overhang",results)
        elif shore_mining:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-visible-terrain"))
            from mining import visit as lower_post
            attempt(lambda: lower_post(saved_source,first,results,trail,aim,goto,shot,key,click,mine,hotbar,
                                       out,game,st,env,retain_f2),"lower-the-shore-torch",results)
        elif bank_screen:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-torch-penumbra"))
            from bank import visit as build_screen
            attempt(lambda: build_screen(saved_source,first,results,trail,aim,goto,shot,key,click,mine,hotbar),
                    "build-two-sided-shore-light",results)
        elif args.meadow_shelter:
            import trail
            sys.path.insert(0, str(ROOT/"reports/2026-11-23-torch-umbra"))
            from shelter import explore, return_to_lake
            trip = return_to_lake if leaving_shelter else explore
            attempt(lambda: trip(saved_source,first,results,trail,aim,goto,shot,key,click,mine,hotbar),
                    "open-exit-and-follow-lamps-home" if leaving_shelter else "dig-and-light-meadow-shelter",results)
        elif pasture_lights:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-wet-oak-motion"))
            from pasture import walk as pasture_walk
            attempt(lambda: pasture_walk(saved_source,first,results,trail,aim,goto,shot,key,click,hotbar),"mark-the-pasture-route",results)
            if "mark-the-pasture-route" in results.get("completed",[]):
                attempt(trace_herd,"watch-cattle-in-the-meadow",results)
        elif args.shore_trail:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-leaf-tiles"))
            from shore_walk import walk as shore_walk
            attempt(lambda: shore_walk(saved_source,first,results,trail,aim,goto,shot,key,click,mine,hotbar),"light-two-shores-and-open-inlet",results)
        elif args.forest_return_meter in ("wet-motion","wet-components"):
            import trail
            from wet_motion_walk import walk as wet_walk
            attempt(lambda: wet_walk(saved_source,first,results,trail,turn,goto,observe,key,hold,shot,hotbar,display,st["wid"],env,out,guard_ok,x),"wet-oak-out-and-back",results)
        elif args.forest_return_meter in ("storm","storm-track"):
            import trail
            from storm_walk import walk as walk_in_rain
            attempt(lambda: walk_in_rain(saved_source,first,results,trail,turn,goto,observe,f3,key,hold,shot,hotbar,display,st["wid"],env,out,tracking=args.forest_return_meter=="storm-track"),"cross-under-rainy-oak",results)
        elif args.forest_return_meter=="display":
            import trail
            from display_walk import walk as compare_forest
            attempt(lambda: compare_forest(saved_source,first,results,trail,aim,goto,shot,key,click,hotbar,out),"compare-frozen-leaf-return",results)
        elif args.forest_return_meter:
            import trail
            from forest_meter import walk as read_oak
            attempt(lambda: read_oak(saved_source,first,results,trail,aim,goto,shot,key,click),"read-forest-return",results)
        elif args.oak_opening:
            import trail
            sys.path.insert(0,str(ROOT/"reports/2026-11-23-oak-shadow"))
            from walk import build_post,walk as cut_oak
            if finish_oak_post:
                attempt(lambda: build_post(results,aim,goto,shot,key,click),"finish-lantern-post",results)
            else:
                attempt(lambda: cut_oak(saved_source,first,results,trail,hotbar,aim,goto,shot,key,click,mine),
                        "cut-oak-and-build-lantern-post",results)
        elif args.night_trail:
            import trail
            from night_walk import night_walk
            attempt(lambda: night_walk(first, saved_source, results, trail, hotbar, aim, goto, turn, hold,
                                        observe, shot, key, click, lambda: round(time.monotonic()-st["start"],3)),
                    "oak-to-raised-path",results)
        elif args.isolate_oak:
            import trail
            from oak_approach import isolate, settled_lights
            def photos(prefix,point,facing):
                if args.exposure_readout and prefix=="bark-close":
                    return settled_lights(key,shot,hotbar,reverse=pack!=bark_material)
                return photograph_lights(prefix,point,facing)
            attempt(lambda: isolate(first,saved_source,args.revisit_from,results,trail,hotbar,aim,goto,shot,key,click,photos),
                    "separate-placed-and-held-light",results)
        elif args.return_oak:
            import trail
            from oak_approach import approach
            attempt(lambda: approach(first, saved_source, args.revisit_from, out, results, trail, hotbar,
                                     aim, goto, shot, key, photograph_lights),"return-to-saved-oak",results)
        elif args.forest_cave:
            sys.path.insert(0,str(run_root))
            from cave_walk import visit
            attempt(lambda: visit(results,aim,goto,shot,key,click,observe,mine=mine if args.cut_alcove else None),"natural-cave",results)
        elif args.revisit_from in ("pasture","portrait","grazing"):
            attempt(trace_herd,"lit-oak-and-grazing-herd",results)
        else:
            attempt(outing,"saved-woodland-to-pasture",results)

        end = observe("end", keep=True)
        length = time.monotonic() - st["start"]
    finally:
        if strip:
            try:
                strip.__exit__(None,None,None)
            except (OSError,RuntimeError,subprocess.TimeoutExpired) as error:
                results["stripFailure"]=str(error)
        if video and video.poll() is None:
            video.stdin.write(b"q\n"); video.stdin.flush(); video.wait(timeout=30)
        if vlog:
            vlog.close()
        if st["wid"] and proc.poll() is None:
            subprocess.run(["/tmp/aqualumen-wm-close", hex(int(st["wid"]))], env=env, timeout=8)
        try:
            proc.wait(timeout=40)
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait(timeout=12)
        guard.unlink(missing_ok=True)
        xvfb.terminate()

sys.path.insert(0, str(ROOT / "reports/2026-11-21-door-light/playable"))
from validate_world import parse_nbt  # noqa: E402
level = parse_nbt(gzip.decompress((save / "level.dat").read_bytes()))["Data"]
pfiles = sorted((save / "playerdata").glob("*.dat"))
player = parse_nbt(gzip.decompress(pfiles[0].read_bytes())) if pfiles else None
stats_files = list((save / "stats").glob("*.json"))
stats = json.loads(stats_files[0].read_text())["stats"] if stats_files else {}
t = log()
fpsvals = [r["fps"] for r in fpsrec]
record = {
    "run": args.run, "renderer": re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip(), "pack": pack.name, "packSha256": pack_sha,
    "compilerJarSha256": COMPILER_SHA, "mods": sorted(p.name for p in (game / "mods").iterdir()),
    "worldZipSha256": world_sha, "lockAcquired": t_lock, "pipelineSecondsAfterJoin": pipeline_s, "seconds": round(length, 1),
    "video": bool(args.video), "cleanExit": "All dimensions are saved" in t,
    "logErrors": client_errors(t),
    "results": results, "actions": actions, "gridStops": stops, "firstObservation": first, "endObservation": end,
    "displayedFps": {"samples": len(fpsvals), "min": min(fpsvals) if fpsvals else None, "median": float(np.median(fpsvals)) if fpsvals else None,
                     "max": max(fpsvals) if fpsvals else None, "note": "displayed F3 integer FPS only, F3 open, 1600x900, 12 chunks; not a benchmark"},
    "savedLevel": {k: level[k] for k in ("Time", "DayTime", "raining", "GameType", "allowCommands", "Difficulty")},
    "savedPlayer": {"Pos": player["Pos"], "Rotation": player["Rotation"], "playerGameType": player.get("playerGameType")} if player else None,
    "walkMetres": stats.get("minecraft:custom", {}).get("minecraft:walk_one_cm", 0) / 100,
    "labFilesUnchanged": all(sha(orig / n) == v for n, v in original.items()), "modsUnchanged": all(sha(orig / "mods" / n) == v for n, v in mods.items()),
    "worldZipUnchanged": sha(world) == world_sha, "benchmarkSentinelPresent": g.SENTINEL.exists(), "privateGameDir": str(game),
    "previousSaveUnchanged": save_digest(saved_source) == saved_before, "revisit": revisit,
}
record["walkedAfterReloadMetres"] = round(record["walkMetres"] - revisit["sourceWalkMetres"], 2)
write(out / "complete.json", record)
write(out / "status.json", {"stage": "complete", "seconds": round(length, 1)})
progress(f"{args.run}: complete cleanExit={record['cleanExit']} walked={record['walkedAfterReloadMetres']}m time={record['savedLevel']['Time']}")
print(json.dumps({k: record[k] for k in ("cleanExit", "displayedFps", "savedLevel", "walkedAfterReloadMetres")}, indent=1))
