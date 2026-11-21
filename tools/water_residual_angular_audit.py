"""Read-only CPU audit of saved residual-angular native artifacts.

No GL, app actions or writes. Peak counts describe a predeclared common ROI;
they are not a quality gate or physical/energy/reciprocity/Iris acceptance.
"""
import argparse
from array import array
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

SIZE=257
PIXELS=SIZE*SIZE
EPS8=8*2**-23
SELECTED=((104,140),(152,116),(112,104),(144,152),(116,136),(136,108),(148,132))
ROI=tuple((x,y) for y in range(88,169) for x in range(88,169)
          if (x-128)**2+(y-128)**2<=40**2)
LUMA=(.2126,.7152,.0722)
SOURCE_RETURN='    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());\n'
RULE_GUARD='#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER 3\n#endif\n#if WATER_RESIDUAL_ORDER != 3\n#error This TEST slice implements only the declared order-three rule\n#endif\n'
RULE_BODY='    const float nodes[3]=float[3](-1.7320508075688772,0.0,1.7320508075688772);\n    const float weights[3]=float[3](1.0/6.0,2.0/3.0,1.0/6.0);\n    for (int x=0;x<3;++x) for (int z=0;z<3;++z) {\n'
STORE_BEGIN='\n// RESIDUAL_NATIVE_STORE_BEGIN\n'
STORE_END='// RESIDUAL_NATIVE_STORE_END\n'
INPUT_SPECS=(('gtexture',1,1,34836,4),('colortex4',257,257,34836,4),
             ('colortex6',64,32,34836,4),('depthtex1',257,257,36012,1),
             ('shadowtex0',1,1,36012,1),('colortex8',1,1,34842,4),
             ('aqualumenBathymetry',64,64,34836,4),('colortex7',64,32,34836,4))


def require(condition,reason):
    if not condition:
        raise ValueError(reason)


def typed_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def integer_list(value,expected):
    return type(value) is list and value==expected and all(type(v) is int for v in value)


class Packet:
    def __init__(self,root):
        self.root=Path(root)
        require(not self.root.is_symlink(),'symlink packet')
        self.root=self.root.resolve(strict=True)
        self.hashes={}

    def read(self,name,limit,exact=None):
        require(isinstance(name,str) and name and not Path(name).is_absolute(),'unsafe path')
        parts=Path(name).parts
        require('..' not in parts and all(part not in ('.','') for part in parts),'unsafe path')
        path=self.root
        for part in parts:
            path=path/part
            require(not path.is_symlink(),'symlink artifact')
        require(path.resolve().is_relative_to(self.root),'artifact outside packet')
        with path.open('rb') as stream:
            data=stream.read(limit+1)
        require(len(data)<=limit and (exact is None or len(data)==exact),'artifact size')
        self.hashes[name]=hashlib.sha256(data).hexdigest()
        return data

    def text(self,name):
        return self.read(name,4*1024*1024).decode('utf-8')

    def json(self,name):
        def invalid_constant(_):
            raise ValueError('nonfinite JSON')
        data=json.loads(self.read(name,1024*1024),parse_constant=invalid_constant)
        require(type(data) is dict,'JSON object required')
        return data

    def floats(self,name,count):
        data=self.read(name,count*4,exact=count*4)
        values=array('f')
        values.frombytes(data)
        if sys.byteorder!='little':
            values.byteswap()
        require(all(math.isfinite(v) for v in values),'nonfinite binary32')
        return data,values


def replace_one(source,old,new):
    require(source.count(old)==1,'absent/ambiguous source seam')
    return source.replace(old,new,1)


def block(source,name,replacement):
    begin='// '+name+'_BEGIN\n'
    end='// '+name+'_END\n'
    require(source.count(begin)==1 and source.count(end)==1,'absent/ambiguous marker')
    start=source.index(begin)
    finish=source.index(end,start+len(begin))
    payload=source[start+len(begin):finish]
    return source[:start]+replacement+source[finish+len(end):],payload


