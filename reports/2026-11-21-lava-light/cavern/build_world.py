"""Fresh vanilla-noise survival level for seed 308060 with ONLY level.dat (no region files): Minecraft generates every chunk itself.
NBT writer + 1.21.1 dimension settings reused from tools/create-benchmark-world.py. Spawn = the tuff ledge above the natural lava.
Usage: python3 -I build_world.py <out-dir>   -> <out-dir>/Aqualumen-Lava-Cavern.zip (single entry Aqualumen-Lava-Cavern/level.dat)
"""
import gzip, importlib.util, io, json, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("cbw", REPO / "tools/create-benchmark-world.py")
cbw = importlib.util.module_from_spec(spec); spec.loader.exec_module(cbw)
S, I, B, C, L, payload = cbw.S, cbw.I, cbw.B, cbw.C, cbw.L, cbw.payload
LG = lambda v: (4, v)
F = lambda v: (5, v)
site = json.loads((HERE / "site.json").read_text())
NAME = "Aqualumen-Lava-Cavern"
# keys 1..9 = slots 0..8. Slot 8 stays empty (bare hand for clean photographs).
HOTBAR = [(0, "minecraft:bucket", 1), (1, "minecraft:water_bucket", 1), (2, "minecraft:soul_torch", 16), (3, "minecraft:stone", 64),
          (4, "minecraft:wooden_pickaxe", 1), (5, "minecraft:wooden_shovel", 1), (6, "minecraft:bread", 16)]


def level(name=NAME, hotbar=HOTBAR):
    base = cbw.level_data(site["seed"], name)
    fx, fy, fz = site["spawn"]["feet"]
    yaw, pitch = site["spawn"]["yaw"], site["spawn"]["pitch"]
    inv = [{"Slot": B(s), "id": S(n), "count": I(c)} for s, n, c in hotbar]
    player = {
        "Pos": L(6, [fx, float(fy), fz]), "Motion": L(6, [0.0, 0.0, 0.0]), "Rotation": L(5, [yaw, pitch]),
        "Dimension": S("minecraft:overworld"), "OnGround": B(True), "Air": I(300), "Fire": I(-20), "FallDistance": F(0.0),
        "Health": F(20.0), "foodLevel": I(20), "foodSaturationLevel": F(5.0), "foodExhaustionLevel": F(0.0), "foodTickTimer": I(0),
        "XpLevel": I(0), "XpP": F(0.0), "XpTotal": I(0), "Score": I(0), "playerGameType": I(0), "SelectedItemSlot": I(0),
        "Inventory": L(10, inv),
        "abilities": C({"flying": B(False), "mayfly": B(False), "instabuild": B(False), "invulnerable": B(False), "mayBuild": B(True),
                        "flySpeed": F(0.05), "walkSpeed": F(0.1)}),
    }
    d = {k: v for k, v in base.items() if k in ("DataVersion", "version", "Version", "DragonFight", "WorldGenSettings", "initialized")}
    d["Version"] = C({"Id": I(3955), "Name": S("1.21.1"), "Series": S("main"), "Snapshot": B(False)})
    d.update({
        "LevelName": S(name), "GameType": I(0), "Difficulty": B(0), "DifficultyLocked": B(False),
        "hardcore": B(False), "allowCommands": B(False),
        "SpawnX": I(int(fx // 1)), "SpawnY": I(int(fy)), "SpawnZ": I(int(fz // 1)), "SpawnAngle": F(yaw),
        "Time": LG(site["start_daytime"]), "DayTime": LG(site["start_daytime"]), "LastPlayed": LG(1795219200000),
        "raining": B(False), "rainTime": I(0), "thundering": B(False), "thunderTime": I(0), "clearWeatherTime": I(site["clear_weather_ticks"]),
        "WanderingTraderSpawnChance": I(25), "WanderingTraderSpawnDelay": I(24000),
        "BorderCenterX": (6, 0.0), "BorderCenterZ": (6, 0.0), "BorderSize": (6, 59999968.0), "BorderSafeZone": (6, 5.0),
        "BorderDamagePerBlock": (6, 0.2), "BorderWarningBlocks": (6, 5.0), "BorderWarningTime": (6, 15.0),
        "BorderSizeLerpTime": LG(0), "BorderSizeLerpTarget": (6, 59999968.0),
        "DataPacks": C({"Enabled": L(8, ["vanilla"]), "Disabled": L(8, ["bundle", "trade_rebalance"])}),
        "enabled_features": L(8, ["minecraft:vanilla"]),
        "GameRules": C({}),
        "Player": C(player),
    })
    return b"\x0a\x00\x00" + payload(10, {"Data": C(d)})


def level_dat_bytes():
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(level())
    return buf.getvalue()


def main():
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    zp = out / (NAME + ".zip")
    assert not zp.exists()
    info = zipfile.ZipInfo(NAME + "/level.dat", date_time=(2026, 11, 21, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr(info, level_dat_bytes())
    print(zp)


if __name__ == "__main__":
    main()
