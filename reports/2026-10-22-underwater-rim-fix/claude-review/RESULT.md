**Bottom line:** R1 is strong enough to justify a bounded TEST candidate that corrects the hit point. The patch text is below. It shows that production's normals don't match the true eye-ray hit on these qualified pixels. It does not prove that any particular curl is unphysical, and the reference still has 4 (near) and 11 (deep) TIR components with broad folds. Everything here comes from reading files only (15 Read/Grep/Glob calls). I didn't write a plan file because I have no write tool in this session.

## 1. Is the R1 evidence enough?

Yes, for a TEST candidate:
- **Field match:** normal parity is 100% (P999 1.8e-7). All footprints are below the floor (max 0.93 mm near, 6.4 mm deep). The flat control passes and the 32- and 48-step roots are identical.
- **The test can see a defect:** the forced +5 cm control gives p95 99 px and IoU .79, so the test detects a deliberate defect.
- **Near fails clearly:** p95 29 px against the 4 px gate. In the near-tongue ROI the IoU is .077. The reference's largest TIR component there is 3960 px; production's is 213. The tongue is almost entirely hit-point disagreement.
- **Deep fails too:** p95 6.32 px and an XOR component of 1001 px (gate is 200).

**Why the strict residual fails (not a solver defect).** The camera is at x=448.5. The float spacing at that magnitude is 3.05e-5 m. With slope bound .676, rounding absolute XZ alone shifts the height by about 1e-5 per axis, about 1.5e-5 combined. That matches the 1.58e-5 maximum. Keeping 10 µm as a per-pixel offline exclusion is fine. However, the shader candidate can't do better than this floor, so it must not gate on |residual| < 1e-5. Its certificate should be the sign-bracket invariant plus the monotonic margin.

**Metric defects found:**
1. **Strict mode leaks excluded pixels into boundary distances.** `compare()` restricts the source boundary pixels to the eroded support, but `a`/`b` are not masked before dilation, erosion and the distance transform. Excluded pixels can still act as nearest boundaries. Use `a&support` and `b&support` before computing boundaries.
2. **ROIs aren't per-scene.** The near result includes deep-scene ROIs (deep-*-loop) and the deep result includes near-tongue. Those entries mean nothing and should be dropped or labelled.
3. **No uncertainty band at the threshold.** F ≥ .9999 against F ≥ .9999 is a knife edge, and the earlier parity was only within 1.9e-4 in F. Add the critical-band mask from section 3.

The solver itself looks correct. The global Lipschitz margin guarantees a single root in the bracket. Bisection keeps the sign invariant, and depth 16 with zero gradient is valid for this frame.

**Why `column.x ≥ 0.8` is exact, not a heuristic:** at depth ≥ 0.8, `shore` is exactly 1.0 and `taperDerivative` is exactly 0 (`waves.glsl:56-63`). So any deep column gives exactly the depth-16 reference field.

## 2. Patch text (opt-in pack copy only, behind `AQUALUMEN_HIT_TEST`)

**Helper**, placed before `main()` in the copied `gbuffers_water.fsh`:
```glsl
#ifdef AQUALUMEN_HIT_TEST
// TEST: first eye-ray root on the same filtered full-detail field that supplies
// the optical normal. Deep columns only (shore==1, zero taper derivative).
// Status: 0 solved, 1 no monotonic margin, 2 column unknown/shallow, 3 bracket.
const float hitFootprint=0.035;
vec2 hitWaveBounds() {
    float variance=0.0,heightBound=0.0,slopeBound=0.0;
    for(int i=0;i<WAVE_COMPONENTS;i++) {
        vec2 d;float k,w,p;waveMode(i,d,k,w,p);variance+=0.5*w*w;
        float amplitude=abs(w)*exp(-0.25*pow(k*hitFootprint,2.0));
        heightBound+=amplitude;slopeBound+=amplitude*k;
    }
    return vec2(heightBound,slopeBound)*(0.5*abs(WAVE_HEIGHT)/sqrt(max(variance,1e-6)));
}
bool hitDeepResidual(vec3 point,float meanY,out float residual) {
    vec3 column;float variance;residual=0.0;
    if(!localWaterColumn(point.xz,meanY,column) || column.x<0.8) return false;
    residual=point.y-meanY-localWaveState(point.xz+cameraPosition.xz,frameTimeCounter,hitFootprint,column,1.0,variance).x;
    return true;
}
int waterHitTest(vec3 eye,vec3 ray,float meanY,out vec3 hit) {
    hit=vec3(0.0);vec2 bound=hitWaveBounds();float r;
    if(ray.y-bound.y*length(ray.xz)<=0.00001) return 1;
    float lo=max(0.0,(meanY-bound.x-eye.y)/ray.y),hi=(meanY+bound.x-eye.y)/ray.y;
    if(!hitDeepResidual(eye+lo*ray,meanY,r)) return 2; if(r>0.0) return 3;
    if(!hitDeepResidual(eye+hi*ray,meanY,r)) return 2; if(r<0.0) return 3;
    for(int i=0;i<24;i++) {
        float mid=lo+(hi-lo)*0.5;
        if(!hitDeepResidual(eye+mid*ray,meanY,r)) return 2;
        if(r>0.0) hi=mid; else lo=mid;
    }
    hit=eye+(lo+(hi-lo)*0.5)*ray;return 0;
}
#endif
```
Two deliberate differences from the reference:
- **Strict sign checks at the bracket ends** instead of the reference's ±1e-5 tolerance. A failure falls back to original shading.
- **24 steps** shrink a ~1 m bracket to about 6e-8 m, below the float spacing of s.

