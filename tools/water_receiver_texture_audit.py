"""Public CPU-only audit of actual warmed native texels and independent PNG samples."""
import hashlib
import json
import math
from pathlib import Path

def audit(capture,geometry,request,reference):
    properties=dict(line.split("=",1) for line in request.decode().splitlines() if line)
    world="b22dbccb-2970-41e6-847f-f183b1ec923d"
    if (capture.get("schema")!="aqualumen-actual-receiver-texels-v1" or capture.get("world_id")!=world
            or properties.get("schema")!="2" or properties.get("world_id")!=world or capture.get("seed")!=308060
            or capture.get("request_id")!=properties.get("request_id") or capture.get("requestSHA256")!=hashlib.sha256(request).hexdigest()):
        raise ValueError("Exact warmed request/world scope mismatch")
    if (capture.get("actualNativeImagePixelReadback") is not True or capture.get("GPUAtlasPixelReadback") is not False
            or capture.get("atlasReloadCoherenceProven") is not False or capture.get("sourceUploaded") is not False
            or capture.get("radianceComputed") is not False or capture.get("fullGoalAchieved") is not False
            or capture.get("rawLightNotSmoothed") is not True):raise ValueError("CPU static input scope cannot promote radiance/GPU readiness")
    calibration=capture["knownNativeImageControl"]
    if (any(calibration[k]!=[7,8,9,255] for k in ("expectedRGBA","sampleRGBA","nativeByteRGBA"))
            or calibration["rgbaSHA256"]!="60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1"
            or calibration["actualAssetMutated"] is not False or calibration["immutableAfterOwnNativeImageMutation"] is not True):
        raise ValueError("Actual known NativeImage channel/ownership control failed")
    observations=capture["observations"]
    if len(observations)!=3 or any(len(o["actualClientFaces"])!=16 for o in observations):
        raise ValueError("Exact3x16 observations required")
    times=[o["elapsedNanoseconds"] for o in observations];frames=[o["frame"] for o in observations]
    if (times[0]<5_000_000_000 or frames[0]-capture["firstWorldFrame"]<120
            or any(b-a<1_000_000_000 for a,b in zip(times,times[1:]))
            or any(b<=a for a,b in zip(frames,frames[1:]))):raise ValueError("Actual warmup/ordered separated observations required")
    oracle={(p[0],p[1]):p[2:] for p in reference["samples"]}
    checks=0
    for observation in observations:
        for i,(face,point) in enumerate(zip(observation["actualClientFaces"],geometry["points"])):
            hit=point["firstIntersection"]
            if face["cell"]!=hit["cell"] or face["normal"]!=hit["normal"]:raise ValueError("Saved requested first-face mismatch")
            if properties.get(f"point.{i}")!=",".join(map(str,hit["cell"]+hit["normal"])):raise ValueError("Requested cell/face order mismatch")
            if face["blockState"]!="Block{minecraft:sand}" or face["atlas"]!="minecraft:textures/atlas/blocks.png" or face["sprite"]!="minecraft:block/sand":
                raise ValueError("Actual sand material descriptor mismatch")
            if face["mipLevel"]!=0 or face["staticOpaqueTexture"] is not True:raise ValueError("Only actual static opaque mip0 is qualified")
            for name in ("skyLight","blockLight"):
                if type(face[name]) is not int or not 0<=face[name]<=15:raise ValueError("Raw adjacent light outside vanilla range")
            for name in ("vertexColor","tint"):
                if len(face[name])!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in face[name]):raise ValueError("Finite unshaded color/tint required")
            if not math.isfinite(face["vanillaBrightness"]) or not 0<=face["vanillaBrightness"]<=1:raise ValueError("Actual brightness invalid")
            if face["textureRGBA_SHA256"]!=reference["rgbaSHA256"] or face["textureSize"]!=[16,16]:
                raise ValueError("Actual native sprite pixels differ from independent stock decoder")
            samples=[dict(pixel=face["savedPointPixel"],rgba=face["savedPointRGBA"],localST=face["savedPointLocalST"]),*face["grid"]]
            if len(samples)!=5:raise ValueError("Saved-point plus four-grid pixel scope incomplete")
            axis=next(a for a,n in enumerate(hit["normal"]) if n)
            savedST=[hit["point"][a]-hit["cell"][a] for a in ((axis+1)%3,(axis+2)%3)]
            requestedST=list(map(float,properties[f"local.{i}"].split(",")))
            if requestedST!=savedST or face["savedPointLocalST"]!=requestedST:raise ValueError("Actual local point differs from requested saved point")
            expectedST=[savedST,[.25,.25],[.25,.75],[.75,.25],[.75,.75]]
            loU,hiU,loV,hiV=face["spriteBounds"]
            if not (0<=loU<hiU<=1 and 0<=loV<hiV<=1):raise ValueError("Sprite extent invalid")
            for sample,st in zip(samples,expectedST):
                if sample["localST"]!=st or not all(math.isfinite(v) and 0<=v<=1 for v in st):raise ValueError("Sample grid/local point scope invalid")
                uv=[face["uvOrigin"][a]+st[0]*face["uvS"][a]+st[1]*face["uvT"][a] for a in range(2)]
                if not all(math.isfinite(v) for v in uv) or not (loU<=uv[0]<=hiU and loV<=uv[1]<=hiV):raise ValueError("Actual face UV outside sprite")
                expectedPixel=[min(15,math.floor((uv[0]-loU)/(hiU-loU)*16)),min(15,math.floor((uv[1]-loV)/(hiV-loV)*16))]
                if sample["pixel"]!=expectedPixel:raise ValueError("Correct-looking color at the wrong actual UV cannot qualify")
                if oracle.get(tuple(sample["pixel"]))!=sample["rgba"]:raise ValueError("Actual sparse texel differs from stock PNG reference")
                checks+=1
    faces=observations[0]["actualClientFaces"]
    stable=all(o["actualClientFaces"]==faces for o in observations[1:])
    return dict(schema="aqualumen-actual-receiver-texture-audit-v1",qualifiedFaceObservations=48,
                qualifiedSparsePixelChecks=checks,actualNativeImageReadback=True,GPUAtlasPixelReadback=False,
                qualifiedTextureRGBA_SHA256=reference["rgbaSHA256"],independentDecoder=reference["decoder"],
                observationFrames=frames,observationElapsedNanoseconds=times,
                actualFaceTexelRawLightStableAcrossTheseThreeObservations=stable,
                uniqueCellFaces=len({tuple(f["cell"]+f["normal"]) for f in faces}),
                cameraHiddenRequestedFirstFaces=sum(p["firstIntersection"]["cell"]!=p["independentCameraRayToPhysicalFirstPoint"]["cell"] for p in geometry["points"]),
                rawSkyLightRange=[min(f["skyLight"] for f in faces),max(f["skyLight"] for f in faces)],
                AOOrSmoothedIrradianceComputed=False,atlasReloadCoherenceProven=False,sourceSnapshotSchedulerImplemented=False,
                productionVisualFixImplemented=False,sceneMotionAcceptance=False,frameTimingMeasured=False,
                sourceUploaded=False,radianceComputed=False,fullGoalAchieved=False)

def main():
    root=Path(__file__).resolve().parents[1];out=root/"reports/2026-10-06-water-receiver-texture"
    raw=out/"actual-texture-readback.json";geometry=root/"reports/2026-10-06-water-coast-world/geometry-audit.json"
    request=out/"request.properties";reference=out/"independent-stock-reference.json"
    result=audit(json.loads(raw.read_text()),json.loads(geometry.read_text()),request.read_bytes(),json.loads(reference.read_text()))
    result["inputSHA256"]={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (raw,geometry,request,reference)}
    with (out/"actual-texture-audit.json").open("x") as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(f"PASS48 actual face/texture observations,240 point/grid pixel checks; three-record stability={result['actualFaceTexelRawLightStableAcrossTheseThreeObservations']}; no radiance or GPU source binding")

if __name__=="__main__":main()
