# Actual GPU atlas regions qualified; water source rendering remains pending

Real Minecraft1.21.1 / Iris1.8.8 / Sodium0.6.9 on RTX3080Ti, GL3.2 NVIDIA580.173.02,
runs the guarded TEST-only0.1.2 observer. The original shader and normal physics0.2
are unchanged. Frames491/605/723 after5.006/6.009/7.010s capture48 actual CPU/GPU
sprite regions and48 first-point GPU RGBA checks. All whole sprite hashes match
actual NativeImage plus independently ImageIO-decoded stock sand:
419fc26081190f9a43757aa58be5e3858becfc8e8f956af31987a504135eba90.
CPU saved-point/four-grid validation separately covers240 checks/20 unique pixels.
Fourteen distinct requested faces include eight previously camera-hidden first
receivers; these are not live-fragment/geometry-at-the-same-time proofs.

The already-registered block atlas is read directly, without loading or replacing
an asset: actual textureID13,1024x512, internal-format6408 (`GL_RGBA`), queried
channel bits8/8/8/8 and types35863 (unsigned-normalized). The pure bounded atlas
decoder owns RGBA bytes and slices exact integral rectangles. Fractional extent,
dimension mismatch, unsupported opacity, oversized/malformed input remain unready.
No PNG/full asset image is redistributed. Readback memory is bounded and freed.

Actual object min filter9986 (NEAREST_MIPMAP_LINEAR), mag9728 (NEAREST), wrap10497
(REPEAT), base level0/max4 are recorded. Only mip0 contents are read. This is not
a filtered shader texture fetch, derivative/LOD/anisotropic sampling proof, actual
terrain draw sampler binding, resource-reload epoch or production source upload.
Frame-begin metadata must not be mislabeled as actual terrain-draw binding.

An independently owned2x2 GPU texture has a known RGBA pattern. Its actual readback
has digest60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1;
the point7/8/9/255 stays unchanged in the owned CPU snapshot after an actual GPU
mutation, independently read back as255/255/255/255. Only the owned fixture is
written/deleted. The real atlas is never written, closed, reconfigured or deleted.
Listed active-unit/2D binding, PACK/UNPACK buffers and16 pixel-store values restore
exactly in all three observations and the known fixture. This is listed-state
restoration, not an unchanged-C0/radiance or comprehensive observer-passivity proof.

The actual three records/descriptors agree, but no general temporal/reload
coherence is inferred. Raw tint/light/brightness remain unshaded inputs; AO,
smoothed light, actual shared dry illumination and direct-Sun joining are pending.
The qualified native-v4 hidden-source and nearer-first/wrong-farther-source REDs
remain unchanged. Actual cyan/serrated water appearance persists. No new timing
benchmark, movement acceptance, shipping shader fix or full-goal completion.

The public auditor first verifies schema3/original request hash and uses an
explicit temporary CPU-only schema2 projection to reuse the old input contract.
That projection is not rewritten raw evidence or a GPU proof. GPU format/state,
whole-sprite and point checks and owned GPU control are validated separately.
Five genuine negative audit RED->GREEN increments reject changed binding, GPU
hash/point mismatch, unqualified storage and failed owned mutation. Focused atlas
behavioral tests and affected retained surface/texture/geometry controls pass.

Installed producer908feae33c6d20c5d395eadb7856ce5dfffbc20c8af24beb87d64e519dc2ce12
matches an exclusive deterministic rebuild. The initial unsized-format rejection
is retained separately; it is not overwritten or promoted. Failed TEST owned58119
and qualified TEST owned23887 both exit0 after clean saves. The0.1.2 JAR/property
are recoverably disabled. Original41 ordinary saved/config/Mod files match exactly
before normal0.6/physics0.2 reopens owned79690 / Java3386746. No ordinary commands,
save restore or native GL after normal relaunch. Fresh gameplay/pause images and
ordered pause event are inspected and recorded in checkpoint.json. OpenAL failure
still means audio is unavailable in this launch, not a complete subsystem pass.
