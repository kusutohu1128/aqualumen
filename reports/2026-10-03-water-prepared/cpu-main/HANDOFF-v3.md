V3 is CPU READY; source and tests are frozen. No agent GL/game execution occurred. Use `water-sun-prepared-main-probe-v3`; the original binary and V2 bundles/receipts remain unchanged.

Eight public CPU tests pass; final `g++ -Werror` build has no diagnostics. The new archive CLI was tested failing against V2 before implementation (`TDD-RED-v3.json`). The same archival function is used for synthetic CPU input and actual native readbacks; synthetic exports are explicitly not GPU evidence.

All eleven generated GLSL files are byte-identical to V2. V3 only strengthens saved host-side evidence: both variants' target/view/class maps are always saved for every node, with individual filenames/lengths/SHA256, and actual typed uniform/program/FBO/viewport/eight-route state is queried and saved immediately before/after every node draw. No shader behavior, numerical gate or timer changed.

Raw node files total1,826,122,752 bytes; other full/repeated maps total627,729,696 bytes before input receipts (about2.29GiB combined). No equality-based omission remains. Consumers can reconstruct each mode's exact seven uint32 certificate inputs and per-pixel48-node countword without trusting flags. CPU synthetic replay confirms this compatibility; full actual-main arithmetic still requires root GPU data and the independent saved-file auditor.

Root-only command is identical to V2, except the binary name:

```sh
reports/2026-10-03-water-prepared/cpu-main/water-sun-prepared-main-probe-v3 --native \
  REJECT_REASONS_ROOT ZERO_REASONS_ROOT REJECT_INPUTS_ROOT ZERO_INPUTS_ROOT \
  tools/water_sun_prepared.glsl NEW_NATIVE_OUTPUT \
  --node-gate-result ACCEPTED_ACTUAL_NODE_RESULT.json \
  --warmup-cycles 2 --measure-cycles 6 --max-seconds 900
```

Per-node state is `record.actual_draw_state.MODE.{before,after}` with real queried scalar int fields (`name,type,size,location,value`), current/expected program, framebuffer, viewport, VAO, patch size and all eight draw routes. Source SHA is linked to per-case actual attached-source queries. Physical neutral maps remain independently archived and hash-compared. Timer continues to enclose only the original draw, never these state queries/readback/output.

See `HANDOFF-v3.json` for full hashes, schema and boundaries. V2 omission language applies only to retained historical V2, not the new V3 command.
