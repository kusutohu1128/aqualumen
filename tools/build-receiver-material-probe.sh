#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_output=${1:-build/aqualumen-receiver-material-probe-0.1.2-atlas-v1.jar}
if [[ ! "$task_output" =~ ^build/aqualumen-receiver-material-probe-0\.1\.2-[a-zA-Z0-9._-]+\.jar$ || -e "$task_output" || -L "$task_output" ]]; then
    printf '%s\n' 'Probe build requires a new versioned build/ path; no overwrite'
    exit 1
fi
task_prism=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
task_java="$task_prism/java/java-runtime-delta/bin"
task_loader="$task_prism/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
task_mixin="$task_prism/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
task_iris="$task_prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
task_lwjgl="$task_prism/libraries/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar"
task_gl="$task_prism/libraries/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
task_classes=$(mktemp -d build/receiver-material-probe.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -cp "$task_loader:$task_mixin:$task_iris:$task_lwjgl:$task_gl" -d "$task_classes" \
    physics-mod/dev/aqualumen/physics/BathymetryField.java \
    physics-mod/dev/aqualumen/physics/LoadedWorld.java \
    physics-mod/dev/aqualumen/physics/ReceiverChunkLease.java \
    physics-mod/dev/aqualumen/physics/ReceiverWaterVolume.java \
    physics-mod/dev/aqualumen/physics/ReceiverField.java \
    physics-mod/dev/aqualumen/physics/ReceiverFace.java \
    physics-mod/dev/aqualumen/physics/ReceiverTexture.java \
    physics-mod/dev/aqualumen/physics/ReceiverAtlas.java \
    physics-mod/dev/aqualumen/physics/LoadedReceiverWorld.java \
    physics-mod/dev/aqualumen/physics/LoadedReceiverTexture.java \
    physics-mod/dev/aqualumen/physics/LoadedReceiverFaces.java \
    tools/receiver-material-probe/dev/aqualumen/physics/ReceiverMaterialProbe.java \
    tools/receiver-material-probe/dev/aqualumen/physics/GpuReceiverAtlas.java \
    tools/receiver-material-probe/dev/aqualumen/materialprobe/mixin/MaterialProbeMixin.java
cp tools/receiver-material-probe/fabric.mod.json tools/receiver-material-probe/aqualumen-receiver-material-probe.mixins.json "$task_classes/"
"$task_java/jar" --create --date=2026-10-01T00:00:00Z --file "$task_output" -C "$task_classes" .
printf '%s\n' 'Built TEST-only face readback; not installed or runtime validated'
sha256sum "$task_output"
