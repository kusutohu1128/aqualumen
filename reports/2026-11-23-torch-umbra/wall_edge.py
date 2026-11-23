"""Measure the hand lamp's shadow edge on a visible row of the Minecraft wall."""

import json
from itertools import product
import math
import numpy as np
from PIL import Image
from motion_results import HERE, A, B, W, H, RGB_Y, intersects

fov = np.radians(35)
pitch = np.radians(4)
right = np.array([1., 0., 0.])
up = np.array([0., np.cos(pitch), -np.sin(pitch)])
forward = np.array([0., -np.sin(pitch), -np.cos(pitch)])
taps = np.array([[.66,0],[-.33,.57156],[-.33,-.57156]])
n = np.arange(8192)
theta = n*np.pi*(3-np.sqrt(5))
dense = np.sqrt((n+.5)/len(n))[:,None]*np.column_stack((np.cos(theta),np.sin(theta)))


def single_edge(start, lamp, axis, ortho):
    # The fixture's complete, isolated column lies between the receiver plane
    # and the disk. An edge can clip the disk only if its supporting plane
    # separates the receiver's cone from the outside of the column.
    corners = np.array(list(product((406.,407.),(151.,153.),(-410.,-409.)))) - start
    assert start[2] < -410 and lamp[2] - math.hypot(axis[2],ortho[2]) > -409
    partial = []
    for i, a in enumerate(corners):
        for bit in (1,2,4):
            j = i ^ bit
            if j < i:
                continue
            normal = np.cross(a,corners[j])
            planes = corners @ normal
            if planes.min() < -1e-8 and planes.max() > 1e-8:
                continue
            if planes.min() < -1e-8:
                normal = -normal
            centre = (lamp-start) @ normal
            span = math.hypot(axis @ normal, ortho @ normal)
            if centre < -span:
                return 1.0
            if -span < centre < span:
                partial.append(centre/span)
    if not partial:
        return 0.0
    if len(partial) > 1:
        return None
    d = partial[0]
    return (math.acos(d) - d*math.sqrt(1-d*d))/math.pi


def profile(side, x, y):
    eye = np.array([x,152.62,-407.25])
    lamp = eye + .32*right - .30*up + .43*forward
    def load(suffix):
        return np.asarray(Image.open(HERE/"moving-umbra-r2"/f"hand-{side}-{suffix}-ingame.png").convert("RGB"))
    oak, clear = load("oak"), load("clear")
    samples = []
    for wx in np.arange(404.04,409.96,0.01):
        p = np.array([wx,y,-412.])
        if intersects(eye, p, .012):
            continue
        delta = p-eye
        focal = (H/2)/np.tan(fov)
        u = int(np.floor(W/2 + focal*(delta@right)/(delta@forward)))
        v = int(np.floor(H/2 - focal*(delta@up)/(delta@forward)))
        if not (0 <= u < W and 0 <= v < H):
            continue
        start = p + [0.,0.,.025]
        ray = (lamp-p)/np.linalg.norm(lamp-p)
        axis = np.cross(ray,[0.,1.,0.])
        axis *= .13/np.linalg.norm(axis)
        ortho = np.cross(ray,axis)
        def visible(points):
            targets = lamp + points[:,:1]*axis + points[:,1:]*ortho
            return 1.0 - float(intersects(start,targets,0.).mean())
        disk = visible(dense)
        if not 0.001 < disk < .999:
            continue
        samples.append(dict(worldX=round(float(wx),3), pixel=[u,v], threeTaps=visible(taps),
                            singleEdge=single_edge(start, lamp, axis, ortho),
                            disk=round(disk,5), oakY=float(oak[v,u]@RGB_Y), clearY=float(clear[v,u]@RGB_Y)))
    assert len(samples)>10
    errors=[abs(q["threeTaps"]-q["disk"]) for q in samples]
    edge_errors=[abs(q["singleEdge"]-q["disk"]) for q in samples if q["singleEdge"] is not None]
    assert edge_errors and max(edge_errors)<.003
    return dict(lineY=y, lineZ=-412, cameraX=x, referenceRaysPerReceiver=len(n), partialReceivers=len(samples),
                singleEdgeReceivers=len(edge_errors), singleEdgeMaxError=max(edge_errors),
                singleEdgeMeanError=float(np.mean(edge_errors)),
                meanVisibilityError=float(np.mean(errors)), maxVisibilityError=max(errors), samples=samples)


if __name__=="__main__":
    # The right-hand pose hides the mid-height edge behind the column. Sample
    # the upper edge where the viewer can see the receiver in both captures.
    data={k:profile(k,x,y) for k,x,y in (("left",A,152.30),("right",B,154.05))}
    (HERE/"wall-edge.json").write_text(json.dumps(data,indent=2)+"\n")
    for k,row in data.items():
        print(k, row["partialReceivers"], row["meanVisibilityError"], row["maxVisibilityError"])
