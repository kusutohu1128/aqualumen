"""Exercise the shipping visibility function and the candidate on identical native EGL fixtures."""

from pathlib import Path
from zipfile import ZipFile
import json
import os
import random
import subprocess as sp
import argparse
from candidate import HERE, ROOT, WORK, BASE, NAME, build, replace_once


def prepare():
    for tag, pack in (("base", BASE), ("study", build())):
        folder = WORK / tag
        with ZipFile(pack) as source:
            for n in source.namelist():
                if not n.startswith("shaders/") or n.endswith("/"):
                    continue
                dest = folder / n
                dest.parent.mkdir(exist_ok=True, parents=True)
                data = source.read(n)
                if tag == "study" and n == NAME:
                    code = data.decode().replace(
                        "vec4 lampSolidHit;", "vec4 lampSolidHit;\nbool umbraReported=false;"
                    )
                    code = replace_once(
                        code,
                        "return vec3(0);\n        }\n        sum+=",
                        "{ umbraReported=true; return vec3(0); }\n        }\n        sum+=",
                    )
                    body, ending = code.rsplit("#endif", 1)
                    data = (
                        body
                        + "\nfloat simpleSolidVisibility(vec3 a,vec3 b,vec3 l,vec3 u,vec3 v){return float(umbraReported);}\n#endif"
                        + ending
                    ).encode()
                dest.write_bytes(data)
    inputs = (ROOT / "build/oak-shadow/angles.txt").read_text().splitlines()
    rng = random.Random(41023)
    for scene in range(7):
        for n in range(600):
            a = [rng.uniform(27, 38) for _ in range(3)]
            b = [rng.uniform(29, 36) for _ in range(3)]
            if n % 4 == 0:
                b = [32 + rng.random() for _ in range(3)]
            if n % 4 == 1:
                a = [32 + rng.random() for _ in range(3)]
            inputs.append(" ".join(map(str, [scene, *a, *b, rng.choice((0.13, 0.42, 0.25))])))
    (WORK / "inputs.txt").write_text("\n".join(inputs) + "\n")
    return len(inputs)


def verify(tag, vendor, n, carried=False):
    env = {**os.environ, "__EGL_VENDOR_LIBRARY_FILENAMES": "/usr/share/glvnd/egl_vendor.d/" + vendor}
    if tag == "mesa":
        env.update(LIBGL_ALWAYS_SOFTWARE="1", GALLIUM_DRIVER="llvmpipe")
    command = [
        str(WORK / "carried-probe" if carried else ROOT / "build/oak-shadow/probe"),
        str(WORK / "base/shaders"),
        str(WORK / "study/shaders"),
        str(WORK / "inputs.txt"),
    ]
    if carried:
        command.append("--carried")
    run = sp.run(command, capture_output=True, text=True, env=env)
    (WORK / (tag + ("-carried.log" if carried else ".log"))).write_text(run.stdout + run.stderr)
    run.check_returncode()
    lines = run.stdout.splitlines()
    renderer = next(l for l in lines if l.startswith("renderer "))
    assert ("RTX 3080 Ti" if tag == "rtx" else "llvmpipe") in renderer
    rows = [l.split() for l in lines if len(l.split()) == 5 and l.split()[0].isdigit()]
    assert len(rows) == n
    differences = sum(float(a) != float(b) for _, _, a, b, _ in rows)
    shortcuts = sum(float(hit) == 1 for *_, hit in rows)
    assert not differences and shortcuts > 100, (differences, shortcuts)
    return dict(
        renderer=renderer,
        points=n,
        shortcuts=shortcuts,
        changed=differences,
        penumbra=sum(0 < float(a) < 1 for _, _, a, _, _ in rows),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--carried", action="store_true")
    args = parser.parse_args()
    n = prepare()
    if args.carried:
        sp.run(["g++", "-std=c++17", "-O2", str(HERE.parent/"2026-11-23-oak-shadow/probe.cpp"),
                "-o", str(WORK/"carried-probe"), "-lepoxy", "-lEGL"], check=True)
    results = {tag: verify(tag, icd, n, args.carried) for tag, icd in [("rtx", "10_nvidia.json"), ("mesa", "50_mesa.json")]}
    (HERE / ("carried-visibility.json" if args.carried else "visibility.json")).write_text(json.dumps(results, indent=2) + "\n")
    print(results)
