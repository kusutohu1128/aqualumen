# Literal GLSL CPU node host — frozen handoff

The public `--node VX VY VZ TX TY TZ ETA` CLI compiles the authored
`shaders/lib/water_snell_inverse.glsl` directly as C++. It does not copy the
candidate arithmetic, include OpenGL, create a context, or operate Minecraft.
Raw view/target binary32 values and bits are reported. Generated target direction
semantics and the norm-aware outgoing magnitude are explicit; raw view is not
normalized. The separately labelled frozen-parent port is a control, not an
independent oracle or complete legacy wrapper. That port explicitly normalizes
its generated target again; it is not an exact replay of arbitrary saved target
bits at the original cap call.

## Incremental public tests

- `01-normal-include-red.log`: missing GLSL include; tooling RED, not optics.
- `02-normal-green.log`: one normal-incidence tracer passes.
- `03-tilted-critical-numeric-red.log`: normal passes; independently supported
  tilted critical case fails candidate status `-1` instead of `1`.
- `04-host-double-compatibility-red.log`: initial numerical failure remains
  after adding host double vector types.
- `05-stable-host-double-compatibility-red.log`: new candidate requires an
  explicit host double `abs`; build failure is not a model failure.
- `06-two-node-green.log` onward: stable candidate passes the same numerical
  test, then proved-absent, invalid-target, tilted-family and up-family controls.
- `12-frozen-public-green.log`: **6 tests / 40 node invocations** pass, including
  all fixed `j=12..20`, both-side cases in both 18-case families.

Supported ray absolute gate remains `1e-7`; transmission and Jacobian relative
gates remain `2e-4`, against the independent public Decimal reference. Both
supported and absent sides are retained; no successful-point selection occurs.
`12-frozen-compile.log` is empty: the final compile has no diagnostics.

Final flags: `-std=c++17 -O2 -fno-fast-math -ffp-contract=off
-fsingle-precision-constant`. The last flag gives GNU C++ the GLSL float-literal
semantics; double internal operations promote these constants normally.
Initial logs precede this flag, so the initial literal-include run is not claimed
to reproduce every original GLSL float intermediate. Exact old binary32
discriminant cancellation is separately established by the reference replay and
the explicit-float legacy control. `initial-parent-host` and its saved output are
retained under that limitation, not advertised as the final binary.

## Independent source audit

The current function follows the note's norm-aware magnitude `rho=K/sqrt(t²)`,
unique facing inverse axis, supported transmitted coefficient, and
`J=K*q/(axis²*|facet.y|³)`. Its positive product transmission retains the original
incident-cosine clamp: raw facing greater than one uses clamped cosine and
transmitted Fresnel cosine one, not the raw Snell `q`. Returned float facet is
not fed back into a new float `refract` as an oracle; ray/T/J are individually
compared with the high-precision reference.

The fixed FP64 exclusion band returns invalid `-1` for uncertain signs and
`0` only for separated wrong orientation in the tested domain. It is a local
tested-domain safeguard, **not a general interval certificate**. Status0 is not
authorization to alter whole-source support-zero, reflection, receiver or
legacy full/base admission policy.

No saved-six cap integration is duplicated here; root owns the separate case
matrix. CPU node agreement does not prove NVIDIA execution, actual Iris reason
2/4 attribution, a fish-eye/rim/motion fix, radiometric/energy acceptance or
shipping readiness. No production caller, old frozen report, game config or
world was changed by this worker.

This worker's owned source/test/report writes stop after `HANDOFF.json`.
