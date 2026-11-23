"""Cut a ground-level opening in an oak, test the path light, and build a lantern post."""
import math

TORCH=(566,64,419)
SUPPORT=(566,63,419)
LOG=(568,64,418)
STAND=(569.68,64,420.02)
PATCH=(569.40,64.00,417.98)
POST=(571,64,420)


def walk(world, first, results, trail, hotbar, aim, goto, shot, key, click, mine):
    inventory=hotbar()
    assert inventory.get("1") is None and inventory["2"]=="minecraft:torch" and inventory["7"]=="minecraft:wooden_axe"
    assert inventory["4"]=="minecraft:lantern"
    route=trail.build("oak-night-trail",world,first["xyz"],destination=(569,64,419))
    for cell,want in [(TORCH,"torch"),(LOG,"oak_log"),((568,65,418),"oak_log"),(POST,"air"),((571,63,420),"grass_block")]:
        assert trail.name(*cell)==want
    key("7")
    for i,wp in enumerate(route["waypoints"][1:]):
        goto(wp,"reach-second-oak-"+str(i),.20)
    camera=goto(STAND,"grass-beside-oak",.10)
    results["standing"]=camera

    def target(point,cell,label):
        obs=aim(point,label,want=cell,tries=6)
        assert obs["target"]==cell,(label,obs)
        return obs

    def photo(label):
        o=aim(PATCH,label,tries=6)
        assert math.dist(o["xyz"],camera["xyz"])<.03 and o["target"] in ((569,63,417),(569,63,418)),o
        shot(label,2.3,f2=True)
        results.setdefault("grassViews",[]).append(dict(name=label,pose=o))

    def flame(active):
        if active:
            target((566.50,63.99,419.50),SUPPORT,"lamp-socket")
            key("2");click("3");key("7")
            target((566.50,64.31,419.50),TORCH,"lamp-placed")
        else:
            target((566.50,64.31,419.50),TORCH,"select-lamp")
            click("1")
            target((566.50,63.99,419.50),SUPPORT,"lamp-removed")

    photo("intact-lit")
    flame(False);photo("intact-off")
    flame(True);photo("intact-relit")
    target((568.70,64.55,418.98),LOG,"select-lowest-log")
    mine(1.95)
    target((568.76,63.99,418.86),(568,63,418),"floor-in-opening")
    photo("cut-lit")
    flame(False);photo("cut-off")
    flame(True);photo("cut-relit")
    build_post(results,aim,goto,shot,key,click)


def build_post(results,aim,goto,shot,key,click):
    def target(point,cell,label):
        obs=aim(point,label,want=cell,tries=6)
        assert obs["target"]==cell,(label,obs)

    # The first empty hotbar slot receives the log. Move close enough for the drop
    # to reach the player before using it for a waypost on the raised grass.
    # A dropped item can land on either side of the trunk. Walk around its
    # open east side and across both ends of the cut before leaving the tree.
    goto((569.48,64,419.35),"approach-cut-log",.16)
    goto((569.40,64,417.72),"collect-timber-on-north-side",.13)
    goto((568.60,64,417.65),"collect-timber-on-open-ground",.16)
    goto((569.50,64,417.75),"leave-clearing",.18)
    goto((569.55,64,419.48),"round-trunk",.16)
    goto((570.0,64,420.4),"beside-new-post",.18)
    target((571.5,63.99,420.5),(571,63,420),"post-foundation")
    key("1");click("3");key("7")
    target((571.50,64.97,420.5),POST,"post-built")
    key("4");click("3");key("7")
    target((571.5,65.32,420.5),(571,65,420),"lantern-on-post")
    goto((569.5,64,423.0),"back-from-lantern",.25)
    o=aim((571.0,64.9,419.8),"finished-waypost",tries=5)
    results["newLantern"]=dict(position=[571,65,420],pose=o)
    shot("finished-waypost",2.5,f2=True)
