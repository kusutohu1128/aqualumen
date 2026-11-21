# Resolved mean plus residual water-interface TEST

2026-10-03 JST. Previous resolved-normal slice was progress: actual comparison
images and retained raw draws established a bandwidth contribution; native v2
remains strict RED and the cutoff was not adopted. The full user objective is
unchanged and active. No frozen previous packet is edited.

## Pre-execution contract

Use the pinned factor4/phase120 resolved-normal parent, not a production change.
Add only two TEST helpers and an explicitly removable water-main hook after
the existing interface color. VS/TCS/TES, wave geometry, IOR, source units,
opaque tracing, cloud/solar/exposure policies remain separate.

The residual is an independent missing-power moment closure
sum((1-(G*B)^2)*M), directional xx/xz/zz, using the production waveMode and
normalization. It is not the exact residual of the deterministic soft split;
that split also has cross covariance. No ripple/gradient/normal-derivative
variance is silently added or double-counted.

Approximate the declared Gaussian slope distribution by positive tensor GH3
quadrature (9 nodes; standard-normal nodes0,+/-sqrt3, weights2/3,1/6,1/6).
Plane-area weights multiply dot(nodeNormal,v)/abs(nodeNormal.y), divided by the
same mean-normal projected factor. Finite facing nodes analytically sum1 for
this centered rule; never flip hidden nodes or renormalize survivors. This is
finite-node visible projected measure, not full Smith masking, multiple
scattering, a Gaussian-tail proof or reciprocal dielectric BSDF acceptance.
Each node evaluates Fresnel/TIR and directions before directional source color.

Domain: known submerged upper interface, depth>=.8, no ripple, inactive grazing,
all selected normals facing, reflection in the water hemisphere, non-TIR
transmission in the air hemisphere, and no opaque ray receivers. Reject the
whole operator outside this domain and retain the parent's resolved color.
No bright sky may be invented in TIR or caves; water reflection uses water
scatter/receiver, not the air-sky source. Environment/disk derivatives are
evaluated at every fixed node before TIR/hit/source conditionals.

## Vertical tracer before implementation

The first helper version is pass-through, with covariance but zero coefficient
mass/applied flags. Root will retain its actual four-stage water-main native
RED before implementing quadrature. The fixture has a uniform4m column,
zero gradient/ripples, sky exposure1/block0, zero solar cache/C8, seven qualified
central pixels and a directional zenith-cap LUT; camera C4 is unrelated.

Predeclared tracer limits: coefficient abs2e-5, covariance PSD tolerance1e-7,
absolute C0 response>=1e-5 at>=3/7 selected points, passive C0 abs5e-4/rel2e-4,
depth2e-6; disabled source recovery/repeats exact. New air arithmetic policy,
if exercised, abs8*binary32epsilon*.25+rel8*epsilon for C0, and abs/rel8*epsilon
for normal/derived values; geometry/flags/depth exact. This upfront bounded
policy does not change or retroactively pass the preceding strict-air RED.
The .25 C0 reference scale was specified before native execution when exact
dyadic source tags(.25,.125,.0625) were selected. The constant-source C0 gate
is the stronger vector absolute2e-5, with no relative term.

After that tracer, constant-source and all-TIR/critical-angle refinement tests
are separate increments, not assumptions inferred from a positive directional
response. Coefficient R+T conservation is not radiance/flux energy conservation.
Legacy source units remain unchanged: no blanket eta-squared compensation.
Actual Iris stills/motion, scene compatibility and adoption remain required.

