# Independent prepared-view MAIN replay

Both root-executed native packets passed the CPU saved-data reader; the reader never calls GL or Minecraft. It pins the distinct root execution receipts, archived executed binary (`99dcccea…4307e`), source tree, helpers, unchanged three geometry stages, eight linked programs, actual typed input/sampler/storage/state records and the separately replayed NODE v2 corpus. All source transformations recover the original exactly.

Per packet, 648 full physical/reasons/inputs capture/repeat maps (including depth) and 1,728 directly saved old/prepared per-node maps are finite and validated. Whole binary32 comparisons preserve signed zero. The all48 maps cover 19,022,112 node/pixel pairs per mode; the count ledger is reconstructed over all 396,294 view pixels. Both runs' six case records, including verified map/input/state/source hash ledgers, are exactly identical.

The fixed arithmetic subset was declared before output: center, four axial offsets and four corners listed in the reader. All called nodes at these nine pixels yield 1,440 both-mode observations / 720 unique raw seven-word inputs. Independent unbounded integer/Fraction classification agrees without normalizing inputs or selecting successful pixels. This is **not** an arithmetic oracle for every pixel.

MAIN has 4,148,736 called node/pixel pairs per mode, all supported: 3,170,352 central-positive, 733,152 wide60 and 245,232 wide90. MAIN absent/unknown branch coverage is zero. The separate NODE corpus's 29 absent / 27 unknown / 320 supported identities do not turn into MAIN branch coverage. Wide qualified/applied counts are 15,274/12,673 and 5,109/4,229; central positive is 5,025/5,025. Other three central controls have zero applications.

Actual draw medians for active central / wide60 / wide90 (old → prepared, ms) are 6.015488 → 5.737984, 2.018816 → 1.883648, 1.388032 → 1.243136 in the first run; 7.385088 → 7.117824, 2.027520 → 1.825792, 1.438208 → 1.271808 in the repeat. These are two isolated native `glDrawArrays` ABBA measurements, 2 warmup / 6 measured cycles, 12 samples per variant/fixture. Setup, uniforms, clear, synchronization, result wait and readback are excluded. They are not Minecraft FPS, a general speedup, an FPS floor, or statistical significance.

The per-node all48 C0/depth/TES raw outputs are **not** archived. Their producer in-memory hash records can be checked for consistency with saved physical maps, but cannot be independently recomputed as raw all48 neutrality. Physical/reasons/inputs C0/depth/TES neutrality and repeats are directly validated. No Iris, visual, energy/reciprocity, natural-map, shipping or general performance adoption is made.

Seven public CPU tests include both-mode class corruption with an updated hash ledger, signed-zero mismatch, a full-ledger error outside the arithmetic subset, omitted/truncated maps, and ambiguous source tags. Synthetic fixtures remain unit tests; missing APIs were software test RED, not shader RED. Preliminary outputs and all TDD logs are retained. NODE v2 files are frozen and untouched.

Replay from the repository:

```sh
python3 -B tools/water_sun_prepared_main_audit.py reports/2026-10-03-water-prepared/main-native-v3 --probe-receipt reports/2026-10-03-water-prepared/root-main-receipt-v3.json --node-receipt reports/2026-10-03-water-prepared/root-node-receipt.json
python3 -B tools/water_sun_prepared_main_audit.py reports/2026-10-03-water-prepared/main-native-v3-repeat1 --probe-receipt reports/2026-10-03-water-prepared/root-main-receipt-v3-repeat1.json --node-receipt reports/2026-10-03-water-prepared/root-node-receipt.json
python3 -B -m unittest tools.test_water_sun_prepared_main_audit -v
```
