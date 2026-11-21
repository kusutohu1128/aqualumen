"""NEW TEST support-zero policy packs; CPU packaging is not renderer proof."""
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import stat
import tempfile
from zipfile import BadZipFile,ZipFile,ZipInfo,ZIP_DEFLATED

from water_snell_main_pack import (HELPER,WATER,NODE,NODE_SHA,NODE_EXTENSION_GUARD,
    recover_helper as recover_snell_helper,recover_inputs,INPUT_STORE,FAILURE)
from water_residual_sun_reason_pack import STORE
from water_residual_sun_iris_runtime import COORDINATES

MANIFEST='WATER-SUN-SUPPORT.json'
FROZEN=Path('reports/2026-10-03-water-snell-main/cpu-pack')
PARENTS={
    'reasons':('Aqualumen-SnellMain-stable-reasons-v1.zip',
        '64e1a26e8225934639f7a265e3117f0733a6a7ca6ddb4489d7481d308a63d24b'),
    'inputs':('Aqualumen-SnellMain-stable-inputs-v1.zip',
        'b196be472cefc08106023b54675710037a92d6aca798748568ec9a7a453e4bff')}
CERTIFICATE='shaders/lib/water_sun_support.glsl'
CERTIFICATE_SHA='f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a'
PARENT_HELPERS={
    'reasons':'a0f5a99736429e07a839cf8b7c0ec2c67f5f19486600b714a924dc947b7ff9fd',
    'inputs':'0d62d7b6d9067934c62787677070eb7aa923c7b4eff67ec3250a218d0af3579e'}
PARENT_WATER={
    'reasons':'9ff50e1232b6c1a3e2478b9dfaa97ce223dddef58ed11fb6b088fdca22a856c1',
    'inputs':'2163974162c8656811b18a595f0fa950279db3cdebff431204f07bcbdee430a9'}
QUALIFICATION='        nodeValid=snell.status==1;\n'
QUALIFIED='        nodeValid=snell.status==1 && WSP_supportClass==1;\n'
BODIES={
    'INCLUDE':'#include "/lib/water_sun_support.glsl"\nvec4 WSP_counts=vec4(0.0);\n',
    'RESET':'    WSP_counts=vec4(0.0);\n',
    'POLICY':('        int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);\n'
              '        WSP_counts.w+=1.0;\n'
              '        if (WSP_supportClass==0) {\n'
              '            WSP_counts.x+=1.0;\n'
              '            continue;\n'
              '        }\n'
              '        if (WSP_supportClass==1) WSP_counts.y+=1.0;\n'
              '        else WSP_counts.z+=1.0;\n'),
    'QUALIFICATION':QUALIFIED}
COUNT_EXPRESSION='WSP_counts.x+64.0*WSP_counts.y+4096.0*WSP_counts.z+262144.0*WSP_counts.w'
SUPPORT_STORE=('// AQUALUMEN_SUN_SUPPORT_STORE_BEGIN\n'+
    STORE.replace('    gl_FragData[2]=WNS_status;\n',
        '    gl_FragData[2]=vec4(WNS_status.x,WNS_status.y,'+COUNT_EXPRESSION+',WNS_status.w);\n')+
    '// AQUALUMEN_SUN_SUPPORT_STORE_END\n')
COUNT_POLICY=dict(base=64,field_range=[0,48],
    formula='zero+64*support+4096*unknown+262144*calls',
    class_sum_equals_calls=True,maximum_binary32_exact_exclusive=16777216,
    invocation_scope='Once after unchanged target/axis precheck and before inverse node; no pre/post-loop classification',
    source_kind_constant=0,physical_WNS_status_z_unchanged=True)


def sha(value): return hashlib.sha256(value).hexdigest()


def _tag(name):
    return ('// AQUALUMEN_SUN_SUPPORT_BEGIN:'+name+'\n'+BODIES[name]+
            '// AQUALUMEN_SUN_SUPPORT_END:'+name+'\n')


def recover_helper(observed):
    """Recover the exact same-observer frozen stable helper; not optical proof."""
    source=observed.decode()
    if 'AQUALUMEN_SUN_SUPPORT_BEGIN:' in source:
        for name in BODIES:
            tagged=_tag(name)
            if source.count(tagged)!=1: raise ValueError('Support helper tag differs: '+name)
            source=source.replace(tagged,QUALIFICATION if name=='QUALIFICATION' else '')
    recovered=source.encode()
    if sha(recovered) not in PARENT_HELPERS.values(): raise ValueError('Recovered stable helper differs')
    return recovered


