"""Real lever -> door interaction capture (ordinary client, vanilla datapack, REAL right mouse clicks).

    python3 capture.py --dry-run                       # CPU only: fixture/datapack/log-parser/input-guard tests
    python3 capture.py <shaderpack.zip> <out-dir-name> # one real run under /tmp/aql-render21-1000.lock

Safety model (same runner skeleton as the indirect-light / continuous-walk captures, nothing is copied from them):
  * exact-UUID / seed private clone of the Lab world; the clone is the only world the client opens; the source world
    tree and the original Lab options/iris/sodium files are hashed before and after (SOURCE WORLD CHANGED -> failure);
  * three normal mods only, no recorder Mod; Iris must select the pack; renderer must be the NVIDIA one;
  * only the window of OUR java PID is ever focused, recorded, clicked or closed.  A click is refused unless
    xdotool reports that window as focused AND under the pointer;
  * the datapack builds the house once and afterwards only watches (see fixture.py): the door and the lever are never
    written again, so every state change comes from the client's right button.

Timeline of one take: client ready -> server READY (house verified, survival player on the floor, pose verified)
-> one harmless middle click (pointer grab) -> video starts -> closed hold -> right click (open) hold -> right click
(closed) hold -> right click (open, "return") hold -> right click (closed) hold -> video stops.
After every click the server must report the expected lever/door-halves signature before the hold timer starts.

status.json (next to this file) is rewritten after every milestone so a parent process can follow a run.
"""

import fcntl
import gzip
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STATUS = HERE / "status.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# The shared helpers (world copy, tree hashes, NBT, lock path) come from the indirect-light runner. It imports its
# own `fixture` by name, so it must be loaded before anything else registers a module with that name.
C = _load("aql_indirect_capture", ROOT / "reports/2026-11-21-indirect-light/capture.py")
F = _load("aql_lever_fixture", HERE / "fixture.py")
H = F.H
require = F.require

SETTLE = 6.0  # seconds after the client reports a live world before anything is recorded
BASELINE_HOLD = 5.0  # closed door, lever off
STATE_HOLD = 5.5  # seconds each state is held after the server confirmed it (exposure adapts with ~1.8 s)
END_HOLD = 0.5
CONFIRM_TIMEOUT = 3.0
CLICK_HOLD = 0.09  # seconds between XTest button down and up
PATCH = 15  # square pixel patch for the ROI means
POSE_TOL_MM = F.HOLD_POS_MM
POSE_TOL_CDEG = 10  # 0.10 deg
STEPS = [("open", F.SIG_OPEN), ("closed", F.SIG_CLOSED), ("open-return", F.SIG_OPEN), ("closed-return", F.SIG_CLOSED)]
ANCHOR_MM = tuple(round(v * 1000) for v in F.FEET_WORLD)
ANCHOR_CDEG = (round(F.POSE["yaw"] * 100), round(F.POSE["pitch"] * 100))


def status(**fields):
    cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    cur.update(fields, updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, STATUS)


# ---------------------------------------------------------------- log parsing


def fatal(text):
    low = text.lower()
    if "disabling shaders" in low or "reverting to default" in low:
        return "Iris shader fallback"
    m = F.ERROR_RE.search(text)
    if m:
        return "Error line: " + text[text.rfind("\n", 0, m.start()) + 1 : text.find("\n", m.start())][:300]
    for m in F.EVENT_RE.finditer(text):
        if m.group(1) in ("FAIL", "ABORT", "DRIFT"):
            return "Fixture %s%s" % (m.group(1), m.group(2))
    return None


def parse_lines(text, start=0):
    """[(kind, payload, end_offset)] for complete lines after `start`: ('S', dict) or ('E', (kind, tag))."""
    out = []
    pos = start
    while True:
        nl = text.find("\n", pos)
        if nl < 0:
            break
        line = text[pos:nl]
        if m := F.SAMPLE_RE.search(line):
            k, t, sig, x, y, z, yaw, pitch, g = map(int, m.groups())
            out.append(("S", dict(kind=k, tick=t, sig=sig, pos=(x, y, z), yaw=yaw, pitch=pitch, ground=g), nl + 1))
        elif m := F.EVENT_RE.search(line):
            out.append(("E", (m.group(1), m.group(2).lstrip("_")), nl + 1))
        pos = nl + 1
    return out


# ---------------------------------------------------------------- input safety


class Input:
    """XTest mouse input only while the exact window of our PID has focus and is under the pointer."""

    def __init__(self, env, wid, pid, run=subprocess.run):
        self.env, self.wid, self.pid, self.run, self.log = env, str(wid), pid, run, []

    def _out(self, args):
        r = self.run(["xdotool"] + args, env=self.env, text=True, capture_output=True, timeout=4)
        return r.stdout.strip() if r.returncode == 0 else None

    def focused(self):
        return self._out(["getwindowfocus"]) == self.wid and self._out(["getwindowpid", self.wid]) == str(self.pid)

    def pointer(self):
        out = self._out(["getmouselocation", "--shell"]) or ""
        return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)

    def under_pointer(self):
        return self.pointer().get("WINDOW") == self.wid

    def bring_pointer(self, width, height):
        """Only if the pointer is not over our window: move it to the centre of OUR window (never elsewhere)."""
        require(self.focused(), "Minecraft window lost focus; refusing pointer input")
        if not self.under_pointer():
            self.run(["xdotool", "mousemove", "--window", self.wid, str(width // 2), str(height // 2)],
                     env=self.env, check=True, timeout=4)
            time.sleep(0.3)
        require(self.under_pointer(), "pointer is not over the Minecraft window")
        return self.pointer()

    def click(self, button):
        require(self.focused(), "Minecraft window lost focus; refusing click")
        require(self.under_pointer(), "pointer not over the Minecraft window; refusing click")
        down = time.time()
        self.run(["xdotool", "mousedown", str(button)], env=self.env, check=True, timeout=4)
        try:
            time.sleep(CLICK_HOLD)
        finally:
            self.run(["xdotool", "mouseup", str(button)], env=self.env, timeout=4)
        up = time.time()
        row = dict(button=button, down=round(down, 3), up=round(up, 3))
        self.log.append(row)
        return row


# ---------------------------------------------------------------- analysis


def decode_run(samples, clicks, rec_start, rec_end):
    """Check the server record of one take. Returns (summary, problems)."""
    problems = []
    inside = [s for s in samples if rec_start - 1.0 <= s["wall"] <= rec_end + 0.5]
    trans = [s for s in samples if s["kind"] == 1]
    if not inside:
        return {}, ["no server samples during the take"]
    dev = max(max(abs(s["pos"][i] - ANCHOR_MM[i]) for i in range(3)) for s in inside)
    dyaw = max(abs(s["yaw"] - ANCHOR_CDEG[0]) for s in inside)
    dpitch = max(abs(s["pitch"] - ANCHOR_CDEG[1]) for s in inside)
    if dev > POSE_TOL_MM:
        problems.append("player moved %d mm" % dev)
    if dyaw > POSE_TOL_CDEG or dpitch > POSE_TOL_CDEG:
        problems.append("camera rotated yaw %d / pitch %d centidegrees" % (dyaw, dpitch))
    if not all(s["ground"] == 1 for s in inside):
        problems.append("player not on the ground in every sample")
    rows = []
    for i, c in enumerate(clicks):
        nxt = clicks[i + 1]["down"] if i + 1 < len(clicks) else rec_end
        seq = [s for s in trans if c["down"] - 0.05 <= s["wall"] < nxt]
        want = c["expect"]
        got = [s["sig"] for s in seq]
        ok = bool(got) and got[-1] == want
        lever_tick = next((s["tick"] for s in seq if bool(s["sig"] & F.BIT_LEVER_ON) == bool(want & F.BIT_LEVER_ON)), None)
        full_tick = next((s["tick"] for s in seq if s["sig"] == want), None)
        if not ok:
            problems.append("click %d (%s): server signatures %s, expected last %d" % (i + 1, c["name"], got, want))
        # lever and both door halves must agree in the final state
        d = F.decode(got[-1]) if got else {}
        if ok and want == F.SIG_OPEN:
            ok = all(d[k] for k in ("lever_on", "lower_open", "upper_open", "lower_powered", "upper_powered"))
        if ok and want == F.SIG_CLOSED:
            ok = not any(d[k] for k in ("lever_on", "lower_open", "upper_open", "lower_powered", "upper_powered"))
        if not ok:
            problems.append("click %d (%s): final state inconsistent" % (i + 1, c["name"]))
        rows.append(dict(click=i + 1, name=c["name"], clickWall=c["down"], expectSig=want, serverSigs=got,
                         leverTick=lever_tick, doorsTick=full_tick,
                         leverToDoorsTicks=None if lever_tick is None or full_tick is None else full_tick - lever_tick,
                         ticks=[s["tick"] for s in seq]))  # fmt: skip
    summary = dict(
        maxPositionDeviationMm=dev, maxYawDeviationCentiDeg=dyaw, maxPitchDeviationCentiDeg=dpitch,
        samplesDuringTake=len(inside), signaturesSeen=sorted({s["sig"] for s in inside}), clickResults=rows,
        anchorMm=list(ANCHOR_MM), anchorCentiDeg=list(ANCHOR_CDEG),
    )  # fmt: skip
    return summary, problems


def patch_mean(raw, width, rect):
    x0, y0, x1, y1 = rect
    acc = [0, 0, 0]
    for y in range(y0, y1):
        row = raw[(y * width + x0) * 3 : (y * width + x1) * 3]
        for c in range(3):
            acc[c] += sum(row[c::3])
    n = (x1 - x0) * (y1 - y0)
    return [round(a / n, 2) for a in acc]


def roi_rects(width=F.WIDTH, height=F.HEIGHT):
    h = PATCH // 2
    out = []
    for name, pt, what in F.ROIS:
        u, v, _ = F.project(pt)
        cx, cy = int(u), int(v)
        rect = [cx - h, cy - h, cx + h + 1, cy + h + 1]
        require(rect[0] >= 0 and rect[1] >= 0 and rect[2] <= width and rect[3] <= height, "ROI %s outside frame" % name)
        out.append((name, rect, what))
    return out


def frame_rgb(video, t, env):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", str(video), "-frames:v", "1", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "pipe:"], env=env, capture_output=True, check=True, timeout=30)  # fmt: skip
    require(len(r.stdout) == F.WIDTH * F.HEIGHT * 3, "decoded frame size at %.2f s" % t)
    return r.stdout


# ---------------------------------------------------------------- dry run


def dry_run():
    t0 = time.monotonic()
    rep = F.selftest()
    files = F.datapack()
    F.check_datapack(files)
    F.simulate(files)
    target = Path(tempfile.mkdtemp(prefix="aql-lever-dry-"))
    for rel, text in files.items():
        p = target / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    # log parser: samples + events, with both sender spellings, incomplete trailing line ignored
    log = (
        "[Server thread/INFO]: [Not Secure] [Server] AQDI_BUILT_END\n"
        "[Server thread/INFO]: [Not Secure] [%s] AQDI_S 1 100 96 408000 161000 -406700 -5197 192 1 END\n"
        "[Server thread/INFO]: [Not Secure] [Server] AQDI_READY_END\n"
        "[Server thread/INFO]: [Not Secure] [%s] AQDI_S 0 110 96 408000 161000 -406700 -5197 192 1 END\n"
        "[Server thread/INFO]: [Not Secure] [%s] AQDI_S 1 140 127 408000 161000 -406700 -5197 192 1 END\n"
        "[Server thread/INFO]: [Not Secure] [%s] AQDI_S 1 150 12"
    ) % ((F.PLAYER,) * 4)
    got = parse_lines(log)
    require([g[0] for g in got] == ["E", "S", "E", "S", "S"], got)
    require(got[1][1]["sig"] == 96 and got[4][1]["sig"] == 127 and got[4][1]["pos"] == (408000, 161000, -406700), got)
    require(got[2][1] == ("READY", ""), got)
    require(fatal(log) is None, "false fatal")
    require(fatal(log + "\n[Server] AQDI_DRIFT_END\n") == "Fixture DRIFT", "drift")
    require(fatal(log + "\n[Server] AQDI_ABORT_reserved_END\n") == "Fixture ABORT_reserved", "abort")
    require(fatal("[Worker-Main-2/ERROR]: Failed to load function aqdi:watch\n") is not None, "function error")
    # take validator on synthetic samples: open, closed, open, closed with a one-tick door lag
    def smp(wall, tick, sig, kind=1, **kw):
        return dict(wall=wall, tick=tick, sig=sig, kind=kind, pos=ANCHOR_MM, yaw=ANCHOR_CDEG[0], pitch=ANCHOR_CDEG[1], ground=1, **kw)

    s = []
    clicks = []
    t, tick = 100.0, 1000
    for name, sig in STEPS:
        clicks.append(dict(name=name, down=t, expect=sig))
        lever = F.SIG_CLOSED | F.BIT_LEVER_ON if sig == F.SIG_OPEN else F.SIG_OPEN & ~F.BIT_LEVER_ON
        s += [smp(t + 0.1, tick, lever), smp(t + 0.15, tick + 1, sig), smp(t + 0.5, tick + 10, sig, 0)]
        t, tick = t + 6, tick + 120
    summary, probs = decode_run(s, clicks, 95.0, t)
    require(not probs, probs)
    require(all(r["leverToDoorsTicks"] == 1 for r in summary["clickResults"]), summary["clickResults"])
    bad = [dict(x) for x in s]
    bad[4] = dict(bad[4], sig=F.SIG_OPEN & ~F.BIT_UPPER_OPEN)  # upper half stays closed
    _, probs = decode_run(bad, clicks, 95.0, t)
    require(any("click 2" in p or "click 1" in p for p in probs), "validator misses a half-open door")
    moved = [dict(x) for x in s]
    moved[2] = dict(moved[2], pos=(ANCHOR_MM[0] + 80, ANCHOR_MM[1], ANCHOR_MM[2]))
    _, probs = decode_run(moved, clicks, 95.0, t)
    require(any("moved" in p for p in probs), "validator misses a moved player")

    # input guard: no click without focus or pointer; clicks always release the button
    class R:
        def __init__(self, focus, window):
            self.focus, self.window, self.calls = focus, window, []

        def __call__(self, args, **kw):
            self.calls.append(args)
            out = {"getwindowfocus": self.focus, "getwindowpid": "4242", "getmouselocation": "X=1\nY=2\nSCREEN=0\nWINDOW=%s" % self.window}.get(args[1], "")
            return subprocess.CompletedProcess(args, 0, out + "\n", "")

    ok = Input({}, "77", 4242, R("77", "77"))
    ok.click(3)
    verbs = [c[1] for c in ok.run.calls if c[1] in ("mousedown", "mouseup")]
    require(verbs == ["mousedown", "mouseup"], verbs)
    for focus, window in (("78", "77"), ("77", "78")):
        bad_in = Input({}, "77", 4242, R(focus, window))
        try:
            bad_in.click(3)
            raise AssertionError("clicked without focus/pointer")
        except RuntimeError:
            pass
        require(not any(c[1] == "mousedown" for c in bad_in.run.calls), "mousedown sent")
    rois = roi_rects()
    print("dry run ok:", target, "| functions", len(files) - 2, "| %.1fs" % (time.monotonic() - t0))
    print("player feet %s yaw %s pitch %s | lever distance %.2f m (reach %.1f) | crosshair on %s" % (
        rep["pose"]["feetWorld"], rep["pose"]["yaw"], rep["pose"]["pitch"], rep["crosshair"]["distance"], F.REACH, rep["crosshair"]["what"]))
    for name, rect, what in rois:
        print("  ROI %-15s %s %s" % (name, rect, what))
    return target


# ---------------------------------------------------------------- real run


def main(argv):
    require(len(argv) == 3, "usage: capture.py <shaderpack.zip> <out-dir-name> | --dry-run")
    require(os.getuid() == 1000, "Fixed lock/runtime paths assume uid 1000")
    pack = Path(argv[1])
    require(pack.is_file() and not pack.is_symlink() and pack.suffix == ".zip", "Pack must be a regular .zip")
    pack = pack.resolve()
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", argv[2]) is not None, "Out dir must be a simple name")
    out = HERE / argv[2]
    require(out.parent == HERE and not out.exists() and not out.is_symlink(), "Out dir exists or escapes")
    files = F.datapack()
    F.check_datapack(files)
    F.simulate(files)
    F.selftest()
    scripts = {n: C.sha((HERE / n).read_bytes()) for n in ("capture.py", "fixture.py")}
    pack_sha = C.sha(pack.read_bytes())
    status(phase="waiting for the render lock", run=argv[2], pack=pack.name, packSha256=pack_sha, pid=os.getpid(),
           note="CPU checks passed; no client launched yet", milestones=[], error=None)  # fmt: skip
    milestones = []

    def mark(phase, **kw):
        milestones.append(dict(phase=phase, at=time.strftime("%H:%M:%S"), **kw))
        status(phase=phase, milestones=milestones, **kw)
        print(json.dumps(dict(phase=phase, **kw)), flush=True)

    lock = open(C.LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    mark("render lock acquired")
    sys.path.insert(0, str(ROOT / "tools"))
    import ground_shadow_lab as g

    lab = g.lab
    orig = g.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    assets = orig.parents[2] / "assets"
    src = orig / "saves" / lab.WORLD
    require(src.is_dir() and not src.is_symlink() and src.resolve().parent == orig / "saves", "Source world path")
    require(not str(pack).startswith(str(orig) + os.sep), "Pack must not live inside the Lab instance")
    require(os.access("/tmp/aqualumen-wm-close", os.X_OK), "Missing /tmp/aqualumen-wm-close")
    originals = {n: C.sha((orig / n).read_bytes()) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json") if (orig / n).is_file()}  # fmt: skip
    mods = {n: C.sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}
    require(len(mods) == 3, "Expected exactly the three normal mods")

    out.mkdir()
    labroot = Path(tempfile.mkdtemp(prefix="lever-door-", dir=orig.parent)).resolve()
    game = labroot / "Aqualumen Lab/minecraft"
    require(labroot.parent == orig.parent and not str(game).startswith(str(orig) + os.sep), "Clone path")
    game.mkdir(parents=True)
    (out / "private-game.txt").write_text(str(game) + "\n")
    for n in ["shaderpacks", "mods", "config", "saves"]:
        (game / n).mkdir()
    lab.shared.world_marker()
    with (src / "session.lock").open("r+b") as f:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_manifest = C.copy_world(src, game / "saves" / lab.WORLD)
    world = (game / "saves" / lab.WORLD).resolve()
    require(world.parent == game / "saves" and len(list((game / "saves").iterdir())) == 1, "Clone not unique")
    require(C.tree(world) == source_manifest, "Clone differs from source")
    marker = lab.pairs((world / "aqualumen-world.properties").read_bytes())
    require(marker.get("world_id") == lab.WORLD_ID and marker.get("seed") == str(C.SEED), "Clone UUID/seed marker")
    level = C.nbt(gzip.decompress((world / "level.dat").read_bytes()))
    require(level["Data"]["WorldGenSettings"]["seed"] == C.SEED, "level.dat seed differs")
    require(not (world / "playerdata" / F.PLAYER_FILE).exists(), "Fixture player already in source world")
    require(not (world / "datapacks" / F.PACK_NAME).exists(), "Datapack already present")
    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
        require(C.sha((game / "mods" / n).read_bytes()) == mods[n], "Mod copy differs")
    shutil.copy(pack, game / "shaderpacks")
    require(C.sha((game / "shaderpacks" / pack.name).read_bytes()) == pack_sha, "Pack copy differs")
    for n in ["sodium-options.json", "iris.properties"]:
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    require(lab.pairs(iris.read_bytes()).get("enableShaders", "true") == "true", "Shaders disabled in config")
    options = dict(
        lab.OPTIONS, maxFps="120", overrideWidth=str(F.WIDTH), overrideHeight=str(F.HEIGHT), pauseOnLostFocus="false",
        chatVisibility="2", mainHand='"right"', autoJump="false", fov=F.fmt(F.FOV_OPTION), fovEffectScale="0.0", bobView="false",
    )  # fmt: skip
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    kit = world / "datapacks" / F.PACK_NAME
    for rel, text in files.items():
        q = kit / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(text)
    datapack_digest = C.digest({k: C.sha(v.encode()) for k, v in files.items()})
    the_plan = dict(
        F.plan(), pack=pack.name, packSha256=pack_sha, datapackDigest=datapack_digest, options=options, scripts=scripts,
        world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=C.SEED, sourceDigest=C.digest(source_manifest)),
        timing=dict(settle=SETTLE, baselineHold=BASELINE_HOLD, stateHold=STATE_HOLD, clickHold=CLICK_HOLD),
        steps=[dict(name=n, expectSig=s) for n, s in STEPS], selftest=F.selftest(),
        rois=[dict(name=n, rect=r, what=w) for n, r, w in roi_rects()],
    )  # fmt: skip
    (out / "plan.json").write_text(json.dumps(the_plan, indent=2))
    mark("private clone verified", world=lab.WORLD_ID, sourceDigest=C.digest(source_manifest)[:16], datapackDigest=datapack_digest[:16])

    env = dict(
        os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000", DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus",
        __GLX_VENDOR_LIBRARY_NAME="nvidia", ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(labroot / "cache"),
    )  # fmt: skip
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    java = [
        runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4",
        "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
        "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", F.PLAYER, "--version", "1.21.1",
        "--gameDir", str(game), "--assetsDir", str(assets), "--assetIndex", "17", "--uuid", F.PLAYER_UUID,
        "--accessToken", "0", "--userType", "legacy", "--width", str(F.WIDTH), "--height", str(F.HEIGHT),
        "--quickPlaySingleplayer", lab.WORLD,
    ]  # fmt: skip
    log = out / "client.log"
    raw_video = labroot / "take-raw.mkv"
    samples, events, timeline, clicks = [], [], [], []
    proc = ffmpeg = inp = None
    state = dict(cursor=0, status="incomplete", rec_start=None, rec_end=None, ff_wall=None)

    def note(kind, **kw):
        row = dict(wall=round(time.time(), 3), kind=kind, **kw)
        timeline.append(row)
        print(json.dumps(row), flush=True)

    def window():
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(proc.pid), "--name", "Minecraft"],
                           env=env, text=True, capture_output=True)  # fmt: skip
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def poll():
        text = log.read_text(errors="replace")
        f = fatal(text)
        require(f is None, str(f))
        require(proc.poll() is None, "Client exited")
        new = []
        for kind, payload, end in parse_lines(text, state["cursor"]):
            state["cursor"] = end
            now = time.time()
            if kind == "S":
                samples.append(dict(payload, wall=round(now, 3)))
            else:
                events.append(dict(kind=payload[0], tag=payload[1], wall=round(now, 3)))
                new.append(payload)
                note("server", event=payload[0], tag=payload[1])
        return new

    def wait_event(kind, timeout):
        deadline = time.monotonic() + timeout
        while True:
            if any(e[0] == kind for e in poll()):
                return
            require(time.monotonic() < deadline, "Timed out waiting for AQDI_" + kind)
            time.sleep(0.05)

    def latest(max_age=1.5):
        require(samples and time.time() - samples[-1]["wall"] < max_age, "no fresh server sample")
        return samples[-1]

    def check_pose(expect_sig):
        s = latest()
        dev = max(abs(s["pos"][i] - ANCHOR_MM[i]) for i in range(3))
        require(dev <= POSE_TOL_MM and abs(s["yaw"] - ANCHOR_CDEG[0]) <= POSE_TOL_CDEG
                and abs(s["pitch"] - ANCHOR_CDEG[1]) <= POSE_TOL_CDEG and s["ground"] == 1,
                "player pose off the anchor: %s" % (s,))  # fmt: skip
        require(s["sig"] == expect_sig, "unexpected door/lever state %d (wanted %d)" % (s["sig"], expect_sig))
        return s

    def hold(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            poll()
            time.sleep(0.05)

    stop_monitor, focus_lost = threading.Event(), threading.Event()
    with log.open("xb") as stream:
        proc = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        mark("client launched", pid=proc.pid)
        try:
            deadline = time.monotonic() + 300
            while not (ready := C.READY_RE.search(t := log.read_text(errors="replace"))):
                require(fatal(t) is None, str(fatal(t)))
                require(proc.poll() is None and time.monotonic() < deadline, "Client never reached a live world render")
                time.sleep(0.3)
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            require(renderer and lab.nvidia(renderer.group(1)), "Not the NVIDIA renderer")
            require("Using shaderpack: " + pack.name in t, "Iris did not select the pack")
            client_ready = time.monotonic()
            mark("client ready", renderer=renderer.group(1).strip())
            wait_event("BUILT", 120)
            mark("house built by datapack")
            wait_event("READY", 120)
            mark("fixture verified (survival player, pose, house, closed door, lever off)")
            time.sleep(max(0.0, client_ready + SETTLE - time.monotonic()))
            wid = window()
            require(wid is not None, "Minecraft window not found (or not unique) for our PID")
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], env=env, check=True, timeout=4)
            inp = Input(env, wid, proc.pid)
            require(inp.focused(), "Window focus/PID")
            title = subprocess.check_output(["xdotool", "getwindowname", wid], env=env, text=True).strip()
            require("Minecraft" in title, "Window title")
            geo = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", wid], env=env, text=True)
            ptr = inp.bring_pointer(F.WIDTH, F.HEIGHT)
            note("window", wid=wid, title=title, geometry=geo.split(), pointer=ptr)
            # One harmless middle click (survival pick-block with nothing to pick) so the client has grabbed the pointer
            # before recording; it can not toggle the lever.
            inp.click(2)
            note("input", button=2, why="pointer grab before recording; no gameplay effect")
            hold(1.5)
            check_pose(F.SIG_CLOSED)

            def monitor():
                while not stop_monitor.wait(0.15):
                    if not inp.focused():
                        focus_lost.set()
                        break

            threading.Thread(target=monitor, daemon=True).start()
            state["ff_wall"] = time.time()
            ffmpeg = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0", "-framerate", "30",
                 "-window_id", wid, "-i", env["DISPLAY"], "-copyts", "-c:v", "libx264", "-preset", "superfast", "-crf", "17",
                 "-pix_fmt", "yuv420p", "-threads", "4", str(raw_video)],
                env=env, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
            )  # fmt: skip
            time.sleep(0.6)
            require(ffmpeg.poll() is None, "ffmpeg exited early")
            state["rec_start"] = time.time()
            mark("recording started", pid=ffmpeg.pid)
            hold(BASELINE_HOLD)
            for i, (name, want) in enumerate(STEPS):
                require(not focus_lost.is_set(), "Minecraft window lost focus")
                check_pose(STEPS[i - 1][1] if i else F.SIG_CLOSED)
                row = None
                for attempt in (1, 2):
                    row = dict(inp.click(3), name=name, expect=want, attempt=attempt, tickBefore=latest()["tick"])
                    note("input", button=3, why="right click on the lever: " + name, attempt=attempt)
                    deadline = time.monotonic() + CONFIRM_TIMEOUT
                    while time.monotonic() < deadline and not any(
                        s["sig"] == want and s["wall"] >= row["down"] - 0.05 for s in samples[-40:]):
                        poll()
                        time.sleep(0.02)
                    if any(s["sig"] == want and s["wall"] >= row["down"] - 0.05 for s in samples[-40:]):
                        break
                    note("click-unconfirmed", name=name, attempt=attempt)
                    require(attempt == 1, "Server never confirmed state %d after the click" % want)
                row["confirmedWall"] = next(s["wall"] for s in samples[-40:] if s["sig"] == want and s["wall"] >= row["down"] - 0.05)
                clicks.append(row)
                mark("click %d confirmed by server: %s" % (i + 1, name), sig=want, lagSeconds=round(row["confirmedWall"] - row["down"], 3))
                hold(STATE_HOLD)
            hold(END_HOLD)
            state["rec_end"] = time.time()
            stop_monitor.set()
            state["status"] = "finished"
            mark("last hold finished; stopping video")
        finally:
            stop_monitor.set()
            if ffmpeg is not None and ffmpeg.poll() is None:
                try:
                    ffmpeg.communicate(b"q", timeout=20)
                except subprocess.TimeoutExpired:
                    ffmpeg.terminate()
                    ffmpeg.wait(timeout=10)
            if inp is not None:
                subprocess.run(["xdotool", "mouseup", "3"], env=env, timeout=4)  # never leave a button pressed
            wid_now = window() if proc.poll() is None else None
            if wid_now:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(wid_now))], check=True, env=env)
            try:
                proc.wait(timeout=24)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
            try:
                poll_text = log.read_text(errors="replace")
                for kind, payload, end in parse_lines(poll_text, state["cursor"]):
                    state["cursor"] = end
                    if kind == "S":
                        samples.append(dict(payload, wall=round(time.time(), 3)))
            except Exception:  # noqa: BLE001
                pass
            (out / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
            (out / "timeline.json").write_text(json.dumps(dict(status=state["status"], timeline=timeline, clicks=clicks,
                                                               inputLog=inp.log if inp else []), indent=1))  # fmt: skip

    text = log.read_text(errors="replace")
    require(fatal(text) is None, str(fatal(text)))
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", text).group(1).strip()
    require(lab.nvidia(renderer) and "All dimensions are saved" in text, "Clean NVIDIA shutdown not logged")
    require(C.tree(src) == source_manifest, "SOURCE WORLD CHANGED")
    for n, h in originals.items():
        require(C.sha((orig / n).read_bytes()) == h, "Original Lab file changed: " + n)
    mark("client closed cleanly; source world and Lab files unchanged")

    # ---- video: zero-based remux, alignment of server wall times with the first captured frame
    first = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                            "-read_intervals", "%+#1", "-of", "csv=p=0", str(raw_video)], capture_output=True, text=True, check=True).stdout.split()  # fmt: skip
    t0 = float(first[0]) if first else None
    wallclock = t0 is not None and abs(t0 - state["ff_wall"]) < 5
    base = t0 if wallclock else state["ff_wall"]
    video = out / "lever-door.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(raw_video), "-c", "copy", "-movflags", "+faststart", str(video)], check=True)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,nb_frames,avg_frame_rate",
                                       "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout)  # fmt: skip
    duration = float(probe["format"]["duration"])
    summary, problems = decode_run(samples, clicks, state["rec_start"], state["rec_end"])
    if not 20.0 <= duration <= 45.0:
        problems.append("video duration %.1f s outside 20-45 s" % duration)
    vt = lambda wall: round(wall - base, 3)

    # ---- display-referred ROI means from the decoded video at the end of each hold
    holds = []
    edges = [(state["rec_start"], clicks[0]["down"], "closed", F.SIG_CLOSED)]
    for i, c in enumerate(clicks):
        edges.append((c["confirmedWall"], clicks[i + 1]["down"] if i + 1 < len(clicks) else state["rec_end"], c["name"], c["expect"]))
    rects = roi_rects()
    (out / "frames").mkdir()
    for i, (a, b, name, sig) in enumerate(edges):
        row = dict(index=i, state=name, sig=sig, startVideoS=vt(a), endVideoS=vt(b), samples={})
        for label, when in (("early", a + 1.0), ("late", b - 0.35)):
            tv = max(0.0, min(vt(when), duration - 0.1))
            raw = frame_rgb(video, tv, env)
            row["samples"][label] = dict(videoS=round(tv, 3), roiMeanSRGB8={n: patch_mean(raw, F.WIDTH, r) for n, r, _ in rects})
            if label == "late":
                subprocess.run(["ffmpeg", "-v", "error", "-n", "-ss", "%.3f" % tv, "-i", str(video), "-frames:v", "1", "-q:v", "3",
                                str(out / "frames" / ("%d-%s.jpg" % (i, name)))], check=True, env=env)
        holds.append(row)
    # evidence strings for the report; nothing here is a performance measurement
    transitions = [dict(tick=s["tick"], videoS=vt(s["wall"]), sig=s["sig"], **F.decode(s["sig"])) for s in samples if s["kind"] == 1 and s["wall"] >= state["rec_start"] - 5]
    (out / "server-events.log").write_text("\n".join(l for l in text.splitlines() if "AQDI_" in l) + "\n")
    complete = dict(
        status=state["status"], problems=problems, renderer=renderer, glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", text)), None),
        pack=pack.name, sha256=pack_sha, normalModFiles=mods, recorderMod=False, shaderFallback=False,
        world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=C.SEED, sourceDigest=C.digest(source_manifest), sourceUnchanged=True),
        originalLabFilesUnchanged=sorted(originals), datapackDigest=datapack_digest, scripts=scripts,
        video=dict(file=video.name, sha256=C.sha(video.read_bytes()), durationSeconds=round(duration, 3), probe=probe,
                   cadenceNote="30 fps is the encoder cadence of the screen capture only; it is not a Minecraft frame-time measurement",
                   alignment="x11grab wallclock pts" if wallclock else "ffmpeg spawn time (approx. +0.1..0.5 s)",
                   recordingStartWall=round(state["rec_start"], 3), recordingEndWall=round(state["rec_end"], 3)),
        take=summary, transitions=transitions, holds=holds, clicks=clicks,
        input=dict(realMouse="xdotool XTest mousedown/mouseup, button 3 on the focused window of our PID (button 2 once before recording)",
                   doorOrLeverWrittenAfterBuild=False, flightOrCreative=False, gamemode="survival"),
        limitations=["ROI means are display-referred 8-bit sRGB from the decoded H.264 video and include auto-exposure and compression",
                     "server sample wall times are the reader's observation of the log, not exact tick or frame times"],
    )  # fmt: skip
    (out / "complete.json").write_text(json.dumps(complete, indent=2))
    mark("evidence written", video=str(video), duration=round(duration, 2), problems=problems or None)
    require(not problems, "Validation failed: %s" % problems)
    status(phase="complete", video=str(video), durationSeconds=round(duration, 2), error=None)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--dry-run"]:
            dry_run()
        else:
            main(sys.argv)
    except BaseException as e:  # noqa: BLE001 - leave a final status for whoever is following the run
        if sys.argv[1:] != ["--dry-run"]:
            status(phase="failed", error="%s: %s" % (type(e).__name__, e))
        raise
