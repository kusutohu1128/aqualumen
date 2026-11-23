"""Look at the existing porch lights from two positions inside the saved house."""
def visit_pane(results,aim,goto,shot,key,click,observe,x,guard_ok):
    key("7")
    start=observe("house-window-start",keep=True)
    assert abs(start["xyz"][0]+901.5)<.35 and abs(start["xyz"][2]-577.3)<.35
    torch=(-899.54,71.52,575.70)
    door=aim(torch,"check-window-sightline")
    if door["target"]==(-902,71,576) and door["open"] is True:
        click("3")
        results["closedDoor"]=True
    pane=(-901,71,576)
    def look(point,label):
        seen=aim(point,label,want=pane,tries=6)
        assert seen["target"]==pane,(label,seen)
        shot(label,1.2,f2=True)
        return seen
    results["torchThroughGlass"]=look(torch,"porch-torch-through-red-window")
    results["lanternThroughGlass"]=look((-899.50,70.74,575.50),"porch-lantern-through-red-window")
    guard_ok()
    x("keydown","Shift_L")
    try:
        goto((-901.5,70,578.35),"step-back-from-window",.25)
    finally:
        x("keyup","Shift_L")
    results["secondView"]=look((-900.48,71.55,576.50),"red-window-from-inside")
    results["returnedInside"]=observe("house-window-finish",keep=True)

def view_street(results,aim,goto,shot,key,click,observe,x,guard_ok):
    key("7")
    # The full log below this window really does hide the low porch lantern.
    sill=aim((-899.5,70.74,575.5),"low-lantern-behind-sill",want=(-901,70,576),tries=6)
    assert sill["target"]==(-901,70,576)
    results["sill"]=sill
    shot("sill-in-front-of-low-porch-lantern",1.2,f2=True)
    # This separate hanging lantern faces the street beyond the porch. Its
    # saved block and the intervening red pane are checked independently.
    hanging=aim((-895.5,72.58,571.5),"street-lantern-through-window",want=(-901,71,576),tries=6)
    assert hanging["target"]==(-901,71,576)
    results["hangingLantern"]=hanging
    shot("hanging-street-lantern-through-red-glass",1.5,f2=True)
    guard_ok()
    x("keydown","Shift_L")
    try:
        goto((-901.5,70,578.35),"step-back-from-window",.25)
    finally:
        x("keyup","Shift_L")
    pane=aim((-900.5,71.48,576.5),"window-from-back-of-room",want=(-901,71,576),tries=6)
    assert pane["target"]==(-901,71,576)
    results["secondView"]=pane
    shot("red-window-from-back-of-room",1.2,f2=True)
    results["returnedInside"]=observe("inside-after-window-visit",keep=True)

def porch_to_window(results,aim,goto,shot,key,click,observe,x,guard_ok):
    """Return from the saved porch and follow the actual foreground block."""
    key("7")
    door=aim((-901.5,71.15,576.5),"find-door-from-porch")
    if door["target"] in ((-902,70,576),(-902,71,576)) and door["open"] is False:
        click("3")
    aim((-895.5,72.58,571.5),"street-lantern-before-entry")
    shot("street-lamp-from-outside",1.2,f2=True)
    # Enter via the east half-stair. Let Minecraft step up naturally:
    # jumping at the centre hits the spruce eaves above the lower step.
    goto((-900.5,68.9,574.4),"reach-east-side",.25)
    goto((-900.5,68.9,575.45),"take-east-half-stair",.25)
    guard_ok()
    x("keydown","Shift_L")
    try:
        goto((-901.5,68.9,575.5),"cross-upper-stair",.24)
        door=aim((-901.5,71.15,576.5),"check-door-at-entry")
        if door["target"] in ((-902,70,576),(-902,71,576)) and door["open"] is False:
            click("3")
        goto((-901.5,68.9,577.55),"return-inside-with-view",.26)
    finally:
        x("keyup","Shift_L")
    # From this spot an open door may screen the pane. Aim at the street
    # lantern, close the door if struck, then verify the pane under the reticle.
    target=(-895.5,72.58,571.5)
    seen=aim(target,"street-light-from-the-room",tries=4)
    if seen["target"] in ((-902,70,576),(-902,71,576)) and seen["open"] is True:
        click("3")
    seen=aim(target,"street-light-through-pane",want=(-901,71,576),tries=4)
    if seen["target"]!=(-901,71,576):
        # Aim at the centre of the pane from the current position; a wide
        # view includes the street. Record which sightline was obtained.
        seen=aim((-900.5,71.5,576.5),"centre-of-house-window",want=(-901,71,576),tries=5)
        results["centredOnPane"]=True
    assert seen["target"]==(-901,71,576),seen
    results["windowSightline"]=seen
    shot("the-street-through-the-red-window",1.4,f2=True)
    results["returnedInside"]=observe("home-after-viewing-window",keep=True)
    assert results["returnedInside"]["xyz"][2]>577

def through_door(results,aim,goto,shot,key,click,observe,x,guard_ok):
    key("7")
    at=observe("upper-porch-before-entry",keep=True)
    assert abs(at["xyz"][1]-70)<.01 and abs(at["xyz"][2]-575.7)<.25,at
    door=aim((-901.5,71.1,576.45),"check-upper-door")
    if door["target"] in ((-902,70,576),(-902,71,576)) and door["open"] is False:click("3")
    guard_ok()
    x("keydown","Shift_L")
    try:
        # The open door occupies 3/16 of the eastern edge. Leave room for
        # the player's full 0.6 m-wide body before advancing through it.
        goto((-901.645,69,575.7),"clear-the-hinge-side",.055)
        goto((-901.645,69,577.40),"walk-straight-through-door",.20)
    finally:
        x("keyup","Shift_L")
    point=(-895.5,72.58,571.5)
    seen=aim(point,"look-towards-street-lantern")
    if seen["target"] in ((-902,70,576),(-902,71,576)) and seen["open"] is True:click("3")
    seen=aim(point,"sightline-past-porch",want=(-901,71,576),tries=4)
    if seen["target"]!=(-901,71,576):
        seen=aim((-900.5,71.45,576.5),"find-red-glass",want=(-901,71,576),tries=5)
        results["centredOnPane"]=True
    assert seen["target"]==(-901,71,576),seen
    results["windowSightline"]=seen
    shot("the-street-through-the-red-window",1.3,f2=True)
    results["returnedInside"]=observe("inside-with-closed-window",keep=True)
    assert results["returnedInside"]["xyz"][2]>577
