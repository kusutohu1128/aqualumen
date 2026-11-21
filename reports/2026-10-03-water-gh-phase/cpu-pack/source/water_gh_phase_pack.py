"""Pinned reversible TEST GH-phase ZIPs; CPU construction, never installation."""
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
OUTPUT_ROOT = ROOT / 'reports/2026-10-03-water-gh-phase/cpu-pack'
PARENT_SHA = 'b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452'
RESIDUAL = 'shaders/lib/water_residual.glsl'
SUN = 'shaders/lib/water_residual_sun.glsl'
WATER = 'shaders/gbuffers_water.fsh'
FINAL = 'shaders/final.fsh'
PREPARE = 'shaders/prepare.fsh'
PROPERTIES = 'shaders/shaders.properties'
MANIFEST = 'WATER-GH-PHASE.json'
PARENT_ARCHIVE = 'GH-PHASE-original/parent.zip'
PINS = {RESIDUAL: 'def6b357c619b42e437a533d5a0ee751272afa27ecc434206de9fd6a95bbfd9c',
        SUN: '2a65aeec03f3ba645270b3672f9f01e69c50c5261dcdddfe87189a825c5fb9c9',
        WATER: 'dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4',
        FINAL: '43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf',
        PREPARE: 'b31c535fc8959809f76a3f2f2bcc0a795e628709d7109f1d6adc31b67ba5ae11',
        'shaders/lib/water_sun_support.glsl': 'ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441'}
GEOMETRY = [('shaders/gbuffers_water.vsh', '5cb5cde275882a57395d34e1bdd7e2ccf852051cbcb5d421995e1a76557401fd'),
            ('shaders/gbuffers_water.tcs', 'bcdebf3c355194c6be1f901a2c8b582ec7eeb4d1ae5fb5ce6dcc23143a9df932'),
            ('shaders/gbuffers_water.tes', '973e088388ddec93565cb5aaa47f0bbd397703d7a381f900b19f8ed1d1765b6b')]
OLD_NODE = b'        vec2 perturbation=vec2(rootX*nodes[x],crossTerm*nodes[x]+rootZ*nodes[z]);\n'
MAX_BYTES = 64 * 1024 * 1024


def sha(value):
    return hashlib.sha256(value).hexdigest()


def _read(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink() or not path.is_file():
        raise ValueError('Nonregular or aliased input')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Oversized input')
    return path.read_bytes()


def _archive(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized ZIP')
    with ZipFile(BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > 1024 or len({e.filename for e in entries}) != len(entries):
            raise ValueError('Duplicate or excessive ZIP members')
        if sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError('Oversized ZIP storage')
        for entry in entries:
            name = entry.filename
            if (not name or not name.isascii() or '\\' in name or ':' in name or '\x00' in name
                    or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))
                    or not PurePosixPath(name).parts or entry.is_dir()
                    or stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG)
                    or entry.flag_bits & 1 or entry.compress_type not in (ZIP_DEFLATED, ZIP_STORED)):
                raise ValueError('Unsafe ZIP member')
        return {entry.filename: archive.read(entry) for entry in entries}


def _one(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Missing or ambiguous exact source anchor')
    return source.replace(old, new, 1)


def _tag(family, name, body):
    start = f'// AQUALUMEN_{family}_BEGIN:{name}\n'.encode()
    end = f'// AQUALUMEN_{family}_END:{name}\n'.encode()
    return start + body + end


def _erase_tags(source, family):
    prefix = f'// AQUALUMEN_{family}_BEGIN:'.encode()
    while prefix in source:
        start = source.index(prefix)
        newline = source.index(b'\n', start)
        name = source[start + len(prefix):newline]
        end = b'// AQUALUMEN_' + family.encode() + b'_END:' + name + b'\n'
        if source.count(prefix + name + b'\n') != 1 or source.count(end) != 1:
            raise ValueError('Missing or ambiguous recovery tag')
        finish = source.index(end, newline) + len(end)
        restore = (b'/* RENDERTARGETS:0,9,10,11,12 */\n'
                   if family == 'GH_OBSERVE' and name == b'ROUTE' else b'')
        source = source[:start] + restore + source[finish:]
    if f'AQUALUMEN_{family}_'.encode() in source:
        raise ValueError('Unmatched recovery tag')
    return source


def _phase(original, phase):
    if type(phase) is not int or phase not in (0, 45):
        raise ValueError('Phase must be integer zero or 45')
    define = _tag('GH_PHASE', 'DEFINE', f'#define WGP_GH_PHASE {phase}\n'.encode())
    source = _one(original, b'#define AQUALUMEN_WATER_RESIDUAL\n',
                  b'#define AQUALUMEN_WATER_RESIDUAL\n' + define)
    before = _tag('GH_PHASE', 'NODE_BEFORE', b'#if WGP_GH_PHASE == 0\n')
    after = _tag('GH_PHASE', 'NODE_AFTER',
        b'#elif WGP_GH_PHASE == 45\n'
        b'        vec2 WGP_standard=vec2(nodes[x]-nodes[z],nodes[x]+nodes[z])*0.7071067811865475244;\n'
        b'        vec2 perturbation=vec2(rootX*WGP_standard.x,crossTerm*WGP_standard.x+rootZ*WGP_standard.y);\n'
        b'#else\n#error Unapproved GH phase\n#endif\n')
    source = _one(source, OLD_NODE, before + OLD_NODE + after)
    if _erase_tags(source, 'GH_PHASE') != original:
        raise ValueError('GH exact helper recovery differs')
    return source


def _expand(files, name, depth=0):
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
            result.append(_expand(files, 'shaders/' + included, depth + 1))
        else:
            result.append((line + '\n').encode())
    return b''.join(result)


def _atlas(original):
    source = _one(original, b'in vec2 texcoord;\n',
                  b''.join(f'uniform sampler2D colortex{n};\n'.encode() for n in range(9, 16))
                  + b'in vec2 texcoord;\n')
    start = source.index(b'void main() {\n')
    # Preserve original exposure/tone and physical AA arithmetic. Only its
    # source coordinate and final return differ in this diagnostic display.
    physical = _one(source[start:], b'void main() {\n', b'vec3 WGP_displayPhysical(vec2 sourceUV) {\n')
    physical = physical.replace(b'texcoord', b'sourceUV')
    physical = _one(physical, b'    gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);\n',
                    b'    return pow(color,vec3(1.0/2.2));\n')
    return source[:start] + physical + b'''
// TEST atlas: four columns, two rows; identical sourceUV in all eight tiles.
// Bottom row: physical C0, C9, C10, C11. Top row: C12, C13, C14, C15.
// Record tiles encode signed RGB as .5+.5*x/(1+abs(x)); bottom 1/8 shows A.
// C15 uses original exposure/tone/gamma on raw final water RGB, no second AA;
// its bottom 1/8 shows actual callSeen. This is not a calibrated color readback.
vec3 WGP_showRecord(vec4 value,vec2 sourceUV) {
    vec3 encoded=vec3(0.5)+0.5*value.rgb/(vec3(1.0)+abs(value.rgb));
    if (sourceUV.y<0.125) encoded=vec3(0.5+0.5*value.a/(1.0+abs(value.a)));
    return encoded;
}
void main() {
    vec2 atlas=texcoord*vec2(4.0,2.0);
    ivec2 tileXY=clamp(ivec2(floor(atlas)),ivec2(0),ivec2(3,1));
    int tile=tileXY.x+4*tileXY.y;
    vec2 sourceUV=clamp(atlas-vec2(tileXY),vec2(0.0),vec2(1.0));
    ivec2 sourceSize=textureSize(colortex9,0);
    ivec2 sourcePixel=clamp(ivec2(sourceUV*vec2(sourceSize)),ivec2(0),sourceSize-ivec2(1));
    vec3 displayed;
    if (tile==0) displayed=WGP_displayPhysical(sourceUV);
    else {
        vec4 record=vec4(0.0);
        if (tile==1) record=texelFetch(colortex9,sourcePixel,0);
        else if (tile==2) record=texelFetch(colortex10,sourcePixel,0);
        else if (tile==3) record=texelFetch(colortex11,sourcePixel,0);
        else if (tile==4) record=texelFetch(colortex12,sourcePixel,0);
        else if (tile==5) record=texelFetch(colortex13,sourcePixel,0);
        else if (tile==6) record=texelFetch(colortex14,sourcePixel,0);
        else if (tile==7) record=texelFetch(colortex15,sourcePixel,0);
        displayed=WGP_showRecord(record,sourceUV);
        if (tile==7) {
            displayed=pow(tone(record.rgb),vec3(1.0/2.2));
            if (sourceUV.y<0.125) displayed=vec3(clamp(record.a,0.0,1.0));
        }
    }
    gl_FragColor=vec4(displayed,1.0);
}
'''


def _observe(files):
    physical = dict(files)
    sun = _one(files[SUN], b'bool WNS_legacyApplied(); // removable bridge AFTER unchanged old helper\n',
        b'bool WNS_legacyApplied(); // removable bridge AFTER unchanged old helper\n' +
        _tag('GH_OBSERVE', 'GLOBALS', b'vec4 WGP_readLegacyStatus();\n'
             b'vec4 WGP_fullWR=vec4(0.0);\nvec4 WGP_baseWR=vec4(0.0);\n'))
    sun = _one(sun, b'    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n',
        b'    WNS_status=vec4(float(requested),0.0,0.0,0.0);\n' +
        _tag('GH_OBSERVE', 'RESET', b'    WGP_fullWR=vec4(0.0);\n    WGP_baseWR=vec4(0.0);\n'))
    for label in ('full', 'base'):
        anchor = f'    bool {label}Applied=WNS_legacyApplied();\n'.encode()
        sun = _one(sun, anchor, anchor + _tag('GH_OBSERVE', label.upper(),
                       f'    WGP_{label}WR=WGP_readLegacyStatus();\n'.encode()))
    files[SUN] = sun
    water = _one(files[WATER], b'/* RENDERTARGETS:0,9,10,11,12 */\n',
        _tag('GH_OBSERVE', 'ROUTE', b'/* RENDERTARGETS:0,9,10,11,12,13,14,15 */\n'))
    anchor = b'bool WNS_legacyApplied() { return WR_status.y==1.0; }\n'
    water = _one(water, anchor, anchor + _tag('GH_OBSERVE', 'BRIDGE',
                    b'vec4 WGP_readLegacyStatus() { return WR_status; }\n'))
    anchor = b'    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);\n'
    water = _one(water, anchor, anchor + _tag('GH_OBSERVE', 'MAIN_RESET',
                    b'    float WGP_callSeen=0.0;\n    float WGP_grazingResolved=0.0;\n'))
    anchor = b'/* UNDERWATER_PROBE_END */\n        return;\n'
    water = _one(water, anchor, b'/* UNDERWATER_PROBE_END */\n' +
        _tag('GH_OBSERVE', 'NONWATER', b'        gl_FragData[5]=vec4(0.0);\n'
             b'        gl_FragData[6]=vec4(0.0);\n        gl_FragData[7]=vec4(0.0);\n') + b'        return;\n')
    anchor = b'        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));\n'
    water = _one(water, anchor, anchor + _tag('GH_OBSERVE', 'GRAZING', b'        WGP_grazingResolved=resolved;\n'))
    anchor = b'    if (aqualumenSunTestAuthorized==1) {\n'
    water = _one(water, anchor, anchor + _tag('GH_OBSERVE', 'CALL', b'    WGP_callSeen=1.0;\n'))
    anchor = b'/* UNDERWATER_PROBE_END */\n}\n'
    store = b'''    gl_FragData[1]=WNS_reasons;
    gl_FragData[2]=vec4(WNS_status.xy,WSP_counts.x+64.0*WSP_counts.y+4096.0*WSP_counts.z+262144.0*WSP_counts.w,WNS_status.w);
    gl_FragData[3]=vec4(float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible),WGP_grazingResolved,float(receiverKind),reflectedHit.a);
    gl_FragData[5]=WGP_fullWR;
    gl_FragData[6]=WGP_baseWR;
    gl_FragData[7]=vec4(max(color,vec3(0.0)),WGP_callSeen);
'''
    water = _one(water, anchor, b'/* UNDERWATER_PROBE_END */\n' + _tag('GH_OBSERVE', 'STORE', store) + b'}\n')
    files[WATER] = water
    declarations = b''.join((f'const int colortex{n}Format = RGBA32F;\n'
                            f'const bool colortex{n}Clear = true;\n'
                            f'const vec4 colortex{n}ClearColor = vec4(0.0,0.0,0.0,0.0);\n').encode()
                            for n in range(13, 16))
    anchor = b'// UNDERWATER_PROBE_END\n'
    files[PREPARE] = _one(files[PREPARE], anchor, anchor + _tag('GH_OBSERVE', 'FORMATS', declarations))
    blend = b''.join(f'blend.gbuffers_water.colortex{n}=off\n'.encode() for n in range(13, 16))
    # Properties uses # comments, so these recovery markers are translated
    # without changing their meaning or creating invalid property keys.
    properties_tag = _tag('GH_OBSERVE', 'BLEND', blend).replace(b'// AQUALUMEN_', b'# AQUALUMEN_')
    files[PROPERTIES] += properties_tag
    for name in (SUN, WATER, PREPARE):
        if _erase_tags(files[name], 'GH_OBSERVE') != physical[name]:
            raise ValueError('Observer source recovery differs')
    if files[PROPERTIES][:-len(properties_tag)] != physical[PROPERTIES]:
        raise ValueError('Observer property recovery differs')
    files[FINAL] = _atlas(physical[FINAL])


def _files(parent_raw, phase, role):
    if sha(parent_raw) != PARENT_SHA:
        raise ValueError('Unapproved prepared physical parent ZIP')
    if type(role) is not str or role not in ('physical', 'diagnostic'):
        raise ValueError('Unapproved GH role')
    files = _archive(parent_raw)
    for name, pin in PINS.items():
        if sha(files[name]) != pin:
            raise ValueError('Pinned parent source differs')
    old = dict(files)
    files[RESIDUAL] = _phase(old[RESIDUAL], phase)
    added = {PARENT_ARCHIVE: parent_raw, 'GH-PHASE-physical.fsh': old[WATER],
             'GH-PHASE-physical-water_residual.glsl': files[RESIDUAL],
             'GH-PHASE-physical-water_residual_sun.glsl': old[SUN],
             'GH-PHASE-physical-expanded.fsh': _expand(files, WATER)}
    if role == 'diagnostic':
        _observe(files)
        added['GH-PHASE-observed-expanded.fsh'] = _expand(files, WATER)
        if _erase_tags(added['GH-PHASE-observed-expanded.fsh'], 'GH_OBSERVE') != added['GH-PHASE-physical-expanded.fsh']:
            raise ValueError('Expanded observer recovery differs')
    changed = [name for name in old if old[name] != files[name]]
    originals = {name: 'GH-PHASE-original/' + name for name in changed}
    for index, (name, pin) in enumerate(GEOMETRY):
        expanded = _expand(files, name)
        if sha(expanded) != pin:
            raise ValueError('Phase120 tessellation4 geometry differs')
        added[f'GH-PHASE-geometry-stage{index}.glsl'] = expanded
    added.update({archive: old[name] for name, archive in originals.items()})
    if set(added).intersection(files) or MANIFEST in files:
        raise ValueError('GH wrapper already present')
    files.update(added)
    metadata = dict(schema='aqualumen-water-gh-phase-v1', phase_degrees=phase,
        role=role, test_only=True, not_shipping=True,
        parent_pack_sha256=PARENT_SHA, parent_archive_member=PARENT_ARCHIVE,
        changed_existing_members=changed, original_members=originals,
        original_sha256={name: sha(old[name]) for name in changed},
        current_sha256={name: sha(files[name]) for name in changed},
        source_exports_sha256={name: sha(value) for name, value in added.items()},
        FINAL_physical_byte_exact=role == 'physical', original_FINAL_sha256=PINS[FINAL],
        original_zero_expression_byte_exact=True, source_rotation_before_Cholesky=True,
        geometry_factor=4, fixed_phase_seconds=120.0, Sun48_source_unchanged=True,
        executed_Sun48_counts_invariant_claim=False, prepared_helper_unchanged=True,
        guard_unchanged=True, all_other_parent_members_byte_identical=True,
        CPU_only=True, runtime_accepted=False, GL_accepted=False, Iris_accepted=False,
        visual_accepted=False, performance_accepted=False, shipping_accepted=False,
        exact_parent_ZIP_recovery=True,
        layout_schema='aqualumen-gh-visible-band-v1' if role == 'diagnostic' else None,
        old_covariance_layout_compatible=False, covariance_unchanged_in_source=True,
        covariance_exported=False,
        observer_outputs=({'colortex9': 'WNS_reasons.xyzw',
            'colortex10': 'WNS_status.xy, exact old WSP countword, WNS_status.w',
            'colortex11': 'original 4bit flags, copied grazing resolved, outer receiverKind, RAW reflectedHit.a',
            'colortex12': 'unchanged tessStageCoord',
            'colortex13': 'full raw WR_status immediately after full legacy call',
            'colortex14': 'base raw WR_status immediately after base legacy call',
            'colortex15': 'same final water max(color,0) RGB, actual authorized-call marker'}
            if role == 'diagnostic' else {}),
        atlas=(dict(grid=[4, 2], row_order='bottom-to-top',
            tiles=['physical C0', 'C9', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15'],
            source_uv_identical=True, raw_records='integer texelFetch; same C9 dimensions required at runtime',
            record_rgb='signed x encoded .5+.5*x/(1+abs(x)); lower 1/8 shows A',
            C15_rgb='original exposure/tone/gamma; no second AA; lower 1/8 actual call marker',
            physical_tile='original exposure/tone/gamma/AA at same source UV and full-size neighbor offset',
            not_color_calibrated=True, separate_from_physical_appearance_and_timing=True)
            if role == 'diagnostic' else None))
    files[MANIFEST] = (json.dumps(metadata, indent=2, sort_keys=True) + '\n').encode()
    return files, metadata


def _destination(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError('Destination exists')
    if path.resolve() != path or path.suffix != '.zip':
        raise ValueError('Aliased or non-ZIP destination')
    temporary = Path(tempfile.gettempdir()).resolve()
    system_scratch = any(temporary.is_relative_to(Path(root)) for root in ('/tmp', '/var/tmp'))
    allowed = path.is_relative_to(OUTPUT_ROOT) or (system_scratch and path.is_relative_to(temporary))
    protected_repository = path.is_relative_to(ROOT) and not path.is_relative_to(OUTPUT_ROOT)
    if protected_repository or not allowed:
        raise ValueError('Output outside NEW GH CPU subtree or CPU temporary directory')
    return path


def _zip(files):
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, value in sorted(files.items()):
            entry = ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.create_system = 3
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, value, compresslevel=9)
    return output.getvalue()


def _publish(raw, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.gh-phase-cpu-', dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(raw)
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink()


def build_pack(parent, phase, role, destination):
    destination = _destination(destination)
    files, metadata = _files(_read(parent), phase, role)
    if destination.name != f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-{role}-v1.zip':
        raise ValueError('Dedicated TEST pack filename required')
    raw = _zip(files)
    _publish(raw, destination)
    return dict(phase=phase, role=role, pack_sha256=sha(raw), parent_pack_sha256=PARENT_SHA)


def recover_pack(candidate, destination):
    destination = _destination(destination)
    files = _archive(_read(candidate))
    metadata = json.loads(files[MANIFEST])
    parent = files[PARENT_ARCHIVE]
    expected, _ = _files(parent, metadata['phase_degrees'], metadata['role'])
    if files != expected:
        raise ValueError('Source, metadata or unchanged member tampering')
    _publish(parent, destination)
    return dict(recovered_parent_sha256=sha(parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--parent', type=Path, required=True)
    build.add_argument('--phase', choices=('0', '45'), required=True)
    build.add_argument('--role', choices=('physical', 'diagnostic'), required=True)
    build.add_argument('--output', type=Path, required=True)
    recover = commands.add_parser('recover')
    recover.add_argument('--candidate', type=Path, required=True)
    recover.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (build_pack(args.parent, int(args.phase), args.role, args.output) if args.command == 'build'
                  else recover_pack(args.candidate, args.output))
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, UnicodeError, RuntimeError) as failure:
        parser.exit(1, 'Rejected GH TEST pack: ' + type(failure).__name__ + ': ' + str(failure) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
