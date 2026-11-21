"""Leave a warm torch under the oak and walk to the water with a soul torch."""
def capture(role,slot,point):
    key(slot)
    pose=aim(point,"look-"+role)
    results[role]={"pose":pose,"photo":shot(role,1.2,f2=True),"slot":slot}

def journey():
    goto(VIEW,"old-oak",.25)
    capture("old-oak","8",TRUNK)
    place_block((561,63,422),"warm-torch","2")
    capture("placed-torch","8",TRUNK)
    capture("lift-soul","3",TRUNK)
    walk_leg("view->water","carry-soul")
    capture("waters-edge","3",(549.5,62.8,417.5))
    walk_leg("view->water","back-to-oak",reverse=True)
    goto(VIEW,"return-to-placed-torch",.25)
    capture("both-on-return","3",TRUNK)
    capture("put-away-on-return","8",TRUNK)
    confirm=aim((561.5,63.35,422.5),"check-persisting-torch",want=(561,63,422))
    assert confirm["target"]==(561,63,422)
    results["savedTorch"]=confirm
    aim(TRUNK,"last-oak")
attempt(journey,"torch-and-shore-return",results)
