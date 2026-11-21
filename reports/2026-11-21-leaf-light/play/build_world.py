"""Fresh survival level.dat for seed 308060 (vanilla noise Overworld, features on); NO region files, so Minecraft generates
every chunk itself. NBT writer + dimension settings are reused from tools/create-benchmark-world.py (1.21.1 level format).
Usage: python3 -I build_world.py <out-dir>   (creates <out-dir>/Aqualumen-Woodland/level.dat only)
"""
import gzip, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("cbw", REPO / "tools/create-benchmark-world.py")
cbw = importlib.util.module_from_spec(spec); spec.loader.exec_module(cbw)
S, I, B, C, L, payload = cbw.S, cbw.I, cbw.B, cbw.C, cbw.L, cbw.payload
LG = lambda v: (4, v)
F = lambda v: (5, v)
site = json.loads((HERE / "site.json").read_text())

# Hotbar: slot 0 stays empty (bare hand removes torches/leaves). Ordinary wooden kit, no iron, no advancement-triggering items.
HOTBAR = [(1, "minecraft:torch", 32), (2, "minecraft:soul_torch", 32), (3, "minecraft:lantern", 4), (4, "minecraft:soul_lantern", 4),
          (5, "minecraft:wooden_pickaxe", 1), (6, "minecraft:wooden_axe", 1), (7, "minecraft:wooden_shovel", 1), (8, "minecraft:bread", 16)]


def level(location=site, name="Aqualumen Woodland", hotbar=HOTBAR, initial_storm_ticks=0):
    base = cbw.level_data(location["seed"], name)
    spawn = location["spawn"]
    fx, fy, fz = spawn["feet"]
    inv = [{"Slot": B(s), "id": S(n), "count": I(c)} for s, n, c in hotbar]
    player = {
        "Pos": L(6, [fx, fy, fz]), "Motion": L(6, [0.0, 0.0, 0.0]), "Rotation": L(5, [spawn["yaw"], spawn["pitch"]]),
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
        "SpawnX": I(int(fx // 1)), "SpawnY": I(int(fy)), "SpawnZ": I(int(fz // 1)), "SpawnAngle": F(spawn["yaw"]),
        "Time": LG(location["start_daytime"]), "DayTime": LG(location["start_daytime"]), "LastPlayed": LG(1795219200000),
        "raining": B(bool(initial_storm_ticks)), "rainTime": I(initial_storm_ticks), "thundering": B(False), "thunderTime": I(0), "clearWeatherTime": I(location["clear_weather_ticks"]),
        "WanderingTraderSpawnChance": I(25), "WanderingTraderSpawnDelay": I(24000),
        "BorderCenterX": (6, 0.0), "BorderCenterZ": (6, 0.0), "BorderSize": (6, 59999968.0), "BorderSafeZone": (6, 5.0),
        "BorderDamagePerBlock": (6, 0.2), "BorderWarningBlocks": (6, 5.0), "BorderWarningTime": (6, 15.0),
        "BorderSizeLerpTime": LG(0), "BorderSizeLerpTarget": (6, 59999968.0),
        "DataPacks": C({"Enabled": L(8, ["vanilla"]), "Disabled": L(8, ["bundle", "trade_rebalance"])}),
        "enabled_features": L(8, ["minecraft:vanilla"]),
        "GameRules": C({}),  # every rule at its vanilla default (daylight and weather cycles, mob spawning on)
        "Player": C(player),
    })
    return b"\x0a\x00\x00" + payload(10, {"Data": C(d)})


def main():
    out = Path(sys.argv[1]) / "Aqualumen-Woodland"
    out.mkdir(parents=True, exist_ok=False)
    with gzip.GzipFile(out / "level.dat", "wb", mtime=0, compresslevel=9) as g:
        g.write(level())
    print(out / "level.dat")


if __name__ == "__main__":
    main()
