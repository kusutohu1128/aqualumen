# Actual fluid-qualified atomic plant publication v99

Actual run `display-water-candidate-20261011-v99`, request
`3162c797-2608-4701-bcdf-df9305255aa9`, completed with owned launcher exit 0.

All 4,042 models and 48,192 triangles were retained, with 334,416 cell memberships,
no unavailable models and no unloaded scan cells. All 272,484 scanned block
states were checked before and after diagnostic GPU work.

The actual padded 89x38x89 cell publication reads three successive world water
observations per cell, starts a fresh chunk-validation phase, and compares those
observations again before publication. 112,428 cells qualified as full water
columns. Complete owner flags remain deliberately false: completeOwnerCells=0.
Water proof is not proof of complete plant model coverage.

The actual atomic publisher uploaded headers, membership indices, tiled geometry
and associated tiled material together. All four textures passed exact GPU
readback. The separate 384x753 material readback also matched. Diagnostic textures
were released; none were bound to the water draw or admitted as live reflection.

Next establish complete cell model-owner coverage, including missing/new owners,
spill/boundary rules and fresh world/resource ownership, then connect publication
to the actual draw without reusing a stale one-shot epoch. The successful upload
must not be confused with rendered vegetation reflection or natural water motion.

Normal configurations, Mods and ordinary save hashes matched after restore;
no save rollback was performed. No beauty-image or temporal review was performed
for this packet. Main sky, Sun/coherent-light, motion and usable-performance
requirements remain incomplete.
