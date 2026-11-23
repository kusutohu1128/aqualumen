"""Shade lamp-lit opaque terrain once, after opaque depth ownership is known."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "build/visible-terrain"
SOURCE = ROOT / "dist/Aqualumen-Hand-Penumbra-Study.zip"
SOURCE_SHA = "3fd9a38e39b8a4be6a48355bf76876e03535866923f6f14277b0f0607e0ecbf8"
STUDY_SHA = "0fd89fc4c8b3d638f6bc270c450d772817564559a4690cae01c10de78bd73a36"
PACK = WORK / "Aqualumen-Visible-Terrain.zip"


def build():
    assert sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    WORK.mkdir(parents=True, exist_ok=True)
    key = "    if(count==0 && poolGroups==0) return vanilla;"
    code = """
#ifdef AQUALUMEN_FORWARD_FIELD
    // A negative solar alpha marks the frontmost terrain sample. The existing
    // deferred pass reads its normal, pigment, wet film and block light.
    // Keep pool lighting on its usual path, including the cached lava faces.
    if(receiveLava && count>0 && poolGroups==0) {
        pendingAreaLight=true;
        return vec3(0);
    }
#endif"""
    with ZipFile(SOURCE) as src, ZipFile(PACK, "w") as dst:
        for entry in src.infolist():
            data = src.read(entry)
            if entry.filename == "shaders/lib/local_lighting.glsl":
                shader = data.decode()
                assert shader.count(key) == 1
                data = shader.replace(key, key + code).encode()
            dst.writestr(entry, data)
    return PACK


if __name__ == "__main__":
    digest = sha256(build().read_bytes()).hexdigest()
    assert digest == STUDY_SHA
    print(digest)
