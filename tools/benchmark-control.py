"""Prepare and control the opt-in benchmark inside the isolated Aqualumen Lab.

The mod polls a local file; this tool never sends network/chat commands and never
launches/kills Minecraft. Launch the generated world with --quickPlaySingleplayer
WORLD after installing the instrumentation JAR. Requests are acknowledged through
status.json. Existing saves are never replaced.

For a quality-review shot sequence, use existing controls, e.g.:
start --scenes ocean-day ocean-dusk ocean-night ocean-rain coast-day underwater
moving-view cave-water glass-layers --warmup 10 --sample 10
Frame timings remain observations; the screenshots require visual review.
"""
import argparse
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

DEFAULT_GAME = Path.home() / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft"
SCENARIOS = ["ocean-day", "coast-day", "river-day", "ocean-dusk", "ocean-night", "ocean-rain", "underwater", "moving-view", "boat-contact", "chunk-traversal"]
OPTIONAL_SCENARIOS = ["cave-water", "glass-layers", "nether-view", "end-view"]
FIXTURE_WORLD = "AqualumenNaturalV2"
FIXTURE_WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
OPAQUE_SCENARIOS = [f"opaque-{distance}-{variant}" for distance in ("near", "far")
                    for variant in ("magenta", "lime", "open-magenta", "open-lime")]
AIR_SHADOW_SCENARIOS = ["air-shadow-backlit", "air-sunlit-front", "air-backlit-open"]
OPTIONAL_SCENARIOS += OPAQUE_SCENARIOS + AIR_SHADOW_SCENARIOS


def game_path(value):
    path = value.resolve()
    if path.name not in {"minecraft", ".minecraft"} or path.parent.name != "Aqualumen Lab":
        raise ValueError("Only the isolated Aqualumen Lab game directory is accepted")
    if not path.is_dir():
        raise ValueError("Game directory does not exist")
    return path


def properties(path):
    return dict(line.strip().split("=", 1) for line in path.read_text().splitlines() if line.strip() and not line.startswith("#"))


def write_atomic(path, text):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def validate_fixture_world(config, scenes):
    if any(scene in OPAQUE_SCENARIOS + AIR_SHADOW_SCENARIOS for scene in scenes) and (
            config.get("world") != FIXTURE_WORLD or config.get("world_id") != FIXTURE_WORLD_ID):
        raise ValueError("Opaque fixtures require the exact disposable AqualumenNaturalV2 world UUID")


def prepare(game, args):
    if not re.fullmatch(r"AqualumenNatural[A-Za-z0-9_.-]*", args.world):
        raise ValueError("Expected an AqualumenNatural world folder name")
    world = game / "saves" / args.world
    marker = properties(world / "aqualumen-world.properties")
    uuid.UUID(marker["world_id"])
    if marker["generator"] != "minecraft:noise/overworld" or not (world / "level.dat").exists():
        raise ValueError("Expected generated natural world with marker and level.dat")
    pack = args.pack.resolve()
    if pack.parent != (game / "shaderpacks").resolve() or not pack.is_file() or pack.suffix != ".zip":
        raise ValueError("Pack must be an installed ZIP in this instance's shaderpacks")
    values = {"schema": "2", "world": args.world, "world_id": marker["world_id"],
              "expected_pack": pack.name, "expected_pack_sha256": hashlib.sha256(pack.read_bytes()).hexdigest(),
              "width": "2560", "height": "1440", "render_chunks": "12", "simulation_chunks": "6"}
    config = game / "config"
    config.mkdir(exist_ok=True)
    write_atomic(config / "aqualumen-benchmark.properties", "\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    write_atomic(config / "aqualumen-benchmark.enabled", "Local natural-world benchmark enabled by benchmark-control.py\n")
    print(json.dumps(values, indent=2))


def request(game, args):
    config = properties(game / "config/aqualumen-benchmark.properties")
    if args.action == "start":
        # Reject before creating a control directory or writing any request.
        validate_fixture_world(config, args.scenes)
    control = game / "aqualumen-benchmark"
    control.mkdir(exist_ok=True)
    if (control / "request.properties").exists():
        raise ValueError("A request is already pending; wait for acknowledgement")
    values = {"request_id": str(uuid.uuid4()), "action": args.action, "world_id": config["world_id"]}
    if args.action == "start":
        run_id = args.run_id or time.strftime("natural-%Y%m%d-%H%M%S")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", run_id):
            raise ValueError("Invalid run identifier")
        if (control / "runs" / run_id).exists():
            raise ValueError("Run identifier already exists; records are never overwritten")
        values.update(run_id=run_id, scenarios=",".join(args.scenes), warmup_seconds=str(args.warmup), sample_seconds=str(args.sample), auto_quit=str(args.auto_quit).lower())
    write_atomic(control / "request.properties", "\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    print(json.dumps(values, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--world", required=True)
    prepare_parser.add_argument("--pack", required=True, type=Path)
    start = sub.add_parser("start")
    start.add_argument("--run-id")
    start.add_argument("--scenes", nargs="+", choices=SCENARIOS + OPTIONAL_SCENARIOS, default=SCENARIOS)
    start.add_argument("--warmup", type=float, default=20)
    start.add_argument("--sample", type=float, default=30)
    start.add_argument("--auto-quit", action="store_true")
    sub.add_parser("stop")
    sub.add_parser("quit")
    sub.add_parser("status")
    args = parser.parse_args()
    game = game_path(args.game)
    if args.action == "prepare":
        prepare(game, args)
    elif args.action == "status":
        status = game / "aqualumen-benchmark/status.json"
        print(status.read_text() if status.exists() else json.dumps({"state": "uninitialized", "note": "No mod acknowledgement yet"}))
    else:
        if args.action == "start" and (args.warmup < 5 or not 5 <= args.sample <= 300):
            raise ValueError("Warmup must be >=5s, sample must be 5..300s")
        request(game, args)


if __name__ == "__main__":
    main()
