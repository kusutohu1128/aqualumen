"""Read-only pinned bytecode/source boundary record, not a live draw observation."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-sun/vertex-boundary"
GAME = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    iris = GAME / "mods/iris-fabric-1.8.8+mc1.21.1.jar"
    sodium = GAME / "mods/sodium-fabric-0.6.9+mc1.21.1.jar"
    classes = [
        (sodium, "net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderer"),
        (sodium, "net.caffeinemc.mods.sodium.client.render.chunk.vertex.format.ChunkVertexEncoder$Vertex"),
        (sodium, "net.caffeinemc.mods.sodium.api.util.ColorABGR"),
        (sodium, "net.caffeinemc.mods.sodium.api.util.ColorU8"),
        (iris, "net.irisshaders.iris.vertices.sodium.terrain.XHFPTerrainVertex"),
        (iris, "net.irisshaders.iris.pipeline.transform.transformer.SodiumTransformer"),
    ]
    output = {}
    for jar, name in classes:
        result = subprocess.run(["rtk", "proxy", "javap", "-p", "-c", "-v", "-classpath", str(jar), name],
                                cwd=ROOT, capture_output=True, text=True)
        with (OUT / (name.rsplit(".", 1)[-1] + ".javap.txt")).open("x") as stream:
            stream.write(result.stdout + result.stderr)
        if result.returncode != 0:
            raise ValueError("Pinned bytecode inspection failed")
        output[name.rsplit(".", 1)[-1]] = result.stdout
    required = {
        "BlockRenderer": ("ColorARGB.toABGR", "Vertex.ao:F", "Vertex.light:I", "ChunkMeshBufferBuilder.push"),
        "XHFPTerrainVertex": ("shouldUseSeparateAo", "ColorABGR.withAlpha", "ColorARGB.mulRGB", "iris_LightmapTextureMatrix"),
        "SodiumTransformer": ("gl_Color", "_vert_color", "a_LightAndData", "iris_LightmapTextureMatrix"),
    }
    # The lightmap matrix belongs to the transformer, not the binary encoder.
    required["XHFPTerrainVertex"] = required["XHFPTerrainVertex"][:-1]
    for name, markers in required.items():
        if any(marker not in output[name] for marker in markers):
            raise ValueError("Pinned input handoff differs from inspected convention")
    with zipfile.ZipFile(GAME / "shaderpacks/Aqualumen-0.6.0.zip") as archive:
        properties = archive.read("shaders/shaders.properties")
    with (OUT / "ordinary-pack-shaders.properties").open("xb") as stream:
        stream.write(properties)
    if b"separateAo=true" not in properties:
        raise ValueError("Ordinary pack does not opt into the inspected separate-AO convention")
    result = dict(schema="aqualumen-pinned-vertex-boundary-v1", irisJarSHA256=sha(iris), sodiumJarSHA256=sha(sodium),
        actualInstalledBytecodeInspected=True, actualMinecraftMesherEventCaptured=False,
        actualIrisShaderDrawInputCaptured=False, ordinaryPackSeparateAo=True,
        geometryCoordinatesAndUVStillPreEncoder=True, matrixUniformAndFilteredUVNotQualified=True,
        mesherArrayLifetimeMustBeCopied=True, colorAlreadyIncludesSodiumTint=True,
        separateAoUsesEightBitAlpha=True, lightByteRange=[8, 248], liveEpochOrSourceProducer=False,
        fullGoalAchieved=False)
    with (OUT / "boundary.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print("Pinned block-mesher -> Iris color/AO/light boundary recorded; not a live capture or shaded source")


if __name__ == "__main__":
    main()
