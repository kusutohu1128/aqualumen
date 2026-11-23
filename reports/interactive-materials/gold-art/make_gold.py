"""Build an original 32 px stone-hosted gold ore and an optically neutral control."""
from io import BytesIO
import json
import math
from pathlib import Path
import random
import zipfile

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
rng = random.Random(1701)

# Seamless value fields provide stone strata at two scales.
def noise_field(nx, ny):
    grid = [[rng.uniform(-1, 1) for _ in range(nx)] for _ in range(ny)]

    def sample(x, y):
        u, v = x * nx / SIZE, y * ny / SIZE
        i, j = math.floor(u), math.floor(v)
        tx, ty = u-i, v-j
        tx, ty = tx*tx*(3-2*tx), ty*ty*(3-2*ty)
        a = grid[j%ny][i%nx]*(1-tx) + grid[j%ny][(i+1)%nx]*tx
        b = grid[(j+1)%ny][i%nx]*(1-tx) + grid[(j+1)%ny][(i+1)%nx]*tx
        return a*(1-ty)+b*ty
    return sample

broad, fleck = noise_field(4, 7), noise_field(8, 11)
stone = [(93,91,90),(104,103,102),(113,113,112),(121,121,120),
         (129,128,126),(136,135,133),(145,143,141)]
ore = Image.new('RGB',(SIZE,SIZE))
for y in range(SIZE):
    for x in range(SIZE):
        bias = 2.55*broad(x+.8*math.sin(2*math.pi*y/SIZE), y+x) + 1.3*fleck(x,y)
        shade = max(0,min(6,round(3+bias+rng.uniform(-.23,.23))))
        ore.putpixel((x,y),stone[shade])

# Letters specify individual faces of a nugget. Directions remain constant per face.
grains = [
    (2,3,["..aab",".aaab","eccb.","ee..."]),
    (18,2,[".cbb","accb",".dd."]),
    (24,10,["..ee..",".aaeb.","acccb.","..ddb.","...d.."]),
    (12,13,["...b","..ab",".ace","ecd."]),
    (4,20,[".cb..","acbb.","accbd",".eed."]),
    (18,23,["...ac","..aac",".eed.","ee..."]),
    (28,27,[".ba","db."]),
    (9,28,[".ab","ee."]),
    (7,10,[".a","e."]),
    (20,18,["ab"]),
]
# Subdued ore albedo leaves highlight strength and hue to the lamp/shader.
facets = {
    'a':((186,145,68),  -.54, .27,211),
    'b':((196,154,72),   .43, .42,207),
    'c':((204,164,85),   .08,-.08,218),
    'd':((177,134,62),   .52,-.28,200),
    'e':((183,139,65),  -.31,-.51,204),
}
norm = Image.new('RGBA',ore.size,(128,128,255,255))
spec = Image.new('RGBA',ore.size,(35,0,0,255))
mask = set()
for group,(gx,gy,stamp) in enumerate(grains):
    for sy,line in enumerate(stamp):
        for sx,letter in enumerate(line):
            if letter=='.':
                continue
            p=(gx+sx,gy+sy)
            assert p not in mask
            mask.add(p)
            albedo,fx,fy,gloss=facets[letter]
            angle = (group%4)*math.pi/2
            dx,dy=fx*math.cos(angle)-fy*math.sin(angle),fx*math.sin(angle)+fy*math.cos(angle)
            ch=lambda v: round((v+1)*127.5)
            ore.putpixel(p,albedo)
            norm.putpixel(p,(ch(dx),ch(dy),255,255))
            spec.putpixel(p,(gloss,231,0,255))

# A few irregular embedding seams at the rock/gold boundary.
for x,y in sorted(mask):
    for dx,dy in ((1,0),(0,1)):
        p=((x+dx)%SIZE,(y+dy)%SIZE)
        if p not in mask and (3*x+7*y)%5 in (0,1):
            c=ore.getpixel(p)
            ore.putpixel(p,tuple(round(v*.89) for v in c))
def encode(img):
    stream=BytesIO();img.save(stream,'PNG');return stream.getvalue()
def put(z,name,data):
    entry=zipfile.ZipInfo(name,(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(entry,data)
prefix='assets/minecraft/textures/block/'
for variant in ('Faceted','Control'):
    target=HERE/f'Aqualumen-Gold-{variant}-32x.zip'
    maps={'gold_ore.png':ore,'gold_ore_n.png':norm,'gold_ore_s.png':spec}
    if variant=='Control':
        maps['gold_ore_n.png']=Image.new('RGBA',ore.size,(128,128,255,255))
        maps['gold_ore_s.png']=Image.new('RGBA',ore.size,(35,0,0,255))
    with zipfile.ZipFile(target,'w') as z:
        put(z,'pack.mcmeta', json.dumps({'pack': {'pack_format':34,'description':f'Aqualumen | {variant} gold ore, original 32x art'}}).encode())
        for filename,img in maps.items(): put(z,prefix+filename,encode(img))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for filename in maps:
            img=Image.open(BytesIO(z.read(prefix+filename)));img.load()
            assert img.size==(32,32)
assert len(mask)==sum(t[1]==231 for t in spec.getdata())
assert all(195<=spec.getpixel(p)[0]<=220 for p in mask)
assert all(norm.getpixel(p)[2:]==(255,255) for p in mask)
ore.resize((384,384),Image.Resampling.NEAREST).save(HERE/'Gold-art-preview.png')
print(len(mask),'gold pixels;',len(set(norm.getpixel(p)[:2] for p in mask)),'grain orientations')
