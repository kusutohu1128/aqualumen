"""Read-only biome census of every saved chunk of AqualumenNaturalV2 (centre column, y=64 section).
Usage: python3 -I biomemap.py out.json
"""
import json, sys
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import audit, WORLD


def region(rc):
    rx, rz = rc
    p = WORLD / f"region/r.{rx}.{rz}.mca"
    data = p.read_bytes()
    out = {}
    for lz in range(32):
        for lx in range(32):
            off = (lx + lz * 32) * 4
            if data[off:off + 4] == b"\0\0\0\0":
                continue
            cx, cz = rx * 32 + lx, rz * 32 + lz
            try:
                nbt, _ = audit.decode_chunk(data, None, cx, cz)
            except ValueError:
                continue
            if nbt.get("Status") != "minecraft:full":
                continue
            sec = {s["Y"]: s for s in nbt["sections"]}.get(4)
            if not sec:
                continue
            b = sec["biomes"]; pal = b["palette"]
            if len(pal) == 1:
                out[f"{cx},{cz}"] = pal[0][10:]
            else:
                bits = max(1, (len(pal) - 1).bit_length()); per = 64 // bits
                i = 2 * 16 + 2 * 4 + 2
                out[f"{cx},{cz}"] = pal[((b["data"][i // per] & (2**64 - 1)) >> ((i % per) * bits)) & ((1 << bits) - 1)][10:]
    return out


if __name__ == "__main__":
    regs = [tuple(int(v) for v in f.name[2:-4].split(".")) for f in (WORLD / "region").glob("r.*.mca")]
    with Pool(8) as pool:
        res = pool.map(region, regs)
    m = {}
    for r in res:
        m.update(r)
    json.dump(m, open(sys.argv[1], "w"))
    from collections import Counter
    print(len(m), Counter(m.values()).most_common())
