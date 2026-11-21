# Actual static receiver texels; not yet water-source radiance

The UUID-guarded standalone0.1.1 TEST observer captures actual sprite mip0 pixels
in real Minecraft1.21.1 / Iris1.8.8 / Sodium0.6.9 on RTX3080Ti, GL3.2 NVIDIA580.173.02.
There are three warmed16-face observations, frames490/605/723 after5.001/6.001/7.006s,
covering14 unique sand cell-faces and eight previously saved camera-hidden first
receivers. The face/texture/raw-light records are equal across these three events;
this is not a general temporal, frame/geometry coherence or resource-reload proof.

NativeImage ABGR layout is calibrated using a separately owned known2x2 image,
independent native byte getters, and copy ownership after mutation of that owned
fixture only. Actual game asset images are never written or closed. Animated,
nonopaque, oversized, unsupported or inconsistent descriptors stay unready.
The adapter is loaded-only, synchronous and render-thread guarded; no new cache,
sampler, shader source, world command or renderer source upload is introduced.

Independent JDK ImageIO reads the local official indexed4-bit sand PNG in memory.
Its whole top-first RGBA digest419fc26081190f9a43757aa58be5e3858becfc8e8f956af31987a504135eba90
matches every native snapshot. All240 saved-point/four-grid pixel checks match,
including independently recomputed affine face UV and20 unique pixel coordinates.
No copied PNG/art asset is distributed in this packet. CPU nearest mip0 sampling
is explicitly not actual GPU atlas filtering, mip choice or shaded albedo/radiance.

Raw sky8..12/block0, tint and baked quad color are available, but not Sodium AO,
smoothed vertex light or a proved dry-terrain radiance convention. Render-view
brightness1.0 is an observed API value, not a validated physical illumination.
Both qualified original-MAIN native-v4 source REDs remain unchanged, and cyan/
serrated actual water appearance persists. No motion acceptance or new timings.

The actual installed observer JAR and exclusive deterministic rebuild both hash
to a3387c9ced746600b5649af895850d00611f5f7e27303aa9a10491dc3a7f749c.
Focused public texture/record behavior checks and affected geometry/bathymetry/
face/pause regressions are retained. Prior sealed packets are not modified.

After clean TEST Save/Quit, the observer JAR/property are recoverably disabled.
Original41 ordinary saved files/configs/three Mods match exactly before reopening;
no saves are restored. Normal0.6 / physics0.2 runs as Java3363600, owned8254.
Actual gameplay15:57:08 and new pause15:57:46 are inspected, with a fresh intervening
15:57:40 server pause event. All10 opt-in entrypoints are absent. No native GL
after normal relaunch. The launch log also records OpenAL device failure, so
audio is unavailable; this is not a clean all-subsystem acceptance claim.

See `actual-texture-audit.json`, `checkpoint.json`, CPU logs and frozen producer
sources. A checksum seal preserves this input milestone, not full-goal completion.
