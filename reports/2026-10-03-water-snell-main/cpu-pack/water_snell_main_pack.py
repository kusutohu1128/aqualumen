"""NEW TEST main-cap old/stable packs. CPU packaging is not renderer proof."""
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import stat
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from water_residual_sun_reason_pack import STORE, FLAGS

PARENT = Path('reports/2026-10-03-water-residual-sun-reasons/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-reasons-v1.zip')
PARENT_SHA = '61e76a7ea00265eab85614858a8dd3560dde8e3d21f1dfa4f9f6a711d0898aa4'
HELPER = 'shaders/lib/water_residual_sun.glsl'
HELPER_SHA = '3a39ab9442d4ad37a7d21110f44b8b94eb3689313bdaa7602ea9f5f1722f407c'
WATER = 'shaders/gbuffers_water.fsh'
MANIFEST = 'WATER-SNELL-MAIN.json'
NODE = 'shaders/lib/water_snell_inverse.glsl'
NODE_SHA = '4338e67785ec1bb5cf9fb7dca99f31d1913081277bae5afcbf9f46e3d4330e27'
NODE_EXTENSION_GUARD = ('#ifndef AQUALUMEN_SNELL_CPU_HOST\n'
                        '#extension GL_ARB_gpu_shader_fp64 : require\n#endif\n')
EXTENSION = ('// AQUALUMEN_SNELL_MAIN_EXTENSION_BEGIN\n'
             '#extension GL_ARB_gpu_shader_fp64 : require\n'
             '// AQUALUMEN_SNELL_MAIN_EXTENSION_END\n')
MODULE = ('// AQUALUMEN_SNELL_MAIN_MODULE_BEGIN\n'
          '#include "/lib/water_snell_inverse.glsl"\n'
          '// AQUALUMEN_SNELL_MAIN_MODULE_END\n')
REPLACEMENTS = {
    'BRANCH': (
        '        vec3 facet=axis/sqrt(axis2);\n'
        '        float facing=dot(facet,viewToEye);\n'
        '        float transmittedDot=dot(target,facet);\n'
        '        float discriminant=1.0-eta*eta*(1.0-facing*facing);\n'
        '        nodeValid=facet.y<0.0 && facing>0.0 && transmittedDot<0.0\n'
        '            && discriminant>0.0 && WNS_finite(discriminant);\n',
        '        WaterSnellNode snell=waterSnellNode(viewToEye,target,eta);\n'
        '        vec3 facet=snell.facet;\n'
        '        float facing=snell.facing;\n'
        '        nodeValid=snell.status==1;\n'),
    'RAY': ('        vec3 transmitted=refract(-viewToEye,facet,eta);\n',
            '        vec3 transmitted=snell.ray;\n'),
    'JACOBIAN': ('        float jacobian=k2*abs(transmittedDot)/(axis2*pow(abs(facet.y),3.0));\n',
                 '        float jacobian=snell.jacobian;\n'),
    'TRANSMISSION': ('        float transmission=1.0-waterFresnel(facing,eta,1.0);\n',
                    '        float transmission=snell.transmission;\n'),
}
FAILURE = '        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }\n'
INPUT_STORE = ('// AQUALUMEN_SNELL_INPUT_STORE_BEGIN\n'
               '    gl_FragData[1]=WSM_meanCalled;\n'
               '    gl_FragData[2]=WSM_viewRequested;\n'
               '    gl_FragData[3]=vec4(WSM_covariance,'+FLAGS+');\n'
               '    gl_FragData[4]=WSM_firstFailed;\n'
               '// AQUALUMEN_SNELL_INPUT_STORE_END\n')
