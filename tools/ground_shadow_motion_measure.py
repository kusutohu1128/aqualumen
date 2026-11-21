"""Measure the first stone step's moving shadow using each captured frame's light direction."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from ground_shadow_measure import header


def measure(directory, output, camera_sweep=False):
    rows = list(csv.DictReader((directory/"ticks.csv").open()))
    raw = np.memmap(directory/"bottom-up.rgba", dtype="u1", mode="r")
    frames = raw.reshape(-1,480,1024,4)
    if len(frames) != len(rows) or len(rows) < 200:
        raise ValueError("Incomplete 10-second strip capture")
    offsets = np.linspace(-.18,.18,361)
    oz,ox = np.meshgrid(np.linspace(341.25,341.75,31), offsets,indexing="ij")
    series = []
    cameras, light_space = [], []
    for row,frame in zip(rows,frames):
        invp,invv,camera,sun,light,shadow_view,_ = header(frame[::-1,:,:3])
        cameras.append(camera)
        light_space.append((shadow_view @ [*(np.array([134,63,341])-camera),1])[:3])
        x_true = 133-light[0]/light[1]
        world = np.stack((x_true+ox, np.full_like(ox,63.0001),oz),axis=-1)
        p = np.concatenate((world-camera, np.ones((*ox.shape,1))),axis=-1)
        clip = p @ np.linalg.inv(invv).T @ np.linalg.inv(invp).T
        uv=clip[:,:,:2]/clip[:,:,3:]*.5+.5
        x=(uv[:,:,0]*2560).astype(int)-780
        y=(uv[:,:,1]*1440).astype(int)-490
        if x.min()<0 or y.min()<0 or x.max()>=1024 or y.max()>=480:
            raise ValueError("Stone edge outside the native crop")
        rgb=frame[y,x,:3]
        if not np.all(rgb[:,:,0]==255) or np.max(np.abs(rgb[:,:,2]/255-sun[1]))>.012:
            raise ValueError("Moving edge left metric-path ground")
        v=rgb[:,:,1]/255
        crossings = (v[:,:-1]<.5)&(v[:,1:]>=.5)
        if not np.all(crossings.sum(axis=1)==1) or np.any(v[:,0]>.1) or np.any(v[:,-1]<.9):
            raise ValueError("Missing unambiguous shadow crossing in preselected scanlines")
        j=crossings.argmax(axis=1); i=np.arange(len(j))
        error=offsets[j]+.001*(.5-v[i,j])/(v[i,j+1]-v[i,j])
        series.append((int(row["frame"]),int(row["world_tick"]),int(row["elapsed_ns"]),x_true,
                       float(np.median(error)),float(np.percentile(abs(error),90))))
    a=np.asarray(series)
    if not (np.all(np.diff(a[:,0])==1) and np.all(np.diff(a[:,2])>0)):
        raise ValueError("Frame order mismatch")
    camera_x=np.array(cameras)[:,0]
    shifts=np.linalg.norm(np.diff(light_space,axis=0),axis=1)
    if camera_sweep:
        if np.ptp(a[:,1]) or np.ptp(a[:,3])>.0001 or np.ptp(camera_x)<.75:
            raise ValueError("Fixed Sun and camera sweep not observed")
    elif a[-1,1]-a[0,1]<=150 or a[-1,3]-a[0,3]<=.05 or np.ptp(camera_x)>.001:
        raise ValueError("Insufficient camera-locked solar motion")
    with (output/"moving-edge.csv").open("x") as f:
        writer=csv.writer(f);writer.writerow(("frame","world_tick","elapsed_ns","expected_x_m","median_error_m","p90_abs_error_m"));writer.writerows(series)
    d=np.abs(np.diff(a[:,4]))
    result=dict(frames=len(rows),durationSeconds=(a[-1,2]-a[0,2])*1e-9,worldTickRange=a[[0,-1],1].tolist(),
                expectedTravelMetres=a[-1,3]-a[0,3],medianErrorMetres=float(np.median(a[:,4])),
                p95ErrorMetres=float(np.percentile(np.abs(a[:,4]),95)),maxFrameGapMs=float(np.diff(a[:,2]).max()*1e-6),
                p95UnexpectedStepMetres=float(np.percentile(d,95)),maxUnexpectedStepMetres=d.max())
    if camera_sweep:
        snap=np.flatnonzero(shifts>.5)
        result.update(cameraXRange=camera_x[[0,-1]].tolist(),shadowOriginMaxShiftMetres=float(shifts.max()),
                      snapFrames=(snap+1).tolist(),edgeJumpsAtSnapMetres=d[snap].tolist())
    with (output/"moving-edge.json").open("x") as f:
        json.dump(result,f,indent=2)
    print(result)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("run",type=Path)
    p.add_argument("--camera",action="store_true")
    args=p.parse_args()
    measure(args.run/"capture/ground-clip",args.run,args.camera)
