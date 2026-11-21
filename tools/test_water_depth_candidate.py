import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

import water_depth_candidate as depth
import water_optical_probe as probe


ROOT = Path("/home/kusutohu/repos/aqualumen")
STAGING = Path(__file__).parent


class DepthCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archives = {}
        for label, pin in depth.ARCHIVE_PINS.items():
            path = ROOT / depth.BASE / (label + ".zip")
            probe.read_pinned(path, pin)
            with zipfile.ZipFile(path) as archive:
                cls.archives[label] = {name: archive.read(name) for name in archive.namelist()}
        cls.sources = {name: probe.read_pinned(ROOT / depth.BASE / "observer-sources" / name, pin) for name, pin in depth.SOURCE_PINS.items()}
        cls.helper = (STAGING / "water_hit_depth_test.glsl").read_text()

    def pack(self, mode, paired=True):
        label = "paired" if paired else "control"
        result = depth.water_depth(self.archives[label], self.helper, mode, paired)
        return depth.passive_observation(result) if paired else result

    def test_baseline_control_exact_and_passive_shading(self):
        self.assertEqual(self.pack("baseline", False), self.archives["control"])
        baseline = self.pack("baseline")
        old = self.archives["paired"]["shaders/gbuffers_water.fsh"].decode()
        new = baseline["shaders/gbuffers_water.fsh"].decode()
        self.assertNotIn("gl_FragDepth=", new)
        for anchor in ("if(continuousStatus==0)opticalPoint=solved;", "shadowVisibility(worldPosition,n)*skyAccess",
                       "vec3 opticalViewPos=(gbufferModelView*vec4(opticalPoint,1.0)).xyz;"):
            self.assertIn(anchor, new)
        self.assertEqual(re.findall(r"gl_FragData\[0\]=[^;]+;", old), re.findall(r"gl_FragData\[0\]=[^;]+;", new))

    def test_candidate_initializes_depth_before_every_exit(self):
        for paired in (False, True):
            f = self.pack("candidate", paired)["shaders/gbuffers_water.fsh"].decode()
            main = f[f.index("void main() {"):]
            self.assertTrue(main.startswith("void main() {\n    gl_FragDepth=gl_FragCoord.z;"))
            self.assertLess(main.index("gl_FragDepth=gl_FragCoord.z;"), main.index("if (materialId!=10000.0)"))
            self.assertEqual(main.count("gl_FragDepth="), 2)
            self.assertIn("gl_FragDepth=primaryHit.windowDepth;", main)
            self.assertIn("vec3 opticalViewPos=primaryHit.viewPoint;", main)
            self.assertIn("if(primaryHit.accepted)opticalPoint=primaryHit.point;", main)
            self.assertIn("clamp(length(opaquePosition-opticalViewPos),0.0,48.0)", main)
            self.assertIn("shadowVisibility(opticalPoint,n)*skyAccess", main)
            self.assertNotIn("early_fragment_tests", f)
            self.assertNotIn("depth_greater", f)
            self.assertNotIn("depth_less", f)

    def test_projection_has_complete_guards_without_opaque_guard(self):
        for anchor in ("struct WaterPrimaryHit", "solveStatus!=0", "any(isnan(solvedPoint))", "any(isinf(solvedPoint))",
                       "any(isnan(clip))", "any(isinf(clip))", "clip.w<=0.0", "gl_DepthRange.diff",
                       "gl_DepthRange.near", "gl_DepthRange.far", "abs(pixel-gl_FragCoord.xy)", "vec2(0.01)",
                       "depth<=0.0 || depth>=1.0", "return WaterPrimaryHit(true,solvedPoint,view.xyz,depth)"):
            self.assertIn(anchor, self.helper)
        for forbidden in ("opaqueDepth", "depthtex", "clamp(", "discard", "gl_FragDepth="):
            self.assertNotIn(forbidden, self.helper)

    def test_raster_derivatives_source_transport_and_libraries_unchanged(self):
        old = self.archives["paired"]["shaders/gbuffers_water.fsh"].decode()
        f = self.pack("candidate")["shaders/gbuffers_water.fsh"].decode()
        for expression in re.findall(r"(?:dFdx|dFdy)\([^)]*\)", old):
            self.assertEqual(old.count(expression), f.count(expression), expression)
        for line in old.splitlines():
            if "incidentDepth=" in line or "float verticalDepth=" in line or "absolutePosition=" in line:
                self.assertIn(line, f)
        for mode in depth.VERSIONS:
            for paired in (False, True):
                label = "paired" if paired else "control"
                pack = self.pack(mode, paired)
                for name, data in self.archives[label].items():
                    if name.startswith("shaders/lib/") or name.endswith(".vsh") or name.endswith(".csh"):
                        self.assertEqual(data, pack[name], name)

    def test_composite_observes_actual_values_and_initializes_all_paths(self):
        old = self.archives["paired"]["shaders/composite.fsh"].decode()
        pack = self.pack("candidate")
        f = pack["shaders/composite.fsh"].decode()
        self.assertIn("/* RENDERTARGETS:0,2 */", f)
        self.assertLess(f.index("gl_FragData[1]=vec4(0.0);"), f.index("if (isEyeInWater==1)"))
        self.assertIn("vec3 transmission=waterTransmission(distanceToEye);\n        gl_FragData[1]=vec4(distanceToEye,transmission);", f)
        self.assertEqual(f.count("waterTransmission(distanceToEye)"), 1)
        self.assertEqual(old, f.replace("/* RENDERTARGETS:0,2 */", "/* DRAWBUFFERS:0 */")
                         .replace("\n    gl_FragData[1]=vec4(0.0);", "")
                         .replace("\n        gl_FragData[1]=vec4(distanceToEye,transmission);", ""))
        self.assertIn(b"blend.composite.colortex2=off", pack["shaders/shaders.properties"])

    def test_final_depth_branches_are_preview_only_and_zero_is_default(self):
        pack = self.pack("candidate")
        old = self.archives["paired"]["shaders/final.fsh"].decode()
        f = pack["shaders/final.fsh"].decode()
        self.assertEqual(old[old.index("void main()"):old.index("    // TEST paired-water")],
                         f[f.index("void main()"):f.index("    // TEST paired-water")])
        self.assertIn("uniform sampler2D depthtex0;", f)
        self.assertIn("uniform sampler2D depthtex1;", f)
        for view in (8, 9):
            self.assertIn(f"if (aqualumenPairedView=={view})", f)
        self.assertIn(b"uniform.int.aqualumenPairedView=0", pack["shaders/shaders.properties"])

    def test_observer_has_separate_strict_depth_boundary_and_versions(self):
        for mode, version in depth.VERSIONS.items():
            sources = depth.observer_sources(self.sources, mode)
            read = sources["dev/aqualumen/paired/GlReadback.java"].decode()
            old = self.sources["dev/aqualumen/paired/GlReadback.java"].decode()
            start, end = old.index("    public static Map<String,Object> sampler("), old.index("    public static int uniform(")
            self.assertIn(old[start:end], read)
            for anchor in ("Set.of(33190,36012,35056,36013)", "compare!=0||effectiveCompare!=0", "uniform(program,name,35678)",
                           "poison(Math.multiplyExact(w,h))", "3553,0,6402,5126,data", "!Float.isFinite(value)||value<0.0f||value>1.0f"):
                self.assertIn(anchor, read)
            for anchor in ("format==6402&&depthBits==24&&depthType==35863",'out.put("depthBits",depthBits)',
                           'out.put("depthType",depthType)',"int depthBits=level(34890),depthType=level(35862)"):
                self.assertIn(anchor, read)
            self.assertNotIn("glGetError", read)
            observer = sources["dev/aqualumen/paired/PairedObserver.java"].decode()
            self.assertEqual(observer.count('"depth samplers changed after FINAL"'), 2)
            for anchor in ('"depthSamplers"', '"depthSamplerMapsMatchedAfterQuad"', '"depthChannels"', '".r32f"',
                           '"depth/color/output textures alias"', '"opticalSchema","aqualumen-water-hit-depth-v1"',
                           '"distanceToEye","transmission.r","transmission.g","transmission.b"', '"projectedDepthOrNegativeStatus"'):
                self.assertIn(anchor, observer)
            for anchor in ("private static boolean scope(", "private static Map<String,Object> mods(", "private static boolean recorderReady(", "private static CaptureRules.Identity identity("):
                start = self.sources["dev/aqualumen/paired/PairedObserver.java"].decode().index(anchor)
                original = self.sources["dev/aqualumen/paired/PairedObserver.java"].decode()
                end = original.index("\n    private static", start + 1)
                self.assertIn(original[start:end], observer)
            self.assertEqual(json.loads(sources["fabric.mod.json"])["version"], version)
            self.assertIn(f'"observerVersion","{version}"', observer)

    def test_strict_anchors_fail_closed(self):
        for function, name, old in ((lambda x: depth.water_depth(x, self.helper, "candidate", True), "shaders/gbuffers_water.fsh", b"    int continuousStatus=-1;"),
                                    (depth.passive_observation, "shaders/composite.fsh", b"/* DRAWBUFFERS:0 */"),
                                    (depth.passive_observation, "shaders/final.fsh", b"uniform sampler2D colortex15;")):
            broken = dict(self.archives["paired"])
            broken[name] = broken[name].replace(old, b"missing anchor")
            with self.assertRaises(ValueError):
                function(broken)
        with self.assertRaises(ValueError):
            depth.water_depth(self.archives["paired"], self.helper, "typo", True)

    def test_generation_is_deterministic_exclusive_and_preserves_inputs(self):
        before = {path: probe.sha(path.read_bytes()) for path in (ROOT / "shaders").rglob("*") if path.is_file()}
        with tempfile.TemporaryDirectory(dir=STAGING) as directory:
            directory = Path(directory)
            for mode in depth.VERSIONS:
                first, second = directory / (mode + "1"), directory / (mode + "2")
                a = depth.generate(ROOT, first, mode)
                b = depth.generate(ROOT, second, mode)
                self.assertEqual(a, b)
                self.assertFalse(a["productionSourceModified"])
                self.assertIsNone(a["observerBuild"])
                self.assertEqual(a["inputArchiveSHA256"], depth.ARCHIVE_PINS)
                self.assertEqual(a["sourcePins"], depth.SOURCE_PINS)
                self.assertEqual(a["helperSHA256"], probe.sha(self.helper.encode()))
                for name, pin in a["generatedSourceSha256"].items():
                    self.assertEqual(probe.sha((first / "observer-sources" / name).read_bytes()), pin)
                for label in depth.ARCHIVE_PINS:
                    self.assertEqual((first / (label + ".zip")).read_bytes(), (second / (label + ".zip")).read_bytes())
                with self.assertRaises(FileExistsError):
                    depth.generate(ROOT, first, mode)
        self.assertEqual(before, {path: probe.sha(path.read_bytes()) for path in before})
        for label, pin in depth.ARCHIVE_PINS.items():
            probe.read_pinned(ROOT / depth.BASE / (label + ".zip"), pin)


if __name__ == "__main__":
    unittest.main()
