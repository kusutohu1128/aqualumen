# Critical refraction footprint correction — goal still incomplete

The current production water shader computes a Snell discriminant and its
pixel derivative span before evaluating transmitted sky. When the discriminant
is within twice that span of the critical boundary, or the quad crosses the
transmission/TIR domain boundary, the solar disk uses point-direction coverage
instead of an invalid linearized gnomonic pixel parallelogram. Well-resolved
footprints retain the original disk clipping. TIR still transmits no sky; the
actual reflection, refraction, Fresnel, IOR, solar scale and angular radius are
unchanged. This is a conservative anti-aliasing safeguard, not a complete rough
dielectric integration or a guaranteed alias-free near-horizon Sun.

## Native evidence

The new isolated64x64 GLSL fixture uses actual `refract`, production solar
coverage and the new production footprint helper, five subpixel shifts,
constant interface normal and a zenith Sun. Its actual rays all remain far
from that Sun near the critical boundary. This is not a production water-main
or natural-scene trace replay.

- Original false solar coverage: maximum1.93356e-7, with10272 transmitted and
  10208 TIR samples. The recorded original test exits1.
- Polygon-overlap rejection alone fails; a simple domain-change guard still
  leaves1.96881e-9. Both failed logs remain in the parent packet. The ineffective
  overlap code was removed rather than presented as a successful fix.
- The discriminant-span guard produces exact0 false coverage. An unguarded
  sensitivity control still produces1.93356e-7; a real zenith Sun retains
  peak coverage1. The test rejects blanket suppression of the Sun.
- Parent `native-check-solar-domain.log` is a complete NVIDIA RTX3080Ti GL4.6
  exit0 with13 program pairs, new glare/critical-footprint controls and all
  retained optical, foreground, water and solar-radiometry regressions.

The current source snapshot is `native-source.tar.gz`, SHA-256
`f055f1acf8ffd47dbad4cca94d6b4de74de3e107b3fd034276cf09466c887df3`.
Candidate ZIP SHA-256:
`8da4caabbf0521a82ede43abd4e074872bb711f50ef8d920de933d11dff65a7e`.

## Actual runtime and remaining work

Two new owned TEST runs each capture six scenes at1600x800, real NVIDIA/Iris,
without fallback, and exit0. Both include the new optical guard; only the four
glare stages differ, with all common ZIP bytes identical. This comparison tests
glare after the correction, not a phase-matched original-versus-fixed optical
comparison. The parent1600x900 images have different aspect and wave/cloud
phases and must not be treated as causal pixel pairs.

The new near-underwater PNGs visually no longer exhibit the conspicuous isolated
rim lights seen in the earlier candidate. The broad dark exterior and distorted
window remain. There is still no accepted Sun-facing above-water close-up or
complete natural underwater appearance. The candidate is not adopted into
ordinary play.

The control first launched with options.overrideHeight900 despite instance
height800; the benchmark correctly rejected that mismatch. The same live
disposable client was resized to800 and the request retried, without a restart.
The lifecycle tool now writes the options override as well. Actual window bounds
are320,190 /1600x800 inside the1920x1080 desktop. Nevertheless the55-second
X11 recordings contain large black regions: inspecting control frame25s shows
most of the image missing while the native screenshot is intact. Window fit and
1650 encoded frames do not qualify this recording path. Preserve the failed
clips; use actual framebuffer/compositor capture next, not more X11 crop tuning.

`runtime-audit.json` independently verifies12 strict native PNGs and all raw CSV
metrics. Five-second samples include video-encoder overhead; no performance
improvement or1440p benchmark is claimed. C9 live storage remains unqueried.

`runtime-restored.json` verifies exact normal configs/Mods, ordinary save bytes
and the backed-up instance.cfg; no save rollback or ordinary-world automation.
All TEST clients are stopped. The next work remains actual reflected-source
diagnosis for the dark exterior, proper full-frame motion capture and a direct
above-water Sun appearance test. Full requested goal is active, not achieved.
