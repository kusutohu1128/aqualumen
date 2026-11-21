# Natural underwater normal comparison v80

Both owned launchers completed with exit zero and automatic quit. Control run
`display-water-control-20261011-v80` used request
`427562cc-2a10-4757-a21f-df60de6b184c`; candidate run
`display-water-candidate-20261011-v80` used request
`76331e14-449e-4748-93d6-1421d31f56d6`.

The two ZIP member lists are identical. Byte comparison established that only
`shaders/gbuffers_water.fsh` differs, and removing the candidate's underwater
`waterReflectionNormal` invocation exactly reproduces the control. Unlike the
older glare comparisons, this control keeps both composite passes intact.

Both roles recorded two focused NVIDIA/Iris scenes without fallback, 1600x800.
Actual static camera position and rotation match: (448.5,62.38899988555908,-383.5),
yaw -45 / pitch -90. Moving scene positions match but final yaw differs:
69.17332 control versus 71.24724 candidate, both pitch -65. Wind/wave phase was
not synchronized. Do not treat these images as pixelwise causal A/B evidence.

| Scene | Control frames / mean FPS | Candidate frames / mean FPS |
| --- | --- | --- |
| underwater-up-near | 13 / 1.3848658392740898 | 14 / 1.4782258687390781 |
| underwater-up-moving | 14 / 1.4843783970314384 | 14 / 1.4436362380673837 |

`native_motion_audit.py` verified 27 control and 28 candidate PNGs with their
recording metadata. This is file/timestamp validation, not temporal acceptance.
All four principal original PNGs were visually inspected. Both roles retain
folded bright rims, dark polygonal exterior patches and distorted sky windows;
small dark square marks also remain in moving-view stills. Their individual
causes were not established by this experiment. No visual fix is accepted and
approximately 1.4 FPS remains unusable for meaningful natural motion judgment.

After collection, normal configurations and Mods were restored exactly.
The ordinary save matches the pre-run tree; no save rollback occurred and
the instance configuration did not change. See `runtime-restored.json`.

The candidate invocation was subsequently removed from ordinary shader source,
not promoted. The production helper and direct GPU invariant test are retained
as research. These artifacts do not complete the Sun/water/lighting goal.
