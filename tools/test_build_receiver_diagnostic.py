from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from build_receiver_diagnostic import build, diagnostic_shader, interface_shader, rejection_shader, run_rejection_shader, unknown_rejection_shader


class ReceiverDiagnosticTests(unittest.TestCase):
    def test_raw_receiver_readout_preserves_outcome_palette(self):
        shader=(Path(__file__).resolve().parents[1]/'shaders/gbuffers_water.fsh').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.zip';target=Path(directory)/'raw.zip'
            with ZipFile(source,'w') as archive:
                archive.writestr('shaders/gbuffers_water.fsh',shader)
                archive.writestr('shaders/final.fsh',b'original final')
            build(source,target,raw_receiver=True)
            with ZipFile(target) as archive:
                water=archive.read('shaders/gbuffers_water.fsh')
                self.assertIn(b'fresnel>=0.9999?receiverDiagnostic',water)
                self.assertIn(b'gl_FragData[1]=underwater?vec4(color,1.0)',water)
                self.assertIn(b'texelFetch(colortex12',archive.read('shaders/final.fsh'))
            with self.assertRaisesRegex(ValueError,'receiver-only'):
                build(source,Path(directory)/'invalid.zip',raw_receiver=True,exit_rays=True)

    def test_coupled_normal_is_explicit_diagnostic_only(self):
        shader=(Path(__file__).resolve().parents[1]/'shaders/gbuffers_water.fsh').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.zip'
            with ZipFile(source,'w') as archive:
                archive.writestr('shaders/gbuffers_water.fsh',shader)
                archive.writestr('shaders/lib/water.glsl',b'unchanged helper')
            target=Path(directory)/'candidate.zip'
            build(source,target,exit_rays=True,interface_normal=True)
            with ZipFile(target) as archive:
                self.assertIn(b'#define AQUALUMEN_INTERFACE_NORMAL_COMPARISON',archive.read('shaders/gbuffers_water.fsh'))
                self.assertEqual(archive.read('shaders/lib/water.glsl'),b'unchanged helper')
            with self.assertRaisesRegex(ValueError,'requires an interface diagnostic'):
                build(source,Path(directory)/'invalid.zip',interface_normal=True)

    def test_raw_readout_owns_unused_target_and_preserves_other_stages(self):
        shader=(Path(__file__).resolve().parents[1]/'shaders/gbuffers_water.fsh').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.zip';target=Path(directory)/'raw.zip'
            with ZipFile(source,'w') as archive:
                archive.writestr('shaders/gbuffers_water.fsh',shader)
                archive.writestr('shaders/final.fsh',b'original final')
                archive.writestr('shaders/composite.fsh',b'unchanged composite')
            build(source,target,exit_rays=True,raw_interface=True)
            with ZipFile(target) as archive:
                water=archive.read('shaders/gbuffers_water.fsh').decode()
                final=archive.read('shaders/final.fsh').decode()
                self.assertIn('/* RENDERTARGETS:0,12 */',water)
                self.assertIn('colortex12ClearColor = vec4(0.0,0.0,0.0,0.0)',water)
                self.assertNotIn('colortex12ClearColor = vec4(0.0);',water)
                self.assertIn('gl_FragData[1]=underwater?vec4(color,1.0):vec4(0.0)',water)
                self.assertIn('texelFetch(colortex12,ivec2(gl_FragCoord.xy),0)',final)
                self.assertNotIn('tone(',final)
                self.assertEqual(archive.read('shaders/composite.fsh'),b'unchanged composite')
            with self.assertRaises(ValueError):
                build(source,Path(directory)/'invalid.zip',raw_interface=True)
            with ZipFile(source,'a') as archive:
                archive.writestr('shaders/lib/foreign.glsl',b'uniform sampler2D colortex12;')
            with self.assertRaisesRegex(ValueError,'already owned'):
                build(source,Path(directory)/'collision.zip',interface=True,raw_interface=True)

    def test_exit_direction_diagnostic_keeps_side_failures_distinct(self):
        shader=(Path(__file__).resolve().parents[1]/'shaders/gbuffers_water.fsh').read_text()
        changed=interface_shader(shader,exit_rays=True)
        self.assertIn('transmittedSide<=0.00001 && reflectedSide>=-0.00001',changed)
        self.assertIn('transmitted.y < -0.00001',changed)
        self.assertEqual(changed.count('vec3 transmitted=refract(-v,n,eta/etaTarget);'),1)
        anchor='    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);'
        self.assertTrue(changed.startswith(shader.split(anchor)[0]))

    def test_interface_diagnostic_preserves_ray_calculation_and_other_members(self):
        shader=(Path(__file__).resolve().parents[1]/'shaders/gbuffers_water.fsh').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.zip';target=Path(directory)/'interface.zip'
            with ZipFile(source,'w') as archive:
                archive.writestr('shaders/gbuffers_water.fsh',shader)
                archive.writestr('shaders/lib/unchanged.glsl',b'unchanged')
            build(source,target,interface=True)
            with ZipFile(target) as archive:
                changed=archive.read('shaders/gbuffers_water.fsh').decode()
                self.assertEqual(archive.read('shaders/lib/unchanged.glsl'),b'unchanged')
            anchor='    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);'
            self.assertTrue(changed.startswith(shader.decode().split(anchor)[0]))
            self.assertIn('reflectedSide < -0.00001',changed)
            self.assertIn('transmittedSide>0.00001',changed)
            with self.assertRaises(FileExistsError):
                build(source,target,interface=True)
            with self.assertRaises(ValueError):
                build(source,target,interface=True,unknown_kinds=True)

    def test_only_water_fragment_changes_and_target_is_exclusive(self):
        shader = (Path(__file__).resolve().parents[1] / 'shaders/gbuffers_water.fsh').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.zip'
            target = Path(directory) / 'diagnostic.zip'
            with ZipFile(source, 'w') as archive:
                archive.writestr('shaders/gbuffers_water.fsh', shader)
                archive.writestr('shaders/lib/unchanged.glsl', b'unchanged')
            build(source, target)
            with ZipFile(target) as archive:
                self.assertEqual(archive.read('shaders/lib/unchanged.glsl'), b'unchanged')
                changed = archive.read('shaders/gbuffers_water.fsh').decode()
                self.assertIn('receiverDiagnostic=vec3(0.0,1.0,0.0)', changed)
                self.assertIn('fresnel>=0.9999?receiverDiagnostic', changed)
            with self.assertRaises(FileExistsError):
                build(source, target)

    def test_missing_or_duplicate_anchor_rejects(self):
        shader = (Path(__file__).resolve().parents[1] / 'shaders/gbuffers_water.fsh').read_text()
        with self.assertRaises(ValueError):
            diagnostic_shader('unrelated shader')
        with self.assertRaises(ValueError):
            diagnostic_shader(shader+'\n    vec4 reflectedHit=reflectionTrace(')

    def test_rejections_preserve_returns_and_pin_the_source(self):
        retained = Path(__file__).resolve().parents[1] / 'dist/Aqualumen-DisplayWater-ReceiverInterfaceCrest-v33-2026-10-11.zip'
        with ZipFile(retained) as archive:
            source = archive.read('shaders/lib/water_receiver.glsl').decode()
        changed = rejection_shader(source)
        self.assertEqual(changed.count('return result;'), source.count('return result;')+2)
        self.assertIn('aqualumenDiagnosticReason=32;return result;', changed)
        self.assertIn('aqualumenDiagnosticReason=33;return result;', changed)
        self.assertIn('aqualumenDiagnosticReason==5', changed)
        with self.assertRaises(ValueError):
            rejection_shader(source+'\n')

    def test_run_rejections_keep_geometry_and_source_guards(self):
        source = (Path(__file__).resolve().parents[1] / 'shaders/lib/water_receiver.glsl').read_text()
        changed = run_rejection_shader(source)
        self.assertEqual(changed.count('return result;'), source.count('return result;')+3)
        for reason in (6, 7, 9, 17, 20, 31, 32, 33, 41, 42):
            self.assertIn('aqualumenDiagnosticReason='+str(reason)+';return result;', changed)
        for guard in ('receiverRunCell(', 'if(runs && sourceIndex<0)', 'if(face.a!=1.0)',
                      'if(any(notEqual(face.xyz,normal)))', 'source.a!=1.0', 'direct.a!=1.0',
                      'any(greaterThan(direct.rgb,source.rgb))', 'if(next>48.0)'):
            self.assertIn(guard, changed)
        with self.assertRaises(ValueError):
            run_rejection_shader(source+'\n')
        with self.assertRaises(ValueError):
            rejection_shader(source)

    def test_modes_cannot_be_combined(self):
        with self.assertRaises(ValueError):
            build(Path('unused'), Path('unused-target'), True, True)
        with self.assertRaises(ValueError):
            build(Path('unused'), Path('unused-target'), False, True, True)

    def test_nested_plant_guards_keep_palette_at_header_scope_and_old_pin(self):
        source = (Path(__file__).resolve().parents[1] / 'shaders/lib/water_receiver.glsl').read_text()
        changed = run_rejection_shader(source)
        self.assertEqual(changed.count('#ifdef AQUALUMEN_PLANT_RECEIVER'), source.count('#ifdef AQUALUMEN_PLANT_RECEIVER'))
        prefix = changed[:changed.index('vec3 aqualumenDiagnosticRejectionColor()')]
        depth = sum(line.startswith('#if') for line in prefix.splitlines())-sum(line.startswith('#endif') for line in prefix.splitlines())
        self.assertEqual(depth, 1)
        retained = Path(__file__).resolve().parents[1] / 'dist/Aqualumen-DisplayWater-PlantAlphaRGBA-v57-2026-10-11.zip'
        with ZipFile(retained) as archive:
            old = archive.read('shaders/lib/water_receiver.glsl').decode()
        self.assertIn('aqualumenDiagnosticReason=17;return result;', run_rejection_shader(old))

    def test_unknown_palette_only_reads_tag_after_unknown_rejection(self):
        source = (Path(__file__).resolve().parents[1] / 'shaders/lib/water_receiver.glsl').read_text()
        changed = unknown_rejection_shader(source)
        self.assertEqual(changed.count('return result;'), source.count('return result;')+3)
        self.assertIn('if(kind!=2.0 && kind!=4.0 && kind!=5.0){aqualumenDiagnosticUnknownKind=geometry.g;', changed)
        self.assertIn('if(aqualumenDiagnosticReason!=17)return vec3(0.1);', changed)
        for subtype in range(1, 10):
            self.assertIn('aqualumenDiagnosticUnknownKind=='+str(subtype)+'.0', changed)
        for guard in ('if(runs && sourceIndex<0)', 'source.a!=1.0', 'direct.a!=1.0', 'if(next>48.0)'):
            self.assertIn(guard, changed)
        with self.assertRaises(ValueError):
            unknown_rejection_shader(source+'\n')


if __name__ == '__main__':
    unittest.main()
