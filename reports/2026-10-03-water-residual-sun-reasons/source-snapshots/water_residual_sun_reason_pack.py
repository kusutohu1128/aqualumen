"""Build a NEW passive loop-reason TEST observer from frozen guarded enabled1.

Source recovery is CPU evidence, not GL neutrality or physics acceptance.
"""
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from water_residual_sun_iris_pack import FLAGS,STORE as PARENT_STORE,PANELS as PARENT_PANELS
from water_residual_sun_iris_runtime import COORDINATES

PARENT_RELATIVE=Path('reports/2026-10-03-water-residual-sun-iris/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-iris-enabled1-v1.zip')
PARENT_SHA256='34387253bd9de9bef2e306eb45b8d3c412861f7b324e03f81a4056f60e675f2c'
SUN_MEMBER='shaders/lib/water_residual_sun.glsl'
SUN_SHA256='a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3'
MANIFEST='WATER-RESIDUAL-SUN-REASONS.json'
TAG_PATTERN=r'// AQUALUMEN_SUN_REASONS_BEGIN:([A-Z]+)\n.*?// AQUALUMEN_SUN_REASONS_END:\1\n'
STORE=('// AQUALUMEN_SUN_REASONS_STORE_BEGIN\n'
       '    gl_FragData[1]=WNS_reasons;\n'
       '    gl_FragData[2]=WNS_status;\n'
       '    gl_FragData[3]=vec4(WR_covariance,'+FLAGS+');\n'
       '// AQUALUMEN_SUN_REASONS_STORE_END\n')
PANELS=('// AQUALUMEN_SUN_REASONS_PANEL_BEGIN\n'
        '    // C9=first node reason and grouped failed-node counts; NOT coefficients.\n'
        '    vec3 panel;\n'
        '    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));\n'
        '    else if (probeStage.a<0.5) panel=vec3(1.0,1.0,0.0);\n'
        '    else if (y==1) {\n'
        '        panel=probeNormal.yzw/48.0;\n'
        '        if (q.y>0.9) panel=vec3(probeNormal.x/9.0);\n'
        '    } else if (x==0) {\n'
        '        float rejected=max(probeState.w,0.0);\n'
        '        panel=vec3(probeState.x,probeState.y,rejected/(rejected+1.0));\n'
        '        if (q.y>0.9) panel=vec3(clamp(probeState.z,0.0,1.0));\n'
        '    } else {\n'
        '        float covX=max(probeReflection.x,0.0),covZ=max(probeReflection.z,0.0);\n'
        '        float correlation=probeReflection.y/sqrt(max(covX*covZ,1e-20));\n'
        '        panel=vec3(covX/(covX+0.01),0.5+0.5*correlation,covZ/(covZ+0.01));\n'
        '        if (q.y>0.9) panel=vec3(probeReflection.w/15.0);\n'
        '    }\n'
        '// AQUALUMEN_SUN_REASONS_PANEL_END\n')
CATEGORIES={'1':'target_or_axis','2':'facet_or_critical','3':'reflected_hemisphere',
            '4':'reconstruction_or_finite','5':'kernel','6':'transmission_opaque',
            '7':'reflection_alpha_rejection','8':'sky_or_nonfinite_receiver','9':'transmission_hemisphere'}
CHANNELS={'9':['firstReason','hemisphereRejectedNodes','receiverRejectedNodes','otherRejectedNodes'],
          '10':['requested','featureApplied','sourceKind','rejectionCount'],
          '11':['Cxx','Cxz','Czz','productionFlags'],
          '12':['barycentricX','barycentricY','barycentricZ','stagePresent']}


def tagged(name,body):
    return '// AQUALUMEN_SUN_REASONS_BEGIN:'+name+'\n'+body+'// AQUALUMEN_SUN_REASONS_END:'+name+'\n'


def strip_reason_blocks(source):
    """Public exact source-recovery seam; no transformation of parent code."""
    return re.sub(TAG_PATTERN,'',source,flags=re.S)


