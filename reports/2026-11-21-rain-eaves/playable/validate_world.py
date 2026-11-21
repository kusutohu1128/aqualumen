"""Independent offline validation of the Aqualumen Rain Walk archive (stdlib only).

    python3 -I validate_world.py <archive.zip> --json validation.json --map map.txt

It never imports build_world.py.  It re-decodes level.dat and every packaged chunk with the NBT / Anvil
decoder of the Lantern House validator (a separate, older implementation) and derives everything from the
decoded blocks: settings, hotbar, patio strip/eave pairs, lantern-mirror line of sight, torch tree, tunnel
sky cover, reed/water rules, and walking routes in both directions with a block-level movement model.
No Sun, sky or lighting values are computed or claimed here: only geometry.
"""

import gzip
import importlib.util
import json
import math
import sys
import tempfile
import zipfile
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("aql_lh_validate", HERE.parents[1] / "2026-11-21-door-light/playable/validate_world.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

FAILS = V.FAILS
RESULT = {}
WORLD_FOLDER = "Aqualumen-Rain-Walk"
EYE = 1.62
PASSABLE = {"minecraft:air", "minecraft:short_grass", "minecraft:fern", "minecraft:poppy", "minecraft:dandelion",
            "minecraft:cornflower", "minecraft:oxeye_daisy", "minecraft:torch", "minecraft:wall_torch",
            "minecraft:oak_sign", "minecraft:sugar_cane"}
FORBIDDEN = ("command_block", "structure_block", "jigsaw", "barrier", "light", "redstone", "repeater", "comparator", "lever",
             "button", "pressure_plate", "tnt", "piston", "dispenser", "dropper", "observer", "hopper", "spawner", "end_portal",
             "lava", "cactus", "magma", "fire", "_bed", "chest", "furnace", "crafting", "debug")
GOOD_BANK = {"minecraft:stone", "minecraft:cobblestone", "minecraft:mossy_cobblestone"}


def check(ok, message):
    if not ok:
        FAILS.append(message)
    return ok


class World:
    def __init__(self, blocks):
        self.b = blocks
        self.ymax = max(y for _, y, _ in blocks)

    def name(self, x, y, z):
        v = self.b.get((x, y, z))
        if v:
            return v[0]
        # superflat default of every chunk we decode (chunks are fully written, so air above the stack)
        return "minecraft:air"

    def props(self, x, y, z):
        v = self.b.get((x, y, z))
        return v[1] if v else {}

    def passable(self, c):
        return self.name(*c) in PASSABLE

    def support(self, c):
        n = self.name(*c)
        return n not in PASSABLE and n != "minecraft:water" and n != "minecraft:lily_pad" and n not in ("minecraft:lantern", "minecraft:soul_lantern", "minecraft:chain")

    def sky_blocked(self, x, y, z):
        """A solid (non-passable, non-lantern/chain) block anywhere above the cell (decoded blocks only)."""
        for yy in range(y + 1, self.ymax + 1):
            n = self.name(x, yy, z)
            if n not in PASSABLE and n != "minecraft:water":
                return True
        return False

    def standable(self, x, y, z):
        return self.passable((x, y, z)) and self.passable((x, y + 1, z)) and self.support((x, y - 1, z))

    def segment_clear(self, a, b, skip=(), step=0.02):
        d = [q - p for p, q in zip(a, b)]
        n = max(int(math.sqrt(sum(v * v for v in d)) / step), 1)
        for i in range(n + 1):
            t = i / n
            c = tuple(math.floor(a[k] + d[k] * t) for k in range(3))
            if c in skip:
                continue
            if self.name(*c) not in PASSABLE:
                return False, c
        return True, None


# ------------------------------------------------------------------ main
def main(argv):
    zip_path = Path(argv[1])
    out_json = argv[argv.index("--json") + 1] if "--json" in argv else None
    out_map = argv[argv.index("--map") + 1] if "--map" in argv else None

    # ---- archive
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        infos = z.infolist()
        RESULT["archiveFiles"] = names
        check(all(n.startswith(WORLD_FOLDER + "/") for n in names), "not a single top-level world folder")
        check(WORLD_FOLDER + "/level.dat" in names, "level.dat missing")
        check(all(n == WORLD_FOLDER + "/level.dat" or (n.startswith(WORLD_FOLDER + "/region/r.") and n.endswith(".mca")) for n in names),
              "unexpected archive members: %s" % [n for n in names if n not in (WORLD_FOLDER + "/level.dat",) and not n.startswith(WORLD_FOLDER + "/region/r.")])
        check(all(i.date_time == (2026, 11, 21, 0, 0, 0) for i in infos), "zip timestamps are not the fixed deterministic ones")
        check(not any(("datapack" in n or "function" in n or "playerdata" in n or "icon" in n or "session" in n or ".txt" in n or ".json" in n) for n in names),
              "datapack/playerdata/marker-like member present")
        check(z.testzip() is None, "zip CRC")
        tmp = tempfile.mkdtemp(prefix="aql-rw-validate-")
        for i in infos:
            check(".." not in i.filename and not i.filename.startswith("/"), "unsafe member path")
            target = Path(tmp) / i.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(i))
    world_dir = Path(tmp) / WORLD_FOLDER

    # ---- level.dat settings
    lv = V.parse_nbt(gzip.decompress((world_dir / "level.dat").read_bytes()))["Data"]
    check(lv["DataVersion"] == 3955 and lv["Version"]["Name"] == "1.21.1", "not 1.21.1")
    check(lv["GameType"] == 0, "not survival")
    check(lv["Difficulty"] == 0, "not peaceful")
    check(lv["allowCommands"] == 0 and lv["hardcore"] == 0, "commands/hardcore")
    check(lv["GameRules"] == {}, "game rules must be all vanilla defaults (so day/night, weather cycle, mob rules are normal): %s" % lv["GameRules"])
    check(lv["DataPacks"]["Enabled"] == ["vanilla"], "datapacks enabled: %s" % lv["DataPacks"])
    check(lv["enabled_features"] == ["minecraft:vanilla"], "feature flags")
    gen = lv["WorldGenSettings"]["dimensions"]["minecraft:overworld"]["generator"]
    check(gen["type"] == "minecraft:flat" and gen["settings"]["biome"] == "minecraft:plains", "not superflat plains")
    check([(l["block"], l["height"]) for l in gen["settings"]["layers"]] == [("minecraft:bedrock", 1), ("minecraft:dirt", 2), ("minecraft:grass_block", 1)], "layers")
    check(gen["settings"]["structure_overrides"] == [] and not gen["settings"]["features"], "structures/features")
    check(not any(k in lv for k in ("ServerBrands", "CustomBossEvents", "ScheduledEvents", "WasModded", "Bukkit.Version")), "extra level keys")
    day, rain_t = lv["DayTime"], lv["rainTime"]
    check(lv["raining"] == 1 and lv["thundering"] == 0 and lv["clearWeatherTime"] == 0, "weather must start as plain rain, no forced clear/thunder")
    check(9000 <= day <= 12000, "DayTime %d not late afternoon/dusk" % day)
    check(3000 <= rain_t <= 4000, "rainTime %d ticks is not ~150-200 s" % rain_t)
    check(day + rain_t <= 14000, "rain would end after dark")
    RESULT["settings"] = dict(gameType=lv["GameType"], difficulty=lv["Difficulty"], allowCommands=lv["allowCommands"], gameRules=lv["GameRules"],
                              dayTime=day, time=lv["Time"], raining=lv["raining"], rainTicks=rain_t, rainSeconds=rain_t / 20,
                              rainEndsAtDayTime=day + rain_t, thunderTime=lv["thunderTime"], dataPacks=lv["DataPacks"])
    player = lv["Player"]
    check("UUID" not in player and "SpawnX" not in player, "player identity data present")
    ab = player["abilities"]
    check(not ab["mayfly"] and not ab["flying"] and not ab["instabuild"] and not ab["invulnerable"], "abilities are not plain survival")
    check(player["playerGameType"] == 0 and player["Health"] == 20.0 and player["foodLevel"] == 20, "player not a fresh survival player")
    inv = {i["Slot"]: (i["id"], i["count"]) for i in player["Inventory"]}
    RESULT["inventory"] = {str(k): v for k, v in sorted(inv.items())}
    sel = player.get("SelectedItemSlot", player.get("selectedItemSlot"))
    check(sel not in inv and sel is not None, "selected hotbar slot %s is not empty" % sel)
    check(all(0 <= s <= 8 for s in inv), "items outside the hotbar")
    ids = sorted(n for n, _ in inv.values())
    check(ids == sorted(["minecraft:torch", "minecraft:lantern", "minecraft:soul_lantern", "minecraft:wooden_pickaxe"]), "hotbar items: %s" % ids)
    pos, rot = player["Pos"], player["Rotation"]
    RESULT["spawn"] = dict(pos=pos, rotation=rot, selectedSlot=sel, worldSpawn=[lv["SpawnX"], lv["SpawnY"], lv["SpawnZ"]])

    # ---- chunks
    chunks = V.read_chunks(world_dir / "region")
    RESULT["chunks"] = len(chunks)
    blocks = V.decode_blocks(chunks)
    W = World(blocks)
    counts = {}
    for b in blocks.values():
        counts[b[0]] = counts.get(b[0], 0) + 1
    RESULT["blockCounts"] = dict(sorted(counts.items()))
    bad = sorted(n for n in counts if any(f in n for f in FORBIDDEN))
    check(not bad, "forbidden/test blocks: %s" % bad)
    bes = {}
    for ch in chunks.values():
        for be in ch["block_entities"]:
            bes[(be["x"], be["y"], be["z"])] = be
    check(set(be["id"] for be in bes.values()) == {"minecraft:sign"} and len(bes) == 2, "block entities beyond exactly 2 signs")
    for p, be in bes.items():
        check(W.name(*p) == "minecraft:oak_sign", "sign BE without sign block at %s" % (p,))
    RESULT["signs"] = {str(p): [json.loads(m)["text"] for m in be["front_text"]["messages"]] for p, be in sorted(bes.items())}
    check(all(any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF for c in "".join(t)) for t in RESULT["signs"].values()), "sign text not Japanese")
    check(all(len(t) <= 16 for lines in RESULT["signs"].values() for t in lines), "sign line too long")

    FLOOR = -61  # superflat grass layer (world y); feet stand at -60
    ex, ey, ez = pos[0], pos[1] + EYE, pos[2]
    sx, sy, sz = math.floor(pos[0]), math.floor(pos[1] + 1e-6), math.floor(pos[2])
    check(abs(pos[1] - (FLOOR + 1)) < 1e-9, "spawn feet not on the ground-level floor top")
    check(W.standable(sx, sy, sz), "spawn cell not standable")
    check(W.name(sx, sy - 1, sz) == "minecraft:stone", "spawn stands on %s, expected the stone strip" % W.name(sx, sy - 1, sz))
    check(abs(pos[0] - 3.5) < 1e-9 and abs(rot[0] - 180.0) < 1e-6, "spawn must be on route line x=3.5 facing north (yaw 180)")

    # ---- patio: lantern, strips, eave pairs
    lanterns = [p for p, b in blocks.items() if b[0] == "minecraft:lantern"]
    patio_lantern = [p for p in lanterns if W.name(p[0], p[1] + 1, p[2]) == "minecraft:dark_oak_planks"]
    check(len(patio_lantern) == 1 and blocks[patio_lantern[0]][1].get("hanging") == "true", "exactly one hanging lantern under the patio roof")
    lx, ly, lz = patio_lantern[0]
    L = (lx + 0.5, ly + 4.5 / 16, lz + 0.5)  # fixture model: glow centre 4.5/16 above the cell bottom
    roof = {p for p, b in blocks.items() if b[0] == "minecraft:dark_oak_planks"}
    eave_z = max(z for _, _, z in roof) + 1  # first row of cells with open sky
    RESULT["patio"] = dict(lanternCell=[lx, ly, lz], lanternCentre=[round(c, 4) for c in L], eavePlaneZ=eave_z, roofCells=len(roof))
    check(all(p[1] == ly + 1 for p in roof), "roof is not a single plane")
    stone = sorted(p for p, b in blocks.items() if b[0] == "minecraft:stone" and p[1] == FLOOR and 0 <= p[0] <= 12 and 0 <= p[2] <= 14)
    smooth = sorted(p for p, b in blocks.items() if b[0] == "minecraft:smooth_stone" and p[1] == FLOOR)
    check(len(stone) == 3 * 14 and len(smooth) == 3 * 14, "strips are not 3x14 of real stone / smooth_stone (%d, %d)" % (len(stone), len(smooth)))
    shelter, exposed = {}, {}
    for (x, y, z) in stone + smooth:
        (exposed if not W.sky_blocked(x, y, z) else shelter)[(x, z, W.name(x, y, z))] = True
    check(any(m == "minecraft:stone" for _, _, m in shelter) and any(m == "minecraft:stone" for _, _, m in exposed) and
          any(m == "minecraft:smooth_stone" for _, _, m in shelter) and any(m == "minecraft:smooth_stone" for _, _, m in exposed),
          "stone and smooth_stone must both exist sheltered and exposed")
    pairs = []
    for strip, xc in (("minecraft:stone", 4), ("minecraft:smooth_stone", 8)):
        for near, far in ((4, 6), (2, 8)):  # fixture pair rows: z +/- 1.5 and 3.0 around the eave plane (z 6)
            a = (xc + 0.5, FLOOR + 1.0, near + 0.5)
            b = (xc + 0.5, FLOOR + 1.0, far + 0.5)
            ca, cb = (xc, FLOOR, near), (xc, FLOOR, far)
            ok = W.name(*ca) == strip == W.name(*cb) and W.sky_blocked(*ca) and not W.sky_blocked(*cb)
            da, db = math.dist(a, L), math.dist(b, L)
            check(ok and abs(da - db) < 1e-9, "eave pair %s z%d/z%d: material/exposure/distance (%.4f vs %.4f)" % (strip, near, far, da, db))
            pairs.append(dict(material=strip, sheltered=list(ca), exposed=list(cb), distanceToLantern=round(da, 4), distanceExposed=round(db, 4)))
    RESULT["patio"]["pairs"] = pairs
    # sheltered/exposed boundary on the strips is exactly the eave plane
    check(all(W.sky_blocked(x, FLOOR, z) == (z < eave_z) for x, _, z in stone + smooth), "strip exposure does not follow the eave line")

    # ---- mirror line (specular reflection of the lantern on the exposed stone strip) from the spawn eye
    f = (ey - (FLOOR + 1.0)) / ((ey - (FLOOR + 1.0)) + (L[1] - (FLOOR + 1.0)))
    M = (ex + f * (L[0] - ex), FLOOR + 1.0, ez + f * (L[2] - ez))
    mc = tuple(math.floor(c) for c in (M[0], M[1] - 0.5, M[2]))
    check(W.name(*mc) == "minecraft:stone" and not W.sky_blocked(*mc), "mirror point %s is not exposed stone (%s)" % (M, W.name(*mc)))
    check(3.6 < M[0] < 5.4 and M[2] > eave_z + 1.0, "mirror point not well inside the exposed stone strip")
    ok1, hit1 = W.segment_clear((ex, ey, ez), (M[0], M[1] + 0.01, M[2]))
    ok2, hit2 = W.segment_clear((M[0], M[1] + 0.01, M[2]), L, skip={(lx, ly, lz)})
    ok3, hit3 = W.segment_clear((ex, ey, ez), L, skip={(lx, ly, lz)})
    check(ok1 and ok2 and ok3, "mirror/lantern line of sight blocked: %s %s %s" % (hit1, hit2, hit3))
    # camera frustum at the saved rotation (vertical FOV 70, the Lab default options fov 0.0), 16:9 and 1600x900 / 1280x720
    yaw, pitch = math.radians(rot[0]), math.radians(rot[1])
    fwd = (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
    right = (-math.cos(yaw), 0.0, -math.sin(yaw))
    up = (right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])

    def ndc(pt):
        d = [pt[i] - (ex, ey, ez)[i] for i in range(3)]
        depth = sum(a * b for a, b in zip(d, fwd))
        t = math.tan(math.radians(35))
        return (sum(a * b for a, b in zip(d, right)) / depth / (t * 16 / 9), sum(a * b for a, b in zip(d, up)) / depth / t, depth)

    nl, nm = ndc(L), ndc(M)
    for name, n in (("lantern", nl), ("mirror point", nm)):
        check(n[2] > 0 and abs(n[0]) < 0.85 and abs(n[1]) < 0.9, "%s outside the spawn frame: %s" % (name, n))
    px = lambda n: (round((n[0] + 1) * 800), round((1 - n[1]) * 450))
    RESULT["mirror"] = dict(eye=[round(c, 4) for c in (ex, ey, ez)], yaw=rot[0], pitch=rot[1], mirrorPoint=[round(c, 4) for c in M], mirrorBlock=list(mc),
                            mirrorBlockName=W.name(*mc), lineOfSight=dict(eyeToMirror=ok1, mirrorToLantern=ok2, eyeToLantern=ok3),
                            lanternPixel1600x900=px(nl), mirrorPixel1600x900=px(nm), lanternNdc=[round(v, 3) for v in nl[:2]],
                            mirrorNdc=[round(v, 3) for v in nm[:2]], distanceEyeToLantern=round(nl[2], 3), distanceEyeToMirror=round(nm[2], 3))
    # the same lantern also reflects on smooth stone from x where pose B stands (reported, not required in the spawn frame)
    ex_b = (8.5 - f * L[0]) / (1 - f)
    RESULT["mirror"]["smoothStonePoseB"] = dict(eyeXZ=[round(ex_b, 3), round(ez, 3)], mirrorPoint=[8.5, round(M[2], 3)],
                                                block=W.name(8, FLOOR, math.floor(M[2])))

    # ---- walking: straight W line and a block-level BFS, both directions
    line = []
    z = sz
    while W.standable(sx, sy, z):
        line.append(z)
        z -= 1
    end_z = line[-1]
    ahead = W.name(sx, sy - 1, end_z - 1), W.name(sx, sy, end_z - 1)
    water_ahead = any(W.name(sx + dx, sy - 1, end_z - 1 - k) == "minecraft:water" for k in range(0, 3) for dx in (0,))
    check(water_ahead, "the straight north line does not end at water (ahead %s)" % (ahead,))
    check(line[-1] < -70, "straight north line is only %d cells long" % len(line))
    # every cell of the line, both directions: flat, 2 headroom, no side obstruction in the 0.6-wide hitbox (it stays in column x=3)
    flat = all(W.standable(sx, sy, zz) for zz in line)
    check(flat, "line has non-flat cells")
    # tunnel: contiguous run of the line whose columns are roofed
    covered = [zz for zz in line if W.sky_blocked(sx, sy, zz)]
    runs, cur = [], []
    for zz in line:
        if W.sky_blocked(sx, sy, zz):
            cur.append(zz)
        elif cur:
            runs.append(cur), (cur := [])
    if cur:
        runs.append(cur)
    # patio roof run + tunnel run: patio z 0..5, tunnel is the long one
    tunnel = max(runs, key=len)
    check(len(tunnel) >= 15 and min(tunnel) < -30, "no tunnel-length sky-blocked run on the line (%s)" % [len(r) for r in runs])
    RESULT["route"] = dict(startCell=[sx, sy, sz], lineCells=len(line), endCell=[sx, sy, end_z], flatLine=flat,
                           skyBlockedRuns=[[r[0], r[-1]] for r in runs], aheadOfEnd=list(ahead),
                           lineLengthMeters=round(pos[2] - (end_z + 0.5), 2))

    def bfs(start, goal_fn, dy_allowed):
        q, prev = deque([start]), {start: None}
        while q:
            c = q.popleft()
            if goal_fn(c):
                path = []
                while c:
                    path.append(c)
                    c = prev[c]
                return path[::-1]
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for dy in dy_allowed:
                    n = (c[0] + dx, c[1] + dy, c[2] + dz)
                    if n in prev or not (-60 <= n[0] <= 60 and -130 <= n[2] <= 40):
                        continue
                    if not W.standable(*n):
                        continue
                    if dy == 1 and not W.passable((c[0], c[1] + 2, c[2])):
                        continue  # no headroom to jump
                    if dy == -1 and not W.passable((n[0], n[1] + 2, n[2])):
                        continue
                    prev[n] = c
                    q.append(n)
        return None

    bank_goal = lambda c: any(W.name(c[0] + dx, c[1] - 1, c[2] + dz) == "minecraft:water" for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    start, end = (sx, sy, sz), (sx, sy, end_z)
    tunnel_mid = (sx, sy, tunnel[len(tunnel) // 2])
    for label, dys in (("flatOnly", (0,)), ("stepsOneUpDown", (0, 1, -1))):
        fwd_path = bfs(start, lambda c: c == end, dys)
        back_path = bfs(end, lambda c: c == start, dys)
        mid_path = bfs(start, lambda c: c == tunnel_mid, dys)
        bank = bfs(start, bank_goal, dys)
        check(fwd_path and back_path and mid_path and bank, "route %s: no path (fwd/back/tunnel/bank)" % label)
        if fwd_path:
            steps = [b[1] - a[1] for a, b in zip(fwd_path, fwd_path[1:])]
            RESULT["route"][label] = dict(forwardCells=len(fwd_path), backCells=len(back_path) if back_path else None,
                                          toTunnelMid=len(mid_path) if mid_path else None, verticalSteps=sum(1 for s in steps if s),
                                          toBankCells=len(bank) if bank else None)
    check(RESULT["route"].get("flatOnly", {}).get("verticalSteps") == 0, "flat route needs a step")
    # hazards beside the line (3x3 around the centre column, 0..3 high): no fluid, no fire, no hazardous block
    haz = [(x, y, zz) for zz in line for x in (sx - 1, sx, sx + 1) for y in (sy, sy + 1, sy + 2)
           if W.name(x, y, zz) in ("minecraft:water", "minecraft:lava", "minecraft:fire", "minecraft:cactus", "minecraft:magma_block")]
    check(not haz, "fluid/hazard beside the walking line: %s" % haz[:4])
    # headroom on the line: 3 free cells above the floor in the tunnel (beams are flush with the ceiling)
    tight = [zz for zz in tunnel if not all(W.passable((sx, sy + k, zz)) for k in (0, 1, 2))]
    check(not tight, "tunnel headroom below 3 at %s" % tight)

    # ---- torch tree
    torch_trees = []
    off = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}  # facing -> offset of the supporting block
    for p, b in sorted(blocks.items()):
        if b[0] != "minecraft:wall_torch":
            continue
        d = off[b[1]["facing"]]
        sup = (p[0] + d[0], p[1], p[2] + d[1])
        check(W.support(sup), "wall torch %s has no support" % (p,))
        if W.name(*sup).endswith("_log"):
            leaves = sum(1 for dx in range(-3, 4) for dz in range(-3, 4) for dy in range(0, 7)
                         if W.name(sup[0] + dx, sup[1] + dy, sup[2] + dz).endswith("_leaves"))
            torch_trees.append(dict(torch=list(p), facing=b[1]["facing"], trunk=list(sup), trunkBlock=W.name(*sup), leavesNearby=leaves))
    tree_torches = [t for t in torch_trees if t["torch"][2] > -30]  # south of the ridge, on the line to the tunnel
    check(len(tree_torches) == 1, "expected exactly one torch on a tree south of the ridge, found %d" % len(tree_torches))
    if tree_torches:
        t = tree_torches[0]
        check(t["leavesNearby"] > 20, "torch tree has no crown")
        tp = tuple(t["torch"])
        check(abs(tp[0] - 3) <= 8, "torch tree is not beside the route")
        okt, hitt = W.segment_clear((ex, ey, ez), (tp[0] + 0.5, tp[1] + 0.8, tp[2] + 0.5), skip={tp})
        check(okt, "torch not visible from spawn: %s" % (hitt,))
        okp, hitp = W.segment_clear((3.5, -60 + EYE, tp[2] + 0.5), (tp[0] + 0.5, tp[1] + 0.8, tp[2] + 0.5), skip={tp})
        check(okp, "torch not visible from the path beside it")
        RESULT["torchTree"] = dict(t, visibleFromSpawn=okt, visibleFromPathBeside=okp)

    # ---- tunnel: ceiling cover, frames, torches, lantern, ore
    cover_min = min(min(y2 for y2 in range(sy + 1, W.ymax + 2) if W.name(x, y2, zz) not in PASSABLE) for zz in tunnel for x in (sx - 1, sx, sx + 1)) if tunnel else None
    thick = []
    for zz in tunnel:
        for x in (sx - 1, sx, sx + 1):
            first = next(y2 for y2 in range(sy + 1, W.ymax + 2) if W.name(x, y2, zz) not in PASSABLE)
            solid_above = sum(1 for y2 in range(first, W.ymax + 1) if W.name(x, y2, zz) not in PASSABLE and W.name(x, y2, zz) != "minecraft:water")
            thick.append(solid_above)
    check(min(thick) >= 3, "tunnel cover thinner than 3 blocks (%d)" % min(thick))
    zr = (min(tunnel) - 2, max(tunnel) + 2)
    in_tun = lambda p: zr[0] <= p[2] <= zr[1] and -2 <= p[0] <= 8
    tun_torch = sorted(p for p, b in blocks.items() if b[0] == "minecraft:wall_torch" and in_tun(p))
    tun_lantern = sorted(p for p in lanterns if in_tun(p))
    frames = sorted({p[2] for p, b in blocks.items() if b[0] == "minecraft:oak_log" and b[1].get("axis") == "x" and in_tun(p)})
    ore = {n: sum(1 for p, b in blocks.items() if b[0] == n and in_tun(p)) for n in ("minecraft:coal_ore", "minecraft:iron_ore")}
    check(len(tun_torch) >= 4 and len(tun_lantern) >= 1 and len(frames) >= 3 and ore["minecraft:coal_ore"] >= 5, "tunnel dressing too thin")
    # mid-tunnel cell is dark relative to portals: no torch/lantern within 3 blocks of at least one route cell
    lights = tun_torch + tun_lantern + [p for p in blocks if blocks[p][0] == "minecraft:wall_torch" and zr[0] - 1 <= p[2] <= zr[1] + 1]
    gap = {zz: round(min(math.dist((sx + .5, sy + 1, zz + .5), (p[0] + .5, p[1] + .5, p[2] + .5)) for p in lights), 2) for zz in tunnel}
    far = [zz for zz in tunnel if gap[zz] > 4]
    RESULT["tunnel"] = dict(skyBlockedZ=[tunnel[0], tunnel[-1]], lengthBlocks=len(tunnel), minSolidAbove=min(thick), wallTorches=[list(p) for p in tun_torch],
                            lanterns=[list(p) for p in tun_lantern], timberFrameZ=frames, ore=ore, dimmestRouteCell=dict(z=max(gap, key=gap.get), metresFromNearestLight=max(gap.values())),
                            routeCellsMoreThan4mFromAnyLight=len(far))
    # tunnel floor: solid stone-ish, never water/air
    check(all(W.name(sx, sy - 1, zz) in ("minecraft:cobblestone", "minecraft:gravel", "minecraft:andesite") for zz in tunnel), "tunnel floor materials")

    # ---- pond: connected source water, banks, reeds
    water = {p for p, b in blocks.items() if b[0] == "minecraft:water"}
    check(all(b[1].get("level") == "0" for p, b in blocks.items() if b[0] == "minecraft:water"), "non-source water")
    seen, comps = set(), []
    for p in sorted(water):
        if p in seen:
            continue
        comp, q = [], deque([p])
        seen.add(p)
        while q:
            c = q.popleft()
            comp.append(c)
            for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)):
                n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
                if n in water and n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(comp)
    check(len(comps) == 1, "water is not one body (%d)" % len(comps))
    body = comps[0]
    surface_cells = [p for p in body if p[1] == FLOOR]
    # no leaks: every water cell's side neighbours are water or solid (nothing for it to flow into), floor is solid
    leaks = [p for p in body for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)) if W.name(p[0] + d[0], p[1] + d[1], p[2] + d[2]) in PASSABLE]
    check(not leaks, "water has open neighbours (would flow): %s" % leaks[:3])
    check(len(surface_cells) >= 250 and max(p[1] for p in body) == FLOOR and min(p[1] for p in body) == FLOOR - 1, "pond too small/shallow: %d surface cells" % len(surface_cells))
    xs = [p[0] for p in surface_cells]
    zs = [p[2] for p in surface_cells]
    bank = [p for p in blocks if blocks[p][0] in GOOD_BANK and p[1] == FLOOR and any((p[0] + dx, FLOOR, p[2] + dz) in water for dx in (-1, 0, 1) for dz in (-1, 0, 1))]
    check(len(bank) >= 20, "stone bank too short (%d)" % len(bank))
    cane = [p for p, b in blocks.items() if b[0] == "minecraft:sugar_cane" and W.name(p[0], p[1] - 1, p[2]) != "minecraft:sugar_cane"]
    bad_cane = [p for p in cane if not (W.name(p[0], p[1] - 1, p[2]) in ("minecraft:sand", "minecraft:grass_block", "minecraft:dirt") and
                                         any((p[0] + dx, p[1] - 1, p[2] + dz) in water for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))))]
    check(len(cane) >= 12 and not bad_cane, "reeds: %d plants, %d without a water-adjacent sand/grass base" % (len(cane), len(bad_cane)))
    inlet = [p for p in surface_cells if p[0] < -5]  # the narrow west arm
    check(len(inlet) >= 12, "no narrow inlet arm (%d cells)" % len(inlet))
    pads = [p for p, b in blocks.items() if b[0] == "minecraft:lily_pad" and (p[0], p[1] - 1, p[2]) in water]
    RESULT["pond"] = dict(surfaceCells=len(surface_cells), depth=2, xRange=[min(xs), max(xs)], zRange=[min(zs), max(zs)], inletArmCells=len(inlet),
                          stoneBankCells=len(bank), bankMaterials={n: sum(1 for p in bank if blocks[p][0] == n) for n in sorted(GOOD_BANK)},
                          reeds=len(cane), reedColumnsHeight=sorted({sum(1 for k in range(0, 4) if W.name(p[0], p[1] + k, p[2]) == "minecraft:sugar_cane") for p in cane}),
                          lilyPads=len(pads), singleBody=len(comps) == 1)

    # ---- trees: every leaf persistent and attached; nothing hangs into the walking line
    leaf = [(p, b) for p, b in blocks.items() if b[0].endswith("_leaves")]
    check(all(b[1]["persistent"] == "true" for _, b in leaf), "non-persistent leaves would decay")
    check(not any(p[0] in (2, 3, 4) and p[1] in (sy, sy + 1, sy + 2) for p, _ in leaf if p[2] in line), "leaves in the walking corridor")
    species = {n: sum(1 for p, b in blocks.items() if b[0] == n and b[1].get("axis") == "y") for n in ("minecraft:oak_log", "minecraft:birch_log", "minecraft:spruce_log")}
    RESULT["trees"] = dict(logBlocks=species, leafBlocks=len(leaf))
    grass_top = {}
    for p, b in blocks.items():
        if b[0] == "minecraft:grass_block" and -58 <= p[2] <= -33 and -20 <= p[0] <= 28:
            grass_top[(p[0], p[2])] = max(grass_top.get((p[0], p[2]), -99), p[1])
    RESULT["ridge"] = dict(maxTopY=max(grass_top.values()), heightAboveGround=max(grass_top.values()) - FLOOR, treesOnRidge=sum(
        1 for p, b in blocks.items() if b[0].endswith("_log") and b[1].get("axis") == "y" and -58 <= p[2] <= -33 and p[1] > FLOOR + 3 and W.name(p[0], p[1] - 1, p[2]) in ("minecraft:grass_block",)))
    check(RESULT["ridge"]["treesOnRidge"] >= 10, "ridge is not wooded")

    # ---- maps
    if out_map:
        glyph = {"minecraft:grass_block": ".", "minecraft:dirt_path": "=", "minecraft:water": "~", "minecraft:stone": "s", "minecraft:smooth_stone": "S",
                 "minecraft:spruce_planks": "p", "minecraft:dark_oak_planks": "R", "minecraft:sand": ",", "minecraft:cobblestone": "c", "minecraft:mossy_cobblestone": "m",
                 "minecraft:gravel": "g", "minecraft:andesite": "a", "minecraft:dirt": "d"}
        lines = ["top-down: first non-air block from above; '^' = tree crown/leaves, '|' = log, 'H' = hill top(grass, y>2), '*' = lantern, 't' = wall torch, '@' = spawn, '#' = route line",
                 "x -24..31 across, z 16 (south, top) .. -100 (north, bottom); '+' marks the x=3 route column", ""]
        for z in range(16, -101, -1):
            row = []
            for x in range(-24, 32):
                top = None
                for y in range(W.ymax, -64, -1):
                    n = W.name(x, y, z)
                    if n != "minecraft:air":
                        top = (y, n)
                        break
                if top is None:
                    row.append(" ")
                    continue
                y, n = top
                if n.endswith("_leaves"):
                    g = "^"
                elif n.endswith("_log"):
                    g = "|"
                elif n == "minecraft:lantern":
                    g = "*"
                elif n == "minecraft:wall_torch" or n == "minecraft:torch":
                    g = "t"
                elif n == "minecraft:grass_block" and y > FLOOR + 2:
                    g = "H"
                elif n in ("minecraft:short_grass", "minecraft:fern", "minecraft:poppy", "minecraft:dandelion", "minecraft:cornflower", "minecraft:oxeye_daisy"):
                    g = "."
                elif n == "minecraft:sugar_cane":
                    g = "i"
                elif n == "minecraft:oak_sign":
                    g = "!"
                else:
                    g = glyph.get(n, "?")
                if (x, z) == (3, 12):
                    g = "@"
                row.append(g)
            lines.append("%4d " % z + "".join(row))
        lines += ["", "side view along the route column x=3 (z -100 = north at the left .. z 16 = south at the right), y -42 (top) .. -63, '.' air, '#' solid, 'w' water, 'L' lantern/torch, '|' log, '^' leaves", ""]
        for y in range(-42, -64, -1):
            row = []
            for z in range(-100, 17):
                n = W.name(3, y, z)
                row.append("." if n == "minecraft:air" else "w" if n == "minecraft:water" else "L" if "lantern" in n or "torch" in n else "|" if n.endswith("_log") else "^" if n.endswith("_leaves") else "#")
            lines.append("%4d " % y + "".join(row))
        Path(out_map).write_text("\n".join(lines) + "\n")

    RESULT["failures"] = FAILS
    RESULT["ok"] = not FAILS
    if out_json:
        Path(out_json).write_text(json.dumps(RESULT, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: RESULT[k] for k in ("ok", "failures", "settings", "route", "mirror", "pond", "tunnel", "torchTree", "trees", "ridge") if k in RESULT}, indent=1, ensure_ascii=False))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
