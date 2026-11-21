#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-run-radiance-test.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/dev/aqualumen/physics/ReceiverRunLayout.java physics-mod/dev/aqualumen/physics/ReceiverRunRadiance.java physics-mod/test/dev/aqualumen/physics/ReceiverRunRadianceTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverRunRadianceTest
"$java_bin/javac" -proc:none -cp "$classes" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverRadiancePublisher.java physics-mod/dev/aqualumen/physics/ReceiverRunPublisher.java physics-mod/test/dev/aqualumen/physics/ReceiverRunPublisherTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverRunPublisherTest
"$java_bin/javac" -proc:none -cp "$classes" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverSourceVolume.java physics-mod/dev/aqualumen/physics/ReceiverCaptureCache.java physics-mod/dev/aqualumen/physics/ReceiverRunSourceCapture.java physics-mod/test/dev/aqualumen/physics/ReceiverRunSourceCaptureTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverRunSourceCaptureTest
