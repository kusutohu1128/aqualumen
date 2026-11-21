"""Build a NEW guarded native Sun observation TEST pack from frozen CAP ZIP.

The shader requires an exact integer authorization uniform from a separate
fail-closed TEST Mod. Packaging is not actual world-guard or GL qualification.
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

CAP_RELATIVE=Path('reports/2026-10-03-water-residual-native-sun/cpu-pack-cap/Aqualumen-ShoreProbe-world-water-residual-native-sun-cap-v1.zip')
CAP_SHA256='7d08d62b960a28fa7e83ec8b5b3b9f856fbc32793d58392655e7345fcd9e4725'
SUN_SHA256='a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3'
OLD_CALL=('    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
          '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n')
UNIFORM=('// AQUALUMEN_SUN_IRIS_GUARD_UNIFORM_BEGIN\n'
         'uniform int aqualumenSunTestAuthorized;\n'
         '// AQUALUMEN_SUN_IRIS_GUARD_UNIFORM_END\n')
GUARDED_CALL=('// AQUALUMEN_SUN_IRIS_GUARD_CALL_BEGIN\n'
              '    if (aqualumenSunTestAuthorized==1) {\n'+OLD_CALL+
              '    }\n'
              '// AQUALUMEN_SUN_IRIS_GUARD_CALL_END\n')
FLAGS=('float(localColumnKnown)+2.0*float(upperSurface)'
       '+4.0*float(underwater)+8.0*float(residualEligible)')
STORE=('// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_BEGIN\n'
       '    gl_FragData[1]=WR_coefficients;\n'
       '    gl_FragData[2]=WNS_status;\n'
       '    gl_FragData[3]=vec4(WR_covariance,'+FLAGS+');\n'
       '// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_END\n')
PARENT_PANELS=('    vec3 panel;\n'
               '    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));\n'
               '    else if (probeState.z<0.5) panel=vec3(0.0);\n'
               '    else if (y==1) panel=probeStage.a>=0.5?(probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0)):vec3(1.0,1.0,0.0);\n'
               '    else if (x==0) panel=probeState.rgb;\n'
               '    else panel=vec3(probeReflection.z,probeReflection.y,probeReflection.z);\n')
PANELS=('// AQUALUMEN_SUN_IRIS_PANEL_BEGIN\n'
        '    // C9=legacy coefficients; C10=new Sun status; C11=covariance/original flags.\n'
        '    vec3 panel;\n'
        '    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));\n'
        '    else if (probeStage.a<0.5) panel=vec3(1.0,1.0,0.0);\n'
        '    else if (y==1) {\n'
        '        panel=probeNormal.yzw;\n'
        '        if (abs(probeNormal.x-1.0)>0.002) panel=vec3(1.0,0.0,1.0);\n'
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
        '// AQUALUMEN_SUN_IRIS_PANEL_END\n')


def build_pack(root,destination,enabled=1):
    """Publish observer ZIP, preserving exact guarded physical FS as a member."""
    if type(enabled) is not int or enabled not in (0,1):
        raise ValueError('enabled must be integer zero or one')
    root=Path(root).resolve()
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination exists')
    destination=destination.resolve()
    if any(destination.is_relative_to((root/folder).resolve()) for folder in ('shaders','dist')):
        raise ValueError('TEST packs must stay outside shipping trees')
    with (root/CAP_RELATIVE).open('rb') as stream:
        raw=stream.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=CAP_SHA256:
        raise ValueError('Frozen CAP ZIP differs')
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
                or sum(e.file_size for e in entries)>64*1024*1024
                or any(Path(e.filename).is_absolute() or '..' in Path(e.filename).parts
                       or stat.S_ISLNK(e.external_attr>>16) for e in entries)):
            raise ValueError('Unsafe or oversized CAP archive')
        files={e.filename:archive.read(e) for e in entries}
    parent_bytes=files['WATER-RESIDUAL-SUN-CAP.json']
    parent=json.loads(parent_bytes)
    if (parent.get('schema')!='aqualumen-water-residual-sun-cap-v1'
            or parent.get('mode')!='residual-native-sun-sharp-cap'
            or parent.get('sun_cap_helper_sha256')!=SUN_SHA256
            or parent.get('radial_order')!=4 or parent.get('azimuth_order')!=12
            or parent.get('geometry_factor')!=4 or parent.get('fixed_phase_seconds')!=120.0
            or parent.get('shipping_fix') is not False):
        raise ValueError('Unapproved frozen CAP policy')
    helper_member='shaders/lib/water_residual_sun.glsl'
    if hashlib.sha256(files[helper_member]).hexdigest()!=SUN_SHA256:
        raise ValueError('Frozen CAP helper differs')
    water=files['shaders/gbuffers_water.fsh'].decode()
    include='// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'
    if (water.count(include)!=1 or water.count(OLD_CALL)!=1 or not water.endswith('}\n')
            or water.count('/* RENDERTARGETS:0,9,10,11,12 */')!=1
            or water.count('    gl_FragData[4]=tessStageCoord;\n')!=1
            or 'AQUALUMEN_SUN_IRIS_' in water or 'aqualumenSunTestAuthorized' in water):
        raise ValueError('Frozen water guard/STORE seams differ')
    config=('// AQUALUMEN_SUN_IRIS_CONFIG_BEGIN\n#define NATIVE_SUN_ENABLED '+str(enabled)+
            '\n// AQUALUMEN_SUN_IRIS_CONFIG_END\n')
    physical=water.replace(include,include+UNIFORM+config).replace(OLD_CALL,GUARDED_CALL)
    recovered=physical.replace(UNIFORM,'').replace(config,'').replace(GUARDED_CALL,OLD_CALL)
    if recovered!=water:
        raise ValueError('Guard/config recovery differs from CAP FS')
    observed=physical[:-2]+STORE+physical[-2:]
    if observed.replace(STORE,'')!=physical:
        raise ValueError('Observer removal differs from guarded physical FS')
    physical_member='PARENT-SUN-IRIS-physical.fsh'
    final_member='PARENT-SUN-IRIS-final.fsh'
    if any(name in files for name in (physical_member,final_member,'WATER-RESIDUAL-SUN-IRIS.json')):
        raise ValueError('Parent already contains Iris wrapper provenance')
    files[physical_member]=physical.encode()
    files['shaders/gbuffers_water.fsh']=observed.encode()
    parent_final=files['shaders/final.fsh']
    final=parent_final.decode()
    if final.count(PARENT_PANELS)!=1 or 'AQUALUMEN_SUN_IRIS_' in final:
        raise ValueError('Frozen FINAL panel seam differs')
    files[final_member]=parent_final
    files['shaders/final.fsh']=final.replace(PARENT_PANELS,PANELS).encode()
    current={
        'schema':'aqualumen-water-residual-sun-iris-v1','mode':'guarded-native-sun-observe',
        'test_only':True,'not_shipping':True,'shipping_fix':False,'enabled':enabled,
        'parent_cap_pack_sha256':CAP_SHA256,'parent_cap_metadata_member':'WATER-RESIDUAL-SUN-CAP.json',
        'parent_cap_metadata_sha256':hashlib.sha256(parent_bytes).hexdigest(),
        'inherited_metadata_is_current_optical_policy':False,'inherited_metadata_is_current_atlas_policy':False,
        'helper_sha256':{helper_member:SUN_SHA256,**parent['old_helper_sha256']},
        'original_sha256':parent['original_sha256'],'geometry_factor':4,'fixed_phase_seconds':120.0,
        'geometry_source_changed':False,'cap_helper_source_changed':False,'atmosphere_source_changed':False,
        'scalar_units_changed':False,'scatter_policy_changed':False,'FS_C0_source_observation_changed':False,
        'guard_uniform':{'name':'aqualumenSunTestAuthorized','glsl_type':'int','required_value':1,'default_if_mod_absent':0},
        'guard_call_expression':'if (aqualumenSunTestAuthorized==1)',
        'world_guard_requires_mod':True,'shader_authorization_gate_present':True,'pack_enforces_world_guard':False,
        'guard_0_policy':'Skip actual Sun call and both old residual calls; per-invocation WR/WNS defaults stay zero; prior resolved-parent optical color retained',
        'enabled_0_policy':'Authorized call still runs old full-source residual helper; new Sun requested/applied0. Not equivalent to guard0',
        'ordinary_world_scope':'Production pack/files untouched; this TEST still retains phase120/tess4/resolved-normal/atlas, not shipping geometry/display equivalence',
        'physical_water_fs_member':physical_member,'physical_water_fs_sha256':hashlib.sha256(physical.encode()).hexdigest(),
        'observer_water_fs_sha256':hashlib.sha256(observed.encode()).hexdigest(),
        'parent_water_fs_sha256':hashlib.sha256(water.encode()).hexdigest(),
        'parent_final_member':final_member,'parent_final_sha256':hashlib.sha256(parent_final).hexdigest(),
        'FINAL_atlas_policy_changed':True,'MRT_semantics_changed':True,
        'target_channels':{'9':['mass','R','T','TIR'],'10':['requested','featureApplied','sourceKind','rejectionCount'],
                           '11':['Cxx','Cxz','Czz','productionFlags'],
                           '12':['barycentricX','barycentricY','barycentricZ','stagePresent']},
        'production_flags':{'known':1,'upper':2,'underwater':4,'residualEligible':8},
        'production_flags_range':[0,15],'production_flags_expression':FLAGS,
        'flags_scope':'Original eligibility only; flags15 does not prove authorization, legacy application or new Sun application',
        'legacy_status_scope':'WR valid/applied not directly exported; C9 coefficient mass alone is not legacy application proof',
        'final_panels':{'top_left':'Physical C0 with unchanged parent tone/display',
                        'top_right':'R,T,TIR; magenta when abs(mass-1)>.002 (display only, including skipped/unavailable mass)',
                        'bottom_left':'requested,featureApplied,rejections/(1+rejections); top tenth sourceKind clipped0..1',
                        'bottom_right':'Covariance display; top tenth original flags/15',
                        'yellow':'No water/TES marker at texel, not proof of missing GL stages'},
        'recovery':'Remove observer STORE for exact physical FS; remove uniform/config and replace guarded CALL block with unchanged literal parent CALL for exact CAP FS',
        'passivity_scope':'Compare observer with archived guarded physical FS at SAME guard and enabled values; intentional guard/control optics changes are not observer deltas',
        'declared_cap_rule':[4,12],'actual_shader_node_count_qualified':False,
        'runtime_accepted':False,'actual_guard_runtime_verified':False,'GL_neutrality_verified':False,
        'pixel_AA_equivalence_accepted':False,'energy_accepted':False,'reciprocity_accepted':False,
        'visual_accepted':False,'performance_accepted':False,'generated_geometry_accepted':False,'motion_accepted':False,
    }
    files['WATER-RESIDUAL-SUN-IRIS.json']=(json.dumps(current,indent=2,sort_keys=True)+'\n').encode()
    files['WATER-RESIDUAL-SUN-IRIS.txt']=(
        'TEST ONLY guarded observation pack. Authoritative policy: WATER-RESIDUAL-SUN-IRIS.json.\n'
        'All inherited declarations/legends are provenance, not current atlas/guard policy.\n'
        'Separate fail-closed TEST Mod supplies scalar int aqualumenSunTestAuthorized; only value1 calls operators.\n'
        'Guard0 skips old residual and new Sun calls; WR/WNS defaults0, original flags remain honest.\n'
        'Enabled0 is authorized legacy control, not guard0. C9 coefficients do not prove legacy application.\n'
        'C9 mass,R,T,TIR; C10 requested,NEW-applied,native-kind0,rejections; C11 covariance/original flags; C12 TES.\n'
        'Flags15 is NOT authorization/application. Top-left parent C0; diagnostic panels are not acceptance tests.\n'
        'Declared cap4x12 is provenance, not actual invocation-count proof.\n'
        'Archived guarded physical FS must be used at SAME uniform/config for observer passivity.\n'
        'No actual guard/GL, pixel-AA/narrow-SPD/rim/critical/visibility, energy/reciprocity, visual or shipping acceptance.\n'
        'Production files untouched; TEST phase/geometry/resolved optics/atlas do not become production outside guard.\n'
    ).encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.sun-iris-',suffix='.zip',dir=destination.parent,delete=False) as output:
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
    parser.add_argument('--enabled',type=int,choices=(0,1),default=1)
    args=parser.parse_args()
    try:
        path=build_pack(Path(__file__).resolve().parents[1],args.destination,args.enabled)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected Sun Iris pack: '+type(failure).__name__+'\n')
    print(path)


if __name__=='__main__':
    main()
