# Candidate solar-source integration seam (not implemented/adopted)

2026-10-03. Source-grounded follow-up to the residual angular experiment.
This is a proposed numerical architecture, not an executed fix or visual pass.
Finite GH3/9/17 actual-main diagnosis must establish its error/domain behavior
before this proposal becomes a shader implementation. Preserve all old failures.

The current helper sums a very narrow analytic Sun at fixed slope nodes. Adding
many such nodes can be expensive and can alter the all-or-nothing node domain.
If the controlled angular experiment confirms source undersampling, integrate
only the sharp solar contribution in light-direction space, while keeping the
same Gaussian slope measure and independently checking zero/singular limits.
This is not permission to blur the complete frame or enlarge the physical Sun.

## Explicit measure and inverse mapping

For current helper conventions, v is the water-side direction toward the eye,
I=-v, eta=1.333 and t is the outward air-side transmitted unit direction.
On a qualified branch, the lower-side interface normal is
n=normalize(t+eta*v). Check by reconstructing refract(-v,n,eta): orientation,
facing, air/water hemispheres and inverse error must qualify; no face flipping.
The slope coordinates are s=(-n.x/n.y,-n.z/n.y). The declared Gaussian density
is p(s), centered at the observed mean slope with the observed covariance.

The original projected-plane integrand is p(s)*w(s)*T(s)*L(t(s)), where
w=dot(n,v)/(abs(n.y)*meanProjected). Changing variables gives

    d omega_n / d omega_t = abs(dot(t,n)) / length(t+eta*v)^2
    d s / d omega_n = 1 / abs(n.y)^3
    K(t) = p(s(t))*w(s(t))*T(s(t))
           *abs(dot(t,n))/(length(t+eta*v)^2*abs(n.y)^3)
    source = integral K(t)*L(t) d omega_t

The first determinant follows differentiating sphere normalization of
t+eta*v, and the second differentiating the slope-to-normal graph. This is
the change of variables for the **current** legacy helper measure, not a new
Smith/multiscattering model or a correction of its radiance-index convention.
[PBRT rough dielectric](https://www.pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF)
provides the separate normal/direction Jacobian and transport-mode distinction;
its full BSDF must not be claimed from this partial measure.

## Proposed tests before implementation

- Independent finite-difference determinant checks at qualified inverse-Snell
  normals, including correlated covariance and off-axis directions.
- Compare light-domain integral with support-seeded slope-domain continuous
  reference for narrow diagnostic sources before changing native solarDisk.
- Genuine actual-main source-response RED against that same converged reference,
  then a minimal integration replacement, unchanged fixture and numerical gates.
- Native Sun disk integral must retain SUN_ANGULAR_RADIUS, cache beam, weather,
  projected solid-angle normalization and source units exactly. No enlargement,
  ad hoc gain or eta-squared factor to hide another radiometric mismatch.
- Positive-definite, well-resolved covariance first. Zero/rank-deficient limits
  need a separately verified policy; dividing by an arbitrary epsilon is not
  physical convergence. Preserve same-mean zero residual and all-TIR controls.
- Opaque/source visibility and branch changes remain observed independently.
  No whole-frame acceptance from source-only numeric convergence or changed
  rejection masks. Pixel footprint integration and temporal appearance remain
  necessary, particularly when the residual distribution becomes very narrow.

There is no candidate production change in this document. Current natural
shore/cloud/motion/critical-boundary requirements and full goal remain open.

## Subsequent actual diagnostic checkpoint

The [frozen angular-source experiment](../../reports/2026-10-03-water-residual-angular/README.md)
supports the undersampling hypothesis on a derivative-free, common-domain
fixture. Selected actual finite arithmetic matches the independent same-rule
calculation, while source-positive points differ substantially from converged
finite-window integration. GH17 is not a ground-truth or monotonic cure. This
qualifies the motivation for the proposed seam, not its mapping, integral,
physical model, native solar filtering or natural-rendering implementation.

The separate [CPU inverse-mapping checkpoint](../../reports/2026-10-03-water-residual-light-mapping/README.md)
now retains two public-API RED→GREEN increments and six passing tests for the
inverse branch and slope/solid-angle Jacobian. Exact-unit double fixtures and
five local finite differences qualify only that restricted mathematical seam.
No Gaussian kernel/source integral, binary32 intake, shader, physical units,
critical global behavior or real-view correction is implemented by it.
