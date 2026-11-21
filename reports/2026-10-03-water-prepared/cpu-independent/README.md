# Independent node replay

CPU-only replay of root's completed `node-native-v1` archives passed. No GL,
game, process, world, settings, shader or prior-packet actions were performed.

```
python3 -B tools/water_sun_prepared_audit.py \
  reports/2026-10-03-water-prepared/node-native-v1 \
  --probe-receipt reports/2026-10-03-water-prepared/root-node-receipt.json
python3 -B -m unittest tools/test_water_sun_prepared_audit.py -v
```

All 376 records were retained: 344 frozen cases plus 24 invalid/boundary and
eight signed-zero/nonunit CPU fixtures. Classes are unknown 27, absent 29,
supported 320. The 65 groups, 48 maps (288,768 bytes), 2,256 typed before/after
uniform records, eight actual integer storage/attachment/routes and three
attached programs/sources match the saved contract. All 13,536 interval triples
were independently recalculated with Python unbounded integer/Fraction
arithmetic, rather than copying GLSL uint16-limb multiplication. Raw echoes,
individual classifications, six interval endpoints/validities, context validity,
group count/checksum and repeated bytes match; signed zero is not normalized.

The root-executed binary is `41703de8…75aa93`, explicitly distinct from the
agent's absolute-path binary. The receipt's source/binary snapshot hashes and
root completion are checked; attached source bytes are recovered from the
pinned construction, not accepted merely because producer `PASS` flags agree.

Eleven public tests pass. Logs 01/03/05/08 are software-interface REDs, not
shader failures. Log 10 retained a test-fixture mistake: setting `selected` to
its already-zero value was not a corruption. The corrected nonzero change is
rejected, and log 11 passes. Corruption tests write temporary copies only.

This qualifies the fixed standalone classifier/cache identity, not physical
truth for the additional fixtures, water-main integration, speed, Iris,
pixel-AA, energy, natural appearance or shipping adoption. The old role's
interval telemetry recomputes its primitive tree; it is not an internal STORE
inside the original classifier. Actual-main final-source/raw/timer review is
separate and pending. The reader emits no native success for absent, synthetic,
stale or malformed evidence.
