"""Voxel grid + camera geometry helpers for the forest torch site search (read-only analytics)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

AIR, LEAVES, LOG, GRASS, DIRT, SOLID, WATER, PLANT, UNKNOWN = 0, 1, 2, 3, 4, 5, 6, 7, 255
NAMES = {AIR: "air", LEAVES: "leaves", LOG: "log", GRASS: "grass_block", DIRT: "dirt", SOLID: "solid",
         WATER: "water", PLANT: "plant", UNKNOWN: "unknown"}
PLANT_WORDS = ("grass", "fern", "tulip", "orchid", "allium", "azure_bluet", "cornflower", "lily", "dandelion",
               "poppy", "rose_bush", "peony", "lilac", "sweet_berry", "mushroom", "sugar_cane", "bush", "flower",
               "vine", "kelp", "seagrass", "sapling", "moss_carpet", "snow", "carpet", "bamboo", "torch")
FOV_V, ASPECT = 70.0, 16 / 9


def categorize(name):
    if name in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
        return AIR
    if name == "minecraft:water":
        return WATER
    if name.endswith("_leaves"):
        return LEAVES
    if name.endswith("_log") or name.endswith("_wood"):
        return LOG
    if name == "minecraft:grass_block":
        return GRASS
    if name in ("minecraft:dirt", "minecraft:podzol", "minecraft:coarse_dirt", "minecraft:rooted_dirt"):
        return DIRT
    if name == "minecraft:snow":
        return PLANT
    short = name.split(":", 1)[1]
    if name != "minecraft:grass_block" and any(w in short for w in PLANT_WORDS) and "block" not in short:
        return PLANT
    return SOLID


class Grid:
    def __init__(self, world, x0, z0, x1, z1, y0, y1):
        self.x0, self.z0, self.y0, self.W, self.D, self.H = x0, z0, y0, x1 - x0 + 1, z1 - z0 + 1, y1 - y0 + 1
        self.cells = bytearray([UNKNOWN]) * (self.W * self.D * self.H)
        self.names = {}  # packed -> exact state dict for non-air cells (needed for evidence)
        cache = {}
        for cx in range(x0 // 16, x1 // 16 + 1):
            for cz in range(z0 // 16, z1 // 16 + 1):
                secs = world.chunk(cx, cz)
                if secs is None:
                    continue
                for sy in range(y0 // 16, y1 // 16 + 1):
                    sec = secs.get(sy)
                    for i in range(4096):
                        y = sy * 16 + i // 256
                        if y < y0 or y > y1:
                            continue
                        x = cx * 16 + i % 16
                        z = cz * 16 + (i // 16) % 16
                        if x < x0 or x > x1 or z < z0 or z > z1:
                            continue
                        if sec is None:
                            cat = AIR
                        else:
                            palette, idx = sec
                            entry = palette[0] if idx is None else palette[idx[i]]
                            name = entry["Name"]
                            cat = cache.get(name)
                            if cat is None:
                                cat = cache[name] = categorize(name)
                        self.cells[((y - y0) * self.D + (z - z0)) * self.W + (x - x0)] = cat

    def inside(self, x, y, z):
        return self.x0 <= x < self.x0 + self.W and self.z0 <= z < self.z0 + self.D and self.y0 <= y < self.y0 + self.H

    def cat(self, x, y, z):
        if not self.inside(x, y, z):
            return UNKNOWN
        return self.cells[((y - self.y0) * self.D + (z - self.z0)) * self.W + (x - self.x0)]

    def cast(self, o, d, maxdist, stop=(LEAVES, LOG, GRASS, DIRT, SOLID, WATER, UNKNOWN)):
        """Amanatides-Woo traversal. Returns (cat, dist, cell, plants_passed)."""
        ox, oy, oz = o
        dx, dy, dz = d
        ix, iy, iz = math.floor(ox), math.floor(oy), math.floor(oz)
        sx, sy, sz = (1 if dx > 0 else -1), (1 if dy > 0 else -1), (1 if dz > 0 else -1)
        inf = float("inf")
        tdx = abs(1 / dx) if dx else inf
        tdy = abs(1 / dy) if dy else inf
        tdz = abs(1 / dz) if dz else inf
        tx = ((ix + (1 if sx > 0 else 0)) - ox) / dx if dx else inf
        ty = ((iy + (1 if sy > 0 else 0)) - oy) / dy if dy else inf
        tz = ((iz + (1 if sz > 0 else 0)) - oz) / dz if dz else inf
        t = 0.0
        plants = 0
        while t <= maxdist:
            c = self.cat(ix, iy, iz)
            if c in stop:
                return c, t, (ix, iy, iz), plants
            if c == PLANT:
                plants += 1
            if tx <= ty and tx <= tz:
                t = tx; tx += tdx; ix += sx
            elif ty <= tz:
                t = ty; ty += tdy; iy += sy
            else:
                t = tz; tz += tdz; iz += sz
        return AIR, maxdist, None, plants


def basis(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    f = (-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p))
    r = (-math.cos(y), 0.0, -math.sin(y))
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    return f, r, u


def project(point, eye, yaw, pitch, fov=FOV_V, aspect=ASPECT):
    """NDC (x right+, y up+) of a world point as in LocalLightFixture.project; None when behind."""
    f, r, u = basis(yaw, pitch)
    d = (point[0] - eye[0], point[1] - eye[1], point[2] - eye[2])
    zv = d[0] * f[0] + d[1] * f[1] + d[2] * f[2]
    if zv <= 1e-6:
        return None
    t = math.tan(math.radians(fov) / 2)
    return ((d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / (zv * t * aspect),
            (d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / (zv * t), zv)


def ray_dir(nx, ny, yaw, pitch, fov=FOV_V, aspect=ASPECT):
    f, r, u = basis(yaw, pitch)
    t = math.tan(math.radians(fov) / 2)
    d = [f[i] + r[i] * nx * t * aspect + u[i] * ny * t for i in range(3)]
    n = math.sqrt(sum(v * v for v in d))
    return tuple(v / n for v in d)


def sun_direction(time_of_day):
    """Vanilla sky angle and overworld sun path as used by LocalLightFixture.sunDirection (x west-, no z)."""
    d = time_of_day / 24000.0 - .25
    d -= math.floor(d)
    angle = (d * 2 + (.5 - math.cos(d * math.pi) / 2)) / 3 * 2 * math.pi
    return (-math.sin(angle), math.cos(angle), 0.0)
