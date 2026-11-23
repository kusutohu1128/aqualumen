"""Gather a red flower in the existing snowy village survival world."""
import json
from pathlib import Path
import sys
from flower_route import FLOWER,plan

HERE=Path(__file__).resolve().parent
def forage(saved,results,aim,goto,shot,key,click,observe):
    route=plan(saved)
    assert route==dict(json.loads((HERE/"flower-route.json").read_text()),flower=FLOWER)
    sys.path.insert(0,str(HERE.parent/"2026-11-21-settlement-light/playable"))
    from house_walk import enter
    def door():
        d=aim((-901.5,70.55,576.5),"spruce-door",tries=6)
        if d["target"] in ((-902,70,576),(-902,71,576)) and d["open"] is False:
            click("3")
    key("1")
    door()
    goto((-901.5,69,575.5),"leave-the-house",.23)
    goto((-900.5,69,575.45),"east-stair",.23)
    for i,p in enumerate(route["waypoints"]):goto(p,"poppy-trail-"+str(i),.24)
    for dx,dz in ((.5,.5),(.35,.4),(.65,.6),(.65,.35),(.35,.65)):
        at=aim((FLOWER[0]+dx,FLOWER[1]+.27,FLOWER[2]+dz),"poppy",tries=5)
        if at["target"]==FLOWER:break
    assert at["target"]==FLOWER,at
    shot("poppy-in-snow",1.2,f2=True)
    click("1")
    goto((FLOWER[0]+.5,FLOWER[1],FLOWER[2]+.5),"pick-up-poppy",.18)
    aim((FLOWER[0]+.5,FLOWER[1]-.008,FLOWER[2]+.5),"picked-flower")
    results["pickedFlower"]=list(FLOWER)
    for i,p in enumerate(reversed(route["waypoints"])):goto(p,"return-with-poppy-"+str(i),.25)
    door()
    enter(aim,goto,shot,key,observe)
    results["returnedInside"]=observe("back-at-home",keep=True)
