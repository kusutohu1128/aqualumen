"""Independent CPU oracle for the carried-light (lamp-hand-*) room (no Minecraft, no GPU).

Re-derives from the reviewed layout in HandLightFixture.java: sealed room, matched first-person pose,
close receiving surfaces, and the receiver ROIs against the release shader's first-person carried-light
anchor (release/shaders/lib/carried_light.glsl: view (+-0.32, -0.30, -0.43)) with its three finite-emitter
taps (local_lighting.glsl lampVisibility: radius 0.13 * 0.66). Blocking uses exact slab intervals with the
shader's 0.00005 m in-cell threshold, independent of the Java DDA port.
"""
import math
import unittest

BOX = (400, 148, -420, 413, 158, -401)
SHELL = (403, 150, -412, 410, 154, -404)
EYE = (406.65, 152.62, -407.0)
WIDTH, HEIGHT, FOV, ROI = 2560, 1440, 70.0, 9
FRONT = {(406, y, -410) for y in (151, 152, 153)}
HIDDEN = {(407, y, -409) for y in (151, 152, 153)}
E = .001
BACK = -411 + E
PLANE = -411.0


def anchor(eye, main):
    side = 1 if main else -1  # yaw 180, pitch 0: right +X, up +Y, forward -Z
    return (eye[0] + .32 * side, eye[1] - .30, eye[2] - .43)


MAIN, OFF = anchor(EYE, True), anchor(EYE, False)


def shell():
    x0, y0, z0, x1, y1, z1 = SHELL
    return {(x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) for z in range(z0, z1 + 1)
            if x in (x0, x1) or y in (y0, y1) or z in (z0, z1)}


def clear(solid, a, b):
    steps = int(math.ceil(math.dist(a, b) / .002))
    for i in range(1, steps):
        t = i / steps
        if tuple(math.floor(a[k] + t * (b[k] - a[k])) for k in range(3)) in solid:
            return False
    return True


def inside_room(p):
    return 404 <= p[0] <= 410 and 151 <= p[1] <= 154 and -411 <= p[2] <= -404


def blocked(cells, a, b):
    """Exact slab test: True when the segment spends more than 0.00005 m inside any cell."""
    length = math.dist(a, b)
    for cell in cells:
        t0, t1 = 0.0, 1.0
        for k in range(3):
            d = b[k] - a[k]
            if abs(d) < 1e-12:
                if not cell[k] < a[k] < cell[k] + 1:
                    t0, t1 = 1.0, 0.0
                    break
                continue
            lo, hi = sorted(((cell[k] - a[k]) / d, (cell[k] + 1 - a[k]) / d))
            t0, t1 = max(t0, lo), min(t1, hi)
        if (t1 - t0) * length > .00005:
            return True
    return False


def taps(receiver, lamp, radius=.13):
    l = [lamp[k] - receiver[k] for k in range(3)]
    n = math.sqrt(sum(c * c for c in l))
    l = [c / n for c in l]
    axis = (0, 1, 0) if abs(l[1]) < .9 else (1, 0, 0)
    u = [l[1] * axis[2] - l[2] * axis[1], l[2] * axis[0] - l[0] * axis[2], l[0] * axis[1] - l[1] * axis[0]]
    m = math.sqrt(sum(c * c for c in u))
    u = [c / m * radius * .66 for c in u]
    v = [l[1] * u[2] - l[2] * u[1], l[2] * u[0] - l[0] * u[2], l[0] * u[1] - l[1] * u[0]]
    return [tuple(lamp[k] + u[k] for k in range(3)),
            tuple(lamp[k] - .5 * u[k] + .866 * v[k] for k in range(3)),
            tuple(lamp[k] - .5 * u[k] - .866 * v[k] for k in range(3))]


def taps_open(pillar, receiver, lamp):
    start = (receiver[0], receiver[1], receiver[2] + .025)
    result = []
    for tap in taps(receiver, lamp):
        # Both ends inside the convex room interior: only pillar cells can intersect the segment.
        assert inside_room(start) and inside_room(tap)
        result.append(not blocked(pillar, start, tap))
    return result


