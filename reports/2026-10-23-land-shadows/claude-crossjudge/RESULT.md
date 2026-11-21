# Land-shadow cross-judgment (read-only, 9 reads, no writes)

I read the two skill files from the repo. The architect "design it twice" requirement is met, since both candidates are compare-sampler PCF behind the same adapter. The two differ in only one place: the depth they compare against. That is where all the risk sits.

## Scores (0–2)

| Rubric item | A (Claude) | B (Codex) | Note |
|---|---|---|---|
| 1 Preservation | 2 | 2 | Both swap one include in two wrappers. Caveat below about which files the alias reaches. |
| 2 Sampler contract | 2 | 2 | Both use `shadowtex0` only, with no directives. Whether the macro alias survives Iris's preprocessor is still unverified for both. |
| 3 Coherent geometry | 1 | 2* | See below. *B gets 2 only if it passes the caster gate. |
| 4 Data shape / boundary | 2 | 2 | A is smaller but assumes a diagonal projection. B validates that, but its handling of nonfinite inputs is undecided. |
| 5 Tests | 1 | 1 | A has numeric thresholds but no warp-residual or origin-crossing case. B names the right cases but declares no budgets. |
| 6 Preview | 2 | 1 | The condensed B record doesn't say how the preview is packaged or installed. |

The totals tie at 10. I'm not breaking the tie by counting; the reasons are below.

**A's maths is correct but its bias is not justified.** I checked A's inverse Jacobian against `shaders/lib/shadows.glsl:9-11`: radial d²/0.15, tangential d. The gradient `Gc = 0.2·P22·J⁻¹·(g/diag P)` is also right. The problem is the bias:
- **The slope term is too small.** The `|Gc|/res` term is meant to cover hardware bilinear compare, but the four bilinear corners can sit up to √2 texels away along the gradient. One texel under-covers diagonal gradients.
- **It grows to metres at range.** At r≈0.95 a radial texel is about 0.86 m, so g=1.73 gives about 1.5 m of depth bias, against legacy's 0.19 m. A's claim that distant contacts are "no worse than now" is false. It trades acne for detached contact shadows.
- **The 3 cm constant is untested.** It is an assumption, not evidence.
- **The "never NaN" invariant is unsupported.** A NaN `coord` makes every `lessThan`/`greaterThan` false, so it slips past the bounds check, exactly as in legacy.

**B's construction is the coherent one.** Without MSAA, the rasterizer writes caster depth at texel centres. Evaluating the receiver plane at the same snapped centres therefore removes the slope term entirely. What remains is warp-linearisation error plus precision. It also stops one reference depth being compared against four different texels.

**B's risk is the 2 mm residual, which I predict fails under the player.** Coarse per-vertex distortion has a kink at r=0. I did a 1-D chord calculation for a 1 m face straddling the origin. The rasterized depth differs from B's inverse-distorted plane by about 2.5 mm × g. That is about 4 mm at a 30° Sun and about 12 mm at 12°. The error falls off quickly away from the centre. This is my analytic estimate and needs measuring. It also means A's "~1 cm" figure is about right for low Sun near the centre. Whether 3 cm covers it in general is still unproven.

## Recommendation

**Base: B.** Its texel-centre plane reference is the only design where the bias doesn't have to absorb slope.

**Graft 1, from A:** the concrete adapter guards and the test protocol:
- the `#error` guards (lighting already instantiated, alias collision);
- the fail-first run where land is aliased to legacy;
- tests F1–F8 with numeric thresholds;
- the archive checks: one-line wrapper diff, a grep for forbidden directives, and byte-equal expansion of non-opaque programs.

**Graft 2, from A:** keep the legacy receiver normal offset (`0.015+0.00025·dist`) unless the gate shows it causes leaks. B's record doesn't say whether it keeps this offset.

**Rejected:**
- A's constant 3 cm plus one-texel slope bias as an acceptance mechanism.
- A's "always finite" and "no worse at distance" claims.
- B's 2 mm as a fixed constant before any measurement.
- Any bias increase made after a gate fails.

## Separate gates and budgets

Declare these before any run:
- **Self-plane acne:** actual `shadow.vsh`/`shadow.fsh`, 1 m block faces, Sun elevation {12, 30, 60}° and Moon, r ∈ {straddling the origin, 0.05, 0.5, 0.95}. Pass if visibility ≥ 0.99 on lit receivers. Report the signed warp residual in metres (max and p99) separately for each (r, g).
- **Contact leak:** a 1 m cube on ground, receivers 0.05 m and 0.10 m past the base, both near the origin and at r=0.5. Pass if land ≤ 0.05 at 0.10 m. Record legacy's value. If legacy doesn't leak there, the case for the candidate has to be re-argued.
- **Cutout, bounds and parity:** as in A's F3, F5 and F6.

## Nonfinite inputs

Contract wording: finite refused cases fall back to legacy, and nonfinite inputs give the same outcome as legacy, which is unspecified. Don't claim `[0,1]`/finite output except for finite, validated inputs. Test only that claim.

## Texel snapping and temporal steps

Snapped taps are each a binary compare. Legacy's hardware bilinear gives continuous edges, so B will step and crawl as the Sun angle moves.

The fix is a plane-correct 4-corner layer: four compare fetches per tap, each with its own plane reference, plus manual bilinear weights. That costs about 4× the fetches.

My verdict:
- For the first unit, treat this as a **labelled limitation**.
- Add a sub-texel Sun-angle sweep test that reports the largest visibility jump per step, compared with legacy.
- The 4-corner layer is **required before any visual-parity or acceptance claim**, unless the sweep shows steps no worse than legacy.

## Smallest reliable first unit

Not the filter. The first unit is:
1. The `land_lighting.glsl` adapter with `landShadowVisibility` behaving identically to legacy, built from the verified ordinary 0.6 ZIP (not the dirty root).
2. Archive and expansion-equality tests, plus compile/link of every original program pair.
3. The native caster warp-residual measurement above: real `shadow.vsh`/`shadow.fsh`, with depth read back in the test context only, compared against B's inverse-distorted plane at snapped centres.
4. The fail-first acne and contact runs against legacy.

This is the single decisive experiment before the pick. If the origin-straddling residual is ≲2 mm × g... the outcome sets the path:
- **Small residual:** implement B as specified.
- **Residual about 2.5 mm × g, as I predict:** choose one of these and record the decision:
  - (a) a declared, geometry-derived residual bound, |g|·ε_warp(r) for a stated maximum caster edge length. Entities can exceed 1 m and must be labelled as such.
  - (b) B's own outcome: keep ordinary 0.6 and report caster tessellation/deformation as an architectural issue.

## Reconcile before implementing the filter

1. The residual budget: 2 mm, a derived ε_warp(r)·|g|, or refusal.
2. Footprint: B's 35 mm expanding to about one texel, or A's legacy 1.6-texel disk. These match near the player but diverge at range.
3. Whether to keep the legacy normal offset.
4. The nonfinite outcome wording.
5. Whether snapping without bilinear is a labelled limitation or the 4-corner layer comes now.
6. Alias reach. `lighting.glsl:3` includes `clouds.glsl` inside the alias scope. Root `clouds.glsl` doesn't call `shadowVisibility`, but `clouds.glsl` is one of the 9 entries that differ in ordinary 0.6. Check the ordinary copy, and make expansion equality cover transitive includes.
7. Whether the macro survives Iris 1.8.8's preprocessor. This is open for both candidates.

Native results from the harness must be labelled as harness evidence. They are not in-game appearance, FPS or acceptance. Nothing here needs the running ordinary 0.6 Lab client or its config.