**Call site, replacing lines 296–306:**
```glsl
    int hitStatus=-1; // -1: not a candidate (air, nonwater, unknown, side, ripple, footprint, shallow)
    vec3 opticalPosition=worldPosition;
    if (upperSurface) {
        n=rasterFacet;
        if (localColumnKnown) {
            vec2 waveX=absolutePosition.xz;
            #ifdef AQUALUMEN_HIT_TEST
            if (underwater && abs(worldPosition.y-aqualumenGrid.w)>=0.30
                && footprint*1.25<=0.035 && localColumn.x>=0.8) {
                vec3 eye=relativeWorld(vec3(0.0)),hit;
                hitStatus=waterHitTest(eye,normalize(worldPosition-eye),waterMeanSurfaceY,hit);
                if (hitStatus==0) { opticalPosition=hit; waveX=hit.xz+cameraPosition.xz; }
            }
            #endif
            wave=localWaveState(waveX,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);
            if (abs(worldPosition.y-aqualumenGrid.w)<0.30) { /* unchanged ripple block */ }
            n=normalize(vec3(-wave.y,1.0,-wave.z));
        }
    }
    vec3 opticalViewPos=(gbufferModelView*vec4(opticalPosition,1.0)).xyz;
```

**Eligibility and fallback:**
- **Untouched paths:** above-water, nonwater, unknown/mixed vertices, sides and ripple-active pixels never enter the new branch. Any status other than 0 runs the exact original expressions.
- **Ripples:** if the frozen pack leaves the ripple branch active at the mean surface, the candidate count will be about 0. Report that; don't relax the condition. The generator should switch ripples off at the source.
- **Remaining risk:** "all intermediate lookups deep" is checked only at the bisection samples. A shallow pocket smaller than one sample spacing on the segment could be missed. That's acceptable for this uniform-16 m frame but is not a general certificate.

**Origins:**
- **Must move:**
  - The normal's evaluation point (done above).
  - Refraction trace origin, line 367: `viewPos` → `opticalViewPos`.
  - TIR reflection trace, line 434: `viewPos+normalView*0.06` → `opticalViewPos+…`.
  - Reflected world receiver, lines 437–438: `worldPosition+n*0.06` → `opticalPosition+n*0.06`.

  The hit lies on the eye ray, so the screen start pixel doesn't change; only the start depth shifts by Δs. Changing only the normal and leaving these origins is the partial fix you described and must be labelled that way.
- **Can stay for this TEST (declare as partial):**
  - `v`: same ray, so F differences come only from n.
  - Shadow origin, line 345: cm offset, far below a shadow texel.
  - Line 442 `absolutePosition.y`.
  - The `searchSeed`/caustic lines: above-water only.
  - The grazing blend's `rasterFacet`: blend is 1 here.
  - The derivative footprint, C0 depth and geometry.
- **Side effect to note:** `normalVariance`, which uses dFdx(n), will jump at status boundaries. It affects roughness, not F.

**Observer:** keep C1 as the raster point. In the candidate schema only, set **C3 = vec4(opticalPosition, float(hitStatus))**. The original proof jar and schema stay unchanged.

## 3. Fail-first match and gates

**Fail-first:**
- The original pack's C12/F against R1 already fails; record those runs as the failing baseline.
- The candidate with a TEST-only `+0.05` offset on the root must also fail the same match.

**Invariance:**
- In the candidate capture, C1 and C14 must be byte-identical to the original capture, proving geometry, depth and view are unchanged. That lets the existing R1 be reused as the reference.
- For pixels with hitStatus ≠ 0, plus air captures and unknown-column captures, every MRT except C3 must be byte-identical to the original pack. Report any ULP differences rather than waiving them.

**Candidate point proof** (native probe re-run on C3, hitStatus==0 pixels):
1. Root distance along the ray: |s_C3 − s_R1| ≤ 2 float-spacing units of s.
2. The offline 10 µm residual as a per-pixel exclusion, with counts.
3. The field normal at the C3 point matches C13 within 2e-4 for at least 99.9% of pixels.
4. Sign certificate: residual ≤ 0 just before the root and ≥ 0 just after.

**Mask match:**
- Support S = R1-valid ∩ hitStatus==0 ∩ strict-pass ∩ ¬U, where U = |k_R1| ≤ 1e-3. That is roughly 3× the k change produced by a 2e-4 rad normal tolerance.
- Pass requires XOR = 0 on S, p95 boundary ≤ 1 px with the masked boundaries from defect 1, and no near-tongue XOR component of 200 px or more.
- List every excluded and uncertain pixel. Make no whole-frame claim if any are excluded.

**Gates that stay open:** R2 (sub-pixel physical visibility and coverage), continuous-surface occlusion of other geometry, sky/reflection radiance, actual-Iris runtime and release. Passing this TEST shows only that the optics match the true hit on this frozen field; it does not show the broad curls are gone.
