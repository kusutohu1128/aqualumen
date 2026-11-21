"""Public CPU GH-pack contracts; no GPU/Iris/runtime acceptance."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/water_gh_phase_pack.py'
PARENT = ROOT / 'reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
RESIDUAL = 'shaders/lib/water_residual.glsl'
MANIFEST = 'WATER-GH-PHASE.json'
OLD_NODE = b'        vec2 perturbation=vec2(rootX*nodes[x],crossTerm*nodes[x]+rootZ*nodes[z]);\n'


def cli(*args, env=None):
    return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                          text=True, capture_output=True, env=env)


def strip_tags(source, family):
    source = source.replace(b'# AQUALUMEN_' + family.encode() + b'_',
                            b'// AQUALUMEN_' + family.encode() + b'_')
    prefix = b'// AQUALUMEN_' + family.encode() + b'_BEGIN:'
    while prefix in source:
        a = source.index(prefix)
        name_end = source.index(b'\n', a)
        tag = source[a + len(prefix):name_end]
        end = b'// AQUALUMEN_' + family.encode() + b'_END:' + tag + b'\n'
        b = source.index(end, name_end) + len(end)
        restore = (b'/* RENDERTARGETS:0,9,10,11,12 */\n'
                   if family == 'GH_OBSERVE' and tag == b'ROUTE' else b'')
        source = source[:a] + restore + source[b:]
    return source


class GHPhasePackTests(unittest.TestCase):
    def test_public_zero_physical_pack_preserves_original_expression_and_recovers_exact_parent(self):
        with tempfile.TemporaryDirectory(prefix='gh-phase-cpu-') as temporary:
            first = Path(temporary) / 'Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'
            second = Path(temporary) / 'again/Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'
            for output in (first, second):
                result = cli('build', '--parent', PARENT, '--phase', '0', '--role', 'physical', '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(PARENT) as parent, ZipFile(first) as candidate:
                for name in parent.namelist():
                    if name != RESIDUAL:
                        self.assertEqual(candidate.read(name), parent.read(name), name)
                helper = candidate.read(RESIDUAL)
                self.assertEqual(helper.count(OLD_NODE), 1)
                self.assertEqual(strip_tags(helper, 'GH_PHASE'), parent.read(RESIDUAL))
                metadata = json.loads(candidate.read(MANIFEST))
                self.assertEqual(metadata['schema'], 'aqualumen-water-gh-phase-v1')
                self.assertEqual(metadata['phase_degrees'], 0)
                self.assertEqual(metadata['role'], 'physical')
                self.assertEqual(metadata['changed_existing_members'], [RESIDUAL])
                self.assertIs(metadata['FINAL_physical_byte_exact'], True)
                self.assertIs(metadata['runtime_accepted'], False)
                self.assertEqual(candidate.read(metadata['parent_archive_member']), PARENT.read_bytes())
            recovered = Path(temporary) / 'parent.zip'
            result = cli('recover', '--candidate', first, '--output', recovered)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(recovered.read_bytes(), PARENT.read_bytes())

    def test_public_45_control_rotates_standard_nodes_before_covariance_and_changes_nothing_else(self):
        with tempfile.TemporaryDirectory(prefix='gh-rotate-cpu-') as temporary:
            output = Path(temporary) / 'Aqualumen-ShoreProbe-world-gh-phase-45-physical-v1.zip'
            result = cli('build', '--parent', PARENT, '--phase', '45', '--role', 'physical', '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(PARENT) as parent, ZipFile(output) as candidate:
                for name in parent.namelist():
                    if name != RESIDUAL:
                        self.assertEqual(candidate.read(name), parent.read(name), name)
                helper = candidate.read(RESIDUAL)
                self.assertIn(b'#define WGP_GH_PHASE 45\n', helper)
                self.assertIn(b'vec2 WGP_standard=vec2(nodes[x]-nodes[z],nodes[x]+nodes[z])*0.7071067811865475244;', helper)
                self.assertIn(b'vec2 perturbation=vec2(rootX*WGP_standard.x,crossTerm*WGP_standard.x+rootZ*WGP_standard.y);', helper)
                self.assertEqual(helper.count(OLD_NODE), 1)
                self.assertEqual(strip_tags(helper, 'GH_PHASE'), parent.read(RESIDUAL))
                metadata = json.loads(candidate.read(MANIFEST))
                self.assertEqual(metadata['phase_degrees'], 45)
                self.assertIs(metadata['executed_Sun48_counts_invariant_claim'], False)
            # Independent double-precision second-moment control for L*R*z.
            # It is mathematical fixture qualification, not GPU/transport truth.
            Cxx, Cxz, Czz = 0.021, 0.007, 0.032
            a = math.sqrt(Cxx)
            b = Cxz / a
            c = math.sqrt(Czz - b*b)
            nodes = (-math.sqrt(3), 0.0, math.sqrt(3))
            weights = (1/6, 2/3, 1/6)
            moments = [0.0] * 5
            for i, x in enumerate(nodes):
                for j, z in enumerate(nodes):
                    u, v = (x-z)/math.sqrt(2), (x+z)/math.sqrt(2)
                    X, Z = a*u, b*u+c*v
                    w = weights[i]*weights[j]
                    for k, value in enumerate((X, Z, X*X, X*Z, Z*Z)):
                        moments[k] += w*value
            for actual, expected in zip(moments, (0, 0, Cxx, Cxz, Czz)):
                self.assertAlmostEqual(actual, expected, delta=2e-16)

    def test_public_diagnostic_records_same_invocation_and_displays_all_seven_targets_reversibly(self):
        with tempfile.TemporaryDirectory(prefix='gh-observe-cpu-') as temporary:
            for phase in (0, 45):
                physical = Path(temporary) / f'physical/Aqualumen-ShoreProbe-world-gh-phase-{phase}-physical-v1.zip'
                diagnostic = Path(temporary) / f'diagnostic/Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip'
                for role, output in (('physical', physical), ('diagnostic', diagnostic)):
                    result = cli('build', '--parent', PARENT, '--phase', phase, '--role', role, '--output', output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                with ZipFile(PARENT) as parent, ZipFile(physical) as plain, ZipFile(diagnostic) as observed:
                    metadata = json.loads(observed.read(MANIFEST))
                    self.assertEqual(metadata['layout_schema'], 'aqualumen-gh-visible-band-v1')
                    self.assertIs(metadata['old_covariance_layout_compatible'], False)
                    self.assertIs(metadata['FINAL_physical_byte_exact'], False)
                    self.assertIs(metadata['runtime_accepted'], False)
                    for member in parent.namelist():
                        if member not in metadata['changed_existing_members']:
                            self.assertEqual(observed.read(member), parent.read(member), member)
                    for member in ('shaders/gbuffers_water.fsh', 'shaders/lib/water_residual_sun.glsl',
                                   'shaders/prepare.fsh', 'shaders/shaders.properties'):
                        self.assertEqual(strip_tags(observed.read(member), 'GH_OBSERVE'), plain.read(member), member)
                    self.assertEqual(observed.read(RESIDUAL), plain.read(RESIDUAL))
                    self.assertEqual(observed.read('GH-PHASE-physical-expanded.fsh'), plain.read('GH-PHASE-physical-expanded.fsh'))
                    self.assertEqual(strip_tags(observed.read('GH-PHASE-observed-expanded.fsh'), 'GH_OBSERVE'),
                                     plain.read('GH-PHASE-physical-expanded.fsh'))
                    water = observed.read('shaders/gbuffers_water.fsh')
                    sun = observed.read('shaders/lib/water_residual_sun.glsl')
                    self.assertIn(b'/* RENDERTARGETS:0,9,10,11,12,13,14,15 */', water)
                    self.assertIn(b'gl_FragData[7]=vec4(max(color,vec3(0.0)),WGP_callSeen);', water)
                    self.assertIn(b'WGP_grazingResolved=resolved;', water)
                    self.assertIn(b'float(receiverKind),reflectedHit.a);', water)
                    for label in (b'full', b'base'):
                        self.assertIn(b'bool '+label+b'Applied=WNS_legacyApplied();\n'
                                      b'// AQUALUMEN_GH_OBSERVE_BEGIN:'+label.upper()+b'\n'
                                      b'    WGP_'+label+b'WR=WGP_readLegacyStatus();', sun)
                    final = observed.read('shaders/final.fsh')
                    for target in range(9, 16):
                        self.assertIn(f'uniform sampler2D colortex{target};'.encode(), final)
                        self.assertIn(f'texelFetch(colortex{target},sourcePixel,0)'.encode(), final)
                    self.assertIn(b'WGP_displayPhysical(sourceUV)', final)
                    self.assertEqual(observed.read(metadata['original_members']['shaders/final.fsh']),
                                     parent.read('shaders/final.fsh'))
                    for target in range(13, 16):
                        declarations = observed.read('shaders/prepare.fsh')
                        self.assertIn(f'const int colortex{target}Format = RGBA32F;'.encode(), declarations)
                        self.assertIn(f'const bool colortex{target}Clear = true;'.encode(), declarations)
                        self.assertIn(f'const vec4 colortex{target}ClearColor = vec4(0.0,0.0,0.0,0.0);'.encode(), declarations)
                        self.assertIn(f'blend.gbuffers_water.colortex{target}=off'.encode(), observed.read('shaders/shaders.properties'))
                    for member in metadata['changed_existing_members']:
                        self.assertEqual(observed.read(metadata['original_members'][member]), parent.read(member), member)
                        self.assertEqual(hashlib.sha256(parent.read(member)).hexdigest(), metadata['original_sha256'][member])
                        self.assertEqual(hashlib.sha256(observed.read(member)).hexdigest(), metadata['current_sha256'][member])
                    for member, digest in metadata['source_exports_sha256'].items():
                        self.assertEqual(hashlib.sha256(observed.read(member)).hexdigest(), digest, member)
                    for field in range(5, 8):
                        self.assertIn(f'gl_FragData[{field}]=vec4(0.0);'.encode(), water)
                recovered = Path(temporary) / f'recovered-{phase}.zip'
                result = cli('recover', '--candidate', diagnostic, '--output', recovered)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(recovered.read_bytes(), PARENT.read_bytes())

    def test_public_commands_reject_unpinned_parent_unsafe_candidate_tampering_and_protected_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='gh-safety-cpu-') as temporary:
            directory = Path(temporary)
            output = directory / 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'
            bad_parent = directory / 'bad-parent.zip'
            bad_parent.write_bytes(PARENT.read_bytes() + b'not pinned')
            result = cli('build', '--parent', bad_parent, '--phase', '0', '--role', 'diagnostic', '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            for args in (('--phase', '90', '--role', 'physical'), ('--phase', '0', '--role', 'shipping')):
                result = cli('build', '--parent', PARENT, *args, '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
            for protected in (ROOT / 'shaders/Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip',
                              ROOT / 'reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'):
                self.assertFalse(protected.exists())
                result = cli('build', '--parent', PARENT, '--phase', '0', '--role', 'diagnostic', '--output', protected)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(protected.exists())
            result = cli('build', '--parent', PARENT, '--phase', '0', '--role', 'diagnostic', '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            initial = output.read_bytes()
            result = cli('build', '--parent', PARENT, '--phase', '0', '--role', 'diagnostic', '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), initial)
            recovered = directory / 'recovered.zip'
            for label in ('changed', 'unknown-member', 'unsafe-path', 'symbolic-member'):
                tampered = directory / (label + '.zip')
                with ZipFile(output) as original, ZipFile(tampered, 'w') as candidate:
                    for name in original.namelist():
                        raw = original.read(name)
                        if label == 'changed' and name == 'shaders/gbuffers_water.fsh':
                            raw += b'// changed original computation\n'
                        candidate.writestr(name, raw)
                    if label == 'unknown-member':
                        candidate.writestr('extra.txt', b'unapproved member')
                    elif label == 'unsafe-path':
                        candidate.writestr('../escape.txt', b'unsafe')
                    elif label == 'symbolic-member':
                        entry = ZipInfo('unsafe-link')
                        entry.create_system = 3
                        entry.external_attr = 0o120777 << 16
                        candidate.writestr(entry, b'/unrelated')
                result = cli('recover', '--candidate', tampered, '--output', recovered)
                self.assertNotEqual(result.returncode, 0, label)
                self.assertFalse(recovered.exists())
            alias = directory / 'parent-alias.zip'
            alias.symlink_to(PARENT)
            result = cli('build', '--parent', alias, '--phase', '0', '--role', 'diagnostic', '--output', directory / 'new.zip')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((directory / 'new.zip').exists())

    def test_public_protected_output_rejects_before_input_even_if_TMPDIR_names_repository(self):
        with tempfile.TemporaryDirectory(prefix='gh-env-cpu-') as temporary:
            invalid_parent = Path(temporary) / 'unpinned.zip'
            invalid_parent.write_bytes(b'not a parent')
            protected = ROOT / 'shaders/Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'
            self.assertFalse(protected.exists())
            # Invalid parent prevents any artifact publication even in the RED
            # implementation. Public error priority proves destination refusal
            # precedes processing parent contents; no protected file is created.
            result = cli('build', '--parent', invalid_parent, '--phase', '0', '--role', 'physical',
                         '--output', protected, env={**os.environ, 'TMPDIR': str(ROOT)})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Output outside NEW GH CPU subtree', result.stderr)
            self.assertFalse(protected.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