def recover_water(observed,observe):
    """Recover the exact frozen observer FS; inputs C12 is not TES."""
    if observe not in PARENTS: raise ValueError('Unknown observer role')
    source=observed.decode()
    if 'AQUALUMEN_SUN_SUPPORT_STORE_' in source:
        if observe!='reasons' or source.count(SUPPORT_STORE)!=1:
            raise ValueError('Certificate count STORE differs')
        source=source.replace(SUPPORT_STORE,STORE)
    if sha(source.encode())!=PARENT_WATER[observe]: raise ValueError('Recovered stable FS differs')
    return source.encode()


def transform_helper(original):
    recover_helper(original);source=original.decode()
    seams={
        'INCLUDE':'#define AQUALUMEN_WATER_RESIDUAL_SUN\n',
        'RESET':'    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n',
        'POLICY':FAILURE+'// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:BRANCH\n',
        'QUALIFICATION':QUALIFICATION}
    for name,seam in seams.items():
        if source.count(seam)!=1: raise ValueError('Support seam differs: '+name)
        replacement=(_tag(name) if name=='QUALIFICATION' else
                     FAILURE+_tag(name)+'// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:BRANCH\n'
                     if name=='POLICY' else seam+_tag(name))
        source=source.replace(seam,replacement)
    if recover_helper(source.encode())!=original: raise ValueError('Support recovery differs')
    return source.encode()


def _parent(root,observe):
    filename,pin=PARENTS[observe];raw=(root/FROZEN/filename).read_bytes()
    if len(raw)>64*1024*1024 or sha(raw)!=pin: raise ValueError('Frozen stable parent changed')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
            or sum(e.file_size for e in entries)>64*1024*1024
            or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe stable archive')
        files={e.filename:archive.read(e) for e in entries}
    metadata=json.loads(files['WATER-SNELL-MAIN.json'])
    if (metadata.get('schema')!='aqualumen-water-snell-main-v1' or metadata.get('mode')!='stable'
        or metadata.get('observe')!=observe or metadata.get('shipping_fix') is not False):
        raise ValueError('Unapproved stable parent')
    helper=files[HELPER];reason_helper=recover_inputs(helper) if observe=='inputs' else helper
    recover_snell_helper(reason_helper)
    if sha(helper)!=PARENT_HELPERS[observe] or sha(files[WATER])!=PARENT_WATER[observe]:
        raise ValueError('Stable observer source differs')
    original=files['PARENT-SNELL-MAIN-node.glsl']
    if (sha(original)!=NODE_SHA or original.count(NODE_EXTENSION_GUARD.encode())!=1
        or files[NODE]!=original.replace(NODE_EXTENSION_GUARD.encode(),b'',1)):
        raise ValueError('Adapted inverse node differs')
    store=INPUT_STORE if observe=='inputs' else STORE
    if files[WATER].decode().count(store)!=1 or files[WATER].decode().replace(store,'').encode()!=files['SNELL-MAIN-physical.fsh']:
        raise ValueError('Physical source recovery differs')
    return files,metadata,pin


def _publish(files,destination):
    destination.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.sun-support-',suffix='.zip',dir=destination.parent,delete=False) as output:
            temporary=Path(output.name)
            with ZipFile(output,'w',compression=ZIP_DEFLATED) as archive:
                for name,content in sorted(files.items()):
                    entry=ZipInfo(name,(2026,10,3,0,0,0));entry.compress_type=ZIP_DEFLATED
                    entry.external_attr=0o100644<<16;archive.writestr(entry,content)
        os.link(temporary,destination)
    finally:
        if temporary is not None: temporary.unlink()


