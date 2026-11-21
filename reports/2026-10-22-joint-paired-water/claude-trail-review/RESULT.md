Reviewed by Claude Opus 5.5 (claude-opus-5-5), read-only. I made 12 tool calls and edited nothing. The figures I could check against the artifacts are right: the route counts and percentages, the Fresnel values at (1430,200), preview0 and texture 77/FBO 18/output 3 in the near-view manifest, the pack SHA, and the 18+5=23 CPU test count. restored.json says what SUMMARY says. I did not open the deep-view manifest.

## Attention flags

1. **(Medium) "SSR 0 pixels" is not qualified where it is reported.**
   - SUMMARY.md:22 uses "SSR=0" to argue against a hypothesis. But route 1 has never been tested on the GPU (qualification.json `untestedRoutes:[1]`).
   - The earlier review also noted that a non-finite SSR result is labelled route 4.
   - So zero SSR pixels could also mean SSR is mislabelled and counted inside the ~39–42% UNKNOWN share.
   - Line 22 should repeat the "route 1 untested" caveat next to the observation, not leave it only at line 30.

2. **(Medium) AUDIT.json does not link the evidence it is said to audit.**
   - It contains only verdict booleans and counts: `originalShadersExact`, `allFilesAndPNGOrientationVerified`, `nativeSSR1Tested`.
   - It has no paths or hashes for the two capture manifests, qualification.json, the native-final receipt, the compile logs or the original shaders.
   - The only link is the chain qualification.json → receipt + logs, and nothing ties qualification.json back to AUDIT.json.
   - Correction to the premise: SUMMARY.md:33 and your brief say AUDIT.json links these artifacts. It does not; someone would have to rebuild the chain by hand.

3. **(Low–Medium) The compile logs don't say which pack they compiled.**
   - control-compile.log and paired-compile.log have the same hash, `a85c72eb…`.
   - Neither log names its pack or records an exit code.
   - Hash-binding them in qualification.json shows what they say, not which pack produced them or that they were two separate runs.
   - The proof that the paired pack (`95bbbd…`) works rests on the native-final receipt, not on these logs.

4. **(Low) The decision trail has gaps and an ordering problem.**
   - paired-water-2026-10-22.tsv has no row for the native-final run (the preview0/preview1 FINAL fixture). Row 6 cites only native-initial, yet qualification.json binds native-final.
   - Rows 7 and 8 share the timestamp 12:45:27Z. The review fix in row 8 came after the game run, so the rows were written together, not as things happened.
   - There is no row for the comment-only review, or for the risky decision to run the experimental physics v100 instead of the normal 0.2.0. SUMMARY records it; the trail does not.

5. **(Low) The archived evidence was produced by the old runtime tool.**
   - restored.json and both manifests came from the runtime code before the M2 fix. The new staging and recovery path has never run against the real instance.
   - SUMMARY.md:36 says this, but nothing records the hash of the tool version that produced the evidence. A future reader could assume the current code made it.
   - Recording that hash is enough; no rerun is needed.

6. **(Info) The game run never produced a non-water pixel.**
   - NOT_WATER is 0 in both frames (counts add up to the full 1600×900), which fits a camera looking straight up from underwater.
   - So the real-Minecraft run never exercised C12 clearing or route 0, which matches SUMMARY.md:31.
   - The manifests also say `producerSourceIdentityDirectlyObserved:false` and `plantSourceReady:false`. The "producer ready=2" claim therefore relies on logs, and SUMMARY's "0% producer unavailable" column should not be read as direct proof the producer was live.

## Checked, no defect

- **Earlier finding M1:** the description and correction in SUMMARY.md:36 hold. qualification.json uses the expected schema and binds the native-final receipt and both logs, with route 1 listed as untested. Nothing claims the raw receipt can be passed in directly.
- **Acceptance claims are not overstated.** Visual, physical, performance and Iris acceptance are false throughout. The 17 s wave freeze, ripples off, v100 physics, GL_LINEAR mixing and attribution limits are all stated.
- **Restoration and leftovers are reported plainly:** exact restore, unchanged save hash, no rollback, leftover files in V2 and the cache.

None of these flags needs a new Minecraft run. Flags 1–4 are edits to the documents and trail. Flag 5 only needs a tool hash recorded.
