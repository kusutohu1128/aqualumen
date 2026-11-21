# Iris unsized depth storage

Actual hit1d baseline FINAL capture failed closed on depthtex0 format 6402 at 1600x900, base level 0. Failure manifest is archived in `runtime-baseline/failed-depth-format-capture`. No raw depth acceptance was claimed. Lab was cooperatively stopped and normal config, Mods and ordinary save hashes were restored exactly.

The pinned Iris jar's DepthBufferFormat maps its default DEPTH to GL_DEPTH_COMPONENT and UNSIGNED_SHORT. A new context on this actual NVIDIA driver using the same allocation returns format 6402, depthBits 24 and depthType 35863 (UNSIGNED_NORMALIZED). The native receipt is in `depth-storage-probe`. That probe is not actual Iris storage proof.

The observer now accepts unsized format 6402 only with the exact 24-bit unsigned-normalized storage pair, and records both queried fields. Other unsized storage still fails. Sized depth formats and the strict RGBA32F color guard are unchanged. Actual Iris must independently match those fields during the new capture. Versions become hit1d2/depth2. Old generated copies and failed capture remain immutable.

Only the observer Java changes. Regenerated shader ZIPs must be byte-identical to baseline/candidate, so their previous actual NVIDIA compile/native qualification can be reused by exact archive hash. No completed shader test is repeated for this observer-only boundary fix. The original generator is saved as `generator-depth1.py` before updating its canonical new source.
