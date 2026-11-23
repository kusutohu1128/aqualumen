"""Mount a warm torch next to the red window and return indoors in survival."""
import sys
from pathlib import Path

def light_window(results, aim, goto, shot, key, click, observe):
    previous = Path(__file__).resolve().parent.parent/"2026-11-21-settlement-light/playable"
    sys.path.insert(0,str(previous))
    from house_walk import enter

    def target(point, block, label):
        at = aim(point, label, want=block, tries=6)
        assert at["target"]==block, (label,at)
        return at

    key("7")
    target((-900.50,71.48,576.50),(-901,71,576),"look-through-window")
    shot("inside-before-warm-torch",1.5,f2=True)
    door = aim((-901.5,70.55,576.5),"door-to-porch",tries=6)
    if door["target"] in ((-902,70,576),(-902,71,576)) and door["open"] is False:
        click("3")
    goto((-901.5,69,575.5),"out-onto-porch",.23)
    goto((-900.5,69,575.45),"east-stair",.21)
    goto((-900.5,68.9,574.4),"outside-east",.2)
    # The north face of the upright beside the window is clear at this height.
    # The lantern on the porch stays in place one block below the new light.
    target((-899.53,71.47,576.01),(-900,71,576),"window-post")
    shot("porch-before",1.2,f2=True)
    key("2")
    click("3")
    key("7")
    at=target((-899.50,71.54,575.84),(-900,71,575),"mounted-torch")
    results["porchTorch"]=at["target"]
    aim((-900.45,71.45,576.48),"lit-red-pane")
    shot("porch-after",1.5,f2=True)
    enter(aim,goto,shot,key,observe)
    key("7")
    target((-900.50,71.48,576.50),(-901,71,576),"window-after-return")
    shot("inside-after-warm-torch",1.5,f2=True)
    results["returnedInside"]=observe("inside-the-red-window",keep=True)
