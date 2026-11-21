import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2)


def run(command,out,name,env=None):
    print(name,flush=True)
    result=subprocess.run(['rtk','proxy',*map(str,command)],capture_output=True,text=True,env=env,timeout=240)
    for suffix,value in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (out/(name+'.'+suffix)).open('x') as stream:
            stream.write(value)
    receipt=dict(command=list(map(str,command)),exitCode=result.returncode,
        stdoutSHA256=sha(out/(name+'.stdout')),stderrSHA256=sha(out/(name+'.stderr')))
    save(out/(name+'-receipt.json'),receipt)
    if result.returncode:
        raise RuntimeError(name+' failed; exclusive Evidence retained')
    return result,receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    report=args.report.resolve(strict=True);out=args.out.absolute();out.mkdir(exist_ok=False)
    env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
    receipt=dict(schema='aqualumen-water-hit-depth-native-v1',passed=False,
        runnerSHA256=sha(Path(__file__)),sources={str(p.relative_to(root)):sha(p) for p in
        (root/'tools/water_hit_depth_native.cpp',root/'tools/water_paired_native.cpp')})
    try:
        for mode in ('baseline','candidate'):
            pack=report/mode
            run([sys.executable,root/'tools/water_paired_native_run.py',pack/'control.zip',pack/'paired.zip',out/(mode+'-passivity'),
                '--view-zoom','3'],out,mode+'-passivity',env)
            native=json.loads((out/(mode+'-passivity/receipt.json')).read_text())
            if not native['passed']:
                raise RuntimeError('Passive native classification failed')
            for role in ('control','paired'):
                shader=out/(mode+'-passivity')/role/'shaders'
                before={str(p.relative_to(shader)):sha(p) for p in shader.rglob('*') if p.is_file()}
                compiled,_=run([root/'build/glcheck',shader,'--compile-only'],out,mode+'-'+role+'-compile',env)
                if 'Renderer: NVIDIA' not in compiled.stdout:
                    raise RuntimeError('Missing actual NVIDIA compiler renderer')
                if before!={str(p.relative_to(shader)):sha(p) for p in shader.rglob('*') if p.is_file()}:
                    raise RuntimeError('Compiler inputs changed')
                save(out/(mode+'-'+role+'-source-pins.json'),before)
        binary=out/'water-hit-depth-native'
        run(['g++','-std=c++17','-O2','-Wall','-Wextra',root/'tools/water_hit_depth_native.cpp','-o',binary,'-lepoxy','-lEGL'],out,'depth-build')
        receipt['binarySHA256']=sha(binary)
        roots=[out/(mode+'-passivity')/role/'shaders' for mode in ('baseline','candidate') for role in ('control','paired')]
        result,_=run([binary,*roots,out/'depth-captures'],out,'depth-regression',env)
        for marker in ('old_depth_mismatch=','candidate_depth_mismatch=0','candidate_occlusion_wrong=0',
                       'blocking_ceiling_leaks=0','eight_mrt_water_passivity=1','depth_consistency_complete=1'):
            if marker not in result.stdout:
                raise RuntimeError('Missing native regression witness '+marker)
        for mode in ('baseline','candidate'):
            path=out/(mode+'-passivity/receipt.json');native=json.loads(path.read_text())
            evidence=[path,*[out/(mode+'-'+role+'-compile-receipt.json') for role in ('control','paired')],out/'depth-regression-receipt.json']
            proof=dict(schema='aqualumen-paired-water-qualification-v1',packSHA256=sha(report/mode/'paired.zip'),
                renderer=native['renderer'],compileExitCode=0,nativeExitCode=0,C0Exact=True,classificationPassed=True,
                C0ExactComparedToControlZipSHA256=sha(report/mode/'control.zip'),
                testedRoutes=native['tested_routes'],untestedRoutes=native['untested_routes'],
                evidence=[dict(path=str(p.relative_to(root)),sha256=sha(p)) for p in evidence],
                eightMRTNativeWaterPassivity=True,actualIrisAccepted=False,physicalAccepted=False)
            save(out/(mode+'-qualification.json'),proof)
        receipt['passed']=True
    except Exception as error:
        receipt['failure']=str(error)
        raise
    finally:
        save(out/'receipt.json',receipt)


if __name__=='__main__':
    main()
