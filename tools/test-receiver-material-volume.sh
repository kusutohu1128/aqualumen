#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-material-volume-test.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverFace.java physics-mod/dev/aqualumen/physics/ReceiverTexture.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/dev/aqualumen/physics/ReceiverMaterialVolume.java physics-mod/test/dev/aqualumen/physics/ReceiverMaterialVolumeTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverMaterialVolumeTest
