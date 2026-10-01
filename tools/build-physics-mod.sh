#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
prism_root=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
iris="$prism_root/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
joml="$prism_root/libraries/org/joml/joml/1.10.5/joml-1.10.5.jar"
task_classes=$(mktemp -d build/physics-classes.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin:$iris:$joml" -d "$task_classes" physics-mod/dev/aqualumen/physics/Contacts.java physics-mod/dev/aqualumen/physics/mixin/UniformMixin.java
cp physics-mod/fabric.mod.json physics-mod/aqualumen-physics.mixins.json "$task_classes/"
cp LICENSE "$task_classes/"
mkdir -p dist
"$java_bin/jar" --create --date=2026-10-01T00:00:00Z --file dist/aqualumen-physics-0.2.0.jar -C "$task_classes" .
printf '%s\n' 'Built dist/aqualumen-physics-0.2.0.jar'
