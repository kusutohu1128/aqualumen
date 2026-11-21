# Paired water diagnostic: design contract (Claude candidate)

This is a design only. I haven't run anything, and it doesn't claim the view is fixed. I couldn't write the plan file because only Read/Glob/Grep are available, so the full design is below.

## Facts that constrain both candidates (from the files I read)
- `gbuffers_water.fsh:434` runs the single SSR trace. A hit returns `a = length(...)`, which is always more than 0.4. A miss returns `-1`.
- `:435–447` consults the receiver only when the camera is underwater, SSR missed, and `aqualumenReceiverReady ∈ {1,2}`. Inside that block, `reflectedReceiver` (`known`, `sourceReady`, `travel`) is locally scoped.
- So the route can be taken from values the shader already computes, with no second trace:
  - `!underwater`, or `materialId != 10000` → 0, with mask 0.
  - The `a` at :434 is above 0 → 1.
  - SSR missed and ready ∉ {1,2} → 5.
  - `sourceReady` → 2.
  - `known` but not `sourceReady` → 3.
  - Otherwise → 4.
  - Travel is the final `reflectedHit.a` for routes 1 and 2, `reflectedReceiver.travel` for route 3, and 0 otherwise. Fresnel is `fresnel`.
- `shaders.properties:17` sets `blend.gbuffers_water=SRC_ALPHA ONE_MINUS_SRC_ALPHA …`. That blend would apply to C12 too: a non-water fragment writing `vec4(0)` would leave a stale water class under stained glass. The TEST pack therefore **must** add `blend.gbuffers_water.colortex12=off`.
- Nothing in `shaders/` mentions `colortex12`. Its format and clear behaviour have to be declared explicitly.
- Only `lib/uniforms.glsl:12` declares `frameTimeCounter`. `rippleState` is called from `water_geometry.glsl:8` (displacement and receiver corners) and `gbuffers_water.fsh:301`. Both go through `lib/ripples.glsl:8`.

## Shared generated transforms (control and paired, identical)
Each transform is an exact-anchor replacement that must match exactly once:
- **Wave phase:** `uniform float frameTimeCounter;` becomes `const float frameTimeCounter=17.0;`. Before applying it, the generator enumerates every file under `shaders/` that references `frameTimeCounter` and requires that set to equal a pinned list. That catches any compute/`begin.csh` use; the parent should check the `dt` semantics there, since the simulation is explicitly not validated.
- **Ripples:** `if(aqualumenActive==0) return vec3(0.0);` becomes `return vec3(0.0);`.
- Both variants record the qualification string `wave_phase=17.0;interaction_ripples=disabled`.

## Candidate 1 (recommended): passive C12 MRT plus an observer on the same FINAL invocation
**Paired `gbuffers_water.fsh` copy** (anchor transforms):
- `/* DRAWBUFFERS:0 */` becomes `/* RENDERTARGETS: 0,12 */`.
- Declare `float pairedRoute=0.0,pairedTravel=0.0;` before :434.
- Right after :434: `if(underwater) pairedRoute = reflectedHit.a>0.0 ? 1.0 : ((aqualumenReceiverReady==1||aqualumenReceiverReady==2) ? 4.0 : 5.0);` and set the travel the same way.
- Inside the receiver block, after `reflectedReceiver` is assigned, set route 2 or 3 and the matching travel.
- Non-water branch (:265): `gl_FragData[1]=vec4(0.0);`.
- Water exit (:469): `gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);`.
- No existing expression or branch changes, so C0 is identical by construction. The native test checks this.

**Paired `final.fsh` copy:**
- Add `uniform sampler2D colortex12; uniform int aqualumenPairedView;`.
- After line 29: `if(aqualumenPairedView==1) gl_FragColor=vec4(clamp(texture(colortex12,texcoord).xyz*vec3(0.2,1.0,1.0/48.0),0.0,1.0),1.0);`
- Add a comment-block directive: `colortex12Format=RGBA32F`, `colortex12Clear=true`, `colortex12ClearColor=vec4(0)`.
- **Paired `shaders.properties`:** `uniform.int.aqualumenPairedView=0` and the C12 blend-off line.
- **Iris feasibility:** a branch on a uniform can't be constant-folded, so the `colortex12` sampler stays active.
  - If Iris 1.8.8 doesn't register the `uniform.int` line, the GL link default is still 0.
  - Either way, the observer records whether the uniform is registered and its value is 0. It doesn't assume either.

