"""Travel from the oak post to two different lights on the natural shoreline."""
import math


def walk(world, first, results, trail, aim, goto, shot, key, click, mine, hotbar):
    bar=hotbar()
    assert [bar[k] for k in ("4","5","8")]==["minecraft:lantern","minecraft:soul_lantern","minecraft:wooden_shovel"]
    def travel(position,dest,label):
        route=trail.build("oak-opening",world,position,destination=dest)
        obs=first
        for i,wp in enumerate(route["waypoints"][1:]):
            obs=goto(wp,f"{label}-{i}",.27)
        assert math.dist(obs["xyz"],[dest[0]+.5,dest[1],dest[2]+.5])<.45
        results.setdefault("shoreRoute",[]).append(dict(to=label,route=route["waypoints"],arrived=obs))
        return obs
    def target(point,cell,label):
        obs=aim(point,label,want=cell,tries=6)
        assert obs["target"]==cell,(label,obs)
    def set_lantern(x,z,slot,label):
        target((x+.5,62.99,z+.5),(x,62,z),label+"-ground")
        key(slot);click("3");key("1")
        target((x+.5,63.28,z+.5),(x,63,z),label+"-placed")
    key("1")
    near=travel(first["xyz"],(558,63,420),"near-shore")
    assert trail.name(556,63,420)=="air" and trail.name(555,62,419)=="water"
    set_lantern(556,420,"4","warm")
    aim((554.7,63.15,420.4),"warm-on-bank",tries=5);shot("warm-on-bank",1.2,f2=True)
    far=travel(near["xyz"],(543,63,394),"sand-bank")
    assert trail.name(541,62,394)=="sand" and trail.name(540,62,394)=="water"
    key("8");target((541.5,62.99,394.5),(541,62,394),"edge-before")
    shot("sand-before",1.0,f2=True);mine(.60)
    key("1");aim((541.5,62.5,394.5),"opened-inlet",tries=4)
    shot("inlet-before-lamp",1.4,f2=True)
    set_lantern(541,395,"5","soul")
    aim((540.9,62.9,394.8),"blue-on-water",tries=6);shot("blue-on-water",1.4,f2=True)
    results["inlet"]=[541,62,394]
    results["shoreLights"]=[[556,63,420],[541,63,395]]
