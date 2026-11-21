"""Window projection room. The light is behind the door, camera and white receiver in front."""
from itertools import product

LOWER, UPPER = (6, 1, 3), (6, 2, 3)
LAMP = (6, 2, 6)
ROLES = {
    "dark": ("dark_oak", False),
    "oak": ("oak", False),
    "open": ("oak", True),
    "empty": (None, False),
    "acacia": ("acacia", False),
    "oak-return": ("oak", False),
}


def install(f):
    # The existing fixture runner supports two single-cell material slots plus
    # two optional baffles. Here the material slots carry the two door halves.
    def unit(c):
        return f.box(*(n for v in c for n in (v, v)))

    f.ORIGIN = (445, 150, -425)
    f.EAST_BOX, f.LAMP_BOX, f.LAMP_CELL = unit(LOWER), unit(UPPER), UPPER
    f.FIRST_BOX, f.SECOND_BOX = unit((10, 2, 8)), unit((10, 3, 8))
    f.SHELL = f.SHELL[:7] + [
        (f.box(12, 12, 0, 6, 0, 9), f.BLACK),
        (f.box(0, 5, 0, 6, 3, 3), f.BLACK),
        (f.box(7, 11, 0, 6, 3, 3), f.BLACK),
        (unit((6, 0, 3)), f.BLACK),
        (f.box(6, 6, 3, 6, 3, 3), f.BLACK),
        (unit((6, 1, 6)), f.BLACK),
        (unit(LAMP), "minecraft:lantern[hanging=false,waterlogged=false]"),
    ]

    def state(species, opened, half):
        if not species:
            return f.AIR
        return ("minecraft:%s_door[facing=south,half=%s,hinge=left,open=%s,powered=false]"
                % (species, half, str(opened).lower()))

    f.EAST = {name: state(*v, "lower") for name, v in ROLES.items()}
    f.LAMP = {name: state(*v, "upper") for name, v in ROLES.items()}
    f.ROLES = [(name, name, name, False, False, "receiver", name) for name in ROLES]
    f.ROLE_NAMES = list(ROLES)
    f.POSES = {"receiver": dict(eye=(6.5, 2.5, 2.40), yaw=180.0, pitch=0.0)}
    # Project canonical points in the upper panel onto the wall, from the
    # centre of the lantern. Oak has four holes; the central stile is opaque.
    scale = 6.5 / (6.5 - (3 + 1.5/16))
    f.RECEIVERS = [(6.5 + (u-.5)*scale, 2.5 + (v-.5)*scale, 0.0)
                   for u, v in [(5/16, 11.5/16), (.5, 11.5/16), (11/16, 11.5/16), (.5, 2/16)]]
    f.PATCH = 5
    assert all(f.first_hit(f.role(name), f.POSES["receiver"], *f.project(f.POSES["receiver"], p)[:2])[0] == f.WHITE
               for name, p in product(ROLES, f.RECEIVERS))
