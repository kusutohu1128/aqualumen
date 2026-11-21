"""Read-only bounded Anvil/NBT audit of the exact approved disposable fixture.

No network, control requests, writes, Minecraft process actions or user saves.
Print evidence to stdout; callers persist it separately using apply_patch.
"""
import collections
import hashlib
import json
import math
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

WORLD = Path.home() / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft/saves/AqualumenNaturalV2"
UUID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SEED = "308060"
LIMIT = 64 * 1024 * 1024


class NBT:
    def __init__(self, payload):
        if len(payload) > LIMIT:
            raise ValueError("Uncompressed NBT exceeds audit bound")
        self.payload, self.offset = payload, 0

    def take(self, size):
        if size < 0 or self.offset + size > len(self.payload):
            raise ValueError("Truncated or negative NBT length")
        value = self.payload[self.offset:self.offset + size]
        self.offset += size
        return value

    def number(self, fmt):
        return struct.unpack(">" + fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self):
        return self.take(self.number("H")).decode("utf-8")

    def array_length(self, item_size):
        count = self.number("i")
        if count < 0 or count > LIMIT // item_size:
            raise ValueError("NBT array/list exceeds audit bound")
        return count

    def value(self, tag, depth=0):
        if depth > 64:
            raise ValueError("NBT nesting exceeds audit bound")
        if tag in (1, 2, 3, 4, 5, 6):
            return self.number({1: "b", 2: "h", 3: "i", 4: "q", 5: "f", 6: "d"}[tag])
        if tag == 7:
            return self.take(self.array_length(1))
        if tag == 8:
            return self.string()
        if tag == 9:
            element = self.number("B")
            count = self.array_length(1)
            if element == 0 and count:
                raise ValueError("Nonempty TAG_End list")
            return [self.value(element, depth + 1) for _ in range(count)]
        if tag == 10:
            values = {}
            while True:
                item = self.number("B")
                if item == 0:
                    return values
                name = self.string()
                if name in values:
                    raise ValueError("Duplicate compound key")
                values[name] = self.value(item, depth + 1)
        if tag in (11, 12):
            fmt, size = ("i", 4) if tag == 11 else ("q", 8)
            return [self.number(fmt) for _ in range(self.array_length(size))]
        raise ValueError(f"Unknown NBT tag {tag}")

    def root(self):
        if self.number("B") != 10:
            raise ValueError("Expected compound NBT root")
        self.string()
        result = self.value(10)
        if self.offset != len(self.payload):
            raise ValueError("Unparsed trailing NBT bytes")
        return result


def decode_chunk(region_bytes, region, cx, cz):
    index = (cx % 32) + (cz % 32) * 32
    location = int.from_bytes(region_bytes[index * 4:index * 4 + 4], "big")
    sector, allocation = location >> 8, location & 255
    if sector < 2 or allocation < 1:
        raise ValueError(f"Chunk {cx},{cz} is absent from saved Anvil region")
    offset = sector * 4096
    if offset + 5 > len(region_bytes):
        raise ValueError("Chunk offset outside region")
    length = int.from_bytes(region_bytes[offset:offset + 4], "big")
    codec = region_bytes[offset + 4]
    if length < 1 or length + 4 > allocation * 4096 or offset + length + 4 > len(region_bytes):
        raise ValueError("Chunk length outside allocation/file")
    compressed = region_bytes[offset + 5:offset + 4 + length]
    if codec & 128:
        raise ValueError("External Anvil chunk is outside this bounded audit plan")
    if codec == 2:
        stream = zlib.decompressobj()
        payload = stream.decompress(compressed, LIMIT + 1)
        if len(payload) > LIMIT or not stream.eof or stream.unconsumed_tail or stream.unused_data:
            raise ValueError("Invalid/oversized compressed chunk")
    elif codec == 1:
        # Current Minecraft uses zlib. Refuse an unbounded gzip decode rather
        # than silently broadening this bounded, production-file reader.
        raise ValueError("Gzip chunk is outside this bounded audit plan")
    elif codec == 3:
        payload = compressed
    else:
        raise ValueError(f"Unsupported Anvil codec {codec}")
    chunk = NBT(payload).root()
    if (chunk.get("xPos"), chunk.get("zPos")) != (cx, cz) or chunk.get("DataVersion") != 3955:
        raise ValueError("Chunk coordinates or Minecraft1.21.1 DataVersion mismatch")
    return chunk, {"chunk": [cx, cz], "sector_offset": sector, "allocated_sectors": allocation,
                   "compressed_bytes": len(compressed), "codec": codec,
                   "nbt_sha256": hashlib.sha256(payload).hexdigest(),
                   "data_version": chunk["DataVersion"], "status": chunk.get("Status"),
                   "last_update": chunk.get("LastUpdate")}


