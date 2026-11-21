# Land-only shadow preview architecture

## Problem and usage

User put water development on hold and requested other shadows. Ordinary0.6 was initially running for inspection and was left untouched. The later scoped ownership check found it stopped. The preview must not import dirty-root water/cloud/receiver work or reinterpret its shared shadow sampler. Source algorithms for water, shared illumination, composite and caster stay unchanged.

Both opaque wrappers replace only the lighting include with land_lighting.glsl. Existing terrainLight calls remain unchanged. The adapter owns the scoped shadowVisibility alias, includes the unchanged lighting body, and immediately undefines the alias. It fails compilation on pre-existing lighting instantiation or alias collision. The only new library entries are land_lighting.glsl and land_shadows.glsl.

## Synthesis decision

Independent Codex and actual Claude both rejected raw-depth PCSS for this first unit. The cross-judge recommends Codex's texel-centred receiver-plane construction as the conditional base. The parent agrees. Claude's adapter guards and explicit positive/negative test protocol are grafted. Its3cmplus slope-support acceptance bias is rejected because the slope term can grow to metres off-axis. The cross-judge's analytic caster-error estimate is not a GPU measurement.

The first implementation unit is the identity adapter/pack boundary and a real-caster native fixture. No filter is accepted before the coarse vertex-warp residual and old failure are observed. A successful baseline run must distinguish fixture validity from the expected old contact failure.

## Shape

Pack input is an exact pinned ordinary ZIP, not root/shaders. The builder validates the baseline hash, exactly one lighting include in each opaque wrapper, the complete archive payload allowlist, and unchanged nonopaque expansions. It produces an exclusive new preview ZIP and manifest. It does not install, activate, quit, reload, or mutate any game/config/world.

The first landShadowVisibility(pos,normal) delegates exactly to legacy. After the geometry gate, the proposed LandShadowReceiver carries validated light-space point/normal, projection inverse, depth metric and footprint. Each tap projects a metric offset and evaluates receiver depth at actual texel centres. No new texture/uniform resources or shadow directives are introduced.

The parent chooses a plane-correct four-corner manual bilinear layer for the later filter, rather than shipping binary snapped edges. Each corner keeps its own plane reference. Its additional fetch cost will be reported without an FPS claim. Source sampler state remains unchanged.

## Declared gates before GPU results

- Actual unchanged shadow.vsh/fsh renders D24 at2048, with finite fully-lit and fully-blocked controls, correct cutout and map-boundary checks.
- A4cm-separated blocker inside full map coverage is the near-contact witness. Legacy must violate the shadowed target, or its alleged leak is not reproduced. Candidate target is visibility<=.01 in the declared interior, not at the geometric silhouette. The finalized fixture budget allows at most0.1percent wrong selected pixels, reports every count/min/max, and requires more than100selected pixels. This is frozen before any GPU result, not a post-result exclusion.
- Actual1m caster planes at central/origin-crossing and off-axis positions, slopes0/30/60degrees, must keep lit interior visibility>=.99 under the same0.1percent wrong-pixel budget if the candidate is to be accepted for those cases. Report signed warp residual separately in metres. Broader sun/Moon orientations and geometry require named controls, not inference.
- No post-failure increase of the proposed2mm residual constant merely to hide the coarse caster error. A new geometry-derived bound or caster change would require a revised explicit design and new evidence, not a silently relaxed test.
- Analytic injected plane isolates receiver-reference correctness but does not substitute for actual caster rasterization.
- Sun-angle/subtexel sweeps must report transition jumps. Four-corner sampling is included before a usable improved-filter preview, not postponed behind a visual-completion claim.
- Identity preview output must preserve all original payloads except two one-line wrapper edits. Nonopaque expansions are exact. All original program pairs compile/link on actual NVIDIA. Native evidence is not actual Iris appearance or game FPS.

## Outcomes and limitations

Identity has exactly legacy behavior, including legacy handling outside valid input domains. For a later filter, finite valid input and finite fallback behavior must be reconciled explicitly before implementation. No unconditional never-NaN claim is inherited from either design.

