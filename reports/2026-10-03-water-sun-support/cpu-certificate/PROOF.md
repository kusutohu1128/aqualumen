# Exact integer angular-support certificate (TEST only)

The public seam is `int waterSunSupportClass(vec3 rawV, vec3 rawTarget, float eta)`.
It returns 0 only for certified absence of the prescribed inverse-transmission
branch, 1 for certified strict support, and -1 for invalid, boundary, overflow,
out-of-domain, or overlapping intervals. This is not a Fresnel-zero, whole-water,
continuous solar-cap, pixel-AA, energy, performance, visual, or shipping claim.
The pure module has no shipping caller. Its literal GLSL source is exercised by
the C++ CPU adapter in the public test, not a port of candidate arithmetic.

## Physical branch and exact rational oracle

Raw binary32 input values are exact real numbers for this proof. Do not normalize
the observed view. The generated target is interpreted only as a direction;
its squared norm is retained in homogeneous comparisons, not silently set to 1.
Let `v=rawV`, `t=rawTarget`, `E=eta^2`, `V=v.v`, `U=t.t`, `B=v.t`, and
`K2=1+E*(V-1)`. The prescribed domain is eta>1, v.y<0, t.y>0, V>0, U>0, K2>0.
Let K=sqrt(K2), o=K*t/sqrt(U), and A=o+eta*v.

An admissible water-incident-side facet has f=v.n>0 and q=sqrt(D)>=0. Snell's
raw-view algebra gives `A=(eta*f-q)*n`. Since
`(eta*f)^2-q^2=eta^2-1>0`, the coefficient is strictly positive: the only
incident-facing inverse facet is +A/|A|. The opposite normal is not another
admissible water-incident solution. Also `eta^2*V-K2=eta^2-1>0`, so
eta*sqrt(V)>K. Cauchy-Schwarz then shows A is nonzero and v.A>0; incident
facing is strictly positive without a normalization assumption for v.

A downward facet requires A.y<0. Both K*t.y/sqrt(U) and -eta*v.y are positive,
so this is equivalent to

    K2*t.y^2 < E*v.y^2*U.                         (downward)

The forward transmitted side requires o.n<0, equivalent to
`K*sqrt(U)+eta*B<0`. Since K,sqrt(U),eta are positive, this is equivalent to

    B<0 and K2*U < E*B^2.                         (forward)

Under these strict conditions q=-o.n>0 and the raw Snell discriminant equals
q^2>0. These comparisons describe geometric support of this prescribed
single-transmission branch; they do not bypass existing Fresnel clamping,
reflection, inverse-reconstruction bounds, receiver policies, or full/base
admission. Raw f>1 cases still use the unchanged node/caller policy.

The independently authored Fraction oracle forms these polynomial expressions
directly from exact binary32 values. It does not import candidate arithmetic or
use Snell status as a certificate. Equality in ANY of the two comparisons or B=0
returns unknown, even if another strict inequality already opposes support.
This conservative extra rule is preserved by the interval module.

## Why integer intervals, rather than one-ULP float intervals

GLSL330 defines IEEE binary32 storage/bit encoding but does not require IEEE
operation precision. Its unsigned integers have exactly 32 bits and arithmetic
wraps to low-order bits. These properties, and `floatBitsToUint`, are the only
language numerical guarantees used by the certificate.
[GLSL330 specification, sections 4.1.3, 4.1.4 and 8.3](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.3.30.pdf).

