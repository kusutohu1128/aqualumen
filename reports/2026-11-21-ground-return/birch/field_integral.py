"""Independently integrate the color change on the raised floor into the birch.
Reads real game quarter-face radiance. Only the top faces of changed floor
tiles differ between the two inputs. Use area integration, not the shader's
angular samples. World coordinates and north-face quarter order are explicit.
"""
import argparse
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
FLOOR=json.loads((HERE/"placements.json").read_text())["floor"]
CENTRES=np.array([[209.25,65.25,359.998],[209.75,65.25,359.998],
                  [209.25,65.75,359.998],[209.75,65.75,359.998]])

def field(folder,scene):
    return json.loads((folder/(scene+".json")).read_text())["opaque_fixture"]["ground_field"]

def differences(white,red):
    patches={}
    for x,y,z in FLOOR:
        key=f"{x},{y},{z}"
        assert white[key]["captured"] and red[key]["captured"]
        # Upward-face basis is (z,x). First texture coordinate is fastest.
        patches[x,z]=(np.array(white[key]["quarterRGBA"])[:,:3]-
                      np.array(red[key]["quarterRGBA"])[:,:3]).reshape(2,2,3)
    return patches

def quadrature(patches,n):
    # Subdivide each square directly. cos(receiver)*cos(floor)/r^2 is the
    # differential projected solid angle, independent of camera orientation.
    k=(np.arange(n)+.5)/n
    u,v=np.meshgrid(k,k,indexing="ij")
    wx=np.clip(2*u-.5,0,1)[...,None];wz=np.clip(2*v-.5,0,1)[...,None]
    result=np.zeros((4,3))
    for (x,z),tex in patches.items():
        radiance=(1-wx)*((1-wz)*tex[0,0]+wz*tex[0,1])+wx*((1-wz)*tex[1,0]+wz*tex[1,1])
        for i,(px,py,pz) in enumerate(CENTRES):
            dz=pz-(z+v);dy=py-65
            rr=(x+u-px)**2+dy*dy+dz**2
            weight=dy*dz/(np.pi*rr**2)
            result[i]+=np.mean(weight[...,None]*radiance,axis=(0,1))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args()
    rows={}
    for name,white,red in (("open","ground-noon","ground-evening"),("roof","air-shadow-backlit","ground-low-sun")):
        a=field(args.folder,white);b=field(args.folder,red)
        patches=differences(a,b)
        exact=quadrature(patches,64);coarse=quadrature(patches,32)
        measured=np.array(a["209,65,360"]["quarterRGBA"])[:,:3]-np.array(b["209,65,360"]["quarterRGBA"])[:,:3]
        rows[name]={"gameIncidentWhiteMinusRed":measured.tolist(),"floorOnlyIntegral":exact.tolist(),
                    "maxRefinement":float(np.max(abs(exact-coarse))),
                    "meanGame":measured.mean(0).tolist(),"meanIntegral":exact.mean(0).tolist()}
    output={"scope":"Signed linear game-field deltas. Independent integral of the 30 real floor top faces using captured outgoing radiance, with unobstructed return over the raised floor. Other solids, side faces and frame-to-frame weather differences are outside that integral.","rows":rows}
    args.output.write_text(json.dumps(output,indent=2)+"\n")
    for name,r in rows.items():print(name,"measured",r["meanGame"],"integral",r["meanIntegral"])
if __name__=="__main__":main()
