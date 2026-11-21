# Independent physical-display saved-data audit

`python3 -B reports/2026-10-03-water-sun-support/cpu-independent-physical-view/audit.py reports/2026-10-03-water-sun-support`
prints the CPU replay JSON without writing captures, running GL or controlling
Minecraft. Its optional `installed_packs` public filesystem boundary is used
only by synthetic CPU tests; the actual replay checked the retained Lab aliases.

The two frozen packs change exactly two existing members and add exactly three
provenance/manifest members. Original FINAL is restored at
`43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf`;
water main is the exact role-STORE-free archive at
`dce58815841eba4c60b3cf80a39c0197290ffff09d495f84578078b8f9ebc3e4`.
Every other parent member is unchanged. This is **not fully observer-free**:
inherited MRT/TES and helper assignments remain. Its inherited atlas metadata
does not describe the current physical FINAL.

Public CPU tests: 9/9 PASS, with initial incomplete CLI, scene, archive and
complete synthetic filesystem RED→GREEN logs preserved. The missing-interface
REDs are tool construction, not shader failures. The first packet fixture had a
missing test reference to the public version schema; that error is retained in
07, the corrected fixture's interface RED in 08, and GREEN in 09. Synthetic PNGs,
metadata and prepared-stage/guard records are expressly mock filesystem inputs,
never observed Minecraft/GL evidence. Five further tests protect wrong head,
short sample, unapproved moving profile, guard0 and partial PNG rejection.

## Actual six-view result

`actual-audit.json` SHA256:
`6a8c8a8a0f3f281a9b15ee0257b3fdb81f02fee5e18add0b70f98f344528f9f3`.
Saved-data replay PASS: all six full PNGs, strict first-person WATER poses,
exact source/installed identities, separate prepared int1 guards/four attached
stages and 394 positive integer-nanosecond intervals qualified. The three
cross-policy camera/eye/rotation/depth pairs are exactly equal; both original
and rewritten VS/TCS/TES identities match. The prepared snapshots are after
run completion; their camera pose and PNG-frame application are not measured.

Controls: 10s warmup / 5s requested sample, actual raw duration at least4.9s,
1600×900, cap120, VSync off, render12/simulation6, fixed analytic phase120 and
factor4. Near/tilt measured eye depth0.499889308m; deep3.249889308m.

| Policy | View | Intervals | Mean FPS | Worst ms |
| --- | --- | ---: | ---: | ---: |
| reject | near | 64 | 12.97123619 | 77.981246 |
| reject | deep | 58 | 11.61015064 | 89.570573 |
| reject | tilt | 68 | 13.74259648 | 75.215708 |
| zero | near | 67 | 13.57274783 | 75.063862 |
| zero | deep | 59 | 11.88179025 | 85.703700 |
| zero | tilt | 78 | 15.79363864 | 65.833368 |

Every interval exceeds the 16.667ms reference. These short warmed900p
observations are not a performance-causality result, 1440p test or FPS-floor
guarantee. The implementation was not changed after this actual replay.

FINAL does not consume C9–C12 here: application, counts, selected TES texels and
the fixed16/min4 diagnostic gate are **unobserved, not waived**. A separate
prepared guard1 plus attached-stage hashes cannot supply those missing facts.
This auditor does not visually judge the six images or establish pixel
causality: live particles/contact fields can differ across client phases.
Natural appearance, native pixel-AA, motion, source physics, energy,
reciprocity, performance and shipping adoption remain false. Ordinary-world
save/restore and lifecycle proof are root-owned and outside this audit.
