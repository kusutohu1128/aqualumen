# Opaque receiver geometry candidate (not enabled)

## Live compressed runtime checkpoint: not adopted

The [v42 runtime](../reports/2026-10-11-display-water/receiver-live-runs-v42/README.md)
wires 87x36x87 compressed intake, owned sources, fresh final audit, six-table
publication and actual shader mode/count/texture checks into the experimental
bridge. Minecraft bound about 55k records and 6.7k ready sources. However,
producer samples exceed one second, and the benchmark aborted with too few
frame intervals before completing the static scene. Partial frame-003 was
viewed; dark exterior patches remain. This is not adopted appearance or speed.
The failure is preserved; normal settings, Mods and ordinary save hashes were
restored exactly. Earlier candidate sections describe intermediate test scope,
not additional evidence that this failed broad runtime passed.

## Lossless column-run layout candidate

`ReceiverRunLayout` is the first geometry-layout stage for wider coverage. It
merges exactly equal full-water, unknown or explicitly source-ineligible solid
cells along Y. Every source-eligible opaque, partial-interface and upper-crest
cell remains its own record. Unknown spans
are retained, not skipped, and opaque source addresses retain the original
dense cell identity. Thus compression cannot jump over vegetation/cutout
unknowns or combine two first-hit surfaces merely because their material agrees.

A supplied 95x36x95 CPU fixture reconstructs all 324900 cells exactly from
63175 run records, below the 65536-record table limit. Column headers and range
metadata consume additional space; the run-count ratio is not a total-byte or
speedup claim. Fragmented data exceeding capacity rejects rather than dropping
cells. The fixture also checks two adjacent opaque addresses, interrupted water,
interface metadata, nonfinite data and defensive array ownership.

Source-ineligible solid runs retain known first-hit geometry and an explicit
absent source address. The DDA cannot borrow radiance even if their packed
channels are forged ready. CPU tests retain buried solids while preserving the
exposed floor's separate source address; GPU tests stop at a merged unlit solid
before the farther red floor.

NVIDIA GPU lookup reconstructs every supplied cell and opaque source address
exactly, with fractional/count/range/nonopaque-source/nonfinite/unsupported/
disabled/extent negatives. The DDA now has an opt-in run-mode branch using the
same first-hit rules and packed record coordinates for source/Sun/face tables.
Mode zero retains the dense representation and its capacity guards. Existing
supplied dense-ray regressions still pass; these do not qualify compressed-ray
transport or production Minecraft integration.

The subsequent supplied NVIDIA compressed-DDA test reaches a red floor more
than 30m horizontally from its origin, beyond the former 16-cell half-window.
Point, travel and Beer extinction match independent expectations. Missing total
or direct source readiness, opposite face ownership, an intervening unknown
span, dense-mode misuse and a path exceeding 48m reject the reflection. This
proves the shipping DDA's opt-in compressed branch on supplied textures, not
actual source shading, Minecraft publication or visual acceptance.

`ReceiverRunRadiance` now packs total/Sun/face tables by opaque run record,
checking each supplied source's dense-cell address and world/frame/resource
epoch. Dense and compressed tables share radiance/face validation rules.
Unavailable sources remain unavailable; padding and nonopaque runs cannot own
ready source data. CPU fixtures check pairing, stale/reordered ownership,
nonfinite data and defensive copies. This packer does not itself establish the
geometry capture's freshness or validate live Sodium inputs.

`ReceiverRunPublisher` adds six-table transactional GPU publication. The
radiance pack must own the exact immutable layout object and agree with its
window dimensions and current epoch. Geometry/source/Sun/faces plus headers and
ranges become ready only after every allocation succeeds; a partial failure
deletes pending allocations and leaves no ready old publication. Replacement
and close release the previously owned allocations.

NVIDIA native Java tests read back all six uploaded tables exactly. An injected
failure before the sixth upload confirms partial-allocation cleanup and active
texture/unpack/PBO restoration; expiry, replacement and idempotent close also
pass. These are controlled-context tests, not Minecraft sampler binding or
live-world freshness acceptance. At that checkpoint the bridge used the dense publisher.

The compressed `ReceiverDrawBinding.open` overload now binds all six resources,
camera-relative origin, full window size, run mode and record count through a
tested GL-only binding core. NVIDIA tests verify actual sampler and uniform
readback, exact prior-state restoration, program-owner rejection, sampler-unit
alias rejection and incompatible comparison-sampler rejection. They do not
render an actual Minecraft draw. The v47 Mod builds but is not installed, and
the bridge did not yet capture or publish a live compressed field at that checkpoint.

`ReceiverRunSourceCapture` composes the layout and exposed-top sources through
the existing world/source boundary, then discards collection caches and rereads
every geometry cell before returning a publication candidate. Eligible floor
block identities are also rechecked. Missing sources remain unavailable; edit,
height-drift, unload and reordered batch fixtures reject. This is CPU composition,
not actual wide-field intake: live cache capacity and bridge scheduling still
need integration and performance validation.

The loaded-world adapter now accepts an explicit per-capture cache capacity;
the dense path keeps its existing 131072 default. Wide composition derives a
bounded capacity from window extent plus qualification-neighbor margins:
95x36x95 uses 411642 entries per cell-keyed cache, with a global maximum of
1048576. Allocation remains lazy. A CPU test fills 324900 distinct keys and
verifies the final audit discards collection values and rereads changed data.
This prevents the known narrow-cache capacity failure; it is not a memory or
speed acceptance result. The v48 artifact builds but is not installed, and the
live bridge did not yet schedule wide compressed captures at that checkpoint.

