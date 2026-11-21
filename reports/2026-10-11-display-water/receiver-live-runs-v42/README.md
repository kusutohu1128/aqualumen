# Live wide compressed field: failed timing run

The full Sun/underwater appearance and performance goal remains unachieved.

Mod v50 SHA256:
`9760f625ac38bc89ac0bc42557be563c21b3475c7dde7226a89b262aa72d7a0e`.
Candidate pack: `Aqualumen-DisplayWater-ReceiverLiveRuns-v42-2026-10-11.zip`.
The bridge captures 87x36x87 rather than the dense 33x36x33 window, composes
owned exposed-top source points, freshly audits geometry and publishes six
compressed textures. The shader supports a maximum horizontal extent of 96;
this runtime window leaves record-capacity headroom for nonuniform terrain.

Actual NVIDIA Minecraft / Aqualumen Lab / UUID-guarded AqualumenNaturalV2
published and bound run mode 1. Initial receipt: 55983 records, 6748 ready
sources, 6777 owned mesh captures, 60 section copies, two source batches,
600146 backend cell/height reads across both phases. Later receipts: 55329
records, 6686 ready sources, 6715 mesh captures, 54 sections and two batches.
The bound program's actual mode/count and all six texture IDs were checked.

Producer wall samples were 2520.309047ms initially, then 1085.692785ms and
1113.587188ms. This is grossly unacceptable. The benchmark aborted in the static
scene with `Too few frame intervals`; no complete timing result or moving scene
was collected. Three recorded native-motion timestamps are about 1.18-1.19s
apart; they are not a completed frame-time benchmark.

Four partial native PNGs are retained in `candidate-aborted-runtime`; frame-003
was actually viewed. Dark exterior patches remain. This is not a controlled
image comparison, motion acceptance, complete PNG/pose audit or proof that wide
coverage alone resolves the boundary. The failure is preserved, not treated as
a successful runtime run or hidden by weakening the frame-count check.

The owned benchmark's UUID-guarded quit request exited normally (0), with
fixture cleanup complete. Normal configs, Mods, instance settings and ordinary
save hashes were restored exactly without save rollback. Receiver-only stdout
is archived; private launcher data is excluded.

Next work must reduce source generation and fresh geometry-audit cost before
this broad field can be adopted. Sparse GPU storage solves the dense capacity
limit, not the CPU cost of meshing thousands of individual source faces each
frame. Field hit diagnosis and critical-angle boundary treatment still need
qualified image evidence; Sun appearance remains an open requirement.
