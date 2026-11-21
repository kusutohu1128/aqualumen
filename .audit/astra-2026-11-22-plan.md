# Finish preview 8 and publish it as an optional pack

**Decision requested from Devin — A, at `d4303c3`.** The realism goal calls for a playable cave-to-daylight transition with measured Minecraft frame times. Preview 8 already has a view-dependent effect in the seed 20261123 cave: looking up at the opening takes gain from 16.0 to 12.4, and turning to the wall brings it back to 15.9. The maximum suppression during descent was 0.91 stops. In the daytime village house the two previews looked alike. Publish that bounded result with its cost. Flattening the overlays can wait until the qualified bytes are pinned; optimizing indirect light now would change a second variable before the baseline is measured.

## Artifact and rendering contract

| Pack | Input for qualification | Expected SHA-256 |
| --- | --- | --- |
| 7 | `dist/Aqualumen-1.9.0-preview.7.zip` | `c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c` |
| 8 | `build/eye-adaptation/Aqualumen-1.9.0-preview.8.zip` | `2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72` |

- Rebuild `python3 tools/build.py --eye-preview --output <fresh-staging-path>` and compare the entire archive with input 8. Both preview ZIPs have the same 138 member names. Only `shaders/composite3.csh`, `shaders/setup1.csh` and `shaders/final.fsh` differ between 7 and 8. Tolerance is zero bytes for the rebuild and for the 135 common payloads.
- Ship the existing algorithm. One 16×16 workgroup meters center-weighted daylight, subtracting local luminance on visible opaque terrain. In the existing 198×1090 RG32F image, texel (0,0) holds lamp gain and tag 1729; (1,0) holds daylight exposure in stops and air-history tag 1730. Bright/dark response times are 0.38/1.65 s. Setup invalidates daylight history and the final pass applies the valid gain. Preserve the image count, row layout, indirect-light passes, shader sources and default 1.8.0 build.

## Files for the implementation after review

Paths below use `R = reports/2026-11-22-eye-adaptation` and `T = reports/2026-11-21-animal-light`.

- Edit `T/timing/measure.py` so `extract` accepts an optional explicit pack path. Existing three-argument callers keep their dist lookup. This lets us verify a staged ZIP before publishing it.
- Add `R/frame_times.py` and `R/test_frame_times.py` for the paired-run summary and its evidence checks. Write `R/frame-times.json` (run labels, hashes, settings, raw intervals, per-run statistics and paired deltas) and `R/lab.json` (publication paths, before/after hashes, selected pack and mod state).
- Use the existing runner as written. Its generated outputs are `T/progress.txt`, `T/result.json` and `T/<run-label>/` with `complete.json`, `observer.json`, `geometry.json`, `client.log`, the private path receipt and captures. Keep raw captures local under the existing ignore rules.
- Update `R/README.md`, `README.md` and the cave/house progress in `docs/REALISM_GOAL.md` with the measured results, build command, optional-use instructions and limitations. Local distribution outputs are `dist/Aqualumen-1.9.0-preview.8.zip` and the same filename in the Lab shaderpacks directory recorded in `reports/2026-11-22-ceiling-return/lab.json`. Devin reviews the diff and makes all git commits.

## Correctness before timing

1. CPU red → green: start with dist/8 absent. Test that a complete fixture for an explicitly supplied staged pack is accepted, that substituting another ZIP is rejected even under the expected filename, and that missing STILL or a window shorter than 10 s is rejected. Use disposable fixture files. Run the tests before adding staged-path support and after implementing it. Check the legacy three-argument extraction against the saved `ceiling-isolated` run (38.34 FPS / 30.58 ms p99 at night, 64.12 / 19.26 by day, rounded).
2. On RTX, run `make check-eye` and `build/glcheck <unpacked-8>/shaders --play-release`; on Mesa llvmpipe run the staged `--eye-exposure-probe`. Record renderer, versions and exit status in `R/README.md`. The existing probe requires absolute error <2e-5 for half-field daylight (2 stops), lamp-only/midnight controls (4 stops), and time subdivision; the validity tags are exact. Retain the existing NVIDIA/Mesa logs and cave/house evidence. Existing `make check` targets stable 1.8.0. Any pass times or ns/receiver in glcheck are GPU-harness measurements only.

## Actual Minecraft timing

- Before **each** GPU job inspect `nvidia-smi` (graphics and compute processes, utilization) and `ps -eo pid,comm,args` for active Minecraft, runners, glcheck and unrelated GPU compute. Wait for an idle device apart from the idle desktop. Run one GPU job at a time through exit, respecting the runner's render lock. Keep even software probes outside timing windows. If another job appears, discard the affected timing window and repeat with a fresh label.
- Preflight Lab's five recorded normal-file hashes, selected 1.8.0, physics 0.2.0, disabled compiler 0.3.0 and source-world marker. The runner clones `AqualumenNaturalV2`, seed 308060, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, for every launch. Only these private clients get the enabled compiler and frame observer. Use one observer JAR hash and one compiler JAR hash throughout.
- From repo root, run the following command once per row, in order. Use a common private driver cache. Start sampling only after scene verification and settling.

      python3 reports/2026-11-21-animal-light/run.py <pack> <label> --frame-intervals --backend vgl --size 2560x1440 --period-ticks 680 --settle 1 --stages both-west,day-white --compiler-mod dist/aqualumen-lighting-compiler-0.3.0.jar --glcache build/eye-adaptation/timing-glcache

| Order | Pack from table above | Fresh run label |
| --- | --- | --- |
| 1 | 7 | `eye-frames-p7-a` |
| 2 | 8 | `eye-frames-p8-a` |
| 3 | 8 | `eye-frames-p8-b` |
| 4 | 7 | `eye-frames-p7-b` |

- Match `ceiling-isolated` geometry: `both-west` is a fixed cow under a roof with two lanterns at night; `day-white` has the same cow at noon with the roof open and lamps off. Require READY/STILL validation, matching source digest, GPU identity, pack hash and Iris load line, 12 chunks, VSync off and cap 120. Check the original world/config receipt after each exit. These fixed scenes add zero survival days.
- Reuse the render-return interval extractor. Drop its first three post-F2 batches; retain consecutive intervals totaling 10.0 to <10.2 s with >100 frames. Report each run's FPS (frame count / elapsed seconds), mean interval and nearest-rank p99 ms. Compare 8−7 within pairs a and b, separately per scene. Record cache status and launch-to-first-render time separately from warm frame intervals; the historical 3 min 56 s was a cold preview 7 launch.

## Decision and stop conditions

- Treat >5% slower mean interval or >10% slower p99 in a scene as a regression to investigate. If only one pair crosses a threshold, repeat that pair once with labels `eye-frames-p7-c` and `eye-frames-p8-c` and report all samples. Hold publication for Devin if the same metric reproducibly crosses its threshold or the comparison remains inconclusive. These are proposed relative investigation thresholds; there is no 60 FPS floor.
- Stop on a hash/UUID mismatch, renderer fallback, compiler or probe failure, changed Lab state, or unverified scene. Preserve the failed receipt. A runner waiting for a lock supplies no frame data. Use a new label for any retry.
- After qualification, copy the exact tested bytes to dist and to Lab via same-directory temporary files and atomic rename. If a destination exists, accept an identical hash or stop on a conflict. Verify both destination hashes and all normal-file hashes against preflight, including the disabled compiler's hash and active mod list. Keep preview 7 available and 1.8.0 selected. Document how to opt in manually. The two timing scenes establish cost only there; the prior walk supplies the cave exposure evidence.
