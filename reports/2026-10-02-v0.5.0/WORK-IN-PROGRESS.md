# Aqualumen0.5 incident-Sun transport checkpoint

Full realistic-water/sunlight goal remains active. This is not a final visual
acceptance or a minimum-FPS guarantee. The frozen0.4 baseline is commit6dd4e5a,
ZIP5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069.
The0.5 candidate is built and installed only in Aqualumen Lab, SHA-256
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.

## Actual vertical-slice RED/GREEN evidence

All tests link real production main shaders and use coherent total/direct-Sun
texture pairs, not private helpers or copied shader bodies. Actual renderer is
RTX3080Ti, NVIDIA580.173.02, native GL4.6; native probes are not Minecraft FPS.

1. Underwater composite: keep receiver and1m outgoing eye leg fixed, grow the
   incident water depth1.5→3.5m. Raw receiver-Sun response ratios were RED
   `(1,1,1)` and become GREEN `(0.527292,0.843665,0.932394)`, agreeing with
   independent Beer exponentials. Positive response remains; zero-source
   background is unchanged.
2. Same production fixture, subsequent absolute entry-energy behavior: normal
   incidence reflectance is0.0203732. Beer-only RGB response was RED
   `(0.0898658,0.121284,0.0916219)` against expected admitted-power response
   `(0.0880349,0.118813,0.0897553)`. GREEN matches that expectation while
   retaining the incident-depth ratio. No arbitrary IOR-squared gain is applied.
3. Above-water actual water vertex/fragment main: fixed eye/interface, horizontal
   bottom depth1.5→3.5m, coherent C4/C8 lit/unlit pairs, flat public wave option.
   Both incoming and outgoing legs grow2m. RED ratios were outgoing-only
   `(0.527296,0.843645,0.932368)`; GREEN is
   `(0.278069,0.711784,0.869316)`, versus independent two-leg Beer references
   `(0.278037,0.711770,0.869358)`. Constant specular/background terms cancel.

Logs are preserved in [native](native/). The final both-sides `make check`, rerun
as [frozen-final-check.log](native/frozen-final-check.log), passes11 graphics
pairs,3 compute programs and all retained regression controls.
Legacy fixed-total-C0/C8-only controls are correctly labelled channel attribution
and provenance: after Sun-base replacement they do not isolate positive focusing.

## Implementation and limits

C8 stays an immutable raw air-lit direct-Sun decomposition. A flat-interface
Snell direction gives incident path depth/cosWater; exact dielectric Fresnel
entry fraction and RGB Beer attenuation replace only that raw Sun component,
including its base and focusing terms. Existing single outgoing attenuation
remains separate. Confirmed above-water receivers and paired-depth underwater
opaque receivers use this correction. Unknown above-water proxies are unchanged.

The active local plane is not a world water-membership mask. This is a bounded
horizontal-interface approximation: arbitrary receiver normals retain their
old air-directed cosine; bent-ray shadows, disconnected/dry pockets, unknown
proxies, incident diffuse/light paths and depth-dependent water in-scattering
remain unsolved. The0.4 shore confidence proof is not universal bank continuity.
Do not infer that more physically correct direct energy necessarily desaturates
cyan: the unchanged coefficients extinguish red more strongly than blue.

## Runtime/next work

The exact UUID-guarded disposable V2 client completed the16-scene1600x900
[quality capture](real-view/run.json) at20:32:25 UTC. Every capture records the
candidate active without fallback and a focused window. These are5s warmed
samples, not a1440p benchmark or a temporal visual acceptance. The independent
data audit and original PNGs remain in this release directory; real coast/river
images retain strong cyan/mint shallows and serrated dark/clear bands.

After test cleanup/save evidence and another instrumented shutdown stall, only
the identified TEST Java/launcher were terminated. That instrumentation shutdown
defect remains open. The active benchmark JAR and opt-in marker were recoverably
disabled, options were restored byte-for-byte, and a fresh normal-account launch
activated0.5 and physics0.2.0 in the user's existing world. The
[ordinary handoff](ordinary-handoff.json) and native
[current](user-scene/current.png)/[paused](user-scene/paused.png) images verify
1600x900, cap120 and a paused game. No automated ordinary-world camera/time or
terrain operation was used. A live ordinary world naturally saves again after
launch; its pre-test timestamp is not claimed unchanged after normal play resumes.
This separate resolution must not replace the frozen1440p performance baseline.

Remaining real shore hue/bands, natural rowing/wake motion, spatial cloud shade,
solar-disk/direct-beam radiometry and cloud appearance keep the full goal open.
Implementation/test/review is Codex work, not a new Claude call.