The codec was subsequently integrated in v42, with failed runtime timing. It still reads every
supplied geometry cell, and does not qualify epochs, source lighting or
loaded-world freshness itself. Live capture, transactional uploads and actual
Minecraft compressed reflected-ray coverage must be integrated and tested before widening
the current runtime field. No speed or natural appearance acceptance is claimed.

## API metadata reuse candidate

Owned Sodium meshing now reuses resolved Java constructors and methods in a
bounded metadata-only cache. Keys contain declaring/runtime classes, method
name, static status and argument types, never world, block, mesh or draw objects.
The original primitive/null matching and ambiguous-method rejection are
retained. All frame/world/resource/thread checks and per-face meshing remain;
this does not introduce stale geometry or cross-frame lighting reuse.

CPU fixtures verify repeated lookup identity, invocation, primitive/null/static
negatives, ambiguity and bounded extent. The v46 artifact is built but not
installed. Any actual timing benefit is unmeasured. Wider receiver coverage still
requires a structural change; metadata reuse alone does not repair field exits.

## Dynamic interface entry candidate

`tools/build_receiver_diagnostic.py` creates an opt-in diagnostic ZIP from an
existing pack, changing only the water fragment stage. It refuses overwritten
targets and missing/duplicate source anchors. Pure-TIR pixels show green for a
world receiver with paired source readiness, yellow for known geometry without
its source, blue for a screen-space reflection hit, red for a world trace miss
with a bound field, and magenta when no field trace was attempted. Non-TIR
pixels are gray. Subsequent compositing may alter displayed colors; this is a
path-outcome observer, not raw receiver RGB or accepted appearance. It preserves
the shipping source and does not certify why a world trace rejected a ray.

The optional `--rejections` builder mode additionally instruments the pinned
v33 receiver library. Its hash and return count are checked before assigning
labels. Interface rejection is separated without changing short-circuit order:
cyan means a segment failed the below-both-triangulations test, yellow means
corner reconstruction was unavailable, red means field exit, orange means the
48m bound, blue means unknown cell type, magenta means outside-field origin or
disabled interface entry, and white groups other failures. A ready world source
remains green. These labels are diagnostics, not permission to skip unknown air
or opaque geometry. Supplied NVIDIA path regressions pass for the instrumented
library, but they do not replace actual runtime or color-interpretation review.

The subsequent v34 underwater optical-normal candidate used the actual raster
facet for resolved slopes plus the detail-1 minus detail-0 spectral residual.
Actual moving frame-015 showed prominent triangle seams while the folded rim
and dark exterior remained. This candidate was rejected and its optical-normal
changes reverted; its pack and runtime evidence are preserved. Matching the
piecewise-flat facet alone does not establish a visually coherent interface or
residual-normal distribution integration.

The water vertex stage and receiver corner reconstruction now share
`water_geometry.glsl`. Underwater upper-surface reflection may traverse a
qualified partial cell only when its whole ray interval lies below both possible
quad triangulations, including crossings of either diagonal. Unknown corners,
nonfinite heights and intervals crossing air still reject the receiver. The
above-water path retains the earlier conservative envelope.

The producer additionally qualifies an upper crest cell only above loaded air
with a qualified partial-water cell immediately below it. This kind-5 cell owns
no radiance and is usable only through the dynamic interface check; it does not
turn ordinary air into full water. Final validation rereads this qualification.

NVIDIA supplied-input tests cover near-interface and upper-crest Beer paths,
both-diagonal saddle rejection, missing corner ownership and air crossings.
The production backface fixture remains green with zero front/back vertex
position difference. These checks do not establish live Sodium corner ownership
or natural-scene receiver hits. The v45 physics artifact is built but not
installed; Minecraft appearance and timing acceptance remain open.

## Capture-phase cache checkpoint

The [v32 checkpoint](../reports/2026-10-11-display-water/receiver-phase-cache-v32/README.md)
adds bounded, thread-owned within-capture memoization, with an explicit cache
discard before the final geometry audit. Collection data cannot satisfy that
audit. Validation shares only fresh reads within its own phase; close prevents
cross-capture reuse. CPU tests reject an edit concealed by the collection cache,
height drift, wrong batch ownership, and cache extent/thread/closed-owner misuse.

Actual publication retains 1009 sources and 2178 partial/cap cells with six
matching water-draw receipts. Periodic post-initial producer wall samples are
about 136-154ms, still far too high for adoption. The viewed image still has
a broken boundary and dark exterior. Live block-edit/unload/reload acceptance,
actual interface entry and the full appearance/performance goal remain open.

## Wide batched runtime checkpoint

The [v31 actual runtime checkpoint](../reports/2026-10-11-display-water/receiver-wide-batch-v31/README.md)
now verifies 33x36x33 publication with 1009 owned sources, 2178 partial/cap
cells, 12 section copies and one GPU source draw per recorded capture. Private
Sodium state is reused within the field only; grouping by section does not alter
result ownership order. The raw uploader now admits source widths up to 4096
while retaining its 65536-texel bound; field bounds still have their own 64-cell
axis limit. Native 65/4096-wide readback/restoration and oversize negatives pass.
The earlier v30 uploader-width crash is retained as rejected evidence, not hidden.

Actual steady periodic producer samples are about 215-223ms; this is not an
accepted budget. The viewed moving image still has a broken window rim and dark
exterior. Actual interface entry, receiver-hit proof, repeated-work reduction,
normal-distribution treatment and full visual/performance acceptance remain open.
Normal settings/Mods/ordinary save hashes were verified after restoration.

## Conservative partial-water geometry checkpoint

The current candidate encodes qualified flat partial-water cells as kind 4,
with `(kind, relativeSurfaceHeight, 1, 1)`. Heights below one describe the
top cell; heights between one and two describe its immediately underlying
cap cell. Neither cell owns radiance. Exact height one and absent qualification
are invalid. Capture rechecks heights after source shading.

