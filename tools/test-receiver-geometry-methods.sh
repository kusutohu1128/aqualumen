#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-geometry-methods.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/BathymetryField.java physics-mod/dev/aqualumen/physics/ReceiverChunkLease.java physics-mod/dev/aqualumen/physics/ReceiverWaterVolume.java physics-mod/dev/aqualumen/physics/LoadedWorld.java physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/LoadedReceiverWorld.java physics-mod/test/dev/aqualumen/physics/ReceiverGeometryMethodTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverGeometryMethodTest
