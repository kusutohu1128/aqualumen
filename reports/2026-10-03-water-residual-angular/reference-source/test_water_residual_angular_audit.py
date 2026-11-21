"""Public CPU saved-artifact contracts; no GL or renderer qualification."""
import json
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('water_residual_angular_audit.py')

# Serialized CPU fixture, deliberately not a GL compilation or GPU run. Array
# values come from the independent public quadrature generator, not this auditor.
def fixture(packet):
    from water_residual_angular_reference import standard_normal_rule
    cache={}
    def put(path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        key=hashlib.sha256(data).digest()
        if key in cache:
            os.link(cache[key],path)
        else:
            path.write_bytes(data)
            cache[key]=path
    def text(path,value):
        put(path,value.encode())
    def raw(path,values):
        put(path,struct.pack('<'+'f'*len(values),*values))
    guard='#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER 3\n#endif\n#if WATER_RESIDUAL_ORDER != 3\n#error This TEST slice implements only the declared order-three rule\n#endif\n'
    body='    const float nodes[3]=float[3](-1.7320508075688772,0.0,1.7320508075688772);\n    const float weights[3]=float[3](1.0/6.0,2.0/3.0,1.0/6.0);\n    for (int x=0;x<3;++x) for (int z=0;z<3;++z) {\n'
    env='    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());\n'
    begin='\n// RESIDUAL_NATIVE_STORE_BEGIN\n'
    end='// RESIDUAL_NATIVE_STORE_END\n'
    original=('#define frameTimeCounter 120.0\n'+env+
              '// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'+guard+body+
              '// AQUALUMEN_RESIDUAL_INCLUDE_END\nvoid main() {\n'+
              '        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n'+
              '        gl_FragData[0]=vec4(lit,tex.a);\n        return;\n'+
              '// AQUALUMEN_RESIDUAL_HOOK_BEGIN\ncolor=waterResidualInterface(waveResidualCovariance());\n'+
              '// AQUALUMEN_RESIDUAL_HOOK_END\n'+
              '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n\n}\n')
    text(packet/'source-original-expanded.fsh',original)
    parent=original[:original.index('// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n')]+original[original.index('// AQUALUMEN_RESIDUAL_INCLUDE_END\n')+len('// AQUALUMEN_RESIDUAL_INCLUDE_END\n'):]
    parent=parent[:parent.index('// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n')]+parent[parent.index('// AQUALUMEN_RESIDUAL_HOOK_END\n')+len('// AQUALUMEN_RESIDUAL_HOOK_END\n'):]
    text(packet/'parent-expanded.fsh',parent)
    for stage in range(3):
        text(packet/f'geometry-stage{stage}.glsl',f'#define frameTimeCounter 120.0\n// CPU synthetic geometry {stage}\n')
    specs=[('gtexture',1,1,34836,4),('colortex4',257,257,34836,4),
           ('colortex6',64,32,34836,4),('depthtex1',257,257,36012,1),
           ('shadowtex0',1,1,36012,1),('colortex8',1,1,34842,4),
           ('aqualumenBathymetry',64,64,34836,4),('colortex7',64,32,34836,4)]
    eye=(0.,-1.,0.,1.)
    fields=[None,eye,(.001,0.,.001,.035),(1.,.02,.98,0.),(1.,1.,.9,0.),
            eye,(1.,1.,1.,1.),(0.,0.,0.,1.)]
    zero=[0.]* (257*257*4)
    depth=[.5]*(257*257)
    identity=[1. if i%5==0 else 0. for i in range(16)]
    cases=[]
    for source in ('narrow','broad','constant','dark'):
        sigma={'narrow':.00465,'broad':.08}.get(source)
        for rule in (3,9,17):
            name=f'{source}-gh{rule}'
            directory=packet/name
            expression={'constant':'vec3(0.25,0.125,0.0625)','dark':'vec3(0.0)'}.get(source)
            if expression is None:
                s=format(sigma,'.17g')
                expression=f'vec3(0.25,0.125,0.0625)*exp(-dot(normalize(ray)-vec3(0.0,1.0,0.0),normalize(ray)-vec3(0.0,1.0,0.0))/(2.0*{s}*{s}))'
            pure=original.replace(env,'// ANGULAR_SOURCE_BEGIN\n    return sampleSky(lut,ray)+'+expression+';\n// ANGULAR_SOURCE_END\n')
            if rule!=3:
                nodes,weights=zip(*standard_normal_rule(rule))
                replacement=f'// ANGULAR_RULE_GUARD_BEGIN\n#ifndef WATER_RESIDUAL_ORDER\n#define WATER_RESIDUAL_ORDER {rule}\n#endif\n#if WATER_RESIDUAL_ORDER != {rule}\n#error Angular TEST rule must match declared order\n#endif\n// ANGULAR_RULE_GUARD_END\n'
                pure=pure.replace(guard,replacement)
                array=lambda a: ','.join(format(v,'.17e') for v in a)
                replacement=(f'// ANGULAR_RULE_BODY_BEGIN\n    const float nodes[{rule}]=float[{rule}]('+array(nodes)+');\n'+
                             f'    const float weights[{rule}]=float[{rule}]('+array(weights)+');\n'+
                             f'    for (int x=0;x<{rule};++x) for (int z=0;z<{rule};++z) {{\n// ANGULAR_RULE_BODY_END\n')
                pure=pure.replace(body,replacement)
            observer=pure.replace('void main() {\n','void main() {\n'+begin+'    float OBS_residualGrazing=-1.0;\n'+end)
            anchor='        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n'
            observer=observer.replace(anchor,anchor+begin+'        OBS_residualGrazing=resolved;\n'+end)
            observer=observer.replace('        return;',begin+''.join(f'    gl_FragData[{s}]=vec4(0.0);\n' for s in range(1,8))+end+'        return;')
            store=('    gl_FragData[1]=vec4(n,OBS_residualGrazing);\n'+
                   '    gl_FragData[2]=vec4(WR_covariance,max(footprint*1.25,0.035));\n'+
                   '    gl_FragData[3]=WR_coefficients;\n    gl_FragData[4]=WR_status;\n'+
                   '    gl_FragData[5]=vec4(v,float(residualEligible));\n'+
                   '    gl_FragData[6]=vec4(float(localColumnKnown),float(upperSurface),float(underwater),1.0);\n'+
                   '    gl_FragData[7]=vec4(scatter,float(residualEligible));\n')
            observer=observer.replace('\n}\n',begin+store+end+'\n}\n')
            text(directory/'pure-expanded.fsh',pure)
            text(directory/'observer-expanded.fsh',observer)
            C0=zero.copy()
            for p in range(257*257):
                C0[p*4+3]=1.
                if source=='constant' or (source!='dark' and p==128*257+128):
                    C0[p*4:p*4+3]=[.25*.98,.125*.98,.0625*.98]
            for slot in range(8):
                value=C0 if slot==0 else list(fields[slot])*(257*257)
                for label in ('observer','observer-repeat'):
                    raw(directory/f'{label}-slot{slot}.rgba32f',value)
                for label in ('pure','pure-repeat'):
                    raw(directory/f'{label}-slot{slot}.rgba32f',value if slot<5 else zero)
            for label in ('pure','pure-repeat','observer','observer-repeat'):
                raw(directory/f'{label}-depth.f32',depth)
            raw(directory/'uploaded-water-vertices.f32',[0.]*90)
            raw(directory/'uploaded-open-water-vertices.f32',[0.]*90)
            samplers=[]
            for unit,(uniform,w,h,internal,components) in enumerate(specs):
                suffix='.f32' if components==1 else '.rgba32f'
                filename=f'input-sampler{unit}'+suffix
                values=([1.]*(w*h) if components==1 else
                        list((4.,3.25,1.,0.) if unit==6 else (0.,0.,0.,1.))*(w*h))
                raw(directory/filename,values)
                if unit==6:
                    raw(directory/'actual-bathymetry.rgba32f',values)
                samplers.append(dict(unit=unit,name=uniform,texture=unit+100,internalFormat=internal,
                                     width=w,height=h,components=components,minFilter=9728,magFilter=9728,
                                     compareMode=34894 if unit==4 else 0,wrapS=33071,wrapT=33071,file=filename))
            index=len(cases)
            ids=[1000+index*2,1001+index*2]
            inputs=dict(schema='aqualumen-native-residual-angular-inputs-v1',program=ids[1],
                        currentProgramBefore=ids[1],currentProgramAfter=ids[1],activeTextureBefore=33991,
                        activeTextureAfter=33991,textureBindingBefore=107,textureBindingAfter=107,
                        bindingRestored=True,matrices={s:identity for s in
                        ('gbufferProjection','gbufferProjectionInverse','gbufferModelView','gbufferModelViewInverse')},
                        fixedFunctionProjection=identity,fixedFunctionModelView=identity,samplers=samplers,
                        targets=[dict(slot=s,texture=200+s,internalFormat=34836,width=257,height=257) for s in range(8)],
                        depth=dict(slot=8,texture=208,internalFormat=36012,width=257,height=257))
            text(directory/'actual-inputs.json',json.dumps(inputs))
            cases.append(dict(source=source,sigma=sigma,rule=rule,path=name,program_ids=ids,
                              programs=[dict(name=name+suffix,linked=True,stage_types=[35632,35633,36487,36488],
                                             tess_layout=[3,4,514,2305,0]) for suffix in ('-pure','-observer')],
                              comparisons=[],samples=[],domainQualified=True,qualified=True))
    manifest=dict(schema='aqualumen-native-residual-angular-v1',renderer='CPU synthetic fixture; not GPU evidence',
                  GL='CPU synthetic',size=257,phase_seconds=120,
                  sourceUnits='fixed-peak directional radiance; CHORD Gaussian, not calibrated solar beam',
                  geometry_sources_identical=True,disabled_source_recovers_parent_exact=True,
                  observer_recovers_original_exact=True,source_transform_recovers_original_exact=True,
                  rule_transform_recovers_original_exact=True,culling_enabled=False,
                  pure_draw_buffer_slots=[0,1,2,3,4],pure_cleared_inactive_slots=[5,6,7],
                  observer_slot5='actual viewToEye xyz / residualEligible',
                  rawFormat='little-endian binary32 bottom-left origin',
                  policy=dict(C0_absolute=5e-4,C0_relative=2e-4,depth_absolute=2e-6,
                              coefficient_absolute=2e-5,double_moment_scaled=2e-11,
                              binary32_moment_absolute=2e-6,ROI_center=[128,128],ROI_integer_radius=40,
                              peak_fraction=.2,component_neighbors=8,luminance=[.2126,.7152,.0722]),
                  cases=cases,accepted=True)
    text(packet/'result.json',json.dumps(manifest))
    return manifest


class AngularSavedAuditTests(unittest.TestCase):
    def test_public_cli_keeps_common_roi_hole_inconclusive_not_a_surviving_subset(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-domain-') as temporary:
            packet=Path(temporary)
            fixture(packet)
            for label in ('observer','observer-repeat'):
                path=packet/'broad-gh17'/f'{label}-slot4.rgba32f'
                data=bytearray(path.read_bytes())
                struct.pack_into('<ff',data,(128*257+128)*16,0.,0.)
                path.unlink()
                path.write_bytes(data)
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(data['descriptorOutcome'],'INCONCLUSIVE')
            self.assertEqual(data['commonROI']['excludedPoints'],1)
            self.assertEqual(data['commonROI']['excludedPixels'],[[128,128]])
            self.assertEqual(data['commonROI']['domainReasons'],{'appliedFalse':1,'validFalse':1})
            self.assertEqual(data['peaks'],[])
            self.assertTrue(data['selectedPointQualification']['qualified'])
            self.assertFalse(data['physicalAccepted'])

    def test_public_cli_rejects_saved_data_or_source_corruption_without_trusting_pass(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-corrupt-') as temporary:
            packet=Path(temporary)
            fixture(packet)
            source=packet/'narrow-gh3'/'observer-expanded.fsh'
            normal=packet/'narrow-gh3'/'observer-slot1.rgba32f'
            repeated=packet/'narrow-gh3'/'observer-repeat-slot1.rgba32f'
            inputs=packet/'narrow-gh3'/'actual-inputs.json'
            source_bytes=source.read_bytes()
            normal_bytes=normal.read_bytes()
            input_bytes=inputs.read_bytes()
            bad_input=json.loads(input_bytes)
            bad_input['samplers'][0]['width']=True
            mutations=[(source,source_bytes.replace(b'gl_FragData[5]=vec4(v,float(residualEligible));',b'gl_FragData[5]=WR_sources;')),
                       (normal,struct.pack('<f',float('nan'))+normal_bytes[4:]),
                       (repeated,normal_bytes[:-4]),
                       (repeated,struct.pack('<f',.001)+normal_bytes[4:]),
                       (inputs,json.dumps(bad_input).encode())]
            for path,payload in mutations:
                with self.subTest(path=path.name,sha=hashlib.sha256(payload).hexdigest()):
                    before=path.read_bytes()
                    path.unlink()
                    path.write_bytes(payload)
                    result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],capture_output=True,text=True)
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(result.stdout,'')
                    self.assertEqual(result.stderr,'Rejected angular saved-output: ValueError\n')
                    self.assertEqual(path.read_bytes(),payload)
                    path.unlink()
                    path.write_bytes(before)

    def test_public_cli_rejects_float_reflected_integer_layout(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-types-') as temporary:
            packet=Path(temporary)
            manifest=fixture(packet)
            manifest['cases'][0]['programs'][0]['tess_layout'][0]=3.0
            (packet/'result.json').unlink()
            (packet/'result.json').write_text(json.dumps(manifest))
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stdout,'')
            self.assertEqual(result.stderr,'Rejected angular saved-output: ValueError\n')

    def test_public_cli_rejects_changed_predeclared_policy_before_arrays(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-policy-') as temporary:
            packet=Path(temporary)
            manifest=fixture(packet)
            manifest['policy']['peak_fraction']=.1
            (packet/'result.json').unlink()
            (packet/'result.json').write_text(json.dumps(manifest))
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stdout,'')
            self.assertEqual(result.stderr,'Rejected angular saved-output: ValueError\n')

    def test_public_cli_describes_valid_saved_synthetic_peaks_without_adoption(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-valid-') as temporary:
            packet=Path(temporary)
            fixture(packet)
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(data['descriptorOutcome'],'QUALIFIED')
            self.assertEqual(data['commonROI']['points'],5025)
            self.assertEqual(data['commonROI']['excludedPoints'],0)
            self.assertEqual([p['components'] for p in data['peaks']],[1]*6)
            self.assertTrue(data['selectedPointQualification']['qualified'])
            self.assertFalse(data['physicalAccepted'])
            self.assertFalse(data['naturalAccepted'])
            self.assertFalse(data['shippingAccepted'])

    def test_public_cli_rejects_missing_native_manifest_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-angular-audit-missing-') as temporary:
            packet=Path(temporary)
            marker=packet/'cpu-only-fixture.txt'
            marker.write_text('Synthetic CPU evidence; not a GPU run.\n')
            before={p.name:p.read_bytes() for p in packet.iterdir()}
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(packet)],
                                  capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stdout,'')
            self.assertEqual(result.stderr,'Rejected angular saved-output: FileNotFoundError\n')
            self.assertEqual(before,{p.name:p.read_bytes() for p in packet.iterdir()})


if __name__=='__main__':
    unittest.main(verbosity=2)
