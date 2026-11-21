#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_output=${1:?New versioned build/ output required}
if [[ ! "$task_output" =~ ^build/aqualumen-receiver-mesher-probe-0\.1\.0-[a-zA-Z0-9._-]+\.jar$ || -e "$task_output" || -L "$task_output" ]]; then
    printf '%s\n' 'Probe build requires a unique new path; no overwrite'
    exit 1
fi
task_prism=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
task_java="$task_prism/java/java-runtime-delta/bin"
task_loader="$task_prism/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
task_mixin="$task_prism/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
task_iris="$task_prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
task_sodium="$task_prism/instances/Aqualumen Lab/minecraft/mods/sodium-fabric-0.6.9+mc1.21.1.jar"
task_lwjgl="$task_prism/libraries/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar"
task_classes=$(mktemp -d build/receiver-mesher-probe.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -cp "$task_loader:$task_mixin:$task_iris:$task_sodium:$task_lwjgl" -d "$task_classes" \
    physics-mod/dev/aqualumen/physics/ReceiverVertex.java \
    tools/receiver-mesher-probe/dev/aqualumen/physics/ReceiverMesherScope.java \
    tools/receiver-mesher-probe/dev/aqualumen/physics/ReceiverMesherProbe.java \
    tools/receiver-mesher-probe/dev/aqualumen/mesherprobe/mixin/MesherMixin.java \
    tools/receiver-mesher-probe/dev/aqualumen/mesherprobe/mixin/EncoderMixin.java \
    tools/receiver-mesher-probe/dev/aqualumen/mesherprobe/mixin/FrameMixin.java
cp tools/receiver-mesher-probe/fabric.mod.json tools/receiver-mesher-probe/aqualumen-receiver-mesher-probe.mixins.json "$task_classes/"
"$task_java/jar" --create --date=2026-10-01T00:00:00Z --file "$task_output" -C "$task_classes" .
printf '%s\n' 'Built TEST-only actual mesher/encoder observer; runtime not yet qualified'
sha256sum "$task_output"