def observer(source):
    def after(anchor,payload):
        nonlocal source
        source=replace_one(source,anchor,anchor+STORE_BEGIN+payload+STORE_END)
    def before_terminator(anchor,terminator,payload):
        nonlocal source
        require(source.count(anchor)==1,'observer anchor')
        at=source.index(terminator,source.index(anchor)+len(anchor))
        source=source[:at]+STORE_BEGIN+payload+STORE_END+source[at:]
    after('void main() {\n','    float OBS_residualGrazing=-1.0;\n')
    after('        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n',
          '        OBS_residualGrazing=resolved;\n')
    before_terminator('        gl_FragData[0]=vec4(lit,tex.a);\n','        return;',
                      ''.join(f'    gl_FragData[{s}]=vec4(0.0);\n' for s in range(1,8)))
    before_terminator('    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n','\n}',
        '    gl_FragData[1]=vec4(n,OBS_residualGrazing);\n'
        '    gl_FragData[2]=vec4(WR_covariance,max(footprint*1.25,0.035));\n'
        '    gl_FragData[3]=WR_coefficients;\n    gl_FragData[4]=WR_status;\n'
        '    gl_FragData[5]=vec4(v,float(residualEligible));\n'
        '    gl_FragData[6]=vec4(float(localColumnKnown),float(upperSurface),float(underwater),1.0);\n'
        '    gl_FragData[7]=vec4(scatter,float(residualEligible));\n')
    return source


def recover_variant(source,kind,rule):
    recovered,payload=block(source,'ANGULAR_SOURCE',SOURCE_RETURN)
    expression={'constant':'vec3(0.25,0.125,0.0625)','dark':'vec3(0.0)'}.get(kind)
    if expression is None:
        sigma=format(.00465 if kind=='narrow' else .08,'.17g')
        expression=('vec3(0.25,0.125,0.0625)*exp(-dot(normalize(ray)-vec3(0.0,1.0,0.0),'
                    'normalize(ray)-vec3(0.0,1.0,0.0))/(2.0*'+sigma+'*'+sigma+'))')
    require(payload=='    return sampleSky(lut,ray)+'+expression+';\n','source expression differs')
    if rule==3:
        require('ANGULAR_RULE_' not in recovered,'GH3 must be unchanged')
        require(recovered.count(RULE_GUARD)==1 and recovered.count(RULE_BODY)==1,'GH3 seam')
    else:
        recovered,guard=block(recovered,'ANGULAR_RULE_GUARD',RULE_GUARD)
        require(guard==f'#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER {rule}\n#endif\n#if WATER_RESIDUAL_ORDER != {rule}\n#error Angular TEST rule must match declared order\n#endif\n','GH guard differs')
        recovered,body=block(recovered,'ANGULAR_RULE_BODY',RULE_BODY)
        pattern=(rf'    const float nodes\[{rule}\]=float\[{rule}\]\(([^()]+)\);\n'
                 rf'    const float weights\[{rule}\]=float\[{rule}\]\(([^()]+)\);\n'
                 rf'    for \(int x=0;x<{rule};\+\+x\) for \(int z=0;z<{rule};\+\+z\) {{\n')
        match=re.fullmatch(pattern,body)
        require(match is not None,'GH body differs beyond arrays/loop bounds')
        arrays=[]
        for text in match.groups():
            require(re.fullmatch(r'[+\-0-9.eE,]+',text) is not None,'invalid GH numeric literal')
            values=[float(v) for v in text.split(',')]
            require(len(values)==rule and all(math.isfinite(v) for v in values),'GH array arity')
            arrays.append(values)
        nodes,weights=arrays
        require(all(w>0 for w in weights) and nodes==sorted(nodes),'nonpositive/unordered rule')
        for degree in range(2*rule):
            expected=0 if degree%2 else math.prod(range(1,degree,2))
            terms=[w*n**degree for n,w in zip(nodes,weights)]
            require(abs(math.fsum(terms)-expected)<=2e-11*max(1,abs(expected),math.fsum(map(abs,terms))),
                    'standard-normal moment differs')
        for degree,expected in ((0,1),(1,0),(2,1),(4,3)):
            f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
            require(abs(math.fsum(f32(w)*f32(n)**degree for n,w in zip(nodes,weights))-expected)<=2e-6,
                    'binary32 moment differs')
    return recovered