Qualification requires retained loaded 3-by-3 pure-water cells with identical
actual fluid heights, air above and two full water layers below. The traversal
accepts a complete segment only below the resolved spectral height bound plus
the 0.07 interaction-wave clamp and 0.002 mesh/quantization margin. This also
protects the cap layer when a thin static top layer is displaced downward.
Full-water traversal is unavailable when that margin exceeds one cell.

CPU composition and native NVIDIA reflection fixtures cover partial/cap metadata,
Beer attenuation, and rejection of near-surface, upward-crossing, malformed and
nonfinite geometry. These are not live Minecraft receiver-hit evidence. The
actual displaced interface entry, wider reflection coverage and natural-view
acceptance remain incomplete; this conservative lower envelope is not a fix for
the visible rim or permission to skip unknown geometry.

## Paired radiance volume candidate

The current owned material-source candidate gathers qualified face-center
inputs before shading, then processes up to 4096 independent points per GPU
draw. Each batch uses N-by-1 input/output textures and two paired readbacks,
refreshing the same captured current lighting and atlas state. Each point keeps
its original UV, tint, AO, lightmap and camera-relative position; derivatives
remain explicit zero-gradient point approximations, not reflection footprints.
Unavailable lanes stay paired zero while valid neighbors remain qualified.
The field builder rejects reordered or wrongly sized results even when all
material IDs match, then performs its original final geometry/height recheck.

CPU tests exercise two distinct sources, an unavailable neighbor and order/extent
negatives. The native source fixture uses distinct atlas samples with an invalid
middle UV lane and independently checks addressed RGB/readiness. These are not
actual Java batch/state-restoration or live multi-face ownership evidence.
The source-v40 experimental Mod was built but uninstalled. Its mesh contexts
were still created per face and coverage was 3-by-3. The subsequent v31 checkpoint
above supersedes those limits without establishing a fixed dark exterior or an
accepted broad-field performance budget.

The owned source program now has a field-capture-scoped session. Multiple
qualified face-center draws in the same capture reuse one linked private program,
but each draw still refreshes actual lighting uniforms and atlas/LUT bindings.
The session rejects changed world/frame/resource, source owner or fragment text,
and releases its program when capture ends, including failure paths. This is not
a cross-frame lighting cache. Owned mesh captures remain per face; broad-field performance and actual runtime
reuse/state restoration have not yet been measured for this change.

`ReceiverRadianceVolume` now owns copied, bounded sliced-2D cell/source/direct-Sun
and face arrays. Its layout matches `x + width*(y*depth+z)` in the existing GLSL
receiver traversal. Only explicit full-water, opaque, or unknown cells are
encoded; source readiness is paired with direct attribution and one axial face.
Negative/nonfinite radiance, direct exceeding total, inconsistent readiness and
out-of-window indices are rejected. World identity, exact frame and resource
epoch must match before a caller can publish it. Caller tokens do not prove that
live capture was coherent: scheduling and actual shared material/light shading
are still required. No guessed sand color or inferred full-water geometry is
introduced, and this class is not a producer or renderer-enabled bridge.

The new GLSL readiness value 2 requires the first hit's entry normal to match
its declared source face; value 1 retains the older explicit homogeneous-source
fixture contract. This prevents a top-face source from lighting a side/back face
of the same voxel. Unavailable source/face keeps the first hit unready rather
than searching through it. `bash tools/test-receiver-radiance-volume.sh` checks
owned copies, extent/layout, paired attribution, face validity and epoch changes.
The bounded native source fixture additionally checks a matching face positive
and opposite-face negative. Neither test establishes the full original water
main join or actual natural runtime source production.

`ReceiverRadiancePublisher` transactionally creates all four paired textures
before publishing readiness. Failed/stale publication exposes neither partial
new data nor previously valid source, disposes partial allocations, and retains
only owned allocations for explicit release. Fake-backend CPU tests qualify
replacement, failures, epoch expiry and repeated close. The new
`ReceiverRadianceTextureUpload` implements bounded RGBA32F allocation, verifies
actual storage dimensions/format, and restores active texture/binding plus PBO
and unpack state. It requires the render thread and compiles against the pinned
LWJGL dependencies; actual GL upload/state-restoration testing is still needed.
The publisher/upload classes alone enable no registration, world scheduler or
ready natural source. Fresh four-texture allocation is a bounded prototype, not an
accepted per-frame budget or release cache policy.

The actual LWJGL upload test now passes on NVIDIA RTX 3080 Ti / GL4.6. It queries
RGBA32F storage and reads back exact input float texels, deliberately sets
nondefault unpack/PBO/active-texture/binding state and verifies restoration,
publishes all four paired textures, rejects expired readiness and verifies
allocation release. Evidence is retained in
`reports/2026-10-11-display-water/receiver-upload-paired-gl.log`. The hidden GLFW
fixture controls its own context/thread guard; this does not verify Minecraft's
RenderSystem boundary, Iris sampler registration, natural source capture, or a
rendered reflection. Those runtime/source-owner steps remain open.

`ReceiverRadianceBridge` is now connected to the existing CommonUniforms and
Iris level-sampler mixins in the experimental source. It registers four dynamic
samplers, explicit readiness, size and camera-relative world origin, and exposes
the publisher only for a matching current world/frame/pipeline-generation token
in an active Overworld Aqualumen pipeline. Pipeline registration invalidates old
readiness. Resource-atlas/mesh-owner invalidation still needs the actual producer;
the pipeline-generation counter is not proof of every resource epoch. No caller
currently publishes natural radiance, so readiness stays zero.

