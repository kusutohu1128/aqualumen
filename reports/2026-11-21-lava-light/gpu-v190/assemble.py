"""Collect the lava GPU QA runs into result.json (no GPU work here).

Inputs are the logs/JSON written by build/claude-lava-qa/glcheck-lava2 (see COMMANDS.md).
NVIDIA results are the gate; llvmpipe is an independent software cross-check.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QA = ROOT / "build/claude-lava-qa"
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log_summary(path):
    if not path.exists():
        return {"present": False}
    text = path.read_text(errors="replace")
    renderer = re.search(r"^Renderer: (.*)$", text, re.M)
    return {
        "present": True,
        "renderer": renderer.group(1) if renderer else None,
        "passLines": len(re.findall(r"^PASS", text, re.M)),
        "failLines": re.findall(r"^FAIL.*$", text, re.M)
        + re.findall(r"^.*QA FAIL.*$", text, re.M),
        "lastLine": text.strip().splitlines()[-1] if text.strip() else "",
    }


def main():
    nvidia = json.loads((QA / "lava-nvidia.json").read_text())
    mesa = json.loads((QA / "lava-mesa.json").read_text())
    cross = {}
    for key in ("one-open", "one-pillar", "nine-open", "nine-pillar"):
        a, b, c = nvidia[key + "Gpu"], mesa[key + "Gpu"], nvidia[key + "Unoccluded"]
        cross[key] = max(abs(x - y) / z for x, y, z in zip(a, b, c))
    status = {}
    for line in (QA / "nvidia-jobs.txt").read_text().splitlines():
        m = re.match(r"\S+ (\S+) exit=(\d+)", line)
        if m:
            status[m.group(1)] = int(m.group(2))
    logs = {name: log_summary(QA / f"nv-{name}.log") for name in status}
    candidate = ROOT / "build/lava-v190-src/shaders"
    result = {
        "date": "2026-11-21",
        "role": "Claude independent QA: engine regression compatibility + targeted lava GPU probe",
        "kind": "GPU harness (surfaceless EGL) on production GLSL; not Minecraft frame timing, not in-game images",
        "inputs": {
            "candidate": str(candidate.relative_to(ROOT)),
            "candidateLavaSha256": {
                p.name: sha(p)
                for p in sorted(candidate.glob("lib/lava_*.glsl"))
                + [candidate / "shadowcomp1.csh", candidate / "shaders.properties"]
            },
            "baseline": "dist/Aqualumen-1.8.0.zip (identical to release/shaders)",
            "baselineSha256": sha(ROOT / "dist/Aqualumen-1.8.0.zip"),
        },
        "toolSha256": {
            p: sha(ROOT / p)
            for p in (
                "tools/lava-light-probe.h",
                "tools/local-lights-probe.h",
                "tools/entity-light-probe.h",
                "tools/glcheck.cpp",
                "Makefile",
            )
        },
        "nvidiaJobs": status,
        "nvidiaLogs": logs,
        "lavaNvidia": nvidia,
        "lavaMesaSummary": {k: mesa[k] for k in ("renderer", "passed", "failed")},
        "crossRendererMaxAbsDiffOverUnoccluded": cross,
        "verdict": {
            "regressionSuiteCompatible": all(
                status.get(k) == 0
                for k in status
                if k.startswith(("cand-", "rel-")) and k != "cand-play-release"
            ),
            "lavaProbeFailed": nvidia["failed"],
            "lavaGateGreen": nvidia["failed"] == 0,
        },
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["verdict"]), json.dumps(cross))


if __name__ == "__main__":
    sys.exit(main())
