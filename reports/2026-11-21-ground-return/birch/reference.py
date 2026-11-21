"""Cosine integral toward the actual thirty raised floor blocks in the test."""
import json
import math
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]/"2026-11-21-leaf-light/forest"))
from sitesearch import Scene, SOLID, sun_direction

cells=json.loads((here/"placements.json").read_text())
floor={tuple(c) for c in cells["floor"]}
roof={tuple(c) for c in cells["roof"]}
s=Scene((203,350,216,362))
origin=(209.5,65.5,359.998)
sun=sun_direction(6000)
rows={}
for label,region in (("open",floor),("roof",floor|roof)):
    s.extra={p:SOLID for p in region}
    result=[]
    for bands,angles in ((32,64),(64,128)):
        sunlit=seen=0
        for j in range(bands):
            y=-(j+.5)/bands
            radial=math.sqrt(1-y*y)
            for i in range(angles):
                phi=math.tau*(i+.5+.5*(j%2))/angles
                ray=radial*math.cos(phi),y,radial*math.sin(phi)
                if ray[2]>=0: continue
                hit=s.trace(origin,ray,12)
                if hit["cell"] not in floor or hit["normal"]!=(0,1,0): continue
                w=-ray[2]*2/(bands*angles)
                seen+=w
                p=hit["point"]
                if s.trace((p[0],p[1]+.002,p[2]),sun,20)["kind"]=="sky": sunlit+=w
        result.append({"directions":bands*angles,"floorWeight":seen,"directlySunlitWeight":sunlit})
    rows[label]=result
print(json.dumps({"origin":origin,"sun":sun,"rows":rows,
    "scope":"Actual raised floor and roof coordinates in the saved forest. Upward floor faces only, opaque natural obstacles and sprite-masked leaves at entry. Coefficients relative to the reflected radiance of a unit-pigment lit floor, independent of exposure, weather or game shader."},indent=2))
