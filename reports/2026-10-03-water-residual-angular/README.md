# Residual angular-source diagnosis — not a shipping fix

2026-10-03 JST. **Progress, not completion or visual adoption.** The actual
native water-main experiment reproduces separated bright images with a narrow,
derivative-free source on a common valid/applied domain. Independent double
arithmetic agrees with the finite GPU rule, while a separately converged
finite-window integral shows large source-sampling error. Merely increasing
the rule order is not a demonstrated cure. Production shaders and normal-play
assets remain unchanged.

## Actual execution

The pre-execution [contract](EXPERIMENT.md) records ranked hypotheses, fixed
inputs, numerical gates and lifecycle. [Native output](native-angular-v1/result.json)
contains 12 cases: narrow/broad/constant/dark sources × GH3/GH9/GH17. These are
one-dimensional rule orders; their tensor products have 9/81/289 nodes.
The actual RTX 3080 Ti context reports OpenGL 4.6 NVIDIA 580.173.02. Original
VS/TCS/TES/FS main, factor4, phase120, geometry, covariance and source units
are held fixed. The shipping shader is not changed.

The synthetic CHORD Gaussian has peak RGB(.25,.125,.0625), with sigma .00465
or .08. This is **fixed peak radiance**, not fixed integrated power, the stock
solarDisk, calibrated beam, or an actual Minecraft Sun measurement. It bypasses
solarDisk pixel derivatives. All 5,025 pixels in the fixed radius40 disk are
known underwater top water and eligible/valid/applied under every case. No
domain intersection shrink or surviving-node renormalization is used.

Raw RGBA32F outputs, depth, repeated pure/observer draws, expanded shader
sources, queried program layouts/matrices and actual immutable sampler inputs
are saved. Native repeat/passivity/source-recovery checks pass. Pure slots5–7
are cleared inactive targets, not evidence of shader stores; observer slot5
records the actual view-to-eye ray, unlike the earlier interface experiment.
The retained [native baseline](retained-native-baseline.log) also passes.

## Independent saved-data arithmetic

The [separate agent saved-data audit](independent-angular-saved-cpu-audit.json)
consumes606 files; the root reruns that final tool in the
[root saved-data audit](root-saved-data-audit.json). It independently checks
source/hook/observer recovery, GH moments, finite raw sizes, byte-exact repeats,
passivity, uploaded inputs/geometry/matrices and the predeclared common-domain
policy. It qualifies all5,025 ROI pixels and the original seven points. Its
component pixel sets/peak coordinates exactly agree with the separate small
root analyzer ([empty comparison diff](root-independent-component-set-diff.log)).
Saved metadata does not contain queried matrix uniform type/count or sampler
uniform types; this CPU audit does not establish those reflection proofs.

The root [combined CPU run](root-all-cpu-contracts.log) passes14 tests, including
source corruption, nonfinite/truncated/repeated-output corruption, integer
metadata and policy rejection, and one common-domain hole retained as
INCONCLUSIVE instead of a surviving ROI subset. These are CPU tooling contracts,
not a new shader-behavior RED→GREEN. Harness/reference/auditor construction REDs
remain in their respective subdirectories. The first root oracle invocation
failed to import its module ([retained log](root-oracle-tests.log)); the corrected
PYTHONPATH invocation and combined run pass. That command error is not a model RED.

The [original seven-point audit](CPU-reference/actual-seven-oracle.json) checks
84 actual source/rule/pixel samples. All are independently domain-qualified and
match the same finite rule in double arithmetic within the unchanged gates:
maximum coefficient error3.172e-7; source-minus-dark RGB error7.930e-8.

The [separate supplemental audit](CPU-reference/actual-supplemental-oracle.json)
uses the fixed center and five observed GH3 component peaks. It is explicitly
a post-capture positive diagnostic, not a replacement for the original seven
or a predeclared appearance gate. Its 72/72 samples qualify and match finite
arithmetic; maximum coefficient error5.961e-7, RGB error1.202e-7.
Actual selected normal/covariance/eye inputs are exact across all 12 cases.

