"""NEW physical-display TEST packs; no model, geometry or shipping adoption."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import stat
from zipfile import BadZipFile,ZipFile

from water_sun_support_pack import _publish,SUPPORT_STORE,STORE,HELPER,WATER,CERTIFICATE_SHA

MANIFEST='WATER-SUN-SUPPORT-PHYSICAL-VIEW.json'
FINAL='shaders/final.fsh'
FROZEN=Path('reports/2026-10-03-water-sun-support/cpu-pack')
PARENTS={
    'reject':('Aqualumen-ShoreProbe-world-sun-support-reject-reasons-v1.zip',
        '681bd672fde78d6e7e9a89a873c2b29a3d0b64d81f473c245960bbc4cccbe0ff'),
    'zero':('Aqualumen-ShoreProbe-world-sun-support-zero-reasons-v1.zip',
        '7f15dbc05a68cc80be3ae0f6ea66ec5ae3c3f42785eb753d4e603f7089ba9048')}
FINAL_SHA='43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf'
WATER_SHA='dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4'


def sha(value): return hashlib.sha256(value).hexdigest()


def build_pack(root,destination,mode='zero'):
    """Restore only original FINAL and exact role-STORE-free water main."""
    root=Path(root).resolve();destination=Path(destination)
    if type(mode) is not str or mode not in PARENTS: raise ValueError('Unknown support policy')
    if destination.exists() or destination.is_symlink(): raise FileExistsError('Destination exists')
    lexical=destination.absolute();destination=destination.resolve()
    for candidate in (lexical,destination):
        if any(candidate.is_relative_to(root/folder) for folder in ('shaders','dist')):
            raise ValueError('TEST destination overlaps shipping')
        if candidate.is_relative_to(root/'reports') and not candidate.is_relative_to(root/'reports/2026-10-03-water-sun-support/cpu-physical-view'):
            raise ValueError('Other report trees frozen')
    name,pin=PARENTS[mode];raw=(root/FROZEN/name).read_bytes()
    if len(raw)>64*1024*1024 or sha(raw)!=pin: raise ValueError('Frozen reasons parent differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
            or sum(e.file_size for e in entries)>64*1024*1024
            or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe parent archive')
        files={e.filename:archive.read(e) for e in entries}
    parent_bytes=files['WATER-SUN-SUPPORT.json'];parent=json.loads(parent_bytes)
    if (parent.get('schema')!='aqualumen-water-sun-support-v1' or parent.get('mode')!=mode
        or parent.get('observe')!='reasons' or parent.get('shipping_accepted') is not False
        or parent.get('geometry_factor')!=4 or parent.get('fixed_phase_seconds')!=120.0):
        raise ValueError('Unapproved parent policy')
    original_final=files['original/'+FINAL];physical=files['SUN-SUPPORT-physical.fsh']
    declared=json.loads(files['UNDERWATER-PROBE.json'])['original_sha256'][FINAL]
    store=SUPPORT_STORE if mode=='zero' else STORE
    if (sha(original_final)!=FINAL_SHA or declared!=FINAL_SHA or sha(physical)!=WATER_SHA
        or files[WATER].decode().count(store)!=1 or files[WATER].decode().replace(store,'').encode()!=physical
        or sha(files[HELPER])!=parent['helper_sha256']
        or 'uniform sampler2D colortex9;' in original_final.decode()):
        raise ValueError('Physical source recovery differs')
    prior_final=files[FINAL];prior_water=files[WATER]
    archives={'PARENT-SUN-PHYSICAL-VIEW-final.fsh':prior_final,
              'PARENT-SUN-PHYSICAL-VIEW-water.fsh':prior_water}
    if any(name in files for name in (*archives,MANIFEST)):
        raise ValueError('Physical wrapper already present')
    files.update(archives);files[FINAL]=original_final;files[WATER]=physical
    metadata=dict(schema='aqualumen-water-sun-support-physical-view-v1',mode=mode,
        view='physical-final',test_only=True,not_shipping=True,shipping_fix=False,
        parent_pack_sha256=pin,parent_metadata_member='WATER-SUN-SUPPORT.json',parent_metadata_sha256=sha(parent_bytes),
        changed_existing_members=[FINAL,WATER],original_archives_unchanged=True,
        parent_final_member='PARENT-SUN-PHYSICAL-VIEW-final.fsh',parent_final_sha256=sha(prior_final),
        parent_water_member='PARENT-SUN-PHYSICAL-VIEW-water.fsh',parent_water_sha256=sha(prior_water),
        restored_final_member='original/'+FINAL,restored_final_sha256=FINAL_SHA,
        physical_water_fs_member='SUN-SUPPORT-physical.fsh',physical_water_fs_sha256=WATER_SHA,
        helper_sha256=parent['helper_sha256'],certificate_sha256=CERTIFICATE_SHA if mode=='zero' else None,
        same_frozen_kernel_and_guard=True,geometry_factor=4,fixed_phase_seconds=120.0,
        guard_uniform=parent['guard_uniform'],guard_call_expression=parent['guard_call_expression'],
        role_STORE_removed=True,fully_observer_free=False,inherited_MRT_and_TES_retained=True,
        helper_reason_and_certificate_assignments_retained=True,
        inherited_metadata_is_current_display_policy=False,inherited_FINAL_legends_authoritative=False,
        FINAL_display_policy_changed=True,FINAL_policy='Exact original exposure/tone/gamma and five-tap display AA; no atlas',
        performance_settings_changed=False,sky_cloud_reflection_density_source_changed=False,
        current_FINAL_fixed16_qualification_available=False,C9_C12_FINAL_uniforms_expected_inactive=True,
        operator_application_observed=False,fixed16_minimum4_diagnostic_gate_waived=False,
        runtime_evidence_scope='Typed guarded translucent uniform + attached stages and physical PNG/timing only; no FINAL-bound count/raw16 qualification',
        source_recovery='Remove only role STORE from parent water; restore exact original FINAL; archived parent sources recover observer/atlas bytes',
        physical_accepted=False,runtime_accepted=False,pixel_AA_accepted=False,visual_accepted=False,
        performance_accepted=False,energy_accepted=False,reciprocity_accepted=False,shipping_accepted=False,
        ordinary_scope='Dedicated guarded TEST world only; phase120/tess4/resolved optics are not normal shipping equivalence')
    files[MANIFEST]=(json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode()
    _publish(files,destination);return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    parser.add_argument('--mode',choices=('reject','zero'),default='zero');args=parser.parse_args()
    try: path=build_pack(Path(__file__).resolve().parents[1],args.destination,args.mode)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected physical-view TEST pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__': main()
