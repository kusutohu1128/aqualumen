"""Record full display output in one stationary private client for all three shader paths."""
import math
from pathlib import Path
from PIL import Image


def walk(world, first, results, trail, aim, goto, shot, key, click, hotbar, folder):
    bar=hotbar()
    assert [bar[str(i)] for i in (6,7,8)]==["minecraft:wooden_pickaxe","minecraft:wooden_axe","minecraft:wooden_shovel"]
    torch=(566,64,419)
    support=(566,63,419)
    route=trail.build("oak-night-trail",world,first["xyz"],destination=(569,64,419))
    assert trail.name(*torch)=="torch" and trail.name(568,64,418)=="oak_log"
    key("7")
    for i,wp in enumerate(route["waypoints"][1:]):
        goto(wp,"approach-"+str(i),.2)
    camera=goto((569.68,64,420.02),"register-ground",.1)
    def group(label,point):
        pose=aim(point,label,tries=6)
        assert math.dist(pose["xyz"],camera["xyz"])<.03
        states=(("6","base",1),("7","leaf",2),("8","tiled",3),("8","tiled",3),("7","leaf",2),("6","base",1))
        for index,(slot,name,mode) in enumerate(states):
            key(slot)
            fn=f"{label}-{index}-{name}"
            shot(fn,1.4,f2=True)
            path=Path(folder)/(fn+"-ingame.png")
            with Image.open(path) as picture:
                stamp=picture.getpixel((2,picture.height-2))[:3]
            assert stamp==(74,mode,213),(label,slot,stamp)
        results.setdefault("displayGroups",[]).append(dict(label=label,pose=pose))
    def target(point,cell,label):
        assert aim(point,label,want=cell,tries=6)["target"]==cell
    ground=(569.4,64.,417.98)
    group("warm",ground)
    group("forest",(568.8,65.8,415.3))
    target((566.5,64.31,419.5),torch,"target-torch")
    click("1")
    target((566.5,63.99,419.5),support,"empty-socket")
    group("off",ground)
    target((566.5,63.99,419.5),support,"socket-soul");key("3");click("3")
    target((566.5,64.31,419.5),torch,"placed-soul")
    group("soul",ground)