Preserved water source algorithms do not imply identical water pictures. Opaque C0/C5 changes naturally affect C4/C8, reflections and caustic inputs. Coverage fade, map resolution, offscreen casters and broad physical/visual/performance acceptance remain outside the bounded native claim.

## Implementation reconciliation

The identity boundary passed26CPU tests, all-program compile/link on RTX3080Ti, and exact output equality for all26native lookup frames. No improved filter is implied by that result. Its source snapshot and archive stay frozen under identity-checks and identity.zip.

The actual native-baseline1 measurement reproduced the4cm gap leak on all16641receiver pixels. Empty/solid/cutout/bounds controls passed. The off-axis60degree receiver has16641self-shadowed pixels under the declared criterion. Real caster warp reaches about24.04mm, whereas analytic per-texel planes remain within about0.108mm. This is controlled native geometry, not observed Minecraft near/far values or natural appearance.

The parent accepts the cross-judge's second graft. Retain the existing normal offset exactly,0.015+length(position)*0.00025, rather than remove it. Keep2mm as the new light-axis residual depth bias, not as a claim that total geometric bias is2mm. Retaining this pre-existing offset is not increasing the residual after a failure. A physical receiver plane displaced along its normal can cover more light-axis distance than that normal offset. Every resulting contact/acne target still has to pass unchanged. No3cmconstant or unbounded slope-support addition is accepted.

Proceed with35mmmetric radius expanded to one local shadow texel via the largest singular value of the local inverse UV mapping. Four-corner, plane-correct manual bilinear filtering is part of the first improved candidate. Use actual textureSize, not an unrelated assumed map size, and preserve the legacy coverage fade through its existing constant.

Finite supported orthographic matrices and orthonormal shadow-view rotation form the new filter domain. Handle both signs of light-normal Z and projection Z. Finite unsupported but evaluable legacy cases retain legacy behavior. Nonfinite input or undefined projection must not sample an invalid coordinate; define an explicit unknown fallback and do not present it as physical visibility evidence. Final exact outcome wording must match implementation before closing.

The builder's resource guard must permit reading existing shadow constants while forbidding their declarations, redefinitions and new sampler/image/uniform resources. The identity guard rejected reads as well; relaxing that lexical overreach changes no archive payload. Add positive existing-constant-read and negative directive tests.

The next native probe also includes a fixed-light receiver subtexel sweep across a real caster edge. Declare endpoint contrast, monotonicity and a maximum0.02visibility jump per1/512of its0.2m sweep before observing results. Compare legacy as a control. This is not a dynamic Sun or live-game stability claim.

Parent alone integrates and runs GPU tests. The active client remains untouched.

## Current contract and next step

The final receiver has REFUSED, LEGACY and METRIC outcomes. Nonfinite inputs or undefined legacy projection refuse before a lookup and return1as unknown unshadowed coverage. Evaluable finite input outside the supported orthographic/orthonormal domain uses legacy. Invalid texture extent also refuses. Supported metric receivers use the plane-correct four-corner filter. These fallback results are not physical visibility evidence.

The comment-reviewed candidate2archive has SHA ea3cbd1e19453aabc1807df7016549001379714a47e57187b3b72a31be0e6652. Its28CPU pack checks, all-program NVIDIA compile/link and26native geometry targets passed. Every selected native pixel met its target. The513position fixed-light receiver sweep passed with a largest visibility step0.0091095under the frozen0.02gate. These results do not prove dynamic Sun motion or actual Iris appearance. Three isolated GPU mutants independently expose flat-reference acne, excessive depth-bias contact loss and nearest-only transition jumps.

Proceed to the three guarded air-shadow scenes in the exact disposable V2world, with the pinned ordinary0.6control and candidate, then restore the captured normal config and physics0.2. Do not load an ordinary world. The runtime helper must refuse live Lab ownership or unknown state, preserve partial-failure recovery and never kill the game or roll back saves. Actual Claude's final review is blocked by an external usage limit; retain that gap even if independent Codex review and runtime checks pass.