def build_pack(root,destination,mode='reject',observe='reasons'):
    """Publish TEST reject or certified-zero policy; no runtime acceptance."""
    root=Path(root).resolve();destination=Path(destination)
    if type(mode) is not str or mode not in ('reject','zero'): raise ValueError('Unknown support policy')
    if type(observe) is not str or observe not in PARENTS: raise ValueError('Unknown observer role')
    if destination.exists() or destination.is_symlink(): raise FileExistsError('Destination exists')
    lexical=destination.absolute();destination=destination.resolve()
    for candidate in (lexical,destination):
        if any(candidate.is_relative_to(root/folder) for folder in ('shaders','dist')):
            raise ValueError('TEST destination overlaps shipping')
        if candidate.is_relative_to(root/'reports') and not candidate.is_relative_to(root/'reports/2026-10-03-water-sun-support'):
            raise ValueError('Existing report trees frozen')
    files,parent,pin=_parent(root,observe)
    files['PARENT-SUN-SUPPORT-helper.glsl']=files[HELPER]
    files['PARENT-SUN-SUPPORT-water.fsh']=files[WATER]
    files['PARENT-SUN-SUPPORT-physical.fsh']=files['SNELL-MAIN-physical.fsh']
    if mode=='zero':
        certificate=(root/CERTIFICATE).read_bytes()
        if sha(certificate)!=CERTIFICATE_SHA: raise ValueError('Support certificate differs')
        files[CERTIFICATE]=certificate;files[HELPER]=transform_helper(files[HELPER])
        if observe=='reasons': files[WATER]=files[WATER].decode().replace(STORE,SUPPORT_STORE).encode()
    recover_helper(files[HELPER]);recover_water(files[WATER],observe)
    current_store=SUPPORT_STORE if mode=='zero' and observe=='reasons' else INPUT_STORE if observe=='inputs' else STORE
    files['SUN-SUPPORT-physical.fsh']=files[WATER].decode().replace(current_store,'').encode()
    channels={key:value.copy() for key,value in parent['target_channels'].items()}
    if observe=='reasons': channels['10'][2]='certificateCounts'
    metadata=dict(schema='aqualumen-water-sun-support-v1',mode=mode,observe=observe,test_only=True,
        not_shipping=True,shipping_fix=False,parent_pack_sha256=pin,
        parent_manifest_member='WATER-SNELL-MAIN.json',parent_manifest_sha256=sha(files['WATER-SNELL-MAIN.json']),
        parent_shader_bytes_exact=mode=='reject',certificate_present=mode=='zero',
        certificate_member=CERTIFICATE if mode=='zero' else None,
        certificate_sha256=CERTIFICATE_SHA if mode=='zero' else None,
        certificate_arithmetic='Exact Q24 integer outward intervals; no added extension or float arithmetic',
        countsNotCollected=mode=='reject' or observe=='inputs',
        current_certificate_counts_observed=mode=='zero' and observe=='reasons',certificate_count_policy=COUNT_POLICY,
        target_channels=channels,source_kind_constant=0,
        fixed_texel_coordinates=[list(p) for p in COORDINATES],minimum_qualified_applied_points=4,
        declared_cap_rule=[4,12],geometry_factor=4,fixed_phase_seconds=120.0,
        guard_uniform=parent['guard_uniform'],guard_call_expression='if (aqualumenSunTestAuthorized==1)',
        helper_sha256=sha(files[HELPER]),observer_water_fs_sha256=sha(files[WATER]),
        physical_water_fs_member='SUN-SUPPORT-physical.fsh',physical_water_fs_sha256=sha(files['SUN-SUPPORT-physical.fsh']),
        C12_is_TES=observe=='reasons',inherited_FINAL_legends_authoritative=False,
        certificate_counts_scope=('Same-draw loop calls only; no pre/post-loop or axis-failure classification; separate from inputs capture'
            if mode=='zero' and observe=='reasons' else 'Not observed; reject does not invoke certificate, inputs has no count lane'),
        certificate_policy=dict(absent=0,supported=1,unknown=-1,
            absent_action='Continue with zero air-Sun node contribution only; no survivor normalization',
            supported_action='Unchanged stable inverse, reconstruction EPS8, R/receiver/kernel gates',
            unknown_action='Whole result fallback through original branch2; never zero or supported',
            branch2_scope='Inverse status failure OR certificate unknown in zero mode; not individually distinguished'),
        physical_accepted=False,runtime_accepted=False,visual_accepted=False,pixel_AA_accepted=False,
        shipping_accepted=False,GL_neutrality_verified=False,
        policy_scope=('Reject shader bytes exactly preserve frozen stable source and all original archives' if mode=='reject' else
            'Only certified absent air-Sun nodes skipped; original 48 weights/legacy full-base/geometry/source units retained; unknown whole fallback'))
    files[MANIFEST]=(json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode()
    _publish(files,destination);return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--mode',choices=('reject','zero'),default='reject')
    parser.add_argument('--observe',choices=('reasons','inputs'),default='reasons')
    args=parser.parse_args()
    try: path=build_pack(Path(__file__).resolve().parents[1],args.destination,args.mode,args.observe)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected Sun support pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__': main()
