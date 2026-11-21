"""Post-process one finished run: before/after comparison JPG + compact MP4 from the real journey.mkv. Usage: finish.py <run-dir>"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
d = Path(sys.argv[1])
pairs = [('01-spawn-before', 'spawn (before)'), ('02-shelf-lava-before', 'ledge, natural lava'), ('03-soul-torch-lava', 'soul torch placed'),
         ('04-water-flow-1', 'water poured (8 s)'), ('05-obsidian-after', 'after: water retrieved'), ('04-lava-pickup-1', 'lava source taken (14 s)'), ('05-lava-source-removed', 'after: source removed')]
tiles = [(Image.open(d / (n + '.png')).convert('RGB'), t) for n, t in pairs if (d / (n + '.png')).exists()]
w, h = 800, 450
sheet = Image.new('RGB', (w * 2, h * ((len(tiles) + 1) // 2)), (0, 0, 0))
for i, (im, t) in enumerate(tiles):
    im = im.resize((w, h), Image.LANCZOS); dr = ImageDraw.Draw(im); dr.rectangle([0, 0, 330, 18], fill=(0, 0, 0)); dr.text((4, 3), t, fill=(255, 255, 255))
    sheet.paste(im, ((i % 2) * w, (i // 2) * h))
sheet.save(d / 'comparison.jpg', quality=88)
if (d / 'journey.mkv').exists():
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(d / 'journey.mkv'), '-vf', 'scale=1024:-2,fps=15', '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-an', str(d / 'journey-compact.mp4')], check=True)
print('done')
