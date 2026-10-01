# Independent exported-data audit: Aqualumen 0.4.0

Codex independent CPU/read-only audit, 2026-10-02. This is not a new Claude
Opus/Sonnet review or a fresh Minecraft/GPU benchmark. Only this new audit
document was authored; run data, images, configurations and source were not
modified. No GPU context, game lifecycle/control, private process arguments,
private logs or model calls were used.

## Disposition

**Exported image integrity, frame statistics, pack identity and recorded scene
metadata pass the checks below.** The candidate has two intervals over the
16.667 ms reference budget; an observed all-frame 60 FPS floor is false for this
run. Some A/B focus conditions differ, so FPS changes are not a pack-only causal
measurement. Ordinary-play settings restoration/instrumentation-disable evidence
has not yet been exported at this audit checkpoint; fixture completion is a
separate confirmed record. This audit does not mark the
[full realism goal](../../docs/REALISM_GOAL.md) achieved.

## Scope and verification method

Audited saved runs are [before](before/run.json), run ID
`water-v0.4-before-v0.3.3`, and [after](after/run.json), run ID `water-v0.4-after`.
Each requested 5 seconds warmup and 5 seconds measurement. The captures were
recorded at 2026-10-01 19:16–19:27 UTC (2026-10-02 JST), not during this audit.

Imported [tools/report.py](../../tools/report.py) and called `load_run` for both
directories without invoking its report-writing `main`. Python bytecode writes
were disabled. Additionally read every CSV and independently recomputed all
metrics using `math.fsum`; checked sequential frame indices, positive finite
intervals and agreement of integer nanoseconds with stored milliseconds.
The report helper SHA-256 at audit was
`716e7dbbb58c736ad076f317d214f23ba542bc0e91b1b480865eb1d37201b31c`.

- **20/20 PNGs pass**: 4 before and 16 after, exactly the requested scene sets,
  each 2560x1440. Strict signature, chunk bounds/order/type/CRC, single IHDR,
  contiguous IDAT, final IEND without trailing bytes, bounded zlib EOF/decoded
  size and legal scanline-filter checks pass. This establishes file integrity,
  not visual/physical quality or temporal stability.
- **18,506/18,506 intervals pass**: 3,889 before and 14,617 after. Frame indices
  are contiguous from zero. Nanosecond-to-millisecond differences are at most
  `1.78e-15` ms, attributable to floating-point representation.
- Frame count, mean FPS, slowest-1%-mean FPS, P99, maximum interval, reciprocal
  maximum FPS and over-budget count agree with every per-scene JSON. Maximum
  independent numeric difference is `5.69e-14`, well inside the validator's
  tolerance. No rejected/truncated/aborted run record was found.
- CSV sums differ from capture-window duration by 2.617–8.016 ms after and
  3.079–5.916 ms before. Metrics correctly use the sum of retained intervals,
  not the slightly longer sampling envelope. The documented recorder discards
  a start boundary; screenshots/serialization occur outside the timed interval.

## Candidate measurements recalculated from all raw intervals

These are stored observations under the recorded configuration/focus conditions,
not new measurements. The 1% low is the reciprocal mean of the slowest ceil(1%)
intervals, not an absolute minimum.

| Scene | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | >16.667 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coast-day | 798 | 159.58 | 116.95 | 8.2125 | 9.0345 | 0 |
| river-day | 804 | 160.86 | 122.36 | 8.0592 | 8.5995 | 0 |
| ocean-day | 680 | 136.08 | 90.89 | 10.1931 | 14.8541 | 0 |
| ocean-dusk | 680 | 136.11 | 90.10 | 9.7798 | 17.0882 | 1 |
| ocean-night | 715 | 143.15 | 90.65 | 9.2431 | 21.7753 | 1 |
| ocean-rain | 630 | 125.97 | 92.95 | 10.5525 | 11.1537 | 0 |
| underwater | 780 | 156.08 | 113.72 | 8.5690 | 9.0537 | 0 |
| underwater-up-near | 960 | 192.11 | 135.37 | 7.0923 | 7.7534 | 0 |
| underwater-up-deep | 941 | 188.30 | 133.33 | 7.1453 | 8.0797 | 0 |
| underwater-up-tilt | 966 | 193.31 | 137.95 | 6.9381 | 8.8607 | 0 |
| moving-view | 683 | 136.64 | 100.95 | 9.5231 | 10.4992 | 0 |
| boat-contact | 663 | 132.59 | 84.03 | 10.2167 | 14.7596 | 0 |
| cave-water | 808 | 161.69 | 109.71 | 8.7401 | 10.3363 | 0 |
| glass-layers | 748 | 149.75 | 91.40 | 9.9454 | 15.2602 | 0 |
| nether-view | 1875 | 375.19 | 233.91 | 3.9927 | 4.7017 | 0 |
| end-view | 1886 | 377.26 | 230.15 | 4.0184 | 4.7525 | 0 |

All scene P99 values fit 16.667 ms, but not all individual intervals do. Exact
misses are [ocean-dusk.csv](after/ocean-dusk.csv) frame314 `17.088164` ms and
[ocean-night.csv](after/ocean-night.csv) frame346 `21.775271` ms. The worst
reciprocal instantaneous rate is approximately 45.92 FPS. The original strict
60-FPS floor was relaxed; these two misses are disclosed observations, not
grounds for asserting a floor or silently rejecting the quality-priority slice.

## Four A/B comparisons: what matches and what does not

