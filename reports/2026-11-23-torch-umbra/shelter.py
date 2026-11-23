"""Enter the low overhang below the grazing meadow and build a two-colour lamp recess in survival."""

import math


def explore(world, first, results, trail, aim, goto, shot, key, click, mine, hotbar):
    inventory = hotbar()
    assert inventory["8"] == "minecraft:wooden_shovel"
    assert inventory["4"] == "minecraft:lantern" and inventory["5"] == "minecraft:soul_lantern"
    stand = (620, 65, 377)
    route = trail.build("lakeside-to-meadow", world, first["xyz"], destination=stand)
    assert trail.name(620, 67, 377) in ("dirt", "grass_block")
    assert [trail.name(621, y, 377) for y in (64, 65, 66, 67)] == ["dirt", "dirt", "dirt", "grass_block"]
    assert trail.name(620, 65, 378) == "air" and trail.name(620, 64, 378) not in trail.free
    results["shelterRoute"] = route["waypoints"]
    key("2")
    for i, step in enumerate(route["waypoints"][1:], 1):
        pose = goto(step, f"under-meadow-{i}", .27)
        if i == 11:
            aim((620.5, 67, 376.5), "slope")
            shot("hillside", 1.2, f2=True)
    assert math.dist(pose["xyz"], (620.5, 65, 377.5)) < .5

    def target(point, cell, tag):
        view = aim(point, tag, want=cell, tries=8)
        assert view["target"] == cell, (tag, view)
        return view

    key("1")
    pocket = (621, 65, 377)
    target((621.02, 65.57, 377.51), pocket, "earth-face")
    shot("earth-before", 1.8, f2=True)
    key("8")
    mine(.50)
    key("1")
    target((621.35, 64.98, 377.5), (621, 64, 377), "recess-floor")
    key("5")
    click("3")
    key("1")
    results["blueSocket"] = target((621.5, 65.30, 377.5), pocket, "blue-in-recess")
    shot("blue-recess", 2.4, f2=True)
    target((620.5, 64.98, 378.5), (620, 64, 378), "warm-on-lip")
    key("4")
    click("3")
    key("1")
    results["warmOnLip"] = target((620.5, 65.30, 378.5), (620, 65, 378), "warm-in-doorway")
    aim((621.2, 65.35, 377.86), "two-colours", tries=6)
    shot("two-colours", 2.4, f2=True)


def return_to_lake(world, first, results, trail, aim, goto, shot, key, click, mine, hotbar):
    assert hotbar()["8"] == "minecraft:wooden_shovel"
    assert math.dist(first["xyz"], (620.5, 65, 377.5)) < .5

    def target(point, cell, label):
        view = aim(point, label, want=cell, tries=8)
        assert view["target"] == cell, (label, view)
        return view

    # Keep both lanterns in the save and cut a player-sized path beside them.
    target((620.5,65.5,376.92), (620,65,376), "select-north-exit")
    key("8")
    mine(.60)
    key("1")
    target((620.5,64.98,376.5), (620,64,376), "exit-floor")
    goto((620.5,65,376.5), "through-new-exit", .22)
    pose = goto((620.5,66,375.5), "climb-to-grass", .25)
    assert abs(pose["xyz"][1]-66)<.1
    results["dugExit"] = [620,65,376]
    aim((620.7,65.52,377.55), "look-back-at-shelter", tries=8)
    shot("outside-shelter", 2, f2=True)

    for label, stand, lamp in (("meadow-guide",(585,64,363),(587,64,362)),
                               ("ridge-guide",(562,64,386),(560,64,385)),
                               ("lake-guide",(543,63,394),(541,63,395))):
        key("2")
        route=trail.build("meadow-shelter",world,pose["xyz"],destination=stand)
        results.setdefault("homewardRoute", []).append(route["waypoints"])
        for i, step in enumerate(route["waypoints"][1:],1):
            pose=goto(step,f"{label}-{i}",.30)
        lx,ly,lz=lamp
        key("1")
        results.setdefault("rediscovered",[]).append(target((lx+.5,ly+.28,lz+.5), lamp, label))
        shot(label, 2.0, f2=True)
    aim((541.5,62.6,392.0),"along-the-inlet",tries=8)
    shot("lake-return", 2.4, f2=True)
