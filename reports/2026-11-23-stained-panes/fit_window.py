"""Use the survival inventory and crafting table to fit the previously opened window."""
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent


def panel_origin(image):
    assert image.size == (1600,900)
    top = 142
    # The recipe book shifts the container by 77 GUI pixels. Match both
    # outer rims; the identical repeating slot borders inside are ambiguous.
    signature = ((0,0),(1,255),(2,255),(3,198),(172,198),(173,85),(174,85),(175,0))
    def matches(left):
        return all(max(abs(c-value) for c in image.getpixel((2*(left+u)+1,2*(top+110)+1))) <= 4
                   for u,value in signature)
    origins = [left for left in (312,389) if matches(left)]
    assert len(origins) == 1, origins
    return origins[0],top


def fit(results, aim, goto, shot, key, click, x, guard_ok, grab, out):
    checkpoint = HERE.parent / "2026-11-22-ceiling-return/village/house-poppy/save.json"
    inventory = json.loads(checkpoint.read_text())["inventory"]
    def slot_of(item):
        return next(int(k) for k,v in inventory.items() if v[0] == "minecraft:" + item)
    def main_slot(index):
        assert 9 <= index < 36
        return (16 + 18*((index-9)%9), 92 + 18*((index-9)//9))
    def hot(index):
        return 16 + 18*index, 150
    def target(point, block, label):
        found = aim(point, label, want=block, tries=7)
        assert found["target"] == block, found
    def panel(name):
        time.sleep(.6)
        im = grab()
        im.save(out / (name + ".png"))
        return panel_origin(im)
    def use(pos, button="1"):
        guard_ok()
        x("mousemove","--window",x("getwindowfocus"),str(2*(origin[0]+pos[0])+1),str(2*(origin[1]+pos[1])+1))
        click(button)
    def proof(label):
        # Move the pointer clear of items so the result icon is visible.
        guard_ok()
        x("mousemove","--window",x("getwindowfocus"),str(2*(origin[0]+172)),str(2*(origin[1]+78)))
        time.sleep(.25)
        grab().save(out / (label+".png"))

    poppy = main_slot(slot_of("poppy"))
    glass = main_slot(slot_of("glass"))
    planks = hot(slot_of("spruce_planks"))
    spare = main_slot(next(i for i in range(9,36) if str(i) not in inventory))
    key("7")
    aim((-900.5,71.5,576.5),"window-before")
    shot("window-before",1.3,f2=True)
    key("e")
    try:
        origin = panel("inventory-before")
        use(planks)
        for p in ((106,26),(124,26),(106,44),(124,44)):
            use(p,"3")
        use(planks)
        proof("table-recipe")
        use((162,36)); use(hot(0)); use(spare)
        use(poppy); use((106,26))
        proof("dye-recipe")
        use((162,36)); use(poppy)
    finally:
        key("e")
    key("1")
    target((-902.50,71.48,576.985),(-903,71,576),"table-support")
    click("3")
    target((-902.011,71.53,577.45),(-903,71,577),"placed-table")
    click("3")
    try:
        origin = panel("crafting-before")
        use(glass)
        for y in (25,43,61):
            for u in (38,56,74):
                if (u,y)!=(56,43): use((u,y),"3")
        use(poppy); use((56,43))
        proof("red-glass-recipe")
        use((132,43)); use(glass)
        use(glass)
        for y in (25,43):
            for u in (38,56,74): use((u,y),"3")
        use(glass)
        proof("pane-recipe")
        use((132,43)); use(hot(0))
    finally:
        key("e")
    key("1")
    target((-900.5,70.996,576.65),(-901,70,576),"window-sill")
    click("3")
    key("7")
    target((-900.5,71.48,576.5),(-901,71,576),"fitted-window")
    shot("window-after",1.3,f2=True)
    results["window"]=[-901,71,576]
    results["table"]=[-903,71,577]
