"""Walk from the window to the open snowfield and light the trail in survival."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
VILLAGE=HERE.parent/"2026-11-22-ceiling-return/village"
SOURCE=VILLAGE/"red-window-porch-light"
LANTERN=(-896,71,508)

def mark_trail(world, results, aim, goto, shot, key, click, observe):
    sys.path.insert(0,str(HERE.parent/"2026-11-21-rain-eaves/fixture"))
    from anvil import World
    source=World(world)
    assert source.block(*LANTERN)=="minecraft:air"
    assert source.block(-896,70,508).startswith("minecraft:grass_block")
    route=json.loads((HERE.parent/"2026-11-23-stained-panes/flower-route.json").read_text())["waypoints"]
    sys.path.insert(0,str(HERE.parent/"2026-11-21-settlement-light/playable"))
    from house_walk import enter
    def open_door():
        state=aim((-901.5,70.55,576.5),"village-door",tries=6)
        if state["target"] in ((-902,70,576),(-902,71,576)) and state["open"] is False: click("3")
    key("7")
    open_door()
    goto((-901.5,69,575.5),"from-house",.23)
    goto((-900.5,69,575.45),"east-stair",.23)
    for i,p in enumerate(route):
        goto(p,"snowfield-out-"+str(i),.25)
        if i==13:
            aim((-901,72,576),"house-on-the-horizon")
            shot("village-from-the-road",1.2,f2=True)
    foot=(-895.5,70.99,508.5)
    before=aim(foot,"trail-marker-site",want=(-896,70,508),tries=6)
    assert before["target"]==(-896,70,508),before
    shot("snow-before-light",1.2,f2=True)
    key("4")
    click("3")
    key("7")
    target=aim((-895.5,71.31,508.5),"snowfield-lantern",want=LANTERN,tries=6)
    assert target["target"]==LANTERN,target
    shot("snow-trail-lantern",1.2,f2=True)
    results["trailLantern"]=list(target["target"])
    for i,p in enumerate(reversed(route[:-1])):
        goto(p,"snowfield-return-"+str(i),.25)
    open_door()
    enter(aim,goto,shot,key,observe)
    aim((-900.5,71.45,576.5),"home-window")
    shot("home-after-the-snowfield",1.5,f2=True)
    results["returnedInside"]=observe("home-again",keep=True)
