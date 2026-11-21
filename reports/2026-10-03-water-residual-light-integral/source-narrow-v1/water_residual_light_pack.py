"""Build a NEW TEST-only approved light candidate from the frozen guard-v2 ZIP.

Packaging/source recovery only, not runtime or shipping acceptance. Helper
digests distinguish frozen STUB and sourceKind1 integral snapshots; no tuning.
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
HELPER='shaders/lib/water_residual_light.glsl'
LIGHT_STUB_SHA256='94972e0f5f57023d759b24379ba8c5eab50a610f444cc5b339231304446c885f'
LIGHT_INTEGRAL_SHA256='cb23f666912677e08f5838cc6e1ac79981b853dbca2bd3fbdcfd5f14eaf6d3a8'
RULES_SHA256='9b65389ee8ceeb2af4bf65806fe83e96839aaf0765b5c4587c074e689da3d7db'
OLD_INCLUDE='#include "/lib/water_residual.glsl"\n'
OLD_CALL=('    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
          '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n')
LIGHT_INCLUDE=('// AQUALUMEN_LIGHT_INCLUDE_BEGIN\n'
               '#include "/lib/water_residual_light.glsl"\n'
               '#define environmentSkyRadiance WLS_baseSky\n'
               '// AQUALUMEN_LIGHT_INCLUDE_END\n')
LIGHT_RESTORE=('// AQUALUMEN_LIGHT_RESTORE_ENV_BEGIN\n'
               '#undef environmentSkyRadiance\n'
               '// AQUALUMEN_LIGHT_RESTORE_ENV_END\n')
CALL_BEGIN=('// AQUALUMEN_LIGHT_CALL_BEGIN_ALIAS_BEGIN\n'
            '#define waterResidualInterface waterResidualLightInterface\n'
            '// AQUALUMEN_LIGHT_CALL_BEGIN_ALIAS_END\n')
CALL_END=('// AQUALUMEN_LIGHT_CALL_END_ALIAS_BEGIN\n'
          '#undef waterResidualInterface\n'
          '// AQUALUMEN_LIGHT_CALL_END_ALIAS_END\n')


def build_pack(root,destination):
    """Copy pinned parent and inject reversible approved-helper aliases."""
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
    if HELPER in files or 'WATER-RESIDUAL-LIGHT.json' in files:
        raise ValueError('Parent already contains light candidate')
    water=files['shaders/gbuffers_water.fsh'].decode()
    outer_include=('// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'
                   '#include "/lib/wave_residual.glsl"\n'+OLD_INCLUDE+
                   '// AQUALUMEN_RESIDUAL_INCLUDE_END\n')
    if (water.count(outer_include)!=1 or water.count(OLD_CALL)!=1
            or water.count('// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n')!=1
            or water.count('// AQUALUMEN_RESIDUAL_HOOK_END\n')!=1 or 'AQUALUMEN_LIGHT_' in water):
        raise ValueError('Frozen include/hook seams differ')
    with (root/HELPER).open('rb') as stream:
        helper=stream.read(262145)
    digest=hashlib.sha256(helper).hexdigest()
    if not helper or len(helper)>262144 or digest not in (LIGHT_STUB_SHA256,LIGHT_INTEGRAL_SHA256):
        raise ValueError('Light helper is not an approved source snapshot')
    stub=digest==LIGHT_STUB_SHA256
    restore=LIGHT_RESTORE if stub else LIGHT_RESTORE.replace(
        '#undef environmentSkyRadiance\n',
        '#undef environmentSkyRadiance\n'
        'bool WLS_legacyApplied() { return WR_status.y==1.0; }\n')
    water_new=water.replace(OLD_INCLUDE,LIGHT_INCLUDE+OLD_INCLUDE+restore).replace(OLD_CALL,CALL_BEGIN+OLD_CALL+CALL_END)
    recovered=water_new
    for block in (LIGHT_INCLUDE,restore,CALL_BEGIN,CALL_END):
        recovered=recovered.replace(block,'')
    if recovered!=water:
        raise ValueError('Light tag removal does not recover frozen FS')
    files[HELPER]=helper
    files['shaders/gbuffers_water.fsh']=water_new.encode()
    current={
        'schema':'aqualumen-water-residual-light-v1',
        'mode':'residual-light-integral-stub' if stub else 'residual-light-integral-narrow',
        'test_only':True,'not_shipping':True,'shipping_fix':False,'stub_only':stub,
        'parent_pack_sha256':PARENT_SHA256,'resolved_parent_pack_sha256':RESOLVED_SHA256,
        'parent_metadata_member':'WATER-RESIDUAL-PROBE.json',
        'parent_metadata_sha256':hashlib.sha256(metadata_bytes).hexdigest(),
        'parent_water_fs_sha256':hashlib.sha256(water.encode()).hexdigest(),
        'parent_metadata_is_current_optical_policy':False,
        'parent_metadata_is_current_atlas_policy':False,
        'light_helper_sha256':digest,
        'old_helper_sha256':parent['helper_sha256'],
        'geometry_factor':4,'fixed_phase_seconds':120.0,'geometry_source_changed':False,
        'old_helpers_source_changed':False,'scalar_units_changed':False,'FINAL_atlas_policy_changed':False,
        'source_kinds':{'nativeSun':0,'narrowGaussian':1,'broadGaussian':2,'constant':3,'dark':4},
        'source_kind_default':0,'light_enabled_default':1,
        'WLS_status_channels':['requested','featureApplied','sourceKind','rejectionCount'],
        'WLS_feature_applied_stub':0 if stub else None,'WR_legacy_status_is_WLS_application':False,
        'model_implementation':'Pass-through STUB' if stub else 'Finite 8x16 sourceKind1 CHORD Gaussian light-domain integral snapshot',
        'supported_source_kinds':[] if stub else [1],'native_sun_unsupported':True,
        'radial_order':None if stub else 8,'azimuth_order':None if stub else 16,
        'refined_rules_sha256':None if stub else RULES_SHA256,
        'generated_target_direction':'Not used' if stub else 'normalize analytic CHORD ring; caller n/v never normalized',
        'inverse_reconstruction_guard':'EPS8*max(1,k,eta), componentwise local binary32 guard' if not stub else None,
        'covariance_policy':'Strict SPD for new inverse; zero/rank/invalid unsupported, no epsilon inverse',
        'fallback_policy':'Whole replacement rejection restores inactive full legacy helper; applied0/rejectionCount>0, no survivor normalization',
        'source_units_scope':'Fixed peak(.25,.125,.0625) diagnostic radiance; not calibrated Sun/beam or eta-squared unit conversion',
        'implementation_qualification':'Approved source snapshot only; packaging does not prove integral execution or reference match',
        'trace_scope':'Existing implicit-lookups unchanged; NEAREST/base-level open-depth diagnostic does not establish general Iris derivative/receiver safety',
        'targets':parent['targets'],'original_sha256':parent['original_sha256'],
        'runtime_accepted':False,'actual_renderer_RED_observed':False,'GL_neutrality_verified':False,
        'energy_accepted':False,'reciprocity_accepted':False,'visual_accepted':False,
        'performance_accepted':False,'generated_geometry_accepted':False,'motion_accepted':False,
        'pack_enforces_world_guard':False,
    }
    files['WATER-RESIDUAL-LIGHT.json']=(json.dumps(current,sort_keys=True,indent=2)+'\n').encode()
    files['WATER-RESIDUAL-LIGHT.txt']=(
        'TEST ONLY approved helper snapshot. Current light policy: WATER-RESIDUAL-LIGHT.json.\n'
        'All inherited declarations/legends are parent provenance; old atlas remains unchanged.\n'
        'WLS status requested/NEW-feature-applied/source-kind/rejection-count; applied0 STUB or rejected/unsupported.\n'
        'Integral snapshot supports kind1 only; native Sun kind0 remains explicitly unsupported/full legacy.\n'
        'WR status is legacy helper application, not new feature application.\n'
        'Inner light tag removal recovers guard-v2 FS; outer residual disable recovers resolved parent.\n'
        'Snapshot is not integral execution/reference match, neutrality, energy/reciprocity, visual or shipping acceptance.\n'
    ).encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.residual-light-',suffix='.zip',dir=destination.parent,delete=False) as output:
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
        parser.exit(1,'Rejected light pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__':
    main()
