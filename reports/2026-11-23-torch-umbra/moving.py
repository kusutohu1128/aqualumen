"""Compare two unchanged packs in a private Minecraft scene with a moving hand light and cow."""

import importlib.util
import sys

from candidate import HERE, ROOT, BASE, build

ANIMALS = HERE.parent / "2026-11-21-animal-light"
PROFILE = HERE.parent / "2026-11-22-gpu-profile"
sys.path.insert(0, str(PROFILE))
import run as guarded

COMPILER = ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar"
CACHE = guarded.BUILD / "driver-cache"
A, B = 405.9, 407.3
OAK_BASE = (406, 151, -410)
HAND = {
    "hand-dark": (A, False, False),
    "hand-left-clear": (A, True, False),
    "hand-left-oak": (A, True, True),
    "hand-right-oak": (B, True, True),
    "hand-right-clear": (B, True, False),
    "hand-right-dark": (B, False, False),
}
STAGES = ["both-empty", "both-west", "both-east", "both-restored", *HAND, "walk", "walk-cleared"]


class MovingScene:
    def __init__(self, animals):
        self.base = animals
        self.STAGE_TABLE = {**animals.STAGE_TABLE, **HAND}

    def __getattr__(self, attr):
        return getattr(self.base, attr)

    def self_test(self, names):
        assert names == STAGES
        assert self.PERIOD - self.STILL_AT > 28

    def geometry(self, names):
        scene = self.base.geometry([n for n in names if n not in HAND])
        scene.update(hand=HAND, cameraYZ=[151, -407.25], yawPitch=[180, 4],
                     oakBase=OAK_BASE, oakHeight=2, crossingTicks=24)
        return scene

    def datapack(self, names):
        # Reuse the original cow, room and moving-animal controls. Give each hand
        # stage an unlit, empty room before setting its exact torch and oak.
        for name in HAND:
            self.base.STAGE_TABLE[name] = (False, False, None, "white_concrete", True, 18000)
        files = self.base.datapack(names)
        directory = "data/animal/function/"
        for index, name in enumerate(names):
            key = directory + f"s{index}.mcfunction"
            stage = files[key].splitlines()
            if name not in HAND:
                continue
            x, lit, oak = HAND[name]
            log = "oak_log" if oak else "air"
            item = "torch" if lit else "air"
            t = stage.index(f"tp {self.PLAYER} {self.POSE}")
            stage[t:t+1] = [f"tp {self.PLAYER} {x} 151 -407.25 180 4",
                            f"item replace entity {self.PLAYER} weapon.mainhand with {item}",
                            f"fill 406 151 -410 406 152 -410 {log}"]
            if name == "hand-left-oak":
                start = self.STILL_AT + 3
                # Each actual 20 Hz server position has a render-interpolated camera in between.
                for step in range(1, 25):
                    new_x = A + (B - A) * step / 24
                    stage.append(f"schedule function animal:slide{step} {start+step}t replace")
                    files[directory + f"slide{step}.mcfunction"] = (
                        f"tp {self.PLAYER} {new_x:.6f} 151 -407.25 180 4\n"
                        f"execute positioned {new_x:.6f} 151 -407.25 if entity "
                        f"@a[name={self.PLAYER},distance=..0.01] run say AQ_HAND_STEP_{step}\n"
                    )
            files[key] = "\n".join(stage) + "\n"
            # The client/server may represent yaw 180 as -180; Minecraft wraps both ends.
            pose = (f"positioned {x} 151 -407.25 if entity @a[name={self.PLAYER},distance=..0.04,"
                    "x_rotation=3.95..4.05,y_rotation=179.95..-179.95]")
            check = (f"if block 406 151 -410 {log} if block 406 152 -410 {log} "
                     f"if block 406 152 -413 white_concrete if block {self.base.WARM} air "
                     f"if block {self.base.SOUL} air unless entity {self.SELECT} "
                     f"{'if' if lit else 'unless'} items entity {self.PLAYER} weapon.mainhand "
                     f"{'minecraft:torch' if lit else '*'} unless items entity {self.PLAYER} weapon.offhand * {pose}")
            for phase in ("v", "e"):
                guard = directory + f"{phase}{index}.mcfunction"
                lines = files[guard].splitlines()
                lines[2] = f"execute if score #t aq_room matches 18000 {check} run scoreboard players set #ok aq_room 1"
                files[guard] = "\n".join(lines) + "\n"
        return files


def main():
    op, label = sys.argv[1:]
    candidate = build()
    pack, expected = {
        "moving-reference": (BASE, "fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"),
        "moving-umbra": (candidate, "1b4ef25c23a9948ae0069e201f0de4fb14276e44869647a2215e9c0b26606a85"),
        "moving-umbra-r2": (candidate.parent/"Aqualumen-1.9.0-preview.12.zip",
                            "be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2"),
    }[label]
    assert guarded.sha(pack) == expected
    if op == "play":
        fixed = {"backend": "vgl", "size": "1280x720", "settle": "1", "shot-gap": ".15",
                 "period-ticks": "220", "glcache": str(CACHE), "compiler-mod": str(COMPILER),
                 "stages": ",".join(STAGES)}
        guarded.launch(pack, label, "off", fixed, HERE, MovingScene)
    elif op == "record":
        spec = importlib.util.spec_from_file_location("cow_walk", ANIMALS / "walk.py")
        walk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(walk)
        walk.capture(pack, label, COMPILER, CACHE, out_root=HERE,
                     command=[sys.executable, __file__, "play", label])
    else:
        raise ValueError(op)


if __name__ == "__main__":
    main()
