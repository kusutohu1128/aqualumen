"""Reversible, pinned TEST-only prepared-context ZIPs. CPU packaging only."""
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from zipfile import BadZipFile, ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / 'reports/2026-10-03-water-prepared-iris/cpu-pack'
SUPPORT = 'shaders/lib/water_sun_support.glsl'
CAP = 'shaders/lib/water_residual_sun.glsl'
MANIFEST = 'WATER-SUN-PREPARED.json'
PARENT_ARCHIVE = 'PREPARED-original/parent.zip'
ORIGINALS = {CAP: 'PREPARED-original/water_residual_sun.glsl',
             SUPPORT: 'PREPARED-original/water_sun_support.glsl'}
OLD_SHA = 'f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a'
PREPARED_SHA = 'ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441'
MAIN_SHA = '0e7e27e6cbf6655638745021c197c0c16f50784474f9fe820dce01e678b7ead5'
PARENTS = {
    '33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda': 'physical',
    '7f15dbc05a68cc80be3ae0f6ea66ec5ae3c3f42785eb753d4e603f7089ba9048': 'reasons',
    '5a1dd986f95961c96d9175301b8ce432d65cde792e89f99e01935234abde70b0': 'inputs'}
CAP_SHA = {'physical': '93ff088ca7967f1cf0cbddc0454f32de93b129a4fe54eb5b7d17413d199d0cdc',
           'reasons': '93ff088ca7967f1cf0cbddc0454f32de93b129a4fe54eb5b7d17413d199d0cdc',
           'inputs': '3bd8e7b41f7c17e3e8f4eb875c4152c7493b75cf3658813f5ef85f88149121f8'}
OLD_CALL = b'        int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);\n'
NEW_CALL = b'        int WSP_supportClass=waterSunSupportClassPrepared(WPM_viewContext,target);\n'
ANCHOR = (b'    float integral=0.0;\n'
          b'    if (valid) for (int r=0;r<4;++r) for (int j=0;j<12;++j) {\n')
CONTEXT = (b'// AQUALUMEN_PREPARED_MAIN_CONTEXT_BEGIN\n'
           b'    WSPViewContext WPM_viewContext=waterSunSupportPrepareView(viewToEye,eta);\n'
           b'// AQUALUMEN_PREPARED_MAIN_CONTEXT_END\n')
MAX_BYTES = 64 * 1024 * 1024
NATIVE_EXPANDED = {
    'physical': ('c51fe78bce0db6df333cfca9f0368eacef2364135b568a4f54a505f4f4109840',
                 '792265daf8fb6cebdc0ebf33fb567a9b1dd0ac9307ceb6d07926990c69243adf'),
    'reasons': ('0fc5f046d5d62b7bd1af1196d0645085d2667e927f344f330d1012d0b0243b1a',
                '75ccfe7e33270fda60ed71238b133f3b31631197911724d2de7163ef898fb097'),
    'inputs': ('bc4d98c67bb03ee85c02c1c2a4726a393fcceca478a837b94e519bc0fc25da4e',
               '286844598ed411b33ccff34cf1da5d01fcdc5c79eaf2ce8072eb5eea822e3495')}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def _read_file(path):
    path = Path(path).absolute()
    if path.is_symlink() or path.resolve() != path or not path.is_file():
        raise ValueError('Nonregular or aliased input')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Oversized input')
    return path.read_bytes()


def _archive(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized archive')
    with ZipFile(BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > 1024 or len({e.filename for e in entries}) != len(entries):
            raise ValueError('Duplicate or excessive archive members')
        if sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError('Oversized archive storage')
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name).parts
            file_type = stat.S_IFMT(entry.external_attr >> 16)
            if (not name or not name.isascii() or '\\' in name or ':' in name or '\x00' in name
                    or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))
                    or not parts or entry.is_dir() or file_type not in (0, stat.S_IFREG)
                    or entry.flag_bits & 1 or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED)):
                raise ValueError('Unsafe archive member')
        return {entry.filename: archive.read(entry) for entry in entries}