def project(point, eye=EYE, fov=FOV, width=WIDTH, height=HEIGHT):
    dx, dy, dz = (point[i] - eye[i] for i in range(3))
    depth = -dz
    if depth <= 0:
        return None
    tan = math.tan(math.radians(fov) / 2)
    return ((dx / (depth * tan * width / height) + 1) / 2 * width, (1 - dy / (depth * tan)) / 2 * height)


def wall_point(px, py, eye=EYE):
    tan = math.tan(math.radians(FOV) / 2)
    nx, ny = px / WIDTH * 2 - 1, 1 - py / HEIGHT * 2
    depth = eye[2] - PLANE
    return (eye[0] + nx * tan * WIDTH / HEIGHT * depth, eye[1] + ny * tan * depth, PLANE)


def roi_violation(pillar, column, row, need, eye=EYE):
    main, off = anchor(eye, True), anchor(eye, False)
    for px in range(column - ROI // 2, column + ROI // 2 + 1):
        for py in range(row - ROI // 2, row + ROI // 2 + 1):
            p = wall_point(px + .5, py + .5, eye)
            if not (404 < p[0] < 410 and 151 < p[1] < 154):
                return f"{px},{py} off wall"
            if blocked(pillar, eye, p):
                return f"{px},{py} camera"
            m = taps_open(pillar, p, main)
            if need.startswith("shadow") and any(m):
                return f"{px},{py} main open {m}"
            if need.startswith("lit") and not all(m):
                return f"{px},{py} main blocked {m}"
            if need in ("shadow-open-off", "lit-both") and not all(taps_open(pillar, p, off)):
                return f"{px},{py} off blocked"
    return None


def pose_box(delta):
    return [(EYE[0] + a * delta, EYE[1] + b * delta, EYE[2] + c * delta)
            for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]


ROIS = {"hand-hidden-shadow-wall": (HIDDEN, 1434, 720, "shadow-open-off"),
        "hand-hidden-lit-wall": (HIDDEN, 982, 720, "lit-both"),
        "hand-front-shadow-wall": (FRONT, 892, 720, "shadow"),
        "hand-front-lit-wall": (FRONT, 1758, 720, "lit")}
ACCEPTED_EYE_TOLERANCE = .02


class HandLightGeometryTest(unittest.TestCase):
    def test_room_in_reserved_box_and_sealed(self):
        cells = shell() | FRONT | HIDDEN
        for x, y, z in cells:
            self.assertTrue(BOX[0] <= x <= BOX[3] and BOX[1] <= y <= BOX[4] and BOX[2] <= z <= BOX[5])
        solid = shell()
        self.assertEqual(len(solid), 8 * 5 * 9 - 6 * 3 * 7)
        interior = {(x, y, z) for x in range(404, 410) for y in range(151, 154) for z in range(-411, -404)}
        for x, y, z in interior:
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + d[0], y + d[1], z + d[2])
                self.assertTrue(n in interior or n in solid, n)
        self.assertTrue(FRONT <= interior and HIDDEN <= interior)

    def test_pose_stands_on_floor_and_body_clear(self):
        feet = EYE[1] - 1.62
        self.assertAlmostEqual(feet, 151.0)
        for walk_x in (EYE[0], EYE[0] + 1.75, EYE[0] - 1.75):
            body = {(x, y, z) for x in range(math.floor(walk_x - .3), math.floor(walk_x + .3) + 1)
                    for y in (151, 152) for z in range(math.floor(EYE[2] - .3), math.floor(EYE[2] + .3) + 1)}
            self.assertFalse(body & (shell() | FRONT | HIDDEN), walk_x)

    def test_close_surfaces_in_frame(self):
        samples = {"back": (EYE[0], EYE[1], BACK), "floor": (406.5, 151 + E, -410.0), "ceiling": (406.5, 154 - E, -410.0),
                   "west": (404 + E, EYE[1], -410.0), "east": (410 - E, EYE[1], -410.5)}
        for name, point in samples.items():
            with self.subTest(name=name):
                self.assertTrue(2 <= math.dist(EYE, point) <= 5)
                u, v = project(point)
                self.assertTrue(0 < u < 2560 and 0 < v < 1440, (u, v))
                self.assertTrue(clear(shell(), EYE, point))
        self.assertAlmostEqual(EYE[2] - (-411), 4.0)

    def test_release_anchors(self):
        self.assertEqual(tuple(round(c, 9) for c in MAIN), (406.97, 152.32, -407.43))
        self.assertEqual(tuple(round(c, 9) for c in OFF), (406.33, 152.32, -407.43))
        for point in (MAIN, OFF):
            self.assertTrue(inside_room(point))
            self.assertFalse(blocked(FRONT | HIDDEN, EYE, point))  # constrainHand inactive

    def test_old_receivers_were_wrong_for_actual_anchors(self):
        old_hidden = (406.1, EYE[1], BACK)
        self.assertEqual(taps_open(HIDDEN, old_hidden, MAIN), [True] * 3)
        self.assertEqual(taps_open(HIDDEN, old_hidden, OFF), [True] * 3)
        partial = taps_open(FRONT, (404.85, EYE[1], BACK), MAIN)
        self.assertIn(True, partial)
        self.assertIn(False, partial)

    def test_roi_centres_world_coordinates(self):
        hidden = wall_point(1434.5, 720.5)
        front = wall_point(892.5, 720.5)
        self.assertAlmostEqual(hidden[0], 407.25101, places=4)
        self.assertAlmostEqual(front[0], 405.14261, places=4)
        self.assertAlmostEqual(hidden[1], 152.61805, places=4)
        self.assertTrue(407.23 < wall_point(1430, 716)[0] < wall_point(1439, 725)[0] < 407.27)
        self.assertTrue(405.12 < wall_point(888, 716)[0] < wall_point(897, 725)[0] < 405.17)
        u, v = project((hidden[0], hidden[1], PLANE))
        self.assertEqual((math.floor(u), math.floor(v)), (1434, 720))

    def test_rois_hold_at_pose_and_accepted_tolerance(self):
        for name, (pillar, column, row, need) in ROIS.items():
            for eye in pose_box(ACCEPTED_EYE_TOLERANCE):
                with self.subTest(roi=name, eye=eye):
                    self.assertIsNone(roi_violation(pillar, column, row, need, eye))

    def test_open_room_controls_lit(self):
        self.assertIsNone(roi_violation(set(), 1434, 720, "lit-both"))
        self.assertIsNone(roi_violation(set(), 892, 720, "lit"))

    def test_hidden_roi_not_robust_to_old_tolerance(self):
        pillar, column, row, need = ROIS["hand-hidden-shadow-wall"]
        self.assertTrue(any(roi_violation(pillar, column, row, need, eye) for eye in pose_box(.05)))
        self.assertTrue(roi_violation(pillar, column + 30, row, need))
        self.assertTrue(roi_violation(pillar, column - 30, row, need))

    def test_neighbouring_columns_bound_the_hidden_strip(self):
        pillar, _, row, need = ROIS["hand-hidden-shadow-wall"]
        good = [c for c in range(1400, 1470) if roi_violation(pillar, c, row, need) is None]
        self.assertEqual((good[0], good[-1]), (1411, 1455))
        self.assertLessEqual(abs((good[0] + good[-1]) / 2 - 1434), 1)

    def test_walk_reveals_receiver_behind_pillar(self):
        solid = shell() | FRONT
        target = (EYE[0], EYE[1], BACK)
        seen = {clear(solid, (EYE[0] + 1.75 * math.sin(2 * math.pi * t / 80), EYE[1], EYE[2]), target) for t in range(81)}
        self.assertEqual(seen, {True, False})


if __name__ == "__main__":
    unittest.main()
