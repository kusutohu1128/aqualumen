# Replay harness rejection (not a renderer failure)

Initial replay stopped before Java/field generation: exact sealed-camera-oracle
equality failed on point7 because `math.dist` changed the length reduction order.
Travel14.107517099810128 versus sealed14.107517099810126 (~2e-15m); voxel/state
identity was unchanged. The next harness preserves the original explicit
`sqrt(sum(v*v))` reduction; it does not loosen or re-fit the oracle.

This failed directory is retained. No old Evidence or live game was modified.
