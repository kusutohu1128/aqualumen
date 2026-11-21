# Actual region intake v69 — measured and restored, not visual acceptance

The exact diagnostic pack and Mod v76 were installed only in the reversible Lab
fixture. NVIDIA native checks compiled/linked 14 pairs and executed the existing
receiver/Sun regressions. Mod SHA256:
194e41a245d58ab70c4ff065e123e0177d715d98ad605b5e03ba6177f9b79dab.

Actual initial terrain frame 3/resources 1 reports 74 captured plant models,
1184 triangles and 10608 spatial memberships, with zero capture failures or
unloaded scanned cells. Owner states and retained chunk identities validate.
The region explicitly reports completeModelOwners=false and traceAdmission=false:
these observations do not establish whole-world ownership or visual acceptance.

The first benchmark request arrived before the integrated singleplayer server
was ready and was rejected. The owned launcher stayed live; after actual terrain
capture established world readiness, a fresh request was sent to the same client,
without restarting or overwriting a completed run. The same owned launcher exited
0 after the completed static/moving scenes. `candidate-runtime` and the filtered
`candidate-receiver-runtime.log` were collected. The native motion audit validates
60 PNG files; it does not establish visual acceptance. Moving mean FPS is
1.530917389, unsuitable for ordinary adoption.

`runtime-restored.json` confirms exact normal config/Mods and unchanged ordinary
save, with no save rollback and no instance-config change. No Java client remains.
The runtime helper now records a privacy-safe previous-log byte-count/hash before
launch and requires a newly written log with singleplayer start-region and then
world-pipeline markers before submitting a measurement request. Old logs and
appended late old-client lines are rejected by CPU tests. Existing v69 receipts
predate that future-launch guard; no claim is made that it was used for this run.

Actual region capture is established; complete world-model ownership, production
plant traversal/radiance, usable performance and full sky/Sun visual acceptance
remain unachieved.
