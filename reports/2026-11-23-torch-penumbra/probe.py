"""Read visibility from the private pack after the real capture and publication passes."""
import argparse
from pathlib import Path
import os
import subprocess
from zipfile import ZipFile
from pack import BASE, ROOT, WORK, build, edit


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("driver", choices=["rtx","mesa"])
    parser.add_argument("table")
    parser.add_argument("--carried", action="store_true")
    model=parser.add_mutually_exclusive_group()
    model.add_argument("--rim",action="store_true")
    model.add_argument("--joint",action="store_true")
    args=parser.parse_args()
    if args.joint:
        from joint_pack import build_joint
        pack=build_joint()
    else:
        pack=build(args.rim)
    for path, name in [(BASE,"base"),(pack,"study")]:
        with ZipFile(path) as z:
            z.extractall(WORK/name)
        if name=="study":
            # Instrument the already-executed branch. Do not call the integrator
            # twice or assume a global write survived an early return.
            shader=WORK/name/"shaders/lib/local_lighting.glsl"
            text=edit(shader.read_text(),"vec3 lampVisibility(","float measuredArea=-1.;\nvec3 lampVisibility(")
            gate="if(area>=0.) {" if args.joint else "if(area>=0.) return vec3(area);"
            text=edit(text,gate,"measuredArea=area;\n        "+gate)
            index=text.rindex("#endif")
            shader.write_text(text[:index]+"float simpleSolidVisibility(vec3 a,vec3 b,vec3 l,vec3 u,vec3 v){return measuredArea;}\n"+text[index:])
    env=os.environ.copy()
    icd="10_nvidia" if args.driver=="rtx" else "50_mesa"
    env["__EGL_VENDOR_LIBRARY_FILENAMES"]=f"/usr/share/glvnd/egl_vendor.d/{icd}.json"
    if args.driver=="mesa":
        env.update(LIBGL_ALWAYS_SOFTWARE="1",GALLIUM_DRIVER="llvmpipe")
    path=WORK/"lamp-probe"
    source=ROOT/"reports/2026-11-23-oak-shadow/probe.cpp"
    includes=[source,ROOT/"tools/glcheck.cpp",*(ROOT/"tools").glob("*-probe.h")]
    if not path.is_file() or any(s.stat().st_mtime>path.stat().st_mtime for s in includes):
        subprocess.run(["g++","-std=c++17","-O2",str(source),"-o",str(path),"-lepoxy","-lEGL"],check=True)
    table=Path(args.table)
    tag=("joint-" if args.joint else "rim-" if args.rim else "")+table.stem+"-"+args.driver+("-hand" if args.carried else "-placed")
    with (WORK/(tag+".log")).open("w") as out:
        subprocess.run([str(path),str(WORK/"base/shaders"),str(WORK/"study/shaders"),str(table)]+(["--carried"] if args.carried else []),env=env,stdout=out,check=True)


if __name__=="__main__":
    main()