The experimental `build/aqualumen-physics-0.3.0-receiver-bridge-v1.jar` compiles
against the installed pinned dependencies. Its SHA256 is
`ec3ef58baa59528395efe3cdba4ac2fb10a7b8d43d0629d2e03c581f3937fdc1`.
It is not a release: actual Iris binding/units and positive source publication
were not established by compilation. Existing physics artifacts were not
overwritten. The build script now supports an explicit new output and refuses
to overwrite an existing artifact.

The subsequent `receiver-bridge-v8` packet temporarily ran this JAR in Lab and
completed two NVIDIA/Iris upward scenes without fallback, validating the
empty-producer integration only. All 70 native sequence PNGs were checked.
Normal configs/Mods and ordinary save bytes were preserved/restored. Actual
sampler/uniform readback, positive publication and natural material/radiance
capture remain unverified; the dark exterior and rim distortion remain visible.

`ReceiverMaterialVolume` now captures bounded geometry with sparse owned top-face
inputs through `LoadedReceiverMaterialWorld`. The actual adapter uses only retained
loaded chunks, the existing vanilla face/static-sprite boundary, and a copied
center mip0 texel; it enforces the render-owner thread and rechecks block identity.
Pure water is declared full only below another pure water block. Partial surface
cells, unloaded/unsupported cells and unavailable/nonopaque material remain
unknown/unshaded. Opaque first geometry is retained even without material.

CPU fake-world tests verify layout, full-versus-partial water, no unloaded reads,
identity/opacity rejection and immutable copies. The complete experimental Mod
compiles as `build/aqualumen-physics-0.3.0-receiver-material-v3.jar`; it is not
installed. This captures raw unsmoothed face lighting/tint and one nearest mip0
texel, not Sodium AO/interpolation, atlas filtering, shaded radiance, automatic
publication or natural appearance. A bounded coherent shared-shading producer
and actual intake verification remain necessary. Partial water at the real wave
interface also needs a qualified segment policy before reflected rays can use
the full-water traversal; do not silently treat those surface cells as full.

`receiver_shading.glsl` now joins material conversion and the existing shared
`terrainLight` path. Ordinary terrain uses this same function without an extra
atlas fetch. The shared `receiver_source.glsl` stage accepts qualified
texel/tint/normal/position/lightmap-AO inputs and produces paired total/direct-Sun
RGBA32F radiance, rejecting missing readiness, mismatched extents, nonfinite or
out-of-domain inputs. NVIDIA compilation/link is verified separately from draws.
The ordinary terrain/solar native regression remains the light-consistency
check. The actual source stage is now drawn in the native GPU fixture and is
registered as Iris `prepare1`. Independent RGB checks cover tinted material,
block light, legacy-cache direct Sun, rain attenuation, shadow rejection and
skylight gating, with paired readiness and invalid-input rejection. This does
not qualify the separate clear-cache/cloud branch or Minecraft source ownership.
Current actual material intake is not qualified to invent Sodium AO or filtered
atlas/interpolation values. Those ownership/approximation choices and a positive
renderer integration still need verification before natural publication.

`ReceiverLightingState` provides the read-only GL intake for that integration.
It reads the currently linked program's typed inverse-view/shadow matrices,
camera and light positions, cloud time, rain, and distinct same-size sky/clear
LUTs plus the actual depth-comparison shadow binding. Sampler objects override
texture comparison state; undefined light directions, missing/mistyped uniforms,
nonfinite values, aliased caches and unavailable storage reject the capture.
Active texture, bindings, program and upload state are not changed. Uniform
values are owned copies, but GPU texture/sampler handles are borrowed, valid
only under the producer's same-world/frame/resource ownership boundary. An
epoch match alone does not prove those resources were not subsequently mutated.
The NVIDIA GL test verifies readback and sampler-object overrides in a controlled
context. The pinned `ExtendedShader.updateUniforms` tail now invokes intake after
Iris updates matrices, samplers, common/custom uniforms and images. The actual
`receiver-lighting-depth-v11` Lab run returned a qualified capture from program
300: distinct 1024x512 sky/clear textures on units 3/4 and a 2048x2048 comparison
shadow on unit 5 with sampler object 2. Earlier v9/v10 runs rejected Iris's valid
unsized `GL_DEPTH_COMPONENT` storage; the adapter now accepts that depth format
without relaxing comparison or color/depth resource checks. Cold-start Minecraft
intake is verified, but coherent source drawing/publication, resource reload and
appearance acceptance are not. Intake adds synchronous GL queries; the native
sequence timing includes capture overhead and does not establish clean cost.

`prepare1` follows the sky/clear LUT pass and reserves paired 16x256 RGBA32F
targets C10/C11 for total and direct-Sun radiance. Its real fragment source is
also the native positive/negative draw fixture, not a separate test surrogate.
The bridge explicitly advertises input size zero and assigns distinct sampler
units to unavailable inputs; no raw vanilla brightness is invented as Sodium
AO and no material is silently declared ready. Natural source publication is
still disabled. The native full suite now compiles 14 root program pairs.

The `receiver-prepare-bound-v13` Lab run verifies the actual source program 19,
bound FBO 12, C10/C11 attachments 66/68, both 16x256/GL_RGBA32F, with input size
0x0. Capture runs at `Program.use` tail after uniforms/samplers/images; actual
source lighting became qualified at frame 2. Frame 1 had an undefined light
direction and correctly remained unqualified. A uniform supplier's early
initialization invocation is not proof of a bound draw; v12 exposed that error
and was superseded for this evidence. No actual C10/C11 RGB readback, positive
world material publication or resource/motion coherence acceptance is claimed.

