# Capture-phase cache runtime checkpoint

The full Sun/underwater appearance goal remains unachieved. This candidate
reduces repeated within-frame geometry queries; it does not fix interface entry.

The experimental Mod is `aqualumen-physics-0.3.0-receiver-phase-cache-v44.jar`,
SHA256 `e86b72205abf59225184a64fcdaa401aa69651128f0f34830b5bc06b4a85f371`.
The installed candidate was `Aqualumen-DisplayWater-ReceiverPhaseCache-v32-2026-10-11.zip`,
in Aqualumen Lab / UUID-guarded AqualumenNaturalV2 on NVIDIA RTX 3080 Ti.
Shader source is unchanged from the preceding full native v30 receipt.

The cache is scoped to one owned capture, with a bounded per-key map for loaded
chunks, classified cells, actual fluid heights and full/partial qualification.
Before the final geometry audit, the builder explicitly discards all collection
values. Validation reads fresh world data and only shares repeated reads within
that verification phase. Closing the capture clears the maps; thread/extent/
closed-owner checks prevent later reuse. The owned mesh session also reuses its
geometry adapter rather than constructing it for every face. No cross-frame
geometry, lighting, source or resource cache is introduced.

CPU tests qualify repeated-query suppression, fresh validation reads, extent/
thread/close rejection, and a block edit hidden by the collection cache that must
invalidate publication after the fresh audit. Height drift and prior ownership/
batch negatives remain covered. These are CPU fixtures, not live block-edit or
chunk-unload/reload acceptance tests.

`receiver-runtime.log` records six current-frame updates and six matching ready-2
water-draw bindings, with no owned-source failures. Every receipt has a 33x36x33
field, 1009 sources/mesh captures, 2178 partial/cap cells, 12 section copies, one
source batch and 87113 backend cell/height reads across collection and validation.
That read count excludes private mesher reads and does not count every underlying
Minecraft API operation.

Logged producer wall samples in milliseconds are:
793.850883 (initial), 141.626489, 143.082451, 138.491665, 135.631068, 154.192053.
They are periodic samples, not all calls or independent GPU timings. The earlier
v31 steady receipts were about 215-223ms, but these separate runs are not a
controlled performance benchmark. Current overhead is still unacceptable.

At actual 1600x800 with native screenshot capture:

| Scene | Frames | Mean ms | Median ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| underwater-up-near | 30 | 162.49209423333332 | 165.412975 | 178.316886 |
| underwater-up-moving | 28 | 178.479669 | 177.4926785 | 200.726078 |

The native audit verified 49 PNGs and pose/time metadata, not visual acceptance.
Moving frame-015 was actually viewed: the folded/fragmented boundary and broad
dark exterior remain. No production offscreen receiver-hit or complete motion
review is claimed. Source coverage and caching alone do not qualify a ray
starting above the conservative lower partial-water envelope.

Client exit was normal (0). `runtime-restored.json` confirms exact normal configs,
Mods, instance settings and ordinary save hashes, without ordinary-save rollback.
Further work remains on actual wave-interface-owned entry, repeated mesh work,
resolved/residual interface normals, source illumination and full Sun/water
visual/performance acceptance.
