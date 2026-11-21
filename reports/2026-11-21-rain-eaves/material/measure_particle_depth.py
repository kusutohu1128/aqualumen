"""Read aligned records for real precipitation fragments from three encoded panels."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"fixture"))
import fixture as patio
import anvil

def vector_rays(w,h,pose):
    f,r,u=np.array(patio.basis(pose["yaw"],pose["pitch"]))
    xs=np.arange(w)*3+1.5
    ys=np.arange(h)+.5
    dirs=(f+(xs[None,:,None]/1280*2-1)*patio.TAN*patio.ASPECT*r+
          (1-ys[:,None,None]/720*2)*patio.TAN*u)
    return dirs/np.linalg.norm(dirs,axis=2,keepdims=True)

def quant(values,qs=(.1,.5,.9)):
    return [float(x) for x in np.quantile(values,qs)] if len(values) else []

def process(run):
    receipt=json.loads((run/"complete.json").read_text())
    assert receipt["diagnosticShader"] and receipt["sourceUnchanged"] and receipt["pack"]=="Aqualumen-rain-particle-depth.zip"
    pose=json.loads((run/"plan.json").read_text())["poses"].get("particle",patio.POSES["a"])
    # Minecraft centres integer horizontal tp arguments. Use the saved camera of
    # this exact test player rather than silently treating the planned decimal as its position.
    camera_file=run/"saved-particle-camera.json"
    game=Path((run/"private-game.txt").read_text())
    world=game/"saves/AqualumenNaturalV2"
    playerfile=world/"playerdata/00000000-0000-4000-8000-000000000442.dat"
    if playerfile.is_file():
        player=anvil.nbt(gzip.decompress(playerfile.read_bytes()))
        feet=np.array(player["Pos"])
        local_eye=feet+np.array([0,patio.EYE,0])-np.array(patio.ORIGIN)
        saved={"planned":pose,"eye":local_eye.tolist(),"savedFeetWorld":feet.tolist(),"yaw":player["Rotation"][0],
               "pitch":player["Rotation"][1],"playerFileSHA256":hashlib.sha256(playerfile.read_bytes()).hexdigest(),
               "actualTeleport":(world/"datapacks/RainMaterialGauge/data/gauge/function/s0.mcfunction").read_text().splitlines()[0]}
        if camera_file.exists():assert json.loads(camera_file.read_text())==saved
        else:camera_file.write_text(json.dumps(saved,indent=2)+"\n")
    camera=json.loads(camera_file.read_text())
    rays=vector_rays(426,720,camera)
    eye=np.array(camera["eye"])
    nominal=np.array([6.5,4.44,5.5])
    upper_right=(np.arange(720)[:,None]<230)&(np.arange(426)[None,:]>=330)
    summary={}
    for phase in ("clear_lamp","warm_rain","lamp_off","soul_rain","lamp_back"):
        clip=run/(phase+".mkv")
        assert hashlib.sha256(clip.read_bytes()).hexdigest()==receipt["samples"][phase]["sha256"]
        f=subprocess.check_output(["ffmpeg","-v","error","-threads","2","-i",str(clip),"-pix_fmt","rgb24","-threads","1","-f","rawvideo","pipe:1"])
        frames=np.frombuffer(f,np.uint8).reshape(32,720,1280,3)
        entries=[]
        # Every third source-screen x is present. Three panels describe the identical fragment on each frame.
        for frame in frames:
            a,b,c=(frame[:,i*426:(i+1)*426,:] for i in range(3))
            mask=(c[:,:,2]==255)&(c[:,:,1]>0)&(a[:,:,1]<254)
            if not mask.any():continue
            geo=a[mask].astype(np.float32)/255
            rgb=(b[mask].astype(np.float32)/255)**2
            rgb=rgb/np.maximum(1-rgb,.0001)
            d=geo[:,0]*32
            eye_d=geo[:,1]*32
            picked=c[:,:,0][mask].astype(np.float32)*32/255
            pos=eye+rays[mask]*eye_d[:,None]
            expected=np.linalg.norm(pos-nominal,axis=1)
            angle=geo[:,2]*2-1
            luma=rgb@np.array([.2126,.7152,.0722])
            entries.append(np.column_stack([d,eye_d,picked,expected,angle,luma,upper_right[mask]]))
        if not entries:
            summary[phase]={"samples":0}
            continue
        distance,eye_dist,picked,expected,angle,luma,corner=np.concatenate(entries).T
        traced=picked<30;lit=luma>1e-5
        data={"samples":len(luma),"tracedSamples":int(traced.sum()),"directLitSamples":int(lit.sum()),
              "geometricRayErrorMetresP50P95P99":quant(abs(expected-distance),(.5,.95,.99)),
              "tracedSourceVsNominalMetresP50P95P99":quant(abs(picked[traced]-distance[traced]),(.5,.95,.99)),
              "sourceDistanceBands":[]}
        for lo,hi in ((0,3),(3,6),(6,9),(9,12),(12,14),(14,33)):
            band=(distance>=lo)&(distance<hi)
            data["sourceDistanceBands"].append({"metres":[lo,hi],"samples":int(band.sum()),
                "directEnergyP50P90P99":quant(luma[band],(.5,.9,.99)),"litFraction":float(lit[band].mean()) if band.any() else None})
        area=corner.astype(bool)&lit
        if area.any():
            bright=area & (luma>=np.quantile(luma[area],.9))
            data["upperRightBrightestLocalDecile"]={"samples":int(bright.sum()),"distanceToLampMetresP10P50P90":quant(distance[bright]),"distanceToEyeMetresP10P50P90":quant(eye_dist[bright]),"phaseCosineP10P50P90":quant(angle[bright])}
        summary[phase]=data
    checks={"clear_sky_no_particles":summary["clear_lamp"]["samples"]==0,
            "unlit_rain_has_no_direct_lamp":summary["lamp_off"]["samples"]>500 and summary["lamp_off"]["directLitSamples"]==0}
    for k in ("warm_rain","soul_rain","lamp_back"):
        s=summary[k]
        checks[k+"_matches_independent_camera_ray"]=s.get("geometricRayErrorMetresP50P95P99",[1]*3)[2]<.25
        checks[k+"_selected_correct_lamp"]=bool(s.get("tracedSamples",0)>500 and s["tracedSourceVsNominalMetresP50P95P99"][2]<.25)
        checks[k+"_finite_local_range"]=bool(s.get("directLitSamples",0)>500 and s["sourceDistanceBands"][-1]["directEnergyP50P90P99"] and s["sourceDistanceBands"][-1]["directEnergyP50P90P99"][-1]<.001)
    result={"method":"RGB8 capture of 3 readback panels from one post-depth-test weather fragment per coordinate. Lamp distance and eye distance quantised in 32m/255 steps; final clamp excluded on eye depth. Per-frame overdraw keeps only the last blended weather quad; stats do not resolve separate overlapping drops. Screen region x>=991,y<230.","checks":checks,"stages":summary}
    (run/"particle-depth.json").write_text(json.dumps(result,indent=2)+"\n")
    print(checks)
    return all(checks.values())

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    raise SystemExit(not process(parser.parse_args().run))
