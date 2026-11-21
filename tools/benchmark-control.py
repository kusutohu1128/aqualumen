"""Prepare and control the opt-in benchmark inside the isolated Aqualumen Lab.

The mod polls a local file; this tool never sends network/chat commands and never
launches/kills Minecraft. Launch the generated world with --quickPlaySingleplayer
WORLD after installing the instrumentation JAR. Requests are acknowledged through
status.json. Existing saves are never replaced.

For a quality-review shot sequence, use existing controls, e.g.:
start --scenes ocean-day ocean-dusk ocean-night ocean-rain coast-day underwater
moving-view cave-water glass-layers --warmup 10 --sample 10
Local-light fixture (exact V2 UUID + seed 308060 only; temporary, restored to AIR):
start --scenes lamp-day-off lamp-day-torch lamp-day-wall lamp-day-wall-off lamp-night-off
lamp-night-torch lamp-night-soul lamp-night-both lamp-night-wall lamp-night-wall-off
lamp-night-water lamp-night-moving lamp-day-canopy lamp-night-glass lamp-night-glass-off
lamp-night-walk lamp-night-walk-east lamp-night-walk-west --warmup 20 --sample 10
(lamp-night-walk: 8 s translating route; --sample >= 9. For a clip run it alone with the
existing capture_motion=true native PNG transport, or water_frame_clip=true at 960x540.)
Carried-light (hand-held) fixture, same exact V2 UUID + seed guard; sealed room in the same reserved
AIR box, creative first-person driver with real torch/soul_torch stacks (whole driver inventory must
be empty; stacks, recipes/criteria and game mode are journaled and restored per scene):
start --scenes lamp-hand-empty lamp-hand-main lamp-hand-off lamp-hand-soul lamp-hand-both
lamp-hand-pillar lamp-hand-pillar-empty lamp-hand-hidden lamp-hand-hidden-off lamp-hand-hidden-empty
lamp-hand-walk lamp-hand-walk-empty lamp-hand-putaway --warmup 20 --sample 10
(lamp-hand-walk*/putaway: 8 s route/schedule, --sample >= 9; any lamp-hand scene may be filmed
with water_frame_clip=true at 960x540 or capture_motion=true.)
lamp-hand scenes additionally require --carried-light-test and --game naming the private duplicate
<Aqualumen Lab instance>/carried-matrix-<random>/Aqualumen Lab/minecraft (symlink-free, distinct from
and never inside the untouched <instance>/minecraft, world files not hard-linked); the request then names
both games and the mod re-proves them plus the AqualumenOptics player before any change or equip.
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
OPTIONAL_SCENARIOS = ["coast-rain-close", "cave-water", "glass-layers", "nether-view", "end-view", "ocean-sun-day", "ocean-sun-dusk"]
FIXTURE_WORLD = "AqualumenNaturalV2"
FIXTURE_WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
OPAQUE_SCENARIOS = [f"opaque-{distance}-{variant}" for distance in ("near", "far")
                    for variant in ("magenta", "lime", "open-magenta", "open-lime")]
AIR_SHADOW_SCENARIOS = ["air-shadow-backlit", "air-sunlit-front", "air-backlit-open"]
GROUND_SHADOW_SCENARIOS = ["ground-noon", "ground-evening", "ground-low-sun", "ground-sun-motion", "ground-camera-motion"]
UNDERWATER_UP_SCENARIOS = ["underwater-up-near", "underwater-up-deep", "underwater-up-tilt", "underwater-up-moving", "underwater-shore-moving", "underwater-shore-view"]
LOCAL_LIGHT_SCENARIOS = ["lamp-day-off", "lamp-day-torch", "lamp-day-wall", "lamp-day-wall-off",
                         "lamp-night-off", "lamp-night-torch", "lamp-night-soul", "lamp-night-both", "lamp-night-wall",
                         "lamp-night-wall-off", "lamp-night-water", "lamp-night-moving",
                         "lamp-day-canopy", "lamp-night-glass", "lamp-night-glass-off",
                         "lamp-night-walk", "lamp-night-walk-east", "lamp-night-walk-west"]
HAND_LIGHT_SCENARIOS = ["lamp-hand-empty", "lamp-hand-main", "lamp-hand-off", "lamp-hand-soul", "lamp-hand-both",
                        "lamp-hand-pillar", "lamp-hand-pillar-empty", "lamp-hand-hidden", "lamp-hand-hidden-off",
                        "lamp-hand-hidden-empty", "lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway"]
HAND_LIGHT_SEQUENCE_SCENARIOS = ["lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway"]
LOCAL_LIGHT_SCENARIOS += HAND_LIGHT_SCENARIOS
LOCAL_LIGHT_MIN_WARMUP = 15
LOCAL_LIGHT_WALK_SCENARIOS = ["lamp-night-walk"]
LOCAL_LIGHT_WALK_MIN_SAMPLE = 9
WATER_FIXTURE_SCENARIOS = UNDERWATER_UP_SCENARIOS + ["coast-rain-close"] + LOCAL_LIGHT_SCENARIOS
OPTIONAL_SCENARIOS += OPAQUE_SCENARIOS + AIR_SHADOW_SCENARIOS + GROUND_SHADOW_SCENARIOS + UNDERWATER_UP_SCENARIOS + LOCAL_LIGHT_SCENARIOS


def game_path(value):
    path = value.resolve()
    if path.name not in {"minecraft", ".minecraft"} or path.parent.name != "Aqualumen Lab":
        raise ValueError("Only the isolated Aqualumen Lab game directory is accepted")
    if not path.is_dir():
        raise ValueError("Game directory does not exist")
    return path


CARRIED_MATRIX = re.compile(r"carried-matrix-[A-Za-z0-9][A-Za-z0-9_-]{5,63}")
CARRIED_OPT_IN = {"carried_light_test": "private-duplicate-v1"}


def _real_directory(path):
    return path.is_dir() and not path.is_symlink()


def _unshared(path):
    if path.is_symlink():
        raise ValueError(f"Symbolic link inside the TEST world: {path}")
    if path.is_file() and os.lstat(path).st_nlink != 1:
        raise ValueError(f"Hard-linked TEST world file shared with another path: {path}")


def carried_test_game(raw_game, world):
    """Independently identify the private duplicated carried-light TEST game; return request opt-in values."""
    if not re.fullmatch(r"AqualumenNatural[A-Za-z0-9_.-]*", world) or ".." in world:
        raise ValueError("Unexpected carried-light world folder")
    absolute = Path(os.path.abspath(raw_game))
    walk = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        walk = walk / part
        if walk.is_symlink():
            raise ValueError(f"Carried-light TEST game path crosses a symbolic link: {walk}")
    if not absolute.is_dir() or Path(os.path.realpath(absolute)) != absolute:
        raise ValueError("Carried-light TEST game path is missing or not canonical")
    lab, matrix = absolute.parent, absolute.parent.parent
    instance = matrix.parent
    if (absolute.name != "minecraft" or lab.name != "Aqualumen Lab" or not CARRIED_MATRIX.fullmatch(matrix.name)
            or instance.name != "Aqualumen Lab"):
        raise ValueError("Carried-light scenes require <Aqualumen Lab instance>/carried-matrix-<random>/Aqualumen Lab/minecraft")
    for directory in (absolute, lab, matrix, instance):
        if not _real_directory(directory):
            raise ValueError(f"Not a real directory: {directory}")
    original = instance / "minecraft"
    if not _real_directory(original) or Path(os.path.realpath(original)) != original:
        raise ValueError("Untouched original <instance>/minecraft not found as a real directory")
    if os.path.samefile(original, absolute) or absolute.is_relative_to(original) or original.is_relative_to(absolute):
        raise ValueError("Carried-light TEST game is the original game")
    saves = absolute / "saves"
    world_dir = saves / world
    if not _real_directory(saves) or not _real_directory(world_dir) or Path(os.path.realpath(world_dir)) != world_dir:
        raise ValueError("Carried-light TEST world is missing or a symbolic link")
    original_world = original / "saves" / world
    if original_world.exists() and os.path.samefile(original_world, world_dir):
        raise ValueError("Carried-light TEST world is the original world")
    _unshared(world_dir / "level.dat")
    _unshared(world_dir / "aqualumen-world.properties")
    for sub in ("region", "entities", "poi", "playerdata", "data"):
        directory = world_dir / sub
        if not directory.exists() and not directory.is_symlink():
            continue
        if not _real_directory(directory):
            raise ValueError(f"TEST world subdirectory is a symbolic link: {directory}")
        for item in directory.iterdir():
            _unshared(item)
    return dict(CARRIED_OPT_IN, carried_light_test_game=str(absolute), carried_light_original_game=str(original))


def properties(path):
    return dict(line.strip().split("=", 1) for line in path.read_text().splitlines() if line.strip() and not line.startswith("#"))


def write_atomic(path, text):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def validate_fixture_world(config, scenes):
    if any(scene in OPAQUE_SCENARIOS + AIR_SHADOW_SCENARIOS + GROUND_SHADOW_SCENARIOS for scene in scenes) and (
            config.get("world") != FIXTURE_WORLD or config.get("world_id") != FIXTURE_WORLD_ID):
        raise ValueError("Opaque fixtures require the exact disposable AqualumenNaturalV2 world UUID")
    if any(scene in WATER_FIXTURE_SCENARIOS for scene in scenes) and (
            config.get("world") != FIXTURE_WORLD or config.get("world_id") != FIXTURE_WORLD_ID):
        raise ValueError("Water fixture views require the exact disposable AqualumenNaturalV2 world UUID")
    if any(scene in LOCAL_LIGHT_SCENARIOS for scene in scenes) and (
            config.get("world") != FIXTURE_WORLD or config.get("world_id") != FIXTURE_WORLD_ID):
        raise ValueError("Local-light fixtures require the exact disposable AqualumenNaturalV2 world UUID")


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
    carried = {}
    if args.action == "start":
        # Reject before creating a control directory or writing any request.
        validate_fixture_world(config, args.scenes)
        hand = any(scene in HAND_LIGHT_SCENARIOS for scene in args.scenes)
        if hand and not args.carried_light_test:
            raise ValueError("lamp-hand scenes need --carried-light-test inside the private duplicated TEST game")
        if args.carried_light_test and not hand:
            raise ValueError("--carried-light-test is only for lamp-hand scenes")
        if hand:
            carried = carried_test_game(args.game, config.get("world", ""))
        if any(scene in LOCAL_LIGHT_SCENARIOS for scene in args.scenes) and args.warmup < LOCAL_LIGHT_MIN_WARMUP:
            raise ValueError("Local-light scenes need --warmup >= 15 for chunk mesh and block-light updates")
        if any(scene in LOCAL_LIGHT_WALK_SCENARIOS for scene in args.scenes) and args.sample < LOCAL_LIGHT_WALK_MIN_SAMPLE:
            raise ValueError("lamp-night-walk needs --sample >= 9 (8 s route plus a held end pose before capture)")
        if any(scene in HAND_LIGHT_SEQUENCE_SCENARIOS for scene in args.scenes) and args.sample < LOCAL_LIGHT_WALK_MIN_SAMPLE:
            raise ValueError("lamp-hand walk/putaway need --sample >= 9 (8 s route/schedule plus a held, settled final state)")
        if any(scene in WATER_FIXTURE_SCENARIOS for scene in args.scenes):
            marker = properties(game / "saves" / FIXTURE_WORLD / "aqualumen-world.properties")
            if (marker.get("world_id") != FIXTURE_WORLD_ID or marker.get("seed") != "308060" or
                    marker.get("schema") != "2" or marker.get("generator") != "minecraft:noise/overworld"):
                raise ValueError("Water fixture views require the exact approved V2 UUID/seed/noise marker")
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
        values.update(carried)
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
    start.add_argument("--carried-light-test", action="store_true",
                       help="Opt in to lamp-hand scenes inside the private duplicated TEST game only")
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