**Generator (Claude-owned), `tools/water_paired_diagnostic.py`:**
```python
@dataclass(frozen=True)
class Transform: path: str; anchor: str; replacement: str
class SourceShapeError(Exception): ...
PINNED_SOURCE_SHA256: dict[str, str]                  # every touched root file
def variant_files(root: Path, variant: Literal["control", "paired"]) -> dict[str, bytes]
def generate(root: Path, out_dir: Path) -> dict       # manifest; O_EXCL zip, refuses dist/
```
- A hash mismatch, a missing or duplicated anchor, or any other program writing C12 (`RENDERTARGETS`/`DRAWBUFFERS` scan) raises `SourceShapeError`.
- The output is deterministic: sorted entries and a fixed ZIP mtime.

**Observer (parent-owned).** This is a new package derived from the `JointMixin` before/after `renderQuad` bracket; the hardcoded layout is not reused.

*Before the quad:*
- Snapshot `GL_CURRENT_PROGRAM`.
- Find the `colortex12` and `colortex0` locations, then `glGetUniformi` to get their texture units, then `GL_TEXTURE_BINDING_2D` on each unit to get the **actual bound texture IDs**. This avoids any flip assumption.
- Record `aqualumenPairedView` (must be 0), the viewport, the draw FBO, and the frame counter.

*After the quad:*
- Attach the recorded C12 texture to a temporary read FBO and read it with `glReadPixels(RGBA, FLOAT)`.
- Read the final draw FBO as `RGBA8` `UNSIGNED_BYTE`.
- Require: internal format `GL_RGBA32F`, size equal to the viewport, and the final attachment's `COLOR_ENCODING` is `LINEAR`.

*State saved and restored:* read FBO, read buffer, `PACK_ALIGNMENT`/`ROW_LENGTH`/`SKIP_*`, `PIXEL_PACK_BUFFER`, active texture, and the temporary FBO (deleted). After restoring, it re-snapshots and compares.

*Record:*
```java
record PairedWaterCapture(long frame, int program, int vw, int vh, int c12Unit, int c12Tex, int c12Fmt,
                          int c0Tex, int finalFbo, int finalEncoding, int pairedView,
                          String packSha256, double[] camera, Path beautyRaw, Path classRaw)
```

*Capture is rejected when:* any check fails, the program or frame differs between before and after, any non-finite value appears, a route isn't an integer in 0–5, a mask isn't 0 or 1, a mask-0 pixel is non-zero, no pixel has mask 1, or the UUID or pack hash doesn't match.

## Candidate 2: same-frame atlas in FINAL
- It still needs the same C12 producer, and it adds a FINAL that writes beauty and class into split addresses of the RGBA8 output.
- It can't be full resolution, and it changes what FINAL shows, so it isn't production beauty.
- It quantizes Fresnel and travel to 8 bits and needs its own encoding contract.
- Its only advantage is that a plain screenshot reads it, with no sampler-identity hunting.
- It loses on alignment, production-colour invariance and lossless data, and it ties no actual resource identity. That's worse on every criterion in the contract except observer simplicity.

## Selection and falsifiers
**Base: Candidate 1.** Any one of these falsifies it, in which case fall back to Candidate 2 at half resolution, labelled non-production:
- The final program has no active `colortex12` location, or the unit lookup is ambiguous.
- The bound texture isn't `RGBA32F`, or its size differs from the viewport.
- The `renderQuad` ordinal 0 isn't the single final quad.
- The final FBO encoding is sRGB or not `RGBA8`.
- `aqualumenPairedView` is not 0.
- The native C0 bitwise invariance test fails.
- The native test shows the blend override was ignored (a stale class survives under glass).

## Verification
**Native (NVIDIA; record `GL_RENDERER`):**
- Compile and link all programs for both variants.
- Synthetic harness for control vs paired `gbuffers_water`: C0 must be bitwise equal.
- Positive cases: SSR hit → 1, ready=0 → 5, valid source → 2, `source.a≠1` → 3, origin outside volume → 4, camera above water → 0, glass over water → 0 with blend off, discard → clear 0.
- Negative cases: a mutant route assignment fails, and a removed or duplicated anchor raises.

**Real Minecraft (Aqualumen Lab, V2 UUID only):**
- The log shows the TEST pack active with no fallback.
- One capture passes every check above, including restored state.
- The control pack has no C12 binding.
- Normal mods, configs and instance settings are restored and the ordinary save is preserved.
- Any control vs paired beauty comparison is reported only as similarity, never as proof of pairing.

## Ownership
- **Claude:** patch text for `tools/water_paired_diagnostic.py` and `tools/test_water_paired_diagnostic.py`.
- **Parent:** the observer mod, its mixin and build, the `display_water_runtime.py` lifecycle, the native harness, installation, and all runs.
- Root `shaders/` files stay untouched.
