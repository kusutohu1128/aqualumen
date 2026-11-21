"""Numeric audit of a run directory (stdlib + ffmpeg only).

    python3 analyze.py <run-dir> [<other-run-dir>]

Per stage (game-side F2 image): mean linear luminance over the white-wall ROI, 8 vertical-band profile, and the
delta against the `dark` stage; x11grab-vs-F2 agreement; restoration exactness (restored-* vs original stage).
With two directories it also prints the per-stage change (second minus first). Writes analysis.json in each run dir.
"""
import json
import subprocess
import sys
from pathlib import Path

W, H = 1280, 720
ROI = (40, 40, 800, 300)  # x0, y0, x1, y1: plain white concrete wall in the fixed camera view
LUT = [((c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4) for c in range(256)]
RESTORE_OF = {'restored-mixed': 'torch-lava1-open', 'restored-dark': 'dark'}


def raw(path):
    global W, H
    data = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], check=True, capture_output=True).stdout
    assert len(data) == W * H * 3, path
    return data


def lum(px, o):
    return 0.2126 * LUT[px[o]] + 0.7152 * LUT[px[o + 1]] + 0.0722 * LUT[px[o + 2]]


def roi_stats(px):
    x0, y0, x1, y1 = ROI
    tot, n = 0.0, 0
    bands = [0.0] * 8
    bw = (x1 - x0) // 8
    for y in range(y0, y1, 2):
        base = y * W * 3
        for x in range(x0, x1, 2):
            v = lum(px, base + x * 3)
            tot += v
            n += 1
            bands[min(7, (x - x0) // bw)] += v

    per = n // 8
    return tot / n, [b / (n / 8) for b in bands]


def diff(a, b):
    """(mean abs 8-bit channel difference over the frame, max abs difference)."""
    s = 0
    m = 0
    for i in range(0, len(a), 7):
        d = abs(a[i] - b[i])
        s += d
        m = max(m, d)
    return s / len(range(0, len(a), 7)), m


def analyze(run):
    run = Path(run)
    meta = json.loads((run / 'complete.json').read_text())
    global W, H, ROI
    W, H = meta.get('size', [1280, 720])
    ROI = tuple(int(v * W / 1280) if i % 2 == 0 else int(v * H / 720) for i, v in enumerate((40, 40, 800, 300)))
    shots = meta['screenshots']
    images = {n: {t: raw(run / ('%s-%s.png' % (n, t))) for t in s} for n, s in shots.items()}
    out = dict(run=str(run), pack=meta['pack'], renderer=meta['gl']['renderer'], backend=meta['backend'], stages={})
    base = None
    if 'dark' in images:
        base = roi_stats(images['dark']['ingame'])[0]
    for n, imgs in images.items():
        mean, bands = roi_stats(imgs['ingame'])
        entry = dict(roiMeanLinear=mean, bands=bands, deltaVsDark=(mean - base) if base is not None else None,
                     ratioVsDark=(mean / base) if base else None,
                     x11VsIngameMeanAbs=diff(imgs['ingame'], imgs['x11-a'])[0],
                     x11PairMeanAbs=diff(imgs['x11-a'], imgs['x11-b'])[0])
        out['stages'][n] = entry
    for r, o in RESTORE_OF.items():
        if r in images and o in images:
            ma, mx = diff(images[r]['ingame'], images[o]['ingame'])
            out['stages'][r]['restoreVs_' + o] = dict(meanAbs8bit=ma, maxAbs8bit=mx, roiMeanDelta=out['stages'][r]['roiMeanLinear'] - out['stages'][o]['roiMeanLinear'])
    (run / 'analysis.json').write_text(json.dumps(out, indent=2))
    return out


def table(a, b=None):
    print('%-22s %10s %10s %8s' % ('stage', 'roiMean', 'dVsDark', 'ratio') + ('   %10s %10s' % ('other', 'other-this') if b else ''))
    for n, e in a['stages'].items():
        line = '%-22s %10.5f %10.5f %8.3f' % (n, e['roiMeanLinear'], e['deltaVsDark'] or 0, e['ratioVsDark'] or 0)
        if b and n in b['stages']:
            line += '   %10.5f %10.5f' % (b['stages'][n]['roiMeanLinear'], b['stages'][n]['roiMeanLinear'] - e['roiMeanLinear'])
        print(line)
        for k, v in e.items():
            if k.startswith('restoreVs_'):
                print('    %s: meanAbs=%.3f maxAbs=%d roiDelta=%.6f' % (k, v['meanAbs8bit'], v['maxAbs8bit'], v['roiMeanDelta']))


if __name__ == '__main__':
    runs = [analyze(p) for p in sys.argv[1:3]]
    print('# %s renderer=%s backend=%s' % (runs[0]['pack'], runs[0]['renderer'], runs[0]['backend']))
    table(runs[0], runs[1] if len(runs) > 1 else None)
