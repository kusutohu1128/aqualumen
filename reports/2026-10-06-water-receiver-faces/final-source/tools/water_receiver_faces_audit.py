"""CPU-only audit of the actual pinned vanilla face readback public record.

Does not load Minecraft, infer shaded radiance, or claim simultaneous saved/live
geometry. The former saved first-hit coordinates are only the requested scope.
"""
import hashlib
import json
import math
from pathlib import Path

def audit(capture, geometry, request):
    properties=dict(line.split("=",1) for line in request.decode().splitlines() if line)
    world="b22dbccb-2970-41e6-847f-f183b1ec923d"
    if (capture.get("schema")!="aqualumen-actual-receiver-faces-v1" or capture.get("world_id")!=world
            or properties.get("world_id")!=world or properties.get("schema")!="1"
            or capture.get("seed")!=308060 or capture.get("request_id")!=properties.get("request_id")
            or capture.get("requestSHA256")!=hashlib.sha256(request).hexdigest()):
        raise ValueError("Exact actual face request/world identity mismatch")
    if (capture.get("radianceComputed") is not False or capture.get("sourceUploaded") is not False
            or capture.get("fullGoalAchieved") is not False or capture.get("rawLightNotSmoothed") is not True):
        raise ValueError("Raw unsmoothed face inputs cannot assert renderer/radiance readiness")
    points=geometry["points"]
    faces=capture["actualClientFaces"]
    if len(points)!=16 or len(faces)!=16:raise ValueError("Ordered16 face scope required")
    records=[]
    for face,point in zip(faces,points):
        hit=point["firstIntersection"]
        if properties.get(f"point.{len(records)}")!=",".join(map(str,hit["cell"]+hit["normal"])):
            raise ValueError("Ordered request disagrees with saved first faces")
        if face["cell"]!=hit["cell"] or face["normal"]!=hit["normal"]:
            raise ValueError("Actual requested first-face identity mismatch")
        if face["blockState"]!="Block{minecraft:sand}" or hit["state"]!={"Name":"minecraft:sand"}:
            raise ValueError("Actual saved/client sand subset mismatch")
        if face["atlas"]!="minecraft:textures/atlas/blocks.png" or face["sprite"]!="minecraft:block/sand":
            raise ValueError("Actual sand atlas/sprite identity mismatch")
        for name in ("skyLight","blockLight"):
            if type(face[name]) is not int or not 0<=face[name]<=15:
                raise ValueError("Raw light outside vanilla integer range")
        for name in ("vertexColor","tint"):
            if len(face[name])!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in face[name]):
                raise ValueError("Finite unshaded RGB input required")
        if (type(face["shade"]) is not bool or not math.isfinite(face["vanillaBrightness"])
                or not 0<=face["vanillaBrightness"]<=1):raise ValueError("Finite brightness/shade input required")
        loU,hiU,loV,hiV=face["spriteBounds"]
        origin,alongS,alongT=(face[k] for k in ("uvOrigin","uvS","uvT"))
        values=[loU,hiU,loV,hiV,*origin,*alongS,*alongT]
        if not all(math.isfinite(v) for v in values) or not (0<=loU<hiU<=1 and 0<=loV<hiV<=1):
            raise ValueError("Finite normalized sprite required")
        corners=[]
        for s,t in ((0,0),(1,0),(0,1),(1,1)):
            u=origin[0]+s*alongS[0]+t*alongT[0]
            v=origin[1]+s*alongS[1]+t*alongT[1]
            if not (loU-1e-7<=u<=hiU+1e-7 and loV-1e-7<=v<=hiV+1e-7):
                raise ValueError("Face UV escapes actual sprite")
            corners.append([u,v])
        if abs(alongS[0]*alongT[1]-alongS[1]*alongT[0])<1e-12:
            raise ValueError("Degenerate face UV")
        axis=next(i for i,v in enumerate(face["normal"]) if v)
        local=[p-c for p,c in zip(hit["point"],face["cell"])]
        if not all(-1e-7<=v<=1+1e-7 for v in local):raise ValueError("Saved first point outside requested face")
        if abs(local[axis]-(1 if face["normal"][axis]>0 else 0))>1e-7:
            raise ValueError("Saved point is not on the declared outward face")
        s,t=local[(axis+1)%3],local[(axis+2)%3]
        uv=[origin[i]+s*alongS[i]+t*alongT[i] for i in range(2)]
        camera=point["independentCameraRayToPhysicalFirstPoint"]
        hidden=camera["cell"]!=hit["cell"]
        records.append(dict(cell=face["cell"],normal=face["normal"],cameraHiddenInPriorSavedAudit=hidden,
                            savedPointAtlasUV=uv,corners=corners,skyLight=face["skyLight"],blockLight=face["blockLight"],
                            irisContextBrightness=face["vanillaBrightness"]))
    return dict(schema="aqualumen-actual-face-audit-v1",qualifiedFirstFaces=len(records),
                cameraHiddenFirstFaces=sum(p["cameraHiddenInPriorSavedAudit"] for p in records),
                uniqueCellFaces=len({tuple(f["cell"]+f["normal"]) for f in faces}),
                rawSkyLightRange=[min(f["skyLight"] for f in faces),max(f["skyLight"] for f in faces)],
                actualFaceFrame=capture["frame"],lightingWarmthOrTemporalStabilityProven=False,
                actualTexturePixelReadback=False,actualIrisSamplerBinding=False,
                savedAndLiveGeometrySameFrameProven=False,shaderAppearanceImproved=False,
                records=records,radianceComputed=False,sourceUploaded=False,fullGoalAchieved=False)

def main():
    import sys
    root=Path(__file__).resolve().parents[1]
    out=root/"reports/2026-10-06-water-receiver-faces"
    raw=out/"actual-face-readback.json";geometry=root/"reports/2026-10-06-water-coast-world/geometry-audit.json"
    request=out/"request.properties"
    result=audit(json.loads(raw.read_text()),json.loads(geometry.read_text()),request.read_bytes())
    result["inputSHA256"]={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (raw,geometry,request)}
    with (out/"actual-face-audit.json").open("x") as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(f"PASS {result['qualifiedFirstFaces']} actual faces / {result['uniqueCellFaces']} unique cell-faces; no shaded texture/radiance upload")

if __name__=="__main__":main()
