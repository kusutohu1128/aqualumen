# Independent GH3 phase reference (CPU only)

`evaluate((Cxx,Cxz,Czz), phase_degrees=0|45, mean=(muX,muZ))` uses the fixed white tensor rule
`z=(-sqrt(3),0,sqrt(3))`, `w=(1/6,2/3,1/6)`, then **mean + L R z**. Rotation is before Cholesky, not after it. All nine product weights are positive and their exact sum is one; coincident nodes in degenerate cases are not removed or reweighted.

The mathematical domain is exact PSD: `Cxx>=0`, `Czz>=0`, `Cxx*Czz>=Cxz^2`, and `Cxx=0 => Cxz=0`. When Cxx is zero, L has only `Lzz=sqrt(Czz)`; otherwise `Lxx=sqrt(Cxx)`, `Lzx=Cxz/Lxx`, `Lzz=sqrt((Cxx*Czz-Cxz^2)/Cxx)`. There is no epsilon repair or input normalization. Fraction preserves integer/rational/decimal-string inputs; float inputs mean their exact binary64 values.

The one-dimensional rule has Gaussian moments through degree five. Rotation of a polynomial of total degree at most four remains in that exact tensor domain; therefore `E[L R z]=0` and `E[(L R z)(L R z)^T]=C`. The independent Gaussian targets use Isserlis pair sums, not another copy of the node transform. Fourth moments are `3*Cxx^2`, `3*Cxx*Cxz`, `Cxx*Czz+2*Cxz^2`, `3*Cxz*Czz`, `3*Czz^2`. Decimal80/120 node sums are compared with the predeclared `1e-60*(1+abs(reference))` agreement policy. This is numerical agreement, not a general interval enclosure.

Scope is **TOTAL degree <=4**, not every per-axis degree <=4. White X6 is 9 at phase0 and 27/2 at phase45 (Gaussian15). White X4Z4 is 9 and 9/4 respectively (Gaussian9); degree eight is explicitly not promised. For `C=(4,0,1)`, the incorrect order `R L z` rotates the covariance to `(5/2,3/2,5/2)`. These counterexamples prohibit interpreting low-order agreement as equal distributions or convergence.

The separate binary32 diagnostic rounds exact rational primitives to nearest/ties-even, including sqrt by squared midpoint comparison. It uses the existing sqrt3 decimal literal and the declared phase45 literal `0.7071067811865476`, not a GPU-observed rotation. Products/sums/division/sqrt round after each primitive (no FMA); weights are never renormalized. White degree-four moment diagnostics use a predeclared `64*2^-23` abs+relative bound. Their moment sum is exact rational arithmetic on rounded nodes/weights, **not GPU accumulation**; transformed covariance/moment errors are descriptive, with no universal covariance-conditioned error bound. Binary32 overflow is unavailable and zero is canonical positive zero, so this is not signed-zero/GPU arithmetic equivalence. The rank-one `(1,1/10,1/100)` fixture remains valid mathematically but has a negative rounded Schur complement and reports binary32 unavailable without repair.

Replay:

```sh
python3 -B -m unittest discover -s tools -p test_water_gh_phase_reference.py
python3 -B tools/water_gh_phase_reference.py --covariance 4 1 3 --phase 45 --mean 1/4 -1/2
```

Eight public CPU tests pass. Numbered RED logs are CPU interface/output-contract failures, not shader bugs; the initial Decimal zero-power implementation failure is retained separately. Five exported example JSONs and exact source/test snapshots are pinned in HANDOFF.json. No GL, shaders, packs, game, installed files or frozen older evidence were modified. Mathematical nine-node count and any declared Sun48 target count do not prove actual executed shader-node counts. Physical, convergence, rendering, band-removal, GPU and shipping acceptance remain false.
