# Display-water first implementation checkpoint

Goal: natural Sun presence and a convincing underwater sky/interface, as
requested in the current session. Neither appearance goal is accepted yet.

The candidate adds original separable HDR display glare, without changing solar
angular radius, scene illumination or water optical source buffers. Both passes
execute after the existing composite and before final tone mapping. C9 is a new
RGBA32F temporary attachment; live Iris allocation/activation remains unverified.
The kernel uses fixed pixel units and redistributes only 2% of above-threshold
light. Natural daylight/sunset comparison and timing remain required.

`native-check.log` records a complete `make check` run with NVIDIA GeForce RTX
3080 Ti / OpenGL 4.6 / driver 580.173.02, exit 0. All 13 program pairs and retained
regressions pass. The new glare fixture executes actual composite1/composite2:
zero and dim inputs remain exact, interior HDR sum remains 264984, and corner
sum is 261287 with discarded outside-viewport light. Maximum oracle error is
0.00311421 at a 264984 peak. This is not a Minecraft appearance/FPS result.

Build: `dist/Aqualumen-DisplayWater-2026-10-11.zip`, SHA-256
`56a95086ca7f12c9622db5d971798dd638a56ef4cce74ffe4416596cecebf44f`.
No installation or ordinary instance/config/world changes were performed.

Underwater inspection confirms that existing source already repairs a near-wall
SSR miss; it would be misleading to implement that repair again. Existing
resolved-normal images are diagnostic four-panel captures, not new accepted
screenshots. Their real-color upper-left panel still shows a distorted rim.
Unqualified residual-interface experiment modules must not be promoted as an
accepted fix. Next: fresh guarded natural views and same-invocation source/miss
observations, then a causal water correction with retained TIR/cave/geometry
controls. Offscreen reflected surfaces require a qualified source; invented sky
or arbitrary bright fallback colors are not acceptable replacements.

## Actual Iris comparison, not visual acceptance

`control-runtime/` and `candidate-runtime/` now retain six actual scenes each:
day/dusk, near/deep/tilted upward underwater views and moving-view. Both owned
TEST launchers exited 0. The saved manifests identify real RTX3080Ti/Iris1.8.8
GL3.2, 1600x900, active exact ZIP hashes and no fallback. The independent
`runtime-audit.json` verifies all12 strict PNGs and raw CSV metrics; common ZIP
members are byte-identical and only four glare stage files differ. This does
not freeze cloud/wave phases and is not a pack-only timing comparison. Each
sample is five seconds; video encoding overlaps selected samples.

The initial pre-world control request was rejected with `An integrated
singleplayer server is required`; it was not a run or an accepted capture.
The same still-live client was allowed to load, then a new request succeeded.
The lifecycle tool now separates selecting files from requesting a loaded run.

Visual inspection finds a persistent uniformly dark underwater exterior and
distorted window rim. The candidate spreads the central Sun but also makes
separate bright rim points more conspicuous. It is **not adopted** as a natural
underwater or finished Sun appearance. Day/dusk screenshots do not provide a
clear isolated above-water Sun close-up; that acceptance item remains missing.
The separate tiny dark squares seen in the recorded candidate frame are not
diagnosed as either display artifacts or optical failures yet.

Both20-second X11 clips contain600 frames at1600x900. They capture mixed scene
transitions, not one uninterrupted underwater camera test. The candidate's
inspected first frame includes a narrow black top strip; the live window also
extended10 pixels beyond the visible desktop. Frame dimensions therefore do
not prove complete image coverage, and these clips are **not** accepted full
window temporal evidence. Retain them as failed/limited recording evidence.

`runtime-restored.json` verifies exact normal options, Iris/benchmark config,
active Mods and every ordinary save byte, with no save rollback. Benchmark
entry point was removed. The launcher updated instance.cfg metadata (its full
hash differs), so do not claim that entire file unchanged. No ordinary game was
reopened automatically. Five lifecycle safety unit tests pass.

Next action: fix video coverage, capture an actual above-water Sun-oriented
view, and qualify passive same-invocation underwater reflection/TIR/source
observations before choosing the optical correction. Cosmetic brightening or
removing Snell's window is not a substitute for the user's requested result.
