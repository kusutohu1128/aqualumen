# Prepared classifier node probe: CPU handoff

The probe and public construction tests are frozen. Five public CPU tests pass; the final executable compiles warning-free with `-Wall -Wextra -Werror -fno-fast-math -ffp-contract=off`. No successful GPU mode, game, installation, pack construction, or shipping change was performed by this author.

`HANDOFF.json` pins receipt-relative source/test/binary snapshots and all unchanged dependencies. `construction.json` is the actual final public CPU constructor output. `additional-inputs.json` keeps the 32 added inputs separate from the byte-unchanged frozen 344 corpus: 24 invalid/boundary and 8 signed-zero/nonunit fixtures, with raw input bits and literal CPU class expectations. These extra class expectations are not a physical oracle.

## Root-only execution

Compile using the absolute source path below to keep the loader's `__FILE__` bits and binary hash identical:

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off /home/kusutohu/repos/aqualumen/tools/water_sun_prepared_node_probe.cpp -o /home/kusutohu/repos/aqualumen/reports/2026-10-03-water-prepared/cpu-node/water-sun-prepared-node-probe-v2 -lepoxy -lEGL -lcrypto
```

The GPU command needs a genuinely new output path:

```sh
/home/kusutohu/repos/aqualumen/reports/2026-10-03-water-prepared/cpu-node/water-sun-prepared-node-probe-v2 --gpu /home/kusutohu/repos/aqualumen/shaders/lib/water_sun_support.glsl /home/kusutohu/repos/aqualumen/tools/water_sun_prepared.glsl /home/kusutohu/repos/aqualumen/reports/2026-10-03-water-sun-support/cpu-certificate/cases.json NEW_NONEXISTING_OUTPUT
```

The GPU path requires the actual NVIDIA RTX 3080 Ti renderer, checks attached VS/FS sources and typed uniform values before/after each draw, records all eight queried draw routes, queried per-target storage/component/object and actual program output locations, and saves repeated eight-target RGBA32UI maps. Direct class output is recorded for every one of the 376 nodes. The group checksum only keeps the loop active; it is not a substitute for direct per-node equality.

The three programs use literal old / prepared wrapper / prepared reused-context helper sources. Six interval triples (signed endpoint bits plus valid flag) are recorded. Since the old production API does not expose a context, the old-program interval witness separately repeats its exact original integer expression tree; it does not prove the old compiler's internal scheduling.

Only an actual `aqualumen-prepared-node-native-v1` result with all declared gates true can establish this bounded GPU identity. This CPU receipt does not establish GPU identity, water-main acceptance, physical accuracy, Iris acceptance, shipping adoption, or performance improvement. The author performs no GL execution.

## Retained progression

Logs 01–06 preserve earlier public missing-interface/missing-mode and warning failures followed by CPU construction GREEN. Log 07 records the genuine metadata contract RED (missing `runtimeCaptureFields`), followed by the final captured five-test GREEN in log 08. The approved final amendment adds query evidence metadata only; classifier arithmetic, drawing and acceptance gates are unchanged. Log 09 records the completed final warning-free build command and binary pin.
