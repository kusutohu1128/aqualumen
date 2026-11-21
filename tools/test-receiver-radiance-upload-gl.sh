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
classes=$(mktemp -d build/receiver-upload-gl-test.XXXXXX)
"$prism/java/java-runtime-delta/bin/javac" -proc:none -cp "$classpath" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverTextureBinding.java
classpath="$classes:$classpath"
"$prism/java/java-runtime-delta/bin/javac" -proc:none -cp "$classpath" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/dev/aqualumen/physics/ReceiverRadiancePublisher.java physics-mod/dev/aqualumen/physics/ReceiverRadianceTextureUpload.java physics-mod/dev/aqualumen/physics/ReceiverLightingState.java physics-mod/dev/aqualumen/physics/ReceiverRunLayout.java physics-mod/dev/aqualumen/physics/ReceiverRunRadiance.java physics-mod/dev/aqualumen/physics/ReceiverRunPublisher.java physics-mod/test/dev/aqualumen/physics/ReceiverRadianceUploadGLTest.java
DISPLAY=:1 "$prism/java/java-runtime-delta/bin/java" -cp "$classes:$classpath" dev.aqualumen.physics.ReceiverRadianceUploadGLTest
