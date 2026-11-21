CPU READY only. Root exclusively executes GL; there is no actual-main/timer result yet.

Build and seven public CPU tests completed without final compiler diagnostics. The first missing-public-CLI failure is retained in `TDD-RED.json`; no CPU failure is called a shader RED. Final recoverable source bundle is `construction-final-v2/`, not the earlier pre-guard-fix `construction-final-v1/`.

The frozen four input shader roots must be supplied in this exact order: reject-reasons, zero-reasons, reject-inputs, zero-inputs. Existing parent/source recovery pins are checked before any GL. Root's separately executed actual node gate is required and copied/hash-recorded before constructing a context.

Root-only command (substitute the four existing read-only extracted roots; output must not exist):

```sh
reports/2026-10-03-water-prepared/cpu-main/water-sun-prepared-main-probe --native \
  REJECT_REASONS_ROOT ZERO_REASONS_ROOT REJECT_INPUTS_ROOT ZERO_INPUTS_ROOT \
  tools/water_sun_prepared.glsl NEW_NATIVE_OUTPUT \
  --node-gate-result reports/2026-10-03-water-prepared/node-native-v1/result.json \
  --warmup-cycles 2 --measure-cycles 6 --max-seconds 900
```

Exit 0 means bounded native main differential accepted and elapsed draws completed; exit 1 means a qualified differential mismatch; exit 2 means construction/input/observer/driver/time qualification failure. Existing output is rejected before source/gate/context access. Partial evidence is preserved on failure.

All48 observation is separate from timing: target generation is unchanged, the old local class is copied without an additional classifier call, and private STORE tags erase back to the corresponding physical source exactly. Generated-but-not-classified and not-generated are distinct markers. Full-view countwords are independently reconstructed from the 48 maps. Source class/interval identity remains the separately executed node test's scope, not a replacement physical integral oracle.

Timing encloses only the original `glDrawArrays(GL_PATCHES,0,6)`. Setup, clearing, uniforms, `glFinish`, query-result polling, readback and file output are outside the query. Physical source remains STORE-free but retains inherited counters and five MRT outputs; this is not a counters-free or whole-game benchmark. Raw integer nanoseconds, actual typed guards, source pins and input/state receipts are exported. ABBA has two warmup and six measurement cycles by default. Deadline checks cannot interrupt a hung driver call.

No shader/helper/old harness, game, configuration or sealed report was changed. No shipping/visual/physics/Iris/FPS acceptance is implied. The independent source reviewer found no other concrete blocker; root found and corrected two unset guard-before-input-snapshot host call sites before any main GPU execution, and the CPU source-handoff test now verifies those explicit call-plan seams.
