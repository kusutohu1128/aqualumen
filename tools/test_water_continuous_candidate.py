import json
from pathlib import Path
import unittest
import zipfile
import water_continuous_candidate as candidate
import water_optical_probe as probe

ROOT=Path('/home/kusutohu/repos/aqualumen')

class ContinuousCandidateTest(unittest.TestCase):
    def test_shared_physics_and_geometry_are_unchanged(self):
        helper=(ROOT/'tools/water_continuous_interface_test.glsl').read_text()
        for paired,path in [(False,ROOT/candidate.CONTROL),(True,ROOT/candidate.OPTICAL/'optical.zip')]:
            with zipfile.ZipFile(path) as z:base={name:z.read(name) for name in z.namelist()}
            result=candidate.corrected(base,helper,paired)
            self.assertEqual([name for name in base if base[name]!=result[name]],['shaders/gbuffers_water.fsh'])
            s=result['shaders/gbuffers_water.fsh'].decode()
            self.assertIn('if(underwater && footprint*1.25<=0.035 && localColumn.x>=0.8)',s)
            self.assertIn('refractionTrace(opticalViewPos,transmittedView,',s)
            self.assertIn('waterReceiverFirstFromInterface(opticalPoint+n*0.06,reflected)',s)
            if paired:
                self.assertIn('gl_FragData[2]=underwater?vec4(worldPosition,waterMeanSurfaceY)',s)
                self.assertIn('gl_FragData[4]=underwater?vec4(opticalPoint,float(continuousStatus))',s)

    def test_strict_seams_and_pinned_inputs(self):
        probe.read_pinned(ROOT/candidate.CONTROL,candidate.CONTROL_SHA)
        probe.read_pinned(ROOT/candidate.OPTICAL/'optical.zip',candidate.OPTICAL_SHA)
        with self.assertRaises(ValueError):candidate.corrected({'shaders/gbuffers_water.fsh':b'void main() {}'},'',False)

if __name__=='__main__':unittest.main()
