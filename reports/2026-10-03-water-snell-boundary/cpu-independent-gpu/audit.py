"""Read-only CPU audit of all fixed standalone Snell GPU node outputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from decimal import Decimal, localcontext

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO/'tools'))
from water_snell_boundary_reference import diagnose
from water_snell_boundary_cases import fixtures, PINS, PIXELS
from water_residual_sun_integral import sun_integral, RADIUS

PINS_SOURCE = {
    'tools/water_snell_boundary_reference.py':'511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0',
    'tools/water_snell_boundary_cases.py':'9ee84c2f6cc5bc8c1b5b259bcadc4bd79e00255b55def7829ac76f14553961b5',
    'tools/water_snell_boundary_gpu.cpp':'8323353524254525fe47c57d6c47105662fee2aa079069b34162a9dc5af240a7',
    'build/water_snell_boundary_gpu-v2':'85cfc23d1a2e3e0fd5e075c2778725c8e7bc900e60d1e72074b0d558b9830c2c',
    'shaders/lib/water_snell_inverse.glsl':'4338e67785ec1bb5cf9fb7dca99f31d1913081277bae5afcbf9f46e3d4330e27',
    'tools/water_residual_sun_integral.py':'d58d86873b192f6015ce0ae50c2dbce4d0ac839d6feb603685ddde217df8de1e',
    'tools/water_residual_light_integral.py':'f5b6db7013907ab4baf6e28df0542a2f2066ddaef1c8cdb6e8a28fc4e352de92',
}
INPUT_SHA='7e181a8d6b4494a6952e1d51af369b935273dda94039eaba2e362ad6affb2d06'
CASE_SHA='a844555de190b04afd6989f6b1125a051950e4d441bc12ec7a6b4240ede8e792'
PARENT_SHA='d30c6970d6a35bcd53362328d9de2aaaaa210bf7cb40eb7fece5111675878cee'
VECTOR_ABSOLUTE=1e-7
SCALAR_RELATIVE=2e-4
C0_ABSOLUTE,C0_RELATIVE=2e-6,2e-4
BEAM=(9.,11.,12.75)
VERTEX=b'#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n'
SUFFIX=(b'\nuniform vec3 wsView; uniform vec3 wsTarget; uniform float wsEta;\n'
 b'void main(){WaterSnellNode node=waterSnellNode(wsView,wsTarget,wsEta);\n'
 b'gl_FragData[0]=vec4(node.facet,float(node.status));\n'
 b'gl_FragData[1]=vec4(node.ray,node.facing);\n'
 b'gl_FragData[2]=vec4(node.transmittedCosine,node.transmission,node.jacobian,1.0);}\n')


def require(value,message):
    if not value: raise ValueError(message)


def read(path,manifest):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=16*1024*1024,'Unbounded/missing artifact')
    raw=path.read_bytes();manifest[str(path.relative_to(REPO))]=hashlib.sha256(raw).hexdigest()
    return raw


def objects(raw):
    def unique(pairs):
        out={}
        for key,value in pairs:
            require(key not in out,'Duplicate JSON key');out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=unique)


def bits(values):
    require(all(type(x) in (int,float) and math.isfinite(x) for x in values),'Nonfinite/non-numeric values')
    return struct.pack('<'+'f'*len(values),*values)


def packet(directory,helper,inputs,manifest):
    result=objects(read(directory/'result.json',manifest))
    require(result['schema']=='aqualumen-snell-node-native-v1' and result['width']==325
        and result['height']==1 and result['targetInternalFormat']==34836
        and result['format']=='little-endian binary32','Actual final storage/schema mismatch')
    require('RTX 3080 Ti' in result['renderer'] and result['GL']=='4.6.0 NVIDIA 580.173.02'
        and result['fp64Extension'] is True,'Actual native renderer/capability mismatch')
    require(all(result[k] is False for k in ('mathAccepted','waterMainExecuted','physicalAccepted','shippingAccepted')),
        'Exporter is not a physical/water-main acceptance')
    require(read(directory/'inputs.f32',manifest)==inputs and read(directory/'helper.glsl',manifest)==helper,'Input/helper mismatch')
    require(read(directory/'attached-vertex.glsl',manifest)==VERTEX
        and read(directory/'attached-fragment.glsl',manifest)==b'#version 330 compatibility\n'+helper+SUFFIX,
        'Actual attached VS/FS bytes differ')
    uniforms=result['uniforms']
    require(len(uniforms)==3 and len({r['location'] for r in uniforms})==3,'Uniform alias/missing descriptor')
    for row,name,kind in zip(uniforms,('wsView','wsTarget','wsEta'),(35665,35665,5126)):
        require(row['name']==name and type(row['type']) is int and row['type']==kind
            and type(row['size']) is int and row['size']==1 and type(row['location']) is int
            and row['location']>=0,'Actual typed uniform mismatch')
    require(type(result['program']) is int and result['program']>0,'Program identity unavailable')
    require(len(result['uploads'])==650,'No dropping uniform query rows')
    for index,row in enumerate(result['uploads']):
        repeat,i=divmod(index,325);record=inputs[i*28:(i+1)*28]
        require(type(row['index']) is int and row['index']==i and type(row['repeat']) is int and row['repeat']==repeat
            and len(row['before'])==len(row['after'])==7
            and bits(row['before'])==bits(row['after'])==record,'Actual queried uniform bits/order differ')
    maps=[]
    for slot in range(3):
        raw=read(directory/f'slot{slot}.rgba32f',manifest)
        require(len(raw)==325*16 and read(directory/f'repeat-slot{slot}.rgba32f',manifest)==raw,'Whole-map repeat/size mismatch')
        values=struct.unpack('<'+('f'*1300),raw)
        require(all(math.isfinite(x) for x in values),'Nonfinite actual output')
        maps.append([values[i*4:(i+1)*4] for i in range(325)])
    require(result['repeatByteIdentical'] is True and result['finiteOutputs'] is True,'Recorded telemetry contradicts raw')
    require(len(result['results'])==325,'Dropped recorded output rows')
    for i,row in enumerate(result['results']):
        require(type(row['index']) is int and row['index']==i and len(row['slots'])==3,'Recorded row order/roles')
        for slot in range(3): require(bits(row['slots'][slot])==bits(maps[slot][i]),'JSON/raw output mismatch')
    return maps


def node_compare(cases,maps):
    rows=[];maximum_vector=maximum_relative=maximum_scalar=0.;counts=dict(supported=0,unsupported=0,accepted=0)
    for i,case in enumerate(cases):
        ref=case['reference']['physical'];a,b,c=(m[i] for m in maps)
        require(c[3]==1 and a[3] in (-1,0,1),'Status/output marker is not finite typed value')
        supported=ref['supported'];counts['supported' if supported else 'unsupported']+=1
        status_expected=1 if supported else 0
        vec=rel=scalar=None
        if supported:
            k=math.sqrt(float(ref['k2']))
            expected=list(map(float,ref['normal']))+list(map(float,ref['forward']))+[float(ref['facing']),-k*float(ref['transmitted_dot'])]
            actual=list(a[:3])+list(b[:3])+[b[3],c[0]]
            # The predeclared vector gate applies to facet/ray XYZ, not scalar telemetry.
            vec=max(abs(x-y) for x,y in zip(actual[:6],expected[:6]))
            scalar=max(abs(x-y) for x,y in zip(actual[6:],expected[6:]))
            rel=max(abs(c[1]/float(ref['raw_cosine_transmission'])-1),abs(c[2]/float(ref['jacobian_slope_per_solid_angle'])-1))
            maximum_vector=max(maximum_vector,vec);maximum_relative=max(maximum_relative,rel)
            maximum_scalar=max(maximum_scalar,scalar)
        passed=a[3]==status_expected and (not supported or vec<=VECTOR_ABSOLUTE and rel<=SCALAR_RELATIVE)
        counts['accepted']+=passed
        rows.append(dict(index=i,name=case['name'],family=case.get('family','normal'),supported=supported,
            actualStatus=a[3],expectedStatus=status_expected,maximumVectorAbsoluteError=vec,
            observedFacingQAbsoluteError=scalar,maximumTJRelativeError=rel,accepted=passed))
    return dict(**counts,failed=325-counts['accepted'],maximumVectorAbsoluteError=maximum_vector,
        maximumTJRelativeError=maximum_relative,observedFacingQAbsoluteError=maximum_scalar,rows=rows)


def kernel(normal,view,covariance,facet,facing,transmission,jacobian,decimal=False):
    cast=Decimal if decimal else float
    n,v,c,h=[tuple(map(cast,row)) for row in (normal,view,covariance,facet)]
    f,T,J=map(cast,(facing,transmission,jacobian));xx,xz,zz=c;det=xx*zz-xz*xz
    require(xx>0 and zz>0 and det>0 and h[1]<0,'Strict Gaussian/facet domain')
    M=sum(x*y for x,y in zip(n,v))/abs(n[1]);require(M>0,'Nonpositive mean projected area')
    dx,dz=-h[0]/h[1]+n[0]/n[1],-h[2]/h[1]+n[2]/n[1]
    quadratic=(zz*dx*dx-2*xz*dx*dz+xx*dz*dz)/det
    if decimal:
        density=(-quadratic/2).exp()/(Decimal.from_float(2*math.pi)*det.sqrt())
    else:
        density=math.exp(-.5*quadratic)/(2*math.pi*math.sqrt(det))
    return density*(f/(abs(h[1])*M))*T*J


def compare_rgb(actual,expected):
    errors=[abs(a-b) for a,b in zip(actual,expected)]
    bounds=[C0_ABSOLUTE+C0_RELATIVE*max(abs(a),abs(b)) for a,b in zip(actual,expected)]
    return dict(accepted=all(e<=b for e,b in zip(errors,bounds)),errors=errors,bounds=bounds)


def saved_sum(cases,maps):
    results=[];area=math.pi*math.sin(RADIUS)**2
    for pixel in PIXELS:
        selected=[(i,c) for i,c in enumerate(cases) if c.get('family')=='saved' and c['pixel']==list(pixel)]
        require(len(selected)==48 and [c['node'] for _,c in selected]==list(range(48)),'No48-node omission/reordering')
        fixture=selected[0][1]['saved_fixture'];actual_terms=[];reference_terms=[]
        with localcontext() as ctx:
            ctx.prec=120
            for i,case in selected:
                require(case['saved_fixture']==fixture and case['reference']['physical']['supported'] and maps[0][i][3]==1,
                    'Saved interior controls are not all supported')
                a,b,c=(m[i] for m in maps);ref=case['reference']['physical'];weight=case['weight']
                require(type(weight) is float and math.isfinite(weight) and weight>0,'Invalid positive weight')
                args=(fixture['mean_normal'],fixture['view_to_eye'],fixture['covariance'])
                actual_terms.append(weight*kernel(*args,a[:3],b[3],c[1],c[2]))
                reference_terms.append(Decimal(weight)*kernel(*args,ref['normal'],ref['facing'],
                    ref['raw_cosine_transmission'],ref['jacobian_slope_per_solid_angle'],decimal=True))
            exact=float(sum(reference_terms))
        actual=[x*math.fsum(actual_terms)/area for x in BEAM];reference=[x*exact/area for x in BEAM]
        old=sun_integral(fixture,(0.,1.,0.),BEAM,radial_order=4,azimuth_order=12)
        require(old['domain_qualified'] is True and old['evaluated_nodes']==48,'Old public interior control domain')
        results.append(dict(pixel=list(pixel),nodes=48,sourceResponseMath=actual,highPrecisionNodeReference=reference,
            oldPublicSourceResponseMath=old['source_difference_C0'],toHighPrecision=compare_rgb(actual,reference),
            toOldPublicControl=compare_rgb(actual,old['source_difference_C0'])))
    return results


def audit(root):
    root=root.resolve();manifest={}
    for name,pin in PINS_SOURCE.items(): require(hashlib.sha256(read(REPO/name,manifest)).hexdigest()==pin,'Frozen source/binary changed')
    metadata=objects(read(root/'fixed-inputs/cases.json',manifest));inputs=read(root/'fixed-inputs/inputs.f32',manifest)
    require(hashlib.sha256(inputs).hexdigest()==INPUT_SHA and hashlib.sha256((root/'fixed-inputs/cases.json').read_bytes()).hexdigest()==CASE_SHA,'Fixed input packet changed')
    require(metadata['schema']=='aqualumen-fixed-snell-node-inputs-v1' and metadata['count']==325
        and metadata['inputSHA256']==INPUT_SHA and metadata['savedMapSHA256']==PINS,'Fixed corpus identity differs')
    require(metadata['sourceSHA256']=={Path(name).name:pin for name,pin in PINS_SOURCE.items()
        if name.endswith('.py')},'Corpus source pins differ')
    cases=fixtures();require(metadata['cases']==cases and len(cases)==325,'Fresh full case/reference regeneration differs')
    require(inputs==b''.join(bits(c['input']) for c in cases),'Seven-float binary corpus differs')
    require(all(c['reference']==diagnose(c['input'][:3],c['input'][3:6],c['input'][6])
        and c['reference']['precision_agreement'] for c in cases),'Fresh80/120 oracle replay differs')
    parent=read(root/'initial-parent-arithmetic.glsl',manifest);require(hashlib.sha256(parent).hexdigest()==PARENT_SHA,'Parent arithmetic changed')
    stable=read(REPO/'shaders/lib/water_snell_inverse.glsl',manifest)
    data={name:packet(root/f'native-{name}-final',helper,inputs,manifest) for name,helper in (('parent',parent),('stable',stable))}
    comparisons={name:node_compare(cases,maps) for name,maps in data.items()}
    sums={name:saved_sum(cases,maps) for name,maps in data.items()}
    require(comparisons['stable']['accepted']==325 and all(s['toHighPrecision']['accepted'] and s['toOldPublicControl']['accepted'] for s in sums['stable']),'Stable node/source math gate RED')
    saved_fail=[r for r in comparisons['parent']['rows'] if not r['accepted'] and r['family']=='saved']
    return dict(schema='aqualumen-independent-gpu-snell-node-audit-v1',status='PASS_STANDALONE_STABLE_NODE',
        cases=325,variants=2,finiteMaps=12,exactWholeMapRepeatPairs=6,typedUniformRows=1300,
        queriedBeforeAfterFloatRecords=2600,sourceRecoveryQualified=True,comparisons=comparisons,
        savedSourceResponseMath=sums,manifest=manifest,
        parentSavedVectorFailureCount=len(saved_fail),parentSavedFailureStatus1Count=sum(r['actualStatus']==1 for r in saved_fail),
        gates=dict(vectorAbsolute=VECTOR_ABSOLUTE,TJRelative=SCALAR_RELATIVE,C0Absolute=C0_ABSOLUTE,C0Relative=C0_RELATIVE),
        sourceUnits=dict(beamDeclared=BEAM,radiusDeclared=RADIUS,measure='48positiveCPUcapweights; no normalization, no scatter subtraction; source-response math is derived, NOT rendered C0'),
        oldCriticalWholeGHGate='The fixed tilted positive node fixture still fails unchanged legacy full/base nine-node admission (sixTIR and positive reflectedY per retained cpu-math/NOTE.md). This standalone node proof does not bypass/adopt that gate.',
        limits='Parent22 saved failures use newly stricter1e-7 witness gate, NOT proof of22 whole-wrapper failures. Float32 cast facet is not re-refracted as a reference. Generated targets are not actual Iris target exports. Actual process provenance is parent-attested, not independently measured here.',
        waterMainExecuted=False,renderedC0Accepted=False,wholeCapAccepted=False,IrisAccepted=False,
        pixelAAAccepted=False,performanceAccepted=False,energyAccepted=False,physicalAccepted=False,shippingAccepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packet',type=Path)
    args=parser.parse_args();print(json.dumps(audit(args.packet),indent=2,sort_keys=True,allow_nan=False))
