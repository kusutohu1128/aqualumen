#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_classes=$(mktemp -d build/receiver-face-test-classes.XXXXXX)
"$task_java/javac" -proc:none -d "$task_classes" physics-mod/dev/aqualumen/physics/ReceiverFace.java physics-mod/test/dev/aqualumen/physics/ReceiverFaceTest.java
"$task_java/java" -cp "$task_classes" dev.aqualumen.physics.ReceiverFaceTest
