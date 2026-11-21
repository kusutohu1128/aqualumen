"""Minimal stdlib NBT + Anvil reader (read-only). No third-party dependencies."""
import gzip, io, struct, zlib

def _read(f, t):
    if t == 1: return struct.unpack('>b', f.read(1))[0]
    if t == 2: return struct.unpack('>h', f.read(2))[0]
    if t == 3: return struct.unpack('>i', f.read(4))[0]
    if t == 4: return struct.unpack('>q', f.read(8))[0]
    if t == 5: return struct.unpack('>f', f.read(4))[0]
    if t == 6: return struct.unpack('>d', f.read(8))[0]
    if t == 7:
        n = struct.unpack('>i', f.read(4))[0]; return list(struct.unpack('>%db' % n, f.read(n)))
    if t == 8:
        n = struct.unpack('>H', f.read(2))[0]; return f.read(n).decode('utf-8', 'replace')
    if t == 9:
        it = f.read(1)[0]; n = struct.unpack('>i', f.read(4))[0]
        return [_read(f, it) for _ in range(n)]
    if t == 10:
        d = {}
        while True:
            tt = f.read(1)[0]
            if tt == 0: return d
            n = struct.unpack('>H', f.read(2))[0]; k = f.read(n).decode('utf-8', 'replace')
            d[k] = _read(f, tt)
    if t == 11:
        n = struct.unpack('>i', f.read(4))[0]; return list(struct.unpack('>%di' % n, f.read(4 * n)))
    if t == 12:
        n = struct.unpack('>i', f.read(4))[0]; return list(struct.unpack('>%dq' % n, f.read(8 * n)))
    raise ValueError('bad tag %d' % t)

def parse(raw):
    f = io.BytesIO(raw)
    t = f.read(1)[0]
    n = struct.unpack('>H', f.read(2))[0]; f.read(n)
    return _read(f, t)

def load_gz(path):
    with open(path, 'rb') as fh:
        return parse(gzip.decompress(fh.read()))

class Region:
    """Reads one r.X.Z.mca (opened read-only)."""
    def __init__(self, path):
        with open(path, 'rb') as fh:
            self.data = fh.read()
        if len(self.data) < 8192: self.data = self.data.ljust(8192, b'\0')  # empty/short file: no chunks
    def chunk(self, cx, cz):
        i = (cx & 31) + (cz & 31) * 32
        e = struct.unpack('>I', self.data[4 * i:4 * i + 4])[0]
        off, cnt = e >> 8, e & 255
        if off == 0: return None
        o = off * 4096
        ln = struct.unpack('>I', self.data[o:o + 4])[0]
        comp = self.data[o + 4]
        body = self.data[o + 5:o + 4 + ln]
        if comp == 2: return parse(zlib.decompress(body))
        if comp == 1: return parse(gzip.decompress(body))
        if comp == 3: return parse(body)
        raise ValueError('compression %d' % comp)
    def present(self):
        out = []
        for i in range(1024):
            if struct.unpack('>I', self.data[4 * i:4 * i + 4])[0] >> 8: out.append((i & 31, i >> 5))
        return out

def block_at(chunk, x, y, z):
    """Block state {Name, Properties} at world coords inside the chunk (1.21.1 layout)."""
    secs = {s['Y']: s for s in chunk['sections']}
    sy = y >> 4
    s = secs.get(sy)
    if s is None or 'block_states' not in s: return {'Name': 'minecraft:air'}
    bs = s['block_states']; pal = bs['palette']
    if len(pal) == 1: return pal[0]
    data = bs.get('data')
    bits = max(4, (len(pal) - 1).bit_length())
    per = 64 // bits
    idx = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
    word = data[idx // per] & 0xFFFFFFFFFFFFFFFF
    return pal[(word >> ((idx % per) * bits)) & ((1 << bits) - 1)]
