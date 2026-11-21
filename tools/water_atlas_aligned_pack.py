"""Reversible aligned-atlas TEST wrapper; CPU construction, never installation."""
import argparse
import json
from pathlib import Path
import tempfile
from zipfile import BadZipFile

import water_gh_phase_pack as gh

OUTPUT_ROOT = gh.ROOT / 'reports/2026-10-06-water-band-atlas/cpu-pack'
HELPER_PIN = '8c7966183672ce0006a37703f2892d8ec97db5b07943189304acbf775bcbf6b3'
PARENT_PINS = {
    0: '04b9e74db4d34d505ae3e385568cd6b720568c16df0f66809f2e664f975cfda8',
    45: '088866e780d0d86fd8b787dfd18e617a516658246b57f5fe962b2871b45ae88d',
}
MANIFEST = 'WATER-ATLAS-ALIGNED.json'
PARENT_ARCHIVE = 'ATLAS-ALIGNED-original/parent.zip'
ORIGINAL_COORDINATES = b'''    vec2 atlas=texcoord*vec2(4.0,2.0);
    ivec2 tileXY=clamp(ivec2(floor(atlas)),ivec2(0),ivec2(3,1));
    int tile=tileXY.x+4*tileXY.y;
    vec2 sourceUV=clamp(atlas-vec2(tileXY),vec2(0.0),vec2(1.0));
    ivec2 sourceSize=textureSize(colortex9,0);
    ivec2 sourcePixel=clamp(ivec2(sourceUV*vec2(sourceSize)),ivec2(0),sourceSize-ivec2(1));
'''
ALIGNED_COORDINATES = b'''    // TEST aligned-v2: zero-origin viewport, extent divisible by (4,2).
    // Integer tile-local coordinates avoid varying-UV cancellation/floor drift.
    ivec2 sourceSize=textureSize(colortex9,0);
    ivec2 outputSize=ivec2(viewWidth,viewHeight);
    ivec2 tileSize=outputSize/ivec2(4,2);
    ivec2 outputPixel=ivec2(gl_FragCoord.xy);
    ivec2 tileXY=clamp(outputPixel/tileSize,ivec2(0),ivec2(3,1));
    int tile=tileXY.x+4*tileXY.y;
    ivec2 localPixel=outputPixel-tileXY*tileSize;
    ivec2 sourcePixel=clamp(((2*localPixel+ivec2(1))*sourceSize)/(2*tileSize),
                             ivec2(0),sourceSize-ivec2(1));
    vec2 sourceUV=(vec2(sourcePixel)+vec2(0.5))/vec2(sourceSize);
'''


def source_pixel(x, y, width, height):
    """CPU integer address reference for qualified full-size C9 extents only."""
    if (any(type(v) is not int for v in (x, y, width, height))
            or (width, height) not in ((1600, 900), (2560, 1440))
            or not 0 <= x < width or not 0 <= y < height):
        raise ValueError('Unqualified extent or output pixel')
    tw, th = width // 4, height // 2
    return ((2*(x % tw)+1)*width // (2*tw),
            (2*(y % th)+1)*height // (2*th))


def _files(parent):
    if gh.sha(gh._read(Path(gh.__file__))) != HELPER_PIN:
        raise ValueError('Frozen archive helper differs')
    phases = [phase for phase, pin in PARENT_PINS.items() if gh.sha(parent) == pin]
    if len(phases) != 1:
        raise ValueError('Unapproved frozen diagnostic parent ZIP')
    phase = phases[0]
    files = gh._archive(parent)
    inherited = json.loads(files[gh.MANIFEST])
    if inherited['role'] != 'diagnostic' or inherited['phase_degrees'] != phase:
        raise ValueError('Parent role or phase differs')
    original = files[gh.FINAL]
    files[gh.FINAL] = gh._one(original, ORIGINAL_COORDINATES, ALIGNED_COORDINATES)
    metadata = dict(
        schema='aqualumen-water-atlas-aligned-v2', test_only=True, not_shipping=True,
        phase_degrees=phase, parent_pack_sha256=gh.sha(parent),
        parent_archive_member=PARENT_ARCHIVE, changed_existing_members=[gh.FINAL],
        original_FINAL_sha256=gh.sha(original), current_FINAL_sha256=gh.sha(files[gh.FINAL]),
        inherited_manifest=gh.MANIFEST,
        inherited_manifest_scope='Unchanged historical parent descriptor, not current FINAL authority',
        integer_address_policy='floor((2*localPixel+1)*sourceSize/(2*tileSize))',
        C0_display_coordinate_changed=True, C0_buffer_and_MAIN_unchanged=True,
        C0_display_policy='Unchanged AA/exposure/tone/gamma arithmetic at selected texel-center UV',
        physical_band_fix_claim=False, all_other_parent_members_byte_identical=True,
        exact_parent_ZIP_recovery=True, CPU_only=True, GL_accepted=False,
        Iris_accepted=False, visual_accepted=False, shipping_accepted=False,
        runtime_requirements=dict(
            zero_origin_viewport=True, viewport_extent_equals_view_uniforms=True,
            supported_extents=[[1600, 900], [2560, 1440]],
            seven_active_distinct_RGBA32F_same_full_extent_bindings=True,
            new_filename_requires_new_runtime_qualifier=True,
            original_16_point_qualification_and_minimum_4_Sun_gate_not_waived=True,
            same_invocation_band_pixel_raw_readback_still_required=True),
    )
    files[PARENT_ARCHIVE] = parent
    files[MANIFEST] = (json.dumps(metadata, indent=2, sort_keys=True) + '\n').encode()
    return files, metadata


def _destination(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError('Destination exists')
    if path.resolve() != path or path.suffix != '.zip':
        raise ValueError('Aliased or non-ZIP destination')
    scratch = Path(tempfile.gettempdir()).resolve()
    allowed = path.is_relative_to(OUTPUT_ROOT) or (
        scratch.is_relative_to(Path('/tmp')) and path.is_relative_to(scratch))
    if (path.is_relative_to(gh.ROOT) and not path.is_relative_to(OUTPUT_ROOT)) or not allowed:
        raise ValueError('Output outside NEW aligned-atlas CPU subtree or /tmp')
    return path


def build_pack(parent_path, output_path):
    destination = _destination(output_path)
    files, metadata = _files(gh._read(parent_path))
    phase = metadata['phase_degrees']
    if destination.name != f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip':
        raise ValueError('Dedicated aligned TEST filename required')
    raw = gh._zip(files)
    gh._publish(raw, destination)
    return dict(pack_sha256=gh.sha(raw), **metadata)


def recover_pack(candidate, output_path):
    destination = _destination(output_path)
    files = gh._archive(gh._read(candidate))
    parent = files[PARENT_ARCHIVE]
    expected, _ = _files(parent)
    if files != expected:
        raise ValueError('Source, metadata or unchanged member tampering')
    gh._publish(parent, destination)
    return dict(recovered_parent_sha256=gh.sha(parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--parent', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    recover = commands.add_parser('recover')
    recover.add_argument('--candidate', type=Path, required=True)
    recover.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (build_pack(args.parent, args.output) if args.command == 'build'
                  else recover_pack(args.candidate, args.output))
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, UnicodeError, RuntimeError) as failure:
        parser.exit(1, 'Rejected aligned atlas TEST pack: ' + type(failure).__name__ + ': ' + str(failure) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
