"""Keep a cold-linking private test client alive and capture F2 between the server's checked markers."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "private_scene", here.parent / "runtime-v190/run.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session", type=Path)
    p.add_argument("label")
    p.add_argument("pid", type=int)
    a = p.parse_args()
    source = a.session.resolve()
    game = Path((source / "private-game.txt").read_text()).resolve(strict=True)
    assert game.parent.parent == Path("/tmp") and game.parent.name.startswith(
        "aql-v190-run-"
    )
    proc = Path("/proc") / str(a.pid)
    args = (proc / "cmdline").read_bytes().split(b"\0")
    assert b"--gameDir" in args and args[args.index(b"--gameDir") + 1] == os.fsencode(
        game
    )
    parent = int(re.search(r"^PPid:\s+(\d+)", (proc / "status").read_text(), re.M)[1])
    parent_args = (Path("/proc") / str(parent) / "cmdline").read_bytes().split(b"\0")
    assert (
        Path(os.fsdecode(parent_args[1])).resolve() == here / "run.py"
        and os.fsdecode(parent_args[3]) == source.name
    )
    display = next(
        v.split(b"=", 1)[1].decode()
        for v in (proc / "environ").read_bytes().split(b"\0")
        if v.startswith(b"DISPLAY=")
    )
    assert int(display[1:]) >= 201 and display != os.getenv("DISPLAY")
    env = runner.clean_env(display)
    log = source / "client.log"
    log_text = lambda: log.read_text(errors="replace")
    geometry = json.loads((source / "geometry.json").read_text())
    names = list(geometry["stages"])
    (pack,) = (game / "shaderpacks").glob("*.zip")
    digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    assert (
        "Using shaderpack: " + pack.name in log_text() and "RTX 3080 Ti" in log_text()
    )
    assert (
        "AQLAVA_BEGIN" not in log_text()
        and "contact bridge initialized" not in log_text()
    )
    assert re.fullmatch(r"[a-z0-9-]+", a.label)
    out = here / a.label
    out.mkdir()
    shutil.copy2(source / "geometry.json", out)
    (out / "private-game.txt").write_text(str(game))
    photos, times = {}, {}
    success = False

    def latest():
        events = list(runner.scene.EVENT_RE.finditer(log_text()))
        return events[-1] if events else None

    def key(*args):
        return subprocess.run(
            ["xdotool", *args],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=8,
        ).stdout.strip()

    # Move supervision only for this verified private parent. Its own cleanup,
    # protected-world check and failed first-timeout record resume in finally.
    os.kill(parent, signal.SIGSTOP)
    try:
        until = time.monotonic() + 2400
        while "contact bridge initialized" not in log_text():
            text = log_text()
            if (
                not proc.exists()
                or time.monotonic() > until
                or "Error encountered when linking program" in text
            ):
                raise RuntimeError("Private client did not finish linking")
            time.sleep(1)
        windows = runner.window_ids(env, a.pid)
        assert len(windows) == 1
        window = windows[0]
        key("windowfocus", "--sync", window)
        assert key("getwindowfocus") == window
        time.sleep(2)
        key("key", "F1")
        time.sleep(0.6)
        key("keydown", "f")
        time.sleep(0.3)
        key("keyup", "f")
        until = time.monotonic() + 420
        seen = set()
        while len(photos) < len(names) and time.monotonic() < until:
            e = latest()
            if e is None or e[1] != "READY" or e[2] in photos or e.start() in seen:
                time.sleep(0.12)
                continue
            seen.add(e.start())
            name = e[2]
            assert name in names and key("getwindowfocus") == window
            time.sleep(0.8)
            if latest().start() != e.start():
                continue
            pre = set((game / "screenshots").glob("*.png"))
            key("key", "F2")
            file = None
            for _ in range(60):
                new = set((game / "screenshots").glob("*.png")) - pre
                if len(new) == 1:
                    candidate = next(iter(new))
                    if candidate.read_bytes().endswith(b"IEND\xaeB\x60\x82"):
                        file = candidate
                        break
                time.sleep(0.08)
            if file is None or latest().start() != e.start():
                continue
            while latest().start() == e.start() and time.monotonic() < until:
                time.sleep(0.10)
            mark = latest()
            if mark[1] != "STILL" or mark[2] != name:
                continue
            dst = out / (name + "-ingame.png")
            shutil.copy2(file, dst)
            photos[name] = {"ingame": digest(dst)}
            times[name] = {
                "readyLogOffset": e.start(),
                "sourceF2": file.name,
                "stillLogOffset": mark.start(),
            }
            print(name, flush=True)
        success = len(photos) == len(names)
    finally:
        os.kill(parent, signal.SIGCONT)
        for _ in range(160):
            if (source / "complete.json").is_file():
                break
            time.sleep(0.5)
        earlier = (
            json.loads((source / "complete.json").read_text())
            if (source / "complete.json").exists()
            else {}
        )
        shutil.copy2(log, out / "client.log")
        record = dict(
            label=a.label,
            pack=pack.name,
            packSha256=digest(pack),
            backend="vgl",
            gl=earlier.get("gl", {}),
            stages=names,
            screenshots=photos,
            exposureChecks=times,
            complete=success,
            shaderpackLogged=True,
            privateGameDir=str(game),
            originalWorldAndConfigUnchanged=earlier.get(
                "originalWorldAndConfigUnchanged", False
            ),
        )
        (out / "complete.json").write_text(json.dumps(record, indent=2) + "\n")
    assert success and record["originalWorldAndConfigUnchanged"]


if __name__ == "__main__":
    main()
