"""Traverse the oak in both directions without turning the camera while recording."""

from pathlib import Path
import subprocess
import time


def walk(
    world,
    first,
    results,
    trail,
    turn,
    goto,
    observe,
    key,
    hold,
    shot,
    hotbar,
    display,
    wid,
    env,
    out,
    guard,
    x,
):
    path = Path(out)
    assert "1" not in hotbar() and hotbar()["2"] == "minecraft:torch"
    trail.build("oak-night-trail", world, first["xyz"], destination=(569, 64, 419))
    assert trail.clear_line((565, 64, 419), (570, 64, 419))
    for tag, slot, start, duration, creep in (
        ("empty", "1", 565.592, 1.15, False),
        ("warm", "2", 565.592, 1.15, False),
        ("slow-empty", "1", 567.00, 1.65, True),
    ):
        key(slot)
        pose = goto((start, 64.0, 419.493), tag + "-start", 0.13)
        for _ in range(5):
            turn(-90, 18, pose)
            pose = observe(tag + "-aim")
            if abs(pose["angle"][0] + 90) < 0.4 and abs(pose["angle"][1] - 18) < 0.5:
                break
        else:
            raise ValueError(pose)
        for motion, button in (("east", "w"), ("west", "s")):
            label = tag + "-" + motion
            before = observe(label + "-before")
            if creep:
                guard()
                x("keydown", "Shift_L")
            try:
                png = shot(label + "-start", 1.0, f2=True)
                video = path / (label + ".mkv")
                with (path / (label + "-ffmpeg.log")).open("xb") as log:
                    cmd = [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-n",
                        "-f",
                        "x11grab",
                        "-framerate",
                        "30",
                        "-window_id",
                        str(wid),
                        "-i",
                        display,
                        "-c:v",
                        "ffv1",
                        "-threads",
                        "3",
                        "-pix_fmt",
                        "bgr0",
                        str(video),
                    ]
                    with subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=log, stderr=log) as ff:
                        try:
                            time.sleep(0.9)
                            hold(button, duration)
                            time.sleep(0.75)
                        finally:
                            if ff.poll() is None:
                                ff.stdin.write(b"q\n")
                                ff.stdin.flush()
                            assert ff.wait(timeout=20) == 0
            finally:
                if creep:
                    x("keyup", "Shift_L")
            after = observe(label + "-after")
            a, b = before["xyz"][0], after["xyz"][0]
            assert min(a, b) < 567.6 and max(a, b) > 568.45 and (motion == "east") == bool(a < b), (a, b)
            assert abs(after["xyz"][2] - before["xyz"][2]) < 0.12 and abs(after["angle"][0] + 90) < 0.4
            results.setdefault("wetPassages", []).append(
                dict(label=label, before=before, after=after, video=video.name, photo=png)
            )
