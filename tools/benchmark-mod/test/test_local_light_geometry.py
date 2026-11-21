"""Independent CPU oracle for the extended local-light fixture geometry (no Minecraft, no GPU).

Re-derives, from the reviewed layout in LocalLightFixture.java, the facts the new scenes rely on:
canopy torch lighting/shade, red-glass divider path, and walk-route visibility/in-frame/body clearance.
"""
import math
import unittest
from collections import deque

OX, OY, OZ = 400, 150, -420
EYE = (409.5, 157.0, -402.0)
BOX = (400, 148, -420, 413, 158, -401)
NON_OPAQUE = {"oak_leaves", "water", "torch", "soul_torch", "lantern", "red_stained_glass"}
EMIT = {"torch": 14, "soul_torch": 10, "lantern": 15}
TORCH_A = ("torch", 407, 151, -417)
LANTERN = ("lantern", 406, 152, -412)
CANOPY_TORCH = ("torch", 403, 151, -415)
WALK_SHADE_HIDDEN_BELOW_X = 407.5
E = .001
SAMPLES = {
    "receiver-back-wall": (OX + 11.5, 152.5, OZ + 2 + E), "receiver-floor-deep": (OX + 11.5, 151 + E, OZ + 3.5),
    "receiver-floor-mid": (OX + 10.5, 151 + E, OZ + 4.5), "lamp-bay-floor": (OX + 6.5, 151 + E, OZ + 4.5),
    "lamp-bay-back-wall": (OX + 7.5, 152.5, OZ + 2 + E), "canopy-shade-grass": (OX + 2.5, 151 + E, OZ + 2.5),
    "sunlit-grass": (OX + 2.5, 151 + E, OZ + 10.5), "pool-surface-center": (OX + 9.5, 150 + 8 / 9, OZ + 10.5),
    "submerged-receiver": (OX + 9.5, 149 + E, OZ + 9.5), "canopy-torch-grass": (OX + 3.5, 151 + E, OZ + 6.5),
    "canopy-trunk-face": (OX + 2.5, 152.5, OZ + 5 + E)}


def placements(divider=None, lamps=()):
    grid = {}

    def put(dx, y, dz, block):
        grid[(OX + dx, y, OZ + dz)] = block
    for dx in range(14):
        for dz in range(13):
            if 7 <= dx <= 11 and 9 <= dz <= 11:
                continue
            if dx <= 4:
                block = "dirt" if (dx, dz) == (2, 4) else "grass_block"
            else:
                block = "smooth_stone" if 2 <= dz <= 6 and (6 <= dx <= 8 or 10 <= dx <= 12) else "stone"
            put(dx, OY, dz, block)
    for dx in range(7, 12):
        for dz in range(9, 12):
            put(dx, 148, dz, "white_concrete" if dz == 9 and 8 <= dx <= 10 else "stone")
    for dx in range(6, 13):
        for dz in range(8, 13):
            if dx in (6, 12) or dz in (8, 12):
                put(dx, 149, dz, "stone")
    put(6, 151, 8, "stone_bricks")
    for y in range(151, 155):
        for dx in range(5, 14):
            put(dx, y, 1, "white_concrete" if 6 <= dx <= 8 or 10 <= dx <= 12 else "stone_bricks")
        for dz in range(2, 7):
            put(5, y, dz, "stone_bricks")
            put(13, y, dz, "stone_bricks")
    for dx in range(5, 14):
        for dz in range(1, 7):
            put(dx, 155, dz, "spruce_planks")
    for y in range(151, 156):
        put(2, y, 4, "oak_log")
    for y in range(154, 157):
        for dx in range(5):
            for dz in range(2, 7):
                if (dx, dz) == (2, 4) and y <= 155:
                    continue
                corner = dx in (0, 4) and dz in (2, 6)
                if (y == 155 and corner) or (y == 156 and (dx in (0, 4) or dz in (2, 6))):
                    continue
                put(dx, y, dz, "oak_leaves")
    if divider:
        for y in range(151, 155):
            for dz in range(2, 7):
                put(9, y, dz, divider)
    for y in (149, 150):
        for dx in range(7, 12):
            for dz in range(9, 12):
                put(dx, y, dz, "water")
    for block, x, y, z in lamps:
        grid[(x, y, z)] = block
    return grid


def opaque(block):
    return block is not None and block not in NON_OPAQUE


def clear(grid, a, b, leaves_block):
    steps = math.ceil(math.dist(a, b) / .002)
    for k in range(1, steps):
        t = k / steps
        block = grid.get(tuple(math.floor(a[j] + t * (b[j] - a[j])) for j in range(3)))
        if opaque(block) or (leaves_block and block == "oak_leaves"):
            return False
    return True


def block_light(grid, lamps, point):
    target = tuple(math.floor(v) for v in point)
    best = 0
    for block, x, y, z in lamps:
        level = {(x, y, z): EMIT[block]}
        queue = deque([(x, y, z)])
        while queue:
            at = queue.popleft()
            value = level[at]
            if value <= 1:
                continue
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nxt = (at[0] + d[0], at[1] + d[1], at[2] + d[2])
                if opaque(grid.get(nxt)) or level.get(nxt, 0) >= value - 1:
                    continue
                level[nxt] = value - 1
                queue.append(nxt)
        best = max(best, level.get(target, 0))
    return best


