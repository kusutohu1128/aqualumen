"""Build a NEW TEST-only pass-through native Sun STUB from frozen guard-v2.

CPU packaging/source recovery only, not GL neutrality or cap implementation.
Full atmosphere and all old helper bytes are copied from the pinned parent.
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

PARENT_RELATIVE=Path('reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip')
PARENT_SHA256='9c104ebebe77d5fd12cea95f75e30e686668a8b4605a4a5ea6227cc6e0ca5e85'
RESOLVED_SHA256='3a83e837628f4b0b21617d1468baa3d2e6fd659b5a758800cfa301d75646ab26'
HELPER='shaders/lib/water_residual_sun.glsl'
SUN_STUB_SHA256='64a5c396950401e29f2d3f40d487c25f2cf0c108b56c4a4100930339053192e3'
OLD_INCLUDE='#include "/lib/water_residual.glsl"\n'
OLD_CALL=('    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
          '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n')
SUN_INCLUDE=('// AQUALUMEN_SUN_INCLUDE_BEGIN\n'
             '#include "/lib/water_residual_sun.glsl"\n'
             '#define environmentSkyRadiance WNS_baseSky\n'
             '// AQUALUMEN_SUN_INCLUDE_END\n')
SUN_RESTORE=('// AQUALUMEN_SUN_RESTORE_ENV_BEGIN\n'
             '#undef environmentSkyRadiance\n'
             'bool WNS_legacyApplied() { return WR_status.y==1.0; }\n'
             '// AQUALUMEN_SUN_RESTORE_ENV_END\n')
CALL_BEGIN=('// AQUALUMEN_SUN_CALL_BEGIN_ALIAS_BEGIN\n'
            '#define waterResidualInterface waterResidualSunInterface\n'
            '// AQUALUMEN_SUN_CALL_BEGIN_ALIAS_END\n')
CALL_END=('// AQUALUMEN_SUN_CALL_END_ALIAS_BEGIN\n'
          '#undef waterResidualInterface\n'
          '// AQUALUMEN_SUN_CALL_END_ALIAS_END\n')


def build_pack(root,destination):
    """Copy the pinned parent with approved, reversible native Sun STUB seams."""
    root=Path(root).resolve()
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination exists')
    destination=destination.resolve()
    if any(destination.is_relative_to((root/folder).resolve()) for folder in ('shaders','dist')):
        raise ValueError('TEST packs must stay outside shipping trees')
    with (root/PARENT_RELATIVE).open('rb') as stream:
        raw=stream.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=PARENT_SHA256:
        raise ValueError('Frozen guard-v2 parent digest differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
                or sum(e.file_size for e in entries)>64*1024*1024
                or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                       or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe or oversized parent archive')
        files={e.filename:archive.read(e) for e in entries}
    metadata_bytes=files['WATER-RESIDUAL-PROBE.json']
    parent=json.loads(metadata_bytes)
    if (parent.get('schema')!='aqualumen-water-residual-probe-v1'
            or parent.get('mode')!='residual-interface-atlas'
            or type(parent.get('quadrature_order')) is not int or parent['quadrature_order']!=3
            or parent.get('geometry_factor')!=4 or parent.get('fixed_phase_seconds')!=120.0
            or parent.get('parent_pack_sha256')!=RESOLVED_SHA256 or parent.get('shipping_fix') is not False):
        raise ValueError('Unapproved frozen guard-v2 policy')
    for name,digest in parent['helper_sha256'].items():
        if hashlib.sha256(files[name]).hexdigest()!=digest:
            raise ValueError('Frozen helper does not match provenance')
    if HELPER in files or 'WATER-RESIDUAL-SUN.json' in files:
        raise ValueError('Parent already contains native Sun candidate')
    water=files['shaders/gbuffers_water.fsh'].decode()
    outer_include=('// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'
                   '#include "/lib/wave_residual.glsl"\n'+OLD_INCLUDE+
                   '// AQUALUMEN_RESIDUAL_INCLUDE_END\n')
    if (water.count(outer_include)!=1 or water.count(OLD_CALL)!=1
            or water.count('// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n')!=1
            or water.count('// AQUALUMEN_RESIDUAL_HOOK_END\n')!=1 or 'AQUALUMEN_SUN_' in water):
        raise ValueError('Frozen include/hook seams differ')
    with (root/HELPER).open('rb') as stream:
        helper=stream.read(262145)
    digest=hashlib.sha256(helper).hexdigest()
    if not helper or len(helper)>262144 or digest!=SUN_STUB_SHA256:
        raise ValueError('Sun helper is not the approved STUB snapshot')
    water_new=water.replace(OLD_INCLUDE,SUN_INCLUDE+OLD_INCLUDE+SUN_RESTORE).replace(OLD_CALL,CALL_BEGIN+OLD_CALL+CALL_END)
    recovered=water_new
    for block in (SUN_INCLUDE,SUN_RESTORE,CALL_BEGIN,CALL_END):
        recovered=recovered.replace(block,'')
    if recovered!=water:
        raise ValueError('Sun tag removal does not recover frozen FS')
    files[HELPER]=helper
    files['shaders/gbuffers_water.fsh']=water_new.encode()
    current={
        'schema':'aqualumen-water-residual-sun-v1','mode':'residual-native-sun-stub',
        'test_only':True,'not_shipping':True,'shipping_fix':False,'stub_only':True,
        'parent_pack_sha256':PARENT_SHA256,'resolved_parent_pack_sha256':RESOLVED_SHA256,
        'parent_metadata_member':'WATER-RESIDUAL-PROBE.json',
        'parent_metadata_sha256':hashlib.sha256(metadata_bytes).hexdigest(),
        'parent_water_fs_sha256':hashlib.sha256(water.encode()).hexdigest(),
        'parent_metadata_is_current_optical_policy':False,
        'parent_metadata_is_current_atlas_policy':False,
        'sun_helper_sha256':digest,'old_helper_sha256':parent['helper_sha256'],
        'atmosphere_sha256':hashlib.sha256(files['shaders/lib/atmosphere.glsl']).hexdigest(),
        'geometry_factor':4,'fixed_phase_seconds':120.0,'geometry_source_changed':False,
        'old_helpers_source_changed':False,'atmosphere_source_changed':False,
        'scalar_units_changed':False,'scatter_policy_changed':False,'FINAL_atlas_policy_changed':False,
        'native_sun_enabled_default':1,'source_kind':0,'supported_source_kinds':[],
        'WNS_status_channels':['requested','featureApplied','sourceKind','rejectionCount'],
        'WNS_feature_applied_stub':0,'WR_legacy_status_is_WNS_application':False,
        'model_implementation':'Pass-through STUB; no cap integral implemented',
        'native_sun_implemented':False,'radial_order':None,'azimuth_order':None,
        'source_units_scope':'Unchanged stock Sun: perpendicular beam SOLAR*cachedSolarTransmission*(1-0.85rainStrength), radiance beam/(PI*sin(radius)^2); no extra eta-squared conversion',
        'sun_angular_radius_radians':0.00465,'source_return_replaced':False,
        'covariance_policy':'Future inverse requires strict SPD; zero/rank/invalid remain full legacy, no epsilon inverse',
        'fallback_policy':'STUB always inactive full legacy; future whole replacement rejection must restore full legacy/applied0, no survivor normalization',
        'derivative_scope':'Full legacy environment and Moon base evaluated before varying selection; no general Iris derivative or receiver safety established',
        'implementation_qualification':'Approved pass-through source snapshot only; no actual renderer RED or neutrality inferred',
        'targets':parent['targets'],'original_sha256':parent['original_sha256'],
        'runtime_accepted':False,'actual_renderer_RED_observed':False,'GL_neutrality_verified':False,
        'energy_accepted':False,'reciprocity_accepted':False,'visual_accepted':False,
        'performance_accepted':False,'generated_geometry_accepted':False,'motion_accepted':False,
        'pack_enforces_world_guard':False,
    }
    files['WATER-RESIDUAL-SUN.json']=(json.dumps(current,sort_keys=True,indent=2)+'\n').encode()
    files['WATER-RESIDUAL-SUN.txt']=(
        'TEST ONLY native Sun pass-through STUB. Current policy: WATER-RESIDUAL-SUN.json.\n'
        'Inherited declarations/legends are parent provenance; old atlas unchanged.\n'
        'WNS requested/NEW-feature-applied/native-kind0/rejection-count; new feature always unapplied.\n'
        'WR status is legacy helper application, not new native Sun application.\n'
        'Stock atmosphere/cache/weather/units/scatter copied unchanged; no source return replacement.\n'
        'Inner Sun tag removal recovers guard-v2 FS; outer disable recovers resolved parent.\n'
        'Not cap implementation, actual renderer RED, neutrality, energy/reciprocity, visual or shipping acceptance.\n'
    ).encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.residual-sun-',suffix='.zip',dir=destination.parent,delete=False) as output:
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
        parser.exit(1,'Rejected native Sun pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__':
    main()
