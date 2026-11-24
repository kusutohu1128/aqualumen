"""Launch a single guarded profiling client. The argument defaults reproduce the reviewed rooms."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import birch_scene
import re
import shutil
import subprocess
import sys
import threading
import time

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
T = R.parent/"2026-11-21-animal-light"
BUILD = ROOT/"build/gpu-profiler"
RUNS = R/"runs"
LAB = json.loads((R.parent/"2026-11-22-eye-adaptation/lab.json").read_text())
GAME = Path(LAB["destinations"]["lab"]["path"]).parents[1]
PACKS = {"stable":("Aqualumen-1.8.0.zip", "c5d804e4a6776cf7df14b405f32a605d09451cab10aabb8b3fae4c5428c73af8"),
         "p3":("Aqualumen-1.9.0-preview.3.zip", "a5084110b9373db7240244b1953c24f2f1d42a6c9430d148a05901a9b210266b"),
         "cal": ("Aqualumen-profile-4x.zip", "63b69616e9332484b7a7ce44c5b05bdb6e39a476452a6ba2a71b4b20f6acf6d0"),
         "p7": (Path(LAB["previousPreview"]).name, LAB["previousPreviewSha256"]),
         "p8": (Path(LAB["destinations"]["dist"]["path"]).name, LAB["sha256"])}
FACE_PREVIEW = ("Aqualumen-1.9.0-preview.10.zip", "a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9")
ORDER = {"gp-cal-4x-c": "cal", "gp-overhead-off-a": "p7", "gp-p7-a": "p7", "gp-p8-a": "p8",
         "gp-p8-b": "p8", "gp-p7-b": "p7", "gp-overhead-off-b": "p7"}
PREVIEW_RUNS=tuple(ORDER)
OLDER_RUNS={"gp-stable-a":"stable","gp-p3-a":"p3","gp-p3-b":"p3","gp-stable-b":"stable"}
ORDER.update(OLDER_RUNS)
DESKTOP = set(json.loads((T/"eye-frames-p7-a/preflight.json").read_text())["gpuDesktopProcesses"].values()) | {"cosmic-monitor"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n")


IRIS = "config/iris.properties"
# Iris re-saves config/iris.properties with a fresh '#<date>' comment on every
# config write; only that comment may drift against the receipts. The
# receipt-era non-comment body is pinned by content hash and shaderPack must
# remain the receipt's selected pack. Verified 2026-11-24: the sole change is
# the timestamp comment '#Sat Nov 21 07:59:36 JST 2026' ->
# '#Tue Nov 24 00:38:22 JST 2026' (old comments + current body reproduce the
# receipt sha256 a69a20fd... exactly).
IRIS_BODY_SHA256 = "4fa3fa7ce8629a463a29b1486669cbdb6520c44cff561e2203e63dea7cb552f9"
IRIS_RECEIPT_COMMENT = "#Sat Nov 21 07:59:36 JST 2026"
IRIS_STAMP = re.compile(r"^#(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \w{3} \d{2} \d{2}:\d{2}:\d{2}")


def iris_content(path):
    """Split iris.properties into (non-comment body bytes, comment lines)."""
    lines = path.read_bytes().split(b"\n")
    body = b"\n".join(l for l in lines if not l.lstrip().startswith(b"#"))
    comments = [l.decode(errors="replace") for l in lines if l.lstrip().startswith(b"#")]
    return body, comments


def lab_check():
    expected = {**LAB["normalFileHashesAfter"], "mods/"+LAB["compilerDisabled"]: LAB["compilerSha256"],
                "shaderpacks/"+PACKS["p7"][0]: PACKS["p7"][1], "shaderpacks/"+PACKS["p8"][0]: PACKS["p8"][1]}
    optional = "shaderpacks/"+FACE_PREVIEW[0]
    if (GAME/optional).exists():
        expected[optional] = FACE_PREVIEW[1]
    actual = {name: sha(GAME/name) for name in expected}
    mods = sorted(p.name for p in (GAME/"mods").glob("*.jar"))
    assert mods == sorted(LAB["activeMods"])
    for name in expected:
        if name != IRIS:
            assert actual[name] == expected[name], f"lab file hash drift: {name}"
    body, comments = iris_content(GAME/IRIS)
    assert hashlib.sha256(body).hexdigest() == IRIS_BODY_SHA256, "iris.properties non-comment content changed"
    assert ("shaderPack=%s" % LAB["selected"]).encode() in body.split(b"\n"), "iris.properties shaderPack changed"
    drift = None
    if actual[IRIS] != expected[IRIS]:
        stamps = [c for c in comments if IRIS_STAMP.match(c)]
        drift = dict(receiptHash=expected[IRIS], currentHash=actual[IRIS],
                     receiptComment=IRIS_RECEIPT_COMMENT,
                     currentComment=stamps[-1] if stamps else None,
                     comments=comments)
    meta = hashlib.sha256()
    meta_ex = hashlib.sha256()
    for p in sorted(GAME.rglob("*")):
        s = p.lstat()
        line = f"{p.relative_to(GAME)}|{s.st_size}|{s.st_mtime_ns}\n".encode()
        meta.update(line)
        if p != GAME/IRIS:
            meta_ex.update(line)
    return dict(fileHashes=actual, activeMods=mods, selected=LAB["selected"], metadata=meta.hexdigest(),
                metadataExIris=meta_ex.hexdigest(), labConfigTimestampDrift=drift)


def lab_equivalent(recorded, current):
    """True when a recorded lab state matches the current one, tolerating only
    the config/iris.properties timestamp-comment drift.

    Pre-drift receipts store the old iris.properties byte hash and an all-files
    metadata digest that includes its old mtime; neither can be normalized for
    those receipts, so both are excluded here. Every other expected-file hash,
    the mod list and the selected pack stay strict, and metadataExIris is
    compared whenever both sides carry it.
    """
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return recorded == current
    if recorded.get("activeMods") != current.get("activeMods"):
        return False
    if recorded.get("selected") != current.get("selected"):
        return False
    if "metadataExIris" in recorded and "metadataExIris" in current:
        if recorded["metadataExIris"] != current["metadataExIris"]:
            return False
    a = {k: v for k, v in (recorded.get("fileHashes") or {}).items() if k != IRIS}
    b = {k: v for k, v in (current.get("fileHashes") or {}).items() if k != IRIS}
    return a == b


def cache_state():
    cache=BUILD/"driver-cache"
    files={str(p.relative_to(cache)):dict(bytes=p.stat().st_size,sha256=sha(p))
           for p in sorted(cache.rglob("*")) if p.is_file()}
    return {"path":str(cache),"files":files,"readWrite":os.access(cache,os.R_OK|os.W_OK),
            "populated":all(any(name.endswith(ext) and data["bytes"]>0 for name,data in files.items())
                            for ext in (".toc",".bin"))}


def inspect_gpu(game=None, owned_instances=None):
    smi = subprocess.check_output(["nvidia-smi"], text=True)
    ps = subprocess.check_output(["ps", "-eo", "pid,comm,args"], text=True)
    jobs = {}
    for line in ps.splitlines()[1:]:
        pid, name, *args = line.split(None, 2)
        jobs[int(pid)] = (name, args[0] if args else "")
    gpu = {int(pid): jobs.get(int(pid), ("unknown", ""))[0] for pid in
           re.findall(r"^\|\s*\d+\s+\S+\s+\S+\s+(\d+)\s+[CG+]+", smi, re.M)}
    def owned(pid):
        if not game or owned_instances is None:
            return False
        name,args=jobs.get(pid,("",""))
        if name!="java":
            return False
        try:
            born=Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()[19]
        except FileNotFoundError:
            return pid in owned_instances
        if ("--gameDir "+str(game)+" ") in args:
            owned_instances[pid]=born
        return owned_instances.get(pid)==born
    foreign = {pid:name for pid,name in gpu.items() if name not in DESKTOP and not owned(pid)}
    for pid,(name,args) in jobs.items():
        if name in {"java","glcheck","vglrun","nsys","ncu"} and not owned(pid):
            foreign[pid]=name
        elif name.startswith("python") and re.search(r"\b(train|glcheck)\.py\b",args):
            foreign[pid]=name
    return dict(at=datetime.now().astimezone().isoformat(), gpu=gpu, foreign=foreign,
                gpuStatus=smi.split("Processes:")[0].rstrip("| \n"))


def run_base(label):
    return re.sub(r"-retry[12]$", "", label)


def latest(base, runs=RUNS):
    return next((name for name in (base+"-retry2",base+"-retry1",base) if (runs/name).exists()),base)


def check_sequence(label, runs=RUNS):
    base=run_base(label)
    if base not in ORDER or (runs/label).exists():
        raise ValueError("unknown or used label")
    if label!=base:
        n=int(label[-1])
        attempts=sum(1 for path in runs.glob("*/complete.json") if run_base(path.parent.name) in ORDER
                     and path.parent.name!=run_base(path.parent.name))
        prior=base if n==1 else base+"-retry1"
        if attempts>=2 or not (runs/prior/"complete.json").is_file():
            raise ValueError("retry limit or missing prior receipt")
    previous=list(ORDER)[:list(ORDER).index(base)]
    for prior in previous:
        path=runs/latest(prior,runs)
        summary=path/"summary.json"
        if not summary.is_file() or json.loads(summary.read_text()).get("validated") is not True:
            raise ValueError("missing validated arm "+prior)
    if "gp-p7-a" in previous:
        gate=runs.parent/"summary.json"
        state=json.loads(gate.read_text()) if gate.exists() else {}
        if not state.get("pass") or (base in OLDER_RUNS and set(state["overhead"])!={"a","b"}):
            raise ValueError("instrument calibration and first overhead pair must pass")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("pack",type=Path)
    parser.add_argument("label")
    parser.add_argument("--gpu-profile",choices=("off","on"),required=True)
    parser.add_argument("--frame-intervals",action="store_true",required=True)
    # The remaining switches can spell out these fixed settings for reproducible reruns.
    fixed={"backend":"vgl","size":"2560x1440","period-ticks":"680","settle":"1","stages":"both-west,day-white",
           "glcache":str(BUILD/"driver-cache"),"compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")}
    for k,v in fixed.items():
        parser.add_argument("--"+k,default=v)
    parser.set_defaults(stages=None)
    args=parser.parse_args()
    label=args.label
    base=run_base(label)
    if base in OLDER_RUNS:
        fixed["stages"]=",".join(birch_scene.STAGES)
    if args.stages is None:
        args.stages=fixed["stages"]
    pack=args.pack.resolve(strict=True)
    assert base in ORDER and (pack.name,sha(pack))==PACKS[ORDER[base]]
    assert args.gpu_profile==("off" if "-off-" in label else "on")
    check_sequence(label)
    for k,v in fixed.items():
        actual=getattr(args,k.replace("-","_"))
        assert (str(Path(actual).resolve()) if k in ("glcache","compiler-mod") else actual)==v
    launch(pack,label,args.gpu_profile,fixed,RUNS,birch_scene.BirchRooms if base in OLDER_RUNS else None)


def launch(pack, label, profile, fixed, runs, scene_factory=None, prepare_extra=None, collect_extra=None):
    """Run one hash-checked private client using the historical preflight and render lock."""
    before=lab_check()
    baseline=RUNS/"gp-p7-a/preflight.json"
    if baseline.exists():
        previous=json.loads(baseline.read_text())["labAfter"]
        if not lab_equivalent(before, previous):
            receipt_path=R.parent/"2026-11-23-torch-density/lab.json"
            published=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            if not (lab_equivalent(published.get("labBefore"), previous)
                    and lab_equivalent(published.get("labAfter"), before)
                    and published.get("sha256")==FACE_PREVIEW[1]):
                raise ValueError("Lab differs from the profiled state and its recorded optional pack installation")
    cache=cache_state()
    pre=inspect_gpu()
    if pre["foreign"]:
        raise SystemExit(f"GPU busy {pre['foreign']}")
    sys.path.insert(0,str(T))
    spec=importlib.util.spec_from_file_location("animal_private_runner",T/"run.py")
    animal=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(animal)
    runner=animal.runner
    runs.mkdir(exist_ok=True)
    runner.here=runs
    if scene_factory is not None:
        runner.scene=scene_factory(runner.scene)
    receipt={"cacheBefore":cache,"beforeLock":pre,"labBefore":before,"foreignObservations":[],
             "labConfigTimestampDrift":before.get("labConfigTimestampDrift")}
    complete=threading.Event()

    def prepare(game,clone,out):
        assert game.parent.parent==Path("/tmp") and game.parent.name.startswith("aql-v190-run-")
        assert clone==game/"saves"/runner.g.lab.WORLD
        assert runner.g.lab.pairs((clone/"aqualumen-world.properties").read_bytes())["world_id"]==runner.g.lab.WORLD_ID
        receipt["underLock"]=inspect_gpu()
        save(out/"preflight.json",receipt)
        assert not receipt["underLock"]["foreign"]
        expected={name:sha(GAME/"mods"/name) for name in LAB["activeMods"]}
        expected["aqualumen-lighting-compiler-0.3.0.jar"]=LAB["compilerSha256"]
        assert {p.name:sha(p) for p in (game/"mods").iterdir()}==expected
        assert sha(game/"mods/iris-fabric-1.8.8+mc1.21.1.jar")=="b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5"
        assert sha(game/"mods/sodium-fabric-0.6.9+mc1.21.1.jar")=="411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2"
        assert sha(game/"shaderpacks"/pack.name)==sha(pack)
        if scene_factory is not None:
            # Reproduce the historical spectator projection. Both older arms use this setting in every stage.
            options=game/"options.txt"
            options.write_bytes(runner.g.lab.replace_values(options.read_bytes(), {"fovEffectScale":"1.0"}, ":"))
            save(out/"birch-world.json",birch_scene.audit_world())
        observer=Path(shutil.copy2(BUILD/"frame-sample.jar",game/"mods"))
        (game/"config/animal-frame-probe.enabled").write_text(str(game)+"\n")
        (game/"config/frame-ordinals.enabled").touch()
        mods={"frameObserverSha256":sha(observer),"worldId":runner.g.lab.WORLD_ID}
        if profile=="on":
            profiler=Path(shutil.copy2(BUILD/"gpu-profiler.jar",game/"mods"))
            mods["gpuProfilerSha256"]=sha(profiler)
            (game/"config/gpu-profile.properties").write_text(f"game={game}\nlabel={label}\npack={pack.name}\nsha256={sha(pack)}\n")
        if prepare_extra is not None:
            prepare_extra(game, out, mods)
        save(out/"observer.json",mods)
        receipt["cacheFilesBefore"]=sum(p.is_file() for p in (BUILD/"driver-cache").rglob("*"))
        owned_instances={}
        def monitor():
            while not complete.wait(4):
                try:
                    state=inspect_gpu(game,owned_instances)
                    receipt["samples"]=receipt.get("samples",0)+1
                    if state["foreign"]:
                        receipt["foreignObservations"].append(state)
                except Exception as exc:
                    receipt["foreignObservations"].append(str(exc))
        thread=threading.Thread(target=monitor,daemon=True)
        thread.start()

    def collect(game,out):
        if profile=="on":
            raw=game/"gpu-frames.csv"
            if raw.exists():
                shutil.copy2(raw,BUILD/(label+".csv"))
        if collect_extra is not None:
            collect_extra(game, out)

    def monitor_log(txt,allow):
        errors=original_log_check(txt,allow)
        if receipt["foreignObservations"]: errors.append("foreign GPU job or monitor failure")
        if "AQ_PROFILE_INVALID" in txt: errors.append("GPU profiler disabled; invalid run")
        if "AQ_RENDER_PROBE_FAILED" in txt: errors.append("CPU observer guard")
        return errors
    original_log_check=runner.error_lines
    runner.error_lines=monitor_log
    options={"load-timeout":"600",**fixed}
    sys.argv=[sys.argv[0],str(pack),label,*[arg for k,v in options.items() for arg in ("--"+k,v)]]
    try:
        runner.main(prepare_private_client=prepare,collect_private_client=collect)
    finally:
        complete.set()
        if (runs/label).exists():
            receipt["cacheAfter"]=cache_state()
            receipt["labAfter"]=lab_check()
            save(runs/label/"preflight.json",receipt)
            assert receipt["labAfter"]==before and not receipt["foreignObservations"]


if __name__=="__main__":
    main()
