"""Descend the surveyed natural staircase and compare the outside view with the torchlit stone."""
import json
import math
from pathlib import Path


def visit(results,aim,goto,shot,key,click,observe,*,mine=None):
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
    if mine is not None:
        cut_alcove(results,aim,goto,shot,key,click,mine)
    for i,point in enumerate(reversed(path[:-1])):goto(point,"ascend-"+str(i),.24)
    outside=observe("above-ground",keep=True)
    assert math.dist(outside["xyz"],path[0])<.45,outside
    results["outside"]=outside
    aim(path[-1],"look-back-into-cave")
    shot("back-in-forest",3,f2=True)

def cut_alcove(results,aim,goto,shot,key,click,mine):
    # One natural stone next to the first, warm floor torch. All input stays
    # inside this private survival window and checks the selected block first.
    # Stand clear of the grass block at (1667,93,1066) when aiming into the recess.
    goto((1666.35,93,1066.18),"step-to-shelf",.20)
    cell=(1667,93,1065)
    floor=(1667,92,1065)
    face=(1667.04,93.6,1065.7)
    socket=(1667.23,92.96,1065.39)
    wall=(1668.3,94.35,1064.6)
    key("1");aim(wall,"before-cut");shot("before-cut",1.4,f2=True)
    o=aim(face,"select-stone",want=cell)
    assert o["target"]==cell,o
    key("6");mine(1.45);key("1")
    o=aim(socket,"verify-new-floor",want=floor)
    assert o["target"]==floor,o
    results["minedStone"]=cell
    aim(wall,"bare-recess");shot("bare-recess",1.4,f2=True)
    o=aim(socket,"light-support",want=floor)
    assert o["target"]==floor,o
    key("3");click("3");key("1")
    o=aim((1667.5,93.3,1065.5),"placed-in-stone",want=cell)
    assert o["target"]==cell,o
    results["soulInAlcove"]=o
    aim(wall,"mixed-cave-light");shot("mixed-cave-light",2,f2=True)
