"""Create an isolated vanilla 1.21.1 noise world, without changing existing saves.

Minecraft generates the terrain at first load. The benchmark mod discovers real
ocean, beach and river biomes on the integrated server; no fill commands are used.
A UUID marker identifies this disposable world independently of its level name.
"""
import argparse
import gzip
import json
import struct
import uuid
from pathlib import Path


def string(value):
    raw = value.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def payload(kind, value):
    if kind == 1:
        return struct.pack(">b", value)
    if kind == 3:
        return struct.pack(">i", value)
    if kind == 4:
        return struct.pack(">q", value)
    if kind == 5:
        return struct.pack(">f", value)
    if kind == 6:
        return struct.pack(">d", value)
    if kind == 8:
        return string(value)
    if kind == 9:
        subtype, items = value
        return bytes([subtype]) + struct.pack(">i", len(items)) + b"".join(payload(subtype, x) for x in items)
    if kind == 10:
        return b"".join(bytes([t]) + string(k) + payload(t, v) for k, (t, v) in value.items()) + b"\0"
    raise ValueError(kind)


S = lambda x: (8, x)
I = lambda x: (3, x)
B = lambda x: (1, int(x))
C = lambda x: (10, x)
L = lambda t, x: (9, (t, x))


def level_data(seed, level_name):
    def noise(setting, source):
        return {"type": S("minecraft:noise"), "settings": S("minecraft:" + setting), "biome_source": C(source)}

    dimensions = {
        "minecraft:overworld": C({"type": S("minecraft:overworld"), "generator": C(noise("overworld", {"type": S("minecraft:multi_noise"), "preset": S("minecraft:overworld")}))}),
        "minecraft:the_nether": C({"type": S("minecraft:the_nether"), "generator": C(noise("nether", {"type": S("minecraft:multi_noise"), "preset": S("minecraft:nether")}))}),
        "minecraft:the_end": C({"type": S("minecraft:the_end"), "generator": C(noise("end", {"type": S("minecraft:the_end")}))}),
    }
    player = {
        "Pos": L(6, [0.5, 160.0, 0.5]), "Motion": L(6, [0.0, 0.0, 0.0]), "Rotation": L(5, [0.0, 12.0]),
        "Dimension": S("minecraft:overworld"), "Health": (5, 20.0), "foodLevel": I(20),
        "playerGameType": I(3), "Inventory": L(10, []),
        "abilities": C({"flying": B(True), "mayfly": B(True), "invulnerable": B(True), "instabuild": B(False), "mayBuild": B(False), "flySpeed": (5, 0.05), "walkSpeed": (5, 0.1)}),
    }
    return {
        "DataVersion": I(3955), "version": I(19133), "DragonFight": C({}),
        "Version": C({"Id": I(3955), "Name": S("1.21.1"), "Snapshot": B(False)}),
        "LevelName": S(level_name), "GameType": I(3), "Difficulty": B(0),
        "hardcore": B(False), "allowCommands": B(True), "initialized": B(True),
        "SpawnX": I(0), "SpawnY": I(160), "SpawnZ": I(0), "Time": (4, 6000), "DayTime": (4, 6000),
        "raining": B(False), "thundering": B(False), "rainTime": I(999999), "thunderTime": I(999999),
        "GameRules": C({k: S(v) for k, v in {"doDaylightCycle": "false", "doWeatherCycle": "false", "doMobSpawning": "false", "randomTickSpeed": "0", "sendCommandFeedback": "false", "logAdminCommands": "false"}.items()}),
        "WorldGenSettings": C({"seed": (4, seed), "generate_features": B(True), "bonus_chest": B(False), "dimensions": C(dimensions)}),
        "Player": C(player),
    }


def validate_target(target):
    target = target.resolve()
    if target.parent.name != "saves" or target.parent.parent.name not in {"minecraft", ".minecraft"} or target.parent.parent.parent.name != "Aqualumen Lab":
        raise ValueError("Refusing target outside Aqualumen Lab/minecraft/saves")
    if not target.name.startswith("AqualumenNatural"):
        raise ValueError("World directory must begin with AqualumenNatural")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--seed", type=int, default=308060)
    args = parser.parse_args()
    target = validate_target(args.target)
    data = level_data(args.seed, "Aqualumen Natural Water Lab")
    world_id = str(uuid.uuid4())
    target.mkdir(parents=True, exist_ok=False)
    with gzip.open(target / "level.dat", "wb") as stream:
        stream.write(b"\x0a\x00\x00" + payload(10, {"Data": C(data)}))
    marker = {"schema": "2", "world_id": world_id, "seed": str(args.seed), "generator": "minecraft:noise/overworld", "minecraft": "1.21.1"}
    (target / "aqualumen-world.properties").write_text("\n".join(f"{k}={v}" for k, v in marker.items()) + "\n", encoding="utf-8")
    print(json.dumps({"world": str(target), **marker}, indent=2))


if __name__ == "__main__":
    main()
