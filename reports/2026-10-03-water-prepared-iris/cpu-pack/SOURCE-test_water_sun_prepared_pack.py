"""Public CPU packaging contracts; not Iris, GPU or visual acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/water_sun_prepared_pack.py'
PARENT_ROOT = ROOT / 'reports/2026-10-03-water-sun-support'
PHYSICAL = PARENT_ROOT / 'cpu-physical-view/Aqualumen-ShoreProbe-world-sun-support-zero-physical-v1.zip'
PREPARED = ROOT / 'tools/water_sun_prepared.glsl'
SUPPORT = 'shaders/lib/water_sun_support.glsl'
CAP = 'shaders/lib/water_residual_sun.glsl'
MANIFEST = 'WATER-SUN-PREPARED.json'
SEALED = ROOT / 'reports/2026-10-03-water-prepared/cpu-main/construction-final-v3'
PARENTS = {'physical': PHYSICAL,
           'reasons': PARENT_ROOT / 'cpu-pack/Aqualumen-ShoreProbe-world-sun-support-zero-reasons-v1.zip',
           'inputs': PARENT_ROOT / 'cpu-pack/Aqualumen-ShoreProbe-world-sun-support-zero-inputs-v1.zip'}
OLD_CALL = b'        int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);\n'
NEW_CALL = b'        int WSP_supportClass=waterSunSupportClassPrepared(WPM_viewContext,target);\n'
CONTEXT = (b'// AQUALUMEN_PREPARED_MAIN_CONTEXT_BEGIN\n'
           b'    WSPViewContext WPM_viewContext=waterSunSupportPrepareView(viewToEye,eta);\n'
           b'// AQUALUMEN_PREPARED_MAIN_CONTEXT_END\n')


def cli(*args):
    return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


def expanded(archive, name, depth=0):
    if depth > 32:
        raise ValueError('Include cycle')
    result = []
    for line in archive.read(name).decode().splitlines():
        if line.startswith('#include'):
            include = line.split('"')[1].lstrip('/')
            result.append(expanded(archive, 'shaders/' + include, depth + 1))
        else:
            result.append(line + '\n')
    return ''.join(result)


def native_physical(source):
    # The retained native physical program removes these helper observations;
    # the sealed physical-display ZIP intentionally retains them.
    for tag in ('GLOBALS', 'RESET', 'TARGET', 'BRANCH', 'RAYS', 'KERNEL', 'RECEIVER'):
        begin = b'// AQUALUMEN_SUN_REASONS_BEGIN:' + tag.encode() + b'\n'
        end = b'// AQUALUMEN_SUN_REASONS_END:' + tag.encode() + b'\n'
        assert source.count(begin) == source.count(end) == 1
        a = source.index(begin)
        b = source.index(end, a) + len(end)
        source = source[:a] + source[b:]
    return source


class PreparedPackTests(unittest.TestCase):
    def test_public_physical_build_is_one_reversible_change_and_deterministic(self):
        with tempfile.TemporaryDirectory(prefix='prepared-pack-cpu-') as temporary:
            first = Path(temporary) / 'Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
            second = Path(temporary) / 'second/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
            for output in (first, second):
                result = cli('build', '--parent', PHYSICAL, '--prepared-helper', PREPARED, '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(PHYSICAL) as parent, ZipFile(first) as built:
                for name in parent.namelist():
                    if name not in (SUPPORT, CAP):
                        self.assertEqual(built.read(name), parent.read(name), name)
                self.assertEqual(built.read(SUPPORT), PREPARED.read_bytes())
                cap = built.read(CAP)
                self.assertEqual(cap.count(CONTEXT), 1)
                self.assertEqual(cap.count(NEW_CALL), 1)
                self.assertNotIn(OLD_CALL, cap)
                self.assertEqual(cap.replace(CONTEXT, b'').replace(NEW_CALL, OLD_CALL), parent.read(CAP))
                metadata = json.loads(built.read(MANIFEST))
                self.assertEqual(metadata['schema'], 'aqualumen-water-sun-prepared-pack-v1')
                self.assertEqual(metadata['role'], 'physical')
                self.assertEqual(metadata['changed_existing_members'], [CAP, SUPPORT])
                self.assertEqual(metadata['parent_pack_sha256'], hashlib.sha256(PHYSICAL.read_bytes()).hexdigest())
                for field in ('GL_accepted', 'Iris_accepted', 'visual_accepted', 'performance_accepted', 'shipping_accepted'):
                    self.assertIs(metadata[field], False)
                self.assertEqual(built.read(metadata['parent_archive_member']), PHYSICAL.read_bytes())
                self.assertEqual(built.read(metadata['original_members'][CAP]), parent.read(CAP))
                self.assertEqual(built.read(metadata['original_members'][SUPPORT]), parent.read(SUPPORT))
            recovered = Path(temporary) / PHYSICAL.name
            result = cli('recover', '--candidate', first, '--output', recovered)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(recovered.read_bytes(), PHYSICAL.read_bytes())

    def test_all_three_public_roles_expand_to_exact_sealed_old_and_prepared_main(self):
        with tempfile.TemporaryDirectory(prefix='prepared-expanded-cpu-') as temporary:
            for role, parent_path in PARENTS.items():
                with self.subTest(role=role):
                    output = Path(temporary) / f'Aqualumen-ShoreProbe-world-sun-prepared-{role}-v1.zip'
                    result = cli('build', '--parent', parent_path, '--prepared-helper', PREPARED, '--output', output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    with ZipFile(parent_path) as parent, ZipFile(output) as built:
                        old = expanded(parent, 'shaders/gbuffers_water.fsh').encode()
                        new = expanded(built, 'shaders/gbuffers_water.fsh').encode()
                        native_old = native_physical(old) if role == 'physical' else old
                        native_new = native_physical(new) if role == 'physical' else new
                        self.assertEqual(native_old, (SEALED / f'old-{role}-expanded.fsh').read_bytes())
                        self.assertEqual(native_new, (SEALED / f'prepared-{role}-expanded.fsh').read_bytes())
                        metadata = json.loads(built.read(MANIFEST))
                        self.assertEqual(metadata['old_expanded_main_sha256'], hashlib.sha256(old).hexdigest())
                        self.assertEqual(metadata['prepared_expanded_main_sha256'], hashlib.sha256(new).hexdigest())
                        for name in parent.namelist():
                            if name not in (CAP, SUPPORT):
                                self.assertEqual(built.read(name), parent.read(name), name)
                    recovered = Path(temporary) / ('recovered-' + parent_path.name)
                    result = cli('recover', '--candidate', output, '--output', recovered)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(recovered.read_bytes(), parent_path.read_bytes())

    def test_public_cli_rejects_bad_parent_or_helper_before_creating_output(self):
        with tempfile.TemporaryDirectory(prefix='prepared-pin-cpu-') as temporary:
            temporary = Path(temporary)
            bad_parent = temporary / 'changed-parent.zip'
            bad_parent.write_bytes(PHYSICAL.read_bytes() + b'changed')
            bad_helper = temporary / 'changed-helper.glsl'
            bad_helper.write_bytes(PREPARED.read_bytes() + b'changed')
            for parent, helper in ((bad_parent, PREPARED), (PHYSICAL, bad_helper)):
                destination = temporary / 'never-created/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
                result = cli('build', '--parent', parent, '--prepared-helper', helper, '--output', destination)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(destination.parent.exists())

    def test_public_cli_never_overwrites_or_writes_through_aliases_or_to_sealed_trees(self):
        with tempfile.TemporaryDirectory(prefix='prepared-path-cpu-') as temporary:
            temporary = Path(temporary)
            destination = temporary / 'Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
            destination.write_bytes(b'preserved')
            result = cli('build', '--parent', PHYSICAL, '--prepared-helper', PREPARED, '--output', destination)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_bytes(), b'preserved')
            alias = temporary / 'shipping-alias'
            alias.symlink_to(ROOT / 'shaders', target_is_directory=True)
            destinations = [alias / destination.name, ROOT / 'dist' / destination.name,
                            PHYSICAL.parent / destination.name,
                            ROOT / 'reports/2026-10-03-water-prepared' / destination.name]
            for target in destinations:
                result = cli('build', '--parent', PHYSICAL, '--prepared-helper', PREPARED, '--output', target)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())

    def test_public_recovery_rejects_all_member_tampering_and_unsafe_archives(self):
        with tempfile.TemporaryDirectory(prefix='prepared-recovery-cpu-') as temporary:
            temporary = Path(temporary)
            candidate = temporary / 'Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
            result = cli('build', '--parent', PHYSICAL, '--prepared-helper', PREPARED, '--output', candidate)
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(candidate) as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            for name in (CAP, SUPPORT, MANIFEST, 'shaders/gbuffers_water.vsh', 'PREPARED-original/parent.zip'):
                changed = dict(files)
                changed[name] += b'changed'
                tampered = temporary / 'changed.zip'
                with ZipFile(tampered, 'w') as archive:
                    for member, value in changed.items():
                        archive.writestr(member, value)
                destination = temporary / 'never-created/parent.zip'
                result = cli('recover', '--candidate', tampered, '--output', destination)
                self.assertNotEqual(result.returncode, 0, name)
                self.assertFalse(destination.parent.exists())
            for bad_name, mode in (('../outside.glsl', 0o100644),
                                   ('shaders\\outside.glsl', 0o100644),
                                   ('/absolute.glsl', 0o100644),
                                   ('C:/drive.glsl', 0o100644),
                                   ('link.glsl', 0o120777),
                                   ('shaders/gbuffers_water.vsh', 0o100644)):
                tampered = temporary / 'unsafe.zip'
                with ZipFile(tampered, 'w') as archive:
                    for name, value in files.items():
                        archive.writestr(name, value)
                    extra = ZipInfo(bad_name)
                    extra.create_system = 3
                    extra.external_attr = mode << 16
                    if bad_name in files:
                        with self.assertWarns(UserWarning):
                            archive.writestr(extra, b'not a shader')
                    else:
                        archive.writestr(extra, b'not a shader')
                destination = temporary / 'never-created/parent.zip'
                result = cli('recover', '--candidate', tampered, '--output', destination)
                self.assertNotEqual(result.returncode, 0, bad_name)
                self.assertFalse(destination.parent.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
