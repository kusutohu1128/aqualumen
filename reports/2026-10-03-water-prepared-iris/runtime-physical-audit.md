# Prepared-view physical Iris pair: independent CPU audit

Saved-data audit only; no GL, game/UI, process, world or runtime configuration changes were made by this reviewer. The machine-readable receipt is [runtime-physical-audit.json](runtime-physical-audit.json). Existing public PNG/metric/underwater-pose and typed guard/stage readers were used without weakening their policies or changing frozen sources.

## Integrity and matched scope

All six completed scene archives qualify under the explicit **1600×900** policy: PNG chunk CRCs, bounded zlib stream, scanline filters and final IEND; every positive contiguous integer-ns CSV row; scene/run/complete IDs; JSON metric agreement; actual focused first-person underwater camera and fixed poses; selected ZIP/no Iris fallback. **871 emitted measured intervals** are retained without trimming or winsorizing. The generic report.load_run 2560×1440 policy was neither called nor monkeypatched.

Both clients record Minecraft1.21.1, Java21.0.7, Iris1.8.8/Sodium0.6.9, benchmark0.3.9, physics0.3.0 and the same complete Mod version dictionary, renderer RTX3080Ti/GL3.2 NVIDIA580.173.02. Declared controls match: render12/simulation6, VSyncfalse, cap120, cloudOFF, default pack options, warmup10s + sample10s each. Actual camera/player/eye coordinates, angles and depths match exactly for each paired view. Matching complete options snapshots have SHA `6a8f5a5ee4df9dfca07262c0099122c9037041f23d467a8d13949395451e1888`; raw fov setting0.0 is recorded without interpreting it as an independently measured field of view. Options are point-in-time evidence, not continuous polling. Mod version equality is independently checked; root's separate installed-JAR hash verification is not relabeled as this reader's proof.

## All observed frame intervals

Every cell below is old → prepared. Mean FPS is frames divided by total recorded interval duration; 1% low is reciprocal mean of the slowest ceil(N/100) intervals, not the absolute minimum. P99 is the nearest-rank ceil(0.99N) interval. The complete raw-ns totals and maximums are in the JSON.

| View | Frames | Mean ms | Median ms | P99 ms | Max ms | Mean FPS | 1% low FPS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| near | 134 → 149 | 74.608 → 66.816 | 74.620 → 66.770 | 76.777 → 68.543 | 76.829 → 68.631 | 13.40 → 14.97 | 13.02 → 14.58 |
| deep | 117 → 133 | 85.194 → 75.016 | 85.135 → 75.002 | 86.612 → 77.229 | 86.794 → 78.509 | 11.74 → 13.33 | 11.53 → 12.84 |
| tilt | 156 → 182 | 63.833 → 54.704 | 63.803 → 54.611 | 65.842 → 56.422 | 67.116 → 57.475 | 15.67 → 18.28 | 15.04 → 17.56 |

Observed mean-frame-time reductions are **10.44% / 11.95% / 14.30%** (near/deep/tilt), with mean-FPS increases **11.66% / 13.57% / 16.69%** in these sequential runs. All 871 intervals exceed 16.667ms; no 60FPS floor is claimed. This is one old client followed by one prepared client, not randomized/ABBA Minecraft sampling, a significance estimate, or a general performance guarantee.

## Caller and archive boundaries

The old physical ZIP is `33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda`; prepared is `b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452`. Full prepared archive validation recovers the exact old parent and confirms all other parent members unchanged, geometryfactor4/phase120, original physical FINAL and guarded optical policies retained.

However the ZIP grows **233,866 → 418,748 bytes**: **+184,882 bytes (+79.05%)**. The exact original parent is embedded as PREPARED-original/parent.zip (233,866 uncompressed /177,320 compressed bytes). Fresh authorization policy is unchanged: SunAuthorization.value(runtime(game)) calls BathymetrySnapshot.inspectScope, whose source hashes Files.readAllBytes of the full installed ZIP on each authorized invocation. Therefore the actual client comparison includes a different archive read/hash workload as well as classifier preparation reuse. Invocation frequency, CPU cost and filesystem caching were not separately measured here. These frame intervals include CPU/GPU work, pacing and any chunk work; they are not the isolated native GPU draw timer or proof that every observed change is caused solely by GPU arithmetic savings.

Post-completion held-tilt observations qualify the active typed int guard1 and attached VS/TCS/TES/FS for each client. Old frame3577 and prepared frame2522 each have matching guard/stage frame/program; the guard was captured 63.364s / 46.156s after the respective run completed. The three rewritten geometry stage bytes/hashes are identical; only the fragment stage hash differs. These are separate observations from the six PNG frames, not proof of a same-frame draw/fetch, water-exclusive program, all-frame operator application or FINAL-bound count readback.

CPU audit qualifies integrity, recorded settings/poses and these local measurements only. Visual/physical/pixel-AA/shipping acceptance, universal speedup and a guaranteed frame floor remain false. Root's separate still-image review must not be inferred from PNG CRC validity; remaining bands/rim are not scored or declared fixed here.