def instrument_helper(original):
    if hashlib.sha256(original).hexdigest()!=SUN_SHA256:
        raise ValueError('Pinned CAP helper differs')
    source=original.decode()
    failure='        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }\n'
    if source.count(failure)!=5 or 'AQUALUMEN_SUN_REASONS' in source:
        raise ValueError('CAP failed-node seams differ')
    globals_line='vec4 WNS_status=vec4(0.0); // requested, NEW applied, native-kind0, rejection-count\n'
    globals_body=('vec4 WNS_reasons=vec4(0.0); // firstReason, hemisphere, receiver, other nodes\n'
        'void WNS_recordReason(float reason) {\n'
        '    if (WNS_reasons.x==0.0) WNS_reasons.x=reason;\n'
        '    if (reason==3.0 || reason==9.0) WNS_reasons.y+=1.0;\n'
        '    else if (reason==6.0 || reason==7.0) WNS_reasons.z+=1.0;\n'
        '    else WNS_reasons.w+=1.0;\n'
        '}\n')
    reset='    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n'
    if source.count(globals_line)!=1 or source.count(reset)!=1:
        raise ValueError('CAP default/reset seams differ')
    source=source.replace(globals_line,globals_line+tagged('GLOBALS',globals_body))
    source=source.replace(reset,reset+tagged('RESET','    WNS_reasons=vec4(0.0);\n'))
    bodies=[('TARGET','        if (!nodeValid) WNS_recordReason(1.0);\n'),
        ('BRANCH','        if (!nodeValid) WNS_recordReason(2.0);\n'),
        ('RAYS','        if (!nodeValid) {\n'
         '            bool reasonInverse=WNS_finite(transmitted) && WNS_finite(reflected)\n'
         '                && max(max(reconstruction.x,reconstruction.y),reconstruction.z)<=inverseBound\n'
         '                && dot(transmitted,transmitted)>=1e-6;\n'
         '            WNS_recordReason(reasonInverse?(transmitted.y>0.0?3.0:9.0):4.0);\n'
         '        }\n'),
        ('KERNEL','        if (!nodeValid) WNS_recordReason(5.0);\n'),
        ('RECEIVER','        if (!nodeValid) {\n'
         '            float reason=kind==1?6.0:(!(reflection.a<=0.0)?7.0:8.0);\n'
         '            WNS_recordReason(reason);\n'
         '        }\n')]
    chunks=source.split(failure)
    source=chunks[0]+''.join(tagged(name,body)+failure+chunk for (name,body),chunk in zip(bodies,chunks[1:]))
    if strip_reason_blocks(source).encode()!=original:
        raise ValueError('Instrumented helper recovery differs')
    return source.encode()


