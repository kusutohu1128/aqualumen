#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_classes=$(mktemp -d build/physics-test-classes.XXXXXX)
"$task_java/javac" -proc:none -d "$task_classes" physics-mod/dev/aqualumen/physics/BathymetryField.java physics-mod/test/dev/aqualumen/physics/BathymetryFieldTest.java
"$task_java/java" -cp "$task_classes" dev.aqualumen.physics.BathymetryFieldTest
