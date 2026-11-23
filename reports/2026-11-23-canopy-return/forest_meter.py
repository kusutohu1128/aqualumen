"""Use a real torch, an empty socket and a soul torch against the same intact trunk."""
import math

def walk(world, first, results, trail, aim, goto, shot, key, click):
    torch=(566,64,419);support=(566,63,419)
    route=trail.build("oak-night-trail",world,first["xyz"],destination=(569,64,419))
    assert trail.name(*torch)=="torch" and trail.name(568,64,418)=="oak_log"
    key("7")
    for i,wp in enumerate(route["waypoints"][1:]): goto(wp,"reach-oak-"+str(i),.20)
    camera=goto((569.68,64,420.02),"grass-camera",.10)
    def target(point,cell,label):
        o=aim(point,label,want=cell,tries=6)
        assert o["target"]==cell,(label,o)
    def view(label):
        o=aim((569.40,64.,417.98),label,tries=6)
        assert math.dist(o["xyz"],camera["xyz"])<.03 and o["target"] in ((569,63,417),(569,63,418))
        for repeat in ("a","b"):
            shot(label+"-"+repeat,1.8,f2=True)
        results.setdefault("forestViews",[]).append(dict(name=label,pose=o))
    def remove():
        target((566.5,64.31,419.5),torch,"target-torch");click("1")
        target((566.5,63.99,419.5),support,"empty-socket")
    def place(slot):
        target((566.5,63.99,419.5),support,"select-socket");key(slot);click("3");key("7")
        target((566.5,64.31,419.5),torch,"placed-torch")
    view("warm")
    remove();view("off")
    place("3");view("soul")
    remove();place("2");view("restored")
