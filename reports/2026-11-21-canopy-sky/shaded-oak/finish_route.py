"""Fetch the last saved dirt drop from the open north edge and finish the trail."""
def at(x,y,z,label):
    goto((x,y,z),label,.20)


def fetch_drop():
    at(562.5,63,420.5,"north-verge")
    at(562.5,64,418.5,"north-of-crown")
    at(565.5,64,418.5,"beside-drop")
    cell = (565,63,419)
    key("8")
    before = aim((565.5,63.98,419.5),"access-top",want=cell)
    assert before["target"] == cell, before
    for _ in range(3):
        dig(.70)
        if observe("access-open")["target"] != cell:
            break
    at(565.5,63,419.52,"pickup-dirt")
    at(565.55,63,419.68,"toward-item")
    time.sleep(1)
    at(565.5,64,418.5,"out-of-access")
    place_block(cell, "close-access", "1")


def finish():
    fetch_drop()
    at(562.5,64,418.5,"away-from-crown")
    at(562.5,63,420.5,"return-west")
    for x in (561,560):
        at(x+.5,63,420.5,"rim-" + str(x))
        place_block((x,62,421),"donor-" + str(x),"1")
    at(560.5,63,422.5,"find-flower")
    key("1")
    for dx,dz in ((.5,.5),(.35,.35),(.65,.35),(.35,.65),(.65,.65)):
        plant = aim((560+dx,63.23,423+dz),"select-neighbour-poppy")
        if plant["target"] == (560,63,423):
            break
    assert plant["target"] == (560,63,423), plant
    click("2")
    at(561.5,63,422.5,"flower-bed")
    ground = aim((563.5,62.99,422.5),"replant-ground",want=(563,62,422))
    assert ground["target"] == (563,62,422), ground
    click("3")
    actions.append({"action":"replant from inventory","cell":(563,63,422)})
    write(out / "actions.json",actions)
    at(*VIEW,"home-view")
    key("8")
    pose = aim(TRUNK,"saved-oak")
    results["oak"] = {"pose":pose, "image":shot("final-oak",1.2,f2=True)}


attempt(finish, "restore-woodland-trail", results)
