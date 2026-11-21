"""Package only shader sources, with a reproducible ZIP timestamp."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
mode=parser.add_mutually_exclusive_group()
mode.add_argument('--release', action='store_true', help='Build the normal-play pack, including when specifying a custom output')
mode.add_argument('--development', action='store_true', help='Package the separate experimental shaders tree')
mode.add_argument('--lava-preview', action='store_true', help='Build the candidate with independent area lights for lava')
mode.add_argument('--canopy-preview', action='store_true', help='Build directional diffuse sky over the area-light preview')
mode.add_argument('--ground-preview', action='store_true', help='Build nearby sunlight reflected by terrain')
mode.add_argument('--animal-preview', action='store_true', help='Build directional sky and reflected daylight for moving entities')
mode.add_argument('--ceiling-preview', action='store_true', help='Build two diffuse reflections of local lights on terrain')
mode.add_argument('--eye-preview', action='store_true', help='Build daylight exposure adaptation at windows and cave openings')
args = parser.parse_args()
previews = ((args.ground_preview, 'ground-preview'), (args.animal_preview, 'animal-preview'),
            (args.ceiling_preview, 'ceiling-preview'), (args.eye_preview, 'eye-preview'))
if any(selected for selected, _ in previews):
    from release_pack import build
    index = next(i for i, (selected, _) in enumerate(previews) if selected)
    version = 5 + index
    target = args.output or root / 'dist' / f'Aqualumen-1.9.0-preview.{version}.zip'
    layers = ['lava-preview', 'canopy-preview'] + [layer for _, layer in previews[:index+1]]
    build(target, *(root / 'release' / layer for layer in layers))
    print(target)
    raise SystemExit(0)
if args.canopy_preview:
    from release_pack import build
    target = args.output or root / 'dist' / 'Aqualumen-1.9.0-preview.4.zip'
    build(target, root / 'release' / 'lava-preview', root / 'release' / 'canopy-preview')
    print(target)
    raise SystemExit(0)
if args.lava_preview:
    from release_pack import build
    target = args.output or root / 'dist' / 'Aqualumen-1.9.0-preview.3.zip'
    build(target, root / 'release' / 'lava-preview')
    print(target)
    raise SystemExit(0)
# Existing development scripts use --output alone. A no-option build ships the release.
if args.release or (not args.development and args.output is None):
    from release_pack import build
    target = args.output or root / 'dist' / 'Aqualumen-1.8.0.zip'
    build(target)
    print(target)
    raise SystemExit(0)
target = args.output or root / 'dist' / 'Aqualumen-0.8.6.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
    for source in sorted([*(root / 'shaders').rglob('*'), root / 'LICENSE']):
        if source.is_file():
            entry = ZipInfo(source.relative_to(root).as_posix(), (2026, 10, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, source.read_bytes())
print(target)
