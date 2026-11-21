# Continue to actual GPU material and lighting input qualification

The new first-object CPU material association is implemented and tested, and
16 original saved refracted points match their actual face texels offline.
The actual warmed sprite packet is sealed separately at ../2026-10-06-water-receiver-texture/.
Do not redo the already completed phase0/45/role pairs, saved terrain capture,
or old shader-native controls without a relevant change. Original-MAIN v4 still
has two qualified REDs; no shipping shader fix has occurred.

Next implement a bounded actual render-owned snapshot producer, with an atlas
revision/lifetime that cannot alias world changes, dimension changes or reloads.
Current ReceiverSurface.Stamp enforces caller equality only; it is not such a
producer. Qualify real GPU atlas coordinates, nearest/filtered/mip behavior and
resource handling before calculating a shared dry-terrain receiver source.
Actual raw albedo/tint inputs must join real smoothed light/AO or a separately
declared and qualified lighting model, preserving direct-Sun source attribution.
Do not silently treat raw sky8..12 or Iris render-view brightness1.0 as a complete
irradiance model. Screen and miss-proxy radiance also need actual first identity.

Once the actual source path is available, run the unchanged v4 hidden/visible/
near-first controls through original water MAIN, then actual UUID-guarded Iris
natural coast, nonzero waves/tessellation, movement/contact and raw timings.
No desaturation, forced hits, synthetic shipped radiance or weakened thresholds.
Full coherent Sun/Moon/cloud/volume and accurately described physical effects
remain requirements, not replaced by successful CPU association.

Last confirmed normal launch: owned8254, Java3363600, ordinary lockFD153,
runtime15:57:08 and freshly paused15:57:46; all10 opt-in entrypoints absent.
Recheck process/handle before action. No native GL since that normal relaunch.
Before a new GPU or TEST session cleanly Save/Quit/title Quit and confirm that
same process exits; use a NEW post-save baseline/cache/OUT/request/JAR. Never
restore ordinary saves, reuse an exclusive output or overwrite either seal.
The host OpenAL device failed in the existing launch; no audio acceptance claim.
