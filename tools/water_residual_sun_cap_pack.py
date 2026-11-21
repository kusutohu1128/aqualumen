"""Build NEW TEST-only native sharp-cap snapshot from the frozen Sun STUB ZIP.

Only its helper member changes. CPU packaging is not actual renderer success,
pixel-filter equivalence, arbitrary-SPD convergence or physical/shipping adoption.
"""
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import stat
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

STUB_RELATIVE=Path('reports/2026-10-03-water-residual-native-sun/cpu-pack-stub/Aqualumen-ShoreProbe-world-water-residual-native-sun-stub-v1.zip')
STUB_SHA256='454bb0fd92b4d36fe57ffb08faf77c82557a00e9e2b6b40291faf4a74c2de111'
GUARD_SHA256='9c104ebebe77d5fd12cea95f75e30e686668a8b4605a4a5ea6227cc6e0ca5e85'
RESOLVED_SHA256='3a83e837628f4b0b21617d1468baa3d2e6fd659b5a758800cfa301d75646ab26'
STUB_HELPER_SHA256='64a5c396950401e29f2d3f40d487c25f2cf0c108b56c4a4100930339053192e3'
CAP_PATH='shaders/lib/water_residual_sun_cap.glsl'
HELPER_MEMBER='shaders/lib/water_residual_sun.glsl'
CAP_SHA256='a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3'
MATH_SHA256='d58d86873b192f6015ce0ae50c2dbce4d0ac839d6feb603685ddde217df8de1e'
RULES_SHA256='4cae55d8c6d33b65d8aab0c2ced84a051151e889b08d9ee54c8dd4dc89318787'


