"""Contact sheets for review: zoomed tiles, a mixed-variant log wall, ore set in stone, and a distant view."""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
T = HERE / 'textures'
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22)
load = lambda n: Image.open(T / n).convert('RGB')
side = [load(f'birch_side_{i}.png') for i in range(3)]
top, stone, ore = load('birch_top.png'), load('stone.png'), load('gold_ore.png')
norm, spec = load('gold_ore_n.png'), load('gold_ore_s.png')

def zoom(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)

def wall(pick, cols, rows):
    w = Image.new('RGB', (32 * cols, 32 * rows))
    for y in range(rows):
        for x in range(cols):
            w.paste(pick(x, y), (32 * x, 32 * y))
    return w

def shade(im, f): return im.point(lambda v: int(v * f))

rng = random.Random(5)
weights = [0] * 5 + [1] * 3 + [2] * 3
logs = wall(lambda x, y: side[rng.choice(weights)], 4, 6)
# Fake tree corner: two faces with Minecraft-like directional shading, top cap above.
tree = Image.new('RGB', (128, 224), (60, 80, 60))
for y in range(6):
    v = side[rng.choice(weights)]
    tree.paste(shade(v, .8), (0, 32 + 32 * y)); tree.paste(shade(v, .6), (32, 32 + 32 * y))
    v = side[rng.choice(weights)]
    tree.paste(shade(v, .8), (72, 32 + 32 * y)); tree.paste(shade(v, .6), (104 - 8, 32 + 32 * y))
tree.paste(top, (0, 0)); tree.paste(top, (72, 0))
mine = wall(lambda x, y: ore if (x, y) in {(1, 1), (2, 1), (2, 2), (4, 2)} else stone, 6, 4)

sheet = Image.new('RGB', (1720, 1500), (32, 34, 34))
d = ImageDraw.Draw(sheet)
def label(t, x, y): d.text((x, y), t, font=font, fill='white')
label('白樺 側面 0 / 1 / 2 と上面（10倍）', 16, 8)
for i, im in enumerate(side + [top]):
    sheet.paste(zoom(im, 10), (16 + i * 336, 44))
label('白樺 ランダム壁（4倍）', 16, 380)
sheet.paste(zoom(logs, 4).crop((0, 0, 512, 768)), (16, 416))
label('簡易コーナー', 548, 380)
sheet.paste(zoom(tree, 3), (548, 416))
label('石 / 金鉱石 / 法線 / スペキュラー（6倍）', 960, 380)
for i, im in enumerate((stone, ore, norm, spec)):
    sheet.paste(zoom(im, 6), (960 + (i % 2) * 200, 416 + (i // 2) * 200))
    sheet.paste(zoom(im, 6).crop((0, 0, 192, 192)), (960 + (i % 2) * 200, 416 + (i // 2) * 200))
label('石壁に金鉱石（3倍）', 960, 824)
sheet.paste(zoom(mine, 3).crop((0, 0, 576, 384)), (960, 860))
label('遠景（1/2 縮小 → 2倍表示）', 16, 1200)
far = logs.resize((64, 96), Image.BOX)
sheet.paste(zoom(far, 2).crop((0, 0, 128, 192)), (16, 1236))
farm = mine.resize((96, 64), Image.BOX)
sheet.paste(zoom(farm, 2), (180, 1236))
sheet.save(HERE / 'review.png')
