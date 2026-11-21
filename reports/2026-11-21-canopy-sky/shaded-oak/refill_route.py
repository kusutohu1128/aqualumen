"""Continue from below the saved oak, collect the dirt, and close the temporary path."""
def mine_side(x):
    cell = (x,62,422)
    key("8")
    target = aim((x+.005,62.45,422.5), "side-" + str(x), want=cell)
    assert target["target"] == cell, target
    for _ in range(3):
        dig(.78)
        after = observe("path-" + str(x) + "-opened")
        if after["target"] != cell:
            actions.append({"action": "open path", "cell": cell, "after": after})
            write(out / "actions.json",actions)
            return
    raise RuntimeError("Could not mine the confirmed block " + str(cell))


def refill():
    for x in (563,564):
        mine_side(x)
        goto((x+.45,62,422.5),"retrieve-" + str(x),.22)
    for z in (422.27,422.73):
        goto((564.5,62,z),"collect-at-edge",.12)
        time.sleep(.7)
    goto((562.45,62,422.5),"back-out",.25)
    for x in (564,563):
        place_block((x,62,422),"refill-path-" + str(x),"1")
    goto((561.5,63,423.5),"climb-out")
    place_block((562,62,422),"refill-path-562","1")
    for x in (560,561):
        place_block((x,62,421),"refill-old-hole-" + str(x),"1")
    # Vanilla middle-click brings a matching item from the inventory to the
    # hotbar in survival. Replant the poppy displaced while opening the path.
    key("1")
    flower = aim((560.5,63.28,423.5),"pick-poppy",want=(560,63,423))
    assert flower["target"] == (560,63,423), flower
    click("2")
    floor = aim((563.5,62.99,422.5),"plant-on-soil",want=(563,62,422))
    assert floor["target"] == (563,62,422), floor
    click("3")
    plant = aim((563.5,63.25,422.5),"replanted",want=(563,63,422))
    assert plant["target"] == (563,63,422), plant
    actions.append({"action":"replant poppy","cell":(563,63,422),"observation":plant})
    write(out / "actions.json",actions)
    goto(VIEW,"home")
    key("8")
    results["oak"] = subject("restored-trail")


attempt(refill, "refill-trail-and-replant", results)
