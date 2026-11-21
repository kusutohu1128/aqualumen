# Raw-view Snell boundary: exact support and a bounded stable candidate

CPU/source derivation only. No shader, tool, GL or game change; no runtime RED or
physical/shipping acceptance is claimed. The retained Iris reason result remains
2/16 applied, first2=10 / first3=2 / first4=2; its C9–C12 capture does not contain
the exact n/v/Sun targets. The earlier conditional reason3 plan is not adopted.
Source pins: cap `a0708a5d...a91196c3`, old residual `def6b357...bbfd9c`, CPU
light kernel `f5b6db70...352de92`. This derives the shader's **raw-view convention**,
not a normalization of observed rays or a radiometric/Maxwell-model proof.

## 1. Exact inverse, exactly unit target

Let eta>1 (the shader's binary32 literal eta is 1.3329999446868896), finite raw
view v, m²=v·v, K²=1+eta²(m²−1)>0, and unit air target t. A unit facet h uses
GLSL's forward law

    f=h·v; D=1−eta²*(1−f²)
    r=−eta*v+(eta*f−sqrt(D))*h,  f>0, D>=0.

Squaring gives r·r=K². For desired r=K*t, define

    a=K*t+eta*v; A=|a|; h=a/A
    S=K+eta*(t·v); q=eta*f−A=−K*S/A
    t·h=S/A; D=q².

These identities follow by expansion, not by evaluating the cancellation-prone
D expression. Since eta²*m²−K²=eta²−1>0, A>=eta*|v|−K>0 and
f>0 for every unit target. Moreover eta*f−sqrt(D)>0 on a transmitting branch,
so h=a/A is the **unique facing preimage**; flipping it cannot repair support.
For the declared downward-graph facet distribution and upward air source,
positive transmission exists exactly when **a.y<0 and S<0**, with t.y>0.
At S=0 the critical transmitted coefficient/kernel limit is zero. S>0 has no
facing forward preimage for this target. a.y>=0 has no finite downward-graph
facet preimage. These are support statements of this model, not scene visibility.
K²<=0, zero target, NaN or overflow are outside this API's admitted ray domain;
do not disguise them as a physical zero-light result.

On supported points use sqrt(D)=q>=0 and the algebraically equivalent forward
coefficient eta*f−q=A, hence r=K*t. This reconstructs forward Snell without
subtracting nearly equal terms in D or repeatedly calling float32 refract.
The original reflected-y/SSR gates are **not** transmitted-Snell support tests.

## 2. A generated binary32 target is not exactly unit

Let U=t·t>0 for the unchanged raw target bits. Keeping the old literal desired
ray K*t requests squared length K²*U, not K²: unless U=1 it has no exact forward
preimage. For its old a=K*t+eta*v and q=eta*f−A, exact expansion instead gives

    D=q²+K²*(1−U)
    r_forward−K*t=(q−sqrt(D))*h.

Even perfect arithmetic therefore has reconstruction error near critical; for
q>=0 it equals K²*(U−1)/(q+sqrt(D)) along h. This is not just bad GPU sqrt.
Treating that mismatch as absent physical sunlight would be wrong.

An explicit **direction-semantics** candidate leaves raw v/t unmodified and
solves the outgoing magnitude: rho=K/sqrt(U), desired r=rho*t. Define

    a=rho*t+eta*v; A=|a|; h=a/A
    S=rho*U+eta*(t·v); q=−rho*S/A
    D=q²; r=−eta*v+(eta*f−q)*h=rho*t.

This is a declared norm-aware magnitude parameterization, not silently repairing
an observed vector. If the API instead insists on literal K*t, U!=1 is a numeric
contract mismatch/UNKNOWN, not support-zero. No epsilon, vector flip or norm
floor is justified. The Jacobian is with respect to **unit-direction solid
angle**, so J=K*q/(A²*|h.y|³), not the old formula with unscaled raw t·h.

## 3. Stable Fresnel and the positive Gaussian critical limit

Keep the legacy clamp c=clamp(f,0,1). On the supported near-critical domain c=f,
ct=q, and the original denominator floors are inactive. Compute directly

    T=2*eta*f*q * [(eta*f+q)^(-2)+(f+eta*q)^(-2)]
    P=f/(|h.y|*M),  M=meanNormal·v/|meanNormal.y|>0
    J=K*q/(A²*|h.y|³),  kernel=p(slope)*P*T*J.

This is exactly 1−the original unpolarized Fresnel, but avoids losing tiny T by
subtracting reflectance from one. If raw f>1, retain c=1 and ct=1; do not use q
as a substitute for the clamped Fresnel law there. Keep the existing Gaussian
covariance/normalization and slopes, with strictly SPD covariance and no floor.
At a finite critical facet h_c.y<0, p_c>0, f_c=sqrt(1−eta^-2), and fixed M>0,

    kernel/q² -> 2*p_c*K*(eta+1/eta)/(M*A_c²*|h_c.y|^4) >0.

The limit is quadratic zero, not a step of constant transmitted power. A proven
unsupported point contributes zero to the source integral **without survivor
renormalization**. Unknown arithmetic, receiver visibility, old legacy rejection
or reflected-y failure cannot be relabeled zero. This support-zero integration
policy is a separate model slice from stable arithmetic at supported nodes.

## 4. Bounded arithmetic, not an unproved float32 fix

Prefer q=−rho*S/A over a second rounded facet dot, but every pure32 form still
subtracts O(1) quantities to obtain tiny S. For IEEE nearest-even normal-range
operations, gamma_n=n*u/(1−n*u), u=2^-24, bounds a three-term dot by
gamma_5*sum(abs(products)). Propagate outward intervals through m²,K²,U,b=v·t,
sqrt/division, S,A and q, including permitted FMA variants. Only an interval
strictly S<0 and a.y<0 proves supported; strictly S>0 or a.y>0 proves absence.
An interval crossing a boundary is status−1/UNKNOWN, never sign-clamped to zero.
These are IEEE replay bounds, not an assertion of general GLSL transcendental
accuracy; using captured target bits removes sin/cos variation from this seam.

A narrow TEST candidate can calculate these scalars, h, P/T/J and forward ray
in binary64 from exact raw32 inputs (or fully certified double-single, including
sqrt/division), then cast witnesses/results once. Binary64 u=2^-53 makes this
family's ~1e−6 support margins resolvable; the actual linked node still needs its
public RED→GREEN and predeclared numeric gates. Compensating only the dot does
not bound errors in K/rho/A. On ordinary unfused32 replay, q's relative error for
dot/S/numerator forms is respectively .0251%/.00551%/.00551% at j13,
.1809%/.5035%/.5035% at j17, and 3.702%/7.018%/2.281% at j20. Stable T/J alone
does not establish the previous 2e−4 relative radiance bound across this family.
Along this two-dimensional tilted family, h changes O(offset²), r and q
O(offset): distinct targets can
round to the same facet32. Compare returned facet/ray separately to the precise
reference; feeding rounded facet into a fresh float32 refract is a different
representation, not an exact oracle. Do not recompute T from that rounded facet.

## 5. Predeclared tilted positive fixture, and its integration limitation

Use eta32 above, raw v=(.31224989891052246,−.949999988079071,0), observed frozen
C=(.006807451602071524,.0027949956711381674,.002802651608362794), and mean32
n=(−.5062107443809509,−.8624098300933838,0). m²=.9999999767198666,
K²=.9999999586337905, M=.7667179239782286. Generate—not replace—the test target:
e=v/|v|, e_perp=(−v.y,v.x,0)/|v|, c_j=(−K/eta ± 2^-j)/|v|,
t_j=round32(c_j*e−sqrt(1−c_j²)*e_perp), j12..20. Minus is supported, plus is
absent; both sides are retained. The exact center target is approximately
(−.8624098225493084,.5062107248670957,0). The helper still receives raw v.

Independent binary64 formula evaluation (not GPU output/high-precision test):

| supported j | raw target x,y | q | T | J | positive kernel | ordinary32 D |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | −.862316370010376, .506369948387146 | 1.8464194e−4 | .0011626983 | .0003706912 | 2.0436051e−5 | 0 |
| 17 | −.862403988838196, .506220698356628 | 1.1554398e−5 | 7.2801330e−5 | 2.3187756e−5 | 8.0041583e−8 | −1.1920929e−7 |
| 20 | −.862409114837646, .506211996078491 | 1.4545575e−6 | 9.1651127e−6 | 2.9189883e−6 | 1.2684922e−9 | 0 |

Density stays ~47.4152 and P~1; inverse reflected-y stays ~−.190494, with facet-y
~−.862410 and positive outgoing-y. At j13 old32 reconstruction error is .0001593
against existing inverse bound ~1.271e−6. Stock disk radiance times this kernel
has red directional integrand ~2.7076 at j13 and ~.010605 at j17: these are
nonvacuous **directional integrands, not pixel C0**. No source rescaling is used.

However this mean/C's unchanged nine-node legacy rule has six TIR nodes and max
reflected-y **+.017904**, so the old full/base wrapper gate excludes it before
the cap loop. Use a public real-main **node** seam for numeric RED, separately
observing the legacy exclusion; do not bypass it and call the whole wrapper
fixed. A preliminary 4×12 support-zero cap sum has 24 supported nodes and RGB
~(.0145303,.0177593,.0205846), but is neither a refined reference nor an adopted
mixed-support/visibility policy. No host/software result proves actual GPU,
Iris coverage, receiver correctness, full critical/rim convergence or shipping.
