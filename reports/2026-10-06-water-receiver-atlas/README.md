# Preserved rejected actual GPU observer

The exact-world TEST0.1.2 first attempt starts normally with0.6/physics0.2 and
actual NVIDIA/Iris, but rejects atlas internal-format enum6408 (`GL_RGBA`) at
16:12:15. The guard incorrectly required the sized enum32856 (`GL_RGBA8`).
It did not query component bits/types, so no GPU pixel acceptance is claimed.
The raw error, runtime log, exact installed/rebuilt JAR96ccb1c0c451dd8b37cb16e6c0a9a2ea2e76f7a3b8103ea66b6e271b514f8791
and pre-change producer sources are retained. No data is fabricated or replaced.

The stopped observer does not retry or change the actual atlas. TEST gameplay/
Save-Quit/title images are inspected. Owned58119 exits0 after16:14:16 all-dimensions
save; the observer is recoverably removed. Original41 ordinary save/config/Mod
bytes match before the next exclusive TEST cycle; no save restore occurs.

The corrected attempt is ../2026-10-06-water-receiver-atlas-v2/. It queries all
four channel sizes/types and accepts sized or unsized RGBA only if the actual
storage is8-bit unsigned-normalized for all four channels. This failed packet
is rejected evidence, not a qualified actual atlas or rendering improvement.