def matrix(value):
    require(type(value) is list and len(value)==16 and all(typed_number(v) for v in value),'matrix shape/type')
    return value


def input_identity(packet,path,case):
    data=packet.json(path+'/actual-inputs.json')
    require(data.get('schema')=='aqualumen-native-residual-angular-inputs-v1','input schema')
    program=case['program_ids'][1]
    require(type(program) is int and program>0 and all(type(data.get(k)) is int and data[k]==program
            for k in ('program','currentProgramBefore','currentProgramAfter')),'observer program identity')
    require(data.get('bindingRestored') is True,'bindings not restored')
    for before,after in (('activeTextureBefore','activeTextureAfter'),('textureBindingBefore','textureBindingAfter')):
        require(type(data.get(before)) is int and type(data.get(after)) is int and data[before]==data[after],'typed query state')
    require(33984<=data['activeTextureBefore']<=33991 and data['textureBindingBefore']>0,'query state range')
    matrices=data.get('matrices')
    names=('gbufferProjection','gbufferProjectionInverse','gbufferModelView','gbufferModelViewInverse')
    require(type(matrices) is dict and set(matrices)==set(names),'matrix names')
    matrices={name:matrix(matrices[name]) for name in names}
    require(matrix(data.get('fixedFunctionProjection'))==matrices['gbufferProjection'] and
            matrix(data.get('fixedFunctionModelView'))==matrices['gbufferModelView'],'fixed/uniform matrices differ')
    samplers=data.get('samplers')
    require(type(samplers) is list and len(samplers)==8,'sampler arity')
    identities=[]
    for unit,(name,w,h,internal,components) in enumerate(INPUT_SPECS):
        item=samplers[unit]
        require(type(item) is dict,'sampler object')
        expected=dict(unit=unit,name=name,width=w,height=h,internalFormat=internal,components=components,
                      minFilter=9728,magFilter=9728,compareMode=34894 if unit==4 else 0,
                      wrapS=33071,wrapT=33071,
                      file=f'input-sampler{unit}'+('.f32' if components==1 else '.rgba32f'))
        require(all(type(item.get(k)) is type(v) and item[k]==v for k,v in expected.items()),'sampler storage/state/type')
        require(type(item.get('texture')) is int and item['texture']>0,'sampler texture id')
        raw,values=packet.floats(path+'/'+item['file'],w*h*components)
        if unit in (2,7):
            require(all(v==(1. if i%4==3 else 0.) for i,v in enumerate(values)),'LUT/cache not black')
        if unit==3:
            require(all(v==1 for v in values),'opaque depth not open sky')
        if unit==6:
            require(packet.read(path+'/actual-bathymetry.rgba32f',len(raw),exact=len(raw))==raw,'queried/uploaded bathymetry differs')
        identities.append((expected,packet.hashes[path+'/'+item['file']]))
    require(len({s['texture'] for s in samplers})==8,'sampler texture alias')
    targets=data.get('targets')
    require(type(targets) is list and len(targets)==8,'target arity')
    for slot,item in enumerate(targets):
        require(type(item) is dict and all(type(item.get(k)) is int and item[k]==v for k,v in
                dict(slot=slot,internalFormat=34836,width=257,height=257).items()),'target scalar/storage type')
        require(type(item.get('texture')) is int and item['texture']>0,'target texture id')
    depth=data.get('depth')
    require(type(depth) is dict and all(type(depth.get(k)) is int and depth[k]==v for k,v in
            dict(slot=8,internalFormat=36012,width=257,height=257).items()),'depth storage/type')
    require(type(depth.get('texture')) is int and depth['texture']>0,'depth texture id')
    require(len({t['texture'] for t in targets}|{depth['texture']})==9,'target/depth alias')
    uploads=[]
    for name in ('uploaded-water-vertices.f32','uploaded-open-water-vertices.f32'):
        packet.floats(path+'/'+name,90)
        uploads.append(packet.hashes[path+'/'+name])
    return dict(matrices=matrices,inputs=identities,uploads=uploads)


