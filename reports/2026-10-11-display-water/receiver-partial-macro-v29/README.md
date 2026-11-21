# Partial water and underwater macro-normal runtime checkpoint

The full Sun/underwater appearance goal remains unachieved.

- Actual Minecraft 1.21.1 / Iris 1.8.8 / Sodium 0.6.9, NVIDIA RTX 3080 Ti,
  isolated Aqualumen Lab and UUID-guarded AqualumenNaturalV2.
- Candidate pack: `Aqualumen-DisplayWater-ReceiverPartialMacro-v29-2026-10-11.zip`.
- Experimental physics artifact: `aqualumen-physics-0.3.0-receiver-field-session-v39.jar`,
  SHA256 `bde6a0665b12b1f9afa05a7c4cedf6f70a6b6060994534ed326b73d0ef0e7be6`.
- Near and moving underwater scenes; five-second warmup and sampling each;
  actual framebuffer 1600x800, not target-resolution FPS acceptance.

`receiver-runtime.log` contains 30 periodic current-frame source updates and
30 matching ready-2 water-draw binding receipts, one source and 18 qualified
partial/cap cells per receipt, with no owned-source failure reports. The
logged producer wall-time samples have median 8.5957125ms and maximum 76.340583ms,
including the initial compile/readback. These are not all producer calls or
isolated GPU timings; no performance improvement is established.

The near scene recorded 371 frames, p99 25.045796ms; moving recorded 349 frames,
p99 25.258226ms. Native motion audit validated 68 PNGs and recorded pose/time
metadata. This audit is not visual review. The moving frame-015 was actually
viewed: fragmented/folded bright sky-window boundaries and a broad dark exterior
remain. No controlled visual improvement or full sequence acceptance is claimed.

The production macro-normal reference below an upper interface now follows the
actual displaced triangle. The native passive-store/transform-feedback test in
`../displaced-macro-normal-v29/` independently reconstructs that facet, reporting
maximum normal error 4.8499585746861e-6 and flat-normal sensitivity
0.050891313701868. Both windings, true bottoms and unknown surfaces retain their
checks. `../native-displaced-macro-full-v29.log` records the full retained native
suite and 14 linked program pairs. None proves a natural underwater correction.

The broader above-water macro-normal v28 experiment failed the retained
visible-deep-bed transmission regression and was never installed. Its native
receipt and ZIP are preserved as rejected evidence. V29 leaves that path intact.

Client exit was normal (code 0), Java absence was checked, and
`runtime-restored.json` confirms exact normal configs/Mods/instance settings and
ordinary save hashes. No ordinary save rollback was used.

Remaining causal work: interface-owned ray entry rather than a conservative
lower-envelope-only start, wide reflected-source coverage with batched ownership,
and a resolved/residual normal distribution treatment at the critical boundary.
The source program session currently saves duplicate linking only within one
capture; this one-source runtime does not establish multiple-face reuse.
