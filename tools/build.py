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
mode.add_argument('--idle-preview', action='store_true', help='Stage the single-program lava-idle candidate')
mode.add_argument('--face-preview', action='store_true', help='Build the face-tiled two-bounce lighting preview')
mode.add_argument('--leaf-return-preview', action='store_true', help='Build local lamp reflections from foliage onto terrain')
mode.add_argument('--torch-umbra-preview', action='store_true', help='Build the finite-source shadow optimization over the foliage reflection preview')
mode.add_argument('--visible-terrain-preview', action='store_true', help='Build smooth hand-light shadows and shade the frontmost lamp-lit terrain')
mode.add_argument('--wet-plane-study', action='store_true', help='Use the measured plane direction for wet horizontal terrain on preview 13')
mode.add_argument('--placed-penumbra-study', action='store_true', help='Build the world-space finite-area shadows for placed torches')
mode.add_argument('--placed-penumbra-animal-study', action='store_true', help='Combine placed torch penumbras with moving entity shadows')
mode.add_argument('--placed-shadow-union-study', action='store_true', help='Combine two opaque silhouettes on the same placed torch')
mode.add_argument('--torch-shadow-contours', action='store_true', help='Build the grazing-angle correction for placed torch shadows')
mode.add_argument('--torch-shadow-motion', action='store_true', help='Resolve motion across partial placed-light shadows with a fixed 24-point disk')
mode.add_argument('--torch-shadow-geometry', action='store_true', help='Find the opaque blocks between the receiver and the full torch disk')
mode.add_argument('--torch-shadow-rows', action='store_true', help='Restrict torch blocker searches to rows crossed by the finite light beam')
mode.add_argument('--diffuse-display', action='store_true', help='Build the optional midtone display study over row-scanned torch shadows')
mode.add_argument('--stained-panes', action='store_true', help='Build the optional shader with coloured light through connected stained glass panes')
mode.add_argument('--sunlit-panes', action='store_true', help='Build the optional shader with direct sunlight filtered by nearby stained glass panes')
mode.add_argument('--pane-beam', action='store_true', help='Build the window lighting study with a shared box for torch disk samples')
mode.add_argument('--window-cells', action='store_true', help='Build the placed torch window study with cached pane geometry')
mode.add_argument('--window-routing', action='store_true', help='Select the ordinary or stained pane lighting program at draw time')
mode.add_argument('--window-tiles', action='store_true', help='Select the stained pane lighting program for individual screen regions')
mode.add_argument('--camera-glass', action='store_true', help='Use the optical thickness of stained panes when looking through them')
mode.add_argument('--glass-view-pass', action='store_true', help='Filter the opaque view through stained panes after both lighting draws')
args = parser.parse_args()
previews = ((args.ground_preview, 'ground-preview'), (args.animal_preview, 'animal-preview'),
            (args.ceiling_preview, 'ceiling-preview'), (args.eye_preview, 'eye-preview'))
camera_glass = args.camera_glass or args.glass_view_pass
window_tiles = args.window_tiles or camera_glass
window_routing = args.window_routing or window_tiles
solar_panes = args.sunlit_panes or args.pane_beam or args.window_cells or window_routing
pane_layers = args.stained_panes or solar_panes
display_layers = args.diffuse_display or pane_layers
row_layers = args.torch_shadow_rows or display_layers
geometry_layers = args.torch_shadow_geometry or row_layers
contour_layers = args.torch_shadow_contours or args.torch_shadow_motion or geometry_layers
two_box_layers = args.placed_shadow_union_study or contour_layers
animal_penumbra_layers = args.placed_penumbra_animal_study or two_box_layers
placed_layers = args.placed_penumbra_study or animal_penumbra_layers
visible_layers = args.visible_terrain_preview or args.wet_plane_study or placed_layers
umbra_layers = args.torch_umbra_preview or visible_layers
face_layers = args.face_preview or args.leaf_return_preview or umbra_layers
if args.idle_preview or face_layers or any(selected for selected, _ in previews):
    from release_pack import build
    # The two lighting experiments are independent children of preview 8.
    index = next((i for i, (selected, _) in enumerate(previews) if selected), len(previews)-1)
    layers = ['lava-preview', 'canopy-preview'] + [layer for _, layer in previews[:index+1]]
    if args.idle_preview:
        version = 9
        layers.append('idle-preview')
    elif face_layers:
        version = 10
        layers.append('face-tiles')
        if args.leaf_return_preview or umbra_layers:
            version = 11
            layers.append('leaf-return')
        if umbra_layers:
            version = 12
            layers.append('torch-umbra')
        if visible_layers:
            version = 13
            layers.append('visible-terrain')
    else:
        version = 5 + index
    directory = root / 'build' / 'lava-idle' if args.idle_preview else root / 'dist'
    name = f'Aqualumen-1.9.0-preview.{version}.zip'
    if args.wet_plane_study or placed_layers:
        layers.append('wet-plane-study')
        name = 'Aqualumen-Wet-Plane-Study.zip'
    if placed_layers:
        layers.append('placed-penumbra-study')
        name = 'Aqualumen-Placed-Penumbra-Study.zip'
    if animal_penumbra_layers:
        layers.append('placed-penumbra-animal-study')
        name = 'Aqualumen-Placed-Penumbra-Animal-Study.zip'
    if two_box_layers:
        layers.append('placed-shadow-union-study')
        name = 'Aqualumen-Placed-Torch-Shadows.zip'
    if contour_layers:
        layers.append('torch-shadow-contours')
        name = 'Aqualumen-Torch-Shadow-Contours.zip'
    if args.torch_shadow_motion:
        layers.append('torch-shadow-motion')
        name = 'Aqualumen-Torch-Shadow-Motion.zip'
    if geometry_layers:
        layers.append('torch-shadow-geometry')
        name = 'Aqualumen-Torch-Shadow-Geometry.zip'
    if row_layers:
        layers.append('torch-shadow-rows')
        name = 'Aqualumen-Torch-Shadow-Rows.zip'
    if display_layers:
        layers.append('diffuse-display')
        name = 'Aqualumen-Diffuse-Display.zip'
    if pane_layers:
        layers.append('stained-panes')
        name = 'Aqualumen-Stained-Panes.zip'
    if solar_panes:
        layers.append('sunlit-panes')
        name = 'Aqualumen-Sunlit-Panes.zip'
    if args.pane_beam:
        layers.append('pane-beam')
        name = 'Aqualumen-Pane-Beam.zip'
    if args.window_cells or window_routing:
        layers.append('window-cells')
        name = 'Aqualumen-Window-Cells.zip'
    if window_routing:
        layers.append('window-routing')
        name = 'Aqualumen-Window-Routing.zip'
    if window_tiles:
        layers.append('window-tiles')
        name = 'Aqualumen-Window-Tiles.zip'
    if camera_glass:
        layers.append('camera-glass')
        name = 'Aqualumen-Camera-Glass.zip'
    if args.glass_view_pass:
        layers.append('glass-view-pass')
        name = 'Aqualumen-Glass-View-Pass.zip'
    target = args.output or directory / name
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