The older GL arithmetic guidance is approximate rather than a strict one-ULP
error bound; shader5 `precise` controls expression order and type precision but
does not establish the missing exact rounding bound. Neither is used as such a
proof here. [OpenGL3.3, section 2.1.1](https://registry.khronos.org/OpenGL/specs/gl/glspec33.compatibility.pdf),
[ARB_gpu_shader5](https://registry.khronos.org/OpenGL/extensions/ARB/ARB_gpu_shader5.txt).

Consequently there is NO float arithmetic in the certificate, no FP64 rounding
assumption, no arbitrary epsilon, no nextafter, no sqrt/division, no precise
qualifier, no umulExtended, and no new extension directive. The existing pack's
other FP64 requirement is outside this pure module and remains unchanged.

## Q24 enclosure invariant

Each valid interval `[lo,hi]` represents `[lo*2^-24,hi*2^-24]`, with exact signed
integer endpoints bounded by M=2^30-1. A valid interval encloses the exact real
expression it represents. Any loss of this invariant returns invalid, propagated
to public class -1. No invalid interval can produce a class0/1.

Input guards accept only finite zeros or normal binary32 components with
|component|<=2, and 1<eta<=2. Raw subnormal inputs are unknown; no claim is made
about preservation of pre-shader subnormal values. IEEE bit decoding supplies
sign, exponent e, and exact 24-bit mantissa m. Its Q24 value is `m*2^(e-126)`.
For e>=126 a left shift of at most two bits is exact; otherwise an integer right
shift supplies the floor and a nonzero remainder raises the ceiling by one.
For very small normals the enclosing endpoint magnitudes are 0 and 1. Negating
and exchanging these bounds encloses negative inputs. Signed zeros are exact
zero points, while the public domain rejects zero v.y/t.y.

Addition/subtraction use the usual monotone endpoint sums/differences. Because
each operand endpoint lies in [-M,M], an intermediate sum/difference lies in
[-2M,2M], strictly within int32; it cannot overflow. The resulting endpoints
are then checked against M, returning unknown if they exceed the allowed bound.

Multiplication evaluates all four endpoint products. Magnitudes are safely
negated (INT_MIN is impossible) and split into two 16-bit limbs. Each limb
product fits uint32. Two modulo-low-word additions, each with an unsigned
comparison carry, produce the exact 64-bit high/low product. The high word adds
the high cross-product halves and the two carries. This is standard radix-2^16
integer expansion; with magnitudes<=M, the actual product is below 2^60, and
the nonnegative high-word summands cannot overflow uint32.

The product is divided by 2^24 using exact high/low shifts. A high word>=2^22
means the quotient>=2^30 and immediately returns unknown. Otherwise
`q=(high<<8)|(low>>24)` is exact, and `low&0xffffff` is the exact remainder.
Positive product bounds are q and q+1 when needed; negative bounds are
-(q+1) and -q. Ceiling formation remains within int32 and is then guarded by M.
The min of four floors and max of four ceilings enclose the bilinear product
over the full input rectangle. Correlations are not assumed, so dependency can
only widen the enclosure. Polynomial composition preserves the invariant.

V.lo,U.lo,K2.lo must all be strictly positive. Both downward and forward
left/right intervals must be disjoint, and B must strictly exclude zero before
ANY classification. Therefore exact equality or interval overlap always gives
-1. A left lower endpoint greater than the right upper endpoint proves the
strict opposing inequality; conversely left upper<right lower proves support.
Class0 requires at least one such exact opposition (or strictly positive B).
Class1 requires all support signs. These are mathematical certificates within
the explicit input/overflow domain, not an empirically calibrated FP error guard.

## Public evidence and honest RED labels

Nine CPU public behavior tests pass. Actual first-failure inputs from the frozen
Iris input audit classify as ten absent and four supported. All agree with the
independent exact oracle and frozen Decimal80/120 support classifications. The
frozen325 raw-node corpus classifies as eighteen absent and307 supported; no
false certificate occurs. The288 saved-view cases have NEW controlled CPU cap
targets, not observed actual Iris generated targets.

Critical controls include an exact forward equality (unknown), an exact downward
equality with another opposing gate (still unknown), and a strictly supported
raw target whose Q24 intervals overlap (unknown). In one exactly representable
Pythagorean control, one-ULP neighbors ARE rigorously separable and correctly
classify supported/absent. Invalid/nonfinite/subnormal/zero-domain and bounded
input/intermediate-overflow controls all stay unknown. Raw nonunit view and
nonunit target direction controls retain their prescribed semantics.

Initial reference-CLI and literal-GLSL host REDs were missing files/API seam,
not an optical bug. `04-incorrect-neighbor-expectation-red.log` preserves an
incorrect test assumption that every one-ULP neighbor must be unknown. Its
independent Fraction signs and interval proof instead justify [1,-1,0], so the
test expectation was corrected without changing shader arithmetic.
`05-incorrect-coverage-expectation-red.log` similarly preserves an incorrect
expectation that the frozen325 corpus must contain an unresolved interval. All
325 are actually separable; a distinct supported-overlap fixture tests the
required unknown behavior. Neither failure is advertised as a shader defect or
numeric RED. `06-full-green.log` is the final nine-test pass.

`cases.json` supplies344 raw-bit cases (325+14+5) for the root-owned pure GPU
replay:29 CPU absent,312 supported,3 unknown. No GL/game was used for this CPU
packet. GPU bit-identical integer replay, actual main integration, unchanged
receiver/reconstruction/full-base gates, critical/mixed-cap convergence, Iris
readback, and visual/energy adoption remain separate root-owned evidence gates.
Forty-eight certified-zero samples would not prove the continuous cap integral
is zero. Unknown must retain whole-wrapper fallback; supported must retain all
existing node/receiver checks; absent zeros only the angular source contribution
without survivor renormalization or deletion of the legacy full/base term.