References: [PBRT rough dielectric](https://www.pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF)
and [Walter et al. 2007](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf)
establish the distinct role of visible normals, masking and dielectric transport;
this bounded TEST does not implement that full model. Positive Gaussian
quadrature uses the standard [DLMF quadrature framework](https://dlmf.nist.gov/3.5).

Root owns all native GL/game. Agents are CPU/source only and are not Claude.
Ordinary saves/settings and previous packets must remain preserved; native GL
may run only after the ordinary client has saved/quit and every JVM is absent.

## First actual-main RED to GREEN

Normal client all-dimension SaveQuit08:26:57, fresh paused/title F2 images
08:25:43/08:28:22 viewed in separate calls before the relevant clicks; owned
launcher session56451 exited0. All Minecraft JVMs were absent. A fresh post-save
ordinary whole-tree backup is comparison-only, never restored. Settings and
normal0.6/physics0.2 remain unchanged while native work runs.

The new public native source-recovery CPU contract initially failed because a
single-marker eraser was applied to several passive STORE blocks. A minimal
multi-block recovery correction passed the same contract before GPU execution;
this CPU RED is not a shader/model failure. Both logs are retained. Native v1
source44e46766...d3a303e and binary5e189a99...f05006f stayed identical for the
actual stub/model executions.

Root's actual NVIDIA3080Ti/GL4.6 stub run exited1 RED with full JSON and raw
arrays. All14 selected known-water points were eligible, with nonzero PSD
covariance trace.00961010321043, but coefficient/source mass and applied flags
were zero and directional response0/7. All passive, repeat, flag, depth and
air/unknown controls passed. This is the intended actual-main behavioral RED.

Only then root implemented GH3 projected-weight per-ray integration, without
changing the tests, fixture, IOR/source units or acceptance thresholds. The
same native binary on the new model ZIP exited0 GREEN. Directional response is
nonzero at7/7 points (.00259486144388–.0120965685334 RGB-vector distance).
Constant-source C0 error max3.29728894173e-8; mass ranges
.999999940395–1.00000011921. Air/unknown C0 changes are0. All passive/repeat,
geometry-source/depth/flag controls pass. Selected points have no TIR; these
results do not qualify the critical-angle boundary or quadrature convergence.

`independent-native-v1-audit.json` independently recomputes352 saved raw arrays,
232 comparisons and input/provenance checks. It accepts this bounded native
fixture, not an independent per-node Fresnel oracle, physical energy, Iris or
natural appearance. The actual Schur remainder is positive(.00165508549), so
no covariance repair is exercised. Source review found a separate guard gap:
the implementation accepts a Schur remainder down to-1e-7 (slope² units), which
can admit a small non-PSD matrix and repair its Czz without reporting the repair.
That is not the determinant tolerance used in native qualification. A new
actual-main invalid-input regression is required before correcting that guard.

Retained ZIP hashes: stube6cce0e81193835036d6b3be33aa53a285be41f799785de576de2517122938d3;
GH3v1d30ed3716a25110aea4c1a35e90d2e36c5a248897e53c6aba560dc4609468553.
Snapshots live under `stub-source`, `native-v1-source`, `quadrature-v1-source`.
No new pack has been installed/selected; production and shipping0.8.6 unchanged.

## Actual boundary guard RED before correction

Root boundary driver source af39ea59...ca97377 / binary f0c19cb2...c63a9c60
ran only with all Minecraft JVMs absent. It exited1 RED. All five declared
fixtures qualified: zero-residual same-mean7 points, zero-wave air/unknown
negative controls, nonzero all-TIR5 points and invalid-input7 points. The
zero/negative/TIR cases passed. All-TIR transmission is exactly0, reflected
mass and TIR mass approximately1; the source is the water-scatter fixture,
not air sky. This is not a critical-angle sweep or continuity/convergence proof.

Only the deliberate invalid helper-input matrix (1e-8,2e-8,1e-8), with negative
determinant, failed: all7 points incorrectly had valid/applied1. It is an
explicit TEST input override, not a claimed production wave state. Root now
changes only the Schur guard to reject every negative computed remainder.
No silent covariance repair is accepted; sqrt's max remains solely to keep
rejected-node evaluation safe. Fixtures, driver, views, source policies and
thresholds remain identical for the next run. Original v1 ZIP/source/results
remain preserved; correction is a separately named v2-guard TEST package.

The same boundary binary then exited0 GREEN with all five fixtures still
qualified. Invalid-input7 points now have valid/applied0; no selected zero/TIR
or negative control changed acceptance. The original four-case tracer binary
also exited0 on the corrected package, directional response7/7 and constant
source vector error max3.29728894173e-8. Neither driver nor thresholds changed.
Corrected helper SHA def6b357c619b42e437a533d5a0ee751272afa27ecc434206de9fd6a95bbfd9c;
v2-guard ZIP SHA9c104ebebe77d5fd12cea95f75e30e686668a8b4605a4a5ea6227cc6e0ca5e85.
Independent saved-raw audit and actual-Iris observation remain separate work.

The new runtime auditor's seven public CLI tests passed again at root. Their
fixtures are explicitly synthetic CPU files; no actual Iris capture has yet
been qualified. The proposed observer changes only final diagnostic stores
C9 coefficients, C10 status, C11 covariance plus actual known/upper/underwater/
hook-eligible bitword, and preserves C12 TES stage values. Passive actual-main
C0/depth qualification is required before installing this observation pack.

## Actual-Iris plan before execution

After native passivity qualification only, use the existing exact disposable
AqualumenNaturalV2 UUID b22dbccb-2970-41e6-847f-f183b1ec923d / seed308060.
Normal save tree is comparison-only backed up and stays untouched. Temporarily
enable the retained physics0.3, benchmark0.3.9 projection-guards and stage0.1
instrumentation, with explicit exact-world opt-in markers; ordinary physics0.2
is recoverably disabled. No launcher private output is published.

Matched CONTROL uses the pinned resolved parent3a83...ab26; TEST uses the new
guard-corrected residual observation pack. Both retain factor4/phase120,
1600x900, chunks12/simulation6, cap120/Vsyncfalse/FOV60. The approved benchmark
alone sets underwater-up-near/deep/tilt camera/time/weather in this disposable
world, with warmup10s/sample5s per separate run. It places no terrain. This is
still-frame timing observation, not a FPS floor or 1440p qualification.

After each completed measurement, request one-shot selected unfiltered FINAL
C9-C12 readback at the previously declared16 texels. CONTROL roles use the
retained resolved auditor; TEST roles use the new residual auditor. Exactly
six FINAL requests plus at most two linked-stage requests are planned per
fresh JVM. Explicitly distinguish successful binding/readback from applied
operator statistics and from natural visual/physical acceptance. View every
actual run PNG. Do not infer same-frame PNG causality from a later readback.
If no TEST texel has applied1, report the lack of application instead of
calling an unchanged picture a successful physical model test.

CONTROL and TEST will use separate normally closed/reopened disposable clients
so pack selection/config changes occur offline, not via guessed live UI reloads.
Each fresh client needs three FINAL requests and one linked-stage request;
six/two above are the total across the comparison, not a claim of one JVM.
This is a matched fixed-scene comparison, not lockstep cross-client same-frame
identity, and startup/warmup scheduling can differ.

## Actual-Iris result and non-adoption

The final STORE-only observer native binary b319c541...255c9 exited0 with both
actual four-stage programs and same5 enabled draw buffers. Whole-array C0/depth
passivity and C12 exactness, all repeats, actual domain bits and selected
statistics passed. Selected C0 changes are0 at28 points;14 known points apply
the operator. Slots5–7 are cleared inactive storage, not shader-output proof.
Only then root installed observation ZIP3ab0d963...fcaf8.

Root captured and viewed all6 actual CONTROL/TEST near/deep/tilt PNGs in the
approved disposable world. All runs used the declared1600x900/cap120 controls,
had no Iris fallback, and retained raw frame CSVs and measured camera records.
Each TEST later selected FINAL snapshot has16 applied/valid points with actual
flagword15 and qualified coefficients/covariance (48 total). Both actual
linked TRANSLUCENT program snapshots show VS/TCS/TES/FS and patch/output arity3;
they are not exclusive-water draw or invocation-count proof. No native GL ran
while any Minecraft JVM was live.

The first actual residual readback audit was a tooling RED, not a shader-model
RED: observer0.3.9 additionally exports canonical inactive C13–C15 descriptors,
while the new synthetic CPU fixture had only four descriptors. The rejected
raw record and rejection trace remain unchanged. A new public CPU RED→GREEN
test preceded the bounded parser correction: optional unique exact inactive
13/14/15 dictionaries only. Active bindings, numeric/domain thresholds and raw
bytes were not altered or normalized into the old role validator. The new
auditor SHA ff1c587...ca51d38 accepts all3 original TEST raw records into NEW
`test-*-final-audit-v2.json`; the initial empty rejected output is explicitly
retained as `.rejected-empty`. Root final residual-family suite:23 CPU tests PASS.

Appearance is NOT accepted. In the C0 panel TEST produces several separated
small bright points where CONTROL showed one sun, and changes/broadens the
window with folds/striations still present near its rim. Discrete GH3 angular
aliasing is a source-grounded hypothesis, not yet a causal isolation or a
convergence result. Pixel-sized dark marks also occur in CONTROL deep, so they
are not all attributed to this change. Unresolved offscreen reflection, domain
fallback continuity, critical-angle refinement, lighting units, temporal/shore/
weather behavior and full physical water/sun objective remain open.

CONTROL's dark-purple normal panel was separately checked: encoded downward
normal n*.5+.5 is near(.5,0,.5), not the full bright-magenta warning. PNGs and
later selected readbacks have different times/frame counters; no same-frame
causality is claimed. Diagnostic panels are not ordinary game appearance.

CONTROL SaveQuit09:17:37 / owned launcher23725 exit0; TEST SaveQuit09:29:57 /
owned launcher50515 exit0, then all JVMs absent. Ordinary whole save tree still
equaled the fresh post-save comparison backup before ordinary relaunch; no
backup was restored. Normal config bytes/options were restored, experimental
mods and active markers recoverably disabled. Ordinary0.6/physics0.2 reopened
and root viewed fresh paused F2 `2026-10-03_09.33.52.png` after separate Esc/F2
calls. Host prismrun3837377 / Java3837452 / owned session92068 remain paused.
No native GL follows this ordinary relaunch. This is implementation/evidence
progress; no production/shipping source or candidate adoption, no full-goal
completion, no commit/push or external model/API call.

Independent read-only CPU audit `independent-natural-residual-cpu-audit.json`
checks all six saved PNGs, exact world/pack/camera/completion identity and all
six CSVs (3,552 captured frames), plus independently recomputes the 48 later
selected TEST points. Maximum mass error is2.384185791015625e-7 and coefficient
balance error1.7881393432617188e-7. Public PNG/metrics/camera helpers are reused
with the predeclared1600x900 policy; the generic1440p loader is neither called
nor monkeypatched. No resolution, numerical gates, old failures or raw records
are reclassified. Same-frame PNG causality, actual node count, full-frame
application, natural-water appearance, energy/reciprocity, shipping and FPS
floor remain explicitly unaccepted. This audit executes no GPU/app commands.

SaveQuit the disposable client normally, close its owned launcher and verify
every Minecraft JVM absent before further native work. Disable all experiment
mods/markers recoverably, restore normal config bytes (not save backups), verify
ordinary saves unchanged, then reopen ordinary0.6/physics0.2 paused with fresh
Esc/F2 and separate image view. No native GL after that ordinary relaunch.