`OwnedSodiumReceiver` now constructs a separate bounded Sodium render cache and
mesh buffers on the render thread for a requested supported opaque voxel. The
3x3 neighbor columns must already be loaded before LevelSlice preparation; no
chunk requests, commands or world writes are made. The scope matches the exact
renderer/world/cell/state, copies the actual four pre-encoder vertices before
push, and accepts only one full-unit upward face with separate AO. Incomplete,
foreign, duplicate, nested or stale/thread-mismatched inputs stay unqualified.
Owned renderer/cache/native mesh buffers are released after capture, not submitted
as a terrain mesh or reused from a background worker.

The actual `receiver-owned-sodium-face-v18` run captures gravel at (448,45,-384)
in frame 2/resource generation 1. Its four AO values are 0.5999756, 0.5999756,
1.0, 1.0; packed light is 0 and vertex color is white. Raw UV/positions are
retained in the receipt. Sodium's normalFace is POS_Y, not Minecraft's UP; the
adapter now explicitly maps that name to the scope's canonical upward face.
Earlier v17 correctly retained unready input but exposed this adapter mismatch.

Material intake may inspect an opaque voxel below an unsupported seagrass voxel:
it is collecting per-cell inputs, not establishing a reflected optical path.
The water DDA still stops at unsupported geometry; no farther-floor borrowing
or guessed plant transparency is introduced. This verifies one cold-start owned
Sodium CPU face, not actual filtered atlas fetch, UV/lightmap shader decoding of
this new capture, GPU radiance output, a complete source volume, resource reload
or appearance acceptance. Do not invent skylight or AO to make this data ready.
Source input size remains zero pending those integrations.

`ReceiverField` is a pure, bounded, immutable geometry contract for the optional
read-only client bridge. It supplements—not replaces—the existing bathymetry
columns. Bathymetry cannot describe stepped first walls or camera-occluded beds.

`capture(World, Bounds)` copies at most65,536 cells, with each dimension1..64.
The caller must run on the world owner thread without concurrent world changes;
this is a synchronous prototype, **not** a per-frame update budget or cache.
Unloaded columns and out-of-build-height cells remain unknown without voxel reads.
`LoadedReceiverWorld` uses the existing retained `getChunk(FULL,false)` boundary.
No missing chunk generation, block writes, commands, Mixin registration, Iris
sampler registration, GL allocation or renderer scheduling is introduced here.

`Snapshot.firstHit(origin, unitDirection, maxMetres)` returns the first supported
opaque voxel, block registry identity, entry point/distance and entry normal.
Travel is bounded to48m. Unknown, unsupported, out-of-window, inside-solid and
ambiguous edge/corner/parallel-boundary cases are explicit non-hit statuses.
It must never search through those cells for a farther visually convenient bed.
Snapshots retain no chunk references and do not follow later world mutations.

The initial exact vanilla full-cube subset additionally requires empty fluid and
the pinned full/solid predicates. Transparent, partial, aquatic-cutout, modded
and unqualified blocks are unsupported. Pure vanilla water is traversable for
opaque geometry only: entered-water-cell count does **not** establish a continuous
water body, actual partial-fluid volume or a Beer attenuation path. Air can also
be traversed, so the geometric travel must not be assumed entirely underwater.

`HIT` means **geometry readiness only**. A registry name is not an atlas UV,
face material, tint, lighting, radiance or appearance-readiness proof. There is
intentionally no guessed sand color, screen-RGB proxy or shader hit promotion.
Actual vanilla appearance extraction, per-frame coherent snapshot lifetime,
bounded scheduling, sliced2D encoding/upload, dynamic Iris sampler assignment,
GL-state restoration and production optical joining remain required work.

At the initial geometry-only checkpoint the adapter's new registry signatures
were checked against the local pinned1.21.1 intermediary bytecode and `javac`.
The later actual-face probe below validates the loaded geometry/face reflection
boundary for its16 requested records, not a scheduled world snapshot or renderer
integration. Do not install this as a qualified release based on CPU tests.

CPU verification:

```sh
rtk proxy bash tools/test-receiver-field.sh
rtk proxy python3 tools/water_receiver_saved_replay.py --out reports/2026-10-06-water-receiver-contract-NEW
```

The replay output must not already exist. It independently decodes immutable
closed TEST terrain and checks16 actual original-MAIN refracted rays plus16
camera rays against the new Java implementation. This is saved-world CPU
evidence, not a new Minecraft/GPU run. See the v3 report and its remaining gates.

## Actual face input decoder and pinned adapter (still not enabled)

`ReceiverFace.decode` copies one actual opaque vanilla32-int quad into an
immutable face descriptor: axis/sign, atlas/sprite/UV bounds, an affine world-face
UV map, uniform unshaded vertex color, separate raw tint, shade flag, and raw
sky/block light plus the actual render-view brightness. Unsupported vertex
layouts, non-unit/partial faces, opposite winding, extra geometry, non-affine or
degenerate UV, nonfinite values, gradient/transparent vertex colors stay unready.
No guessed sand color or material radiance is produced.

`LoadedReceiverFaces.faceAt` requires the supported opaque geometry predicate and
already-loaded columns; obtains the block's actual rendering seed/model/face
quad, resetting the seed as the pinned caller does; rejects additional unculled
or multiple face quads. Tint blending additionally requires the conservative
maximum7-block surrounding columns already loaded. Adjacent-column raw light
reads remain inside build height. No command, world write, GL call, image access,
cache scheduler, sampler registration or shaded RGB calculation is added.

The [actual face evidence](../reports/2026-10-06-water-receiver-faces/README.md)
proves16 selected sand records (14 unique cell-faces, including UP/EAST/WEST)
through real Iris1.8.8/MC1.21.1 on RTX3080Ti. The original normal shader and
physics0.2 were unchanged; a standalone guarded TEST-only observer was removed
after clean exit. This includes the previously saved eight camera-hidden first
receivers, but does not assert saved/live geometry at the same fragment/frame.

