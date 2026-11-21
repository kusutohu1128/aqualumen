"""Read-only Anvil (.mca) reader: biomes, block states, heightmaps and saved light (stdlib only).

    python3 anvil.py <world-dir> x0 z0 x1 z1 [y]     # biome / surface / column survey
"""

import gzip
import json
import math
import struct
import sys
import zlib
from pathlib import Path


def nbt(data):
    pos = 0

    def take(n):
        nonlocal pos
        pos += n
        return data[pos - n : pos]

    def payload(tag):
        if tag == 1:
            return struct.unpack(">b", take(1))[0]
        if tag == 2:
            return struct.unpack(">h", take(2))[0]
        if tag == 3:
            return struct.unpack(">i", take(4))[0]
        if tag == 4:
            return struct.unpack(">q", take(8))[0]
        if tag == 5:
            return struct.unpack(">f", take(4))[0]
        if tag == 6:
            return struct.unpack(">d", take(8))[0]
        if tag == 7:
            n = struct.unpack(">i", take(4))[0]
            return take(n)
        if tag == 11:
            n = struct.unpack(">i", take(4))[0]
            return list(struct.unpack(">%di" % n, take(4 * n)))
        if tag == 12:
            n = struct.unpack(">i", take(4))[0]
            return list(struct.unpack(">%dq" % n, take(8 * n)))
        if tag == 8:
            return take(struct.unpack(">H", take(2))[0]).decode("utf-8", "replace")
        if tag == 9:
            kind, n = struct.unpack(">bi", take(5))
            return [payload(kind) for _ in range(n)]
        if tag == 10:
            out = {}
            while (kind := take(1)[0]) != 0:
                key = take(struct.unpack(">H", take(2))[0]).decode("utf-8", "replace")
                out[key] = payload(kind)
            return out
        raise ValueError("bad NBT tag %d" % tag)

    assert take(1)[0] == 10
    take(struct.unpack(">H", take(2))[0])
    return payload(10)


def level(world):
    return nbt(gzip.decompress((Path(world) / "level.dat").read_bytes()))


class World:
    def __init__(self, world, folder="region"):
        self.dir = Path(world) / folder
        self.cache = {}

    def chunk(self, cx, cz):
        key = (cx, cz)
        if key in self.cache:
            return self.cache[key]
        path = self.dir / ("r.%d.%d.mca" % (cx >> 5, cz >> 5))
        out = None
        if path.is_file():
            with path.open("rb") as f:
                i = (cx & 31) + (cz & 31) * 32
                f.seek(4 * i)
                loc = struct.unpack(">I", f.read(4))[0]
                if loc >> 8:
                    f.seek((loc >> 8) * 4096)
                    length, kind = struct.unpack(">IB", f.read(5))
                    raw = f.read(length - 1)
                    raw = zlib.decompress(raw) if kind == 2 else gzip.decompress(raw) if kind == 1 else raw
                    out = nbt(raw)
        self.cache[key] = out
        return out

    def section(self, x, y, z):
        c = self.chunk(x >> 4, z >> 4)
        if c is None:
            return None, None
        for s in c.get("sections", []):
            if s["Y"] == y >> 4:
                return c, s
        return c, None

    @staticmethod
    def _index(data, bits, i):
        per = 64 // bits
        word = data[i // per] & 0xFFFFFFFFFFFFFFFF
        return (word >> ((i % per) * bits)) & ((1 << bits) - 1)

    def block(self, x, y, z):
        c, s = self.section(x, y, z)
        if s is None or "block_states" not in s:
            return None
        bs = s["block_states"]
        pal = bs["palette"]
        if len(pal) == 1:
            e = pal[0]
        else:
            bits = max(4, math.ceil(math.log2(len(pal))))
            e = pal[self._index(bs["data"], bits, ((y & 15) * 16 + (z & 15)) * 16 + (x & 15))]
        name = e["Name"]
        if e.get("Properties"):
            name += "[" + ",".join("%s=%s" % kv for kv in sorted(e["Properties"].items())) + "]"
        return name

    def biome(self, x, y, z):
        c, s = self.section(x, y, z)
        if s is None or "biomes" not in s:
            return None
        b = s["biomes"]
        pal = b["palette"]
        if len(pal) == 1:
            return pal[0]
        bits = max(1, math.ceil(math.log2(len(pal))))
        i = (((y & 15) >> 2) * 4 + ((z & 15) >> 2)) * 4 + ((x & 15) >> 2)
        return pal[self._index(b["data"], bits, i)]

    def light(self, x, y, z, kind="SkyLight"):
        c, s = self.section(x, y, z)
        if s is None or kind not in s:
            return None
        arr = s[kind]
        i = ((y & 15) * 16 + (z & 15)) * 16 + (x & 15)
        v = arr[i >> 1]
        return (v >> 4) & 15 if i & 1 else v & 15

    def height(self, x, z, kind="MOTION_BLOCKING"):
        c = self.chunk(x >> 4, z >> 4)
        if c is None or kind not in c.get("Heightmaps", {}):
            return None
        data = c["Heightmaps"][kind]
        bits = max(1, math.ceil(math.log2(384 + 1)))  # 9
        return self._index(data, bits, (z & 15) * 16 + (x & 15)) + c.get("yPos", -4) * 16


if __name__ == "__main__":
    w = World(sys.argv[1])
    x0, z0, x1, z1 = map(int, sys.argv[2:6])
    y = int(sys.argv[6]) if len(sys.argv) > 6 else None
    rows = {}
    for x in range(x0, x1 + 1, 8):
        for z in range(z0, z1 + 1, 8):
            h = w.height(x, z)
            rows["%d,%d" % (x, z)] = dict(h=h, surface=w.block(x, h - 1, z) if h is not None else None,
                                          biome=w.biome(x, y if y is not None else (h or 64), z),
                                          status=(w.chunk(x >> 4, z >> 4) or {}).get("Status"))
    print(json.dumps(rows, indent=0))
