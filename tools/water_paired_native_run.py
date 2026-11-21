#!/usr/bin/env python3
"""Bind an exclusive native paired-water fixture to two actual input archives."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive, destination):
    destination.mkdir()
    seen = set()
    with zipfile.ZipFile(archive) as package:
        for entry in package.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or entry.filename in seen:
                raise ValueError("unsafe or duplicate ZIP entry")
            seen.add(entry.filename)
            if entry.is_dir():
                continue
            if entry.file_size > 8 * 1024 * 1024:
                raise ValueError("oversized ZIP entry")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(package.read(entry))
    root = destination / "shaders"
    if not (root / "gbuffers_water.fsh").is_file():
        raise ValueError("archive does not contain shaders/gbuffers_water.fsh")
    return root


def save(path, text):
    with path.open("x") as stream:
        stream.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control_zip", type=Path)
    parser.add_argument("paired_zip", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--view-zoom", type=float, choices=(1.0,3.0), default=1.0)
    args = parser.parse_args()
    args.control_zip = args.control_zip.resolve(strict=True)
    args.paired_zip = args.paired_zip.resolve(strict=True)
    args.output = args.output.absolute()
    args.output.mkdir(parents=False, exist_ok=False)
    native_source = Path(__file__).with_name("water_paired_native.cpp").resolve(strict=True)
    receipt = {
        "schema": "native-paired-water/1",
        "scope": "native generated VS/FS fixture, not Iris resource binding or natural visual acceptance",
        "control_zip": str(args.control_zip),
        "paired_zip": str(args.paired_zip),
        "control_zip_sha256": sha256(args.control_zip),
        "paired_zip_sha256": sha256(args.paired_zip),
        "native_source_sha256": sha256(native_source),
        "passed": False,
        "view_zoom": args.view_zoom,
    }
    try:
        control_root = extract(args.control_zip, args.output / "control")
        paired_root = extract(args.paired_zip, args.output / "paired")
        binary = args.output / "water-paired-native"
        compiled_source = native_source
        if args.view_zoom != 1:
            original = native_source.read_text()
            anchor = 'const float f=1/std::tan(3.14159265358979323846f/6)'
            if original.count(anchor) != 1:
                raise ValueError('view-zoom fixture anchor differs')
            compiled_source = args.output / 'water-paired-native-zoom.cpp'
            save(compiled_source, original.replace(anchor, 'const float f=3/std::tan(3.14159265358979323846f/6)', 1))
        receipt['compiled_source_sha256'] = sha256(compiled_source)
        build_command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", str(compiled_source), "-o", str(binary), "-lepoxy", "-lEGL"]
        built = subprocess.run(build_command, capture_output=True, text=True, timeout=120)
        receipt["build_command"] = build_command
        receipt["build_exit_code"] = built.returncode
        save(args.output / "build.stdout", built.stdout)
        save(args.output / "build.stderr", built.stderr)
        if built.returncode:
            raise RuntimeError("native fixture build failed")
        receipt["native_binary_sha256"] = sha256(binary)
        native_command = [str(binary), str(control_root), str(paired_root), str(args.output / "captures")]
        environment = dict(os.environ)
        environment["__EGL_VENDOR_LIBRARY_FILENAMES"] = "/usr/share/glvnd/egl_vendor.d/10_nvidia.json"
        receipt["egl_vendor_library_filenames"] = environment["__EGL_VENDOR_LIBRARY_FILENAMES"]
        run = subprocess.run(native_command, capture_output=True, text=True, timeout=180, env=environment)
        receipt["native_command"] = native_command
        receipt["exit_code"] = run.returncode
        save(args.output / "native.stdout", run.stdout)
        save(args.output / "native.stderr", run.stderr)
        renderer = re.search(r"^renderer=(.+)$", run.stdout, re.M)
        version = re.search(r"^version=(.+)$", run.stdout, re.M)
        receipt["renderer"] = renderer.group(1) if renderer else None
        receipt["gl_version"] = version.group(1) if version else None
        if run.returncode:
            raise RuntimeError("native fixture failed")
        cases = []
        for name, route, count, equal in re.findall(r"^([a-z-]+) expected_route=(\d+) expected_count=(\d+) C0_byte_equal=(\d+)$", run.stdout, re.M):
            cases.append({"name": name, "expected_route": int(route), "expected_count": int(count), "c0_byte_equal": equal == "1"})
        receipt["cases"] = cases
        receipt["tested_routes"] = sorted({case["expected_route"] for case in cases})
        receipt["untested_routes"] = sorted(set(range(6)) - set(receipt["tested_routes"]))
        receipt["route_assignment_mutant_rejected"] = "route_assignment_mutant=rejected\n" in run.stdout
        receipt["nonwater_translucent_without_clear_zero"] = "nonwater_translucent_without_C12_clear=zero\n" in run.stdout
        receipt["final_preview0_byte_equal"] = "final_preview0_byte_equal=1\n" in run.stdout
        receipt["final_preview1_sensitive"] = "final_preview1_sensitive=1\n" in run.stdout
        receipt["final_preview1_expected_pattern"] = "final_preview1_expected_pattern=1\n" in run.stdout
        receipt["final_preview_uniform_active_int"] = "final_preview_uniform=active-int\nfinal_preview0_uniform=0\n" in run.stdout
        if receipt["tested_routes"] != [0, 2, 3, 4, 5] or len(cases) != 6:
            raise RuntimeError("native case coverage incomplete")
        if not all(case["c0_byte_equal"] for case in cases):
            raise RuntimeError("C0 passivity failed")
        if not receipt["route_assignment_mutant_rejected"] or not receipt["nonwater_translucent_without_clear_zero"]:
            raise RuntimeError("negative or stale-record check absent")
        if not all(receipt[key] for key in ("final_preview0_byte_equal", "final_preview1_sensitive", "final_preview1_expected_pattern", "final_preview_uniform_active_int")):
            raise RuntimeError("actual final preview invariance or sensitivity evidence absent")
        if not receipt["renderer"] or "NVIDIA" not in receipt["renderer"]:
            raise RuntimeError("NVIDIA renderer evidence absent")
        if receipt["control_zip_sha256"] != sha256(args.control_zip) or receipt["paired_zip_sha256"] != sha256(args.paired_zip):
            raise RuntimeError("input ZIP changed during run")
        if receipt["native_source_sha256"] != sha256(native_source):
            raise RuntimeError("native source changed during run")
        receipt["passed"] = True
    except Exception as error:
        receipt["error"] = str(error)
    receipt["artifacts"] = [
        {"path": str(path.relative_to(args.output)), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(args.output.rglob("*")) if path.is_file()
    ]
    save(args.output / "receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "receipt": str(args.output / "receipt.json"), "error": receipt.get("error")}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