Face-input readiness is not source readiness. The probe captured frame1, so
lighting warmup/stability is not proved. `vanillaBrightness` is the actual
MC render-view return value in the Iris/Sodium context (all1.0 here), not proof
of unmodified vanilla face shading or a physical lighting model. Raw light is
unsmoothed; there is no AO/per-vertex irradiance, actual texture pixel readback,
atlas epoch/reload coherence, CPU/GPU radiance convention, or water renderer
source upload yet. These must be qualified before renderer/source promotion.

The [handoff correction](../reports/2026-10-06-water-receiver-faces-handoff-addendum/README.md)
supersedes the first packet's invalid final-pause assertion without changing its
actual face records or producer. The corrected actual menu is15:36:17; the
original named pause image was gameplay and is preserved as rejected evidence.

```sh
rtk proxy bash tools/test-receiver-face.sh
rtk proxy python3 tools/test_water_receiver_faces_audit.py
```

## Actual static opaque sprite input (not renderer-enabled)

`ReceiverTexture.capture` owns copied, bounded256x256 static opaque mip0 ABGR
pixels. Sampling uses the decoded affine face UV and explicit top-first RGBA
conversion; it rejects wrong sprite identity or out-of-sprite UV. Animated,
nonopaque or unsupported shapes remain unready, not guessed colors.
`LoadedReceiverTexture` reads the actual pinned SpriteContents/NativeImage on
the render thread, never mutating or closing asset images. `materialAt` obtains
the face and texture from the same actual quad/sprite invocation. That one-shot
association is not a resource reload epoch, terrain snapshot scheduler or GPU
source lifetime proof.

The [actual texture packet](../reports/2026-10-06-water-receiver-texture/README.md)
qualifies48 warmed actual face observations and240 sparse sample checks against
independent JDK ImageIO decoding of the local stock sand PNG. Actual known-image
channel/copy-ownership controls pass. The three records are equal, including
raw light, but general temporal stability is not inferred. Native CPU nearest
mip0 pixels are not actual GPU atlas/mip filtering or source radiance. Sodium
AO/smoothed light, shared dry lighting, direct-Sun attribution, coherent bounded
geometry/material capture, Iris upload and production optical joining remain
required before shipping or claiming the two original-MAIN REDs corrected.

```sh
rtk proxy bash tools/test-receiver-texture.sh
rtk proxy python3 tools/test_water_receiver_texture_audit.py
```

## Exact first-face CPU material association (not renderer-enabled)

`ReceiverSurface.capture(geometry, stamp, surfaces)` owns a sparse catalog of
up to4096 unique cell/face owners and1048576 distinct retained texels. Existing
immutable textures can be shared; ambiguous duplicate ownership is rejected.
`firstSample(stamp, origin, direction, metres)` returns raw `PIXEL` only from
the first opaque cell's own block identity and entry normal. Missing/unready
first faces cannot borrow a farther color. All non-HIT geometry stays geometry
only. Different world/dimension/frame/atlas tokens return STALE, with no pixels.

The stamp is a caller contract, not a proved live epoch or capture scheduler.
It cannot by itself establish that saved geometry and live atlas/light data
were captured together, or survive aliased frame/revision counters. `PIXEL`
means nearest CPU input only, not filtered albedo, light, radiance or readiness
to promote a shader hit. Actual runtime capture/lighting/GPU joining is pending.

The [surface replay](../reports/2026-10-06-water-receiver-surface-v2/README.md)
uses the sealed saved-field and original16 refracted rays, later actual face
metadata and independently decoded full-digest matching stock sand texture.
All16 first-object/normal/UV pixel expectations match offline, including eight
previously hidden requests. The original water-MAIN radiance REDs remain open.

```sh
rtk proxy bash tools/test-receiver-surface.sh
rtk proxy python3 tools/test_water_receiver_surface_replay.py
```

## Actual GPU atlas input qualification (still not renderer-enabled)

`ReceiverAtlas` owns a bounded2048x2048 RGBA readback and extracts only integral,
size-matched static opaque sprite regions into immutable `ReceiverTexture`.
RGBA8 storage is accepted only with queried8-bit unsigned-normalized channels,
including the actual Minecraft unsized `GL_RGBA` format; no guessed conversion.
The TEST-only `GpuReceiverAtlas` reads the already-registered block texture on
the render thread and restores listed texture/buffer/pixel-store state. It never
loads/replaces/writes the asset; only a separately owned known GPU fixture is
allocated, mutated and deleted. No GPU-readback loop is installed in normal play.

The [actual atlas evidence](../reports/2026-10-06-water-receiver-atlas-v2/README.md)
qualifies48 whole sprite matches and48 GPU point checks against CPU NativeImage
and independent stock decoding in real Iris/NVIDIA. This raw mip0 data and
texture-object filter parameters do not qualify actual filtered/LOD shader
sampling, terrain-draw binding, live geometry/atlas epoch or source radiance.
Actual AO/smoothed light or separately qualified illumination, producer lifetime,
Iris source binding and water-MAIN integration remain required. No water fix yet.

```sh
rtk proxy bash tools/test-receiver-atlas.sh
rtk proxy python3 tools/test_water_receiver_atlas_audit.py
```

## First world-source shader candidate (normal input remains disabled)

`water_receiver.glsl` adds a bounded camera-relative sliced2D DDA and separate
total/direct-Sun homogeneous-voxel source inputs. `gbuffers_water.fsh` uses a
qualified first source without camera-proxy mixing. Known first geometry with
unready source retains its first path and an explicit unknown-source environment
fallback, never a farther material. Traversal only admits declared full water;
air/unknown/unsupported/tied/out-of-window cases remain unqualified.

