"""Retry the paper hand-swap after a cold renderer has produced its first usable frame."""
import argparse
import os
import re
import subprocess
import time
from pathlib import Path


def arm(directory, timeout):
    directory = directory.resolve()
    game = Path((directory / "private-game.txt").read_text()).resolve(strict=True)
    assert game.parent.parent == Path("/tmp") and game.parent.name.startswith("aql-v190-run-")
    java = []
    for p in Path("/proc").glob("[0-9]*"):
        try:
            argv = (p / "cmdline").read_bytes().split(b"\0")
            if b"--gameDir" in argv and argv[argv.index(b"--gameDir") + 1] == os.fsencode(game):
                java.append(p)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    assert len(java) == 1
    process = java[0]
    env = dict(x.split(b"=", 1) for x in (process / "environ").read_bytes().split(b"\0") if b"=" in x)
    display = env[b"DISPLAY"].decode()
    assert re.fullmatch(r":\d{3}", display) and int(display[1:]) >= 171 and os.getenv("DISPLAY") != display
    xenv = {"PATH":os.environ["PATH"], "DISPLAY":display}

    def x(*args):
        return subprocess.check_output(["xdotool", *args], env=xenv, text=True, timeout=8).strip()

    until = time.monotonic()+timeout
    while True:
        log = (directory / "client.log").read_text(errors="replace")
        if "AQLAVA_BEGIN_" in log:
            print(directory.name, "server confirmed start", flush=True)
            return
        if not process.exists() or time.monotonic() > until:
            raise RuntimeError("private client did not start its stage")
        if "contact bridge initialized" in log and "AQLAVA_ARM_END" in log:
            time.sleep(4)
            if "AQLAVA_BEGIN_" in (directory / "client.log").read_text():
                continue
            wid, = x("search","--all","--onlyvisible","--pid",process.name,"--name","Minecraft").splitlines()
            assert x("getwindowfocus") == wid
            x("keydown","f")
            time.sleep(.35)
            x("keyup","f")
        time.sleep(2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--timeout", type=int, default=3300)
    a = parser.parse_args()
    arm(a.directory, a.timeout)
