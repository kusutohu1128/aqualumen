# Explicit plant upload capacity v72

The ordinary radiance uploader retains its 65536-texel limit. A separate explicit
plant factory permits up to 1048576 RGBA32F texels, with each dimension still
bounded to 4096. This covers the existing maximum cell-header and membership-link
publication extents, without changing ordinary source allocation policy. Invalid
policy values, over-capacity requests and nonfinite payloads remain rejected.
The same render-thread guard, GL-state restoration and allocation-format audit
are retained.

`../native-plant-upload-capacity-v72.log` records an actual NVIDIA RTX 3080 Ti
256×4096 texture allocation, upload and complete readback equality, including
nonzero first/middle/last sentinels. It also proves the ordinary 256×257 request
still rejects, plant 257×4096 rejects, and invalid policy capacity rejects. The
atomic publisher and joint cell-decoder/intersection GPU controls pass using the
explicit plant policy. This is controlled GL validation, not live Iris binding
or actual world-model coverage.

The full Mod artifact `build/aqualumen-physics-0.3.0-plant-large-upload-v79.jar`
is built but not installed. No Minecraft client, normal settings or saves were
changed. Live producer aggregation, complete-owner proofs, draw binding and leaf
shading remain open. Full water/underwater sky/Sun acceptance remains unachieved.
