"""Build frozen deep-water hit-point TEST copies, never edit production shaders."""
import argparse
import json
from pathlib import Path
import zipfile
import water_optical_probe as probe

CONTROL='reports/2026-10-22-joint-paired-water/packs/control.zip'
CONTROL_SHA='a150afe2261970d88eff432b1a30c5b2ad1127bf9926324222300ee12c43fcf5'
OPTICAL='reports/2026-10-22-underwater-rim-fix/optical3'
OPTICAL_SHA='4c35bd7cde0858fffddd8718c02ea3d61858fecc2683d35ec1472f0473a3af46'
VERSION='0.1.0-hit1'

def corrected(entries,helper,paired):
    result=dict(entries)
    s=result['shaders/gbuffers_water.fsh'].decode()
    s=probe.replace_one(s,'void main() {',helper+'\nvoid main() {')
    anchor='    if (upperSurface) {\n        n=rasterFacet;'
    s=probe.replace_one(s,anchor,'    vec3 opticalPoint=worldPosition;\n    int continuousStatus=-1;\n'+anchor)
    anchor='            wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);'
    s=probe.replace_one(s,anchor,'''            vec2 opticalXZ=absolutePosition.xz;
            if(underwater && footprint*1.25<=0.035 && localColumn.x>=0.8) {
                vec3 solved,solvedColumn;
                continuousStatus=continuousWaterPoint(worldPosition,waterMeanSurfaceY,solved,solvedColumn);
                if(continuousStatus==0)opticalPoint=solved;
                opticalXZ=opticalPoint.xz+cameraPosition.xz;
            }
            wave=localWaveState(opticalXZ,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);''')
    anchor='    vec3 normalView=mat3(gbufferModelView)*n;'
    s=probe.replace_one(s,anchor,'    vec3 opticalViewPos=(gbufferModelView*vec4(opticalPoint,1.0)).xyz;\n'+anchor)
    s=probe.replace_one(s,'refractionTrace(viewPos,transmittedView,','refractionTrace(opticalViewPos,transmittedView,')
    s=probe.replace_one(s,'reflectionTrace(viewPos+normalView*0.06,','reflectionTrace(opticalViewPos+normalView*0.06,')
    for name in ('waterReceiverFirstFromInterface','waterReceiverFirst'):
        s=probe.replace_one(s,name+'(worldPosition+n*0.06,reflected)',name+'(opticalPoint+n*0.06,reflected)')
    if paired:
        s=probe.replace_one(s,'gl_FragData[4]=underwater?vec4(opticalOrientedNormal,opticalGrazingBlend):vec4(0.0);',
            'gl_FragData[4]=underwater?vec4(opticalPoint,float(continuousStatus)):vec4(0.0);')
    result['shaders/gbuffers_water.fsh']=s.encode()
    return result

def generate(root,out):
    base=root/OPTICAL
    meta=json.loads((base/'manifest.json').read_text())
    archives={}
    for label,path,pin in [('control',root/CONTROL,CONTROL_SHA),('paired',base/'optical.zip',OPTICAL_SHA)]:
        probe.read_pinned(path,pin)
        with zipfile.ZipFile(path) as z:
            if len(z.namelist())!=len(set(z.namelist())):raise ValueError('duplicate archive')
            archives[label]={name:z.read(name) for name in z.namelist()}
    helper=(root/'tools/water_continuous_interface_test.glsl').read_text()
    frozen=archives['paired']['shaders/lib/ripples.glsl']
    if b'return vec3(0.0);' not in frozen:raise ValueError('requires frozen zero-ripple TEST base')
    sources={name:probe.read_pinned(base/'observer-sources'/name,pin) for name,pin in meta['generatedSourceSha256'].items()}
    key='dev/aqualumen/paired/PairedObserver.java'
    s=sources[key].decode()
    s=probe.replace_one(s,'m.put("observerVersion","0.1.0-optics3");',f'm.put("observerVersion","{VERSION}");')
    s=probe.replace_one(s,'"colortex3",List.of("orientedNormal.x","orientedNormal.y","orientedNormal.z","grazingBlend")',
        '"colortex3",List.of("opticalPoint.x","opticalPoint.y","opticalPoint.z","continuousStatus")')
    sources[key]=s.encode()
    info=json.loads(sources['fabric.mod.json']);info['version']=VERSION
    sources['fabric.mod.json']=(json.dumps(info,sort_keys=True,separators=(',',':'))+'\n').encode()
    out.mkdir(parents=True,exist_ok=False)
    source_dir=out/'observer-sources';source_dir.mkdir()
    for name,data in sources.items():
        path=source_dir/name;path.parent.mkdir(exist_ok=True,parents=True)
        with path.open('xb') as f:f.write(data)
    for label,entries in archives.items():probe.write_zip(out/(label+'.zip'),corrected(entries,helper,label=='paired'))
    receipt=dict(schema='aqualumen-continuous-hit-test-v1',testOnly=True,
        helperSHA256=probe.sha(helper.encode()),generatorSHA256=probe.sha(Path(__file__).read_bytes()),
        inputSHA256=dict(control=CONTROL_SHA,paired=OPTICAL_SHA),
        archives={label:probe.sha((out/(label+'.zip')).read_bytes()) for label in archives},
        observerBuild=probe.build_observer(root,out,source_dir,f'aqualumen-paired-water-probe-{VERSION}.jar'),
        limitations=['Frozen17s, zero ripples, known deep columns and .035 footprint only.',
            'C1 remains raster position. C3 is optical point xyz and status; -1 not eligible,0 solved,1 margin,2 column,3 bracket.',
            'Trace origins move with optical point; raster depth, shadow point and composite water eye attenuation stay unchanged.',
            'No whole-scene visibility, physical fluid, release, visual or performance acceptance.'])
    with (out/'manifest.json').open('x') as f:json.dump(receipt,f,indent=2)
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=generate(args.root.resolve(),args.out.absolute())
    print(json.dumps(result,indent=2))
    raise SystemExit(result['observerBuild']['exitCode'])
