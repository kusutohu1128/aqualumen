"""Independent saved actual mesh-input/output reader; no live/native GL replay."""
import json
import math
from pathlib import Path
import struct
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / "reports/2026-10-06-water-receiver-mesher"
FACES = {"POS_X": (1, 0, 0), "NEG_X": (-1, 0, 0), "POS_Y": (0, 1, 0),
         "NEG_Y": (0, -1, 0), "POS_Z": (0, 0, 1), "NEG_Z": (0, 0, -1)}


def f32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


def texture_code(center, value):
    bias = 1 if value < center else -1
    q = math.floor(f32(value * 32768) + .5) + bias
    return q & 32767 | (int(bias < 0) << 15)


def audit(out=OUT):
    data = json.loads((out / "actual-mesher-readback.json").read_text())
    install = json.loads((out / "install.json").read_text())
    build = json.loads((out / "build-receipt.json").read_text())
    request = out / "request.properties"
    props = dict(line.split("=", 1) for line in request.read_text().splitlines())
    if (data.get("schema") != "aqualumen-actual-receiver-mesher-v1" or data.get("error")
            or data["world_id"] != "b22dbccb-2970-41e6-847f-f183b1ec923d" or data["seed"] != 308060
            or data["request_id"] != install["requestId"] or data["request_id"] != props["request_id"]
            or data["requestSHA256"] != sha(request) or not data["actualSeparateAo"]):
        raise ValueError("Actual guarded request provenance rejected")
    if (build["exitCode"] != 0 or not build["sourceUnchangedDuringBuild"]
            or sha(out / "actual-build" / build["jar"]) != build["artifactSHA256"]
            or install["probeSHA256"] != build["artifactSHA256"]):
        raise ValueError("Actual built observer artifact not qualified")
    for name, digest in build["sourceSHA256"].items():
        if sha(out / "actual-build/source" / name) != digest:
            raise ValueError("Frozen actual compiled source changed")
    if sha(out / "installation-lifecycle.py") != install["installationLifecycleSHA256"]:
        raise ValueError("Actual installation tooling provenance changed")
    log = (out / "test-mesher-runtime.log").read_text()
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log
            or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "PASS requested actual immutable mesher -> Iris encoder readbacks" not in log
            or "TEST safely stopped" in log or "OpenGL debug message" in log):
        raise ValueError("Actual NVIDIA/Iris observer activation not qualified")
    for flag in ("nativeBufferModified", "worldMutated", "sourceUploaded", "drawMatrixOrFilteredSamplingCaptured",
                 "liveResourceGeometryEpochProven", "shadedSourceRadiance", "fullGoalAchieved"):
        if data[flag] is not False:
            raise ValueError("Declared observation scope changed")
    requested = set()
    for i in range(16):
        p = tuple(int(x) for x in props[f"point.{i}"].split(","))
        if len(p) != 6 or p[3:] not in FACES.values():
            raise ValueError("Requested first-face normal invalid")
        face = next(k for k, v in FACES.items() if v == p[3:])
        requested.add((p[:3], face))
    events = data["actualMesherEncodes"]
    keys = [(tuple(e["cell"]), e["face"]) for e in events]
    if len(keys) != len(set(keys)) or set(keys) != requested or data["requestedUniqueOwners"] != len(requested):
        raise ValueError("Actual unique requested first-face ownership incomplete/ambiguous")
    if len({e["sequence"] for e in events}) != len(events):
        raise ValueError("Encoder invocation identity aliased")
    # Cross-packet static affine input comparison is not a live atlas/resource epoch.
    previous = ROOT / "reports/2026-10-06-water-receiver-atlas-v2/actual-texture-readback.json"
    atlas = json.loads(previous.read_text())
    metadata = {(tuple(e["cell"]), tuple(e["normal"])): e for e in atlas["observations"][0]["actualClientFaces"]}
    aos, skies, blocks, strides, threads = [], [], [], set(), set()
    for event, key in zip(events, keys):
        normal = FACES[event["face"]]
        axis = next(i for i, n in enumerate(normal) if n)
        if (event["blockState"] != "Block{minecraft:sand}" or not event["matchingSynchronousVertexArray"]
                or not event["readOnlyNativeBuffer"] or event["requestId"] != data["request_id"]
                or event["armedRenderFrame"] != data["armedRenderFrame"] or event["elapsedNanoseconds"] <= 0
                or event["threadId"] <= 0 or not event["threadName"].startswith("Chunk Render Task Executor #")):
            raise ValueError("Actual synchronous worker/owner association rejected")
        threads.add((event["threadId"], event["threadName"]))
        stride = event["stride"]
        if stride < 20 or stride > 128 or stride % 4:
            raise ValueError("Native written extent invalid")
        strides.add(stride)
        raw, encoded = event["rawVertices"], event["encodedFirst20ByteWords"]
        if len(raw) != 4 or len(encoded) != 4:
            raise ValueError("Actual quad shape changed")
        center = [0.0, 0.0]
        for v in raw:
            for a in range(2):
                center[a] = f32(center[a] + v["uv"][a])
        center = [f32(x * .25) for x in center]
        local_vertices = []
        prior = metadata[(key[0], normal)]
        for v, words in zip(raw, encoded):
            if len(words) != 5 or any(not isinstance(w, int) or w < 0 or w > 0xffffffff for w in words):
                raise ValueError("Written native word scope invalid")
            xyz, uv, ao, light, color = v["xyz"], v["uv"], v["ao"], v["packedLight"], v["colorABGR"]
            if (len(xyz) != 3 or len(uv) != 2 or not all(math.isfinite(x) for x in xyz + uv + [ao])
                    or not 0 <= ao <= 1 or not all(0 <= x <= 1 for x in uv)
                    or light & 0xff00ff00):
                raise ValueError("Actual input tuple invalid")
            local = [xyz[a] - event["chunkRelativeOffset"][a] for a in range(3)]
            if any(x not in (0, 1) for x in local) or local[axis] != int(normal[axis] > 0):
                raise ValueError("Encoder vertices are not the requested owner's full unit face")
            local_vertices.append(local)
            # Sand has no random model offset: actual owner chunk-relative position.
            if event["chunkRelativeOffset"] != [cell & 15 for cell in event["cell"]]:
                raise ValueError("Mesher owner and actual section offset disagree")
            s, t = local[(axis + 1) % 3], local[(axis + 2) % 3]
            expected_uv = [prior["uvOrigin"][a] + prior["uvS"][a] * s + prior["uvT"][a] * t for a in range(2)]
            if uv != expected_uv:
                raise ValueError("Actual prepared UV differs from the owned static face input")
            q = [int(f32(f32(f32(8 + x) / 32) * 1048576)) & 1048575 for x in xyz]
            hi = sum(((q[a] >> 10) & 1023) << (a * 10) for a in range(3))
            lo = sum((q[a] & 1023) << (a * 10) for a in range(3))
            alpha = int(f32(f32(ao) * 255)) & 255
            expected_color = color & 0xffffff | alpha << 24
            block, sky = max(8, min(248, light & 255)), max(8, min(248, light >> 16 & 255))
            uv_word = texture_code(center[0], uv[0]) | texture_code(center[1], uv[1]) << 16
            light_word = block | sky << 8 | (event["material"] & 255) << 16 | (event["section"] & 255) << 24
            if words != [hi, lo, expected_color, uv_word, light_word]:
                raise ValueError("Independent actual position/UV/color/AO/light encoding mismatch")
            aos.append(ao); skies.append(light >> 16 & 255); blocks.append(light & 255)
        if len(set(tuple(p) for p in local_vertices)) != 4:
            raise ValueError("Actual full-face corner ownership incomplete")
        p0, p1, p2 = local_vertices[:3]
        a, b = [p1[i] - p0[i] for i in range(3)], [p2[i] - p0[i] for i in range(3)]
        cross = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        if tuple(cross) != normal:
            raise ValueError("Actual vertex winding disagrees with first-face normal")
    return dict(schema="aqualumen-independent-mesher-audit-v1", actualOwnedFaces=len(events), actualVertices=len(aos),
        actualWorkerThreads=[dict(id=i, name=n) for i, n in sorted(threads)], actualStrides=sorted(strides),
        aoRange=[min(aos), max(aos)], rawSkyByteRange=[min(skies), max(skies)], rawBlockByteRange=[min(blocks), max(blocks)],
        actualMinecraftMesherEncoderValidated=True, independentNativeWordsMatched=5*len(aos),
        staticAffineFaceInputMatches=len(aos), previousStaticAtlasCaptureSHA256=sha(previous),
        syntheticCpuInputs=False, actualShaderDrawInputs=False, liveEpochProven=False,
        filteredSamplingOrLightmapMatrix=False, shadedSourceRadiance=False, sourceUploaded=False,
        newMinecraftFrameTimings=False, naturalVisualAcceptance=False, fullGoalAchieved=False)


if __name__ == "__main__":
    result = audit()
    with (OUT / "independent-mesher-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
