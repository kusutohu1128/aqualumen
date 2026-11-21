# Independent saved-Iris replay

Both NEW roles pass saved-data qualification. This is CPU-only replay, not a GL/client action. The frozen wrapper and all old validators/artifacts were preserved. Reproduce:

```sh
python3 -B reports/2026-10-03-water-prepared-iris/actual-independent/audit.py reports/2026-10-03-water-prepared-iris --role reasons
python3 -B reports/2026-10-03-water-prepared-iris/actual-independent/audit.py reports/2026-10-03-water-prepared-iris --role inputs
```

Both saved root JSON audits reproduce byte-for-byte. Exact prepared pack recovery, typed int1 guard, all four distinct scalar RGBA32F bindings, all eleven restored FINAL state fields, linked four shader stages and unchanged actual rewritten VS/TCS/TES hashes qualify. Observer timestamps follow completion; the held first-person WATER near eye depth is 0.4998893079757707 m. Each PNG passes full bounded CRC/decompression validation at 1600×900; all raw integer-ns intervals and metrics are independently recomputed.

| Role | Intervals / raw ns sum | Mean FPS / 1% low | Worst/P99 ms |
| --- | --- | --- | --- |
| Reasons | 74 / 4,968,806,719 | 14.892912 / 14.293856 | 69.960129 |
| Inputs | 74 / 4,994,281,392 | 14.816946 / 14.261883 | 70.116966 |

Both are warmed near-only, 5 s warmup/5 s sampling, cap120/VSync off/chunks12+6; every recorded interval exceeds16.667 ms. Historical reference captures used 10 s warmup, so these numbers are not a controlled old/new performance comparison or a FPS-floor acceptance.

Reasons preserve 12/16 qualified application, minimum4 unchanged, complete48 calls at all16 selected points: absent502/supported266/unknown0/calls768. Four first failures are category3, with hemisphere-group170; the group combines3/9 and does not individually identify every failed node. All sixteen reason/status/covariance+flags/TES vec4s match the archived old-zero actual capture bit-for-bit.

Inputs retain twelve zero first-failure codes and four category3 first targets, each physically supported in the independent Fraction and Decimal80/120 references. All sixteen mean/called, rawview/requested, covariance/flags and firsttarget/reason vec4s match archived old-zero inputs bit-for-bit. C12 is firsttarget encoding, **not TES** here; no input-role application/count observation is claimed. Across both roles, 512 selected binary32 component comparisons match; this is not a whole-image comparison.

Reasons guard/stage/FINAL counters are2262/2262/2262; inputs are4198/4198/4199. Even equal counters do not prove a simultaneous draw or fragment invocation. Actual linked FS digests are exported separately from archive expansion hashes; post-Iris source text is not available for exact rewritten-line recovery. These raw records, PNGs, guard and stage snapshots are distinct captures.

Certified absence is exercised in the selected reasons records; the unknown branch is not. Firsttarget code0 means no observed first failure, not continuum zero or proof of all48 raw targets. No full natural-map coverage, motion, pixel-AA equivalence, energy/reciprocity, appearance, 1440p/FPS-floor or shipping adoption is accepted. This replay does not audit the separate three-view physical-display comparison or ordinary handoff.
