"""Walk downhill from the saved lantern camp to a naturally grown birch."""
import math

def walk(saved,first,results,trail,hotbar,aim,goto,shot,key,click):
    assert math.dist(first["xyz"],(593.508,71.,427.496))<.08
    assert hotbar()["2"]=="minecraft:torch"
    def route(origin,dest,label):
        plan=trail.build("stone-torch-niche",saved,origin,destination=dest)
        results[label+"Route"]=plan["waypoints"]
        result=None
        for i,p in enumerate(plan["waypoints"][1:]):
            result=goto(p,label+"-"+str(i),.22)
        assert result is not None and abs(result["xyz"][1]-dest[1])<.1
        return result
    base=route(first["xyz"],(584,64,422),"downhill")
    trunk=(583,64,424)
    lamp=(584,64,424)
    support=(584,63,424)
    assert trail.name(*trunk)=="birch_log" and trail.name(*support)=="grass_block" and trail.name(*lamp)=="air"
    def sight(target,point,label):
        pose=aim(point,label,want=target,tries=8)
        assert pose["target"]==target,(label,pose)
        return pose
    key("5")
    side=(583.82,64.58,424.04)
    sight(trunk,side,"birch-before")
    shot("birch-before",1.4,f2=True)
    key("2")
    sight(support,(584.48,63.985,424.49),"grass-beside-birch")
    click("3")
    key("5")
    sight(lamp,(584.5,64.42,424.5),"standing-torch")
    results["placedTorch"]=list(lamp)
    sight(trunk,side,"birch-after")
    shot("birch-lit",1.4,f2=True)
    route(base["xyz"],(581,64,425),"around-trunk")
    sight(trunk,(583.02,64.62,424.5),"unlit-side")
    shot("far-side",2.,f2=True)
    results["birch"]=list(trunk)