Independent slope-domain integration uses a support-seeded standard-normal
square[-6,6]², grid refinement and an independent GL6→GL8 order check. It
qualifies 34/39 distinct references. Five original narrow cases remain
**INCONCLUSIVE** under the predeclared near-zero policy, even though their
sampled window geometry qualifies. Omitted projected radiance bounds are at
most1.035e-9 per C0 component; this does not prove visibility/domain validity
outside that window or full dielectric energy/reciprocity.

Two supplemental narrow-source locations show the sampling error clearly.
Values below are actual source-minus-dark **red-channel** responses, compared
with the qualified continuous finite-window reference:

| Pixel | GH3 | GH9 | GH17 | Continuous reference |
| --- | ---: | ---: | ---: | ---: |
| Center(128,128) | 0.0000001216 | 0.00713969 | 0.01491409 | 0.00862005 |
| Peak(132,131) | 0.09712414 | 0.03666667 | 0.02251957 | 0.01305445 |

Thus the finite rule both misses light between nodes and over-concentrates it
at a node image. GH17 is not ground truth; the center error is not monotonically
improved by increasing order. Across these six locations, GH3's maximum broad
source/reference red error is5.101e-5 and constant-source error8.023e-8, versus
0.08406969 for the narrow source. These are descriptive current-operator
numerical comparisons, not a physical BSDF or subjective-quality certificate.

## Raw-map spatial diagnosis

The small root [descriptive analysis](root-actual-descriptive-peaks.json) uses
same-rule source-minus-dark positive linear luminance, eight-neighbor connected
components above .2 of each fixed-ROI peak. Narrow source component counts are
5/3/4 for GH3/GH9/GH17; broad source counts are1/1/1. Relative per-case threshold
makes this a description, not a monotonic density or visual-quality metric.

This bounded reproduction supports sparse angular-source sampling. Its common
valid/applied domain and derivative-free source exclude applicability switching
and stock solar pixel derivatives **for this reproduction only**. They do not
exclude those effects at a natural curved rim, critical angle or native Sun.

## Safe ordinary handoff

Ordinary0.6/physics0.2 was cleanly saved/closed before native work. All Minecraft
JVMs were absent during GL execution. Before relaunch, normal configuration
bytes and the ordinary save tree matched fresh post-save snapshots; no ordinary
backup was restored and no ordinary camera/time/terrain automation occurred.

After all native work ended, the normal account/world was reopened with exact
0.6 ZIP `6ceb9cf0…c9a73` and physics0.2 `1e17cf11…0cce2e`, with development
instrumentation disabled. Esc and F2 were separate actions; the root separately
viewed [the fresh pause screenshot](ordinary-after-paused.png), captured10:35:21
at1600×900. [The ordinary Minecraft log](ordinary-restored.log) confirms active
0.6, physics0.2 and NVIDIA GL3.2. The different GL context is not conflated with
native4.6. Options and benchmark configuration remain byte-equal; Iris rewrites
only its timestamp comment on relaunch. Private Prism output is not published.
No native GL is run after this ordinary relaunch.

After the CPU checks, the root captures and separately views another
[actual paused F2](ordinary-final-paused.png) at10:51:58, with the same ordinary
client still active. Both point-in-time captures are retained in the
[handoff record](ordinary-handoff.json), together with the final Minecraft log.

## Remaining work

No new Iris experimental capture, natural image/motion acceptance, performance
claim, shipping release, commit or push is established by this packet. Earlier
strict RED/INCONCLUSIVE results and frozen packets remain unchanged. This turn
adds diagnosis/test tooling, not the source-integration correction.

The next [proposed light-domain seam](../../docs/reviews/codex-water-residual-solar-integral-next.md)
must preserve the current slope measure and stock Sun size/radiance, verify the
inverse-Snell mapping/Jacobian, then demonstrate actual-main RED→GREEN against
the unchanged continuous reference. Zero/singular residual, visibility/domain,
critical/rim and pixel-footprint/motion behavior require separate qualification.
Natural shore/cloud/light-transport/contact requirements remain open. The full
goal stays active, not achieved.

Before this handoff, a separate [CPU mapping checkpoint](../2026-10-03-water-residual-light-mapping/README.md)
implements/tests that restricted exact-unit inverse mapping and determinant:
two public-API RED→GREEN increments, six root-rerun tests. It is not the source
integral, direct binary32 intake or a shader fix; actual-main and real-view
qualification remain pending.