def _one(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Missing or ambiguous exact source anchor')
    return source.replace(old, new, 1)


def _expanded(files, name='shaders/gbuffers_water.fsh', depth=0):
    if depth > 32:
        raise ValueError('Include cycle')
    result = []
    for line in files[name].decode().splitlines():
        if line.startswith('#include'):
            match = re.fullmatch(r'#include\s+"(/?[^"\s]+)"\s*', line)
            if not match:
                raise ValueError('Malformed include')
            included = match[1].lstrip('/')
            if '..' in included.split('/') or '\\' in included:
                raise ValueError('Unsafe include')
            result.append(_expanded(files, 'shaders/' + included, depth + 1))
        else:
            result.append((line + '\n').encode())
    return b''.join(result)


def _native_physical(source):
    for tag in ('GLOBALS', 'RESET', 'TARGET', 'BRANCH', 'RAYS', 'KERNEL', 'RECEIVER'):
        begin = b'// AQUALUMEN_SUN_REASONS_BEGIN:' + tag.encode() + b'\n'
        end = b'// AQUALUMEN_SUN_REASONS_END:' + tag.encode() + b'\n'
        if source.count(begin) != 1 or source.count(end) != 1:
            raise ValueError('Reason normalization span differs')
        start = source.index(begin)
        finish = source.index(end, start) + len(end)
        source = source[:start] + source[finish:]
    return source


def _files(parent_raw, prepared):
    pin = sha(parent_raw)
    if pin not in PARENTS:
        raise ValueError('Unapproved parent ZIP hash')
    if sha(prepared) != PREPARED_SHA:
        raise ValueError('Prepared helper hash differs')
    role = PARENTS[pin]
    files = _archive(parent_raw)
    if sha(files[SUPPORT]) != OLD_SHA or sha(files[CAP]) != CAP_SHA[role]:
        raise ValueError('Parent helper source hash differs')
    parent_metadata = json.loads(files['WATER-SUN-SUPPORT.json'])
    if (parent_metadata.get('schema') != 'aqualumen-water-sun-support-v1'
            or parent_metadata.get('mode') != 'zero'
            or parent_metadata.get('observe') != ('inputs' if role == 'inputs' else 'reasons')
            or parent_metadata.get('shipping_accepted') is not False
            or parent_metadata.get('geometry_factor') != 4
            or parent_metadata.get('fixed_phase_seconds') != 120.0):
        raise ValueError('Parent policy differs')
    new_names = {MANIFEST, PARENT_ARCHIVE, *ORIGINALS.values()}
    if new_names.intersection(files):
        raise ValueError('Prepared wrapper already present')
    old_cap = files[CAP]
    old_expanded = _expanded(files)
    if b'AQUALUMEN_PREPARED_MAIN_CONTEXT_' in old_cap:
        raise ValueError('Parent already contains prepared context')
    cap = _one(old_cap, ANCHOR,
               b'    float integral=0.0;\n' + CONTEXT + ANCHOR.split(b'\n', 1)[1])
    cap = _one(cap, OLD_CALL, NEW_CALL)
    recovered = _one(_one(cap, CONTEXT, b''), NEW_CALL, OLD_CALL)
    if recovered != old_cap or b'if (!WPM_viewContext.valid)' in cap:
        raise ValueError('Exact recovery or invalid-context policy differs')
    for name, original in ORIGINALS.items():
        files[original] = files[name]
    files[PARENT_ARCHIVE] = parent_raw
    files[SUPPORT] = prepared
    files[CAP] = cap
    new_expanded = _expanded(files)
    old_native = _native_physical(old_expanded) if role == 'physical' else old_expanded
    new_native = _native_physical(new_expanded) if role == 'physical' else new_expanded
    if (sha(old_native), sha(new_native)) != NATIVE_EXPANDED[role]:
        raise ValueError('Expanded source differs from sealed native transform')
    metadata = dict(
        schema='aqualumen-water-sun-prepared-pack-v1', role=role,
        test_only=True, not_shipping=True, shipping_fix=False,
        parent_pack_sha256=pin, parent_archive_member=PARENT_ARCHIVE,
        original_members=ORIGINALS,
        original_sha256={name: sha(files[original]) for name, original in ORIGINALS.items()},
        current_sha256={name: sha(files[name]) for name in ORIGINALS},
        changed_existing_members=sorted(ORIGINALS),
        added_members=sorted(new_names), all_other_parent_members_byte_identical=True,
        main_transform_source='tools/water_sun_prepared_main_probe.cpp',
        main_transform_source_sha256=MAIN_SHA,
        old_expanded_main_sha256=sha(old_expanded), prepared_expanded_main_sha256=sha(new_expanded),
        old_native_comparison_sha256=sha(old_native), prepared_native_comparison_sha256=sha(new_native),
        native_comparison_normalization=('Remove exactly seven helper reason spans for comparison only; ZIP retains them'
                                         if role == 'physical' else 'No normalization; literal expanded source equality'),
        old_helper_sha256=OLD_SHA, prepared_helper_sha256=PREPARED_SHA,
        context_scope='One local context per native 48-node cap invocation, before the original valid-loop guard',
        cap_context_declarations=1, node_class_call_sites=1,
        invalid_context_shortcut=False, unknown_whole_fallback_unchanged=True,
        counts_reasons_48_weights_unchanged=True,
        geometry_factor=4, fixed_phase_seconds=120.0,
        physical_parameters_geometry_sources_guard_and_FINAL_unchanged=True,
        inherited_counters_MRT_TES_retained=True, fully_observer_free=False,
        role_STORE_free=(role == 'physical'),
        inherited_metadata_is_current_helper_identity=False,
        inherited_prepared_helper_comments_are_historical=True,
        exact_parent_zip_recovery=True, CPU_packaging_only=True,
        GL_accepted=False, Iris_accepted=False, visual_accepted=False,
        performance_accepted=False, physics_accepted=False, shipping_accepted=False,
        acceptance_scope='Pinned byte transformation and exact reversible archive only; native prior evidence does not qualify this ZIP in Iris')
    files[MANIFEST] = (json.dumps(metadata, indent=2, sort_keys=True) + '\n').encode()
    return files, metadata


def _destination(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError('Destination exists')
    if path.resolve() != path or path.suffix != '.zip':
        raise ValueError('Aliased or non-ZIP destination')
    # This tool never installs a pack. Only this NEW report subtree or OS temp
    # directories for public CPU tests can receive output.
    if not (path.is_relative_to(OUTPUT_ROOT) or path.is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise ValueError('Destination outside NEW CPU packaging scope')
    return path


def _publish(raw, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.prepared-cpu-', dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(raw)
        os.link(temporary, destination)  # Atomic publication; never overwrites.
    finally:
        if temporary is not None:
            temporary.unlink()


def _zip(files):
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            entry = ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content, compresslevel=9)
    return output.getvalue()


def build_pack(parent, prepared_helper, destination):
    """Build only from one of three sealed parents; no rendering or install."""
    destination = _destination(destination)
    if (sha(_read_file(ROOT / 'tools/water_sun_prepared_main_probe.cpp')) != MAIN_SHA
            or sha(_read_file(ROOT / SUPPORT)) != OLD_SHA):
        raise ValueError('Pinned local source differs')
    files, metadata = _files(_read_file(parent), _read_file(prepared_helper))
    expected_name = f'Aqualumen-ShoreProbe-world-sun-prepared-{metadata["role"]}-v1.zip'
    if destination.name != expected_name:
        raise ValueError('Dedicated TEST pack name required')
    raw = _zip(files)
    _publish(raw, destination)
    return dict(role=metadata['role'], pack_sha256=sha(raw), parent_pack_sha256=metadata['parent_pack_sha256'])


def recover_pack(candidate, destination):
    """Recover original ZIP bytes only after every candidate member is checked."""
    destination = _destination(destination)
    files = _archive(_read_file(candidate))
    parent_raw = files[PARENT_ARCHIVE]
    expected, metadata = _files(parent_raw, files[SUPPORT])
    if files != expected:
        raise ValueError('Candidate source, metadata or unchanged members differ')
    _publish(parent_raw, destination)
    return dict(recovered_parent_sha256=sha(parent_raw), role=metadata['role'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--parent', type=Path, required=True)
    build.add_argument('--prepared-helper', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    recover = commands.add_parser('recover')
    recover.add_argument('--candidate', type=Path, required=True)
    recover.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (build_pack(args.parent, args.prepared_helper, args.output) if args.command == 'build'
                  else recover_pack(args.candidate, args.output))
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, UnicodeError, RuntimeError) as failure:
        parser.exit(1, 'Rejected prepared TEST pack: ' + type(failure).__name__ + ': ' + str(failure) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
