"""Travel outside the saved torch's 14-block reach in ordinary survival."""
def picture(role,slot,target):
    key(slot)
    o=aim(target,"look-"+role)
    results[role]={"pose":o,"photo":shot(role,1.0,f2=True),"slot":slot}
def excursion():
    warm=(561,63,422)
    o=aim((561.5,63.35,422.5),"saved-warm-torch",want=warm)
    assert o["target"]==warm
    picture("saved-fire","8",TRUNK)
    key("3")
    walk_leg("view->water","via-shore")
    ridge=plan["legs"]["water->cave"]["waypoints"][:8]
    for i,point in enumerate(ridge[1:]):
        goto(point,"east-trail-"+str(i))
    near_ground=(576.5,62.99,421.5)
    picture("outside-with-soul","3",near_ground)
    picture("outside-empty","8",near_ground)
    key("3")
    for i,point in enumerate(ridge[-2::-1]):
        goto(point,"west-trail-"+str(i))
    walk_leg("view->water","back-to-tree",reverse=True)
    goto(VIEW,"by-the-oak",.25)
    picture("warm-on-return","8",TRUNK)
    o=aim((561.5,63.35,422.5),"returned-warm-torch",want=warm)
    assert o["target"]==warm
    results["savedTorch"]=o
    aim(TRUNK,"save-at-oak")
attempt(excursion,"outside-the-lamp-range-and-back",results)
