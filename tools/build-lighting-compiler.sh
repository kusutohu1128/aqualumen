#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-$HOME/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
lib="$prism_root/libraries"
mixin="$lib/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
gl="$lib/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
output="${1:-dist/aqualumen-lighting-compiler-0.3.0.jar}"
mkdir -p build
work=$(mktemp -d build/lighting-compiler.XXXXXX)
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/classes"
"$java_bin/javac" --release 21 -proc:none -cp "$mixin:$gl" -d "$work/classes" compiler-mod/dev/aqualumen/compiler/*.java compiler-mod/dev/aqualumen/compiler/mixin/*.java
cp compiler-mod/*.json LICENSE "$work/classes/"
"$java_bin/jar" --create --date=2026-11-21T00:00:00Z --file "$work/pack.jar" -C "$work/classes" .
if [[ -f "$output" ]]; then
    cmp "$work/pack.jar" "$output"
else
    ln "$work/pack.jar" "$output"
fi
sha256sum "$output"
