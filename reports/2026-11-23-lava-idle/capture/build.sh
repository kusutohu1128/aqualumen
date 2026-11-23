#!/usr/bin/env bash
set -eu
src=$(dirname "$0")
root=$(cd "$src/../../.." && pwd)
prism=${AQUALUMEN_PRISM_ROOT:-$HOME/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}
jdk=$prism/java/java-runtime-delta/bin
lib=$prism/libraries
dest=$root/build/lava-idle
iris="$prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
mixin="$lib/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
loader="$lib/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
gl="$lib/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
mkdir -p "$dest"
classes=$(mktemp -d "$dest/capture-classes.XXXXXX")
trap 'rm -rf -- "$classes"' EXIT
"$jdk/javac" -proc:none --release 21 -cp "$iris:$mixin:$loader:$gl:$lib/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar:$root/build/gpu-profiler/frame-sample.jar" -d "$classes" "$src/"*.java
cp "$src/"*.json "$classes/"
"$jdk/jar" --create --date=2026-11-21T00:00:00Z --file "$dest/idle-capture.jar" -C "$classes" .
