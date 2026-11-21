#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-plant-cell-index.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/dev/aqualumen/physics/ReceiverWaterVolume.java physics-mod/dev/aqualumen/physics/ReceiverQuadIntersection.java physics-mod/dev/aqualumen/physics/ReceiverPlantPacket.java physics-mod/dev/aqualumen/physics/ReceiverPlantCellIndex.java physics-mod/dev/aqualumen/physics/ReceiverPlantCellPublication.java physics-mod/test/dev/aqualumen/physics/ReceiverPlantCellIndexTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverPlantCellIndexTest
"$java_bin/javac" -proc:none -cp "$classes" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java physics-mod/dev/aqualumen/physics/ReceiverMaterialPoint.java physics-mod/dev/aqualumen/physics/ReceiverMaterialTriangle.java physics-mod/dev/aqualumen/physics/ReceiverPlantMaterialPacket.java physics-mod/dev/aqualumen/physics/ReceiverRadiancePublisher.java physics-mod/dev/aqualumen/physics/ReceiverPlantPublisher.java physics-mod/test/dev/aqualumen/physics/ReceiverPlantPublisherTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverPlantPublisherTest
