"""TEST-only same-invocation refraction stop witness; no production edits."""
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import water_coast_attribution_pack as base

ROOT=base.ROOT
OUT=ROOT/'reports/2026-10-06-water-coast-stop'
PACK='Aqualumen-ShoreProbe-world-CoastStop-v1.zip'
BEGIN,END='// DEBUG-coast-stop-BEGIN\n','// DEBUG-coast-stop-END\n'


def block(value):
    return BEGIN+value+END


def strip(value):
    while BEGIN in value:
        a=value.index(BEGIN)
        b=value.index(END,a)+len(END)
        value=value[:a]+value[b:]
    return value


def transform(original):
    files=base.transform(original)
    fs=files['shaders/gbuffers_water.fsh'].decode()
    fs=base.once(fs,'/* RENDERTARGETS:0,9,10,11 */','/* RENDERTARGETS:0,9,10,11,12,13,14,15 */')
    start=fs.index('vec2 refractionTrace(')
    end=fs.index('\nvoid main()',start)
    function=fs[start:end]
    def before(old,observation):
        nonlocal function
        function=base.once(function,old,block(observation)+old)
    before('    if (abs(ray.z) < 0.02) return original;\n',
        '    if (abs(ray.z)<0.02) stopCode=1.0;\n')
    before('        vec4 projected = gbufferProjection * vec4(origin + ray * travel, 1.0);\n',
        '        stopIteration=float(i); stopTravel=travel;\n')
    before('        if (projected.w <= 0.0) break;\n',
        '        if (projected.w<=0.0) stopCode=2.0;\n')
    before('        if (any(lessThan(candidate, vec2(0.001))) || any(greaterThan(candidate, vec2(0.999)))) break;\n',
        '        stopCandidate=candidate;\n'
        '        if (any(lessThan(candidate,vec2(0.001))) || any(greaterThan(candidate,vec2(0.999)))) stopCode=3.0;\n')
    before('        if (depth >= 0.999999) {\n',
        '        stopDepth=depth;\n'
        '        if (depth>=0.999999) stopCode=4.0;\n')
    before('        // A foreground bank must never leak into the water behind it.\n',
        '        stopReceiverZ=receiver.z;\n'
        '        stopReceiverWorldY=relativeWorld(receiver).y+cameraPosition.y;\n'
        '        stopBankClearance=origin.z+0.025-receiver.z;\n'
        '        stopSurfaceClearance=surfaceY+0.08-stopReceiverWorldY;\n')
    before('        if (receiver.z > origin.z + 0.025) break;\n',
        '        if (receiver.z>origin.z+0.025) stopCode=5.0;\n')
    before('        if (upperSurface && relativeWorld(receiver).y + cameraPosition.y > surfaceY + 0.08) break;\n',
        '        if (upperSurface && relativeWorld(receiver).y+cameraPosition.y>surfaceY+0.08) stopCode=6.0;\n')
    before('        if (nextTravel <= 0.0) break;\n',
        '        stopNextTravel=nextTravel;\n'
        '        if (nextTravel<=0.0) stopCode=7.0;\n')
    before('            opticalPath = clamp(travel, 0.0, 48.0);\n','            stopCode=0.0;\n')
    before('        if (upperSurface && i==8) break;\n',
        '        if (upperSurface && i==8) stopCode=8.0;\n')
    # This is the unique function-final return, not the early near-horizontal guard.
    before('    return original;\n','    if (stopCode<0.0) stopCode=9.0;\n')
    declarations=block('float stopCode=-1.0,stopIteration=-1.0,stopTravel=-999.0;\n'
        'vec2 stopCandidate=vec2(-999.0);\n'
        'float stopDepth=-999.0,stopNextTravel=-999.0,stopReceiverZ=-999.0;\n'
        'float stopReceiverWorldY=-999.0,stopBankClearance=-999.0,stopSurfaceClearance=-999.0;\n')
    fs=fs[:start]+declarations+function+fs[end:]
    fs=base.once(fs,'    gl_FragData[3]=vec4(reflectedHit.a,upperSurface?1.0:0.0,worldNormal.y,1.0);\n',
        '    gl_FragData[3]=vec4(reflectedHit.a,stopCode,stopIteration,stopTravel);\n')
    tail='    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
    fs=base.once(fs,tail,tail+block(
        '    gl_FragData[4]=vec4(stopCandidate,stopDepth,stopNextTravel);\n'
        '    gl_FragData[5]=vec4(viewPos,initialPath);\n'
        '    gl_FragData[6]=vec4(transmittedView,searchSeed);\n'
        '    gl_FragData[7]=vec4(stopReceiverZ,stopReceiverWorldY,stopBankClearance,stopSurfaceClearance);\n'))
    nonwater='        gl_FragData[0]=vec4(lit,tex.a);\n'
    fs=base.once(fs,nonwater,nonwater+block(''.join(f'        gl_FragData[{i}]=vec4(0.0);\n' for i in range(4,8))))
    files['shaders/gbuffers_water.fsh']=fs.encode()
    prepare=files['shaders/prepare.fsh'].decode()
    formats=''.join(f'const int colortex{i}Format = RGBA32F;\nconst bool colortex{i}Clear = true;\n'
        f'const vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);\n' for i in range(12,16))
    files['shaders/prepare.fsh']=base.once(prepare,'const int colortex0Format',block(formats)+'const int colortex0Format').encode()
    # Put extra blend declarations inside the existing recoverable appended block.
    props=files['shaders/shaders.properties'].decode()
    files['shaders/shaders.properties']=base.once(props,base.END,
        ''.join(f'blend.gbuffers_water.colortex{i}=off\n' for i in range(12,16))+base.END).encode()
    final=files['shaders/final.fsh'].decode()
    final=base.once(final,'uniform sampler2D colortex0;\n','uniform sampler2D colortex0;\n'+block(
        ''.join(f'uniform sampler2D colortex{i};\n' for i in range(12,16))))
    final=base.once(final,'    gl_FragColor=vec4(clamp(panel,0.0,1.0),1.0);\n',block('''    vec4 stopProjection=texelFetch(colortex12,p,0);
    vec4 stopOrigin=texelFetch(colortex13,p,0);
    vec4 stopRay=texelFetch(colortex14,p,0);
    vec4 stopReceiver=texelFetch(colortex15,p,0);
    if (x==1 && y==0 && knowledge.a>0.5) {
        panel=vec3((reflection.y+1.0)/10.0,abs(stopRay.z),transmission.y==1.0?1.0:0.0);
        if (any(isnan(stopProjection)) || any(isinf(stopProjection))
            || any(isnan(stopOrigin)) || any(isinf(stopOrigin))
            || any(isnan(stopRay)) || any(isinf(stopRay))
            || any(isnan(stopReceiver)) || any(isinf(stopReceiver))) panel=vec3(1.0,0.0,0.0);
    }
''')+'    gl_FragColor=vec4(clamp(panel,0.0,1.0),1.0);\n')
    files['shaders/final.fsh']=final.encode()
    return files


def verify(original,files):
    recovered={n:strip(b.decode()).encode() if n.endswith(('.glsl','.fsh','.vsh','.properties')) else b for n,b in files.items()}
    fs=recovered['shaders/gbuffers_water.fsh'].decode()
    recovered['shaders/gbuffers_water.fsh']=base.once(fs,'/* RENDERTARGETS:0,9,10,11,12,13,14,15 */',
        '/* RENDERTARGETS:0,9,10,11 */').encode()
    return base.verify(original,recovered)


def build():
    assert not OUT.exists()
    original={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'),ROOT/'LICENSE']) if p.is_file()}
    files=transform(original)
    verify(original,files)
    OUT.mkdir()
    for name,blob in files.items():
        target=OUT/'diagnostic-source-v1'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(blob)
    packet=dict(files)
    packet.update({'original/'+n:b for n,b in original.items()})
    with (OUT/PACK).open('xb') as f,ZipFile(f,'w',compression=ZIP_DEFLATED) as z:
        for name,blob in sorted(packet.items()):
            item=ZipInfo(name,(2026,10,6,0,0,0));item.compress_type=ZIP_DEFLATED;item.external_attr=0o100644<<16
            z.writestr(item,blob)
    record=dict(schema='aqualumen-coast-stop-pack-v1',pack=PACK,packSHA256=base.sha((OUT/PACK).read_bytes()),
        originalSHA256={n:base.sha(b) for n,b in original.items()},exactOriginalRecoveryPassed=True,
        phaseSeconds=120.0,sameInvocation=True,secondTrace=False,productionFilesModified=False,
        stopCodes={'-1':'not invoked/TIR','0':'opaque success','1':'near horizontal rayZ','2':'nonpositive projectionW',
            '3':'viewport','4':'sampled sky','5':'foreground receiverZ','6':'above surface receiverY',
            '7':'nonpositive nextTravel','8':'upper final residual exceeded','9':'loop exhausted'},
        targets={'9':'raw known/final known/vertex unknown/water mask','10':'Fresnel/kind/confidence/path',
            '11':'SSR path/stop code/iteration/current travel','12':'last UV/depth/next travel',
            '13':'view origin xyz/initial path','14':'transmitted view ray xyz/search seed',
            '15':'last receiver view Z/world Y/bank clearance/surface clearance'},
        defaults='-999 for unexecuted fields; final ray/origin always written; stop -1 if trace not invoked',
        nativeNeutralityProven=False,actualIrisAccepted=False,physicalReceiverCorrectnessProven=False,fullGoalAchieved=False)
    with (OUT/'pack.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True)
    print(json.dumps(dict(pack=PACK,sha256=record['packSHA256'],sourceRecovery=True),indent=2))


if __name__=='__main__':build()
