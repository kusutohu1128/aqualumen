# Stable inverse-Snell node — implementation checkpoint

Implemented a **TEST-only** pure GLSL inverse node, with numerical RED→GREEN
on the actual RTX 3080 Ti. It is not included by production water main or the
cap caller, and no shipping pack was built, installed or selected this turn.
The full realism goal and underwater fish-eye/rectangular-rim problem are not
complete. Diagnosis and TDD kept this slice to arithmetic, not presentation,
covariance, visibility or legacy admission tuning.

## Result and fixed scope

The authoritative `native-parent-final/` and `native-stable-final/` runs use the
final GPU exporter binary SHA
`85cfc23d1a2e3e0fd5e075c2778725c8e7bc900e60d1e72074b0d558b9830c2c`.
Actual GL is `4.6.0 NVIDIA 580.173.02`, renderer RTX 3080 Ti, with FP64 support;
three queried RGBA32F targets hold literal standalone-node outputs. Actual
attached sources, all typed uniforms before/after each draw, input bytes and
whole-map repeats are saved. The independent CPU replay and root replay agree.

| Fixed family | Inputs | Old node passes | Stable node passes |
| --- | ---: | ---: | ---: |
| Normal incidence | 1 | 1 | 1 |
| Up-target critical boundary, both sides | 18 | 9 | 18 |
| Tilted critical boundary, both sides | 18 | 9 | 18 |
| Six saved interior points × 48 controlled Sun directions | 288 | 266 | 288 |
| Total | 325 | 285 | 325 |

There are 307 supported and 18 independently unsupported inputs. The old node
rejects 18 **supported** critical cases. The other 22 old failures violate the
new, stricter facet/ray witness gate of absolute `1e-7`; they do not prove old
whole-wrapper failures. No case is omitted or relabeled from numerical failure
to physical zero. Maximum stable facet/ray absolute error is
`2.9733949968857587e-8`; maximum T/J relative error is
`5.2664187233375515e-8`, below the fixed `2e-4` gate.

Six derived 48-node source-response sums pass against both the independent
high-precision node reference and the frozen public Sun control, with unchanged
absolute `2e-6` + relative `2e-4` bounds. These are Gaussian/projected-area/T/J
**math sums, not rendered C0**, cap convergence or water-main acceptance. Both
old and stable interior response sums pass. No reflected-scatter subtraction,
source rescaling or survivor renormalization is introduced.

Root's 23 new CPU public tests pass. Retained `make check` passes all 11 linked
program pairs and existing NVIDIA checks; it does not compile the new module
through a production caller. The separately executed literal module is the
new shader's actual-GPU evidence. No Minecraft FPS result is claimed.

## What changed

`shaders/lib/water_snell_inverse.glsl` implements
`waterSnellNode(rawView, generatedTarget, eta)`. Raw binary32 view and eta are
preserved. A generated target explicitly denotes a direction: its rounded
norm is accounted for, rather than assuming those bits are exactly unit.
Inverse geometry, positive-product transmission and Jacobian are evaluated
internally in FP64, then cast once. The tiny supported discriminant is not
recovered by subtracting two order-one terms, nor by re-refracting a rounded
facet. The existing reconstruction bound and Fresnel incident-cosine clamp
are retained. Status is supported / separated unsupported / invalid-uncertain;
the local FP64 roundoff guard is **not** a general interval or energy proof.

The initial literal-parent helper, numeric failures and tooling/build failures
are retained separately. Initial CPU unsuffixed literals could promote to
double; that host result alone is not faithful full-GLSL binary32 replay.
Explicit float replay and actual parent GPU failures provide that evidence.
The auditor's initial accidental scalar application of the vector gate is
also retained and explicitly corrected, without changing inputs or bounds.

The first non-final native exports remain as historical artifacts. Their v1
exporter was built before the final storage-query changes. Only the `-final`
runs are authoritative for the final source/binary provenance.

## Still required

The tilted positive node has finite positive Gaussian power and valid reflected
world hemisphere, but its unchanged legacy nine-node full/base admission still
rejects the overall fixture. This arithmetic fix does not bypass that gate.
The earlier actual Iris 2/16 application result remains negative. Its ten
compound facet/critical failures lack raw n/v/Sun/target exports, so the current
constructed reproduction does not establish their individual causes.

Water-main/cap integration, actual-input attribution, mixed physical support,
rim/critical convergence, pixel AA, Iris application, full-frame motion,
performance and physical energy/reciprocity remain unaccepted. See [NEXT.md](NEXT.md).
Normal 0.6/physics 0.2 is restored and freshly viewed paused; no ordinary save
copy was restored. See [ORDINARY-LIFECYCLE.md](ORDINARY-LIFECYCLE.md).

## Evidence and CPU-only reproduction

- [Predeclared experiment](EXPERIMENT.md), [math convention](cpu-math/NOTE.md),
  [independent reference](cpu-reference/DERIVATION.md).
- [Full independent replay](cpu-independent-gpu/result.json),
  [audit scope and correction](cpu-independent-gpu/AUDIT.md),
  [root replay](root-independent-audit.json).
- `source-snapshot/` pins all nine new module/tool/test sources. `SHA256SUMS`
  seals this packet; earlier frozen packets remain unchanged.

```sh
python3 -B -m unittest discover -s tools -p 'test_water_snell_boundary*.py' -v
python3 -B reports/2026-10-03-water-snell-boundary/cpu-independent-gpu/audit.py reports/2026-10-03-water-snell-boundary
```

These replay checks do not launch GL or Minecraft. GPU reruns require the
ordinary client to be cleanly saved/closed first and NEW output directories.
