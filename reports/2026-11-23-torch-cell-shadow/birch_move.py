"""Move the previously saved east torch around the same birch using survival controls."""
import math


def relocate(saved, first, results, trail, hotbar, aim, goto, shot, key, click):
    assert math.dist(first["xyz"], (598.433, 71, 427.502)) < .06
    assert hotbar()["2"] == "minecraft:torch" and "4" not in hotbar()
    route = trail.build("stone-display-wider-camp", saved, (593.5,71,427.5), destination=(585,64,424))
    results["downhillRoute"] = route["waypoints"]
    old, new, support = (584,64,424), (582,64,423), (582,63,423)
    assert [trail.name(*c) for c in (old,new,support)] == ["torch","air","grass_block"]

    def see(block, point, label):
        read = aim(point, label, want=block, tries=8)
        assert read["target"] == block, (label, read)

    def photograph(label):
        see((583,65,424), (583.99,65.47,424.52), label)
        shot(label, 1.3, f2=True)

    key("4")
    for i, point in enumerate(route["waypoints"]):
        goto(point, "descend-" + str(i), .22)
    photograph("birch-east-lit")
    see(old, (584.5,64.39,424.5), "old-torch")
    click("1")
    see((584,63,424), (584.5,63.99,424.5), "east-torch-removed")
    photograph("birch-east-extinguished")
    goto((585.5,64,422.5), "north-of-east-flame", .21)
    goto((583.5,64,422.5), "north-of-soil-step", .19)
    finish(results,hotbar,aim,goto,shot,key,click)


def finish(results,hotbar,aim,goto,shot,key,click):
    assert hotbar()["2"]=="minecraft:torch" and "4" not in hotbar()
    new=(582,64,423)
    def see(block,point,label):
        obs=aim(point,label,want=block,tries=6)
        assert obs["target"]==block,(label,obs)
    def sight_any(block,points,label):
        for point in points:
            obs=aim(point,label,tries=6)
            if obs["target"]==block:
                return
        raise RuntimeError(f"All visible points missed {block}: {obs}")
    # See the near edge of the grass through the gap between a low branch
    # and the raised soil step. Left-clicking the overhanging leaves is unnecessary.
    key("4")
    support=(582,63,423)
    sight_any(support,[(582.67,63.995,423.17),(582.71,63.995,423.10),(582.60,63.995,423.22)],
              "north-west-support")
    key("2")
    click("3")
    key("4")
    sight_any(new,[(582.54,64.08,423.46),(582.56,64.18,423.43),(582.5,64.10,423.50)],
              "relocated-torch")
    shot("birch-north-west-flame", 1.3, f2=True)
    goto((585.5,64,422.5), "east-of-soul-torch", .21)
    see((583,65,423), (583.5,65.4,423.5), "untouched-soul-torch")
    goto((585.5,64,424.5), "back-to-east-face", .21)
    see((583,65,424), (583.99,65.47,424.52), "east-face-after-relocation")
    shot("birch-east-after-relocation",1.3,f2=True)
    results["removedTorch"], results["newTorch"] = [584,64,424], list(new)
