"""Build a NEW TEST-only actual-main residual observation ZIP.

Only final diagnostic STOREs and the diagnostic display/legends may differ from
the freshly built physical parent. Packaging is not GL neutrality, operator
execution, physical energy/reciprocity, visual adoption or performance proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from water_residual_pack import build_pack as build_parent


FLAGS_EXPRESSION = ('float(localColumnKnown)+2.0*float(upperSurface)'
                    '+4.0*float(underwater)+8.0*float(residualEligible)')
STORE = (
    '// AQUALUMEN_RESIDUAL_OBSERVE_STORE_BEGIN\n'
    '    gl_FragData[1]=WR_coefficients;\n'
    '    gl_FragData[2]=WR_status;\n'
    '    gl_FragData[3]=vec4(WR_covariance,' + FLAGS_EXPRESSION + ');\n'
    '// AQUALUMEN_RESIDUAL_OBSERVE_STORE_END\n'
)
PARENT_PANELS = (
    '    vec3 panel;\n'
    '    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));\n'
    '    else if (probeState.z<0.5) panel=vec3(0.0);\n'
    '    else if (y==1) panel=probeStage.a>=0.5?(probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0)):vec3(1.0,1.0,0.0);\n'
    '    else if (x==0) panel=probeState.rgb;\n'
    '    else panel=vec3(probeReflection.z,probeReflection.y,probeReflection.z);\n'
)
OBSERVE_PANELS = (
    '// AQUALUMEN_RESIDUAL_OBSERVE_PANEL_BEGIN\n'
    '    // C9=mass,R,T,TIR; C10=valid,applied,facing,opaque; C11=covariance,flags.\n'
    '    vec3 panel;\n'
    '    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));\n'
    '    else if (probeStage.a<0.5) panel=vec3(1.0,1.0,0.0);\n'
    '    else if (y==1) {\n'
    '        panel=probeNormal.yzw;\n'
    '        if (abs(probeNormal.x-1.0)>0.002) panel=vec3(1.0,0.0,1.0);\n'
    '    } else if (x==0) {\n'
    '        panel=probeState.rgb;\n'
    '        if (q.y>0.9) panel=vec3(clamp(probeState.w,0.0,1.0),0.0,0.0);\n'
    '    } else {\n'
    '        float covX=max(probeReflection.x,0.0),covZ=max(probeReflection.z,0.0);\n'
    '        float correlation=probeReflection.y/sqrt(max(covX*covZ,1e-20));\n'
    '        panel=vec3(covX/(covX+0.01),0.5+0.5*correlation,covZ/(covZ+0.01));\n'
    '        if (q.y>0.9) panel=vec3(probeReflection.w/15.0);\n'
    '    }\n'
    '// AQUALUMEN_RESIDUAL_OBSERVE_PANEL_END\n'
)
LEGENDS = ('UNDERWATER-PROBE.txt','WATER-TESSELLATION-PROBE.txt',
           'UNDERWATER-RESOLVED-PROBE.txt','WATER-RESIDUAL-PROBE.txt')


def _destination(root, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination = destination.resolve()
    if any(destination.is_relative_to((root/folder).resolve()) for folder in ('shaders', 'dist')):
        raise ValueError('Observation packs must stay outside shipping trees')
    return destination


def _publish(files, destination):
    """Same-filesystem atomic publication without replacing an existing name."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.residual-observe-', suffix='.zip',
                                         dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
                for name, content in sorted(files.items()):
                    entry = ZipInfo(name, (2026,10,3,0,0,0))
                    entry.compress_type = ZIP_DEFLATED
                    entry.external_attr = 0o100644 << 16
                    archive.writestr(entry, content)
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink()


