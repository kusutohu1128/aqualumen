"""Build an exclusive land-shadow preview from the pinned ordinary pack."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Mapping, Sequence
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


BASE_SHA256 = "6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73"
BASE_NAMES = frozenset(
    """LICENSE
shaders/begin.csh
shaders/begin1.csh
shaders/block.properties
shaders/composite.fsh
shaders/composite.vsh
shaders/deferred.fsh
shaders/deferred.vsh
shaders/final.fsh
shaders/final.vsh
shaders/gbuffers_basic.fsh
shaders/gbuffers_basic.vsh
shaders/gbuffers_skybasic.fsh
shaders/gbuffers_skybasic.vsh
shaders/gbuffers_terrain.fsh
shaders/gbuffers_terrain.vsh
shaders/gbuffers_textured.fsh
shaders/gbuffers_textured.vsh
shaders/gbuffers_textured_lit.fsh
shaders/gbuffers_textured_lit.vsh
shaders/gbuffers_water.fsh
shaders/gbuffers_water.vsh
shaders/lang/en_US.lang
shaders/lang/ja_JP.lang
shaders/lib/aerial.glsl
shaders/lib/atmosphere.glsl
shaders/lib/caustics.glsl
shaders/lib/clouds.glsl
shaders/lib/fullscreen.vsh.glsl
shaders/lib/illumination.glsl
shaders/lib/lighting.glsl
shaders/lib/ripple_solver.glsl
shaders/lib/ripples.glsl
shaders/lib/settings.glsl
shaders/lib/shadows.glsl
shaders/lib/terrain.fsh.glsl
shaders/lib/terrain.vsh.glsl
shaders/lib/uniforms.glsl
shaders/lib/water.glsl
shaders/lib/waves.glsl
shaders/prepare.fsh
shaders/prepare.vsh
shaders/setup.csh
shaders/shaders.properties
shaders/shadow.fsh
shaders/shadow.vsh""".splitlines()
)
WRAPPERS = frozenset(
    ("shaders/gbuffers_terrain.fsh", "shaders/gbuffers_textured_lit.fsh")
)
LIBRARY_NAMES = ("shaders/lib/land_lighting.glsl", "shaders/lib/land_shadows.glsl")
LIGHTING_INCLUDE = b'#include "/lib/lighting.glsl"\n'
LAND_LIGHTING_INCLUDE = b'#include "/lib/land_lighting.glsl"\n'
INCLUDE = re.compile(rb'^[ \t]*#include[ \t]+"([^"\r\n]+)"[ \t]*(?:\r?\n|$)', re.M)
RESERVED_LIBRARY = re.compile(
    r"\b(?:uniform|buffer|atomic_uint|[iu]?sampler\w*|[iu]?image\w*)\b"
    r"|^\s*#\s*(?:version|extension)\b",
    re.M,
)
SHADOW_CONSTANTS = frozenset((
    "shadowMapResolution", "shadowDistance", "shadowIntervalSize",
    "shadowHardwareFiltering", "shadowtex0Mipmap",
))
SHADOW_DIRECTIVE = re.compile(
    r"^\s*#\s*(?:define|undef)\s+(\w+)", re.M
)
GLSL_TYPE = r"(?:float|double|int|uint|bool|[dibu]?vec[234]|d?mat[234](?:x[234])?)"
DECLARATION = re.compile(r"\b" + GLSL_TYPE + r"\s+([^;{}]+);")
DECLARATION_HEAD = re.compile(r"\b" + GLSL_TYPE + r"\s+(\w+)")


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    payload: bytes


@dataclass(frozen=True)
class BasePack:
    entries: tuple[ArchiveEntry, ...]
    sha256: str


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def entry_map(
    entries: tuple[ArchiveEntry, ...], expected_names: frozenset[str]
) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for entry in entries:
        path = PurePosixPath(entry.name)
        if (
            not entry.name
            or "\\" in entry.name
            or "\0" in entry.name
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != entry.name
        ):
            raise ValueError(f"unsafe archive entry {entry.name!r}")
        if entry.name in result:
            raise ValueError(f"duplicate archive entry {entry.name!r}")
        result[entry.name] = entry.payload
    if result.keys() != expected_names:
        missing = sorted(expected_names - result.keys())
        extra = sorted(result.keys() - expected_names)
        raise ValueError(f"archive names differ, missing={missing!r}, extra={extra!r}")
    return result


def parse_archive(payload: bytes) -> tuple[ArchiveEntry, ...]:
    with ZipFile(io.BytesIO(payload)) as archive:
        entries = tuple(ArchiveEntry(info.filename, archive.read(info)) for info in archive.infolist())
    original = entry_map(entries, BASE_NAMES)
    for name in WRAPPERS:
        if original[name].count(LIGHTING_INCLUDE) != 1:
            raise ValueError(f"expected exactly one lighting include in {name}")
    return entries


def load_base(path: Path) -> BasePack:
    payload = path.read_bytes()
    digest = sha256(payload)
    if digest != BASE_SHA256:
        raise ValueError(f"base SHA-256 differs, expected {BASE_SHA256}, found {digest}")
    return BasePack(parse_archive(payload), digest)


def load_libraries(directory: Path) -> Mapping[str, bytes]:
    sources = {}
    for name in LIBRARY_NAMES:
        payload = (directory / PurePosixPath(name).name).read_bytes()
        text = payload.decode("utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
        if reserved_library(code):
            raise ValueError(f"reserved resource or global directive in {name}")
        sources[name] = payload
    return MappingProxyType(sources)


def reserved_library(code: str) -> bool:
    if RESERVED_LIBRARY.search(code):
        return True
    if any(match.group(1) in SHADOW_CONSTANTS for match in SHADOW_DIRECTIVE.finditer(code)):
        return True
    if any(match.group(1) in SHADOW_CONSTANTS for match in DECLARATION_HEAD.finditer(code)):
        return True
    for declaration in DECLARATION.finditer(code):
        depth = 0
        begin = 0
        body = declaration.group(1)
        for index, char in enumerate(body + ","):
            if char in "([":
                depth += 1
            elif char in ")]":
                depth -= 1
            elif char == "," and depth == 0:
                name = re.match(r"\s*(\w+)", body[begin:index])
                if name and name.group(1) in SHADOW_CONSTANTS:
                    return True
                begin = index + 1
    return False


def expanded_shader(entries: Mapping[str, bytes], name: str) -> bytes:
    def expand(current: str, parents: tuple[str, ...]) -> bytes:
        if current in parents:
            raise ValueError(f"cyclic shader include at {current}")

        def include(match: re.Match[bytes]) -> bytes:
            target = match.group(1).decode("utf-8")
            if target.startswith("/"):
                target = "shaders" + target
            else:
                target = (PurePosixPath(current).parent / target).as_posix()
            if target not in entries:
                raise ValueError(f"missing shader include {target}")
            return expand(target, (*parents, current))

        return INCLUDE.sub(include, entries[current])

    return expand(name, ())


def audit_preservation(
    base: BasePack,
    preview: tuple[ArchiveEntry, ...],
    libraries: Mapping[str, bytes],
) -> dict[str, object]:
    original = {entry.name: entry.payload for entry in base.entries}
    output = entry_map(preview, BASE_NAMES | frozenset(LIBRARY_NAMES))
    changed = []
    for name, payload in original.items():
        expected = payload
        if name in WRAPPERS:
            if payload.count(LIGHTING_INCLUDE) != 1:
                raise ValueError(f"expected exactly one lighting include in {name}")
            expected = payload.replace(LIGHTING_INCLUDE, LAND_LIGHTING_INCLUDE)
            changed.append(name)
        if output[name] != expected:
            raise ValueError(f"original payload preservation failed for {name}")
    for name in LIBRARY_NAMES:
        if output[name] != libraries[name]:
            raise ValueError(f"added library differs from its source for {name}")
    nonopaque = sorted(
        name
        for name in original
        if PurePosixPath(name).parent == PurePosixPath("shaders")
        and PurePosixPath(name).suffix in (".fsh", ".vsh", ".csh")
        and name not in WRAPPERS
    )
    for name in nonopaque:
        if expanded_shader(original, name) != expanded_shader(output, name):
            raise ValueError(f"nonopaque expansion changed for {name}")
    return {
        "changed": sorted(changed),
        "added": sorted(LIBRARY_NAMES),
        "preserved_original_entries": len(original) - len(changed),
        "preserved_nonopaque_expansions": nonopaque,
    }


def preview_entries(base: BasePack, libraries: Mapping[str, bytes]) -> tuple[ArchiveEntry, ...]:
    entries = tuple(
        ArchiveEntry(
            entry.name,
            entry.payload.replace(LIGHTING_INCLUDE, LAND_LIGHTING_INCLUDE)
            if entry.name in WRAPPERS
            else entry.payload,
        )
        for entry in base.entries
    ) + tuple(ArchiveEntry(name, libraries[name]) for name in LIBRARY_NAMES)
    return tuple(sorted(entries, key=lambda entry: entry.name))


def zip_bytes(entries: tuple[ArchiveEntry, ...]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            info = ZipInfo(entry.name, (2026, 10, 23, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entry.payload, compress_type=ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def sidecar_path(output: Path) -> Path:
    return output.with_name(output.name + ".manifest.json")


def write_exclusive(output: Path, payload: bytes, manifest: bytes) -> None:
    sidecar = sidecar_path(output)
    for path in (output, sidecar):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"refusing existing output {path}")
    with sidecar.open("xb") as manifest_file:
        archive_created = False
        try:
            with output.open("xb") as archive_file:
                archive_created = True
                archive_file.write(payload)
                manifest_file.write(manifest)
        except BaseException:
            if archive_created:
                output.unlink()
            sidecar.unlink()
            raise


def build_pack(base_path: Path, output: Path, library_dir: Path) -> dict[str, object]:
    base = load_base(base_path)
    libraries = load_libraries(library_dir)
    entries = preview_entries(base, libraries)
    audit = audit_preservation(base, entries, libraries)
    payload = zip_bytes(entries)
    manifest = {
        "format": "aqualumen-land-shadow-preview-v1",
        "base_sha256": base.sha256,
        "source_sha256": {name: sha256(libraries[name]) for name in LIBRARY_NAMES},
        "output_sha256": sha256(payload),
        **audit,
        "output_entry_sha256": {entry.name: sha256(entry.payload) for entry in entries},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    write_exclusive(output, payload, manifest_bytes)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--library-dir", type=Path, default=Path(__file__).resolve().parents[1] / "shaders" / "lib"
    )
    arguments = parser.parse_args(argv)
    try:
        manifest = build_pack(arguments.base, arguments.output, arguments.library_dir)
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps({"output": str(arguments.output), "manifest": str(sidecar_path(arguments.output)), "sha256": manifest["output_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
