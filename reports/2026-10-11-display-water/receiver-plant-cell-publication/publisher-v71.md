# Atomic plant texture publication v71

`ReceiverPlantPublisher` publishes header, membership-link and primitive textures
as one epoch-qualified set. Cell publication must own the exact original packet,
not merely an equal-sized packet from the same frame. A mismatched pair is rejected
before upload. Owner epoch is checked before and after every allocation. Partial
failures delete only pending textures and make readiness false; prior resources
remain retained until a successful replacement or close. Texture name aliases are
rejected. Successful replacement releases the previous three textures.

Readiness here means a coherent uploaded plant data set, not source radiance,
actual complete-model coverage or ordinary-play admission. Each cell's independent
fluid/model qualifications are still authoritative for traversal. The current
uploader's 65536-texel limit remains; widest whole-field payloads need an explicit
larger bounded upload policy rather than silently extending ordinary allocations.

`../plant-publisher-cpu-v71.log` covers packet identity, partial third-upload failure,
owner epoch drift during upload, stale getters, replacement and idempotent close.
`../native-plant-publisher-v71.log` exercises the actual transactional uploader on
NVIDIA RTX 3080 Ti and draws/reads the resulting Java-produced cell and primitive
data through the joint decoder/intersection kernel. Malformed-data and existing
alpha/interval controls remain passing. Fixtures use synthetic model/fluid proofs;
there is no live-world binding or visual acceptance claim.

No Minecraft client was launched or ordinary state altered. Whole-model owner
coverage, full-field upload/binding, leaf radiance and complete water/sky/Sun
acceptance remain open.
