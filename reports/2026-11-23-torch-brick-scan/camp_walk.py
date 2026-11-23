"""Carry a torch back up the hillside and mark the entrance of the old stone camp."""
import math


def return_to_camp(saved, first, results, trail, hotbar, aim, goto, shot, key, click):
    assert math.dist(first["xyz"], (585.49, 64., 424.45)) < .12
    assert hotbar()["2"] == "minecraft:torch" and "1" not in hotbar()
    route = trail.build("raised-soul-torch", saved, first["xyz"], destination=(593, 71, 427))
    results["uphillRoute"] = route["waypoints"]
    marker = (593, 71, 426)
    assert trail.name(*marker) == "air" and trail.name(593, 70, 426) == "grass_block"

    def target(cell, point, label):
        read = aim(point, label, want=cell, tries=8)
        assert read["target"] == cell, (label, read)

    key("1")
    target((584, 64, 424), (584.5, 64.38, 424.5), "east-side-flame")
    shot("birch-at-departure", 1.2, f2=True)
    key("2")
    for i, point in enumerate(route["waypoints"][1:]):
        pose = goto(point, f"climb-{i}", .22)
        assert abs(pose["xyz"][1] - point[1]) < .65
    target((593, 70, 426), (593.45, 70.995, 426.45), "grass-at-entrance")
    click("3")
    key("1")
    target(marker, (593.5, 71.35, 426.5), "new-entrance-light")
    shot("entrance-light", 1.2, f2=True)
    results["entranceTorch"] = list(marker)
    goto((598.5, 71., 427.5), "under-stone-overhang", .21)
    wall = (599, 72, 425)
    point = (599.50, 72.43, 425.17)
    target(wall, point, "niche-empty-hand")
    shot("niche-empty-hand", 1.3, f2=True)
    key("2")
    target(wall, point, "niche-held-torch")
    shot("niche-held-torch", 1.3, f2=True)
    key("1")
    aim((593.5, 71.45, 426.5), "look-back-to-the-trail", tries=8)
    shot("path-from-overhang", 1.3, f2=True)
    results["nicheTorch"] = list(wall)


def sample_lamps(first, results, hotbar, aim, shot, key, turn, observe):
    """Repeat the hand switch at one fixed view of the niche in a diagnostic save copy."""
    assert math.dist(first["xyz"], (598.439, 71., 427.487)) < .03
    assert hotbar()["2"] == "minecraft:torch" and "1" not in hotbar()
    wall = (599, 72, 425)
    read = aim((599.50, 72.43, 425.17), "repeated-niche-view", want=wall, tries=9)
    assert read["target"] == wall
    # Use the exact F3 heading from the uninstrumented walk for registered pixel regions.
    yaw, pitch = -155.4, 4.2
    for _ in range(4):
        if max(abs(read["angle"][0] - yaw), abs(read["angle"][1] - pitch)) <= .11:
            break
        turn(yaw, pitch, read)
        read = observe("align-stone-niche")
    assert read["target"] == wall and max(abs(read["angle"][0] - yaw), abs(read["angle"][1] - pitch)) <= .16
    results["camera"] = read
    for index, (slot, name) in enumerate((("1","empty"), ("2","held"), ("1","empty"))):
        key(slot)
        for repeat in range(3):
            shot(f"sample-{index}-{name}-{repeat}", 8.5 if repeat == 0 else 1.2, f2=True)
