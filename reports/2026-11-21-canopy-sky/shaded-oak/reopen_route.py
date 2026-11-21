"""Reopen the walked woodland branch with its two saved soil screens."""
def remove_saved(cell, point, name):
    key("8")
    before = aim(point, "target-" + name, want=cell)
    assert before["target"] == cell, before
    dig(.62)
    after = observe("removed-" + name)
    assert after["target"] != cell, after
    actions.append({"action": "mine " + name, "cell": cell, "before": before, "after": after})
    write(out / "actions.json", actions)


def sight(role):
    key("8")
    pose = aim((564.005, 63.25, 423.5), "view-" + role)
    results[role] = {"pose": pose, "image": shot(role, 1.0, f2=True)}


def restore():
    # A low ray reaches the wall below the westernmost leaf. Aiming at the
    # top of the wall would hit the real leaf in front of it.
    sight("saved-walls")
    remove_saved((564,63,423),(564.005,63.25,423.5),"south-screen")
    sight("south-open")
    goto((561.5,63,421.5),"north-view")
    remove_saved((564,63,421),(564.005,63.25,421.5),"north-screen")
    # The crown leaves only a one-block gap beneath it. Dig a temporary
    # shallow path, walk under the leaves and collect the two dropped blocks.
    for x in (562,563,564):
        plant = (x,63,422)
        if x == 563:
            target = aim((563.5,63.25,422.5),"poppy",want=plant)
            if target["target"] == plant:
                click("1")
        remove_saved((x,62,422),(x+.5,62.99,422.5),"path-" + str(x))
        goto((x+.5,62,422.5),"pickup-" + str(x),.27)
    time.sleep(1.0)
    goto((562.5,62,422.5),"leave-path",.25)
    for x in (564,563):
        place_block((x,62,422),"replace-path-" + str(x),"1")
    goto((561.5,63,423.5),"exit-path")
    place_block((562,62,422),"replace-path-562","1")
    for x in (560,561):
        place_block((x,62,421),"refill-donor-" + str(x),"1")
    goto(VIEW,"return-to-oak")
    results["open-oak"] = subject("open-oak")


attempt(restore, "reopen-remove-screens-and-refill", results)
