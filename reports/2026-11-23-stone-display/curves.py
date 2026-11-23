"""Linear-light reference implementation and numerical checks of the SDR display transform."""
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-brick-scan"))
from read_niche import LUMA


def reference(c):
    return c / (1 + c.max(axis=-1, keepdims=True))


def candidate(c):
    key = .3 * (c @ LUMA) + .7 * c.max(axis=-1)
    t = np.clip((key - .12) / .88, 0., 1.)
    bridge = .12 + t * (.88 + t * (-1.43544 + .86544 * t))
    drive = np.where(key <= .12, key, np.where(key <= 1., bridge, .43 * key**1.6))
    value = drive / (1 + drive)
    rgb = c * (value / np.maximum(key, 1.e-8))[..., None]
    y = rgb @ LUMA
    delta = rgb - y[..., None]
    span = delta.max(axis=-1) / np.maximum(1 - y, 1.e-6)
    excess = np.maximum(0., span - .85)
    limited = .85 + excess / (1 + excess / .15)
    return y[..., None] + delta * np.minimum(1., limited / np.maximum(span, 1.e-12))[..., None]


def diffuse(c,strength=1.):
    peak=c.max(axis=-1)
    v=peak/(1.+peak)
    pivot=2./3.
    below=v<pivot
    width=np.where(below,pivot-.43,.82-pivot)
    t=np.clip(np.where(below,v-.43,v-pivot)/width,0.,1.)
    offset=(2.1*strength)*width*t*(1-t)*np.where(below,-t,1-t)
    return reference(c)*(1.+offset/np.maximum(v,1.e-10))[...,None]


def validate_rays(curve=candidate):
    hues = np.array(np.meshgrid(*[np.linspace(0, 1, 9)] * 3)).reshape(3, -1).T
    gains = np.geomspace(.00001, 65504., 1024)
    output = curve(hues[:, None, :] * gains[None, :, None])
    derivative = np.diff(output @ LUMA, axis=1)
    assert derivative.min() >= -1.e-12 and output.min() >= -1.e-10 and output.max() <= 1.000001
    return dict(rays=len(hues), levels=len(gains), maxInput=gains[-1],
                minOutput=float(output.min()), maxOutput=float(output.max()))


if __name__ == "__main__":
    print(validate_rays())
