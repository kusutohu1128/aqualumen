# Water performance attribution, not shipping acceptance

2026-10-03. This slice measured the heavy experimental water path without
changing optics, the support gate or fresh permission checks. Normal0.6 and
physics0.2 are restored; the ordinary game is live and paused. The full realism
goal, underwater dark bands/polygon boundaries and motion remain open.

## What was actually measured

One original baseline and two matched control/profile pairs used the frozen
zero-physical ZIP SHA-256
`33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda`.
All runs used the exact disposable V2 world, near/deep/tilt views,900p,
VSync off, cap120, render12/sim6,10s warmup+10s sampling per view.
These performance numbers describe the TEST path, not the restored normal
shader or a promised frame-rate floor.

| Pair | Control mean FPS near/deep/tilt | Profile mean FPS near/deep/tilt |
|---|---:|---:|
| First | 13.515 / 11.822 / 15.782 | 13.537 / 11.812 / 15.758 |
| Repeat | 13.412 / 11.744 / 15.672 | 13.392 / 11.735 / 15.638 |

Both profiles contain1680 total fresh supplier checks; every check authorized
and performed the complete233,866-byte ZIP read/hash. Measurement failures,
rejections, original exceptions, unowned hashes and nested suppliers are zero.
The822 sampling calls average0.581ms for authorization and0.220ms for its
nested full read/digest/hex/equals expression. Count-aligned authorization
share is0.685–0.889% of frame intervals; nested hash share0.258–0.343%.
The nested interval is NOT additive and does not isolate SHA computation.

This rules out measured fresh authorization/hash work as the dominant source
of the70–85ms frame intervals in these runs. Coarse per-process Java SM means
96.09–97.60% suggest substantial GPU work, but do not identify a shader stage,
certificate/FP64 cost or establish a GPU-timer speedup. Counts discard one
start row per sampling group; CSV has no direct absolute Iris timestamp join.

## Reproducibility and boundaries

- [Independent reader](cpu-independent-profile/README.md): both pairs' raw
  integer CSVs,12 PNG integrity checks, actual settings/poses/cleanup, source
  recovery24 files and generated JAR identity. Root final readers reproduce
  the two archived audits byte-for-byte. Historical point-in-time installed
  hashes are not a current-normal or every-run installation proof.
- [Profiler construction](cpu-profile/HANDOFF.md): TEST-only reversible
  instrumentation, full original checks and expression ordering retained,
  no permission/digest cache. Root4 build tests PASS; generated Java tests
  PASS. Existing failed construction/API test evidence retained separately.
- [Prepared CPU candidate](cpu-prepared/README.md): new standalone helper
  caches identical raw-view/eta interval work for ONE cap invocation. All377
  CPU evaluations preserve old classes and interval endpoint/valid bits;
  root5 public tests PASS. Source-level operation reductions are not GPU
  measurements. No GPU test, actual-main identity, pack build or adoption.
- [Lifecycle](LIFECYCLE.md): root-owned clean exits, ordinary-save comparison,
  restoration and fresh paused return image. Original normal ZIP SHA-256
  `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`;
  physics0.2 SHA-256
  `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.

Only first-pair tilt PNGs were root-compared byte-identical; do not generalize
that to all frames, whole-scene optical identity or motion. The Sun-support
slice's rim improvement survives, but fine underwater dark bands remain.
The pre-existing OpenAL/SoundSystem startup error also remains separate and
unfixed. No external Claude/API call, commit or push occurred in this slice.
Tracked pre-existing shader/physics changes and the old sealed packet were
preserved. `source-snapshot/` contains exact newly authored source/test bytes.

## Next bounded work

First isolate the actual GPU water-draw cost; do not remove permission checks.
Qualify prepared-context class/interval bits on actual NVIDIA, then actual-main
maps/48-target inputs/classes/counts/reasons/TES/C0-depth identity. Measure
water draw excluding uniform/readback/output costs before claiming a speedup.
Only after these gates should a new pack be considered. Separately investigate
remaining bands with one optical causal variable; no density/settings sweep
or broad algorithm change has been adopted here.

This packet's SHA256SUMS seals evidence, not a visual, physical, performance or
full-goal acceptance. The full goal stays active.