The [original-MAIN packet](../reports/2026-10-06-water-receiver-main/README.md)
now corrects both prior native-v4 synthetic-source REDs on RTX3080Ti, with
unchanged whole fixture inputs, independent first/Snell/Fresnel/Beer evidence
and zero passive C0 difference. A genuine additional unready-first RED->GREEN
blocks farther borrowing. Readiness zero preserves all four whole C0/seven
observed fields exactly against the original. The existing 11-pair native suite,
absolute direct radiance and nonzero-wave first-visible-bed controls pass.

This is not actual per-face source sampling, shaded vanilla data, a live
producer/epoch, dynamic Iris binding, nonzero world-source Sun acceptance or
natural image/motion/timing proof. The input is synthetic air-lit linear RGB,
not an albedo conversion or guessed sand. Normal0.6/physics0.2 are unchanged.
Continue the packet's RESUME.md; renderer integration and full goal remain open.

## Positive world-source Sun and pinned vertex-input preparation

The [Sun/input checkpoint](../reports/2026-10-06-water-receiver-sun/README.md)
qualifies a positive paired total/direct-Sun source on the unchanged original
MAIN with NVIDIA readbacks. Red response0.00168775022 agrees with independent
two-leg Fresnel/Beer/exit-etendue0.00168774753; green/blue and passive C0 changes
are zero. Missing, unready, negative and excess paired-Sun inputs cannot promote
the qualified first hidden material. This is a flat zero-wave synthetic fixture,
not general displaced-surface/bent-shadow transport or real terrain shading.

`ReceiverVertex.capture` now owns four immutable pre-encoder inputs, preserves
already-applied tint, encodes separate8-bit AO and clamps actual packed-light
bytes8..248. Four public CPU RED->GREEN increments qualify invalid-input rejection;
tests use the installed Sodium color conversion, not mocked collaborators.
Pinned installed mesher/encoder/transformer bytecode is retained. Actual mesh
events, encoded position/UV, draw matrices/filtering, face ownership and coherent
live epochs remain uncaptured. This module does not imply source readiness.

No production shader changed in this cycle; completed native gates were retained
instead of replayed. No new pack/Mod was installed and no Minecraft frame timing
was measured. Continue guarded actual mesher/encoder observation and per-face
source integration, not homogeneous voxel RGB as a substitute for real material.

## Actual terrain mesher/encoder input observation

The [mesher checkpoint](../reports/2026-10-06-water-receiver-mesher/README.md)
adds an exact-world TEST-only read observer, not a normal producer. Actual
BlockRenderer owner/vertices join the same worker's identity-matched encoder
invocation, before mutable arrays are reused. Fourteen unique first-sand faces,
56 vertices and280 initialized output words match independent position/UV/
separate-AO/color/smoothed-light encoding in real Iris/NVIDIA. Two actual workers
are observed; AO0.39996338..1 and raw sky bytes128..192 are retained rather than
guessed. Native buffers/vertices/world are not written. Public ownership and
independent-capture negative controls pass; no shader implementation changed.

This still does not establish shader attribute interpolation, actual matrix/
filtered draw sampling, resource/geometry epoch or shaded per-face source upload.
Continue those concrete seams from its RESUME.md. The unchanged natural TEST
view still shows cyan/serrated water; visual/motion/full-goal acceptance is open.

## Actual Iris draw inputs and vertex decoding

The [draw checkpoint](../reports/2026-10-06-water-receiver-draw/README.md)
observes the actual original terrain multi-draw after its bound VAO, uniforms
and texture/sampler are ready. The unchanged linked Iris vertex source is also
run in an owned transform-feedback fixture with the archived actual14-face /
56-vertex inputs. All448 UV/lightmap/color floats match `ReceiverVertexShader`
and a separate scalar reader exactly after float32 conversion.

Important pinned convention: Iris `_vert_init` passes **raw encoded light bytes**
to `iris_LightmapTextureMatrix`, whose observed scale is1/256 and translation1/32.
Generic Sodium's pre-division by256 would double-convert these inputs. Actual
UV bias/shrink and normalized ABGR alpha are retained. The immutable public CPU
decoder rejects nonfinite uniforms and unsupported light bytes; it does not
declare missing material ready. Three incremental public-API RED->GREENs and
external capture-negative controls are retained, not represented as shader bugs.

This proves only the listed draw snapshot and eight vertex outputs. The owned
fixture has no fragment invocation, uses archived geometry without a coherent
live epoch, and does not prove per-triangle interpolation, filtered atlas fetch,
shared-light/Sun source radiance or dynamic Iris source upload. Filter metadata
is not a fetched fragment result. No production GLSL or normal release changed.
Continue the concrete renderer-source seams in its RESUME.md; full natural
shore/motion/lighting/physics acceptance remains open.

## Owned full-face triangle interpolation

The [triangle checkpoint](../reports/2026-10-06-water-receiver-triangle/README.md)
invokes the installed public Sodium CPU index generator: both index formats give
`0,1,2,2,3,0`. Pinned DefaultChunkRenderer bytecode establishes the nontranslucent
shared-index TRIANGLES path; no original live element buffer is read. Archived
actual mesher order is retained rather than re-sorting corners or inventing a
different AO diagonal.

`ReceiverTriangle.capture` owns a supported full-unit four-corner face and the
pinned local indices; its point sampler returns piecewise triangle-interpolated
UV/lightmap/color/AO and local derivatives. Unsupported diagonal, incomplete /
nonfinite geometry or attributes, and outside points do not become ready sources.
Three public API RED->GREEN increments establish the added behavior. A varying
affine UV control qualifies local gradients only, not projected screen derivatives.

