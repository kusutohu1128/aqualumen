# Prepared-view reuse: CPU caller and coverage review

This is a read-only source/saved-evidence review, not a new rendering experiment. No GL, game, UI, shader, tool, installed pack or sealed packet was changed. Diagnosis uses the retained differential packets as its feedback loop; the remaining visual symptom was not re-rendered here, so the hypotheses below are not established causes or fixes.

## Exact integration seam

Reviewed `tools/water_sun_prepared_main_probe.cpp` SHA `0e7e27e6cbf6655638745021c197c0c16f50784474f9fe820dce01e678b7ead5`, old certificate `f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a`, and literal prepared helper `ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441`.

The transform at MAIN lines 42–46 and 94–120 changes exactly the included classifier, adds one local `waterSunSupportPrepareView(viewToEye,eta)` before the original `if (valid)` loop, and replaces its existing classifier call with `waterSunSupportClassPrepared(WPM_viewContext,target)`. It does not add an invalid-context shortcut. Target generation, axis precheck, all 48 count updates, certified-zero `continue`, unknown whole-result fallback, inverse/reconstruction/reflected-direction/receiver gates, quadrature weights and geometry remain unchanged. Preparing invalid input before a loop that is not entered is a scheduling difference, not permission to classify or skip nodes differently.

The six cached intervals are `vx`, `vy`, `vz`, `E`, `K2`, `downScale`. `V` retains `(vx²+vy²)+vz²`; `K2` retains `1+E*(V-1)`; `downScale` retains `E*(vy*vy)`. No interval square shortcut, vector normalization, floating-point algebra or narrowing of overlap/equality to zero is introduced. The per-target code retains the original expression tree and strict comparisons.

This review independently erased the exact literal helper/context/call transformation from the saved `main-native-v3` physical, reasons, inputs and all48 expanded sources: all four recover their saved old-role source byte-for-byte. This is source recovery, not independent optical acceptance.

The frozen old zero-role ZIPs were also read directly:

| Role | ZIP SHA256 | Source relationship |
| --- | --- | --- |
| reasons | `7f15dbc05a68cc80be3ae0f6ea66ec5ae3c3f42785eb753d4e603f7089ba9048` | Helper/water recovery matches frozen stable reasons pins. |
| inputs | `5a1dd986f95961c96d9175301b8ce432d65cde792e89f99e01935234abde70b0` | Helper/water recovery matches frozen stable inputs pins. |
| physical | `33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda` | Water FS equals both roles' archived `SUN-SUPPORT-physical.fsh`, SHA `dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4`. |

All three contain the exact old certificate and identical VS/TCS/TES bytes. Physical retains the reasons helper, including passive instrumentation; it is not wholly instrumentation-free. Its FINAL equals `original/shaders/final.fsh`, SHA `43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf`, so it does not offer the diagnostic FINAL C9–C12 readback contract.

## Which natural rays can be absent or unknown?

Let `V=|v|²`, `U=|t|²`, `B=v·t`, `E=eta²`, and `K²=1+E*(V-1)` using the actual raw binary32 inputs. Within the certificate's declared domain, support requires the strict signs/separations corresponding to:

```
B < 0
E*B² > K²*U                 forward inverse branch
E*vy²*U > K²*ty²           downward facet branch
```

The integer code returns unknown if any required interval comparison overlaps/equalizes, even when another comparison contradicts support. Only separated contradictions certify absent. Invalid raw signs/norm interval/range, overflow or nonfinite/subnormal inputs also remain unknown. Generated `t` is normalized by the existing cap generator; caller `v` is never repaired.

For the illustration **exact unit** `v` and zenith `t=(0,1,0)`, support reduces to `-v.y > 1/1.333`: an angle below **41.3934°** from the downward view-to-eye axis. This is not the flat-interface TIR critical angle `asin(1/1.333)=48.6066°`, and not a universal camera cutoff. A tilted Sun changes `B` and `ty`; raw norm roundoff changes `K²/U`. The stock source radius is 0.00465 radians (0.266425°), so a near-boundary view can have mixed supported/absent cap nodes. A naturally sampled view near an interval boundary can produce unknown; no such actual Iris unknown was observed in the retained fixed 16.

