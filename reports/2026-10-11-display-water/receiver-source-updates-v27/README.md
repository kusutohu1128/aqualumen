# Fresh source production across frames

The one-shot producer has been replaced by a frame/world/resource scheduler.
Each eligible frame owns fresh bounded geometry, mesher inputs, current draw
UV/lightmap uniforms, actual atlas/lighting resources and GPU-shaded source.
The schedule permits one attempt per frame and rejects duplicate/older attempts
within the same world/resource namespace. Failed or missing new-frame production
does not make an earlier field current. New worlds/resources and pipeline reset
require fresh work. CPU controls are in `../receiver-source-update-schedule-test.log`.

The redundant material-only center scan and duplicate shaded point were removed.
Only declared exposed full-unit top faces are shaded for the source volume;
vegetation, partial water and unloaded cells remain unavailable. The field is
still sparse 3x36x3 and uses the declared face-center point approximation.

Actual NVIDIA/Iris receipts span frames 3 through 10620, resource generation 1:
178 periodic source-update receipts and 178 corresponding water-draw binding
receipts, with no source-intake/terrain/binding failure reports. The Y origin
changed from 32 to 29 across the scenes. The producer did not retain one old
source while only updating a readiness flag: the owned intake, GPU shading and
transactional upload execute anew each eligible frame. Texture names can be
recycled after deletion; name reuse across distant trace frames is not itself
stale-source evidence.

Recorded producer wall-time samples have median 7.0813405ms and maximum
55.337404ms. These 178 periodic samples include synchronous GPU readback; they
are not isolated GPU timings or an unbiased measurement of every producer call.
The actual 1600x800 benchmark, including native capture overhead, measured:

- Underwater near: 434 frames, mean 11.515923ms, p99 21.161002ms.
- Underwater moving: 423 frames, mean 11.820627ms, p99 22.117954ms.

Sixty-nine native PNGs and camera/timing metadata passed sequence validation.
Only moving `frame-015.png` was visually inspected this cycle: the strongly
folded window rim and broad dark exterior remain. This is not visual acceptance,
whole motion review, a positive world-reflection hit or 2560x1440/FPS acceptance.
Actual block edits/resource reload, larger source coverage, reflected footprints,
qualified partial-water entry and resolved/residual normal filtering remain open.
The full Sun/underwater-view goal remains unachieved.

Experimental Mod SHA256:
`7ce78eec58fb4d52895d7a6aff193f0cf03af09cce44294309c7390a9de1fa16`.
The client exited normally; normal config/Mods, instance settings and ordinary
save bytes were restored/verified exactly without any save rollback.