def deltas(a,b,absolute=0.,relative=0.,components=None):
    maximum=0.
    failed=0
    for i,(x,y) in enumerate(zip(a,b)):
        if components is not None and i%4 not in components:
            continue
        delta=abs(x-y)
        maximum=max(maximum,delta)
        failed+=delta>absolute+relative*max(abs(x),abs(y))
    return dict(qualified=failed==0,maxAbsoluteDelta=maximum,excludedScalarCount=failed)


def reasons(maps,p):
    status=maps[4]
    flags=maps[6]
    names=('known','upper','underwater','water')
    result=[name+'False' for c,name in enumerate(names) if flags[p+c]!=1]
    result+=['eyeEligibilityFalse'] if maps[5][p+3]!=1 else []
    result+=['scatterEligibilityFalse'] if maps[7][p+3]!=1 else []
    result+=['validFalse'] if status[p]!=1 else []
    result+=['appliedFalse'] if status[p+1]!=1 else []
    result+=['nonFacing'] if status[p+2]<=0 else []
    result+=['opaqueReceiver'] if status[p+3]!=0 else []
    return result


def selected(maps,source):
    result=[]
    floor=struct.unpack('<f',struct.pack('<f',.035))[0]
    for x,y in SELECTED:
        p=(y*SIZE+x)*4
        why=reasons(maps,p)
        xx,xz,zz,footprint=maps[2][p:p+4]
        determinant=xx*zz-xz*xz
        mass,R,T,tir=maps[3][p:p+4]
        coefficient=(abs(mass-1)<=2e-5 and min(R,T,tir)>=0 and tir<=R+2e-5 and abs(R+T-mass)<=2e-5)
        domain=not why and maps[1][p+3]==1 and footprint==floor and min(xx,zz)>=0 and determinant>=0 and xx+zz>1e-5
        error=0.
        if source in ('constant','dark'):
            error=max(abs(maps[0][p+c]-(maps[7][p+c]*R+((.25,.125,.0625)[c]*T if source=='constant' else 0))) for c in range(3))
        result.append(dict(pixel=[x,y],domainQualified=domain,reasons=why,coefficientQualified=coefficient,
                           constantSourceMaxAbsolute=error,qualified=domain and coefficient and error<=2e-5))
    return result


def components(signal):
    maximum=max(signal.values(),default=0.)
    active={p for p,v in signal.items() if maximum>0 and v>.2*maximum}
    groups=[]
    while active:
        seed=min(active)
        active.remove(seed)
        group=[seed]
        for x,y in group:
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    q=(x+dx,y+dy)
                    if q in active:
                        active.remove(q)
                        group.append(q)
        count=len(group)
        peak=min(group,key=lambda p:(-signal[p],p))
        groups.append(dict(pixels=count,centroid=[sum(p[c] for p in group)/count for c in (0,1)],
                           peakPixel=list(peak),maxPositiveLuminance=signal[peak],
                           touchesROIBoundary=any(any((x+dx,y+dy) not in signal for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))) for x,y in group)))
    return dict(components=len(groups),groups=groups,maximumPositiveLuminance=maximum,
                positiveLuminanceSum=math.fsum(signal.values()))