INPUT_BODIES = {
    'GLOBALS': ('vec4 WSM_meanCalled=vec4(0.0);\n'
                'vec4 WSM_viewRequested=vec4(0.0);\n'
                'vec3 WSM_covariance=vec3(0.0);\n'
                'vec4 WSM_firstFailed=vec4(0.0);\n'),
    'ENTRY': ('    WSM_meanCalled=vec4(meanNormal,1.0);\n'
              '    WSM_viewRequested=vec4(viewToEye,WNS_status.x);\n'
              '    WSM_covariance=vec3(0.0);\n'
              '    WSM_firstFailed=vec4(0.0);\n'),
    'COVARIANCE': '    WSM_covariance=covariance;\n',
}
for _index in range(5):
    INPUT_BODIES['TARGET'+str(_index)] = (
        '        if (!nodeValid && WSM_firstFailed.w==0.0)\n'
        '            WSM_firstFailed=vec4(target,float(r*12+j+1)+64.0*WNS_reasons.x);\n')


def _input_tag(name,body):
    return '// AQUALUMEN_SNELL_INPUT_BEGIN:'+name+'\n'+body+'// AQUALUMEN_SNELL_INPUT_END:'+name+'\n'


def recover_inputs(observed):
    """Erase passive assignments for exact recovery of the same reason variant."""
    source = observed.decode()
    for name,body in INPUT_BODIES.items():
        tagged = _input_tag(name,body)
        if source.count(tagged)!=1:
            raise ValueError('Input tag differs: '+name)
        source = source.replace(tagged,'')
    recovered = source.encode()
    if sha(recovered)!=HELPER_SHA:
        recover_helper(recovered)
    return recovered


def observe_inputs(original):
    source = original.decode()
    if sha(original)!=HELPER_SHA:
        recover_helper(original)
    seams = {
        'GLOBALS': 'vec4 WNS_status=vec4(0.0); // requested, NEW applied, native-kind0, rejection-count\n',
        'ENTRY': '    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n',
        'COVARIANCE': '    vec3 covariance=waveResidualCovariance(effectiveFootprint,columnDepth);\n',
    }
    for name,seam in seams.items():
        if source.count(seam)!=1:
            raise ValueError('Input capture seam differs: '+name)
        source = source.replace(seam,seam+_input_tag(name,INPUT_BODIES[name]))
    if source.count(FAILURE)!=5:
        raise ValueError('Common failures differ')
    chunks = source.split(FAILURE)
    source = chunks[0]+''.join(_input_tag('TARGET'+str(i),INPUT_BODIES['TARGET'+str(i)])+FAILURE+tail
                              for i,tail in enumerate(chunks[1:]))
    if recover_inputs(source.encode())!=original:
        raise ValueError('Input observer recovery differs')
    return source.encode()


def _tag(name,body):
    return '// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:'+name+'\n'+body+'// AQUALUMEN_SNELL_MAIN_REPLACE_END:'+name+'\n'


def transform_helper(original):
    """Replace only inverse-node arithmetic; all other parent bytes recover."""
    if sha(original)!=HELPER_SHA:
        raise ValueError('Parent helper differs')
    source = original.decode()
    include = '#define AQUALUMEN_WATER_RESIDUAL_SUN\n'
    if source.count(include)!=1 or 'AQUALUMEN_SNELL_MAIN' in source:
        raise ValueError('Module include seam differs')
    source = source.replace(include,include+MODULE)
    for name,(old,new) in REPLACEMENTS.items():
        if source.count(old)!=1:
            raise ValueError('Inverse seam differs: '+name)
        source = source.replace(old,_tag(name,new))
    if recover_helper(source.encode())!=original:
        raise ValueError('Stable helper recovery differs')
    return source.encode()


