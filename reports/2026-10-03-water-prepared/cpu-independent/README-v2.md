# Corrected independent node replay (v2)

This revision supersedes the v1 independent arithmetic-coverage claim. Root
found that v1's per-record loop was outside the role/capture loops, checking
only `reused` repeat. Thus v1 actually checked 376 raw arithmetic records /
2,256 interval triples, while incorrectly reporting 13,536 triples. The older
reader/tests, result, handoff, README and logs are retained unchanged.

The public regression first changed BOTH repeats of OLD or WRAPPER endpoint,
class and raw-input fields and updated the hash ledger. All six corruptions
incorrectly passed v1; `12-every-role-red.log` preserves this real auditor
defect, not a shader failure. The minimal fix nests the record loop correctly
and increments coverage counters at the actual checks. All six corruptions
are now rejected; all 12 tests pass (`14-v2-public-tests-green.log`).

```
python3 -B tools/water_sun_prepared_audit.py \
  reports/2026-10-03-water-prepared/node-native-v1 \
  --probe-receipt reports/2026-10-03-water-prepared/root-node-receipt.json
python3 -B -m unittest tools/test_water_sun_prepared_audit.py -v
```

`node-audit-v2.json` replays the SAME unchanged root GPU archives. PASS now
includes 2,256 actually checked raw arithmetic records and 13,536 actually
checked interval triples across all three roles and both repeats. The 376
classes remain unknown 27 / absent 29 / supported 320; all 65 groups, 48 maps,
typed input/state/storage/source checks and original proof limits remain.
This is not water-main, performance, Iris, physical, AA or shipping acceptance.