def build_pack(root,destination):
    """Publish a new observer ZIP without touching the parent or live shaders."""
    root=Path(root).resolve();destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination exists')
    destination=destination.resolve()
    if any(destination.is_relative_to((root/folder).resolve()) for folder in ('shaders','dist')):
        raise ValueError('TEST packs must stay outside shipping trees')
    with (root/PARENT_RELATIVE).open('rb') as stream: raw=stream.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=PARENT_SHA256:
        raise ValueError('Frozen enabled1 ZIP differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
            or sum(e.file_size for e in entries)>64*1024*1024
            or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                   or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe or oversized parent archive')
        files={e.filename:archive.read(e) for e in entries}
    parent_bytes=files['WATER-RESIDUAL-SUN-IRIS.json'];parent=json.loads(parent_bytes)
    if (parent.get('schema')!='aqualumen-water-residual-sun-iris-v1' or parent.get('enabled')!=1
        or parent.get('mode')!='guarded-native-sun-observe' or parent.get('shipping_fix') is not False
        or parent['helper_sha256'][SUN_MEMBER]!=SUN_SHA256):
        raise ValueError('Unapproved parent policy')
    original_helper=files[SUN_MEMBER];instrumented=instrument_helper(original_helper)
    physical=files['PARENT-SUN-IRIS-physical.fsh']
    water=files['shaders/gbuffers_water.fsh'].decode()
    if water.count(PARENT_STORE)!=1 or water.replace(PARENT_STORE,'').encode()!=physical:
        raise ValueError('Parent observer/physical seam differs')
    observed=water.replace(PARENT_STORE,STORE)
    if observed.replace(STORE,'').encode()!=physical:
        raise ValueError('Reason STORE recovery differs')
    parent_final=files['shaders/final.fsh'];final=parent_final.decode()
    if final.count(PARENT_PANELS)!=1:
        raise ValueError('Parent FINAL panel seam differs')
    additions={'PARENT-SUN-REASONS-helper.glsl':original_helper,
        'PARENT-SUN-REASONS-physical.fsh':physical,'PARENT-SUN-REASONS-final.fsh':parent_final}
    if MANIFEST in files or set(additions)&set(files):
        raise ValueError('Parent already has reason provenance')
    files.update(additions);files[SUN_MEMBER]=instrumented
    files['shaders/gbuffers_water.fsh']=observed.encode()
    files['shaders/final.fsh']=final.replace(PARENT_PANELS,PANELS).encode()
    metadata=dict(schema='aqualumen-water-residual-sun-reasons-v1',mode='guarded-native-sun-reason-observe',
        test_only=True,not_shipping=True,enabled=1,parent_guarded_pack_sha256=PARENT_SHA256,
        parent_guarded_metadata_member='WATER-RESIDUAL-SUN-IRIS.json',
        parent_guarded_metadata_sha256=hashlib.sha256(parent_bytes).hexdigest(),
        helper_sha256={**parent['helper_sha256'],SUN_MEMBER:hashlib.sha256(instrumented).hexdigest()},
        instrumented_helper_member=SUN_MEMBER,instrumented_helper_sha256=hashlib.sha256(instrumented).hexdigest(),
        physical_helper_member='PARENT-SUN-REASONS-helper.glsl',physical_helper_sha256=SUN_SHA256,
        physical_water_fs_member='PARENT-SUN-REASONS-physical.fsh',physical_water_fs_sha256=hashlib.sha256(physical).hexdigest(),
        observer_water_fs_sha256=hashlib.sha256(observed.encode()).hexdigest(),
        parent_final_member='PARENT-SUN-REASONS-final.fsh',parent_final_sha256=hashlib.sha256(parent_final).hexdigest(),
        original_sha256=parent['original_sha256'],geometry_factor=4,fixed_phase_seconds=120.0,declared_cap_rule=[4,12],
        guard_uniform=parent['guard_uniform'],guard_call_expression=parent['guard_call_expression'],
        world_guard_requires_mod=True,shader_authorization_gate_present=True,target_channels=CHANNELS,
        production_flags=parent['production_flags'],production_flags_range=[0,15],production_flags_expression=FLAGS,
        fixed_texel_coordinates=[list(p) for p in COORDINATES],minimum_qualified_applied_points=4,
        reason_categories=CATEGORIES,reason_groups=dict(hemisphere=[3,9],receiver=[6,7],other=[1,2,4,5,8]),
        loop_only=True,pre_or_post_loop_rejection_categorized=False,
        reason_scope='First failed NODE category only; grouped counters count nodes. Pre/post-loop fallback rejection1 may differ from grouped sum. Accepted/default/guard0/source-absent reasons0.',
        category_priority='RAYS: finite/reconstruction/length fails =>4, else transmitted.y>0 fails =>9, else reflected hemisphere=>3. RECEIVER: kind1=>6, else !(reflection.a<=0)=>7, else8.',
        category9_scope='Transmission world-y predicate fails after finite/reconstruction/length pass; category3 is remaining reflected world-y failure.',
        category7_scope='Reflection alpha predicate rejection: positive opaque alpha OR nonordered NaN; not independent opaque proof.',
        recovery='Remove helper BEGIN/END named tag blocks for exact a070; remove reason STORE for exact archived guarded physical FS.',
        observation_scope='C9 reasons, NOT legacy coefficients; inherited legends/metadata are provenance, not current atlas/telemetry.',
        source_instrumentation_present=True,predicate_arithmetic_control_flow_changed=False,
        normalization_changed=False,geometry_source_changed=False,atmosphere_source_changed=False,
        scatter_policy_changed=False,scalar_units_changed=False,FS_C0_source_observation_changed=False)
    for key in ('shipping_fix','runtime_accepted','GL_neutrality_verified','physics_accepted','pixel_AA_equivalence_accepted',
        'energy_accepted','reciprocity_accepted','visual_accepted','performance_accepted','motion_accepted',
        'generated_geometry_accepted','actual_shader_node_count_qualified','pack_enforces_world_guard',
        'actual_guard_runtime_verified','inherited_metadata_is_current_atlas_policy',
        'inherited_metadata_is_current_optical_policy','coefficient_telemetry_current'):
        metadata[key]=False
    files[MANIFEST]=(json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode()
    files['WATER-RESIDUAL-SUN-REASONS.txt']=(
        'TEST ONLY passive LOOP reason observer. C9 firstReason,hemisphere,receiver,other failed nodes.\n'
        'C10 WNS; C11 covariance/original flags; C12 TES; top-left C0 display unchanged.\n'
        'C9 is NOT coefficients. Inherited declarations/legends are provenance only.\n'
        'Reason1 target/axis,2facet/critical,3R-hemisphere,4reconstruction/finite,5kernel,6T-opaque,7R-alpha,8sky/nonfinite,9T-hemisphere.\n'
        'Category7 includes nonordered alpha, not independent opaque proof.\n'
        'Only failed loop nodes count; pre/post-loop fallback1 can differ. No gates or model changes.\n'
        'Same fixed16 and minimum4 application gate unchanged. No actual GL/runtime/physics/AA/shipping acceptance.\n').encode()
    destination.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.sun-reasons-',suffix='.zip',dir=destination.parent,delete=False) as output:
            temporary=Path(output.name)
            with ZipFile(output,'w',compression=ZIP_DEFLATED) as archive:
                for name,content in sorted(files.items()):
                    entry=ZipInfo(name,(2026,10,3,0,0,0));entry.compress_type=ZIP_DEFLATED
                    entry.external_attr=0o100644<<16;archive.writestr(entry,content)
        os.link(temporary,destination)
    finally:
        if temporary is not None: temporary.unlink()
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path);args=parser.parse_args()
    try: path=build_pack(Path(__file__).resolve().parents[1],args.destination)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected Sun reason pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__': main()
