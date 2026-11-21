# Underwater Snell-window rim: a ray-direction bug is the likely cause of the curled folds

I've proposed a mechanism, a single experiment that picks the next patch, and a fix to apply only if the experiment supports it. Nothing has been run. I used 18 Read/Grep calls and made no edits, commands, subagents or network calls.

## Bottom line

The likely cause is in `gbuffers_water.fsh:360-374`. Near the critical angle, the ray leaving the water heads downward in world space (`transmitted.y < 0`), and the shader still treats it as reaching open sky. This happens in exactly the pixels where a wave tilt pushes the window outward. Those rays sample the lower half of the sky lookup table (LUT), which describes the atmosphere looking down from at least 2 m altitude (`prepare.fsh:32-39`), not a water surface. Underwater, `refractionTrace` also has no check that a hit is on the air side, so it may accept a hit on underwater geometry.

The result is a brightness jump wherever the exit direction crosses horizontal. The outline of that crossing is drawn across the wave normals, which would produce the loops, rings and curled tongue in the captures. A real wavy window has a wavy edge and dark islands inside it where light is totally reflected (TIR). It has no seam where the exit ray crosses the horizon.

## Why the outward rim always produces downward exit rays

Take a ray heading away from the camera at θ from vertical, hitting a surface tilted away by α. It refracts out only if θ−α < θc. So every part of the window beyond the flat-water critical circle needs α > 0.

Near the critical angle the exiting ray runs almost along the tilted surface, which slopes downward by α. Its elevation is therefore about −α, plus a small amount that grows as the incidence moves inside the critical angle. **The bands of pixels that extend the rim outward are therefore the same pixels whose exit rays point below horizontal.**

This links directly to the observations:
- Near frame, sample (1430,200): Fresnel ≈ 0.36, so it is near-critical, and it sits in the tongue (about x 1300–1600, y 100–300).
- Deep frame: loops and rings at about (1400,30), (1420,650) and (200,630). Their soft, horizon-coloured "liquid metal" bands look like the outline of where the exit ray crosses horizontal.
- The dark islands are probably real TIR islands.
- The earlier ablation that used only the raster facet changed the folds because swapping the normal changes α everywhere. That is consistent with this mechanism and doesn't point to a mesh bug.

**What correct physics looks like here.** An air-side ray with elevation e < 0 hits the surrounding water within about one wavelength. Its brightness is roughly:

F_air(|t.y|) · L_sky(mirrored ray) + (1 − F_air) · L_water

As e → 0, F_air → 1, so the brightness flows smoothly into L_sky at the horizon. A correct render has no brightness jump at e = 0. A seam there is a bug. A seam along the TIR outline is physical.

## Ranked causes and what each predicts

1. **Downward exit ray (described above).** Predictions:
   - The folds lie in the e < 0 region or within 2 px of the e = 0 outline.
   - Near (1430,200) has e < 0. Deep (1430,200) has e > 0, since F ≈ 0.077 puts it well inside the window.
   - Brightness jumps across e = 0, while pixels with e > 0 stay smooth.
2. **Shore-taper slope term** (`waves.glsl:63`) combined with the depth gradient (`bathymetry.glsl:37-38`). Where water depth is between 0.035 and 0.8, slope gains `h·taperDerivative·∇d`. With a one-block step, ∇d is about 1, so slope can add up to about 0.2 (roughly 11°). That moves the rim in large, smooth lobes that aren't real wave tilt. Prediction: the tongue sits only over cells in that depth band with a non-zero gradient. The near frame has terrain silhouettes on the right, so this is plausible there. It can't explain the deep-water loops.
3. **Point-sampled Fresnel/TIR on a smoothed normal.** Small waves that the pixel can't resolve aren't averaged through Fresnel or the exit direction. Prediction: 1–3 px stair-stepping or crawling along the TIR outline that changes with resolution. It doesn't produce large loops. The fix is the residual-quadrature work already designed in `codex-resolved-normal-physical-next.md`.
4. **Mesh facet vs optical normal.** The coarse mesh uses the low-detail wave height at 1 m vertex spacing, so 1.26–2 m wavelengths alias. Underwater, the facet only affects which way the normal is flipped and the grazing blend. The grazing blend acts only when dot(n,v) < about 0.15 (incidence above about 81°), which is deep in the TIR region, so it can't shape the rim. Ranked low.
5. **Duplicate front/back faces.** The forward and reversed quads share the same diagonal. However, the reversed quad is only displaced when the water column is known. Unknown vertices give a flat normal and an undisplaced reversed surface, which would show as hard triangular patches. The observed tongue is smooth, so this doesn't fit. A cheap check is a preview of `waterUnknownWeight > 0`.

