# Wide batched source runtime checkpoint

The full Sun/underwater appearance goal remains unachieved. This is a working
multi-face producer experiment, not an accepted visual or performance candidate.

- Actual Minecraft 1.21.1 / Iris 1.8.8 / Sodium 0.6.9, NVIDIA RTX 3080 Ti,
  Aqualumen Lab and UUID-guarded AqualumenNaturalV2.
- Candidate pack: `Aqualumen-DisplayWater-ReceiverWideBatch-v31-2026-10-11.zip`.
- Mod: `aqualumen-physics-0.3.0-receiver-wide-session-v43.jar`, SHA256
  `7009f2c637e8d7710a7e958859b40647e3ccfe6d4743ee74d85574436bae4747`.
- Shader sources match the v30 full native receipt (14 linked program pairs),
  while `../native-wide-upload-v31.log` covers the fixed raw uploader.

`receiver-runtime.log` records actual current-frame 33x36x33 fields with 1009
qualified face-center sources and 2178 partial/cap cells. Each periodic receipt
reports 1009 owned mesh captures, 12 section copies and one GPU source batch,
followed by ready-2 water-draw binding. No owned-source failure reports occurred.
The private renderer/buffers/cloned sections are scoped to one field capture;
source requests are grouped by section and returned in original ownership order.
Buffers reset before each face, packed inputs are copied before reuse, and all
private assets are released when capture ends. No ordinary terrain mesh is
submitted, and this is not a cross-frame material/light cache.

The first logged producer wall time is 971.502614ms. Periodic frames 60 and 120
record 223.342434ms and 215.297484ms. Only three periodic samples are available;
these are not all calls, independent GPU timings or proof of optimization gains.
This overhead is far too high for adoption despite the successful batch.

At actual 1600x800 with native screenshot capture:

| Scene | Frames | Mean ms | Median ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| underwater-up-near | 18 | 271.5449174444444 | 248.124338 | 449.00096 |
| underwater-up-moving | 19 | 253.76975042105263 | 250.376824 | 302.309213 |

The audit validated 37 native PNGs and pose/time metadata, not visual acceptance.
Moving frame-015 was actually viewed: fragmented bright boundary bands and a
broad dark exterior remain. Wide source production does not by itself admit a
ray starting on the displaced interface, and no production receiver-hit proof
or full motion-sequence acceptance is claimed.

Client exit was normal (0), and `runtime-restored.json` verifies exact normal
configuration/Mods/instance settings and ordinary save hashes. No ordinary save
rollback occurred. The rejected v30 crash was preserved and recovered only
through the explicitly verified stopped-packet path.

Next causal work: qualify actual interface-owned entry rather than skipping the
partial cell; reduce repeated within-frame world/mesh work while retaining a
fresh final geometry/light/resource audit; integrate resolved/residual interface
normals without inventing sky across TIR. Sun appearance acceptance remains open.
