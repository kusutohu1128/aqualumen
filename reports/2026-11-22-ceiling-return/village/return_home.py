"""Walk back to the naturally generated spruce house and leave a soul torch at home."""
import json
import math
import sys

def visit(source,first,results,aim,goto,shot,key,click,observe,hotbar):
    sys.path.insert(0,str(source))
    from house_walk import enter
    inventory=hotbar()
    assert "1" not in inventory and inventory["3"]=="minecraft:soul_torch"
    steps=list(reversed(json.loads((source/"plains-route.json").read_text())["waypoints"]))
    idx=min(range(len(steps)),key=lambda i:math.dist(steps[i],first["xyz"]))
    key("1")
    aim((first["xyz"][0]+12,first["xyz"][1]+2,first["xyz"][2]-2),"revisit-plains")
    shot("plains",f2=True)
    for i,step in enumerate(steps[idx+1:],idx+1):
        goto(step,"road-"+str(i),.34)
        if i in (15,32):
            x,y,z=step
            aim((x+10,y+2.5,z-2),"east-toward-home")
            shot("road-"+str(i),f2=True)
    results["road"]=observe("return-to-porch",keep=True)
    door=(-902,70,576)
    centre=(-901.5,70.55,576.5)
    o=aim(centre,"porch-door")
    if o["target"] in (door,(door[0],door[1]+1,door[2])):click("3")
    results["entered"]=enter(aim,goto,shot,key,observe)
    point=(-902.5,72.25,578.8)
    key("1");aim(point,"lit-ceiling")
    shot("original-ceiling",f2=True)
    key("3");shot("held-soul-torch",f2=True)
    floor=(-902,69,578)
    support=aim((-901.5,69.98,578.5),"floor-for-torch",want=floor)
    assert support["target"]==floor,support
    click("3");key("1")
    torch=(-902,70,578)
    placed=aim((-901.5,70.3,578.5),"placed-soul-torch",want=torch)
    assert placed["target"]==torch,placed
    results["placed"]=placed
    aim(point,"lit-ceiling-again");shot("planted-soul-torch",f2=True)
    aim((-901.5,71.0,579.45),"window-and-placed-torch")
    shot("evening-at-home",f2=True)


def relight(results,aim,shot,key,click):
    """Open the archived ordinary world, remove its saved torch, and put it back."""
    point=(-902.5,72.25,578.8)
    tip=(-901.5,70.35,578.5)
    torch=(-902,70,578)
    floor=(-902,69,578)
    key("1")
    check=aim(tip,"find-saved-torch",want=torch)
    assert check["target"]==torch,check
    aim(point,"with-saved-torch");shot("reloaded-lit",f2=True)
    check=aim(tip,"touch-saved-torch",want=torch)
    assert check["target"]==torch
    click("1")
    check=aim((-901.5,69.98,578.5),"exposed-floor",want=floor)
    assert check["target"]==floor,check
    results["exposedFloor"]=check
    aim(point,"without-soul-torch");shot("removed",f2=True)
    key("3")
    check=aim((-901.5,69.98,578.5),"replace-on-floor",want=floor)
    assert check["target"]==floor,check
    click("3");key("1")
    check=aim(tip,"read-back-restored-torch",want=torch)
    assert check["target"]==torch,check
    results["restoredTorch"]=check
    aim(point,"after-replacing");shot("replaced",f2=True)


def move_window(results, aim, shot, key, click, mine, hotbar):
    """Close the original rear window and cut a new opening next to the front door."""
    inventory = hotbar()
    assert inventory.get("7") == "minecraft:wooden_axe" and inventory.get("8") == "minecraft:spruce_planks"
    rear = (-902, 71, 579)
    front = (-901, 71, 576)
    beam = (-902.5, 72.25, 578.8)

    def target(point, block, label):
        found = aim(point, label, want=block)
        assert found["target"] == block, (block, found)
        results[label] = found

    def compare(label):
        key("1")
        aim(beam, label + "-beam")
        shot(label + "-beam", f2=True)

    compare("original")
    target((-901.5, 71.55, 579.5), rear, "original-pane")
    shot("rear-window", 4, f2=True)
    # Hold camera position for a view-only control before changing the wall.
    aim(beam, "turn-away-from-snow")
    shot("back-to-beam", 5, f2=True)
    target((-901.5, 71.55, 579.5), rear, "return-to-pane")
    shot("second-look-at-snow", 4, f2=True)
    mine(.65)
    target((-901.5, 70.99, 579.4), (-902, 70, 579), "rear-sill")
    key("8")
    click("3")
    target((-901.5, 71.55, 579.5), rear, "closed-opening")
    compare("closed")
    key("7")
    target((-900.5, 71.55, 576.8), front, "front-log")
    mine(1.85)
    key("1")
    target((-900.5, 70.99, 576.55), (-901, 70, 576), "front-sill")
    aim((-900.5, 71.55, 576.8), "new-aperture")
    shot("front-window", f2=True)
    compare("relocated")


def see_window(results, aim, goto, shot, key, click, mine, observe):
    """Look in from the porch; board up and reopen the same one-block aperture."""
    key("1")
    door = (-902, 70, 576)
    test = aim((-901.5, 70.55, 576.5), "door-from-inside")
    if test["target"] in (door, (-902, 71, 576)):
        click("3")
    goto((-901.5, 69, 575.5), "outside-on-porch", .23)
    goto((-900.5, 69, 575.45), "east-stair", .23)
    goto((-900.5, 69, 574.4), "opposite-window", .15)
    results["exterior"] = observe("exterior-position", keep=True)
    window = (-901, 71, 576)
    centre = (-900.5, 71.50, 576.55)
    def look(label):
        key("1")
        found = aim(centre, label)
        results[label] = found
        shot(label, f2=True)
        return found["target"]

    assert look("outside-open") != window
    jamb = aim((-899.997, 71.45, 576.6), "east-jamb", want=(-900, 71, 576))
    assert jamb["target"] == (-900, 71, 576), jamb
    key("8")
    click("3")
    assert look("outside-boarded") == window
    key("7")
    mine(1.85)
    assert look("outside-reopened") != window
