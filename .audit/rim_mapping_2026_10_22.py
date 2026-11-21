import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from water_optical_audit import ROIS, load

parser = argparse.ArgumentParser()
parser.add_argument('capture', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
manifest, data = load(args.capture)
w, h = manifest['width'], manifest['height']
fields = {key:np.asarray(value).reshape(h,w,4)[::-1].astype(np.float64) for key,value in data.items()}
rays = fields['optics-colortex15'][...,:3]
fresnel = fields['classification'][...,1]
water = fields['classification'][...,3] == 1
valid = water & (fresnel < .9999)
dy = np.gradient(rays, axis=0)
dx = np.gradient(rays, axis=1)
jacobian = np.sum(np.cross(dx,dy)*rays,axis=2)
support = valid.copy()
support[[0,-1],:] = False
support[:,[0,-1]] = False
support[1:-1,1:-1] &= valid[:-2,1:-1] & valid[2:,1:-1] & valid[1:-1,:-2] & valid[1:-1,2:]
orient = np.sign(np.median(jacobian[400:500,750:850]))
assert orient != 0
opposed = support & (jacobian*orient < -1e-10)
args.output.mkdir(exist_ok=False)
azimuth = np.arctan2(rays[...,2],rays[...,0])
elevation = np.arcsin(np.clip(rays[...,1],-1,1))
grid = np.stack((.55+.35*np.cos(12*azimuth),.55+.35*np.cos(16*elevation),.55+.35*np.sin(9*azimuth+8*elevation)),axis=2)
grid = grid*(1-fresnel[...,None]) + np.array([.015,.03,.05])*fresnel[...,None]
Image.fromarray(np.uint8(np.clip(grid,0,1)*255)).save(args.output/'direction-grid.png')
mask = np.zeros((h,w,3),np.uint8)
mask[support] = (70,70,70)
mask[opposed] = (255,190,0)
mask[valid & (rays[...,1]<0)] = (255,0,255)
Image.fromarray(mask).save(args.output/'direction-fold-mask.png')
result = dict(scene=manifest['scene'], frame=manifest['frame'],
    manifestSHA256=hashlib.sha256((args.capture/'manifest.json').read_bytes()).hexdigest(),
    supported=int(support.sum()), locallyReversedDirectionMapping=int(opposed.sum()), regions={})
for name,(x0,y0,x1,y1) in ROIS.items():
    region = np.s_[y0:y1,x0:x1]
    count = int(support[region].sum())
    result['regions'][name] = dict(supported=count, locallyReversed=int(opposed[region].sum()),
        minimumTransmittedY=float(np.min(rays[region][valid[region],1])) if valid[region].any() else None)
result['interpretationLimits'] = [
    'A reversed direction-map Jacobian is a fold in the recorded optical mapping, not by itself a rendering bug.',
    'Procedural directional grid omits sky LUT, world reflection, water medium and FINAL tonemapping.',
    'Invalid/TIR neighbors are excluded from Jacobian support; critical or one-pixel derivatives are not a full subpixel integration.',
    'Compare a qualified continuous-heightfield reference before calling these folds nonphysical.']
with (args.output/'result.json').open('x') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(result))
