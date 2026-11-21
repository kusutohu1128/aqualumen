#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-radiance-test.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/test/dev/aqualumen/physics/ReceiverRadianceVolumeTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverRadianceVolumeTest
"$java_bin/javac" -proc:none -cp "$classes" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverRadiancePublisher.java physics-mod/test/dev/aqualumen/physics/ReceiverRadiancePublisherTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverRadiancePublisherTest
