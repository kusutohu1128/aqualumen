"""Paired underwater reflection TEST pack generator: candidate A, passive C12 MRT.

CPU construction only. It never installs, compiles, launches Minecraft or claims
a shader fix. Root shaders/ and LICENSE are read once and hash-checked against a
caller-supplied complete mapping; outputs go to one NEW directory. A partial
write failure keeps the files already written and raises; nothing is cleaned.
"""
import argparse
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SCHEMA = 'aqualumen-paired-water-diagnostic-v1'
VARIANTS = ('control', 'paired')
ZIP_TIME = (2026, 10, 22, 0, 0, 0)
MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 1024
WATER = 'shaders/gbuffers_water.fsh'
FINAL = 'shaders/final.fsh'
PREPARE = 'shaders/prepare.fsh'
PROPERTIES = 'shaders/shaders.properties'
WAVES = 'shaders/lib/waves.glsl'
RIPPLES = 'shaders/lib/ripples.glsl'
UNIFORMS = 'shaders/lib/uniforms.glsl'
CLOUDS = 'shaders/lib/clouds.glsl'
LICENSE = 'LICENSE'
REQUIRED = (WATER, FINAL, PREPARE, PROPERTIES, WAVES, RIPPLES, UNIFORMS, CLOUDS, LICENSE)
WAVE_PHASE_SECONDS = 17.0
ROUTES = {0: 'NOT_WATER', 1: 'SSR', 2: 'WORLD_SOURCE', 3: 'KNOWN_UNREADY',
          4: 'UNKNOWN', 5: 'PRODUCER_UNAVAILABLE'}
COLLISIONS = (b'colortex12', b'colorimg12', b'aqualumenPairedView', b'pairedRoute',
              b'pairedTravel', b'TEST paired-water')
PLANT_DEFINE = re.compile(rb'#\s*define\s+AQUALUMEN_PLANT')
TIME_OVERRIDE = re.compile(rb'(const\s+float|#\s*define)\s+frameTimeCounter\b')
DIRECTIVE = re.compile(rb'/\*\s*(DRAWBUFFERS|RENDERTARGETS)\s*:\s*([^*]*?)\s*\*/')

WAVE_ENTRY = (b'vec3 waveSurfaceLocal(vec2 x, float time, float footprint, float depth, vec2 depthGradient, float detail,\n'
              b'                 out vec3 curvature, out float unresolvedVariance) {\n')
WAVE_FREEZE = b'    time=17.0; // TEST paired-water: frozen resolved wave phase, seconds\n'
WAVE_DELEGATIONS = (
    b'    return waveSurfaceLocal(x,time,footprint,depth,vec2(0.0),detail,curvature,unresolvedVariance);\n',
    b'    return waveSurfaceLocal(x,time,footprint,column.x,column.yz,detail,curvature,slopeVariance);\n')
RIPPLE_ENTRY = b'vec3 rippleState(vec2 worldXZ) {\n'
RIPPLE_GUARD = b'    if(aqualumenActive==0) return vec3(0.0);\n'
RIPPLE_OFF = b'    return vec3(0.0); // TEST paired-water: interaction ripple sampling disabled\n'
WATER_DRAWBUFFERS = b'/* DRAWBUFFERS:0 */\n'
WATER_RENDERTARGETS = b'/* RENDERTARGETS: 0,12 */\n'
MAIN_HEAD = b'void main() {\n'
MAIN_NEXT = b'    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);\n'
MAIN_ZERO = b'    gl_FragData[1]=vec4(0.0); // TEST paired-water: C12 zero before any early return\n'
WATER_SSR = (b'    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,'
             b'environment,upperSurface&&!underwater,worldPosition.y);\n')
SSR_ROUTE = (
    b'    // TEST paired-water C12: classify the actual SSR result above; no second trace.\n'
    b'    float pairedRoute=0.0,pairedTravel=0.0;\n'
    b'    if (underwater) {\n'
    b'        if (reflectedHit.a>0.0) {pairedRoute=1.0;pairedTravel=reflectedHit.a;}\n'
    b'        else if (reflectedHit.a<=0.0 && aqualumenReceiverReady!=1 && aqualumenReceiverReady!=2) pairedRoute=5.0;\n'
    b'        else pairedRoute=4.0;\n'
    b'    }\n')
RECEIVER_ASSIGN = b'            :waterReceiverFirst(worldPosition+n*0.06,reflected);\n'
RECEIVER_NEXT = b'        if (reflectedReceiver.sourceReady) {\n'
RECEIVER_ROUTE = (
    b'        // TEST paired-water C12: the existing receiver result updates the route.\n'
    b'        pairedRoute=reflectedReceiver.sourceReady?2.0:(reflectedReceiver.known?3.0:4.0);\n'
    b'        pairedTravel=pairedRoute<3.5?reflectedReceiver.travel:0.0;\n')
WATER_BEAUTY = b'    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
WATER_STORE = b'    gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);\n'
FINAL_SAMPLER = b'uniform sampler2D colortex0;\n'
FINAL_DECLARATIONS = b'uniform sampler2D colortex12;\nuniform int aqualumenPairedView;\n'
FINAL_BEAUTY = b'    gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);\n'
FINAL_PREVIEW = (
    b'    // TEST paired-water: 0 keeps production beauty; observer capture requires 0.\n'
    b'    if (aqualumenPairedView!=0)\n'
    b'        gl_FragColor=vec4(clamp(texelFetch(colortex12,ivec2(gl_FragCoord.xy),0).xyz'
    b'*vec3(0.2,1.0,1.0/48.0),0.0,1.0),1.0);\n')
PREPARE_FORMATS = b'const int colortex7Format = RGBA16F;\n'
PREPARE_C12 = (b'const int colortex12Format = RGBA32F;\n'
               b'const bool colortex12Clear = true;\n'
               b'const vec4 colortex12ClearColor = vec4(0.0, 0.0, 0.0, 0.0);\n')
WATER_BLEND = b'blend.gbuffers_water=SRC_ALPHA ONE_MINUS_SRC_ALPHA ONE ONE_MINUS_SRC_ALPHA\n'
PAIRED_PROPERTIES = b'blend.gbuffers_water.colortex12=off\nuniform.int.aqualumenPairedView=0\n'

# (label, variants, path, exact anchor, replacement); every anchor must match once.
TRANSFORMS = (
    ('wave_phase_17s', VARIANTS, WAVES, WAVE_ENTRY, WAVE_ENTRY + WAVE_FREEZE),
    ('ripple_sampling_disabled', VARIANTS, RIPPLES, RIPPLE_ENTRY + RIPPLE_GUARD,
     RIPPLE_ENTRY + RIPPLE_OFF + RIPPLE_GUARD),
    ('c12_rendertargets', ('paired',), WATER, WATER_DRAWBUFFERS, WATER_RENDERTARGETS),
    ('c12_zero_at_main_entry', ('paired',), WATER, MAIN_HEAD + MAIN_NEXT, MAIN_HEAD + MAIN_ZERO + MAIN_NEXT),
    ('c12_route_from_actual_ssr', ('paired',), WATER, WATER_SSR, WATER_SSR + SSR_ROUTE),
    ('c12_route_from_actual_receiver', ('paired',), WATER, RECEIVER_ASSIGN + RECEIVER_NEXT,
     RECEIVER_ASSIGN + RECEIVER_ROUTE + RECEIVER_NEXT),
    ('c12_store_at_water_exit', ('paired',), WATER, WATER_BEAUTY + b'}\n', WATER_BEAUTY + WATER_STORE + b'}\n'),
    ('final_c12_sampler_and_selector', ('paired',), FINAL, FINAL_SAMPLER, FINAL_SAMPLER + FINAL_DECLARATIONS),
    ('final_c12_preview_when_selector_nonzero', ('paired',), FINAL, FINAL_BEAUTY + b'}\n',
     FINAL_BEAUTY + FINAL_PREVIEW + b'}\n'),
    ('c12_format_and_zero_clear', ('paired',), PREPARE, PREPARE_FORMATS + b'*/\n',
     PREPARE_FORMATS + PREPARE_C12 + b'*/\n'),
    ('c12_blend_off_and_selector_uniform', ('paired',), PROPERTIES, WATER_BLEND, WATER_BLEND + PAIRED_PROPERTIES),
)


