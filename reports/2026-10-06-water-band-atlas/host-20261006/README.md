# Host recovery and bounded FINAL observation — 2026-10-06 JST

The full water/sunlight realism goal remains **unachieved and active**. Host/GPU
access is now available. The earlier sandbox/approval failures in frozen reports
were real historical environment restrictions, not a refusal by the user.

No physical shader, geometry, water density or optical-policy change was made
in this host turn. The diagnose skill kept this to the diagnostic address/read
boundary. Existing phase0/45 physical runs and four geometry role pairs from
Oct3/Oct5 are reused, not rerun. No shipping pack was replaced.

## Actual new evidence

- `native-address-result.json`: native RTX3080Ti, OpenGL4.6 NVIDIA580.173.02.
  Full FINAL pairs linked; a **reduced coordinate-expression main** drew all
  eight tiles. Aligned integer addressing has zero mismatches over1,440,000
  pixels at900p and3,686,400 at1440p. Old expression comparisons report
  1,440,000 and2,548,665 mismatches respectively. Those large old counts are
  fixture results, **not proof those Minecraft pixels were wrong**; varying
  interpolation/reduced-main optimization and the actual draw are not qualified.
- Actual Minecraft/Iris uses OpenGL3.2 NVIDIA580.173.02. New diagnostic-only tilt
  captures are `phase0-tilt-run/` and `phase45-tilt-run/`,1600×900,5s warmup/5s
  measurement each. Mean FPS18.0576 /18.0769, p99 frame57.621586 /56.238392ms.
  These are short **diagnostic Minecraft** timings, not normal0.6, native harness
  timings, performance acceptance, or visual/physical acceptance.
- Fresh original16 selected coordinates were retained. Both
  `phase{0,45}-selected-audit.json` qualify all seven distinct bound RGBA32F
  roles/extents and11 Sun applications /16 points, preserving minimum4.
  Phase0 guard/frame3243 and FINAL/frame956 are separate. Phase45 guard, stage,
  FINAL source and original16 all show counter289; this is not by itself a
  same-invocation producer/draw-freshness proof. The frozen original auditor
  was not widened and no historical raw observation was relabeled.
- `phase{0,45}-v013-final-source.json` contain actual shader source queried at
  ProgramCreator.create RETURN, after link/detach but before ProgramBuilder
  destroys GlShader arguments. Exact active FINAL program cache lookup occurs
  before renderQuad after Program.use/custom uniforms. Actual zero-origin
  viewport and scalar-float viewWidth/viewHeight are1600×900, stable across
  the snapshot. Renderer, stage lengths and SHA256 are recorded.
- `phase{0,45}-actual-final-main-audit.json` compare the entire canonical FINAL
  **main** with the actual Iris-transformed fragment main, allowing only
  whitespace/literal spelling and gl_FragColor→iris_FragData0 transformation.
  Both qualify the linked coordinate/fetch source and view scalars. This does
  **not** qualify all helper semantics, executed texel addresses, actual
  per-pixel image correspondence, producer/draw freshness, or the band fix.

All new source/view/address reports retain `alignedRuntimeAccepted=false` or
`IrisAccepted=false`. No band-point packet was taken: the separate actual
executed-address/freshness gate is still pending. The four old nominal targets
must not be promoted to certified band pixels from this evidence.

## TEST observer failures and narrowly scoped adaptation

Version0.1.0 found no attached shaders at draw time. Pinned Iris bytecode shows
ProgramCreator detaches and ProgramBuilder destroys them after link. Version
0.1.1 moved the read earlier, but scope admission still failed at construction.
Version0.1.2 records the CPU reason: initial construction had no usable world
scope; after reload all live V2 facts matched but `expectedPack=false`.
`Iris.isPackInUseQuick()` requires an already published IrisRenderingPipeline,
which is absent while constructing its FINAL program.

Version0.1.3 substitutes only that construction lifecycle condition: fresh
actual integrated/local-camera/one-player/no-LAN V2 UUID/seed/dimension/Mod
guards remain; selected/current pack name, fresh canonical file hash, enabled
Iris config, V2 generator marker, null unpublished pipeline and no stored Iris
error/fallback are additionally required **before every GL source query**.
At draw time the original full active-pack scope is still mandatory. This is
a material TEST observer gate adaptation, **not an unchanged old gate** and
not a shader admission-policy relaxation. Versioned source archives and failed
raw observations are retained. Version0.1.3 JAR SHA256:
`6ce3747695e5d5e973f2e5c8aa9f1b0414a05abd95ab26ce203a5ad7f54091f0`.

