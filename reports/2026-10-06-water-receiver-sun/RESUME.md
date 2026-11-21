# Continue actual first-face source integration

Full realism goal remains active/unachieved. Read checkpoint.json and verify
its specific actual live process/handle before relying on the paused handoff.
Timeout is not terminal; re-poll the same handle. Old packets are sealed.

Completed this cycle: positive/zero/missing/unready/negative/excess paired world
Sun qualification on actual NVIDIA original MAIN; independent energy/source
audit; four ReceiverVertex CPU RED->GREEN increments; pinned installed bytecode
input-boundary inspection. No shader sources changed, no source producer or
candidate was installed, no new Minecraft frame timings measured. Don't replay
these unchanged results instead of advancing live source integration.

Next implementation:

1. Capture guarded **actual** BlockRenderer-prepared vertices with owner block
   position/state/face and encoder invocation provenance, before mutable arrays
   are reused. Reuse ReceiverVertex for immutable color/AO/light input ownership,
   not as source/face readiness. Trace the actual XHFPTerrainVertex output too:
   RGB with separate8-bit alpha AO and clamped light bytes, packed/quantized UV
   and position. Observe actual configured matrices/filtering before matching
   shader interpolation. Vertex-boundary/*.javap.txt are bytecode evidence only.
2. Potential TEST observation seam: pinned BlockRenderer.bufferQuad prepares
   `vertices` and calls ChunkMeshBufferBuilder.push; inherited `pos`/`state` carry
   world owner and `posOffset` chunk-relative translation. Iris encoder.write
   receives the prepared array and writes color atbyte8/light+data atbyte16.
   Scope worker-thread owner association carefully (thread-local invocation,
   not global last-block metadata). Do not mutate producer buffers/arrays.
3. Existing GPU/native mip0 and CPU face/surface packets qualify raw material
   inputs only. Pair actual quad tint/AO/smoothed light with exact first face,
   shared terrainLight plus separate Sun attribution, live geometry/resource
   epoch, and declared valid optical water membership. Avoid double tint,
   guessed AO=1, raw neighboring-light substitution or homogeneous cell RGB as
   final per-face texture sampling. Known unready first cannot borrow farther.
4. Build unique TEST-only producer/pack paths, never retained dist0.8.6. Real
   Minecraft/GPU tests must stay in existing isolated Aqualumen Lab and exact
   V2 UUID b22dbccb-2970-41e6-847f-f183b1ec923d/seed308060; ordinary world gets
   no automation or observer flags. No purchased assets/copied shader packs.
5. Native EGL needs clean owned-client Save/Quit/title-Quit, confirmed terminal
   exit and no Java, then a fresh post-save ordinary baseline. No blanket kill,
   no save rollback, no restart just because observation expired. After final
   native/TEST exit preserve exact configs/JARs/saves, restore0.6/physics0.2,
   inspect fresh gameplay then genuinely subsequent pause; no native GL after.

Still open: actual source shading/binding/epochs/partial-water and wave geometry,
natural cyan/serrated shoreline quality, coherent illumination/cloud/shadows,
camera/contact motion and honest separate optical/wave/fluid-physics acceptance.
Old strict60FPS floor is relaxed; real Minecraft timing must be measured and
reported, not inferred from these native/CPU tests.
