# Unprofiled pack-predicate runtime v84

Run `display-water-candidate-20261011-v84`, request
`715cd769-643c-4107-abe6-ce7c10c305d6`, completed on actual NVIDIA/Iris with
automatic quit and owned launcher exit zero. No JFR recording was requested.
Both focused scenes retain original PNG/CSV/JSON artifacts.

| Scene | Frames | Mean FPS |
| --- | --- | --- |
| underwater-up-near | 22 | 2.266517845277995 |
| underwater-up-moving | 22 | 2.265608839289858 |

Previous v83 means were 1.9815560269239316 and 1.9259565163775805 FPS.
The ZIP member payloads of the v83/v84 shader packs are identical. A byte
comparison of Mod v85/v86 finds one added class (`ReceiverPackEligibility`)
and one changed class (`ReceiverRadianceBridge`), with no other additions,
removals or changed payloads. Thus the code intervention is confined to the
pack-name predicate; this does not establish matched runtime load/wave phase,
repeatability or a causal percentage speedup. About 2.27 FPS is not usable.

`native_motion_audit.py` validated 44 PNG files/timestamps, not temporal
appearance. The original near-view PNG was visually inspected: distorted sky
window, compressed/folded boundary and dark polygonal exterior patches remain.
Moving-view frames have not been visually reviewed in this run. No visual or
natural-motion acceptance is claimed.

Normal config/Mods and instance configuration were restored exactly. The
ordinary save matches its pre-run tree; no rollback occurred.
See `runtime-restored.json`. The full water/Sun/illumination goal remains open;
further optimization cannot substitute for fixing the optical/receiver paths.