def build_pack(root, destination):
    """Snapshot current default-three physical parent and expose its fields."""
    root = Path(root).resolve()
    destination = _destination(root, destination)
    with tempfile.TemporaryDirectory(prefix='aqualumen-residual-observe-parent-') as folder:
        parent = build_parent(root, Path(folder)/'physical-parent.zip')
        parent_bytes = parent.read_bytes()
        parent_digest = hashlib.sha256(parent_bytes).hexdigest()
        with ZipFile(parent) as archive:
            entries = archive.infolist()
            if (len(entries)>1024 or len({e.filename for e in entries})!=len(entries)
                    or sum(e.file_size for e in entries)>64*1024*1024):
                raise ValueError('Duplicate or oversized physical parent')
            files = {entry.filename:archive.read(entry) for entry in entries}
    if 'WATER-RESIDUAL-OBSERVE.json' in files:
        raise ValueError('Physical parent already contains observation policy')
    parent_metadata_bytes = files['WATER-RESIDUAL-PROBE.json']
    parent_metadata = json.loads(parent_metadata_bytes)
    if (parent_metadata.get('schema')!='aqualumen-water-residual-probe-v1'
            or parent_metadata.get('mode')!='residual-interface-atlas'
            or type(parent_metadata.get('quadrature_order')) is not int
            or parent_metadata['quadrature_order']!=3
            or parent_metadata.get('geometry_factor')!=4
            or parent_metadata.get('fixed_phase_seconds')!=120.0
            or parent_metadata.get('shipping_fix') is not False):
        raise ValueError('Unapproved physical parent declarations')
    helpers = parent_metadata['helper_sha256']
    if set(helpers)!= {'shaders/lib/wave_residual.glsl','shaders/lib/water_residual.glsl'}:
        raise ValueError('Unexpected physical helper manifest')
    if any(hashlib.sha256(files[name]).hexdigest()!=digest for name,digest in helpers.items()):
        raise ValueError('Physical helper bytes differ from parent metadata')
    water = files['shaders/gbuffers_water.fsh'].decode()
    tail = '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
    if (water.count(tail)!=1 or not water.endswith('}\n')
            or water.count('/* RENDERTARGETS:0,9,10,11,12 */')!=1
            or water.count('    gl_FragData[4]=tessStageCoord;\n')!=1
            or water.count('    bool residualEligible=')!=1
            or 'AQUALUMEN_RESIDUAL_OBSERVE_STORE_' in water):
        raise ValueError('Physical final STORE/eligibility seams differ')
    observed = water[:-2]+STORE+water[-2:]
    if observed.replace(STORE,'')!=water:
        raise ValueError('Removable observation does not recover physical FS')
    files['shaders/gbuffers_water.fsh'] = observed.encode()
    parent_final_bytes = files['shaders/final.fsh']
    final = parent_final_bytes.decode()
    if final.count(PARENT_PANELS)!=1 or 'AQUALUMEN_RESIDUAL_OBSERVE_PANEL_' in final:
        raise ValueError('Physical parent atlas panel seam differs')
    final = final.replace(PARENT_PANELS,OBSERVE_PANELS)
    parent_final_member = 'PARENT-RESIDUAL-OBSERVE-final.fsh'
    if parent_final_member in files:
        raise ValueError('Parent final provenance name already exists')
    files[parent_final_member] = parent_final_bytes
    files['shaders/final.fsh'] = final.encode()
    targets = {
        '9':'quadrature mass / reflected coefficient / transmitted coefficient / TIR mass',
        '10':'valid / applied / minimum facing / opaque receiver count',
        '11':'Cxx / Cxz / Czz / production eligibility bitword',
        '12':parent_metadata['targets']['12'],
    }
    metadata = {
        'schema':'aqualumen-water-residual-observe-v1', 'mode':'residual-interface-observe',
        'test_only':True, 'not_shipping':True, 'shipping_fix':False,
        'parent_pack_sha256':parent_digest, 'parent_metadata_member':'WATER-RESIDUAL-PROBE.json',
        'parent_metadata_sha256':hashlib.sha256(parent_metadata_bytes).hexdigest(),
        'helper_sha256':helpers, 'original_sha256':parent_metadata['original_sha256'],
        'geometry_factor':4, 'fixed_phase_seconds':120.0,
        'fixed_phase_scope':parent_metadata['fixed_phase_scope'], 'quadrature_order':3,
        'quadrature_order_scope':'Parent declaration only; no actual shader node-count proof',
        'actual_shader_node_count_qualified':False,
        'parent_metadata_is_current_atlas_policy':False,
        'inherited_metadata_is_current_atlas_policy':False,
        'parent_metadata_is_current_optical_policy':False,
        'geometry_source_changed':False, 'operator_source_changed':False,
        'FS_transport_changed':False, 'FS_C0_source_changed':False, 'MRT_semantics_changed':True,
        'parent_water_fs_sha256':hashlib.sha256(water.encode()).hexdigest(),
        'parent_final_member':parent_final_member,
        'parent_final_sha256':hashlib.sha256(parent_final_bytes).hexdigest(),
        'FINAL_atlas_policy_changed':True,
        'final_panels':{'top_left':'Physical C0; parent tone/display unchanged',
                        'top_right':'RGB=R,T,TIR; magenta when abs(mass-1)>.002 (display-only warning)',
                        'bottom_left':'RGB=valid,applied,minFacing; top tenth red=opaqueCount clipped0..1',
                        'bottom_right':'RGB=Cxx/(Cxx+.01), .5+.5*correlation, Czz/(Czz+.01); top tenth gray=flags/15',
                        'yellow':'No water/TES marker at this texel; not proof of missing GL stages'},
        'targets':targets,
        'target_channels':{'9':['mass','R','T','TIR'], '10':['valid','applied','minFacing','opaqueCount'],
                           '11':['Cxx','Cxz','Czz','productionFlags'],
                           '12':['barycentricX','barycentricY','barycentricZ','stagePresent']},
        'production_flags':{'known':1,'upper':2,'underwater':4,'residualEligible':8},
        'production_flags_range':[0,15], 'production_flags_expression':FLAGS_EXPRESSION,
        'observation_scope':'Actual original-main final STORE fields; inactive/rejected points do not establish operator acceptance',
        'GL_neutrality_verified':False, 'runtime_accepted':False,
        'energy_accepted':False, 'reciprocity_accepted':False, 'visual_accepted':False,
        'performance_accepted':False, 'generated_geometry_accepted':False,
        'motion_accepted':False, 'pack_enforces_world_guard':False,
    }
    files['WATER-RESIDUAL-OBSERVE.json'] = (json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode()
    files['WATER-RESIDUAL-OBSERVE.txt'] = (
        'TEST ONLY: authoritative observation policy is WATER-RESIDUAL-OBSERVE.json.\n'
        'C9=mass,R,T,TIR; C10=valid,applied,minFacing,opaqueCount.\n'
        'C11=Cxx,Cxz,Czz,productionFlags; C12 retains parent TES barycentrics/present.\n'
        'Flag bits known=1,upper=2,underwater=4,residualEligible=8; flags15 alone is not applied/valid.\n'
        'Top-left is parent C0 display. Top-right RGB=R,T,TIR; magenta warns abs(mass-1)>.002.\n'
        'Bottom-left RGB=valid,applied,minFacing; top tenth red=opaqueCount clipped0..1.\n'
        'Bottom-right RGB=xx/(xx+.01),.5+.5*xz/sqrt(xx*zz),zz/(zz+.01); top tenth gray=flags/15.\n'
        'Yellow means no water/TES marker at that texel, not proof of missing GL stages.\n'
        'Panel scales/warnings are diagnostic display choices, not acceptance tolerances or energy tests.\n'
        'Parent declares order3; actual shader node count is not observed by this pack.\n'
        'Inactive/rejected points and coefficient sums do not establish operator physics.\n'
        'All inherited metadata/legends are parent provenance, not current atlas semantics.\n'
        'Exact physical parent FINAL and replaced legends are preserved as PARENT-RESIDUAL-OBSERVE-*.\n'
        'Additional final STORE removal recovers exact parent water FS; C0/geometry/helpers/originals unchanged.\n'
        'Pure C0 neutrality still requires actual native/Iris qualification; no runtime or shipping acceptance.\n'
        'No visual, generated-geometry, motion, FPS, energy/reciprocity or physical-fluid acceptance.\n'
    ).encode()
    for name in LEGENDS:
        provenance = 'PARENT-RESIDUAL-OBSERVE-'+name
        if provenance in files:
            raise ValueError('Parent legend provenance name already exists')
        files[provenance] = files[name]
        files[name] = ('TEST ONLY: current diagnostic atlas policy is WATER-RESIDUAL-OBSERVE.json/.txt.\n'
                       'This inherited policy is parent provenance only. Original legend: '+provenance+'\n').encode()
    _publish(files,destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args = parser.parse_args()
    try:
        result = build_pack(Path(__file__).resolve().parents[1],args.destination)
    except (OSError,ValueError,KeyError,TypeError,BadZipFile,UnicodeError) as failure:
        parser.exit(1,'Rejected residual observation: '+type(failure).__name__+'\n')
    print(result)


if __name__=='__main__':
    main()