The earlier natural zero-reasons capture has 16 complete 48-call ledgers: **502 absent, 266 supported, 0 unknown**, 12 applied and 4 reflected-hemisphere rejections (`iris-zero-reasons/reason-audit.json`). The separately captured inputs show near-central `v.y≈-1`, edge directions near `-0.67…-0.72`, and transition directions near `-0.75`; these are consistent with the illustration, not a same-frame pairing proof. Certificate absent means only the prescribed air-Sun inverse branch is absent. It is not a Fresnel/TIR-zero, whole cap-flux-zero or visibility certificate.

## Coverage and observer limits

- The standalone node GPU gate covers the frozen 344 plus 32 bounded invalid/signed-zero/nonunit inputs, including old/wrapper/reused classes and six interval triples. This covers invalid-context scheduling and classifier branches in that standalone seam, not their natural water-main prevalence.
- Saved actual MAIN central positive, wide60 and wide90 inspected ledgers contain **only support class 1**: 241,200, 733,152 and 245,232 calls respectively, zero absent/unknown. MAIN's all48 target/view/class observers preserve actual values and do not call the classifier again. Wider FOV alone did not make these fixtures cover absent/unknown. The wide masks are known/eligible water, not whole-raster physical acceptance.
- Natural reasons C10 countword can witness aggregate zero/support/unknown/calls at the fixed 16 and C9 first/group rejection categories. It cannot export each node's raw input. Calls occur only after the unchanged target/axis precheck; no pre/post-loop reason is inferred from those counts.
- Inputs C12 records only the first failed target/index/reason. Certified absent nodes `continue` without failure, so this observer does not export them; code 0 is **no observed first failure**, not a support-zero or missing-input conclusion. Inputs C12 is not TES. Guard and FINAL captures, and reasons versus inputs clients, are separate observations—not the same draw/frame.
- Physical FINAL/PNG/timing has no current selected-16 operator qualification. Fresh typed guard and linked-stage evidence is necessary but does not replace per-node or whole-frame application evidence. Keep the ordered 16 and minimum-four gate unchanged. If the new Iris run has no unknowns, record that gap rather than changing coordinates or claiming unknown caller coverage.

## Remaining underwater bands/rim: ranked source hypotheses only

Pointers below refer to saved `main-native-v3/old-physical-expanded.fsh`, which is the checked expanded caller, not an inferred current shipping source.

1. **Whole-result admission/fallback boundaries.** Lines 1264–1276 require both legacy GH evaluations to apply; 1317–1367 reject the complete cap on one inverse, reflected hemisphere or receiver failure. Legacy lines 1407–1475 likewise require all nine facets and receivers. Retained natural firstReason3 at four selected points establishes reflected-hemisphere exclusions there, but does not attribute the visible bands to them. Prediction: a same-draw boundary mask of eligibility/full-base validity/WNS rejection aligns with the relevant contour; unchanged masks across a contour would weaken this hypothesis. No reflected or receiver gate should be dropped to raise counts.
2. **Discrete angular environment sampling.** Sharp Sun uses the fixed 48-node cap, but cloud/sky/Moon transport in the saved full/base calls still uses the nine-node GH rule, with per-node Fresnel/TIR and source lookup. This can generate discretization structure; the sharp-Sun integral does not prove broad-source convergence. A later, separately authorized rotation of the same whitened GH lattice would preserve its moments while testing whether a contour tracks its orientation. No rotation, source blur or quadrature change belongs in the present prepared-view experiment.
3. **Known/facet/grazing handoff.** Lines 1527–1554 require exact `waterUnknownWeight==0`, use analytic known-column normals versus raster facets, and blend grazing normals toward the geometric face. Lines 1646–1648 disallow ripples, adjusted normals and opaque/SSR cases for the residual operator. Prediction: polygonal segments align with same-draw known/grazing/eligibility transitions rather than the physical Snell boundary. The optimization does not change these predicates, geometry, normal spectrum or footprint.
4. **Screen-space receiver/environment handoff.** Lines 1593–1600 and 1635–1648 distinguish opaque hits, unknown misses, confirmed sky and reflection hits. Offscreen visibility and cave/sky fallbacks remain approximate. Prediction: the contour follows receiver/SSR class or screen-edge transitions, not merely view incidence. Do not alter cache safety, scattering or geometry as a simultaneous explanation.

A curved Snell window and total internal reflection are expected physical phenomena; a dark curved outline alone is not a bug diagnosis. Current source evidence does not select one explanation for the residual band/polygon artifact. The present test should remain solely the operation-identical prepared-view reuse, with fresh Iris caller/count witnesses and honest timing. Visual correction, general critical/rim/visibility acceptance, physical completeness, universal speedup and shipping adoption remain unproven.
