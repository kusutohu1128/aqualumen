"""Layouts for testing the light arriving on a white wall above a contained lava pool."""
from itertools import product

stages = [
    ("dark", False, 0), ("dark-pillar", True, 0), ("one-open",False,1), ("one-pillar",True,1),
    ("nine-pillar",True,9), ("nine-open",False,9), ("one-again",False,1), ("dark-again",False,0),
]
# The entire top is covered, so the pixels on the wall receive no direct moonlight.
room = ["fill 198 172 359 209 180 367 minecraft:smooth_stone outline",
        "fill 199 173 366 208 179 366 minecraft:white_concrete"]
def layout(name, pillar, count):
    blocks={(x,172,z):'minecraft:smooth_stone' for x,z in product(range(201,204),range(360,363))}
    for x,_,z in blocks.copy():
        if count==9 or (count==1 and (x,z)==(202,361)):
            blocks[x,172,z]='minecraft:lava[level=0]'
    blocks.update({(202,y,364):'minecraft:stone' if pillar else 'minecraft:air' for y in range(173,176)})
    assignments=['setblock %d %d %d %s'%(*k,v) for k,v in blocks.items()]
    condition=' '.join('if block %d %d %d %s'%(*k,v) for k,v in blocks.items())
    return assignments,condition
