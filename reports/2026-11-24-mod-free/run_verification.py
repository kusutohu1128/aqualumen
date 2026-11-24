"""Mod-free preview-14 in-game verification.

Six private-client launches through the reviewed gpu-profile runner
(reports/2026-11-22-gpu-profile/run.py :: launch), order A B C C B A:
  A = preview 13 pack + lighting compiler 0.3.0
  B = preview 14 pack, compiler jar removed before launch
  C = preview 14 pack + lighting compiler 0.3.0

Each launch covers the gp-density birch-4 fixture (4 placed torches in the
birch forest) plus four lava-study stages, merged into one stage loop by
MergedScene: animal:/aqlava: namespaces coexist, only animal: start is
triggered, and the stage chain is patched at the two namespace borders.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GP = ROOT / "reports/2026-11-22-gpu-profile"
TD = ROOT / "reports/2026-11-23-torch-density"
AL = ROOT / "reports/2026-11-21-animal-light"
LAVA_DIR = ROOT / "reports/2026-11-21-lava-light/runtime-v190"

sys.path.insert(0, str(GP))
import run as guarded  # noqa: E402
sys.path.insert(0, str(TD))
import measure_density as md  # noqa: E402  (TorchCounts, analyze)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lava = _load("lava_scene_modfree", LAVA_DIR / "scene.py")
animals = _load("animals_scene_modfree", AL / "scene.py")

BIRCH = ["birch-4"]
LAVA = ["lava1-open", "lava9-open", "torch-lava9-open", "lava9-pillar"]
STAGES = BIRCH + LAVA
LAVA_PLAYER = lava.PLAYER  # 'AqualumenLava' -> rewritten to the Optics player


class MergedScene:
    """One stage loop over TorchCounts birch stages then lava-study stages."""

    PLAYER = animals.PLAYER
    PLAYER_UUID = animals.PLAYER_UUID
    EVENT_RE = animals.EVENT_RE

    def __init__(self, rooms):
        assert rooms is animals or rooms.__name__ in ("scene", "animals_scene_modfree")
        self.rooms = animals
        self.torch = md.TorchCounts(animals)
        self.STAGE_TABLE = {n: ("torch", n) for n in BIRCH}
        self.STAGE_TABLE.update({n: lava.STAGE_TABLE[n] for n in LAVA})
        self.PERIOD = self.READY_AT = self.STILL_AT = None

    def configure(self, period):
        for mod in (animals, lava):
            mod.PERIOD = period
            mod.READY_AT = period // 5
            mod.STILL_AT = period * 17 // 20
        self.PERIOD = period
        self.READY_AT = period // 5
        self.STILL_AT = period * 17 // 20

    def self_test(self, names):
        assert names and len(set(names)) == len(names)
        assert all(n in self.STAGE_TABLE for n in names)

    def _patch_schedule(self, text, frm, to, period):
        pattern = r"schedule function %s \d+t replace" % re.escape(frm)
        replacement = "schedule function %s %dt replace" % (to, period)
        out, count = re.subn(pattern, replacement, text)
        assert count == 1, (frm, to, count)
        return out

    def datapack(self, names):
        self.self_test(names)
        torch_names = [n for n in names if n in BIRCH]
        lava_names = [n for n in names if n in LAVA]
        files = dict(self.torch.datapack(torch_names)) if torch_names else {}
        lfiles = dict(lava.datapack(lava_names)) if lava_names else {}
        lfiles = {k: v.replace(LAVA_PLAYER, self.PLAYER) for k, v in lfiles.items()}
        period = self.PERIOD
        # Lava checks need daytime == lava.TIME and gamemode=creative (their
        # pose_selector requires it); birch stages leave the player in
        # spectator, so each lava stage function re-asserts both at stage start.
        for i in range(len(lava_names)):
            key = "data/%s/function/s%d.mcfunction" % (lava.NS, i)
            text = lfiles[key]
            lines = text.splitlines()
            assert not any(l.startswith(("time set", "gamemode")) for l in lines)
            lfiles[key] = "time set %d\ngamemode creative %s\n" % (lava.TIME, self.PLAYER) + text
        # Chain borders: last torch stage -> first lava stage; last lava -> first torch.
        if torch_names and lava_names:
            t_last = len(torch_names) - 1
            key = "data/animal/function/s%d.mcfunction" % t_last
            files[key] = self._patch_schedule(files[key], "animal:s0", "%s:s0" % lava.NS, period)
            l_last = len(lava_names) - 1
            key = "data/%s/function/s%d.mcfunction" % (lava.NS, l_last)
            lfiles[key] = self._patch_schedule(lfiles[key], "%s:s0" % lava.NS, "animal:s0", period)
        elif torch_names:
            # Single-namespace fallback: keep TorchCounts' own wrap.
            pass
        files.update(lfiles)
        # One merged tick: run both setups once, trigger only the animal loop.
        files["pack.mcmeta"] = json.dumps({"pack": {"pack_format": 48, "description": "Mod-free preview-14 verification"}})
        files["data/minecraft/tags/function/tick.json"] = json.dumps({"values": ["aqmerge:tick"]})
        files["data/aqmerge/function/tick.mcfunction"] = "\n".join([
            "execute as @a[name=%s,tag=!aq_init] run function animal:setup" % self.PLAYER,
            "execute as @a[name=%s,tag=!%s_init] run function %s:setup" % (self.PLAYER, lava.NS, lava.NS),
            "execute as @a[name=%s,tag=aq_ready,tag=!aq_start] if items entity @s weapon.offhand minecraft:paper run function animal:start" % self.PLAYER,
        ]) + "\n"
        return files

    def geometry(self, names):
        self.self_test(names)
        torch_names = [n for n in names if n in BIRCH]
        lava_names = [n for n in names if n in LAVA]
        out = self.torch.geometry(torch_names) if torch_names else {}
        if lava_names:
            lg = lava.geometry(lava_names)
            out["lava"] = {k: lg[k] for k in ("eye", "target", "yaw", "pitch", "player", "time", "wallZ", "stages")}
        out["stages"] = names
        return out


def scene_factory(rooms):
    return MergedScene(rooms)


def strip_compiler(game, out, mods):
    jar = game / "mods" / "aqualumen-lighting-compiler-0.3.0.jar"
    assert jar.is_file(), jar
    jar.unlink()
    mods["compilerModRemovedBeforeLaunch"] = True
    (out / "compiler-removed.txt").write_text("deleted mods/aqualumen-lighting-compiler-0.3.0.jar before client launch\n")


def fixed_for(stages):
    fixed = dict(backend="vgl", size="2560x1440", settle="1", stages=",".join(stages),
                 glcache=str(guarded.BUILD / "driver-cache"))
    fixed.update({"period-ticks": "800",
                  "compiler-mod": str(ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar")})
    return fixed


P13 = ROOT / "dist" / "Aqualumen-1.9.0-preview.13.zip"
# v2: compile-budget also defines AQUALUMEN_LAVA_AREA_EXACT in shadowcomp2.csh —
# the bounce-exit/areaDiffuse field feeds deferred and the terrain lava-face
# cache, so it must keep the exact area source (v1 lost it -> dimmed lava).
P14 = Path("/tmp/aq-p14/p14-v2.zip")
RUNS = HERE / "runs"

# label -> (pack, strip compiler?). Labels must match the gpu-profiler guard
# regex gp-[a-z0-9-]+ (tools/gpu-profiler-mod/Timers.java opted()).
PLAN = [
    ("gp-mf-a1-p13-compiler", P13, False),
    ("gp-mf-b1-p14-nocompiler", P14, True),
    ("gp-mf-c1-p14-compiler", P14, False),
    ("gp-mf-c2-p14-compiler", P14, False),
    ("gp-mf-b2-p14-nocompiler", P14, True),
    ("gp-mf-a2-p13-compiler", P13, False),
]


def main():
    only = set(sys.argv[1:])
    results = {}
    for label, pack, strip in PLAN:
        if only and label not in only:
            continue
        folder = RUNS / label
        if folder.exists():
            raise FileExistsError(folder)
        fixed = fixed_for(STAGES)
        print("=== launch", label, "pack", pack.name, "strip" if strip else "compiler", flush=True)
        code = 0
        try:
            guarded.launch(pack.resolve(strict=True), label, "on", fixed, RUNS, scene_factory,
                           prepare_extra=strip_compiler if strip else None)
        except SystemExit as exc:
            code = exc.code or 0
            print("=== launch", label, "exited code", code, flush=True)
        except Exception as exc:
            code = -1
            print("=== launch", label, "raised", type(exc).__name__, exc, flush=True)
        results[label] = code
        complete = folder / "complete.json"
        if complete.is_file():
            try:
                md.analyze(folder, pack.resolve(strict=True), True)
                print("=== analyzed", label, flush=True)
            except Exception as exc:
                print("=== analyze", label, "failed:", type(exc).__name__, exc, flush=True)
        else:
            print("=== no complete.json for", label, flush=True)
    print("=== RESULT", json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
