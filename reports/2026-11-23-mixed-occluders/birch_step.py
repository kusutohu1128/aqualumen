"""Use the last carried dirt block to extend the terrain at the previously lit birch."""
import math

def place(first,results,hotbar,aim,goto,shot,key,click):
    assert math.dist(first["xyz"],(581.515,64.,425.484))<.08
    assert hotbar()["1"]=="minecraft:dirt"
    for i,waypoint in enumerate([(582.5,64,424.5),(582.5,64,423.5),(583.5,64,423.5),(584.5,64,422.5)]):
        goto(waypoint,"north-of-birch-"+str(i),.20)
    support=(583,63,423)
    step=(583,64,423)
    bark=(583,65,424)
    def sight(block,point,label):
        pose=aim(point,label,want=block,tries=8)
        assert pose["target"]==block,(block,pose)
    key("5")
    sight(bark,(583.55,65.38,424.015),"before-step")
    shot("before-step",1.5,f2=True)
    key("1")
    sight(support,(583.49,63.99,423.51),"soil-support")
    click("3")
    key("5")
    sight(step,(583.51,64.58,423.015),"new-dirt-step")
    sight(bark,(583.55,65.38,424.015),"after-step")
    shot("after-step",1.5,f2=True)
    goto((585.5,64,422.5),"around-east",.23)
    goto((585.5,64,424.5),"torch-side",.23)
    sight((584,64,424),(584.51,64.41,424.5),"previous-torch")
    shot("torch-and-step",1.5,f2=True)
    results["placedSoil"]=list(step)
    results["torchStillPresent"]=[584,64,424]
