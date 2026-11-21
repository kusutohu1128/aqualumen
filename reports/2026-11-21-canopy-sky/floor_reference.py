"""Direct sunlight reflected once from a resurfaced patch towards the saved birch."""
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image

from ground_reference import Scene, SNAP, sun_direction
from sitesearch import CLIENT


def texture_albedo(archive, material):
    path = "assets/minecraft/textures/block/" + material + ".png"
    image = Image.open(io.BytesIO(archive.read(path))).convert("RGB")
    encoded = np.asarray(image, dtype=float) / 255
    return np.where(encoded <= .04045, encoded / 12.92, ((encoded + .055) / 1.055) ** 2.4).mean((0, 1))


def patch(x, z):
    return 206 <= x < 213 and 354 <= z < 360


def sun_on_patch(scene, tick, bands, azimuths):
    sun = sun_direction(tick)
    receiver = (209.5, 65.5, 359.999)
    weight_sum = reached = uncovered = covered = 0.
    for j in range(bands):
        drop = (j + .5) / bands
        radial = math.sqrt(1 - drop * drop)
        for i in range(azimuths):
            phi = math.tau * (i + .5 + .5 * (j % 2)) / azimuths
            direction = (radial * math.cos(phi), -drop, radial * math.sin(phi))
            cosine = -direction[2]
            if cosine <= 0:
                continue
            weight_sum += cosine
            hit = scene.trace(receiver, direction, 12)
            assert hit["kind"] != "unknown"
            if hit["kind"] != "ground" or hit["normal"] != (0, 1, 0):
                continue
            x, y, z = hit["point"]
            if not patch(x, z):
                continue
            reached += cosine
            beam = scene.trace((x, y + .002, z), sun, 20)
            assert beam["kind"] != "unknown"
            if beam["kind"] != "sky":
                continue
            uncovered += cosine
            roof_distance = (67 - y) / sun[1]
            if roof_distance <= 0 or not patch(x + sun[0]*roof_distance, z + sun[2]*roof_distance):
                covered += cosine
    return {
        "patchViewFraction": reached / weight_sum,
        "sunlitWeight": uncovered / weight_sum,
        "sunlitWeightWithRoof": covered / weight_sum,
    }


if __name__ == "__main__":
    scene = Scene((195, 347, 222, 373))
    with zipfile.ZipFile(CLIENT) as archive:
        colors = {k: texture_albedo(archive, k) for k in ("white_concrete", "red_concrete")}
    result = {}
    for tick in (6000, 9800, 11500):
        fine = sun_on_patch(scene, tick, 64, 128)
        coarse = sun_on_patch(scene, tick, 32, 64)
        assert 0 <= fine["sunlitWeightWithRoof"] <= fine["sunlitWeight"] <= fine["patchViewFraction"] <= 1
        result[tick] = {
            "fine": fine, "coarse": coarse,
            "whiteToRedDeltaOpen": ((colors["red_concrete"]-colors["white_concrete"])*fine["sunlitWeight"]).tolist(),
            "whiteToRedDeltaRoof": ((colors["red_concrete"]-colors["white_concrete"])*fine["sunlitWeightWithRoof"]).tolist(),
        }
    assert result[6000]["fine"]["sunlitWeight"] > .05 and result[6000]["fine"]["sunlitWeightWithRoof"] < .01
    print(json.dumps({
        "seed": SNAP["seed"], "snapshotDigest": SNAP["sourceDigest"], "receiver": [209.5, 65.5, 359.999],
        "region": "Upward-facing existing grass or dirt within [206,213) x [354,360) in x,z. Roof control places an opaque rectangle over the same footprint at y=67.",
        "scope": "Hypothetical resurfacing only, no world edits. Exact same visible terrain for the two colours. Extra roof blocks the solar beam to the patch. Its own reflection is excluded. Values are changes in the lower hemisphere direct-sun term relative to a fully visible unit-albedo sunlit horizontal surface, not display RGB. Plants are approximate opaque cubes, water has no diffuse return here.",
        "textureMeansLinearRGB": {k: v.tolist() for k,v in colors.items()},
        "times": result,
    }, indent=2))
