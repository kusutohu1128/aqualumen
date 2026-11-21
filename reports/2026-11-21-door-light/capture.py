"""Native door-light house capture: wraps reports/2026-11-21-indirect-light/capture.py.

The indirect-light runner (exact-UUID/seed private Lab-world clone, three normal mods and no
recorder Mod, render lock, NVIDIA renderer check, handshake-synchronised x11grab of only the
private client window, source-world-unchanged check) is imported and its fixture hooks are
re-pointed to house.py / fixture.py.  Nothing of that runner is copied here.

    python3 capture.py --dry-run
    python3 capture.py <shaderpack.zip> <role-dir>        # one real run
    python3 capture.py campaign                           # before (1.5.0), then after (rc1 when present)
    AQL_DOOR_ROLES=open-warm,closed-warm python3 capture.py ...   # optional subset
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "status.json"
BEFORE = ROOT / "dist/Aqualumen-1.5.0.zip"
BEFORE_SHA = "0f1582d613132fa9a4f8f39110a17c85982bfa174c403acbb4598f4b81c98cbe"
AFTER = ROOT / "dist/Aqualumen-1.6.0-door-rc1.zip"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# The base runner imports its own fixture as `fixture`; load it before our modules.
C = _load("aql_indirect_capture", HERE.parent / "2026-11-21-indirect-light/capture.py")
sys.path.insert(0, str(HERE))
import house as H  # noqa: E402

D = _load("aql_door_fixture", HERE / "fixture.py")

_builtin_print = print


def status(**fields):
    cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    cur.update(fields, updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, STATUS)


def selected_roles(env=os.environ):
    raw = env.get("AQL_DOOR_ROLES", "").strip()
    if not raw:
        return list(H.ROLE_NAMES)
    names = [n.strip() for n in raw.split(",") if n.strip()]
    C.require(len(set(names)) == len(names), "Duplicate role")
    unknown = sorted(set(names) - set(H.ROLE_NAMES))
    C.require(not unknown, "Unknown roles: " + ",".join(unknown))
    return [n for n in H.ROLE_NAMES if n in names]


def configure(run_name=None):
    C.HERE = HERE
    C.F = H
    C.NS, C.PACK_NAME = D.NS, D.PACK_NAME
    C.EVENT_RE, C.ERROR_RE = D.EVENT_RE, D.ERROR_RE
    C.PLAYER_UUID = "00000000000040008000000000000431"
    C.PLAYER_FILE = "00000000-0000-4000-8000-000000000431.dat"
    C.DWELL = 4.0  # lamp-exposure adaptation rises with a 1.8 s time constant
    C.SETTLE = float(os.environ.get("AQL_DOOR_SETTLE", C.SETTLE))
    C.datapack = lambda roles: D.datapack(roles, C)
    C.check_datapack = D.check_datapack
    C.simulate = lambda files, roles: D.simulate(files, roles, C)
    C.plan = lambda roles: dict(D.plan(roles, C), scripts={n: C.sha((HERE / n).read_bytes()) for n in ("house.py", "fixture.py", "capture.py")})
    C.selected_roles = selected_roles

    def progress(*args, **kw):
        _builtin_print(*args, **kw)
        if run_name and args and args[0] in H.ROLE_NAMES:
            cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
            done = cur.get("runs", {}).get(run_name, {}).get("captured", [])
            runs = cur.get("runs", {})
            runs.setdefault(run_name, {})["captured"] = done + [args[0]]
            status(runs=runs)

    C.print = progress


def dry_run():
    t0 = time.monotonic()
    configure()
    rep = H.selftest()
    roles = selected_roles()
    files = C.datapack(roles)
    C.check_datapack(files, roles)
    C.simulate(files, roles)
    target = Path(tempfile.mkdtemp(prefix="aql-door-dry-"))
    for rel, text in files.items():
        p = target / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    plan = C.plan(roles)
    (target / "plan.json").write_text(json.dumps(plan, indent=2))
    log = (
        "[Server thread/INFO]: [Not Secure] [Server] AQD_READY_open-warm_END\n"
        "[Render thread/INFO]: [STDOUT]: [Aqualumen Physics] 0.2.0 contact bridge initialized (512)\n"
        "[Server thread/INFO]: [Not Secure] [Server] AQD_BEGIN_closed-warm_END\n"
        "[Server thread/INFO]: [Not Secure] [Server] AQD_READY_returned-closed_END\n"
    )
    ready = C.READY_RE.search(log)
    ev = C.events(log, ready.end())
    C.require([(k, r) for k, r, _ in ev] == [("BEGIN", "closed-warm"), ("READY", "returned-closed")], ev)
    C.require(C.fatal(log) is None, "false fatal")
    C.require(C.fatal(log + "[Server] AQD_FAIL_cow-warm_END\n") == "Fixture verification failed: cow-warm", "fail")
    C.require(C.fatal("[Worker-Main-2/ERROR]: Failed to load function aqd:s0\n") is not None, "function error")
    longest = max(len(t.splitlines()) for t in files.values())
    print("dry run ok:", target, "| functions", len(files) - 2, "| longest", longest, "lines | %.1fs" % (time.monotonic() - t0))
    print("cow shadow grid", rep["cowShadowGrid"], "sun elevation", rep["sunElevationDeg"])
    for row in plan["roles"]:
        print("%-17s %-11s warm=%d soul=%d cow=%d %s" % (row["name"], row["door"], row["warm"], row["soul"], row["cow"], row["pose"]))
    return target


def timeline(out, stop, every=4.0):
    """Optional: periodic x11grab of only the private client window (found by its private gameDir)."""
    import threading

    def body():
        while not (out / "private-game.txt").is_file():
            if stop.wait(0.5):
                return
        game = (out / "private-game.txt").read_text().strip()
        target = out / "timeline"
        target.mkdir()
        rows, pid, env = [], None, dict(os.environ, DISPLAY=":1")
        while not stop.is_set():
            if pid is None:
                r = subprocess.run(["pgrep", "-f", "--", "--gameDir " + game], capture_output=True, text=True)
                pids = r.stdout.split()
                pid = pids[0] if len(pids) == 1 else None
            wid = None
            if pid:
                r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", pid, "--name", "Minecraft"],
                                   env=env, capture_output=True, text=True)
                wid = r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None
            if wid:
                t = time.time()
                f = target / ("%04d.png" % len(rows))
                ok = subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", ":1",
                                     "-frames:v", "1", "-threads", "1", str(f)], env=env, timeout=6).returncode == 0
                if ok:
                    raw = C.rgb(f, env)
                    rows.append(dict(file=f.name, epoch=round(t, 2), clock=time.strftime("%H:%M:%S", time.localtime(t)),
                                     size=list(C.png_size(f)),
                                     frameMean=[round(sum(raw[c::3]) / (len(raw) // 3), 3) for c in range(3)],
                                     patches={s["name"]: C.patch_mean(raw, s["patch"]) for s in H.samples(H.role("open-warm"))}
                                     if C.png_size(f) == (H.WIDTH, H.HEIGHT) else None))
                    (target / "timeline.json").write_text(json.dumps(rows, indent=1))
            stop.wait(every)

    th = threading.Thread(target=body, daemon=True)
    th.start()
    return th


def real(pack, run_name):
    configure(run_name)
    stop = None
    if os.environ.get("AQL_DOOR_TIMELINE") == "1":
        import threading

        stop = threading.Event()
        th = timeline(HERE / run_name, stop)
    runs = json.loads(STATUS.read_text()).get("runs", {}) if STATUS.exists() else {}
    runs[run_name] = dict(pack=Path(pack).name, state="running", started=time.strftime("%H:%M:%S"), captured=[])
    status(runs=runs)
    try:
        C.main(["capture.py", str(pack), run_name])
    except BaseException as e:
        if stop:
            stop.set()
        cur = json.loads(STATUS.read_text())
        cur["runs"][run_name].update(state="failed", error="%s: %s" % (type(e).__name__, e),
                                     trace=traceback.format_exc()[-1500:])
        status(runs=cur["runs"])
        raise
    if stop:
        stop.set()
        th.join(10)
    cur = json.loads(STATUS.read_text())
    done = json.loads((HERE / run_name / "complete.json").read_text())
    cur["runs"][run_name].update(state="complete", renderer=done["renderer"], sha256=done["sha256"],
                                 finished=time.strftime("%H:%M:%S"))
    status(runs=cur["runs"])


def completed(prefix):
    for d in sorted(HERE.glob(prefix + "-r*")):
        if (d / "complete.json").is_file():
            return d.name
    return None


def next_name(prefix):
    i = 1
    while (HERE / ("%s-r%d" % (prefix, i))).exists():
        i += 1
    return "%s-r%d" % (prefix, i)


def campaign():
    C.require(C.sha(BEFORE.read_bytes()) == BEFORE_SHA, "1.5.0 archive differs from the released hash")
    status(phase="campaign", pid=os.getpid(), unit=os.environ.get("INVOCATION_ID"))
    for prefix, pack in (("before", BEFORE), ("after", AFTER)):
        if completed(prefix):
            continue
        if prefix == "after":
            status(phase="waiting for " + AFTER.name)
            deadline = time.time() + 6 * 3600
            while not AFTER.is_file():
                C.require(time.time() < deadline, "Candidate never appeared")
                time.sleep(30)
            size = -1
            while size != AFTER.stat().st_size:  # wait for the writer to finish
                size = AFTER.stat().st_size
                time.sleep(5)
        for attempt in range(2):
            name = next_name(prefix)
            status(phase="capturing " + name)
            try:
                real(pack, name)
                break
            except Exception:
                if attempt:
                    status(phase="failed " + name)
                    raise
        subprocess.run([sys.executable, str(HERE / "measure.py")], check=False)
    status(phase="complete")


if __name__ == "__main__":
    if sys.argv[1:] == ["--dry-run"]:
        dry_run()
    elif sys.argv[1:] == ["campaign"]:
        campaign()
    else:
        C.require(len(sys.argv) == 3, __doc__)
        real(sys.argv[1], sys.argv[2])
