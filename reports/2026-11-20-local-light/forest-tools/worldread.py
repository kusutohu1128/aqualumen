"""Read-only block access to the exact AqualumenNaturalV2 TEST save (no writes, no network).

Reuses the bounded NBT/Anvil decoder of tools/audit-fixture-air.py (repo file, imported by path).
"""
import importlib.util
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("audit_fixture_air", REPO / "tools/audit-fixture-air.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

WORLD, UUID, SEED = audit.WORLD, audit.UUID, audit.SEED


def validate_world():
    if WORLD.resolve() != WORLD.absolute():
        raise ValueError("World symlink redirection is forbidden")
    marker = dict(l.split("=", 1) for l in (WORLD / "aqualumen-world.properties").read_text().splitlines()
                  if l and not l.startswith("#"))
    audit.validate_marker(WORLD.name, marker)
    return marker


class World:
    def __init__(self):
        self.marker = validate_world()
        self.regions = {}
        self.chunks = {}
        self.stat = {}

    def region_bytes(self, rx, rz):
        key = (rx, rz)
        if key not in self.regions:
            path = WORLD / f"region/r.{rx}.{rz}.mca"
            if path.is_symlink() or not path.exists():
                self.regions[key] = None
            else:
                st = path.stat()
                data = path.read_bytes()
                self.stat[key] = (st.st_size, st.st_mtime_ns)
                self.regions[key] = data
        return self.regions[key]

    def chunk(self, cx, cz):
        key = (cx, cz)
        if key in self.chunks:
            return self.chunks[key]
        data = self.region_bytes(cx // 32, cz // 32)
        result = None
        if data is not None:
            try:
                nbt, _ = audit.decode_chunk(data, None, cx, cz)
                result = self._sections(nbt)
            except ValueError:
                result = None
        self.chunks[key] = result
        return result

    @staticmethod
    def _sections(nbt):
        out = {}
        for section in nbt["sections"]:
            states = section["block_states"]
            palette = states["palette"]
            if len(palette) == 1:
                out[section["Y"]] = (palette, None)
                continue
            bits = max(4, (len(palette) - 1).bit_length())
            per = 64 // bits
            mask = (1 << bits) - 1
            data = states["data"]
            idx = []
            for word in data:
                word &= (1 << 64) - 1
                for i in range(per):
                    idx.append((word >> (i * bits)) & mask)
            out[section["Y"]] = (palette, idx[:4096])
        return out

    def state(self, x, y, z):
        """Return the palette entry dict {'Name':..., 'Properties':{...}}; unloaded -> None."""
        sections = self.chunk(x // 16, z // 16)
        if sections is None:
            return None
        sec = sections.get(y // 16)
        if sec is None:
            return {"Name": "minecraft:air"}
        palette, idx = sec
        if idx is None:
            return palette[0]
        return palette[idx[(y % 16) * 256 + (z % 16) * 16 + (x % 16)]]

    def name(self, x, y, z):
        s = self.state(x, y, z)
        return None if s is None else s["Name"]

    def height_log_scan(self, cx, cz, names):
        """Yield (x,y,z,name) of blocks whose palette name is in names for one chunk."""
        sections = self.chunk(cx, cz)
        if sections is None:
            return
        for sy, (palette, idx) in sections.items():
            wanted = {i for i, p in enumerate(palette) if p["Name"] in names}
            if not wanted:
                continue
            if idx is None:
                continue
            for i, p in enumerate(idx):
                if p in wanted:
                    yield (cx * 16 + (i % 16), sy * 16 + i // 256, cz * 16 + (i // 16) % 16, palette[p]["Name"])

    def unchanged(self):
        for key, before in self.stat.items():
            p = WORLD / f"region/r.{key[0]}.{key[1]}.mca"
            st = p.stat()
            if (st.st_size, st.st_mtime_ns) != before:
                return False
        return True
