"""Carry two lanterns from the saved shoreline to the approach to the grazing meadow."""

import math


def walk(world, first, results, trail, aim, goto, shot, key, click, hotbar):
    assert hotbar()["4"] == "minecraft:lantern" and hotbar()["5"] == "minecraft:soul_lantern"
    pose = first
    key("1")
    for name, stand, cell, slot in (
        ("ridge-light", (562, 64, 386), (560, 64, 385), "4"),
        ("meadow-light", (585, 64, 363), (587, 64, 362), "5"),
    ):
        route = trail.build("lakeside-lanterns", world, pose["xyz"], destination=stand)
        results.setdefault("pastureRoute", []).append(route["waypoints"])
        for i, step in enumerate(route["waypoints"][1:]):
            pose = goto(step, f"{name}-walk-{i}", 0.30)
        assert math.dist(pose["xyz"], (stand[0] + 0.5, stand[1], stand[2] + 0.5)) < 0.5
        x, y, z = cell
        assert trail.name(x, y, z) == "air" and trail.name(x, y - 1, z) == "grass_block"
        o = aim((x + 0.5, y - 0.01, z + 0.5), name + "-ground", want=(x, y - 1, z), tries=7)
        assert o["target"] == [x, y - 1, z] or tuple(o["target"]) == (x, y - 1, z)
        key(slot)
        click("3")
        key("1")
        o = aim((x + 0.5, y + 0.25, z + 0.5), name + "-placed", want=cell, tries=7)
        assert tuple(o["target"]) == cell
        shot(name, 1.2, f2=True)
        results.setdefault("pastureLights", []).append(list(cell))
