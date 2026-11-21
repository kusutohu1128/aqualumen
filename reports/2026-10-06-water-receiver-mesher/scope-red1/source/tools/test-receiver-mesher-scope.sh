#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher/PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
# Use the actual installed Java21 runtime, not a guessed system compiler.
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_classes=$(mktemp -d build/receiver-mesher-scope-test.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -d "$task_classes" \
    physics-mod/dev/aqualumen/physics/ReceiverVertex.java \
    tools/receiver-mesher-probe/dev/aqualumen/physics/ReceiverMesherScope.java \
    tools/receiver-mesher-probe/test/dev/aqualumen/physics/ReceiverMesherScopeTest.java
"$task_java/java" -cp "$task_classes" dev.aqualumen.physics.ReceiverMesherScopeTest
