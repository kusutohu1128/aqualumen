"""Cut a torch niche by the blue lantern, then view it from the open path."""
import math


def cut(first,results,aim,goto,shot,key,click,mine,hotbar):
    assert math.dist(first["xyz"],(599.529,71.,427.375))<.06
    inventory=hotbar()
    assert inventory["6"]=="minecraft:wooden_pickaxe" and inventory["2"]=="minecraft:torch"
    cell=(599,72,425)
    back=(599,72,424)
    def target(point,world_cell,label):
        pose=aim(point,label,want=world_cell,tries=8)
        assert pose["target"]==world_cell,(label,pose)
        return pose
    key("6")
    target((599.5,72.5,425.96),cell,"unworked-stone")
    shot("before-cut",1.,f2=True)
    mine(1.38)
    target((599.5,72.5,424.97),back,"back-of-niche")
    shot("cut-niche",1.,f2=True)
    key("2")
    click("3")
    key("5")
    # The lit torch occupies the freshly opened voxel, on its northern wall.
    target((599.5,72.45,425.15),cell,"mounted-torch")
    shot("lit-niche",2.,f2=True)
    results["mountedTorch"]=list(cell)
    goto((593.5,71.,427.5),"step-into-daylight",.20)
    aim((599.6,71.9,426.2),"look-back-at-camp",tries=8)
    shot("camp-from-path",2.,f2=True)
