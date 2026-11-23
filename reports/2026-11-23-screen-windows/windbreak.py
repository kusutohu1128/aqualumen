"""Add a glass screen beside the lantern, then look back through it at dusk."""
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
CELLS=((-896,71,507),(-895,71,507))

def build_screen(world,results,aim,goto,shot,key,click,mine,observe):
    sys.path.insert(0,str(HERE.parent/"2026-11-21-rain-eaves/fixture"))
    from anvil import World
    w=World(world)
    assert w.block(-896,71,508).startswith("minecraft:lantern")
    for x,y,z in CELLS:
        assert w.block(x,y-1,z).startswith("minecraft:grass_block")
        assert w.block(x,y,z).split("[")[0] in ("minecraft:air","minecraft:snow")
    assert w.block(-895,70,508).startswith("minecraft:grass_block")
    sys.path.insert(0,str(HERE.parent/"2026-11-21-settlement-light/playable"))
    from house_walk import enter
    route=json.loads((HERE.parent/"2026-11-23-stained-panes/flower-route.json").read_text())["waypoints"]
    def door():
        rec=aim((-901.5,70.55,576.5),"look-at-door",tries=6)
        if rec["target"] in ((-902,70,576),(-902,71,576)) and rec["open"] is False:click("3")
    key("7")
    door()
    goto((-901.5,69,575.5),"onto-the-porch",.23)
    goto((-900.5,69,575.45),"porch-steps",.23)
    for i,pos in enumerate(route):goto(pos,"dusk-trail-"+str(i),.25)
    goto((-894.5,72,509.5),"east-of-lantern",.2)
    aim((-895.5,71.35,508.5),"look-at-lantern")
    shot("lantern-before-glass",1.3,f2=True)
    for x,y,z in CELLS:
        ground=(x,y-1,z)
        at=(x+.5,y-.012,z+.5)
        key("7")
        rec=aim(at,"look-at-snow",tries=6)
        if rec["target"]==(x,y,z):
            mine(.28)
        rec=aim(at,"exposed-ground",want=ground,tries=6)
        assert rec["target"]==ground,rec
        key("1")
        click("3")
        key("7")
        pane=aim((x+.5,y+.4,z+.5),"placed-glass",want=(x,y,z),tries=6)
        assert pane["target"]==(x,y,z),pane
    results["trailPanes"]=[list(pos) for pos in CELLS]
    ground=(-895,70,508)
    point=(-894.5,70.988,508.5)
    rec=aim(point,"torch-site",tries=6)
    if rec["target"]==(-895,71,508): mine(.28)
    rec=aim(point,"torch-support",want=ground,tries=6)
    assert rec["target"]==ground,rec
    key("2")
    click("3")
    key("7")
    torch=aim((-894.5,71.40,508.5),"torch-by-red-pane",want=(-895,71,508),tries=6)
    assert torch["target"]==(-895,71,508),torch
    results["trailTorch"]=list(torch["target"])
    around=((-892.5,72.,509.5),(-892.5,71.,507.5),(-893.5,71.,505.5))
    for i,pos in enumerate(around):goto(pos,"around-window-"+str(i),.23)
    aim((-895.40,71.36,507.8),"lantern-through-red-glass")
    shot("lantern-through-red-glass",2.,f2=True)
    results["snowfieldView"]=observe("other-side-of-glass",keep=True)
    for i,pos in enumerate(reversed(around[:-1])):goto(pos,"back-around-glass-"+str(i),.25)
    goto(route[-1],"return-to-road",.25)
    for i,pos in enumerate(reversed(route[:-1])):goto(pos,"home-by-lantern-"+str(i),.25)
    door()
    enter(aim,goto,shot,key,observe)
    aim((-900.5,71.45,576.5),"look-at-home-window")
    shot("home-after-dusk",1.5,f2=True)
    results["returnedInside"]=observe("dusk-at-home",keep=True)

def enter_from_porch(results,aim,goto,shot,key,click,observe,x,guard_ok):
    px,py,pz=observe("saved-porch")["xyz"]
    assert abs(px+901.5)<.5 and abs(pz-575.5)<.35 and abs(py-70)<.05
    key("7")
    door=aim((-901.5,71.1,576.5),"porch-door",tries=6)
    if door["target"] in ((-902,70,576),(-902,71,576)) and door["open"] is False:click("3")
    guard_ok()
    x("keydown","Shift_L")
    try:
        goto((-901.5,70,575.5),"centre-of-doorway",.19)
        goto((-901.5,70,577.55),"inside-after-snowfield",.35)
    finally:
        x("keyup","Shift_L")
    aim((-900.5,71.45,576.5),"window-at-night")
    shot("home-after-dusk",1.5,f2=True)
    results["returnedInside"]=observe("inside-the-saved-house",keep=True)
