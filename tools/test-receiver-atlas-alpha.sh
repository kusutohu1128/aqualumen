#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
classpath=""
for module in lwjgl lwjgl-opengl lwjgl-glfw; do
    for artifact in "$module" "$module-natives-linux"; do
        jar="$prism/libraries/org/lwjgl/$artifact/3.3.3/$artifact-3.3.3.jar"
        test -f "$jar"
        classpath="${classpath:+$classpath:}$jar"
    done
done
classes=$(mktemp -d build/receiver-atlas-alpha-test.XXXXXX)
"$prism/java/java-runtime-delta/bin/javac" -proc:none -cp "$classpath" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverAtlasAlpha.java physics-mod/dev/aqualumen/physics/ReceiverAtlasReadback.java physics-mod/test/dev/aqualumen/physics/ReceiverAtlasAlphaTest.java physics-mod/test/dev/aqualumen/physics/ReceiverAtlasReadbackGLTest.java
"$prism/java/java-runtime-delta/bin/java" -cp "$classes:$classpath" dev.aqualumen.physics.ReceiverAtlasAlphaTest
DISPLAY=:1 "$prism/java/java-runtime-delta/bin/java" -cp "$classes:$classpath" dev.aqualumen.physics.ReceiverAtlasReadbackGLTest
