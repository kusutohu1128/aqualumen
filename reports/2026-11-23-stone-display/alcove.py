"""Extend the torch recess in survival and look back at camp from the trail."""
import math


def widen(first, results, hotbar, aim, goto, shot, key, mine):
    assert math.dist(first["xyz"], (598.439,71.,427.487)) < .03
    assert hotbar()["6"] == "minecraft:wooden_pickaxe" and "4" not in hotbar()

    def sight(cell, point, label):
        seen = aim(point, label, want=cell, tries=8)
        assert seen["target"] == cell, (label, seen)
        return seen

    cell = (598,72,425)
    back = (598,72,424)
    key("4")
    sight(cell, (598.5,72.5,425.96), "stone-left-of-the-flame")
    shot("solid-face", 1.3, f2=True)
    key("6")
    mine(1.38)
    key("4")
    sight(back, (598.5,72.5,424.96), "new-back-wall")
    shot("widened-recess", 2., f2=True)
    key("2")
    shot("widened-recess-held", 2., f2=True)
    key("4")
    goto((593.55,71.,427.52), "walk-out-to-the-trail-light", .23)
    aim((598.9,72.4,425.1), "see-the-opened-niche-from-trail", tries=8)
    shot("camp-from-trail", 2., f2=True)
    goto((598.5,71.,427.5), "return-to-the-excavation", .23)
    sight((599,72,425), (599.50,72.43,425.17), "undisturbed-wall-torch")
    results["openedStone"] = list(cell)
    results["backWall"] = list(back)
