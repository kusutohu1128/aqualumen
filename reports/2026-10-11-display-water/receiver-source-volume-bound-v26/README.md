# Same-frame water-draw field binding

The bounded owned source producer again published one qualified source at frame
3/resource generation 1, in a 3x36x3 field at (447,32,-385). The actual water
multi-draw, program 424, read ready 2 with the four exact published texture IDs:
cells 83/unit7, total 84/unit8, Sun 85/unit9, faces 86/unit10.
`source-runtime.log` retains the positive producer and actual binding receipts.

Publication happens after normal per-frame uniform updates may already have
run. A temporary draw-scoped binding therefore supplies the current exact-epoch
ready/bounds/origin and four textures immediately before the actual water draw.
It uses the Iris-assigned distinct sampler units, rejects incompatible comparison
samplers, and restores original texture bindings and readiness/bounds/origin
after the multi-draw, querying their restored values. It does not overwrite
normal pipeline uniform caches or leave borrowed draw state changed.

The producer is still one-shot, with readiness valid only for frame 3. There is
no positive later-frame/stale-readback or reload proof. The sparse field and
face-center point approximation do not establish a reflection-ray hit, original
fragment derivatives, persistent source scheduling or a natural view. Partial
surface water and vegetation remain unavailable barriers. The broad dark TIR
exterior and rim/Sun appearance gates remain open; the full goal is not complete.

Experimental Mod SHA256:
`6a697d09b98a7bc1130cd42be7b3ecdf2efdc602d46c1df0bfe6fc63cadaf543`.
The near-view run and restoration receipts are separate from this first-frame
binding evidence; native PNG validation is not visual/FPS acceptance.
