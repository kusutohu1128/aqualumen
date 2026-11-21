# Published plant backend in the real receiver DDA v73

`water_plant_backend.glsl` implements the existing opt-in DDA callbacks using
validated cell headers/links and the original primitive texture. Unknown cells
require independent full-water and complete-model proofs before promotion. Known
water retains the DDA's existing interface tests, then requires complete-model
coverage for its indexed segment. Earlier opaque geometry remains authoritative.
Alpha-visible leaves stop with their actual normal and no borrowed floor radiance.

Receiver cells map through an explicit integer window offset; ray origins map
through the packet's camera-relative reference. Offsets are bounded before integer
addition, preventing extreme forged offset overflow. Ready state, atlas ownership
and explicit LOD bounds remain separate qualifications. This file is not included
or enabled in ordinary shader programs yet: live producer and scoped draw binding
must supply the complete contract first.

`../native-plant-backend-v73.log` compiles and draws the actual receiver DDA with
this backend on NVIDIA RTX 3080 Ti, replacing the previous fixture-only callbacks.
Supplied header/link/triangle controls cover transparent continuation to a paired
floor, opaque diagonal first leaf, unavailable alpha/fluid/model, earlier bank,
interface rejection and a later genuinely unqualified unknown cell. Additional
controls cover translated packet reference, nonzero valid window offset, invalid
offset/ready/LOD, unowned atlas, forged footer count and duplicate links.

An initial failing unknown-cell control incorrectly supplied full-water and model
proofs to that cell, so the new backend correctly qualified it. The fixture now
removes its water proof rather than forcing a qualified cell to remain unknown.
This is supplied-fixture GPU evidence, not live publication, leaf radiance or
Minecraft visual acceptance. Existing receiver/source GPU and diagnostic-builder
regressions pass. Full water/sky/Sun acceptance and live integration remain open.
