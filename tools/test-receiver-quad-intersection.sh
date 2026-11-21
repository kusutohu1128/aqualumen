#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-quad-intersection-test.XXXXXX)
"$java_bin/javac" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverQuadIntersection.java physics-mod/test/dev/aqualumen/physics/ReceiverQuadIntersectionTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverQuadIntersectionTest
