Here's the patch, built from the actual tree. I haven't run it: this session only had read tools, so the tests' pass/fail status is unknown until you run them. I haven't computed any SHA pins either. `generate()` requires your independently supplied mapping covering every `shaders/**` file plus `LICENSE`, and fails before transforming anything if a key or hash differs.

**Choices that differ from or add to the design:**
- **C12 format/clear directive placement:** it goes in the existing `/* const ...Format */` block in `shaders/prepare.fsh` (paired only), because that block is already proven to be read by Iris for this pack. It sets `RGBA32F`, `Clear=true` and `ClearColor = vec4(0.0, 0.0, 0.0, 0.0)`. `final.fsh` only adds the `colortex12` sampler, the `aqualumenPairedView` int and the `!=0` preview branch, so any nonzero value shows the preview and only 0 gives beauty.
- **Route logic** copies the original branch conditions exactly:
  - `a>0` gives 1.
  - `a<=0` with ready not in {1,2} gives 5.
  - Otherwise 4, which the existing receiver branch then overwrites with 2, 3 or 4 from the `reflectedReceiver` it already computed.
  - A non-finite `a` that enters neither branch stays at 4.
- **Fail-closed shape checks** go beyond anchors. The generator also stops if any of these hold:
  - Any file contains `colortex12`, `colorimg12` or a diagnostic token, or any program already writes target 12.
  - A `DRAWBUFFERS`/`RENDERTARGETS` directive can't be parsed.
  - Any file defines `AQUALUMEN_PLANT*`.
  - `waveSurfaceLocal`, `rippleState` or `uniform float frameTimeCounter;` is not defined exactly once in its expected file, or the two `waveSurfaceLocal` delegations are missing.
  - `9.81` appears anywhere except `waves.glsl`.
  - `frameTimeCounter` has been turned into a const or define.
  - `clouds.glsl` no longer uses `frameTimeCounter`.
  - The water stage writes anything other than C0.
- **Possible anchor whitespace risk:** I counted 17 leading spaces on the second line of the `waveSurfaceLocal` signature from the file view. If that's wrong, the generator refuses to build rather than producing a wrong pack, and the real-tree tests will show it.
- **Output behaviour:**
  - The output directory's parent must already exist; nothing is created above it.
  - Files are written in `x` mode in the order `control.zip`, `paired.zip`, then `manifest.json` last.
  - Both archives are read back before the manifest is written.
  - A partial failure leaves whatever was written and raises; nothing is cleaned up or overwritten.
- **Manifest claims:** only the hash match, the anchor checks and the archive read-back are marked true. Compile, native C0 invariance, Iris load, Minecraft capture, observer, physical acceptance and any shader-fix or performance claim are all false.