| Scene | Before mean FPS | After mean FPS | Observed change | Before/after capture focus |
| --- | ---: | ---: | ---: | --- |
| coast-day | 172.22 | 159.58 | -7.34% | true / true |
| river-day | 176.52 | 160.86 | -8.87% | true / true |
| ocean-day | 173.62 | 136.08 | -21.62% | true / false |
| underwater-up-near | 255.69 | 192.11 | -24.86% | true / false |

Mean FPS is lower in all four saved pairs. **Do not attribute these reductions
solely to the pack.** `window_focused` differs for two pairs and records the
capture-time state, not a full sampling-interval focus trace. The candidate's
coast/river captures are focused; its other 14 captures are unfocused. Even the
two focused pairs are sequential observations with changing shader animation
and possible background load, not repeated randomized fixed-input timings.

All four pairs exactly agree in world/local-player identity, actual player and
rendered-camera positions/angles, site, resolutions and capture method. The
fixed actual camera poses are:

- Coast: `(-191.5,65.71999988555908,320.5)`, yaw/pitch `(0,9)`.
- River: `(-63.5,65.71999988555908,-63.5)`, `(-45,9)`.
- Ocean: `(448.5,65.71999988555908,-383.5)`, `(-45,9)`.
- Upward near-water: `(448.5,62.38899988555908,-383.5)`, `(-45,-90)`;
  separately recorded eye `(448.5,62.38900000476837,-383.5)`, actual player
  `(448.5,60.769,-383.5)`.

The upward near-water pair also exactly matches explicit first-person/eye-match,
actual water submersion/surface/depth and requested/client/server time6000
metadata. General coast/river/ocean captures do **not** export a separate actual
eye position or first-person validation flag, nor actual time/rain strength;
their actual camera pose is confirmed, but those absent controls cannot be
independently certified. Wave/cloud phase is not frozen by setting world time.

## Identity, settings and all 16 compatibility scenes

Independent archive hashing matches both expected and active recorded identities
in the run files and every associated per-scene JSON:

- Before `dist/Aqualumen-0.3.3.zip`:
  `ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5`.
- Candidate `dist/Aqualumen-0.4.0.zip`:
  `5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`.

World UUID is `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed308060, approved
`AqualumenNaturalV2`, vanilla noise generation. All scene records have correct
UUID, active shader without fallback, matching pack and 2560x1440 window/
framebuffer. Fixed-scene angles agree with requested values. All 16 candidate
metadata records pass the report validator; Nether and End use their expected
dimensions. Recorded physics outputs show inactive bridge in those dimensions.

Both runs use Minecraft1.21.1, Java21.0.7, Iris1.8.8, Sodium0.6.9, physics0.2.0,
the same installed mods, ZGC/2GiB initial/6GiB maximum heap, 12 render/6 simulation
chunks, VSync off, frame limit260, Iris/effective vanilla clouds OFF and default
pack options. Exported Iris configuration differs only in selected pack and
save-time comment, not other settings. The benchmark Mod remains version0.3.3;
that instrumentation version is not the shader-pack version.

For `moving-view`, actual camera/player yaw14.979683 degrees agree, but expected
yaw15.061745 differs by0.082062 degrees. The dynamic yaw is sampled at different
instants and is deliberately not subjected to the fixed-scene yaw equality;
this is not an exact stationary pose control. Three upward-water scenes have
explicit eye/first-person validation; the other 13 candidate scenes do not
export independent eye position.

`boat-contact` records physics active, one simultaneous contact and maximum
force0.2208, consistent with its exported physics status/samples. Its 6m/s,
20Hz server-translated boat is an instrumented contact workload, not ordinary
manual rowing. Its 663 recorded frames have no 16.667ms misses. This run does
not contain chunk traversal and does not establish new-terrain performance.

## Native evidence and cleanup boundaries

[native-final-check.txt](native-final-check.txt) records RTX3080Ti OpenGL
**4.6.0** NVIDIA580.173.02, 11 graphics program pairs and retained physical/
production regressions passing, including zero-source Sun-only caustics,
positive Sun attribution, receiver rejection, continuity and underwater
sky/Fresnel/TIR/cave/translated-eye controls. These are archived fixture results,
not GPU tests performed by this auditor or proof of every real Iris draw route.

The Minecraft run files instead record GL **3.2.0** NVIDIA580.173.02 on the same
GPU. These are distinct context/version strings; do not relabel native GL4.6
checks as Minecraft FPS measurements or claim that the recorded Minecraft
version string is the GPU's maximum supported capability.

Both [before completion](before/complete.json) and
[after completion](after/complete.json) match their run IDs/scenes and report
`status=complete`, `fixture_cleanup_complete=true`. The candidate's three
temporary glass layers are an explicitly disclosed disposable-world fixture,
not untouched natural terrain. The recorder's completion path waits for return
to the local Overworld and restoration of its HUD, but the completion JSON does
not itself export the resulting ordinary-play settings or instrumentation state.

At this checkpoint no exported normal-play restoration/disabled-instrumentation
summary is present. Full handoff cleanup therefore remains **not independently
verified here**, rather than failed or assumed complete. A subsequent exported
summary can be audited and added without changing the run data. Missing cleanup
evidence does not invalidate the recorded PNG/interval checks above.

No new timing, visual replay, temporal-video grading or universal physical/FPS
claim is made by this audit. Preserve the original images/CSV and disclose the
focus/metadata limits when using these measurements for release communication.