def block_state(chunk, x, y, z):
    section_y = y // 16
    matches = [section for section in chunk["sections"] if section["Y"] == section_y]
    if len(matches) != 1:
        raise ValueError("Missing or duplicate fixture block section")
    states = matches[0]["block_states"]
    palette = states["palette"]
    if not 1 <= len(palette) <= 4096:
        raise ValueError("Invalid block-state palette")
    if len(palette) == 1:
        palette_index = 0
    else:
        bits = max(4, (len(palette) - 1).bit_length())
        per_long = 64 // bits
        index = (y % 16) * 256 + (z % 16) * 16 + (x % 16)
        data = states["data"]
        if len(data) != math.ceil(4096 / per_long):
            raise ValueError("Packed block-state array length mismatch")
        word = data[index // per_long] & ((1 << 64) - 1)
        palette_index = (word >> ((index % per_long) * bits)) & ((1 << bits) - 1)
    if palette_index >= len(palette):
        raise ValueError("Palette index outside actual saved palette")
    return palette[palette_index]


def approved_cells():
    """Return only the six reviewed plots, never caller-supplied coordinates."""
    plots = [
        {"range": "near", "kind": "wall", "bounds": [444,157,-367,452,165,-367]},
        {"range": "near", "kind": "target", "bounds": [445,158,-361,451,164,-361]},
        {"range": "far", "kind": "wall", "bounds": [444,157,-239,452,165,-239]},
        {"range": "far", "kind": "target", "bounds": [445,158,-233,451,164,-233]},
        {"range": "west-air", "kind": "wall", "bounds": [432,157,-387,432,165,-379]},
        {"range": "west-air", "kind": "target", "bounds": [426,158,-386,426,164,-380]},
    ]
    cells = set()
    for plot in plots:
        x0,y0,z0,x1,y1,z1 = plot["bounds"]
        reserved = {(x,y,z) for x in range(x0,x1+1) for y in range(y0,y1+1) for z in range(z0,z1+1)}
        if cells.intersection(reserved):
            raise ValueError("Unexpected overlapping fixture plots")
        cells.update(reserved)
        plot["cells"] = len(reserved)
    if len(cells) != 390:
        raise ValueError("Wrong approved unique-cell count")
    return cells, plots


def validate_marker(name, marker):
    if (name != "AqualumenNaturalV2" or marker.get("world_id") != UUID or marker.get("seed") != SEED or
            marker.get("schema") != "2" or marker.get("generator") != "minecraft:noise/overworld"):
        raise ValueError("Exact disposable save/UUID/seed/generator authorization failed")


def main():
    # No world or plot override exists. Symlink redirection is also forbidden.
    if WORLD.resolve() != WORLD.absolute():
        raise ValueError("World symlink redirection is forbidden")
    marker = dict(line.split("=", 1) for line in (WORLD / "aqualumen-world.properties").read_text().splitlines() if line and not line.startswith("#"))
    validate_marker(WORLD.name, marker)
    journal = WORLD.parent.parent / "aqualumen-benchmark/opaque-fixture-journal.json"
    if journal.exists() or journal.is_symlink():
        raise ValueError("A pending fixture ownership journal prevents a clean saved-world audit")
    cells, plots = approved_cells()
    region = WORLD / "region/r.0.-1.mca"
    if region.is_symlink():
        raise ValueError("Region symlink redirection is forbidden")
    stat_before = region.stat()
    if not 8192 <= stat_before.st_size <= LIMIT:
        raise ValueError("Region file exceeds bounded read")
    with region.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if len(data) != stat_before.st_size:
        raise ValueError("Region file changed or exceeded bounded read")
    chunks, chunk_records = {}, []
    for cx, cz in sorted({(x // 16, z // 16) for x, y, z in cells}):
        if (cx // 32, cz // 32) != (0, -1):
            raise ValueError("Coordinate outside approved region")
        chunk, record = decode_chunk(data, region, cx, cz)
        chunks[cx, cz] = chunk
        record["checked_cells"] = sum((x // 16, z // 16) == (cx, cz) for x, y, z in cells)
        record["checked_sections"] = [9, 10]
        chunk_records.append(record)
    states = collections.Counter()
    non_air = []
    for x, y, z in sorted(cells):
        state = block_state(chunks[x // 16, z // 16], x, y, z)
        states[state["Name"]] += 1
        if state != {"Name": "minecraft:air"}:
            non_air.append({"position": [x, y, z], "state": state})
    stat_after = region.stat()
    if (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns):
        raise ValueError("Save changed during read-only audit; evidence rejected")
    no_journal = not (journal.exists() or journal.is_symlink())
    print(json.dumps({"audit": "read-only persisted Anvil fixture AIR audit", "utc": datetime.now(timezone.utc).isoformat(),
        "world_directory": str(WORLD), "world_id": UUID, "seed_marker": marker.get("seed"),
        "region": str(region), "region_sha256": hashlib.sha256(data).hexdigest(),
        "region_size_bytes": len(data), "region_mtime_ns": stat_after.st_mtime_ns,
        "method": "Read actual saved chunk palette and padded packed block-state indices; no runtime journal used",
        "plots": plots, "chunks": chunk_records, "checked_unique_cells": len(cells),
        "actual_state_counts": dict(states), "all_exact_air": not non_air, "non_air_cells": non_air,
        "no_pending_fixture_journal": no_journal, "cleanup_pass": not non_air and no_journal,
        "world_writes": False, "control_requests": False}, indent=2))
    return 0 if not non_air and no_journal else 1


if __name__ == "__main__":
    raise SystemExit(main())
