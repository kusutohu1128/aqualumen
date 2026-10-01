# Aqualumen 0.3.1: opaque-foreground cloud ghosting

2026-10-02 JST. RTX 3080 Ti / NVIDIA 580.173.02, Minecraft 1.21.1,
Fabric Loader 0.19.5, Iris 1.8.8, Sodium 0.6.9, Java 21.0.7.

Status: native GPU/CPU, eight Minecraft occlusion controls and ten compatibility
scenes passed. The original normal-play world/account has been reopened.

## Diagnosis and narrowly scoped fix

The user reported partly distant blocks looking translucent and confirmed this
also affects land, not only underwater receivers. A supplied screenshot of the
exact symptom was unavailable, so the report does not claim an exact visual
match to every aspect of that report. Solid terrain alpha is one; vertex alpha
is used for ambient occlusion, not material opacity. It was not changed.

The production foreground composite used the full distant sky/cloud image as
local aerial haze. A deterministic real-GLSL regression held opaque color,
depth, atmospheric radiance and direct-light transmittance fixed, changing only
background cloud radiance by +4. At 128 m, the red channel changed
0.0713577 → 0.640898 (difference 0.56954), with output alpha still one. The test
failed before the fix: [captured RED output](foreground-cloud-red.txt).

`prepare` now writes cloud-bearing sky to `colortex6` and cloud-free atmosphere
to `colortex7`, both 1024×512 RGBA16F. Foreground aerial haze samples only the
second. Visible sky, reflections and cloud attenuation of solar illumination
still use the first; legitimate haze and shadows are not removed. Integration
of the clear atmosphere is shared. The extra ping-pong pair costs approximately
8 MiB, plus one 4 MiB attachment write per frame.

[Final native NVIDIA output](glcheck-release.txt) passes all 11 draw pairs and
three compute programs, including actual production composite probes:

| Opaque receiver | Fixed clear/cloudy foreground red | Cloud-only difference |
| --- | ---: | ---: |
| 16 m | 0.0528525 | 0 |
| 64 m | 0.0610887 | 0 |
| 128 m | 0.0713577 | 0 |

The production `prepare` MRT test verifies both complete outputs, separate
cloud radiance (maximum difference 5.43176), valid clear/cloud-attenuated solar
cache values, alpha one and reserved-row sky exclusion. Pinned Iris 1.8.8
bytecode inspection additionally confirmed `DRAWBUFFERS:67`, independent
texture flipping, sampler7 handling and equal attachment dimensions. The native
test is not a Minecraft FPS test or full physically calibrated atmosphere.

The diagnose/TDD workflow made the failing production-path assertion a release
regression, rather than merely changing terrain transparency settings.
[Actual Sonnet contribution and verification responsibilities](../../docs/reviews/sonnet-v0.3.1-implementation.md)
are recorded separately.

## Additional water correctness corrections

`waterCaustic` no longer evaluates fragment derivatives after varying-depth
early returns or within conditionally executed caller paths. Both fragment
callers evaluate the receiver footprint before varying branches and pass it in.
Above-water caustics explicitly require the Earth atmosphere dimension. These
resolve inherited source-level hazards, not experimentally established causes
of every shoreline color or shimmer issue. The footprint is an approximation
from the original view-ray receiver, not the converged refracted endpoint.
No water extinction/scattering coefficients, terrain alpha or haze density
were changed. The physics contact Mod remains unchanged at 0.2.0.

