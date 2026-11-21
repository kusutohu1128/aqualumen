# 0.8 native checkpoint — not a game release

Recorded 2026-10-02 UTC. The full realistic-water/sunlight goal remains active.
Ordinary Minecraft still runs selected 0.6.0 with physics bridge 0.2.0; neither
candidate 0.8.0 nor physics bridge 0.3.0 has been installed at this checkpoint.
No Minecraft lifecycle, ordinary camera/time/terrain or settings changes were
performed for these native tests.

## Candidate identity

- Final shader ZIP: `dist/Aqualumen-0.8.0.zip`, SHA-256
  `8fab2af68e5a82def9f8454831d6d4b9e4cfdb41bf38d5ff95bcc31e3794a5aa`.
- Read-only physics 0.3.0 candidate: SHA-256
  `958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310`.
- Final water fragment: SHA-256
  `231546b85e2317ba11d458b8033cca83301d779c8e92121f0545cd6805062f87`.
- Final native harness: SHA-256
  `bf73816c0a0e1d0bab3755838977e231c80b90476711b2288fa2e7da9bdc9dd0`.
- Earlier pre-root-refinement 0.8 ZIP `e054f474...` is a different snapshot,
  preserved separately in the source archive; do not assign it final results.
- Retained 0.7 ZIP `09f6fb16...` and installed 0.6 ZIP `6ceb9cf0...` are unchanged.

Frozen [shader/native/physics sources](source-and-candidates.tgz),
[native readbacks/fixtures](native-fixtures.tgz) and [log/hash inventory](SHA256SUMS)
preserve the bounded evidence. They contain no launcher account files or saves.
The source archive includes the pre-refinement and unguarded-proposal fragments;
the final ZIP contains neither diagnostic variant nor passive MRT instrumentation.

## Shared local bathymetry

The optional Mod supplies world-anchored, undisturbed surface-to-confirmed-floor
columns in a 64×64 RGBA32F texture. Vertex displacement and optical normals use
that same field and the wave damping's depth-gradient product rule. Unknown,
out-of-window, incompatible-surface or mixed-known/unknown mesh primitives use
the actual coarse raster facet; the unrelated camera-ray receiver no longer
determines their wave slope. This is bounded bathymetry, not fluid conservation,
arbitrary water-body connectivity or a continuous exact block-floor surface.

The Mod scans retained, already-loaded client chunks only, with 16 column scans
per frame and a bounded cache. CPU extraction/cache tests and build pass. Initial
fill, delayed changed-block refresh, partial/waterlogged floors and unmatched pool
elevations remain explicit limitations; see the [bridge contract](../../physics-mod/README.md).
Issued upload counts are not proof of live sampler binding or accepted GL storage.

## Native RED / GREEN evidence

All GPU results below use RTX 3080 Ti / NVIDIA 580.173.02 / OpenGL 4.6. They are
controlled production-main/library fixtures, **not Minecraft images or FPS**.

| Behavior | Retained failure | Final bounded result |
|---|---|---|
| Same local water/bed, different remote camera-depth receiver | Frozen 0.7 reflected-source response difference `0.01926681399` | Final valid bathymetry input difference `0` (earlier positive GREEN `1.49e-8`), unchanged bound `7.87e-6` |
| Physical 0.25m versus 1.25m column | Actual floor and map move together, not metadata alone | Actual VS height and optical normal both change; reflection-only attribution passes |
| Unavailable or one contributing unknown vertex | Inputs explicitly declined, never fabricated known depth | Ready0, invalid, out-of-map, surface mismatch and unknown-corner controls pass; geometry/normals independent of remote depth |
| Visible deep-bed radiance, pixel65,45 / phase1.5 | NEAREST response `.072958827/.073332757`, expected `.084533204` | `.084635213` at both endpoints within unchanged physical/plane-pixel bound |
| Same fixture with LINEAR depth/color input | Unguarded direct-root proposal regressed to `.083632037/.083584636` below `.083973625` | Guarded proposal `.084545672/.084543005` within the same bound |

The final near-root proposal is accepted only when it remains inside the existing
bracket and its actual reprojection retrieves **exactly the same depth**. Otherwise
the prior bisection is retained. The original final iteration, visibility,
foreground-bank, surface, residual and confidence formulas are unchanged. There
is no confidence=1 override, larger tolerance, source desaturation or early hit.
Passive traces show NEAREST residual becomes zero at iterations7/8; LINEAR keeps
the pre-proposal sequence rather than overshooting. The paired difference is
independently predicted by Fresnel/Beer transport and the physical first receiver.

The new fixture is selected from geometry/visibility/untagged-input qualification
**before tagged responses**, never by finding a passing response. Pixel, phase,
endpoints and filter are now explicitly replayable. Historical65,46/phase1.25
hits a lawful foreground bank under the new coarse facet: that old fixture's
qualification failure is INCONCLUSIVE, not another shader RED. It remains separate.
The unchanged one-pixel bound permits quantized depth-plane reconstruction error;
it does not establish exact continuous intersection precision.

The final default `make check` passes all11 graphics pairs, wave compute tests,
retained foreground/underwater/caustic/solar tests and both NEAREST/LINEAR versions
of the same newly frozen visible-bed fixture. The sampled-facet SSR wall positive
and off-ray/submerged negatives also pass. Separate final bathymetry and gradient
commands pass. An intentionally omitted depth-gradient term fails the derivative
oracle; this is a diagnostic negative, not a claimed historical production RED.

Relevant logs are saved under [native/](native/). Explicit per-run directories
never overwrite their REDs. A first pre-guard full native run briefly overlapped
the passive capture; it is not timing evidence and is superseded by the final
serialized GPU runs recorded here.

## Still required

Live Mod Mixin/sampler/Ready/Grid/texture-column acceptance and natural-shore
Minecraft comparison remain unverified. A separate TEST-only passive bridge
observer is being prepared; CPU compilation will not be called live acceptance.
Natural cyan/mint shores, jagged bands, convincing moving highlights/wakes,
cloud shape and coherent cloud shade remain open until actual scenes/motion
prove improvement. Existing TEST Save/Quit stalls are not fixed by this work.
No new Minecraft performance claim, ordinary release handoff or full-goal
completion is made. Current implementation/review is Codex work, not a new
Claude invocation.
