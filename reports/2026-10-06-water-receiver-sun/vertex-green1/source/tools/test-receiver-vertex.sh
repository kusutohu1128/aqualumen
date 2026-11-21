#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_sodium='/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft/mods/sodium-fabric-0.6.9+mc1.21.1.jar'
task_classes=$(mktemp -d build/receiver-vertex-test-classes.XXXXXX)
"$task_java/javac" -proc:none -cp "$task_sodium" -d "$task_classes" physics-mod/dev/aqualumen/physics/ReceiverVertex.java physics-mod/test/dev/aqualumen/physics/ReceiverVertexTest.java
"$task_java/java" -cp "$task_classes:$task_sodium" dev.aqualumen.physics.ReceiverVertexTest
