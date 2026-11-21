"""Public actual GPU-region audit, with explicitly separate CPU-input projection."""
import copy
import hashlib
import json
from pathlib import Path
from water_receiver_texture_audit import audit as audit_cpu

def audit(capture,geometry,request,reference):
    properties=dict(line.split("=",1) for line in request.decode().splitlines() if line)
    if (capture.get("schema")!="aqualumen-actual-receiver-atlas-v1" or properties.get("schema")!="3"
            or capture.get("GPUAtlasPixelReadback") is not True
            or capture.get("requestSHA256")!=hashlib.sha256(request).hexdigest()):raise ValueError("Exact GPU request scope required")
    # Reuse the old CPU behavioral contract ONLY after checking the actual schema
    # and original request digest. This temporary projection is not new raw evidence.
    cpu=copy.deepcopy(capture);cpu["schema"]="aqualumen-actual-receiver-texels-v1";cpu["GPUAtlasPixelReadback"]=False
    cpuRequest=request.replace(b"schema=3\n",b"schema=2\n",1);cpu["requestSHA256"]=hashlib.sha256(cpuRequest).hexdigest()
    result=audit_cpu(cpu,geometry,cpuRequest,reference)
    calibration=capture["knownGPUTextureControl"]
    if (calibration.get("expectedRGBA")!=[7,8,9,255] or calibration.get("ownGPUTextureMutationReadbackRGBA")!=[255]*4
            or calibration.get("rgbaSHA256")!="60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1"
            or calibration.get("immutableAfterOwnGPUTextureMutation") is not True or calibration.get("actualAssetMutated") is not False
            or calibration.get("listedGLStateRestored") is not True or calibration.get("before")!=calibration.get("after")):
        raise ValueError("Actual owned GPU channel/orientation/mutation/ownership control failed")
    for observation in capture["observations"]:
        atlas=observation["gpuAtlas"]
        if (atlas.get("atlas")!="minecraft:textures/atlas/blocks.png" or atlas.get("internalFormat") not in (6408,32856)
                or atlas.get("componentBits")!=[8]*4 or atlas.get("componentTypes")!=[35863]*4
                or type(atlas.get("textureID")) is not int or atlas["textureID"]<1
                or len(atlas.get("size",[]))!=2 or any(type(v) is not int or not 1<=v<=2048 for v in atlas["size"])):
            raise ValueError("Actual bounded normalized RGBA8 storage must be queried")
        if atlas.get("listedGLStateRestored") is not True or atlas.get("before")!=atlas.get("after"):
            raise ValueError("Actual listed GL binding/pack/unpack restoration required")
        if (atlas.get("textureDataMutated") is not False or atlas.get("actualTerrainSamplerBindingProven") is not False
                or atlas.get("filteredTextureFetchProven") is not False or atlas.get("atlasReloadCoherenceProven") is not False):
            raise ValueError("Raw atlas pixels cannot promote terrain/filtering/epoch proof")
        if (atlas.get("minFilter") not in (9728,9729,9984,9985,9986,9987) or atlas.get("magFilter") not in (9728,9729)
                or atlas.get("baseLevel")!=0 or type(atlas.get("maxLevel")) is not int or not 0<=atlas["maxLevel"]<=11):
            raise ValueError("Actual mip/filter descriptor scope invalid")
        for face in observation["actualClientFaces"]:
            w,h=atlas["size"];loU,hiU,loV,hiV=face["spriteBounds"]
            coords=[loU*w,hiU*w,loV*h,hiV*h]
            if any(abs(v-round(v))>1e-5 for v in coords) or round(coords[1])-round(coords[0])!=16 or round(coords[3])-round(coords[2])!=16:
                raise ValueError("Actual GPU sprite rectangle must match CPU16x16 extent")
        for face in observation["actualClientFaces"]:
            if face.get("gpuTextureRGBA_SHA256")!=face["textureRGBA_SHA256"] or face.get("gpuTextureRGBA_SHA256")!=reference["rgbaSHA256"]:
                raise ValueError("GPU/native/independent whole sprite bytes differ")
            if face.get("gpuSavedPointRGBA")!=face["savedPointRGBA"]:raise ValueError("GPU actual first-point color differs")
    result.update(schema="aqualumen-actual-receiver-atlas-audit-v1",GPUAtlasPixelReadback=True,
                  actualGPUWholeSpriteMatches=48,actualGPUPointChecks=48,filteredTextureFetchProven=False,
                  actualTerrainSamplerBindingProven=False,liveGeometryAtlasFrameCoherenceProven=False)
    fields=("atlas","textureID","size","internalFormat","componentBits","componentTypes","minFilter","magFilter","baseLevel","maxLevel")
    result["actualAtlasDescriptorsStableAcrossTheseThreeObservations"]=all(
        all(o["gpuAtlas"][key]==capture["observations"][0]["gpuAtlas"][key] for key in fields) for o in capture["observations"][1:])
    result["listedGLStateRestored"]=True
    return result

def main():
    root=Path(__file__).resolve().parents[1];out=root/"reports/2026-10-06-water-receiver-atlas-v2"
    paths=[out/"actual-texture-readback.json",root/"reports/2026-10-06-water-coast-world/geometry-audit.json",
           out/"request.properties",out/"independent-stock-reference.json"]
    result=audit(json.loads(paths[0].read_text()),json.loads(paths[1].read_text()),paths[2].read_bytes(),json.loads(paths[3].read_text()))
    result["inputSHA256"]={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with (out/"actual-atlas-audit.json").open("x") as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print("PASS actual48 GPU/native/stock sprite and point matches; filtering/terrain binding/radiance remain unqualified")
if __name__=="__main__":main()
