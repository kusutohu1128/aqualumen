# 0.8.1 first-visible-bed correction — bounded development checkpoint

This is a genuine production-water correction, **not an accepted natural-water
release or completion of the realism goal**. The broad cyan/mint shallows,
pointed dark shore bands and repetitive cloud shape remain in the actual images.

## Corrected behavior

A confirmed local two-metre column and an independently camera-visible first
refracted shelf are unchanged while only the remote original-view floor changes
from two to six/eight metres. The old main starts its search too far away,
projects outside the viewport, and returns the original-UV miss proxy, losing
the near shelf's tagged source. The candidate separates the exploration seed
from that unchanged miss proxy. A confirmed local column supplies only a search
hint; the final viewport/bank/surface/residual/confidence checks still decide
whether the sampled opaque receiver is valid. No color/extinction coefficient,
forced-hit, forced-confidence or global path-shortening change is included.

Actual original VS/FS main, zero public wave-height/shore-foam, real coherent
closed-box depth/color/column inputs and store-only observations form the native
fixture. CPU Snell/box intersection, first hit, camera visibility, source cell,
all derivative-quad inputs and the independent Beer/Fresnel response bounds are
qualified before inspecting C0. Both filters reproduce old RED and candidate
GREEN on NVIDIA RTX3080Ti OpenGL4.6:

| Filter | Old positive / remote6 / remote8 green response | Candidate all three |
|---|---|---|
| NEAREST | 0.081048727 / 0 / 0 | 0.081048727 |
| LINEAR | 0.080964118 / 0 / 0 | 0.080964118 |

The independent first distance is `2.9863116469m`, its footprint bound
`[2.8965265300,3.0533078155]m`, and response range
`[0.0805049156,0.0815849375]`. Candidate returned cell `(65,15)` equals the
independent visible source cell; old failing proxies return `(65,48)`.
Current fixture archives include mode0/2/3 neutral/tag C0 and repeat C0, all
original input arrays and per-state bathymetry. Observational/repeat differences
are zero in these fixtures. Earlier logs without these archived mode0/repeat
images are not substituted for the latest evidence.

The [native evidence archive](native/first-visible-bed-evidence.tgz) includes
frozen before-source, old failures and final candidate raw outputs. The
[candidate source/harness archive](native/candidate-source-and-harness.tgz)
preserves the code used. The [full current native suite](native/full-native-final.log)
passes all eleven graphics program pairs, compute programs and retained
underwater/shore/solar regressions. Every native GPU job was terminal before
the following Minecraft run; these are not Minecraft timings.

This is a search-hint correction, not a general first-hit proof for sloped,
multiple, occluded or offscreen receivers. It does not prove every visible
shore-band cause has been fixed.

## Actual Minecraft evidence and limits

The [six-scene run](captures/v081-first-bed-smoke-20261002-1335/run.json) completes
coast, river, ocean, underwater and two upward underwater views with active
0.8.1 and no fallback. Minecraft uses NVIDIA OpenGL3.2, Iris1.8.8/Sodium0.6.9,
physics0.3.0 and observer0.3.7. The exact disposable V2 world is UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, vanilla noise seed308060. No terrain was
placed. Each scene has twenty seconds of warmup and five seconds of raw sample,
1600x900, cap120, VSyncOFF, 12 render/6 simulation chunks. The unchanged1440p
release reporter is not weakened; this is a separate smoke/quality checkpoint.
Mean rates around118FPS near the configured cap do not establish a1440p result,
an all-frame floor, new-chunk traversal or long-running arbitrary-world behavior.

The [actual water draw observation](observations/95eeb2d9-a31f-4b81-9b4c-3ef0e3a6da9a.json)
and paired65536-byte field prove the named sampler accesses a64x64 RGBA32F
texture with Ready1 and4096 known columns. This request occurs after all six
timing samples, not inside them; touched state is restored. The loaded Mod is
0.3.7, while this legacy field observer labels itself0.3.6. Absolute same-frame
camera/full terrain/final fetch attribution are not provided by this seam.
Do not infer an actual-world first-hit proof from field availability alone.

The [independent smoke audit](smoke-audit.json) recomputes raw timings and checks
PNG integrity and identity; the [visual audit](VISUAL-AUDIT.md) judges the actual
images. Same-camera old0.8 stills differ in wave phase/contact history and are
only qualitative comparisons, not controlled pixel A/B evidence. The old
rectangular underwater sky seam/double map is not apparent in the latest two
upward stills, but their strong round curvature remains. Motion and the user's
complete desired underwater appearance are not accepted from these stills.

## Artifact identities

- Candidate ZIP: `Aqualumen-0.8.1.zip`, SHA256
  `e8500f10bc66b1b4bc72a3eef1d4467bbe451d421310d1ab61e4f5b6ac841257`.
- Water FS: `0a4bc571bf719fe577c29d05f58a8d2d7bc73ba6f1d8dfad3fc7f0f67f44a05a`.
- Final water fixture header:
  `b78967f406d4c5c79c437e8d8593c65b1d8825187a2ea07dd8baa89c92cc234d`.
- Final glcheck source:
  `4e65040c59da485606524793dc0451756ef4e1a70674c742f1e5daf649f4e38e`.
- Physics0.3.0: `958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310`.
- Observer0.3.7: `e89739cb92f65d55309187fc2e58f8e4cfaeb3395167c9fb1b37b39299d045dd`.

The old0.6 and0.8 shipping artifacts remain retained. Implementation and team
review are Codex work; no Claude invocation is claimed.

## Lifecycle and next requirement

TEST Save/Quit was focused through the inspected native pause menu and activated
at13:51:32 JST. Player disconnect appears, but complete-save/title/clean-exit
markers do not; the fresh correct namespace PID26 thread dump is retained
privately. Persisted approved390-cell AIR/no-journal checks pass before and
after the quit attempt. Scoped TERM targets only TEST Java2804613 and its own
launcher2804522. Launch-session35121 returns143, **not a clean exit**. The
termination/restoration handoff is recorded under [lifecycle](lifecycle/).
This is not a shutdown-defect fix or whole-world/entity integrity proof.

Keep the full goal open. Next work must improve the actual natural-shore source
handoff/illumination, then cloud shape/spatial lighting and motion/contact
naturalness, with production-renderer regressions and actual views. Documenting
an unresolved flaw is not its acceptance.
