"""Walk from the close oak to a natural one-block rise and mark the path in survival."""
import math


def night_walk(first, world, results, trail, hotbar, aim, goto, turn, hold, observe, shot, key, click, elapsed):
    route = trail.build("two-flames-oak-r2", world, first["xyz"], destination=(562,63,419))
    assert hotbar()["2"] == "minecraft:torch"
    assert trail.name(561,64,418) == "oak_log" and trail.name(564,63,419) == "grass_block"
    assert trail.name(566,64,419) == "air" and trail.name(566,63,419) == "grass_block"
    key("2")
    for i, point in enumerate(route["waypoints"][1:]):
        goto(point, "approach-oak-"+str(i), .16)
    oak = aim((561.95,64.68,418.97), "close-wood", want=(561,64,418))
    assert oak["target"] == (561,64,418), oak
    results["closeOak"] = oak
    shot("close-wood", 8.5, f2=True)
    # Keep debug text closed throughout the turn and the continuous ascent.
    px, py, pz = oak["xyz"]
    target = (564.02,63.75,419.5)
    dx, dz = target[0]-px, target[2]-pz
    heading = math.degrees(math.atan2(-dx,dz))
    pitch = math.degrees(math.atan2(py+1.62-target[1], math.hypot(dx,dz)))
    yaw = oak["angle"][0]
    results["turnStart"] = elapsed()
    while abs((heading-yaw+180)%360-180) > 68:
        yaw += math.copysign(68, (heading-yaw+180)%360-180)
        turn(yaw, pitch, oak)
        oak = dict(oak, angle=[yaw, pitch])
    turn(heading, pitch, oak)
    results["stepRevealed"] = elapsed()
    results["walkStart"] = elapsed()
    hold("w", .90)
    results["walkEnd"] = elapsed()
    landed = observe("reached-raised-path", keep=True)
    results["landing"] = landed
    assert 564 <= landed["xyz"][0] < 567.4 and abs(landed["xyz"][1]-64)<.05, landed
    shot("above-step", 1.8, f2=True)
    # Stand clear of the placement voxel. A saved torch records the new waymark.
    goto((565.45,64,419.5), "beside-waymark", .19)
    support = aim((566.5,63.98,419.5), "waymark-support", want=(566,63,419))
    assert support["target"] == (566,63,419), support
    click("3")
    key("1")
    marker = aim((566.5,64.36,419.5), "saved-waymark", want=(566,64,419))
    assert marker["target"] == (566,64,419), marker
    results["marker"] = marker
    shot("waymark", 3.0, f2=True)
