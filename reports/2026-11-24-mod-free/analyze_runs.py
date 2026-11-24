#!/usr/bin/env python3
"""Per-launch analysis for the gp-mf-* verification matrix.

Extracts: pack+sha, compiler-mod presence, shader-pack load -> first-frame
timing, per-stage CPU/GPU stats, shader-compile error grep, cache cold/warm.
"""
import json, re, sys, os
from pathlib import Path

RUNS = Path(__file__).parent / "runs"
ORDER = ["gp-mf-a1-p13-compiler", "gp-mf-b1-p14-nocompiler",
         "gp-mf-c1-p14-compiler", "gp-mf-c2-p14-compiler",
         "gp-mf-b2-p14-nocompiler", "gp-mf-a2-p13-compiler"]

def log_ts(line):
    m = re.match(r"\[(\d+):(\d+):(\d+)\]", line)
    return (int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))) if m else None

def analyze(label):
    d = RUNS / label
    out = {"label": label}
    cj = d / "complete.json"
    if not cj.exists():
        out["error"] = "no complete.json"; return out
    c = json.loads(cj.read_text())
    out["pack"] = c.get("pack"); out["packSha"] = (c.get("packSha256") or "")[:12]
    out["compilerModSha"] = (c.get("compilerModSha256") or "")[:12]
    out["complete"] = c.get("complete"); out["unchanged"] = c.get("originalWorldAndConfigUnchanged")
    out["seconds"] = c.get("seconds")
    # compiler mod actually removed? (prepare_extra deletes jar for nocompiler)
    cr = d / "compiler-removed.txt"
    out["compilerRemoved"] = cr.exists()
    # client.log timing + errors
    log = (d / "client.log").read_text(errors="replace").splitlines()
    pack_i = next((i for i,l in enumerate(log) if "Using shaderpack:" in l), None)
    pipe_i = next((i for i,l in enumerate(log) if "Creating pipeline for dimension" in l), None)
    out["packLoadLog"] = log[pack_i].split("]")[0].strip("[") if pack_i is not None else None
    out["pipelineLog"] = log[pipe_i].split("]")[0].strip("[") if pipe_i is not None else None
    # first AQ_RENDER_FRAME_END epoch after pipeline creation -> first world frame
    first_ep = None
    for l in log[pipe_i:] if pipe_i is not None else []:
        m = re.search(r"AQ_RENDER_FRAME_END (\d+)", l)
        if m: first_ep = int(m.group(1)); break
    out["firstFrameEpochMs"] = first_ep
    if pack_i is not None and first_ep is not None:
        # anchor: find an AQ_RENDER_FRAME_END line's log ts + epoch to build offset
        # simpler: use pipeline log ts (second precision) -> approximate; report both raw
        pass
    # error grep
    errs = [l for l in log if re.search(r"too many instructions|Failed to compile|Compilation failed|GLSL compile|Shader .*error|Exception in thread|crash", l, re.I)]
    out["shaderErrors"] = errs[:6]
    out["errorCount"] = len(errs)
    # cache before/after populated + file count
    pf = d / "preflight.json"
    if pf.exists():
        p = json.loads(pf.read_text())
        cb = p.get("cacheBefore") or {}; ca = p.get("cacheAfter") or {}
        out["cacheBeforeFiles"] = len(cb.get("files") or {})
        out["cacheAfterFiles"] = len(ca.get("files") or {})
        out["cachePopulated"] = cb.get("populated")
        drift = (p.get("labBefore") or {}).get("labConfigTimestampDrift")
        out["labDrift"] = bool(drift)
    # summary.json per-stage
    sj = d / "summary.json"
    if sj.exists():
        s = json.loads(sj.read_text())
        scenes = s.get("scenes") or {}
        st = {}
        for name, sc in scenes.items():
            gpu = sc.get("gpu") or {}
            rng = gpu.get("ranges") or {}
            # total gpu frame ms = sum of range medians? use 'frame' if present
            keys = list(rng.keys())
            st[name] = {
                "cpuMeanMs": round(sc.get("cpuMeanMs") or 0, 2),
                "cpuP99Ms": round(sc.get("cpuP99Ms") or 0, 2),
                "frames": sc.get("frames"),
                "gpuRanges": {k: round((v.get("medianMs") or 0),3) for k,v in rng.items()},
            }
        out["stages"] = st
    return out

if __name__ == "__main__":
    res = [analyze(l) for l in ORDER]
    print(json.dumps(res, indent=1))
