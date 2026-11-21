# Unprofiled classification/clock runtime v83

Run `display-water-candidate-20261011-v83`, request
`1d9f4465-3a4e-4c44-91d1-7d3bfed83c80`, completed on actual NVIDIA/Iris with
automatic quit and owned launcher exit zero. No JFR recording was requested.
Both focused underwater scenes retain raw PNG/CSV/JSON artifacts.

Near: 19 frames, mean 1.9815560269239316 FPS.
Moving: 19 frames, mean 1.9259565163775805 FPS.
The earlier unprofiled v81 values were 1.4133598578335562 and
1.4980169328242137 FPS. This observation is encouraging but is not a repeated,
matched load/phase A/B, nor does it separate the two interventions (clock guard
and classification switches). Do not claim an established causal percentage
improvement. Approximately 2 FPS is still not usable natural motion.

Normal configuration/Mods and instance configuration were restored exactly.
Ordinary save unchanged; no rollback. See `runtime-restored.json`.
These newly captured images have not been visually reviewed in this run;
the water/Sun/coherent-light full goal remains unachieved.

The next candidate separately memoizes only the immutable pack-name prefix
predicate by String reference. Pinned Iris bytecode inspection confirmed
`getCurrentPackName()` directly returns a static String field. Each owner read
still fetches the current name, checks Iris activity/world/dimension/frame/
resource validity, and rechecks the prefix for a different String object.
This is not a cached pack-enabled flag or a relaxation of resource freshness.
