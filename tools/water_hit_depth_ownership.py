#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import shutil
import zipfile

import water_optical_probe as probe


BASE = "reports/2026-10-22-water-hit-depth"
MANIFEST_PINS = {
    "baseline": "47834dbb73da2395292f64e39a88d21e88a578f72614775247330d6573db168e",
    "candidate": "212760541e860cea61f966ec8e9fa1612c3f89603813ebd7c644e3fba5eb241f",
}
VERSIONS = {"baseline": "0.1.0-hit1d3", "candidate": "0.1.0-depth3"}
OLD_VERSIONS = {"baseline": "0.1.0-hit1d2", "candidate": "0.1.0-depth2"}
PROBE_HELPER_SHA256 = "c5a57b0098ba71df31998f1fcc4cd452e25fdbb5ba2b2aa18b0bb491c6043547"
MARKER_PROTOCOL = "last-known-nonwater-diagnostic-writer-v1"
PATCHED_FILES = ("shaders/gbuffers_textured.fsh", "shaders/lib/terrain.fsh.glsl")
PATCHED_BINDINGS = {
    "gbuffers_textured": "shaders/gbuffers_textured.fsh",
    "gbuffers_terrain": "shaders/lib/terrain.fsh.glsl",
    "gbuffers_textured_lit": "shaders/lib/terrain.fsh.glsl",
}
PROGRAM_IDS = tuple("gbuffers_" + suffix for suffix in (
    "basic", "line", "textured", "textured_lit", "skybasic", "skytextured", "clouds", "terrain",
    "terrain_solid", "terrain_cutout", "damagedblock", "block", "block_translucent", "beaconbeam",
    "item", "entities", "entities_translucent", "lightning", "particles", "particles_translucent",
    "entities_glowing", "armor_glint", "spidereyes", "hand", "weather", "water", "hand_water",
))
BLEND_KEYS = tuple(f"blend.{program}.colortex{target}" for program in PROGRAM_IDS for target in (12, 3))
MARKER_WRITES = "    gl_FragData[2]=vec4(0.0);\n    gl_FragData[3]=vec4(0.0,0.0,0.0,-3.0);\n"
OLD_ATTRIBUTION = "Discard leaves earlier contributors; nonwater translucent draws can mix C0 while clearing surviving C12"
NEW_ATTRIBUTION = "Discard preserves earlier diagnostic records; only patched known nonwater paths replace C12/C3 with the exact marker; unmarked paths can mix C0 without replacing them"


def safe_name(name: str) -> bool:
    return bool(name) and not name.startswith("/") and ".." not in Path(name).parts and "\\" not in name


def pinned_inputs(root: Path, mode: str) -> tuple[dict, dict[str, bytes], dict[str, dict[str, bytes]], dict[str, bytes]]:
    if mode not in VERSIONS:
        raise ValueError("unknown ownership mode")
    probe.read_pinned(root / "tools/water_optical_probe.py", PROBE_HELPER_SHA256)
    if probe.sha(Path(probe.__file__).read_bytes()) != PROBE_HELPER_SHA256:
        raise ValueError("imported probe helper differs")
    base = root / BASE / (mode + "2")
    manifest = json.loads(probe.read_pinned(base / "manifest.json", MANIFEST_PINS[mode]))
    if manifest["mode"] != mode or manifest["observerVersion"] != OLD_VERSIONS[mode]:
        raise ValueError("input generation identity differs")
    if set(manifest["archives"]) != {"control", "paired"}:
        raise ValueError("input archive labels differ")
    raw, packs = {}, {}
    for label, pin in manifest["archives"].items():
        raw[label] = probe.read_pinned(base / (label + ".zip"), pin)
        with zipfile.ZipFile(io.BytesIO(raw[label])) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(not safe_name(name) for name in names):
                raise ValueError("duplicate or unsafe archive member")
            packs[label] = {name: archive.read(name) for name in names}
        if {name: probe.sha(data) for name, data in packs[label].items()} != manifest["generatedPackSourceSha256"][label]:
            raise ValueError("input archive source pins differ")
    sources = {}
    for name, pin in manifest["generatedSourceSha256"].items():
        if not safe_name(name):
            raise ValueError("unsafe observer source member")
        sources[name] = probe.read_pinned(base / "observer-sources" / name, pin)
    actual_sources = {str(path.relative_to(base / "observer-sources")) for path in (base / "observer-sources").rglob("*") if path.is_file()}
    if actual_sources != set(sources):
        raise ValueError("observer source set differs")
    return manifest, raw, packs, sources


