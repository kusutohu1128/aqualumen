"""Set a soul torch on the saved soil step and revisit both sides of the birch."""
import math


def place(first,results,hotbar,aim,goto,shot,key,click):
    assert math.dist(first["xyz"],(585.49,64.,424.44))<.12
    assert hotbar().get("3")=="minecraft:soul_torch" and "1" not in hotbar()

    def sight(block,point,label):
        observed=aim(point,label,want=block,tries=8)
        assert observed["target"]==block,(label,observed)

    key("1")
    sight((584,64,424),(584.5,64.38,424.5),"warm-light-on-east")
    goto((585.5,64,422.5),"north-east-of-step",.23)
    trunk=(583,65,424)
    bark=(583.83,65.68,424.025)
    sight(trunk,bark,"one-light-on-the-birch")
    shot("one-light",1.3,f2=True)
    sight((583,64,423),(583.69,64.992,423.34),"top-of-soil-step")
    key("3")
    click("3")
    key("1")
    sight((583,65,423),(583.50,65.38,423.50),"new-soul-torch")
    sight(trunk,bark,"two-lights-on-the-birch")
    shot("two-lights",1.3,f2=True)
    goto((584.5,64,422.5),"near-north-torch",.23)
    sight((583,65,423),(583.5,65.39,423.5),"north-light")
    shot("blue-flame",1.1,f2=True)
    goto((585.5,64,422.5),"round-the-birch",.23)
    goto((585.5,64,424.5),"east-flame",.23)
    sight((584,64,424),(584.50,64.4,424.50),"warm-light-still-standing")
    shot("east-flame",1.3,f2=True)
    results["raisedSoulTorch"]=[583,65,423]
    results["warmTorch"]=[584,64,424]
