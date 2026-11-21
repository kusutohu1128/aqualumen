"""Audit bounded FINAL TES-output readback; not stage/geometry/visual proof.

CPU-only. The pack supplies the source chain and native attachment qualification
separately. These observations cannot accept C0/depth neutrality, same-frame PNGs,
all world primitives, an attached terrain program query or shipping quality.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile


STATE_KEYS = {"active", "binding", "packBuffer", "alignment", "rowLength",
              "imageHeight", "skipPixels", "skipRows", "skipImages", "swap", "lsb"}
NAMES = ("colortex9", "colortex10", "colortex11", "colortex12")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def qualify_readback(raw, pack_name, pack_sha256, width=1600, height=900):
    for key in ("available", "stateRestored", "scopeAuthorized"):
        require(raw.get(key) is True, key + " must be true")
    expected = dict(worldId="b22dbccb-2970-41e6-847f-f183b1ec923d",
        world="AqualumenNaturalV2", seed=308060, dimension="minecraft:overworld",
        packName=pack_name, packSha256=pack_sha256, observerVersion="0.3.9",
        width=width, height=height)
    require(all(raw.get(k) == v for k,v in expected.items()), "identity/scope mismatch")
    require("NVIDIA" in raw.get("renderer", ""), "actual NVIDIA renderer required")
    require(type(raw.get("program")) is int and raw["program"] > 0 and
            raw["program"] == raw.get("expectedProgram"), "FINAL program mismatch")
    require(set(raw.get("stateBefore", {})) == STATE_KEYS and
            raw["stateBefore"] == raw.get("stateAfter"), "GL state not exactly restored")
    active = [s for s in raw.get("samplers", []) if s.get("active") is True]
    require(len(active) == 4 and {s.get("name") for s in active} == set(NAMES),
            "exactly C9-C12 must be active")
    by_name = {s["name"]:s for s in active}
    require(len({s.get("unit") for s in active}) == 4 and
            len({s.get("textureId") for s in active}) == 4, "aliased bindings")
    coordinates = None
    for sampler in active:
        require(sampler.get("type") == 35678 and sampler.get("size") == 1 and
                type(sampler.get("location")) is int and sampler["location"] >= 0 and
                type(sampler.get("unit")) is int and sampler["unit"] >= 0 and
                type(sampler.get("textureId")) is int and sampler["textureId"] > 0 and
                sampler.get("textureExists") is True and sampler.get("actualFormat") == 34836 and
                sampler.get("width") == width and sampler.get("height") == height,
                "actual typed RGBA32F binding required")
        points = sampler.get("samples", [])
        require(len(points) == 16, "exactly 16 selected points required")
        current = []
        for p in points:
            require(type(p.get("x")) is int and type(p.get("y")) is int and
                    0 <= p["x"] < width and 0 <= p["y"] < height, "invalid texel coordinate")
            values = p.get("rgba", [])
            require(len(values) == 4 and all(type(v) in (int,float) and math.isfinite(v)
                    for v in values), "nonfinite/invalid RGBA")
            current.append((p["x"],p["y"]))
        require(len(set(current)) == 16, "duplicate points")
        require(coordinates is None or coordinates == current, "role coordinate mismatch")
        coordinates = current
        metadata = [m for m in raw.get("samplerMetadata", []) if
                    m.get("unit") == sampler["unit"] and m.get("textureId") == sampler["textureId"]]
        require(len(metadata) == 1 and metadata[0].get("wholeTargetReadbackBytes") == width*height*16
                and metadata[0].get("exportedTexelCount") == 16, "readback bound mismatch")
    qualified = 0
    barycentrics = set()
    maximum_error = 0.0
    for index in range(16):
        normal, state, reflection, stage = (by_name[name]["samples"][index]["rgba"] for name in NAMES)
        require(state[2] in (0,1), "invalid water mask")
        if state[2] == 0:
            require(all(v == 0 for v in stage), "nonwater stage output not zero")
            continue
        require(state[1] in (0,1) and state[3] == 1 and normal[3] in (0,1), "invalid water flags")
        # TES constant-one is a smooth varying: the rasterizer can round its
        # interpolated value. This finite eight-binary32-epsilon allowance is
        # a declared selected-point guard, not an all-driver error bound.
        require(abs(stage[3]-1) <= 8*2**-23 and all(-2e-5 <= v <= 1+2e-5 for v in stage[:3]),
                "missing TES-origin flag/invalid barycentrics")
        error = abs(sum(stage[:3])-1)
        require(error <= 2e-5, "TES barycentric sum differs from one")
        maximum_error = max(maximum_error,error)
        require(0 <= state[0] <= 1 and reflection[1] in (0,1) and
                reflection[2] == 1-reflection[1] and reflection[3] == 1, "invalid optical fields")
        if state[1] == 1 and normal[3] == 1:
            require(abs(sum(v*v for v in normal[:3])-1) <= 2e-4, "known normal not unit")
            qualified += 1
            barycentrics.add(tuple(round(v,4) for v in stage[:3]))
    require(qualified >= 4 and len(barycentrics) >= 2, "vacuous/constant TES-output observation")
    return dict(scope="bounded selected FINAL texels and TES-origin source chain; not terrain attachment query",
        qualifiedUnderwaterKnownStagePoints=qualified, distinctBarycentricTriples=len(barycentrics),
        maximumBarycentricSumError=maximum_error, actualFourRoleBindingsQualified=True,
        geometryNeutralityAccepted=False, stageAttachmentQueryObserved=False,
        pngSameFrameAccepted=False, visualQualityAccepted=False, shippingAccepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    with ZipFile(args.pack) as archive:
        metadata = json.loads(archive.read("WATER-TESSELLATION-PROBE.json"))
        require(metadata.get("schema") == "aqualumen-water-tessellation-probe-v1" and
                metadata.get("level") == 1 and metadata.get("shipping_fix") is False,
                "expected level-one diagnostic pack")
    result = qualify_readback(json.loads(args.raw.read_text()), args.pack.name,
                             hashlib.sha256(args.pack.read_bytes()).hexdigest())
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