*** Begin Patch
*** Add File: tools/water_paired_diagnostic.py
+"""Paired underwater reflection TEST pack generator: candidate A, passive C12 MRT.
+
+CPU construction only. It never installs, compiles, launches Minecraft or claims
+a shader fix. Root shaders/ and LICENSE are read once and hash-checked against a
+caller-supplied complete mapping; outputs go to one NEW directory. A partial
+write failure keeps the files already written and raises; nothing is cleaned.
+"""
+import argparse
+import hashlib
+import json
+import os
+from io import BytesIO
+from pathlib import Path
+import re
+from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
+
+SCHEMA = 'aqualumen-paired-water-diagnostic-v1'
+VARIANTS = ('control', 'paired')
+ZIP_TIME = (2026, 10, 22, 0, 0, 0)
+MAX_BYTES = 64 * 1024 * 1024
+MAX_FILES = 1024
+WATER = 'shaders/gbuffers_water.fsh'
+FINAL = 'shaders/final.fsh'
+PREPARE = 'shaders/prepare.fsh'
+PROPERTIES = 'shaders/shaders.properties'
+WAVES = 'shaders/lib/waves.glsl'
+RIPPLES = 'shaders/lib/ripples.glsl'
+UNIFORMS = 'shaders/lib/uniforms.glsl'
+CLOUDS = 'shaders/lib/clouds.glsl'
+LICENSE = 'LICENSE'
+REQUIRED = (WATER, FINAL, PREPARE, PROPERTIES, WAVES, RIPPLES, UNIFORMS, CLOUDS, LICENSE)
+WAVE_PHASE_SECONDS = 17.0
+ROUTES = {0: 'NOT_WATER', 1: 'SSR', 2: 'WORLD_SOURCE', 3: 'KNOWN_UNREADY',
+          4: 'UNKNOWN', 5: 'PRODUCER_UNAVAILABLE'}
+COLLISIONS = (b'colortex12', b'colorimg12', b'aqualumenPairedView', b'pairedRoute',
+              b'pairedTravel', b'TEST paired-water')
+PLANT_DEFINE = re.compile(rb'#\s*define\s+AQUALUMEN_PLANT')
+TIME_OVERRIDE = re.compile(rb'(const\s+float|#\s*define)\s+frameTimeCounter\b')
+DIRECTIVE = re.compile(rb'/\*\s*(DRAWBUFFERS|RENDERTARGETS)\s*:\s*([^*]*?)\s*\*/')
+
+WAVE_ENTRY = (b'vec3 waveSurfaceLocal(vec2 x, float time, float footprint, float depth, vec2 depthGradient, float detail,\n'
+              b'                 out vec3 curvature, out float unresolvedVariance) {\n')
+WAVE_FREEZE = b'    time=17.0; // TEST paired-water: frozen resolved wave phase, seconds\n'
+WAVE_DELEGATIONS = (
+    b'    return waveSurfaceLocal(x,time,footprint,depth,vec2(0.0),detail,curvature,unresolvedVariance);\n',
+    b'    return waveSurfaceLocal(x,time,footprint,column.x,column.yz,detail,curvature,slopeVariance);\n')
+RIPPLE_ENTRY = b'vec3 rippleState(vec2 worldXZ) {\n'
+RIPPLE_GUARD = b'    if(aqualumenActive==0) return vec3(0.0);\n'
+RIPPLE_OFF = b'    return vec3(0.0); // TEST paired-water: interaction ripple sampling disabled\n'
+WATER_DRAWBUFFERS = b'/* DRAWBUFFERS:0 */\n'
+WATER_RENDERTARGETS = b'/* RENDERTARGETS: 0,12 */\n'
+MAIN_HEAD = b'void main() {\n'
+MAIN_NEXT = b'    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);\n'
+MAIN_ZERO = b'    gl_FragData[1]=vec4(0.0); // TEST paired-water: C12 zero before any early return\n'
+WATER_SSR = (b'    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,'
+             b'environment,upperSurface&&!underwater,worldPosition.y);\n')
+SSR_ROUTE = (
+    b'    // TEST paired-water C12: classify the actual SSR result above; no second trace.\n'
+    b'    float pairedRoute=0.0,pairedTravel=0.0;\n'
+    b'    if (underwater) {\n'
+    b'        if (reflectedHit.a>0.0) {pairedRoute=1.0;pairedTravel=reflectedHit.a;}\n'
+    b'        else if (reflectedHit.a<=0.0 && aqualumenReceiverReady!=1 && aqualumenReceiverReady!=2) pairedRoute=5.0;\n'
+    b'        else pairedRoute=4.0;\n'
+    b'    }\n')
+RECEIVER_ASSIGN = b'            :waterReceiverFirst(worldPosition+n*0.06,reflected);\n'
+RECEIVER_NEXT = b'        if (reflectedReceiver.sourceReady) {\n'
+RECEIVER_ROUTE = (
+    b'        // TEST paired-water C12: the existing receiver result updates the route.\n'
+    b'        pairedRoute=reflectedReceiver.sourceReady?2.0:(reflectedReceiver.known?3.0:4.0);\n'
+    b'        pairedTravel=pairedRoute<3.5?reflectedReceiver.travel:0.0;\n')
+WATER_BEAUTY = b'    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
+WATER_STORE = b'    gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);\n'
+FINAL_SAMPLER = b'uniform sampler2D colortex0;\n'
+FINAL_DECLARATIONS = b'uniform sampler2D colortex12;\nuniform int aqualumenPairedView;\n'
+FINAL_BEAUTY = b'    gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);\n'
+FINAL_PREVIEW = (
+    b'    // TEST paired-water: 0 keeps production beauty; observer capture requires 0.\n'
+    b'    if (aqualumenPairedView!=0)\n'
+    b'        gl_FragColor=vec4(clamp(texelFetch(colortex12,ivec2(gl_FragCoord.xy),0).xyz'
+    b'*vec3(0.2,1.0,1.0/48.0),0.0,1.0),1.0);\n')
+PREPARE_FORMATS = b'const int colortex7Format = RGBA16F;\n'
+PREPARE_C12 = (b'const int colortex12Format = RGBA32F;\n'
+               b'const bool colortex12Clear = true;\n'
+               b'const vec4 colortex12ClearColor = vec4(0.0, 0.0, 0.0, 0.0);\n')
+WATER_BLEND = b'blend.gbuffers_water=SRC_ALPHA ONE_MINUS_SRC_ALPHA ONE ONE_MINUS_SRC_ALPHA\n'
+PAIRED_PROPERTIES = b'blend.gbuffers_water.colortex12=off\nuniform.int.aqualumenPairedView=0\n'
+
+# (label, variants, path, exact anchor, replacement); every anchor must match once.
+TRANSFORMS = (
+    ('wave_phase_17s', VARIANTS, WAVES, WAVE_ENTRY, WAVE_ENTRY + WAVE_FREEZE),
+    ('ripple_sampling_disabled', VARIANTS, RIPPLES, RIPPLE_ENTRY + RIPPLE_GUARD,
+     RIPPLE_ENTRY + RIPPLE_OFF + RIPPLE_GUARD),
+    ('c12_rendertargets', ('paired',), WATER, WATER_DRAWBUFFERS, WATER_RENDERTARGETS),
+    ('c12_zero_at_main_entry', ('paired',), WATER, MAIN_HEAD + MAIN_NEXT, MAIN_HEAD + MAIN_ZERO + MAIN_NEXT),
+    ('c12_route_from_actual_ssr', ('paired',), WATER, WATER_SSR, WATER_SSR + SSR_ROUTE),
+    ('c12_route_from_actual_receiver', ('paired',), WATER, RECEIVER_ASSIGN + RECEIVER_NEXT,
+     RECEIVER_ASSIGN + RECEIVER_ROUTE + RECEIVER_NEXT),
+    ('c12_store_at_water_exit', ('paired',), WATER, WATER_BEAUTY + b'}\n', WATER_BEAUTY + WATER_STORE + b'}\n'),
+    ('final_c12_sampler_and_selector', ('paired',), FINAL, FINAL_SAMPLER, FINAL_SAMPLER + FINAL_DECLARATIONS),
+    ('final_c12_preview_when_selector_nonzero', ('paired',), FINAL, FINAL_BEAUTY + b'}\n',
+     FINAL_BEAUTY + FINAL_PREVIEW + b'}\n'),
+    ('c12_format_and_zero_clear', ('paired',), PREPARE, PREPARE_FORMATS + b'*/\n',
+     PREPARE_FORMATS + PREPARE_C12 + b'*/\n'),
+    ('c12_blend_off_and_selector_uniform', ('paired',), PROPERTIES, WATER_BLEND, WATER_BLEND + PAIRED_PROPERTIES),
+)
+
+
+class SourceShapeError(Exception):
+    """The source tree differs from the exact shape this generator transforms."""
+
+
+def _sha(data):
+    return hashlib.sha256(data).hexdigest()
+
+
+def _read(path):
+    if path.is_symlink() or not path.is_file():
+        raise SourceShapeError(f'Missing, aliased or nonregular input: {path}')
+    if path.stat().st_size > MAX_BYTES:
+        raise SourceShapeError(f'Oversized input: {path}')
+    return path.read_bytes()
+
+
+def _snapshot(root):
+    root = Path(root).absolute()
+    if root.is_symlink() or not root.is_dir():
+        raise SourceShapeError('Unknown root shape: root is not a plain directory')
+    root = root.resolve()
+    shaders = root / 'shaders'
+    if shaders.is_symlink() or not shaders.is_dir():
+        raise SourceShapeError('Unknown root shape: shaders/ missing or aliased')
+    files = {}
+    for directory, directories, names in os.walk(shaders):
+        directories.sort()
+        for entry in directories + names:
+            if (Path(directory) / entry).is_symlink():
+                raise SourceShapeError(f'Symlink in source tree: {Path(directory) / entry}')
+        for name in sorted(names):
+            path = Path(directory) / name
+            key = path.relative_to(root).as_posix()
+            if not key.isascii() or '\\' in key:
+                raise SourceShapeError(f'Unsupported source path: {key!r}')
+            files[key] = _read(path)
+            if len(files) > MAX_FILES:
+                raise SourceShapeError('Excessive source file count')
+    files[LICENSE] = _read(root / LICENSE)
+    return dict(sorted(files.items()))
+
+
+def _targets(name, data):
+    matches = DIRECTIVE.findall(data)
+    if len(matches) != data.count(b'DRAWBUFFERS') + data.count(b'RENDERTARGETS'):
+        raise SourceShapeError(f'Unrecognized render-target directive in {name}')
+    targets = set()
+    for kind, value in matches:
+        if kind == b'DRAWBUFFERS':
+            if not re.fullmatch(rb'[0-9]+', value):
+                raise SourceShapeError(f'Unrecognized DRAWBUFFERS value in {name}')
+            targets.update(int(chr(digit)) for digit in value)
+        else:
+            parts = value.split(b',')
+            if not all(re.fullmatch(rb'\s*[0-9]+\s*', part) for part in parts):
+                raise SourceShapeError(f'Unrecognized RENDERTARGETS value in {name}')
+            targets.update(int(part) for part in parts)
+    return targets
+
+
+def _check_shape(files):
+    missing = [name for name in REQUIRED if name not in files]
+    if missing:
+        raise SourceShapeError('Unknown root shape; missing ' + ', '.join(missing))
+    for name, data in files.items():
+        for token in COLLISIONS:
+            if token in data:
+                raise SourceShapeError(f'Active C12/diagnostic collision {token.decode()!r} in {name}')
+        if PLANT_DEFINE.search(data) or (name == PROPERTIES and b'AQUALUMEN_PLANT' in data):
+            raise SourceShapeError(f'Plant receiver define in {name}')
+        if TIME_OVERRIDE.search(data):
+            raise SourceShapeError(f'frameTimeCounter replaced by a constant in {name}')
+        if 12 in _targets(name, data):
+            raise SourceShapeError(f'Existing program already writes C12: {name}')
+
+    def single(token, path):
+        owners = [name for name, data in files.items() if token in data]
+        if owners != [path] or files[path].count(token) != 1:
+            raise SourceShapeError(f'{token.decode()!r} must occur once, only in {path}; found in {owners}')
+
+    single(b'vec3 waveSurfaceLocal(', WAVES)
+    single(b'vec3 rippleState(', RIPPLES)
+    single(b'uniform float frameTimeCounter;', UNIFORMS)
+    # The dispersion relation marks the only resolved-phase evaluator.
+    single(b'9.81', WAVES)
+    for delegation in WAVE_DELEGATIONS:
+        if files[WAVES].count(delegation) != 1:
+            raise SourceShapeError('waveSurface/localWaveState no longer delegate to waveSurfaceLocal')
+    if b'frameTimeCounter' not in files[CLOUDS]:
+        raise SourceShapeError('Live non-wave frameTimeCounter consumer (clouds) missing')
+    water = files[WATER]
+    if water.count(b'gl_FragData[') != 2 or water.count(b'gl_FragData[0]') != 2:
+        raise SourceShapeError('Water stage outputs differ from the C0-only shape')
+    if b'blend.gbuffers_water.' in files[PROPERTIES]:
+        raise SourceShapeError('Existing per-buffer water blend override')
+
+
+def _transform(files, variant):
+    if variant not in VARIANTS:
+        raise ValueError(f'Unknown variant {variant!r}; only control or paired')
+    _check_shape(files)
+    output = dict(files)
+    for label, variants, path, anchor, replacement in TRANSFORMS:
+        if variant in variants:
+            count = output[path].count(anchor)
+            if count != 1:
+                raise SourceShapeError(f'{label}: exact anchor in {path} found {count} times, expected 1')
+            output[path] = output[path].replace(anchor, replacement, 1)
+    return output
+
+
+def variant_files(root: Path, variant: str) -> dict[str, bytes]:
+    """Archive paths (shaders/... and LICENSE) to transformed bytes for one variant."""
+    if variant not in VARIANTS:
+        raise ValueError(f'Unknown variant {variant!r}; only control or paired')
+    return _transform(_snapshot(root), variant)
+
+
+def _zip(files):
+    output = BytesIO()
+    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
+        for name in sorted(files):
+            entry = ZipInfo(name, ZIP_TIME)
+            entry.create_system = 3
+            entry.compress_type = ZIP_DEFLATED
+            entry.external_attr = 0o100644 << 16
+            archive.writestr(entry, files[name], compresslevel=9)
+    return output.getvalue()
+
+
+def _expected(mapping):
+    if not isinstance(mapping, dict) or not mapping:
+        raise ValueError('expected_hashes must be a non-empty mapping')
+    for key, value in mapping.items():
+        if not isinstance(key, str) or not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
+            raise ValueError(f'Malformed expected hash entry: {key!r}')
+    return mapping
+
+
+def _destination(root, out_dir):
+    path = Path(out_dir).absolute()
+    if path.exists() or path.is_symlink():
+        raise FileExistsError(f'Output exists: {path}')
+    resolved = path.resolve()
+    root = Path(root).absolute()
+    for protected in (root / 'dist', root / 'shaders'):
+        for form in {protected, protected.resolve()}:
+            if path.is_relative_to(form) or resolved.is_relative_to(form):
+                raise ValueError(f'Output under protected {form}')
+    return resolved
+
+
+def _write_new(path, data):
+    with open(path, 'xb') as output:
+        output.write(data)
+
+
+def _manifest(files, variants, archives):
+    variant_records = {}
+    for variant in VARIANTS:
+        members = variants[variant]
+        variant_records[variant] = dict(
+            archive=f'{variant}.zip', sha256=_sha(archives[variant]),
+            members={name: _sha(data) for name, data in sorted(members.items())},
+            changed_members=sorted(name for name in files if members[name] != files[name]))
+    return dict(
+        schema=SCHEMA,
+        candidate='A: passive water MRT C12, full resolution, read in the same FINAL invocation',
+        test_only=True, not_shipping=True, installed=False,
+        inputs=dict(
+            sha256=files and {name: _sha(data) for name, data in files.items()},
+            expected_hashes='Caller-supplied complete mapping pinned independently by the parent; '
+                            'matched exactly before any transformation. This generator originates no pins.'),
+        variants=variant_records,
+        transformations=[dict(label=label, variants=list(names), path=path,
+                              anchor_sha256=_sha(anchor), replacement_sha256=_sha(replacement))
+                         for label, names, path, anchor, replacement in TRANSFORMS],
+        wave_direct_includers=sorted(name for name, data in files.items()
+                                     if b'#include "/lib/waves.glsl"' in data),
+        c12_record=dict(
+            format='RGBA32F', channels=['route', 'fresnel', 'travel', 'waterMask'],
+            clear=[0.0, 0.0, 0.0, 0.0], clear_directive=PREPARE,
+            blend='blend.gbuffers_water.colortex12=off; C0 blending unchanged',
+            initialization='gl_FragData[1]=vec4(0.0) at gbuffers_water main entry, before the nonwater early return',
+            routes={str(code): name for code, name in ROUTES.items()},
+            route_rules=[
+                'Camera above water, nonwater fragments and discards: C12 (0,0,0,0); waterMask 0.',
+                'Underwater water fragment with original reflectionTrace a>0: route 1 SSR, travel=a.',
+                'SSR miss (a<=0) with aqualumenReceiverReady not 1/2: route 5 PRODUCER_UNAVAILABLE, travel 0.',
+                'SSR miss with ready 1/2: the existing receiver branch sets route 2 WORLD_SOURCE '
+                '(sourceReady; travel=reflectedReceiver.travel=final reflectedHit.a), 3 KNOWN_UNREADY '
+                '(known; travel=reflectedReceiver.travel) or 4 UNKNOWN (travel 0).',
+                'Non-finite SSR result entering neither branch: route 4 UNKNOWN, travel 0.',
+                'fresnel is the shader value used by the existing mix; waterMask=1 for every underwater water record.'],
+            second_trace=False),
+        final_preview=dict(
+            uniform='aqualumenPairedView', property='uniform.int.aqualumenPairedView=0',
+            beauty_when='aqualumenPairedView==0', sampler='colortex12 stays active through the preview branch',
+            observer_requirement='Query the active int uniform in the FINAL program and require 0 at capture; '
+                                 'a link default is not evidence.'),
+        qualifications=[
+            'Wave phase: both variants assign time=17.0 at the entry of shaders/lib/waves.glsl waveSurfaceLocal, '
+            'the single shared spectrum evaluator. waveSurface, localWaveState, waveState, waveStateFiltered and '
+            'waveNormal delegate to it, so water vertex displacement, water fragment optical normals, receiver '
+            'interface geometry and caustics share the 17.0 s phase.',
+            'The real frameTimeCounter uniform declaration is unchanged and live: clouds/lighting, shore foam noise '
+            'and other non-wave time uses remain real time, and ReceiverLightingState.capture keeps the active '
+            'uniform. Clouds are not frozen.',
+            'Interaction ripples: both variants return vec3(0.0) unconditionally at rippleState entry. '
+            'aqualumenActive/aqualumenRippleA may become inactive where only rippleState used them. The contact '
+            'simulation and compute passes still run and are neither frozen nor validated.',
+            'Production shaders/ and dist/ are unchanged; only the new output directory is written; nothing is installed.',
+            'Daylight and camera control are outside this generator; the parent-owned observer restricts them to the V2 UUID.',
+            'Control has the identical wave/ripple qualification and no C12 store, sampler, selector, format, clear or blend line.'],
+        attribution_limitations=[
+            'FINAL tone maps C0 at the centre and four neighbours and adaptively mixes them; texture filtering '
+            'footprints may add contributors. One final beauty pixel mixes multiple C0 source pixels.',
+            'Full-resolution C12 records the last surviving gbuffers_water fragment at each source pixel: a source '
+            'record, not sole provenance of the final colour.',
+            'Discarded fragments leave earlier C0/C12 contributors untouched. Nonwater translucent fragments blend '
+            'into C0 but reset the surviving C12 record to zero (C12 blending off).',
+            'The route reports the reflection branch actually invoked, not why other models were unsupported.'],
+        observer_requirements_unverified=[
+            'FINAL has an active colortex12 sampler and an active int aqualumenPairedView equal to 0 at capture.',
+            'Read the actual bound C12 texture with glGetTexImage before the FINAL quad and the final output after '
+            'that same quad; RGBA32F, viewport-sized; reject partial or mismatched captures.',
+            'Pin the pack SHA256 to variants.paired.sha256 and the world to the V2 UUID.'],
+        verification=dict(
+            input_sha256_matched_expected=True, strict_source_anchors_matched=True,
+            archives_read_back_matched=True, glsl_compiled=False, native_c0_invariance_tested=False,
+            iris_loaded=False, minecraft_capture=False, observer_present=False,
+            physical_acceptance=False, shader_fix_claim=False, performance_claim=False),
+    )
+
+
+def generate(root: Path, out_dir: Path, expected_hashes: dict[str, str]) -> dict:
+    """Write control.zip, paired.zip and manifest.json into a NEW out_dir."""
+    root = Path(root).absolute()
+    destination = _destination(root, out_dir)
+    expected = _expected(expected_hashes)
+    files = _snapshot(root)
+    actual = {name: _sha(data) for name, data in files.items()}
+    if set(actual) != set(expected):
+        raise SourceShapeError(f'Input key set differs; missing {sorted(set(expected) - set(actual))}, '
+                               f'unexpected {sorted(set(actual) - set(expected))}')
+    differing = sorted(name for name in actual if actual[name] != expected[name])
+    if differing:
+        raise SourceShapeError('SHA256 mismatch: ' + ', '.join(differing))
+    variants = {variant: _transform(files, variant) for variant in VARIANTS}
+    archives = {variant: _zip(variants[variant]) for variant in VARIANTS}
+    destination.mkdir()
+    for variant in VARIANTS:
+        _write_new(destination / f'{variant}.zip', archives[variant])
+    for variant in VARIANTS:
+        if _sha((destination / f'{variant}.zip').read_bytes()) != _sha(archives[variant]):
+            raise RuntimeError(f'{variant}.zip read-back differs; partial evidence kept')
+    manifest = _manifest(files, variants, archives)
+    _write_new(destination / 'manifest.json',
+               (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
+    return manifest
+
+
+def main(argv=None):
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--root', type=Path, required=True)
+    parser.add_argument('--out', type=Path, required=True)
+    parser.add_argument('--expected-hashes', type=Path, required=True,
+                        help='JSON object {archive path: sha256} for every shaders/ file plus LICENSE')
+    args = parser.parse_args(argv)
+    try:
+        if args.expected_hashes.stat().st_size > MAX_BYTES:
+            raise ValueError('Oversized expected-hashes file')
+        expected = json.loads(args.expected_hashes.read_text(encoding='utf-8'))
+        manifest = generate(args.root, args.out, expected)
+    except (OSError, ValueError, SourceShapeError, RuntimeError) as failure:
+        parser.exit(1, f'Rejected paired water TEST pack: {type(failure).__name__}: {failure}\n')
+    print(json.dumps(dict(out=str(args.out), **{f'{variant}.zip': manifest['variants'][variant]['sha256']
+                                                for variant in VARIANTS}), sort_keys=True))
+
+
+if __name__ == '__main__':
+    main()
*** Add File: tools/test_water_paired_diagnostic.py
+"""CPU-only tests for the paired water TEST pack generator; not GPU or Iris tests."""
+import contextlib
+import hashlib
+import io
+import json
+import os
+from pathlib import Path
+import re
+import shutil
+import sys
+import tempfile
+import unittest
+from zipfile import ZipFile
+
+ROOT = Path(__file__).resolve().parents[1]
+sys.path.insert(0, str(ROOT / 'tools'))
+import water_paired_diagnostic as wpd  # noqa: E402
+
+ASSIGNMENT = re.compile(r'([A-Za-z_]\w*(?:\[\d+\])?)\s*=(?!=)')
+
+
+def read_tree(root):
+    root = Path(root)
+    paths = [path for path in (root / 'shaders').rglob('*') if path.is_file()] + [root / 'LICENSE']
+    return {path.relative_to(root).as_posix(): path.read_bytes() for path in paths}
+
+
+def pins(root):
+    return {name: hashlib.sha256(data).hexdigest() for name, data in read_tree(root).items()}
+
+
+def snapshot(directory):
+    root = Path(directory) / 'src'
+    shutil.copytree(ROOT / 'shaders', root / 'shaders', symlinks=True)
+    shutil.copyfile(ROOT / 'LICENSE', root / 'LICENSE')
+    return root
+
+
+def mutate(root, name, old, new):
+    path = root / name
+    data = path.read_bytes()
+    if old not in data:
+        raise AssertionError(f'Mutation anchor absent in {name}')
+    path.write_bytes(data.replace(old, new, 1))
+
+
+def added_lines(original, transformed):
+    """Lines of transformed that are not the in-order original subsequence."""
+    old, added, index = original.decode().splitlines(), [], 0
+    for line in transformed.decode().splitlines():
+        if index < len(old) and line == old[index]:
+            index += 1
+        else:
+            added.append(line)
+    return added if index == len(old) else None
+
+
+class PairedWaterDiagnosticTests(unittest.TestCase):
+    @classmethod
+    def setUpClass(cls):
+        cls.original = read_tree(ROOT)
+        cls.control = wpd.variant_files(ROOT, 'control')
+        cls.paired = wpd.variant_files(ROOT, 'paired')
+
+    def changed(self, files):
+        return {name for name in self.original if files[name] != self.original[name]}
+
+    def test_member_sets_and_changed_files(self):
+        for files in (self.control, self.paired):
+            self.assertEqual(set(files), set(self.original))
+            self.assertIn('LICENSE', files)
+            self.assertTrue(all(name == 'LICENSE' or name.startswith('shaders/') for name in files))
+        self.assertEqual(self.changed(self.control), {wpd.WAVES, wpd.RIPPLES})
+        self.assertEqual(self.changed(self.paired), {wpd.WAVES, wpd.RIPPLES, wpd.WATER, wpd.FINAL,
+                                                     wpd.PREPARE, wpd.PROPERTIES})
+
+    def test_wave_override_both_variants(self):
+        for files in (self.control, self.paired):
+            waves = files[wpd.WAVES]
+            self.assertEqual(waves.count(b'time=17.0;'), 1)
+            self.assertEqual(waves.count(wpd.WAVE_ENTRY + wpd.WAVE_FREEZE), 1)
+            self.assertEqual(waves.replace(wpd.WAVE_FREEZE, b''), self.original[wpd.WAVES])
+        self.assertEqual(self.control[wpd.WAVES], self.paired[wpd.WAVES])
+
+    def test_ripple_disabled_both_variants(self):
+        for files in (self.control, self.paired):
+            ripples = files[wpd.RIPPLES]
+            self.assertIn(b'vec3 rippleState(vec2 worldXZ) {\n    return vec3(0.0);', ripples)
+            self.assertEqual(ripples.replace(wpd.RIPPLE_OFF, b''), self.original[wpd.RIPPLES])
+        self.assertEqual(self.control[wpd.RIPPLES], self.paired[wpd.RIPPLES])
+
+    def test_time_uniform_preserved(self):
+        for files in (self.control, self.paired):
+            self.assertEqual(files[wpd.UNIFORMS], self.original[wpd.UNIFORMS])
+            self.assertIn(b'uniform float frameTimeCounter;\n', files[wpd.UNIFORMS])
+            self.assertEqual(files[wpd.CLOUDS], self.original[wpd.CLOUDS])
+            self.assertIn(b'frameTimeCounter', files[wpd.CLOUDS])
+            self.assertIn(b'localWaveState(absolutePosition.xz,frameTimeCounter,', files[wpd.WATER])
+            for data in files.values():
+                self.assertIsNone(wpd.TIME_OVERRIDE.search(data))
+
+    def test_no_plant_defines(self):
+        for files in (self.control, self.paired):
+            for name, data in files.items():
+                self.assertIsNone(wpd.PLANT_DEFINE.search(data), name)
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            mutate(root, 'shaders/lib/settings.glsl', b'#define AQUALUMEN_SETTINGS\n',
+                   b'#define AQUALUMEN_SETTINGS\n#define AQUALUMEN_PLANT_RECEIVER\n')
+            for variant in wpd.VARIANTS:
+                with self.assertRaises(wpd.SourceShapeError):
+                    wpd.variant_files(root, variant)
+
+    def test_control_has_no_observer_stores(self):
+        for data in self.control.values():
+            for token in (b'colortex12', b'gl_FragData[1]', b'aqualumenPairedView', b'RENDERTARGETS: 0,12'):
+                self.assertNotIn(token, data)
+        self.assertEqual(self.control[wpd.WATER], self.original[wpd.WATER])
+
+    def test_paired_c12_producer_shape(self):
+        water = self.paired[wpd.WATER]
+        self.assertIn(b'/* RENDERTARGETS: 0,12 */\n', water)
+        self.assertNotIn(b'DRAWBUFFERS', water)
+        self.assertIn(b'void main() {\n    gl_FragData[1]=vec4(0.0);', water)
+        self.assertEqual(water.count(b'gl_FragData[1]'), 2)
+        self.assertLess(water.index(b'gl_FragData[1]=vec4(0.0);'), water.index(b'discard;'))
+        self.assertEqual(water.count(b'reflectionTrace(viewPos'), 1)
+        self.assertLess(water.index(wpd.WATER_SSR), water.index(b'pairedRoute=5.0'))
+        self.assertLess(water.index(b'pairedRoute=reflectedReceiver.sourceReady'),
+                        water.index(b'if (reflectedReceiver.sourceReady)'))
+        self.assertIn(b'gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);', water)
+        prepare = self.paired[wpd.PREPARE]
+        self.assertIn(b'const int colortex12Format = RGBA32F;', prepare)
+        self.assertIn(b'const bool colortex12Clear = true;', prepare)
+        clear = re.search(rb'const vec4 colortex12ClearColor = vec4\(([^)]*)\);', prepare)
+        self.assertEqual([float(part) for part in clear.group(1).split(b',')], [0.0] * 4)
+        self.assertLess(prepare.index(b'colortex12Format'), prepare.index(b'*/'))
+
+    def test_beauty_c0_untouched(self):
+        original = self.original[wpd.WATER].replace(wpd.WATER_DRAWBUFFERS, wpd.WATER_RENDERTARGETS)
+        added = added_lines(original, self.paired[wpd.WATER])
+        self.assertIsNotNone(added, 'original water source is not an in-order subsequence')
+        self.assertTrue(added)
+        for line in added:
+            code = line.split('//')[0]
+            self.assertNotIn('gl_FragData[0]', code)
+            self.assertNotIn('return', code)
+            self.assertNotIn('discard', code)
+            for target in ASSIGNMENT.findall(code):
+                self.assertIn(target, {'pairedRoute', 'pairedTravel', 'gl_FragData[1]'}, line)
+        self.assertEqual(self.paired[wpd.WATER].count(b'gl_FragData[0]'), 2)
+
+    def test_final_preview_selector_and_properties(self):
+        final = self.paired[wpd.FINAL]
+        added = added_lines(self.original[wpd.FINAL], final)
+        self.assertIsNotNone(added)
+        self.assertIn('uniform sampler2D colortex12;', added)
+        self.assertIn('uniform int aqualumenPairedView;', added)
+        lines = final.decode().splitlines()
+        assignments = [index for index, line in enumerate(lines) if 'gl_FragColor=' in line]
+        self.assertEqual(len(assignments), 2)
+        self.assertEqual(lines[assignments[1] - 1].strip(), 'if (aqualumenPairedView!=0)')
+        self.assertIn('texelFetch(colortex12', lines[assignments[1]])
+        properties = self.paired[wpd.PROPERTIES]
+        self.assertIn(b'\nblend.gbuffers_water.colortex12=off\n', properties)
+        self.assertIn(b'\nuniform.int.aqualumenPairedView=0\n', properties)
+        self.assertIn(wpd.WATER_BLEND, properties)
+
+    def test_unknown_variant(self):
+        for variant in ('', 'Paired', 'production', None):
+            with self.assertRaises(ValueError):
+                wpd.variant_files(ROOT, variant)
+
+    def test_unknown_root_shape(self):
+        with tempfile.TemporaryDirectory() as directory:
+            root = Path(directory)
+            (root / 'LICENSE').write_bytes(b'x')
+            with self.assertRaises(wpd.SourceShapeError):
+                wpd.variant_files(root, 'control')
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            (root / 'LICENSE').unlink()
+            with self.assertRaises(wpd.SourceShapeError):
+                wpd.variant_files(root, 'control')
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            os.symlink(root / 'shaders/lib/waves.glsl', root / 'shaders/lib/alias.glsl')
+            with self.assertRaises(wpd.SourceShapeError):
+                wpd.variant_files(root, 'control')
+
+    def test_missing_and_duplicate_anchors(self):
+        cases = [
+            ('wave entry shape', wpd.WAVES, b'vec3 waveSurfaceLocal(vec2 x, float time,',
+             b'vec3 waveSurfaceLocal(vec2 x,float time,', ('control', 'paired')),
+            ('wave definition duplicate', 'shaders/lib/wave_residual.glsl', b'#endif\n',
+             b'vec3 waveSurfaceLocal(vec2 x);\n#endif\n', ('control', 'paired')),
+            ('ripple guard', wpd.RIPPLES, b'if(aqualumenActive==0)', b'if(aqualumenActive<1)', ('control', 'paired')),
+            ('receiver anchor', wpd.WATER, wpd.RECEIVER_ASSIGN,
+             b'            : waterReceiverFirst(worldPosition+n*0.06,reflected);\n', ('paired',)),
+            ('final duplicate', wpd.FINAL, wpd.FINAL_SAMPLER, wpd.FINAL_SAMPLER * 2, ('paired',)),
+            ('blend missing', wpd.PROPERTIES, wpd.WATER_BLEND, b'', ('paired',)),
+        ]
+        for label, name, old, new, failing in cases:
+            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
+                root = snapshot(directory)
+                mutate(root, name, old, new)
+                for variant in wpd.VARIANTS:
+                    if variant in failing:
+                        with self.assertRaises(wpd.SourceShapeError):
+                            wpd.variant_files(root, variant)
+                    else:
+                        wpd.variant_files(root, variant)
+
+    def test_active_c12_collisions(self):
+        cases = [
+            ('C12 sampler', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */\n',
+             b'/* DRAWBUFFERS:0 */\nuniform sampler2D colortex12;\n'),
+            ('C12 target', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* RENDERTARGETS:0,12 */'),
+            ('unknown directive', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* DRAWBUFFERS:0C */'),
+            ('C12 property', wpd.PROPERTIES, wpd.WATER_BLEND, wpd.WATER_BLEND + b'size.buffer.colortex12=1 1\n'),
+            ('time constant', wpd.UNIFORMS, b'uniform float frameTimeCounter;',
+             b'uniform float frameTimeCounter;\nconst float frameTimeCounter=17.0;'),
+        ]
+        for label, name, old, new in cases:
+            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
+                root = snapshot(directory)
+                mutate(root, name, old, new)
+                for variant in wpd.VARIANTS:
+                    with self.assertRaises(wpd.SourceShapeError):
+                        wpd.variant_files(root, variant)
+
+    def test_hash_mismatch_and_key_set(self):
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            good = pins(root)
+            altered = dict(good, **{wpd.WATER: '0' * 64})
+            missing = {name: value for name, value in good.items() if name != 'LICENSE'}
+            extra = dict(good, **{'shaders/extra.glsl': '0' * 64})
+            for label, expected in (('value', altered), ('missing', missing), ('extra', extra)):
+                with self.subTest(label):
+                    out = Path(directory) / f'out-{label}'
+                    with self.assertRaises(wpd.SourceShapeError):
+                        wpd.generate(root, out, expected)
+                    self.assertFalse(out.exists())
+            mutate(root, 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* DRAWBUFFERS:0 */ ')
+            with self.assertRaises(wpd.SourceShapeError):
+                wpd.generate(root, Path(directory) / 'out-drift', good)
+            with self.assertRaises(ValueError):
+                wpd.generate(root, Path(directory) / 'out-bad', {wpd.WATER: 'not-a-hash'})
+
+    def test_deterministic_archives_across_tempdirs(self):
+        before = pins(ROOT)
+        outputs = []
+        for _ in range(2):
+            with tempfile.TemporaryDirectory() as directory:
+                out = Path(directory) / 'paired-water'
+                manifest = wpd.generate(ROOT, out, before)
+                self.assertEqual(sorted(path.name for path in out.iterdir()),
+                                 ['control.zip', 'manifest.json', 'paired.zip'])
+                outputs.append({path.name: path.read_bytes() for path in out.iterdir()})
+        self.assertEqual(outputs[0], outputs[1])
+        self.assertEqual(pins(ROOT), before)
+        for variant, expected in (('control', self.control), ('paired', self.paired)):
+            raw = outputs[0][f'{variant}.zip']
+            self.assertEqual(manifest['variants'][variant]['sha256'], hashlib.sha256(raw).hexdigest())
+            with ZipFile(io.BytesIO(raw)) as archive:
+                infos = archive.infolist()
+                self.assertEqual([info.filename for info in infos], sorted(expected))
+                self.assertTrue(all(info.date_time == wpd.ZIP_TIME for info in infos))
+                self.assertEqual({info.filename: archive.read(info) for info in infos}, expected)
+        recorded = json.loads(outputs[0]['manifest.json'])
+        self.assertEqual(recorded, manifest)
+        self.assertEqual(recorded['inputs']['sha256'], before)
+        verification = recorded['verification']
+        for claim in ('glsl_compiled', 'native_c0_invariance_tested', 'iris_loaded', 'minecraft_capture',
+                      'observer_present', 'physical_acceptance', 'shader_fix_claim', 'performance_claim'):
+            self.assertIs(verification[claim], False)
+        self.assertEqual(recorded['c12_record']['routes']['5'], 'PRODUCER_UNAVAILABLE')
+
+    def test_existing_output_refused(self):
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            out = Path(directory) / 'out'
+            out.mkdir()
+            (out / 'evidence').write_bytes(b'keep')
+            with self.assertRaises(FileExistsError):
+                wpd.generate(root, out, pins(root))
+            self.assertEqual([path.name for path in out.iterdir()], ['evidence'])
+            self.assertEqual((out / 'evidence').read_bytes(), b'keep')
+
+    def test_protected_output_refused(self):
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            (root / 'dist').mkdir()
+            alias = Path(directory) / 'alias'
+            os.symlink(root / 'dist', alias)
+            expected = pins(root)
+            for out in (root / 'dist' / 'pack', root / 'shaders' / 'diag', root / 'dist', alias / 'pack'):
+                with self.subTest(str(out)):
+                    with self.assertRaises((ValueError, FileExistsError)):
+                        wpd.generate(root, out, expected)
+            self.assertEqual(list((root / 'dist').iterdir()), [])
+            self.assertEqual(pins(root), expected)
+
+    def test_cli(self):
+        with tempfile.TemporaryDirectory() as directory:
+            root = snapshot(directory)
+            good = Path(directory) / 'pins.json'
+            good.write_text(json.dumps(pins(root)))
+            out = Path(directory) / 'out'
+            stdout = io.StringIO()
+            with contextlib.redirect_stdout(stdout):
+                wpd.main(['--root', str(root), '--out', str(out), '--expected-hashes', str(good)])
+            self.assertEqual(set(json.loads(stdout.getvalue())), {'out', 'control.zip', 'paired.zip'})
+            bad = Path(directory) / 'bad.json'
+            bad.write_text(json.dumps(dict(pins(root), LICENSE='0' * 64)))
+            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
+                wpd.main(['--root', str(root), '--out', str(Path(directory) / 'out2'),
+                          '--expected-hashes', str(bad)])
+            self.assertEqual(exit_.exception.code, 1)
+            self.assertFalse((Path(directory) / 'out2').exists())
+
+
+if __name__ == '__main__':
+    unittest.main()
*** End Patch

To run the tests: `python3 -m unittest tools/test_water_paired_diagnostic.py` from the repo root, or run the file directly. They only read the real tree (one test checks its hashes are unchanged afterwards); every edit is made in a temp copy. This is a CPU pack generator only. It makes no claim that the shader is fixed and no claim of physical acceptance. Compile/link, native C0 invariance, Iris load and the observer capture all remain with you.
