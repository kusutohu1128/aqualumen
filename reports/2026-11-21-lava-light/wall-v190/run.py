"""Use the mixed-scene runner on a second private display and new evidence directory."""

import importlib.util
import os
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
tool = here.parent / "runtime-v190/run.py"
spec = importlib.util.spec_from_file_location("lava_native_chamber", tool)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
# This run only measures F2 pixel values. Its X server, clone and input have
# private identities; the source save is still locked and hashed during copy.
# Reserve the private optical runner separately from timed GPU experiments.
runner.base.LOCK = Path("/tmp/aqualumen-private-lava-wall-stills.lock")
runner.here = here
runner.PRIVATE_DISPLAY_MIN = 201
sealed = len(sys.argv) > 2 and (sys.argv[2].startswith("sealed-") or sys.argv[2] == "compact-bounce-r5")
if sealed:
    # A pool replaces the top layer of this suspended test room. Give it a
    # real bed so that sources removed in a later stage leave no flowing lava.
    runner.scene.basin.room = [
        "fill 198 170 359 209 171 367 minecraft:smooth_stone",
        *runner.scene.basin.room,
    ]
    original_stages = runner.scene.stage_functions

    def checked_stages(names):
        functions = original_stages(names)
        guards = [
            f"if block {x} 171 {z} minecraft:smooth_stone"
            for x in range(200, 205) for z in range(359, 364)
        ]
        for i in range(len(names)):
            line = functions[f"c{i}"][-1]
            functions[f"c{i}"][-1] = line.replace(" if entity ", " " + " ".join(guards) + " if entity ")
        return functions

    runner.scene.stage_functions = checked_stages
    if sys.argv[2].startswith("sealed-glass-"):
        # A real translucent display entity in front of the same illuminated
        # wall. Count and locate it independently at both camera handshakes.
        scene = runner.scene
        for label, light in (("open-lit", 1), ("glass-lit", 1), ("glass-dark", 0), ("open-dark", 0)):
            scene.STAGE_TABLE[label] = (False, light, False, False)
        sealed_stages = scene.stage_functions
        def glass_stages(names):
            functions = sealed_stages(names)
            tag = "aql_translucent_wall"
            entity = "@e[type=minecraft:block_display,tag=" + tag + "]"
            pose = ("@e[type=minecraft:block_display,tag=" + tag
                    + ",x=203.25,y=173.65,z=364.05,distance=..0.02,"
                      "nbt={block_state:{Name:\"minecraft:white_stained_glass\"}}]")
            for i, name in enumerate(names):
                commands = ["kill " + entity]
                expected = "unless entity " + entity
                if name.startswith("glass-"):
                    commands.append('summon minecraft:block_display 203.25 173.65 364.05 '
                                    '{Tags:["aql_translucent_wall"],block_state:{Name:"minecraft:white_stained_glass"}}')
                    expected = "if entity " + pose
                functions[f"s{i}"] = commands + functions[f"s{i}"]
                check = functions[f"c{i}"][-1].replace(
                    "unless entity @e[type=!minecraft:player,",
                    expected + " unless entity @e[type=!minecraft:player,tag=!" + tag + ",")
                assert expected in check
                functions[f"c{i}"][-1] = check
            return functions
        scene.stage_functions = glass_stages
    if sys.argv[2].startswith("sealed-field"):
        runner.base.LOCK = Path("/tmp/aqualumen-private-lava-field-stills.lock")
        runner.PRIVATE_DISPLAY_MIN = 210
        runner.SCREEN = (640, 360)
    elif sys.argv[2].startswith("sealed-link"):
        runner.base.LOCK = Path("/tmp/aqualumen-private-lava-link-stills.lock")
        runner.PRIVATE_DISPLAY_MIN = 221
if "--backend" in sys.argv and sys.argv[sys.argv.index("--backend") + 1] == "llvmpipe":
    # The software fallback is a separate real-game optical check with a reduced
    # framebuffer. Hardware frame rates and startup data come from NVIDIA runs.
    runner.SCREEN = (640, 360)
    os.environ.setdefault("LP_NUM_THREADS", "6")
runner.scene.STAGE_TABLE["dark-pillar"] = (True, 0, False, False)
if sealed or os.environ.get("AQUALUMEN_LAVA_STUDY_SETTLE") == "1":
    # Cross the same source with and without a pillar in both directions. Delay
    # READY until the client has had time to rebuild its section mesh.
    runner.scene.STAGE_TABLE["repeat-one-pillar"] = (True, 1, False, False)
    runner.scene.STAGE_TABLE["repeat-one-open"] = (False, 1, False, False)
    runner.scene.PERIOD, runner.scene.READY_AT, runner.scene.STILL_AT = 400, 155, 320
    if hasattr(runner.scene, "configure"):
        base_configure = runner.scene.configure
        def configure(period):
            base_configure(period)
            if period == 400:
                runner.scene.READY_AT, runner.scene.STILL_AT = 155, 320
        runner.scene.configure = configure
        if "--period-ticks" not in sys.argv:
            sys.argv.extend(["--period-ticks", "400"])
        if "--size" not in sys.argv:
            sys.argv.extend(["--size", "%dx%d" % runner.SCREEN])
original_errors = runner.error_lines


def link_errors(text, allow):
    errors = original_errors(text, allow)
    if (
        "Error encountered when linking program" in text
        or "Internal error: assembly compile error" in text
    ):
        errors.append("The GPU driver rejected the active shader program")
    return errors


runner.error_lines = link_errors
runner.main()
