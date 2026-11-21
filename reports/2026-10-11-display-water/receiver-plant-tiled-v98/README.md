# Full tiled plant capture v98

Actual run `display-water-candidate-20261011-v98`, request
`4f2f06de-d34d-4854-b579-597ef11bc33a`, completed with owned launcher exit 0.

The actual initial 87x36x87 receiver window retained all 4,042 captured models:
1,731 kelp-plant, 329 kelp, 1,618 tall-seagrass and 364 seagrass blocks.
There were no unavailable captures or unloaded scan cells. All 48,192 triangles
were aggregated without truncation, with 334,416 conservative cell memberships.
All 272,484 scanned block states and retained model owner states were validated.

The actual 1,156,608 material attributes were uploaded to a 384x753 RGBA32F
tiled texture and read back exactly, including padded storage. This resolves
the previous v97 capacity failure for this specific initial window. It does not
prove live per-hit shading, complete neighboring model owners, full fluid-column
proofs, or fresh coverage of subsequent camera positions. Plant reflection is
still disabled; completeModelOwners=false and traceAdmission=false are retained.

Next construct per-cell owner/fluid proofs over the full captured window and
connect atomic geometry/material publication to the actual water draw. Do not
reuse this initial capture across new frames or scene locations without fresh
owner/resource validation. No beauty-image review or temporal acceptance was
performed for this packet.

Ordinary configurations, Mods and save hashes matched after restoration;
no save rollback was performed. Main sky-window, Sun, coherent light, natural
motion and usable-performance requirements remain incomplete.