**Checked and ruled out:** wave phase and mean height match between the vertex and fragment shaders (same `frameTimeCounter`, displacement in Y only). `waterRefractionFootprintContinuous` only affects the sun disk.

## One decisive experiment (test-only, same fixed phase 17, same near/deep manifests)

Extend the existing preview/C12 classification at the real call site to record, per water pixel:
- TIR (Fresnel ≥ 1),
- `transmitted.y < 0`,
- the underwater refraction receiver type (0, 1 or 2),
- whether the column depth is in the 0.035–0.8 taper band.

Annotate the fold regions on the existing PNGs before looking at the masks: the near tongue, plus deep (1380–1440, 0–60), (1380–1460, 600–700) and (150–320, 600–800).

The result picks the next patch:
- **≥ 80% of fold pixels in e < 0 or within 2 px of e = 0:** cause 1 confirmed. Apply the fix below.
- **Folds mainly match the taper band:** cause 2. The next patch is shore mean-surface and depth-gradient consistency, not optics.
- **Folds sit on the TIR outline only, with e < 0 covering under 20% of them:** cause 1 is rejected. The remaining folds are mostly physical TIR, and the next patch is the residual quadrature (cause 3).
- **Underwater receiver type 1 inside the e < 0 band:** independently confirms that underwater geometry is being accepted as an air-side hit.

For a native fail-first test, reuse the real production main through `underwaterSkyProbe` / `underwater-angular-probe.h` (I didn't open them). Use a constant 10° tilted facet, sweep incidence across the critical angle, and fill the LUT's lower half with a sentinel colour. The current code should output the sentinel, and the patched code should not.

## Minimal fix (only if cause 1 is confirmed)

In the underwater block of `gbuffers_water.fsh`, with no change to `n`, `fresnel`, TIR or the rim position:

```
bool belowHorizonExit = validSkyRay && transmitted.y < 0.0;
if (belowHorizonExit) {
    vec3 mirrored = vec3(transmitted.x, -transmitted.y, transmitted.z);
    float airFresnel = waterFresnel(-transmitted.y, 1.0, 1.333);
    refractedSky = airFresnel*environmentSkyRadiance(mirrored, colortex6, continuousSkyFootprint)
                 + (1.0-airFresnel)*scatter;
}
```

- When `belowHorizonExit` is true, skip `refractionTrace` and set `behind = refractedSky`. This removes the chance of a downward air ray landing on underwater geometry.
- `scatter` is the existing water-side fallback that TIR already uses.
- Document this as one bounce off the mean flat surface. It doesn't model air-side masking for small positive e; that is later work.
- An underwater air-side receiver check for e ≥ 0, mirroring line 197, is a separate later step.

## Pass/fail criteria in actual Minecraft (NVIDIA)

1. **Rim unchanged:** the TIR mask and the C12 Fresnel values are bit-identical between baseline and patch. This shows no normal clamp crept in.
2. **Window interior unchanged:** water pixels with e ≥ 0, more than 1 px from e = 0 and with no route change, are byte-identical in C0.
3. **Seam gone:** for adjacent non-TIR pixel pairs that cross e = 0, the median relative brightness jump is at most 1.5× that of pairs that don't cross. The baseline must fail this. If the baseline already passes, cause 1 isn't the visible cause, so stop.
4. **Plausible range:** brightness in the e < 0 region stays between `scatter` and the horizon-row brightness of the LUT. No sentinel or dark gaps.
5. **Visual:** the annotated loops and tongue become a continuous wavy horizon band. TIR islands and the circular window remain.

## Not a repeat of earlier attempts

- The normal, detail level, footprint, wave amplitude and exposure are all untouched, and criterion 1 enforces this.
- The disabled `waterInterfaceNormal` path (only called under the comparison macro) bends the normal, which moves the Snell rim. This fix instead supplies the missing radiance for a ray direction the code never handled.
- If the experiment points to cause 2 or 3, this patch is the wrong one. I'd send it back rather than adjust brightness.