def project(point, eye, yaw=180.0, pitch=22.0, fov=70.0, width=2560, height=1440):
    yr, pr = math.radians(yaw), math.radians(pitch)
    forward = (-math.sin(yr) * math.cos(pr), -math.sin(pr), math.cos(yr) * math.cos(pr))
    right = (-math.cos(yr), 0.0, -math.sin(yr))
    up = (right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
          right[0] * forward[1] - right[1] * forward[0])
    d = [point[j] - eye[j] for j in range(3)]

    def dot(a, b):
        return sum(a[j] * b[j] for j in range(3))
    depth = dot(d, forward)
    if depth <= 1e-6:
        return None
    tan = math.tan(math.radians(fov) / 2)
    return ((dot(d, right) / (depth * tan * width / height) + 1) / 2 * width, (1 - dot(d, up) / (depth * tan)) / 2 * height)


def sun_direction(time):
    d = time / 24000 - .25
    d -= math.floor(d)
    angle = (d * 2 + (.5 - math.cos(d * math.pi) / 2)) / 3 * 2 * math.pi
    return (-math.sin(angle), math.cos(angle), 0.0)


def solar_shaded(grid, point, time=7000):
    sun = sun_direction(time)
    t = (BOX[4] + 1 - point[1]) / sun[1]
    return not clear(grid, point, tuple(point[j] + t * sun[j] for j in range(3)), True)


def walk_x(seconds):
    return 410.5 + (405.5 - 410.5) * max(0.0, min(1.0, seconds / 8))


def in_frame(pixel):
    return pixel is not None and 0 < pixel[0] < 2560 and 0 < pixel[1] < 1440


class ExtendedLocalLightGeometry(unittest.TestCase):
    def test_canopy_torch_lights_visible_grass_and_trunk_face_in_solar_shade(self):
        canopy, off = placements(lamps=[CANOPY_TORCH]), placements()
        torch_center = (403.5, 151.5, -414.5)
        self.assertEqual(canopy[(403, 150, -415)], "grass_block")
        self.assertEqual(canopy[(403, 154, -415)], "oak_leaves")
        self.assertTrue(solar_shaded(canopy, torch_center))
        for name in ("canopy-torch-grass", "canopy-trunk-face"):
            point = SAMPLES[name]
            with self.subTest(sample=name):
                self.assertGreaterEqual(block_light(canopy, [CANOPY_TORCH], point), 12)
                self.assertEqual(block_light(off, [], point), 0)
                self.assertTrue(clear(canopy, torch_center, point, False))
                self.assertTrue(clear(canopy, EYE, point, True))
                self.assertTrue(in_frame(project(point, EYE)))
                self.assertTrue(solar_shaded(canopy, point))
        self.assertTrue(solar_shaded(off, SAMPLES["canopy-shade-grass"]))
        self.assertFalse(solar_shaded(off, SAMPLES["sunlit-grass"]))

    def test_sun_direction_matches_vanilla_sky_angle(self):
        sun = sun_direction(7000)
        self.assertAlmostEqual(math.degrees(math.atan2(-sun[0], sun[1])), 10.513, places=2)
        # Vanilla's eased sky angle puts the time-0 sun ~12.4 deg above the eastern horizon, not on it.
        self.assertAlmostEqual(math.degrees(math.atan2(sun_direction(0)[1], sun_direction(0)[0])), 12.39, places=1)

    def test_red_glass_divider_passes_vanilla_light_and_shares_wall_cells(self):
        wall, glass, torch = placements("stone_bricks", [TORCH_A]), placements("red_stained_glass", [TORCH_A]), placements(lamps=[TORCH_A])
        self.assertEqual({k for k, v in wall.items() if v == "stone_bricks" and k[0] == 409 and -418 <= k[2] <= -414},
                         {k for k, v in glass.items() if v == "red_stained_glass"})
        for name in ("receiver-back-wall", "receiver-floor-deep", "receiver-floor-mid"):
            point = SAMPLES[name]
            with self.subTest(receiver=name):
                self.assertTrue(clear(glass, (407.5, 151.5, -416.5), point, False))
                self.assertFalse(clear(wall, (407.5, 151.5, -416.5), point, False))
                self.assertEqual(block_light(glass, [TORCH_A], point), block_light(torch, [TORCH_A], point))

    def test_walk_route_sees_every_sample_in_frame_and_never_collides(self):
        walk = placements(lamps=[TORCH_A, LANTERN])
        clusters = set()
        for step in range(801):
            x = walk_x(step * .01)
            clusters.add(math.floor(x) // 8)
            for bx in range(math.floor(x - .3), math.floor(x + .3) + 1):
                for by in range(155, 158):
                    for bz in (-403, -402):
                        self.assertNotIn((bx, by, bz), walk)
                        self.assertTrue(BOX[0] <= bx <= BOX[3] and BOX[1] <= by <= BOX[4] and BOX[2] <= bz <= BOX[5])
        self.assertEqual(clusters, {50, 51})
        for step in range(17):
            eye = (walk_x(step * .5), 157.0, -402.0)
            for name, point in SAMPLES.items():
                with self.subTest(x=eye[0], sample=name):
                    # The day-only shade sample is hidden by the canopy from the west part of the night route.
                    expected = not (name == "canopy-shade-grass" and eye[0] < WALK_SHADE_HIDDEN_BELOW_X)
                    self.assertEqual(clear(walk, eye, point, True), expected)
                    self.assertTrue(in_frame(project(point, eye)), project(point, eye))


if __name__ == "__main__":
    unittest.main()
