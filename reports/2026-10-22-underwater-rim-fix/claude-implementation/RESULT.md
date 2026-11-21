I can't name a remaining source defect from the current data, and I haven't proven one. The new data narrow the open question to one invariant that nothing has tested yet. My hand estimate says the broad curls are what this wave spectrum should physically produce at the near camera depth. A ray-traced reference against the real surface would settle it, and the existing native GL probe pattern can run it cheaply. I'm not proposing a patch, because a source-proven patch can't exist yet. No edits or commands were made, and I used 16 Read/Grep calls.

## What the data now establish

- **Snell/Fresnel are correct for the normal and view the shader actually used**, in both frames (direction within 3.1e-5, F within 1.9e-4).
- **The grazing blend never fires:** `grazingChanged` is 0 in every region and blend = 1.
- **Downward exit rays are rare** (206 near, 173 deep) and have no screen receivers. My first hypothesis is withdrawn.
- **The pixel-footprint filter is inactive in both frames (estimate; the reference will check).** `gbuffers_water.fsh:299` uses `max(footprint*1.25, 0.035)`. Near-frame pixels are 0.63 m from the camera and deep-frame pixels about 4.6 m, so footprints are roughly 0.001–0.007 m, below the 0.028 m where the 0.035 floor stops applying. If so, the optical normal is one fixed, continuous field, and "normals inconsistent across pixel footprints" is ruled out for these frames.
- **The near tongue comes from waves the mesh doesn't contain.** At (1430,200) the mesh normal is flat (0.45°), but the optical normal tilts 3.4° outward. The fragment sits 4.7 cm below the mean surface, and the camera is only about 0.50 m below it (`colortex1.w` = 0.4989). Incidence is 47.7° against a critical angle of 48.6°, so a pixel just inside the window is expected there.

## The remaining untested invariant

**Hit-point consistency.** Each pixel's normal should equal the normal of the defined surface at the point where that pixel's eye ray first meets that surface.

Production breaks this by construction:
- The visible point is the ray's hit on the coarse mesh (low-detail height, 1 m linear facets).
- The normal is the gradient of the full-detail, filtered height field, evaluated at that mesh point rather than the true hit.

The previous ablations (factor-4 mesh, low detail, raster facet) changed the surface or the normal. None of them measured the rim against a ray hitting the same surface the normal comes from.

**Expectation (hand estimate, not evidence).** With WAVE_HEIGHT 0.12 and WIND 1, the peak wavelength is 8 m. Slope variance comes about equally from 0.35–3 m modes, giving roughly 8° RMS slope (about 5.6° per axis).
- **Near frame:** the window radius on the surface is about 0.57 m. A ±5.6° tilt in the incidence plane moves the local rim between about 0.47 and 0.69 m. The lobes are about the size of the window, so broad tongues are what you'd expect. This matches Lynch (2015).
- **Deep frame:** the window radius is about 3.7 m across many wavelengths, so expect a ragged rim with loops about one wavelength in size.
- **Hit-point error:** short-wave height (about 1 cm RMS) plus facet error gives Δx of about 1–2 cm. That changes the normal by about 0.5°, enough for a few pixels of rim shift but not for tongues.

That is only a prediction; the test below decides it.

## Next step: reference test (diagnostic only, no production change)

Build `tools/water-surface-reference-probe.h` the same way as `tools/bathymetry-gradient-probe.h`. That probe expands the unchanged `lib/settings.glsl`, `lib/bathymetry.glsl` and `lib/waves.glsl` and checks for NVIDIA. Reusing the production spectrum this way avoids a transcription error. The probe runs once per frame on the existing optics3 near and deep raw fields, uploaded as RGBA32F textures.

**Inputs per pixel:** `colortex1` (camera-relative position and mean surface Y), `colortex14` (v), `colortex2.w` (flags), and classification (production F). Use only pixels with flags == 3. Supply `cameraPosition` from the scene record, time = 17.0 (explicitly, to match the freeze), and column = (64,0,0). Eye at the origin is confirmed by the sample: v = −normalize(P) within 1e-6.

**Gate 0, parity (must pass before any comparison).** Evaluate `localWaveState(P.xz + camera.xz, 17, 0.035, column, 1, var)` at the recorded P and form n. At least 99.9% of pixels must match recorded `colortex3` within 2e-4. This checks spectrum, time, phase precision and column.
- If parity fails only where the depth taper is active, the column must be recorded in a new diagnostic capture channel. Don't guess it.
- Also log the measured footprint distribution (from P differences) to confirm the 0.035 floor is everywhere.

**R1, same field at the true hit.**
1. Along the pixel ray P(s) = P + s·d with d = −v, solve P.y + s·d.y − meanY − h_f(xz(s)) = 0. h_f is the same filtered full-detail height (component x).
2. Bracket ±(bound + 0.05)/d.y, march in 2 mm steps, then bisect 30 times.
3. Take the first root on the eye side. Record the number of roots in the bracket (shows any visibility ambiguity).
4. At the root, compute n_ref and k_ref, using the same flip toward v.
5. Output Δs, the angle between n_ref and the production n, and the TIR mask.

**R2, pixel-integrated physical surface.** Same procedure with footprint 0 and a 4×4 stratified sub-pixel ray grid built from the neighbouring recorded rays. Output TIR coverage C ∈ [0,1].

**Controls (prove the test can detect a defect):**
- Positive: with flat water (WAVE_HEIGHT forced to 0 in the probe only), the rim must be the 48.6° circle within 1 px.
- Negative: R1 with the root forced to s + 5 cm, or with the low-detail normal, must fail the metric below. A test that can't detect a deliberate defect isn't decisive.

**Metric.** Compute it over each declared ROI and over the rim band, meaning pixels whose view angle from vertical is within ±12° of 48.6°. Use the production mask M_p = F ≥ 0.9999.
1. Symmetric boundary distance between M_p and M_R1: mean ≤ 1.5 px and 95th percentile ≤ 4 px.
2. No connected XOR component of 200 px or more, which is tongue scale.
3. Same count of TIR components of 50 px or more in each ROI.
4. In the rim band, IoU(M_p, C_R2 ≥ 0.5) ≥ 0.95, with no XOR component of 200 px or more.

## Decision

- **Everything passes:** the broad curls, notch and dark outside are physical consequences of the defined spectrum at this camera depth. The optics are not at fault, so there is nothing to fix. Reducing the curls would mean changing the spectrum or depth, which is an artistic decision for you to make, not part of this task. Further work then becomes a separate radiometry check across the rim, not a geometry change.
- **R1 fails (XOR tongues or a boundary distance above 4 px):** the hit-point inconsistency is the defect, and R1 is its fail-first test. The patch would be a few secant iterations in `gbuffers_water.fsh` that move `absolutePosition` along −v onto the filtered full-detail height before line 299. That keeps the normal, spectrum, IOR and Fresnel unchanged, and it must then pass the same metric. I'd write the patch text only after this failure is shown.
- **R1 passes but R2 fails:** the 0.035 floor filter is shaping the rim. That's unlikely, since it only removes wavelengths under about 0.2 m. Report it before changing anything.
- **Multi-root pixels cluster on a curl:** visibility is missing, a separate defect. Report its extent.

This isn't a repeat of any earlier attempt: the factor-4 mesh, v80/v90/v91/v92, low-detail and quadrature runs all changed production. This test leaves production untouched and compares the rim against an exact ray–surface solution on the same field.
