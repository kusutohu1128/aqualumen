"""Run inside the private survival harness after confirming actual mouse movement."""
torch_cell = (561, 63, 422)
wall_cell = (562, 63, 422)
donor = (559, 62, 422)
trunk_face = (565.01, 63.82, 422.50)


def picture(role):
    # The shovel remains selected in every frame. A torch in the player's hand
    # would illuminate the very same bark as the placed torch.
    key("8")
    pose = aim(trunk_face, "view-" + role)
    image = shot(role, 1.2, f2=True)
    results[role] = {"photo": image, "pose": pose, "selectedSlot": 8}


def wall():
    place_block(wall_cell, "dirt-screen", "1")
    picture("warm-wall")
    break_cell(wall_cell, "dirt-screen")
    picture("warm-reopened")


def remove_lamp(kind):
    key("8")
    before = aim((561.5, 63.35, 422.5), "aim-remove-" + kind, want=torch_cell)
    assert before["target"] == torch_cell
    click("1")
    after = observe("removed-" + kind)
    assert after["target"] != torch_cell
    actions.append({"action": "remove " + kind, "cell": torch_cell, "before": before, "after": after})
    write(out / "actions.json", actions)


# The player begins beside the donor block. Collect it before the first
# photo, so its removal cannot account for a later between-photo change.
attempt(lambda: break_cell(donor, "donor-grass"), "collect-dirt", results)
picture("off")
place_block(torch_cell, "warm-torch", "2")
picture("warm")
attempt(wall, "place-and-remove-screen", results)
remove_lamp("warm-torch")
picture("off-again")
place_block(torch_cell, "soul-torch", "3")
picture("soul")
remove_lamp("soul-torch")
picture("restored")
