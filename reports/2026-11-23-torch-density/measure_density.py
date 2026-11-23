"""Measure installed torch count in private clones of the surveyed birch and sand sites."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from statistics import mean
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "2026-11-22-gpu-profile"))
import run as guarded
import summarize as gpu
from profile_data import collect_window, read_rows

sys.path.insert(0, str(guarded.birch_scene.FOREST))
from worldread import World

SITES = {"birch": (208, 64, 355, "grass_block"), "sand": (157, 63, 349, "sand")}
OFFSETS = ((-1, 4), (2, 4), (-3, 2), (0, 5))
COUNTS = (0, 1, 2, 4)
STAGES = [f"{site}-{n}" for site in SITES for n in COUNTS]
PREFIX = "data/animal/function/"
BASE = ROOT / "dist" / guarded.PACKS["p8"][0]


def survey():
    world = World()
    sites = {}
    for site, (x, y, z, floor) in SITES.items():
        cells = [(x+dx, y, z+dz) for dx, dz in OFFSETS]
        for a, b, c in [(x, y, z), *cells]:
            assert world.name(a, b-1, c) == "minecraft:"+floor
            assert world.name(a, b, c) == world.name(a, b+1, c) == "minecraft:air"
        nearby = Counter(world.name(a,b,c) for a in range(x-8,x+9) for b in range(y,y+12) for c in range(z-3,z+9))
        assert None not in nearby
        sites[site] = dict(feet=[x+.5, y, z+.5], yaw=12.7, pitch=-2, supports=floor, slots=cells,
                           nearLeaves=sum(n for block,n in nearby.items() if block.endswith("_leaves")),
                           sampledCells=sum(nearby.values()))
    assert world.unchanged()
    return sites


class TorchCounts:
    def __init__(self, rooms):
        self.rooms = rooms
        self.STAGE_TABLE = dict.fromkeys(STAGES)

    def __getattr__(self, name):
        return getattr(self.rooms, name)

    def self_test(self, names):
        assert names and len(set(names)) == len(names) and set(names) <= set(STAGES)

    def geometry(self, names):
        return dict(sites=survey(), time=9800, stages=names)

    def datapack(self, names):
        self.self_test(names)
        files = self.rooms.datapack(["day-white"])
        sites = survey()
        for i, stage in enumerate(names):
            site, count = stage.split("-")
            count = int(count)
            info = sites[site]
            pos = " ".join(map(str, info["feet"]))
            slots = [" ".join(map(str, cell)) for cell in info["slots"]]
            def put(label, lines):
                files[f"{PREFIX}{label}{i}.mcfunction"] = "\n".join(lines)+"\n"
            put("s", [f"gamemode spectator {self.PLAYER}", f"tp {self.PLAYER} {pos} 12.7 -2", "time set 9800",
                      f"say AQLAVA_BEGIN_{stage}_END",f"schedule function animal:p{i} 80t replace",
                      f"schedule function animal:v{i} {self.READY_AT}t replace",
                      f"schedule function animal:e{i} {self.STILL_AT}t replace",
                      f"schedule function animal:s{(i+1)%len(names)} {self.PERIOD}t replace"])
            put("p", [f"execute if block {slot} air run setblock {slot} torch" for slot in slots[:count]]
                or ["# zero sources"])
            checks = ["scoreboard players set #ok aq_room 1", "execute store result score #t aq_room run time query daytime",
                "execute unless score #t aq_room matches 9800 run scoreboard players set #ok aq_room 0",
                f"execute positioned {pos} unless entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.04,x_rotation=-2.05..-1.95,y_rotation=12.65..12.75] run scoreboard players set #ok aq_room 0"]
            checks.extend(f"execute if items entity {self.PLAYER} weapon.{hand} * run scoreboard players set #ok aq_room 0"
                          for hand in ("offhand","mainhand"))
            for j, (a,b,c) in enumerate(info["slots"]):
                for at, block in ((f"{a} {b} {c}", "torch" if j<count else "air"),
                                  (f"{a} {b-1} {c}", info["supports"])):
                    checks.append(f"execute unless block {at} {block} run scoreboard players set #ok aq_room 0")
            x,y,z,_ = SITES[site]
            for a in range((x//8)*8-32,(x//8)*8+32,8):
                for c in range((z//8)*8-32,(z//8)*8+32,8):
                    checks.append(f"execute unless loaded {a} {y} {c} run scoreboard players set #ok aq_room 0")
            for fn,ok,bad in (("v","READY","FAIL"),("e","STILL","DRIFT")):
                lines = list(checks)
                if fn=="e":
                    for slot in slots[:count]:
                        lines.extend([f"execute if block {slot} torch run setblock {slot} air",
                                      f"execute unless block {slot} air run scoreboard players set #ok aq_room 0"])
                lines.extend([f"execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{stage}_END",
                              f"execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{stage}_END"])
                put(fn, lines)
        return files


def analyze(folder, pack, profile, *, min_frames=101, required_passes=None):
    read = gpu.read
    receipt = read(folder/"complete.json")
    pre = read(folder/"preflight.json")
    assert receipt["complete"] and receipt["sourcePackShaNow"] == receipt["packSha256"] == guarded.sha(pack)
    assert pre["labAfter"] == pre["labBefore"] and not pre["foreignObservations"] and pre["samples"]>0
    observer = read(folder/"observer.json")
    assert observer["frameObserverSha256"] == "636e71f6ad232cc0719391008612871d58c05d38cea8a39f8fbd0f7bc1c614fb"
    if profile:
        assert observer["gpuProfilerSha256"] == "75d6e7307d9437c3aa165d25530878ea7f42456644e7112713728cc2c918ea20"
    else:
        assert "gpuProfilerSha256" not in observer
    log = (folder/"client.log").read_text()
    assert not any(marker in log for marker in ["AQ_PROFILE_DROP","AQ_PROFILE_INVALID","[Server] AQLAVA_FAIL","[Server] AQLAVA_DRIFT"])
    hooks = Counter(re.findall(r'AQ_PROFILE_HOOK [^\n]+',log))
    assert hooks == (Counter((guarded.BUILD/'injections.txt').read_text().splitlines()) if profile else Counter())
    frames = {}
    if profile:
        with (guarded.BUILD/(folder.name+".csv")).open() as stream:
            frames = read_rows(stream)
    windows = {}
    for stage in receipt["stages"]:
        data = gpu.extract(folder, stage, None, pack_path=pack, condition=stage, min_frames=min_frames)
        ids = gpu.window_ids(log, stage, data["intervalsUs"])
        result = dict(cpuMeanMs=mean(data["intervalsUs"])/1000,cpuP99Ms=data["p99Ms"],firstFrame=ids[0],
                      lastFrame=ids[-1],frames=len(ids),capture=data["captureHash"])
        if profile:
            samples=collect_window(frames,ids)
            expected=gpu.EXPECTED if required_passes is None else required_passes
            assert all(expected == {k for k in s['calls'] if k.startswith(('dispatch/', 'quad/'))} for s in samples)
            result["gpu"]=gpu.gpu_stats(samples)
            result["meanMs"]={k:mean(s['inclusive'].get(k,0) for s in samples)/1e6 for k in result["gpu"]["ranges"]}
        windows[stage]=result
    guarded.save(folder/"summary.json", dict(packSha=receipt["packSha256"], renderer=receipt["gl"], scenes=windows))
    print([(s, round(v["cpuMeanMs"],2)) for s,v in windows.items()],flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--pack", type=Path, default=BASE)
    ap.add_argument("--sha", default=guarded.PACKS["p8"][1])
    ap.add_argument("--cpu-only",action="store_true",help="Record Minecraft render intervals with GPU timestamps disabled")
    ap.add_argument("--analyze",action="store_true")
    a=ap.parse_args()
    assert re.fullmatch("gp-density-[a-z0-9-]+",a.label)
    pack=a.pack.resolve(strict=True)
    assert guarded.sha(pack)==a.sha
    folder=HERE/a.label
    if not a.analyze:
        if folder.exists() or (guarded.BUILD/(a.label+".csv")).exists(): raise FileExistsError(folder)
        fixed=dict(backend="vgl",size="2560x1440",settle="1",stages=a.stages,glcache=str(guarded.BUILD/"driver-cache"))
        fixed.update({"period-ticks":"800","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
        try:
            guarded.launch(pack,a.label,"off" if a.cpu_only else "on",fixed,HERE,TorchCounts)
        except SystemExit as exc:
            if exc.code: raise
    analyze(folder,pack,not a.cpu_only)

if __name__ == "__main__":
    main()