def audit(packet):
    saved=Packet(packet)
    manifest=saved.json('result.json')
    require(manifest.get('schema')=='aqualumen-native-residual-angular-v1','native schema')
    require(type(manifest.get('size')) is int and manifest['size']==257,'pinned dimensions')
    require(typed_number(manifest.get('phase_seconds')) and manifest['phase_seconds']==120,'pinned phase')
    require(manifest.get('rawFormat')=='little-endian binary32 bottom-left origin' and
            manifest.get('sourceUnits')=='fixed-peak directional radiance; CHORD Gaussian, not calibrated solar beam' and
            manifest.get('observer_slot5')=='actual viewToEye xyz / residualEligible','raw/source/observer convention')
    require(integer_list(manifest.get('pure_draw_buffer_slots'),[0,1,2,3,4]) and
            integer_list(manifest.get('pure_cleared_inactive_slots'),[5,6,7]) and manifest.get('culling_enabled') is False,'draw contract')
    policy=manifest.get('policy')
    pinned_policy=dict(C0_absolute=5e-4,C0_relative=2e-4,depth_absolute=2e-6,
                       coefficient_absolute=2e-5,double_moment_scaled=2e-11,
                       binary32_moment_absolute=2e-6,ROI_center=[128,128],ROI_integer_radius=40,
                       peak_fraction=.2,component_neighbors=8,luminance=[.2126,.7152,.0722])
    require(type(policy) is dict and policy==pinned_policy,'predeclared policy differs')
    original=saved.text('source-original-expanded.fsh')
    require('#define frameTimeCounter 120.0\n' in original,'FS fixed phase absent')
    without_hook,_=block(original,'AQUALUMEN_RESIDUAL_HOOK','')
    without_helpers,_=block(without_hook,'AQUALUMEN_RESIDUAL_INCLUDE','')
    require(without_helpers==saved.text('parent-expanded.fsh'),'disabled exact recovery differs')
    for stage in range(3):
        saved.text(f'geometry-stage{stage}.glsl')
    cases=manifest.get('cases')
    require(type(cases) is list and len(cases)==12,'case arity')
    order=[(s,r) for s in ('narrow','broad','constant','dark') for r in (3,9,17)]
    frames={}
    first_inputs=None
    case_reports=[]
    excluded=set()
    total_reasons=Counter()
    reference=None
    for case,(source,rule) in zip(cases,order):
        require(type(case) is dict and case.get('source')==source and type(case.get('rule')) is int and case['rule']==rule,'case order/type')
        path=source+f'-gh{rule}'
        require(case.get('path')==path and case.get('sigma')=={'narrow':.00465,'broad':.08}.get(source),'case path/sigma')
        programs=case.get('programs')
        ids=case.get('program_ids')
        require(type(programs) is list and len(programs)==2 and type(ids) is list and len(ids)==2 and
                all(type(v) is int and v>0 for v in ids) and ids[0]!=ids[1],'program arity/id')
        for program,suffix in zip(programs,('-pure','-observer')):
            require(type(program) is dict and program.get('name')==path+suffix and program.get('linked') is True and
                    integer_list(program.get('stage_types'),[35632,35633,36487,36488]) and
                    integer_list(program.get('tess_layout'),[3,4,514,2305,0]),'reflected four-stage contract')
        pure=saved.text(path+'/pure-expanded.fsh')
        require(recover_variant(pure,source,rule)==original,'source/rule recovery differs')
        require(saved.text(path+'/observer-expanded.fsh')==observer(pure),'observer exact transform differs')
        identity_inputs=input_identity(saved,path,case)
        if first_inputs is None:
            first_inputs=identity_inputs
        require(identity_inputs==first_inputs,'immutable uploaded inputs/matrices differ')
        maps=[]
        passivity={}
        for slot in range(8):
            observed,values=saved.floats(path+f'/observer-slot{slot}.rgba32f',PIXELS*4)
            require(saved.read(path+f'/observer-repeat-slot{slot}.rgba32f',len(observed),exact=len(observed))==observed,'observer repeat differs')
            baseline,pure_values=saved.floats(path+f'/pure-slot{slot}.rgba32f',PIXELS*4)
            require(saved.read(path+f'/pure-repeat-slot{slot}.rgba32f',len(baseline),exact=len(baseline))==baseline,'pure repeat differs')
            if slot>=5:
                require(all(v==0 for v in pure_values),'pure inactive slot not cleared')
            if slot==0:
                passivity['C0']=deltas(pure_values,values,5e-4,2e-4)
            maps.append(values)
        raw_depth,depth=saved.floats(path+'/observer-depth.f32',PIXELS)
        require(saved.read(path+'/observer-repeat-depth.f32',len(raw_depth),exact=len(raw_depth))==raw_depth,'observer depth repeat')
        base_depth,pure_depth=saved.floats(path+'/pure-depth.f32',PIXELS)
        require(saved.read(path+'/pure-repeat-depth.f32',len(base_depth),exact=len(base_depth))==base_depth,'pure depth repeat')
        passivity['depth']=deltas(pure_depth,depth,2e-6)
        require(all(v['qualified'] for v in passivity.values()),'observer passivity outside declared bound')
        identity={}
        if reference is None:
            reference=(maps,raw_depth,depth)
        for slot in (1,2,5,6,7):
            if slot in (1,5,7):
                identity[f'slot{slot}xyz']=deltas(reference[0][slot],maps[slot],EPS8,EPS8,(0,1,2))
                identity[f'slot{slot}alpha']=deltas(reference[0][slot],maps[slot],components=(3,))
            else:
                identity[f'slot{slot}']=deltas(reference[0][slot],maps[slot])
        identity['depthExact']=deltas(reference[2],depth)
        identity['depthExact']['qualified']=raw_depth==reference[1]
        require(all(v['qualified'] for v in identity.values()),'common geometry/source-input arithmetic identity differs')
        case_reasons=Counter()
        excluded_here=[]
        for x,y in ROI:
            why=reasons(maps,(y*SIZE+x)*4)
            if why:
                excluded_here.append([x,y])
                excluded.add((x,y))
                case_reasons.update(why)
        total_reasons.update(case_reasons)
        selected_report=selected(maps,source)
        case_reports.append(dict(path=path,repeatQualified=True,observerPassivity=passivity,
                                 commonIdentity=identity,excludedROIPoints=len(excluded_here),
                                 excludedPixels=excluded_here,domainReasons=dict(case_reasons),selected=selected_report))
        frames[(source,rule)]=maps[0]
    peaks=[]
    if not excluded:
        for source in ('narrow','broad'):
            for rule in (3,9,17):
                source_map=frames[(source,rule)]
                dark=frames[('dark',rule)]
                signal={(x,y):max(0.,math.fsum(LUMA[c]*(source_map[(y*SIZE+x)*4+c]-dark[(y*SIZE+x)*4+c]) for c in range(3))) for x,y in ROI}
                peaks.append(dict(source=source,rule=rule,**components(signal)))
    return dict(schema='aqualumen-residual-angular-saved-cpu-audit-v1',
                descriptorOutcome='QUALIFIED' if not excluded else 'INCONCLUSIVE',
                commonROI=dict(center=[128,128],integerRadius=40,points=len(ROI),excludedPoints=len(excluded),
                               excludedPixels=[list(p) for p in sorted(excluded)],domainReasons=dict(total_reasons)),
                selectedPointQualification=dict(qualified=all(p['qualified'] for c in case_reports for p in c['selected']),
                                                  selectedPerCase=7,caseCount=12),cases=case_reports,peaks=peaks,
                policy=dict(peakFraction=.2,neighbors=8,positiveGaussianMinusDarkLuminance=list(LUMA),
                            localBinary32XYZAbsolute=EPS8,localBinary32XYZRelative=EPS8,
                            passiveC0Absolute=5e-4,passiveC0Relative=2e-4,passiveDepthAbsolute=2e-6,
                            coefficientAbsolute=2e-5,allCommonROIDomainRequired=True),
                sourceRecoveryQualified=True,immutableInputsQualified=True,consumedSha256=saved.hashes,
                rendererDeclaration=manifest.get('renderer'),GLDeclaration=manifest.get('GL'),
                physicalAccepted=False,naturalAccepted=False,shippingAccepted=False,energyAccepted=False,
                reciprocityAccepted=False,IrisAccepted=False,
                scope='Saved finite CPU evidence only. Declared GL reflection is not independently queried here. '
                      'Sampler storage/bindings are audited; actual uniform sampler types are not in this schema. '
                      'Peak components are descriptive, not a reference error, visible node count or quality gate. '
                      'No ROI subsets, surviving-node renormalization, calibrated solar beam, all-tail, visibility, '
                      'same-frame Minecraft image, FPS or adoption claim.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet',type=Path)
    args=parser.parse_args()
    try:
        result=audit(args.packet)
    except (OSError,ValueError,TypeError,KeyError,IndexError,OverflowError) as failure:
        parser.exit(1,'Rejected angular saved-output: '+type(failure).__name__+'\n')
    print(json.dumps(result,sort_keys=True,allow_nan=False))


if __name__=='__main__':
    main()
