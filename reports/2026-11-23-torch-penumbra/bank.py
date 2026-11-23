"""Build a two-sided shore light from the two dirt blocks carried out of the hill."""
import math


def visit(world,first,results,trail,aim,goto,shot,key,click,mine,hotbar):
    assert math.dist(first["xyz"],(543.49,63,394.42))<.4
    bar=hotbar()
    assert bar["1"]=="minecraft:dirt" and bar["2"]=="minecraft:torch" and "4" not in bar
    trail.world=world
    assert trail.name(542,62,395)=="sand" and trail.name(541,63,395)=="soul_lantern"
    assert all(trail.name(542,y,395)=="air" for y in (63,64))
    def target(point,block,label):
        obs=aim(point,label,want=block,tries=8)
        assert obs["target"]==block,(label,obs)
        results.setdefault("confirmedTargets",{})[label]=block
    key("4")
    target((541.5,63.26,395.5),(541,63,395),"blue-before-screen")
    shot("blue-before-screen",1.5,f2=True)
    for y in (62,63):
        target((542.5,y+.98,395.5),(542,y,395),f"support-{y}")
        key("1");click("3");key("4")
    target((542.99,64.45,395.42),(542,64,395),"landward-face")
    shot("screen-before-torch",1.6,f2=True)
    key("2");click("3");key("4")
    target((543.12,64.57,395.5),(543,64,395),"east-wall-torch")
    shot("landward-torch",1.7,f2=True)
    pose=first
    for name,dest,point in [("along-the-shore",(540,63,392),(541.7,63.6,395.5)),
                            ("behind-the-light",(540,63,391),(542.2,63.9,395.4)),
                            ("bank-return",(543,63,394),(542.6,64.1,395.6))]:
        route=trail.build("meadow-lake-home",world,pose["xyz"],destination=dest)
        for i,wp in enumerate(route["waypoints"][1:]):
            pose=goto(wp,f"{name}-{i}",.26)
        aim(point,name,tries=8)
        shot(name,1.4,f2=True)
        results.setdefault("shoreViewpoints",[]).append({"label":name,"xyz":pose["xyz"],"route":route["waypoints"]})
    # Walk back out along the dry spit to see the two sides as the sky brightens.
    # The world clock, weather and exposure run normally throughout.
    dest=(539,63,391)
    route=trail.build("meadow-lake-home",world,pose["xyz"],destination=dest)
    for i,wp in enumerate(route["waypoints"][1:]):
        pose=goto(wp,f"morning-spit-{i}",.26)
    aim((543,64,395.5),"turn-back-on-spit",tries=8)
    shot("two-sided-marker",2.0,f2=True)
    aim((535.0,63.25,397.0),"over-the-lake",tries=8)
    shot("morning-water",2.0,f2=True)
    results["newScreen"]=[[542,63,395],[542,64,395]]
    results["wallTorch"]=[543,64,395]
