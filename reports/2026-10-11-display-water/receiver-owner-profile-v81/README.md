# Owner guard optimization runtime v81

The actual NVIDIA/Iris run completed with auto-quit, and the owned launcher
exited zero. Request `30b10b9a-f7fd-43a5-9057-0cb6eb963e4c` recorded
`display-water-candidate-20261011-v81` using the allocation-free owner Mod v83.
The shader does not invoke the rejected hemisphere-normal candidate.

Underwater near recorded 14 frames / mean 1.4133598578335562 FPS;
underwater moving recorded 15 frames / mean 1.4980169328242137 FPS.
These remain unusable for convincing real-time motion. This is not a matched
same-wave/frame A/B and establishes no causal timing improvement over v80.

The attempted JFR startup did NOT succeed. `jcmd` returned zero but its response
said it could not write the recording file. No finalized JFR exists; no CPU
stack profile or recording-overhead conclusion is available. The original
`profile-receipt.json` records the attempted command parameters, not success.
Raw command response is retained only in its private directory.

The runtime helper now supports `profile-start`: it uses a cwd-relative filename
inside the verified Lab game directory, rather than a host-only cache path,
and requires an explicit `Started recording` response as well as zero exit.
That corrected path still needs live verification on a new owned run.

Collection completed and normal configurations/Mods were restored exactly.
The ordinary save is unchanged, no save rollback occurred, and instance config
is unchanged. See `runtime-restored.json`. Full water/Sun goal remains open.
