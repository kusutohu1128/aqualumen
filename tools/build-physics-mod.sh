#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-$HOME/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
iris="$prism_root/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
sodium="$prism_root/instances/Aqualumen Lab/minecraft/mods/sodium-fabric-0.6.9+mc1.21.1.jar"
joml="$prism_root/libraries/org/joml/joml/1.10.5/joml-1.10.5.jar"
lwjgl="$prism_root/libraries/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar"
opengl="$prism_root/libraries/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
output="${1:-dist/aqualumen-physics-0.3.0.jar}"
if [[ $# -gt 1 || ! "$output" =~ ^(build|dist)/aqualumen-physics-[A-Za-z0-9._-]+\.jar$ ]]; then
    printf '%s\n' 'Output must be a physics JAR directly under build/ or dist/' >&2
    exit 1
fi
if [[ -e "$output" || -L "$output" ]]; then
    printf 'Refusing to overwrite existing %s\n' "$output" >&2
    exit 1
fi
mkdir -p build
task_classes=$(mktemp -d build/physics-classes.XXXXXX)
mapfile -t task_sources < <(rg --files physics-mod/dev -g '*.java' | sort)
"$java_bin/javac" -proc:none -cp "$loader:$mixin:$iris:$sodium:$joml:$lwjgl:$opengl" -d "$task_classes" "${task_sources[@]}"
cp physics-mod/fabric.mod.json physics-mod/aqualumen-physics.mixins.json "$task_classes/"
cp shaders/lib/water_plant_intersection.glsl "$task_classes/dev/aqualumen/physics/"
cp LICENSE "$task_classes/"
mkdir -p dist
"$java_bin/jar" --create --date=2026-10-01T00:00:00Z --file "$output" -C "$task_classes" .
printf 'Built %s (not installed; existing artifacts untouched)\n' "$output"