def recover_helper(transformed):
    """Public exact old-helper source recovery, not a numerical oracle."""
    source = transformed.decode()
    if source.count(MODULE)!=1:
        raise ValueError('Module tag missing or duplicated')
    source = source.replace(MODULE,'')
    for name,(old,new) in REPLACEMENTS.items():
        tagged = _tag(name,new)
        if source.count(tagged)!=1:
            raise ValueError('Replacement tag differs: '+name)
        source = source.replace(tagged,old)
    if sha(source.encode())!=HELPER_SHA:
        raise ValueError('Recovered parent helper differs')
    return source.encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def _read_parent(root):
    raw = (root/PARENT).read_bytes()
    if len(raw)>64*1024*1024 or sha(raw)!=PARENT_SHA:
        raise ValueError('Frozen reason parent differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
            or sum(e.file_size for e in entries)>64*1024*1024
            or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                   or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe parent archive')
        files = {e.filename:archive.read(e) for e in entries}
    metadata = json.loads(files['WATER-RESIDUAL-SUN-REASONS.json'])
    if (metadata.get('schema')!='aqualumen-water-residual-sun-reasons-v1'
        or metadata.get('enabled')!=1 or metadata.get('shipping_fix') is not False
        or metadata.get('instrumented_helper_sha256')!=HELPER_SHA
        or sha(files[HELPER])!=HELPER_SHA):
        raise ValueError('Unapproved reason parent')
    water = files[WATER].decode()
    if water.count(STORE)!=1 or water.replace(STORE,'').encode()!=files['PARENT-SUN-REASONS-physical.fsh']:
        raise ValueError('Parent physical recovery differs')
    return files, metadata


def _publish(files,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.snell-main-',suffix='.zip',
                                         dir=destination.parent,delete=False) as output:
            temporary = Path(output.name)
            with ZipFile(output,'w',compression=ZIP_DEFLATED) as archive:
                for name,content in sorted(files.items()):
                    entry = ZipInfo(name,(2026,10,3,0,0,0))
                    entry.compress_type = ZIP_DEFLATED
                    entry.external_attr = 0o100644<<16
                    archive.writestr(entry,content)
        os.link(temporary,destination)
    finally:
        if temporary is not None:
            temporary.unlink()


def build_pack(root,destination,mode='stable',observe='reasons'):
    """Publish NEW old or stable TEST; whole-rejection policies are unchanged."""
    root = Path(root).resolve()
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination exists')
    destination = destination.resolve()
    if any(destination.is_relative_to(root/folder) for folder in ('shaders','dist')):
        raise ValueError('TEST destination overlaps shipping')
    reports = root/'reports'
    if destination.is_relative_to(reports) and not destination.is_relative_to(reports/'2026-10-03-water-snell-main'):
        raise ValueError('Older report trees are frozen')
    if mode not in ('old','stable'):
        raise ValueError('Expected old or stable mode')
    if observe not in ('reasons','inputs'):
        raise ValueError('Expected reasons or inputs observation')
    files,parent = _read_parent(root)
    physical = files['PARENT-SUN-REASONS-physical.fsh']
    files['PARENT-SNELL-MAIN-reason-helper.glsl'] = files[HELPER]
    files['PARENT-SNELL-MAIN-reason-water.fsh'] = files[WATER]
    files['PARENT-SNELL-MAIN-physical.fsh'] = physical
    if mode=='stable':
        original_node = (root/NODE).read_bytes()
        if sha(original_node)!=NODE_SHA or original_node.count(NODE_EXTENSION_GUARD.encode())!=1:
            raise ValueError('Stable node pin or extension seam differs')
        if NODE in files:
            raise ValueError('Parent already includes stable node')
        node = original_node.replace(NODE_EXTENSION_GUARD.encode(),b'',1)
        files['PARENT-SNELL-MAIN-node.glsl'] = original_node
        files[NODE] = node
        files[HELPER] = transform_helper(files[HELPER])
        water = files[WATER].decode()
        first,newline,rest = water.partition('\n')
        if first!='#version 330 compatibility' or not newline:
            raise ValueError('Version seam differs')
        files[WATER] = (first+'\n'+EXTENSION+rest).encode()
        physical = files[WATER].decode().replace(STORE,'').encode()
        files['SNELL-MAIN-physical.fsh'] = physical
    else:
        files['SNELL-MAIN-physical.fsh'] = physical
    reason_helper,reason_water = files[HELPER],files[WATER]
    files['SNELL-MAIN-reason-helper.glsl'] = reason_helper
    files['SNELL-MAIN-reason-water.fsh'] = reason_water
    if observe=='inputs':
        files[HELPER] = observe_inputs(reason_helper)
        water = reason_water.decode()
        if water.count(STORE)!=1:
            raise ValueError('Reason STORE differs')
        files[WATER] = water.replace(STORE,INPUT_STORE).encode()
        if files[WATER].decode().replace(INPUT_STORE,'').encode()!=physical:
            raise ValueError('Input physical FS recovery differs')
    metadata = dict(schema='aqualumen-water-snell-main-v1',mode=mode,observe=observe,test_only=True,
        not_shipping=True,shipping_fix=False,parent_pack_sha256=PARENT_SHA,
        parent_helper_sha256=HELPER_SHA,helper_sha256=sha(files[HELPER]),
        observer_water_fs_sha256=sha(files[WATER]),physical_water_fs_member='SNELL-MAIN-physical.fsh',
        physical_water_fs_sha256=sha(physical),old_shader_bytes_exact=mode=='old' and observe=='reasons',
        reason_helper_member='SNELL-MAIN-reason-helper.glsl',reason_helper_sha256=sha(reason_helper),
        reason_water_fs_member='SNELL-MAIN-reason-water.fsh',reason_water_fs_sha256=sha(reason_water),
        target_channels=parent['target_channels'],guard_uniform=parent['guard_uniform'],
        declared_cap_rule=[4,12],geometry_factor=4,fixed_phase_seconds=120.0,
        status0_policy='Unchanged whole replacement rejection',
        statusMinus1_policy='Unchanged whole replacement rejection',
        runtime_accepted=False,physics_accepted=False,visual_accepted=False,shipping_accepted=False)
    if observe=='inputs':
        metadata.update(target_channels={'9':['meanNormalX','meanNormalY','meanNormalZ','helperCalled'],
            '10':['viewX','viewY','viewZ','requested'],'11':['Cxx','Cxz','Czz','productionFlags'],
            '12':['firstFailedTargetX','firstFailedTargetY','firstFailedTargetZ','encodedFirstReasonAndNode']},
            input_helper_member=HELPER,input_helper_sha256=sha(files[HELPER]),
            input_recovery='Erase exact named input assignment blocks for same reason helper; replace input STORE with reason STORE for same reason FS',
            target_code=dict(base=64,node_index_range=[1,48],reason_range=[1,9],none=0,
                formula='(r*12+j+1)+64*firstReason',
                same_draw_first_reason=True),
            first_target_scope='First failed loop node only; node index 1..48, not all48 causes. Guard0/helper-not-called defaults0; pre/post-loop fallback may have no target.',
            helper_called_scope='Assigned1 only at actual wrapper entry; not application or all-node proof',
            flags_scope='Original main production flags; not authorization, helper call or application',
            C12_is_TES=False,FINAL_inherited_display_is_authoritative=False,
            FINAL_scope='Parent FINAL bytes preserved; inherited reason/TES panels are not current input legends',
            passive_assignments_only=True,actual_GL_neutrality_verified=False)
    if mode=='stable':
        metadata.update(node_original_member='PARENT-SNELL-MAIN-node.glsl',
            node_original_sha256=NODE_SHA,node_adapted_member=NODE,node_adapted_sha256=sha(files[NODE]),
            node_adaptation='Exact removal of extension guard only; directive hoisted immediately after FS version',
            inverse_node_recovery='Remove named module/replacement blocks and restore fixed old spans for exact parent helper',
            changed_math=['inverse facet/support','forward transmitted ray','Jacobian','transmission'],
            preserved_policies=['axis precheck','reflection formula','reconstruction EPS','ray length/up',
                'reflected hemisphere','receivers','full/base admission','whole fallback','covariance',
                '48 generated targets','solar/cache/weather units','reason STORE','geometry','FINAL'])
    files[MANIFEST] = (json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode()
    _publish(files,destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--mode',choices=('old','stable'),default='stable')
    parser.add_argument('--observe',choices=('reasons','inputs'),default='reasons')
    args = parser.parse_args()
    try:
        path = build_pack(Path(__file__).resolve().parents[1],args.destination,args.mode,args.observe)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as error:
        parser.exit(1,'Rejected Snell main pack: '+type(error).__name__+'\n')
    print(path)


if __name__=='__main__':
    main()
