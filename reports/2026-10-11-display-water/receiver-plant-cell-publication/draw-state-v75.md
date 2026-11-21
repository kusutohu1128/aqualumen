# Complete plant draw state v75

`ReceiverPlantDrawBinding` derives bounded integer window offsets and a
camera-relative packet reference from the exact current publication. It validates
camera/LOD domains before GL changes, captures all backend metadata, disables
readiness while binding data plus the owned atlas/sampler, and enables readiness
only after final publication/program qualification. Context guard and epoch
readiness remain separate. Ordinary programs without the contract are not enabled.

Close restores metadata, all four textures/samplers and the caller's active program,
including a caller program switch. Failed-open rollback restores the previous state
instead of leaving partly updated metadata. Sampler unit collisions remain checked
across active resource arrays. This does not create complete world-model coverage,
atlas ownership or a production LOD estimate; those inputs need live validation.

`../native-plant-draw-state-v75.log` draws the actual shared published backend with
the complete binding on NVIDIA RTX 3080 Ti. Results match direct Java publication
for opaque/transparent/unowned alpha. Metadata and nonzero texture/sampler bindings
restore; camera-relative translation and nonzero receiver-window offsets preserve
the draw. Camera/LOD/atlas-alias controls reject, and changed-program close and
late program-change failed-open rollback restore captured state.

The final current-source artifact is
`build/aqualumen-physics-0.3.0-plant-draw-state-guard-v82.jar`, built but not installed.
The preceding v81 artifact predates the final late-program guard and is retained
without overwrite. No Minecraft runtime or ordinary settings/saves changed. Live
owner-complete capture and adoption, leaf radiance, performance and complete
water/sky/Sun visual/temporal acceptance remain open.
