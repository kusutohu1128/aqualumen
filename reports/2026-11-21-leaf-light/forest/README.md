# Forest leaf-transport acceptance scene (natural V2 forest, private clones only)

Owner: Claude Opus (scene/visual advisor). Owns only this directory, `/tmp/aql-leaf-forest-*` and the campaign unit
`aql-leaf-forest-campaign` (systemd --user, survives the CLI turn). No product, other reports, Lab instance, original
world or config was edited. Live status: `status.json`.

## Site (naturally generated, read from a private snapshot of the exact V2 world)

* Snapshot: `snapshot.py` → `/tmp/aql-leaf-forest-snapshot-*/AqualumenNaturalV2` (copied under the exclusive
  `session.lock`, UUID `b22dbccb-…`, seed 308060, made read-only; digest in `snapshot.json`).
* Search: `sitesearch.py` (texel-resolved ray cast with the vanilla 1.21.1 leaf alpha masks read from the client JAR,
  vanilla cube UVs; plants/other models are counted as opaque). `choose.py` froze the result into `site.json`.
* Biome `minecraft:dark_forest`; both target leaves are generated `minecraft:oak_leaves[persistent=false]` of one tree.
* **Torch scene** – leaf `(208,69,372)`, camera-facing front face normal −X. Warm slot `(210,66,372)` and soul slot
  `(210,66,371)` stand on natural `grass_block`, 2 cells behind the leaf plane (n·L ≈ −0.65 at every patch). Stone
  blocker cells `(209,66..67,372)` sit between the warm flame and the leaf. In the close pose the flame is hidden by
  natural leaves; in the wide pose the flame is directly visible below the canopy.
* **Day scene** – leaf `(209,71,371)`, front normal +X, frozen time 11000 (Sun elevation 27.6° from −X; n·Sun = −0.886).
  All 256 face-texel Sun rays are open (model); the removable 3×4 stone wall at x=206, y 72–74, z 369–372 blocks all 256.
* Poses (`site.json → poses`, spectator, eye = feet + 1.62, vertical FOV 70, 1600×900): `torch-close`, `torch-wide`,
  `day-close`, `day-wide`, each with four 6×6 (close) / 4×4 (wide) pixel patches whose every pixel-centre ray hits an
  opaque texel of the target face (texels, world point and n·L recorded).
* 140 natural leaf/log cells around both leaves, the two grass supports and 29 reserved AIR cells are counted by the
  server before any write and at every READY/hold check; natural cells are never written (static check in `campaign.py`).

## Run design (`campaign.py`)

Ordinary client (three normal mods, no recorder mod), private exact-UUID/seed clone, `/tmp/aql-render21-1000.lock` held
per client, NVIDIA renderer asserted, source world tree, original Lab configs, mods and the pack archive re-hashed after
exit. A world-local datapack cycles 20 still items + 2 clips; each READY requires: all natural/reserved/support cells,
frozen `daytime`, clear weather (predicate), no non-player entity within 20 m (killed at scene start), exact spectator
pose (±0.01 m, ±0.05°). DRIFT/BEGIN after READY invalidates the capture (retried next cycle). HUD hidden with F1;
spectator has no selection outline/crosshair. Also logged: server light level of the camera-side air cell (location predicate).

Stills (pair of frames 0.6 s apart, pair diff and top-band "sky" diff recorded):
`off / warm / soul / both / blocked / restored` × `torch-close / torch-wide` (time 18000), then
`day-open / day-wall / day-restored / night-dark` × `day-close / day-wide`.
Clips: `orbit-warm`, `orbit-day` – ±35° arc around the leaf face, server `tp` every tick (20 Hz pose steps) recorded at
30 fps; this is instrumented camera motion, not uninstrumented play.

Commands:

```
python3 -I campaign.py dry
python3 -I campaign.py run <pack.zip> <run-name>     # e.g. a later rc2: run build/Aqualumen-1.8.0-leaf-rc2.zip rc2-r1
python3 -I campaign.py compare base-r1 rc2-r1
```

The `campaign` unit runs `base-r1` (dist/Aqualumen-1.7.0.zip) and then polls for
`build/Aqualumen-1.8.0-leaf-rc1.zip` (stable SHA required), runs `rc1-r1` and writes `compare-base-r1-vs-rc1-r1/`.
A campaign lock (`/tmp/aql-leaf-forest-campaign.lock`) prevents stacking; run dirs are never overwritten.

## Left to the parent explicitly

1440p frame timing, supplemental native QA, final install and the separate player experience.
Shader clouds advance with `frameTimeCounter` and cannot be frozen without product edits; the top-band pair diff reports it.
