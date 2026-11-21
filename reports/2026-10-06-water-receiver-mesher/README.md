# Actual requested terrain vertices and Iris encoder output

This advances actual source inputs, not a released water correction. The full
realistic water/sunlight/physics goal remains active. Installed normal0.6 and
physics0.2 are unchanged; no new Minecraft timing or motion acceptance is claimed.

## Actual runtime evidence

The NEW TEST-only0.1.0 observer ran in original isolated Aqualumen Lab / exact
V2 UUIDb22dbccb-2970-41e6-847f-f183b1ec923d / actualseed308060 / overworld.
Minecraft1.21.1, Iris1.8.8, Sodium0.6.9, actual NVIDIA RTX3080Ti renderer, active
unchanged0.6 pack. Owned handle44144 / Java3440419. The existing16 first-receiver
requests contain14 unique sand cell/face owners; all14 are captured naturally
during initial chunk compilation, without camera/terrain commands or F3+A.

The observer copies **actual** BlockRenderer-prepared vertex arrays immediately
before its buffer push. Owner position/state/normal and actual chunk-relative
offset are retained. A thread-local, identity-matched, single-use association
joins these immutable records to the actual synchronous XHFPTerrainVertex.write.
Only the five initialized20-byte words per vertex are read after that invocation
returns its checked4-stride extent. No native buffer or mutable vertex is written.

14 full faces /56 actual vertices /280 output words match independent pinned
position quantization, packed UV bias, RGB/separate8-bit AO and clamped smoothed
light encoding. Actual stride28; workers#0/#4 (thread144/148); AO0.39996338..1.0,
raw sky bytes128..192, raw block bytes0. All56 raw affine UVs agree with the
previous actual static sand face input. This cross-packet comparison is not a
live resource/geometry epoch proof. AO is not guessed1, and smoothed light is
not replaced with a neighboring integer sky level.

`independent-mesher-audit.json` validates the saved request/build/runtime scope,
unique ownership, full-face corners/winding and280 independent word expectations.
Five public tests include copied-capture negatives for corrupt position, guessed
full AO, duplicated owners and a non-worker label; original captures are unchanged.

The public immutable-scope tracer had a genuine missing-behavior RED->GREEN;
supplemental reuse/wrong-array/unsupported-input/two-real-thread isolation checks
pass. The new independent reader also has a frozen unimplemented-reader RED and
implemented GREEN. These are new module/reader tests, **not shader defect REDs**.
No internal collaborators are mocked, as required by the TDD skill used here.

## Build and safety provenance

`actual-build` retains compiler output, the exact JAR and compiler inputs;
`build-receipt.json` proves source stability through the synchronous build.
JAR SHA25644e46901d3b845765459fef08c266d678fff97aa982b49f03e54e8acb1e20b1b.
The preliminary same-source compile also succeeded at unique events-v1; retained
events-v2 is the explicitly recorded runtime artifact. Neither retained release
dist nor sealed evidence is overwritten.

The first baseline attempt was rejected by the existing strict backup-prefix
guard before any Mod/config install. Its private temporary config copies remain
recoverable. Correcting only the lifecycle cache prefix produced the accepted
fresh post-save41-file baseline. That lifecycle is not a compiler input; its
post-build correction is separately frozen in installation-lifecycle.py.
Compiled Java/metadata/builder sources remain byte-identical to the build record.

Ordinary owned51490 exits0 via clean Save/Quit/title-Quit before TEST. TEST44144
also exits0 with AllDimensionsSaved before recoverably disabling its JAR/opt-in.
All41 ordinary saved files/configs/3 Mods match the fresh baseline **before**
normal reopening, with no save rollback. Final actual gameplay/subsequent pause,
new live ownership and all11 disabled opt-ins are recorded in checkpoint.json.
Authentication logs stay private. OpenAL failure remains explicitly unresolved.
No native EGL or standalone GL harness is run in this cycle or after normal launch.

Final root-inspected normal gameplay17:12:49, fresh server pause17:13:23 and
actual menu17:13:32 qualify the new paused handoff, owned3603 / Java3445977.
This is a point-in-time verified live handoff, not a permanent process guarantee.

## Still required

Actual shader attribute decode/interpolation, iris_LightmapTextureMatrix and
terrain draw texture/filter/LOD binding are not observed. The source is not
shaded, uploaded or renderer-ready; no coherent live resource/geometry epoch
is established. Full/partial-water topology and displaced interfaces, dynamic
Iris per-face source binding, coherent direct Sun/ambient shading and original
natural shoreline/motion/frame timing acceptance remain open. The inspected
unchanged TEST view still shows strong cyan water and serrated shore bands.
See RESUME.md for the next actual integration seam, not a cosmetic substitute.