def build_pack(root,destination):
    """Replace only the frozen STUB helper member with the approved CAP source."""
    root=Path(root).resolve()
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination exists')
    destination=destination.resolve()
    if any(destination.is_relative_to((root/folder).resolve()) for folder in ('shaders','dist')):
        raise ValueError('TEST packs must stay outside shipping trees')
    with (root/STUB_RELATIVE).open('rb') as stream:
        raw=stream.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=STUB_SHA256:
        raise ValueError('Frozen Sun STUB digest differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
                or sum(e.file_size for e in entries)>64*1024*1024
                or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                       or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe or oversized STUB archive')
        files={e.filename:archive.read(e) for e in entries}
    metadata_bytes=files['WATER-RESIDUAL-SUN.json']
    parent=json.loads(metadata_bytes)
    if (parent.get('schema')!='aqualumen-water-residual-sun-v1'
            or parent.get('mode')!='residual-native-sun-stub' or parent.get('stub_only') is not True
            or parent.get('parent_pack_sha256')!=GUARD_SHA256
            or parent.get('resolved_parent_pack_sha256')!=RESOLVED_SHA256
            or parent.get('sun_helper_sha256')!=STUB_HELPER_SHA256
            or parent.get('geometry_factor')!=4 or parent.get('fixed_phase_seconds')!=120.0
            or parent.get('shipping_fix') is not False or parent.get('pack_enforces_world_guard') is not False):
        raise ValueError('Unapproved frozen STUB policy')
    if hashlib.sha256(files[HELPER_MEMBER]).hexdigest()!=STUB_HELPER_SHA256:
        raise ValueError('STUB helper provenance differs')
    for name,digest in parent['old_helper_sha256'].items():
        if hashlib.sha256(files[name]).hexdigest()!=digest:
            raise ValueError('Old helper provenance differs')
    if hashlib.sha256(files['shaders/lib/atmosphere.glsl']).hexdigest()!=parent['atmosphere_sha256']:
        raise ValueError('Native atmosphere provenance differs')
    if 'WATER-RESIDUAL-SUN-CAP.json' in files:
        raise ValueError('STUB already contains CAP policy')
    water=files['shaders/gbuffers_water.fsh'].decode()
    recovered=water
    for tag in ('AQUALUMEN_SUN_INCLUDE','AQUALUMEN_SUN_RESTORE_ENV',
                'AQUALUMEN_SUN_CALL_BEGIN_ALIAS','AQUALUMEN_SUN_CALL_END_ALIAS'):
        begin='// '+tag+'_BEGIN\n'
        end='// '+tag+'_END\n'
        if recovered.count(begin)!=1 or recovered.count(end)!=1:
            raise ValueError('Malformed Sun removal seam')
        at=recovered.index(begin)
        finish=recovered.index(end,at)+len(end)
        recovered=recovered[:at]+recovered[finish:]
    if hashlib.sha256(recovered.encode()).hexdigest()!=parent['parent_water_fs_sha256']:
        raise ValueError('Sun removal does not recover guard FS')
    with (root/CAP_PATH).open('rb') as stream:
        helper=stream.read(262145)
    if not helper or len(helper)>262144 or hashlib.sha256(helper).hexdigest()!=CAP_SHA256:
        raise ValueError('CAP helper is not the approved snapshot')
    files[HELPER_MEMBER]=helper
    current={
        'schema':'aqualumen-water-residual-sun-cap-v1','mode':'residual-native-sun-sharp-cap',
        'test_only':True,'not_shipping':True,'shipping_fix':False,'stub_only':False,
        'parent_stub_pack_sha256':STUB_SHA256,'guard_parent_pack_sha256':GUARD_SHA256,
        'resolved_parent_pack_sha256':RESOLVED_SHA256,
        'parent_stub_metadata_member':'WATER-RESIDUAL-SUN.json',
        'parent_stub_metadata_sha256':hashlib.sha256(metadata_bytes).hexdigest(),
        'parent_stub_metadata_is_provenance_only':True,
        'all_inherited_metadata_is_current_optical_policy':False,
        'all_inherited_metadata_is_current_atlas_policy':False,
        'helper_input_path':CAP_PATH,'helper_archive_member':HELPER_MEMBER,
        'sun_cap_helper_sha256':CAP_SHA256,'parent_stub_helper_sha256':STUB_HELPER_SHA256,
        'old_helper_sha256':parent['old_helper_sha256'],'atmosphere_sha256':parent['atmosphere_sha256'],
        'water_fs_sha256':hashlib.sha256(files['shaders/gbuffers_water.fsh']).hexdigest(),
        'cpu_source_math_sha256':MATH_SHA256,'cap_rules_sha256':RULES_SHA256,
        'geometry_factor':4,'fixed_phase_seconds':120.0,'geometry_source_changed':False,
        'water_fs_source_changed_from_stub':False,'old_helpers_source_changed':False,
        'atmosphere_source_changed':False,'source_return_replaced':False,
        'scalar_units_changed':False,'scatter_policy_changed':False,'FINAL_atlas_policy_changed':False,
        'native_sun_enabled_default':1,'source_kind':0,'native_sun_implemented':True,
        'radial_order':4,'azimuth_order':12,'sun_angular_radius_radians':0.00465,
        'cap_measure':'delta=2*sin(radius/2)^2; q in [0,1]; solid weight=wq*delta*TAU/12; no renormalization',
        'source_units_scope':parent['source_units_scope'],
        'WNS_status_channels':['requested','featureApplied','sourceKind','rejectionCount'],
        'WR_legacy_status_is_WNS_application':False,
        'zero_beam_policy':'Enabled eligible zero beam: requested1/applied0/rejection0, full legacy',
        'fallback_policy':'Two unconditional old calls, full then candidate base; every unsupported inverse/node/receiver rejects WHOLE new source and returns saved full legacy/applied0; no survivor normalization',
        'covariance_policy':'Strict SPD algebra only, no epsilon inverse/floor; zero/rank fallback does not qualify very narrow SPD or near-singular convergence',
        'generated_direction_policy':'Normalize generated Sun axis/target only; observed mean n/v stay raw',
        'inverse_reconstruction_guard':'EPS8*max(1,k,eta), componentwise local binary32 guard',
        'derivative_scope':'Both legacy calls unconditional before NEW varying branches; unchanged implicit trace lookups require NEAREST/base-level fixture qualification, not general Iris safety',
        'response_scope':'Sharp central cap only; native derivative pixel-AA is not an equivalent oracle. Cache also changes scatter: subtract actual legacy R*(scatterPositive-scatterZero)',
        'domain_scope':'Current broad positive covariance and fixed support fixtures only; arbitrary/narrow SPD, rim, visibility and critical limits unaccepted',
        'implementation_qualification':'Approved source snapshot, not same-binary execution, convergence or acceptance',
        'targets':parent['targets'],'original_sha256':parent['original_sha256'],
        'runtime_accepted':False,'GL_neutrality_verified':False,'pixel_AA_equivalence_accepted':False,
        'energy_accepted':False,'reciprocity_accepted':False,'visual_accepted':False,
        'performance_accepted':False,'generated_geometry_accepted':False,'motion_accepted':False,
        'pack_enforces_world_guard':False,
    }
    files['WATER-RESIDUAL-SUN-CAP.json']=(json.dumps(current,sort_keys=True,indent=2)+'\n').encode()
    files['WATER-RESIDUAL-SUN-CAP.txt']=(
        'TEST ONLY sharp native Sun CAP4x12 source snapshot. Current policy: WATER-RESIDUAL-SUN-CAP.json.\n'
        'All inherited STUB/residual/atlas declarations are provenance, not current new-feature policy.\n'
        'Only helper member changed: water FS/geometry/full atmosphere/scatter/units copied unchanged.\n'
        'WNS application distinct from WR legacy. Zero beam stays full legacy, requested1/applied0/rejection0.\n'
        'Two unconditional old calls and all-or-nothing cap rejection; no surviving-node normalization.\n'
        'No arbitrary/narrow-SPD, rim/visibility/critical, pixel-AA, energy/reciprocity, Iris, visual or shipping acceptance.\n'
    ).encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.sun-cap-',suffix='.zip',dir=destination.parent,delete=False) as output:
            temporary=Path(output.name)
            with ZipFile(output,'w',compression=ZIP_DEFLATED) as archive:
                for name,content in sorted(files.items()):
                    entry=ZipInfo(name,(2026,10,3,0,0,0))
                    entry.compress_type=ZIP_DEFLATED
                    entry.external_attr=0o100644<<16
                    archive.writestr(entry,content)
        os.link(temporary,destination)
    finally:
        if temporary is not None:
            temporary.unlink()
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    try:
        path=build_pack(Path(__file__).resolve().parents[1],args.destination)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected native Sun CAP pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__':
    main()
