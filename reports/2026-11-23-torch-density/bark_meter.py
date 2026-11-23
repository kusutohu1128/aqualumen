"""Add pre-display RGB readout for 64 registered bark points, only in the diagnostic pack."""
import io
import sys
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "2026-11-22-eye-adaptation"))
from meter import instrument, candidate

PACK = ROOT / "build/torch-density/Aqualumen-Bark-Meter.zip"
MATERIAL = ROOT / "build/torch-density/Aqualumen-Bark-Material.zip"
RESPONSE = ROOT / "build/torch-density/Aqualumen-Bark-Response.zip"
READOUT = b"""
    ivec2 cell = ivec2(gl_FragCoord.xy) - ivec2(16, 48);
    if (all(greaterThanEqual(cell, ivec2(0))) && all(lessThan(cell, ivec2(24, 8)))) {
        ivec2 grid = ivec2(cell.x / 3, cell.y);
        ivec2 topLeft = ivec2(700,365) + ivec2((vec2(grid)+0.5)*vec2(210,185)/8.0);
        ivec2 address = ivec2(topLeft.x, textureSize(colortex0,0).y-1-topLeft.y);
        vec3 scene = max(texelFetch(colortex0,address,0).rgb, vec3(0));
        gl_FragColor = vec4(meterBytes(log2(1.+scene[cell.x%3])/8.),1.);
        return;
    }
"""
FULL_PATCH = b"""
    ivec2 patchPixel = ivec2(gl_FragCoord.xy) - ivec2(16, 64);
    if (all(greaterThanEqual(patchPixel, ivec2(0))) && all(lessThan(patchPixel, ivec2(630,185)))) {
        ivec2 topLeft = ivec2(700 + patchPixel.x / 3, 365 + patchPixel.y);
        ivec2 address = ivec2(topLeft.x, textureSize(colortex0,0).y-1-topLeft.y);
        vec3 scene = max(texelFetch(colortex0,address,0).rgb, vec3(0));
        gl_FragColor = vec4(meterBytes(log2(1.+scene[patchPixel.x%3])/8.),1.);
        return;
    }
"""


def diagnostic(full_patch=False, revised_meter=False):
    data = io.BytesIO()
    with ZipFile(io.BytesIO(instrument(candidate))) as original, ZipFile(data, "w") as target:
        for entry in original.infolist():
            body = original.read(entry)
            if revised_meter and entry.filename in ("shaders/composite3.csh","shaders/lib/display_exposure.glsl"):
                body=(HERE/"exposure-study"/entry.filename).read_bytes()
            if entry.filename == "shaders/final.fsh":
                start = b"void main() {"
                assert body.count(start) == 1
                body = body.replace(start, start+READOUT+(FULL_PATCH if full_patch else b""))
            target.writestr(entry, body)
    return data.getvalue()


if __name__ == "__main__":
    for path, dense, revised in ((PACK,False,False), (MATERIAL,True,False), (RESPONSE,True,True)):
        payload = diagnostic(dense,revised)
        if path.exists():
            assert path.read_bytes() == payload
        else:
            path.write_bytes(payload)
