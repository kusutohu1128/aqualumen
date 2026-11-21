"""Which nearby surfaces can actually return direct sunlight to the birch?"""
import collections
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-21-leaf-light/forest"))
from sitesearch import Scene, SNAP, sun_direction


def observe(scene,point,normal,time,bands,angles):
    sun=sun_direction(time)
    assert sun[1]>0
    total=lit=term=0.
    kinds=collections.Counter()
    for j in range(bands):
        y=-(j+.5)/bands
        radius=math.sqrt(1-y*y)
        for i in range(angles):
            phi=math.tau*(i+.5+(j%2)*.5)/angles
            d=(radius*math.cos(phi),y,radius*math.sin(phi))
            weight=max(0,sum(a*b for a,b in zip(normal,d)))
            if weight<=0: continue
            total+=weight
            hit=scene.trace(point,d,12)
            assert hit["kind"]!="unknown"
            kinds[hit["kind"]]+=weight
            if hit["kind"]=="sky": continue
            n=hit["normal"]
            incidence=sum(a*b for a,b in zip(n,sun))
            if incidence<=0: continue
            start=tuple(p+.002*q for p,q in zip(hit["point"],n))
            beam=scene.trace(start,sun,20)
            assert beam["kind"]!="unknown"
            if beam["kind"]=="sky":
                lit+=weight
                term+=weight*incidence
    return {"lowerHemisphereFractionByFirstHit":{k:round(v/total,5) for k,v in kinds.items()},
            "fractionSeeingSunlitFace":round(lit/total,5),
            "unitDiffuseDirectReturnRelativeToAlwaysSunlitFlatGround":round(term/(total*sun[1]),5)}


if __name__=="__main__":
    scene=Scene((195,347,222,373))
    rows={}
    for t in (6000,9800,11500):
        rows[str(t)]={str(y): observe(scene,(209.5,y,359.999),(0,0,-1),t,32,96)
                      for y in (64.5,65.5,66.5)}
    print(json.dumps({"seed":SNAP["seed"],"sourceDigest":SNAP["sourceDigest"],
          "meaning":"Lower hemisphere only. First-hit + visibility of a collimated Sun for uniform unit-albedo Lambert surfaces. Vanilla sprite holes at exposed leaf entries; plants treated as boxes. No diffuse skylight on hit surfaces, shadows outside the 20 m beam, secondary bounces, tone mapping or exposure. Compare to the existing uniform sunlit-ground fallback on vertical faces; not actual Minecraft HDR values.",
          "times":rows},indent=2))
