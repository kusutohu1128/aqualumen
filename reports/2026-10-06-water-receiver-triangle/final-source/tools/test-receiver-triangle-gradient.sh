#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_classes=$(mktemp -d build/receiver-triangle-gradient.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -d "$task_classes" physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java physics-mod/dev/aqualumen/physics/ReceiverTriangle.java physics-mod/test/dev/aqualumen/physics/ReceiverTriangleGradientTest.java
"$task_java/java" -cp "$task_classes" dev.aqualumen.physics.ReceiverTriangleGradientTest
