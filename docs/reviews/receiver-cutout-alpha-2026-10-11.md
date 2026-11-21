# Explicit cutout source alpha qualification

The original receiver source accepted only alpha exactly one. That is retained
for ordinary top-face and generic material points. A separate explicit
`cutoutMaterialPoints` API now selects `receiverAlphaMode=1` in its private
captured source session, admitting finite alpha in [0.1,1], matching the
terrain shader's cutout discard threshold. This is binary cutout qualification,
not translucent blending or alpha-weighted radiance. Unknown mode, NaN,
out-of-range alpha and below-threshold coverage return paired unready zero.
Original caller-program uniforms are not modified by the private source draw.

The actual NVIDIA GPU receiver-source fixture verifies that strict mode rejects
alpha 0.5, cutout mode admits 0.1/0.5/1 with the same paired RGB as the original
opaque source, and rejects 0/0.099/1.01/NaN and invalid mode 2. All retained
source material/block-light, legacy-cache Sun/weather, atlas gradient/batch,
world-reflection, compressed DDA and published plant-backend controls succeeded
in the same `--water-world-reflection-only` run. These are controlled GPU
draw/readback results, not a new actual Minecraft cutout/LOD acceptance.

The updated Mod and shader must be tested together: the old pack lacks the
active alpha-mode uniform. No ordinary installation was changed. Live plant
source publication, complete model ownership and natural-image/motion judgment
remain required before adoption; the full rendering goal remains incomplete.
