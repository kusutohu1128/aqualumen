# Independent CPU review: post-0.5 shore diagnostic

Reviewed 2026-10-02. **Useful causal narrowing, not a shipping fix or a proven continuity defect.** This review used the diagnose skill's one-variable/correct-seam discipline. Only this document was edited; no GPU, game, lifecycle, configuration or source operation was performed.

Read-only checks covered `shoreDiagnosticProbe`, the [measured design append](codex-shore-diagnostic-design.md), both preserved artifact directories, expanded programs, float32 dumps and endpoint/source-response CSVs. Shipping ZIP still hashes to `88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.

Independent include expansion matches the saved production vertex program. The fragment baseline has only common public foam=0; each ablation has exactly its authorized expression change. All five expanded files are identical between first/second runs and match the measured append's hashes. The closed-box nearest hit coherently supplies C4/depth; sampled R32 depth, seeded framebuffer DEPTH32F and colour output are separate. No framebuffer feedback is apparent.

Both NEAREST/LINEAR have **3,945** water ROI pixels. CPU dump recalculation reproduces baseline red reflection-tag responses **0.1507544145 / 0.1453433484**, positive deep/shallow responses, and exactly zero red response with environment-only SSR. Original/proxy rays are below the horizon; the red target is above water. The logs report repeat error zero; this reviewer did not rerun GPU repeat execution.

The pointwise green baseline-minus-environment CSV has 3,945 rows, maximum **2.98023224e-8** for both deep/shallow increments. Thus submerged-source SSR is **not demonstrated in this NEAREST fixture/phase**, not ruled out generally. CPU reconstruction of actual saved water geometry reproduces **2,064** qualified deep derivative-quad pixels, minimum clearance **1.136735141 m**, and depth64 RGB difference **0**.

The initial raw maxima were input discontinuities: finite field edge→sky, or same-face C4 palette switching at waterY=-0.5. The second qualification correctly requires stable original face/part/C4/water alpha throughout the endpoint quad (LINEAR padded to 4×4), excludes outer edges, and retains qualification at bisection midpoints. Independent CSV checks pass all 4 NEAREST/all 16 LINEAR footprint cells for the selected baseline bracket.

The producer compares **the same baseline pixel (65,46) and endpoints** across variants, not their unrelated maxima:

| Filter / fine b interval(m) | Baseline | Supplied face normal | Environment-only | Depth64 |
|---|---:|---:|---:|---:|
| NEAREST / 0.0464765616→0.0464843735 | .051877059 | 9.56654549e-6 | .051877059 | 7.45058060e-9 |
| LINEAR / 0.0484453142→0.0484531298 | .00166225433 | 5.23328781e-5 | .00166225433 | 3.30805779e-6 |

Independent float32 baseline endpoint reading reproduces both baseline figures. NEAREST RGB is `(.106928252,.154123142,.166918367)→(.158805311,.171639606,.174513862)`; original face165/part1 and gray C4 remain fixed. Ablation values agree between producer log/CSV, but those particular same-bracket ablation renders were not independently rerun here. Replay should use high-precision log bounds.

**SSR selection is not the sole necessary explanation for this bracket**: environment-only does not remove it. Normal/fragment-depth coupling matters. However, supplied face normal is not displaced-triangle normal, and depth64 changes slopes/variance; neither is a physically justified release fix. Actual *traced* receiver identity, NEAREST texel switches and refracted riser visibility remain unqualified. LINEAR refinement is not an asymptotic proof, and other depth64 own-maxima still reach .0495198/.0716468. No natural-coast cause, full shoreline continuity or visual acceptance is established.

Provenance: first log SHA `39397cbcd0f30222a47b6c78f96a8cc3c9dddd3e888bf95e65fc4e048cf89f3c`; second `af0cd5226ec9765a1b13d7f134937be04a02aa0299cb2bfac4f316b3c4dbd3c4`. Both directories remain preserved. The next separately authorized seam must qualify continuous actual traced-source behavior at this bracket while retaining bank rejection; **tracer-source continuity is pending**.
