# Actual underwater exit-direction diagnostic v88

Run `display-water-candidate-20261011-v88`, request
`cb9fa709-0aa7-47d5-a3b8-8b96e7801c1a`, disposable world UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, Aqualumen Lab.

This opt-in pack retains the original geometry, wave normals and ray calculation.
It adds yellow to the v87 palette only when a valid transmitted ray passes both
geometric-side tests but has world Y direction below -0.00001. Orange/red
geometric-side failures remain distinct. Yellow is a direction observation, not
proof that a subsequent displaced water interface is intersected.

The diagnostic pack's NVIDIA compile/link checks passed. Runtime routing tests
passed. Two 1600x800 scenarios completed with 5-second warmup and 20-second
samples. Both principal PNGs were visually inspected: the near image is largely
green/blue with narrow warm-colored boundary strips; the moving principal image
has localized yellow-green boundary patches alongside fragmented green/blue
regions. No large yellow interior region was apparent. Neither this observation
nor v87 explains the whole sky-window distortion by a broad wrong-side region.

Compositing and tone mapping alter the displayed palette: nominal yellow can
appear green-yellow. Existing v87 displayed-color thresholds must not be used
to claim exact yellow/orange ray-status counts. Exact separation requires a
dedicated untouched diagnostic target and an untonemapped final readout, or
qualified raw GPU readback. The full moving sequence was not visually reviewed;
the file/timestamp audit verified 83 PNGs, not temporal appearance.

The owned launcher exited with code 0. Collection and exact configuration/Mod
restoration completed without save rollback. No Java process remained. Ordinary
saves were not operated on. No rendering improvement or ordinary adoption is
claimed. The goal remains unmet.
