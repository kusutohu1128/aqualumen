# Aqualumen 0.4.0 implementation and verification checkpoint

2026-10-02. This is a bounded water-renderer checkpoint, **not completion of the
[realistic-water/sunlight goal](../../docs/REALISM_GOAL.md)**. Implementation and
independent review are Codex work, not a new Claude invocation.

## Frozen shader identity

Built, installed and selected `Aqualumen-0.4.0.zip` SHA-256:
`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`.
The unchanged previous 0.3.3 ZIP is
`ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5`.
Physics bridge 0.2.0 is unchanged. See source/ZIP byte matches in the
[visual audit](../../docs/reviews/codex-v0.4.0-visual-audit.md).

## Causal native corrections

The actual production shaders were run on the RTX 3080 Ti, NVIDIA 580.173.02,
native OpenGL4.6 compatibility context. This is not a Minecraft FPS measurement.
The [final full check](native-final-check.txt) compiles/links 11 graphics pairs
and 3 compute programs and retains atmosphere, aerial transport, sky, waves,
Fresnel/TIR, closed-cave and eye-coordinate controls.

- Opaque direct-Sun radiance is exported independently of diffuse sky, Moon and
  block light, then copied with opaque RGB/depth before translucents. Actual
  terrain/deferred MRT controls retain positive Sun and zero-Sun diffuse output;
  immutable copies survive later producer-buffer mutation.
- Above-water caustics focus only a confirmed receiver's direct component.
  Zero-direct-source direction dependence was RED `0.0289524` maximum RGB and is
  GREEN `0`; positive red-only focusing remains `0.0107598`, other channels zero.
  An unknown finite-shelf proxy leak was RED `0.000158489`, now zero.
- Above-water top faces finish a fixed refinement and blend separately
  transported hit/proxy radiances by reliability. The preserved smooth-bed RED
  interval jumped `0.066329` RGB over about0.00004m; GREEN is `0.00000570714`.
  This does not prove every discrete bank or reflection-source transition.
- Underwater composite uses same-pixel raw opaque depth/direct attribution.
  Zero-source dependence was RED `0.0769311`, now zero; red-only focusing remains
  `0.0285025`. Matching-depth positive controls and nearer-layer rejection pass
  with both NEAREST and LINEAR texture filtering. Depth-free/copanar transparent
  layers are not fully identified by this conservative depth test.

RED/GREEN originals and the source diagnosis are retained in this directory and
[the shore review](../../docs/reviews/v0.4.0-shore-diagnosis.md). No global water
desaturation or extinction/scatter coefficient adjustment was made.

## Real Minecraft evidence

Exact UUID-guarded disposable `AqualumenNaturalV2`, vanilla seed308060,
Minecraft1.21.1 / Iris1.8.8 / Sodium0.6.9 / Java21.0.7 / RTX3080Ti.
Actual Minecraft reports GL3.2; do not substitute the native harness GL4.6 label.

The [before](before/RESULTS.md) run has four scenes and the [after](after/RESULTS.md)
run has16: coast, river, ocean/day/dusk/night/rain, underwater and three upward
views, moving view, scripted boat, cave, glass, Nether and End. Each has5s warmup
and5s measurement at2560x1440, render/simulation12/6, default BALANCED, VSync off.
All candidate records identify the correct active pack, without Iris fallback.

Independent audits validate20 PNGs and18,506 raw intervals and recompute the
stored statistics. Land/water candidate means are approximately126–193 FPS.
Two intervals exceed16.667ms: dusk17.088164ms and night21.775271ms. There is no
minimum60-FPS guarantee. Ocean/upward A/B focus differs, and only coast/river
candidate captures were focused; sequential timings are not pack-only causal
comparisons. See the [independent data audit](INDEPENDENT-AUDIT.md).

Actual coast/river images **still show saturated cyan/mint shallows and serrated
dark/clear bands**. Open-ocean/upward-sky/cave/glass/dimension compatibility is
retained in the observed views, not a proof of all scenes or photorealism.

## Temporal observations, distinct from 1440p timings

The first1440p X11 recordings were clipped by an offscreen window and are retained
only as diagnostic attempts. A later15s full-window coast attempt includes a
scene transition and is not the aligned final coast clip.

The completed [temporal run](temporal-run/run.json) is a separate1600x900 workload:
5s warmup/30s sample, focused, same pack/UUID, no terrain placement. Each full-window
coast/moving/boat clip begins at the observed corresponding sampling state and
lasts20s, before that scene's capture boundary. The
[video integrity audit](temporal-video-audit.json) records SHA, start status,
timestamps, dimensions and1200 decoded frames per clip. No adjacent decoded
frame hashes are identical; this does not prove unstalled native acquisitions
or native Minecraft frame rate. Videos remain in `build/quality-v0.4.0/`:

- `coast-day-full-motion.mp4`
- `moving-view-full-motion.mp4`
- `boat-contact-full-motion.mp4`

Independent selected-frame review confirms full image coverage but retained
cyan/serrated bands. Boat-relative geometry changes sharply near10s and the wake
is mostly outside this forward view. Scripted translation is not vanilla rowing;
the boat clip **does not establish natural movement/wake quality**. Contacts also
differ from the short still suite. See the independent visual audit for exact
workloads and sampled-frame scope; temporal naturalness remains unaccepted.

## Safety and current handoff boundary

The ordinary user's existing world was saved/closed normally before testing.
Its `level.dat` still has the original03:31:47JST save timestamp. No ordinary-world
automation, teleport/time command or terrain edit was used. Automated operations
were confined to the verified disposable UUID. Both test runs completed cleanup;
persisted actual390-cell AIR audits before restart and after final test shutdown
are retained as `fixture-before-video-restart.json` and
`fixture-after-motion-stop.json`. No pending fixture ownership journal remains.

Instrumented client shutdown again stalled, as documented in earlier releases.
After completed data/cleanup and save evidence, only the identified TEST Java
processes and their own launchers were terminated. This limitation is not fixed.

Ordinary `options.txt` was restored byte-for-byte, SHA
`02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`:
1600x900, cap120, pause-on-lost-focus true. Launcher dimensions were restored;
legitimate launch/play counters were retained, not falsely reset. Benchmark JAR
and enabling marker were recoverably renamed `.0.4-release-disabled` and are
inactive. The current configuration selects0.4.0. A fresh ordinary-account
runtime/handoff capture is still pending at this checkpoint; restored files
alone are not that runtime proof.

## Open full-goal work

Missing incident Sun water leg and its bent-ray shadows/receiver normals,
underwater source-depth scattering, remaining real shore boundaries/hue,
ordinary rowing/contact motion, spatial cloud shadows, solar-disk/direct-beam
radiometric coherence and more natural cloud shape remain open. The next
[incident-path plan](../../docs/reviews/codex-water-incident-plan.md) is one
falsifiable slice, not a substitute definition of completion.
