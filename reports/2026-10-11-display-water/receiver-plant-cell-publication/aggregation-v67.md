# Multi-model packet aggregation v67

`ReceiverPlantPacket.aggregate` combines independently captured model packets
without changing their uploaded float coordinates, UV or alpha qualification.
It requires one exact coordinate reference and the same world/frame/resource
epoch. Duplicate packet objects, mixed references, stale epochs, empty inputs
and capacity overflow are rejected. The explicit maximum is 4096 triangles,
compatible with a 4×4096 primitive texture and the current bounded uploader.
The 512 limit remains per selected cell, not per global aggregate.

CPU tests aggregate 300 model packets into 600 triangles, verify exact original
serialized payloads and stable global addresses for every owner cell, and cover
qualification/order/identity/capacity negatives. Controlled NVIDIA intersection
tests additionally draw against a 600-triangle texture while selecting only two
high-index triangles, retaining their original IDs. Evidence is recorded in
`../native-plant-aggregate-v67.log`.

This is aggregation of supplied packets, not proof that every world model was
captured. Model-owner coverage, capture invalidation, larger-scene capacity policy
and live publication/binding remain required. No Minecraft client or ordinary
settings/saves were touched. Full visual water/sky/Sun acceptance remains open.
