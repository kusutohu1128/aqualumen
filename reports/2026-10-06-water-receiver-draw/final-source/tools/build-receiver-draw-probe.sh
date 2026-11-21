#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_output=${1:?Unique new build/ artifact required}
task_fixture=${2:?Exact generated archived vertex fixture required}
if [[ ! "$task_output" =~ ^build/aqualumen-receiver-draw-probe-0\.1\.0-[a-zA-Z0-9._-]+\.jar$ || -e "$task_output" || -L "$task_output" ]]; then
    printf '%s\n' 'Unique new versioned output required; no overwrite'
    exit 1
fi
task_prism=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
task_java="$task_prism/java/java-runtime-delta/bin"
task_loader="$task_prism/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
task_mixin="$task_prism/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
task_iris="$task_prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
task_lwjgl="$task_prism/libraries/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar"
task_gl="$task_prism/libraries/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
task_classes=$(mktemp -d build/receiver-draw-probe.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -cp "$task_loader:$task_mixin:$task_iris:$task_lwjgl:$task_gl" -d "$task_classes" \
    tools/receiver-draw-probe/dev/aqualumen/drawprobe/GpuVertexDecode.java \
    tools/receiver-draw-probe/dev/aqualumen/drawprobe/ReceiverDrawProbe.java \
    tools/receiver-draw-probe/dev/aqualumen/drawprobe/mixin/DrawMixin.java \
    tools/receiver-draw-probe/dev/aqualumen/drawprobe/mixin/FrameMixin.java
cp tools/receiver-draw-probe/fabric.mod.json tools/receiver-draw-probe/aqualumen-receiver-draw-probe.mixins.json "$task_classes/"
cp "$task_fixture" "$task_classes/receiver-vertices.words"
"$task_java/jar" --create --date=2026-10-01T00:00:00Z --file "$task_output" -C "$task_classes" .
printf '%s\n' 'Built TEST-only actual terrain-draw/owned GPU vertex decoder; not runtime qualified'
sha256sum "$task_output"
