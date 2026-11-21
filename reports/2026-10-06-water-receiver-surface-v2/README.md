# Exact first-face material association, CPU candidate only

`ReceiverSurface` joins the existing immutable first-opaque geometry with a
sparse immutable catalog of actual decoded face descriptors and copied texture
snapshots. It returns raw nearest-mip0 RGBA only for the exact first cell, block
identity and entry normal. Unready/missing near material cannot borrow a farther
available face. Geometry UNKNOWN, unsupported or boundary ambiguity cannot be
promoted by catalog entries. `PIXEL` is unshaded input, never radiance readiness.

The caller token includes world UUID, dimension, frame and atlas revision. A
different token returns STALE without exposing geometry/pixels. This enforces
API ownership but does not create or prove a real Minecraft/atlas snapshot epoch.
The caller still must synchronously capture coherent resources and provide a
correct revision that cannot be reused across resets/reloads. No runtime owner,
cache scheduler, Iris sampler, source upload or production shader is added here.

The catalog bounds are4096 unique face owners and1048576 unique retained texels
(4MiB pixel payload plus descriptors/field). Shared immutable texture objects
count once; copied equivalent textures count separately. Conflicting/duplicate
face owners are rejected, rather than arbitrarily selecting the last color.
The catalog list is copied and does not follow later caller mutations.

Six actual incremental public-API RED->GREEN cycles qualify first-face sampling,
frame rejection, block identity, duplicate ownership, face count and unique
texture budget. Further public controls cover near-unready/farther-present,
missing first face, opposite normal, world/dimension/atlas scope, immutable list,
inclusive capacity, shared texture memory and unknown/edge geometry. Actual
game access is substituted only at the external World boundary; no own-module
mocks, shader harness, native GL or live Minecraft measurement is used here.

The changed joining module is then replayed on the existing sealed saved-field
and original16 refracted rays, rather than recapturing terrain or rerunning old
GPU geometry work. Fourteen unique face descriptors are taken from the already
qualified actual0.1.1 probe. Stock sand pixels are decoded in memory with ImageIO;
their full RGBA digest must match actual NativeImage snapshots. All16 first
cell/normal/block/distance and sparse pixel/RGBA expectations match, including
the eight previously camera-hidden requested receivers. No asset PNG/full pixel
image is copied into the report. Frozen saved terrain and later actual face
capture are not contemporaneous; this is explicitly offline association proof.

The first preparer failure is retained in ../2026-10-06-water-receiver-surface/.
Different savedPoint positions/pixels on one identical face are not conflicting
material descriptors. The corrected preparer compares the remaining descriptor
fields, keeps each ray's expected texel and passes two focused checks. Unique
synchronous compilation completes before replay; no old-binary substitution.

Source joining now has bounded tested CPU input ownership, but both original
water-MAIN native-v4 radiance REDs remain unchanged. GPU atlas/mip/filtering,
actual coherent source capture, AO/smoothed light, dry-light/direct-Sun joining,
sampler/state/epoch qualification, production rendering, natural water/motion,
timings and full realism goal remain open. Ordinary0.6/physics0.2 is unchanged.
