"""Measure displayed diagnostic palette regions, not raw shader ray values."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from water_coast_attribution_image import decode


def classify(rgb):
    red, green, blue = rgb
    if green > 2 * red and green > 2 * blue:
        return 'transmission'
    if blue > 2 * red and blue > 2 * green:
        return 'tir'
    if red > 2 * blue and green >= .3 * red and red >= .8 * green:
        return 'transmission_wrong_side'
    if red > 2 * blue and green < .3 * red:
        return 'reflection_wrong_side'
    return 'unclassified'


def classify_raw(rgb):
    red, green, blue = rgb
    if red == 0 and green in (127, 128) and blue == 0:
        return 'transmission'
    if red == 0 and green == 0 and blue in (127, 128):
        return 'tir'
    if red == 255 and green in (89, 90) and blue == 0:
        return 'transmission_wrong_side'
    if red == 255 and green == 0 and blue == 0:
        return 'reflection_wrong_side'
    if red == 255 and green == 255 and blue == 0:
        return 'admitted_downward_transmission'
    if red == 0 and green == 0 and blue == 0:
        return 'unobserved'
    return 'unclassified'


def measure(path, raw_interface=False):
    raw = path.read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG')
    width, height = struct.unpack_from('>II', raw, 16)
    if width * height > 16777216:
        raise ValueError('Image exceeds diagnostic pixel limit')
    pixels, channels = decode(raw, (width, height))
    classifier = classify_raw if raw_interface else classify
    counts = Counter(classifier(pixels[offset:offset + 3])
                     for offset in range(0, len(pixels), channels))
    if raw_interface and (counts['unclassified'] or not (counts['transmission'] + counts['tir'])):
        raise ValueError('Raw interface target has unknown codes or no positive water observation')
    return dict(image=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                resolution=[width, height], pixels=width * height, counts=dict(counts),
                fractions={name: count / (width * height) for name, count in counts.items()},
                evidence=('Untonemapped RGBA8 interface status target; not raw ray-vector readback'
                          if raw_interface else 'Displayed palette estimate after compositing; not raw ray-status readback'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', type=Path, nargs='+')
    parser.add_argument('--raw-interface', action='store_true')
    arguments = parser.parse_args()
    print(json.dumps([measure(path, arguments.raw_interface) for path in arguments.images], indent=2))
