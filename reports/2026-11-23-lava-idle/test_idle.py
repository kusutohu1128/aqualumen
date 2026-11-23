import unittest
from diagnostics import entries, variants, P3, STABLE, expanded


class DiagnosisTests(unittest.TestCase):
    def test_changes_affect_only_named_program(self):
        p3=entries(P3)
        packs=variants(p3,entries(STABLE))
        def changed(a,b):
            return {k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
        self.assertEqual(changed(packs['comp-pragma'],packs['comp-default']),{'shaders/composite.fsh'})
        self.assertEqual(changed(packs['def-five'],packs['def-four']),{'shaders/deferred.fsh'})
        for key,data in packs.items():
            program='deferred' if key.startswith('comp') else 'composite'
            self.assertEqual(expanded(data,program+'.fsh'),expanded(p3,program+'.fsh'))
        self.assertNotIn('LavaLight aqualumenAreaSourceLighting(',expanded(packs['comp-pragma'],'composite.fsh'))
        self.assertIn('aqualumenAreaSourceLightingIdleWater',expanded(packs['comp-pragma'],'composite.fsh'))
        self.assertNotIn('aqualumenAreaSourceLightingIdleWater',expanded(packs['comp-default'],'composite.fsh'))
        self.assertIn('0,4,8,10,14',expanded(packs['def-five'],'deferred.fsh'))
        self.assertNotIn('colortex14',expanded(packs['def-four'],'deferred.fsh'))

    def test_idle_overlay_keeps_older_archive_and_slots(self):
        from diagnostics import ROOT, P8
        from pathlib import Path
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'test.zip'
            subprocess.run(['python3',str(ROOT/'tools/build.py'),'--idle-preview','--output',str(out)],check=True)
            a,b=entries(P8),entries(out)
            changed={k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
            self.assertEqual(changed,{'shaders/deferred.fsh','shaders/deferred.vsh','shaders/composite.fsh',
                                      'shaders/lib/idle_deferred.glsl'})
            self.assertIn(b'0,4,8,10,14',b['shaders/deferred.fsh'])

    def test_staged_client_consumes_marker_then_verifies_empty_hands(self):
        import runpy
        import sys
        from pathlib import Path
        module=runpy.run_path(str(Path(__file__).with_name('run.py')))
        sys.path.insert(0,str(module['guarded'].T))
        import scene
        for cls,names in [('BirchOnly',('birch-off',)),('FourScenes',module['birch'].STAGES)]:
            controller=module[cls](scene)
            files=controller.datapack(names)
            self.assertIn('weapon.offhand with air',files['data/animal/function/start.mcfunction'])
            for i in ((2,) if cls=='BirchOnly' else range(4)):
                for prefix in ('v','e'):
                    stage=files[f'data/animal/function/{prefix}{i}.mcfunction']
                    for hand in ('mainhand','offhand'):
                        self.assertIn(f'weapon.{hand} * run scoreboard players set #ok aq_room 0',stage)