class SourceShapeError(Exception):
    """The source tree differs from the exact shape this generator transforms."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise SourceShapeError(f'Missing, aliased or nonregular input: {path}')
    if path.stat().st_size > MAX_BYTES:
        raise SourceShapeError(f'Oversized input: {path}')
    return path.read_bytes()


def _snapshot(root):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise SourceShapeError('Unknown root shape: root is not a plain directory')
    root = root.resolve()
    shaders = root / 'shaders'
    if shaders.is_symlink() or not shaders.is_dir():
        raise SourceShapeError('Unknown root shape: shaders/ missing or aliased')
    files = {}
    for directory, directories, names in os.walk(shaders):
        directories.sort()
        for entry in directories + names:
            if (Path(directory) / entry).is_symlink():
                raise SourceShapeError(f'Symlink in source tree: {Path(directory) / entry}')
        for name in sorted(names):
            path = Path(directory) / name
            key = path.relative_to(root).as_posix()
            if not key.isascii() or '\\' in key:
                raise SourceShapeError(f'Unsupported source path: {key!r}')
            files[key] = _read(path)
            if len(files) > MAX_FILES:
                raise SourceShapeError('Excessive source file count')
    files[LICENSE] = _read(root / LICENSE)
    return dict(sorted(files.items()))


def _targets(name, data):
    matches = DIRECTIVE.findall(data)
    if len(matches) != data.count(b'DRAWBUFFERS') + data.count(b'RENDERTARGETS'):
        raise SourceShapeError(f'Unrecognized render-target directive in {name}')
    targets = set()
    for kind, value in matches:
        if kind == b'DRAWBUFFERS':
            if not re.fullmatch(rb'[0-9]+', value):
                raise SourceShapeError(f'Unrecognized DRAWBUFFERS value in {name}')
            targets.update(int(chr(digit)) for digit in value)
        else:
            parts = value.split(b',')
            if not all(re.fullmatch(rb'\s*[0-9]+\s*', part) for part in parts):
                raise SourceShapeError(f'Unrecognized RENDERTARGETS value in {name}')
            targets.update(int(part) for part in parts)
    return targets


def _check_shape(files):
    missing = [name for name in REQUIRED if name not in files]
    if missing:
        raise SourceShapeError('Unknown root shape; missing ' + ', '.join(missing))
    for name, data in files.items():
        for token in COLLISIONS:
            if token in data:
                raise SourceShapeError(f'Active C12/diagnostic collision {token.decode()!r} in {name}')
        if PLANT_DEFINE.search(data) or (name == PROPERTIES and b'AQUALUMEN_PLANT' in data):
            raise SourceShapeError(f'Plant receiver define in {name}')
        if TIME_OVERRIDE.search(data):
            raise SourceShapeError(f'frameTimeCounter replaced by a constant in {name}')
        if 12 in _targets(name, data):
            raise SourceShapeError(f'Existing program already writes C12: {name}')

    def single(token, path):
        owners = [name for name, data in files.items() if token in data]
        if owners != [path] or files[path].count(token) != 1:
            raise SourceShapeError(f'{token.decode()!r} must occur once, only in {path}; found in {owners}')

    single(b'vec3 waveSurfaceLocal(', WAVES)
    single(b'vec3 rippleState(', RIPPLES)
    single(b'uniform float frameTimeCounter;', UNIFORMS)
    # The dispersion relation marks the only resolved-phase evaluator.
    single(b'9.81', WAVES)
    for delegation in WAVE_DELEGATIONS:
        if files[WAVES].count(delegation) != 1:
            raise SourceShapeError('waveSurface/localWaveState no longer delegate to waveSurfaceLocal')
    if b'frameTimeCounter' not in files[CLOUDS]:
        raise SourceShapeError('Live non-wave frameTimeCounter consumer (clouds) missing')
    water = files[WATER]
    if water.count(b'gl_FragData[') != 2 or water.count(b'gl_FragData[0]') != 2:
        raise SourceShapeError('Water stage outputs differ from the C0-only shape')
    if b'blend.gbuffers_water.' in files[PROPERTIES]:
        raise SourceShapeError('Existing per-buffer water blend override')


def _transform(files, variant):
    if variant not in VARIANTS:
        raise ValueError(f'Unknown variant {variant!r}; only control or paired')
    _check_shape(files)
    output = dict(files)
    for label, variants, path, anchor, replacement in TRANSFORMS:
        if variant in variants:
            count = output[path].count(anchor)
            if count != 1:
                raise SourceShapeError(f'{label}: exact anchor in {path} found {count} times, expected 1')
            output[path] = output[path].replace(anchor, replacement, 1)
    return output


def variant_files(root: Path, variant: str) -> dict[str, bytes]:
    """Archive paths (shaders/... and LICENSE) to transformed bytes for one variant."""
    if variant not in VARIANTS:
        raise ValueError(f'Unknown variant {variant!r}; only control or paired')
    return _transform(_snapshot(root), variant)


def _zip(files):
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            entry = ZipInfo(name, ZIP_TIME)
            entry.create_system = 3
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, files[name], compresslevel=9)
    return output.getvalue()


def _expected(mapping):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('expected_hashes must be a non-empty mapping')
    for key, value in mapping.items():
        if not isinstance(key, str) or not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError(f'Malformed expected hash entry: {key!r}')
    return mapping


def _destination(root, out_dir):
    path = Path(out_dir).absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f'Output exists: {path}')
    resolved = path.resolve()
    root = Path(root).absolute()
    for protected in (root / 'dist', root / 'shaders'):
        for form in {protected, protected.resolve()}:
            if path.is_relative_to(form) or resolved.is_relative_to(form):
                raise ValueError(f'Output under protected {form}')
    return resolved


def _write_new(path, data):
    with open(path, 'xb') as output:
        output.write(data)


def _manifest(files, variants, archives):
    variant_records = {}
    for variant in VARIANTS:
        members = variants[variant]
        variant_records[variant] = dict(
            archive=f'{variant}.zip', sha256=_sha(archives[variant]),
            members={name: _sha(data) for name, data in sorted(members.items())},
            changed_members=sorted(name for name in files if members[name] != files[name]))
    return dict(
        schema=SCHEMA,
        candidate='A: passive water MRT C12, full resolution, read in the same FINAL invocation',
        test_only=True, not_shipping=True, installed=False,
        inputs=dict(
            sha256=files and {name: _sha(data) for name, data in files.items()},
            expected_hashes='Caller-supplied complete mapping pinned independently by the parent; '
                            'matched exactly before any transformation. This generator originates no pins.'),
        variants=variant_records,
        transformations=[dict(label=label, variants=list(names), path=path,
                              anchor_sha256=_sha(anchor), replacement_sha256=_sha(replacement))
                         for label, names, path, anchor, replacement in TRANSFORMS],
        wave_direct_includers=sorted(name for name, data in files.items()
                                     if b'#include "/lib/waves.glsl"' in data),
        c12_record=dict(
            format='RGBA32F', channels=['route', 'fresnel', 'travel', 'waterMask'],
            clear=[0.0, 0.0, 0.0, 0.0], clear_directive=PREPARE,
            blend='blend.gbuffers_water.colortex12=off; C0 blending unchanged',
            initialization='gl_FragData[1]=vec4(0.0) at gbuffers_water main entry, before the nonwater early return',
            routes={str(code): name for code, name in ROUTES.items()},
            route_rules=[
                'Camera above water, nonwater fragments and discards: C12 (0,0,0,0); waterMask 0.',
                'Underwater water fragment with original reflectionTrace a>0: route 1 SSR, travel=a.',
                'SSR miss (a<=0) with aqualumenReceiverReady not 1/2: route 5 PRODUCER_UNAVAILABLE, travel 0.',
                'SSR miss with ready 1/2: the existing receiver branch sets route 2 WORLD_SOURCE '
                '(sourceReady; travel=reflectedReceiver.travel=final reflectedHit.a), 3 KNOWN_UNREADY '
                '(known; travel=reflectedReceiver.travel) or 4 UNKNOWN (travel 0).',
                'Non-finite SSR result entering neither branch: route 4 UNKNOWN, travel 0.',
                'fresnel is the shader value used by the existing mix; waterMask=1 for every underwater water record.'],
            second_trace=False),
        final_preview=dict(
            uniform='aqualumenPairedView', property='uniform.int.aqualumenPairedView=0',
            beauty_when='aqualumenPairedView==0', sampler='colortex12 stays active through the preview branch',
            observer_requirement='Query the active int uniform in the FINAL program and require 0 at capture; '
                                 'a link default is not evidence.'),
        qualifications=[
            'Wave phase: both variants assign time=17.0 at the entry of shaders/lib/waves.glsl waveSurfaceLocal, '
            'the single shared spectrum evaluator. waveSurface, localWaveState, waveState, waveStateFiltered and '
            'waveNormal delegate to it, so water vertex displacement, water fragment optical normals, receiver '
            'interface geometry and caustics share the 17.0 s phase.',
            'The real frameTimeCounter uniform declaration is unchanged and live: clouds/lighting, shore foam noise '
            'and other non-wave time uses remain real time. ReceiverLightingState.capture requires an active '
            'uniform; actual link activity and producer readiness still require GPU/Iris verification. Clouds are not frozen.',
            'Interaction ripples: both variants return vec3(0.0) unconditionally at rippleState entry. '
            'aqualumenActive/aqualumenRippleA may become inactive where only rippleState used them. The contact '
            'simulation and compute passes still run and are neither frozen nor validated.',
            'Production shaders/ and dist/ are unchanged; only the new output directory is written; nothing is installed.',
            'Daylight and camera control are outside this generator; the parent-owned observer restricts them to the V2 UUID.',
            'Control has the identical wave/ripple qualification and no C12 store, sampler, selector, format, clear or blend line.'],
        attribution_limitations=[
            'FINAL tone maps C0 at the centre and four neighbours and adaptively mixes them; texture filtering '
            'footprints may add contributors. One final beauty pixel mixes multiple C0 source pixels.',
            'Full-resolution C12 records the last surviving gbuffers_water fragment at each source pixel: a source '
            'record, not sole provenance of the final colour.',
            'Discarded fragments leave earlier C0/C12 contributors untouched. Nonwater translucent fragments blend '
            'into C0 but reset the surviving C12 record to zero (C12 blending off).',
            'The route reports the reflection branch actually invoked, not why other models were unsupported.'],
        observer_requirements_unverified=[
            'FINAL has an active colortex12 sampler and an active int aqualumenPairedView equal to 0 at capture.',
            'Read the actual bound C12 texture with glGetTexImage before the FINAL quad and the final output after '
            'that same quad; RGBA32F, viewport-sized; reject partial or mismatched captures.',
            'Pin the pack SHA256 to variants.paired.sha256 and the world to the V2 UUID.'],
        verification=dict(
            input_sha256_matched_expected=True, strict_source_anchors_matched=True,
            archives_read_back_matched=True, glsl_compiled=False, native_c0_invariance_tested=False,
            iris_loaded=False, minecraft_capture=False, observer_present=False,
            physical_acceptance=False, shader_fix_claim=False, performance_claim=False),
    )


def generate(root: Path, out_dir: Path, expected_hashes: dict[str, str]) -> dict:
    """Write control.zip, paired.zip and manifest.json into a NEW out_dir."""
    root = Path(root).absolute()
    destination = _destination(root, out_dir)
    expected = _expected(expected_hashes)
    files = _snapshot(root)
    actual = {name: _sha(data) for name, data in files.items()}
    if set(actual) != set(expected):
        raise SourceShapeError(f'Input key set differs; missing {sorted(set(expected) - set(actual))}, '
                               f'unexpected {sorted(set(actual) - set(expected))}')
    differing = sorted(name for name in actual if actual[name] != expected[name])
    if differing:
        raise SourceShapeError('SHA256 mismatch: ' + ', '.join(differing))
    variants = {variant: _transform(files, variant) for variant in VARIANTS}
    archives = {variant: _zip(variants[variant]) for variant in VARIANTS}
    destination.mkdir()
    for variant in VARIANTS:
        _write_new(destination / f'{variant}.zip', archives[variant])
    for variant in VARIANTS:
        if _sha((destination / f'{variant}.zip').read_bytes()) != _sha(archives[variant]):
            raise RuntimeError(f'{variant}.zip read-back differs; partial evidence kept')
    manifest = _manifest(files, variants, archives)
    _write_new(destination / 'manifest.json',
               (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-hashes', type=Path, required=True,
                        help='JSON object {archive path: sha256} for every shaders/ file plus LICENSE')
    args = parser.parse_args(argv)
    try:
        if args.expected_hashes.stat().st_size > MAX_BYTES:
            raise ValueError('Oversized expected-hashes file')
        expected = json.loads(args.expected_hashes.read_text(encoding='utf-8'))
        manifest = generate(args.root, args.out, expected)
    except (OSError, ValueError, SourceShapeError, RuntimeError) as failure:
        parser.exit(1, f'Rejected paired water TEST pack: {type(failure).__name__}: {failure}\n')
    print(json.dumps(dict(out=str(args.out), **{f'{variant}.zip': manifest['variants'][variant]['sha256']
                                                for variant in VARIANTS}), sort_keys=True))


if __name__ == '__main__':
    main()
