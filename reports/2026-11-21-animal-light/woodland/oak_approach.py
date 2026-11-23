"""Walk to the fixed torch with an empty hand, then compare carried light at the oak."""
import math
import json
import gzip
import struct


def freeze_sky(level, expected_time=63746):
    """Edit the two existing string game rules in the disposable diagnostic copy."""
    from mcnbt import parse
    raw=gzip.decompress(level.read_bytes())
    before=parse(raw)
    data=before["Data"]
    assert data["WorldGenSettings"]["seed"]==308060 and data["Time"]==expected_time
    def string(value):
        encoded=value.encode()
        return struct.pack(">H",len(encoded))+encoded
    for name in ("doDaylightCycle","doWeatherCycle"):
        assert data["GameRules"][name]=="true"
        tag=b"\x08"+string(name)
        assert raw.count(tag+string("true"))==1
        raw=raw.replace(tag+string("true"),tag+string("false"))
        data["GameRules"][name]="false"
    assert parse(raw)==before
    level.write_bytes(gzip.compress(raw,mtime=0))
    return dict(dayTime=data["DayTime"],rain=data["raining"],weatherCycle=False,daylightCycle=False)


def settled_lights(key,shot,hotbar,reverse=True):
    inventory=hotbar()
    assert inventory.get("1") is None and inventory["2"]=="minecraft:torch" and inventory["3"]=="minecraft:soul_torch"
    photos=[]
    # Hold long enough to observe the 1.8 second dark-adaptation tail.
    sequence=[("1","empty"),("2","warm"),("3","soul")]
    if reverse:
        sequence.extend((("1","empty"),("3","soul"),("2","warm"),("1","empty")))
    for i,(slot,hand) in enumerate(sequence):
        key(slot)
        label=f"settled-{i}-{hand}"
        shot(label,8.5,f2=True)
        photos.append(dict(file=label+"-ingame.png",held=inventory.get(slot)))
    return photos


def approach(first, world, source, out, results, trail, hotbar, aim, goto, shot, key, photograph_lights):
    flame=(561.5,63.35,422.5)
    endpoint=(559,63,423)
    assert hotbar().get("1") is None
    route=trail.build(source,world,first["xyz"],destination=endpoint)
    assert trail.name(561,63,422)=="torch"
    (out/"homeward-route.json").write_text(json.dumps(route,indent=2)+"\n")
    key("1")
    marks=iter((16,10,6))
    threshold=next(marks)
    frames=[]
    for i,point in enumerate(route["waypoints"][1:]):
        pose=goto(point,f"homeward-{i}",.29)
        distance=math.dist(pose["xyz"],flame)
        if threshold and distance<=threshold:
            label=f"approach-{threshold}"
            camera=aim(flame,label)
            shot(label,1.4,f2=True)
            frames.append(dict(distance=distance,pose=camera,frame=label+"-ingame.png",held=None))
            threshold=next(marks,None)
    results["approach"]=frames
    target=aim(flame,"verify-persistent-torch",want=(561,63,422))
    assert tuple(target["target"] or ())==(561,63,422),target
    results["savedTorch"]=target
    results["closeOak"]=photograph_lights("close-oak",(562.5,64.6,422.5))
    assert len(frames)==3


def isolate(first, world, source, results, trail, hotbar, aim, goto, shot, key, click, photograph_lights):
    assert hotbar().get("1") is None and hotbar()["3"]=="minecraft:soul_torch"
    placed=(565,64,425)
    middle=(565.5,64.35,425.5)
    floor=(565,63,425)
    south=(563,64,426)
    camera_target=(565.5,65.4,423.)
    position=first["xyz"]

    def travel(destination,label):
        nonlocal position
        path=trail.build(source,world,position,destination=destination)
        for i,wp in enumerate(path["waypoints"][1:]):
            position=goto(wp,label+"-"+str(i),.21)["xyz"]

    def fixed(label,target):
        key("1")
        o=aim(target,label)
        results[label]=dict(pose=o,photo=shot(label,1.4,f2=True))

    def restore():
        key("3")
        o=aim((565.5,63.94,425.5),"support-of-soul",want=floor)
        assert o["target"]==floor,o
        click("3");key("1")
        o=aim(middle,"restored-soul",want=placed)
        assert o["target"]==placed,o
        results["restoredSoul"]=o

    travel(south,"reach-soul")
    assert trail.name(*placed)=="soul_torch" and trail.name(561,63,422)=="torch"
    fixed("south-both-placed",camera_target)
    o=aim(middle,"select-soul",want=placed)
    assert o["target"]==placed,o
    click("1")
    removed=aim((565.5,63.94,425.5),"removed-soul",want=floor)
    assert removed["target"]==floor,removed
    results["removedSoul"]=removed
    try:
        fixed("south-warm-only",camera_target)
        # The east face of this nearby oak is unobstructed at both distances.
        for name,dest in (("bark-far",(563,64,417)),("bark-close",(562,64,418))):
            travel(dest,name)
            bark=(561,65,418)
            camera=aim((561.99,65.55,418.5),name+"-target",want=bark)
            assert camera["target"]==bark,camera
            results[name]=dict(pose=camera,photos=photograph_lights(name,None,True))
    finally:
        travel(south,"back-to-soul")
        restore()
    fixed("south-both-restored",camera_target)
    travel((559,63,423),"home")
    o=aim((561.5,63.35,422.5),"warm-still-standing",want=(561,63,422))
    assert o["target"]==(561,63,422),o
    results["warmStillStanding"]=o
