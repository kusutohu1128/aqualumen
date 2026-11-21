import argparse
import json
import os
from pathlib import Path
import sys
import zipfile

from water_hit_depth_run import run,save,sha
from water_paired_native_run import extract


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];report=args.report.resolve(strict=True);out=args.out.absolute();out.mkdir(exist_ok=False)
    env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
    receipt=dict(schema='aqualumen-nonwater-witness-native-v1',passed=False,runnerSHA256=sha(Path(__file__)),
        sources={name:sha(root/'tools'/name) for name in ('water_hit_depth_ownership_native.cpp','water_paired_native.cpp')})
    try:
        roots={}
        for mode in ('baseline','candidate'):
            before=json.loads((report/(mode+'2')/'manifest.json').read_text())
            pack=report/(mode+'3');meta=json.loads((pack/'manifest.json').read_text())
            if sha(pack/'control.zip')!=before['archives']['control']:
                raise RuntimeError('Ownership control archive changed')
            with zipfile.ZipFile(pack/'paired.zip') as new,zipfile.ZipFile(report/(mode+'2')/'paired.zip') as old:
                if set(new.namelist())!=set(old.namelist()):raise RuntimeError('Ownership source set changed')
                changed=[name for name in old.namelist() if old.read(name)!=new.read(name)]
                if set(changed)!={'shaders/gbuffers_textured.fsh','shaders/lib/terrain.fsh.glsl','shaders/shaders.properties'}:
                    raise RuntimeError('Physical water/composite/vertex source changed')
            roots[mode]={role:extract(pack/(role+'.zip'),out/(mode+'-'+role)) for role in ('control','paired')}
            result,_=run([root/'build/glcheck',roots[mode]['paired'],'--compile-only'],out,mode+'-paired-compile',env)
            if 'Renderer: NVIDIA' not in result.stdout:raise RuntimeError('Missing actual NVIDIA compiler renderer')
            receipt[mode+'ManifestSHA256']=sha(pack/'manifest.json')
        binary=out/'ownership-native'
        run(['g++','-std=c++17','-O2','-Wall','-Wextra',root/'tools/water_hit_depth_ownership_native.cpp','-o',binary,'-lepoxy','-lEGL'],out,'build')
        result,_=run([binary,roots['candidate']['control'],roots['candidate']['paired'],out/'captures'],out,'overlay',env)
        if 'ownership_protocol_complete=1' not in result.stdout or result.stdout.count('C0_depth_exact=1')!=4:
            raise RuntimeError('Incomplete nonwater witness coverage')
        if result.stdout.count('blend_mutant_rejected=1')!=2:raise RuntimeError('Missing blend negative controls')
        receipt['binarySHA256']=sha(binary)
        for mode in ('baseline','candidate'):
            old=report/'native-depth2'/(mode+'-qualification.json')
            prior=json.loads(old.read_text());proof=dict(prior)
            proof['packSHA256']=sha(report/(mode+'3')/'paired.zip')
            proof['evidence']=[dict(path=str(p.relative_to(root)),sha256=sha(p)) for p in
                (old,out/(mode+'-paired-compile-receipt.json'),out/'overlay-receipt.json',report/(mode+'3')/'manifest.json')]
            proof['scope']='Native water/composite proof carried over only for byte-identical physical stages; new nonwater witness C0/depth checked independently.'
            proof['physicalStagesCarriedOverFromPackSHA256']=prior['packSHA256']
            proof['nonwaterWitnessNativeVerified']=True
            proof['actualIrisAccepted']=False
            save(out/(mode+'-qualification.json'),proof)
        receipt['passed']=True
    except Exception as error:
        receipt['failure']=str(error);raise
    finally:
        save(out/'receipt.json',receipt)


if __name__=='__main__':
    main()