Six CPU source-auditor tests passed: bounded recorded qualification, changed
frame/type/hash rejection, failed-observation rejection, and literal/output
transform discrimination. Pure Java FINAL protocol tests passed when each
new observer was built; these are not GL or negative-world runtime tests.
All TEST observers are now disabled in Lab, so they are absent from ordinary
Minecraft. No ordinary-world observer GL query was needed for return validation.

Other failed diagnostic attempts are not hidden: Qt initially lacked DISPLAY;
help was obtained offscreen and launch used DISPLAY=:1. A guard request first
lacked schema1 and produced no observation until corrected. A metadata-print
attempt had a Python syntax error. The first source audit missed the pinned
Iris gl_FragColor output rewrite and rejected it; the explicitly permitted
output rewrite was then added, with negative normalization tests. A checksum
check used the wrong cwd and reported missing files; all three were subsequently
checked from repository root with exit0 (114/12/8 entries). None of these was
a reproduction/fix of the rendering symptom. OpenAL sound startup still fails
as before; no audio settings were changed.

## Safe return and preservation

Fresh preturn config backups were used, not the stale Oct5 backups. Five active
TEST JARs and six active marker/request files were recoverably renamed with
`.atlas-host-20261006-disabled`. Previous disabled TEST files remain untouched;
older observer versions also remain recoverably disabled. Original physics0.2
was reactivated with its exact starting hash. All five TEST clients were quit
via new UUID-guarded V2 control requests; owned process exits0 and Java absence
were observed before each switch. No broad process kill was used.

`ordinary-restoration.json` confirms byte-exact restoration of the three
fresh configs, only the three original active JARs, and all eight TEST control
names absent. All41 ordinary `新規ワールド` save-file hashes were unchanged
**before ordinary reopening**; no whole-save restore occurred.

The normal Lab was then reopened with `新規ワールド` and remains **live and
paused**, owned exec session **56068**, window62914567, DISPLAY=:1. Real ingame
and pause screenshots were inspected and saved, with the normal game log.
The log identifies Aqualumen0.6 and physics0.2; all eight TEST controls remain
absent and the exact original active JAR hashes match. Live Iris settings are
semantically unchanged; the launcher rewrote its comment timestamp. Fallback
was not queried by a new ordinary-world observer. The physics status JSON left
by0.3 is stale and was **not** used as normal0.2 evidence. Reopening naturally
allows normal save changes; the41-file equality is a pre-reopening guarantee,
not a promise of a permanently frozen live user world. No terrain/time/camera
automation ran in that world. No native GL experiment was run after handoff.

Tracked user work is unchanged:22 files /1517 insertions /102 deletions;
`git diff` SHA256
`ee4e019473a0468d187e9d3567ec1b1e30f4c6a5dc6b0526c494c3dcbfdd52c5`.
Frozen prior manifests114/12/8 all verify. No commit/push or memory write.

## Intended next action — not another physical phase0/45 rerun

1. Keep the paused ordinary client and existing Evidence intact. Check its
   owned handle/state before any scoped switch; a lost tool handle is not a
   clean-exit observation. Take fresh config/save hashes again if switching.
2. Design the still-missing **actual FINAL executed address/output and joint
   image freshness** observation. Link/source/view qualification above is a
   prerequisite, not a substitute. A bounded after-quad color/readback seam
   could test the actual encoded panel pixel against the same invocation's raw
   selected role, but must first qualify framebuffer routing, state restoration,
   passivity and exact-world gates. Do not insert optical changes at this stage.
3. Preserve original16/minimum4 and collect any additional bounded band targets
   only as a separate packet after address correspondence is qualified. Verify
   their relevance on the new aligned images, not the old nominal PNG mapping.
4. If fresh aligned raw records contradict the Sun gate, investigate routing/
   freshness first. If rejection really tracks the dark contours, design one
   admission experiment with energy/boundary acceptance; otherwise return to
   finite integration/receiver/geometry hypotheses. Full visual/energy/motion
   acceptance remains outstanding. Restore normal settings after TEST work.