A standalone NVIDIA GL4.6 fixture runs the unchanged archived actual Iris VS
with initialized actual28-byte-stride inputs and an owned pass-through fragment
shader. Sixteen saved first-receiver points and42 supplemental interior points
qualify eight interpolants under orthographic and projective transforms. All928
positive floats agree with independent barycentric evaluation; max error is
8.731773e-7. A deliberate opposite-diagonal GPU control differs by0.10196084,
showing why full-quad averaging/bilinear AO is not an interchangeable substitute.

This is not live original terrain fragment shading or filtered material fetch;
the projections and pass-through FS are diagnostic. Actual live binding/epochs,
shared lighting/Sun source, dynamic Iris upload and natural acceptance remain
required. No production shader or installed pack/Mod changes this cycle.

## Actual filtered atlas and original lighting inputs

The [continuous-update checkpoint](../reports/2026-10-11-display-water/receiver-source-updates-v27/README.md)
removes the one-shot producer gate and redundant material-only probe. Fresh
owned intake, GPU shading and transactional field upload now run once per
eligible frame, followed by draw-scoped water binding. Actual near/moving runs
logged 178 matched periodic update/binding receipts over frames 3..10620 and
validated 69 native PNGs. The small sparse field, explicit point approximation,
partial-water barriers and rim defects remain; neither a natural reflected hit
nor whole appearance/reload acceptance is established. Earlier one-shot sections
are historical checkpoints, not the current experimental scheduling path.

The [bounded publication](../reports/2026-10-11-display-water/receiver-source-volume-bound-v26/README.md)
now composes actual owned/GPU-shaded top faces with conservative full-water and
opaque geometry, rechecks geometry after shading, transactionally uploads all
four textures, and verifies a positive same-frame actual water-draw binding.
The draw-scoped update accounts for publication after ordinary per-frame uniform
updates and restores original bindings/uniforms after the draw. This remains a
one-shot sparse 3x36x3 field with one source and a face-center point approximation;
no later-frame producer, reflective ray hit, partial-water traversal, reload or
natural appearance acceptance is claimed. Earlier no-producer sections describe
historical checkpoints, not this newest experimental path.

The [shared-source GPU point](../reports/2026-10-11-display-water/receiver-source-point-compiled-v24/README.md)
now feeds the same-epoch owned face through the unchanged actual compiled
receiver fragment, current atlas/sampler and prepared lighting resources. It
read back finite paired total/direct-Sun RGB in the actual client and restored
and queried the observed draw/texture/indexed-blend/pixel-pack state. This is
an explicit point footprint, logged and discarded: no natural source volume,
water reflection publication or appearance acceptance is implied. Original
fragment derivatives, source scheduling and unsupported ray geometry remain
open. Source text is copied during ProgramCreator.create, before Iris destroys
the compiled shader objects; no detached-stage reuse is assumed.

The [terrain-input checkpoint](../reports/2026-10-11-display-water/receiver-terrain-input-v21/README.md)
now observes an actual Sodium terrain multi-draw and applies its copied current
Iris UV-shrink/lightmap matrix to a same-epoch owned encoded face. It retains
actual atlas/sampler identity and interpolates UV, tint, AO and decoded light at
the face center. Local surface derivatives are not camera/reflective footprints;
borrowed texture handles are not frozen resources. Live GPU atlas/shared shading
and paired source publication remain required.

The [owned encoder checkpoint](../reports/2026-10-11-display-water/receiver-owned-encoder-v20/README.md)
now captures the pinned Iris encoder's actual packed UV/color/light for the
dedicated Sodium face before native-buffer cleanup. Its live stride is 28;
prepared color/light agreement and native extent are checked. This advances
the material intake beyond unquantized pre-encoder UVs, but does not replace
current draw lightmap/shrink ownership or qualify GPU shaded radiance.

The current `prepare1` shared-source stage has an explicit optional GPU atlas
path: `receiverTexelMode=1`, UV input `(u,v,0,1)`, and gradient input
`(du/dx,dv/dx,du/dy,dv/dy)` feed `textureGrad`. Mode zero preserves qualified
pre-sampled inputs. Unknown modes, invalid UV/gradients and nonopaque samples
produce paired unavailable outputs. Native tests use deliberately different
base/mip colors to distinguish bilinear filtering from explicit mip selection.
These are controlled footprints, not original camera fragment derivatives.
The normal bridge still supplies no inputs and zero input size; this capability
does not qualify the captured Sodium face, publish natural radiance, or fix the
underwater view by itself. New sampler names are registered on distinct Iris
units even while disabled, avoiding sampler-type aliasing with shadow maps.

The [resource checkpoint](../reports/2026-10-06-water-receiver-light/README.md)
captures the linked actual terrain program's16 active uniforms and all seven
defined sampled2D levels for atlas/LUT/shadow in one draw. Original0.6's cached
colortex6 path is distinguished from the uninstalled candidate. Actual shadow
sampler state and all atlas mip pixels are retained; no guessed mip generation
or inactive uniform values are substituted.

Eighty owned GPU textureGrad queries use the original bound atlas and archived
first-face triangle UVs decoded with the current draw's matrix/shrink. Independent
repeat/nearest/two-level filtering agrees within7.620236e-6. Ten copied-capture
audit controls include explicit rejection of false live-epoch/natural-derivative
claims. Listed GL state is restored and original multi-draw returns.

These controlled footprints are not original fragment derivatives or live source
ownership. Texture component sizes/swizzles are not captured; unsized GL_RGBA is
reported honestly. Original shared terrainLight/direct-Sun, qualified normal and
position, coherent live mesh/resource/light epochs and dynamic readiness/upload
remain required. Unknown source stays unavailable. No production GLSL or ordinary
pack/Mod changed; proceed to actual shared shading rather than another UV replay.
