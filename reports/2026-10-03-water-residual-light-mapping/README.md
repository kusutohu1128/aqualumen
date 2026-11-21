# CPU inverse-Snell mapping checkpoint — not a shader fix

2026-10-03 JST. This small checkpoint verifies the mathematical seam proposed
after the [actual angular-source diagnosis](../2026-10-03-water-residual-angular/README.md).
It does **not** implement a source integral or alter any shader/Mod/runtime asset.
No GL, game automation, native solar, natural appearance or shipping proof is
claimed. The full water/sun/shore/cloud/motion goal remains active.

For qualified exact-unit water-eye direction v, outward light direction t and
water-to-air eta>1, the prototype checks n=normalize(t+eta*v), reconstructs
refract(-v,n,eta), and computes the current slope-measure Jacobian:

    ds / d omega_t = abs(dot(t,n)) / (length(t+eta*v)^2 * abs(n.y)^3)

It never flips the normal, normalizes invalid caller vectors, clamps a critical
branch or substitutes an epsilon for a singular determinant. Eta1, wrong
hemispheres/orientation, horizontal-normal singularity, critical/TIR, nonfinite
and nonunit callers are rejected. This is a restricted mathematical branch,
not a global dielectric model or the numerical behavior of native refract.

Two genuine public-API increments are retained:

- [Pass-through RED](cpu/01-pass-through-red.log): returning n=v produces
  off-axis forward reconstruction error0.19588084275. The inverse mapping
  then [passes](cpu/02-mapping-green.log).
- [Unity-Jacobian RED](cpu/03-jacobian-red.log):1 instead of9.01802703605 at
  normal incidence. The derived determinant then [passes](cpu/04-jacobian-green.log).

The [numeric observations](cpu/06-numerical-observations.json) compare five
normal/off-axis cases with independent tangent-plane central differences.
Step1e-5, absolute2e-8+relative2e-7, unit1e-12 and reconstruction1e-11 were
fixed before outputs. Maximum determinant error is3.009e-9; maximum forward
reconstruction error is3.331e-16. The root read all88 tool lines and92 test
lines, verified final source hashes and [reran six CPU tests](root-tests.log):PASS.

Source SHA-256 `7d2e9fb1fefc0d08a627232c79b0fcf67477a55a91c3f54e18e5716de6d2f6bf`;
tests SHA-256 `d1e3ee46f58fc91d1130fba15c779afb747f062fb84cc3f14667df161b3a5311`.
Byte-equal final source copies are retained in cpu/source.

The exact-unit CPU caller policy does not accept direct binary32 observer
vectors as a drop-in replacement. No Gaussian/SPD kernel, full source
integration, zero/rank-deficient residual policy, physical units/energy,
pixel filtering or temporal behavior is established. Next implement the
bounded sharp-source integral and demonstrate actual-main RED→GREEN against
the unchanged qualified continuous reference, then inspect actual Iris/rim/
motion. Ordinary0.6/physics0.2 remains paused; all work here is CPU-only.
