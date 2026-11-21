#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_output=${1:?Unique build output required}
task_fixture=${2:?Archived material query fixture required}
if [[ ! "$task_output" =~ ^build/aqualumen-receiver-light-probe-0\.1\.0-[a-zA-Z0-9._-]+\.jar$ || -e "$task_output" || -L "$task_output" ]]; then
    printf '%s\n' 'Unique versioned artifact required; no overwrite'; exit 1
fi
task_prism=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
task_java="$task_prism/java/java-runtime-delta/bin"
task_classes=$(mktemp -d build/receiver-light-probe.XXXXXX)
task_cp="$task_prism/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar:$task_prism/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar:$task_prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar:$task_prism/libraries/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar:$task_prism/libraries/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
"$task_java/javac" -proc:none -Xlint:all -cp "$task_cp" -d "$task_classes" \
    physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java \
    physics-mod/dev/aqualumen/physics/ReceiverTriangle.java \
    tools/receiver-light-probe/dev/aqualumen/lightprobe/*.java \
    tools/receiver-light-probe/dev/aqualumen/lightprobe/mixin/*.java
cp tools/receiver-light-probe/fabric.mod.json tools/receiver-light-probe/aqualumen-receiver-light-probe.mixins.json "$task_classes/"
cp "$task_fixture" "$task_classes/material-queries.bin"
"$task_java/jar" --create --date=2026-10-01T00:00:00Z --file "$task_output" -C "$task_classes" .
printf '%s\n' 'Built guarded TEST-only resource/material observer; runtime qualification pending'
sha256sum "$task_output"
