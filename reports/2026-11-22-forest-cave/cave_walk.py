"""Descend the surveyed natural staircase and compare the outside view with the torchlit stone."""
import json
import math
from pathlib import Path


def visit(results,aim,goto,shot,key,click,observe):
    route=json.loads((Path(__file__).parent/"route.json").read_text())
    path=[(x+.5,y,z+.5) for x,y,z in route["waypoints"]]
    key("1")
    aim(path[-1],"entrance-from-trees")
    shot("rain-at-entrance",2,f2=True)
    for i,point in enumerate(path[1:],1):goto(point,"descend-"+str(i),.22)
    deep=observe("under-stone",keep=True)
    assert math.dist(deep["xyz"],path[-1])<.45,deep
    results["inside"]=deep
    x,y,z=path[-1]
    stone=(x+1.1,y+1.45,z-2.4)
    sky=(x+2.7,y+1.62+8.4,z+10)
    aim(stone,"unlit-stone")
    for slot,name in (("1","unlit"),("2","warm"),("3","soul"),("1","empty-again")):
        key(slot)
        shot(name,3,f2=True)
    for point,name in ((sky,"opening"),(stone,"stone-after-opening"),(sky,"opening-again")):
        results[name]=aim(point,name)
        shot(name,5,f2=True)
    cell=(1666,93,1065)
    floor=(1666,92,1065)
    o=aim((1666.5,92.99,1065.5),"torch-support",want=floor)
    assert o["target"]==floor,o
    key("2");click("3");key("1")
    placed=aim((1666.5,93.3,1065.5),"saved-flame",want=cell)
    assert placed["target"]==cell,placed
    results["placed"]=placed
    aim(stone,"warm-wall")
    shot("placed-warm",3,f2=True)
    aim(sky,"toward-rain")
    shot("rain-over-torch",3,f2=True)
    for i,point in enumerate(reversed(path[:-1])):goto(point,"ascend-"+str(i),.24)
    outside=observe("above-ground",keep=True)
    assert math.dist(outside["xyz"],path[0])<.45,outside
    results["outside"]=outside
    aim(path[-1],"look-back-into-cave")
    shot("back-in-forest",3,f2=True)
