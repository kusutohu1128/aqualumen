# One causal Sun correction, then judge the original image

CPU/source review only; no new GPU, Minecraft or visual acceptance. The active
requirements in `docs/REALISM_GOAL.md` are convincing water/Sun images and motion,
not an indefinitely expanding diagnostics suite. Parent CAP helper SHA256:
`a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3`.

**Source facts.** `shaders/lib/water_residual_sun_cap.glsl:105–114` checks the
actual transmitted facet sidedness/reconstruction, then additionally rejects
when the counterfactual reflected ray points upward. Lines137–140 also reject
its reflectionTrace alpha. Neither reflected ray nor that reflection RGB enters
the new Sun integral at141: it uses kernel × transmitted skyWeight. The full/base
legacy calls at57–67 and their application gate at73 remain independent;
`water_residual.glsl:62,81–87` still checks its real reflected contribution.
Thus the cap's extra reflection gates are not automatically justified as
transmission visibility, but removing them cannot repair an invalid legacy call.

**Next single improvement, conditional on evidence.** If the saved reason
readback identifies firstReason3 as the dominant first failure, test removal of
ONLY the new cap's counterfactual `reflected.y<0` admission predicate. Keep
finite/reconstruction, actual incident/transmitted sidedness, Snell/Jacobian,
kernel, transmitted receiver, source units, whole-replacement fallback and
legacy full/base gates unchanged. Do not simultaneously remove reflection-alpha
gating, widen the Sun, increase tessellation/nodes or tune colors. Reason3/9 share
the hemisphere counter: firstReason3 plus48 hemisphere nodes does **not** prove
all48 were specifically reflected-hemisphere failures. If another first reason
dominates, follow that measured seam instead of this hypothesis.

**Physical regression before visual rerun.** Use actual main with an independently
valid transmitted incident/outgoing pair and inverse facet whose counterfactual
reflection points upward; prove the original rejects a positive transmitted Sun
response and the candidate recovers its bounded independent integral. Preserve
wrong transmitted hemisphere/reconstruction and transmitted opaque negatives,
zero-cache, disabled/unauthorized, legacy coefficients/scatter and passive-store
controls. A reflection-only receiver is not by itself a transmitted obstruction;
its later alpha rejection is a separate admission question, not permission to
delete real transmitted visibility. This is not a complete masking/energy model.

**Exit from diagnosis.** Once that one qualified regression passes, repeat the
same guarded V2 near/deep/tilt views and short view-angle motion. The fixed16
minimum4 application gate stays unchanged, but passing it only enables review.
Judge the original top-left C0 Sun shape/rim, separated bright points and retained
sky/cave controls—not diagnostic colors or a successful subset. Reject an image
regression even if more points apply. Record ordinary-world preservation and
matched real frame costs. Neither this proposal nor reason readback accepts
pixel-AA, natural-shore realism, a FPS floor, shipping or the full goal.
