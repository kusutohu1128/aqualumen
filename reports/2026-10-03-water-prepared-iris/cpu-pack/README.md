# Prepared-context TEST ZIPs — CPU handoff

READY for Root review and separately authorized native/Iris qualification. Five public CPU tests pass; no GL, Minecraft, installation, performance or visual test was performed by this builder agent. This is Codex work, not a fresh Claude review.

## Exact bounded change

Three parents are accepted by whole-ZIP SHA-256, not filename or declarative metadata: the sealed support-zero physical-display, reasons and inputs ZIPs. The physical parent is `33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda` from the prior `cpu-physical-view` report.

Only two existing members change:

- `shaders/lib/water_sun_support.glsl`: exact prepared helper `ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441` replaces exact original helper `f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a`.
- `shaders/lib/water_residual_sun.glsl`: one tagged local context is prepared after `float integral=0.0;`, before the unchanged 48-node valid-loop guard; the existing class call uses that context. Target generation, admission, all node calls, weights, unknown/fallback, counters/reasons and all physical parameters remain unchanged.

The exact preparation and call strings are pinned to sealed native MAIN source `0e7e27e6cbf6655638745021c197c0c16f50784474f9fe820dce01e678b7ead5`. No new invalid-context shortcut is added. Geometry, phase 120, tessellation factor 4, guard, FINAL and all other parent members are byte-identical. Original helper/cap files and the complete original ZIP bytes are embedded in each new ZIP. The public `recover` CLI validates every member and reproduces the exact original ZIP bytes, not just equivalent entries.

Reasons and inputs expanded fragment sources are literally identical to their sealed prepared native MAIN programs. The physical-display parent intentionally retains seven helper reason-record spans that the native MAIN physical role strips. Those spans remain in the new physical ZIP; removal occurs **only for a documented CPU comparison**, whose result exactly matches the sealed native role. Thus the physical ZIP is role-STORE-free but not fully observer-free, and its raw expanded source is not misrepresented as the native physical source.

Inherited manifests and helper comments are retained as historical parent records. `WATER-SUN-PREPARED.json` is the current helper/source identity and explicitly marks the older helper identities as nonauthoritative. Native prior PASS is not Iris acceptance of these newly built ZIPs.

## Commands

From the repository root, run the CPU contracts:

```sh
python3 -B tools/test_water_sun_prepared_pack.py
```

Build requires a **new** output path; existing exports will be rejected:

```sh
python3 -B tools/water_sun_prepared_pack.py build \
  --parent reports/2026-10-03-water-sun-support/cpu-physical-view/Aqualumen-ShoreProbe-world-sun-support-zero-physical-v1.zip \
  --prepared-helper tools/water_sun_prepared.glsl \
  --output reports/2026-10-03-water-prepared-iris/cpu-pack/new-export/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip
```

```sh
python3 -B tools/water_sun_prepared_pack.py recover \
  --candidate reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip \
  --output reports/2026-10-03-water-prepared-iris/cpu-pack/new-recovery/parent.zip
```

Output is restricted to this new CPU report subtree or OS temporary directories used by public tests. The builder never installs a pack. Parent/source hash mismatch, unsafe or duplicate archive entries, path aliases, destination overwrite and sealed/shipping output paths fail closed before publication. ZIP byte determinism was checked twice on this Python/zlib environment; cross-version compressor byte identity is not claimed.

## Evidence and limits

`01-public-cli-red.log` retains the genuine missing-generator first-test failure; `02-first-public-cli-green.log` retains the minimal first GREEN. `03-final-public-tests-green.log` records all five tests, and `04-public-export.log` records the three exports. All three reconstructed parents in `recovered-parents/` hash exactly to their sealed originals.

During incremental source testing, an initial raw physical/native equality expectation failed because the parent retained reason spans; the test was corrected to match the already documented native normalization, without removing anything from the ZIP. A bytes/string join implementation error then failed the CLI before output and was fixed. Neither failure is a shader behavioral RED. The accepted CPU gates still require literal equality of reasons/inputs, full parent-member preservation, exact physical normalization and exact parent ZIP recovery.

No ordinary world/config/runtime path, sealed report or shipping source was changed. There is no fresh GPU compiler result, live guarded operator result, runtime count/raw-texel qualification, Minecraft FPS, energy correctness, visual improvement or shipping adoption claim in this packet.
