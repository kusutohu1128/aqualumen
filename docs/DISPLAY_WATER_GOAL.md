# Sun appearance and underwater sky goal

User-requested scope, 2026-10-11: improve the small, isolated-looking Sun and
the unnatural underwater sky boundary. Visual quality takes precedence over
the former 60 FPS floor. The full rendering goal remains unachieved.

The initial display-only candidate redistributes 2% of HDR radiance above a
peak-channel threshold of 8 through a normalized separable Gaussian before
the existing display transform. It leaves the angular solar disk, illumination,
water source buffers and optical transport unchanged. The filter loses energy
outside the viewport rather than repeating edge pixels. This is an artistic,
fixed-pixel glare approximation, not a calibrated lens or retinal model.

The current underwater macro-normal candidate uses the actual displaced raster
facet, rather than the original flat block normal, as the shading-normal
orientation/grazing-correction reference below a qualified upper interface.
The analytic optical normal and exact dielectric Fresnel/TIR remain in use;
this does not flatten the waves or invent sky outside the transmission domain.
Native transform feedback and passive stores compare the correction reference
against normals independently reconstructed from the actual displaced triangles,
with a nonflat sensitivity control and both top windings. This is not a natural
rim or moving-view acceptance test. Applying the same change above water failed
the retained visible-deep-bed regression; that broader v28 candidate is rejected.
The v29 candidate deliberately leaves the above-water correction unchanged and
requires a fresh full native check plus actual Minecraft inspection before use.

The [v29 runtime checkpoint](../reports/2026-10-11-display-water/receiver-partial-macro-v29/README.md)
now records those checks: full native suite, real partial/cap publication and
water-draw binding, 68 native PNGs, and exact normal-environment restoration.
The actually viewed moving frame still has a fragmented rim and broad dark
exterior. This candidate is not visually accepted, and its one-source runtime
does not demonstrate multiple-face session reuse or reduced producer cost.

The underwater work must retain Snell refraction and total internal reflection.
Diagnose missing reflected receivers, fallback radiance, interface normals and
temporal stability independently; do not replace total internal reflection with
invented sky. Existing experiments and dirty work must remain intact.

Acceptance requires NVIDIA shader checks, retained regressions, actual Iris
activation without fallback, before/after natural daylight and sunset images,
and moving underwater views with both open water and nearby geometry. Record
actual timings separately. Preserve ordinary saves/settings and install only
into Aqualumen Lab. No visual acceptance or runtime installation is claimed
for this initial candidate.

Build without overwriting the retained 0.8.6 package:

```sh
python3 tools/build.py --output dist/Aqualumen-DisplayWater-2026-10-11.zip
```

The native glare fixture runs both actual production postprocess stages and
checks an independent double-precision convolution for zero/dim inputs, the
264984 HDR solar peak, RGB ratios, zero blue-channel preservation and a corner
source. Interior radiance is conserved; outside-viewport energy is discarded.
These fixture results do not establish resolution-independent glare appearance
or a natural underwater correction. The fixed-pixel kernel and 2% redistribution
remain candidates for actual-image evaluation, not accepted appearance choices.

The first actual 12-image Iris comparison is saved in
`reports/2026-10-11-display-water/`. It confirms activation, not goal completion:
the dark underwater exterior remains, and glare amplifies bright rim points.
The initial video clips have coverage/scene-transition limitations. Normal
config/Mods and ordinary save bytes were restored/verified, without save rollback.
Continue causal optical diagnosis and a Sun-oriented natural capture; do not
adopt this initial glare strength merely because native checks pass.

The subsequent `reports/2026-10-11-display-water/solar-tir-v2/` packet adds a
production discriminant-span safeguard for solar pixel footprints at the
critical refraction boundary. The isolated native negative goes from1.93356e-7
false coverage to0, retaining a positive Sun and a deliberately unguarded
negative control. All retained native regressions pass. New actual images show
less conspicuous isolated rim lights, not a solved dark exterior or accepted
Sun presentation. X11 video capture still has missing regions despite fully
on-screen window bounds; framebuffer capture remains required. Normal configs,
Mods, instance.cfg and ordinary save bytes are verified preserved/restored.

Native framebuffer sequence support is now implemented in the experimental
benchmark source. It is off by default (`capture_motion=true` opts in), restricted
to the dedicated V2 world, limited to 10 requests/s and 80 frames/scene, and waits
for each Minecraft screenshot writer callback before advancing. Each sequence
records actual render-tail elapsed nanoseconds and rendered camera yaw/pitch;
PNG acquisition is not a clean performance benchmark. The new
`underwater-up-moving` pose rotates at 12 degrees/s during sampling at the approved
deep eye position, without changing terrain. Unit tests and the experimental
benchmark build passed; actual framebuffer sequences and motion review remain
unverified. Existing runtime packets must not be overwritten or mistaken for
evidence from this new capture path.

The TEST-only `ssr-diagnostic-v4` actual packet confirms production SSR misses
in the full-reflection exterior of the approved upward views. A candidate shader
join now consults the existing bounded homogeneous-water world receiver only
on an underwater SSR miss and only when its producer declares readiness. A
source-ready first receiver supplies its owned radiance, direct solar component
with entry/Beer correction, and its own reflected travel for Beer/scatter.
Unavailable geometry or source does not become guessed seabed color. This is
not yet a natural-image improvement: the normal bridge still has no ready
receiver producer, and positive offscreen-source tests/runtime integration remain
required. Existing screen-space hits and disabled-producer behavior are retained.

After direct Sun-oriented views in `sun-views-v5`, the next display candidate
widens the Gaussian shoulder to a standard deviation of 16 pixels at 900 pixels
vertical resolution, scaled with image height (4 pixel minimum for tiny fixtures,
32 pixel maximum). The redistribution fraction remains 2%; angular solar radius
and lighting are unchanged. This is a normalized-screen artistic approximation,
not FOV-calibrated optics. Its bounded full-pixel taps avoid sparse stride bands.
The 65, 450 and 900 square native fixtures independently check the corresponding
convolutions, color ratios, identity below threshold, interior energy and viewport
edge loss. Actual appearance and increased postprocess cost remain to be measured
before adoption. The retained v5 pack predates this wider shoulder.

The actual `wide-glare-v6` image revealed visible rectangular tail truncation
at the very high solar source. The next candidate retains the same Gaussian
standard deviation and 2% redistribution, extending its support from three to
six standard deviations. The independent CPU convolution now also bounds the
264984 HDR impulse's boundary contribution below 1e-5 before display. Existing
65/450/900 native impulse, color and energy checks pass. This does not establish
accepted real-Sun appearance or cost; the larger bounded tap count requires a
new runtime inspection, and the previous v6 package remains rejected evidence.

For the missing reflected-world producer, the installed pinned Iris JAR's public
sampler/uniform signatures are retained in
`reports/2026-10-11-display-water/iris-receiver-binding-api.txt`. Existing
`SamplerMixin.addLevelSamplers` already registers bathymetry through
`SamplerHolder.addDynamicSampler(IntSupplier,String...)`; the same installed
interface supports new named receiver textures. UniformHolder supports PER_FRAME
integer readiness and vec3/ivec3 origin/size. This verifies a usable registration
seam, not actual receiver texture upload or material/radiance readiness. Any
implementation must publish cells and paired source/direct radiance coherently,
restore GL upload state, invalidate on world/resource epoch changes, and remain
unready when first-face material/light ownership is unavailable.
