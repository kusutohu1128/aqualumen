"""Independent read-back of a Woodland world folder or ZIP: decode level.dat with the repo's bounded NBT reader and assert the contract.
Usage: python3 -I validate_level.py <world-dir | zip> [out.json]
"""
import gzip, importlib.util, io, json, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE.parents[2] / "tools/audit-fixture-air.py")
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
site = json.loads((HERE / "site.json").read_text())
src = Path(sys.argv[1])
if src.suffix == ".zip":
    z = zipfile.ZipFile(src)
    names = sorted(z.namelist())
    read = lambda n: z.read(n)
    top = {n.split("/")[0] for n in names}
else:
    names = sorted(str(p.relative_to(src.parent)) for p in src.rglob("*") if p.is_file())
    read = lambda n: (src.parent / n).read_bytes()
    top = {src.name}
assert len(top) == 1, top
root = next(iter(top))
assert names == [f"{root}/level.dat"], names  # nothing but level.dat: no region, playerdata, datapacks or markers
data = audit.NBT(gzip.decompress(read(f"{root}/level.dat"))).root()["Data"]
p = data["Player"]
wg = data["WorldGenSettings"]
ow = wg["dimensions"]["minecraft:overworld"]["generator"]
checks = {
    "seed": wg["seed"] == site["seed"], "generate_features": wg["generate_features"] == 1, "bonus_chest": wg["bonus_chest"] == 0,
    "overworld_noise": ow["type"] == "minecraft:noise" and ow["settings"] == "minecraft:overworld"
                       and ow["biome_source"] == {"type": "minecraft:multi_noise", "preset": "minecraft:overworld"},
    "survival": data["GameType"] == 0 and p["playerGameType"] == 0, "peaceful": data["Difficulty"] == 0,
    "cheats_off": data["allowCommands"] == 0, "not_hardcore": data["hardcore"] == 0,
    "gamerules_default": data["GameRules"] == {}, "no_datapack_beyond_vanilla": data["DataPacks"]["Enabled"] == ["vanilla"],
    "time": data["DayTime"] == site["start_daytime"], "weather_clear_window": data["clearWeatherTime"] == site["clear_weather_ticks"] and data["raining"] == 0,
    "pos": p["Pos"] == site["spawn"]["feet"], "rotation": [round(v, 3) for v in p["Rotation"]] == [round(site["spawn"]["yaw"], 3), site["spawn"]["pitch"]],
    "not_flying": p["abilities"]["flying"] == 0 and p["abilities"]["mayfly"] == 0 and p["abilities"]["instabuild"] == 0,
    "no_uuid": "UUID" not in p, "no_test_marker": not any("aqualumen-world" in n for n in names),
}
inv = {i["Slot"]: (i["id"], i["count"]) for i in p["Inventory"]}
out = {"world": src.name, "checks": checks, "inventory": inv, "level_keys": sorted(data), "ok": all(checks.values())}
print(json.dumps(out, indent=1))
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
sys.exit(0 if out["ok"] else 1)