def properties(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            raise ValueError("property without equals")
        key, value = key.strip(), value.strip()
        if key in result:
            raise ValueError(f"duplicate property key: {key}")
        result[key] = value
    return result


def marker_metadata(entries: dict[str, bytes]) -> dict:
    bindings = {"gbuffers_textured": PATCHED_FILES[0]}
    for name, data in entries.items():
        if re.fullmatch(r"shaders/gbuffers_[a-z_]+\.fsh", name) and b'#include "/lib/terrain.fsh.glsl"' in data:
            bindings[Path(name).stem] = PATCHED_FILES[1]
    if bindings != PATCHED_BINDINGS:
        raise ValueError("terrain source program bindings differ")
    direct = {Path(name).stem for name in entries if re.fullmatch(r"shaders/gbuffers_[a-z_]+\.fsh", name)}
    return {
        "markerProtocol": MARKER_PROTOCOL,
        "lastKnownNonwaterMarker": -3,
        "markerChannels": {"colortex12": [0.0, 0.0, 0.0, 0.0], "colortex3": [0.0, 0.0, 0.0, -3.0]},
        "patchedSourceFiles": list(PATCHED_FILES),
        "patchedSourcePrograms": list(bindings),
        "patchedSourceProgramBindings": bindings,
        "blendConfiguredProgramIds": list(PROGRAM_IDS),
        "fallbackBlendProgramIds": [program for program in PROGRAM_IDS if program not in direct],
        "fallbackProgramResolutionDirectlyObserved": False,
        "fallbackProgramResolution": {},
        "diagnosticBlendKeys": list(BLEND_KEYS),
        "explicitUnmarkedPaths": [
            "gbuffers_basic source emits no last-known-nonwater marker",
            "gbuffers_skybasic source emits no last-known-nonwater marker",
            "gbuffers_line fallback source resolution was not directly observed",
            "gbuffers_water nonwater branch retains its existing C12/C3 zero record, not the -3 marker",
        ],
        "writerMarkerNotDepthOrBeautyOwnership": True,
        "physicalProducerWritesAdded": False,
    }


def mark_nonwater(entries: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    metadata = marker_metadata(entries)
    result = dict(entries)
    for name in PATCHED_FILES:
        text = result[name].decode()
        text = probe.replace_one(text, "/* DRAWBUFFERS:05 */", "/* RENDERTARGETS:0,5,12,3 */")
        match = re.search(r"^    gl_FragData\[0\]=", text, re.MULTILINE)
        if match is None or text.count("gl_FragData[0]=") != 1:
            raise ValueError("nonwater C0 write anchor differs")
        if text.rfind("discard;", 0, match.start()) < 0:
            raise ValueError("nonwater discard anchor absent")
        result[name] = (text[:match.start()] + MARKER_WRITES + text[match.start():]).encode()
    name = "shaders/shaders.properties"
    text = result[name].decode()
    parsed = properties(text)
    for key in BLEND_KEYS:
        if key in parsed and parsed[key] != "off":
            raise ValueError(f"diagnostic blend must be off: {key}")
    additions = [key + "=off" for key in BLEND_KEYS if key not in parsed]
    result[name] = (text + "\n" + "\n".join(additions) + "\n").encode()
    return result, metadata


def java_value(value) -> str:
    if isinstance(value, dict):
        return "Map.of(" + ",".join(json.dumps(key) + "," + java_value(item) for key, item in value.items()) + ")"
    if isinstance(value, list):
        return "List.of(" + ",".join(java_value(item) for item in value) + ")"
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def observer_sources(sources: dict[str, bytes], mode: str, metadata: dict) -> dict[str, bytes]:
    result = dict(sources)
    name = "dev/aqualumen/paired/PairedObserver.java"
    text = probe.replace_one(result[name].decode(), '"observerVersion","' + OLD_VERSIONS[mode] + '"', '"observerVersion","' + VERSIONS[mode] + '"')
    anchor = '        m.put("routeNames",List.of('
    additions = "".join(f"        m.put({json.dumps(key)},{java_value(value)});\n" for key, value in metadata.items())
    text = probe.replace_one(text, anchor, additions + anchor)
    text = probe.replace_one(text, 'Map.of("ineligibleOrUnsolved",-1,"projectionRejected",-2)', 'Map.of("ineligibleOrUnsolved",-1,"projectionRejected",-2,"lastKnownNonwater",-3)')
    text = probe.replace_one(text, OLD_ATTRIBUTION, NEW_ATTRIBUTION)
    result[name] = text.encode()
    name = "fabric.mod.json"
    result[name] = probe.replace_one(result[name].decode(), '"version":"' + OLD_VERSIONS[mode] + '"', '"version":"' + VERSIONS[mode] + '"').encode()
    return result


def generate(root: Path, out: Path, mode: str, build: bool = False) -> dict:
    source_manifest, raw, packs, sources = pinned_inputs(root, mode)
    paired, metadata = mark_nonwater(packs["paired"])
    generated = observer_sources(sources, mode, metadata)
    changed = sorted(name for name, data in paired.items() if data != packs["paired"][name])
    if changed != sorted((*PATCHED_FILES, "shaders/shaders.properties")) or set(paired) != set(packs["paired"]):
        raise ValueError("unexpected pack changes")
    out.mkdir(parents=True, exist_ok=False)
    source_dir = out / "observer-sources"
    for name, data in generated.items():
        path = source_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
    with (out / "control.zip").open("xb") as output:
        shutil.copyfileobj(io.BytesIO(raw["control"]), output)
    probe.write_zip(out / "paired.zip", paired)
    control_exact = (out / "control.zip").read_bytes() == raw["control"]
    if not control_exact:
        raise ValueError("control archive copy differs")
    receipt = {
        "schema": "aqualumen-water-hit-depth-ownership-build-v1", "testOnly": True,
        "mode": mode, "observerVersion": VERSIONS[mode],
        "inputManifest": {"path": f"{BASE}/{mode}2/manifest.json", "sha256": MANIFEST_PINS[mode]},
        "inputArchiveSHA256": source_manifest["archives"],
        "sourcePins": source_manifest["generatedSourceSha256"],
        "inputPackSourceSha256": source_manifest["generatedPackSourceSha256"],
        "probeHelperSHA256": PROBE_HELPER_SHA256, "generatorSHA256": probe.sha(Path(__file__).read_bytes()),
        "generatedSourceSha256": {name: probe.sha(data) for name, data in generated.items()},
        "generatedPackSourceSha256": {"control": source_manifest["generatedPackSourceSha256"]["control"], "paired": {name: probe.sha(data) for name, data in paired.items()}},
        "archives": {label: probe.sha((out / (label + ".zip")).read_bytes()) for label in ("control", "paired")},
        "controlArchiveBytesExact": control_exact, "waterVertexCompositeBytesExact": True,
        "changedPairedEntries": changed, "unchangedPairedEntries": sorted(set(paired) - set(changed)),
        "outputOrder": source_manifest["outputOrder"], "compositeOutputOrder": source_manifest["compositeOutputOrder"],
        "opticalChannels": source_manifest["opticalChannels"], "depthChannels": source_manifest["depthChannels"],
        **metadata,
        "observerBuild": probe.build_observer(root, out, source_dir, f"aqualumen-paired-water-probe-{VERSIONS[mode]}.jar") if build else None,
        "productionSourceModified": False, "gpuVerified": False, "physicalAccepted": False, "visualAccepted": False,
        "limitations": [*source_manifest["limitations"],
            "Only the three patched direct source programs emit the exact last-known-nonwater diagnostic marker. All pinned fallback IDs have blend off configured, but fallback source resolution was not directly observed.",
            "A marker is not hardware-depth or full-beauty ownership. Depth-mask-false overlays can mark without changing depth. Unmarked paths remain attribution gaps.",
            "No historical particle-coordinate or depth-distance exclusion is authorized by this protocol. Every remaining water-classified mismatch retains its original declared budget.",
        ],
    }
    with (out / "manifest.json").open("x") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exclusive TEST copies with known nonwater diagnostic writer markers.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=VERSIONS, required=True)
    parser.add_argument("--build-observer", action="store_true")
    args = parser.parse_args()
    result = generate(args.root, args.out, args.mode, args.build_observer)
    print(json.dumps({"mode": args.mode, "out": str(args.out), "archives": result["archives"], "observerBuild": result["observerBuild"]}, indent=2))
    return 0 if result["observerBuild"] is None else result["observerBuild"]["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
