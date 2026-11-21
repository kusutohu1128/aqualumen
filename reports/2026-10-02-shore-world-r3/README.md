# Actual shore surface/ray/receiver snapshot — diagnosis, not a release

The actual Minecraft/Iris diagnostic pack activates without fallback on RTX3080Ti
OpenGL3.2. Its original-color panel still reproduces cyan/mint water and jagged
bands. The ordinary pack remains0.6.0; shipping shader color code was not changed.

## Stronger evidence than an atlas color estimate

The immutable [raw observation](observations/259d112e-d967-4cd3-9aaf-148b28c53a4c.json)
is captured at actual FINAL draw, after Program.use/custom uniforms but before
the quad. Independently reflected final Program21 equals GL_CURRENT_PROGRAM21.
Actual typed samplers C9..C15 use units3..9 and textures71,73,75,77,79,81,83;
each existing level-zero target is1600×900 RGBA32F. All sixteen requested native
integer texels are finite and retain negative absolute world coordinates.
The eleven touched active-unit/binding/PBO/PACK-state values are independently
queried equal before and after. GL error flags are not consumed.

All seven channels belong to **the same original water invocation and frame11329**:

| Channel | Direct production values |
|---|---|
| C9 | weighted transmitted radiance |
| C10 | absolute water-surface XYZ; local-column-known flag |
| C11 | transmitted world direction; receiver confidence |
| C12 | returned-UV opaque absolute XYZ; receiver kind |
| C13 | traced thickness, initial path, original-UV vertical depth, straight path, in metres |
| C14 | original-UV opaque absolute XYZ; confirmed local-column depth |
| C15 | optical world normal; Fresnel |

The snapshot records actual unshifted camera
`(-191.5,65.71999988555908,320.5)` and frameTimeCounter91.464226.
Thirteen points have known water columns, actual water-surface positions and
unit normals/directions. Four have kind1, nine have kind0; three background
points are fully cleared. Kind0 positions equal original-UV opaque positions:
they are **proxy positions, not accepted refracted receivers**. Alpha alone is
not a sufficient water classification; nonwater translucent fragments can
write RGB0/alpha1, while untouched cleared targets are RGBA0.

Selected results include:

| Original texel | Kind / confidence | Traced or proxy path m | Local vertical column m |
|---|---|---:|---:|
| 800,350 | accepted /0.994153 |10.259764 |5.296406 |
| 800,250 | accepted /0.874506 |7.880567 |3.183201 |
| 640,250 | accepted /1 |7.571981 |3.169884 |
| 960,250 | accepted /1 |9.300154 |3.577658 |
| 800,150 | proxy /0 |8.509327 |2.714287 |
| 1000,50 | proxy /0 |8.336278 |1.888889 |

Local vertical depth is at the surface point, whereas a refracted ray can reach
a deeper neighboring column. These numbers alone do not prove a distance bug.
The [saved-terrain ray join](ray-join.json) and its [reader](ray_join.py) compare
all13 qualified directions with the first known saved full-cube collision,
without screen-depth input. Three accepted paths differ by less than0.004m from
that ray intersection. The accepted800,250 path7.880567m differs from the first
saved collision9.189985m: it lies near a stepped-bed edge and is not silently
counted correct. Proxy1000,50 uses8.336278m versus first saved hit4.709128m;
proxy800,450 uses4.955843m versus20.255522m. Neither global shortening nor
local-column-depth substitution is justified by these opposite directions.
Entities/partial-block/visibility/water-membership and same-frame-terrain
qualification remain explicit. The conditional edge discrepancy is a finding,
not yet a verified shader-defect regression or a corrected pixel.

## Limits and verification

The [coast capture](captures/shore-world-r3-20261002-1231/coast-day.png) and its
592 raw intervals completed before this observation, with10s warmup/5s sample,
1600×900/cap120/VSyncOFF,12/6 chunks and a focused exactV2 camera. Their phase is
**not frame11329**. Dynamic waves/clouds were retained, so a screenshot cannot
be used as a pixel-exact image of the later snapshot. This is not the1440p
performance gate, an FPS floor, natural-motion acceptance or a new visual release.

Full-target GL3.2 reads use one bounded reusable NaN-initialized scratch buffer;
only16 texels/target are exported. Seven1600×900 targets transfer161,280,000
bytes. Observation frames are excluded from FPS acceptance. Finite qualification
is only for selected texels, not every texture pixel. Actual sampler objects are0
with level0, linear/clamp object parameters; the diagnostic final uses integer
texelFetch and does not interpolate raw masks. Diagnostic per-buffer blending
is disabled for slots1..7; C0 keeps its original blend. Actual activation and
raw known/kind0 alpha values qualify this pinned-Iris path.

Final's projection/camera uniforms are optimized away, so the observation retains
`geometryUniformsAvailable=false`, `geometryAttributionAccepted=false` and
`runtimeIntegrationAccepted=false`. Coordinates here are the **explicit
water-main MRT payload**, not an invented reconstruction from missing uniforms.
The [independent raw/capture audit](observation-audit.json) and saved-terrain
join are distinct evidence.
No complete geometry/visibility acceptance or physical calibration follows.

[Tool artifacts and CPU/native checks](tools/) retain observer0.3.7
`e89739cb92f65d55309187fc2e58f8e4cfaeb3395167c9fb1b37b39299d045dd`
and probe ZIP `ccd937b89156df9104e6bd1106bae1100f163498242ab1ec8e0ddc89dfe98180`.
Runtime metadata says observer0.3.7 but does not separately hash the loaded JAR;
the stored/installed artifact hash is not that stronger loaded-class proof.
Packaging/CPU observation-tool RED/GREENs are not shoreline shader fixes.
The bounded native shallow-main probe passed before the TEST launch. A later
native comparison was inadvertently run while TEST was idle (12:36:57), after
the recorded12:31:20 timing sample; its log is retained as overlapped and it is
not timing evidence. The [standalone repeat](tools/cpu-native-checks/shipping-native-shallow-standalone.log)
after TEST Java/launcher termination passes the same bounded checks, and its
printed numerical results equal the prelaunch diagnostic native log. This is
not a complete float-image neutrality proof. No ordinary user world was active
during these GPU observations.

## Safe ordinary restoration, not a shutdown fix

Before testing, ordinary GUI Save/Quit saved all dimensions at12:23:25 and
GUI Quit later exited normally. A fresh private post-save backup preserves
that current user play. After the completed r3 observation, TEST GUI Save/Quit
again stalled (12:45:15 player disconnect; no final complete-save marker).
The correct fresh namespace PID26 produced a private thread dump. Scoped TERM
was sent only to identified TEST Java2745419 and its own launcher2745336;
the launch session exited143, not a clean GUI exit. The persisted cleanup
audits retain390 approved cells AIR and no ownership journal. The shutdown
defect remains uncorrected; no full world/entity integrity is claimed.

Normal options, Iris and benchmark properties were restored byte-for-byte to
the fresh backup. The full ordinary-world tree also matched before normal
relaunch. Physics0.2 is restored; physics0.3/observer0.3.7 and both opt-in markers
are recoverably disabled, not deleted. The diagnostic pack is selected off.
Normal relaunch/handoff is recorded separately under [lifecycle](lifecycle/);
normal game writes naturally resume afterward.

The full realism goal remains active. The next correction must exercise the
actual confirmed-depth/view-proxy call pattern with a production-main failing
test, retain bank/viewport/underwater guards and improve real natural scenes.