The GLSL derivative rule is documented by the
[Khronos specification](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.3.30.pdf).
The MRT integration follows the Iris
[draw-buffer directives](https://shaders.properties/current/reference/constants/drawbuffers/)
and [color-buffer sizing](https://shaders.properties/current/reference/buffers/colortex/).

## Frozen artifacts

- Shader ZIP SHA-256: `d32ce1763e7b48573c544dba9ae476ea2bf910725cbf365140140a1d1708e856`.
- Unchanged physics JAR SHA-256: `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.
- Installed test-only benchmark 0.3.1 JAR SHA-256: `c8ccb66ef30d4c5aa86ef0e5e75733c3724a92971c019fc3ebe342ef57c4c400`.
- Benchmark Recorder.class SHA-256: `b9d7289ef423cd6436255439898e523459f69b5eb9aece7118a69cd399f410a2`.

## Minecraft occlusion controls

Eight 10 s warmup + 10 s sample scenes completed at 2560×1440, 12/6 chunks,
BALANCED, VSync off and recorded frame-limit 260, in the exact disposable
`AqualumenNaturalV2` UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`.

These use temporary white concrete walls at approximately 16.5 and 144.5 m
and magenta/lime targets six metres behind them. Wall-removed images are
positive controls. Exact first-person rendered camera versus measured player
eye position is checked within 0.05 m. All 130 reserved cells must be exact AIR
before placement, every placed state is journaled, unexpected replacement
states are preserved, and clean completion requires scoped restoration to AIR.
No fixture is placed in the user's `新規ワールド`. Root visually reviewed the
near/far closed and open magenta captures: the bright target is visible without
the wall and hidden by its uninterrupted solid silhouette with the wall present.
The [eight-scene raw data and images](opaque/RESULTS.md) retain both color variants,
actual eye/camera checks and before/placed/cleanup journals. All eight scenes
completed with scoped cleanup; no fixture ownership journal remains.

A [read-only saved-Anvil audit](fixture-air-audit.json) after the test client stopped independently found
all 260 unique approved wall/target cells to be exact `minecraft:air` in the
four saved chunks (27,-23), (28,-23), (27,-15) and (28,-15). It did not edit any
world or send control requests. This also checks disk restoration despite the
test-only programmatic quit defect, not merely an in-memory cleanup assertion.

These scenes test ordinary geometry occlusion, not an independent causal
cloud-ghosting experiment: moving clouds/exposure prevent pixel-exact comparison
of sequential images, and the original defective composite may also hide the
colored target correctly. The separate native production test establishes the
cloud-radiance leak and its correction.

## Compatibility and handoff

[Ten-scene compatibility data and captures](compatibility/RESULTS.md) completed
with five seconds warmup and five seconds sampling per scene: ocean day, coast,
dusk, night, rain, underwater, cave water, layered glass, Nether and End. The
final scene was End; the client returned to its identified local Overworld
player/camera before the unchanged strict completion guard passed.

Root visually reviewed coast, underwater, night, cave, glass, Nether and End.
The underwater seabed/plants remain faintly visible without a black fallback;
night water is dark, cave stone remains opaque, and glass is intentionally
transparent. Nether/End retain their dimension-specific environments rather
than Overworld clouds. Coast water still has strongly cyan/turquoise patches
and sharp boundaries; the derivative correction does not establish a visual
fix for those. Static images do not verify temporal stability.

The eight Overworld compatibility scenes averaged 167.4–225.0 FPS, with worst
sampled interval 10.26 ms; Nether/End averaged 595.4/669.5 FPS. Every recorded
interval in this short suite was below 16.667 ms. Durations and workload differ
from prior reports; no arbitrary-world floor or causal performance gain is
claimed. Timings include frame pacing; `frame_limit=260` is the recorded
setting, not a demonstrated hardware-throughput limit.

The original `新規ワールド` was saved through its game menu before stopping the
user client; the log confirmed all three dimensions were saved. Only the
disposable test save was used for automated cameras and fixtures. The benchmark
client's programmatic quit hung after `Stopping!` and player disconnect; after
more than 40 seconds, its exact verified Java process was terminated with TERM.
This happened after both completed runs and runtime cleanup, not in the user's
world. Startup/measurement acceptance is separate from this tooling exit defect.

The test JAR and enable marker were renamed to disabled files, not deleted.
Original options were restored exactly to the captured pre-test file, including
1600×900, 120 FPS cap and pause on lost focus. A fresh launch without the offline
test-account override reopened `新規ワールド` as the original `kusutohu1128`
account, loaded 17 mods including physics 0.2.0 and no benchmark, selected
`Aqualumen-0.3.1.zip` and created the Overworld pipeline on the actual NVIDIA GPU.
The installed shader SHA matches the reproducible build. The
[normal world capture](normal-play.png) shows the original hills/shoreline, and
[debug capture](normal-play-debug.png) confirms the active 0.3.1 ZIP, BALANCED,
1600×900, 12/6 chunks, actual RTX 3080 Ti and 120 FPS target (118 instantaneous).
`jcmd VM.flags` independently confirms Generational ZGC and 2/6 GiB heap.
Debug display was turned off and the original world left paused for handoff.
This normal-play snapshot is a configuration smoke check, not an uncapped
benchmark or an exact before/after reproduction of the user's symptom.
No account tokens,
launcher authentication command lines or unrelated saves are included here.

## Remaining limitations

The user prioritizes visual quality over a strict FPS floor. Short captures
record observations, not arbitrary-world minimum-FPS guarantees. Existing 0.3
limitations remain: turquoise shallow water, screen-space refraction boundaries,
procedural clouds, approximate local contact waves and no full GI/TAA or
Navier–Stokes water simulation. Mipmapped cutout textures and final edge
filtering are not ruled out for every possible translucent-looking scene.
Water caustics placed in Nether/End are not claimed tested by dimension-only
smoke captures. The inherited `depth >= 0.999999` sky classification can also
replace geometry extremely close to the projection far plane; this is distinct
from the reproduced cloud-radiance leak and is not ruled out by 144 m tests.
Historical reports and pre-fix evidence remain version-specific.
