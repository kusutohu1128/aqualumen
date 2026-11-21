# Independent saved-profile replay

Both saved pairs pass this bounded CPU evidence audit. No GL, game, process,
configuration, world, shader or original artifact was changed. This is measured
attribution, not an optical, visual, GPU-stage, FPS-floor or shipping acceptance.

Replay (stdout only; no live game directory required):

```sh
python3 reports/2026-10-03-water-performance/cpu-independent-profile/audit.py
python3 reports/2026-10-03-water-performance/cpu-independent-profile/audit.py --control control-repeat-run --profile profile-repeat-run
```

`first-pair-audit.json` and `second-pair-audit.json` retain independent output.
Both byte-equal replays passed. Twelve 1600×900 PNGs passed full bounded CRC,
zlib/scanline integrity checks; all 1,633 positive integer-nanosecond intervals
and derived metrics matched. Exact V2 UUID/seed, focused first-person WATER eye,
near/deep/tilt pose, shader selection/hash/nonfallback, cleanup, 120 cap, VSync
off, render12/sim6 and actual 10-second warmup/sample were checked. No old
2560×1440 report validator was weakened.

## Counts and time attribution

Profile1: 844 calls, all authorized/owned hash calls; frames1139–1982 continuous,
supplier83. Sampling groups136/119/158 correspond to CSV135/118/157 plus one
discarded start boundary each. Profile2: 836 calls, frames857–1692 continuous,
supplier83; sampling134/118/157 corresponds to CSV133/117/156 plus one each.
Both have zero measurement failures, denied outcomes, original throws, unowned
hashes and nested suppliers. Every owned hash read exactly233,866 bytes.

| Scene | Profile1 auth/hash mean (µs) | Profile2 auth/hash mean (µs) | Count-aligned auth share1/2 | Nested hash share1/2 |
|---|---:|---:|---:|---:|
| Near | 585.123 / 221.363 | 613.101 / 227.887 | 0.79258% / 0.82137% | 0.29979% / 0.30530% |
| Deep | 579.855 / 218.346 | 584.996 / 220.278 | 0.68498% / 0.68662% | 0.25782% / 0.25843% |
| Tilt | 558.583 / 214.929 | 568.165 / 219.046 | 0.88013% / 0.88862% | 0.33862% / 0.34260% |

Means include all sampling calls; shares exclude the first row of each sampling
group using the source-confirmed Recorder tail/start-boundary semantics. CSV
does not contain Iris frame timestamps, so this is count-aligned aggregation,
not a direct absolute-timestamp join. Sampling totals (including start rows)
are authorization236,835,506 / 240,387,059 ns and hash90,047,319 / 90,919,950 ns.
Whole-run totals also include warmup/setup/screenshots and are separately saved.
Authorization includes some wrapper work. Hash includes the complete
readAllBytes/digest/hex/equals expression and observation; it is nested in the
authorization interval, NOT additive or isolated SHA time.

Control1/profile1 mean FPS (near/deep/tilt):13.515/11.822/15.782 versus
13.537/11.812/15.758. Control2/profile2:13.412/11.744/15.672 versus
13.392/11.735/15.638. All1,633 intervals exceed the old16.667ms reference;
worst88.609798ms. This is not an adopted performance floor. The measured fresh
authorization/hash interval does not account for the dominant70–85ms frame
intervals. Per-process Java SM activity is high (whole-run means96.09–97.60%),
but these coarse sensors include warmup/setup and do not isolate shader stages.
ZGC names/2–6GiB heap are recorded; no GC-pause causality is established.

## Provenance and limits

All24 parent/source erasures recover exact archived bytes; both generated JARs
match independent rebuild bytes and manifest pins. `installed-at-audit.json`
records actual read-only ZIP/JAR hashes while TEST aliases were installed. It
is point-in-time evidence, not proof of every historic install or the restored
ordinary configuration. Profile source8f87…136d, benchmark330488…80de,
Sun66fe…0920 and ZIP331644…8cda match. First pair has actual prepared scalar int1
guard observations after completion; second pair intentionally has none. The
two profiles' supplier outcomes still prove844/836 respective authorized
calls, not fragment fetch or WNS application. Pose matching and selected PNG
byte equality do not imply whole-scene/frame optical causality. Natural dark
rim/bands, motion, precise GPU cost and full-goal acceptance remain open.
