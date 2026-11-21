"""Run the existing native screenshot and geometry checks in the independent window fixture."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("window_fixture", HERE / "fixture.py")
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)
sys.path.insert(0, str(HERE.parents[1] / "2026-11-21-indirect-light"))
import capture as runner

window.install(runner.F)
f = runner.F
runner.HERE = HERE
runner.MUTABLE = [f.EAST_BOX, f.LAMP_BOX, f.FIRST_BOX, f.SECOND_BOX]
runner.PERIOD, runner.CHECK, runner.DWELL = 112, 40, 1.05
base_datapack = runner.datapack


def build(roles):
    files = base_datapack(roles)
    root = f"data/{runner.NS}/function/"
    # Replacing either half of a door can drop an item from its neighbour.
    # The empty-room guard includes dropped items, so disable those in this clone.
    files[root + "start.mcfunction"] += "gamerule doTileDrops false\n"
    for index in range(len(roles)):
        path = f"data/{runner.NS}/function/s{index}.mcfunction"
        marker = runner.fill(f.EAST_BOX, f.EAST[roles[index]])
        clear = ["setblock " + runner.w(cell) + " minecraft:air" for cell in (window.UPPER, window.LOWER)]
        assert files[path].count(marker) == 1
        files[path] = files[path].replace(marker, "\n".join(clear + [marker]))
        name = roles[index]
        confirm = root + f"c{index}.mcfunction"
        for cell, block in [(window.UPPER, f.LAMP[name]), (window.LOWER, f.EAST[name])]:
            files[confirm] += f"execute unless block {runner.w(cell)} {block} run say DOOR_STATE_MISMATCH {name} {cell}\n"
    return files


runner.datapack = build
runner.plan = lambda roles: dict(
    origin=f.ORIGIN, receiver=f.POSES["receiver"], lamp=window.LAMP, lower=window.LOWER,
    upper=window.UPPER, roles={role: [f.EAST[role], f.LAMP[role]] for role in roles},
    sampleWallPoints=f.RECEIVERS, reservedCellCount=f.CELLS,
)
if sys.argv[1:] == ["--dry-run"]:
    files = runner.datapack(f.ROLE_NAMES)
    runner.check_datapack(files, f.ROLE_NAMES)
    runner.simulate(files, f.ROLE_NAMES)
    print("6 states, %s reserved cells per state, positions and camera verified" % f.CELLS)
else:
    runner.main(sys.argv)
